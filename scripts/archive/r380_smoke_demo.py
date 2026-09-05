"""R380 smoke: dual-lumen tube technical state -> full CAD pass."""
import json
import sys
import tempfile

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")
from discovery_fabric.engine.cad_pipeline import (  # noqa: E402
    run_cad_pass, geometry_warrants_3d, rebuild_with_mutation,
)

state = {
    "objects": [
        {"object_id": "dual_lumen_tube",
         "role": "outer body with two through-lumens and septum"},
    ],
    "parameters": [
        {"param_id": "outer_diameter_mm", "name": "outer diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 3.0,
         "value_class": "MODELLED", "range_min": 2.0, "range_max": 5.0,
         "range_class": "MODELLED", "role": "device envelope"},
        {"param_id": "lumen_diameter_mm", "name": "lumen diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 1.0,
         "value_class": "MODELLED", "range_min": 0.5, "range_max": 2.0,
         "range_class": "MODELLED", "role": "drainage lumen"},
        {"param_id": "length_mm", "name": "tube length",
         "category": "GEOMETRY", "unit": "mm", "value": 30.0,
         "value_class": "MODELLED", "range_min": 10.0, "range_max": 60.0,
         "range_class": "MODELLED", "role": "implant length"},
        {"param_id": "septum_thickness_mm", "name": "septum thickness",
         "category": "GEOMETRY", "unit": "mm", "value": 0.2,
         "value_class": "MODELLED", "range_min": 0.05, "range_max": 0.5,
         "range_class": "MODELLED", "role": "wall between lumens"},
        {"param_id": "wall_thickness_mm", "name": "min wall thickness",
         "category": "PARAMETERS", "unit": "mm", "value": None,
         "value_class": "UNKNOWN", "range_min": None, "range_max": None,
         "range_class": "UNKNOWN", "role": "measured outcome"},
    ],
    "constraints": [
        {"constraint_id": "c1", "target": "wall_thickness_mm",
         "bound": ">=", "limit": 0.15, "limit_class": "MODELLED",
         "justification": "thin-wall micro-extrusion manufacturability"},
    ],
    "dependencies": [],
    "materials": [
        {"material_id": "silicone", "name": "medical grade silicone"}],
    "operating_conditions": [],
    "measurable_outputs": [],
}
spec = {
    "candidate_id": "M2-DUAL-LUMEN-SMOKE",
    "technical_state": {"value": state},
}

w = geometry_warrants_3d(spec)
print("warrants:", w["verdict"], w["measured_basis"])

with tempfile.TemporaryDirectory() as td:
    new_spec, ledger = run_cad_pass(spec, out_dir=td, allow_llm=False)
    print("outcome:", ledger["outcome"])
    print("model_id:", ledger.get("model_id"))
    v = ((new_spec.get("parametric_model") or {}).get("value") or {})
    gv = v.get("geometry_validation") or {}
    print("geometry valid:", gv.get("valid"))
    for g, c in sorted((gv.get("checks") or {}).items()):
        print(f"  {g}: {c['status']}")
    m = (v.get("measurements") or {}).get("objects", {}).get(
        "dual_lumen_tube", {})
    print("measured wall:", m.get("min_wall_thickness_mm"))
    print("measured volume:", m.get("volume_mm3"))
    print("measured bbox:", m.get("bbox"))
    print("artifacts:", sorted((v.get("derived_artifacts") or
                                {}).keys()))
    for k, art in (v.get("derived_artifacts") or {}).items():
        print(f"  {k}: {art.get('bytes')}B sha={str(art.get('sha256'))[:12]}")
    print("views:", {k: (str(p)[:40] if isinstance(p, str) else p)
                     for k, p in (v.get("views") or {}).items()})

    # the CEO mutation example: lumen 1.0 -> 1.2 (KEEP region), then
    # 1.0 -> 1.7 (wall goes negative -> GEOMETRY INVALID)
    model = v
    for newv in (1.2, 1.7):
        child, rec = rebuild_with_mutation(
            model, "lumen_diameter_mm", newv, "tmut:smoke", "demo",
            out_dir=td)
        gvc = (child or {}).get("geometry_validation") or {}
        wall = (((child or {}).get("measurements") or {})
                .get("objects", {}).get("dual_lumen_tube", {})
                .get("min_wall_thickness_mm"))
        print(f"mutation 1.0 -> {newv}: rebuild={rec.get('status')} "
              f"valid={gvc.get('valid')} measured_wall={wall}")
        if not gvc.get("valid"):
            print("  kill reasons:", [r[:90] for r in
                                      (gvc.get("reasons") or [])][:3])
