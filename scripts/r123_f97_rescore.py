#!/usr/bin/env python3
"""r123_f97_rescore.py — the F97 re-scoring of BOTH committed fresh
draws (the R123 verdict dir 2b; zero LLM, zero network).

Re-runs the amendment-1 detector (IMPORTED from scripts/r121_successor_score.py
— which now carries the F97-fixed r40_machine_v77.scan_input_availability)
over the 48 raw artifact pairs (24 items x 2 arms x 2 independent
lanes), and emits:
  - the F97-corrected delivered-defect-rate per arm per lane;
  - the DELTA vs the committed (pre-F97) scoring.json per lane;
  - the per-class table + the per-item before/after map;
  - the pooled n=48 paired bootstrap (the verdict dir 4) seed 124.

Output: eval/r123_f97_rescoring/rescoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

SET = REPO / "eval" / "r123_fresh_set" / "items.jsonl"
LANES = {
    "twin_claiming_run": REPO / "eval" / "r123_fresh_confirmation_run",
    "replication_run": REPO / "eval" / "r123_fresh_run",
}
OUT = REPO / "eval" / "r123_f97_rescoring"
OUT.mkdir(parents=True, exist_ok=True)


def lane_rows(lane_dir: Path, items: dict):
    rows = []
    for pid in sorted(items):
        prob = items[pid]
        bpath = lane_dir / f"bare_{pid}.txt"
        spath = lane_dir / f"succ_{pid}.json"
        rpath = lane_dir / f"row_{pid}.json"
        if bpath.exists():
            bare = bpath.read_text(encoding="utf-8")
            rec = json.loads(spath.read_text(encoding="utf-8"))
        elif rpath.exists():
            rec = json.loads(rpath.read_text(encoding="utf-8"))
            bare = rec["authored_bill"]
        else:
            continue
        succ = rec["delivered_bill"]
        pre = rec.get("post_review_scan") or {}
        rows.append({
            "pid": pid,
            "bare_classes": bill_defect_classes(prob, bare),
            "succ_classes": bill_defect_classes(prob, succ),
            "pre_f97_succ_findings": pre.get("INPUT_UNAVAILABLE", []),
        })
    return rows


def rates(rows):
    n = len(rows)
    b = sum(1 for r in rows if r["bare_classes"])
    s = sum(1 for r in rows if r["succ_classes"])
    return n, b, s, (b / n if n else 0.0), (s / n if n else 0.0)


def _damage(rows):
    """Among clean-bare items, the fraction where the successor's
    delivered bill carries a class the bare bill lacked."""
    clean = [r for r in rows if not r["bare_classes"]]
    dmg = [r for r in clean
           if [c for c in r["succ_classes"]
               if c not in r["bare_classes"]]]
    return {"clean_bare_items": len(clean), "damaged_clean": len(dmg),
            "rate": (round(len(dmg) / len(clean), 4) if clean else 0.0),
            "rows": [r["pid"] for r in dmg]}


def main() -> int:
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in SET.read_text(encoding="utf-8").strip().split("\n")
             if l}
    out = {"record": "R123_F97_RESCORING/1.0.0",
           "note": "both committed fresh draws re-scored under the "
                   "F97-fixed amendment-1 detector (imported bytes; "
                   "zero LLM). The detector change is the R123 "
                   "adjudication dir 2; the pre-F97 committed "
                   "scoring.json records stand as measured.",
           "lanes": {}, "pooled": {}}
    pooled_pairs = []
    for lane, ldir in LANES.items():
        rows = lane_rows(ldir, items)
        n, b, s, br, sr = rates(rows)
        # per-class deltas
        cls = {}
        for k in ("input_availability", "duty_pricing",
                  "constraint_violation", "physics_direction_inversion"):
            cls[k] = {
                "bare": sum(1 for r in rows
                            if k in r["bare_classes"]),
                "succ": sum(1 for r in rows
                            if k in r["succ_classes"])}
        out["lanes"][lane] = {
            "n": n, "bare_defect_n": b, "succ_defect_n": s,
            "bare_rate": round(br, 4), "succ_rate": round(sr, 4),
            "damage_gate": _damage(rows),
            "pre_f97_committed": {
                "twin_claiming_run": {"bare_rate": 0.708, "succ_rate": 0.375},
                "replication_run": {"bare_rate": 0.583, "succ_rate": 0.417},
            }[lane],
            "per_class": cls,
            "per_item": [{"pid": r["pid"],
                          "bare": bool(r["bare_classes"]),
                          "succ": bool(r["succ_classes"]),
                          "succ_classes": r["succ_classes"]}
                         for r in rows],
        }
        pooled_pairs += [(r["pid"], bool(r["bare_classes"]),
                          bool(r["succ_classes"])) for r in rows]

    # pooled n=48 paired bootstrap (the verdict dir 4), seed 124
    import numpy as np
    diffs = [float(b) - float(s) for _, b, s in pooled_pairs]
    rng = np.random.default_rng(124)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    n = len(pooled_pairs)
    nb = sum(d > 0 for d in diffs)
    out["pooled"] = {
        "n_items": n,
        "bare_rate": round(sum(float(b) for _, b, _ in pooled_pairs) / n,
                           4),
        "succ_rate": round(sum(float(s) for _, _, s in pooled_pairs) / n,
                           4),
        "mean_diff": round(float(np.mean(diffs)), 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "seed": 124,
        "items_better": nb, "items_worse": sum(d < 0 for d in diffs),
        "note": "pooled paired bootstrap over the two independent "
                "fresh draws (the R123 verdict dir 4, Art. 14 power); "
                "positive = successor fewer defects"}

    (OUT / "rescoring.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    for lane, d in out["lanes"].items():
        print(f"{lane}: bare {d['bare_defect_n']}/{d['n']} "
              f"({d['bare_rate']}) vs succ {d['succ_defect_n']}/{d['n']} "
              f"({d['succ_rate']}) [pre-F97 committed: "
              f"{d['pre_f97_committed']['bare_rate']} -> "
              f"{d['pre_f97_committed']['succ_rate']}]")
        print(f"  per_class: {json.dumps(d['per_class'])}")
    p = out["pooled"]
    print(f"POOLED n={p['n_items']}: bare {p['bare_rate']} vs succ "
          f"{p['succ_rate']}; mean_diff {p['mean_diff']} "
          f"CI95 {p['ci95']} (better/worse {p['items_better']}/"
          f"{p['items_worse']})")
    print(f"written: {OUT/'rescoring.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
