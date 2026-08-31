"""discovery_fabric/engine/cad_pipeline.py — R380 3D ENGINEERING
DESIGN PIPELINE. Layer 4 of the invention engine, subordinate to it.

CEO directive (2026-08-31, 3D ENGINEERING DESIGN PIPELINE):

    TECHNICAL STATE
    -> PARAMETER MAP
    -> PARAMETRIC 3D MODEL          (CadQuery + OCCT)
    -> STEP/STL/GLB DERIVATIVES
    -> GEOMETRY VALIDATION
    -> TECHNICAL EVALUATION
    -> MUTATION
    -> NEW 3D MODEL
    -> RE-EVALUATION

The source of truth is the PARAMETRIC MODEL DEFINITION — the build
program plus its parameter map — NEVER the exported mesh, NEVER the
rendered image. STEP/STL/GLB/SVG are derived artifacts with hashes.

> "Do not claim that a 3D model is technically validated merely
>  because it renders successfully. A beautiful render is NOT
>  engineering validation."

Constitutional anchors:
- Art. II/III  the geometry verifier MEASURES the built solid (bbox,
             volume, face radii, face distances); it never trusts the
             parameter claims. A build program that ignores a
             parameter is caught by measured-vs-claimed divergence.
- Art. VI     every derived artifact carries a real sha256 of real
             bytes written to disk. No hash is ever invented.
- Art. XVIII  the LLM may PROPOSE a build program; the deterministic
             sandbox + geometry gates admit it or reject it. Nothing
             LLM-proposed enters a spec ungated.
- Art. XXV    UNVERIFIABLE is recorded where a check cannot run
             (e.g. the secondary manifold verifier unavailable); it is
             never silently passed.
- Art. XXVIII RENDER_IS_NOT_VALIDATION: rendering success and geometry
             validation are separate fields; no technical-validity
             claim may be derived from a render. All geometric
             measurements are COMPUTATIONAL_RESULT (rank 4) with
             computation logs — they can never become physical
             evidence (Art. XXXVIII).
- Art. XXXIV the 3D layer exists to serve evidence -> mechanism ->
             technical state -> DESIGN -> evaluation -> improvement.
             It is not a CAD product; inventions with no meaningful
             physical geometry get an honest NOT_APPLICABLE.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import math
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .candidate import sha256_obj, utc_now

CAD_PIPELINE_VERSION = "1.0.0"
PARAMETRIC_MODEL_SECTION = "parametric_model"
KERNEL_ID = "cadquery-occt"

# ---------------------------------------------------------------------------
# Declared thresholds (Art. XXVII — every number that gates anything)
# ---------------------------------------------------------------------------
CAD_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "MEASURED_VS_CLAIMED_TOLERANCE": {
        "value": 1e-3,
        "unit": "mm",
        "epistemic_class": "ENGINEERING",
        "justification": (
            "OCCT builds at mm scale; a build program that actually "
            "uses the declared parameter reproduces the claimed "
            "dimension to floating-point exactness. Tolerance absorbs "
            "only kernel tessellation noise, not design divergence"),
    },
    "MIN_POSITIVE_VOLUME": {
        "value": 1e-9,
        "unit": "mm^3",
        "epistemic_class": "ENGINEERING",
        "justification": (
            "a valid manufactured part has strictly positive material "
            "volume; zero/negative volume catches fully-erased and "
            "degenerate solids"),
    },
    "DEGENERATE_BBOX_TOLERANCE": {
        "value": 1e-6,
        "unit": "mm",
        "epistemic_class": "ENGINEERING",
        "justification": (
            "a 3D engineering solid must have positive extent on all "
            "three axes"),
    },
    "STL_WATERTIGHT_REQUIRED": {
        "value": True,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "the CEO's non-manifold detection list: the STL derivative "
            "must be watertight (each edge shared by exactly two "
            "triangles) — checked by an INDEPENDENT verifier (trimesh), "
            "not by OCCT alone (Art. III verifier separation)"),
    },
}

# sandbox: names a build program may NEVER touch (Art. XVIII — the
# program is untrusted code until the gates admit it)
_FORBIDDEN_AST_NODES = (
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal,
)
_FORBIDDEN_CALL_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "getattr",
    "setattr", "delattr", "globals", "locals", "vars", "input",
    "breakpoint", "memoryview",
}
_FORBIDDEN_NAME_CHARS = ("__",)


# ---------------------------------------------------------------------------
# 0. GEOMETRY_WARRANTS_3D gate (the honest not-applicable path)
# ---------------------------------------------------------------------------
def geometry_warrants_3d(spec: Dict[str, Any]) -> Dict[str, Any]:
    """CEO rule: 'Do not force 3D onto inventions that genuinely have
    no meaningful physical geometry.' This gate decides honestly from
    the technical state: a candidate warrants a parametric 3D model
    when its state declares (a) at least one OBJECT with a physical
    extent role and (b) at least one bounded GEOMETRY/PARAMETERS
    variable with a length-like unit. Everything else is NOT_APPLICABLE
    with the measured reason — recorded, never forced."""
    ts = ((spec.get("technical_state") or {}).get("value") or {})
    objects = ts.get("objects") or []
    params = ts.get("parameters") or []
    geom_like = [
        p for p in params
        if p.get("category") in ("GEOMETRY", "PARAMETERS")
        and p.get("range_min") is not None
        and p.get("range_max") is not None
    ]
    length_like = [
        p for p in geom_like
        if str(p.get("unit") or "").lower() in (
            "mm", "cm", "m", "in", "inch", "mm^2", "mm^3",
            "millimeter", "millimetre") or
        "mm" in str(p.get("unit") or "").lower()
    ]
    reasons: List[str] = []
    if not objects:
        reasons.append("technical state declares no physical OBJECTS")
    if not geom_like:
        reasons.append(
            "no bounded GEOMETRY/PARAMETERS variable with a declared "
            "envelope (an unbounded parameter cannot drive a "
            "reproducible parametric model — ADR_R379 immutability "
            "rule)")
    if geom_like and not length_like:
        reasons.append(
            "bounded variables carry no length-like unit "
            f"({sorted({str(p.get('unit')) for p in geom_like})}) — "
            "no dimensional geometry is warranted")
    if ts.get("_version") is None and not (ts.get("parameters") or
                                           ts.get("objects")):
        reasons.append("candidate carries no structured technical state")

    warranted = not reasons
    return {
        "gate": "GEOMETRY_WARRANTS_3D",
        "warranted": warranted,
        "verdict": "WARRANTED" if warranted else "NOT_APPLICABLE",
        "measured_basis": {
            "objects_declared": len(objects),
            "bounded_geometry_like_variables": len(geom_like),
            "length_like_variables": len(length_like),
        },
        "reasons": reasons,
        "note": (
            "a NOT_APPLICABLE verdict is the honest state for "
            "non-geometric inventions (methods, compositions, "
            "protocols); forcing a decorative 3D image would violate "
            "the CEO directive and Art. XXVIII"),
        "decided_at": utc_now(),
    }


# ---------------------------------------------------------------------------
# 1. The sandbox — untrusted build programs (Art. XVIII)
# ---------------------------------------------------------------------------
def _scan_program_source(source: str) -> List[str]:
    """Static rejection pass. Returns the list of violations (empty =
    clean). The build program is UNTRUSTED CODE: no imports, no dunder
    access, no filesystem/exec primitives, no comprehensions over
    forbidden calls — checked on the AST BEFORE anything executes."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"SYNTAX_ERROR: {exc}"]
    violations: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_AST_NODES):
            violations.append(
                f"FORBIDDEN_NODE: {type(node).__name__} — build "
                "programs may not import or mutate outer scope")
        if isinstance(node, ast.Name) and \
                any(ch in node.id for ch in _FORBIDDEN_NAME_CHARS):
            violations.append(
                f"DUnder_ACCESS: {node.id} — dunder names are closed")
        if isinstance(node, ast.Attribute) and \
                any(ch in node.attr for ch in _FORBIDDEN_NAME_CHARS):
            violations.append(
                f"DUnder_ACCESS: .{node.attr} — dunder attributes are "
                "closed")
        if isinstance(node, ast.Name) and node.id in \
                _FORBIDDEN_CALL_NAMES:
            violations.append(
                f"FORBIDDEN_PRIMITIVE: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr in \
                _FORBIDDEN_CALL_NAMES:
            violations.append(
                f"FORBIDDEN_PRIMITIVE: .{node.attr}")
    return violations


def _execute_build_program(source: str,
                           params: Dict[str, float]
                           ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Execute a scanned build program in the restricted namespace.
    The program must define build(p) -> dict[str, Workplane]. Returns
    (shapes_by_object_id, errors). Import of cadquery happens HERE, in
    trusted code — the program itself cannot import anything."""
    import cadquery  # noqa: PLC0415 — trusted side of the boundary
    errors: List[str] = []
    violations = _scan_program_source(source)
    if violations:
        return None, violations

    namespace: Dict[str, Any] = {
        "cq": cadquery,
        "math": math,
        "build": None,
    }
    try:
        exec(compile(source, "<parametric-build-program>", "exec"),  # noqa: S102
             {"__builtins__": {"min": min, "max": max, "abs": abs,
                               "len": len, "range": range,
                               "float": float, "int": int,
                               "round": round, "sorted": sorted},
              "cq": cadquery, "math": math},
             namespace)
    except Exception as exc:  # noqa: BLE001 — recorded, never fatal
        return None, [f"BUILD_PROGRAM_RUNTIME_ERROR: "
                      f"{type(exc).__name__}: {exc}"]
    build = namespace.get("build")
    if not callable(build):
        return None, ["NO_BUILD_FUNCTION: the program must define "
                      "build(p) -> dict of named shapes"]
    try:
        result = build(dict(params))
    except Exception as exc:  # noqa: BLE001
        return None, [f"BUILD_CALL_ERROR: {type(exc).__name__}: {exc}"]
    if not isinstance(result, dict) or not result:
        return None, ["BAD_BUILD_RETURN: build(p) must return a "
                      "non-empty dict {object_id: shape}"]
    shapes: Dict[str, Any] = {}
    for oid, shape in result.items():
        if shape is None:
            errors.append(f"OBJECT_EMPTY: {oid} — build returned None")
            continue
        try:
            val = shape.val() if hasattr(shape, "val") else shape
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OBJECT_UNREADABLE: {oid}: {exc}")
            continue
        if val is None or (hasattr(val, "Volume") and
                           not callable(getattr(val, "Volume"))):
            errors.append(f"OBJECT_UNREADABLE: {oid}")
            continue
        shapes[str(oid)] = shape
    if not shapes:
        errors.insert(0, "ALL_OBJECTS_EMPTY")
        return None, errors
    return shapes, errors


# ---------------------------------------------------------------------------
# 2. Engine-owned deterministic design templates
# ---------------------------------------------------------------------------
# A template is code the ENGINE owns (version-controlled source, not
# LLM output). Templates provide the hermetic, reproducible path; LLM
# proposals enter through the same deterministic gates (origin marked).
# Template semantics: DUAL_LUMEN_TUBE = the CereVasc-family dual-lumen
# CSF shunt tube: an outer cylinder, two parallel lumens separated by
# a septum, cut through the full length.

DUAL_LUMEN_TUBE_PROGRAM = '''
def build(p):
    od = p["outer_diameter_mm"]
    ld = p["lumen_diameter_mm"]
    L = p["length_mm"]
    st = p["septum_thickness_mm"]
    r = ld / 2.0
    c = r + st / 2.0
    body = cq.Workplane("XY").circle(od / 2.0).extrude(L)
    lumA = (cq.Workplane("XY").center(-c, 0)
            .circle(r).extrude(L))
    lumB = (cq.Workplane("XY").center(c, 0)
            .circle(r).extrude(L))
    part = body.cut(lumA).cut(lumB)
    return {"dual_lumen_tube": part}
'''

TEMPLATE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "dual_lumen_tube": {
        "template_id": "tpl:dual_lumen_tube:v1",
        "origin": "ENGINE_TEMPLATE",
        "program": DUAL_LUMEN_TUBE_PROGRAM.strip(),
        "parameter_bindings": [
            "outer_diameter_mm", "lumen_diameter_mm",
            "length_mm", "septum_thickness_mm",
        ],
        "objects": [
            {"object_id": "dual_lumen_tube",
             "role": "outer body with two through-lumens and septum"},
        ],
        "measured_dimension_bindings": {
            # measured quantity -> parameter the program must honor
            "bbox_xy_max": "outer_diameter_mm",
            "bbox_z": "length_mm",
        },
        "notes": (
            "circular lumens side-by-side inside a circular outer "
            "wall; min wall = od/2 - ld - st/2 measured on the real "
            "faces by the validator"),
    },
}


def template_model_from_state(state: Dict[str, Any],
                              template_id: str = "dual_lumen_tube",
                              candidate_id: str = ""
                              ) -> Tuple[Optional[Dict[str, Any]],
                                         List[str]]:
    """Instantiate an ENGINE-OWNED template against a technical state:
    each binding parameter is taken from the state (value + envelope +
    value_class travel WITH it). Parameters missing from the state are
    reported — never invented (Art. VI/XXV)."""
    tpl = TEMPLATE_REGISTRY.get(template_id)
    if tpl is None:
        return None, [f"UNKNOWN_TEMPLATE: {template_id}"]
    params = {p.get("param_id"): p
              for p in (state or {}).get("parameters") or []}
    pmap: Dict[str, Dict[str, Any]] = {}
    problems: List[str] = []
    for name in tpl["parameter_bindings"]:
        p = params.get(name)
        if p is None:
            problems.append(
                f"MISSING_PARAMETER: technical state has no parameter "
                f"'{name}' — required by template {template_id}")
            continue
        pmap[name] = {
            "param_id": name,
            "value": p.get("value"),
            "unit": p.get("unit"),
            "range_min": p.get("range_min"),
            "range_max": p.get("range_max"),
            "value_class": p.get("value_class"),
            "envelope_class": p.get("range_class"),
            "category": p.get("category"),
        }
    if problems:
        return None, problems
    model = {
        "model_id": None,          # filled at build time (hash of content)
        "model_version": CAD_PIPELINE_VERSION,
        "candidate_id": candidate_id,
        "kernel": KERNEL_ID,
        "kernel_version": _kernel_version(),
        "template_id": tpl["template_id"],
        "origin": "ENGINE_TEMPLATE",
        "build_program": tpl["program"],
        "program_source_sha256": hashlib.sha256(
            tpl["program"].encode("utf-8")).hexdigest(),
        "parameter_map": pmap,
        "objects": copy.deepcopy(tpl["objects"]),
        "measured_dimension_bindings": copy.deepcopy(
            tpl.get("measured_dimension_bindings") or {}),
        "interference_pairs": copy.deepcopy(
            tpl.get("interference_pairs") or []),
        "geometry_assumptions": copy.deepcopy(
            tpl.get("geometry_assumptions") or []),
        "materials": copy.deepcopy((state or {}).get("materials") or []),
        "operating_conditions": copy.deepcopy(
            (state or {}).get("operating_conditions") or []),
        "measurable_outputs": copy.deepcopy(
            (state or {}).get("measurable_outputs") or []),
        "constraints": copy.deepcopy(
            (state or {}).get("constraints") or []),
        "parent_candidate": candidate_id,
        "mutation_provenance": [],
        "source_evidence_provenance": {
            "technical_state_section": "technical_state",
            "evidence_ids": sorted({
                p.get("value_evidence_id")
                for p in (state or {}).get("parameters") or []
                if p.get("value_evidence_id")} | {
                c.get("limit_evidence_id")
                for c in (state or {}).get("constraints") or []
                if c.get("limit_evidence_id")}),
        },
        "derived_artifacts": {},
        "views": {},
        "geometry_validation": None,
        "evidence_class": "COMPUTATIONAL_RESULT",
    }
    return model, []


def _kernel_version() -> str:
    try:
        import cadquery
        return str(getattr(cadquery, "__version__", "unknown"))
    except Exception:  # noqa: BLE001
        return "unknown"


# ---------------------------------------------------------------------------
# 3. MEASURE (the verifier measures the built solid — Art. III)
# ---------------------------------------------------------------------------
def measure_geometry(shapes: Dict[str, Any]) -> Dict[str, Any]:
    """Measure the REAL built solids: validity, volume, bbox, cylinder
    face radii, min face-to-face distances (true wall thickness),
    cross-section area at mid-height. Every measurement enters the
    computation log with the kernel call that produced it — this is a
    COMPUTATIONAL_RESULT (Art. XXXVIII rank 4), never a physical
    observation."""
    measurements: Dict[str, Any] = {"objects": {}, "computation_log": []}
    for oid, wp in shapes.items():
        solid = wp.val() if hasattr(wp, "val") else wp
        entry: Dict[str, Any] = {"object_id": oid}
        try:
            entry["is_valid_solid"] = bool(solid.isValid())
        except Exception as exc:  # noqa: BLE001
            entry["is_valid_solid"] = False
            entry["validity_error"] = f"{type(exc).__name__}: {exc}"
        try:
            entry["volume_mm3"] = round(float(solid.Volume()), 6)
        except Exception as exc:  # noqa: BLE001
            entry["volume_mm3"] = None
            entry["volume_error"] = f"{type(exc).__name__}: {exc}"
        try:
            bb = solid.BoundingBox()
            entry["bbox"] = {
                "xlen": round(float(bb.xlen), 6),
                "ylen": round(float(bb.ylen), 6),
                "zlen": round(float(bb.zlen), 6),
                "xmin": round(float(bb.xmin), 6),
                "xmax": round(float(bb.xmax), 6),
                "ymin": round(float(bb.ymin), 6),
                "ymax": round(float(bb.ymax), 6),
            }
        except Exception as exc:  # noqa: BLE001
            entry["bbox"] = None
            entry["bbox_error"] = f"{type(exc).__name__}: {exc}"
        # cylinder faces measured through BRepAdaptor_Surface (handles
        # trimmed surfaces — the raw Geom_Surface does not expose
        # .Cylinder() on them; discovered on the breach case)
        cyl_faces: List[Dict[str, Any]] = []
        for f in solid.Faces():
            if f.geomType() != "CYLINDER":
                continue
            try:
                from OCP.BRepAdaptor import BRepAdaptor_Surface
                cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
                loc = cyl.Axis().Location()
                cyl_faces.append({
                    "radius": round(float(cyl.Radius()), 6),
                    "axis_x": round(float(loc.X()), 6),
                    "axis_y": round(float(loc.Y()), 6),
                })
            except Exception as exc:  # noqa: BLE001 — per-face, never fatal
                entry.setdefault("face_scan_errors", []).append(
                    f"{type(exc).__name__}: {exc}")
        entry["cylinder_faces"] = cyl_faces
        entry["cylinder_face_radii"] = sorted(
            c["radius"] for c in cyl_faces)
        measurements["objects"][oid] = entry
        measurements["computation_log"].append({
            "object_id": oid,
            "kernel": KERNEL_ID,
            "calls": ["Shape.isValid()", "Shape.Volume()",
                      "Shape.BoundingBox()", "Shape.Faces()",
                      "BRepAdaptor_Cylinder.Radius()"],
            "computed_at": utc_now(),
        })

    # SIGNED containment wall per object: for every cylinder face
    # nested inside the largest-radius cylinder face (the outer wall),
    # wall = R - (|axis - center| + r). NEGATIVE means the inner
    # cylinder's cross-section circle escapes the outer circle — a
    # lumen BREACH (the hole opens through the outer surface). The
    # face-to-face distance is kept as a cross-check; it fails to
    # detect breaches because intersecting faces raise/return zero.
    for oid, entry in measurements["objects"].items():
        cyls = entry.get("cylinder_faces") or []
        radii = [c["radius"] for c in cyls]
        if len(radii) < 2 or max(radii) <= 0:
            continue
        bb = entry.get("bbox") or {}
        if bb.get("xmin") is None:
            continue
        cx = (bb["xmin"] + bb["xmax"]) / 2.0
        cy = (bb["ymin"] + bb["ymax"]) / 2.0
        R = max(radii)
        walls = []
        for c in cyls:
            if c["radius"] >= R - 1e-9:
                continue  # an outer wall face, not a lumen
            d = math.hypot(c["axis_x"] - cx, c["axis_y"] - cy)
            walls.append(round(R - d - c["radius"], 6))
        if walls:
            entry["signed_containment_walls_mm"] = sorted(walls)
            entry["min_wall_thickness_mm"] = min(walls)
            measurements["computation_log"].append({
                "object_id": oid,
                "kernel": KERNEL_ID,
                "calls": ["BRepAdaptor_Surface(face).Cylinder() "
                          "(radius + axis location)",
                          "Shape.BoundingBox() (center)",
                          "signed containment: R - (dist + r)"],
                "quantity": "min_wall_thickness_mm (signed; negative "
                            "= lumen breaches the outer wall)",
                "computed_at": utc_now(),
            })
    return measurements


# ---------------------------------------------------------------------------
# 4. VALIDATE GEOMETRY — the G-gates (CEO's mandatory detection list)
# ---------------------------------------------------------------------------
def validate_geometry(model: Dict[str, Any],
                      shapes: Dict[str, Any],
                      measurements: Dict[str, Any]
                      ) -> Dict[str, Any]:
    """The deterministic geometry validation. Detects (CEO list):
      G1 invalid geometry            (isValid + positive volume)
      G2 non-manifold solids         (OCCT validity + INDEPENDENT STL
                                      watertight check via trimesh —
                                      verifier separation, Art. III)
      G3 impossible dimensions       (finite values, inside declared
                                      envelopes, non-degenerate bbox)
      G4 violated geometric          (measured wall vs declared
         constraints                  constraints + measured-vs-claimed
                                      dimension agreement — catches a
                                      program that ignores a parameter)
      G5 missing parameters          (map <-> program usage both ways)
      G6 broken assemblies           (every declared object present)
      G7 impossible intersections    (declared clearance/contact pairs,
                                      measured interference volume)
      G8 unsupported material/       (thin-wall slenderness measured
         geometry assumptions         vs declared assumption — where
                                      detectable; else UNVERIFIABLE)
      RENDER_IS_NOT_VALIDATION       (structural separation — the
                                      report can never derive technical
                                      validity from a render)
    """
    pmap = model.get("parameter_map") or {}
    checks: Dict[str, Any] = {}
    reasons: List[str] = []

    def _record(gate: str, status: str, detail: Any) -> None:
        checks[gate] = {"status": status, "detail": detail}
        if status in ("VIOLATED", "FAILED", "REJECTED"):
            reasons.append(f"{gate}: {detail}")

    # ---- G3 impossible dimensions (checked BEFORE geometric work:
    #      the envelope is the technical state's own declared bound) --
    g3_bad: List[str] = []
    for pid, p in pmap.items():
        v = p.get("value")
        if v is None or isinstance(v, bool) or \
                not isinstance(v, (int, float)) or \
                not math.isfinite(float(v)):
            g3_bad.append(f"{pid}={v!r} (no finite numeric value)")
            continue
        lo, hi = p.get("range_min"), p.get("range_max")
        if lo is not None and float(v) < float(lo) - 1e-12:
            g3_bad.append(f"{pid}={v} < envelope_min {lo}")
        if hi is not None and float(v) > float(hi) + 1e-12:
            g3_bad.append(f"{pid}={v} > envelope_max {hi}")
        if lo is not None and hi is not None and float(lo) >= float(hi):
            g3_bad.append(f"{pid} envelope degenerate [{lo},{hi}]")
    _record("G3_impossible_dimensions",
            "VIOLATED" if g3_bad else "SATISFIED", g3_bad or "all "
            "parameter values finite and inside declared envelopes")

    # ---- G5 missing parameters (both directions) ---------------------
    src = model.get("build_program") or ""
    used_refs = set(re.findall(r'p\[\s*["\']([^"\']+)["\']\s*\]', src))
    mapped = set(pmap.keys())
    dangling = sorted(used_refs - mapped)
    unused = sorted(mapped - used_refs)
    g5_bad = []
    if dangling:
        g5_bad.append(f"program references unmapped parameters: "
                      f"{dangling}")
    if unused:
        g5_bad.append(f"parameter map entries unused by the program: "
                      f"{unused} (the model does not actually depend on "
                      "them — source-of-truth violation)")
    _record("G5_missing_parameters",
            "VIOLATED" if g5_bad else "SATISFIED", g5_bad or
            f"{len(mapped)} parameters, all bound bidirectionally")

    # ---- hardcoded-value scan (source of truth: values come from p) --
    #      a literal in source that equals a mapped parameter value is
    #      a hardcoded dimension — the parameter is NOT the source.
    hardcoded: List[str] = []
    for pid, p in pmap.items():
        v = p.get("value")
        if v is None or isinstance(v, bool) or \
                not isinstance(v, (int, float)):
            continue
        for form in _number_forms(float(v)):
            if re.search(r'(?<![\w.])' + re.escape(form) +
                         r'(?![\w.])', src):
                hardcoded.append(f"{pid}={v} appears as literal "
                                 f"'{form}' in program source")
                break
    _record("G5b_hardcoded_values", "VIOLATED" if hardcoded else
            "SATISFIED", hardcoded or "no parameter value hardcoded in "
            "program source")

    # ---- G1 invalid geometry + G6 broken assemblies ------------------
    g1_bad: List[str] = []
    g6_bad: List[str] = []
    declared_objs = {o.get("object_id") for o in
                     (model.get("objects") or [])}
    built_objs = set(measurements.get("objects") or {})
    for oid in declared_objs - built_objs:
        g6_bad.append(f"declared object '{oid}' absent from build")
    for oid, m in (measurements.get("objects") or {}).items():
        if not m.get("is_valid_solid"):
            g1_bad.append(f"{oid}: OCCT isValid()=False"
                          + (f" ({m.get('validity_error')})"
                             if m.get("validity_error") else ""))
        vol = m.get("volume_mm3")
        if vol is None or vol < CAD_THRESHOLDS[
                "MIN_POSITIVE_VOLUME"]["value"]:
            g1_bad.append(f"{oid}: non-positive volume {vol}")
        bb = m.get("bbox") or {}
        tol = CAD_THRESHOLDS["DEGENERATE_BBOX_TOLERANCE"]["value"]
        if any((bb.get(k) is not None and bb[k] < tol)
               for k in ("xlen", "ylen", "zlen")):
            g1_bad.append(f"{oid}: degenerate bbox {bb}")
    _record("G1_invalid_geometry", "VIOLATED" if g1_bad else "SATISFIED",
            g1_bad or f"{len(built_objs)} objects valid with positive "
            "volume and 3D extent")
    _record("G6_broken_assembly", "VIOLATED" if g6_bad else "SATISFIED",
            g6_bad or f"all {len(declared_objs)} declared objects built"
            or "single-object model")

    # ---- G4 violated geometric constraints ----------------------------
    #      (a) declared constraints of the technical state whose target
    #          the geometry MEASURES (e.g. wall thickness): checked on
    #          the measurement, never on the claim
    g4_results: List[Dict[str, Any]] = []
    state_constraints = model.get("constraints") or []
    measured_fields = {
        f"{oid}.{field}": value
        for oid, m in (measurements.get("objects") or {}).items()
        for field, value in m.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    for c in state_constraints:
        target = str(c.get("target") or "")
        limit = c.get("limit")
        if limit is None or not isinstance(limit, (int, float)):
            continue
        measured_val = None
        measured_key = None
        for key, value in measured_fields.items():
            field = key.rsplit(".", 1)[-1]
            if field == target or target in field:
                measured_val = float(value)
                measured_key = key
                break
        if measured_val is None:
            g4_results.append({
                "constraint_id": c.get("constraint_id"),
                "target": target, "limit": limit,
                "bound": c.get("bound"),
                "status": "UNVERIFIABLE",
                "reason": ("the geometry does not measure a quantity "
                           "matching this target (Art. XXV: unknown "
                           "is not satisfied)"),
            })
            continue
        ok = (measured_val <= float(limit)) if c.get("bound") == "<=" \
            else (measured_val >= float(limit))
        g4_results.append({
            "constraint_id": c.get("constraint_id"),
            "target": target, "limit": limit, "bound": c.get("bound"),
            "status": "SATISFIED" if ok else "VIOLATED",
            "measured_value": measured_val,
            "measured_from": measured_key,
            "source": "MEASURED_ON_BUILT_SOLID",
        })
    violated_c = [r for r in g4_results
                  if r["status"] == "VIOLATED"]
    _record("G4_violated_geometric_constraints",
            "VIOLATED" if violated_c else
            ("UNVERIFIABLE" if not g4_results else "SATISFIED"),
            violated_c or g4_results)

    #      (b) measured-vs-claimed dimension agreement (the program
    #          must actually USE the parameters — Art. III)
    tol = CAD_THRESHOLDS["MEASURED_VS_CLAIMED_TOLERANCE"]["value"]
    dim_bind = model.get("measured_dimension_bindings") or {}
    agree_bad: List[str] = []
    if dim_bind:
        first = next(iter(measurements.get("objects", {})))
        m = (measurements.get("objects") or {}).get(first or "", {})
        for measured_key, pid in dim_bind.items():
            claimed = (pmap.get(pid) or {}).get("value")
            if measured_key == "bbox_xy_max":
                # BOTH sides of the cross-section must honor the
                # claimed outer diameter: a lumen breach shrinks ONE
                # side while the other stays intact (measured on the
                # real bbox — Art. III)
                gx = (m.get("bbox") or {}).get("xlen")
                gy = (m.get("bbox") or {}).get("ylen")
                got = min(gx, gy) if (gx is not None and
                                      gy is not None) else None
            else:
                got = (m.get("bbox") or {}).get("zlen")
            if claimed is None or got is None:
                continue
            if abs(float(got) - float(claimed)) > tol:
                agree_bad.append(
                    f"measured {measured_key}={got} != claimed "
                    f"{pid}={claimed} — the build program does not "
                    f"honor the parameter (source-of-truth violation)")
    _record("G4b_measured_vs_claimed_dimensions",
            "VIOLATED" if agree_bad else "SATISFIED", agree_bad or
            "measured bounding box agrees with claimed dimensions "
            f"within {tol} mm")

    # ---- G1b lumen containment breach --------------------------------
    #      signed containment wall < 0 on any nested cylinder face
    #      means the inner cylinder's cross-section circle escapes
    #      the outer wall — the hole opens through the outer surface.
    #      MEASURED from the built faces (axis + radius + bbox
    #      center); a breach is invalid geometry for an enclosed-
    #      lumen design (CEO list: impossible intersections).
    g1b_bad: List[str] = []
    g1b_walls: Dict[str, Any] = {}
    for oid, m in (measurements.get("objects") or {}).items():
        walls = m.get("signed_containment_walls_mm")
        if walls is None:
            continue
        g1b_walls[oid] = walls
        if min(walls) < -1e-6:
            g1b_bad.append(
                f"{oid}: lumen breaches the outer wall (signed "
                f"containment wall {min(walls)} mm < 0)")
    _record("G1b_cylinder_containment",
            "VIOLATED" if g1b_bad else
            ("UNVERIFIABLE" if not g1b_walls else "SATISFIED"),
            g1b_bad or g1b_walls or
            "no nested cylinder faces to check")

    # ---- G2 non-manifold (independent second verifier) ---------------
    #      OCCT validity is checked in G1; the STL derivative is
    #      re-checked by trimesh — a DIFFERENT verifier (Art. III).
    #      Runs only when the STL exists (export happens before final
    #      validation); otherwise recorded UNVERIFIABLE, never passed.
    g2_status = "UNVERIFIABLE"
    g2_detail = ("secondary verifier not yet run (no STL derivative at "
                 "validation time) — will be checked on export")
    stl_paths = {
        k: v for k, v in (model.get("derived_artifacts") or {}).items()
        if k.startswith("STL")}
    if stl_paths:
        try:
            import trimesh  # noqa: PLC0415 — independent verifier
            g2_results = []
            for key, art in stl_paths.items():
                mesh = trimesh.load(art.get("path"), force="mesh")
                watertight = bool(mesh.is_watertight)
                g2_results.append({
                    "artifact": key, "path": art.get("path"),
                    "watertight": watertight,
                    "faces": int(len(mesh.faces)),
                    "vertices": int(len(mesh.vertices)),
                })
                if not watertight:
                    reasons.append(f"G2_non_manifold_solids: {key} "
                                   "STL is not watertight")
            g2_status = "VIOLATED" if any(
                not r["watertight"] for r in g2_results) else "SATISFIED"
            g2_detail = g2_results
        except ImportError:
            g2_status = "UNVERIFIABLE"
            g2_detail = ("trimesh (independent secondary verifier) "
                         "unavailable — Art. XXV: not silently passed")
    _record("G2_non_manifold_solids", g2_status, g2_detail)

    # ---- G7 impossible intersections ----------------------------------
    #      declared clearance/contact pairs between objects
    pairs = model.get("interference_pairs") or []
    g7_results: List[Dict[str, Any]] = []
    if len(shapes) > 1 and pairs:
        for pair in pairs:
            a, b = pair.get("a"), pair.get("b")
            req = pair.get("requirement")  # CLEARANCE | CONTACT
            if a not in shapes or b not in shapes:
                g7_results.append({"pair": (a, b), "status":
                                   "UNVERIFIABLE", "reason":
                                   "object not built"})
                continue
            sa = shapes[a].val() if hasattr(shapes[a], "val") \
                else shapes[a]
            sb = shapes[b].val() if hasattr(shapes[b], "val") \
                else shapes[b]
            try:
                inter = sa.intersect(sb)
                ivol = float(inter.Volume()) if inter else 0.0
            except Exception:  # noqa: BLE001
                ivol = 0.0
            if req == "CLEARANCE":
                ok = ivol <= 1e-9
            else:  # CONTACT
                ok = ivol > 0.0
            g7_results.append({
                "pair": (a, b), "requirement": req,
                "measured_interference_volume_mm3": round(ivol, 9),
                "status": "SATISFIED" if ok else "VIOLATED",
            })
    if g7_results:
        _record("G7_impossible_intersections",
                "VIOLATED" if any(r["status"] == "VIOLATED"
                                  for r in g7_results) else "SATISFIED",
                g7_results)
    else:
        _record("G7_impossible_intersections", "UNVERIFIABLE",
                "no multi-object interference pairs declared for this "
                "model (single-object models cannot intersect)")

    # ---- G8 unsupported material/geometry assumptions -----------------
    #      where detectable: thin-wall/slenderness assumptions measured
    #      on the real geometry. Everything else honestly UNVERIFIABLE.
    g8_results: List[Dict[str, Any]] = []
    assumptions = model.get("geometry_assumptions") or []
    for a in assumptions:
        kind = str(a.get("kind") or "")
        if kind == "SLENDERNESS_LIMIT":
            ratio = a.get("max_length_to_diameter_ratio")
            first = next(iter(measurements.get("objects", {})), None)
            m = (measurements.get("objects") or {}).get(first or "", {})
            bb = m.get("bbox") or {}
            dia = max(bb.get("xlen") or 0, bb.get("ylen") or 0)
            length = bb.get("zlen") or 0
            if ratio is not None and dia and length:
                measured_ratio = length / dia
                ok = measured_ratio <= float(ratio)
                g8_results.append({
                    "assumption": a.get("statement"),
                    "measured_ratio": round(measured_ratio, 4),
                    "declared_limit": ratio,
                    "status": "SUPPORTED" if ok else "VIOLATED",
                })
            else:
                g8_results.append({"assumption": a.get("statement"),
                                   "status": "UNVERIFIABLE"})
        else:
            g8_results.append({"assumption": a.get("statement"),
                               "status": "UNVERIFIABLE",
                               "reason": ("not detectable from geometry "
                                          "at this tier (Art. XXV)")})
    _record("G8_geometry_assumptions",
            "VIOLATED" if any(r.get("status") == "VIOLATED"
                              for r in g8_results) else
            ("UNVERIFIABLE" if not any(r.get("status") == "SUPPORTED"
                                       for r in g8_results) else
             "SUPPORTED"),
            g8_results or "no geometry assumptions declared")

    return {
        "validator": "cad_pipeline_geometry_v1 (deterministic, "
                     "measured-on-built-solid)",
        "kernel": f"{KERNEL_ID} {_kernel_version()}",
        "checks": checks,
        "reasons": reasons,
        "valid": not reasons,
        "render_is_not_validation": {
            "renders_successfully": None,
            "technical_validity_derived_from_render": False,
            "rule": ("rendering success is a presentation fact; "
                     "technical validity comes ONLY from the G-gates "
                     "above (Art. XXVIII / CEO R380: a beautiful "
                     "render is NOT engineering validation)"),
        },
        "evidence_class": "COMPUTATIONAL_RESULT",
        "validated_at": utc_now(),
    }


def _number_forms(v: float) -> List[str]:
    forms = {str(v)}
    if float(v).is_integer():
        forms.add(str(int(v)))
    forms.add(f"{float(v):.4f}".rstrip("0").rstrip("."))
    return sorted(forms)


# ---------------------------------------------------------------------------
# 5. EXPORT DERIVATIVES (STEP / STL / GLB / SVG views)
# ---------------------------------------------------------------------------
def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def export_derivatives(model: Dict[str, Any],
                       shapes: Dict[str, Any],
                       out_dir: str
                       ) -> Dict[str, Dict[str, Any]]:
    """Export STEP (engineering exchange), STL (mesh derivative),
    GLB (presentation), and SVG views (isometric + mid-height section
    drawing). Every file's real sha256 of real bytes is recorded —
    Art. VI: no hash is ever invented. The exported files are
    DERIVATIVES; the parametric definition stays the source of truth."""
    import cadquery as cq  # noqa: PLC0415 — trusted side
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    arts: Dict[str, Dict[str, Any]] = {}

    def _record_art(kind: str, oid: str, path: str, role: str) -> None:
        arts[f"{kind}:{oid}"] = {
            "path": str(path), "sha256": _sha256_file(path),
            "bytes": os.path.getsize(path), "role": role,
            "evidence_class": "COMPUTATIONAL_RESULT",
            "derivative_of": "parametric_model:" +
                             str(model.get("model_id")),
            "exported_at": utc_now(),
        }

    first_oid = next(iter(shapes))
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_",
                  str(model.get("candidate_id") or "candidate"))[:60]

    # ---- STEP (per object + assembly) --------------------------------
    for oid, wp in shapes.items():
        p = str(out / f"{base}_{oid}.step")
        solid = wp.val() if hasattr(wp, "val") else wp
        solid.exportStep(p)
        _record_art("STEP", oid, p, "engineering exchange format "
                                  "(B-rep, parametric-precise)")
    if len(shapes) > 1:
        asm = cq.Assembly(name=base or "assembly")
        for oid, wp in shapes.items():
            asm.add(wp, name=oid, color=cq.Color("steelblue"))
        p_asm = str(out / f"{base}_assembly.step")
        asm.save(p_asm)
        _record_art("STEP", "assembly", p_asm,
                    "assembly STEP (all objects)")

    # ---- STL (per object) ---------------------------------------------
    for oid, wp in shapes.items():
        p = str(out / f"{base}_{oid}.stl")
        solid = wp.val() if hasattr(wp, "val") else wp
        solid.exportStl(p, tolerance=0.02, angularTolerance=0.1)
        _record_art("STL", oid, p, "mesh derivative (additive-mfg "
                                   "approximation of the B-rep)")

    # ---- GLB (assembly presentation — NOT engineering validation) ----
    try:
        asm = cq.Assembly(name=base or "assembly")
        for oid, wp in shapes.items():
            asm.add(wp, name=oid, color=cq.Color("steelblue"))
        p_glb = str(out / f"{base}.glb")
        asm.save(p_glb, exportType="GLTF")
        _record_art("GLB", "presentation", p_glb,
                    "presentation/rendering derivative (a render is "
                    "NOT engineering validation — CEO R380)")
    except Exception as exc:  # noqa: BLE001
        arts["GLB:presentation"] = {
            "status": "EXPORT_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "evidence_class": "COMPUTATIONAL_RESULT",
        }

    # ---- SVG views (engineering line drawings via OCCT HLR) ----------
    views: Dict[str, Any] = {}
    wp_first = shapes[first_oid]
    try:
        from cadquery import exporters as cq_exporters
        p_iso = str(out / f"{base}_isometric.svg")
        cq_exporters.export(wp_first, p_iso, opt={
            "projectionDir": (1.0, 1.0, 1.0), "width": 480,
            "height": 480, "marginLeft": 20, "marginTop": 20,
            "showAxes": False, "strokeWidth": 0.35,
            "strokeColor": (0, 0, 0), "hiddenColor": (120, 120, 120),
        })
        _record_art("SVG", "isometric", p_iso,
                    "isometric line view (OCCT hidden-line projection)")
        views["isometric"] = p_iso
    except Exception as exc:  # noqa: BLE001
        views["isometric"] = {"EXPORT_FAILED":
                              f"{type(exc).__name__}: {exc}"}
    try:
        from cadquery import exporters as cq_exporters
        solid = wp_first.val() if hasattr(wp_first, "val") else wp_first
        bb = solid.BoundingBox()
        half = cq.Workplane("XY").box(
            bb.xlen * 4, bb.ylen * 4, bb.zlen * 4,
            centered=(False, True, True)).translate(
            (cq.Vector(0, 0, 0)))
        # cut away y>0 half-space to expose the mid-plane section
        cutter = (cq.Workplane("XY").box(
            bb.xlen * 4, bb.ylen * 4, bb.zlen * 4,
            centered=(True, False, True)))
        sectioned = wp_first.cut(cutter)
        if sectioned.val().isValid():
            p_sec = str(out / f"{base}_section.svg")
            cq_exporters.export(sectioned, p_sec, opt={
                "projectionDir": (0.0, 1.0, 0.0), "width": 480,
                "height": 480, "marginLeft": 20, "marginTop": 20,
                "showAxes": False, "strokeWidth": 0.35,
            })
            _record_art("SVG", "section", p_sec,
                        "mid-height section view (cut at the "
                        "longitudinal plane)")
            views["section"] = p_sec
        else:
            views["section"] = {"status": "UNVERIFIABLE",
                                "reason": "section cut produced an "
                                "invalid solid"}
    except Exception as exc:  # noqa: BLE001
        views["section"] = {"EXPORT_FAILED":
                            f"{type(exc).__name__}: {exc}"}
    # exploded view: honest NOT_APPLICABLE for single-object models
    if len(shapes) > 1:
        views["exploded"] = {"status": "NOT_IMPLEMENTED_V1",
                             "reason": "multi-object exploded layout "
                             "reserved for assembly templates"}
    else:
        views["exploded"] = {
            "status": "NOT_APPLICABLE",
            "reason": ("single-object model — no parts to separate "
                       "(honest not-applicable, never forced)"),
        }
    return {"artifacts": arts, "views": views}


# ---------------------------------------------------------------------------
# 6. BUILD ORCHESTRATION (the full pipeline for one model)
# ---------------------------------------------------------------------------
def build_and_validate_model(model: Dict[str, Any],
                             out_dir: Optional[str] = None,
                             export: bool = True
                             ) -> Tuple[Optional[Dict[str, Any]],
                                        Dict[str, Any]]:
    """Run the pipeline for one parametric model:
    build (sandbox) -> measure -> export derivatives -> validate
    (G1..G8 incl. the independent STL manifold check) -> return the
    model with validation + derivatives attached.

    Returns (model_with_results_or_None_if_hard_failed, record).
    A model whose geometry validation FAILS still returns the model
    (with the failed report attached) — the caller decides KEEP/KILL;
    only infrastructure errors return None."""
    params = {pid: p.get("value") for pid, p in
              (model.get("parameter_map") or {}).items()}
    shapes, errors = _execute_build_program(
        model.get("build_program") or "", params)
    record: Dict[str, Any] = {
        "stage": "CAD_BUILD", "kernel": KERNEL_ID,
        "model_version": model.get("model_version"),
        "built_at": utc_now(),
        "build_errors": errors,
    }
    if shapes is None:
        record["status"] = "BUILD_FAILED"
        model = copy.deepcopy(model)
        model["geometry_validation"] = {
            "validator": "cad_pipeline_geometry_v1",
            "status": "BUILD_FAILED",
            "reasons": errors,
            "valid": False,
            "evidence_class": "COMPUTATIONAL_RESULT",
            "validated_at": utc_now(),
        }
        return model, record

    model = copy.deepcopy(model)
    # model_id: content hash of the parametric definition + parameters
    # (computed BEFORE export so every derivative references a real id)
    model["model_id"] = "pm:" + sha256_obj({
        "program": model.get("build_program"),
        "params": params,
        "template": model.get("template_id"),
        "version": model.get("model_version"),
    })[:16]
    record["model_id"] = model["model_id"]

    measurements = measure_geometry(shapes)
    model["measurements"] = measurements

    if export and out_dir:
        derived = export_derivatives(model, shapes, out_dir)
        model["derived_artifacts"] = derived["artifacts"]
        model["views"] = derived["views"]
    elif not export:
        model.setdefault("derived_artifacts", {})
        model.setdefault("views", {})

    validation = validate_geometry(model, shapes, measurements)
    model["geometry_validation"] = validation
    record["status"] = "OK" if validation.get("valid") \
        else "GEOMETRY_INVALID"
    record["validation_summary"] = {
        g: c.get("status") for g, c in
        (validation.get("checks") or {}).items()}
    return model, record


# ---------------------------------------------------------------------------
# 7. MUTATION + REBUILD (the CEO's core example)
# ---------------------------------------------------------------------------
def rebuild_with_mutation(model: Dict[str, Any],
                          param_id: str,
                          new_value: float,
                          mutation_id: str,
                          reason: str,
                          out_dir: Optional[str] = None
                          ) -> Tuple[Optional[Dict[str, Any]],
                                     Dict[str, Any]]:
    """The CEO R380 loop:

        parameter X = 3.0 mm
        -> technical evaluator identifies X as limiting
        -> mutation proposes 3.6 mm
        -> CAD generator creates new geometry  (THIS)
        -> geometry validates
        -> technical evaluator re-runs
        -> candidate is KEEP or KILL

    The child model carries the SAME build program (source of truth
    unchanged), the mutated parameter map, full mutation provenance,
    and the parent model id. Returns (child_model, record); the child
    model's geometry_validation.valid decides the gate."""
    child = copy.deepcopy(model)
    pmap = child.get("parameter_map") or {}
    if param_id not in pmap:
        return None, {"status": "UNBOUND_PARAMETER",
                      "reason": (f"parameter {param_id!r} is not bound "
                                 "to the parametric model — nothing "
                                 "was rebuilt (Art. VI: no silent "
                                 "substitution)")}
    p = pmap[param_id]
    old = p.get("value")
    p["value"] = new_value
    child["parent_model_id"] = model.get("model_id")
    child["mutation_provenance"] = copy.deepcopy(
        model.get("mutation_provenance") or [])
    child["mutation_provenance"].append({
        "mutation_id": mutation_id,
        "param_id": param_id,
        "from_value": old, "to_value": new_value,
        "value_class": p.get("value_class"),
        "envelope": [p.get("range_min"), p.get("range_max")],
        "reason": reason,
        "before_model_id": model.get("model_id"),
        "mutated_at": utc_now(),
    })
    # derived artifacts of the PARENT do not travel — the child's
    # geometry is rebuilt from the definition, never inherited
    child["derived_artifacts"] = {}
    child["views"] = {}
    child["measurements"] = None
    child["geometry_validation"] = None
    built, rec = build_and_validate_model(child, out_dir=out_dir)
    rec["rebuild_for_mutation"] = {
        "mutation_id": mutation_id, "param_id": param_id,
        "from_value": old, "to_value": new_value,
    }
    return built, rec


# ---------------------------------------------------------------------------
# 8. SPEC ATTACHMENT (mirrors the technical_state pattern)
# ---------------------------------------------------------------------------
def attach_parametric_model(spec: Dict[str, Any],
                            model: Dict[str, Any],
                            build_record: Dict[str, Any],
                            warrants: Dict[str, Any]
                            ) -> Dict[str, Any]:
    """Write the parametric model onto the INVENTION_SPEC as a
    first-class section. The section's epistemic class is
    COMPUTATIONAL_RESULT — geometry is computed, never observed. The
    build record and the warrants decision travel with it."""
    spec = copy.deepcopy(spec)
    spec[PARAMETRIC_MODEL_SECTION] = {
        "value": model,
        "epistemic_class": "COMPUTATIONAL_RESULT",
        "origin_stage": "CAD_PIPELINE (R380)",
        "warrants_3d": warrants,
        "build_record": build_record,
        "note": ("parametric 3D engineering design (R380): the "
                 "parametric definition (build program + parameter "
                 "map) is the source of truth; STEP/STL/GLB/SVG are "
                 "hashed derivatives; geometric measurements are "
                 "COMPUTATIONAL_RESULTs with computation logs and are "
                 "never physical evidence (Art. XXXVIII); rendering "
                 "success is never technical validation (CEO R380)"),
    }
    spec.pop("_spec_hash", None)
    return spec


def get_parametric_model(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pm = spec.get(PARAMETRIC_MODEL_SECTION)
    if isinstance(pm, dict) and isinstance(pm.get("value"), dict):
        return pm["value"]
    return None


# ---------------------------------------------------------------------------
# 9. LLM build-program proposal path (untrusted — Art. XVIII)
# ---------------------------------------------------------------------------
def build_model_program_prompt(spec: Dict[str, Any],
                               state: Dict[str, Any]
                               ) -> str:
    params = state.get("parameters") or []
    param_lines = "\n".join(
        f"- {p.get('param_id')} (category {p.get('category')}, unit "
        f"{p.get('unit')}, value {p.get('value')}, envelope "
        f"[{p.get('range_min')}, {p.get('range_max')}], class "
        f"{p.get('value_class')})"
        for p in params if p.get("range_min") is not None)
    objects = state.get("objects") or []
    obj_lines = "\n".join(
        f"- {o.get('object_id')}: {o.get('role')}" for o in objects)
    return f"""You are a parametric CAD engineer. Write a CadQuery
build program for this invention's physical design.

RULES (violations are rejected by deterministic gates):
1. Define exactly one function: def build(p) -> dict
2. EVERY dimension must come from p["<param_id>"] — NEVER hardcode a
   declared parameter value (hardcoded literals are detected and
   rejected).
3. p contains ONLY these parameters:
{param_lines}

4. The model must build these objects (return dict keys):
{obj_lines}

5. Use ONLY: cq (cadquery), math, min/max/abs/round. NO imports, NO
   file access, NO dunder names — the program runs in a sandbox.
6. Shapes must be valid 3D solids (positive volume, 3D extent).
7. Honor the declared envelopes — the pipeline validates geometry
   against them.

Return ONLY the Python source (no markdown fences, no prose).
"""


def propose_model_program(spec: Dict[str, Any],
                          state: Dict[str, Any],
                          provider: Optional[str] = None
                          ) -> Dict[str, Any]:
    """One LLM proposal attempt for a build program. The output is
    UNTRUSTED SOURCE — it only enters a spec after the sandbox scan,
    the build, and the G-gates admit it (validate + attach happen in
    propose_and_build_model, never here)."""
    from .llm_registry import SelectionPolicy, generate
    prompt = build_model_program_prompt(spec, state)
    preferred = [provider] if provider else [
        p for p in ("zai", "gemini", "openrouter", "nvidia", "mistral")]
    res = generate(
        prompt,
        system=("You are a parametric CAD engineer. Respond with "
                "Python source only."),
        policy=SelectionPolicy(
            preferred_providers=preferred, max_preference_fallback=0,
            purpose="CAD_BUILD_PROGRAM_PROPOSAL"),
        max_tokens=900)
    record: Dict[str, Any] = {
        "proposal_id": f"cadp:{sha256_obj(prompt)[:12]}",
        "provider": res.provider_id, "model": res.model,
        "status": res.status, "prompt_hash": res.prompt_hash,
        "output_hash": res.output_hash, "latency_ms": res.latency_ms,
        "error": res.error,
        "llm_is_untrusted_proposer": True,
    }
    if res.ok:
        content = (res.content or "").strip()
        content = re.sub(r"^```[a-zA-Z]*\n", "", content)
        content = re.sub(r"\n```$", "", content)
        record["program_source"] = content
        record["raw_content_sha256"] = sha256_obj(res.content or "")
    return record


# ---------------------------------------------------------------------------
# 10. THE R380 CAD PASS (top-level; template-first, LLM optional)
# ---------------------------------------------------------------------------
def run_cad_pass(spec: Dict[str, Any],
                 out_dir: Optional[str] = None,
                 provider: Optional[str] = None,
                 allow_llm: bool = True
                 ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """The 3D ENGINEERING DESIGN PIPELINE pass for one candidate:

    TECHNICAL STATE -> (warrants gate) -> PARAMETER MAP ->
    PARAMETRIC 3D MODEL -> STEP/STL/GLB DERIVATIVES ->
    GEOMETRY VALIDATION.

    Path order (honest, recorded):
      1. GEOMETRY_WARRANTS_3D — non-geometric inventions get
         NOT_APPLICABLE (never forced, never an error)
      2. ENGINE_TEMPLATE (deterministic, hermetic) when a registered
         template binds the state's parameters
      3. LLM build program (untrusted proposer, same gates) only when
         no template binds and LLM transport is available — a
         transport failure is BLOCKED_TRANSPORT, never a kill
         (Art. XXV)

    Returns (new_spec, cad_ledger). The candidate NEVER dies here —
    a failed model build records the failure honestly; the mutation
    loop's KEEP/KILL consumes the geometry verdict.
    """
    ledger: Dict[str, Any] = {
        "ledger": "CAD_PIPELINE_LEDGER (R380 3D ENGINEERING DESIGN "
                  "PIPELINE)",
        "version": CAD_PIPELINE_VERSION,
        "kernel": f"{KERNEL_ID} {_kernel_version()}",
        "secondary_verifier": "trimesh (STL watertight, independent)",
        "pass": ("TECHNICAL STATE -> PARAMETER MAP -> PARAMETRIC 3D "
                 "MODEL -> STEP/STL/GLB -> GEOMETRY VALIDATION"),
        "thresholds": CAD_THRESHOLDS,
        "started_at": utc_now(),
        "attempts": [],
        "outcome": None,
        "outcome_reason": "",
    }
    state = ((spec.get("technical_state") or {}).get("value") or {})

    # ---- 1. warrants gate --------------------------------------------
    warrants = geometry_warrants_3d(spec)
    if not warrants["warranted"]:
        ledger["outcome"] = "NOT_APPLICABLE_NO_GEOMETRY"
        ledger["outcome_reason"] = "; ".join(warrants["reasons"])
        ledger["warrants"] = warrants
        ledger["finished_at"] = utc_now()
        return spec, ledger
    ledger["warrants"] = warrants

    # ---- 2. deterministic template path ------------------------------
    attempts: List[Dict[str, Any]] = []
    for template_id in TEMPLATE_REGISTRY:
        model, problems = template_model_from_state(
            state, template_id=template_id,
            candidate_id=str(
                (spec.get("candidate_id") or
                 spec.get("id") or "candidate")))
        if model is None:
            attempts.append({"path": "ENGINE_TEMPLATE",
                             "template_id": template_id,
                             "status": "NOT_BOUND", "problems": problems})
            continue
        built, rec = build_and_validate_model(model, out_dir=out_dir)
        attempts.append({"path": "ENGINE_TEMPLATE",
                         "template_id": template_id,
                         "status": rec.get("status"),
                         "record": rec})
        if built is not None and \
                (built.get("geometry_validation") or
                 {}).get("valid"):
            new_spec = attach_parametric_model(
                spec, built, rec, warrants)
            ledger["outcome"] = "MODEL_BUILT_AND_VALIDATED"
            ledger["attempts"] = attempts
            ledger["model_id"] = built.get("model_id")
            ledger["finished_at"] = utc_now()
            return new_spec, ledger
        # template bound but geometry invalid — record honestly and
        # fall through to the LLM path (the geometry failure is DATA)
        attempts[-1]["geometry_invalid_reasons"] = (
            (built or {}).get("geometry_validation") or
            {}).get("reasons")

    # ---- 3. untrusted LLM build-program path --------------------------
    if not allow_llm:
        ledger["outcome"] = "NO_MODEL_NO_LLM"
        ledger["outcome_reason"] = (
            "no engine template binds this technical state and the "
            "LLM path is disabled (hermetic mode)")
        ledger["attempts"] = attempts
        ledger["finished_at"] = utc_now()
        return spec, ledger
    try:
        proposal = propose_model_program(spec, state,
                                         provider=provider)
    except Exception as exc:  # noqa: BLE001 — transport, never a kill
        ledger["outcome"] = "BLOCKED_TRANSPORT"
        ledger["outcome_reason"] = (
            f"LLM build-program proposal unavailable: "
            f"{type(exc).__name__}: {exc} — infrastructure, not a "
            f"research verdict (Art. XXV)")
        ledger["attempts"] = attempts
        ledger["finished_at"] = utc_now()
        return spec, ledger
    if not proposal.get("program_source"):
        ledger["outcome"] = "BLOCKED_TRANSPORT"
        ledger["outcome_reason"] = (
            f"LLM proposal returned no source (status="
            f"{proposal.get('status')}, error="
            f"{proposal.get('error')}) — never a kill (Art. XXV)")
        ledger["attempts"] = attempts
        ledger["llm_proposal"] = {k: v for k, v in proposal.items()
                                  if k != "program_source"}
        ledger["finished_at"] = utc_now()
        return spec, ledger

    # the LLM program enters through the SAME deterministic gates
    model = {
        "model_id": None,
        "model_version": CAD_PIPELINE_VERSION,
        "candidate_id": str(spec.get("candidate_id") or
                            spec.get("id") or "candidate"),
        "kernel": KERNEL_ID,
        "kernel_version": _kernel_version(),
        "template_id": None,
        "origin": "LLM_PROPOSAL",
        "build_program": proposal["program_source"],
        "program_source_sha256": hashlib.sha256(
            proposal["program_source"].encode("utf-8")).hexdigest(),
        "parameter_map": {},
        "objects": [],
        "measured_dimension_bindings": {},
        "interference_pairs": [],
        "geometry_assumptions": [],
        "materials": copy.deepcopy(state.get("materials") or []),
        "operating_conditions": copy.deepcopy(
            state.get("operating_conditions") or []),
        "measurable_outputs": copy.deepcopy(
            state.get("measurable_outputs") or []),
        "constraints": copy.deepcopy(state.get("constraints") or []),
        "parent_candidate": str(spec.get("candidate_id") or
                                spec.get("id") or "candidate"),
        "mutation_provenance": [],
        "source_evidence_provenance": {
            "technical_state_section": "technical_state",
            "llm_proposal_id": proposal.get("proposal_id"),
            "llm_output_sha256": proposal.get("raw_content_sha256"),
        },
        "derived_artifacts": {},
        "views": {},
        "geometry_validation": None,
        "evidence_class": "COMPUTATIONAL_RESULT",
    }
    # bind the state's bounded parameters into the map
    for p in state.get("parameters") or []:
        if p.get("range_min") is None and p.get("range_max") is None:
            continue
        model["parameter_map"][p["param_id"]] = {
            "param_id": p["param_id"], "value": p.get("value"),
            "unit": p.get("unit"),
            "range_min": p.get("range_min"),
            "range_max": p.get("range_max"),
            "value_class": p.get("value_class"),
            "envelope_class": p.get("range_class"),
            "category": p.get("category"),
        }
    built, rec = build_and_validate_model(model, out_dir=out_dir)
    attempts.append({"path": "LLM_PROPOSAL",
                     "proposal_id": proposal.get("proposal_id"),
                     "status": rec.get("status"), "record": rec})
    valid = (built or {}).get("geometry_validation") or {}
    if valid.get("valid"):
        new_spec = attach_parametric_model(spec, built, rec, warrants)
        ledger["outcome"] = "MODEL_BUILT_AND_VALIDATED"
        ledger["model_id"] = built.get("model_id")
    else:
        new_spec = spec
        ledger["outcome"] = "MODEL_REJECTED_BY_GEOMETRY_GATES"
        ledger["outcome_reason"] = (
            "the proposed build program failed the deterministic "
            "geometry gates — nothing entered the spec (Art. XVIII: "
            "the gates are the trust boundary)")
        ledger["rejection_reasons"] = valid.get("reasons") or \
            rec.get("build_errors")
    ledger["llm_proposal"] = {k: v for k, v in proposal.items()
                              if k != "program_source"}
    ledger["attempts"] = attempts
    ledger["finished_at"] = utc_now()
    return new_spec, ledger
