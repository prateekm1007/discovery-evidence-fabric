#!/usr/bin/env python3
"""r125_f31e_score.py — the F31e clean-confirmation scoring (claim
c-0191; the prereg eval/r125_f31e_prereg.json governs; zero LLM).

Per arm per draw + pooled over the 48 pairs (2 draws x 24 items):
delivered-defect-rate under the CANONICAL F97-fixed detectors (imported
via r121_successor_score.bill_defect_classes). Paired bootstrap 10k
seed 127 (pre-registered). Damage gate. The score-9 acceptance gates:
pooled successor <= 0.25 AND CI lower > 0 AND damage <= 0.25.

Output: eval/r125_f31e_run/scoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

RUN = REPO / "eval" / "r125_f31e_run"
OUT = RUN / "scoring.json"


def main() -> int:
    items = [json.loads(l) for l in (REPO / "eval" / "r125_f31e_set"
             / "items.jsonl").read_text(encoding="utf-8").strip()
             .split("\n") if l]
    rows = []
    for draw in ("d1", "d2"):
        for prob in items:
            pid = prob["problem_id"]
            bpath = RUN / f"bare_{draw}_{pid}.txt"
            spath = RUN / f"succ_{draw}_{pid}.json"
            assert bpath.exists(), f"missing {bpath.name}"
            assert spath.exists(), f"missing {spath.name}"
            rec = json.loads(spath.read_text(encoding="utf-8"))
            bare = bpath.read_text(encoding="utf-8")
            assert rec["authored_bill"] == bare, (
                f"{draw}/{pid}: the record's authored bill is NOT the "
                "draw's committed bare bytes")
            rows.append({
                "draw": draw, "pid": pid,
                "bare_classes": bill_defect_classes(prob, bare),
                "succ_classes": bill_defect_classes(
                    prob, rec["delivered_bill"]),
                "reviewer_skipped": rec.get("reviewer_skipped", False)})

    def stats(rs):
        n = len(rs)
        b = sum(1 for r in rs if r["bare_classes"])
        s = sum(1 for r in rs if r["succ_classes"])
        clean = [r for r in rs if not r["bare_classes"]]
        dmg = [r for r in clean if [c for c in r["succ_classes"]
                                    if c not in r["bare_classes"]]]
        return {"n": n, "bare_n": b, "succ_n": s,
                "bare_rate": round(b / n, 4),
                "succ_rate": round(s / n, 4),
                "damage": {"clean_bare_items": len(clean),
                           "damaged_clean": len(dmg),
                           "rate": round(len(dmg) / len(clean), 4)
                           if clean else 0.0,
                           "rows": [r["pid"] for r in dmg]}}

    pooled = stats(rows)
    per_draw = {d: stats([r for r in rows if r["draw"] == d])
                for d in ("d1", "d2")}

    import numpy as np
    diffs = [float(bool(r["bare_classes"])) -
             float(bool(r["succ_classes"])) for r in rows]
    rng = np.random.default_rng(127)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    boot = {"mean_diff": round(float(np.mean(diffs)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_items": len(diffs), "seed": 127,
            "items_better": sum(d > 0 for d in diffs),
            "items_worse": sum(d < 0 for d in diffs)}

    accepted = (pooled["succ_rate"] <= 0.25 and boot["ci95"][0] > 0
                and pooled["damage"]["rate"] <= 0.25)
    acceptance = (
        "SCORE-9 AXIS ACCEPTED ON THE F31E CLEAN CONFIRMATION — "
        "pooled successor <= 0.25 AND the paired CI excludes 0 below "
        "bare AND damage <= 0.25 (fresh bills never in the F97 "
        "calibration corpus; the canonical F97-fixed detector)"
        if accepted else
        "TYPED_NEGATIVE ON THE F31E GATES AS PRE-REGISTERED — the "
        "clean-acceptance gates failed; the score-9 acceptance "
        "question returns to the auditor with the per-class table")

    cls_names = ("input_availability", "duty_pricing",
                 "constraint_violation", "physics_direction_inversion")
    out = {
        "record": "R125_F31E_RESULT/1.0.0",
        "claim": "c-0191 (r125-f31e-clean-confirmation)",
        "prereg": "eval/r125_f31e_prereg.json",
        "pooled": pooled,
        "per_draw": per_draw,
        "paired_bootstrap": boot,
        "score9_gates": {"successor_le_025":
                         pooled["succ_rate"] <= 0.25,
                         "ci_lower_gt_0": boot["ci95"][0] > 0,
                         "damage_le_025":
                         pooled["damage"]["rate"] <= 0.25,
                         "all_three": accepted},
        "per_class": {c: {
            "bare": sum(1 for r in rows if c in r["bare_classes"]),
            "succ": sum(1 for r in rows if c in r["succ_classes"])}
            for c in cls_names},
        "reviewer_skipped_n": sum(1 for r in rows
                                  if r["reviewer_skipped"]),
        "acceptance_branch": acceptance,
        "detector": "the amendment-1 detectors via the CANONICAL "
                    "F97-fixed machine (imported bytes; UNSTATED-only "
                    "excluded; DETECTOR_ERROR fail-closed); zero LLM "
                    "at scoring time",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"POOLED n={pooled['n']}: bare {pooled['bare_n']} "
          f"({pooled['bare_rate']}) vs succ {pooled['succ_n']} "
          f"({pooled['succ_rate']}); damage {pooled['damage']}")
    for d, s in per_draw.items():
        print(f"  {d}: bare {s['bare_rate']} vs succ "
              f"{s['succ_rate']}; damage {s['damage']['rate']}")
    print(f"bootstrap: {boot}")
    print(f"per_class: {json.dumps(out['per_class'])}")
    print(f"score-9 gates: {out['score9_gates']}")
    print(f"acceptance: {acceptance[:130]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
