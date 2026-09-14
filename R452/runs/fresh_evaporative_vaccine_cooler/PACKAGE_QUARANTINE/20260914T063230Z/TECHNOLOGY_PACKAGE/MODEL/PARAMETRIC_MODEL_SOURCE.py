"""PARAMETRIC MODEL SOURCE — exported from the canonical
engineering geometry program (R425: one CAD source of truth).

Canonical program : discovery_fabric.engine.invention_bridge.engineering_geometry
Builder function  : build_layered_panel
Form              : layered_panel
Canonical module sha256      : b0459b05551b5118a81b1e3283891c5351bf20575d1a23a26a792508ced7b5bb
Canonical builder source sha256: ff2d8d7e543ef6e2e98c66ab790fd0616e3c2a14c46ff1faa933f0494bbb2e0c
Parameter hash (build map)    : 99669aea53cc15d3c97701b7e516ea517ae02c3192edb9361edd57b9674be876

This file is DERIVED, not authored: the builder below is the canonical
FORM_LIBRARY builder, exported verbatim. Executing build() with
MODEL/PARAMETERS.json (or the PARAMETERS literal below) reconstructs
the same geometry the canonical bridge executed; MODEL/STEP/STL/GLB
files are derived artifacts of exactly this program (see
MODEL/CAD_SOURCE_PROVENANCE.json for the full relationship and hashes).

Regeneration check:
    python PARAMETRIC_MODEL_SOURCE.py
rebuilds the solid, measures it (OCCT), and prints the measurements as
JSON — compare against MODEL/KEY_DIMENSIONS.json and
MODEL/3D_EVIDENCE/REGENERATION_CHECK.json.
"""
from typing import Dict, Optional

import cadquery as cq


def build_layered_panel(params: Dict[str, float]) -> cq.Workplane:
    """Solar/energy panel family: substrate + cell + functional layers + frame.

    Expected params (all mm): panel_width, panel_length, substrate_t,
    cell_t, functional_t, frame_w.
    """
    w = params.get("panel_width", 160.0)
    l = params.get("panel_length", 160.0)
    substrate_t = params.get("substrate_t", 3.0)
    cell_t = params.get("cell_t", 0.2)
    functional_t = params.get("functional_t", 0.5)
    frame_w = params.get("frame_w", 10.0)

    if min(w, l, substrate_t, cell_t, functional_t) <= 0:
        raise ValueError("layered_panel: non-positive parameter")

    z = 0.0
    solid = cq.Workplane("XY").box(w, l, substrate_t, centered=(True, True, False))
    z += substrate_t
    solid = solid.union(
        cq.Workplane("XY").workplane(offset=z)
        .box(w - 2 * frame_w, l - 2 * frame_w, cell_t, centered=(True, True, False))
    )
    z += cell_t
    solid = solid.union(
        cq.Workplane("XY").workplane(offset=z)
        .box(w - 2 * frame_w, l - 2 * frame_w, functional_t, centered=(True, True, False))
    )
    z += functional_t
    frame = (
        cq.Workplane("XY").box(w, l, z, centered=(True, True, False))
        .cut(cq.Workplane("XY").box(w - 2 * frame_w, l - 2 * frame_w, z + 1,
                                    centered=(True, True, False)))
    )
    return solid.union(frame)



PARAMETERS = {
    "geom-cell_t": 0.2,
    "geom-frame_w": 10.0,
    "geom-functional_t": 0.5,
    "geom-panel_length": 300.0,
    "geom-panel_width": 300.0,
    "geom-substrate_t": 3.0
}


def build(p: Optional[Dict[str, float]] = None) -> "cq.Workplane":
    """Entry point preserving the shipped-source contract: build(p)
    executes the canonical builder over the shipped parameter map
    (or an explicit override map p)."""
    return build_layered_panel(PARAMETERS if p is None else p)


if __name__ == "__main__":
    import json as _json
    import sys as _sys
    from pathlib import Path as _Path
    _p = _Path(__file__).resolve().parent / "PARAMETERS.json"
    if _p.is_file():
        _doc = _json.loads(_p.read_text())
        _values = {}
        for _e in _doc.get("parameters", []):
            _pid = str(_e.get("param_id") or "")
            _v = _e.get("value")
            if isinstance(_v, (int, float)) and _pid:
                # canonical builder keys are unit-suffix-free (the same
                # normalization the bridge applies); the raw id is kept
                # too so both spellings drive the build
                _values[_pid] = _v
                _values[_pid.replace("_mm", "").replace(
                    "-mm", "").replace(" ", "_").lower()] = _v
        if _values:
            PARAMETERS.update(_values)
    _solid = build()
    _bb = _solid.val().BoundingBox()
    _out = {
        "form": 'layered_panel',
        "volume_mm3": round(_solid.val().Volume(), 6),
        "bbox": {"xlen": round(_bb.xlen, 6), "ylen": round(_bb.ylen, 6),
                 "zlen": round(_bb.zlen, 6)},
        "parameters": PARAMETERS,
    }
    _sys.stdout.write(_json.dumps(_out, indent=2))
