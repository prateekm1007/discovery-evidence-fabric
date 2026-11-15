#!/usr/bin/env python3
"""r11_consolidate_a1_sets.py — AM11 D4 (F25 recurring): consolidate the
duplicate A1 answer sets to ONE authoritative set, retiring the
duplicates IN THE SAME CHANGE with Art. LXIV accounting (the old
implementation is deleted or explicitly archived in the change that
ships the replacement — never left 'for history'; history lives in
git).

Sets in play (measured lineage):
  r11_a1_fresh_r10 (18 pairs)   — the F29-era GLM regen (R10, superseded
                                  twice over; axes+records only for 12)
  r11_a1_r5       (30 pairs)    — the parallel session's F29-closure set
                                  (12 promoted delivery + 18 SYS_A1 GLM
                                  fresh); superseded by the a1f line
  r11_a1f_r1      (30 pairs)    — the SYS_A1F grounding-leg set (audited
                                  at 575c7ee57; battery r7 measured the
                                  F30 trade on it)
  r11_a1f_r2      (30 pairs)    — the SYS_A1F_V2 feasibility-aware set
                                  (this round; battery r8 measures it)

The AUTHORITATIVE set is chosen by measurement (env AUTHORITATIVE):
  r8 SIMULTANEOUS pass  -> r11_a1f_r2 (the tradeoff-broken set)
  otherwise (AM11 §4)   -> r11_a1f_r1 (the audited grounded set)
Every retired set gets a typed accounting entry (what it was, what
measured it, where its bytes remain — the git tip) and is DELETED here.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
PAIRS = REPO / "eval" / "pairs"

SETS = {
    "r11_a1_fresh_r10": {
        "n": 18, "contract": "SYS_A1_GROUNDED (R10 builder session)",
        "role": "F29-era GLM regeneration; superseded by the r11_a1_r5 "
                "30-pair closure set (parallel session) and then by the "
                "a1f line",
    },
    "r11_a1_r5": {
        "n": 30, "contract": "SYS_A1 (12 promoted delivery + 18 fresh)",
        "role": "the audited F29-closure set (ceffc7b6e); superseded "
                "by the feasibility-grounded a1f line (AM11 §4 "
                "consolidation)",
    },
    "r11_a1f_r1": {
        "n": 30, "contract": "SYS_A1F grounding leg",
        "role": "the audited grounded set (575c7ee57); battery r7 "
                "measured the F30 trade on it",
    },
    "r11_a1f_r2": {
        "n": 30, "contract": "SYS_A1F_V2 feasibility-aware ideation",
        "role": "the F30 orthogonality contract; battery r8 measures it",
    },
}


def main() -> int:
    auth = os.environ.get("AUTHORITATIVE", "")
    if auth not in ("r11_a1f_r1", "r11_a1f_r2"):
        print("[cons] AUTHORITATIVE env must be r11_a1f_r1 or r11_a1f_r2")
        return 2
    # the authoritative set's bytes must exist and be complete
    n_auth = len(list((PAIRS / auth).glob("*.json")))
    if n_auth != SETS[auth]["n"]:
        print(f"[cons] authoritative set incomplete: {n_auth}")
        return 2
    tip = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True,
                         check=True).stdout.strip()
    retired = [s for s in SETS if s != auth]
    entries = []
    for s in retired:
        d = PAIRS / s
        if not d.exists():
            entries.append({"set": s, "already_absent": True})
            continue
        n = len(list(d.glob("*.json")))
        shutil.rmtree(d)
        entries.append({
            "set": s, "n_pairs_deleted": n,
            "contract": SETS[s]["contract"], "role": SETS[s]["role"],
            "history": f"git history retains every byte up to tip {tip}",
        })
    rec = {
        "record": "A1_SET_CONSOLIDATION_R11/1.0.0",
        "at": now,
        "article": "LXIV (retired in the same change that ships the "
                   "replacement; history in git, not in the tree)",
        "authoritative_set": auth,
        "authoritative_n": n_auth,
        "authoritative_contract": SETS[auth]["contract"],
        "selection_basis": os.environ.get(
            "AUTH_BASIS", "typed in the consolidation commit"),
        "retired": entries,
        "consumers_repointed": [
            "eval/battery_a1f_r7.json (historical record, unchanged)",
            "eval/battery_a1f_r8.json (historical record, unchanged)",
            "future batteries read the authoritative set only",
        ],
    }
    out = REPO / "eval" / "a1_consolidation_r11.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[cons] authoritative={auth} ({n_auth}); retired: "
          f"{[e['set'] for e in entries if not e.get('already_absent')]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
