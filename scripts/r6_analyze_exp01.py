#!/usr/bin/env python3
"""
R6 EXP-R6-01 Analysis Script — FROZEN BEFORE DATA COLLECTION

Per CEO v30.28 + Article VII + Article XXVI:
  This script is written, hashed, and committed BEFORE any prototype is tested.
  It CANNOT be modified after testing begins.
  Any modification invalidates the experiment (Article VII).

This script:
  1. Loads raw measurement data from EXP-R6-01
  2. Computes per-prototype results (individual, not aggregated)
  3. Applies the FROZEN V21.5 metric-specific thresholds
  4. Applies the FROZEN V21.7 causal decision hierarchy
  5. Produces an embodiment-level decision

Usage:
  python scripts/r6_analyze_exp01.py <raw_data_file.json>

Output:
  V22_2_R6_EXP01_RESULTS.json (per-prototype results + embodiment decision)

SHA-256 of this script is recorded in the execution artifact BEFORE testing.
The script validates raw data BEFORE analysis. Bad data → INCONCLUSIVE, never silent skip.
The final result binds: raw_data_sha256 + analysis_script_sha256 + constitution_hash.
"""
import json
import sys
import hashlib
import statistics
from pathlib import Path
from datetime import datetime, timezone

# Expected prototype count
EXPECTED_PROTOTYPE_COUNT = 20
EXPECTED_PROTOTYPE_IDS = {f"P{i:02d}" for i in range(1, 21)}


# ===========================================================================
# FROZEN THRESHOLDS (from V21.5 — NO GAPS, NO POST-HOC CHANGES)
# ===========================================================================

THRESHOLDS = {
    "opening_pressure": {
        "pass_range": (15, 30),      # mmHg
        "pass_median_range": (20, 25), # mmHg
        "max_failures": 1,            # >1/20 outside range = FAIL
        "category": "ENGINEERING_DEFICIENCY",  # V21.7 causal hierarchy
    },
    "hysteresis": {
        "pass_max": 10,               # mmHg (median < 10 = PASS)
        "conditional_max": 15,        # mmHg (10-15 = CONDITIONAL)
        "fail_above": 15,             # mmHg (> 15 = FAIL)
        "aggregation": "median",
        "category": "CLINICAL_BUYER_TRADEOFF",
    },
    "repeatability": {
        "pass_max_cv": 10,            # % (all valves < 10% = PASS)
        "conditional_max_cv": 20,     # % (1-3 valves 10-20% = CONDITIONAL)
        "fail_above_cv": 20,          # % (any valve > 20% = FAIL)
        "aggregation": "any_valve",
        "category": "ENGINEERING_DEFICIENCY",
    },
    "drift": {
        "pass_range": (-5, 5),        # mmHg (median -5 to +5 = PASS)
        "conditional_range": (-10, -5), # mmHg (median -5 to -10 = CONDITIONAL)
        "fail_below": -10,            # mmHg (median > -10 downward = FAIL)
        "any_valve_fail": -15,        # mmHg (any valve > -15 = FAIL)
        "broke_before_100": "FAIL",   # valve breaks = FAIL (treat as FAIL not INCONCLUSIVE)
        "aggregation": "median_and_any",
        "category": "ENGINEERING_DEFICIENCY",
    },
}

DECISION_HIERARCHY = {
    "HARD_KILL": "NONE in initial protocol (V21.7). Only after design-space exhaustion.",
    "PROVISIONAL_ENGINEERING_FLOOR": "flow < 0.05 mL/min (EXP-R6-02, not EXP-R6-01)",
    "ENGINEERING_DEFICIENCY": "Implementation needs redesign. Invention survives.",
    "CLINICAL_BUYER_TRADEOFF": "Buyer interprets against clinical requirements.",
}


# ===========================================================================
# RAW-DATA VALIDATION (bad data → INCONCLUSIVE, never silent skip)
# ===========================================================================

