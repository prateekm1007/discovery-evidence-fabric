"""
epistemic_integrity/detached_certification_runner.py

Per CEO v20 P0-1:
  "Run the entire certification gate from a detached clean worktree of the exact
   certified commit. Production checkout must not be the execution environment."

Architecture:
  1. Get current HEAD
  2. Create detached worktree: git worktree add --detach /tmp/cert_worktree/<sha> <sha>
  3. Run certification gate INSIDE the detached worktree
  4. All outputs go to /tmp/certification_output/
  5. Production checkout is never the execution environment
  6. Clean up worktree after certification

This makes G8 (production immutability) a defense-in-depth invariant
rather than the primary containment mechanism.
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_detached_certification() -> int:
    """Run certification from a detached clean worktree.

    Returns exit code (0 = GREEN, 1 = RED).
    """
    # Get current HEAD
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        print("ERROR: Cannot get HEAD")
        return 1

    commit_sha = result.stdout.strip()
    print(f"Certifying commit: {commit_sha}")

    # Create detached worktree
    worktree_dir = Path(tempfile.gettempdir()) / f"cert_worktree_{commit_sha[:12]}"
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir)

    print(f"Creating detached worktree: {worktree_dir}")
    result = subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree_dir), commit_sha],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: Cannot create worktree: {result.stderr}")
        return 1

    try:
        # Run certification gate INSIDE the detached worktree
        # All outputs go to /tmp/certification_output/ (outside both worktree and repo)
        output_dir = Path(tempfile.gettempdir()) / "epistemic_certification_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Running certification from detached worktree...")
        print(f"Output directory: {output_dir}")

        result = subprocess.run(
            [
                sys.executable, "-m", "epistemic_integrity.research_authorization_gate",
                "--in-place",  # v25: Run gate directly inside the detached worktree
                               # (avoids infinite recursion through detached runner)
            ],
            cwd=str(worktree_dir),
            capture_output=True, text=True, timeout=900,
            # TRANSPORT BUDGET REPAIR (R412, 2026-09-05, disclosed):
            # the 300 s cap was calibrated when the certification
            # battery was smaller; the R412 phases added ~100 gate-
            # relevant tests and the in-place 14-gate run at ebbe3a3e
            # measured 359 s — the cap was cutting off a HEALTHY
            # certification mid-run (TimeoutExpired, Art. LXI class).
            # 900 s = 2.5x the measured healthy runtime; the GATES,
            # their thresholds, and their verdicts are byte-identical
            # (same class as the R411 attack token-cap correction: a
            # bounded transport budget sized to the measured workload,
            # never an epistemic change).
        )

        # Print output
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr[:500]}")

        return result.returncode

    finally:
        # Clean up worktree
        print(f"\nCleaning up worktree: {worktree_dir}")
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True, timeout=10,
        )
        # Also prune
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(REPO_ROOT),
            capture_output=True, timeout=10,
        )


def main():
    """Run certification from detached worktree. Exit 0 if GREEN, 1 if RED."""
    exit_code = run_detached_certification()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
