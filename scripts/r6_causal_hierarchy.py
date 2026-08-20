#!/usr/bin/env python3
"""
R6 V21.7 — Causal Decision Hierarchy Correction

Per CEO v30.22:
  "Kill the mechanism only when the evidence kills the mechanism.
   Kill an implementation when the evidence kills the implementation."

The V21.6 hierarchy was partly circular:
  - flow < 0.05 was called HARD_KILL but was previously classified as
    PROVISIONAL ENGINEERING FLOOR with 5 explicit contingencies
  - 100-cycle break was called HARD_KILL but may be an implementation
    failure (material/geometry) not a mechanism failure

A genuinely HARD_KILL should be:
  "The invention CONCEPT ITSELF cannot satisfy the essential requirement."
  Not: "This implementation produced a bad number."

Reclassification using the causal rule:
  HARD_KILL → only when evidence shows the MECHANISM cannot perform
              its essential function even under the intended envelope
  ENGINEERING_DEFICIENCY → failure belongs to the IMPLEMENTATION and
              could plausibly be repaired without changing the core
              causal mechanism
  CLINICAL_BUYER_TRADEOFF → engineering performance is real; value
              depends on population/workflow/risk/economics
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def causal_hierarchy_correction():
    return {
        "task_id": "R6-V21.7-CAUSAL-HIERARCHY-CORRECTION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Kill the mechanism only when the evidence kills the "
                         "mechanism. Kill an implementation when the evidence "
                         "kills the implementation.",
        "supersedes": "V21_6_R6_DECISION_HIERARCHY.json (V21.6 was partly circular)",
        "status": "CAUSAL_HIERARCHY_FROZEN — ready for physical execution",

        "causal_rule": {
            "HARD_KILL": "Evidence shows the INVENTION CONCEPT ITSELF cannot "
                         "satisfy the essential requirement. No plausible "
                         "implementation of the same causal mechanism (passive "
                         "bypass lumen that opens when primary obstructs) could "
                         "achieve the required performance. The mechanism is "
                         "dead, not just this implementation.",
            "ENGINEERING_DEFICIENCY": "The observed failure belongs to the "
                                      "IMPLEMENTATION and could plausibly be "
                                      "repaired without changing the invention's "
                                      "core causal mechanism (passive bypass "
                                      "lumen). A different valve design, material, "
                                      "geometry, or manufacturing process could "
                                      "address the deficiency.",
            "CLINICAL_BUYER_TRADEOFF": "Engineering performance is real and "
                                       "measurable. Whether it is valuable depends "
                                       "on patient population, clinical workflow, "
                                       "risk tolerance, or economics. The buyer "
                                       "interprets the data against their clinical "
                                       "requirements (which are PROVISIONAL).",
            "test_for_hard_kill": "Ask: 'Could a DIFFERENT implementation of "
                                  "passive bypass lumen (different valve type, "
                                  "different material, different geometry) plausibly "
                                  "achieve the required performance?' If YES → "
                                  "ENGINEERING_DEFICIENCY. If NO (the physics of "
                                  "passive bypass prevents it) → HARD_KILL.",
        },

        "reclassified_metrics": {

            "EXP-R6-01 opening_pressure_distribution": {
                "old_classification": "HARD_KILL",
                "new_classification": "ENGINEERING_DEFICIENCY",
                "metric": "Opening pressure (mmHg) across 20 valves",
                "FAIL_result": "> 1/20 valves outside 15-30 mmHg OR median outside 20-25",
                "causal_analysis": "If the slit valve opens at the wrong pressure, "
                                   "the question is: could a DIFFERENT valve mechanism "
                                   "(spring-loaded, diaphragm, ball-in-cage, "
                                   "hydrophobic membrane) open at 20-25 mmHg? YES — "
                                   "commercial CSF shunt valves (Medtronic Strata, "
                                   "Codman Hakim, Sophysa Polaris) already achieve "
                                   "precisely this range using different mechanisms. "
                                   "The passive bypass lumen CONCEPT does not require "
                                   "a slit valve specifically. The failure is in the "
                                   "IMPLEMENTATION (slit valve design), not the "
                                   "MECHANISM (passive bypass that opens at obstruction "
                                   "pressure).",
                "test_for_hard_kill": "Could a different valve mechanism open at "
                                      "20-25 mmHg? YES (commercial shunt valves do "
                                      "this). → ENGINEERING_DEFICIENCY.",
                "if_FAIL": "R6 is NOT killed. The slit valve implementation is "
                           "flagged as deficient. Engineering must propose an "
                           "alternative valve mechanism. New pre-registration "
                           "required. Do NOT proceed to EXP-R6-02 with a valve "
                           "that opens at the wrong pressure.",
                "special_case_hard_kill": "If ALL plausible valve mechanisms "
                                          "(slit, spring, diaphragm, membrane, "
                                          "ball-in-cage) fail to open at 15-30 mmHg "
                                          "in the bypass lumen geometry → HARD_KILL. "
                                          "But this would require testing multiple "
                                          "valve types, not just one. A single slit "
                                          "valve failure is ENGINEERING_DEFICIENCY.",
            },

            "EXP-R6-02 flow_at_25_mmhg": {
                "old_classification": "HARD_KILL",
                "new_classification": "PROVISIONAL_ENGINEERING_FLOOR",
                "metric": "Steady-state bypass flow (mL/min) at 25 mmHg",
                "FAIL_result": "Flow < 0.05 mL/min (PRE-REGISTERED ENGINEERING FLOOR)",
                "causal_analysis": "The 0.05 threshold was previously classified as "
                                   "PROVISIONAL with 5 explicit contingencies "
                                   "(target_population, compliance_envelope, "
                                   "danger_threshold, access_to_care, CSF_production). "
                                   "V21.6 incorrectly reclassified it as HARD_KILL, "
                                   "creating a circular conflict with V21.4's "
                                   "provisional classification. The causal question "
                                   "is: could a LARGER bypass lumen or LOWER-resistance "
                                   "valve produce more flow? YES — the Poiseuille "
                                   "equation shows flow scales as r^4. A 2x larger "
                                   "radius gives 16x more flow. The constraint is "
                                   "whether a larger bypass fits alongside the primary "
                                   "lumen — a GEOMETRIC constraint, not a mechanism "
                                   "impossibility.",
                "test_for_hard_kill": "Could a larger bypass lumen produce > 0.05 "
                                      "mL/min? YES (Poiseuille: r=0.5mm gives 100x "
                                      "more flow than r=0.25mm). The question is "
                                      "whether it FITS — which is an engineering "
                                      "constraint, not a mechanism impossibility. "
                                      "→ PROVISIONAL_ENGINEERING_FLOOR, not HARD_KILL.",
                "if_FAIL": "R6 is NOT hard-killed. The flow is below the provisional "
                           "engineering floor. This is treated as a CONDITIONAL_FAIL "
                           "pending: (a) buyer confirmation that 0.05 is the correct "
                           "floor for the target population, (b) engineering assessment "
                           "of whether a larger bypass lumen is geometrically feasible. "
                           "If the buyer confirms 0.05 AND engineering confirms no "
                           "larger lumen fits → HARD_KILL. Otherwise → ENGINEERING_"
                           "DEFICIENCY (redesign with larger lumen).",
                "contingencies_preserved": "The 5 contingencies from V21.4 are "
                                           "preserved: target_population, "
                                           "compliance_envelope, danger_threshold, "
                                           "access_to_care_requirement, CSF_production.",
            },

            "EXP-R6-07 primary_flow_penalty": {
                "old_classification": "HARD_KILL",
                "new_classification": "ENGINEERING_DEFICIENCY",
                "metric": "Primary flow reduction with bypass installed (%)",
                "FAIL_result": "Flow penalty > 20%",
                "causal_analysis": "If the bypass architecture reduces primary flow by "
                                   "> 20%, the question is: could a DIFFERENT "
                                   "architecture (concentric sleeve, external parallel "
                                   "channel, different cross-section) preserve primary "
                                   "flow? YES — the V20 model assumed a concentric "
                                   "design with no primary radius reduction. If the "
                                   "concentric design fails, other architectures "
                                   "(external parallel channel, figure-8 cross-section) "
                                   "could be tried. The passive bypass lumen CONCEPT "
                                   "does not require a specific cross-section. The "
                                   "failure is in the IMPLEMENTATION (this specific "
                                   "cross-section), not the MECHANISM.",
                "test_for_hard_kill": "Could a different cross-section preserve "
                                      "primary flow? YES (concentric, parallel, "
                                      "figure-8). → ENGINEERING_DEFICIENCY.",
                "if_FAIL": "R6 is NOT killed. The cross-section design is flagged "
                           "as deficient. Engineering must propose an alternative "
                           "architecture. New pre-registration required.",
                "special_case_hard_kill": "If ALL plausible cross-sections (concentric, "
                                          "parallel, figure-8, multi-lumen) reduce "
                                          "primary flow by > 20% → HARD_KILL. But "
                                          "this requires testing multiple geometries. "
                                          "A single cross-section failure is "
                                          "ENGINEERING_DEFICIENCY.",
            },

            "EXP-R6-01 drift_valve_breaks": {
                "old_classification": "HARD_KILL (special case)",
                "new_classification": "ENGINEERING_DEFICIENCY (with escalation rule)",
                "metric": "Valve physically breaks before 100 cycles",
                "FAIL_result": "Valve fails structurally during 100-cycle screen",
                "causal_analysis": "If the valve breaks, the question is: WHY did it "
                                   "break? (a) Material failure (silicone fatigue) → "
                                   "different material (PEEK, titanium) could fix. "
                                   "(b) Geometric stress concentration → different "
                                   "geometry could fix. (c) The bypass lumen "
                                   "concept intrinsically requires a component that "
                                   "cannot survive cyclic loading → this would be "
                                   "HARD_KILL, but only if ALL valve mechanisms fail "
                                   "structurally, not just one.",
                "test_for_hard_kill": "Did the valve break because of a material/"
                                      "geometry issue (ENGINEERING_DEFICIENCY) or "
                                      "because the bypass concept intrinsically "
                                      "requires a fragile component (HARD_KILL)? "
                                      "A single material failure is ENGINEERING_"
                                      "DEFICIENCY. Only if the FAILURE ANALYSIS "
                                      "shows that no plausible valve mechanism can "
                                      "survive cyclic loading in the bypass lumen "
                                      "geometry → HARD_KILL.",
                "if_FAIL": "R6 is NOT automatically killed. The valve failure "
                           "triggers a FAILURE ANALYSIS (root cause investigation). "
                           "If root cause is material/geometry → ENGINEERING_"
                           "DEFICIENCY (redesign with different material/geometry). "
                           "If root cause shows intrinsic mechanism impossibility "
                           "→ HARD_KILL.",
                "escalation_rule": "If 3+ different valve designs (different "
                                   "materials AND mechanisms) all break in <100 "
                                   "cycles → escalate to HARD_KILL (the bypass "
                                   "lumen environment is intrinsically hostile to "
                                   "valve survival). A single design failure does "
                                   "NOT escalate.",
            },

            # Metrics that remain unchanged from V21.6

            "EXP-R6-01 hysteresis": {
                "old_classification": "CLINICAL_BUYER_TRADEOFF",
                "new_classification": "CLINICAL_BUYER_TRADEOFF (unchanged)",
                "rationale": "Hysteresis is a risk tradeoff, not a mechanism failure. "
                             "The bypass concept works; the question is whether "
                             "transient over-drainage is acceptable.",
            },
            "EXP-R6-01 repeatability": {
                "old_classification": "ENGINEERING_DEFICIENCY",
                "new_classification": "ENGINEERING_DEFICIENCY (unchanged)",
                "rationale": "Unreliable opening pressure is an implementation problem. "
                             "Different valve mechanisms have different repeatability.",
            },
            "EXP-R6-01 drift_material": {
                "old_classification": "ENGINEERING_DEFICIENCY",
                "new_classification": "ENGINEERING_DEFICIENCY (unchanged)",
                "rationale": "Material loosening is an implementation problem. "
                             "Different materials have different drift characteristics.",
            },
            "EXP-R6-03 failure_open_ratio": {
                "old_classification": "CLINICAL_BUYER_TRADEOFF",
                "new_classification": "CLINICAL_BUYER_TRADEOFF (unchanged)",
                "rationale": "Over-drainage risk depends on failure probability and "
                             "patient tolerance — buyer decides.",
            },
            "EXP-R6-04 partial_obstruction_activation": {
                "old_classification": "CLINICAL_BUYER_TRADEOFF",
                "new_classification": "CLINICAL_BUYER_TRADEOFF (unchanged)",
                "rationale": "Sub-threshold window is a clinical question about "
                             "which patients need benefit.",
            },
            "EXP-R6-05 simultaneous_obstruction": {
                "old_classification": "ENGINEERING_DEFICIENCY",
                "new_classification": "ENGINEERING_DEFICIENCY (unchanged)",
                "rationale": "Outlet geometry is an implementation choice. Different "
                             "geometries could prevent common-mode failure.",
            },
            "EXP-R6-06 residual_volume": {
                "old_classification": "ENGINEERING_DEFICIENCY",
                "new_classification": "ENGINEERING_DEFICIENCY (unchanged)",
                "rationale": "Closure design is an implementation choice. Different "
                             "closure mechanisms could drain the lumen.",
            },
        },

        "revised_decision_matrix_summary": {
            "HARD_KILL": "NONE in the initial protocol. HARD_KILL is only declared "
                         "after: (a) multiple implementation attempts fail, OR "
                         "(b) failure analysis shows intrinsic mechanism impossibility, "
                         "OR (c) the buyer confirms a provisional floor AND "
                         "engineering confirms no plausible design can meet it. "
                         "This prevents the engine from killing a good invention "
                         "because the first embodiment was poor (Article V).",
            "PROVISIONAL_ENGINEERING_FLOOR": [
                "EXP-R6-02 flow < 0.05 mL/min (5 contingencies, buyer + engineering "
                "must confirm before escalating to HARD_KILL)",
            ],
            "ENGINEERING_DEFICIENCY": [
                "EXP-R6-01 opening_pressure (different valve mechanism could fix)",
                "EXP-R6-01 repeatability (different valve mechanism could fix)",
                "EXP-R6-01 drift_material (different material could fix)",
                "EXP-R6-01 drift_valve_breaks (failure analysis required; different "
                "material/geometry could fix; 3+ failures escalate to HARD_KILL)",
                "EXP-R6-05 simultaneous_obstruction (different geometry could fix)",
                "EXP-R6-06 residual_volume (different closure could fix)",
                "EXP-R6-07 primary_flow_penalty (different cross-section could fix)",
            ],
            "CLINICAL_BUYER_TRADEOFF": [
                "EXP-R6-01 hysteresis (transient over-drainage → risk tradeoff)",
                "EXP-R6-03 failure_open_ratio (over-drainage if valve fails → risk tradeoff)",
                "EXP-R6-04 partial_obstruction_activation (sub-threshold window → clinical question)",
            ],
        },

        "revised_overall_decision_logic": {
            "PROVISIONAL_FLOOR_FAIL": "If flow < 0.05 mL/min: R6 is NOT hard-killed. "
                                      "CONDITIONAL_FAIL pending buyer confirmation of "
                                      "the floor AND engineering assessment of whether "
                                      "a larger lumen is feasible. If both confirm → "
                                      "HARD_KILL. If either provides a path forward → "
                                      "ENGINEERING_DEFICIENCY (redesign).",
            "ENGINEERING_DEFICIENCY_only": "R6 SURVIVES with documented deficiency. "
                                           "Engineering proposes redesign. New "
                                           "pre-registration + re-test required.",
            "CLINICAL_BUYER_TRADEOFF_only": "R6 SURVIVES. Buyer interprets the data "
                                            "against their clinical requirements.",
            "MIXED": "R6 SURVIVES. Both deficiency and tradeoff must be resolved "
                     "before clinical translation.",
            "ALL_PASS": "Proceed to EXP-R6-02.",
            "HARD_KILL_ESCALATION": "HARD_KILL is declared only when: "
                                     "(a) 3+ different implementation attempts fail "
                                     "for the same metric, OR "
                                     "(b) failure analysis shows the bypass lumen "
                                     "concept intrinsically cannot achieve the "
                                     "requirement, OR "
                                     "(c) the buyer confirms a provisional floor AND "
                                     "engineering confirms no plausible design meets it. "
                                     "A single implementation failure NEVER escalates "
                                     "to HARD_KILL for ENGINEERING_DEFICIENCY metrics.",
        },

        "frozen": {
            "date": datetime.now(timezone.utc).isoformat(),
            "commitment": "This causal decision hierarchy is FROZEN. The causal rule "
                          "(kill mechanism only when evidence kills mechanism; kill "
                          "implementation when evidence kills implementation) governs "
                          "all post-data interpretation. No post-hoc reclassification "
                          "(Article VII). No universal rejection (Article V). "
                          "A single poor embodiment does not kill a good invention.",
            "principle": "Kill the mechanism only when the evidence kills the mechanism. "
                         "Kill an implementation when the evidence kills the implementation.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V21.7 — CAUSAL DECISION HIERARCHY CORRECTION")
    print("Kill the mechanism only when the evidence kills the mechanism.")
    print("=" * 78)

    results = causal_hierarchy_correction()

    print("\nRECLASSIFIED METRICS:")
    for metric, m in results["reclassified_metrics"].items():
        old = m.get("old_classification", "?")
        new = m.get("new_classification", "?")
        changed = "CHANGED" if old != new else "unchanged"
        print(f"\n  {metric}")
        print(f"    {old} → {new} ({changed})")
        if "causal_analysis" in m:
            print(f"    Causal: {m['causal_analysis'][:120]}...")
        if "test_for_hard_kill" in m:
            print(f"    Test: {m['test_for_hard_kill'][:120]}...")

    s = results["revised_decision_matrix_summary"]
    print(f"\n{'='*78}")
    print("REVISED DECISION MATRIX")
    print(f"{'='*78}")
    print(f"  HARD_KILL: {s['HARD_KILL'][:120]}...")
    print(f"  PROVISIONAL_ENGINEERING_FLOOR: {len(s['PROVISIONAL_ENGINEERING_FLOOR'])} metric(s)")
    print(f"  ENGINEERING_DEFICIENCY: {len(s['ENGINEERING_DEFICIENCY'])} metric(s)")
    print(f"  CLINICAL_BUYER_TRADEOFF: {len(s['CLINICAL_BUYER_TRADEOFF'])} metric(s)")

    print(f"\n{'='*78}")
    print("REVISED DECISION LOGIC")
    print(f"{'='*78}")
    for scenario, logic in results["revised_overall_decision_logic"].items():
        print(f"  {scenario}: {logic[:100]}...")

    print(f"\nFROZEN: {results['frozen']['principle']}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V21_7_R6_CAUSAL_HIERARCHY.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
