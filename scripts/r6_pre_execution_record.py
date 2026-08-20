#!/usr/bin/env python3
"""
R6 V22.1 — Pre-Execution Record (NOT a new protocol version)

Per CEO v30.26:
  "STOP CODING. Another software iteration risks becoming
   productive-looking avoidance of reality."

  "The next breakthrough will not come from another clever software
   abstraction. It will come from confronting the invention with
   reality and refusing to explain away the result."

This is NOT a new protocol version. It is the PRE-EXECUTION RECORD:
  1. Acknowledged limitations (2 CEO-identified issues, recorded, not fixed)
  2. EXP-R6-01 execution checklist (what to do before first measurement)
  3. Per-prototype result schema (preserves individual data, no aggregation erasure)
  4. Single-lot limitation declaration

NO THRESHOLD CHANGES. NO PROTOCOL REDESIGN. NO MODEL TUNING.
This record ACKNOWLEDGES limitations and PREPARES for execution.
"""
import json
import random
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def pre_execution_record():
    # Generate randomized test order (seed=42, frozen before testing)
    random.seed(42)
    test_order = random.sample(range(1, 21), 20)

    return {
        "task_id": "R6-V22.1-PRE-EXECUTION-RECORD",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "STOP CODING. Execute EXP-R6-01 exactly as frozen. "
                         "Confront the invention with reality.",
        "status": "PRE_EXECUTION — this is NOT a new protocol version. "
                  "It is the execution preparation record.",

        "acknowledged_limitations": {
            "limitation_1_metric_specific_promotion": {
                "issue": "The V22 ontology implies one universal promotion threshold "
                         "(>1/20) for prototype → embodiment. But hysteresis or drift "
                         "can be problematic at the individual-valve level even if the "
                         "aggregate opening-pressure failure rate is acceptable.",
                "acknowledged": True,
                "resolution": "The per-prototype result schema (below) preserves "
                              "INDIVIDUAL prototype results for EVERY metric. The "
                              "embodiment-level decision uses METRIC-SPECIFIC "
                              "thresholds from V21.5 (not a single universal threshold). "
                              "The >1/20 rule applies ONLY to opening pressure. "
                              "Hysteresis uses median > 15 mmHg. Repeatability uses "
                              "any valve CV > 20%. Drift uses any valve > -15 mmHg. "
                              "These are DIFFERENT promotion rules for DIFFERENT metrics.",
                "what_we_will_NOT_do": "We will NOT redesign the protocol to fix this. "
                                        "The V21.5 metric-specific thresholds already "
                                        "handle this correctly. The V22 ontology "
                                        "description was imprecise but the actual "
                                        "threshold table (V21.5) is metric-specific.",
            },
            "limitation_2_single_lot": {
                "issue": "All 20 prototypes are from one fabrication lot. Results "
                         "cannot support a manufacturing-generalization claim. "
                         "Lot-to-lot variation is unknown.",
                "acknowledged": True,
                "declaration": "EXP-R6-01 tests 20 prototypes from ONE fabrication "
                               "lot (LOT-{fabrication_date}-001). This establishes "
                               "ENGINEERING FEASIBILITY of the slit valve embodiment. "
                               "It does NOT establish manufacturing process capability. "
                               "Manufacturing capability requires n=100+ from 3+ lots "
                               "(EXP-R6-01b, future, separate pre-registration). "
                               "Any dossier claim based on EXP-R6-01 MUST state: "
                               "'20 prototypes from one fabrication lot.'",
                "what_we_will_NOT_do": "We will NOT claim manufacturing capability "
                                        "from this experiment.",
            },
        },

        "execution_checklist": {
            "before_first_measurement": [
                {
                    "step": 1,
                    "action": "Record exact prototype IDs and fabrication lot",
                    "fields": [
                        "lot_id: LOT-{YYYYMMDD}-001",
                        "prototype_ids: P01 through P20",
                        "material_batch_number",
                        "machine_id",
                        "tool_revision",
                        "molding_temperature",
                        "cycle_time",
                        "operator_id",
                    ],
                    "status": "PENDING — record when prototypes arrive",
                },
                {
                    "step": 2,
                    "action": "Record instrument calibration and positive-control result",
                    "fields": [
                        "pressure_transducer_id + calibration_date + NIST_traceability",
                        "flow_meter_id + calibration_date + gravimetric_verification",
                        "temperature_bath_id + calibration_date",
                        "positive_control: Medtronic Strata NSC, serial_number, "
                        "IFU_specified_opening_pressure, measured_opening_pressure, "
                        "pass: measured within ±2 mmHg of IFU spec",
                    ],
                    "status": "PENDING — perform before first prototype test",
                    "if_positive_control_fails": "INCONCLUSIVE — recalibrate and repeat. "
                                                 "Do NOT test prototypes with uncalibrated apparatus.",
                },
                {
                    "step": 3,
                    "action": "Hash/freeze the analysis and pass/fail scripts",
                    "fields": [
                        "analysis_script_path: scripts/r6_analyze_exp01.py",
                        "analysis_script_hash: SHA-256 of the script file, computed BEFORE first test",
                        "pass_fail_script_hash: SHA-256 of the decision logic, computed BEFORE first test",
                    ],
                    "status": "PENDING — write and hash scripts before testing",
                    "rule": "Scripts CANNOT be modified after testing begins (Article VII). "
                            "Any modification invalidates the experiment.",
                },
                {
                    "step": 4,
                    "action": "Generate and record the randomized test order",
                    "test_order": test_order,
                    "seed": 42,
                    "method": "Python random.seed(42); random.sample(range(1,21), 20)",
                    "status": "FROZEN — test order is pre-generated and recorded above",
                },
                {
                    "step": 5,
                    "action": "Capture raw measurements BEFORE interpretation",
                    "rule": "Record ALL raw data (pressure, flow, temperature, timestamp, "
                            "operator, instrument) in the pre-registered JSON schema. "
                            "Do NOT analyze or interpret until ALL 20 prototypes are tested. "
                            "Do NOT stop testing early if early results look bad (Article XV: "
                            "disclose inconvenient results).",
                    "status": "PENDING — execute after steps 1-4",
                },
            ],
        },

        "per_prototype_result_schema": {
            "description": "Every prototype gets an INDIVIDUAL result record. "
                           "Individual failures are NOT erased by aggregation. "
                           "The embodiment-level decision uses metric-specific "
                           "thresholds from V21.5.",
            "schema": {
                "prototype_id": "string (P01-P20)",
                "test_order": "integer (from randomized sequence above)",
                "operator_id": "string (coded)",
                "instrument_ids": {
                    "pressure_transducer": "string",
                    "flow_meter": "string",
                    "temperature_bath": "string",
                },
                "calibration_verified": "boolean (positive control passed before this prototype)",
                "measurements": {
                    "opening_pressure": {
                        "cycle_1_mmhg": "float",
                        "cycle_2_mmhg": "float",
                        "cycle_3_mmhg": "float",
                        "median_mmhg": "float",
                        "cv_pct": "float",
                        "in_15_30_range": "boolean",
                        "in_20_25_median": "boolean",
                    },
                    "hysteresis": {
                        "opening_pressure_mmhg": "float",
                        "closing_pressure_mmhg": "float",
                        "loop_width_mmhg": "float",
                        "pass": "boolean (< 10)",
                        "conditional": "boolean (10-15)",
                        "fail": "boolean (> 15)",
                    },
                    "repeatability": {
                        "cv_pct": "float",
                        "pass": "boolean (< 10%)",
                        "conditional": "boolean (10-20%)",
                        "fail": "boolean (> 20%)",
                    },
                    "drift": {
                        "initial_opening_mmhg": "float",
                        "after_100_cycles_mmhg": "float",
                        "drift_mmhg": "float (negative = loosened)",
                        "pass": "boolean (-5 to +5)",
                        "conditional": "boolean (-5 to -10)",
                        "fail": "boolean (> -10 or broke)",
                        "broke_before_100": "boolean (if true → FAIL)",
                    },
                },
                "individual_result": "PASS | CONDITIONAL | FAIL | INCONCLUSIVE",
                "anomalies": "string (free text for any observed anomalies)",
                "timestamp": "ISO datetime",
            },
            "aggregation_rule": ("The embodiment-level decision is made by applying "
                                "METRIC-SPECIFIC thresholds (V21.5) to the POPULATION "
                                "of individual results. Different metrics have different "
                                "aggregation rules: "
                                "- opening_pressure: count-based (>1/20 outside range = FAIL); "
                                "- hysteresis: median-based (median >15 = FAIL); "
                                "- repeatability: any-valve (any CV >20% = FAIL); "
                                "- drift: any-valve (any >-15 or broke = FAIL). "
                                "Individual prototype failures are PRESERVED in the data "
                                "and REPORTED, not erased by aggregation."),
        },

        "single_lot_declaration": {
            "statement": "EXP-R6-01 uses 20 prototypes from ONE fabrication lot "
                         "(LOT-{fabrication_date}-001). This establishes engineering "
                         "FEASIBILITY only. Manufacturing process capability is NOT "
                         "established. Lot-to-lot variation is UNKNOWN. Any claim "
                         "based on EXP-R6-01 results MUST include: '20 prototypes "
                         "from one fabrication lot.'",
            "applies_to": "ALL results, interpretations, and claims derived from EXP-R6-01.",
            "does_not_apply_to": "Future EXP-R6-01b (manufacturing capability test, "
                                  "n=100+, 3+ lots, separate pre-registration).",
        },

        "execution_principles": {
            "principle_1": "Record raw measurements BEFORE interpretation.",
            "principle_2": "Preserve individual prototype results. Do not use aggregate "
                           "results to erase individual failures.",
            "principle_3": "Do not redesign a prototype after seeing data.",
            "principle_4": "Do not change thresholds (Article VII).",
            "principle_5": "Do not tune the model (Article VII).",
            "principle_6": "If the embodiment fails, STOP and write the failure report "
                           "before designing embodiment #2.",
            "principle_7": "Report results at the EMBODIMENT level (V22 ontology). "
                           "A slit-valve failure is NOT a mechanism failure.",
            "principle_8": "Report ALL data including failures (Article XV).",
        },

        "final_statement": {
            "date": datetime.now(timezone.utc).isoformat(),
            "text": "We are done preparing. Now we need data. "
                    "The next action is PHYSICAL: fabricate, calibrate, test, record, "
                    "interpret, report. No more software iterations.",
            "stop_coding": True,
            "next_action": "FABRICATE 20 PROTOTYPES AND EXECUTE EXP-R6-01",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V22.1 — PRE-EXECUTION RECORD (NOT a new protocol version)")
    print("We are done preparing. Now we need data.")
    print("=" * 78)

    results = pre_execution_record()

    print("\nACKNOWLEDGED LIMITATIONS:")
    for key, lim in results["acknowledged_limitations"].items():
        print(f"\n  {key}")
        print(f"    Issue: {lim['issue'][:100]}...")
        print(f"    Acknowledged: {lim['acknowledged']}")

    print("\nEXECUTION CHECKLIST:")
    for step in results["execution_checklist"]["before_first_measurement"]:
        print(f"\n  Step {step['step']}: {step['action']}")
        print(f"    Status: {step['status']}")

    print(f"\n  RANDOMIZED TEST ORDER (seed=42, FROZEN):")
    print(f"    {results['execution_checklist']['before_first_measurement'][3]['test_order']}")

    print("\nPER-PROTOTYPE RESULT SCHEMA:")
    schema = results["per_prototype_result_schema"]["schema"]
    print(f"  Fields: {list(schema.keys())}")
    print(f"  Measurements: {list(schema['measurements'].keys())}")
    print(f"  Aggregation: {results['per_prototype_result_schema']['aggregation_rule'][:100]}...")

    print(f"\nSINGLE-LOT DECLARATION:")
    print(f"  {results['single_lot_declaration']['statement'][:150]}...")

    print(f"\n{'='*78}")
    print(f"FINAL: {results['final_statement']['text']}")
    print(f"STOP CODING: {results['final_statement']['stop_coding']}")
    print(f"NEXT: {results['final_statement']['next_action']}")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_1_R6_PRE_EXECUTION_RECORD.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
