#!/usr/bin/env python3
"""
R6 V22.5 — Pre-Acquisition Checklist + Provenance Strength Classification

Per CEO v30.31:
  1. IFU document must be in custody before P01 (physical acquisition task)
  2. Provenance strength must be classified: INSTRUMENT_NATIVE_EXPORT vs OPERATOR_TRANSCRIPTION_FALLBACK

This is the FINAL software artifact. After this: physical acquisition only.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent

ANALYSIS_SCRIPT = (REPO / "scripts" / "r6_analyze_exp01.py").read_bytes()
ANALYSIS_SCRIPT_HASH = hashlib.sha256(ANALYSIS_SCRIPT).hexdigest()


def pre_acquisition_checklist():
    return {
        "task_id": "R6-V22.5-PRE-ACQUISITION-CHECKLIST",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "The closer we get to reality, the less we should rely on "
                         "human transcription and interpretation.",
        "status": "PRE_ACQUISITION — physical tasks only remain",

        "provenance_strength_classification": {
            "INSTRUMENT_NATIVE_EXPORT": {
                "definition": "The instrument directly exported its readings to a file "
                              "(CSV, proprietary format, digital output). The JSON is "
                              "a transformation of the instrument's own digital output, "
                              "not a human transcription.",
                "strength": "HIGHEST — machine-generated, no human interpretation",
                "requirement": "Export file MUST be preserved with SHA-256. The JSON "
                               "must reference the export file.",
            },
            "OPERATOR_TRANSCRIPTION_FALLBACK": {
                "definition": "The instrument does not export digital data. The operator "
                              "read the instrument display and transcribed the values "
                              "into the JSON by hand, with attestation.",
                "strength": "LOWER — human transcription, potential for error",
                "requirement": "Operator attestation MUST be included: 'I attest that "
                               "these measurements were recorded directly from instrument "
                               "readings on [date] using [instrument IDs].' The result "
                               "MUST carry provenance_strength = OPERATOR_TRANSCRIPTION_FALLBACK "
                               "so downstream consumers know the evidence is lower-strength.",
                "not_equivalent": "OPERATOR_TRANSCRIPTION_FALLBACK is NOT equivalent to "
                                  "INSTRUMENT_NATIVE_EXPORT. Results with this classification "
                                  "carry an explicit caveat in the final report.",
            },
            "validation_rule": "The analysis script now validates that provenance_strength "
                               "is present and is one of these two values. If missing or "
                               "invalid: INCONCLUSIVE.",
        },

        "pre_acquisition_checklist": {
            "description": "These are PHYSICAL tasks that must be completed before P01. "
                           "They cannot be done in software. They require purchasing "
                           "hardware, obtaining documents, and calibrating instruments.",
            "items": [
                {
                    "item": 1,
                    "task": "Purchase Medtronic Strata NSC valve",
                    "what_to_record": "product_part_number, serial_number, lot_number, device_received_date",
                    "status": "PENDING — physical purchase required",
                    "blocks": "P01 testing cannot begin without this device",
                },
                {
                    "item": 2,
                    "task": "Obtain Medtronic Strata NSC IFU document",
                    "what_to_record": "ifu_document_hash (SHA-256 of IFU PDF), ifu_obtained_date, ifu_source",
                    "source": "Comes WITH the device purchase, or request from Medtronic customer service",
                    "status": "PENDING — comes with device purchase",
                    "blocks": "Positive control cannot be validated without IFU specification",
                    "rule": "Per Article VI: do NOT fabricate IFU content. If IFU is unavailable: DELAY.",
                },
                {
                    "item": 3,
                    "task": "Record exact IFU performance-level specification",
                    "what_to_record": "ifu_specified_opening_pressure_mmhg (from IFU table for level 2.0)",
                    "source": "The IFU document obtained in item 2",
                    "status": "PENDING — depends on item 2",
                    "blocks": "Pass criterion for positive control cannot be set without this",
                },
                {
                    "item": 4,
                    "task": "Identify and calibrate test instruments",
                    "what_to_record": "pressure_transducer_id + calibration_date + NIST_traceability, "
                                      "flow_meter_id + calibration_date + gravimetric_verification, "
                                      "temperature_bath_id + calibration_date",
                    "status": "PENDING — physical instrument setup required",
                    "blocks": "All measurements depend on calibrated instruments",
                },
                {
                    "item": 5,
                    "task": "Determine instrument export capability",
                    "what_to_record": "Whether each instrument can export native digital data",
                    "if_yes": "provenance_strength = INSTRUMENT_NATIVE_EXPORT; preserve export files + SHA-256",
                    "if_no": "provenance_strength = OPERATOR_TRANSCRIPTION_FALLBACK; operator attestation required",
                    "status": "PENDING — check instrument specifications",
                    "blocks": "Provenance classification of results",
                },
                {
                    "item": 6,
                    "task": "Fabricate 20 slit-valve prototypes",
                    "what_to_record": "lot_id, material_batch, machine_id, tool_revision, "
                                      "molding_temp, cycle_time, operator_id, fabrication_date",
                    "status": "PENDING — physical fabrication required",
                    "blocks": "No prototypes = no experiment",
                },
                {
                    "item": 7,
                    "task": "Verify frozen analysis script hash",
                    "what_to_record": "Run: sha256sum scripts/r6_analyze_exp01.py",
                    "expected_hash": ANALYSIS_SCRIPT_HASH,
                    "status": "READY — can verify anytime",
                    "rule": "If hash does not match: script was modified. Do NOT proceed. "
                            "Restore from git commit e03d853 or later.",
                },
                {
                    "item": 8,
                    "task": "Run positive control (Medtronic Strata NSC) BEFORE P01",
                    "what_to_record": "device_serial, ifu_specified_pressure, measured_pressure, "
                                      "deviation, pass (within ±2 mmHg), test_timestamp, operator_id",
                    "status": "PENDING — depends on items 1-5",
                    "blocks": "If positive control fails: INCONCLUSIVE. Do NOT test prototypes.",
                    "rule": "If fails twice: apparatus is defective. Repair before testing.",
                },
            ],
            "completion_rule": "ALL 8 items must be completed and recorded before P01. "
                               "If ANY item is incomplete: the experiment is BLOCKED. "
                               "Do NOT proceed with partial setup.",
        },

        "updated_analysis_script": {
            "sha256": ANALYSIS_SCRIPT_HASH,
            "changes": "Added provenance_strength validation (must be INSTRUMENT_NATIVE_EXPORT "
                       "or OPERATOR_TRANSCRIPTION_FALLBACK) + provenance_strength in result output.",
        },

        "summary": {
            "total_items": 8,
            "software_tasks": 0,
            "physical_tasks": 7,
            "verification_tasks": 1,
            "stop_coding": True,
            "next_action": "PHYSICAL ACQUISITION: purchase device, obtain IFU, calibrate instruments, "
                           "fabricate prototypes, run positive control, then execute EXP-R6-01.",
            "principle": "The closer we get to reality, the less we should rely on human "
                         "transcription and interpretation.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V22.5 — PRE-ACQUISITION CHECKLIST + PROVENANCE STRENGTH")
    print("=" * 78)

    results = pre_acquisition_checklist()

    print("\nPROVENANCE STRENGTH CLASSIFICATION:")
    for cls, info in results["provenance_strength_classification"].items():
        if isinstance(info, dict) and "definition" in info:
            print(f"  {cls}: {info['strength']}")

    print("\nPRE-ACQUISITION CHECKLIST:")
    for item in results["pre_acquisition_checklist"]["items"]:
        print(f"  {item['item']}. {item['task']} — {item['status']}")

    print(f"\nAnalysis script SHA-256: {results['updated_analysis_script']['sha256'][:20]}...")

    print(f"\n{'='*78}")
    print(f"STOP CODING: {results['summary']['stop_coding']}")
    print(f"NEXT: {results['summary']['next_action'][:80]}...")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_5_R6_PRE_ACQUISITION_CHECKLIST.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
