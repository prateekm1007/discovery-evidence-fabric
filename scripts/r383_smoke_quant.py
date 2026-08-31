"""R383 smoke — hand-verified quantitative evaluation on a state-only
candidate (no CAD yet): Poiseuille must compute Q = 12.72 mL/hr for
D=0.30mm, L=30mm, dP=4mmHg, mu=1.0mPa·s (constant fallback), margin
-36.4% vs the 20 mL/hr requirement, elasticity(D) = 4, solve-for
D = 0.344mm."""
import sys
sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")

from discovery_fabric.engine.technical_equations import (
    evaluate_candidate_quantitatively)
from discovery_fabric.engine.technical_state import (
    attach_technical_state, validate_technical_state)

problem = {"device": "dual-lumen CSF shunt catheter",
           "failure": "insufficient drainage at low pressure head",
           "constraint": "drainage flow"}
state_proposal = {
    "objects": [{"object_id": "dual_lumen_tube",
                 "name": "dual-lumen shunt body",
                 "role": "outer body with two through-lumens"}],
    "parameters": [
        {"param_id": "outer_diameter_mm", "name": "outer diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 2.4,
         "value_class": "MODELLED", "range_min": 2.0, "range_max": 4.0,
         "range_class": "MODELLED", "role": "device envelope"},
        {"param_id": "lumen_diameter_mm", "name": "lumen diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 0.30,
         "value_class": "MODELLED", "range_min": 0.25, "range_max": 0.70,
         "range_class": "MODELLED", "role": "drainage lumen diameter"},
        {"param_id": "length_mm", "name": "tube length",
         "category": "GEOMETRY", "unit": "mm", "value": 30.0,
         "value_class": "MODELLED", "range_min": 10.0, "range_max": 60.0,
         "range_class": "MODELLED", "role": "implantable length"},
        {"param_id": "septum_thickness_mm", "name": "septum thickness",
         "category": "GEOMETRY", "unit": "mm", "value": 0.15,
         "value_class": "MODELLED", "range_min": 0.05, "range_max": 0.5,
         "range_class": "MODELLED", "role": "wall between lumens"},
        {"param_id": "wall_thickness_mm", "name": "min wall thickness",
         "category": "PARAMETERS", "unit": "mm", "value": None,
         "value_class": "UNKNOWN", "role": "measured on geometry"},
        {"param_id": "drainage_flow_ml_hr", "name": "drainage flow",
         "category": "PARAMETERS", "unit": "ml/hr", "value": None,
         "value_class": "UNKNOWN", "role": "outcome flow"},
        {"param_id": "intracranial_pressure_drop_mmhg",
         "name": "pressure drop", "category": "OPERATING_CONDITIONS",
         "unit": "mmHg", "value": 4.0, "value_class": "MODELLED",
         "role": "driving pressure drop across the catheter"},
    ],
    "constraints": [
        {"constraint_id": "c_wall", "target": "wall_thickness_mm",
         "bound": ">=", "limit": 0.15, "unit": "mm",
         "limit_class": "MODELLED",
         "justification": "micro-extrusion manufacturable wall floor"},
        {"constraint_id": "c_flow", "target": "drainage_flow_ml_hr",
         "bound": ">=", "limit": 20.0, "unit": "ml/hr",
         "limit_class": "MODELLED",
         "justification": "minimum drainage requirement at 4 mmHg"},
    ],
    "objectives": [
        {"objective_id": "o1", "target": "drainage_flow_ml_hr",
         "direction": "MAXIMIZE",
         "basis": "problem: insufficient drainage flow at low head"},
    ],
    "dependencies": [
        {"relation_id": "r1", "cause": "lumen_diameter_mm",
         "effect": "wall_thickness_mm", "direction": "DECREASES",
         "relation_class": "MODELLED",
         "statement": "enlarging the lumen thins the wall"},
        {"relation_id": "r2", "cause": "lumen_diameter_mm",
         "effect": "drainage_flow_ml_hr", "direction": "INCREASES",
         "relation_class": "MODELLED",
         "statement": "Poiseuille: flow scales with lumen radius^4"},
    ],
}
state, report = validate_technical_state(state_proposal, [], problem)
spec = {"candidate_id": "SMOKE-R383",
        "mechanism": {"value": {"mechanism": "dual-lumen tube",
                                "intervention": "parametric body",
                                "expected_effect": "drainage"}}}
spec = attach_technical_state(spec, state,
                              {"proposal_id": "smoke", "provider": "SMOKE",
                               "model": "fixture", "status": "OK"},
                              report)
q = evaluate_candidate_quantitatively(spec)
print("status:", q["status"])
for c in q["computations"]:
    print(f"  {c['equation_id']}: {c['status']} "
          f"value={c.get('value')} {c.get('output_unit')} "
          f"-> param {c.get('output_param_id')}")
obj = q["objective"]
print("objective:", obj["statement"][:220])
print("margin:", obj["margin"], obj["margin_status"])
lv = q.get("limiting_variable")
if lv:
    print("LV:", lv["param_id"], lv["improving_move"],
          "elasticity:", lv["elasticity"])
    print("solve_for:", {k: v for k, v in (lv.get("solve_for") or
                                           {}).items()
                         if k in ("status", "proposed_value",
                                  "predicted_output",
                                  "predicted_margin", "target_value",
                                  "best_output")})
    print("statement:", lv["statement"][:400])
print("\nsensitivity:")
for pid, s in q["sensitivity"].items():
    print(f"  {pid}: elasticity={s['elasticity']} "
          f"d={s['derivative']:.6g} {s['derivative_units']}")
visc = [i for b in q["bindings"] for i in b["inputs"]
        if i.get("role") == "viscosity"]
if visc:
    print("\nviscosity source:", visc[0]["source"],
          visc[0].get("constant_id"))
assert q["status"] == "QUANTIFIED"
assert abs(obj["value"] - 12.72) < 0.02, obj["value"]
assert abs(obj["margin"] - (-0.364)) < 0.005, obj["margin"]
assert lv and lv["param_id"] == "lumen_diameter_mm"
assert abs(lv["elasticity"] - 4.0) < 0.05, lv["elasticity"]
sf = lv["solve_for"]
assert sf["status"] == "REACHABLE"
assert abs(sf["proposed_value"] - 0.3438) < 0.002, sf["proposed_value"]
assert abs(sf["predicted_output"] - 22.0) < 0.05, sf["predicted_output"]
assert visc and visc[0]["source"] == "ENGINEERING_REFERENCE"
print("\nSMOKE OK — hand-verified numbers match")
