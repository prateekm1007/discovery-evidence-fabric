#!/usr/bin/env python3
"""r458_space_prune.py — R458-C2: reconcile the Space tree with the
staged (git HEAD) tree by DELETING ghost files.

ROOT CAUSE (measured this round): upload_folder only ADDS/UPDATES —
every file ever deleted from git (R453-C2 UI deletions, R455-LEAN
archive moves, the §N.1 ARCHIVE set) remained in the Space as ghosts
(439 measured). The latent ghost components/TechStage.tsx imports
blockedInsightCards, deleted this round — the build then failed on a
file that no longer exists in the repository (Art. LXIV: superseded
implementations must be retired, not accumulated — the Space tree is
part of the production implementation).

This script:
  1. reads the Space file list and the staged tree (git ls-files + the
     driver's staged extras),
  2. deletes every Space file not in the staged set (README.md and
     dotfiles excluded; the .gitattributes the driver writes stays),
  3. the deletion commit triggers a rebuild.

Deletion-only, additive-nothing: it never writes content. The prior
Space revision (598c1e6f) preserves the pre-prune state in Space
history (Art. XI).

Usage:
  HF_TOKEN=... python3 r458_space_prune.py [--apply]
  (default: dry-run — prints what would be deleted)
"""
from __future__ import annotations

import subprocess
import sys
import time

REPO = "/home/z/my-project/hf_space"
SPACE = "prateekm1/toscanini-prod-validation"
TOKEN = None  # from env
DRIVER_STAGED_EXTRAS = {
    # written by the deploy driver itself (adapter + frontmatter + state)
    "README.md",
    ".gitattributes",
    "DEPLOY_ADAPTER_MARKER.txt",
}


def main() -> int:
    global TOKEN
    import os

    TOKEN = os.environ.get("HF_TOKEN")
    apply = "--apply" in sys.argv
    if not TOKEN:
        print("HF_TOKEN required (env-injected only)")
        return 2

    from huggingface_hub import HfApi

    api = HfApi(token=TOKEN)
    space_files = set(
        api.list_repo_files(SPACE, repo_type="space")
    )
    git_files = set(
        subprocess.run(
            ["git", "ls-files"], cwd=REPO, capture_output=True, text=True
        ).stdout.splitlines()
    )
    staged = git_files | DRIVER_STAGED_EXTRAS
    ghosts = sorted(
        f for f in space_files - staged
        if not f.startswith(".git")
    )
    print(f"space files: {len(space_files)} | staged: {len(staged)} | ghosts: {len(ghosts)}")
    for g in ghosts:
        print("  GHOST", g)

    if not apply:
        print("dry-run: pass --apply to delete")
        return 0

    if ghosts:
        BATCH = 100
        for i in range(0, len(ghosts), BATCH):
            chunk = ghosts[i : i + BATCH]
            api.delete_files(
                repo_id=SPACE,
                repo_type="space",
                delete_patterns=chunk,  # exact paths (glob-safe: plain paths)
                commit_message=f"R458-C2 prune: retire {len(chunk)} ghost files not in the staged tree (Art. LXIV; batch {i//BATCH+1})",
            )
            print(f"deleted batch {i//BATCH+1} ({len(chunk)} files)")
            time.sleep(2)
    else:
        print("nothing to prune")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
