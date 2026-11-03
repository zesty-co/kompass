#!/usr/bin/env python3
"""Persistent release promotion lock using a Git ref compare-and-swap.

The caller supplies Git authentication/configuration and protects the state branch
against deletion and writes outside this controller. There is no time lease:
the active generation spans capture, review, merge, and publication. Complete
only after publication succeeds. Cancel MUST run under the same concurrency lock
as publication; a state check alone cannot fence an already running publisher.

No checkout or index is changed. The orphan state history contains state.json;
subsequent commits retain their parent. Git subprocess output is deliberately
not logged because remote URLs and credential helpers may contain secrets.
"""
import argparse
import json
import re
import subprocess
import sys


REF = "refs/heads/release-notes-state"
ID = re.compile(r"[0-9a-fA-F]{64}\Z")


class LifecycleError(ValueError):
    """A rejected lifecycle operation or unavailable state store."""


def valid_generation(value):
    return type(value) is int and value >= 0


def validate_state(state):
    if (not isinstance(state, dict)
            or set(state) != {"schema_version", "promotion_id", "generation", "status"}
            or type(state["schema_version"]) is not int
            or state["schema_version"] != 1
            or not isinstance(state["promotion_id"], str)
            or not ID.fullmatch(state["promotion_id"])
            or not valid_generation(state["generation"])
            or state["status"] not in ("active", "complete", "cancelled")):
        raise LifecycleError("invalid lifecycle state")
    return state


class Store:
    def __init__(self, repo, remote="origin", ref=REF):
        self.repo, self.remote, self.ref = repo, remote, ref
        if not remote or remote.startswith("-"):
            raise LifecycleError("invalid remote")
        if not ref.startswith("refs/heads/") or self.git("check-ref-format", ref).returncode:
            raise LifecycleError("invalid state ref")

    def git(self, *args, input=None):
        return subprocess.run(["git", "-C", self.repo, *args], input=input,
                              text=True, capture_output=True)

    def checked(self, *args, input=None):
        result = self.git(*args, input=input)
        if result.returncode:
            raise LifecycleError("Git state operation failed (check repository and remote access)")
        return result.stdout.strip()

    def read(self):
        result = self.git("ls-remote", "--exit-code", "--refs", self.remote, self.ref)
        if result.returncode == 2:
            return "", None
        if result.returncode:
            raise LifecycleError("cannot read lifecycle remote")
        lines = result.stdout.splitlines()
        if len(lines) != 1:
            raise LifecycleError("invalid remote state ref response")
        fields = lines[0].split()
        if len(fields) != 2 or fields[1] != self.ref or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", fields[0]):
            raise LifecycleError("invalid remote state ref response")
        sha = fields[0]
        # Fetch the observed object, not a moving ref or shared FETCH_HEAD.
        self.checked("fetch", "--no-tags", "--no-write-fetch-head", self.remote, sha)
        content = self.checked("show", f"{sha}:state.json")
        try:
            state = json.loads(content)
        except (ValueError, TypeError) as exc:
            raise LifecycleError("invalid lifecycle state JSON") from exc
        return sha, validate_state(state)

    def write(self, expected, state):
        blob = self.checked("hash-object", "--stdin", "-w", input=json.dumps(state, sort_keys=True) + "\n")
        tree = self.checked("mktree", input=f"100644 blob {blob}\tstate.json\n")
        parents = ["-p", expected] if expected else []
        commit = self.checked("-c", "user.name=Release notes lifecycle",
                              "-c", "user.email=release-notes@users.noreply.github.com",
                              "commit-tree", tree, *parents,
                              input=f"Release notes {state['status']} generation {state['generation']}\n")
        return self.git("push", f"--force-with-lease={self.ref}:{expected}",
                        self.remote, f"{commit}:{self.ref}").returncode == 0

    def apply(self, command, promotion, generation=None):
        if not ID.fullmatch(promotion):
            raise LifecycleError("promotion must be a 64-character hexadecimal ID")
        if generation is not None and not valid_generation(generation):
            raise LifecycleError("generation must be a nonnegative integer")
        if command in ("complete", "cancel", "check") and generation is None:
            raise LifecycleError("expected generation is required")
        sha, state = self.read()
        if command == "status":
            return state
        if command == "acquire":
            if state and state["status"] == "active":
                if state["promotion_id"] != promotion:
                    raise LifecycleError("another promotion is active")
                if generation is not None and generation != state["generation"]:
                    raise LifecycleError("stale generation")
                return state
            next_generation = state["generation"] + 1 if state else 1
            if generation is not None and generation != next_generation:
                raise LifecycleError("stale generation")
            updated = dict(schema_version=1, promotion_id=promotion,
                           generation=next_generation, status="active")
        else:
            if (not state or state["status"] != "active"
                    or state["promotion_id"] != promotion or state["generation"] != generation):
                raise LifecycleError("active promotion and expected generation do not match")
            if command == "check":
                return state
            updated = dict(state, status="complete" if command == "complete" else "cancelled")
        if self.write(sha, updated):
            return updated
        # One bounded reread, never a blind push retry or takeover. Only an
        # acquisition of the identical active generation can become success.
        _, current = self.read()
        if command == "acquire" and current == updated:
            return current
        raise LifecycleError("state compare-and-swap failed; remote rejected or state changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="existing authenticated Git checkout")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--ref", default=REF)
    parser.add_argument("command", choices=("acquire", "status", "complete", "cancel", "check"))
    parser.add_argument("--promotion", required=True)
    parser.add_argument("--generation", type=int)
    args = parser.parse_args()
    try:
        state = Store(args.repo, args.remote, args.ref).apply(args.command, args.promotion, args.generation)
    except (LifecycleError, OSError) as exc:
        # Do not include subprocess arguments, output, URLs, or environment.
        message = str(exc) if isinstance(exc, LifecycleError) else "cannot execute Git state operation"
        print(message, file=sys.stderr)
        return 1
    print(json.dumps(state, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
