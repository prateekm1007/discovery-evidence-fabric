"""Engineering geometry builder — ENGINEERING_3D (parametric CadQuery/OCCT).

Only used when the recorded run state contains sourced/declared geometry
parameters (numeric value + unit + envelope). Builds device-form parametric
CAD, MEASURES it (volume, bounding box, per-feature), validates it through the
deterministic gates (independent trimesh watertight check + regeneration
determinism check, matching the released-chain conventions) and exports
GLB + STEP + STL.

Every parameter value is labeled with its value_class (MODELLED design
proposal inside a declared envelope, or SOURCE_FACT bound to evidence) —
conventions identical to the released chain (P-07).

Geometry failure is never terminal-silent: the builder returns a categorized
diagnosis so the bridge can attempt repair (handoff section 17):
    GEOMETRY_FAILURE -> diagnose -> repair -> rebuild
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cadquery as cq
import trimesh

from .coloring import apply_gltf_yup, set_uniform_color
from .epistemics import VALUE_CLASS_MODELLED, VALUE_CLASS_SOURCE_FACT

MM_UNITS = {"mm", "millimeter", "millimetre", "mm."}


def _in_mm(unit: str) -> bool:
    return str(unit or "").strip().lower() in MM_UNITS


# ---------------------------------------------------------------------------
# Form library — one builder per device family
# ---------------------------------------------------------------------------

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


def build_dual_lumen_catheter(params: Dict[str, float]) -> cq.Workplane:
    """Medical catheter family (released-chain P-07 conventions).

    Expected params (mm): outer_diameter, primary_lumen_diameter,
    floor_lumen_diameter, floor_offset, length.
    """
    od = params.get("outer_diameter", 3.0)
    pd_ = params.get("primary_lumen_diameter", 1.1)
    fd = params.get("floor_lumen_diameter", 0.6)
    off = params.get("floor_offset", 1.0)
    length = params.get("length", 100.0)

    if min(od, pd_, fd, length) <= 0:
        raise ValueError("catheter: non-positive parameter")
    if pd_ / 2 + fd / 2 + 0.2 > od:  # walls must exist
        raise ValueError("catheter: lumens exceed outer diameter — wall containment violated")

    body = cq.Workplane("XY").circle(od / 2).extrude(length)
    primary = cq.Workplane("XY").workplane(offset=-1).circle(pd_ / 2).extrude(length + 2)
    floor = (
        cq.Workplane("XY").workplane(offset=-1)
        .center(off, 0.0).circle(fd / 2).extrude(length + 2)
    )
    return body.cut(primary).cut(floor)


def build_cylindrical_device(params: Dict[str, float]) -> cq.Workplane:
    """Generic cylindrical housing: body + internal cavity + port.

    Expected params (mm): outer_diameter, height, wall_thickness, port_diameter.
    """
    od = params.get("outer_diameter", 20.0)
    h = params.get("height", 50.0)
    wall = params.get("wall_thickness", 2.0)
    port = params.get("port_diameter", 5.0)

    if min(od, h, wall, port) <= 0 or 2 * wall >= od:
        raise ValueError("cylindrical_device: parameters violate wall containment")

    body = cq.Workplane("XY").circle(od / 2).extrude(h)
    cavity = (
        cq.Workplane("XY").workplane(offset=wall)
        .circle(od / 2 - wall).extrude(h - 2 * wall)
    )
    port_cut = (
        cq.Workplane("XY").workplane(offset=-1)
        .circle(port / 2).extrude(wall + 2)
    )
    return body.cut(cavity).cut(port_cut)


FORM_LIBRARY = {
    "layered_panel": build_layered_panel,
    "dual_lumen_catheter": build_dual_lumen_catheter,
    "cylindrical_device": build_cylindrical_device,
}

# Domain/intervention-site -> form routing (deterministic)
FORM_ROUTING = [
    (("solar", "photovoltaic", "pv panel", "panel"), "layered_panel"),
    (("catheter", "lumen", "shunt", "drainage"), "dual_lumen_catheter"),
    (("housing", "enclosure", "implant", "pump body", "device body"), "cylindrical_device"),
]


def route_form(intervention_site: str, subsystems: List[str]) -> str:
    text = (intervention_site or "").lower() + " " + " ".join(s.lower() for s in subsystems)
    for signals, form in FORM_ROUTING:
        if any(sig in text for sig in signals):
            return form
    return "cylindrical_device"  # conservative default form


def default_form_basis(form: str, intervention_site: str,
                       subsystems: List[str]) -> Dict[str, Any]:
    """R452 (external audit C1/AT-6): a routed-default FORM_LIBRARY
    form is recorded HONESTLY — representation_class
    ENGINEERING_PARAMETRIC_DEFAULT_FORM with the explicit basis that
    the three-shape library does not contain the invention's own form.
    The default is never silently presented as the invention's
    geometry (Art. XXVIII: no silent semantic promotion)."""
    text = (intervention_site or "").lower() + " " + \
        " ".join(s.lower() for s in subsystems)
    matched = [(sig, form_name) for sigs, form_name in FORM_ROUTING
               for sig in sigs if sig in text]
    is_default = not matched
    return {
        "form": form,
        "representation_class": (
            "ENGINEERING_PARAMETRIC_DEFAULT_FORM" if is_default
            else "ENGINEERING_PARAMETRIC_ROUTED_FORM"),
        "form_basis": (
            "the FORM_LIBRARY routing matched no form signal for "
            f"site {intervention_site!r}; the conservative default "
            f"{form!r} is used — the three-shape library does not "
            "contain the invention's own form, and the default shape "
            "is NOT the invention's geometry (audit C1: FORM_LIBRARY "
            "insufficiency disclosed, never hidden)"
            if is_default else
            f"FORM_ROUTING matched {matched} for site "
            f"{intervention_site!r}"),
        "form_library_forms": sorted(FORM_LIBRARY),
        "routed_signals_matched": matched,
    }


# ---------------------------------------------------------------------------
# Canonical parametric-source export (R425 §2 — ONE CAD source of truth)
# ---------------------------------------------------------------------------

def _module_sha256() -> Optional[str]:
    """sha256 of THIS module's bytes on disk — the canonical program's own
    identity (None only when the file is genuinely unreadable, never a
    guess; Art. VI)."""
    try:
        p = Path(__file__).resolve()
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def canonical_source_identity(form: str) -> Dict[str, Any]:
    """The identity tuple of a canonical FORM_LIBRARY builder.

    This is THE export authority for the package layer (R425 §2): the
    package's MODEL/PARAMETRIC_MODEL_SOURCE.py must be derived from the
    EXACT canonical builder this function identifies — an independently
    handwritten reimplementation of the geometry in the package layer
    is a second source of truth and is constitutionally forbidden
    (Art. X: one canonical authority; Art. VI: provenance is real).

    Returns the identity even for an unknown form (with
    builder_function=None) so callers can record the refusal honestly.
    """
    builder = FORM_LIBRARY.get(form)
    if builder is None:
        return {
            "form": form,
            "builder_function": None,
            "canonical_module": __name__,
            "module_path": str(Path(__file__).resolve()),
            "module_sha256": _module_sha256(),
            "builder_source_sha256": None,
            "form_library_forms": sorted(FORM_LIBRARY),
            "status": "UNKNOWN_FORM — no canonical builder exists for "
                      f"form '{form}'; nothing may be exported or "
                      "reimplemented (Art. XXV)",
        }
    source_text = inspect.getsource(builder)
    return {
        "form": form,
        "builder_function": builder.__name__,
        "canonical_module": __name__,
        "module_path": str(Path(__file__).resolve()),
        "module_sha256": _module_sha256(),
        "builder_source_sha256": hashlib.sha256(
            source_text.encode("utf-8")).hexdigest(),
        "form_library_forms": sorted(FORM_LIBRARY),
        "status": "CANONICAL",
    }


def _exported_file_text(form: str, parameters: Dict[str, float],
                        identity: Dict[str, Any],
                        parameter_hash: str) -> str:
    """The standalone parametric source, DERIVED from the canonical
    builder — never a reimplementation.

    The exported file is executable on its own: `build(p)` (or no-arg
    `build()` over the shipped PARAMETERS literal) reconstructs the
    geometry with deterministic CadQuery/OCCT semantics identical to
    the canonical FORM_LIBRARY entry, because the builder body below
    IS the canonical builder body, exported verbatim via
    inspect.getsource (R425 §2's one authoritative source path:
    canonical builder -> exported parametric source + parameters ->
    derived STEP/STL/GLB).
    """
    builder = FORM_LIBRARY[form]
    builder_source = inspect.getsource(builder)
    param_literal = json.dumps(parameters, indent=4, sort_keys=True)
    return f'''"""PARAMETRIC MODEL SOURCE — exported from the canonical
