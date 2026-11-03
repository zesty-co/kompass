#!/usr/bin/env python3
"""Deterministic, evidence-backed release review bundles; Python stdlib plus yq.

Collector input is deliberately not a release-note inference engine. Product
classifies exact evidence entries; only approved title/body text is published.
No chart metadata or runtime files are modified by this module.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import unicodedata

CHARTS = frozenset(("kompass", "kompass-insights", "kompass-pod-placement", "pod-rightsizing"))
ACTORS = {"insights": "Insights Agent", "rightsizing": "Rightsizing", "placement": "Pod Placement",
          "bridge": "Bridge/shared", "shared": "Bridge/shared", "bridge/shared": "Bridge/shared"}
AUDIENCES = frozenset(("pending", "customer-facing", "not-customer-facing"))
VOLATILE = frozenset(("timestamp", "generated_at", "updated_at", "created_at", "collected_at"))
ENTRY_FIELDS = frozenset(("actor", "kind", "title", "body", "source_key", "source_url", "charts"))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON/YAML key: {key}")
        result[key] = value
    return result


def _parse(text):
    return json.loads(text, object_pairs_hook=_object,
                      parse_constant=lambda value: _require(False, f"invalid number: {value}"))


def load_json(path):
    return _parse(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _stable(value):
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def digest(value):
    """SHA256 of sorted, compact UTF-8 JSON, omitting volatile timestamp fields."""
    data = json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _yaml(path):
    # JSON syntax is valid YAML; avoid the subprocess for generated review files.
    text = Path(path).read_text(encoding="utf-8")
    try:
        return _parse(text)
    except json.JSONDecodeError:
        result = subprocess.run(["yq", "-o=json", ".", str(path)], check=True, capture_output=True, text=True)
        return _parse(result.stdout)


def _keys(value, required, optional=()):
    _require(isinstance(value, dict), "expected object")
    _require(set(required) <= value.keys(), f"missing fields: {sorted(set(required) - value.keys())}")
    _require(value.keys() <= set(required) | set(optional), f"unknown fields: {sorted(value.keys() - set(required) - set(optional))}")


def _schema(value, required, optional=()):
    _keys(value, set(required) | {"schema_version"}, optional)
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1, "unsupported schema_version")


def _string(value, field, empty=False):
    _require(isinstance(value, str) and (empty or bool(value.strip())), f"invalid {field}")
    return value


def _names(names):
    _require(isinstance(names, list) and all(isinstance(n, str) and n in CHARTS for n in names), "unknown chart name")
    _require(len(names) == len(set(names)), "duplicate chart name")
    return sorted(names)


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _revision(value):
    _require(isinstance(value, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None,
             "invalid Git revision")


def promotion_id(source):
    """Identity available before collection: only immutable source release pins.

    Component records may be keyed by name or supplied as a project-sorted list.
    String-valued legacy component pins remain supported. Evidence descriptions,
    release timestamps and additional source fields never affect this identity.
    """
    _require(isinstance(source, dict) and {"spoke_sha", "components", "rightsizing"} <= source.keys(), "missing source identities")
    _string(source["spoke_sha"], "spoke_sha")
    _require(isinstance(source["components"], (dict, list)), "components must be an object or list")
    _require(isinstance(source["rightsizing"], (dict, str)), "invalid rightsizing identity")
    def pin(value, fields):
        if isinstance(value, str):
            return _string(value, "release pin")
        _require(isinstance(value, dict), "invalid release pin")
        result = {key: value[key] for key in fields if key in value}
        _require(bool(result), "missing release pin identity")
        for key, item in result.items():
            _string(item, key)
        return result
    components = source["components"]
    fields = ("project", "tag", "sha", "image_tag")
    if isinstance(components, dict):
        components = {name: pin(value, fields) for name, value in components.items()}
    else:
        components = sorted((pin(value, fields) for value in components), key=lambda value: json.dumps(value, sort_keys=True))
        _require(len({digest(value) for value in components}) == len(components), "duplicate component identity")
    return digest({"spoke_sha": source["spoke_sha"], "components": components,
                   "rightsizing": pin(source["rightsizing"], ("tag", "sha"))})


def chart_digest(path):
    """Bind relative paths, Git executable modes and file bytes; reject symlinks.

    Only the chart-root generated RELEASE_NOTES.md is excluded. Nested files,
    including dotfiles, are bound. Empty directories, mtimes, ownership and
    umask-dependent permission bits are not persisted by Git and are ignored.
    """
    path = Path(path)
    _require(not path.is_symlink(), f"symlink chart: {path}")
    _require(path.is_dir(), f"missing chart: {path}")
    records = []
    for item in sorted(path.rglob("*")):
        relative = item.relative_to(path).as_posix()
        mode = item.lstat().st_mode
        _require(not stat.S_ISLNK(mode), f"symlink in chart: {relative}")
        if relative == "RELEASE_NOTES.md":
            continue
        _require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), f"unsupported chart file: {relative}")
        if stat.S_ISREG(mode):
            records.append({"path": relative, "mode": "100755" if mode & stat.S_IXUSR else "100644",
                            "sha256": hashlib.sha256(item.read_bytes()).hexdigest()})
    return digest(records)


def _text(value):
    return unicodedata.normalize("NFC", "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")))


def _entry(raw):
    _keys(raw, ENTRY_FIELDS, {"coverage"})
    for field in ENTRY_FIELDS - {"charts"}:
        _string(raw[field], field, empty=field == "body")
    _require(raw["actor"] in ACTORS, "unknown actor")
    charts = _names(raw["charts"])
    _require(bool(charts), "entry requires chart evidence membership")
    entry = dict(raw, title=_text(raw["title"]), body=_text(raw["body"]), charts=charts)
    identity = {"actor": entry["actor"], "source_key": entry["source_key"]}
    if entry["kind"] in ("text", "bullet", "text-only"):
        identity.update(title=entry["title"], body=entry["body"])
    return dict(entry, id=digest(identity), content_hash=digest(entry))


def reconcile_entries(entries, previous):
    """Return review map; previous is a review entry map, never fuzzy-matched."""
    result = {}
    for entry in entries:
        old = previous.get(entry["id"], {})
        audience = old.get("audience", "pending") if old.get("content_hash") == entry["content_hash"] else "pending"
        _require(audience in AUDIENCES, "invalid prior audience")
        result[entry["id"]] = {"content_hash": entry["content_hash"], "audience": audience}
    return result


def _entries(raw_entries):
    _require(isinstance(raw_entries, list), "entries must be a list")
    entries = sorted((_entry(raw) for raw in raw_entries), key=lambda e: e["id"])
    _require(len({entry["id"] for entry in entries}) == len(entries), "duplicate entry identity")
    return entries


def _membership(entries, chart):
    return sorted(e["id"] for e in entries if chart == "kompass" or chart in e["charts"])


def _previous_version(baselines, name):
    baseline = baselines.get(name)
    if isinstance(baseline, dict):
        baseline = baseline.get("version")
    _require(baseline is None or isinstance(baseline, str), "invalid baseline version")
    return baseline


def _literal(text):
    text = html.escape(text, quote=False).replace("@", "&#64;")
    return re.sub(r"([\\`*_{}\[\]()#+!|~>-])", r"\\\1", text)


def _summary(manifest, entries, review):
    lines = ["# Release review", "", f"Promotion: `{manifest['promotion_id']}`", "",
             "Edit only audience in review.yaml: pending, customer-facing, or not-customer-facing.",
             "Every entry must be classified before publication. Do not edit content_hash or IDs.",
             "To change wording/evidence, update collector input and regenerate; changed entries reset to pending.",
             "No fuzzy matching is performed. README is a generation-time snapshot; review.yaml is authoritative.", ""]
    for entry in entries:
        lines += [f"## {ACTORS[entry['actor']]}: {_literal(entry['title'])}", "",
                  f"ID: `{entry['id']}`", f"Audience: {review[entry['id']]['audience']}",
                  f"Content hash: `{entry['content_hash']}`", f"Kind: {_literal(entry['kind'])}",
                  f"Charts: {', '.join(entry['charts'])}", "", _literal(entry["body"]), "",
                  f"Source key: {_literal(entry['source_key'])}", f"Source: {_literal(entry['source_url'])}", ""]
        if "coverage" in entry:
            lines += ["Coverage: " + _literal(json.dumps(entry["coverage"], sort_keys=True)), ""]
    lines += ["## Collection coverage", "", _literal(json.dumps(manifest.get("coverage", {}), sort_keys=True)), ""]
    return "\n".join(lines)


def generate(inputs, charts_root, output_dir, previous_dir=None):
    """Create a bundle and return manifest. Inputs may be an object or JSON path."""
    if isinstance(inputs, (str, Path)):
        inputs = load_json(inputs)
    _schema(inputs, {"source", "baselines", "entries", "changed_charts"},
            {"coverage", "dependencies", "generator_revision", "public_base_sha"})
    identity = promotion_id(inputs["source"])
    _require(isinstance(inputs["baselines"], dict), "baselines must be an object")
    names = _names(inputs["changed_charts"])
    entries = _entries(inputs["entries"])
    previous = {}
    old = None
    if previous_dir is not None:
        old = validate(previous_dir)
        _require(old["promotion_id"] == identity, "previous promotion source identity mismatch")
        previous = _yaml(Path(previous_dir) / "review.yaml")["entries"]
    review = reconcile_entries(entries, previous)
    charts = []
    for name in names:
        path = Path(charts_root) / name
        runtime_digest = chart_digest(path)
        metadata = _yaml(path / "Chart.yaml")
        _require(isinstance(metadata, dict) and metadata.get("name") == name, f"chart name mismatch: {name}")
        version = _string(metadata.get("version"), "chart version")
        charts.append({"name": name, "version": version, "previous_version": _previous_version(inputs["baselines"], name),
                       "runtime_digest": runtime_digest, "entry_ids": _membership(entries, name)})
    document = {"schema_version": 1, "entries": entries}
    manifest = {"schema_version": 1, "promotion_id": identity, "source": inputs["source"],
                "baselines": inputs["baselines"], "charts": charts, "entries_digest": digest(document),
                "coverage": inputs.get("coverage", {})}
    if "dependencies" in inputs:
        _require(isinstance(inputs["dependencies"], (dict, list)), "dependencies must be an object or list")
        manifest["dependencies"] = inputs["dependencies"]
    for field in ("generator_revision", "public_base_sha"):
        if field in inputs:
            _revision(inputs[field])
            manifest[field] = inputs[field]
    manifest["manifest_digest"] = digest(manifest)
    output = Path(output_dir)
    if old == manifest and previous == review:
        # Read first: previous_dir may be output_dir. Product formatting and the
        # generation-time summary must not create a new Git revision on retry.
        preserved = {name: (Path(previous_dir) / name).read_bytes()
                     for name in ("manifest.json", "entries.json", "review.yaml", "README.md")}
        output.mkdir(parents=True, exist_ok=True)
        for name, content in preserved.items():
            (output / name).write_bytes(content)
        return manifest
    write_json(output / "manifest.json", manifest)
    write_json(output / "entries.json", document)
    write_json(output / "review.yaml", {"schema_version": 1, "entries": review})
    (output / "README.md").write_text(_summary(manifest, entries, review), encoding="utf-8")
    return manifest


def validate(bundle_dir, require_review=False, charts_root=None):
    """Validate schema, integrity, exact review coverage and optional runtime tree.

    Returns the validated manifest. Hashes bind bundle content, not authenticity;
    callers must obtain the bundle from their trusted reviewed Git revision.
    """
    bundle = Path(bundle_dir)
    manifest = load_json(bundle / "manifest.json")
    _schema(manifest, {"promotion_id", "source", "baselines", "charts", "entries_digest", "manifest_digest"},
            {"coverage", "dependencies", "generator_revision", "public_base_sha"})
    for field in ("generator_revision", "public_base_sha"):
        if field in manifest:
            _revision(manifest[field])
    _require(_hash(manifest["promotion_id"]) and manifest["promotion_id"] == promotion_id(manifest["source"]), "promotion identity mismatch")
    if "dependencies" in manifest:
        _require(isinstance(manifest["dependencies"], (dict, list)), "dependencies must be an object or list")
    _require(manifest["manifest_digest"] == digest({k: v for k, v in manifest.items() if k != "manifest_digest"}), "manifest digest mismatch")
    _require(isinstance(manifest["baselines"], dict), "baselines must be an object")
    document = load_json(bundle / "entries.json")
    _schema(document, {"entries"})
    _require(isinstance(document["entries"], list), "entries must be a list")
    raw = []
    for entry in document["entries"]:
        _keys(entry, ENTRY_FIELDS | {"id", "content_hash"}, {"coverage"})
        raw.append({k: v for k, v in entry.items() if k not in ("id", "content_hash")})
    entries = _entries(raw)
    _require(document["entries"] == entries, "entry identity/content hash mismatch or noncanonical entries")
    _require(manifest["entries_digest"] == digest(document), "entries digest mismatch")
    review = _yaml(bundle / "review.yaml")
    _schema(review, {"entries"})
    _require(isinstance(review["entries"], dict), "review entries must be an object")
    _require(set(review["entries"]) == {e["id"] for e in entries}, "missing or unknown review entries")
    for entry in entries:
        decision = review["entries"][entry["id"]]
        _keys(decision, {"content_hash", "audience"})
        _require(decision["content_hash"] == entry["content_hash"], "stale review content hash")
        _require(isinstance(decision["audience"], str) and decision["audience"] in AUDIENCES, "invalid audience")
        _require(not require_review or decision["audience"] != "pending", f"pending review: {entry['id']}")
    _require(isinstance(manifest["charts"], list), "charts must be a list")
    names = []
    for chart in manifest["charts"]:
        _keys(chart, {"name", "version", "previous_version", "runtime_digest", "entry_ids"})
        _names([chart["name"]])
        names.append(chart["name"])
        _string(chart["version"], "chart version")
        _require(chart["previous_version"] == _previous_version(manifest["baselines"], chart["name"]), "baseline version mismatch")
        _require(_hash(chart["runtime_digest"]), "invalid runtime digest")
        _require(chart["entry_ids"] == _membership(entries, chart["name"]), "missing, duplicate or unknown chart entries")
        if charts_root is not None:
            path = Path(charts_root) / chart["name"]
            _require(chart_digest(path) == chart["runtime_digest"], f"runtime digest mismatch: {chart['name']}")
            metadata = _yaml(path / "Chart.yaml")
            _require(metadata.get("name") == chart["name"] and metadata.get("version") == chart["version"], "runtime chart metadata mismatch")
    _require(names == _names(names), "noncanonical chart order")
    return manifest


def render(bundle_dir, output_dir, require_review=True):
    """Write only selected chart projections and combined.md; never raw evidence."""
    manifest = validate(bundle_dir, require_review=require_review)
    bundle = Path(bundle_dir)
    entries = load_json(bundle / "entries.json")["entries"]
    review = _yaml(bundle / "review.yaml")["entries"]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    combined = []
    for chart in manifest["charts"]:
        lines = [f"# {_literal(chart['name'])} release notes", "",
                 f"Version: {_literal(chart['previous_version'] or 'initial')} → {_literal(chart['version'])}", ""]
        visible = [e for e in entries if e["id"] in chart["entry_ids"] and review[e["id"]]["audience"] == "customer-facing"]
        for actor in sorted({e["actor"] for e in visible}):
            lines += [f"## {ACTORS[actor]}", ""]
            for entry in visible:
                if entry["actor"] == actor:
                    lines += [f"- {_literal(entry['title']).replace(chr(10), ' ')}"]
                    if entry["body"]:
                        lines += ["  " + line for line in _literal(entry["body"]).splitlines()]
            lines.append("")
        if not visible:
            lines += ["No customer-facing changes.", ""]
        text = "\n".join(lines)
        destination = output / chart["name"]
        _require(not destination.is_symlink(), "symlink output chart")
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / "RELEASE_NOTES.md"
        _require(not target.is_symlink(), "symlink output release notes")
        target.write_text(text, encoding="utf-8")
        combined.append(text)
    _require(not (output / "combined.md").is_symlink(), "symlink combined output")
    (output / "combined.md").write_text("\n".join(combined), encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate_parser = commands.add_parser("generate")
    for flag in ("inputs", "charts", "output"):
        generate_parser.add_argument("--" + flag, required=True)
    generate_parser.add_argument("--previous")
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--bundle", required=True)
    validate_parser.add_argument("--require-review", action="store_true")
    validate_parser.add_argument("--charts")
    render_parser = commands.add_parser("render")
    render_parser.add_argument("--bundle", required=True)
    render_parser.add_argument("--output", required=True)
    render_parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate(args.inputs, args.charts, args.output, args.previous)
        elif args.command == "validate":
            validate(args.bundle, args.require_review, args.charts)
        else:
            render(args.bundle, args.output, not args.preview)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"release-notes: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
