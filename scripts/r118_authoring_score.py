#!/usr/bin/env python3
"""r118_authoring_score.py — the F31a delivered-defect-rate scoring
(claim c-0176; the prereg eval/r118_authoring_bind_value_prereg.json
governs; zero LLM).

PRIMARY: per arm, the fraction of the 24 DELIVERED bills carrying
>= 1 defect of any of the 6 adjudicated classes, detected by the
committed F30 preflight detectors (scripts/r117_f30_build_v11.py's
own logic, imported — never re-declared). For bare_only the
delivered bill IS the one-call authored text; for bare_plus_binds it
is the delivered bill AFTER the bind check + repair loop.

DAMAGE GATE: among the items whose BARE bill was CLEAN (no class
detected), the fraction where the binds arm's DELIVERED bill carries
a class the bare bill did not (the repair leg introducing a defect
class into a clean bill) — must be <= 0.25.

PAIRED BOOTSTRAP: per-item defect indicator, bare_only minus
bare_plus_binds, percentile bootstrap 10k, seed 118.

Output: eval/r118_authoring_run/scoring.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

RUN = REPO / "eval" / "r118_authoring_run"
KEY = REPO / "eval" / "r118_authoring_set" / "key.json"
ITEMS = REPO / "eval" / "r118_authoring_set" / "items.jsonl"
OUT = RUN / "scoring.json"

# import the machine's own bind scans — the amendment-1 detectors
# (the only committed, adjudicated definitions of the 6 defect
# classes ON bills; the F30 detectors are problem-bytes detectors)
import r40_machine_v77 as m77  # noqa: E402


def bill_defect_classes(prob: dict, bill: str) -> list:
    """The adjudicated defect classes present in a DELIVERED bill
    (amendment 1: the machine's own bind scans over (prob, bill);
    PHYSICS_DIRECTION_UNSTATED does NOT count — 'unstated' is a
    formatting demand, not a defect class)."""
    out = []
    j = None
    checks = [
        ("input_availability", m77.scan_input_availability, (prob, bill)),
        ("duty_pricing", m77.scan_duty_cycle_pricing, (bill,)),
        ("constraint_violation", m77.scan_allowed_measures_class,
         (prob, bill)),
    ]
    for cls, fn, args in checks:
        try:
            r = fn(*args)
            if r and any(k for k in r if k in (
                    "INPUT_UNAVAILABLE", "UNPRICED_DUTY_CYCLE",
                    "CONSTRAINT_EXCLUSION", "ALLOWED_ROW_OUTSIDE",
                    "PHYSICS_DIRECTION_INVERTED", "DRIVER_AS_REMEDY")):
                out.append(cls)
        except Exception:  # noqa: BLE001 — typed, never silent
            out.append(f"DETECTOR_ERROR:{cls}")
    # physics-direction defect findings only (UNSTATED is a formatting
    # demand, not a defect): INVERTED or DRIVER_AS_REMEDY
    try:
        r = m77.scan_physics_direction(prob, bill)
        if any(k in r for k in ("PHYSICS_DIRECTION_INVERTED",
                                "DRIVER_AS_REMEDY")):
            out.append("physics_direction_inversion")
    except Exception:  # noqa: BLE001
        out.append("DETECTOR_ERROR:physics_direction_inversion")
    return out


def main() -> int:
    key = json.loads(KEY.read_text(encoding="utf-8"))
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in ITEMS.read_text(encoding="utf-8")
             .strip().split("\n")}
    per_item, rows = [], []
    bare_defect_n = binds_defect_n = 0
    clean_bare_items = []
    damaged_clean = 0
    for p in key["pairs"]:
        cls_pair = p["class"]
        for pid in p["items"]:
            prob = items[pid]
            bare_bill = (RUN / f"bare_{pid}.txt").read_text(
                encoding="utf-8")
            rec = json.loads(
                (RUN / f"binds_{pid}.json").read_text(
                    encoding="utf-8"))
            binds_bill = rec["delivered_bill"]
            bare_cls = bill_defect_classes(prob, bare_bill)
            binds_cls = bill_defect_classes(prob, binds_bill)
            bare_defect_n += bool(bare_cls)
            binds_defect_n += bool(binds_cls)
            if not bare_cls:
                clean_bare_items.append(pid)
                new = [c for c in binds_cls if c not in bare_cls]
                if new:
                    damaged_clean += 1
            rows.append({"pid": pid, "pair": p["pair"],
                         "scenario_class": cls_pair,
                         "bare_classes": bare_cls,
                         "binds_classes": binds_cls,
                         "bare_defect": float(bool(bare_cls)),
                         "binds_defect": float(bool(binds_cls))})
            per_item.append(
                {"pid": pid,
                 "bare": float(bool(bare_cls)),
                 "binds": float(bool(binds_cls))})

    n = len(rows)
    bare_rate = bare_defect_n / n
    binds_rate = binds_defect_n / n
    damage_rate = (damaged_clean / len(clean_bare_items)
                   if clean_bare_items else 0.0)

    import numpy as np
    diffs = [r["bare"] - r["binds"] for r in per_item]
    rng = np.random.default_rng(118)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    boot = {"mean_diff": round(float(np.mean(diffs)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_items": n, "seed": 118,
            "note": "bare_only minus bare_plus_binds on per-item "
                    "defect indicator (positive = binds fewer defects)"}

    proven = (boot["ci95"][0] > 0 and damage_rate <= 0.25)
    acceptance = (
        "BIND VALUE PROVEN on the working configuration — the paired "
        "CI excludes 0 with bare_plus_binds LOWER (fewer delivered "
        "defects) AND the damage gate holds (<= 0.25)"
        if proven else
        "TYPED_NEGATIVE — the CI covers 0 (or reverses) or the damage "
        "gate failed; the bind-retirement question goes to the auditor "
        "with the per-class table and the damage rows")

    out = {
        "record": "R118_F31A_RESULT/1.0.0",
        "claim": "c-0176 (r118-authoring-bind-value-run)",
        "prereg": "eval/r118_authoring_bind_value_prereg.json",
        "n_items": n,
        "delivered_defect_rate": {
            "bare_only": round(bare_rate, 4),
            "bare_plus_binds": round(binds_rate, 4),
            "bare_n": bare_defect_n, "binds_n": binds_defect_n},
        "damage_gate": {
            "clean_bare_items": len(clean_bare_items),
            "damaged_clean": damaged_clean,
            "rate": round(damage_rate, 4),
            "gate": "<= 0.25"},
        "paired_bootstrap": boot,
        "per_class": {},
        "per_item": rows,
        "acceptance_branch": acceptance,
        "detector": "AMENDMENT 1: the machine's own bind scans "
                    "over (prob, delivered_bill) — the only committed "
                    "definitions of the 6 classes on bills; "
                    "PHYSICS_DIRECTION_UNSTATED excluded (formatting "
                    "demand, not a defect); the circularity caveat "
                    "disclosed in scoring_amendment_1.json and the "
                    "result record; zero LLM, zero judge calls",
        "runner_note": "one pre-run signature fix disclosed: the "
                       "runner's first binds-arm pass called "
                       "scan_stated_formula_direction(prob, answer) — "
                       "the frozen module's signature is (answer); 2 "
                       "TYPED_FAIL stubs were produced and deleted "
                       "BEFORE any successful binds byte existed "
                       "(both stubs authored-bill-only, no repair ran; "
                       "the items re-ran clean after the fix — no "
                       "double generation: the fails produced zero "
                       "committed generation bytes)",
    }
    for cls in ("input_availability", "duty_pricing",
                "constraint_violation",
                "physics_direction_inversion"):
        rb = sum(1 for r in rows if cls in r["bare_classes"])
        rn = sum(1 for r in rows if cls in r["binds_classes"])
        out["per_class"][cls] = {"bare_only": rb,
                                 "bare_plus_binds": rn, "n": n}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"delivered-defect-rate: bare_only {bare_defect_n}/{n} "
          f"({bare_rate:.3f}) vs bare_plus_binds {binds_defect_n}/{n} "
          f"({binds_rate:.3f})")
    print(f"damage gate: {damaged_clean}/{len(clean_bare_items)} "
          f"= {damage_rate:.3f} (gate <= 0.25)")
    print(f"bootstrap: {boot}")
    print(f"acceptance: {acceptance[:110]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
