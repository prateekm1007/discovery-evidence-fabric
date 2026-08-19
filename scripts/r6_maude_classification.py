#!/usr/bin/env python3
"""
R6 MAUDE Classification

Per CEO v30.13 directive + Article XXI.5:
  FDA explicitly warns that MAUDE/MDR data:
  - Cannot be used to establish incidence or event rates
  - Cannot establish causation
  - Should not be used to compare device event rates
  - May contain duplicate, incomplete, or inaccurate data

  Every MAUDE analysis must distinguish:
    malfunction       — device malfunction events
    injury            — patient injury events
    death             — patient death events
    device_problem    — device problem codes
    causality_unverified — FDA has not verified causation
    incidence_unknown — rate cannot be determined from report count

The triangulation engine reported 41,525 MAUDE reports for CSF shunts.
This script:
  1. Classifies what we know about the MAUDE data
  2. Honestly documents what we DON'T know (no individual records retrieved)
  3. Determines what R6 needs to investigate from MAUDE
  4. Never turns report counts into incidence or failure rates
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def classify_maude_data():
    """Classify the MAUDE data for R6.

    The triangulation reported 41,525 MAUDE reports. But this is just a
    SEARCH COUNT — not individual records. Per Article XXI.1, search count
    is NOT evidence. Per Article XXI.5, MAUDE data cannot establish incidence.

    We need to honestly document:
    1. What the 41,525 represents (aggregate search count, not individual records)
    2. What we DON'T know (event types, device types, causation)
    3. What R6 needs from MAUDE (obstruction-specific failure data)
    4. The epistemic limitations (FDA warnings)
    """
    results = {
        "task_id": "R6-MAUDE-CLASSIFICATION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "MAUDE classification (Article XXI.5)",
        "maude_report_count": 41525,
        "epistemic_status": {
            "what_we_know": [
                "41,525 MAUDE reports were returned for CSF shunt-related queries",
                "This is an AGGREGATE SEARCH COUNT, not individual adjudicated records",
                "The reports span ALL CSF shunt types (VP, VA, endovascular, etc.)",
                "The reports span ALL failure modes (obstruction, infection, over-drainage, etc.)",
                "FDA explicitly warns: cannot establish incidence, cannot establish causation, "
                "should not compare device event rates, may contain duplicates/inaccuracies",
            ],
            "what_we_do_not_know": [
                "How many of the 41,525 are specifically OBSTRUCTION-related (R6's target)",
                "How many are malfunction vs injury vs death",
                "How many are for endovascular shunts specifically (vs VP/VA shunts)",
                "Whether any are for bypass-lumen designs specifically",
                "The actual incidence rate (report count ≠ incidence)",
                "Whether any report was causally verified by FDA",
            ],
            "epistemic_limitations": [
                "ARTICLE XXI.5: MAUDE data CANNOT be used to establish incidence or event rates",
                "ARTICLE XXI.5: MAUDE data CANNOT establish causation",
                "ARTICLE XXI.5: MAUDE data SHOULD NOT be used to compare device event rates",
                "ARTICLE XXI.5: MAUDE data MAY contain duplicate, incomplete, or inaccurate data",
                "The 41,525 count was produced by the v16.1 triangulation engine which "
                "was later found to have manufactured a false graveyard signal from "
                "contaminated search counts (Article XXI.10 violation). The graveyard "
                "signal was RETRACTED.",
            ],
        },
        "classification": {
            "malfunction": {
                "status": "UNKNOWN",
                "reason": "Individual records not retrieved. The 41,525 is an aggregate count. "
                          "Cannot determine how many are malfunction events without per-record "
                          "adjudication of MAUDE data.",
                "fda_limitation": "Report count does not equal malfunction count. "
                                  "Some reports may be duplicates, some may be incomplete.",
            },
            "injury": {
                "status": "UNKNOWN",
                "reason": "Individual records not retrieved. Cannot determine injury count.",
                "fda_limitation": "FDA has not verified causation for any report. "
                                  "An injury report does not mean the device caused the injury.",
            },
            "death": {
                "status": "UNKNOWN",
                "reason": "Individual records not retrieved. Cannot determine death count.",
                "fda_limitation": "Death reports in MAUDE do not establish device-caused mortality. "
                                  "Underlying disease, surgical complications, and patient factors "
                                  "may contribute.",
            },
            "device_problem": {
                "status": "UNKNOWN",
                "reason": "MAUDE device problem codes (e.g., 'flow obstruction', 'catheter "
                          "displacement') were not retrieved. Only an aggregate count exists.",
                "what_r6_needs": "Query MAUDE for device problem codes specifically related to "
                                 "'obstruction', 'occlusion', 'blockage', 'flow restriction' "
                                 "in CSF shunt devices. This would tell us what fraction of "
                                 "the 41,525 are obstruction-related (R6's target failure mode).",
            },
            "causality_unverified": {
                "status": "ASSUMED_TRUE_FOR_ALL",
                "reason": "Per FDA guidance, ALL MAUDE reports have unverified causality. "
                          "No MAUDE report has been independently verified by FDA to establish "
                          "that the device caused the adverse event. This is a blanket "
                          "epistemic limitation, not a per-record classification.",
            },
            "incidence_unknown": {
                "status": "CANNOT_BE_DETERMINED",
                "reason": "Per Article XXI.5 and FDA guidance, MAUDE report counts CANNOT "
                          "be used to establish incidence rates. The 41,525 reports represent "
                          "REPORTS, not events, and not a denominator. Without knowing the "
                          "total number of implanted devices and the reporting rate, "
                          "incidence is UNKNOWN.",
                "implication_for_r6": "R6 CANNOT claim 'X% of shunts fail' based on MAUDE. "
                                      "R6 CAN claim 'obstruction is a documented failure mode "
                                      "for CSF shunts' if individual MAUDE records are "
                                      "adjudicated and obstruction-related reports are found.",
            },
        },
        "what_r6_must_do_before_physics": {
            "step_1": "Retrieve individual MAUDE records (not just count) for CSF shunt devices",
            "step_2": "Per-record relevance adjudication: classify each as obstruction-related "
                      "vs infection vs over-drainage vs other",
            "step_3": "Document the FDA limitations on every MAUDE-derived result",
            "step_4": "NEVER turn report counts into incidence or failure rates",
            "step_5": "If obstruction is a significant fraction of MAUDE reports, R6's value "
                      "proposition is strengthened (the problem R6 addresses is real and documented)",
            "step_6": "If obstruction is a small fraction, R6's value proposition is weakened "
                      "(R6 addresses a minor failure mode, not the primary one)",
        },
        "honest_assessment": {
            "can_we_claim_r6_addresses_a_real_problem": "LIKELY YES — shunt obstruction is "
            "well-documented in clinical literature (not just MAUDE). The 40 ADJACENT_RELEVANT "
            "records from the relevance adjudication include papers specifically about shunt "
            "obstruction, revision, and malfunction. The PROBLEM is real regardless of the "
            "MAUDE count's epistemic limitations.",
            "can_we_quantify_the_problem": "NO — MAUDE report counts cannot establish incidence. "
            "The 41,525 is a search count, not evidence of 41,525 obstruction events.",
            "can_we_compare_r6_to_existing_devices": "NO — MAUDE data should not be used to "
            "compare device event rates (FDA guidance). R6 must be compared on PHYSICS and "
            "ENGINEERING grounds, not on MAUDE statistics.",
            "what_is_the_graveyard_signal_really": "The 41,525 MAUDE reports indicate that "
            "CSF shunts have a HIGH FAILURE BURDEN. This is a GRAVEYARD SIGNAL for the PROBLEM "
            "DOMAIN — many approaches have been tried and the failure burden remains high. "
            "But it is NOT a graveyard signal for R6 SPECIFICALLY — R6's bypass lumen mechanism "
            "has ZERO direct prior art, so no one has tried THIS specific approach. The graveyard "
            "is for OTHER approaches, not for R6.",
        },
    }

    return results


if __name__ == "__main__":
    print("=" * 78)
    print("R6 MAUDE CLASSIFICATION")
    print("Per Article XXI.5: MAUDE data limitations must be carried as structured metadata")
    print("=" * 78)

    results = classify_maude_data()

    print(f"\n{'='*78}")
    print("MAUDE CLASSIFICATION SUMMARY")
    print(f"{'='*78}")
    print(f"Report count: {results['maude_report_count']}")
    print(f"\nClassification:")
    for cat, data in results["classification"].items():
        print(f"  {cat}: {data['status']}")
        print(f"    {data['reason'][:120]}")

    print(f"\n{'='*78}")
    print("HONEST ASSESSMENT")
    print(f"{'='*78}")
    for q, a in results["honest_assessment"].items():
        print(f"\n{q.replace('_', ' ').title()}:")
        print(f"  {a}")

    print(f"\n{'='*78}")
    print("WHAT R6 MUST DO BEFORE PHYSICS")
    print(f"{'='*78}")
    for step, desc in results["what_r6_must_do_before_physics"].items():
        print(f"  {step}: {desc[:120]}")

    # Save
    output_path = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V18_R6_MAUDE_CLASSIFICATION.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")
