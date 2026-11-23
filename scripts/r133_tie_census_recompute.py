#!/usr/bin/env python3
"""r133_tie_census_recompute — the tie-census authority (DIR 7 /
R132-F3). Reproduces the auditor's per-judge order-majority tie
census from the raw R132 panel bytes: 16 (5/3/3/5), cohere 13:0+1TIE.

The tie unit (defined in eval/r133_census_reconciliation.json): a
PER-JUDGE PAIR CELL — judge J's cell on pair P is a tie iff J's two
order-passes disagree, or J's only served pass voted TIE.

Usage: python3 -I scripts/r133_tie_census_recompute.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "eval" / "r132_panel"
FAMILIES = ("meta-llama", "qwen", "deepseek", "cohere")
EXPECTED = {"meta-llama": 5, "qwen": 3, "deepseek": 3, "cohere": 5}


def arm_vote(rec):
    pref = str((rec.get("parsed") or {}).get("prefer") or "")
    if pref not in ("A", "B"):
        return "tie"
    return (rec["a_is"] if pref == "A"
            else ("baseline" if rec["a_is"] == "a1" else "a1"))


def main() -> int:
    pids = sorted({f.stem.split("__")[1]
                   for f in RAW.glob("*.json")})
    out, total = {}, 0
    for fam in FAMILIES:
        ties, pos = 0, Counter()
        for pid in pids:
            det = mir = None
            for f in RAW.glob(f"{fam}__{pid}__*.json"):
                r = json.loads(f.read_text())
                if r["outcome"] != "VALID":
                    continue
                v = arm_vote(r)
                pos[str((r.get("parsed") or {}).get("prefer") or "")] += 1
                if r["pass"] == "det":
                    det = v
                else:
                    mir = v
            cell_tie = ((det != mir) if det is not None and mir is not None
                        else (v == "tie") if (det or mir) is not None
                        else False)
            ties += 1 if cell_tie else 0
        out[fam] = {"ties": ties, "A:B": f"{pos['A']}:{pos['B']}",
                    "TIE_votes": pos["TIE"]}
        total += ties
    print(json.dumps({"per_judge": out, "total": total}, indent=1))
    assert total == 16 and all(out[f]["ties"] == EXPECTED[f]
                               for f in FAMILIES), "census drift!"
    assert out["cohere"]["A:B"] == "13:0", "cohere ratio drift!"
    print("CENSUS RECONCILED: 16 (5/3/3/5), cohere 13:0 — diff=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