def validate_raw_data(raw_data: dict) -> tuple:
    """Validate raw data BEFORE analysis. Returns (is_valid, errors).

    Per CEO v30.29: "Bad data must produce INCONCLUSIVE, not a plausible-looking result."
    The script must never silently discard malformed records, missing measurements,
    duplicate IDs, unexpected counts, or modified schema fields.
    """
    errors = []

    # 1. Check prototype count
    prototypes = raw_data.get("prototypes", [])
    if len(prototypes) != EXPECTED_PROTOTYPE_COUNT:
        errors.append(f"WRONG_PROTOTYPE_COUNT: expected {EXPECTED_PROTOTYPE_COUNT}, "
                      f"got {len(prototypes)}")

    # 2. Check for duplicate prototype IDs
    proto_ids = [p.get("prototype_id", "") for p in prototypes]
    seen_ids = set()
    dup_ids = []
    for pid in proto_ids:
        if pid in seen_ids:
            dup_ids.append(pid)
        seen_ids.add(pid)
    if dup_ids:
        errors.append(f"DUPLICATE_PROTOTYPE_IDS: {dup_ids}")

    # 3. Check for unexpected prototype IDs
    actual_ids = set(proto_ids)
    unexpected = actual_ids - EXPECTED_PROTOTYPE_IDS
    missing = EXPECTED_PROTOTYPE_IDS - actual_ids
    if unexpected:
        errors.append(f"UNEXPECTED_PROTOTYPE_IDS: {unexpected}")
    if missing:
        errors.append(f"MISSING_PROTOTYPE_IDS: {missing}")

    # 4. Check each prototype has required measurements
    required_measurements = ["opening_pressure", "hysteresis", "repeatability", "drift"]
    for proto in prototypes:
        pid = proto.get("prototype_id", "UNKNOWN")
        measurements = proto.get("measurements", {})

        for req in required_measurements:
            if req not in measurements:
                errors.append(f"MISSING_MEASUREMENT: {pid} missing '{req}'")
                continue

            m = measurements[req]

            # Check opening_pressure has at least 2 cycles
            if req == "opening_pressure":
                cycles = [m.get("cycle_1_mmhg"), m.get("cycle_2_mmhg"), m.get("cycle_3_mmhg")]
                valid_cycles = [c for c in cycles if c is not None]
                if len(valid_cycles) < 2:
                    errors.append(f"INSUFFICIENT_CYCLES: {pid} has {len(valid_cycles)} cycles (need >=2)")

                # Check for impossible values
                for c in valid_cycles:
                    if c is not None and (c < 0 or c > 100):
                        errors.append(f"IMPOSSIBLE_VALUE: {pid} opening_pressure cycle = {c} mmHg (must be 0-100)")

            # Check hysteresis has loop_width
            if req == "hysteresis":
                lw = m.get("loop_width_mmhg")
                if lw is not None and (lw < 0 or lw > 100):
                    errors.append(f"IMPOSSIBLE_VALUE: {pid} hysteresis loop_width = {lw} mmHg (must be 0-100)")

            # Check drift values
            if req == "drift":
                d = m.get("drift_mmhg")
                if d is not None and (d < -50 or d > 50):
                    errors.append(f"IMPOSSIBLE_VALUE: {pid} drift = {d} mmHg (must be -50 to +50)")

        # 5. Check calibration confirmation
        if not proto.get("calibration_verified", False):
            errors.append(f"CALIBRATION_NOT_VERIFIED: {pid} calibration_verified is False or missing")

    # 6. Check for schema changes (unexpected top-level keys)
    expected_top_keys = {"prototypes", "metadata", "experiment_id"}
    actual_top_keys = set(raw_data.keys())
    unexpected_keys = actual_top_keys - expected_top_keys - {"raw_data_sha256"}
    # Note: extra keys are warnings, not errors — but we log them
    if unexpected_keys:
        errors.append(f"UNEXPECTED_SCHEMA_KEYS: {unexpected_keys} (may indicate schema drift)")

    return (len(errors) == 0, errors)


# ===========================================================================
# PER-PROTOTYPE ANALYSIS
# ===========================================================================