engineering geometry program (R425: one CAD source of truth).

Canonical program : {identity["canonical_module"]}
Builder function  : {identity["builder_function"]}
Form              : {form}
Canonical module sha256      : {identity["module_sha256"]}
Canonical builder source sha256: {identity["builder_source_sha256"]}
Parameter hash (build map)    : {parameter_hash}

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


{builder_source}


PARAMETERS = {param_literal}


def build(p: Optional[Dict[str, float]] = None) -> "cq.Workplane":
    """Entry point preserving the shipped-source contract: build(p)
    executes the canonical builder over the shipped parameter map
    (or an explicit override map p)."""
    return {builder.__name__}(PARAMETERS if p is None else p)


if __name__ == "__main__":
    import json as _json
    import sys as _sys
    from pathlib import Path as _Path
    _p = _Path(__file__).resolve().parent / "PARAMETERS.json"
    if _p.is_file():
        _doc = _json.loads(_p.read_text())
        _values = {{}}
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
    _out = {{
        "form": {form!r},
        "volume_mm3": round(_solid.val().Volume(), 6),
        "bbox": {{"xlen": round(_bb.xlen, 6), "ylen": round(_bb.ylen, 6),
                 "zlen": round(_bb.zlen, 6)}},
        "parameters": PARAMETERS,
    }}
    _sys.stdout.write(_json.dumps(_out, indent=2))
