#!/usr/bin/env python3
"""r123_v2_score.py — the F31d successor-v2 scoring (claim c-0188; the
prereg eval/r123_successor_v2_prereg.json governs; zero LLM).

Arms: bare_only = the committed bare bytes of BOTH draws (48 items);
successor_v2 = the v2 delivered bills (eval/r123_v2_run/v2_*.json).
The detector: the amendment-1 set via the CANONICAL F97-fixed machine
(imported through r121_successor_score.bill_defect_classes).

PRIMARY: pooled + per-lane delivered-defect-rate. Paired bootstrap 10k
seed 126 (pre-registered). Damage gate. The score-9 gates:
pooled succ <= 0.25 AND CI lower > 0 AND damage <= 0.25.

Output: eval/r123_v2_run/scoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402
from r123_v2_run import items_by_lane  # noqa: E402

RUN = REPO / "eval" / "r123_v2_run"
OUT = RUN / "scoring.json"


def main() -> int:
    rows_all = items_by_lane()
    rows = []
    for lane, pid, prob, bare in rows_all:
        outp = RUN / f"v2_{lane}_{pid}.json"
        if not outp.exists():
            raise SystemExit(f"MISSING v2 record: {outp.name}")
        rec = json.loads(outp.read_text(encoding="utf-8"))
        assert rec["authored_bill"] == bare, (
            f"{lane}/{pid}: v2 record's authored bill is NOT the "
            "committed bare bytes")
        b_cls = bill_defect_classes(prob, bare)
        s_cls = bill_defect_classes(prob, rec["delivered_bill"])
        rows.append({"lane": lane, "pid": pid,
                     "bare_classes": b_cls, "succ_classes": s_cls,
                     "surfaced_n": len(rec["surfaced_findings"]),
                     "reviewer_skipped": rec.get("reviewer_skipped",
                                                 False)})

    def stats(rs):
        n = len(rs)
        b = sum(1 for r in rs if r["bare_classes"])
        s = sum(1 for r in rs if r["succ_classes"])
        clean = [r for r in rs if not r["bare_classes"]]
        dmg = [r for r in clean if [c for c in r["succ_classes"]
                                    if c not in r["bare_classes"]]]
        return {"n": n, "bare_n": b, "succ_n": s,
                "bare_rate": round(b / n, 4), "succ_rate": round(s / n, 4),
                "damage": {"clean_bare_items": len(clean),
                           "damaged_clean": len(dmg),
                           "rate": round(len(dmg) / len(clean), 4)
                           if clean else 0.0,
                           "rows": [r["pid"] for r in dmg]}}

    pooled = stats(rows)
    per_lane = {lane: stats([r for r in rows if r["lane"] == lane])
                for lane in ("replication", "claiming")}

    import numpy as np
    diffs = [float(bool(r["bare_classes"])) -
             float(bool(r["succ_classes"])) for r in rows]
    rng = np.random.default_rng(126)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    boot = {"mean_diff": round(float(np.mean(diffs)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_items": len(diffs), "seed": 126,
            "items_better": sum(d > 0 for d in diffs),
            "items_worse": sum(d < 0 for d in diffs)}

    score9 = (pooled["succ_rate"] <= 0.25 and boot["ci95"][0] > 0
              and pooled["damage"]["rate"] <= 0.25)
    acceptance = (
        "SCORE-9 AXIS FULLY MET ON THE POOLED F31D MEASUREMENT — "
        "pooled successor rate <= 0.25 AND the paired CI excludes 0 "
        "below bare AND damage <= 0.25 (the improved-directive "
        "first pass under the canonical F97-fixed detector)"
        if score9 else
        "TYPED_NEGATIVE ON THE F31D GATES AS PRE-REGISTERED — the "
        "gates failed; the score-9 axis question returns to the "
        "auditor with the per-class table and the damage rows")

    cls_names = ("input_availability", "duty_pricing",
                 "constraint_violation", "physics_direction_inversion")
    out = {
        "record": "R123_F31D_RESULT/1.0.0",
        "claim": "c-0188 (r123-successor-v2-fresh-run)",
        "prereg": "eval/r123_successor_v2_prereg.json",
        "pooled": pooled,
        "per_lane": per_lane,
        "paired_bootstrap": boot,
        "score9_gates": {"successor_le_025":
                         pooled["succ_rate"] <= 0.25,
                         "ci_lower_gt_0": boot["ci95"][0] > 0,
                         "damage_le_025":
                         pooled["damage"]["rate"] <= 0.25,
                         "all_three": score9},
        "per_class": {c: {
            "bare": sum(1 for r in rows if c in r["bare_classes"]),
            "succ_v2": sum(1 for r in rows
                           if c in r["succ_classes"])}
            for c in cls_names},
        "reviewer_skipped_n": sum(1 for r in rows
                                  if r["reviewer_skipped"]),
        "acceptance_branch": acceptance,
        "detector": "the amendment-1 detectors via the CANONICAL "
                    "F97-fixed machine (imported bytes; UNSTATED-only "
                    "excluded; DETECTOR_ERROR fail-closed); zero LLM, "
                    "zero judge calls",
        "reviewer_directive": "the twin's FROZEN improved-directive "
                              "bytes (eval/r122_lever_prereg.json), "
                              "imported byte-exact",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"POOLED n={pooled['n']}: bare {pooled['bare_n']} "
          f"({pooled['bare_rate']}) vs succ_v2 {pooled['succ_n']} "
          f"({pooled['succ_rate']}); damage {pooled['damage']}")
    for lane, d in per_lane.items():
        print(f"  {lane}: bare {d['bare_rate']} vs succ_v2 "
              f"{d['succ_rate']}; damage {d['damage']['rate']}")
    print(f"bootstrap: {boot}")
    print(f"per_class: {json.dumps(out['per_class'])}")
    print(f"score-9 gates: {out['score9_gates']}")
    print(f"acceptance: {acceptance[:120]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
