#!/usr/bin/env python3
"""
scripts/pre_commit_constitution_check.py

Git pre-commit hook that enforces the Epistemic Constitution.

Per CEO v27 directive:
  "The system should periodically remind the coder automatically while it
   codes, especially before commits, gate changes, verifier changes, and
   research authorization changes."

This hook blocks the commit if:
  1. The constitution file (EPISTEMIC_CONSTITUTION.md) is missing
  2. The constitution has been modified but not re-acknowledged
  3. The commit touches epistemic infrastructure files without acknowledgment

INSTALLATION:
  cp scripts/pre_commit_constitution_check.py .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit

  Or add to .git/hooks/pre-commit:
    #!/bin/bash
    exec python scripts/pre_commit_constitution_check.py
"""

import json
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "scripts" else Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from epistemic_integrity.constitution_loader import (
    check_constitution_compliance,
    acknowledge_constitution,
    get_pre_session_warning,
    CONSTITUTION_PATH,
)


# Files that are "epistemic infrastructure" — modifying these requires
# explicit constitution acknowledgment
EPISTEMIC_INFRASTRUCTURE_PATTERNS = [
    "epistemic_integrity/",
    "CANONICAL_STATE/",
    "EPISTEMIC_CONSTITUTION.md",
    ".github/workflows/epistemic",
]


def get_staged_files():
    """Get the list of staged files in this commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.split("\n") if f.strip()]


def touches_epistemic_infrastructure(staged_files):
    """Check if any staged file is epistemic infrastructure."""
    for f in staged_files:
        for pattern in EPISTEMIC_INFRASTRUCTURE_PATTERNS:
            if f.startswith(pattern) or f == pattern.rstrip("/"):
                return True
    return False


def main():
    staged_files = get_staged_files()

    if not staged_files:
        # No files staged — allow (might be a merge commit or empty commit)
        return 0

    state = check_constitution_compliance()

    # Check 1: Constitution must be present
    if not state.constitution_present:
        print("❌ EPISTIC CONSTITUTION CHECK FAILED")
        print(f"   Constitution file missing: {CONSTITUTION_PATH}")
        print("   The repository cannot operate without the constitution.")
        print("   Restore EPISTEMIC_CONSTITUTION.md before committing.")
        return 1

    # Check 2: If committing to epistemic infrastructure, require acknowledgment
    touches_infra = touches_epistemic_infrastructure(staged_files)

    if touches_infra:
        if not state.acknowledgment_present:
            # Auto-acknowledge with a record of what's being changed
            change_desc = f"Committing: {', '.join(staged_files[:5])}"
            if len(staged_files) > 5:
                change_desc += f" (+{len(staged_files) - 5} more)"
            acknowledge_constitution(
                agent="pre-commit-hook",
                session="auto",
                intended_change=change_desc,
            )
            print("[OK] Constitution auto-acknowledged by pre-commit hook")
            print(f"   Intended change: {change_desc}")
        else:
            print("[OK] Constitution already acknowledged")
    else:
        # Non-infrastructure commit — just verify constitution exists
        print("[OK] Constitution present (non-infrastructure commit)")

    # Always print the pre-session warning for infrastructure commits
    if touches_infra:
        print()
        print(get_pre_session_warning())

    return 0


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    sys.exit(main())
