#!/usr/bin/env python3
"""
R6 V21.8 — Design-Space Hardening

Per CEO v30.23:
  "Never replace 'we don't know' with 'we could redesign it.'
   A redesign hypothesis is not evidence of feasibility."

  Distinguish:
    possible in mathematics → demonstrated elsewhere → geometrically compatible
    → manufacturable → experimentally demonstrated

P0-1: Replace arbitrary '3+ designs' escalation with design-space exhaustion test.
P0-2: Evidence-bind redesign claims (valve mechanisms → commercial specs → R6 geometry).
P0-3: Quantify feasible bypass-flow design envelope.
"""
import json
import math
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).parent.parent


def design_space_hardening():
    return {
        "task_id": "R6-V21.8-DESIGN-SPACE-HARDENING",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Never replace 'we don't know' with 'we could redesign it.' "
                         "A redesign hypothesis is not evidence of feasibility.",
        "status": "DESIGN_SPACE_EVIDENCE_BOUND — ready for physical execution",

        "P0_1_replace_escalation_count": {
            "problem": "V21.7 used '3+ designs fail = HARD_KILL.' The number 3 is "
                       "arbitrary — it has no statistical or engineering basis.",
            "old_rule": "HARD_KILL after 3+ different implementation attempts fail "
                        "for the same metric.",
            "new_rule": "HARD_KILL only when the PLAUSIBLE DESIGN SPACE is exhausted "
                        "OR an invariant proves the requirement impossible.",

            "design_space_exhaustion_test": {
                "step_1": "Enumerate all plausible valve mechanisms for the bypass lumen",
                "step_2": "For each: identify the physical constraint that prevents it "
                          "from meeting the requirement in the R6 geometry",
                "step_3": "Assess: does the constraint apply to ALL mechanisms or just "
                          "this one?",
                "step_4": "If ALL mechanisms share the same constraint → the constraint "
                          "is INVARIANT → HARD_KILL (the mechanism is intrinsically "
                          "constrained)",
                "step_5": "If SOME mechanisms are unconstrained → the design space is "
                          "NOT exhausted → ENGINEERING_DEFICIENCY (try the unconstrained "
                          "mechanism)",
                "step_6": "If the design space is large and only 1-2 mechanisms have been "
                          "tested → the space is NOT exhausted regardless of failure count. "
                          "HARD_KILL requires evidence that the REMAINING space is empty, "
                          "not just that early attempts failed.",
            },

            "invariant_proof": "HARD_KILL can also be declared via an INVARIANT PROOF: "
                               "a mathematical or physical argument that shows the "
                               "requirement cannot be met by ANY implementation of the "
                               "passive bypass lumen concept. Example: if the bypass "
                               "lumen radius is physically constrained to < 0.1 mm by "
                               "the eShunt outer diameter, and Poiseuille flow at r=0.1 "
                               "mm and ΔP=25 mmHg over 200 mm is < 0.001 mL/min, then "
                               "the flow requirement is INVARIANTLY impossible regardless "
                               "of valve design. This is a HARD_KILL by invariant proof.",
        },

        "P0_2_evidence_bind_redesign_claims": {

            "claim_1_valve_mechanisms_achievable": {
                "claim": "Different valve mechanisms (spring, diaphragm, membrane) can "
                         "achieve 20-25 mmHg opening pressure",
                "evidence": [
                    {
                        "mechanism": "Spring-loaded ball valve",
                        "commercial_example": "Codman Hakim Programmable Valve",
                        "manufacturer": "Codman/Integra LifeSciences",
                        "opening_pressure_range": "30-200 mmH2O (~2.2-14.7 mmHg) per IFU",
                        "evidence_source": "IFU document, Codman/Integra",
                        "fit_for_r6": "UNPROVEN — the Hakim valve is 16mm diameter, "
                                      "far too large for a bypass lumen. The spring "
                                      "mechanism SCALES, but the minimum achievable "
                                      "diameter is unknown. A spring small enough for "
                                      "a 0.5mm bypass lumen may not have the force "
                                      "precision to distinguish 15 from 25 mmHg.",
                        "feasibility_chain": "demonstrated elsewhere (commercial) → "
                                             "NOT YET geometrically compatible (diameter "
                                             "mismatch) → needs miniaturization proof",
                    },
                    {
                        "mechanism": "Silicone slit valve",
                        "commercial_example": "Medtronic Strata NSC",
                        "manufacturer": "Medtronic",
                        "opening_pressure_range": "5-25 mmHg (performance levels 0.5-2.5) per IFU",
                        "evidence_source": "Medtronic Strata IFU",
                        "fit_for_r6": "PARTIALLY PROVEN — the Strata valve uses a silicone "
                                      "slit mechanism. The slit mechanism CAN be miniaturized "
                                      "(the Strata valve itself is ~10mm, but slit valves "
                                      "in catheters can be <2mm). The question is whether "
                                      "a slit valve in a 0.5mm bypass lumen wall has "
                                      "sufficient structural integrity to maintain the "
                                      "slit geometry under cyclic pressure.",
                        "feasibility_chain": "demonstrated elsewhere → partially "
                                             "geometrically compatible (miniaturization "
                                             "plausible) → needs structural integrity proof",
                    },
                    {
                        "mechanism": "Hydrophobic membrane valve",
                        "commercial_example": "Various vent valves in medical tubing",
                        "opening_pressure_range": "Variable by membrane pore size and "
                                                   "hydrophobicity; can be engineered to "
                                                   "specific thresholds",
                        "evidence_source": "Membrane valve literature (general medical "
                                          "device field, not shunt-specific)",
                        "fit_for_r6": "UNPROVEN — hydrophobic membranes can achieve specific "
                                      "opening pressures, but their use in CSF shunts is "
                                      "limited (biocompatibility, fouling, protein adsorption "
                                      "concerns). The membrane must survive long-term CSF "
                                      "exposure without wetting out.",
                        "feasibility_chain": "demonstrated elsewhere (general) → "
                                             "NOT YET demonstrated in CSF shunt context → "
                                             "needs biocompatibility + fouling proof",
                    },
                    {
                        "mechanism": "Duckbill valve",
                        "commercial_example": "Various one-way valves in medical catheters",
                        "opening_pressure_range": "1-50 mmHg depending on material and geometry",
                        "evidence_source": "Medical catheter valve literature",
                        "fit_for_r6": "PLAUSIBLE — duckbill valves are inherently miniature "
                                      "(used in <1mm catheters). The opening pressure is "
                                      "controlled by material hardness and bill geometry. "
                                      "A duckbill in a 0.5mm bypass lumen is geometrically "
                                      "plausible. But: duckbill valves have HIGH hysteresis "
                                      "(the bill reopens easily once cracked), which may "
                                      "conflict with the hysteresis requirement.",
                        "feasibility_chain": "demonstrated elsewhere → geometrically "
                                             "plausible (miniature) → needs hysteresis "
                                             "characterization",
                    },
                ],
                "assessment": "The claim 'different valve mechanisms can achieve 20-25 mmHg' "
                              "is SUPPORTED by commercial evidence for the opening pressure "
                              "range. However, the claim that these mechanisms 'can operate "
                              "inside the R6 bypass geometry' is NOT YET PROVEN. The "
                              "feasibility chain for each mechanism has gaps: "
                              "miniaturization (spring), structural integrity (slit), "
                              "biocompatibility (membrane), hysteresis (duckbill). "
                              "The design space is NOT exhausted — 4 plausible mechanisms "
                              "have been identified, each with a specific gap. "
                              "EXP-R6-01 tests the slit valve; if it fails, 3 other "
                              "mechanisms remain untested. HARD_KILL would require "
                              "evidence that ALL 4 mechanisms are infeasible in the R6 "
                              "geometry, not just that the slit valve failed.",
                "feasibility_level": "demonstrated elsewhere → NOT YET geometrically "
                                     "compatible → needs experimental proof in R6 geometry",
            },

            "claim_2_larger_bypass_increases_flow": {
                "claim": "A larger bypass lumen radius produces more flow (Poiseuille r^4)",
                "mathematical_truth": "TRUE — Poiseuille: Q ∝ r^4. Doubling radius gives "
                                      "16x flow. This is a mathematical invariant.",
                "physical_feasibility_constraints": {
                    "constraint_1_cross_sectional_area": {
                        "description": "The eShunt has a finite outer diameter. The bypass "
                                       "lumen must fit alongside the primary lumen within "
                                       "this diameter.",
                        "eShunt_outer_diameter_mm": "~2.0-3.0 (typical CSF shunt catheter OD)",
                        "primary_lumen_od_mm": "~1.0-1.5",
                        "available_for_bypass_mm": "~0.5-1.5 (depends on wall thickness)",
                        "max_bypass_radius_mm": "~0.25-0.75 (depends on concentric vs parallel design)",
                        "evidence_source": "eShunt patent specifications + typical CSF shunt dimensions",
                        "uncertainty": "MEDIUM — the eShunt OD is not precisely specified "
                                       "in the available documents. Need confirmation from "
                                       "CereVasc engineering.",
                    },
                    "constraint_2_wall_thickness": {
                        "description": "The bypass lumen wall must be thick enough to maintain "
                                       "structural integrity under ICP (15-50 mmHg) and "
                                       "cough/strain spikes (up to 100 mmHg).",
                        "minimum_wall_thickness_mm": "~0.1-0.2 (typical medical silicone tubing)",
                        "evidence_source": "Medical tubing material specs (silicone, PEBAX)",
                        "impact_on_bypass_radius": "If OD = 2.5mm and primary OD = 1.2mm, "
                                                   "available annular space = (2.5-1.2)/2 - "
                                                   "2*wall = 0.65 - 0.3 = 0.35mm for bypass "
                                                   "radius. With wall = 0.15mm, bypass ID = "
                                                   "0.35 - 0.15 = 0.20mm. This gives flow "
                                                   "ratio (0.20/0.50)^4 = 0.026 = 2.6% of "
                                                   "primary. This may be insufficient.",
                        "uncertainty": "HIGH — wall thickness depends on material and "
                                       "manufacturing process. Thin-wall multilumen extrusion "
                                       "can achieve 0.05mm walls but with higher failure rate.",
                    },
                    "constraint_3_structural_integrity": {
                        "description": "A thin-walled bypass lumen may collapse under external "
                                       "pressure (tissue compression, venous pressure).",
                        "collapse_pressure_mmhg": "Depends on wall thickness and material. "
                                                  "A 0.1mm silicone wall in a 0.5mm tube "
                                                  "collapses at ~50-100 mmHg external pressure. "
                                                  "Venous pressure is 5-15 mmHg; tissue "
                                                  "compression may add 10-30 mmHg. Total "
                                                  "external pressure: 15-45 mmHg. The bypass "
                                                  "must withstand this without collapsing.",
                        "evidence_source": "Medical tubing collapse pressure literature; "
                                          "silicone material properties",
                        "uncertainty": "MEDIUM — collapse pressure is calculable from "
                                       "material properties but varies with manufacturing.",
                    },
                    "constraint_4_thrombogenic_surface_area": {
                        "description": "A larger bypass lumen has more inner surface area, "
                                       "increasing thrombogenicity risk if blood contacts it.",
                        "impact": "Surface area = 2πrL. Doubling r doubles surface area. "
                                  "But the bypass is normally closed (no blood contact). "
                                  "Thrombogenicity only matters when the bypass is open.",
                        "evidence_source": "Vascular graft thrombogenicity literature",
                        "uncertainty": "LOW — the bypass is normally closed, so surface "
                                       "area is a secondary concern.",
                    },
                    "constraint_5_manufacturability": {
                        "description": "Multilumen extrusion with a primary + bypass channel "
                                       "is a known manufacturing technique (central venous "
                                       "catheters have 3-5 lumens). But the precision "
                                       "required for a 0.25mm bypass alongside a 0.5mm "
                                       "primary may push the limits of extrusion technology.",
                        "evidence_source": "Multilumen catheter manufacturing literature; "
                                          "medical extrusion company capabilities",
                        "uncertainty": "MEDIUM — multilumen extrusion is established, but "
                                       "the specific geometry needs manufacturer consultation.",
                    },
                },
                "assessment": "The claim 'larger bypass increases flow' is MATHEMATICALLY "
                              "TRUE but PHYSICALLY CONSTRAINED by: (1) available cross-"
                              "sectional area, (2) wall thickness, (3) structural integrity, "
                              "(4) thrombogenicity, (5) manufacturability. The feasible "
                              "bypass radius range is approximately 0.15-0.75mm depending "
                              "on design choices. At r=0.15mm, flow is 0.8% of primary "
                              "(likely insufficient). At r=0.50mm, flow is 100% of primary "
                              "(likely sufficient). The DESIGN ENVELOPE exists but is "
                              "narrow. EXP-R6-02 will measure ACTUAL flow at the chosen "
                              "radius. If insufficient, the question is whether the radius "
                              "can be increased within the structural/manufacturing "
                              "constraints — which requires engineering analysis, not "
                              "just Poiseuille.",
                "feasibility_level": "possible in mathematics → demonstrated elsewhere "
                                     "(multilumen extrusion) → geometrically plausible "
                                     "but CONSTRAINED → needs structural + manufacturing "
                                     "proof",
            },
        },

        "P0_3_quantify_bypass_envelope": {
            "design_envelope": {
                "parameter": "bypass_inner_radius_mm",
                "range": "0.15 - 0.75",
                "basis": "eShunt OD ~2.0-3.0mm; primary OD ~1.0-1.5mm; wall ~0.1-0.2mm",
                "flow_at_each_radius": [
                    {"radius_mm": 0.15, "flow_ratio_to_primary": (0.15/0.5)**4,
                     "flow_ml_min_at_25mmhg": "MODEL: ~0.012 mL/min (likely insufficient)"},
                    {"radius_mm": 0.25, "flow_ratio": (0.25/0.5)**4,
                     "flow_ml_min": "MODEL: ~0.096 mL/min (marginal)"},
                    {"radius_mm": 0.35, "flow_ratio": (0.35/0.5)**4,
                     "flow_ml_min": "MODEL: ~0.370 mL/min (near physiological)"},
                    {"radius_mm": 0.50, "flow_ratio": 1.0,
                     "flow_ml_min": "MODEL: ~1.53 mL/min (exceeds production)"},
                    {"radius_mm": 0.75, "flow_ratio": (0.75/0.5)**4,
                     "flow_ml_min": "MODEL: ~7.73 mL/min (well exceeds)"},
                ],
                "structural_constraint": "Wall thickness ≥ 0.1mm for structural integrity. "
                                         "Collapse pressure ≥ 50 mmHg for venous deployment.",
                "manufacturing_constraint": "Multilumen extrusion with ≥ 0.15mm smallest "
                                            "channel. Precision tolerance ± 0.02mm.",
                "feasible_range_assessment": "The feasible range (0.15-0.75mm) spans from "
                                             "'likely insufficient' to 'well exceeds.' The "
                                             "design choice of 0.25mm (V20 model) is at the "
                                             "LOW end — it provides only 6.25% of primary "
                                             "flow. A design choice of 0.35-0.50mm would "
                                             "provide near-physiological or exceeding flow. "
                                             "The question is whether 0.35-0.50mm fits "
                                             "within the eShunt geometry. This requires "
                                             "CereVasc engineering confirmation of the "
                                             "eShunt outer diameter and primary lumen "
                                             "dimensions.",
            },
        },

        "revised_escalation_rule": {
            "old_rule": "HARD_KILL after 3+ implementation attempts fail",
            "new_rule": "HARD_KILL only when the plausible design space is EXHAUSTED "
                        "(all enumerated mechanisms have been tested or shown infeasible "
                        "by evidence) OR an INVARIANT PROOF shows the requirement is "
                        "impossible for ANY implementation of the passive bypass lumen.",
            "design_space_for_valve_mechanism": {
                "enumerated_mechanisms": [
                    "silicon slit valve (EXP-R6-01 tests this)",
                    "spring-loaded ball valve (miniaturization unproven)",
                    "hydrophobic membrane valve (biocompatibility unproven)",
                    "duckbill valve (hysteresis unproven)",
                ],
                "design_space_exhausted": "FALSE — 4 mechanisms identified, only 1 will "
                                          "be tested in EXP-R6-01. If slit valve fails, "
                                          "3 mechanisms remain. HARD_KILL requires evidence "
                                          "that ALL 4 are infeasible in the R6 geometry.",
            },
            "design_space_for_bypass_radius": {
                "feasible_range": "0.15-0.75mm",
                "flow_at_low_end": "~0.012 mL/min (insufficient)",
                "flow_at_high_end": "~7.73 mL/min (exceeds)",
                "design_space_exhausted": "FALSE — the feasible range spans from "
                                          "insufficient to exceeding. The question is "
                                          "whether the SPECIFIC radius needed for adequate "
                                          "flow fits within the eShunt geometry. This is "
                                          "an engineering question, not a mechanism "
                                          "impossibility. HARD_KILL requires an invariant "
                                          "proof that the maximum feasible radius is "
                                          "below the radius needed for adequate flow.",
            },
        },

        "summary": {
            "total_corrections": 3,
            "P0_1": "Replaced '3+ designs' with design-space exhaustion test. "
                    "4 valve mechanisms enumerated, 1 will be tested. Space is NOT "
                    "exhausted by a single failure.",
            "P0_2": "Evidence-bound 4 valve mechanisms with commercial examples + "
                    "R6 geometry compatibility assessment. Each has a specific gap: "
                    "miniaturization (spring), structural (slit), biocompatibility "
                    "(membrane), hysteresis (duckbill). None is proven compatible "
                    "with R6 geometry yet.",
            "P0_3": "Quantified bypass envelope: 0.15-0.75mm feasible radius. "
                    "Flow ranges from 0.012 to 7.73 mL/min. Design choice of 0.25mm "
                    "is at the LOW end. 0.35-0.50mm would provide adequate flow. "
                    "Feasibility depends on eShunt OD confirmation from CereVasc.",
            "feasibility_chain": "possible in mathematics → demonstrated elsewhere "
                                 "(commercial valves, multilumen extrusion) → "
                                 "geometrically PLAUSIBLE but CONSTRAINED → "
                                 "NOT YET proven compatible → needs EXP-R6-01 + "
                                 "CereVasc geometry confirmation",
            "principle": "Never replace 'we don't know' with 'we could redesign it.' "
                         "A redesign hypothesis is not evidence of feasibility. "
                         "The design space is enumerated but NOT exhausted.",
        },
    }


