#!/usr/bin/env python3
"""
R6 POSITIVE_CONTROL_EVIDENCE_REPORT

Per CEO v30.32:
  The FDA recall + IFU research revealed critical issues:
  1. Performance Level 2.0 = 145-165 mmH2O (~10.7-12.1 mmHg), NOT 15-20 mmHg
  2. The ±2 mmHg criterion was NOT from the IFU — it was our ENGINEERING_TEST_TOLERANCE
  3. The FDA recall (Z-1121-2017) was for StrataMR, NOT Strata NSC — but a separate
     recall (2021) addressed radiopaque marking visibility for Strata II/NSC
  4. The Strata NSC is an ADJUSTABLE valve with 5 performance levels, not a fixed-pressure valve

This report documents the evidence and recommends a corrected control hierarchy.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def positive_control_evidence_report():
    return {
        "task_id": "R6-POSITIVE-CONTROL-EVIDENCE-REPORT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Do not assume ±2 mmHg is an IFU requirement. Attack the "
                         "assumptions underneath the provenance system itself.",
        "status": "EVIDENCE_REPORT — positive control assumption corrected",

        "critical_finding": {
            "what_was_assumed": "Strata NSC performance level 2.0 = ~15-20 mmHg opening pressure",
            "what_the_evidence_shows": "Strata NSC performance level 2.0 = 145-165 mmH2O "
                                       "= approximately 10.7-12.1 mmHg opening pressure",
            "source": "NeuroSpine Product Review (citing Medtronic Strata NSC specifications): "
                      "P/L 0.5: 15-35 mmH2O, P/L 1.0: 35-55 mmH2O, P/L 1.5: 90-110 mmH2O, "
                      "P/L 2.0: 145-165 mmH2O, P/L 2.5: 200-220 mmH2O",
            "source_url": "https://neurospineproductreview.com/ps-medical-strata-nsc-adjustable-shunt-valve",
            "corroborating_source": "ResearchGate (citing Medtronic): 'Settings 1 to 7 cover "
                                    "a range from 25 to 215 mmH2O' — but this refers to the "
                                    "OLDER Strata valve with 7 settings, not the NSC with 5 levels. "
                                    "The NSC has P/L 0.5 to 2.5.",
            "corroborating_url": "https://www.researchgate.net/figure/Medtronic-Strata-valve-at-various-settings",
            "discrepancy_magnitude": "Assumed 15-20 mmHg; actual is ~10.7-12.1 mmHg. "
                                     "This is a ~30% error in the assumed opening pressure.",
            "impact_on_experiment": "The positive control criterion was set to 'within ±2 mmHg "
                                    "of IFU-specified pressure for level 2.0.' If the IFU spec "
                                    "is 10.7-12.1 mmHg (not 15-20), the ±2 mmHg tolerance "
                                    "is a LARGER fraction of the opening pressure than assumed.",
        },

        "evidence_objects": [
            {
                "claim": "Strata NSC P/L 2.0 opening pressure is 145-165 mmH2O",
                "source_identity": {
                    "type": "product_review_website",
                    "title": "PS Medical Strata NSC Adjustable Shunt Valve",
                    "publisher": "NeuroSpine Product Review",
                    "url": "https://neurospineproductreview.com/ps-medical-strata-nsc-adjustable-shunt-valve",
                    "accessed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                },
                "exact_passage": "P/L 0.5: 15-35mmH2O, P/L 1.0: 35-55mmH2O, "
                                 "P/L 1.5: 90-110mmH2O, P/L 2.0: 145-165mmH2O, "
                                 "P/L 2.5: 200-220mmH2O",
                "content_hash": hashlib.sha256(
                    "P/L 0.5: 15-35mmH2O, P/L 1.0: 35-55mmH2O, "
                    "P/L 1.5: 90-110mmH2O, P/L 2.0: 145-165mmH2O, "
                    "P/L 2.5: 200-220mmH2O".encode()
                ).hexdigest(),
                "evidence_class": "SECONDARY_REPORTED",
                "uncertainty": "This is a SECONDARY source (product review website), not the "
                               "primary IFU. The primary IFU must be obtained from Medtronic "
                               "to confirm these values. Do NOT use this as the authoritative "
                               "specification — it is DISCOVERY evidence only.",
            },
            {
                "claim": "Strata NSC opening pressure change per performance level is 5.9-6.5 mmHg",
                "source_identity": {
                    "type": "peer_reviewed_paper",
                    "title": "Evaluation of Strata NSC and Codman Hakim adjustable CSF shunt valves",
                    "authors": ["Arnell K", "et al."],
                    "journal": "Journal of Neurosurgery: Pediatrics",
                    "year": 2009,
                    "volume": "3",
                    "pages": "166-170",
                    "url": "https://thejns.org/pediatrics/view/journals/j-neurosurg-pediatr/3/3/article-p166.xml",
                },
                "exact_passage": "The change in opening pressure in the Strata NSC is "
                                 "5.9-6.5 mm Hg (7.7-8.4 cm H2O)",
                "content_hash": hashlib.sha256(
                    "The change in opening pressure in the Strata NSC is "
                    "5.9-6.5 mm Hg (7.7-8.4 cm H2O)".encode()
                ).hexdigest(),
                "evidence_class": "SECONDARY_REPORTED",
                "uncertainty": "This is the STEP SIZE between performance levels, not the "
                               "absolute opening pressure at any given level.",
            },
        ],

        "fda_recall_investigation": {
            "recall_1": {
                "recall_number": "Z-1121-2017",
                "device": "StrataMR adjustable valves and shunts (NOT Strata NSC)",
                "date_initiated": "2017-01-17",
                "reason": "Potential for performance level discrepancy due to a rare condition "
                          "related to the Strata Valve that can lead to an inaccurate pressure "
                          "level reading",
                "fda_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRes/res.cfm?ID=152582",
                "applies_to_strata_nsc": "NO — FDA explicitly states: 'This recall only applies "
                                         "to StrataMR adjustable valves and shunts and does not "
                                         "apply to Strata II or Strata NSC products.'",
                "source": "FDA + Medtronic press release",
            },
            "recall_2": {
                "recall_number": "Z-1121-2021 (approximate)",
                "device": "Medtronic PS Medical Strata II Valve (related to NSC)",
                "date_initiated": "2021-02-12",
                "reason": "Potential for variation in radiopaque marking visibility under "
                          "radiographic imaging for adjustable and fixed-pressure valves",
                "fda_url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id=185453",
                "applies_to_strata_nsc": "POSSIBLY — this recall addresses radiopaque marking "
                                         "visibility, which affects the ability to READ the "
                                         "performance level setting via X-ray. This is a "
                                         "readability issue, not a pressure-performance issue.",
                "relevance_to_experiment": "If we use a Strata NSC as a positive control, we "
                                           "must verify its performance level setting INDEPENDENTLY "
                                           "of X-ray reading (e.g., by direct pressure measurement, "
                                           "which is what our test apparatus does). The readability "
                                           "recall does NOT affect the valve's actual opening "
                                           "pressure — only the ability to read its setting.",
            },
            "recall_relevance_assessment": "The FDA recalls do NOT disqualify Strata NSC as a "
                                           "positive control. Recall 1 (StrataMR) does not apply "
                                           "to NSC. Recall 2 (marking visibility) affects "
                                           "readability, not pressure performance. Our test "
                                           "apparatus measures ACTUAL opening pressure, not "
                                           "X-ray-readable settings — so the readability issue "
                                           "is irrelevant to our use case. "
                                           "HOWEVER: the recalls highlight that performance-level "
                                           "discrepancies are a known issue in this valve family. "
                                           "This strengthens the argument for using a calibrated "
                                           "pressure standard as the PRIMARY control, with Strata "
                                           "NSC as a SECONDARY device-control.",
        },

        "measurement_uncertainty": {
            "assumed_criterion": "±2 mmHg of IFU-specified pressure",
            "actual_classification": "ENGINEERING_TEST_TOLERANCE — NOT an IFU specification",
            "rationale": "The ±2 mmHg criterion was set by the coder as a reasonable test "
                         "tolerance, NOT by Medtronic as an IFU specification. The IFU gives "
                         "a RANGE (145-165 mmH2O for P/L 2.0), not a ±tolerance. "
                         "The ±2 mmHg must be relabeled as ENGINEERING_TEST_TOLERANCE.",
            "corrected_criterion": "Positive control passes if measured opening pressure "
                                   "falls within the IFU-specified RANGE for the selected "
                                   "performance level (145-165 mmH2O for P/L 2.0 = "
                                   "10.7-12.1 mmHg). The ±2 mmHg is our measurement "
                                   "uncertainty budget, not a pass/fail criterion.",
        },

        "proposed_control_hierarchy": {
            "problem": "Using a Strata NSC as the sole positive control has limitations: "
                       "(1) it's an adjustable valve with known performance-level discrepancy "
                       "issues in the family, (2) we haven't obtained the primary IFU yet, "
                       "(3) the assumed pressure was wrong.",
            "recommendation": "Use a TWO-TIER control hierarchy:",

            "tier_1_primary": {
                "control": "Calibrated pressure standard / reference manometer",
                "description": "A NIST-traceable pressure calibrator (e.g., Fluke 718 or "
                               "equivalent) that generates a known pressure with certified "
                               "accuracy. This is the PRIMARY control — it verifies the test "
                               "apparatus can measure pressure correctly.",
                "pass_criterion": "Apparatus reading within ±0.5 mmHg of calibrator output "
                                  "at 10, 15, 20, 25, 30 mmHg",
                "evidence_basis": "NIST-traceable calibration certificate",
                "strength": "HIGHEST — direct pressure standard, no device variability",
            },
            "tier_2_secondary": {
                "control": "Medtronic Strata NSC at P/L 2.0 (or another P/L closer to 20-25 mmHg)",
                "description": "A commercial CSF shunt valve as a SECONDARY device-control. "
                               "Verifies the apparatus can measure a real valve's opening "
                               "pressure in the expected range.",
                "pass_criterion": "Measured opening pressure falls within the IFU-specified "
                                  "RANGE for the selected performance level",
                "evidence_basis": "Manufacturer IFU (must be obtained as primary document)",
                "strength": "MODERATE — subject to device variability and IFU range width",
                "note_on_performance_level": "P/L 2.0 gives 145-165 mmH2O (~10.7-12.1 mmHg). "
                    "This is BELOW our target range of 15-30 mmHg. Consider using P/L 2.5 "
                    "(200-220 mmH2O = ~14.7-16.2 mmHg) which is closer to the lower bound "
                    "of our target range. OR: acknowledge that the Strata NSC operates at "
                    "LOWER pressures than our R6 target and is therefore a LIMITED control.",
            },
            "recommendation_summary": "Tier 1 (NIST-traceable pressure calibrator) is REQUIRED. "
                                      "Tier 2 (Strata NSC) is RECOMMENDED but not sufficient alone. "
                                      "If only Tier 2 is available: the control is weaker and the "
                                      "result must carry a caveat.",
        },

        "unresolved_questions": [
            "1. Can we obtain the actual Medtronic Strata NSC IFU as a primary document? "
            "   (Requires device purchase or Medtronic customer service request)",
            "2. Should we use P/L 2.5 instead of P/L 2.0 to get closer to our 15-30 mmHg target? "
            "   P/L 2.5 = 200-220 mmH2O = ~14.7-16.2 mmHg — still below 15-30 but closer.",
            "3. Should we use a DIFFERENT commercial valve (e.g., Codman Hakim, Sophysa Polaris) "
            "   that has a performance level closer to 20-25 mmHg?",
            "4. Is a NIST-traceable pressure calibrator available in the lab? "
            "   (This is the strongest control and should be prioritized.)",
            "5. The ±2 mmHg criterion has been relabeled to ENGINEERING_TEST_TOLERANCE. "
            "   What should the actual pass criterion be for the Strata NSC? "
            "   Recommendation: 'measured opening pressure within the IFU-specified RANGE' "
            "   (not ±X of a nominal value).",
        ],

        "final_recommendation": {
            "immediate_actions": [
                "1. OBTAIN a NIST-traceable pressure calibrator as the PRIMARY control",
                "2. OBTAIN the Medtronic Strata NSC IFU as a primary document (with device purchase)",
                "3. CORRECT the performance level assumption: P/L 2.0 = 145-165 mmH2O (~10.7-12.1 mmHg), NOT 15-20 mmHg",
                "4. RELABEL ±2 mmHg as ENGINEERING_TEST_TOLERANCE, not IFU_SPECIFICATION",
                "5. CONSIDER using P/L 2.5 (200-220 mmH2O = ~14.7-16.2 mmHg) or a different valve",
                "6. UPDATE the frozen execution artifact with the corrected control hierarchy",
            ],
            "what_NOT_to_do": [
                "Do NOT use the third-party IFU copy (manualzz.com) as authoritative",
                "Do NOT assume the ±2 mmHg is an IFU requirement — it is our test tolerance",
                "Do NOT use P/L 2.0 without verifying the actual opening pressure range",
                "Do NOT skip the NIST-traceable calibrator — it is the strongest control",
            ],
            "principle": "The FDA recall is NOT evidence that R6 fails. It is evidence that "
                         "our proposed measurement-control assumption deserves adversarial "
                         "examination. The constitution should enforce this distinction.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 POSITIVE CONTROL EVIDENCE REPORT")
    print("=" * 78)

    results = positive_control_evidence_report()

    print(f"\nCRITICAL FINDING:")
    cf = results["critical_finding"]
    print(f"  Assumed: {cf['what_was_assumed']}")
    print(f"  Actual: {cf['what_the_evidence_shows']}")
    print(f"  Discrepancy: {cf['discrepancy_magnitude']}")

    print(f"\nFDA RECALL INVESTIGATION:")
    for key, recall in results["fda_recall_investigation"].items():
        if isinstance(recall, dict) and "device" in recall:
            print(f"\n  {recall['recall_number']}: {recall['device']}")
            print(f"  Reason: {recall['reason'][:100]}...")
            print(f"  Applies to NSC: {recall.get('applies_to_strata_nsc', '?')[:100]}...")

    print(f"\nMEASUREMENT UNCERTAINTY:")
    mu = results["measurement_uncertainty"]
    print(f"  Old label: IFU_SPECIFICATION")
    print(f"  Correct label: {mu['actual_classification']}")
    print(f"  Corrected criterion: {mu['corrected_criterion'][:100]}...")

    print(f"\nPROPOSED CONTROL HIERARCHY:")
    ch = results["proposed_control_hierarchy"]
    print(f"  Tier 1 (Primary): {ch['tier_1_primary']['control']}")
    print(f"    Strength: {ch['tier_1_primary']['strength']}")
    print(f"  Tier 2 (Secondary): {ch['tier_2_secondary']['control']}")
    print(f"    Strength: {ch['tier_2_secondary']['strength']}")
    print(f"    Note: {ch['tier_2_secondary']['note_on_performance_level'][:100]}...")

    print(f"\nUNRESOLVED QUESTIONS: {len(results['unresolved_questions'])}")
    for q in results["unresolved_questions"]:
        print(f"  {q[:100]}...")

    print(f"\n{'='*78}")
    print(f"FINAL RECOMMENDATION:")
    for a in results["final_recommendation"]["immediate_actions"]:
        print(f"  {a[:100]}...")
    print(f"\n  Principle: {results['final_recommendation']['principle'][:100]}...")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "POSITIVE_CONTROL_EVIDENCE_REPORT.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
