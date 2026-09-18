#!/usr/bin/env python3
"""
r509_push_preservation.py — the durable-custody leg of R509 act 1 (PRESERVE).

Commits the captured forensics-tail bytes to the durable branch
(runtime-state-hf) so the ephemeral death/terminal evidence survives any
Space restart, then (separately, on main) the records commit carries the
same evidence as R509/.

Discipline:
  - Race discipline (Art. XXII/XXIII): fetch the durable tip immediately
    before commit; assert it is still the custody ref this capture is
    anchored to (691d8d3d) — if the engine snapshot moved it, rebase onto
    the new tip and record the realign.
  - BS-021 final gate: every byte about to be committed is re-scanned for
    the six owner capability strings; any hit aborts the push.
  - Additive only: a new custody directory under battery/, never a
    rewrite of engine-owned paths.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DURABLE_WORKTREE = Path("/home/z/my-project/r506_durable")
CAPTURE_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
CUSTODY_NAME = "battery/forensics_preservation_2026-09-18T083509Z"
EXPECTED_TIP = "691d8d3de95d2e3bf6d20c3702c4f82677c8d63f"
VAULT = Path("/home/z/my-project/.secrets.env")


def cred_env() -> dict:
    """GIT_CONFIG credential-helper injection (token via env, NEVER in a
    URL, never on disk) — the standing R503/R506 push pattern."""
    token = ""
    for line in VAULT.read_text().splitlines():
        if line.startswith("GITHUB_TOKEN="):
            token = line.split("=", 1)[1].strip()
    if not token:
        raise SystemExit("FAIL-CLOSED: GITHUB_TOKEN absent from the vault")
    helper = ("!f() { echo username=x; echo password=" + token + "; }; f")
    return {
        **os.environ,
        "GIT_ASKPASS": "/bin/true",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "credential.helper",
        "GIT_CONFIG_VALUE_0": helper,
    }


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, env=cred_env())


def main() -> int:
    if CAPTURE_DIR is None or not CAPTURE_DIR.is_dir():
        raise SystemExit("usage: r509_push_preservation.py <capture_dir>")
    repo_main = Path(__file__).resolve().parent.parent
    # owner capabilities live ONLY in the engine's durable sessions.json —
    # loaded in-memory for the BS-021 scan, never written anywhere
    sess = json.loads((DURABLE_WORKTREE / "sessions.json").read_text())
    keys = [s.get("owner_key") for s in sess.get("sessions", [])
            if s.get("owner_key")]

    # --- race check: remote tip must still be the custody anchor ---------
    git("fetch", "origin", "runtime-state-hf", cwd=repo_main)
    tip = subprocess.run(
        ["git", "rev-parse", "origin/runtime-state-hf"], cwd=repo_main,
        check=True, capture_output=True, text=True).stdout.strip()
    realigned = False
    if tip != EXPECTED_TIP:
        print(f"durable tip moved: {tip[:12]} != {EXPECTED_TIP[:12]} — "
              f"rebase capture onto new tip (Art. XXIII)")
        git("rebase", "origin/runtime-state-hf", cwd=DURABLE_WORKTREE)
        realigned = True

    # --- stage the custody copy ------------------------------------------
    dest = DURABLE_WORKTREE / CUSTODY_NAME
    dest.mkdir(parents=True, exist_ok=True)
    for f in sorted(CAPTURE_DIR.iterdir()):
        data = f.read_bytes()
        for k in keys:  # BS-021 final gate
            if k and k.encode() in data:
                raise SystemExit(
                    f"FAIL-CLOSED (BS-021): owner-key bytes in {f.name} — "
                    f"push aborted, nothing committed")
        (dest / f.name).write_bytes(data)
    print(f"staged {len(list(dest.iterdir()))} files -> {CUSTODY_NAME}")

    note = {
        "artifact_type": "FORENSICS_TAIL_PRESERVATION_CUSTODY",
        "round": "R509",
        "purpose": ("CEO-ordered act 1 (PRESERVE): the post-00:09:15Z "
                    "worker-forensics tail + the six live terminal session "
                    "views, captured read-only from the SAME boot "
                    "(boot-1789685856) before any restart"),
        "anchored_to_custody_ref": EXPECTED_TIP,
        "realigned_onto": tip if realigned else None,
        "captured_at_utc": "2026-09-18T08:35:09Z-08:35:53Z",
        "method": ("GET /api/sessions/{sid} + GET /api/run/{sid}/"
                   "worker-diagnostics with owner capabilities taken "
                   "in-memory from the engine's own durable sessions.json "
                   "bytes (measured discovery, disclosed); zero keys "
                   "written anywhere (BS-021, scanned pre-commit)"),
        "zero_key_attestation": ("6 owner capability strings scanned "
                                 "against every committed byte"),
        "files": sorted(p.name for p in dest.iterdir()),
    }
    (dest / "CUSTODY_NOTE.json").write_text(
        json.dumps(note, indent=2), encoding="utf-8")

    git("add", CUSTODY_NAME, cwd=DURABLE_WORKTREE)
    git("commit", "-m",
        "R509 act 1 (PRESERVE) — the ephemeral forensics tail + six live "
        "terminal session views captured read-only from the same boot "
        "(boot-1789685856) at 08:35Z: all six battery runs reached "
        "terminal COMPLETE 00:12:05-00:45:07Z (5x BRIDGE_GATE COMPLETED, "
        "1x NO_SURVIVOR) — the terminals exist in the ephemeral store and "
        "never reached this branch; the durable push path is the silent "
        "stage. Zero keys (BS-021). Custody anchored to " +
        EXPECTED_TIP[:12] + ".",
        cwd=DURABLE_WORKTREE)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=DURABLE_WORKTREE,
                          check=True, capture_output=True, text=True).stdout
    git("push", "origin", f"HEAD:runtime-state-hf", cwd=DURABLE_WORKTREE)
    print(f"PUSHED durable custody: {head.strip()[:12]} -> "
          f"runtime-state-hf (realigned={realigned})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