'''


def parameter_map_hash(parameters: Dict[str, Any]) -> str:
    """sha256 over the canonical JSON serialization of a build parameter
    map — the parameter identity recorded in CAD_SOURCE_PROVENANCE and
    the exported source header (one definition, used by both)."""
    return hashlib.sha256(json.dumps(
        parameters, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def export_parametric_source(form: str,
                             parameters: Dict[str, float]
                             ) -> Tuple[Optional[str], Dict[str, Any]]:
    """(file_text, identity) — the ONE authoritative export path from
    the canonical geometry program to the package's parametric source.

    file_text is None only when no canonical builder exists for the
    form (the identity records the honest UNKNOWN_FORM refusal; a
    package layer must then ship NO parametric source at all — never
    a reimplementation, R425 §2).
    """
    identity = canonical_source_identity(form)
    if identity.get("builder_function") is None:
        return None, identity
    param_hash = parameter_map_hash(parameters)
    return _exported_file_text(form, parameters, identity, param_hash), identity


def verify_cad_source_provenance(model_dir: str) -> Dict[str, Any]:
    """Drift detector (R425 §2 regression hook): re-derive the LIVE
    canonical builder identity and compare it against the identity a
    shipped package recorded in MODEL/CAD_SOURCE_PROVENANCE.json.

    VERDICTS:
      CANONICAL_SOURCE_CONFIRMED — every recorded identity field still
        matches the live canonical program;
      DRIFT_DETECTED — the canonical builder changed after the package
        was built (source or module hash mismatch): the package's
        provenance statement no longer describes the live program;
      PROVENANCE_RECORD_ABSENT / UNKNOWN_FORM — the package layer
        failed to record (or recorded an unresolvable) canonical
        identity — itself a defect for an ENGINEERING package.
    """
    record_path = Path(model_dir) / "CAD_SOURCE_PROVENANCE.json"
    if not record_path.is_file():
        return {"verdict": "PROVENANCE_RECORD_ABSENT",
                "model_dir": str(model_dir)}
    try:
        record = json.loads(record_path.read_text())
    except (OSError, ValueError) as exc:
        return {"verdict": "PROVENANCE_RECORD_UNREADABLE",
                "error": f"{type(exc).__name__}: {exc}"}
    recorded = record.get("canonical_builder") or {}
    form = recorded.get("form")
    live = canonical_source_identity(form) if form else {}
    fields = ("builder_function", "canonical_module",
              "module_sha256", "builder_source_sha256")
    mismatches = [f for f in fields
                  if recorded.get(f) != live.get(f)]
    return {
        "verdict": ("CANONICAL_SOURCE_CONFIRMED" if not mismatches
                    else "DRIFT_DETECTED"),
        "form": form,
        "mismatched_fields": mismatches,
        "recorded_identity": recorded,
        "live_identity": {k: live.get(k) for k in fields},
    }


# ---------------------------------------------------------------------------
# Parameter normalization
# ---------------------------------------------------------------------------

def normalize_parameters(geometry_parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert the classifier's geometry parameters into a build input dict.

    Only mm-family units participate in the parametric build; other-unit
    parameters are recorded but do not drive geometry (recorded in the report).
    """
    params: Dict[str, float] = {}
    meta: List[Dict[str, Any]] = []
    for p in geometry_parameters or []:
        pid = str(p.get("param_id") or p.get("name") or "").strip()
        if not pid or p.get("value") is None:
            continue
        unit = str(p.get("unit") or "")
        entry = {
            "param_id": pid,
            "unit": unit,
            "value": float(p["value"]),
            "envelope": p.get("envelope"),
            "value_class": p.get("value_class") or VALUE_CLASS_MODELLED,
            "origin": p.get("origin", "run state"),
            "used_in_build": False,
        }
        if _in_mm(unit):
            key = pid.replace("_mm", "").replace("-mm", "").replace(" ", "_").lower()
            # remap known naming variants onto form-library keys
            key = {
                "outer_diameter": "outer_diameter",
                "diameter": "outer_diameter",
                "length": "length",
                "primary_lumen_diameter": "primary_lumen_diameter",
                "floor_lumen_diameter": "floor_lumen_diameter",
                "floor_offset": "floor_offset",
                "width": "panel_width",
                "panel_width": "panel_width",
                "panel_length": "panel_length",
                "substrate_t": "substrate_t",
                "cell_t": "cell_t",
                "functional_t": "functional_t",
                "frame_w": "frame_w",
                "height": "height",
                "wall_thickness": "wall_thickness",
                "port_diameter": "port_diameter",
                # R452 (audit A2): the domain registry's own
                # DIMENSIONALLY-COMPATIBLE parameter names join to the
                # same form keys (a pressure or a viscosity is NEVER
                # remapped onto a length — that would misuse the value;
                # non-mm parameters are recorded but do not drive the
                # build, which is the existing honest contract)
                "lumen_inner_diameter": "outer_diameter",
                "inner_diameter": "outer_diameter",
                "lumen_diameter": "outer_diameter",
                "lumen_length": "length",
            }.get(key, key)
            params[key] = float(p["value"])
            entry["used_in_build"] = True
        meta.append(entry)
    return {"build_params": params, "parameter_meta": meta}


# ---------------------------------------------------------------------------
# Measure + validation gates (released-chain conventions)
# ---------------------------------------------------------------------------

def measure(solid: cq.Workplane) -> Dict[str, Any]:
    bb = solid.val().BoundingBox()
    return {
        "volume_mm3": round(solid.val().Volume(), 6),
        "bbox": {
            "xlen": round(bb.xlen, 6), "ylen": round(bb.ylen, 6), "zlen": round(bb.zlen, 6),
            "xmin": round(bb.xmin, 6), "xmax": round(bb.xmax, 6),
            "ymin": round(bb.ymin, 6), "ymax": round(bb.ymax, 6),
            "zmin": round(bb.zmin, 6), "zmax": round(bb.zmax, 6),
        },
        "is_valid_solid": solid.val().isValid(),
    }


def validate_gates(solid: cq.Workplane, mesh: trimesh.Trimesh,
                   rebuild_fn=None) -> Dict[str, Any]:
    """Deterministic validation gates:
    G1 trimesh independent watertight check, G2 regeneration determinism.
    """
    watertight = bool(mesh.is_watertight)
    regen = None
    if rebuild_fn is not None:
        second = rebuild_fn()
        regen = {
            "check": "G9_regeneration",
            "volume_delta_mm3": abs(second.val().Volume() - solid.val().Volume()),
            "deterministic": abs(second.val().Volume() - solid.val().Volume()) < 1e-9,
        }
    return {
        "artifact": "GEOMETRY_VALIDATION_REPORT",
        "gates": {
            "G1_trimesh_watertight": watertight,
            "G9_regeneration": regen,
        },
        "passed": watertight and (regen is None or regen["deterministic"]),
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export(solid: cq.Workplane, name: str, out_dir: str,
           component_colors: Optional[Dict[str, Tuple[int, int, int, int]]] = None,
           component_solids: Optional[List[Tuple[str, cq.Workplane]]] = None) -> Dict[str, Any]:
    """Export GLB (named nodes per component) + STEP + STL for ENGINEERING_3D."""
    import os
    os.makedirs(out_dir, exist_ok=True)

    scene = trimesh.Scene()
    if component_solids:
        for cname, csolid in component_solids:
            verts, tris = csolid.val().tessellate(0.05)
            mesh = trimesh.Trimesh(
                vertices=[(v.x, v.y, v.z) for v in verts],
                faces=[list(t) for t in tris], process=False)
            color = (component_colors or {}).get(cname, (168, 98, 66, 255))
            # R419: vertex colors — the face-color path requires scipy at use
            # time (production defect "No module named 'scipy'"); see
            # coloring.py for the measured matrix.
            set_uniform_color(mesh, color)
            # R419: canonical glTF Y-up orientation (see coloring.py).
            apply_gltf_yup(mesh)
            scene.add_geometry(mesh, node_name=cname, geom_name=cname)
    else:
        verts, tris = solid.val().tessellate(0.05)
        mesh = trimesh.Trimesh(
            vertices=[(v.x, v.y, v.z) for v in verts],
            faces=[list(t) for t in tris], process=False)
        set_uniform_color(mesh, (168, 98, 66, 255))
        apply_gltf_yup(mesh)
        scene.add_geometry(mesh, node_name=name, geom_name=name)

    glb_path = os.path.join(out_dir, f"{name}.glb")
    glb_bytes = scene.export(file_type="glb")
    with open(glb_path, "wb") as f:
        f.write(glb_bytes)

    step_path = os.path.join(out_dir, f"{name}.step")
    cq.exporters.export(solid, step_path)
    stl_path = os.path.join(out_dir, f"{name}.stl")
    cq.exporters.export(solid, stl_path)

    sha = hashlib.sha256(glb_bytes).hexdigest()
    return {
        "glb_path": glb_path, "glb_sha256": sha,
        "step_path": step_path, "stl_path": stl_path,
        "glb_bytes": glb_bytes,
    }


# ---------------------------------------------------------------------------
# Failure taxonomy (handoff section 17: diagnose -> repair -> rebuild)
# ---------------------------------------------------------------------------

def diagnose_failure(exc: Exception, form: str, params: Dict[str, float]) -> Dict[str, Any]:
    text = str(exc)
    if "non-positive" in text or "wall containment" in text or "violat" in text:
        return {
            "failure_class": "PARAMETER_OUT_OF_ENVELOPE",
            "diagnosis": text,
            "repair": "clamp parameters to declared envelopes and rebuild",
        }
    if "boolean" in text.lower() or "cut" in text.lower() or "union" in text.lower():
        return {
            "failure_class": "BOOLEAN_OPERATION_FAILURE",
            "diagnosis": text,
            "repair": "retry with tolerance-relaxed boolean order; record attempt",
        }
    return {
        "failure_class": "GEOMETRY_BUILD_FAILURE",
        "diagnosis": text or exc.__class__.__name__,
        "repair": "fall back to conservative default form parameters",
    }


def attempt_repair(params: Dict[str, float], failure: Dict[str, Any],
                   envelopes: Dict[str, Any]) -> Dict[str, float]:
    """Repair pass 1: clamp every parameter into its declared envelope."""
    repaired = dict(params)
    for key, value in repaired.items():
        env = (envelopes or {}).get(key)
        if env and len(env) == 2:
            lo, hi = float(env[0]), float(env[1])
            repaired[key] = min(max(value, lo), hi)
    return repaired
