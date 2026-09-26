#!/usr/bin/env python3
"""Git pre-commit hook: machine-enforce the artifact-namespace rule.

Per the R537 directive §6: no human reviewer is the enforcement
mechanism — the namespace rule is machine-enforced at the commit.
This hook runs the R537 validator (scripts/validate_artifact_
namespace.py) against the staged changed-file set and BLOCKS the
commit if the set contains a HISTORICAL_SEALED_MUTATION (an in-
place edit / delete / rewrite of an earlier round's sealed evidence,
or a new mutable harvest placed in an old round's directory).

INSTALLATION:
  cp scripts/pre_commit_artifact_namespace.py .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit

This hook runs AFTER the existing pre_commit_constitution_check.py
hook (the two are independent: the constitution check enforces the
constitution; this one enforces the artifact namespace).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1] \
    if Path(__file__).resolve().parent.name == "scripts" \
    else Path(__file__).resolve().parent


def main() -> int:
    validator = REPO_ROOT / "scripts" / "validate_artifact_namespace.py"
    if not validator.exists():
        print("artifact-namespace validator not found — "
              "allowing the commit (the validator is not yet "
              "installed)")
        return 0
    res = subprocess.run(
        [sys.executable, str(validator), "--staged"],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    if res.returncode != 0:
        print()
        print("BLOCKED: the staged changed-file set breaches the "
              "artifact-namespace rule (an earlier round's sealed "
              "evidence was mutated in place, or a new mutable "
              "harvest was placed in an old round's directory).")
        print("A correction to an older round must be a NEW "
              "append-only *_CORRECTION.json under the CURRENT "
              "round, never an in-place edit of the sealed "
              "original (Art. XI).")
        return res.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
