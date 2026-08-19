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
"""
import json
import sys
import hashlib
import statistics
from pathlib import Path
from datetime import datetime, timezone


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

    with open(raw_file) as f:
        raw_data = json.load(f)

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

    # Output
    output = {
        "task_id": "R6-EXP01-RESULTS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_script_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "raw_data_file": str(raw_file),
        "result_scope": "EMBODIMENT_LEVEL",
        "embodiment": "Silicone slit valve, 0.25mm bypass radius, 200mm length, concentric",
        "single_lot_declaration": "Results from 20 prototypes from ONE fabrication lot. "
                                  "Engineering feasibility only. Manufacturing capability NOT established.",
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
