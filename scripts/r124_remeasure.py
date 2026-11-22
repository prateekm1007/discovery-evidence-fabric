#!/usr/bin/env python3
"""r124_remeasure.py — dir 3 (claim c-0186's measurement leg): the
F31c re-measure under the F97 detector (zero LLM — the committed
run bytes only, both independent fresh draws re-scored).

The same scoring shape as the F31c run (the amendment-1 detectors
over (prob, delivered_bill); UNSTATED-only excluded), with
scan_input_availability now the F97-fixed version. The historical
records stand as measured under the OLD detector; this is a NEW
record, never a rewrite.

Draw 1 (mine): eval/r123_fresh_confirmation_run — bare = the
authored_bill (the shared draw), successor = the delivered_bill.
Draw 2 (the twin's): eval/r123_fresh_run — bare/succ per its own
committed rows.

Outputs: eval/r124_f97/remeasure.json (per-draw + pooled preview).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

FRESH = REPO / "eval" / "r123_fresh_set" / "items.jsonl"
OUT = REPO / "eval" / "r124_f97" / "remeasure.json"


def _pairs_draw1():
    """(pid, prob, bare_bill, succ_bill) from my committed run."""
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in FRESH.read_text().strip().split("\n")}
    for pid in sorted(items):
        p = (REPO / "eval" / "r123_fresh_confirmation_run"
             / f"row_{pid}.json")
        rec = json.loads(p.read_text(encoding="utf-8"))
        yield pid, items[pid], rec["authored_bill"], \
            rec["delivered_bill"]


def _pairs_draw2():
    """The twin's run: bare_<pid>.txt + succ_<pid>.json rows."""
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in FRESH.read_text().strip().split("\n")}
    d = REPO / "eval" / "r123_fresh_run"
    for pid in sorted(items):
        bp = d / f"bare_{pid}.txt"
        sp = d / f"succ_{pid}.json"
        if not bp.exists() or not sp.exists():
            continue
        bare = bp.read_text(encoding="utf-8")
        srec = json.loads(sp.read_text(encoding="utf-8"))
        succ = srec.get("delivered_bill") or srec.get("authored_bill")
        if not bare or not succ:
            continue
        yield pid, items[pid], bare, succ


def _score(pairs, label, seed):
    rows, per_item = [], []
    bare_n = succ_n = 0
    clean_bare, damaged = [], 0
    for pid, prob, bare_bill, succ_bill in pairs:
        b_cls = bill_defect_classes(prob, bare_bill)
        s_cls = bill_defect_classes(prob, succ_bill)
        bare_n += bool(b_cls)
        succ_n += bool(s_cls)
        if not b_cls:
            clean_bare.append(pid)
            if [c for c in s_cls if c not in b_cls]:
                damaged += 1
        rows.append({"pid": pid, "bare_classes": b_cls,
                     "succ_classes": s_cls,
                     "bare": float(bool(b_cls)),
                     "succ": float(bool(s_cls))})
        per_item.append({"pid": pid, "bare": float(bool(b_cls)),
                         "succ": float(bool(s_cls))})
    n = len(rows)
    diffs = [r["bare"] - r["succ"] for r in per_item]
    import numpy as np
    rng = np.random.default_rng(seed)
    boots = [float(np.mean(rng.choice(diffs, n, replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {
        "draw": label, "n": n,
        "bare_rate": round(bare_n / n, 4),
        "succ_rate": round(succ_n / n, 4),
        "bare_n": bare_n, "succ_n": succ_n,
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "mean_diff": round(float(sum(diffs) / n), 4),
        "damage": {"clean_bare": len(clean_bare),
                   "damaged": damaged,
                   "rate": round(damaged / len(clean_bare), 4)
                   if clean_bare else 0.0},
        "per_item": rows,
    }


def main() -> int:
    d1 = _score(_pairs_draw1(), "draw-1 (mine, r123_fresh_confirmation_run)", 123)
    d2 = _score(_pairs_draw2(), "draw-2 (twin, r123_fresh_run)", 124)
    # pooled preview (dir 4 runs it fully; same construction here)
    pooled_items = ([{"pid": r["pid"] + "-d1", "bare": r["bare"],
                      "succ": r["succ"]} for r in d1["per_item"]]
                    + [{"pid": r["pid"] + "-d2", "bare": r["bare"],
                        "succ": r["succ"]} for r in d2["per_item"]])
    import numpy as np
    diffs = [r["bare"] - r["succ"] for r in pooled_items]
    rng = np.random.default_rng(125)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    pooled = {
        "n": len(diffs),
        "bare_rate": round(sum(r["bare"] for r in pooled_items)
                           / len(diffs), 4),
        "succ_rate": round(sum(r["succ"] for r in pooled_items)
                           / len(diffs), 4),
        "mean_diff": round(float(np.mean(diffs)), 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "seed": 125,
    }
    gates = {}
    for d in (d1, d2):
        gates[d["draw"][:6]] = {
            "successor_le_025": d["succ_rate"] <= 0.25,
            "ci_lower_gt_0": d["ci95"][0] > 0,
            "damage_le_025": d["damage"]["rate"] <= 0.25}
    out = {
        "record": "R124_F97_REMEASURE/1.0.0",
        "claim": "c-0186 (r124-f97-detector-precision), dir 3",
        "detector": "the F97-fixed scan_input_availability "
                    "(scripts/r40_machine_v77.py @ "
                    "b95afc9006223bcd) inside the amendment-1 "
                    "detector set (imported wrapper); UNSTATED-only "
                    "excluded; DETECTOR_ERROR fail-closed",
        "zero_new_llm": "the committed run bytes only — both "
                        "independent fresh draws re-scored; no "
                        "model was called",
        "draw_1": d1, "draw_2": d2,
        "pooled_preview": pooled,
        "score9_gates_per_draw": gates,
        "history_note": "the F31c/F31b historical records stand as "
                        "measured under the OLD detector (committed "
                        "bytes, never rewritten); this record is the "
                        "re-measure the R124 adjudication ordered "
                        "(dir 3)",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    for d in (d1, d2):
        print(f"{d['draw']}: bare {d['bare_n']}/{d['n']} "
              f"({d['bare_rate']}) vs succ {d['succ_n']}/{d['n']} "
              f"({d['succ_rate']}) | CI {d['ci95']} | damage "
              f"{d['damage']['damaged']}/{d['damage']['clean_bare']}"
              f" = {d['damage']['rate']}")
    print(f"pooled (n={pooled['n']}, seed 125): bare "
          f"{pooled['bare_rate']} vs succ {pooled['succ_rate']} | "
          f"mean {pooled['mean_diff']} CI {pooled['ci95']}")
    print(f"gates: {gates}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
