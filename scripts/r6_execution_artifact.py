#!/usr/bin/env python3
"""
R6 EXP-R6-01 Execution Artifact — Frozen Before Testing

Per CEO v30.28: Complete the missing execution artifacts.
This is NOT a new protocol version. It is the execution handoff record.

Records:
  1. Analysis script SHA-256 (FROZEN)
  2. PASS/FAIL decision script SHA-256 (FROZEN — same script)
  3. Instrument IDs + calibration template (to be filled when hardware arrives)
  4. Positive-control template (to be filled when Medtronic Strata is tested)
  5. Fabrication lot + P01-P20 template (to be filled when prototypes arrive)
  6. Randomized test order (ALREADY FROZEN from V22.1)
  7. Raw-data storage location + immutable timestamping

After this commit: NO SCRIPT CHANGES. Only physical execution.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent

# Compute hash of the analysis script
analysis_script = (REPO / "scripts" / "r6_analyze_exp01.py").read_bytes()
ANALYSIS_SCRIPT_HASH = hashlib.sha256(analysis_script).hexdigest()

# The analysis script IS the pass/fail decision script (it contains both)
PASS_FAIL_SCRIPT_HASH = ANALYSIS_SCRIPT_HASH


def execution_artifact():
    return {
        "task_id": "R6-EXP01-EXECUTION-ARTIFACT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Complete the missing execution artifacts. Then STOP CODING.",
        "status": "EXECUTION_ARTIFACTS_FROZEN — ready for physical testing",

        "frozen_scripts": {
            "analysis_script": {
                "path": "scripts/r6_analyze_exp01.py",
                "sha256": ANALYSIS_SCRIPT_HASH,
                "frozen_at": datetime.now(timezone.utc).isoformat(),
                "rule": "This script CANNOT be modified after testing begins (Article VII). "
                        "Any modification invalidates the experiment.",
                "what_it_does": [
                    "1. Loads raw measurement data from EXP-R6-01",
                    "2. Computes per-prototype results (individual, not aggregated)",
                    "3. Applies FROZEN V21.5 metric-specific thresholds (no gaps)",
                    "4. Applies FROZEN V21.7 causal decision hierarchy",
                    "5. Produces embodiment-level decision (PASS/CONDITIONAL/FAIL/INCONCLUSIVE)",
                    "6. Includes result_scope = EMBODIMENT_LEVEL (V22 ontology)",
                    "7. Includes single-lot declaration",
                ],
            },
            "pass_fail_decision_script": {
                "path": "scripts/r6_analyze_exp01.py (same script — analysis + decision are unified)",
                "sha256": PASS_FAIL_SCRIPT_HASH,
                "rule": "The pass/fail logic is embedded in the analysis script. "
                        "Both are frozen together. No separate decision script can be "
                        "substituted post-hoc.",
            },
        },

        "instrument_calibration_template": {
            "status": "TEMPLATE — fill when instruments are identified",
            "fields_to_record": {
                "pressure_transducer": {
                    "instrument_id": "TBD",
                    "manufacturer": "TBD",
                    "model": "TBD",
                    "range_mmhg": "TBD (must cover 0-50 mmHg)",
                    "accuracy_mmhg": "TBD (must be <= 0.5 mmHg)",
                    "calibration_date": "TBD",
                    "calibration_standard": "TBD (NIST-traceable)",
                    "calibration_certificate_number": "TBD",
                },
                "flow_meter": {
                    "instrument_id": "TBD",
                    "manufacturer": "TBD",
                    "model": "TBD",
                    "range_ml_min": "TBD (must cover 0.001-10 mL/min)",
                    "accuracy_pct": "TBD (must be <= 2% of reading)",
                    "calibration_date": "TBD",
                    "calibration_method": "TBD (gravimetric verification)",
                },
                "temperature_bath": {
                    "instrument_id": "TBD",
                    "range_c": "TBD (must maintain 37 +/- 0.5 C)",
                    "calibration_date": "TBD",
                },
                "analytical_balance": {
                    "instrument_id": "TBD (for gravimetric flow verification)",
                    "accuracy_mg": "TBD (must be <= 1 mg)",
                    "calibration_date": "TBD",
                    "calibration_standard": "TBD (NIST-traceable weights)",
                },
            },
        },

        "positive_control_template": {
            "status": "TEMPLATE — fill when Medtronic Strata is tested",
            "fields_to_record": {
                "device": "Medtronic Strata NSC (or equivalent commercial CSF shunt valve)",
                "serial_number": "TBD",
                "ifu_specified_opening_pressure_mmhg": "TBD (per IFU for selected performance level)",
                "ifu_performance_level": "TBD",
                "ifu_source": "TBD (IFU document reference)",
                "measured_opening_pressure_mmhg": "TBD (measured during calibration check)",
                "measurement_timestamp": "TBD",
                "pass_criterion": "measured within +/- 2 mmHg of IFU specification",
                "result": "TBD (PASS/FAIL — if FAIL, INCONCLUSIVE for entire experiment)",
                "operator_id": "TBD",
            },
            "rule": "Positive control MUST be tested BEFORE P01. If it fails: INCONCLUSIVE, "
                    "recalibrate, repeat. Do NOT test prototypes with uncalibrated apparatus.",
        },

        "fabrication_lot_template": {
            "status": "TEMPLATE — fill when prototypes are fabricated",
            "fields_to_record": {
                "lot_id": "TBD (format: LOT-YYYYMMDD-001)",
                "prototype_ids": ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08",
                                  "P09", "P10", "P11", "P12", "P13", "P14", "P15", "P16",
                                  "P17", "P18", "P19", "P20"],
                "material_batch_number": "TBD",
                "material_specification": "Medical-grade silicone, Shore 50A",
                "machine_id": "TBD",
                "tool_revision": "TBD",
                "molding_temperature_c": "TBD",
                "cycle_time_s": "TBD",
                "operator_id": "TBD",
                "post_processing": "TBD (if any)",
                "fabrication_date": "TBD",
            },
            "single_lot_declaration": "All 20 prototypes from ONE fabrication lot. "
                                       "Engineering feasibility only. Manufacturing capability NOT established.",
        },

        "randomized_test_order": {
            "status": "FROZEN (from V22.1)",
            "order": [4, 1, 9, 8, 17, 3, 12, 2, 11, 18, 13, 7, 19, 16, 14, 10, 5, 15, 6, 20],
            "seed": 42,
            "method": "Python random.seed(42); random.sample(range(1,21), 20)",
            "rule": "Prototypes are tested in this order. Do NOT reorder.",
        },

        "raw_data_storage": {
            "location": "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET/EXP-R6-01-raw-data.json",
            "format": "JSON (per V22.1 per-prototype result schema)",
            "naming_convention": "EXP-R6-01-raw-{lot_id}-{test_date}.json",
            "immutable_timestamping": "Each measurement record includes ISO timestamp. "
                                       "The raw data file is committed to git after testing "
                                       "(git commit provides immutable timestamp).",
            "rule": "Raw measurements are recorded BEFORE interpretation. "
                    "The analysis script is run AFTER all 20 prototypes are tested. "
                    "Do NOT analyze partial results (Article XV: disclose ALL data).",
        },

        "execution_sequence": [
            "1. Fill fabrication lot template (when prototypes arrive)",
            "2. Fill instrument calibration template (when instruments identified)",
            "3. Run positive control (Medtronic Strata) — MUST pass before P01",
            "4. Fill positive control template with measured result",
            "5. Test P01-P20 in frozen randomized order [4,1,9,8,17,3,12,2,11,18,13,7,19,16,14,10,5,15,6,20]",
            "6. Record ALL raw measurements in per-prototype schema",
            "7. Commit raw data file to git (immutable timestamp)",
            "8. Run analysis script: python scripts/r6_analyze_exp01.py <raw_data_file>",
            "9. Verify analysis script hash matches frozen hash",
            "10. Report results at EMBODIMENT level (V22 ontology)",
            "11. If FAIL: write failure report before designing embodiment #2",
        ],

        "frozen_hashes_summary": {
            "analysis_script_sha256": ANALYSIS_SCRIPT_HASH,
            "pass_fail_script_sha256": PASS_FAIL_SCRIPT_HASH,
            "constitution_version": "1.4.0",
            "constitution_hash": "d70e399a8839a237eae013e1bbd3e582998e62b8dc5ef0a65f8afa7f2e65b586",
            "note": "These hashes are FROZEN before any physical testing. "
                    "After testing, the analysis script is run and its hash verified "
                    "against this record. If the hash does not match: the script was "
                    "modified post-hoc and the experiment is INVALIDATED (Article VII).",
        },

        "final_statement": {
            "text": "All execution artifacts are FROZEN. The analysis script is hashed. "
                    "The test order is locked. The templates are defined. "
                    "The next action is PHYSICAL: fabricate, calibrate, test, record, analyze, report. "
                    "STOP CODING.",
            "stop_coding": True,
            "next_action": "FABRICATE 20 PROTOTYPES AND EXECUTE EXP-R6-01",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 EXP-R6-01 EXECUTION ARTIFACT — FROZEN")
    print("=" * 78)

    results = execution_artifact()

    print(f"\n1. FROZEN SCRIPTS:")
    print(f"   Analysis script: {results['frozen_scripts']['analysis_script']['path']}")
    print(f"   SHA-256: {results['frozen_scripts']['analysis_script']['sha256']}")
    print(f"   Pass/fail script: SAME (unified)")
    print(f"   SHA-256: {results['frozen_scripts']['pass_fail_decision_script']['sha256']}")

    print(f"\n2. INSTRUMENT CALIBRATION: TEMPLATE (fill when hardware arrives)")
    print(f"3. POSITIVE CONTROL: TEMPLATE (fill when Strata is tested)")
    print(f"4. FABRICATION LOT: TEMPLATE (fill when prototypes arrive)")
    print(f"5. TEST ORDER: FROZEN: {results['randomized_test_order']['order']}")
    print(f"6. RAW DATA STORAGE: {results['raw_data_storage']['location']}")

    print(f"\nEXECUTION SEQUENCE:")
    for step in results["execution_sequence"]:
        print(f"  {step}")

    print(f"\nFROZEN HASHES:")
    for k, v in results["frozen_hashes_summary"].items():
        if k != "note":
            print(f"  {k}: {v}")

    print(f"\n{'='*78}")
    print(f"STOP CODING: {results['final_statement']['stop_coding']}")
    print(f"NEXT: {results['final_statement']['next_action']}")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_2_R6_EXECUTION_ARTIFACT.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
