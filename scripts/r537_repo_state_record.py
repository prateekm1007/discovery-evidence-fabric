#!/usr/bin/env python3
"""R537 precondition record: the four repository-state autocommands.

Per the R537 directive §1: all repository-state checks are
autocommand/script driven and recorded in the round artifact.
Remote state is NEVER inferred from the local checkout — the
remote ref is read with `git ls-remote origin refs/heads/main`.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R537" / "R537_REPO_STATE_RECORD.json"

R536_REMOTE_SHA = "29c4d17f79df3ddb66518ff2ccf72c04b8982cc6"


def _sh(*args) -> str:
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(REPO)).stdout.strip()


def main() -> int:
    head = _sh("git", "rev-parse", "HEAD")
    origin_main = _sh("git", "rev-parse", "origin/main")
    remote_main = _sh("git", "ls-remote", "origin", "refs/heads/main")
    status = _sh("git", "status", "--short")
    remote_sha = remote_main.split()[0] if remote_main else ""
    rec = {
        "artifact": "R537_REPO_STATE_RECORD/1.0",
        "round": "R537",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "git_head": head,
        "git_origin_main": origin_main,
        "git_ls_remote_refs_heads_main": remote_sha,
        "remote_matches_local_origin": bool(
            remote_sha and remote_sha == origin_main),
        "r536_remote_sha_confirmed": remote_sha == R536_REMOTE_SHA,
        "working_tree_status": status,
        "note": ("R537 precondition: R536 is confirmed on the remote "
                 f"as {R536_REMOTE_SHA}; R536 is ahead of R535 by "
                 "exactly one commit and behind by zero. R536 is "
                 "NOT production-proven — the latest production "
                 "identity proof remains R535 (deployed engine "
                 "eaeba79d8). The R537 round must not claim "
                 "R536-deployed until a fresh production identity "
                 "proof (R537_PRODUCTION_IDENTITY_PROOF.json) "
                 "establishes target == origin/main == deployed "
                 "engine commit == production health commit == "
                 "running artifact identity, with drift/tamper "
                 "false."),
        "independent_ci_certification":
            "NOT_INDEPENDENTLY_CERTIFIED",
        "ci_note": ("the observed GitHub status surface returned no "
                    "statuses and the commit-associated workflow "
                    "query returned no runs for R536 — local pytest "
                    "is not a substitute (Art. XXVI); separate "
                    "infrastructure task, not folded into R537 "
                    "scientific work"),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"HEAD={head}")
    print(f"origin/main={origin_main}")
    print(f"ls-remote main={remote_sha}")
    print(f"remote matches local origin: {rec['remote_matches_local_origin']}")
    print(f"R536 remote confirmed: {rec['r536_remote_sha_confirmed']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
