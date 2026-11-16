#!/usr/bin/env python3
"""r35_pin_tests.py — AM33 D2/D3 acceptance tests on committed bytes.

D2: the ACTUATION_DEVICE_AS_MEASURE pin must FIRE on the committed
    HO5-05 solenoid-valve bytes (the v5 escape: a timer-controlled
    solenoid valve laundered into a permitted duty-cycle change).
D3: the DIRECTION_INVERTED_ARITHMETIC pin must FIRE on the committed
    HO5-06 bytes (30-min holds at 600/1000 °C while claiming to cut
    cumulative creep strain).
FP check: neither NEW family may fire on the other 10 v5 rows
    (their committed residuals stay untouched; any fire would be
    inspected and typed before the pin ships).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from r30_allowed_class_scan import scan_allowed_measures_class  # noqa
from r30_physics_direction_scan import scan_physics_direction  # noqa

ROWS = REPO / "eval" / "pairs" / "holdout_v5_generation"
PACKET = REPO / "eval" / "holdout_v5_problems.json"
OUT = REPO / "eval" / "r35_pin_tests.json"


def main() -> int:
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    rows = packet.get("rows") or packet.get("problems") or []
    probs = {r["problem_id"]: (r.get("problem") or r) for r in rows}
    results = []
    for f in sorted(ROWS.glob("HO5-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d["problem_id"]
        prob = probs.get(pid, {})
        class_out = scan_allowed_measures_class(prob, d["a1_answer"])
        dir_out = scan_physics_direction(prob, d["a1_answer"])
        results.append({
            "problem_id": pid,
            "ACTUATION_DEVICE_AS_MEASURE":
                class_out.get("ACTUATION_DEVICE_AS_MEASURE"),
            "DIRECTION_INVERTED_ARITHMETIC":
                dir_out.get("DIRECTION_INVERTED_ARITHMETIC"),
            "DIRECTION_CONTESTABLE_TYPED":
                dir_out.get("DIRECTION_CONTESTABLE_TYPED"),
            "other_new_families": {
                k: v for k, v in {**class_out, **dir_out}.items()
                if k not in ("ACTUATION_DEVICE_AS_MEASURE",
                             "DIRECTION_INVERTED_ARITHMETIC",
                             "DIRECTION_CONTESTABLE_TYPED")},
        })
    by_id = {r["problem_id"]: r for r in results}
    d2_fire = bool(by_id.get("HO5-05-gearbox-oil-foaming", {})
                   .get("ACTUATION_DEVICE_AS_MEASURE"))
    d2_text = (by_id.get("HO5-05-gearbox-oil-foaming", {})
               .get("ACTUATION_DEVICE_AS_MEASURE") or [""])[0]
    d3_fire = bool(by_id.get("HO5-06-vacuum-furnace-hotzone-sag", {})
                   .get("DIRECTION_INVERTED_ARITHMETIC"))
    d3_text = (by_id.get("HO5-06-vacuum-furnace-hotzone-sag", {})
               .get("DIRECTION_INVERTED_ARITHMETIC") or [""])[0]
    fp = [{"problem_id": r["problem_id"],
           "new_families": [k for k in
                            ("ACTUATION_DEVICE_AS_MEASURE",
                             "DIRECTION_INVERTED_ARITHMETIC")
                            if r.get(k)]}
          for r in results
          if not r["problem_id"].startswith(
              ("HO5-05", "HO5-06")) and (r.get("ACTUATION_DEVICE_AS_MEASURE")
                                         or r.get("DIRECTION_INVERTED_ARITHMETIC"))]
    out = {
        "record": "R35_PIN_TESTS/1.0.0",
        "d2_actuation_pin_fires_on_HO5_05": d2_fire,
        "d2_evidence": d2_text[:220],
        "d3_direction_pin_fires_on_HO5_06": d3_fire,
        "d3_evidence": d3_text[:260],
        "d2_accept": "MET" if d2_fire and not fp else (
            "FIRE-OK-BUT-FP-CHECK-OPEN" if d2_fire else "NOT MET"),
        "d3_accept": "MET" if d3_fire and not fp else (
            "FIRE-OK-BUT-FP-CHECK-OPEN" if d3_fire else "NOT MET"),
        "false_positive_check": {"n_fp_rows": len(fp), "rows": fp},
        "rows": results,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"D2 (HO5-05 solenoid): FIRES={d2_fire}")
    print(f"  evidence: {d2_text[:180]}")
    print(f"D3 (HO5-06 holds):  FIRES={d3_fire}")
    print(f"  evidence: {d3_text[:200]}")
    print(f"FP rows: {len(fp)} -> {[r['problem_id'] for r in fp]}")
    print(f"D2 accept: {out['d2_accept']} | D3 accept: {out['d3_accept']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
