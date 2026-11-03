"""CLI contract tests using only disposable local Git repositories."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("release_notes_lifecycle.py")
REF = "refs/heads/release-notes-state"
A, B = "a" * 64, "b" * 64


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.git(self.root, "init", "--bare", str(self.remote))
        self.repos = [self.root / name for name in ("one", "two")]
        for repo in self.repos:
            self.git(self.root, "clone", str(self.remote), str(repo))
            self.git(repo, "config", "user.name", "Fixture")
            self.git(repo, "config", "user.email", "fixture@example.invalid")
            (repo / "keep").write_text("original\n")
            self.git(repo, "add", "keep")
            self.git(repo, "commit", "-m", "fixture")

    def git(self, repo, *args, input=None):
        return subprocess.run(["git", "-C", str(repo), *args], input=input,
                              text=True, capture_output=True, check=True).stdout.strip()

    def call(self, command, promotion=A, generation=None, repo=0, ok=True):
        args = [sys.executable, str(SCRIPT), "--repo", str(self.repos[repo]),
                command, "--promotion", promotion]
        if generation is not None:
            args += ["--generation", str(generation)]
        result = subprocess.run(args, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        return result.stderr

    def head(self):
        return self.git(self.remote, "rev-parse", REF)

    def test_single_active_idempotency_and_monotonic_generations(self):
        self.assertIsNone(self.call("status"))
        state = self.call("acquire")
        self.assertEqual(state, dict(schema_version=1, promotion_id=A, generation=1, status="active"))
        head = self.head()
        self.assertEqual(self.call("acquire", repo=1), state)
        self.assertEqual(self.head(), head)
        self.call("acquire", B, repo=1, ok=False)
        self.assertEqual(self.call("check", generation=1), state)
        self.call("complete", generation=1)
        self.assertEqual(self.git(self.remote, "rev-parse", REF + "^"), head)
        self.assertEqual(self.call("acquire", B, repo=1)["generation"], 2)
        self.call("cancel", B, generation=2)
        self.assertEqual(self.call("acquire")["generation"], 3)

    def test_stale_and_incomplete_requests_cannot_release_lock(self):
        self.call("acquire")
        head = self.head()
        for command in ("complete", "cancel", "check"):
            for promotion, generation in ((A, None), (A, 0), (A, 2), (B, 1)):
                with self.subTest(command=command, promotion=promotion, generation=generation):
                    self.call(command, promotion, generation, ok=False)
        self.assertEqual(self.head(), head)
        self.call("cancel", generation=1)
        self.call("check", generation=1, ok=False)

    def test_checkout_and_index_are_untouched(self):
        repo = self.repos[0]
        (repo / "keep").write_text("staged\n")
        self.git(repo, "add", "keep")
        (repo / "keep").write_text("unstaged\n")
        (repo / "untracked").write_text("untracked\n")
        before = ((repo / ".git/index").read_bytes(), self.git(repo, "rev-parse", "HEAD"),
                  self.git(repo, "status", "--porcelain"))
        self.call("acquire")
        self.call("complete", generation=1)
        after = ((repo / ".git/index").read_bytes(), self.git(repo, "rev-parse", "HEAD"),
                 self.git(repo, "status", "--porcelain"))
        self.assertEqual(before, after)
        self.assertEqual((repo / "keep").read_text(), "unstaged\n")

    def install_state(self, value):
        repo = self.repos[0]
        blob = self.git(repo, "hash-object", "-w", "--stdin", input=value)
        tree = self.git(repo, "mktree", input=f"100644 blob {blob}\tstate.json\n")
        commit = self.git(repo, "commit-tree", tree, input="fixture\n")
        self.git(repo, "push", "--force", "origin", f"{commit}:{REF}")

    def test_invalid_persisted_state_fails_closed(self):
        valid = dict(schema_version=1, promotion_id=A, generation=1, status="active")
        values = ["not json", "null", "{}"]
        for key, value in (("schema_version", True), ("schema_version", 2),
                           ("promotion_id", "bad"), ("generation", -1),
                           ("generation", True), ("status", "unknown")):
            values.append(json.dumps(dict(valid, **{key: value})))
        for value in values:
            with self.subTest(value=value):
                self.install_state(value)
                head = self.head()
                self.assertIn("state", self.call("acquire", ok=False))
                self.assertEqual(self.head(), head)

    def test_bad_inputs_and_remote_outage_fail_closed(self):
        for promotion in ("", "x" * 64, "a" * 63):
            self.call("acquire", promotion, ok=False)
        self.call("acquire", generation=-1, ok=False)
        self.git(self.repos[0], "remote", "set-url", "origin", str(self.root / "missing.git"))
        self.assertIn("remote", self.call("status", ok=False))

    def race(self, second_promotion):
        # A real receive hook holds both pushes until each has read the absent ref.
        hook = self.remote / "hooks/pre-receive"
        hook.write_text(f"#!{sys.executable}\n"
                        "import os, pathlib, time\n"
                        f"root = pathlib.Path({str(self.root)!r})\n"
                        "(root / ('ready-' + str(os.getpid()))).touch()\n"
                        "deadline = time.monotonic() + 15\n"
                        "while len(list(root.glob('ready-*'))) < 2:\n"
                        "    if time.monotonic() > deadline: raise SystemExit(1)\n"
                        "    time.sleep(.01)\n")
        hook.chmod(0o755)
        def run(repo, promotion):
            return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repos[repo]),
                                   "acquire", "--promotion", promotion], capture_output=True, text=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(run, 0, A)
            two = pool.submit(run, 1, second_promotion)
            return [one.result(), two.result()]

    def test_cas_race_different_promotions_has_one_winner(self):
        results = self.race(B)
        self.assertEqual(sorted(r.returncode for r in results), [0, 1], [r.stderr for r in results])
        winner = next(json.loads(r.stdout) for r in results if r.returncode == 0)
        self.assertEqual(self.call("status"), winner)

    def test_cas_race_same_promotion_is_idempotent(self):
        results = self.race(A)
        self.assertEqual([r.returncode for r in results], [0, 0], [r.stderr for r in results])
        self.assertEqual(json.loads(results[0].stdout), json.loads(results[1].stdout))
        self.assertEqual(self.git(self.remote, "rev-list", "--count", REF), "1")


if __name__ == "__main__":
    unittest.main()
