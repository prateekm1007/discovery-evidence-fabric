#!/usr/bin/env python3
"""r123_fresh_score.py — the F31c fresh-confirmation scoring (claim
c-0183; the prereg eval/r123_fresh_confirmation_prereg.json governs;
zero LLM).

Arms: bare_only = the fresh bare bills (eval/r123_fresh_run/
bare_*.txt); successor = the reviewer-delivered bills (succ_*.json).
The detector function is IMPORTED byte-identical from
scripts/r121_successor_score.py (the amendment-1 detectors — the
machine's own bind scans; UNSTATED-only excluded; DETECTOR_ERROR
fail-closed).

PRIMARY: per arm, the fraction of the 24 delivered bills carrying
>= 1 defect class. Paired bootstrap 10k seed 123 (pre-registered).
Damage gate: among clean-bare items, the fraction where the successor's
delivered bill carries a class the bare bill lacked — <= 0.25.

SCORE-9 GATES (as enacted, R122): successor rate <= 0.25 AND the CI
excludes 0 below bare (lower > 0) AND damage <= 0.25 -> the axis is
ACCEPTED ON THE FRESH SET; else TYPED_NEGATIVE.

Output: eval/r123_fresh_run/scoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

ITEMS = REPO / "eval" / "r123_fresh_set" / "items.jsonl"
RUN = REPO / "eval" / "r123_fresh_run"
OUT = RUN / "scoring.json"


def main() -> int:
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in ITEMS.read_text(encoding="utf-8")
             .strip().split("\n")}
    rows, per_item = [], []
    bare_n = succ_n = 0
    clean_bare, damaged_clean = [], 0
    for pid in sorted(items):
        prob = items[pid]
        bare_bill = (RUN / f"bare_{pid}.txt").read_text(
            encoding="utf-8")
        rec = json.loads((RUN / f"succ_{pid}.json").read_text(
            encoding="utf-8"))
        succ_bill = rec["delivered_bill"]
        b_cls = bill_defect_classes(prob, bare_bill)
        s_cls = bill_defect_classes(prob, succ_bill)
        bare_n += bool(b_cls)
        succ_n += bool(s_cls)
        if not b_cls:
            clean_bare.append(pid)
            if [c for c in s_cls if c not in b_cls]:
                damaged_clean += 1
        rows.append({"pid": pid,
                     "bare_classes": b_cls, "succ_classes": s_cls,
                     "bare_defect": float(bool(b_cls)),
                     "succ_defect": float(bool(s_cls)),
                     "surfaced_n": len(rec["surfaced_findings"])})
        per_item.append({"pid": pid,
                         "bare": float(bool(b_cls)),
                         "succ": float(bool(s_cls))})

    n = len(rows)
    bare_rate, succ_rate = bare_n / n, succ_n / n
    damage = (damaged_clean / len(clean_bare)
              if clean_bare else 0.0)

    import numpy as np
    diffs = [r["bare"] - r["succ"] for r in per_item]
    rng = np.random.default_rng(123)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    boot = {"mean_diff": round(float(np.mean(diffs)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_items": n, "seed": 123,
            "note": "bare_only minus successor on the per-item defect "
                    "indicator (positive = successor fewer defects)"}

    score9 = (succ_rate <= 0.25 and boot["ci95"][0] > 0
              and damage <= 0.25)
    acceptance = (
        "SCORE-9 AXIS ACCEPTED ON THE FRESH SET — successor rate "
        "<= 0.25 AND the paired CI excludes 0 below bare AND the "
        "damage gate holds (<= 0.25): the bind-check value replicates "
        "on held-out scenarios never used in calibration"
        if score9 else
        "TYPED_NEGATIVE ON THE FRESH SET — the gates failed as "
        "pre-registered; the score-9 axis question returns to the "
        "auditor with the per-class table and the damage rows")

    out = {
        "record": "R123_F31C_RESULT/1.0.0",
        "claim": "c-0183 (r123-fresh-confirmation-run)",
        "prereg": "eval/r123_fresh_confirmation_prereg.json",
        "n_items": n,
        "delivered_defect_rate": {
            "bare_only": round(bare_rate, 4),
            "successor": round(succ_rate, 4),
            "bare_n": bare_n, "succ_n": succ_n},
        "damage_gate": {
            "clean_bare_items": len(clean_bare),
            "damaged_clean": damaged_clean,
            "rate": round(damage, 4), "gate": "<= 0.25"},
        "paired_bootstrap": boot,
        "per_class": {},
        "per_item": rows,
        "acceptance_branch": acceptance,
        "score9_gates": {"successor_le_025": succ_rate <= 0.25,
                         "ci_lower_gt_0": boot["ci95"][0] > 0,
                         "damage_le_025": damage <= 0.25,
                         "all_three": score9},
        "detector": "the amendment-1 detectors IMPORTED from "
                    "scripts/r121_successor_score.py (byte-identical; "
                    "UNSTATED-only excluded; DETECTOR_ERROR fail-"
                    "closed); zero LLM, zero judge calls",
        "set_note": "the FRESH held-out set (eval/r123_fresh_set; 12 "
                    "new disjoint domains x 2 draws; no defect ground "
                    "truth seeded; bytes frozen at the prereg commit "
                    "528368856)",
    }
    for cls in ("input_availability", "duty_pricing",
                "constraint_violation",
                "physics_direction_inversion"):
        out["per_class"][cls] = {
            "bare_only": sum(1 for r in rows
                             if cls in r["bare_classes"]),
            "successor": sum(1 for r in rows
                             if cls in r["succ_classes"]), "n": n}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"delivered-defect-rate: bare_only {bare_n}/{n} "
          f"({bare_rate:.3f}) vs successor {succ_n}/{n} "
          f"({succ_rate:.3f})")
    print(f"damage gate: {damaged_clean}/{len(clean_bare)} = "
          f"{damage:.3f} (gate <= 0.25)")
    print(f"bootstrap: {boot}")
    print(f"score-9 gates: {out['score9_gates']}")
    print(f"acceptance: {acceptance[:130]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
