#!/usr/bin/env python3
"""
R6 V22.6 — Final Control Hierarchy: Traceable Standard (Primary) + Strata NSC (Secondary)

Per CEO v30.33:
  "Never let the control become part of the hypothesis.
   The control exists to test the measurement system — not to help R6 pass."

  "The calibration standard must never be selected because it makes R6 look good."

  Tier 1 — Primary: traceable pressure calibration standard (INDEPENDENT of R6)
  Tier 2 — Secondary: Medtronic Strata NSC (sanity check only, using IFU range)

  The correct order is:
    traceable pressure standard → instrument calibration →
    independent commercial-valve sanity check → R6 testing.

This is the FINAL control artifact. After this: STOP CODING. Execute physically.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def final_control_hierarchy():
    return {
        "task_id": "R6-V22.6-FINAL-CONTROL-HIERARCHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Never let the control become part of the hypothesis. "
                         "The control exists to test the measurement system — "
                         "not to help R6 pass.",
        "status": "CONTROL_HIERARCHY_FROZEN — ready for physical execution",

        "principle": {
            "rule": "The calibration standard must never be selected because it makes "
                    "R6 look good. The control exists to test the MEASUREMENT SYSTEM, "
                    "not to validate the invention.",
            "order": "traceable pressure standard → instrument calibration → "
                     "independent commercial-valve sanity check → R6 testing",
            "independence_requirement": "The primary standard must be INDEPENDENT of "
                                        "the device under test. It must not be chosen "
                                        "because its operating range resembles R6's "
                                        "target range.",
        },

        "tier_1_primary_control": {
            "name": "NIST-traceable pressure calibration standard",
            "purpose": "Verify the test apparatus can measure pressure correctly. "
                       "This is the PRIMARY control — it validates the instrument, "
                       "not the invention.",
            "independence": "COMPLETELY INDEPENDENT of R6. The calibrator generates "
                            "known pressures from a certified standard. It does not "
                            "resemble a shunt valve and its range is not selected "
                            "to match R6's target.",
            "recommended_device": {
                "type": "Pressure calibrator (e.g., Fluke 718, Druck DPI 610, "
                        "or equivalent NIST-traceable pressure generator)",
                "required_range": "0-50 mmHg minimum (must cover the full test range)",
                "required_accuracy": "±0.1 mmHg or better (must be significantly tighter "
                                      "than the test apparatus accuracy of ±0.5 mmHg)",
                "certification": "NIST-traceable calibration certificate, current "
                                  "(within 12 months of test date)",
                "selection_criterion": "Selected based on TRACEABILITY and ACCURACY, "
                                       "NOT based on proximity to R6's 20-25 mmHg target.",
            },
            "calibration_procedure": {
                "step_1": "Connect calibrator to test apparatus pressure transducer",
                "step_2": "Generate known pressures at 5, 10, 15, 20, 25, 30, 35, 40 mmHg",
                "step_3": "Record: calibrator_output_mmhg, apparatus_reading_mmhg, "
                          "deviation_mmhg, at each point",
                "step_4": "Pass criterion: apparatus reading within ±0.5 mmHg of "
                          "calibrator output at ALL points",
                "step_5": "If ANY point fails: INCONCLUSIVE — recalibrate apparatus, "
                          "repeat. Do NOT proceed to R6 testing.",
            },
            "pass_criterion": {
                "criterion": "Apparatus reading within ±0.5 mmHg of calibrator output "
                             "at ALL calibration points (5-40 mmHg)",
                "classification": "ENGINEERING_TEST_TOLERANCE",
                "basis": "The ±0.5 mmHg is the apparatus's specified accuracy. "
                         "The calibrator's accuracy (±0.1 mmHg) is 5x tighter, "
                         "providing sufficient margin.",
                "not_selected_for_r6": "The ±0.5 mmHg tolerance is the APPARATUS spec, "
                                       "not a value chosen to make R6 look good.",
            },
            "fields_to_record": {
                "calibrator_id": "TBD (instrument ID)",
                "calibrator_manufacturer": "TBD",
                "calibrator_model": "TBD",
                "calibrator_accuracy_mmhg": "TBD (must be ≤ 0.1 mmHg)",
                "calibration_certificate_number": "TBD (NIST-traceable)",
                "calibration_certificate_date": "TBD (must be within 12 months)",
                "calibration_points": "5, 10, 15, 20, 25, 30, 35, 40 mmHg",
                "measured_deviations": "TBD (recorded at each point)",
                "pass": "TBD (all points within ±0.5 mmHg)",
                "test_timestamp": "TBD",
                "operator_id": "TBD",
            },
            "binding_rule": "Tier 1 MUST pass before ANY other testing. "
                            "If Tier 1 fails: INCONCLUSIVE. No Tier 2. No R6 testing.",
        },

        "tier_2_secondary_control": {
            "name": "Medtronic Strata NSC (independent commercial-valve sanity check)",
            "purpose": "Verify the test apparatus can measure a REAL valve's opening "
                       "pressure in a realistic scenario. This is a SECONDARY check — "
                       "it supplements Tier 1 but cannot replace it.",
            "independence": "The Strata NSC is a commercial CSF shunt valve. It is "
                            "INDEPENDENT of R6 (different manufacturer, different "
                            "mechanism, different design). Its performance level is "
                            "NOT selected to match R6's target — it is selected based "
                            "on availability and IFU documentation.",
            "device_specification": {
                "device": "Medtronic Strata NSC (Non-Adjustable Shunt Valve)",
                "manufacturer": "Medtronic Neurosurgery",
                "performance_level": "TBD — selected based on AVAILABILITY, not R6 proximity",
                "ifu_specified_range_mmh2o": "TBD — from primary IFU document (must be obtained from Medtronic)",
                "ifu_specified_range_mmhg": "TBD — converted from mmH2O (divide by 13.6)",
                "selection_rule": "Select the performance level that is AVAILABLE with "
                                  "a complete IFU. Do NOT select a level because it is "
                                  "closer to 20-25 mmHg. The control's purpose is "
                                  "instrument validation, not R6 resemblance.",
            },
            "pass_criterion": {
                "criterion": "Measured opening pressure falls within the IFU-specified "
                             "RANGE for the selected performance level",
                "classification": "MANUFACTURER_SPECIFICATION (from IFU)",
                "not_engineering_tolerance": "The ±2 mmHg ENGINEERING_TEST_TOLERANCE "
                    "from V22.3 is RETIRED. The pass criterion is now: measured pressure "
                    "within the IFU-specified RANGE (e.g., 145-165 mmH2O for P/L 2.0). "
                    "This is the MANUFACTURER'S specification, not our invention.",
                "range_width_note": "The IFU range is typically 20 mmH2O wide "
                    "(e.g., 145-165 mmH2O = ~1.5 mmHg wide). This is WIDER than the "
                    "old ±2 mmHg tolerance. The wider range is ACCEPTABLE because "
                    "Tier 1 (NIST calibrator) already verified the apparatus to ±0.5 mmHg. "
                    "Tier 2 is a sanity check, not a precision calibration.",
            },
            "fields_to_record": {
                "device_serial": "TBD",
                "device_lot": "TBD",
                "product_part_number": "TBD",
                "performance_level": "TBD (selected on availability, not R6 proximity)",
                "ifu_document_hash": "TBD (SHA-256 of primary IFU PDF from Medtronic)",
                "ifu_source": "TBD (Medtronic Manual Library or device purchase)",
                "ifu_specified_range_mmh2o": "TBD (from IFU table)",
                "measured_opening_pressure_mmhg": "TBD",
                "in_ifu_range": "TBD (boolean)",
                "test_timestamp": "TBD",
                "operator_id": "TBD",
            },
            "binding_rule": "Tier 2 can only be run AFTER Tier 1 passes. "
                            "If Tier 2 fails: the apparatus may have an issue with "
                            "real-valve testing (not just pressure calibration). "
                            "Investigate per V21.5 diagnostic order. "
                            "If investigation shows apparatus is fine: the valve "
                            "may be out of spec (device variability). Obtain a "
                            "different valve and re-test. Do NOT proceed to R6 "
                            "testing until Tier 2 passes OR the failure is "
                            "explained and documented.",
            "ifu_requirement": "The primary IFU document MUST be obtained from "
                               "Medtronic (not a third-party copy). The IFU must "
                               "be the exact document for the exact device purchased. "
                               "SHA-256 of the IFU PDF must be recorded. "
                               "Per Article VI: do NOT fabricate IFU content.",
        },

        "control_hierarchy_summary": {
            "order": [
                "1. Tier 1: NIST-traceable pressure calibrator → apparatus validated to ±0.5 mmHg",
                "2. Tier 2: Medtronic Strata NSC → apparatus validated on real valve (IFU range)",
                "3. Only then: R6 prototype testing (P01-P20)",
            ],
            "independence_guaranteed": "Neither tier is selected to make R6 look good. "
                                       "Tier 1 is a pressure standard (no resemblance to R6). "
                                       "Tier 2 is a commercial valve (different manufacturer, "
                                       "different mechanism, selected on availability).",
            "retired_criteria": [
                "±2 mmHg IFU_SPECIFICATION (was wrong — it was our tolerance, not IFU's)",
                "P/L 2.0 = 15-20 mmHg (was wrong — actual is ~10.7-12.1 mmHg)",
                "Selection of P/L based on R6 proximity (forbidden — select on availability)",
            ],
            "stop_coding": True,
            "next_action": "PHYSICAL: obtain NIST calibrator, obtain Strata NSC + IFU, "
                           "calibrate, sanity-check, then fabricate and test R6 prototypes.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V22.6 — FINAL CONTROL HIERARCHY")
    print("Never let the control become part of the hypothesis.")
    print("=" * 78)

    results = final_control_hierarchy()

    print("\nTIER 1 (PRIMARY): NIST-traceable pressure calibrator")
    t1 = results["tier_1_primary_control"]
    print(f"  Purpose: {t1['purpose'][:80]}...")
    print(f"  Independence: {t1['independence'][:80]}...")
    print(f"  Pass: {t1['pass_criterion']['criterion'][:80]}...")
    print(f"  Classification: {t1['pass_criterion']['classification']}")

    print("\nTIER 2 (SECONDARY): Medtronic Strata NSC")
    t2 = results["tier_2_secondary_control"]
    print(f"  Purpose: {t2['purpose'][:80]}...")
    print(f"  Independence: {t2['independence'][:80]}...")
    print(f"  Pass: {t2['pass_criterion']['criterion'][:80]}...")
    print(f"  Classification: {t2['pass_criterion']['classification']}")
    print(f"  Retired: {t2['pass_criterion']['not_engineering_tolerance'][:80]}...")

    print(f"\n{'='*78}")
    print("ORDER:")
    for step in results["control_hierarchy_summary"]["order"]:
        print(f"  {step}")
    print(f"\nINDEPENDENCE: {results['control_hierarchy_summary']['independence_guaranteed'][:80]}...")
    print(f"\nRETIRED CRITERIA:")
    for r in results["control_hierarchy_summary"]["retired_criteria"]:
        print(f"  {r}")
    print(f"\nSTOP CODING: {results['control_hierarchy_summary']['stop_coding']}")
    print(f"NEXT: {results['control_hierarchy_summary']['next_action'][:80]}...")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_6_R6_FINAL_CONTROL_HIERARCHY.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
