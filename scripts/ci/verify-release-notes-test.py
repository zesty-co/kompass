#!/usr/bin/env python3
"""Exercise the release-note verifier and publication gate without remote writes."""

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from urllib.parse import unquote


REPOSITORY = Path(__file__).resolve().parents[2]
VERIFIER = REPOSITORY / "scripts/ci/verify-release-notes.py"
NOTES = "## Changelog\r\n\r\n- fix: café rollout  \r\n\r\n"
CHART = b"apiVersion: v2\nname: kompass\nversion: 1.2.3\n"
CHILD_CHART = b"apiVersion: v2\nname: child\nversion: 1.0.0\n"

FAKE_GH = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
from urllib.parse import unquote

args = sys.argv[1:]
if not args or args.pop(0) != "api":
    sys.exit("Only gh api is supported by this fixture")
method = "GET"
if "--method" in args:
    index = args.index("--method")
    method = args[index + 1]
    del args[index:index + 2]
if len(args) != 1:
    sys.exit("Expected one API endpoint")
endpoint = args[0]
with open(os.environ["CALLS"], "a") as calls:
    calls.write(json.dumps({"tool": "gh", "method": method, "endpoint": endpoint}) + "\\n")
if method != "GET":
    sys.exit("Remote mutations are forbidden")
prefix = "repos/test-owner/charts/releases/tags/"
if not endpoint.startswith(prefix):
    sys.exit("Unexpected repository or API endpoint")
tag = unquote(endpoint[len(prefix):])
responses = json.loads(Path(os.environ["RESPONSES"]).read_text())
response = responses.get(tag, {"error": "HTTP 404: release not found"})
if "error" in response:
    sys.exit(response["error"])
