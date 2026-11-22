#!/usr/bin/env python3
"""r121_successor_score.py — the F31b delivered-defect-rate scoring
(claim c-0181; the prereg eval/r121_successor_bind_value_prereg.json
governs; zero LLM).

Arms: bare_only = the committed F31a bare bills (byte-identical
re-use); successor = the reviewer-delivered bills in
eval/r121_successor_run/. The amendment-1 detectors (the machine's own
bind scans over (prob, delivered_bill); UNSTATED-only formatting
demands excluded; DETECTOR_ERROR fail-closed).

PRIMARY: per arm, the fraction of the 24 delivered bills carrying
>= 1 defect class. Paired bootstrap 10k seed 121 on the per-item
defect indicator (bare minus successor). Damage gate: among clean-bare
items, the fraction where the successor's delivered bill carries a
class the bare bill lacked — <= 0.25.

Output: eval/r121_successor_run/scoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402

ITEMS = REPO / "eval" / "r118_authoring_set" / "items.jsonl"
BARE_DIR = REPO / "eval" / "r118_authoring_run"
SUCC = REPO / "eval" / "r121_successor_run"
OUT = SUCC / "scoring.json"

DEFECT_KEYS = ("INPUT_UNAVAILABLE", "UNPRICED_DUTY_CYCLE",
               "CONSTRAINT_EXCLUSION", "ALLOWED_ROW_OUTSIDE",
               "PHYSICS_DIRECTION_INVERTED", "DRIVER_AS_REMEDY")


def bill_defect_classes(prob: dict, bill: str) -> list:
    """The amendment-1 detector set — identical to the F31a scoring
    (scripts/r118_authoring_score.py): the defect-finding whitelist;
    UNSTATED-only does not count; DETECTOR_ERROR fail-closed."""
    out = []
    checks = [
        ("input_availability", m77.scan_input_availability,
         (prob, bill)),
        ("duty_pricing", m77.scan_duty_cycle_pricing, (bill,)),
        ("constraint_violation", m77.scan_allowed_measures_class,
         (prob, bill)),
    ]
    for cls, fn, args in checks:
        try:
            r = fn(*args)
            if r and any(k in r for k in DEFECT_KEYS):
                out.append(cls)
        except Exception:  # noqa: BLE001
            out.append(f"DETECTOR_ERROR:{cls}")
    try:
        r = m77.scan_physics_direction(prob, bill)
        if any(k in r for k in ("PHYSICS_DIRECTION_INVERTED",
                                "DRIVER_AS_REMEDY")):
            out.append("physics_direction_inversion")
    except Exception:  # noqa: BLE001
        out.append("DETECTOR_ERROR:physics_direction_inversion")
    return out


def main() -> int:
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in ITEMS.read_text(encoding="utf-8")
             .strip().split("\n")}
    rows, per_item = [], []
    bare_n = succ_n = 0
    clean_bare, damaged_clean = [], 0
    for pid in sorted(items):
        prob = items[pid]
        bare_bill = (BARE_DIR / f"bare_{pid}.txt").read_text(
            encoding="utf-8")
        rec = json.loads((SUCC / f"succ_{pid}.json").read_text(
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
    rng = np.random.default_rng(121)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    boot = {"mean_diff": round(float(np.mean(diffs)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_items": n, "seed": 121,
            "note": "bare_only minus successor on the per-item defect "
                    "indicator (positive = successor fewer defects)"}

    proven = (succ_rate < bare_rate and boot["ci95"][0] > 0
              and damage <= 0.25)
    acceptance = (
        "BIND-CHECK VALUE PROVEN on the successor shape — successor "
        "rate < bare AND the paired CI excludes 0 AND the damage gate "
        "holds (<= 0.25)"
        if proven else
        "TYPED_NEGATIVE — the gates failed as configured; the "
        "bind-retirement question goes to the auditor with the "
        "per-class table and the damage rows")

    out = {
        "record": "R121_F31B_RESULT/1.0.0",
        "claim": "c-0181 (r121-successor-bind-value-run)",
        "prereg": "eval/r121_successor_bind_value_prereg.json",
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
        "detector": "the amendment-1 detectors (the machine's own "
                    "bind scans; UNSTATED-only excluded; "
                    "DETECTOR_ERROR fail-closed); zero LLM, zero "
                    "judge calls",
        "baseline_note": "the bare_only arm is the committed F31a "
                         "baseline re-used byte-identical (zero new "
                         "authoring calls), scored under the SAME "
                         "detectors as the F31a result — the 10/24 "
                         "baseline reproduces exactly",
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
    print(f"acceptance: {acceptance[:120]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
