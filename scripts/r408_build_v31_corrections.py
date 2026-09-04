#!/usr/bin/env python3
"""r408_build_v31_corrections.py — extend P-22-R1's V3 corrections with the
V3.1 operations that close the package-10 vocabulary residue (R408
directive §3: EQ-3 subscripts, traceability DO-002, failure rows,
workplans, unknowns — plus the canonical-side embodiment rows the same
V3 authority covers).

Discipline (unchanged, from the V3 file):
  Art. II   every replacement is exact-match; a missing 'before' string
             is a HARD ERROR at apply time (no fuzzy, no skip).
  Art. VI   the trail records before/after/reason for every operation.
  Art. XXVIII corrections REMOVE the unimplemented balloon/bellows
             embodiment vocabulary and align names to the implemented
             steering-lumen mechanism; no new capability claim is added.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORR = REPO / "premium_package_factory" / "input" / "v3_corrections" / \
    "P-22-R1_V3_CORRECTIONS.json"

d = json.loads(CORR.read_text(encoding="utf-8"))

NEW_OPS = [
    # --- EQ-3: the canonical string re-derived from the corrected canonical
    # so the subscripts bind to the corrected parameter names
    # ('Steering-lumen pressure P', 'Steering-lumen area A'); the variables
    # table already binds P and A to those names (the shipped rows were
    # corrected at V3); the P_actuator/A_actuator subscripts carried the
    # removed balloon/bellows embodiment vocabulary.
    {
        "op": "repair_equation",
        "before": "F_hydraulic = P_actuator * A_actuator [actuator force]",
        "after": "F_hydraulic = P * A [steering-lumen force]",
        "corruption_class": "PRE_V3_EMBODIMENT_VOCABULARY",
        "recovery_basis": "Re-derived from the V3-corrected canonical "
                          "critical parameters 'Steering-lumen pressure P' "
                          "(Pa) and 'Steering-lumen area A' (m^2); the "
                          "governing relation F = P * A is unchanged (same "
                          "equation the V3 corrections already cite for "
                          "subsystems[1].function).",
        "reason": "The subscripts P_actuator/A_actuator carry the removed "
                  "balloon/bellows embodiment; the symbols P and A are the "
                  "recorded critical-parameter symbols of the implemented "
                  "steering-lumen mechanism.",
    },
    # --- governing-model metadata rows
    {
        "op": "replace_string",
        "path": "engineering_core.governing_model.assumptions[2]",
        "before": "Actuator response quasi-static",
        "after": "Steering-lumen response quasi-static",
        "reason": "The quasi-static assumption applies to the steering-lumen "
                  "pressure response (the implemented actuation); "
                  "'actuator' carried the removed embodiment vocabulary.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.governing_model.boundary_conditions[1]",
        "before": "Distal: free tip with actuator moment",
        "after": "Distal: free tip with steering-lumen moment",
        "reason": "The tip moment source is the differential steering-lumen "
                  "pressure (per the corrected key_physics).",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.governing_model.input_variables[0]",
        "before": "Actuator pressure P",
        "after": "Steering-lumen pressure P",
        "reason": "Aligned to the corrected critical-parameter name "
                  "(engineering_core.critical_parameters[2]).",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.governing_model.parameter_sensitivities[2]",
        "before": "Actuator area A — linear scaling of force",
        "after": "Steering-lumen area A — linear scaling of force",
        "reason": "Aligned to the corrected critical-parameter name "
                  "(engineering_core.critical_parameters[3]).",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.governing_model.failure_regimes[2]",
        "before": "Actuator saturation — cannot achieve required bending",
        "after": "Steering-lumen pressure saturation — cannot achieve "
                 "required bending",
        "reason": "The saturation regime is the steering-lumen pressure "
                  "limit of the implemented mechanism.",
    },
    # --- system architecture metadata
    {
        "op": "replace_string",
        "path": "system_architecture.mechanical_model.critical_parameter",
        "before": "EI (flexural rigidity), actuator force, buckling threshold",
        "after": "EI (flexural rigidity), steering-lumen pressure force, "
                 "buckling threshold",
        "reason": "Aligned with the corrected key_physics ('bending moment "
                  "from differential steering-lumen pressure force').",
    },
    {
        "op": "replace_string",
        "path": "mechanism_architecture.navigation_model.model",
        "before": "Closed-loop control: delta = target - sensed; controller "
                  "computes actuator pressures; catheter bends to reduce "
                  "delta",
        "after": "Closed-loop control: delta = target - sensed; controller "
                 "computes steering-lumen pressures; catheter bends to "
                 "reduce delta",
        "reason": "Aligned with the corrected subsystems[3].function (the "
                  "controller computes pressures for the steering lumens).",
    },
    # --- DO-002 (the traceability surface): description + missing inputs
    {
        "op": "replace_string",
        "path": "design_outputs[1].description",
        "before": "Hydraulic actuator design (balloon or bellows)",
        "after": "Hydraulic steering-lumen design (differential "
                 "pressurization of the three offset wall lumens)",
        "reason": "The balloon/bellows embodiment exists in no shipped "
                  "geometry (V3 correction purpose); the design output is "
                  "the implemented steering-lumen system. Same output, same "
                  "unbound status, corrected embodiment vocabulary.",
    },
    {
        "op": "replace_string",
        "path": "design_outputs[1].missing_inputs[0]",
        "before": "Actuator area",
        "after": "Steering-lumen area",
        "reason": "Aligned to the corrected critical-parameter name; the "
                  "DO-002 ABSENT/unbound status is unchanged.",
    },
    # --- canonical embodiment rows (BOM / materials / manufacturing /
    # transfer boundary): the removed balloon/bellows embodiment claimed
    # as components/processes
    {
        "op": "replace_string",
        "path": "bom[1].description",
        "before": "Hydraulic actuator (balloon or bellows)",
        "after": "Hydraulic steering lumens (three offset wall lumens in "
                 "the catheter body)",
        "reason": "The BOM row described the removed embodiment; the "
                  "implemented actuation elements are the three steering "
                  "lumens of the shipped parametric model.",
    },
    {
        "op": "replace_string",
        "path": "materials[2].component",
        "before": "Hydraulic actuator",
        "after": "Hydraulic steering lumens",
        "reason": "Same correction as the BOM row: the material entry "
                  "applies to the implemented steering-lumen walls.",
    },
    {
        "op": "replace_string",
        "path": "manufacturing.candidate_processes[1].process",
        "before": "Balloon/bellows fabrication (actuator)",
        "after": "Not applicable post-V3: the steering lumens are formed by "
                 "the multi-lumen extrusion process above (the "
                 "balloon/bellows embodiment was removed by the V3 "
                 "correction)",
        "reason": "The fabrication process belonged to the removed "
                  "embodiment; recording it as not-applicable preserves the "
                  "row (no silent removal) while removing the unsupported "
                  "claim.",
    },
    {
        "op": "replace_string",
        "path": "transfer_boundary.buyer_must_create[0]",
        "before": "Production catheter design (multi-lumen, actuator "
                  "integrated)",
        "after": "Production catheter design (multi-lumen, steering lumens "
                 "integrated)",
        "reason": "Aligned to the implemented mechanism vocabulary.",
    },
    # --- proposed design
    {
        "op": "replace_string",
        "path": "engineering_core.proposed_design.mechanism",
        "before": "Hydraulic actuator deflects catheter tip; closed-loop "
                  "controller navigates to target",
        "after": "Hydraulic steering-lumen pressure deflects catheter tip; "
                 "closed-loop controller navigates to target",
        "reason": "Aligned to the corrected key_physics.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.proposed_design.transformation",
        "before": "(target, sensed) -> actuator pressures -> catheter "
                  "bending -> tip motion",
        "after": "(target, sensed) -> steering-lumen pressures -> catheter "
                 "bending -> tip motion",
        "reason": "Aligned to the corrected subsystems[3].function.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.proposed_design.component_architecture",
        "before": "Catheter body (multi-lumen) + hydraulic actuators + tip "
                  "sensor + navigation controller + human-in-the-loop "
                  "override",
        "after": "Catheter body (multi-lumen, three steering lumens) + tip "
                 "sensor + navigation controller + human-in-the-loop "
                 "override",
        "reason": "The discrete actuator element exists in no shipped "
                  "geometry; the actuation IS the steering lumens.",
    },
    # --- failure modes / failure analysis (the traceability failure rows)
    {
        "op": "replace_string",
        "path": "engineering_core.failure_modes[3].mode",
        "before": "Actuator failure",
        "after": "Steering-lumen failure",
        "reason": "Aligned to the implemented mechanism; leak/obstruction "
                  "failure of a steering lumen.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.failure_modes[3].design_feature",
        "before": "Hydraulic actuator",
        "after": "Hydraulic steering lumens",
        "reason": "Aligned to the implemented mechanism.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.failure_modes[3].mitigation",
        "before": "Redundant actuator; manual override; fail-safe position",
        "after": "Redundant steering lumens (three independent lumens); "
                 "manual override; fail-safe position",
        "reason": "The implemented geometry carries three independent "
                  "steering lumens (P-22-R1_steerable_catheter_body); the "
                  "redundancy mitigation is restated in the implemented "
                  "terms.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.failure_modes[6].mechanism",
        "before": "Mechanical obstruction in actuator lumen",
        "after": "Mechanical obstruction in steering lumen",
        "reason": "The lumen is the steering lumen.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.failure_modes[6].design_feature",
        "before": "Hydraulic actuator",
        "after": "Hydraulic steering lumens",
        "reason": "Aligned to the implemented mechanism.",
    },
    {
        "op": "replace_string",
        "path": "engineering_core.remaining_unknowns[3]",
        "before": "Actuator failure rate — UNKNOWN",
        "after": "Steering-lumen failure rate — UNKNOWN",
        "reason": "Aligned to the corrected failure mode; the UNKNOWN "
                  "status is unchanged.",
    },
    {
        "op": "replace_string",
        "path": "failure_analysis[3].failure_mode",
        "before": "Actuator failure (leak)",
        "after": "Steering-lumen failure (leak)",
        "reason": "The traceability failure row, aligned to the implemented "
                  "mechanism; unbound status unchanged.",
    },
    {
        "op": "replace_string",
        "path": "failure_analysis[3].design_feature_affected",
        "before": "Hydraulic actuator",
        "after": "Hydraulic steering lumens",
        "reason": "Aligned to the implemented mechanism.",
    },
    {
        "op": "replace_string",
        "path": "failure_analysis[3].mitigation",
        "before": "Redundant actuator; manual override",
        "after": "Redundant steering lumens (three independent lumens); "
                 "manual override",
        "reason": "Same correction as failure_modes[3].mitigation.",
    },
    {
        "op": "replace_string",
        "path": "failure_analysis[6].mechanism",
        "before": "Obstruction in actuator lumen",
        "after": "Obstruction in steering lumen",
        "reason": "The lumen is the steering lumen.",
    },
    {
        "op": "replace_string",
        "path": "failure_analysis[6].design_feature_affected",
        "before": "Hydraulic actuator",
        "after": "Hydraulic steering lumens",
        "reason": "Aligned to the implemented mechanism.",
    },
    # --- workplans (engineering build plan rows)
    {
        "op": "replace_string",
        "path": "engineering_build_plan[1].test_article",
        "before": "Hydraulic actuator prototypes",
        "after": "Steering-lumen prototype catheters (multi-lumen extrusion "
                 "samples)",
        "reason": "The test article is the multi-lumen catheter carrying "
                  "the steering lumens; there is no discrete actuator "
                  "prototype in the implemented mechanism.",
    },
    {
        "op": "replace_string",
        "path": "engineering_build_plan[1].deliverable",
        "before": "Actuator spec",
        "after": "Steering-lumen spec",
        "reason": "Aligned to the corrected test article.",
    },
    {
        "op": "replace_string",
        "path": "engineering_build_plan[4].test_article",
        "before": "Biocompatibility specimens (Pebax multi-lumen catheter + "
                  "hydraulic actuator silicone)",
        "after": "Biocompatibility specimens (Pebax multi-lumen catheter "
                 "including the steering-lumen walls)",
        "reason": "The specimens are the multi-lumen catheter body "
                  "including the steering-lumen walls; there is no discrete "
                  "actuator part.",
    },
    {
        "op": "replace_string",
        "path": "materials[2].source",
        "before": "Standard balloon material",
        "after": "Standard multi-lumen catheter wall material",
        "reason": "Aligned to the corrected component (Hydraulic steering "
                  "lumens); the silicone candidate and verification "
                  "requirements are unchanged.",
    },
    {
        "op": "replace_string",
        "path": "manufacturing.candidate_processes[1].source",
        "before": "Standard balloon catheter manufacturing",
        "after": "Multi-lumen catheter manufacturing (see the extrusion "
                 "process above)",
        "reason": "Aligned to the corrected not-applicable process row.",
    },
    {
        "op": "replace_string",
        "path": "engineering_build_plan[1].design_work",
        "before": "Balloon/bellows design",
        "after": "Steering-lumen design (lumen diameter, offset radius, "
                 "wall thickness)",
        "reason": "The design work is the steering-lumen geometry of the "
                  "shipped parametric model (steering_lumen_diameter_mm, "
                  "steering_offset_radius_mm).",
    },
]

existing = d.get("operations", [])
have = {(o.get("op"), o.get("path"), o.get("before")) for o in existing}
added = 0
for op in NEW_OPS:
    key = (op["op"], op.get("path"), op.get("before"))
    if key in have:
        continue
    existing.append(op)
    added += 1

d["operations"] = existing
d["v3_version"] = "3.1"
d["supersedes"] = ("V3 (3.0) — the R407 P0 re-ship; this V3.1 extension "
                   "adds the vocabulary-closure operations")
d["v31_addendum"] = {
    "added_by": "R408 (P0-closing directive §3: package-10 vocabulary "
                "residue)",
    "operations_added": added,
    "surfaces_covered": [
        "governing_model.equations[2] (EQ-3 subscripts)",
        "governing_model assumptions/boundary_conditions/input_variables/"
        "parameter_sensitivities/failure_regimes",
        "design_outputs[1] (traceability DO-002 description + missing "
        "input)",
        "failure_modes[3]/[6] + failure_analysis[3]/[6] (traceability "
        "failure rows)",
        "remaining_unknowns[3] (unknowns surface)",
        "engineering_build_plan[1]/[4] (workplans)",
        "bom[1] / materials[2] / manufacturing.candidate_processes[1] / "
        "transfer_boundary (canonical embodiment rows)",
        "proposed_design + mechanical_model + navigation_model metadata",
    ],
    "surfaces_left_as_disclosed_orphans": [
        "MODEL/ metadata files (R384-era 3D-layer records; not regenerable "
        "without re-running the frozen 3D pipeline — every remaining "
        "occurrence is enumerated in B1_RESHIP_REPORT.json's orphan list)",
        "MATURITY_BASIS.json known_blockers row (R370-era computed record)",
        "claim_traceability.claims rows (engine-side only, outside "
        "engineering_content, not buyer-surface-derived)",
    ],
    "no_claim_added": True,
    "embodiment_removed_only": True,
}

CORR.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
print(f"V3.1 corrections written: {added} ops added, "
      f"{len(existing)} total, v3_version={d['v3_version']}")
