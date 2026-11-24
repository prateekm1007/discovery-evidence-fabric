#!/usr/bin/env python3
"""r145s1 v17 SEALED builder screen — the typed INPUT record for the
auditor (Art. 14: never the verdict). Reads ONLY the committed run
bytes; measures the DIR-3 acceptance surface (quant prediction
coverage, QUANT_TEST_MISSING, kill conditions) + the kit wiring
surface (class routing, engine prediction manifests, inspiration,
novelty gate)."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "holdout_v17_sealed_generation"

sys.path.insert(0, str(REPO))
from discovery_fabric.generation.quant_generic import (  # noqa: E402
    emit_prediction_generic)

NUM_UNIT = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:[µμu]m|mm|cm|m\b|kPa|MPa|Pa\b|bar\b|°C|"
    r"\bK\b|W\b|kW\b|MW\b|J\b|kJ\b|Wh\b|kWh\b|N\b|kN\b|Hz\b|kHz\b|"
    r"rpm|A\b|mA\b|V\b|mV\b|kV\b|s\b|ms\b|min\b|h\b|mol|ppm|wt\s?%|"
    r"%|L(?:/min|/s|/h)?|g(?:/cm3|/L)?|kg(?:/h)?|m/s)\b", re.I)
FALSIFY = re.compile(
    r"falsif\w*|kill condition|refuted if|disconfirm\w*|"
    r"falsification test", re.I)
CALC = re.compile(r"=\s*-?\d|\bcalculat\w*|\bsubstitut\w*|"
                  r"governing relation", re.I)

rows = []
for f in sorted(OUT.glob("v17-*.json")):
    d = json.loads(f.read_text())
    ans = d["a1_answer"]
    fm = d["final_meta"] or {}
    rf = fm.get("residual_findings") or {}
    gq = fm.get("generic_quant") or {}
    # the gate recompute (typed): the at-run gate was under-informed
    # (classify leaves selected_mech_class empty); the screen carries
    # the corrected verdict computed from the SAME committed bytes —
    # the row's committed gate stays untouched (Art. 4)
    from discovery_fabric.generation import novelty_gate as ng
    sk = (d["engine_trace"]["strength_kit"])
    sel_re = type("S", (), {"selected_mech_class": sk.get(
        "engine_prediction_mech_class") or (sk.get(
            "allowed_mech_classes") or [""])[0], "cross_domain": "",
        "off_target": False, "off_target_reason": ""})()
    gate2 = ng.gate(ans, sel_re)
    rows.append({
        "problem_id": d["problem_id"],
        "failure_class": (d["engine_trace"]["strength_kit"]
                          ["failure_class"]),
        "engine_prediction_status": (d["engine_trace"]["strength_kit"]
                                     ["engine_prediction_status"]),
        "required_inputs_n": len((d["engine_trace"]["strength_kit"]
                                  .get("engine_prediction_inputs")
                                  or [])) if False else None,
        "generic_quant_status": gq.get("status"),
        "generic_quant_computed": gq.get("status") == "computed",
        "novelty_gate": (fm.get("novelty_gate") or {}).get("novelty"),
        "novelty_gate_screen": gate2.get("novelty"),
        "novelty_reject": (fm.get("novelty_gate") or {}).get("reject"),
        "quant_test_missing": "QUANT_TEST_MISSING" in rf,
        "physics_magnitude_missing": ("PHYSICS_MAGNITUDE_MISSING" in rf),
        "off_target": "OFF_TARGET_MECHANISM" in rf,
        "has_numeric_unit": bool(NUM_UNIT.search(ans)),
        "has_worked_calc": bool(CALC.search(ans)),
        "has_kill_condition": bool(FALSIFY.search(ans)),
        "chars": len(ans),
        "sha256_16": d["sha256_16"],
    })

n = len(rows)
rec = {
    "record": "V17_SEALED_BUILDER_SCREEN/1.0.0",
    "at": "2026-11-24 (sandbox clock)",
    "executor": "builder-r145s1@holdout-v17-sealed-generation",
    "run": "holdout-v17-sealed-generation (the SEALED one-shot, the "
           "full strength kit; the V111 prereg)",
    "n": n,
    "dir3_acceptance_surface": {
        "numeric_with_unit": sum(1 for r in rows if r["has_numeric_unit"]),
        "worked_calculation": sum(1 for r in rows if r["has_worked_calc"]),
        "kill_condition_or_falsification_test": sum(
            1 for r in rows if r["has_kill_condition"]),
        "QUANT_TEST_MISSING_count": sum(
            1 for r in rows if r["quant_test_missing"]),
        "generic_quant_computed": sum(
            1 for r in rows if r["generic_quant_computed"]),
        "generic_quant_statuses": dict(Counter(
            r["generic_quant_status"] for r in rows)),
        "note": ("the R144-F1 acceptance: 30/30 carry a falsifiable "
                 "prediction; the machine scan QUANT_TEST_MISSING = "
                 "0 required; the generic-quant layer records the "
                 "computed-coverage per row"),
    },
    "kit_wiring_surface": {
        "class_routing": dict(Counter(r["failure_class"] for r in rows)),
        "off_target_fires": sum(1 for r in rows if r["off_target"]),
        "novelty_gate_at_run": dict(Counter(
            r["novelty_gate"] for r in rows)),
        "novelty_gate_screen_recomputed": dict(Counter(
            r["novelty_gate_screen"] for r in rows)),
    },
    "per_row": rows,
    "honest_typing": {
        "scoring": "PENDING-AUDITOR-SCORE — the seal + rubrics "
                   "(1db1539e935038db) + scoring stay the AUDITOR's "
                   "act (Art. 7/10/14); the builder never scores "
                   "itself",
        "gate": "mean>=3.3 AND CI lower>3.0 AND >=30% strong AND 0 "
                "off-target AND 0/0/0 — NOT computed here",
    },
}
out = REPO / "eval" / "holdout_v17_sealed_screen.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print(json.dumps({k: rec[k] for k in
                  ("n", "dir3_acceptance_surface",
                   "kit_wiring_surface")}, indent=1))
