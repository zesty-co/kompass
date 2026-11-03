"""Behavior tests for the release review and publication boundary (no pip deps)."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("release_notes", Path(__file__).with_name("release_notes.py"))
rn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rn)


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.charts = self.root / "charts"
        for name in ("kompass", "kompass-insights", "pod-rightsizing", "kompass-pod-placement"):
            chart = self.charts / name
            chart.mkdir(parents=True)
            (chart / "Chart.yaml").write_text(json.dumps({"name": name, "version": "2.0.0"}))
            (chart / "values.yaml").write_text("replicas: 2\n")
        self.inputs = {
            "schema_version": 1,
            "source": {"spoke_sha": "a" * 40, "components": {"agent": "v2"}, "rightsizing": {"sha": "b" * 40}},
            "baselines": {"kompass": {"version": "1.0.0"}, "kompass-insights": {"version": "1.0.0"}},
            "changed_charts": ["kompass", "kompass-insights"],
            "entries": [self.entry("Visible improvement", "feature:1"), self.entry("Private detail", "feature:2")],
            "coverage": {"insights": "complete"},
        }
        self.bundle = self.root / "bundle"

    def entry(self, title, key):
        return {"actor": "insights", "kind": "feature", "title": title, "body": "Improves reliability.",
                "source_key": key, "source_url": "https://private.example/issue/123", "charts": ["kompass-insights"]}

    def generate(self, **kwargs):
        return rn.generate(self.inputs, self.charts, self.bundle, **kwargs)

    def review(self, audiences):
        review = rn.load_json(self.bundle / "review.yaml")
        entries = rn.load_json(self.bundle / "entries.json")["entries"]
        for entry in entries:
            review["entries"][entry["id"]]["audience"] = audiences.get(entry["title"], "not-customer-facing")
        rn.write_json(self.bundle / "review.yaml", review)

    def test_review_gate_and_public_projection(self):
        self.generate()
        with self.assertRaisesRegex(ValueError, "pending"):
            rn.render(self.bundle, self.root / "public")
        self.review({"Visible improvement": "customer-facing"})
        rn.render(self.bundle, self.root / "public")
        for name in ("kompass", "kompass-insights"):
            text = (self.root / "public" / name / "RELEASE_NOTES.md").read_text()
            self.assertIn("Visible improvement", text)
            self.assertIn("1.0.0", text)
            self.assertIn("2.0.0", text)
            self.assertNotIn("Private detail", text)
            self.assertNotIn("private.example", text)
            self.assertIn("Insights", text)
        self.assertFalse((self.root / "public" / "pod-rightsizing").exists())
        self.assertIn("feature:1", (self.bundle / "README.md").read_text())

    def test_promotion_identity_ignores_descriptions_and_preserves_dependency_snapshot(self):
        source = {"spoke_sha": "a" * 40,
                  "components": {"agent": {"project": "agent", "tag": "v2", "sha": "b" * 40,
                                             "image_tag": "v2", "description": "old", "released_at": "yesterday"}},
                  "rightsizing": {"tag": "v3", "sha": "c" * 40, "description": "old"}}
        identity = rn.promotion_id(source)
        changed = copy.deepcopy(source)
        changed["components"]["agent"].update(description="new", released_at="today")
        changed["rightsizing"]["description"] = "new"
        self.assertEqual(identity, rn.promotion_id(changed))
        changed["components"]["agent"]["sha"] = "d" * 40
        self.assertNotEqual(identity, rn.promotion_id(changed))
        self.inputs["source"] = source
        self.inputs["dependencies"] = {"kompass": [{"name": "admission", "version": "1.0.0", "sha256": "d" * 64}]}
        manifest = self.generate()
        self.assertEqual(identity, manifest["promotion_id"])
        self.assertEqual(self.inputs["dependencies"], manifest["dependencies"])
        rn.validate(self.bundle)

    def test_unchanged_retry_preserves_product_yaml_and_summary_bytes(self):
        self.inputs["generator_revision"] = "f" * 40
        self.inputs["public_base_sha"] = "a" * 40
        self.generate()
        entries = rn.load_json(self.bundle / "entries.json")["entries"]
        review_text = "# Product reviewed this release\nschema_version: 1\nentries:\n"
        for entry in entries:
            review_text += (f"  {entry['id']}:\n    audience: customer-facing\n"
                            f"    content_hash: '{entry['content_hash']}'\n")
        (self.bundle / "review.yaml").write_text(review_text)
        before = {path.name: path.read_bytes() for path in self.bundle.iterdir()}
        other = self.root / "retry"
        manifest = rn.generate(self.inputs, self.charts, other, self.bundle)
        self.assertEqual("f" * 40, manifest["generator_revision"])
        self.assertEqual("a" * 40, manifest["public_base_sha"])
        self.assertEqual(before, {path.name: path.read_bytes() for path in other.iterdir()})
        rn.generate(self.inputs, self.charts, self.bundle, self.bundle)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.bundle.iterdir()})
        self.inputs["entries"][0]["body"] = "Changed after Product review"
        rn.generate(self.inputs, self.charts, other, self.bundle)
        decisions = rn.load_json(other / "review.yaml")["entries"]
        self.assertEqual(["customer-facing", "pending"], sorted(d["audience"] for d in decisions.values()))
        self.assertIn("Changed after Product review", (other / "README.md").read_text())
        self.inputs["generator_revision"] = "e" * 40
        revised = rn.generate(self.inputs, self.charts, other, self.bundle)
        self.assertNotEqual(manifest["manifest_digest"], revised["manifest_digest"])

    def test_runtime_hash_uses_git_modes_not_umask_or_empty_directories(self):
        chart = self.charts / "kompass"
        original = rn.chart_digest(chart)
        chart.chmod(0o700)
        for path in chart.iterdir():
            path.chmod(0o600)
        (chart / "empty-directory").mkdir(mode=0o700)
        self.assertEqual(original, rn.chart_digest(chart))
        (chart / "values.yaml").chmod(0o700)
        executable = rn.chart_digest(chart)
        self.assertNotEqual(original, executable)
        (chart / "values.yaml").chmod(0o755)
        self.assertEqual(executable, rn.chart_digest(chart))

    def test_deterministic_identity_and_exact_review_carryforward(self):
        self.generate()
        self.review({"Visible improvement": "customer-facing"})
        before = rn.load_json(self.bundle / "manifest.json")
        other = self.root / "other"
        reordered = copy.deepcopy(self.inputs)
        reordered["entries"].reverse()
        reordered["changed_charts"].reverse()
        rn.generate(reordered, self.charts, other, self.bundle)
        self.assertEqual((self.bundle / "manifest.json").read_bytes(), (other / "manifest.json").read_bytes())
        self.assertEqual((self.bundle / "review.yaml").read_bytes(), (other / "review.yaml").read_bytes())
        self.inputs["entries"][0]["body"] = "Changed claim"
        rn.generate(self.inputs, self.charts, other, self.bundle)
        after = rn.load_json(other / "manifest.json")
        self.assertEqual(before["promotion_id"], after["promotion_id"])
        changed = next(e for e in rn.load_json(other / "entries.json")["entries"] if e["title"] == "Visible improvement")
        self.assertEqual(rn.load_json(other / "review.yaml")["entries"][changed["id"]]["audience"], "pending")
        self.inputs["source"]["spoke_sha"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "identity"):
            rn.generate(self.inputs, self.charts, other, self.bundle)

    def test_umbrella_only_does_not_republish_child(self):
        self.inputs["changed_charts"] = ["kompass"]
        self.generate()
        self.review({"Visible improvement": "customer-facing"})
        rn.render(self.bundle, self.root / "public")
        self.assertIn("Visible improvement", (self.root / "public/kompass/RELEASE_NOTES.md").read_text())
        self.assertFalse((self.root / "public/kompass-insights").exists())

    def test_payload_binds_bytes_paths_modes_but_not_generated_notes(self):
        chart = self.charts / "kompass"
        original = rn.chart_digest(chart)
        (chart / "RELEASE_NOTES.md").write_text("Review metadata")
        self.assertEqual(original, rn.chart_digest(chart))
        values = chart / "values.yaml"
        values.chmod(0o755)
        self.assertNotEqual(original, rn.chart_digest(chart))
        values.chmod(0o644)
        values.rename(chart / "renamed.yaml")
        self.assertNotEqual(original, rn.chart_digest(chart))
        (chart / "renamed.yaml").rename(values)
        values.write_text("replicas: 3\n")
        self.assertNotEqual(original, rn.chart_digest(chart))
        self.generate()
        values.write_text("replicas: 4\n")
        with self.assertRaisesRegex(ValueError, "runtime"):
            rn.validate(self.bundle, charts_root=self.charts)

    def test_source_symlinks_rejected_even_excluded_notes(self):
        for name in ("values.yaml", "RELEASE_NOTES.md"):
            with self.subTest(name=name):
                target = self.charts / "kompass" / name
                target.unlink(missing_ok=True)
                target.symlink_to(self.charts / "kompass-insights/Chart.yaml")
                with self.assertRaisesRegex(ValueError, "symlink"):
                    rn.chart_digest(self.charts / "kompass")
                target.unlink()

    def test_input_schema_and_evidence_rejected(self):
        mutations = [
            lambda d: d.pop("changed_charts"),
            lambda d: d["changed_charts"].append("../escape"),
            lambda d: d["entries"].append(copy.deepcopy(d["entries"][0])),
            lambda d: d["entries"][0].pop("source_key"),
            lambda d: d["entries"][0].update(actor="unknown"),
            lambda d: d["entries"][0].update(charts=["../escape"]),
            lambda d: d.update(schema_version=2),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                original = self.inputs
                self.inputs = copy.deepcopy(original)
                mutate(self.inputs)
                with self.assertRaises(ValueError):
                    self.generate()
                self.inputs = original

    def test_review_rejects_missing_unknown_stale_and_invalid_classification(self):
        self.generate()
        original = rn.load_json(self.bundle / "review.yaml")
        key = next(iter(original["entries"]))
        mutations = [lambda d: d["entries"].pop(key),
                     lambda d: d["entries"].update(unknown=d["entries"][key]),
                     lambda d: d["entries"][key].update(content_hash="0" * 64),
                     lambda d: d["entries"][key].update(audience="approved")]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                changed = copy.deepcopy(original)
                mutate(changed)
                rn.write_json(self.bundle / "review.yaml", changed)
                with self.assertRaises(ValueError):
                    rn.validate(self.bundle)

    def test_tampered_entries_rejected(self):
        self.generate()
        entries = rn.load_json(self.bundle / "entries.json")
        entries["entries"][0]["body"] = "Unreviewed public claim"
        rn.write_json(self.bundle / "entries.json", entries)
        with self.assertRaises(ValueError):
            rn.validate(self.bundle)

    def test_valid_hash_cannot_hide_invalid_projection_membership(self):
        self.generate()
        original = rn.load_json(self.bundle / "manifest.json")
        for membership in ([], ["unknown"], original["charts"][0]["entry_ids"] * 2):
            with self.subTest(membership=membership):
                manifest = copy.deepcopy(original)
                manifest["charts"][0]["entry_ids"] = membership
                manifest["manifest_digest"] = rn.digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
                rn.write_json(self.bundle / "manifest.json", manifest)
                with self.assertRaisesRegex(ValueError, "chart entries"):
                    rn.validate(self.bundle)

    def test_duplicate_review_mapping_is_not_silently_last_wins(self):
        self.generate()
        review = rn.load_json(self.bundle / "review.yaml")
        key = next(iter(review["entries"]))
        value = json.dumps(review["entries"][key])
        (self.bundle / "review.yaml").write_text(
            '{"schema_version":1,"entries":{' + json.dumps(key) + ':' + value + ',' + json.dumps(key) + ':' + value + '}}')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rn.validate(self.bundle)

    def test_tampered_manifest_rejected(self):
        self.generate()
        manifest = rn.load_json(self.bundle / "manifest.json")
        manifest["charts"][0]["entry_ids"].append("unknown")
        rn.write_json(self.bundle / "manifest.json", manifest)
        with self.assertRaises(ValueError):
            rn.validate(self.bundle)

    def test_yaml_review_and_literal_upstream_text(self):
        self.inputs["entries"] = [self.entry("<script>alert(1)</script> @everyone [click](javascript:bad)", "feature:3")]
        self.generate()
        entry = rn.load_json(self.bundle / "entries.json")["entries"][0]
        (self.bundle / "review.yaml").write_text(
            f"schema_version: 1\nentries:\n  {entry['id']}:\n    content_hash: {entry['content_hash']}\n    audience: customer-facing\n")
        rn.render(self.bundle, self.root / "public")
        text = (self.root / "public/combined.md").read_text()
        self.assertNotIn("<script>", text)
        self.assertNotIn("@everyone", text)
        self.assertNotIn("[click](javascript:", text)

    def test_text_bullets_use_exact_normalized_text_not_fuzzy_matching(self):
        self.inputs["entries"] = [dict(self.entry("First bullet", "release:v1"), kind="text"),
                                  dict(self.entry("Second bullet", "release:v1"), kind="text")]
        self.generate()
        entries = rn.load_json(self.bundle / "entries.json")["entries"]
        self.assertEqual(2, len({e["id"] for e in entries}))
        self.review({"First bullet": "customer-facing"})
        self.inputs["entries"][0]["title"] = "First bullet improved"
        other = self.root / "other"
        rn.generate(self.inputs, self.charts, other, self.bundle)
        new = next(e for e in rn.load_json(other / "entries.json")["entries"] if e["title"] == "First bullet improved")
        self.assertNotIn(new["id"], {e["id"] for e in entries})

    def test_cli_generate_validate_render_preview_and_runtime_check(self):
        path = self.root / "inputs.json"
        rn.write_json(path, self.inputs)
        def cli(*args):
            return subprocess.run([sys.executable, str(Path(rn.__file__)), *map(str, args)], capture_output=True, text=True)
        result = cli("generate", "--inputs", path, "--charts", self.charts, "--output", self.bundle)
        self.assertEqual(0, result.returncode, result.stderr)
        result = cli("validate", "--bundle", self.bundle, "--charts", self.charts)
        self.assertEqual(0, result.returncode, result.stderr)
        result = cli("render", "--bundle", self.bundle, "--output", self.root / "preview", "--preview")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("Visible improvement", (self.root / "preview/combined.md").read_text())
        result = cli("validate", "--bundle", self.bundle, "--require-review")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("pending", result.stderr)


if __name__ == "__main__":
    unittest.main()