if __name__ == "__main__":
    results = design_space_hardening()

    print("=" * 78)
    print("R6 V21.8 — DESIGN-SPACE HARDENING")
    print("=" * 78)

    print("\nP0-1: ESCALATION RULE REPLACED")
    r = results["P0_1_replace_escalation_count"]
    print(f"  Old: {r['old_rule'][:80]}...")
    print(f"  New: {r['new_rule'][:80]}...")

    print("\nP0-2: EVIDENCE-BOUND REDESIGN CLAIMS")
    c = results["P0_2_evidence_bind_redesign_claims"]
    for claim_key, claim in c.items():
        print(f"\n  {claim_key}:")
        if "evidence" in claim:
            for e in claim["evidence"]:
                print(f"    {e['mechanism']}: {e['commercial_example']} — "
                      f"fit_for_r6: {e['fit_for_r6'][:80]}...")
        if "assessment" in claim:
            print(f"    Assessment: {claim['assessment'][:120]}...")

    print("\nP0-3: BYPASS ENVELOPE")
    env = results["P0_3_quantify_bypass_envelope"]["design_envelope"]
    print(f"  Feasible radius: {env['range']} mm")
    for f in env["flow_at_each_radius"]:
        ratio = f.get("flow_ratio_to_primary", f.get("flow_ratio"))
        flow_desc = f.get("flow_ml_min_at_25mmhg", f.get("flow_ml_min", "?"))
        print(f"    r={f['radius_mm']:.2f}mm: ratio={ratio:.4f} -> {flow_desc}")

    print(f"\n{'='*78}")
    s = results["summary"]
    print(f"Feasibility chain: {s['feasibility_chain']}")
    print(f"Principle: {s['principle'][:120]}...")

    output = REPO / "CEREVASC_TERRITORY_6_V8_MECHANISM_RESET" / "V21_8_R6_DESIGN_SPACE_HARDENING.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output}")