def analyze_prototype(proto_data: dict) -> dict:
    """Analyze a single prototype's raw measurements.

    Returns per-prototype result with metric-specific PASS/CONDITIONAL/FAIL.
    Individual results are PRESERVED — not erased by aggregation.
    """
    pid = proto_data.get("prototype_id", "UNKNOWN")
    result = {
        "prototype_id": pid,
        "individual_result": "UNKNOWN",
        "metrics": {},
    }

    # --- Opening Pressure ---
    op = proto_data.get("measurements", {}).get("opening_pressure", {})
    cycles = [op.get("cycle_1_mmhg"), op.get("cycle_2_mmhg"), op.get("cycle_3_mmhg")]
    cycles_valid = [c for c in cycles if c is not None]

    if len(cycles_valid) >= 2:
        median_op = statistics.median(cycles_valid)
        mean_op = statistics.mean(cycles_valid)
        if len(cycles_valid) > 1:
            stdev_op = statistics.stdev(cycles_valid)
            cv_op = (stdev_op / abs(mean_op) * 100) if mean_op != 0 else 0
        else:
            cv_op = 0

        in_range = THRESHOLDS["opening_pressure"]["pass_range"][0] <= median_op <= THRESHOLDS["opening_pressure"]["pass_range"][1]
        median_in_target = THRESHOLDS["opening_pressure"]["pass_median_range"][0] <= median_op <= THRESHOLDS["opening_pressure"]["pass_median_range"][1]

        result["metrics"]["opening_pressure"] = {
            "median_mmhg": round(median_op, 1),
            "mean_mmhg": round(mean_op, 1),
            "cv_pct": round(cv_op, 1),
            "in_15_30_range": in_range,
            "median_in_20_25": median_in_target,
            "individual_pass": in_range,
            "individual_fail": not in_range,
        }
    else:
        result["metrics"]["opening_pressure"] = {"individual_result": "INCONCLUSIVE", "reason": "insufficient cycles"}

    # --- Hysteresis ---
    hys = proto_data.get("measurements", {}).get("hysteresis", {})
    loop_width = hys.get("loop_width_mmhg")

    if loop_width is not None:
        if loop_width < THRESHOLDS["hysteresis"]["pass_max"]:
            hys_result = "PASS"
        elif loop_width <= THRESHOLDS["hysteresis"]["fail_above"]:
            hys_result = "CONDITIONAL"
        else:
            hys_result = "FAIL"
        result["metrics"]["hysteresis"] = {
            "loop_width_mmhg": round(loop_width, 1),
            "individual_result": hys_result,
        }
    else:
        result["metrics"]["hysteresis"] = {"individual_result": "INCONCLUSIVE"}

    # --- Repeatability (uses CV from opening pressure cycles) ---
    if len(cycles_valid) >= 2 and cv_op is not None:
        if cv_op < THRESHOLDS["repeatability"]["pass_max_cv"]:
            rep_result = "PASS"
        elif cv_op <= THRESHOLDS["repeatability"]["fail_above_cv"]:
            rep_result = "CONDITIONAL"
        else:
            rep_result = "FAIL"
        result["metrics"]["repeatability"] = {
            "cv_pct": round(cv_op, 1),
            "individual_result": rep_result,
        }
    else:
        result["metrics"]["repeatability"] = {"individual_result": "INCONCLUSIVE"}

    # --- Drift ---
    drift = proto_data.get("measurements", {}).get("drift", {})
    broke = drift.get("broke_before_100", False)

    if broke:
        result["metrics"]["drift"] = {
            "broke_before_100": True,
            "individual_result": "FAIL",
            "note": "Valve broke before 100 cycles — treat as FAIL (V21.5)",
        }
    else:
        drift_val = drift.get("drift_mmhg")
        if drift_val is not None:
            if THRESHOLDS["drift"]["pass_range"][0] <= drift_val <= THRESHOLDS["drift"]["pass_range"][1]:
                drift_result = "PASS"
            elif drift_val > THRESHOLDS["drift"]["fail_below"] and drift_val < THRESHOLDS["drift"]["pass_range"][0]:
                drift_result = "CONDITIONAL"
            else:
                drift_result = "FAIL"
            result["metrics"]["drift"] = {
                "drift_mmhg": round(drift_val, 1),
                "individual_result": drift_result,
            }
        else:
            result["metrics"]["drift"] = {"individual_result": "INCONCLUSIVE"}

    # --- Individual prototype result ---
    metric_results = []
    for m in ["opening_pressure", "hysteresis", "repeatability", "drift"]:
        r = result["metrics"].get(m, {}).get("individual_result")
        if r is None:
            # opening_pressure uses in_range/not in_range
            op_metric = result["metrics"].get("opening_pressure", {})
            if op_metric.get("individual_fail"):
                metric_results.append("FAIL")
            elif op_metric.get("individual_pass"):
                metric_results.append("PASS")
            else:
                metric_results.append("INCONCLUSIVE")
        else:
            metric_results.append(r)

    if "FAIL" in metric_results:
        result["individual_result"] = "FAIL"
    elif "INCONCLUSIVE" in metric_results:
        result["individual_result"] = "INCONCLUSIVE"
    elif "CONDITIONAL" in metric_results:
        result["individual_result"] = "CONDITIONAL"
    else:
        result["individual_result"] = "PASS"

    return result