sys.stdout.write(response["raw"])
"""

FAKE_PUBLISH_COMMAND = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

tool = Path(sys.argv[0]).name
with open(os.environ["CALLS"], "a") as calls:
    calls.write(json.dumps({"tool": tool, "args": sys.argv[1:]}) + "\\n")
if tool == "cr" and sys.argv[1] == "upload":
    sys.exit(int(os.environ.get("UPLOAD_EXIT", "0")))
"""


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="release-notes-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.packages = self.root / ".cr-release-packages"
        self.packages.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "calls.jsonl"
        self.responses_file = self.root / "responses.json"
        self.responses = {}
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "CALLS": str(self.calls),
            "RESPONSES": str(self.responses_file),
            "GH_TOKEN": "fixture-token",
            "CR_OWNER": "test-owner",
            "CR_GIT_REPO": "charts",
            "GITHUB_SHA": "fixture-commit",
            "UPLOAD_EXIT": "0",
        }
        self.command("gh", FAKE_GH)

    def command(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def archive(self, filename, entries):
        with tarfile.open(self.packages / filename, "w:gz") as archive:
            for name, content in entries:
                member = tarfile.TarInfo(name)
                if content is None:
                    member.type = tarfile.DIRTYPE
                    archive.addfile(member)
                else:
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))

    def package(self, name="kompass", version="1.2.3", notes=NOTES, extra=()):
        metadata = f"apiVersion: v2\nname: {name}\nversion: {version}\n".encode()
        entries = [(f"{name}/Chart.yaml", metadata)]
        if notes is not None:
            entries.append((f"{name}/RELEASE_NOTES.md", notes.encode()))
        self.archive(f"{name}-{version}.tgz", entries + list(extra))
        return f"{name}-{version}"

    def release(self, tag, body):
        self.responses[tag] = {"raw": json.dumps({"tag_name": tag, "body": body})}

    def run_command(self, command):
        self.responses_file.write_text(json.dumps(self.responses))
        self.calls.write_text("")
        return subprocess.run(
            command, cwd=self.root, env=self.env, capture_output=True, text=True,
            timeout=30,
        )

    def verify(self):
        return self.run_command(
            [sys.executable, str(VERIFIER), str(self.packages), "test-owner/charts"]
        )

    def recorded_calls(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_failure(self, result, message):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)

    def test_verifies_every_package_and_skips_legacy_and_nested_notes(self):
        nested = [
            ("kompass/charts/child/Chart.yaml", CHILD_CHART),
            ("kompass/charts/child/RELEASE_NOTES.md", b"not umbrella notes"),
        ]
        tags = [
            self.package(extra=nested),
            self.package("kompass-insights", "2.0.0"),
            self.package("pod-rightsizing", "v0.9.6-rc.1+build.7"),
        ]
        for tag in tags:
            self.release(tag, NOTES)
        self.package(
            "kompass-pod-placement", notes=None,
            extra=[
                ("kompass-pod-placement/charts/child/Chart.yaml", CHILD_CHART),
                ("kompass-pod-placement/charts/child/RELEASE_NOTES.md", b"child"),
            ],
        )

        result = self.verify()

        self.assert_success(result)
        calls = self.recorded_calls()
        self.assertEqual(len(calls), len(tags))
        self.assertTrue(all(call["method"] == "GET" for call in calls))
        self.assertEqual(
            {unquote(call["endpoint"].rsplit("/", 1)[1]) for call in calls}, set(tags)
        )

    def test_rejects_content_and_whitespace_mismatches(self):
        tag = self.package()
        for body in (
            NOTES.replace("fix:", "feat:"),
            NOTES.rstrip(),
            NOTES + "\n",
            NOTES.replace("\r\n", "\n"),
        ):
            with self.subTest(body=body):
                self.release(tag, body)
                result = self.verify()
                self.assert_failure(result, "does not match")
                self.assertIn(tag, result.stderr)

    def test_empty_notes_are_verified_not_treated_as_legacy(self):
        tag = self.package(notes="")
        self.release(tag, "")
        self.assert_success(self.verify())
        self.release(tag, "fallback description")
        self.assert_failure(self.verify(), "does not match")

    def test_missing_release_and_api_failures_fail_closed(self):
        tag = self.package()
        for error in ("HTTP 404: release not found", "HTTP 403: forbidden", "HTTP 500"):
            with self.subTest(error=error):
                self.responses[tag] = {"error": error}
                self.assert_failure(self.verify(), error)

    def test_malformed_release_responses_fail_closed(self):
        tag = self.package()
        for raw in (
            "not JSON", "null", "[]", "{}",
            json.dumps({"tag_name": tag, "body": None}),
            json.dumps({"tag_name": tag, "body": 42}),
            json.dumps({"tag_name": "wrong-release", "body": NOTES}),
        ):
            with self.subTest(raw=raw):
                self.responses[tag] = {"raw": raw}
                self.assert_failure(self.verify(), "release response")

    def test_malformed_packages_fail_instead_of_looking_like_legacy(self):
        self.release("kompass-1.2.3", NOTES)
        metadata = ("kompass/Chart.yaml", CHART)
        notes = ("kompass/RELEASE_NOTES.md", NOTES.encode())
        for entries in (
            [],
            [notes],
            [metadata, metadata, notes],
            [metadata, notes, notes],
            [metadata, ("kompass/RELEASE_NOTES.md", None)],
            [metadata, ("kompass/RELEASE_NOTES.md", b"\xff")],
            [("kompass/Chart.yaml", b"not: [valid YAML")],
            [("kompass/Chart.yaml", b"apiVersion: v2\nname: kompass\n"), notes],
            [("kompass/Chart.yaml", CHART.replace(b"1.2.3", b"9.9.9")), notes],
            [metadata, ("other/RELEASE_NOTES.md", b"outside chart")],
            [metadata, ("kompass/../RELEASE_NOTES.md", b"unsafe path")],
        ):
            with self.subTest(entries=entries):
                self.archive("kompass-1.2.3.tgz", entries)
                self.assert_failure(self.verify(), "kompass-1.2.3.tgz")
                self.assertEqual(self.recorded_calls(), [])
        (self.packages / "kompass-1.2.3.tgz").write_bytes(b"not a gzip archive")
        self.assert_failure(self.verify(), "kompass-1.2.3.tgz")
        self.assertEqual(self.recorded_calls(), [])

    def test_invalid_chart_version_fails_even_when_filename_matches(self):
        tag = self.package(version="not-semver")
        self.release(tag, NOTES)
        self.assert_failure(self.verify(), "kompass-not-semver.tgz")
        self.assertEqual(self.recorded_calls(), [])

    def test_missing_or_empty_package_directory_fails(self):
        self.assert_failure(self.verify(), "No chart packages")
        self.packages.rmdir()
        self.assert_failure(self.verify(), "No chart packages")

    def test_workflow_indexes_only_after_upload_and_note_verification_succeed(self):
        tag = self.package()
        (self.root / "scripts").symlink_to(REPOSITORY / "scripts", target_is_directory=True)
        for name in ("cr", "git"):
            self.command(name, FAKE_PUBLISH_COMMAND)
        workflow = subprocess.run(
            [
                "yq", "-r",
                '.jobs.release.steps[] | select(.name == "publish charts and index") | .run',
                str(REPOSITORY / ".github/workflows/release.yaml"),
            ],
            check=True, capture_output=True, text=True,
        ).stdout
        for body, upload_exit, expected in (
            (NOTES, "0", ["cr upload", "gh GET", "git fetch", "cr index"]),
            ("wrong notes", "0", ["cr upload", "gh GET"]),
            (NOTES, "1", ["cr upload"]),
        ):
            with self.subTest(body=body, upload_exit=upload_exit):
                self.release(tag, body)
                self.env["UPLOAD_EXIT"] = upload_exit
                result = self.run_command(
                    ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", workflow]
                )
                if len(expected) == 4:
                    self.assert_success(result)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                actual = [
                    f"{call['tool']} {call['method'] if call['tool'] == 'gh' else call['args'][0]}"
                    for call in self.recorded_calls()
                ]
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
