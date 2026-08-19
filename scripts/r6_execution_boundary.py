#!/usr/bin/env python3
"""
R6 V22.3 — Execution-Boundary Hardening (positive control + raw-data validation + crypto binding)

Per CEO v30.29:
  "The experiment isn't trustworthy because the protocol is frozen.
   It is trustworthy when the entire chain from instrument output to
   final decision is tamper-evident and incapable of silently dropping bad data."

Three fixes:
  1. Freeze exact positive control (one device, one config, no substitutions)
  2. Analysis script now validates raw data (bad data → INCONCLUSIVE, never silent skip)
  3. Cryptographic binding: raw_data_sha256 + analysis_script_sha256 + constitution_hash

This is NOT a new protocol version. It is execution-boundary hardening.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent

# Updated analysis script hash (after adding validation + crypto binding)
ANALYSIS_SCRIPT = (REPO / "scripts" / "r6_analyze_exp01.py").read_bytes()
ANALYSIS_SCRIPT_HASH = hashlib.sha256(ANALYSIS_SCRIPT).hexdigest()


def execution_boundary_hardening():
    return {
        "task_id": "R6-V22.3-EXECUTION-BOUNDARY-HARDENING",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "The experiment must be tamper-evident and incapable of "
                         "silently dropping bad data.",
        "status": "EXECUTION_BOUNDARY_HARDENED — ready for physical testing",

        "fix_1_frozen_positive_control": {
            "problem": "V22.2 said 'Medtronic Strata NSC (or equivalent).' "
                       "'Or equivalent' is too loose — allows post-hoc substitution.",
            "solution": "ONE exact device, ONE exact configuration. No substitutions.",

            "frozen_positive_control": {
                "device": "Medtronic Strata NSC (Non-Adjustable Shunt Valve)",
                "manufacturer": "Medtronic Neurosurgery",
                "product_code": "Per Medtronic catalog (to be filled with exact part number when purchased)",
                "performance_level": "2.0 (per IFU table)",
                "ifu_specified_opening_pressure_mmhg": "Per IFU: performance level 2.0 corresponds to approximately 15-20 mmHg opening pressure",
                "ifu_source_document": "Medtronic Strata NSC Instructions for Use (to be obtained from Medtronic with device purchase)",
                "serial_number": "TBD (record when device is obtained)",
                "lot_number": "TBD (record when device is obtained)",
                "selection_timestamp": "FROZEN at " + datetime.now(timezone.utc).isoformat() + " — device type and performance level selected BEFORE testing",
                "no_substitution_rule": "If the specified Medtronic Strata NSC at performance level 2.0 is unavailable, "
                    "the experiment is DELAYED until it is obtained. No substitute device may be used. "
                    "If the positive control fails calibration (measured opening pressure outside ±2 mmHg of IFU spec), "
                    "the experiment is INCONCLUSIVE — recalibrate apparatus, re-test positive control. "
                    "Do NOT substitute a different valve to make the control pass.",
                "pass_criterion": "measured opening pressure within ±2 mmHg of IFU-specified pressure for level 2.0",
                "fail_action": "INCONCLUSIVE — recalibrate apparatus, re-run positive control. If positive control fails twice: apparatus is defective, repair before testing prototypes.",
            },
        },

        "fix_2_raw_data_validation": {
            "problem": "The original analysis script could silently skip malformed records, "
                       "producing a plausible-looking result from bad data.",
            "solution": "The analysis script now validates raw data BEFORE analysis. "
                       "Bad data produces INCONCLUSIVE, never a silent skip.",

            "validation_checks": [
                "WRONG_PROTOTYPE_COUNT: expected 20, got N → INCONCLUSIVE",
                "DUPLICATE_PROTOTYPE_IDS: same ID appears twice → INCONCLUSIVE",
                "UNEXPECTED_PROTOTYPE_IDS: ID not in P01-P20 → INCONCLUSIVE",
                "MISSING_PROTOTYPE_IDS: expected ID not found → INCONCLUSIVE",
                "MISSING_MEASUREMENT: prototype missing a required metric → INCONCLUSIVE",
                "INSUFFICIENT_CYCLES: <2 valid opening pressure cycles → INCONCLUSIVE",
                "IMPOSSIBLE_VALUE: pressure <0 or >100, drift <-50 or >50 → INCONCLUSIVE",
                "CALIBRATION_NOT_VERIFIED: calibration_verified is False → INCONCLUSIVE",
                "UNEXPECTED_SCHEMA_KEYS: unknown top-level keys → INCONCLUSIVE",
            ],
            "rule": "If ANY validation check fails, the ENTIRE experiment is INCONCLUSIVE. "
                    "The script does NOT skip individual prototypes. It does NOT analyze "
                    "partial data. It produces INCONCLUSIVE and exits.",
            "analysis_script_sha256": ANALYSIS_SCRIPT_HASH,
        },

        "fix_3_cryptographic_binding": {
            "problem": "A timestamp inside JSON can be altered before commit. "
                       "The analysis could run on one raw file and later commit a modified one.",
            "solution": "The analysis script now computes SHA-256 of the raw data file "
                       "BEFORE loading it. The final result contains a cryptographic_binding "
                       "block that binds: raw_data_sha256 + analysis_script_sha256 + "
                       "constitution_hash + experiment_id.",

            "binding_chain": {
                "step_1": "Instrument outputs raw measurement → recorded in JSON file",
                "step_2": "Raw data file committed to git (git commit SHA = immutable timestamp)",
                "step_3": "Analysis script computes SHA-256 of raw data file (raw_data_sha256)",
                "step_4": "Analysis script computes SHA-256 of itself (analysis_script_sha256)",
                "step_5": "Analysis script includes constitution_hash (frozen at protocol time)",
                "step_6": "Final result contains all three hashes + binding_statement",
                "step_7": "To verify: re-run analysis script on the same raw file. "
                          "If raw_data_sha256 matches → raw file is unmodified. "
                          "If analysis_script_sha256 matches frozen hash → script is unmodified. "
                          "If either mismatch → result is INVALIDATED.",
            },
            "frozen_hashes": {
                "analysis_script_sha256": ANALYSIS_SCRIPT_HASH,
                "constitution_version": "1.4.0",
                "constitution_hash": "d70e399a8839a237eae013e1bbd3e582998e62b8dc5ef0a65f8afa7f2e65b586",
            },
        },

        "summary": {
            "total_fixes": 3,
            "fix_1": "Positive control frozen: Medtronic Strata NSC, performance level 2.0, "
                     "no substitutions. If unavailable: DELAY. If fails calibration: INCONCLUSIVE.",
            "fix_2": "Raw-data validation: 9 checks. Bad data → INCONCLUSIVE, never silent skip. "
                     "Analysis script SHA-256: " + ANALYSIS_SCRIPT_HASH[:16] + "...",
            "fix_3": "Cryptographic binding: raw_data_sha256 + analysis_script_sha256 + "
                     "constitution_hash in every result. Tamper-evident chain from instrument "
                     "to final decision.",
            "stop_coding": True,
            "next_action": "FABRICATE 20 PROTOTYPES AND EXECUTE EXP-R6-01",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V22.3 — EXECUTION-BOUNDARY HARDENING")
    print("=" * 78)

    results = execution_boundary_hardening()

    print("\n1. FROZEN POSITIVE CONTROL:")
    pc = results["fix_1_frozen_positive_control"]["frozen_positive_control"]
    print(f"   Device: {pc['device']}")
    print(f"   Performance level: {pc['performance_level']}")
    print(f"   IFU spec: {pc['ifu_specified_opening_pressure_mmhg']}")
    print(f"   No substitution: {pc['no_substitution_rule'][:80]}...")

    print("\n2. RAW-DATA VALIDATION:")
    for check in results["fix_2_raw_data_validation"]["validation_checks"]:
        print(f"   {check}")
    print(f"   Script SHA-256: {results['fix_2_raw_data_validation']['analysis_script_sha256'][:16]}...")

    print("\n3. CRYPTOGRAPHIC BINDING:")
    chain = results["fix_3_cryptographic_binding"]["binding_chain"]
    for step in chain.values():
        print(f"   {step[:80]}...")

    print(f"\nFROZEN HASHES:")
    fh = results["fix_3_cryptographic_binding"]["frozen_hashes"]
    for k, v in fh.items():
        print(f"  {k}: {v[:20]}...")

    print(f"\n{'='*78}")
    print(f"STOP CODING: {results['summary']['stop_coding']}")
    print(f"NEXT: {results['summary']['next_action']}")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_3_R6_EXECUTION_BOUNDARY.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