# ===========================================================================
# EMBODIMENT-LEVEL AGGREGATION (metric-specific, V21.5)
# ===========================================================================

def aggregate_embodiment_decision(proto_results: list) -> dict:
    """Aggregate per-prototype results into embodiment-level decision.

    Uses METRIC-SPECIFIC aggregation rules (V21.5):
      - opening_pressure: count-based (>1/20 outside range = FAIL)
      - hysteresis: median-based (median >15 = FAIL)
      - repeatability: any-valve (any CV >20% = FAIL)
      - drift: any-valve (any >-15 or broke = FAIL) + median-based
    """
    n = len(proto_results)
    decision = {
        "n_prototypes": n,
        "metric_decisions": {},
        "overall_decision": "UNKNOWN",
        "decision_hierarchy": DECISION_HIERARCHY,
    }

    # --- Opening Pressure (count-based) ---
    op_fails = sum(1 for p in proto_results
                   if p.get("metrics", {}).get("opening_pressure", {}).get("individual_fail"))
    op_medians = [p["metrics"]["opening_pressure"]["median_mmhg"]
                  for p in proto_results
                  if "median_mmhg" in p.get("metrics", {}).get("opening_pressure", {})]

    if op_medians:
        pop_median = statistics.median(op_medians)
        op_median_in_target = 20 <= pop_median <= 25
    else:
        pop_median = None
        op_median_in_target = False

    op_pass = (op_fails <= THRESHOLDS["opening_pressure"]["max_failures"]) and op_median_in_target
    op_fail = (op_fails > THRESHOLDS["opening_pressure"]["max_failures"]) or not op_median_in_target

    decision["metric_decisions"]["opening_pressure"] = {
        "n_outside_range": op_fails,
        "max_allowed": THRESHOLDS["opening_pressure"]["max_failures"],
        "population_median_mmhg": round(pop_median, 1) if pop_median else None,
        "median_in_20_25": op_median_in_target,
        "result": "PASS" if op_pass else ("FAIL" if op_fail else "INCONCLUSIVE"),
        "category": THRESHOLDS["opening_pressure"]["category"],
    }

    # --- Hysteresis (median-based) ---
    hys_widths = [p["metrics"]["hysteresis"]["loop_width_mmhg"]
                  for p in proto_results
                  if "loop_width_mmhg" in p.get("metrics", {}).get("hysteresis", {})]

    if hys_widths:
        hys_median = statistics.median(hys_widths)
        if hys_median < THRESHOLDS["hysteresis"]["pass_max"]:
            hys_result = "PASS"
        elif hys_median <= THRESHOLDS["hysteresis"]["fail_above"]:
            hys_result = "CONDITIONAL"
        else:
            hys_result = "FAIL"
    else:
        hys_median = None
        hys_result = "INCONCLUSIVE"

    decision["metric_decisions"]["hysteresis"] = {
        "median_loop_width_mmhg": round(hys_median, 1) if hys_median else None,
        "result": hys_result,
        "category": THRESHOLDS["hysteresis"]["category"],
    }

    # --- Repeatability (any-valve) ---
    rep_cvs = [p["metrics"]["repeatability"]["cv_pct"]
               for p in proto_results
               if "cv_pct" in p.get("metrics", {}).get("repeatability", {})]
    n_rep_fail = sum(1 for cv in rep_cvs if cv > THRESHOLDS["repeatability"]["fail_above_cv"])
    n_rep_cond = sum(1 for cv in rep_cvs
                     if THRESHOLDS["repeatability"]["pass_max_cv"] < cv <= THRESHOLDS["repeatability"]["fail_above_cv"])

    if n_rep_fail > 0:
        rep_result = "FAIL"
    elif n_rep_cond > 3:
        rep_result = "FAIL"  # more than 3 valves in CONDITIONAL = treat as FAIL
    elif n_rep_cond > 0:
        rep_result = "CONDITIONAL"
    else:
        rep_result = "PASS"

    decision["metric_decisions"]["repeatability"] = {
        "n_fail": n_rep_fail,
        "n_conditional": n_rep_cond,
        "max_cv_pct": round(max(rep_cvs), 1) if rep_cvs else None,
        "result": rep_result,
        "category": THRESHOLDS["repeatability"]["category"],
    }

    # --- Drift (any-valve + median) ---
    drift_vals = [p["metrics"]["drift"]["drift_mmhg"]
                  for p in proto_results
                  if "drift_mmhg" in p.get("metrics", {}).get("drift", {})]
    n_broke = sum(1 for p in proto_results
                  if p.get("metrics", {}).get("drift", {}).get("broke_before_100"))
    n_drift_fail = sum(1 for d in drift_vals if d < THRESHOLDS["drift"]["any_valve_fail"])

    if n_broke > 0 or n_drift_fail > 0:
        drift_result = "FAIL"
    elif drift_vals:
        drift_median = statistics.median(drift_vals)
        if THRESHOLDS["drift"]["pass_range"][0] <= drift_median <= THRESHOLDS["drift"]["pass_range"][1]:
            drift_result = "PASS"
        elif drift_median > THRESHOLDS["drift"]["fail_below"]:
            drift_result = "CONDITIONAL"
        else:
            drift_result = "FAIL"
    else:
        drift_median = None
        drift_result = "INCONCLUSIVE"

    decision["metric_decisions"]["drift"] = {
        "n_broke": n_broke,
        "n_any_valve_fail": n_drift_fail,
        "median_drift_mmhg": round(drift_median, 1) if drift_vals else None,
        "result": drift_result,
        "category": THRESHOLDS["drift"]["category"],
    }

    # --- Overall embodiment decision (V21.7 causal hierarchy) ---
    all_results = [m["result"] for m in decision["metric_decisions"].values()]

    if "FAIL" in all_results:
        # Check if opening_pressure is FAIL (would be ENGINEERING_DEFICIENCY)
        op_result = decision["metric_decisions"]["opening_pressure"]["result"]
        if op_result == "FAIL":
            decision["overall_decision"] = "FAIL — ENGINEERING_DEFICIENCY: slit valve embodiment fails opening pressure. Try next mechanism (new pre-registration)."
        else:
            # Secondary metric FAIL — check category
            failing_metrics = [m for m, d in decision["metric_decisions"].items() if d["result"] == "FAIL"]
            categories = [decision["metric_decisions"][m]["category"] for m in failing_metrics]
            if "ENGINEERING_DEFICIENCY" in categories:
                decision["overall_decision"] = "FAIL — ENGINEERING_DEFICIENCY: secondary metric(s) fail. Redesign required."
            elif "CLINICAL_BUYER_TRADEOFF" in categories:
                decision["overall_decision"] = "FAIL — CLINICAL_BUYER_TRADEOFF: buyer must assess."
            else:
                decision["overall_decision"] = "FAIL — see metric details."
    elif "INCONCLUSIVE" in all_results:
        decision["overall_decision"] = "INCONCLUSIVE — calibration or data issue. Repeat affected measurements."
    elif "CONDITIONAL" in all_results:
        decision["overall_decision"] = "CONDITIONAL_PASS — opening pressure passes but secondary metric(s) are CONDITIONAL. Documented assessment required."
    else:
        decision["overall_decision"] = "PASS — all metrics pass. Proceed to EXP-R6-02 (flow-response curve)."

    return decision


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/r6_analyze_exp01.py <raw_data_file.json>")
        print("  raw_data_file.json: per-prototype raw measurements in V22.1 schema")
        sys.exit(1)

    raw_file = Path(sys.argv[1])
    if not raw_file.exists():
        print(f"ERROR: raw data file not found: {raw_file}")
        sys.exit(1)

    # Compute raw data SHA-256 BEFORE loading (cryptographic binding)
    raw_bytes = raw_file.read_bytes()
    raw_data_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    with open(raw_file) as f:
        raw_data = json.load(f)

    # === RAW-DATA VALIDATION (before any analysis) ===
    is_valid, validation_errors = validate_raw_data(raw_data)
    if not is_valid:
        print(f"\n{'='*78}")
        print("RAW-DATA VALIDATION FAILED — INCONCLUSIVE")
        print(f"{'='*78}")
        for err in validation_errors:
            print(f"  ERROR: {err}")
        print(f"\nThe experiment is INCONCLUSIVE due to raw-data validation failures.")
        print(f"Bad data must produce INCONCLUSIVE, not a plausible-looking result.")
        print(f"Do NOT proceed with analysis. Fix the data collection issue and re-run.")

        # Still produce a result file — but it's INCONCLUSIVE
        output = {
            "task_id": "R6-EXP01-RESULTS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_data_sha256": raw_data_sha256,
            "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "result_scope": "EMBODIMENT_LEVEL",
            "overall_decision": "INCONCLUSIVE — raw-data validation failed",
            "validation_errors": validation_errors,
            "per_prototype_results": [],
            "embodiment_decision": {"overall_decision": "INCONCLUSIVE — data validation failure"},
        }
        output_path = Path(__file__).parent.parent / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_2_R6_EXP01_RESULTS.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nINCONCLUSIVE result saved to: {output_path}")
        sys.exit(1)

    print(f"Raw-data validation: PASSED ({len(validation_errors)} errors)")

    prototypes = raw_data.get("prototypes", [])
    if not prototypes:
        print("ERROR: no prototype data found in raw data file")
        sys.exit(1)

    print(f"Analyzing {len(prototypes)} prototypes...")

    # Per-prototype analysis
    proto_results = []
    for proto in prototypes:
        result = analyze_prototype(proto)
        proto_results.append(result)
        print(f"  {result['prototype_id']}: {result['individual_result']}")

    # Embodiment-level aggregation
    embodiment = aggregate_embodiment_decision(proto_results)

    print(f"\n{'='*78}")
    print("EMBODIMENT-LEVEL DECISION")
    print(f"{'='*78}")
    for metric, decision in embodiment["metric_decisions"].items():
        print(f"  {metric}: {decision['result']} ({decision.get('category', '?')})")
    print(f"\n  OVERALL: {embodiment['overall_decision']}")

    # Cryptographic binding chain
    analysis_script_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    # Output with full cryptographic binding
    output = {
        "task_id": "R6-EXP01-RESULTS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cryptographic_binding": {
            "raw_data_sha256": raw_data_sha256,
            "analysis_script_sha256": analysis_script_sha256,
            "constitution_version": "1.4.0",
            "constitution_hash": "d70e399a8839a237eae013e1bbd3e582998e62b8dc5ef0a65f8afa7f2e65b586",
            "experiment_id": raw_data.get("experiment_id", "EXP-R6-01"),
            "raw_data_file": str(raw_file),
            "binding_statement": "This result is cryptographically bound to: "
                "(1) the exact raw data file (SHA-256 above), "
                "(2) the exact analysis script (SHA-256 above), "
                "(3) the constitution version under which the protocol was frozen. "
                "Any modification to any of these invalidates the result.",
        },
        "raw_data_file": str(raw_file),
        "raw_data_sha256": raw_data_sha256,
        "analysis_script_hash": analysis_script_sha256,
        "result_scope": "EMBODIMENT_LEVEL",
        "embodiment": "Silicone slit valve, 0.25mm bypass radius, 200mm length, concentric",
        "single_lot_declaration": "Results from 20 prototypes from ONE fabrication lot. "
                                  "Engineering feasibility only. Manufacturing capability NOT established.",
        "validation_result": "PASSED" if is_valid else "FAILED",
        "per_prototype_results": proto_results,
        "embodiment_decision": embodiment,
        "interpretation_rule": "These results apply to the [EMBODIMENT: silicone slit valve at 0.25mm]. "
                               "They do NOT constitute evidence about the [MECHANISM: pressure-activated "
                               "flow path] or [CONCEPT: passive bypass lumen] beyond what this specific "
                               "embodiment demonstrates. Failure of this embodiment does not imply "
                               "failure of the mechanism or concept. (V22 ontology)",
    }

    output_path = Path(__file__).parent.parent / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_2_R6_EXP01_RESULTS.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")
    print(f"Analysis script SHA-256: {output['analysis_script_hash']}")


if __name__ == "__main__":
    main()
