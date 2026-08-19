#!/usr/bin/env python3
"""
R6 V22 — Experiment Ontology: Concept → Mechanism → Embodiment → Prototype → Experiment → Result

Per CEO v30.25:
  "Prototype failure ≠ embodiment failure ≠ mechanism failure ≠ invention failure.
   The decision engine must require separate evidence before promoting a failure
   upward through those levels."

  "EXP-R6-01 tests the first embodiment, not 'R6.'"

  "Make the experiment as narrow as possible, but make the inference as
   precise as necessary."

This is the FINAL software artifact before physical execution.
After this commit: STOP coding. Fabricate. Measure. Report.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def experiment_ontology():
    return {
        "task_id": "R6-V22-EXPERIMENT-ONTOLOGY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Prototype failure ≠ embodiment failure ≠ mechanism failure "
                         "≠ invention failure. Require separate evidence before "
                         "promoting a failure upward through those levels.",
        "status": "ONTOLOGY_FROZEN — this is the final software artifact before "
                  "physical execution. STOP coding. Fabricate. Measure. Report.",

        "ontology": {
            "INVENTION_CONCEPT": {
                "definition": "The abstract idea — a passive bypass lumen in a CSF "
                              "shunt that opens when the primary lumen obstructs, "
                              "restoring drainage without clearing the obstruction.",
                "R6_concept": "Passive bypass lumen for CSF shunt obstruction",
                "what_failure_here_means": "The concept itself is flawed — no "
                                           "implementation of passive bypass can "
                                           "solve the obstruction problem. This "
                                           "requires evidence that the CONCEPT is "
                                           "intrinsically nonviable, not just that "
                                           "one implementation failed.",
                "evidence_required_to_declare_failure": "Design-space exhaustion "
                    "across ALL plausible mechanisms + ALL plausible embodiments, "
                    "OR an invariant proof showing the concept is physically "
                    "impossible. A single embodiment failure NEVER reaches this "
                    "level.",
            },
            "MECHANISM": {
                "definition": "The physical principle by which the concept is "
                              "realized — pressure-activated secondary flow path.",
                "R6_mechanism": "Pressure-activated secondary flow path (bypass "
                                "opens when primary obstructs due to pressure "
                                "differential)",
                "what_failure_here_means": "The pressure-activation principle "
                                           "cannot work — no pressure-activated "
                                           "valve can achieve the required opening "
                                           "pressure, flow, or reliability in the "
                                           "bypass geometry. This requires evidence "
                                           "that ALL pressure-activated valve "
                                           "mechanisms fail, not just one type.",
                "evidence_required_to_declare_failure": "All enumerated mechanism "
                    "classes (elastic deformation, spring-loaded, surface tension, "
                    "+ re-evaluation of omitted classes) have been tested or shown "
                    "infeasible. A single mechanism class failure NEVER reaches "
                    "this level.",
            },
            "EMBODIMENT": {
                "definition": "A specific implementation of the mechanism — "
                              "silicone slit valve in a 0.25mm bypass lumen.",
                "R6_embodiment_1": "Silicone slit valve, 0.25mm radius bypass, "
                                    "200mm length, concentric design, medical-grade "
                                    "silicone Shore 50A, injection-molded",
                "what_failure_here_means": "THIS specific implementation (slit "
                                           "valve in silicone at this geometry) is "
                                           "inadequate. A different embodiment "
                                           "(duckbill, spring, membrane, or slit "
                                           "in different material/geometry) could "
                                           "still succeed.",
                "evidence_required_to_declare_failure": "EXP-R6-01 results show "
                    "that the slit valve embodiment fails one or more metrics. "
                    "This is an EMBODIMENT failure, not a mechanism or concept "
                    "failure. The next embodiment requires a NEW pre-registration.",
            },
            "PROTOTYPE": {
                "definition": "An individual physical unit — one of 20 valves "
                              "manufactured from the same lot.",
                "R6_prototypes": "P01 through P20, from LOT-{date}-001, "
                                 "injection-molded silicone slit valves",
                "what_failure_here_means": "ONE individual valve is defective or "
                                           "out of spec. This is a MANUFACTURING "
                                           "defect, not an embodiment failure. "
                                           "Other prototypes from the same lot may "
                                           "perform differently.",
                "evidence_required_to_declare_failure": "Individual prototype "
                    "failure is RECORDED but does NOT constitute embodiment "
                    "failure unless the failure rate exceeds the pre-registered "
                    "threshold (e.g., >1/20 for opening pressure). A single "
                    "prototype failure is INFORMATION, not a verdict.",
            },
            "EXPERIMENT": {
                "definition": "The pre-registered test protocol applied to the "
                              "prototype set.",
                "R6_experiment_1": "EXP-R6-01: 4 measurements (distribution + "
                                   "hysteresis + repeatability + drift) on 20 "
                                   "prototypes, per V21.1-V21.9 protocol",
                "what_failure_here_means": "The experiment itself may have "
                                           "calibration issues (INCONCLUSIVE), "
                                           "or the results may show PASS, "
                                           "CONDITIONAL, or FAIL for the embodiment.",
                "evidence_required_to_declare_failure": "Calibration check (positive "
                    "control) must pass. If calibration fails: INCONCLUSIVE, repeat. "
                    "If calibration passes: results are VALID for the embodiment level.",
            },
            "RESULT": {
                "definition": "The measured outcome — raw data + statistical "
                              "interpretation against the frozen thresholds.",
                "R6_result_1": "TBD — will be raw measurements from EXP-R6-01, "
                               "analyzed against V21.5 no-gap thresholds, "
                               "interpreted via V21.7 causal decision hierarchy",
                "what_failure_here_means": "The RESULT is a measurement. It tells "
                                           "us about the EMBODIMENT, not about the "
                                           "MECHANISM or CONCEPT. The result must "
                                           "be interpreted at the correct level.",
                "evidence_required_to_declare_failure": "The result is DATA, not a "
                    "failure declaration. The result feeds into the decision matrix "
                    "which determines whether the EMBODIMENT passes or fails. The "
                    "result itself does not declare failure at any level.",
            },
        },

        "failure_promotion_rules": {
            "principle": "A failure at one level does NOT automatically promote "
                         "to the next level. Each promotion requires SEPARATE "
                         "EVIDENCE.",

            "prototype_to_embodiment": {
                "rule": "A single prototype failure (e.g., P03 opens at 35 mmHg) "
                        "is recorded as PROTOTYPE-level data. It promotes to "
                        "EMBODIMENT-level failure ONLY if the failure rate "
                        "exceeds the pre-registered threshold (>1/20 for opening "
                        "pressure, >50% for any single secondary metric).",
                "example": "If 1/20 valves opens outside 15-30 mmHg → PROTOTYPE "
                           "failure recorded, EMBODIMENT PASSES (≤1/20 allowed). "
                           "If 3/20 valves open outside range → EMBODIMENT FAILS "
                           "(>1/20 threshold exceeded).",
            },
            "embodiment_to_mechanism": {
                "rule": "An embodiment failure (e.g., slit valve opens at wrong "
                        "pressure) promotes to MECHANISM-level failure ONLY if "
                        "ALL plausible embodiments of the same mechanism class "
                        "have been tested or shown infeasible. A single embodiment "
                        "failure does NOT promote.",
                "example": "Slit valve fails → try duckbill (new pre-registration). "
                           "If duckbill also fails → try spring valve. If ALL "
                           "enumerated mechanisms fail → MECHANISM failure. "
                           "If ANY mechanism passes → MECHANISM survives.",
            },
            "mechanism_to_concept": {
                "rule": "A mechanism failure promotes to CONCEPT-level failure "
                        "ONLY if the design space is EXHAUSTED (all mechanism "
                        "classes tested or shown infeasible, including omitted "
                        "classes re-evaluated) OR an invariant proof shows the "
                        "concept is physically impossible.",
                "example": "If all 5 mechanism classes fail → CONCEPT failure "
                           "(R6 is dead). If any class is untested → CONCEPT "
                           "survives (design space not exhausted).",
            },
            "concept_to_invention": {
                "rule": "The concept IS the invention. If the concept fails, "
                        "R6 is dead. There is no higher level to promote to.",
            },
        },

        "exp_r6_01_ontology_binding": {
            "CONCEPT": "Passive bypass lumen for CSF shunt obstruction",
            "MECHANISM": "Pressure-activated secondary flow path",
            "EMBODIMENT": "Silicone slit valve, 0.25mm bypass radius, 200mm length, concentric",
            "PROTOTYPES": "P01-P20 from LOT-{fabrication_date}-001",
            "EXPERIMENT": "EXP-R6-01 (4 measurements: distribution + hysteresis + repeatability + drift)",
            "RESULT": "TBD — raw measurements will be recorded and interpreted against frozen thresholds",

            "what_EXP_R6_01_tests": "EXP-R6-01 tests the SILICONE SLIT VALVE "
                                    "EMBODIMENT of the PRESSURE-ACTIVATED MECHANISM "
                                    "of the PASSIVE BYPASS LUMEN CONCEPT.",
            "what_EXP_R6_01_does_NOT_test": ("EXP-R6-01 does NOT test: "
                "- Other valve mechanisms (duckbill, spring, membrane); "
                "- Other bypass radii (0.35, 0.50, 0.75mm); "
                "- Other materials (PEEK, titanium, PEBAX); "
                "- Other geometries (parallel, figure-8); "
                "- In-vivo performance; "
                "- Long-term biological degradation; "
                "- Clinical outcomes"),

            "interpretation_rule": "When reporting EXP-R6-01 results, the report "
                                   "MUST state: 'These results apply to the "
                                   "[EMBODIMENT: silicone slit valve at 0.25mm]. "
                                   "They do NOT constitute evidence about the "
                                   "[MECHANISM: pressure-activated flow path] or "
                                   "[CONCEPT: passive bypass lumen] beyond what "
                                   "this specific embodiment demonstrates. "
                                   "Failure of this embodiment does not imply "
                                   "failure of the mechanism or concept.'",

            "mechanical_enforcement": "The raw-data schema (V21.2 pre-registered) "
                                      "includes a mandatory field 'result_scope' "
                                      "that must be set to 'EMBODIMENT_LEVEL' for "
                                      "all EXP-R6-01 results. This prevents the "
                                      "reporting system from accidentally "
                                      "promoting embodiment-level results to "
                                      "mechanism-level or concept-level claims.",
        },

        "final_declaration": {
            "date": datetime.now(timezone.utc).isoformat(),
            "statement": ("The R6 experimental protocol is COMPLETE. 10 iterations "
                         "of hardening (V21 through V22) have produced a "
                         "pre-registered, evidence-bound, causally-disciplined "
                         "protocol with: "
                         "- No PASS/FAIL gaps (V21.5); "
                         "- Causal decision hierarchy (V21.7); "
                         "- Design-space enumeration with provenance (V21.8-V21.9); "
                         "- All model predictions labeled (V21.9); "
                         "- Experiment ontology with failure-level separation (V22). "
                         "NO FURTHER SOFTWARE ITERATION is warranted before physical "
                         "data. The next action is: "
                         "1. Fabricate 20 slit-valve prototypes; "
                         "2. Execute EXP-R6-01 exactly as pre-registered; "
                         "3. Record raw measurements; "
                         "4. Apply frozen decision matrix; "
                         "5. Report results at the EMBODIMENT level. "
                         "A model can tell us what might work. "
                         "Only reality can tell us what works."),

            "stop_coding": True,
            "next_action": "PHYSICAL: fabricate and test",
            "no_silent_redesign": True,
            "no_threshold_changes": True,
            "no_retrospective_model_tuning": True,
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V22 — EXPERIMENT ONTOLOGY (FINAL SOFTWARE ARTIFACT)")
    print("Prototype failure ≠ embodiment failure ≠ mechanism failure ≠ invention failure")
    print("=" * 78)

    results = experiment_ontology()

    print("\nONTOLOGY HIERARCHY:")
    for level, data in results["ontology"].items():
        print(f"\n  {level}")
        print(f"    Definition: {data['definition'][:100]}...")
        print(f"    Failure means: {data['what_failure_here_means'][:100]}...")
        print(f"    Evidence to declare: {data['evidence_required_to_declare_failure'][:100]}...")

    print(f"\n{'='*78}")
    print("FAILURE PROMOTION RULES:")
    for transition, rule in results["failure_promotion_rules"].items():
        if isinstance(rule, dict) and "rule" in rule:
            print(f"\n  {transition}:")
            print(f"    Rule: {rule['rule'][:100]}...")
            if "example" in rule:
                print(f"    Example: {rule['example'][:100]}...")

    print(f"\n{'='*78}")
    print("EXP-R6-01 ONTOLOGY BINDING:")
    ob = results["exp_r6_01_ontology_binding"]
    print(f"  CONCEPT: {ob['CONCEPT']}")
    print(f"  MECHANISM: {ob['MECHANISM']}")
    print(f"  EMBODIMENT: {ob['EMBODIMENT']}")
    print(f"  PROTOTYPES: {ob['PROTOTYPES']}")
    print(f"  EXPERIMENT: {ob['EXPERIMENT']}")
    print(f"  RESULT: {ob['RESULT']}")
    print(f"\n  What it tests: {ob['what_EXP_R6_01_tests'][:100]}...")
    print(f"  What it does NOT test: {ob['what_EXP_R6_01_does_NOT_test'][:100]}...")
    print(f"\n  Interpretation rule: {ob['interpretation_rule'][:100]}...")

    print(f"\n{'='*78}")
    fd = results["final_declaration"]
    print(f"FINAL DECLARATION:")
    print(f"  {fd['statement'][:200]}...")
    print(f"\n  STOP CODING: {fd['stop_coding']}")
    print(f"  NEXT ACTION: {fd['next_action']}")
    print(f"  NO SILENT REDESIGN: {fd['no_silent_redesign']}")
    print(f"  NO THRESHOLD CHANGES: {fd['no_threshold_changes']}")
    print(f"  NO RETROSPECTIVE MODEL TUNING: {fd['no_retrospective_model_tuning']}")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V22_R6_EXPERIMENT_ONTOLOGY.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
