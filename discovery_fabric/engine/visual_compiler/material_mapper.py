"""material_mapper.py — R441 semantic material mapping.

The Material Constitution (operator directive R441): the material comes
from the COMPONENT TYPE, never from a prompt. One deterministic mapping,
applied identically by the renderer and disclosed in the render record:

    Battery      -> dark graphite
    Solar/PV     -> blue-black silicon
    Motor/shaft  -> machined aluminum
    Chassis      -> matte steel
    Glass        -> clear
    Cooling      -> copper
    Electronics  -> dark polymer
    (+ the R432 scientific-industrial classes, carried forward)

Resolution order (ONE source of truth — the canonical geometry spec
when the run carries one, else the name classifier):

  1. GEOMETRY_SPEC.json (canonical): part.component_id -> material_class
     — the SAME spec classes the deterministic geometry builders used
     for their vertex palettes (R432 sections 5/10: one material
     source of truth).
  2. keyword classifier over the node name (deterministic, ordered,
     first hit wins) — the same hints the Blender path used, now the
     documented fallback.
  3. typed default (never invented per-render: the fallback IS the
     policy, recorded in the mapping table).

Every mapping decision lands in the scene_spec the gate re-verifies:
100% of mesh nodes must resolve to a semantic class (Visual Quality
Gate rule "semantic materials: required").
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# The semantic PBR table. base color is linear RGB (the renderer feeds it
# straight into MeshPhysicalMaterial; the old vertex palettes in
# domain_geometry.py remain the geometry-side identity palette).
#
# R443 (operator directive — material semantics made measurable): the
# table was re-derived against the RENDERED probe measurement (not the
# spec numbers alone) so that every pair of distinct semantic classes
# is OBSERVABLY distinct in the actual render — minimum measured
# rendered separation 10.68 dE00 across all 78 pairs (13 classes,
# live probe runs 2026-09-10), above the 10.0 bar with the probe's
# byte-deterministic rendering. The R442 round record measured the
# old table at CIEDE2000 1.01 between body_metal and machined_metal —
# BELOW the just-noticeable difference (~2.3, CIE 142:2001). The
# re-derived table keeps every semantic label's character (steel dark
# gunmetal, aluminum mirror-chrome, copper copper); the "default"
# class is deliberately a flagging magenta — an UNCLASSIFIED part
# must be noticeable, not silently plausible (Art. XXV: unclassified
# is a state to surface, not to hide). The rendered probe measurement
# (visual_gate.measure_material_distinction) is the standing
# acceptance; provenance in visual_compiler_thresholds.json rev 3.
# ---------------------------------------------------------------------------
SEMANTIC_MATERIALS: Dict[str, Dict[str, Any]] = {
    "body_metal":     {"label": "matte steel (dark)",       "base": (0.13, 0.18, 0.34), "metallic": 0.55, "roughness": 0.5},
    "glass":          {"label": "clear glass",           "base": (0.30, 0.68, 0.90), "metallic": 0.0,  "roughness": 0.08, "alpha": 0.5, "transmission": 0.65},
    "silicon":        {"label": "blue-black silicon",    "base": (0.02, 0.035, 0.13), "metallic": 0.35, "roughness": 0.22},
    "battery":        {"label": "dark graphite",         "base": (0.085, 0.09, 0.10), "metallic": 0.3,  "roughness": 0.45},
    "rubber":         {"label": "rubber",                "base": (0.06, 0.05, 0.045), "metallic": 0.0,  "roughness": 0.9},
    "polymer":        {"label": "engineering polymer",   "base": (0.70, 0.51, 0.25), "metallic": 0.0,  "roughness": 0.55},
    "machined_metal": {"label": "machined aluminum",     "base": (0.72, 0.76, 0.84), "metallic": 1.0,  "roughness": 0.06},
    "circuit":        {"label": "dark polymer (PCB)",    "base": (0.07, 0.24, 0.13), "metallic": 0.05, "roughness": 0.5},
    "ceramic":        {"label": "technical ceramic",     "base": (0.97, 0.97, 0.96), "metallic": 0.0,  "roughness": 0.22},
    "composite":      {"label": "composite",             "base": (0.20, 0.25, 0.17), "metallic": 0.05, "roughness": 0.55},
    "conduit_power":  {"label": "copper (cooling)",      "base": (0.75, 0.42, 0.20), "metallic": 0.85, "roughness": 0.35},
    "conduit_data":   {"label": "data conduit",          "base": (0.28, 0.18, 0.66), "metallic": 0.4,  "roughness": 0.4},
    "default":        {"label": "unclassified (flagged)", "base": (0.55, 0.15, 0.42), "metallic": 0.15, "roughness": 0.5},
}

# The directive's headline table, in keywords-first order. First hit wins;
# the tuple order IS the policy (deterministic, versioned here).
_KEYWORD_RULES: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("battery", "pack_cell", "cell_pack", "bms"), "battery"),
    (("solar", "pv_", "panel", "photovoltaic"), "silicon"),
    (("motor", "stator", "rotor", "shaft", "bearing", "gear",
      "heat_sink", "heatsink", "sink", "antenna", "bus"), "machined_metal"),
    (("thermal", "coolant", "cooling", "loop", "channel", "radiator",
      "condenser", "evaporator"), "conduit_power"),
    (("glass", "window", "lens", "cabin_dome"), "glass"),
    (("board", "pcb", "control", "sensor", "electronics",
      "computer", "ecu"), "circuit"),
    (("wire", "cable", "conduit_data", "harness"), "conduit_data"),
    (("pipe", "tube", "hose", "manifold", "valve_body"), "conduit_power"),
    (("wheel", "tire", "tyre", "seal", "gasket", "o_ring"), "rubber"),
    (("chassis", "frame", "hull", "body", "enclosure", "housing",
      "mount", "bracket", "hub", "port", "connector"), "body_metal"),
    (("tip", "membrane", "coating", "valve", "chamber", "balloon",
      "cuff"), "polymer"),
    (("ceramic", "insulator"), "ceramic"),
    (("carbon", "composite", "fairing"), "composite"),
    (("tube", "catheter", "lumen", "shunt"), "polymer"),
)


def _norm(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_").replace(" ", "_")


def classify_node_name(name: str) -> str:
    """Deterministic keyword classification of one node name."""
    n = _norm(name)
    for keywords, cls in _KEYWORD_RULES:
        for kw in keywords:
            if kw in n:
                return cls
    return "default"


def _spec_part_index(spec: Dict[str, Any]) -> Dict[str, str]:
    """component_id (and label) -> material_class from the canonical
    geometry spec's parts layer."""
    out: Dict[str, str] = {}
    for part in (spec.get("parts") or []):
        cls = part.get("material_class")
        if not cls:
            continue
        for key in (part.get("component_id"), part.get("label")):
            if key:
                out[_norm(str(key))] = cls
    return out


