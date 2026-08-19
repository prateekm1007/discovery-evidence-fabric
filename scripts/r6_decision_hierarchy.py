#!/usr/bin/env python3
"""
R6 V21.6 — Decision Hierarchy: HARD_KILL / ENGINEERING_DEFICIENCY / CLINICAL_BUYER_TRADEOFF

Per CEO v30.21:
  "A failed engineering parameter should not automatically kill a good
   invention; a convenient parameter should not rescue a bad one."

  Distinguish:
    HARD KILL — mechanism is intrinsically unsafe/unusable
    ENGINEERING DEFICIENCY — requires redesign but doesn't kill the invention
    CLINICAL/BUYER TRADEOFF — value depends on population/workflow/risk tolerance

  Map every V21.5 metric into exactly one category.
  Freeze the decision matrix.
  Then proceed to physical execution.

Article V: "Fail closed, but do not become a universal rejector."
A protocol that kills R6 for any secondary metric failure is a universal rejector.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def decision_hierarchy():
    return {
        "task_id": "R6-V21.6-DECISION-HIERARCHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Distinguish hard kill from engineering deficiency from "
                         "clinical/buyer tradeoff. A failed engineering parameter "
                         "should not automatically kill a good invention.",
        "article_compliance": "Article V: Fail closed, but do not become a universal rejector.",
        "status": "DECISION_MATRIX_FROZEN — ready for physical execution",

        "hierarchy_definition": {
            "HARD_KILL": {
                "definition": "The mechanism is intrinsically unsafe or unusable. "
                              "No redesign, tradeoff, or clinical interpretation can "
                              "rescue it. R6 is DEAD.",
                "evidence_standard": "The evidence must establish that the failure "
                                     "makes the concept fundamentally nonviable — "
                                     "not merely suboptimal or risky.",
                "decision_authority": "The experiment alone can declare HARD_KILL. "
                                      "No buyer consultation needed.",
            },
            "ENGINEERING_DEFICIENCY": {
                "definition": "The implementation has a defect that requires redesign, "
                              "but the underlying invention concept is not logically "
                              "killed. R6 survives but needs a new design iteration + "
                              "re-test under a NEW pre-registration.",
                "evidence_standard": "The evidence must show that the failure is "
                                     "implementation-specific, not mechanism-inherent. "
                                     "A plausible alternative design must exist that "
                                     "could address the deficiency.",
                "decision_authority": "The experiment identifies the deficiency. "
                                      "The engineering team decides whether to redesign "
                                      "or abandon. If redesign: new pre-registration, "
                                      "new prototypes, new EXP-R6-01. No post-hoc "
                                      "threshold adjustment on the current data.",
            },
            "CLINICAL_BUYER_TRADEOFF": {
                "definition": "The engineering result is real and acceptable, but its "
                              "clinical value depends on population, workflow, or risk "
                              "tolerance. R6 is not killed — the buyer decides whether "
                              "the tradeoff is acceptable for the target population.",
                "evidence_standard": "The evidence must show a measurable relationship "
                                     "(e.g., flow-response curve, hysteresis loop) that "
                                     "is neither clearly safe nor clearly unsafe. The "
                                     "buyer interprets against their clinical requirements.",
                "decision_authority": "The buyer (CEO) decides. The experiment provides "
                                      "data; the buyer provides judgment. The experiment "
                                      "does NOT pre-decide what 'acceptable' means.",
            },
        },

        "metric_mapping": {

            "EXP-R6-01 opening_pressure_distribution": {
                "metric": "Opening pressure (mmHg) across 20 valves",
                "FAIL_result": "> 1/20 valves outside 15-30 mmHg OR median outside 20-25",
                "category": "HARD_KILL",
                "rationale": "If the valve cannot open in the 15-30 mmHg range, the "
                             "mechanism is intrinsically unusable. Opening too low = "
                             "chronic over-drainage during normal operation. Opening "
                             "too high = bypass never activates during obstruction. "
                             "No clinical tradeoff can rescue a valve that opens at "
                             "the wrong pressure — the physics is wrong, not the "
                             "interpretation.",
                "can_redesign_address_this": "YES — different valve geometry, material, "
                                             "or mechanism could produce different opening "
                                             "pressure. But the CURRENT design is killed. "
                                             "A redesign requires a NEW pre-registration.",
                "if_FAIL": "R6 is HARD_KILLED. Current valve design is dead. "
                           "Engineering may propose a new design iteration with a "
                           "new pre-registration. Do NOT proceed to EXP-R6-02.",
            },

            "EXP-R6-01 hysteresis": {
                "metric": "Hysteresis loop width (mmHg) = P_open - P_close",
                "FAIL_result": "Median hysteresis > 15 mmHg",
                "category": "CLINICAL_BUYER_TRADEOFF",
                "rationale": "High hysteresis means the bypass stays open after ICP "
                             "normalizes. This causes transient over-drainage. But "
                             "whether transient over-drainage is acceptable depends on: "
                             "(a) how long the bypass stays open (minutes? hours? days?), "
                             "(b) the severity of over-drainage (how far below normal ICP), "
                             "(c) the patient's tolerance for transient over-drainage vs "
                             "the benefit of obstruction prevention. This is a RISK "
                             "TRADEOFF, not an intrinsic safety failure.",
                "can_redesign_address_this": "YES — different valve designs (e.g., "
                                             "spring-loaded vs slit) have different "
                                             "hysteresis characteristics. But the "
                                             "current design's hysteresis is a DATA "
                                             "POINT, not a kill criterion.",
                "if_FAIL": "R6 is NOT killed. The hysteresis data is reported to the "
                           "buyer. The buyer decides whether the over-drainage risk is "
                           "acceptable given the obstruction-prevention benefit. If "
                           "unacceptable: engineering may redesign with lower-hysteresis "
                           "valve (NEW pre-registration).",
                "if_CONDITIONAL": "10-15 mmHg hysteresis is reported. Buyer assesses "
                                  "whether transient over-drainage in the 10-15 mmHg "
                                  "window is clinically meaningful.",
            },

            "EXP-R6-01 repeatability": {
                "metric": "Within-valve coefficient of variation (CV, %)",
                "FAIL_result": "Any valve has CV > 20%",
                "category": "ENGINEERING_DEFICIENCY",
                "rationale": "High CV means the valve opens at different pressures on "
                             "different cycles. This is a MANUFACTURING/DESIGN problem "
                             "(inconsistent valve geometry, material variation, or "
                             "mechanism instability). It does NOT mean the bypass concept "
                             "is wrong — it means THIS valve implementation is unreliable. "
                             "A different valve mechanism (e.g., spring-loaded vs slit) "
                             "could have better repeatability.",
                "can_redesign_address_this": "YES — this is exactly the kind of problem "
                                             "that redesign addresses. The mechanism "
                                             "(passive bypass lumen) is sound; the "
                                             "implementation (slit valve) may need "
                                             "improvement.",
                "if_FAIL": "R6 is NOT killed. The valve implementation is flagged as "
                           "an engineering deficiency. Engineering must propose an "
                           "alternative valve mechanism with better repeatability. "
                           "New pre-registration + new EXP-R6-01 required. "
                           "Do NOT proceed to EXP-R6-02 with an unreliable valve.",
            },

            "EXP-R6-01 drift": {
                "metric": "Opening pressure drift after 100 cycles (mmHg)",
                "FAIL_result": "Median drift > -10 mmHg OR any valve > -15 mmHg",
                "category": "ENGINEERING_DEFICIENCY",
                "rationale": "Excessive drift means the valve loosens over use. This is "
                             "a MATERIAL/DURABILITY problem (silicone relaxation, fatigue, "
                             "or wear). It does NOT mean the bypass concept is wrong — "
                             "it means THIS material/design combination is inadequate "
                             "for long-term use. A different material (e.g., PEEK, "
                             "titanium) or valve design could have better drift resistance.",
                "can_redesign_address_this": "YES — material selection and valve geometry "
                                             "directly affect drift. The bypass concept "
                                             "is sound; the material choice may need "
                                             "revision.",
                "if_FAIL": "R6 is NOT killed. The material/design is flagged as an "
                           "engineering deficiency. Engineering must propose alternative "
                           "materials or valve designs with better drift resistance. "
                           "New pre-registration + new EXP-R6-01 required.",
                "special_case": "If valve BREAKS before 100 cycles (INCONCLUSIVE → FAIL): "
                                "this is HARD_KILL. A valve that physically fails in "
                                "100 cycles is intrinsically unsafe — no redesign of "
                                "the bypass concept can rescue a valve that breaks.",
            },

            "EXP-R6-02 flow_at_25_mmhg": {
                "metric": "Steady-state bypass flow (mL/min) at 25 mmHg",
                "FAIL_result": "Flow < 0.05 mL/min (PRE-REGISTERED ENGINEERING FLOOR)",
                "category": "HARD_KILL",
                "rationale": "If bypass flow is below the engineering floor, the bypass "
                             "provides insufficient drainage for ANY plausible clinical "
                             "scenario. No clinical interpretation can rescue a bypass "
                             "that drains less than 0.05 mL/min — the physics is wrong "
                             "(lumen too small, valve too restrictive, or pressure "
                             "differential insufficient).",
                "can_redesign_address_this": "MAYBE — a larger bypass radius or lower-"
                                             "resistance valve could increase flow. But "
                                             "if the bypass radius is already at the "
                                             "maximum that fits alongside the primary "
                                             "lumen, the mechanism itself may be "
                                             "constrained. This is at the boundary between "
                                             "HARD_KILL and ENGINEERING_DEFICIENCY. "
                                             "Treat as HARD_KILL unless engineering can "
                                             "demonstrate a plausible design change that "
                                             "would increase flow above 0.05.",
                "if_FAIL": "R6 is HARD_KILLED unless engineering provides a written "
                           "rationale for why a design change would increase flow above "
                           "0.05 mL/min. If such rationale is accepted: ENGINEERING_"
                           "DEFICIENCY → new pre-registration. If not: HARD_KILL.",
            },

            "EXP-R6-03 failure_open_ratio": {
                "metric": "Bypass/primary flow ratio at normal ICP (15 mmHg)",
                "FAIL_result": "Ratio > 10%",
                "category": "CLINICAL_BUYER_TRADEOFF",
                "rationale": "A high failure-open ratio means the bypass drains too much "
                             "during normal operation IF the valve fails open. But this "
                             "only matters IF the valve actually fails open. The "
                             "question is: what is the acceptable failure-open rate, "
                             "and what is the acceptable over-drainage if it does? "
                             "This depends on: (a) valve failure-open probability "
                             "(measured in repeatability/drift tests), (b) patient "
                             "tolerance for over-drainage, (c) whether the over-drainage "
                             "is symptomatic or asymptomatic. This is a RISK TRADEOFF.",
                "if_FAIL": "R6 is NOT killed. The failure-open ratio is reported to the "
                           "buyer. The buyer decides whether the over-drainage risk is "
                           "acceptable given the valve's failure-open probability "
                           "(from repeatability/drift data).",
            },

            "EXP-R6-04 partial_obstruction_activation": {
                "metric": "Obstruction level at which bypass activates (%)",
                "FAIL_result": "Bypass does not activate until > 20% obstruction",
                "category": "CLINICAL_BUYER_TRADEOFF",
                "rationale": "If the bypass requires > 20% obstruction to activate, "
                             "patients with partial obstruction (10-20%) receive no "
                             "benefit. But whether these patients NEED benefit depends "
                             "on: (a) are they symptomatic at 10-20% obstruction? "
                             "(b) does partial obstruction progress to complete "
                             "obstruction? (c) is the sub-threshold window clinically "
                             "meaningful? This is a CLINICAL question, not an "
                             "engineering one.",
                "if_FAIL": "R6 is NOT killed. The activation threshold is reported to "
                           "the buyer. The buyer decides whether the sub-threshold "
                           "window is clinically acceptable.",
            },

            "EXP-R6-05 simultaneous_obstruction": {
                "metric": "Coverage at which bypass obstructs (%)",
                "FAIL_result": "Bypass obstructs at < 50% coverage",
                "category": "ENGINEERING_DEFICIENCY",
                "rationale": "If the bypass obstructs easily (< 50% coverage), the "
                             "spatial offset design is inadequate. But a DIFFERENT "
                             "outlet geometry (larger offset, different shape, protective "
                             "mesh) could address this. The concept (bypass with offset "
                             "outlets) is sound; the geometry is wrong.",
                "if_FAIL": "R6 is NOT killed. The outlet geometry is flagged as an "
                           "engineering deficiency. Engineering must propose an "
                           "alternative geometry. New pre-registration required.",
            },

            "EXP-R6-06 residual_volume": {
                "metric": "Residual fluid volume when bypass is closed (mL)",
                "FAIL_result": "Residual > 0.01 mL",
                "category": "ENGINEERING_DEFICIENCY",
                "rationale": "High residual volume means the bypass lumen doesn't drain "
                             "when closed. This is a DESIGN problem (closure location, "
                             "lumen geometry, drainage path). A different closure design "
                             "(distal vs proximal, or a different valve type) could "
                             "address this. The concept (bypass that drains when closed) "
                             "is sound; the implementation is wrong.",
                "if_FAIL": "R6 is NOT killed. The closure design is flagged as an "
                           "engineering deficiency. Engineering must propose an "
                           "alternative closure mechanism. New pre-registration required.",
            },

            "EXP-R6-07 primary_flow_penalty": {
                "metric": "Primary flow reduction with bypass installed (%)",
                "FAIL_result": "Flow penalty > 20%",
                "category": "HARD_KILL",
                "rationale": "If the bypass architecture reduces primary flow by > 20%, "
                             "the patient develops chronic under-drainage during NORMAL "
                             "operation. R6 trades obstruction (30-40% revision rate) "
                             "for under-drainage (symptomatic hydrocephalus). This is "
                             "a NET HARM — the 'solution' is worse than the problem. "
                             "No clinical tradeoff can rescue a design that makes "
                             "normal operation worse.",
                "can_redesign_address_this": "MAYBE — a concentric design (bypass as "
                                             "annular sleeve) should not reduce primary "
                                             "flow. If the primary flow penalty is > 20%, "
                                             "the concentric design has FAILED, which "
                                             "means the bypass does not fit without "
                                             "compromising the primary. This may be a "
                                             "fundamental geometric constraint. Treat as "
                                             "HARD_KILL unless engineering can demonstrate "
                                             "a plausible concentric design that preserves "
                                             "primary flow.",
                "if_FAIL": "R6 is HARD_KILLED unless engineering provides a written "
                           "rationale for why a design change would reduce the flow "
                           "penalty below 20%. If accepted: ENGINEERING_DEFICIENCY → "
                           "new pre-registration. If not: HARD_KILL.",
            },
        },

        "decision_matrix_summary": {
            "HARD_KILL_metrics": [
                "EXP-R6-01 opening_pressure_distribution (valve opens at wrong pressure)",
                "EXP-R6-02 flow_at_25_mmhg (flow below engineering floor)",
                "EXP-R6-07 primary_flow_penalty (bypass ruins normal operation)",
                "EXP-R6-01 drift (special case: valve physically breaks)",
            ],
            "ENGINEERING_DEFICIENCY_metrics": [
                "EXP-R6-01 repeatability (valve implementation unreliable → redesign)",
                "EXP-R6-01 drift (material loosens → new material/design)",
                "EXP-R6-05 simultaneous_obstruction (outlet geometry wrong → redesign)",
                "EXP-R6-06 residual_volume (closure design wrong → redesign)",
            ],
            "CLINICAL_BUYER_TRADEOFF_metrics": [
                "EXP-R6-01 hysteresis (transient over-drainage → risk tradeoff)",
                "EXP-R6-03 failure_open_ratio (over-drainage if valve fails → risk tradeoff)",
                "EXP-R6-04 partial_obstruction_activation (sub-threshold window → clinical question)",
            ],
            "principle": "A HARD_KILL means the mechanism is dead. An ENGINEERING_"
                         "DEFICIENCY means the implementation needs work but the "
                         "invention survives. A CLINICAL_BUYER_TRADEOFF means the "
                         "data is real and the buyer decides. "
                         "Article V: fail closed, but do not become a universal rejector.",
        },

        "overall_decision_logic": {
            "HARD_KILL": "If ANY HARD_KILL metric fails → R6 is DEAD. No further "
                         "experiments. No buyer consultation. The mechanism is "
                         "intrinsically nonviable (or the current design cannot be "
                         "rescued without a new concept).",
            "ENGINEERING_DEFICIENCY_only": "If one or more ENGINEERING_DEFICIENCY metrics "
                                           "fail but NO HARD_KILL metric fails → R6 "
                                           "SURVIVES with documented deficiencies. "
                                           "Engineering must propose redesign(s). "
                                           "New pre-registration required before re-test. "
                                           "Do NOT proceed to later experiments with "
                                           "the deficient design.",
            "CLINICAL_BUYER_TRADEOFF_only": "If one or more CLINICAL_BUYER_TRADEOFF "
                                            "metrics fail/conditional but NO HARD_KILL "
                                            "and NO ENGINEERING_DEFICIENCY → R6 "
                                            "SURVIVES. The tradeoff data is reported to "
                                            "the buyer. The buyer decides whether to "
                                            "proceed. The experiment does NOT pre-decide.",
            "MIXED": "If both ENGINEERING_DEFICIENCY and CLINICAL_BUYER_TRADEOFF metrics "
                     "fail (but no HARD_KILL) → R6 SURVIVES with both deficiencies and "
                     "tradeoffs. Engineering addresses deficiencies; buyer addresses "
                     "tradeoffs. Both must be resolved before clinical translation.",
            "ALL_PASS": "If all metrics pass (including CONDITIONAL accepted by buyer) → "
                        "R6 passes EXP-R6-01. Proceed to EXP-R6-02 (flow-response curve).",
        },

        "frozen": {
            "date": datetime.now(timezone.utc).isoformat(),
            "commitment": "This decision matrix is FROZEN. The mapping of metrics to "
                          "categories (HARD_KILL / ENGINEERING_DEFICIENCY / CLINICAL_"
                          "BUYER_TRADEOFF) cannot be changed after data collection. "
                          "Per Article VII: no post-hoc reclassification of a failed "
                          "metric from HARD_KILL to ENGINEERING_DEFICIENCY to rescue R6. "
                          "Per Article V: no universal rejection — a secondary metric "
                          "failure does not automatically kill R6 unless it is mapped "
                          "to HARD_KILL in this frozen matrix.",
            "principle": "A failed engineering parameter should not automatically kill "
                         "a good invention; a convenient parameter should not rescue "
                         "a bad one.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V21.6 — DECISION HIERARCHY (HARD_KILL / ENGINEERING_DEFICIENCY / CLINICAL_BUYER_TRADEOFF)")
    print("=" * 78)

    results = decision_hierarchy()

    print("\nMETRIC MAPPING:")
    for metric, mapping in results["metric_mapping"].items():
        print(f"\n  {metric}")
        print(f"    Category: {mapping['category']}")
        print(f"    FAIL result: {mapping['FAIL_result'][:80]}...")
        print(f"    Rationale: {mapping['rationale'][:100]}...")
        if "if_FAIL" in mapping:
            print(f"    If FAIL: {mapping['if_FAIL'][:100]}...")

    s = results["decision_matrix_summary"]
    print(f"\n{'='*78}")
    print("DECISION MATRIX SUMMARY")
    print(f"{'='*78}")
    print(f"  HARD_KILL ({len(s['HARD_KILL_metrics'])} metrics):")
    for m in s["HARD_KILL_metrics"]:
        print(f"    - {m}")
    print(f"  ENGINEERING_DEFICIENCY ({len(s['ENGINEERING_DEFICIENCY_metrics'])} metrics):")
    for m in s["ENGINEERING_DEFICIENCY_metrics"]:
        print(f"    - {m}")
    print(f"  CLINICAL_BUYER_TRADEOFF ({len(s['CLINICAL_BUYER_TRADEOFF_metrics'])} metrics):")
    for m in s["CLINICAL_BUYER_TRADEOFF_metrics"]:
        print(f"    - {m}")

    print(f"\n{'='*78}")
    print("OVERALL DECISION LOGIC")
    print(f"{'='*78}")
    for scenario, logic in results["overall_decision_logic"].items():
        print(f"  {scenario}: {logic[:100]}...")

    print(f"\nFROZEN: {results['frozen']['commitment'][:100]}...")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V21_6_R6_DECISION_HIERARCHY.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
