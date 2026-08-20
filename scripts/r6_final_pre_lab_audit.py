#!/usr/bin/env python3
"""
R6 V21.9 — Final Pre-Lab Audit: Model Labeling + Design-Space Completeness + Hypothesis Freeze

Per CEO v30.24:
  "A model can tell us what might work. Only reality can tell us what works."
  "The invention engine should never let its own candidate enumeration
   become an invisible boundary around what is possible."

This is the FINAL pre-lab audit. After this commit:
  1. Fabricate 20 slit-valve prototypes
  2. Execute EXP-R6-01 exactly as pre-registered
  3. Record raw measurements before interpretation
  4. If slit valve fails: new pre-registration for next mechanism (no silent redesign)
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def final_pre_lab_audit():
    return {
        "task_id": "R6-V21.9-FINAL-PRE-LAB-AUDIT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "A model can tell us what might work. Only reality can tell "
                         "us what works. This is the final pre-lab audit.",
        "status": "HYPOTHESIS_FROZEN — ready for physical execution of EXP-R6-01",

        "correction_1_model_labels": {
            "problem": "V21.8 said '0.35-0.50mm would provide adequate flow.' This is "
                       "a MODEL prediction presented with too much confidence. The "
                       "flow values come from Poiseuille — they are NOT demonstrated "
                       "achievable designs.",
            "correction": "Every radius/flow result is now explicitly labeled "
                          "MODEL_PREDICTION. No radius/flow combination is called "
                          "'feasible' or 'adequate' until experimentally demonstrated.",

            "relabeled_predictions": [
                {
                    "radius_mm": 0.15,
                    "label": "MODEL_PREDICTION",
                    "model_flow_ml_min": 0.012,
                    "model_assumptions": "Poiseuille, laminar flow, no entrance effects, "
                                         "no valve resistance, water viscosity, 25 mmHg, 200mm length",
                    "NOT_yet_demonstrated": [
                        "can be manufactured at this radius",
                        "structural integrity at this wall thickness",
                        "survives deployment",
                        "preserves primary lumen",
                    ],
                    "old_language": "likely insufficient",
                    "new_language": "MODEL_PREDICTION: under stated assumptions, "
                                    "r=0.15mm predicts ~0.012 mL/min. Whether this "
                                    "radius is manufacturable or structurally viable "
                                    "is NOT YET demonstrated.",
                },
                {
                    "radius_mm": 0.25,
                    "label": "MODEL_PREDICTION",
                    "model_flow_ml_min": 0.096,
                    "model_assumptions": "same as above",
                    "NOT_yet_demonstrated": ["same as above"],
                    "old_language": "marginal — current design choice",
                    "new_language": "MODEL_PREDICTION: under stated assumptions, "
                                    "r=0.25mm predicts ~0.096 mL/min. This is the "
                                    "DESIGN CHOICE for EXP-R6-01. Actual flow will "
                                    "be MEASURED, not assumed.",
                },
                {
                    "radius_mm": 0.35,
                    "label": "MODEL_PREDICTION",
                    "model_flow_ml_min": 0.370,
                    "model_assumptions": "same as above",
                    "NOT_yet_demonstrated": [
                        "fits within eShunt geometry at this radius",
                        "wall thickness allows structural integrity",
                        "manufacturable at this precision",
                    ],
                    "old_language": "near physiological",
                    "new_language": "MODEL_PREDICTION: under stated assumptions, "
                                    "r=0.35mm predicts ~0.370 mL/min. Whether this "
                                    "radius fits the eShunt geometry is NOT YET "
                                    "confirmed by CereVasc engineering.",
                },
                {
                    "radius_mm": 0.50,
                    "label": "MODEL_PREDICTION",
                    "model_flow_ml_min": 1.530,
                    "model_assumptions": "same as above",
                    "NOT_yet_demonstrated": ["same as 0.35mm + primary lumen may be "
                                             "compromised at this bypass size"],
                    "old_language": "exceeds production",
                    "new_language": "MODEL_PREDICTION: under stated assumptions, "
                                    "r=0.50mm predicts ~1.530 mL/min. Whether this "
                                    "radius is geometrically compatible with the "
                                    "eShunt is NOT YET demonstrated.",
                },
                {
                    "radius_mm": 0.75,
                    "label": "MODEL_PREDICTION",
                    "model_flow_ml_min": 7.730,
                    "model_assumptions": "same as above",
                    "NOT_yet_demonstrated": ["unlikely to fit within eShunt OD "
                                             "alongside primary lumen"],
                    "old_language": "well exceeds",
                    "new_language": "MODEL_PREDICTION: under stated assumptions, "
                                    "r=0.75mm predicts ~7.730 mL/min. This radius "
                                    "is LIKELY incompatible with eShunt geometry "
                                    "(too large), but this has not been confirmed.",
                },
            ],

            "summary_correction": "The old summary said '0.35-0.50mm would provide "
                                  "adequate flow.' This is corrected to: 'MODEL_"
                                  "PREDICTION: under Poiseuille assumptions, radii "
                                  "of 0.35-0.50mm predict flows of 0.37-1.53 mL/min. "
                                  "Whether these radii are manufacturable, structurally "
                                  "viable, and geometrically compatible with the eShunt "
                                  "is NOT YET demonstrated. Only physical measurement "
                                  "can establish actual flow.'",
        },

        "correction_2_design_space_completeness": {
            "problem": "V21.8 enumerated 4 valve mechanisms but did not establish that "
                       "the enumeration is COMPLETE. The discovery engine's own "
                       "candidate list could become an invisible boundary.",
            "solution": "Add a formal design-space completeness test with provenance.",

            "completeness_test": {
                "step_1_taxonomy": {
                    "question": "What is the taxonomy of passive pressure-activated "
                                "valve mechanisms?",
                    "taxonomy_source": "Mechanical engineering valve design taxonomy "
                                       "(general engineering, not shunt-specific). "
                                       "Pressure-activated valves operate by one of "
                                       "these physical principles:",
                    "mechanism_classes": [
                        {
                            "class": "Elastic deformation",
                            "principle": "Material deforms under pressure to open/close "
                                        "a flow path",
                            "examples": ["silicone slit valve", "duckbill valve",
                                        "diaphragm valve", "flap valve"],
                            "in_current_enumeration": True,
                        },
                        {
                            "class": "Spring-loaded",
                            "principle": "Mechanical spring holds a sealing element "
                                        "in place; pressure overcomes spring force",
                            "examples": ["ball-in-cage", "poppet valve",
                                        "leaf spring valve"],
                            "in_current_enumeration": True,
                        },
                        {
                            "class": "Surface tension / capillary",
                            "principle": "Liquid surface tension prevents flow until "
                                        "pressure exceeds the capillary barrier",
                            "examples": ["hydrophobic membrane valve",
                                        "capillary break valve"],
                            "in_current_enumeration": True,
                        },
                        {
                            "class": "Phase change / smart material",
                            "principle": "Material changes properties (shape, stiffness, "
                                        "permeability) in response to pressure stimulus",
                            "examples": ["shape-memory alloy valve",
                                        "pressure-responsive hydrogel"],
                            "in_current_enumeration": False,
                            "reason_omitted": "These require active material response "
                                             "to pressure. Shape-memory alloys respond "
                                             "to TEMPERATURE, not pressure. Pressure-"
                                             "responsive hydrogels exist but have slow "
                                             "response times (minutes to hours) — too "
                                             "slow for acute obstruction response. "
                                             "This class is PLAUSIBLY infeasible for the "
                                             "R6 application but is NOT formally excluded.",
                            "residual_risk": "If a pressure-responsive smart material "
                                           "with fast response (<1 second) exists or is "
                                           "developed, this class could provide a solution "
                                           "not covered by the current enumeration.",
                        },
                        {
                            "class": "Geometric / inertial",
                            "principle": "Valve operates by geometry (e.g., vortex, "
                                        "swirl) or inertia (e.g., check valve, "
                                        "flapper) rather than material deformation",
                            "examples": ["swing check valve", "tilting disc valve",
                                        "vortex diode"],
                            "in_current_enumeration": False,
                            "reason_omitted": "These mechanisms typically require larger "
                                             "sizes (>5mm) and have moving parts that "
                                             "may jam in small geometries. They are used "
                                             "in industrial and cardiac applications, "
                                             "not in sub-mm medical catheters. This class "
                                             "is PLAUSIBLY infeasible for the R6 geometry "
                                             "but is NOT formally excluded.",
                            "residual_risk": "If miniaturized check valves become "
                                           "available (e.g., MEMS-based), this class "
                                           "could provide a solution.",
                        },
                    ],
                },
                "step_2_coverage": {
                    "classes_enumerated": 3,
                    "classes_omitted": 2,
                    "omitted_classes": [
                        "Phase change / smart material (slow response, not pressure-activated)",
                        "Geometric / inertial (too large for sub-mm catheter)",
                    ],
                    "reason_omitted_classes_cannot_plausibly_satisfy": [
                        "Smart materials: response time too slow (minutes) for acute "
                        "obstruction (needs <1 second). Pressure-activated smart "
                        "materials with <1s response are not known to exist.",
                        "Geometric/inertial: minimum size >5mm, incompatible with "
                        "bypass lumen geometry (<1mm). MEMS miniaturization is "
                        "theoretical for this application.",
                    ],
                    "residual_uncertainty": "The enumeration covers 3 of 5 plausible "
                                           "mechanism classes. The 2 omitted classes "
                                           "have specific infeasibility arguments but "
                                           "are NOT formally excluded. If EXP-R6-01 "
                                           "fails AND the 3 enumerated classes are "
                                           "exhausted, the 2 omitted classes should be "
                                           "re-evaluated before declaring HARD_KILL.",
                },
                "step_3_completeness_verdict": {
                    "is_enumeration_complete": "PARTIALLY — covers the 3 most plausible "
                                               "classes for sub-mm catheter valves. "
                                               "2 classes are omitted with specific "
                                               "infeasibility arguments. The enumeration "
                                               "has provenance (valve design taxonomy) "
                                               "but is NOT a proof of completeness.",
                    "who_decided": "The enumeration was constructed by the coder "
                                   "based on general valve design taxonomy. It was "
                                   "NOT reviewed by an independent valve design expert. "
                                   "An expert review could identify additional classes.",
                    "what_would_make_it_complete": "Independent review by a medical "
                                                   "device valve engineer confirming that "
                                                   "no additional plausible mechanism "
                                                   "classes exist for sub-mm pressure-"
                                                   "activated valves.",
                },
            },
        },

        "correction_3_hypothesis_freeze": {
            "declaration": "The R6 hypothesis is now FROZEN. No further protocol "
                           "optimization, threshold adjustment, or design-space "
                           "expansion before physical data is generated.",
            "frozen_state": {
                "mechanism": "Passive bypass lumen in CSF shunt that opens when "
                             "primary lumen obstructs, restoring drainage without "
                             "clearing the obstruction",
                "first_implementation": "Silicone slit valve in 0.25mm radius bypass "
                                        "lumen, 200mm length, concentric design",
                "first_experiment": "EXP-R6-01: 20 prototypes, 4 measurements "
                                    "(distribution + hysteresis + repeatability + drift)",
                "decision_matrix": "V21.7 causal hierarchy (0 HARD_KILL in initial "
                                   "protocol; design-space exhaustion for escalation)",
                "thresholds": "V21.5 no-gap thresholds (PASS/CONDITIONAL/FAIL/"
                              "INCONCLUSIVE for every metric)",
                "evidence_bindings": "V21.2 (9 thresholds bound to exact passages) + "
                                     "V21.8 (4 valve mechanisms bound to commercial specs)",
                "flow_predictions": "V21.9 MODEL_PREDICTION labels (all flow values "
                                    "are model-derived, NOT demonstrated)",
                "design_space": "V21.8 + V21.9 (4 mechanisms enumerated from 5-class "
                                "taxonomy; 2 omitted with arguments; NOT formally complete)",
            },
            "execution_rules": [
                "1. Fabricate 20 slit-valve prototypes per V21.1 specifications",
                "2. Execute EXP-R6-01 EXACTLY as pre-registered (no protocol changes)",
                "3. Record RAW MEASUREMENTS before interpretation",
                "4. Apply the FROZEN decision matrix (V21.7) to interpret results",
                "5. If slit valve FAILS (ENGINEERING_DEFICIENCY): do NOT silently "
                   "redesign the same 20 prototypes. Start the next mechanism as a "
                   "NEW pre-registered experiment.",
                "6. If slit valve FAILS (PROVISIONAL_ENGINEERING_FLOOR): report to "
                   "buyer + engineering for floor confirmation and geometric "
                   "feasibility assessment.",
                "7. If slit valve PASSES: proceed to EXP-R6-02 (flow-response curve) "
                   "with MEASURED flow, not model predictions.",
                "8. Do NOT adjust thresholds, decision matrix, or evidence bindings "
                   "after seeing data (Article VII).",
            ],
            "article_compliance": [
                "Article I: evidence precedes assertion (measure before concluding)",
                "Article II: exact evidence beats semantic plausibility (measurement > model)",
                "Article V: fail closed but not universal rejector (single failure → redesign, not kill)",
                "Article VII: never weaken the verifier to rescue a claim (no post-hoc adjustment)",
                "Article XV: disclose inconvenient results (report ALL data including failures)",
                "Article XIX: never optimize for the gate (the experiment tries to KILL R6, not confirm it)",
            ],
        },

        "summary": {
            "total_corrections": 3,
            "correction_1": "All radius/flow predictions labeled MODEL_PREDICTION. "
                            "No prediction called 'feasible' or 'adequate' until "
                            "experimentally demonstrated.",
            "correction_2": "Design-space completeness test added. 5 mechanism classes "
                            "identified from valve taxonomy; 3 enumerated, 2 omitted "
                            "with specific arguments. Enumeration has provenance but "
                            "is NOT a proof of completeness.",
            "correction_3": "Hypothesis FROZEN. 8 execution rules specified. "
                            "No further optimization before physical data.",
            "principle": "A model can tell us what might work. Only reality can tell "
                         "us what works. The invention engine should never let its "
                         "own candidate enumeration become an invisible boundary "
                         "around what is possible.",
            "next_action": "Fabricate 20 slit-valve prototypes. Execute EXP-R6-01. "
                           "Record raw measurements. Apply frozen decision matrix. "
                           "Report results honestly.",
        },
    }


if __name__ == "__main__":
    print("=" * 78)
    print("R6 V21.9 — FINAL PRE-LAB AUDIT")
    print("Hypothesis frozen. Ready for physical execution.")
    print("=" * 78)

    results = final_pre_lab_audit()

    print("\n1. MODEL LABELS")
    for p in results["correction_1_model_labels"]["relabeled_predictions"]:
        print(f"  r={p['radius_mm']:.2f}mm: {p['label']} → {p['model_flow_ml_min']} mL/min")
        print(f"    Old: {p['old_language']}")
        print(f"    New: {p['new_language'][:100]}...")

    print("\n2. DESIGN-SPACE COMPLETENESS")
    ct = results["correction_2_design_space_completeness"]["completeness_test"]
    print(f"  Taxonomy classes: {len(ct['step_1_taxonomy']['mechanism_classes'])}")
    for c in ct["step_1_taxonomy"]["mechanism_classes"]:
        enum = "ENUMERATED" if c["in_current_enumeration"] else "OMITTED"
        print(f"    {c['class']}: {enum}")
    cov = ct["step_2_coverage"]
    print(f"  Coverage: {cov['classes_enumerated']} enumerated, {cov['classes_omitted']} omitted")
    print(f"  Completeness: {ct['step_3_completeness_verdict']['is_enumeration_complete']}")

    print(f"\n3. HYPOTHESIS FROZEN")
    hf = results["correction_3_hypothesis_freeze"]
    print(f"  Declaration: {hf['declaration'][:100]}...")
    print(f"  Execution rules: {len(hf['execution_rules'])}")
    for r in hf["execution_rules"]:
        print(f"    {r[:100]}...")

    print(f"\n{'='*78}")
    print(f"NEXT ACTION: {results['summary']['next_action'][:100]}...")
    print(f"{'='*78}")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V21_9_R6_FINAL_PRE_LAB_AUDIT.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
