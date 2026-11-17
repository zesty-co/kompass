#!/usr/bin/env python3
"""Check newly uploaded releases against Helm packages (requires helm, yq, gh).

Run after cr upload, using its default name-version tags, before publishing the
index. This read-only creation check does not restrict later release-body edits.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from urllib.parse import quote


def packaged_notes(package):
    with tarfile.open(package, "r:gz") as archive:
        members = {}
        roots = set()
        for member in archive.getmembers():
            parts = member.name.split("/")
            if (
                any(part in ("", ".", "..") for part in parts)
                or "\\" in member.name
                or not (member.isfile() or member.isdir())
                or member.name in members
            ):
                raise ValueError(f"Invalid or duplicate archive entry: {member.name}")
            roots.add(parts[0])
            members[member.name] = member
        if len(roots) != 1:
            raise ValueError("Expected one chart root in the package")
        root = roots.pop()
        chart = members.get(f"{root}/Chart.yaml")
        if chart is None or not chart.isfile():
            raise ValueError("Missing regular Chart.yaml")
        # Reuse CI's chart validator and YAML parser instead of approximating either.
        chart_yaml = subprocess.run(
            ["helm", "show", "chart", str(package.resolve())],
            check=True, capture_output=True, timeout=60,
        ).stdout
        metadata = json.loads(subprocess.run(
            ["yq", "-o=json", ".", "-"],
            input=chart_yaml,
            check=True, capture_output=True, timeout=60,
        ).stdout)
        if metadata["name"] != root:
            raise ValueError("Chart root does not match chart metadata")
        tag = f"{metadata['name']}-{metadata['version']}"
        if package.name != f"{tag}.tgz":
            raise ValueError(f"Package filename does not match chart metadata: {tag}")
        notes = members.get(f"{root}/RELEASE_NOTES.md")
        if notes is None:
            return tag, None
        if not notes.isfile():
            raise ValueError("RELEASE_NOTES.md must be a regular file")
        return tag, archive.extractfile(notes).read().decode("utf-8")


def release_body(repository, tag):
    response = subprocess.run(
        ["gh", "api", "--method", "GET",
         f"repos/{repository}/releases/tags/{quote(tag, safe='')}"],
        check=True, capture_output=True, timeout=60,
    ).stdout
    try:
        release = json.loads(response)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"Invalid release response for {tag}") from error
    if (
        not isinstance(release, dict)
        or release.get("tag_name") != tag
        or not isinstance(release.get("body"), str)
    ):
        raise ValueError(f"Invalid release response for {tag}: expected tag and text body")
    return release["body"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_directory", type=Path)
    parser.add_argument("repository", help="GitHub OWNER/REPO")
    args = parser.parse_args()
    packages = sorted(args.package_directory.glob("*.tgz"))
    if not packages:
        parser.exit(1, f"No chart packages found in {args.package_directory}\n")
    for package in packages:
        try:
            tag, notes = packaged_notes(package)
            if notes is None:
                print(f"Skipped {tag}: no RELEASE_NOTES.md; retaining fallback description")
                continue
            if release_body(args.repository, tag) != notes:
                raise ValueError(f"Release {tag} body does not match packaged RELEASE_NOTES.md")
            print(f"Verified {tag}: release body matches packaged RELEASE_NOTES.md exactly")
        except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
            detail = str(error)
            if isinstance(error, subprocess.CalledProcessError):
                detail = error.stderr.decode("utf-8", errors="replace").strip() or detail
            parser.exit(1, f"Error verifying {package.name}: {detail}\n")


if __name__ == "__main__":
    main()
