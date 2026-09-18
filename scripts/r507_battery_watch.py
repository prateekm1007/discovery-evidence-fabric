#!/usr/bin/env python3
"""scripts/r507_battery_watch.py — R507: observe-only watcher for the
R506 yield battery's durable-branch terminal states (the second
container's observation path).

LXXIV discipline: observation is not execution. This watcher only FETCHES
the durable branch and reports what has LANDED; it never touches the
Space, never needs owner capabilities (the 404-on-unauthorized-poll is
the ownership mask, server.py R394 s15), and never claims anything about
runs whose terminals have not landed (UNKNOWN stays UNKNOWN).

Exit codes: 0 = all 6 sessions terminal-durable (harvest ready);
           3 = partial (report printed); 4 = no battery runs on the
           branch yet.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKTREE = Path("/home/z/my-project/r506_durable")
SESSIONS = REPO / "R506" / "BATTERY_SESSIONS.json"
BASELINE_TIP = "691d8d3d"  # the custody push at watcher-authoring time

BATTERY_SIDS = [
    "ts_dbdf24c91535", "ts_ca977637f50b", "ts_66e23c67b511",
    "ts_84a8807b12dc", "ts_6da1b9339ce5", "ts_d9b7d3463583",
]


def _git(*args, cwd=REPO):
    return subprocess.run(["git", *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=120)


def main() -> int:
    _git("fetch", "origin", "runtime-state-hf")

    # new durable commits since the custody baseline
    log = _git("log", "--oneline", f"{BASELINE_TIP}..origin/runtime-state-hf")
    new_commits = [l for l in log.stdout.splitlines() if l.strip()]
    print(f"new durable commits since {BASELINE_TIP}: {len(new_commits)}")
    for c in new_commits[:20]:
        print("  ", c[:110])

    # refresh the worktree to the fetched tip (the harvest reads it)
    if WORKTREE.exists():
        _git("checkout", "origin/runtime-state-hf", "--", ".", cwd=WORKTREE) \
            if False else None
        # hard-sync the worktree ref (read-only use; the branch carries
        # only what the engine pushes — never rewritten here)
        _git("reset", "--hard", "origin/runtime-state-hf", cwd=WORKTREE)

    # battery session -> run-dir mapping (terminal authority)
    found = {}
    if WORKTREE.exists():
        runs = WORKTREE / "runs"
        if runs.exists():
            for slug in sorted(runs.iterdir()):
                if not slug.is_dir():
                    continue
                for fname in ("run_manifest.json", "final_state.json"):
                    p = slug / fname
                    if p.exists():
                        try:
                            d = json.loads(p.read_text())
                        except Exception:  # noqa: BLE001
                            continue
                        sid = d.get("session_id")
                        if sid in BATTERY_SIDS:
                            term = None
                            fs = slug / "final_state.json"
                            if fs.exists():
                                try:
                                    term = json.loads(
                                        fs.read_text()).get("state")
                                except Exception:  # noqa: BLE001
                                    term = "UNREADABLE"
                            found[sid] = {"slug": slug.name,
                                          "terminal_state": term}
    n_terminal = sum(1 for v in found.values() if v["terminal_state"])
    print(f"battery runs on the durable branch: {len(found)}/6 "
          f"(terminal final_state: {n_terminal})")
    for sid in BATTERY_SIDS:
        v = found.get(sid)
        print(f"  {sid}: "
              f"{v['slug'][:60]} state={v['terminal_state']}" if v
              else f"  {sid}: NOT_ON_DURABLE_BRANCH (execution state "
                   f"UNKNOWN from here — the ownership-masked live poll "
                   f"is not evidence, Art. LXXIV/XXV)")

    if n_terminal == 6:
        print("ALL TERMINAL-DURABLE — harvest ready "
              "(python3 scripts/r506_battery_driver.py harvest)")
        return 0
    return 3 if found else 4


if __name__ == "__main__":
    raise SystemExit(main())
