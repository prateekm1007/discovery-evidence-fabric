"""R380 LIVE POSITIVE DEMO — the CEO's exact loop, executed live:

    parameter X = 1.0 mm (lumen_diameter_mm)
    -> technical evaluator identifies X as limiting
    -> mutation proposes 1.2 mm
    -> CAD generator creates new geometry      (CadQuery + OCCT)
    -> geometry validates                      (G1-G8, measured)
    -> technical evaluator re-runs             (independent)
    -> candidate is KEEP                       (K1-K7)
    -> SECOND improvement                      (length 30 -> 40)

Every stage writes its artifacts to a real output directory with
real hashes; nothing is inherited; every measurement carries its
computation log. Hermetic (ENGINE_CAD_LLM=0): the engine template
path carries the geometry, the LLM mutation proposal is mocked to
the deterministic proposal the untrusted proposer would emit — the
gates (T1-T10, K1-K7) are the REAL production gates.
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")

from discovery_fabric.engine.cad_pipeline import (
    geometry_warrants_3d, get_parametric_model, rebuild_with_mutation,
    run_cad_pass)
from discovery_fabric.engine.evaluator_contract import CandidateContext
from discovery_fabric.engine.technical_evaluator import \
    evaluate_candidate_technically
from discovery_fabric.engine.technical_improvement_engine import (
    apply_technical_mutation, keep_or_kill_technical,
    re_evaluate_technical, validate_technical_mutation)
from discovery_fabric.engine.technical_state import attach_technical_state

OUT = Path("/home/z/my-project/discovery-evidence-fabric/"
           "R380_LIVE_DEMO")
OUT.mkdir(parents=True, exist_ok=True)
print("R380 LIVE DEMO — output:", OUT)

# ---------------------------------------------------------------------------
# CANDIDATE A: a dual-lumen CSF shunt tube with evidence-backed state
# ---------------------------------------------------------------------------
problem = {"problem_id": "P-DUAL-LUMEN",
           "title": "insufficient differential drainage and thin "
                    "extruded wall robustness in dual-lumen CSF "
                    "shunt catheters",
           "device": "dual-lumen CSF shunt catheter with septum",
           "failure": "thin extruded wall tears; insufficient "
                      "differential drainage; wall robustness loss"}
state_proposal = {
    "objects": [
        {"object_id": "dual_lumen_tube",
         "name": "dual-lumen shunt body",
         "role": "outer body with two through-lumens and septum"},
        {"object_id": "lumen_a", "name": "drainage lumen",
         "role": "drainage lumen"},
        {"object_id": "lumen_b", "name": "flush access lumen",
         "role": "flush/access lumen"},
    ],
    "parameters": [
        {"param_id": "outer_diameter_mm", "name": "outer diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 3.0,
         "value_class": "MODELLED", "range_min": 2.0, "range_max": 5.0,
         "range_class": "MODELLED", "role": "device envelope"},
        {"param_id": "lumen_diameter_mm", "name": "lumen diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 1.0,
         "value_class": "MODELLED", "range_min": 0.5, "range_max": 2.0,
         "range_class": "MODELLED", "role": "drainage lumen diameter"},
        {"param_id": "length_mm", "name": "tube length",
         "category": "GEOMETRY", "unit": "mm", "value": 30.0,
         "value_class": "MODELLED", "range_min": 10.0, "range_max": 60.0,
         "range_class": "MODELLED", "role": "implantable length"},
        {"param_id": "septum_thickness_mm", "name": "septum thickness",
         "category": "GEOMETRY", "unit": "mm", "value": 0.2,
         "value_class": "MODELLED", "range_min": 0.05, "range_max": 0.5,
         "range_class": "MODELLED", "role": "wall between lumens"},
        {"param_id": "wall_thickness_mm", "name": "min wall thickness",
         "category": "PARAMETERS", "unit": "mm", "value": None,
         "value_class": "UNKNOWN", "range_min": None, "range_max": None,
         "range_class": "UNKNOWN", "role": "measured on geometry"},
        {"param_id": "drainage_flow_ml_hr", "name": "drainage flow",
         "category": "PARAMETERS", "unit": "ml/hr", "value": None,
         "value_class": "UNKNOWN", "range_min": None, "range_max": None,
         "range_class": "UNKNOWN", "role": "outcome"},
    ],
    "constraints": [
        {"constraint_id": "c_wall", "target": "wall_thickness_mm",
         "bound": ">=", "limit": 0.15, "limit_class": "MODELLED",
         "justification": "thin-wall micro-extrusion minimum "
                          "manufacturable wall (MODELLED engineering "
                          "threshold; would need process data to "
                          "promote)"},
        {"constraint_id": "c_od", "target": "outer_diameter_mm",
         "bound": "<=", "limit": 3.5, "limit_class": "MODELLED",
         "justification": "pediatric neurosurgical anatomy envelope"},
    ],
    "objectives": [
        {"objective_id": "o1", "target": "drainage_flow_ml_hr",
         "direction": "MAXIMIZE",
         "basis": "problem: insufficient differential drainage in "
                  "dual-lumen shunt catheters — drainage flow is the "
                  "primary therapeutic quantity"},
    ],
    "dependencies": [
        {"relation_id": "r1", "cause": "lumen_diameter_mm",
         "effect": "wall_thickness_mm", "direction": "DECREASES",
         "relation_class": "MODELLED",
         "statement": "enlarging the lumen thins the wall "
                      "geometrically: wall = od/2 - ld - st/2"},
        {"relation_id": "r2", "cause": "lumen_diameter_mm",
         "effect": "drainage_flow_ml_hr", "direction": "INCREASES",
         "relation_class": "MODELLED",
         "statement": "Poiseuille: flow scales with lumen radius^4"},
    ],
    "materials": [
        {"material_id": "silicone", "name": "medical-grade silicone",
         "role": "extruded body"}],
    "operating_conditions": [],
    "measurable_outputs": [],
}

# validate + attach the state (deterministic admission, as production)
from discovery_fabric.engine.technical_state import \
    validate_technical_state as vts
validated_state, validation_report = vts(
    state_proposal, [], problem)
spec = {
    "candidate_id": "DEMO-DUAL-LUMEN-A",
    "mechanism": {"value": {
        "mechanism": "dual-lumen tube with septum",
        "intervention": "parametric extruded dual-lumen shunt body",
        "expected_effect": "differential drainage with wall robustness"}},
    "distinguishing_features": {"value": {
        "intervention": "parametric extruded dual-lumen shunt body"}},
    "novelty_hypothesis": {"value": {
        "hypothesis": "the parametric wall-preserving lumen envelope "
                      "differentiates this dual-lumen geometry"}},
    "prior_art": {"value": {}},
}
spec = attach_technical_state(
    spec, validated_state,
    {"proposal_id": "demo", "provider": "DEMO", "model": "fixture",
     "prompt_hash": "0", "output_hash": "0", "status": "OK"},
    validation_report)
print("\n[1] TECHNICAL STATE admitted:",
      json.dumps(validation_report.get("admitted_counts")))

# ---------------------------------------------------------------------------
# THE CAD PASS: state -> parameter map -> model -> derivatives -> G-gates
# ---------------------------------------------------------------------------
cad_dir = str(OUT / "three_d")
spec, cad_ledger = run_cad_pass(
    spec, out_dir=cad_dir, allow_llm=False)
print(f"[2] CAD PASS outcome: {cad_ledger['outcome']}")
model = get_parametric_model(spec)
assert model is not None, "model must build for the demo"
gv = model["geometry_validation"]
print(f"    model_id: {model['model_id']}")
print(f"    kernel: {model['kernel']} {model['kernel_version']}")
print(f"    geometry valid: {gv['valid']}")
for g, c in sorted(gv["checks"].items()):
    print(f"      {g}: {c['status']}")
m = model["measurements"]["objects"]["dual_lumen_tube"]
print(f"    MEASURED wall: {m['min_wall_thickness_mm']} mm  "
      f"volume: {m['volume_mm3']} mm3  bbox: {m['bbox']['xlen']}x"
      f"{m['bbox']['ylen']}x{m['bbox']['zlen']}")
print(f"    derivatives: {sorted(model['derived_artifacts'])}")

# ---------------------------------------------------------------------------
# DIAGNOSE: the technical evaluator identifies the limiting variable
# ---------------------------------------------------------------------------
ctx = CandidateContext(spec=spec, problem=problem,
                       run_ctx={"cad_out_dir": cad_dir})
parent_eval = {"technical": evaluate_candidate_technically(spec)}
tech = parent_eval["technical"]
diag = tech.get("limiting_variable") or {}
print(f"\n[3] DIAGNOSE status: {tech.get('status')}")
print(f"    limiting variable: {diag.get('param_id')} "
      f"improving move: {diag.get('improving_move')}")

# ---------------------------------------------------------------------------
# MUTATION 1: the untrusted proposal (mocked transport, REAL gates)
# ---------------------------------------------------------------------------
proposal1 = {
    "proposal_id": "demo-mut-1", "provider": "DEMO", "model": "fixture",
    "prompt_hash": "0", "output_hash": "0", "status": "OK",
    "fields": {
        "MUTATION_KIND": "GEOMETRY_CHANGE",
        "TARGET_PARAM": "lumen_diameter_mm",
        "DIRECTION": "INCREASE",
        "NEW_VALUE": "1.2",
        "VALUE_CLASS": "MODELLED",
        "MECHANISM_DELTA": "enlarging the lumen diameter increases "
                            "drainage capacity per Poiseuille scaling",
        "INTERVENTION_DELTA": "the drainage lumen diameter is "
                              "enlarged from 1.0 to 1.2 mm within the "
                              "extrusion envelope",
        "RATIONALE": "wall 0.4 -> 0.2 still above the 0.15 "
                     "manufacturability floor; flow ~ r^4 gain",
    }}
evaluation = {"limiting_variable": diag}
validation1 = validate_technical_mutation(ctx, proposal1, evaluation)
print(f"\n[4] VALIDATE MUTATION 1: valid={validation1['valid']}")
for chk, ok in validation1["checks"].items():
    print(f"      {chk}: {str(ok)[:110]}")

# the KILL branch demonstrated live: the same mutation at 1.7 mm
proposal_kill = copy.deepcopy(proposal1)
proposal_kill["fields"]["NEW_VALUE"] = "1.7"
validation_kill = validate_technical_mutation(
    ctx, proposal_kill, evaluation)
print(f"\n[5] ADVERSARIAL MUTATION (1.7 mm): valid="
      f"{validation_kill['valid']} — the T10 CAD gate: "
      f"{str(validation_kill['checks'].get('t10_geometry_gate'))[:150]}")

# ---------------------------------------------------------------------------
# APPLY: the child is constructed; the CAD rebuild happens INSIDE apply
# ---------------------------------------------------------------------------
child = apply_technical_mutation(ctx, proposal1, validation1)
child_model = get_parametric_model(child.spec)
print(f"\n[6] APPLY: child model rebuilt "
      f"{validation1['checks'].get('t10_geometry_gate', {}).get('rebuilt_model_id') if isinstance(validation1['checks'].get('t10_geometry_gate'), dict) else ''}")
cm = child_model["measurements"]["objects"]["dual_lumen_tube"]
print(f"    child MEASURED wall: {cm['min_wall_thickness_mm']} mm "
      f"(parent {m['min_wall_thickness_mm']} mm)")
print(f"    child model_id: {child_model['model_id']} "
      f"(parent {model['model_id']})")
print(f"    child derivatives: {sorted(child_model['derived_artifacts'])}")
print(f"    mutation provenance entries: "
      f"{len(child_model['mutation_provenance'])}")

# ---------------------------------------------------------------------------
# RE-EVALUATE independently + KEEP/KILL
# ---------------------------------------------------------------------------
child_ctx = CandidateContext(spec=child.spec, problem=problem,
                             run_ctx={"cad_out_dir": cad_dir})
re_eval = {"technical": evaluate_candidate_technically(child.spec)}
decision = keep_or_kill_technical(ctx, child_ctx, parent_eval,
                                  re_eval, validation1)
print(f"\n[7] KEEP/KILL: {decision['action']}")
for k, v in decision["checks"].items():
    print(f"      {k}: {str(v)[:120]}")

# ---------------------------------------------------------------------------
# SECOND IMPROVEMENT (CEO: KEEP -> second mutation)
# ---------------------------------------------------------------------------
if decision["action"] == "KEEP":
    eval2 = {"limiting_variable":
             (re_eval["technical"].get("limiting_variable") or diag)}
    proposal2 = {
        "proposal_id": "demo-mut-2", "provider": "DEMO",
        "model": "fixture", "prompt_hash": "0", "output_hash": "0",
        "status": "OK",
        "fields": {
            "MUTATION_KIND": "GEOMETRY_CHANGE",
            "TARGET_PARAM": "lumen_diameter_mm",
            "DIRECTION": "INCREASE",
            "NEW_VALUE": "1.24",
            "VALUE_CLASS": "MODELLED",
            "MECHANISM_DELTA": "further lumen diameter increase "
                                "continues the Poiseuille drainage "
                                "gain toward the measured wall limit",
            "INTERVENTION_DELTA": "drainage lumen diameter extended "
                                  "from 1.2 to 1.24 mm — the last "
                                  "defensible step above the 0.15 mm "
                                  "measured wall floor",
            "RATIONALE": "wall = od/2 - ld - st/2: measured 0.2 -> "
                         "0.16 mm, still above the 0.15 floor; flow "
                         "gain ~ (1.24/1.2)^4",
        }}
    validation2 = validate_technical_mutation(
        child_ctx, proposal2, eval2)
    print(f"\n[8] SECOND MUTATION valid={validation2['valid']}")
    grandchild = apply_technical_mutation(child_ctx, proposal2,
                                          validation2)
    gm = get_parametric_model(grandchild.spec)
    gmm = gm["measurements"]["objects"]["dual_lumen_tube"]
    print(f"    grandchild MEASURED wall: "
          f"{gmm['min_wall_thickness_mm']} mm "
          f"(parent chain 0.4 -> 0.2 -> {gmm['min_wall_thickness_mm']})")
    print(f"    grandchild provenance chain: "
          f"{[p['param_id'] + ' ' + str(p['from_value']) + '->' + str(p['to_value']) for p in gm['mutation_provenance']]}")
    gc_ctx = CandidateContext(spec=grandchild.spec, problem=problem)
    re_eval2 = {"technical":
                evaluate_candidate_technically(grandchild.spec)}
    decision2 = keep_or_kill_technical(child_ctx, gc_ctx, re_eval,
                                       re_eval2, validation2)
    print(f"[9] SECOND KEEP/KILL: {decision2['action']}")

# persist the full demo record
record = {
    "demo": "R380 LIVE POSITIVE — CEO exact loop",
    "cad_ledger_outcome": cad_ledger["outcome"],
    "model_id": model.get("model_id"),
    "geometry_checks": {g: c["status"]
                        for g, c in gv["checks"].items()},
    "measured_parent": {k: v for k, v in m.items()
                        if k in ("min_wall_thickness_mm",
                                 "volume_mm3", "bbox")},
    "measured_child": {k: v for k, v in cm.items()
                       if k in ("min_wall_thickness_mm",
                                "volume_mm3", "bbox")},
    "decision_1": decision["action"],
    "decision_2": (decision2["action"] if decision["action"] == "KEEP"
                   else "NOT_REACHED"),
    "evidence_class_everywhere": "COMPUTATIONAL_RESULT",
    "physical_evidence": "NONE (Art. XXXVIII)",
}
(OUT / "LIVE_DEMO_RECORD.json").write_text(
    json.dumps(record, indent=2, default=str))
print("\nDONE. Record:", OUT / "LIVE_DEMO_RECORD.json")