def build_mapping(node_names: List[str],
                  geometry_spec: Optional[Dict[str, Any]] = None,
                  ) -> Dict[str, Dict[str, Any]]:
    """node name -> renderer material dict (semantic + PBR fields).

    The returned mapping is embedded verbatim in scene_spec.json; the
    renderer applies it without inventing anything, and the gate checks
    that every mesh node is covered and resolves to a semantic class.
    """
    spec_index = _spec_part_index(geometry_spec or {})
    mapping: Dict[str, Dict[str, Any]] = {}
    provenance: Dict[str, str] = {}
    for name in node_names:
        n = _norm(name)
        cls = None
        src = None
        # 1. canonical spec: exact component_id / label match, else the
        #    component_id-prefix the deterministic builders embed in the
        #    node name ({component_id}_{suffix})
        if n in spec_index:
            cls, src = spec_index[n], "geometry_spec"
        else:
            for cid, c in spec_index.items():
                if cid and n.startswith(cid + "_"):
                    cls, src = c, "geometry_spec"
                    break
        # 2. keyword classifier (the documented fallback policy)
        if cls is None:
            cls, src = classify_node_name(name), "keyword_rules"
        if cls not in SEMANTIC_MATERIALS:
            cls, src = "default", "keyword_rules"  # unknown class in spec
        mat = SEMANTIC_MATERIALS[cls]
        mapping[name] = {
            "class": cls,
            "label": mat["label"],
            "color": list(mat["base"]),
            "metallic": mat["metallic"],
            "roughness": mat["roughness"],
        }
        for extra in ("alpha", "transmission"):
            if extra in mat:
                mapping[name][extra] = mat[extra]
        provenance[name] = src
    return {"mapping": mapping, "provenance": provenance,
            "classes_used": sorted({m["class"] for m in mapping.values()})}


def load_geometry_spec(work_dir: str,
                       geometry_out: Optional[Dict[str, Any]] = None,
                       ) -> Optional[Dict[str, Any]]:
    """The canonical geometry spec when the run carries one (same file
    the R432 path persisted for the render stage)."""
    candidates = []
    if geometry_out and geometry_out.get("geometry_spec"):
        return geometry_out["geometry_spec"]
    import os
    p = os.path.join(work_dir, "MODEL", "GEOMETRY_SPEC.json")
    if os.path.isfile(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:  # noqa: BLE001 — typed upstream, never a guess
            return None
    return candidates or None
