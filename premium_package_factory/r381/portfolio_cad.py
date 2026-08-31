"""premium_package_factory/r381/portfolio_cad.py — R381 3D ENGINEERING
DESIGN RETROFIT of the 15 portfolio buyer packages (CEO directive
2026-08-31).

WHAT THIS MODULE DOES (per package):
  1. CLASSIFY honestly from the canonical record (R370Q
     ArtifactRichDossier): 3D_PHYSICAL_DESIGN_REQUIRED or
     3D_NOT_APPLICABLE — deterministic, never forced.
  2. For REQUIRED packages: instantiate the PACKAGE-SPECIFIC parametric
     template (r381.templates — no generic template with renamed
     labels), bind every parameter to the record's own critical
     parameters (verbatim recorded values travel into the provenance
     chain; UNKNOWN stays recorded as UNKNOWN), build through the SAME
     deterministic gates as R380 (sandbox, G1-G8, independent trimesh
     watertight, measured-vs-claimed, hardcoded-literal scan).
  3. Export MODEL/ artifacts: parametric source, model manifest,
     parameters, constraints, STEP, STL, GLB, geometry validation
     report, key dimensions + computation logs, engineering provenance
     chains, rendered views (isometric, orthographic x3, section,
     dimensioned, exploded where the assembly warrants).
  4. RUN THE IMPROVEMENT LOOP (CEO: "A 3D image that never participates
     in this loop is NOT sufficient"): limiting parameter -> mutation
     -> CAD rebuild -> geometry measurement -> technical evaluation ->
     KEEP/KILL, recorded in DESIGN_LINEAGE + IMPROVEMENT_LOOP_EVIDENCE.

CONSTITUTIONAL ANCHORS:
- Art. III: the gates MEASURE the built solid; claims never verify
  themselves.
- Art. VI: every hash is the real sha256 of real bytes on disk; no
  timestamp is invented; shipped MODEL files carry NO wall-clock time
  (byte-reproducible release, CEO R374-5) — provenance is git history.
- Art. XXV: not-applicable / uncheckable states are recorded as such.
- Art. XXVII: every envelope/threshold carries class + justification.
- Art. XXVIII: RENDER_IS_NOT_VALIDATION everywhere; all geometry is
  COMPUTATIONAL_RESULT with computation logs; nothing may be promoted
  toward PHYSICAL_OBSERVATION (Art. XXXVIII).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.engine.cad_pipeline import (
    CAD_PIPELINE_VERSION, KERNEL_ID, _kernel_version,
    _execute_build_program, build_and_validate_model,
    rebuild_with_mutation,
)
from premium_package_factory.r371.canonical_source import load_dossier
from premium_package_factory.r381.templates import PORTFOLIO_TEMPLATES

R381_VERSION = "1.0.0"
MODEL_DIR = "MODEL"

# keys that carry wall-clock time and must never enter shipped files
# (CEO R374-5 byte-reproducible release: build provenance = git history)
_VOLATILE_KEYS = {
    "computed_at", "exported_at", "validated_at", "mutated_at",
    "built_at", "decided_at", "finished_at", "started_at",
    "generated_at", "reproduced_at", "at", "now",
}

_STEP_TIME_RE = re.compile(
    r"(FILE_NAME\('[^']*',')[^']*(')", re.IGNORECASE)
_STEP_EPOCH = "1970-01-01T00:00:00"
# OCCT increments a per-process writer counter inside the STEP PRODUCT
# name ("Open CASCADE STEP translator 7.8 1", "... 2", ...). It is
# writer-instance bookkeeping, NOT geometry — pinned to 1 so two builds
# of the same design are byte-identical (G9 compares exactly that).
_STEP_PRODUCT_COUNTER_RE = re.compile(
    r"(Open CASCADE STEP translator [0-9.]+) [0-9]+")
# OCCT assembly writer emits per-export occurrence labels inside
# NEXT_ASSEMBLY_USAGE_OCCURRENCE('N',...) that continue across exports
# within a process. Renumbering them by order of appearance is a
# bookkeeping normalization (the referenced shapes/placements are
# untouched).
_STEP_NAUO_RE = re.compile(
    r"(NEXT_ASSEMBLY_USAGE_OCCURRENCE\(')[^']*(')")
# OCCT XCAF writes STYLED_ITEM presentation bindings in nondeterministic
# order (measured: identical entity set, permuted style-to-shape
# assignment). Presentation blocks are therefore compared by TYPE COUNT;
# every other entity block is compared EXACTLY. This is the G9 assembly
# equivalence rule — geometry blocks can never drift silently.
_STEP_PRESENTATION_TYPES = frozenset((
    "STYLED_ITEM", "PRESENTATION_STYLE_ASSIGNMENT", "STYLED_ITEM_OVER",
    "PRESENTATION_STYLE", "OVER_RIDDEN_STYLED_ITEM",
    "PRESENTATION_STYLE_BY_CONTEXT",
    "MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION",
))


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sanitize(obj: Any) -> Any:
    """Strip wall-clock fields recursively — the shipped MODEL files
    are byte-reproducible (R374-5); the ONLY provenance of time is the
    git history of the build (Art. XI)."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()
                if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# 1. THE HONEST CLASSIFIER (from the canonical record — never forced)
# ---------------------------------------------------------------------------
# Art. II discipline: units are matched EXACTLY (never by substring —
# 'samples'/'MPa' must not count as meters); names are matched only on
# explicit geometry-signaling words.
_GEOMETRY_UNITS_EXACT = frozenset((
    "mm", "mm^2", "mm^3", "um", "μm", "µm", "micron", "cm", "m",
    "m^2", "m^3", "mil", "mm2", "mm3", "millimeter", "inches",
    "inch", "in",
))
_GEOMETRY_NAME_HINTS = (
    "area", "size", "geometry", "diameter", "thickness",
)
_SOFTWARE_SUBSYSTEM_MARKERS = (
    "predictor", "classifier", "feature extractor", "algorithm",
    "controller", "signal processing", "alert interface", "ml",
    "bayesian", "estimator", "software",
)


def classify_3d_requirement(pkg_id: str,
                             dossier: Dict[str, Any]) -> Dict[str, Any]:
    """Decide 3D_PHYSICAL_DESIGN_REQUIRED vs 3D_NOT_APPLICABLE from the
    package's own canonical record:

    REQUIRED  iff the record carries (a) at least one critical
              parameter with a geometry-like unit (length/area/volume)
              — i.e. the record itself declares a geometry design
              variable — or (b) a BOM/manufactured subsystem that the
              buyer would build as the technology.
    NOT_APPLICABLE iff the record's subsystems are computational, its
              BOM is empty, and no critical parameter carries a
              geometry-like unit (a software/algorithm technology).

    The decision is DETERMINISTIC from the record (Art. II — no
    semantic stretching); the measured basis is shipped with the
    verdict."""
    ec = dossier.get("engineering_content") or {}
    core = ec.get("engineering_core") or {}
    cps = core.get("critical_parameters") or []
    bom = ec.get("bom") or []
    subs = [
        (s.get("name", "") if isinstance(s, dict) else str(s)).lower()
        for s in (ec.get("system_architecture") or {}).get("subsystems")
        or []]
    manufacturing = (ec.get("manufacturing") or {}).get(
        "candidate_processes") or []

    geom_params = []
    for cp in cps:
        name = str(cp.get("name") or "")
        unit = str(cp.get("unit") or "").strip().lower()
        value = str(cp.get("value") or "")
        is_geometry = (
            unit in _GEOMETRY_UNITS_EXACT or
            any(h in name.lower() for h in _GEOMETRY_NAME_HINTS))
        if is_geometry and "not applicable" not in value.lower():
            geom_params.append({
                "recorded_name": name, "recorded_unit": cp.get("unit"),
                "recorded_value": value[:120],
            })
    physical_subsystems = [
        s for s in subs
        if s and not any(m in s for m in _SOFTWARE_SUBSYSTEM_MARKERS)]
    software_subsystems = [
        s for s in subs if any(m in s for m in _SOFTWARE_SUBSYSTEM_MARKERS)]

    reasons: List[str] = []
    if geom_params:
        reasons.append(
            f"the canonical record declares {len(geom_params)} geometry-"
            "class critical parameter(s) (length/area/volume units or "
            "size/geometry names): " + "; ".join(
                g["recorded_name"] for g in geom_params[:4]))
    if bom:
        reasons.append(
            f"the record's BOM lists {len(bom)} physical component "
            "entries the buyer would source/manufacture")
    if manufacturing:
        reasons.append(
            "the record declares manufacturing candidate processes: " +
            "; ".join(str(x) for x in manufacturing[:3]))
    if physical_subsystems:
        reasons.append(
            f"{len(physical_subsystems)} of {len(subs)} subsystems are "
            "physical device subsystems (record system_architecture)")

    # STRONG evidence = the record itself declares geometry the buyer
    # must build: a geometry-class critical parameter (exact unit or
    # geometry name), a BOM entry, or a manufacturing process.
    # Subsystem NAMES alone are weak evidence (a 'sensor stream' is a
    # data interface, not a manufactured part of THIS technology) and
    # can never force a 3D design onto a computational technology.
    strong_evidence = bool(geom_params or bom or manufacturing)
    if not strong_evidence:
        if subs and not physical_subsystems:
            software_note = (
                "every recorded subsystem is software/data-path (" +
                "; ".join(software_subsystems[:5]) + ")")
        elif physical_subsystems:
            software_note = (
                "the physical-named subsystems (" + "; ".join(
                    physical_subsystems[:5]) + ") are host/input "
                "interfaces of an otherwise computational system — "
                "none of them is a geometry the buyer builds AS this "
                "technology")
        else:
            software_note = "the record carries no subsystem geometry"
        return {
            "classification": "3D_NOT_APPLICABLE",
            "verdict": "3D_NOT_APPLICABLE",
            "measured_basis": {
                "geometry_class_critical_parameters": 0,
                "bom_entries": 0,
                "manufacturing_processes": 0,
                "physical_subsystems": len(physical_subsystems),
                "software_subsystems": len(software_subsystems),
            },
            "reasons": [
                "the technology is computational: " + software_note,
                "the record's BOM is empty — no physical device is "
                "transferred as the technology itself",
                "no manufacturing candidate process is recorded",
                "no critical parameter carries a geometry-class unit "
                "or geometry name (units present: " + "; ".join(sorted({
                    str(cp.get("unit")) for cp in cps})) + ")",
            ],
            "policy": (
                "CEO R381: do not invent geometry where the technology "
                "does not meaningfully require it. A decorative 3D image "
                "for a software technology would violate the honesty "
                "rule (Art. XXV/XXVIII)."),
        }
    return {
        "classification": "3D_PHYSICAL_DESIGN_REQUIRED",
        "verdict": "3D_PHYSICAL_DESIGN_REQUIRED",
        "measured_basis": {
            "geometry_class_critical_parameters": len(geom_params),
            "bom_entries": len(bom),
            "manufacturing_processes": len(manufacturing),
            "physical_subsystems": len(physical_subsystems),
            "software_subsystems": len(software_subsystems),
        },
        "reasons": reasons,
        "policy": (
            "CEO R381: every applicable package contains a real, "
            "reproducible, package-specific engineering model bound to "
            "its own technical state."),
    }


# ---------------------------------------------------------------------------
# 2. Record binding (verbatim critical-parameter provenance)
# ---------------------------------------------------------------------------
def _record_bindings(pkg_id: str, tpl: Dict[str, Any],
                     dossier: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """For every model parameter: pull the record's own critical
    parameter VERBATIM (name, value, unit, basis). Where the record has
    no such parameter, the binding says so honestly — the engine's
    MODELLED proposal is never laundered into a record value (Art. VI)."""
    core = (dossier.get("engineering_content") or {}).get(
        "engineering_core") or {}
    cps = core.get("critical_parameters") or []
    by_name = {str(cp.get("name")): cp for cp in cps}
    bindings: Dict[str, Dict[str, Any]] = {}
    for p in tpl["parameters"]:
        rec_name = p.get("record_parameter") or ""
        exact = None
        if rec_name and not rec_name.startswith("("):
            exact = by_name.get(rec_name)
        if exact is not None:
            bindings[p["param_id"]] = {
                "binding_status": "BOUND_TO_RECORD",
                "source": ("R370Q ArtifactRichDossier "
                           "engineering_content.engineering_core."
                           "critical_parameters[name="
                           + json.dumps(rec_name) + "]"),
                "recorded_name": exact.get("name"),
                "recorded_value": exact.get("value"),
                "recorded_unit": exact.get("unit"),
                "recorded_basis": exact.get("basis"),
                "recorded_verification_requirement":
                    exact.get("verification_requirement"),
            }
        else:
            bindings[p["param_id"]] = {
                "binding_status": "NOT_IN_RECORD_ENGINE_DECLARED",
                "source": "r381 template (engine-owned design choice)",
                "recorded_name": rec_name,
                "note": ("no verbatim critical parameter of this name "
                         "exists in the canonical record; the value "
                         "below is an ENGINE-DECLARED MODELLED design "
                         "proposal inside a declared envelope — never "
                         "an evidence claim"),
            }
    return bindings


# ---------------------------------------------------------------------------
# 3. Model factory (template -> cad_pipeline model dict)
# ---------------------------------------------------------------------------
def model_from_template(pkg_id: str, tpl: Dict[str, Any],
                        params_override: Optional[Dict[str, float]] = None
                        ) -> Dict[str, Any]:
    pmap: Dict[str, Dict[str, Any]] = {}
    for p in tpl["parameters"]:
        v = (params_override or {}).get(p["param_id"], p["value"])
        pmap[p["param_id"]] = {
            "param_id": p["param_id"], "value": v, "unit": p["unit"],
            "range_min": p["range_min"], "range_max": p["range_max"],
            "value_class": "MODELLED", "envelope_class": "MODELLED",
            "category": "GEOMETRY",
            "design_basis": p.get("design_basis"),
        }
    program = tpl["program"].strip()
    return {
        "model_id": None,
        "model_version": CAD_PIPELINE_VERSION,
        "candidate_id": pkg_id,
        "kernel": KERNEL_ID, "kernel_version": _kernel_version(),
        "template_id": tpl["template_id"], "origin": "ENGINE_TEMPLATE",
        "build_program": program,
        "program_source_sha256": hashlib.sha256(
            program.encode("utf-8")).hexdigest(),
        "parameter_map": pmap,
        "objects": copy.deepcopy(tpl["objects"]),
        "measured_dimension_bindings": copy.deepcopy(
            tpl["measured_dimension_bindings"]),
        "interference_pairs": copy.deepcopy(tpl["interference_pairs"]),
        "geometry_assumptions": copy.deepcopy(tpl["geometry_assumptions"]),
        "materials": [], "operating_conditions": [],
        "measurable_outputs": [],
        "constraints": copy.deepcopy(tpl["constraints"]),
        "parent_candidate": pkg_id, "mutation_provenance": [],
        "source_evidence_provenance": {},
        "derived_artifacts": {}, "views": {},
        "geometry_validation": None,
        "evidence_class": "COMPUTATIONAL_RESULT",
    }


def _objects_for_params(pkg_id: str, tpl: Dict[str, Any],
                         params: Dict[str, float]) -> List[Dict[str, Any]]:
    """Dynamic object lists (e.g. P-01 ring count follows segment_count)
    — the DECLARED assembly must match what the parameters actually
    build (no stale object list after a count mutation)."""
    objs = copy.deepcopy(tpl["objects"])
    if tpl.get("objects_kind") == "dynamic_rings":
        n = int(round(params.get("segment_count", 4.0)))
        objs = [dict(object_id="catheter_body",
                     role="extruded catheter body with central drainage "
                          "lumen")]
        for i in range(n):
            objs.append(dict(
                object_id=f"flow_sensor_ring_s{i + 1}",
                role=f"segment {i + 1} flow sensor collar"))
    return objs


def _pairs_for_params(pkg_id: str, tpl: Dict[str, Any],
                       params: Dict[str, float]) -> List[Dict[str, Any]]:
    if tpl.get("interference_pairs_kind") == "dynamic_rings":
        n = int(round(params.get("segment_count", 4.0)))
        return [dict(a=f"flow_sensor_ring_s{i + 1}", b="catheter_body",
                     requirement="CONTACT") for i in range(n)]
    return copy.deepcopy(tpl["interference_pairs"])


def build_portfolio_model(pkg_id: str, tpl: Dict[str, Any],
                          out_dir: str,
                          params_override: Optional[Dict[str, float]] = None
                          ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Instantiate + build + validate + export derivatives through the
    SAME gates as the engine. Dynamic objects/pairs refresh from the
    parameters. STEP headers are normalized (fixed epoch) and hashes
    recomputed from the real bytes on disk (Art. VI)."""
    model = model_from_template(pkg_id, tpl, params_override)
    params = {pid: p["value"] for pid, p in
              model["parameter_map"].items()}
    model["objects"] = _objects_for_params(pkg_id, tpl, params)
    model["interference_pairs"] = _pairs_for_params(pkg_id, tpl, params)
    built, rec = build_and_validate_model(model, out_dir=out_dir)
    if (built or {}).get("model_id"):
        _normalize_step_files(built)
    return built, rec


def _normalize_step_files(model: Dict[str, Any]) -> None:
    """OCCT writes a wall-clock timestamp into the STEP header — that
    breaks the byte-reproducible release (CEO R374-5). Normalize it to
    the fixed epoch and RE-HASH the real bytes (Art. VI: the recorded
    hash is always the hash of the bytes actually on disk)."""
    for key, art in list((model.get("derived_artifacts") or
                          {}).items()):
        if not key.startswith("STEP") or not art.get("path"):
            continue
        path = art["path"]
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="surrogateescape"
                  ) as fh:
            text = fh.read()
        text2 = _STEP_TIME_RE.sub(
            r"\g<1>" + _STEP_EPOCH + r"\g<2>", text, count=1)
        text2 = _STEP_PRODUCT_COUNTER_RE.sub(r"\g<1> 1", text2)
        # renumber assembly occurrence labels by order of appearance
        if _STEP_NAUO_RE.search(text2):
            _i = [0]

            def _renauo(m, _i=_i):
                _i[0] += 1
                return m.group(1) + str(_i[0]) + m.group(2)
            text2 = _STEP_NAUO_RE.sub(_renauo, text2)
        if text2 != text:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as fh:
                fh.write(text2)
        art["sha256"] = _sha256_file(path)
        art["bytes"] = os.path.getsize(path)
        art["determinism_note"] = (
            "OCCT STEP header timestamp normalized to the fixed epoch, "
            "the per-process writer counter pinned and assembly "
            "occurrence labels renumbered by order of appearance (CEO "
            "R374-5 byte-reproducible release); geometry content is "
            "untouched.")


# ---------------------------------------------------------------------------
# 4. TECHNICAL VIEWS (presentation only — a render is NOT validation)
# ---------------------------------------------------------------------------
def export_technical_views(model: Dict[str, Any], pkg_id: str,
                           out_dir: str) -> Dict[str, Any]:
    """The R381 required visual package: isometric + section already
    exported by the engine pipeline; this adds ORTHOGRAPHIC (front/top/
    right), a DIMENSIONED view (measured dimensions annotated on the
    front projection), and an EXPLODED view for multi-object assemblies.
    All views are OCCT hidden-line projections of the SAME B-rep —
    presentation derivatives, never validation inputs (Art. XXVIII)."""
    import cadquery as cq  # noqa: PLC0415 — trusted side
    from cadquery import exporters as cq_exporters  # noqa: PLC0415

    out = Path(out_dir)
    views: Dict[str, Any] = {}
    params = {pid: p.get("value") for pid, p in
              (model.get("parameter_map") or {}).items()}
    shapes, errors = _execute_build_program(
        model.get("build_program") or "", params)
    if shapes is None:
        return {"status": "UNAVAILABLE", "reason": errors}

    base = pkg_id
    opts_iso = {"width": 480, "height": 480, "marginLeft": 20,
                "marginTop": 20, "showAxes": False, "strokeWidth": 0.35,
                "strokeColor": (0, 0, 0), "hiddenColor": (120, 120, 120)}

    def _proj(name, wp, direction, width=480, height=480):
        try:
            path = str(out / f"{base}_view_{name}.svg")
            cq_exporters.export(wp, path, opt=dict(
                opts_iso, projectionDir=direction, width=width,
                height=height))
            views[name] = {"path": path, "sha256": _sha256_file(path),
                           "bytes": os.path.getsize(path),
                           "role": (f"{name} orthographic projection "
                                   "(OCCT hidden-line) — presentation "
                                   "only, a render is NOT validation")}
        except Exception as exc:  # noqa: BLE001
            views[name] = {"status": "EXPORT_FAILED",
                           "error": f"{type(exc).__name__}: {exc}",
                           "note": "a failed render never blocks the "
                                    "package (render != validation)"}

    first_key = next(iter(shapes))
    wp_first = shapes[first_key]
    _proj("orthographic_front", wp_first, (0.0, -1.0, 0.0))
    _proj("orthographic_top", wp_first, (0.0, 0.0, 1.0))
    _proj("orthographic_right", wp_first, (1.0, 0.0, 0.0))

    # ---- dimensioned technical view (front projection + measured dims)
    try:
        front = views.get("orthographic_front")
        if isinstance(front, dict) and front.get("path"):
            m = (model.get("measurements") or {}).get("objects", {}
                                                      ).get(first_key, {})
            dim = _annotate_dimensions(front["path"], m, out,
                                       f"{base}_view_dimensioned.svg")
            views["dimensioned"] = dim
    except Exception as exc:  # noqa: BLE001
        views["dimensioned"] = {"status": "EXPORT_FAILED",
                                "error": f"{type(exc).__name__}: {exc}"}

    # ---- exploded view (multi-object assemblies only)
    if len(shapes) > 1:
        try:
            parts = []
            solids = []
            for idx, (oid, wp) in enumerate(shapes.items()):
                solid = wp.val() if hasattr(wp, "val") else wp
                solids.append(solid)
                # deterministic axial explode: primary part stays,
                # each subsequent part shifts +k*dz
                dz = idx * (float((model.get("measurements") or {})
                                  .get("objects", {})
                                  .get(first_key, {})
                                  .get("bbox", {}).get("zlen") or 20.0)
                            * 0.12 + 3.0)
                if idx:
                    solid = solid.translate(cq.Vector(0.0, 0.0, dz))
                parts.append(solid)
            comp = cq.Compound.makeCompound(parts)
            wp_expl = cq.Workplane("XY").newObject([comp])
            path = str(out / f"{base}_view_exploded.svg")
            cq_exporters.export(wp_expl, path, opt=dict(
                opts_iso, projectionDir=(1.0, 1.0, 1.0)))
            views["exploded"] = {
                "path": path, "sha256": _sha256_file(path),
                "bytes": os.path.getsize(path),
                "role": ("exploded assembly layout (axial offsets, "
                         f"{len(parts)} objects) — presentation "
                         "only, a render is NOT validation"),
            }
        except Exception as exc:  # noqa: BLE001
            views["exploded"] = {"status": "EXPORT_FAILED",
                                 "error": f"{type(exc).__name__}: {exc}"}
    else:
        views["exploded"] = {
            "status": "NOT_APPLICABLE",
            "reason": ("single-object model — no parts to separate "
                       "(honest not-applicable, never forced)"),
        }
    return {"status": "OK", "views": views}


_SVG_NS = "http://www.w3.org/2000/svg"


def _annotate_dimensions(front_svg: str, measured: Dict[str, Any],
                         out_dir: Path, dest_name: str) -> Dict[str, Any]:
    """Overlay measured dimensions (bbox extents + principal cylinder
    diameters) on a copy of the front projection. The annotation values
    are MEASURED geometry (COMPUTATIONAL_RESULT, computation log in
    KEY_DIMENSIONS.json) — the drawing is presentation, not validation."""
    tree = ET.parse(front_svg)
    root = tree.getroot()
    w = float(root.get("width", 480))
    h = float(root.get("height", 480))
    g = ET.SubElement(root, f"{{{_SVG_NS}}}g", {
        "id": "measured-dimensions",
        "stroke": "#b00020", "fill": "none",
        "stroke-width": "0.8",
        "font-family": "Helvetica, Arial, sans-serif",
        "font-size": "9",
    })

    def _dim_h(y, x1, x2, label):
        ET.SubElement(g, f"{{{_SVG_NS}}}line",
                      {"x1": str(x1), "y1": str(y), "x2": str(x2),
                       "y2": str(y), "marker-start": "url(#arr)",
                       "marker-end": "url(#arr)"})
        t = ET.SubElement(g, f"{{{_SVG_NS}}}text", {
            "x": str((x1 + x2) / 2), "y": str(y - 3),
            "text-anchor": "middle", "fill": "#b00020",
            "stroke": "none"})
        t.text = label

    def _dim_v(x, y1, y2, label):
        ET.SubElement(g, f"{{{_SVG_NS}}}line",
                      {"x1": str(x), "y1": str(y1), "x2": str(x),
                       "y2": str(y2), "marker-start": "url(#arr)",
                       "marker-end": "url(#arr)"})
        t = ET.SubElement(g, f"{{{_SVG_NS}}}text", {
            "x": str(x + 4), "y": str((y1 + y2) / 2),
            "text-anchor": "start", "fill": "#b00020",
            "stroke": "none"})
        t.text = label

    bb = measured.get("bbox") or {}
    radii = measured.get("cylinder_face_radii") or []
    notes = []
    if bb.get("xlen") is not None:
        _dim_h(h - 24, 40, w - 40, f"X {round(bb['xlen'], 3)} mm "
                                   f"(measured)")
        notes.append(f"bbox_x={round(bb['xlen'], 3)}mm")
    if bb.get("zlen") is not None:
        _dim_v(w - 24, 30, h - 40, f"Z {round(bb['zlen'], 3)} mm "
                                   f"(measured)")
        notes.append(f"bbox_z={round(bb['zlen'], 3)}mm")
    if radii:
        dmax = round(2.0 * max(radii), 3)
        _dim_h(30, 40, w - 40, f"OD {dmax} mm (measured, max cylinder)")
        notes.append(f"max_cyl_dia={dmax}mm")
    if measured.get("min_wall_thickness_mm") is not None:
        t = ET.SubElement(g, f"{{{_SVG_NS}}}text", {
            "x": "8", "y": "14", "fill": "#b00020", "stroke": "none"})
        t.text = (f"min wall {round(measured['min_wall_thickness_mm'], 3)} "
                  f"mm (measured, signed containment)")
    legend = ET.SubElement(g, f"{{{_SVG_NS}}}text", {
        "x": "8", "y": str(h - 8), "fill": "#b00020", "stroke": "none",
        "font-size": "7"})
    legend.text = ("dimensions are MEASURED on the built solid "
                   "(COMPUTATIONAL_RESULT) — the drawing is "
                   "presentation, not validation")
    # arrow marker defs
    defs = ET.SubElement(root, f"{{{_SVG_NS}}}defs")
    mk = ET.SubElement(defs, f"{{{_SVG_NS}}}marker", {
        "id": "arr", "markerWidth": "6", "markerHeight": "6",
        "refX": "3", "refY": "3", "orient": "auto"})
    ET.SubElement(mk, f"{{{_SVG_NS}}}path", {
        "d": "M0,0 L6,3 L0,6 z", "fill": "#b00020", "stroke": "none"})
    dest = str(Path(out_dir) / dest_name)
    tree.write(dest, encoding="unicode", xml_declaration=False)
    return {"path": dest, "sha256": _sha256_file(dest),
            "bytes": os.path.getsize(dest),
            "role": ("dimensioned technical view — annotated with "
                     "MEASURED dimensions (computation log: "
                     "KEY_DIMENSIONS.json) — presentation only, "
                     "a render is NOT validation"),
            "annotated_dimensions": notes}


# ---------------------------------------------------------------------------
# 5. PER-PACKAGE TECHNICAL EVALUATORS (the loop's evaluation step)
# ---------------------------------------------------------------------------
# Each evaluator computes the package's declared MODELLED relation from
# MEASURED geometry. Evidence class: COMPUTATIONAL_RESULT computed from
# a MODELLED relation — never a physical observation (Art. XXXVIII).

def _first(model, oid=None):
    objs = (model.get("measurements") or {}).get("objects") or {}
    if oid and oid in objs:
        return objs[oid]
    return next(iter(objs.values())) if objs else {}


def _radii(model, oid=None):
    return (_first(model, oid).get("cylinder_face_radii") or [])


def _g7_volume(model, a, b):
    g7 = ((model.get("geometry_validation") or {}).get("checks") or {}
          ).get("G7_impossible_intersections") or {}
    for row in (g7.get("detail") or []):
        pair = row.get("pair") or ()
        if set(pair) == {a, b}:
            return row.get("measured_interference_volume_mm3")
    return None


def _eval_p01(parent, child):
    L = _first(child, "catheter_body").get("bbox", {}).get("zlen")
    n = (child.get("parameter_map") or {}).get("segment_count", {}
                                               ).get("value")
    L0 = _first(parent, "catheter_body").get("bbox", {}).get("zlen")
    n0 = (parent.get("parameter_map") or {}).get("segment_count", {}
                                                 ).get("value")
    if not all([L, n, L0, n0]):
        return None
    return {
        "quantity": "occlusion_localization_resolution_mm",
        "before": round(L0 / n0, 4), "after": round(L / n, 4),
        "relation": "resolution = measured_length / segment_count",
        "improved": (L / n) < (L0 / n0),
        "computation_basis": (
            "length MEASURED (catheter_body bbox zlen); N is the "
            "mutated design variable"),
    }


def _eval_p02(parent, child):
    a = _g7_volume(child, "valve_poppet", "valve_housing")
    b = _g7_volume(parent, "valve_poppet", "valve_housing")
    if a is None or b is None:
        return None
    return {
        "quantity": "poppet_seat_engagement_mm3",
        "before": round(b, 6), "after": round(a, 6),
        "relation": ("measured interference volume between poppet and "
                     "seat (G7 gate result)"),
        "improved": a > b,
        "computation_basis": "OCCT boolean intersect volume, G7 gate",
    }


def _eval_p04(parent, child):
    def tau(m):
        L = _first(m, "catheter_body").get("bbox", {}).get("zlen")
        rr = sorted(_radii(m, "enzyme_coating_layer"))
        if not L or not rr:
            return None
        r_eff = rr[0]  # innermost coating radius = effective lumen wall
        area = math.pi * r_eff * r_eff
        v = 5.0 / area  # Q = 0.3 mL/min = 5 mm3/s (MODELLED assumption)
        return L / v
    t0, t1 = tau(parent), tau(child)
    if t0 is None or t1 is None:
        return None
    return {
        "quantity": "contact_time_tau_s",
        "before": round(t0, 3), "after": round(t1, 3),
        "relation": ("tau = L_measured / v; v = Q_declared / "
                     "A_measured; Q = 0.3 mL/min MODELLED"),
        "improved": t1 > t0,
        "computation_basis": (
            "L and effective lumen radius MEASURED; Q is a declared "
            "MODELLED operating assumption (record: tau derived as L/v)"),
    }


def _eval_p07(parent, child):
    # the honest KILL demo: geometry gate decides
    d_floor = (child.get("parameter_map") or {}).get(
        "floor_lumen_diameter_mm", {}).get("value")
    d0 = (parent.get("parameter_map") or {}).get(
        "floor_lumen_diameter_mm", {}).get("value")
    d_prim = (parent.get("parameter_map") or {}).get(
        "primary_lumen_diameter_mm", {}).get("value")
    return {
        "quantity": "floor_to_primary_conductance_ratio_modelled",
        "before": round((d0 / d_prim) ** 4, 5),
        "after": round((d_floor / d_prim) ** 4, 5),
        "relation": ("G_floor/G_primary = (d_floor/d_primary)^4 "
                     "(Poiseuille, MODELLED)"),
        "improved": False,
        "computation_basis": (
            "diameters are the mutated design variables; the measured "
            "verdict comes from the geometry gates (wall constraint on "
            "the built solid) — this relation documents the design-side "
            "meaning of the rejected mutation"),
    }


def _eval_p11(parent, child):
    def area(m):
        L = _first(m, "catheter_body").get("bbox", {}).get("zlen")
        rr = sorted(_radii(m, "titanium_coating_layer"))
        if not L or not rr:
            return None
        return math.pi * 2.0 * rr[0] * L
    a0, a1 = area(parent), area(child)
    if a0 is None or a1 is None:
        return None
    return {
        "quantity": "colonizable_coated_area_mm2",
        "before": round(a0, 3), "after": round(a1, 3),
        "relation": ("A = pi * d_effective_measured * L_measured "
                     "(flat-equivalent)"),
        "improved": a1 > a0,
        "computation_basis": (
            "effective Ti-coated radius and length MEASURED; the "
            "electrospun 10-1000x surface multiplier stays the record's "
            "EXTERNAL_PRECEDENT and is NOT applied"),
    }


def _eval_p15(parent, child):
    def vol(m):
        e = _first(m, "piezo_layer_a")
        bb = e.get("bbox") or {}
        if not bb.get("xlen"):
            return None
        return bb["xlen"] * bb["ylen"] * bb["zlen"] * 2.0
    v0, v1 = vol(parent), vol(child)
    if v0 is None or v1 is None:
        return None
    return {
        "quantity": "active_piezo_volume_mm3",
        "before": round(v0, 4), "after": round(v1, 4),
        "relation": "V = 2 * L_measured * W_measured * t_measured",
        "improved": v1 > v0,
        "computation_basis": "both lamina bboxes MEASURED",
    }


def _eval_p16(parent, child):
    def area(m):
        rr = _radii(m, "gaas_pv_cell")
        if not rr:
            return None
        return math.pi * rr[0] * rr[0]
    a0, a1 = area(parent), area(child)
    if a0 is None or a1 is None:
        return None
    return {
        "quantity": "receiver_cell_area_mm2",
        "before": round(a0, 3), "after": round(a1, 3),
        "relation": "A = pi * r_measured^2",
        "improved": a1 > a0,
        "computation_basis": "cell radius MEASURED (BRepAdaptor)",
    }


def _eval_p21(parent, child):
    def vol(m):
        return (_first(m, "helical_antenna").get("volume_mm3"))
    v0, v1 = vol(parent), vol(child)
    if v0 is None or v1 is None:
        return None
    return {
        "quantity": "conductor_volume_mm3",
        "before": round(v0, 4), "after": round(v1, 4),
        "relation": ("V_conductor measured — monotone proxy for "
                     "cross-section at fixed helix geometry"),
        "improved": v1 > v0,
        "computation_basis": ("swept antenna volume MEASURED; SAR stays "
                              "the record's EXTERNAL_PRECEDENT bound"),
    }


def _eval_p22(parent, child):
    def arm(m):
        e = _first(m, "steerable_catheter_body")
        bb = e.get("bbox") or {}
        faces = e.get("cylinder_faces") or []
        if not bb.get("xmin") or not faces:
            return None
        cx = (bb["xmin"] + bb["xmax"]) / 2.0
        cy = (bb["ymin"] + bb["ymax"]) / 2.0
        rs = [f["radius"] for f in faces]
        r_lumen = min(rs)  # steering lumens are the small faces
        offs = []
        for f in faces:
            if abs(f["radius"] - r_lumen) < 1e-9:
                offs.append(math.hypot(f["axis_x"] - cx,
                                       f["axis_y"] - cy))
        return max(offs) if offs else None
    a0, a1 = arm(parent), arm(child)
    if a0 is None or a1 is None:
        return None
    return {
        "quantity": "steering_moment_arm_mm",
        "before": round(a0, 4), "after": round(a1, 4),
        "relation": ("offset of the steering-lumen axes from the body "
                     "axis, MEASURED from cylinder face geometry"),
        "improved": a1 > a0,
        "computation_basis": ("BRepAdaptor cylinder axis locations vs "
                              "bbox center — MEASURED"),
    }


def _eval_p24(parent, child):
    def gap(m):
        bore = sorted(_radii(m, "damper_housing"))
        spool = sorted(_radii(m, "damper_spool"))
        if len(bore) < 2 or len(spool) < 2:
            return None
        return bore[-2] - spool[-1]  # bore wall r - spool outer r
    g0, g1 = gap(parent), gap(child)
    if g0 is None or g1 is None:
        return None
    return {
        "quantity": "annular_damping_gap_mm",
        "before": round(g0, 4), "after": round(g1, 4),
        "relation": ("gap = bore_radius_measured - spool_outer_radius_"
                     "measured; c_h_rel = 1/gap^3 (MODELLED)"),
        "improved": (1.0 / (g1 ** 3)) > (1.0 / (g0 ** 3)),
        "relative_resistance_change": round(
            (g0 / g1) ** 3, 3),
        "computation_basis": ("both radii MEASURED (BRepAdaptor); the "
                              "absolute c_h needs the record's UNKNOWN "
                              "fluid properties — not claimed"),
    }


def _eval_p26(parent, child):
    def area(m):
        md = _radii(m, "semipermeable_membrane")
        ring = _radii(m, "membrane_retaining_ring_upper")
        if not md or not ring:
            return None
        r_active = min(ring)  # ring inner radius = exposed membrane edge
        return math.pi * r_active * r_active
    a0, a1 = area(parent), area(child)
    if a0 is None or a1 is None:
        return None
    return {
        "quantity": "active_membrane_area_mm2",
        "before": round(a0, 3), "after": round(a1, 3),
        "relation": "A_active = pi * clamp_ring_inner_radius_measured^2",
        "improved": a1 > a0,
        "computation_basis": ("retaining-ring inner radius MEASURED "
                              "(the clamped rim is inactive)"),
    }


def _eval_p27(parent, child):
    def diaph(m):
        e = _first(m, "sensor_die")
        bb = e.get("bbox") or {}
        vol = e.get("volume_mm3")
        dw = (m.get("parameter_map") or {}).get("die_width_mm", {}
                                                ).get("value")
        cw = (m.get("parameter_map") or {}).get("cavity_width_mm", {}
                                                ).get("value")
        if not bb.get("zlen") or vol is None or not dw or not cw:
            return None
        # volume = dw^2*t - cw^2*(t-dt)  =>  dt from measured volume
        dt = bb["zlen"] - (bb["zlen"] * dw * dw - vol) / (cw * cw)
        return dt
    d0, d1 = diaph(parent), diaph(child)
    if d0 is None or d1 is None:
        return None
    return {
        "quantity": "diaphragm_thickness_mm",
        "before": round(d0, 4), "after": round(d1, 4),
        "relation": ("dt = die_thickness_measured - cavity_depth "
                     "(cavity depth from measured volume and footprint)"),
        "improved": (1.0 / (d1 * d1)) > (1.0 / (d0 * d0)),
        "relative_sensitivity_change": round((d0 / d1) ** 2, 3),
        "computation_basis": ("die bbox + volume MEASURED; 1/t^2 "
                              "sensitivity scaling is a declared "
                              "MODELLED relation"),
    }


def _eval_p28(parent, child):
    def ap(m):
        rr = sorted(_radii(m, "pzt_transducer_disc"))
        if len(rr) < 2:
            return None
        return math.pi * (rr[-1] ** 2 - rr[0] ** 2)
    a0, a1 = ap(parent), ap(child)
    if a0 is None or a1 is None:
        return None
    return {
        "quantity": "active_aperture_area_mm2",
        "before": round(a0, 4), "after": round(a1, 4),
        "relation": ("A = pi*(pzt_outer_r^2 - lumen_r^2), radii "
                     "MEASURED"),
        "improved": a1 > a0,
        "computation_basis": "PZT annulus radii MEASURED (BRepAdaptor)",
    }


def _eval_p29(parent, child):
    def xs(m):
        rr = sorted(_radii(m, "magnet_segment_proximal"))
        if len(rr) < 2:
            return None
        return math.pi * (rr[-1] ** 2 - rr[0] ** 2) * 0.5
    a0, a1 = xs(parent), xs(child)
    if a0 is None or a1 is None:
        return None
    return {
        "quantity": "magnet_cross_section_mm2_per_segment",
        "before": round(a0, 4), "after": round(a1, 4),
        "relation": ("A = pi*(R_out^2 - R_in^2)/2 for the half-annular "
                     "segment, radii MEASURED"),
        "improved": a1 > a0,
        "computation_basis": ("magnet segment radii MEASURED; absolute "
                              "B0 needs the record's UNKNOWN magnet "
                              "material — not claimed"),
    }


EVALUATORS = {
    "P-01": _eval_p01, "P-02": _eval_p02, "P-04": _eval_p04,
    "P-07": _eval_p07, "P-11": _eval_p11, "P-15-R1": _eval_p15,
    "P-16": _eval_p16, "P-21-R1": _eval_p21, "P-22-R1": _eval_p22,
    "P-24": _eval_p24, "P-26": _eval_p26, "P-27-R1": _eval_p27,
    "P-28": _eval_p28, "P-29": _eval_p29,
}


# ---------------------------------------------------------------------------
# 6. THE IMPROVEMENT LOOP (CEO: mutation -> rebuild -> measure ->
#    evaluate -> KEEP/KILL; a model that never participates is NOT
#    sufficient)
# ---------------------------------------------------------------------------
def run_improvement_loop(pkg_id: str, tpl: Dict[str, Any],
                         base_model: Dict[str, Any],
                         out_dir: str
                         ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Run ONE real mutation of an ACTUAL design variable, rebuild the
    CAD, re-validate the geometry, evaluate the package-specific
    MODELLED relation on the CHILD's measured geometry, and return
    (loop_record, kept_child_or_None).

    KEEP iff the child's geometry gates pass AND the declared relation
    did not degrade. KILL records the honest reasons — a KILL is a
    SUCCESS of the loop (the gate caught an invalid design), never
    hidden (Art. XV)."""
    mut = tpl["mutation"]
    param_id, new_value = mut["param_id"], mut["new_value"]
    mutation_id = "p3dmut:" + hashlib.sha256(
        json.dumps([pkg_id, param_id, new_value],
                   sort_keys=True).encode()).hexdigest()[:16]

    # refresh the DECLARED assembly to the child's parameter set BEFORE
    # the rebuild, so the child's geometry validation covers exactly
    # what it builds (e.g. all N ring-body interference pairs at the
    # mutated segment_count — never a stale declared set)
    child_params = {pid: p.get("value") for pid, p in
                    (base_model.get("parameter_map") or {}).items()}
    child_params[param_id] = new_value
    rebuilt_base = copy.deepcopy(base_model)
    rebuilt_base["objects"] = _objects_for_params(
        pkg_id, tpl, child_params)
    rebuilt_base["interference_pairs"] = _pairs_for_params(
        pkg_id, tpl, child_params)

    child, rec = rebuild_with_mutation(
        rebuilt_base, param_id, new_value, mutation_id,
        reason=mut.get("limiting_parameter_basis", ""),
        out_dir=out_dir)
    if rec.get("status") == "UNBOUND_PARAMETER":
        return {"outcome": "ERROR_UNBOUND_PARAMETER",
                "reason": rec.get("reason")}, None

    # post-rebuild consistency: the declared set must match what was
    # validated (defense in depth — the pre-rebuild refresh already set
    # it; a drift here would mean the template lied about its objects)
    child_params2 = {pid: p.get("value") for pid, p in
                     (child.get("parameter_map") or {}).items()}
    if child is not None:
        expected_objs = _objects_for_params(pkg_id, tpl, child_params2)
        expected_pairs = _pairs_for_params(pkg_id, tpl, child_params2)
        if (child.get("objects") != expected_objs or
                child.get("interference_pairs") != expected_pairs):
            child["objects"] = expected_objs
            child["interference_pairs"] = expected_pairs
        _normalize_step_files(child)

    gv = (child or {}).get("geometry_validation") or {}
    child_valid = bool(gv.get("valid"))
    evaluation = None
    if pkg_id in EVALUATORS:
        try:
            evaluation = EVALUATORS[pkg_id](base_model, child or {})
        except Exception as exc:  # noqa: BLE001
            evaluation = {"status": "EVALUATION_ERROR",
                          "error": f"{type(exc).__name__}: {exc}"}

    kept = False
    if not child_valid:
        outcome = "KILLED_GEOMETRY_INVALID"
        outcome_reason = ("the child failed the deterministic geometry "
                          "gates: " + "; ".join(
                              str(r) for r in (gv.get("reasons") or
                                               rec.get("build_errors")
                                               or [])[:3]))
    elif evaluation and evaluation.get("status") == "EVALUATION_ERROR":
        outcome = "KILLED_EVALUATION_UNAVAILABLE"
        outcome_reason = evaluation.get("error", "")
    elif evaluation is None:
        outcome = "KILLED_EVALUATION_UNAVAILABLE"
        outcome_reason = "no evaluator computed for this package"
    elif evaluation.get("improved"):
        outcome = "KEEP"
        outcome_reason = (
            "child geometry VALID through all gates AND the declared "
            "MODELLED relation improved: "
            f"{evaluation.get('quantity')} "
            f"{evaluation.get('before')} -> {evaluation.get('after')}")
        kept = True
    else:
        outcome = "KILL"
        outcome_reason = (
            "child geometry valid but the declared relation did not "
            f"improve: {evaluation.get('quantity')} "
            f"{evaluation.get('before')} -> {evaluation.get('after')}")

    record = {
        "loop": "R381_3D_IMPROVEMENT_LOOP",
        "package_id": pkg_id,
        "ceo_loop": ("candidate -> limiting parameter identified -> "
                     "parameter mutation -> CAD rebuild -> geometry "
                     "measurement -> technical evaluation -> KEEP/KILL"),
        "limiting_parameter": {
            "param_id": param_id,
            "from_value": ((base_model.get("parameter_map") or {})
                           .get(param_id) or {}).get("value"),
            "to_value": new_value,
            "basis": mut.get("limiting_parameter_basis"),
        },
        "mutation_id": mutation_id,
        "rebuild_status": rec.get("status"),
        "child_model_id": (child or {}).get("model_id"),
        "parent_model_id": base_model.get("model_id"),
        "geometry_validation_of_child": {
            "valid": child_valid,
            "failed_gates": [g for g, c in
                             ((gv.get("checks") or {}).items())
                             if c.get("status") in ("VIOLATED", "FAILED")],
            "reasons": (gv.get("reasons") or [])[:6],
        },
        "technical_evaluation": dict(
            evaluation or {},
            evidence_class="COMPUTATIONAL_RESULT",
            relation_class=(mut.get("evaluation") or {}).get(
                "relation_class", "MODELLED"),
            declared_relation=(mut.get("evaluation") or {}).get("relation"),
        ),
        "outcome": outcome,
        "outcome_reason": outcome_reason,
        "honesty_note": (
            "geometry verdicts are MEASURED on the rebuilt solid by the "
            "deterministic G-gates (Art. III); the relation is a "
            "declared MODELLED design relation — no physical "
            "observation is claimed anywhere in this loop (Art. "
            "XXXVIII)"),
    }
    return record, (child if kept else None)


# ---------------------------------------------------------------------------
# 6b. REGENERATION REPRODUCIBILITY (CEO validation item: "reproducible
#     regeneration" — the shipped design must rebuild identically)
# ---------------------------------------------------------------------------
_STEP_BLOCK_HEAD_RE = re.compile(r"\s*#\d+\s*=\s*([A-Z_0-9]+)\s*\(")


def _step_entity_blocks(path: str) -> List[str]:
    """Split a STEP file into entity blocks (each ends with ';')."""
    with open(path, "r", encoding="utf-8",
              errors="surrogateescape") as fh:
        text = fh.read()
    blocks, buf = [], []
    for line in text.splitlines():
        buf.append(line)
        if line.rstrip().endswith(";"):
            blocks.append("\n".join(buf))
            buf = []
    if buf:
        blocks.append("\n".join(buf))
    return blocks


def _step_block_type(block: str) -> str:
    m = _STEP_BLOCK_HEAD_RE.match(block)
    return m.group(1) if m else "OTHER"


def _step_assembly_equivalent(p1: str, p2: str) -> Tuple[bool, Dict]:
    """G9 assembly-STEP equivalence rule (Art. VII — the comparison is
    not weakened for geometry, only presentation write-order is
    order-insensitive):

    - every NON-presentation entity block must match EXACTLY (as a
      sorted multiset — entity ids are stable across builds);
    - presentation-styling blocks (STYLED_ITEM and friends, written in
      nondeterministic order by OCCT XCAF) must match by type COUNT;
    - a geometry/structure block that drifts is a REAL mismatch.
    """
    blocks1 = _step_entity_blocks(p1)
    blocks2 = _step_entity_blocks(p2)
    t1 = [_step_block_type(b) for b in blocks1]
    t2 = [_step_block_type(b) for b in blocks2]
    detail: Dict[str, Any] = {
        "rule": ("non-presentation entity blocks compared exactly "
                 "(sorted multiset); presentation-styling blocks "
                 "compared by type count (OCCT XCAF write-order is "
                 "nondeterministic — measured, disclosed)"),
        "blocks_a": len(blocks1), "blocks_b": len(blocks2),
    }
    # presentation counts by type
    pres1 = sorted(x for x in t1 if x in _STEP_PRESENTATION_TYPES)
    pres2 = sorted(x for x in t2 if x in _STEP_PRESENTATION_TYPES)
    if pres1 != pres2:
        detail["presentation_type_counts_differ"] = True
        return False, detail
    # exact multiset for non-presentation blocks
    geo1 = sorted(b for b, t in zip(blocks1, t1)
                  if t not in _STEP_PRESENTATION_TYPES)
    geo2 = sorted(b for b, t in zip(blocks2, t2)
                  if t not in _STEP_PRESENTATION_TYPES)
    detail["geometry_structure_blocks"] = len(geo1)
    if geo1 != geo2:
        diff = [i for i, (a, b) in enumerate(zip(geo1, geo2)) if a != b]
        detail["first_differing_block"] = int(diff[0]) if diff else None
        detail["drift_kind"] = "GEOMETRY_OR_STRUCTURE_BLOCK"
        return False, detail
    return True, detail


def check_regeneration(pkg_id: str, tpl: Dict[str, Any],
                       final_model: Dict[str, Any],
                       staging_dir: str) -> Dict[str, Any]:
    """Rebuild the SHIPPED parameter set a second time from the template
    and compare against the shipped model (model identity, measured
    geometry, derivative hashes). A design that does not regenerate is
    not reproducible — the check is honest evidence, never assumed
    (Art. XVI/XIX)."""
    params = {pid: p.get("value") for pid, p in
              (final_model.get("parameter_map") or {}).items()}
    try:
        rebuilt, _rec = build_portfolio_model(
            pkg_id, tpl, out_dir=staging_dir, params_override=params)
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAILED",
                "reason": f"rebuild raised {type(exc).__name__}: {exc}"}
    if not rebuilt or not rebuilt.get("model_id"):
        return {"status": "FAILED",
                "reason": "rebuild produced no model"}

    mismatches: List[str] = []
    if rebuilt.get("model_id") != final_model.get("model_id"):
        mismatches.append("model_id")
    if rebuilt.get("program_source_sha256") != \
            final_model.get("program_source_sha256"):
        mismatches.append("program_source_sha256")
    # measured geometry comparison, per object
    mo = (final_model.get("measurements") or {}).get("objects") or {}
    ro = (rebuilt.get("measurements") or {}).get("objects") or {}
    if set(mo) != set(ro):
        mismatches.append(f"object set {sorted(mo)} != {sorted(ro)}")
    else:
        for oid in mo:
            for field in ("volume_mm3",):
                a, b = mo[oid].get(field), ro[oid].get(field)
                if a is not None and b is not None and \
                        abs(float(a) - float(b)) > 1e-6:
                    mismatches.append(f"{oid}.{field}")
            ba, bb = mo[oid].get("bbox") or {}, ro[oid].get("bbox") or {}
            for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
                if k in ba or k in bb:
                    a, b = ba.get(k), bb.get(k)
                    if a is None or b is None or abs(a - b) > 1e-6:
                        mismatches.append(f"{oid}.bbox.{k}")
    # derivative comparison: per-object STEP/STL/GLB/SVG strict sha256;
    # the ASSEMBLY STEP uses the entity-block equivalence rule (OCCT XCAF
    # writes presentation bindings in nondeterministic order — geometry
    # blocks still compared exactly, never weakened)
    fa = final_model.get("derived_artifacts") or {}
    ra = rebuilt.get("derived_artifacts") or {}
    asm_detail: Dict[str, Any] = {}
    for key in fa:
        if key not in ra:
            continue
        p_ship, p_re = fa[key].get("path"), ra[key].get("path")
        if not p_ship or not p_re or not os.path.exists(p_ship) or \
                not os.path.exists(p_re):
            continue
        if key == "STEP:assembly":
            eq, asm_detail = _step_assembly_equivalent(p_ship, p_re)
            if not eq:
                mismatches.append(f"derivative {key}: "
                                  f"{asm_detail.get('drift_kind')}")
            continue
        if _sha256_file(p_ship) != _sha256_file(p_re):
            mismatches.append(f"derivative {key} sha256")

    return {
        "status": "REPRODUCIBLE" if not mismatches else "NOT_REPRODUCIBLE",
        "check": ("second independent build from the same template + "
                  "shipped parameter map; model identity, per-object "
                  "measured volume/bbox, and derivative hashes compared"),
        "compared": {
            "model_id": rebuilt.get("model_id") ==
                        final_model.get("model_id"),
            "objects_compared": len(mo),
            "derivatives_compared": len(fa),
            "assembly_step_rule": asm_detail or "single-object model",
        },
        "mismatches": mismatches[:12],
        "evidence_class": "COMPUTATIONAL_RESULT",
    }


# ---------------------------------------------------------------------------
# 7. PROVENANCE CHAINS (CEO: TECHNICAL_STATE -> parameter -> CAD feature
#    -> derived geometry -> measured geometry -> validation result)
# ---------------------------------------------------------------------------
# param -> (object_id, measured-field spec) per package. The measured
# value is resolved from the FINAL model's measurement record — never
# from the parameter claim (Art. III).
PARAM_MEASURED = {
    "P-01": {
        "outer_diameter_mm": ("catheter_body", "bbox.xlen"),
        "lumen_diameter_mm": ("catheter_body", "cyl_dia_min"),
        "length_mm": ("catheter_body", "bbox.zlen"),
        "segment_count": ("", "count:flow_sensor_ring_s"),
        "sensor_ring_width_mm": ("flow_sensor_ring_s1", "bbox.zlen"),
        "sensor_ring_outer_diameter_mm": ("flow_sensor_ring_s1", "bbox.xlen"),
    },
    "P-02": {
        "housing_diameter_mm": ("valve_housing", "bbox.xlen"),
        "housing_height_mm": ("valve_housing", "bbox.zlen"),
        "flow_bore_diameter_mm": ("valve_housing", "cyl_dia_min"),
        "poppet_head_diameter_mm": ("valve_poppet", "bbox.xlen"),
        "actuator_cartridge_diameter_mm": ("actuator_cartridge", "bbox.xlen"),
    },
    "P-04": {
        "outer_diameter_mm": ("catheter_body", "bbox.xlen"),
        "lumen_diameter_mm": ("catheter_body", "cyl_dia_min"),
        "length_mm": ("catheter_body", "bbox.zlen"),
        "enzyme_coating_thickness_mm": ("enzyme_coating_layer", "annulus_wall"),
    },
    "P-07": {
        "outer_diameter_mm": ("dual_lumen_catheter", "bbox.xlen"),
        "primary_lumen_diameter_mm": ("dual_lumen_catheter", "cyl_dia_max"),
        "floor_lumen_diameter_mm": ("dual_lumen_catheter", "cyl_dia_min"),
        "floor_offset_mm": ("dual_lumen_catheter", "lumen_axis_offset_min"),
        "length_mm": ("dual_lumen_catheter", "bbox.zlen"),
    },
    "P-11": {
        "outer_diameter_mm": ("catheter_body", "bbox.xlen"),
        "lumen_diameter_mm": ("catheter_body", "cyl_dia_min"),
        "length_mm": ("catheter_body", "bbox.zlen"),
        "titanium_coating_thickness_mm": ("titanium_coating_layer", "annulus_wall"),
        "phage_layer_thickness_mm": ("phage_immobilization_layer", "annulus_wall"),
    },
    "P-15-R1": {
        "beam_length_mm": ("piezo_layer_a", "bbox.xlen"),
        "beam_width_mm": ("piezo_layer_a", "bbox.ylen"),
        "piezo_layer_thickness_mm": ("piezo_layer_a", "bbox.zlen"),
        "proof_mass_size_mm": ("proof_mass", "bbox.xlen"),
        "anchor_length_mm": ("anchor_block", "bbox.xlen"),
    },
    "P-16": {
        "cell_diameter_mm": ("gaas_pv_cell", "bbox.xlen"),
        "cell_thickness_mm": ("gaas_pv_cell", "bbox.zlen"),
        "substrate_thickness_mm": ("substrate_disc", "bbox.zlen"),
        "encapsulation_thickness_mm": ("encapsulation_cap", "bbox.zlen"),
        "encapsulation_margin_mm": ("encapsulation_cap", "bbox.xlen"),
    },
    "P-21-R1": {
        "implant_od_mm": ("implant_body", "bbox.xlen"),
        "lumen_diameter_mm": ("implant_body", "cyl_dia_min"),
        "implant_length_mm": ("implant_body", "bbox.zlen"),
        "antenna_wire_diameter_mm": ("helical_antenna", "volume_mm3"),
        "helix_pitch_mm": ("helical_antenna", "bbox.zlen"),
    },
    "P-22-R1": {
        "outer_diameter_mm": ("steerable_catheter_body", "bbox.xlen"),
        "main_lumen_diameter_mm": ("steerable_catheter_body", "cyl_dia_max"),
        "steering_lumen_diameter_mm": ("steerable_catheter_body", "cyl_dia_min"),
        "steering_offset_radius_mm": ("steerable_catheter_body", "lumen_axis_offset_min"),
        "length_mm": ("steerable_catheter_body", "bbox.zlen"),
    },
    "P-24": {
        "housing_od_mm": ("damper_housing", "cyl_dia_max"),
        "housing_height_mm": ("damper_housing", "bbox.zlen"),
        "bore_diameter_mm": ("damper_housing", "cyl_dia:1"),
        "damping_gap_mm": ("pair_gap:damper_housing|damper_spool", ""),
        "inlet_bore_diameter_mm": ("damper_housing", "cyl_dia_min"),
        "spool_height_mm": ("damper_spool", "bbox.zlen"),
    },
    "P-26": {
        "housing_od_mm": ("valve_housing", "bbox.xlen"),
        "housing_height_mm": ("valve_housing", "bbox.zlen"),
        "chamber_bore_diameter_mm": ("valve_housing", "cyl_dia_min"),
        "membrane_thickness_mm": ("semipermeable_membrane", "bbox.zlen"),
        "membrane_diameter_mm": ("semipermeable_membrane", "cyl_dia_max"),
        "retaining_ring_height_mm": ("membrane_retaining_ring_upper", "bbox.zlen"),
    },
    "P-27-R1": {
        "die_width_mm": ("sensor_die", "bbox.xlen"),
        "die_thickness_mm": ("sensor_die", "bbox.zlen"),
        "diaphragm_thickness_mm": ("sensor_die", "diaphragm_thickness"),
        "cavity_width_mm": ("sensor_die", "volume_mm3"),
        "carrier_platform_thickness_mm": ("carrier_platform", "bbox.zlen"),
        "carrier_margin_mm": ("carrier_platform", "bbox.xlen"),
    },
    "P-28": {
        "catheter_tip_od_mm": ("catheter_tip_body", "bbox.xlen"),
        "lumen_diameter_mm": ("catheter_tip_body", "cyl_dia_min"),
        "tip_length_mm": ("catheter_tip_body", "bbox.zlen"),
        "pzt_disc_diameter_mm": ("pzt_transducer_disc", "cyl_dia_max"),
        "pzt_thickness_mm": ("pzt_transducer_disc", "bbox.zlen"),
        "acoustic_window_thickness_mm": ("acoustic_window_cap", "bbox.zlen"),
    },
    "P-29": {
        "tube_od_mm": ("flow_tube", "bbox.xlen"),
        "tube_length_mm": ("flow_tube", "bbox.zlen"),
        "lumen_diameter_mm": ("flow_tube", "cyl_dia_min"),
        "coil_thickness_mm": ("rf_coil_ring", "annulus_wall"),
        "coil_height_mm": ("rf_coil_ring", "bbox.zlen"),
        "magnet_thickness_mm": ("magnet_segment_proximal", "annulus_wall"),
        "magnet_length_mm": ("magnet_segment_proximal", "bbox.zlen"),
    },
}


def _resolve_measured(model: Dict[str, Any], oid: str, spec: str
                      ) -> Optional[Dict[str, Any]]:
    objs = (model.get("measurements") or {}).get("objects") or {}
    if spec.startswith("count:"):
        prefix = spec.split(":", 1)[1]
        return {"field": "object_count", "value": float(
            sum(1 for k in objs if k.startswith(prefix))),
            "computation": f"count of built objects with prefix '{prefix}'"}
    if spec.startswith("pair_gap:"):
        a, b = spec.split(":", 1)[1].split("|")
        ra = sorted(_radii(model, a))
        rb = sorted(_radii(model, b))
        if not ra or not rb:
            return None
        return {"field": "pair_gap", "value": round(ra[0] - rb[-1], 6),
                "computation": (f"min cylinder radius of {a} minus max "
                                f"cylinder radius of {b} (MEASURED faces)")}
    e = objs.get(oid)
    if e is None:
        return None
    if spec.startswith("bbox."):
        k = spec.split(".", 1)[1]
        v = (e.get("bbox") or {}).get(k)
        return {"field": f"bbox_{k}", "value": v,
                "computation": f"Shape.BoundingBox().{k} on built solid"}
    if spec == "volume_mm3":
        return {"field": "volume_mm3", "value": e.get("volume_mm3"),
                "computation": "Shape.Volume() on built solid"}
    if spec == "min_wall":
        return {"field": "min_wall_thickness_mm",
                "value": e.get("min_wall_thickness_mm"),
                "computation": ("signed containment: R - (|axis-center| + "
                                "r) over nested cylinder faces")}
    if spec == "cyl_dia_min":
        r = sorted(_radii(model, oid))
        return ({"field": "cylinder_diameter_min", "value": round(
            2.0 * r[0], 6),
            "computation": "2 x min(BRepAdaptor cylinder radius)"} if r
            else None)
    if spec == "cyl_dia_max":
        r = sorted(_radii(model, oid))
        return ({"field": "cylinder_diameter_max", "value": round(
            2.0 * r[-1], 6),
            "computation": "2 x max(BRepAdaptor cylinder radius)"} if r
            else None)
    if spec.startswith("cyl_dia:"):
        i = int(spec.split(":", 1)[1])
        r = sorted(_radii(model, oid))
        if len(r) > i:
            return {"field": f"cylinder_diameter_{i}",
                    "value": round(2.0 * r[i], 6),
                    "computation": (f"2 x sorted(BRepAdaptor cylinder "
                                    f"radii)[{i}]")}
        return None
    if spec == "annulus_wall":
        r = sorted(_radii(model, oid))
        if len(r) >= 2:
            return {"field": "annulus_wall",
                    "value": round(r[-1] - r[0], 6),
                    "computation": ("max - min BRepAdaptor cylinder "
                                    "radius of the annular object")}
        return None
    if spec == "lumen_axis_offset_min":
        bb = e.get("bbox") or {}
        faces = e.get("cylinder_faces") or []
        if not bb.get("xmin") or not faces:
            return None
        cx = (bb["xmin"] + bb["xmax"]) / 2.0
        cy = (bb["ymin"] + bb["ymax"]) / 2.0
        r_min = min(f["radius"] for f in faces)
        offs = [math.hypot(f["axis_x"] - cx, f["axis_y"] - cy)
                for f in faces if abs(f["radius"] - r_min) < 1e-9]
        return {"field": "lumen_axis_offset",
                "value": round(max(offs), 6) if offs else None,
                "computation": ("|lumen cylinder axis - bbox center| "
                                "on the built faces")}
    if spec == "diaphragm_thickness":
        bb = e.get("bbox") or {}
        vol = e.get("volume_mm3")
        pm = model.get("parameter_map") or {}
        dw = (pm.get("die_width_mm") or {}).get("value")
        cw = (pm.get("cavity_width_mm") or {}).get("value")
        if not bb.get("zlen") or vol is None or not dw or not cw:
            return None
        dt = bb["zlen"] - (bb["zlen"] * dw * dw - vol) / (cw * cw)
        return {"field": "diaphragm_thickness_mm", "value": round(dt, 6),
                "computation": ("dt = die_thickness_measured - cavity_"
                                "depth; cavity depth derived from "
                                "MEASURED volume and footprint")}
    return None


def build_provenance_chains(pkg_id: str, tpl: Dict[str, Any],
                            model: Dict[str, Any],
                            bindings: Dict[str, Any]) -> Dict[str, Any]:
    """One chain per major geometric parameter, exactly the CEO's R381
    required provenance shape. Every link is machine-derived: record
    values verbatim, program source lines by exact scan, artifact
    hashes from disk, measured values from the built solid."""
    src = model.get("build_program") or ""
    lines = src.splitlines()
    chains = {}
    for p in tpl["parameters"]:
        pid = p["param_id"]
        ref_lines = [
            ln.strip() for ln in lines
            if f'p["{pid}"]' in ln or f"p['{pid}']" in ln]
        meas = None
        spec_map = PARAM_MEASURED.get(pkg_id) or {}
        if pid in spec_map:
            oid, spec = spec_map[pid]
            try:
                meas = _resolve_measured(model, oid, spec)
            except Exception as exc:  # noqa: BLE001
                meas = {"status": "RESOLUTION_ERROR",
                        "error": f"{type(exc).__name__}: {exc}"}
        # derived artifacts: the STEP derivatives of this model
        derived = []
        for key, art in (model.get("derived_artifacts") or {}).items():
            if key.startswith("STEP") and art.get("path") and \
                    os.path.exists(art["path"]):
                derived.append({
                    "artifact": "MODEL/" + os.path.basename(art["path"]),
                    "sha256": _sha256_file(art["path"]),
                    "bytes": os.path.getsize(art["path"]),
                })
        gv = model.get("geometry_validation") or {}
        checks = gv.get("checks") or {}
        chains[pid] = {
            "technical_state": bindings.get(pid),
            "parameter": {
                # the SHIPPED value (from the built model's parameter
                # map — for a KEEP child this is the mutated value,
                # never the template default)
                "value": ((model.get("parameter_map") or {})
                          .get(pid) or {}).get("value", p["value"]),
                "unit": p["unit"],
                "envelope": [p["range_min"], p["range_max"]],
                "value_class": "MODELLED",
                "envelope_class": "MODELLED",
                "design_basis": p.get("design_basis"),
            },
            "cad_feature": {
                "source_of_truth": "MODEL/PARAMETRIC_MODEL_SOURCE.py",
                "program_lines_using_this_parameter": ref_lines,
                "note": ("the build program consumes the parameter on "
                         "these exact lines (deterministic source scan)"),
            },
            "derived_geometry": derived,
            "measured_geometry": meas or {
                "status": "NOT_DIRECTLY_MEASURED",
                "note": ("this parameter has no single measured field "
                         "binding; its effect is carried in the object "
                         "measurements (KEY_DIMENSIONS.json)"),
            },
            "validation_result": {
                "model_valid": gv.get("valid"),
                "gates": {g: c.get("status") for g, c in checks.items()},
            },
        }
    return chains


# ---------------------------------------------------------------------------
# 8. THE MODEL/ DIRECTORY WRITER
# ---------------------------------------------------------------------------
_MODEL_JSON_ROLES = {
    "3D_DESIGN_STATUS.json": "3D design classification + honest verdict (every package)",
    "PARAMETRIC_MODEL_SOURCE.py": "parametric build program — THE SOURCE OF TRUTH",
    "MODEL_MANIFEST.json": "model identity, kernel, objects, artifacts + sha256, views",
    "PARAMETERS.json": "parameter map + envelopes + record bindings (value classes)",
    "CONSTRAINTS.json": "geometric constraints, interference pairs, assumptions, material compatibility",
    "GEOMETRY_VALIDATION_REPORT.json": "deterministic G1-G8 validation on the built solid",
    "KEY_DIMENSIONS.json": "measured geometry + computation logs (COMPUTATIONAL_RESULT)",
    "ENGINEERING_PROVENANCE.json": "per-parameter chain: technical state -> parameter -> CAD feature -> derived -> measured -> validation",
    "DESIGN_LINEAGE.json": "base model -> mutation -> child model lineage (append-only)",
    "IMPROVEMENT_LOOP_EVIDENCE.json": "the CEO improvement loop: mutation -> rebuild -> measure -> evaluate -> KEEP/KILL",
    "README.json": "what this directory is; source-of-truth + evidence-class rules",
}


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, sort_keys=False)


def _shipping_artifacts(model: Dict[str, Any]) -> Dict[str, Any]:
    arts = {}
    for key, art in (model.get("derived_artifacts") or {}).items():
        if not art.get("path") or not os.path.exists(art["path"]):
            arts[key] = {"status": "MISSING_ON_DISK"}
            continue
        entry = dict(_sanitize(art))
        entry["path"] = "MODEL/" + os.path.basename(art["path"])
        entry["sha256"] = _sha256_file(art["path"])
        entry["bytes"] = os.path.getsize(art["path"])
        entry["role"] = art.get("role")
        entry["evidence_class"] = "COMPUTATIONAL_RESULT"
        entry["derivative_of"] = "parametric_model:" + str(
            model.get("model_id"))
        arts[key] = entry
    return arts


def _shipping_views(model: Dict[str, Any],
                    tech_views: Dict[str, Any]) -> Dict[str, Any]:
    views: Dict[str, Any] = {}
    for name in ("isometric", "section"):
        v = (model.get("views") or {}).get(name)
        if isinstance(v, str) and os.path.exists(v):
            views[name] = {
                "path": "MODEL/" + os.path.basename(v),
                "sha256": _sha256_file(v),
                "bytes": os.path.getsize(v),
                "role": ("isometric/section engineering line view (OCCT "
                         "hidden-line) — presentation, NOT validation"),
            }
        elif isinstance(v, dict):
            views[name] = _sanitize(v)
    for name, v in ((tech_views or {}).get("views") or {}).items():
        if isinstance(v, dict) and v.get("path") and \
                os.path.exists(v["path"]):
            entry = dict(_sanitize(v))
            entry["path"] = "MODEL/" + os.path.basename(v["path"])
            entry["sha256"] = _sha256_file(v["path"])
            entry["render_is_not_validation"] = True
            views[name] = entry
        else:
            views[name] = _sanitize(v)
    return views


def write_model_dir(pkg_id: str, portfolio_dir_pkg: str,
                    final_model: Dict[str, Any], tpl: Dict[str, Any],
                    classification: Dict[str, Any],
                    bindings: Dict[str, Any],
                    loop_record: Optional[Dict[str, Any]],
                    base_model: Optional[Dict[str, Any]],
                    final_rec: Dict[str, Any]) -> Dict[str, Any]:
    """Write the complete MODEL/ directory for one applicable package."""
    mdir = os.path.join(portfolio_dir_pkg, MODEL_DIR)
    os.makedirs(mdir, exist_ok=True)
    gv = final_model.get("geometry_validation") or {}
    regen = (gv.get("checks") or {}).get(
        "G9_regeneration_reproducibility") or {}
    if not gv.get("valid"):
        status = ("BLOCKED_NOT_REPRODUCIBLE"
                  if regen.get("status") not in (None, "REPRODUCIBLE")
                  else "BLOCKED_GEOMETRY_INVALID")
    else:
        status = "PRESENT_AND_VALIDATED"

    # --- PARAMETRIC_MODEL_SOURCE.py (the source of truth) -------------
    src_path = os.path.join(mdir, "PARAMETRIC_MODEL_SOURCE.py")
    header = (
        f'"""PARAMETRIC MODEL SOURCE — package {pkg_id} '
        f'({tpl["template_id"]}).\n'
        "THE SOURCE OF TRUTH for this 3D design: this build program plus\n"
        "MODEL/PARAMETERS.json. STEP/STL/GLB/SVG are derived artifacts.\n"
        "Executed in the engine's deterministic sandbox "
        "(discovery_fabric.engine.cad_pipeline._execute_build_program):\n"
        "only cq/math + min/max/abs/len/range/float/int/round/sorted are\n"
        "available; every dimension must come from p[...].\n"
        "program_source_sha256: " +
        str(final_model.get("program_source_sha256")) + "\n"
        '"""\n\n')
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(header + final_model["build_program"] + "\n")

    # --- 3D_DESIGN_STATUS.json ----------------------------------------
    status_doc = {
        "artifact": "3D_DESIGN_STATUS",
        "r381_version": R381_VERSION,
        "package_id": pkg_id,
        "classification": classification["classification"],
        "3d_design_status": status,
        "status_meaning": {
            "PRESENT_AND_VALIDATED": (
                "a package-specific parametric model was built, "
                "measured and validated through the deterministic "
                "geometry gates (incl. the independent trimesh "
                "watertight check and the G9 regeneration check)"),
            "BLOCKED_GEOMETRY_INVALID": (
                "the model was built but FAILED the geometry gates — "
                "the failure is recorded, never hidden"),
            "BLOCKED_NOT_REPRODUCIBLE": (
                "the model builds but does NOT regenerate identically "
                "(G9 mismatch) — the design is not reproducible and is "
                "not shipped as validated"),
        }[status],
        "classification_basis": classification,
        "model_id": final_model.get("model_id"),
        "kernel": f"{KERNEL_ID} {final_model.get('kernel_version')}",
        "template_id": tpl["template_id"],
        "improvement_loop_outcome": (loop_record or {}).get("outcome"),
        "regeneration_check": {
            "status": regen.get("status"),
            "mismatches": regen.get("mismatches", []),
            "evidence_class": "COMPUTATIONAL_RESULT",
        },
        "evidence_class": "COMPUTATIONAL_RESULT",
        "render_is_not_validation": True,
    }
    if status.startswith("BLOCKED"):
        if status == "BLOCKED_NOT_REPRODUCIBLE":
            status_doc["reason"] = (
                "G9 regeneration check " + str(regen.get("status")) +
                ": " + "; ".join(regen.get("mismatches") or
                                 [regen.get("reason") or ""])[:400])
        else:
            status_doc["reason"] = (
                "geometry gates: " + "; ".join(
                    str(r) for r in (gv.get("reasons") or [])[:5])[:400])
    _write_json(os.path.join(mdir, "3D_DESIGN_STATUS.json"), status_doc)

    # --- PARAMETERS.json -----------------------------------------------
    _write_json(os.path.join(mdir, "PARAMETERS.json"), {
        "artifact": "PARAMETERS",
        "package_id": pkg_id,
        "model_id": final_model.get("model_id"),
        "policy": ("values the canonical record does not carry are "
                   "ENGINE-DECLARED MODELLED design proposals inside "
                   "declared envelopes (Art. XXVII) — never evidence "
                   "claims; each parameter carries its verbatim record "
                   "binding"),
        "parameters": [
            {"param_id": p["param_id"],
             "value": ((final_model.get("parameter_map") or {})
                       .get(p["param_id"]) or {}).get("value"),
             "unit": p["unit"],
             "envelope": [p["range_min"], p["range_max"]],
             "value_class": "MODELLED",
             "envelope_class": "MODELLED",
             "category": "GEOMETRY",
             "design_basis": p.get("design_basis"),
             "record_binding": bindings.get(p["param_id"])}
            for p in tpl["parameters"]],
        "record_bindings_policy": (
            "recorded_value is VERBATIM from the canonical engineering "
            "record (R370Q export); UNKNOWN stays UNKNOWN — the engine "
            "never converts a record UNKNOWN into a claim"),
    })

    # --- CONSTRAINTS.json ----------------------------------------------
    _write_json(os.path.join(mdir, "CONSTRAINTS.json"), {
        "artifact": "CONSTRAINTS",
        "package_id": pkg_id,
        "model_id": final_model.get("model_id"),
        "geometric_constraints": [
            dict(c, evaluated_on="MEASURED_ON_BUILT_SOLID")
            for c in tpl["constraints"]],
        "interference_pairs": final_model.get("interference_pairs"),
        "geometry_assumptions": tpl["geometry_assumptions"],
        "materials_from_record": tpl.get("materials_from_record"),
        "material_compatibility": tpl.get("material_compatibility"),
        "threshold_policy": (
            "every limit carries epistemic_class + basis (Art. XXVII); "
            "ENGINEERING bounds declared at ENGINEERING_DEFINITION "
            "maturity are to be replaced by measured process capability "
            "at prototype stage"),
    })

    # --- GEOMETRY_VALIDATION_REPORT.json --------------------------------
    _write_json(os.path.join(mdir, "GEOMETRY_VALIDATION_REPORT.json"),
                dict(_sanitize(gv), package_id=pkg_id,
                     model_id=final_model.get("model_id"),
                     build_record=_sanitize(final_rec)))

    # --- KEY_DIMENSIONS.json --------------------------------------------
    _write_json(os.path.join(mdir, "KEY_DIMENSIONS.json"), dict(
        _sanitize(final_model.get("measurements") or {}),
        package_id=pkg_id, model_id=final_model.get("model_id"),
        evidence_class="COMPUTATIONAL_RESULT",
        note=("every value is measured on the built solid by the OCCT "
              "kernel (see computation_log per object); these are "
              "computations, never physical observations (Art. XXXVIII)"),
    ))

    # --- ENGINEERING_PROVENANCE.json -------------------------------------
    _write_json(os.path.join(mdir, "ENGINEERING_PROVENANCE.json"), {
        "artifact": "ENGINEERING_PROVENANCE",
        "package_id": pkg_id,
        "model_id": final_model.get("model_id"),
        "chain_shape": ("TECHNICAL_STATE -> parameter -> CAD feature -> "
                        "derived geometry -> measured geometry -> "
                        "validation result"),
        "chains": build_provenance_chains(
            pkg_id, tpl, final_model, bindings),
    })

    # --- DESIGN_LINEAGE.json ---------------------------------------------
    lineage = {
        "artifact": "DESIGN_LINEAGE",
        "package_id": pkg_id,
        "lineage": "append-only (Art. XXXVIII causal chain discipline)",
        "base_model_id": (base_model or {}).get("model_id"),
        "shipped_model_id": final_model.get("model_id"),
        "shipped_model_is": (
            "the KEEP child of the improvement loop" if
            (loop_record or {}).get("outcome") == "KEEP" else
            "the base design (the mutation was KILLED — see "
            "IMPROVEMENT_LOOP_EVIDENCE.json)"),
        "mutation_provenance": _sanitize(
            final_model.get("mutation_provenance") or []),
    }
    _write_json(os.path.join(mdir, "DESIGN_LINEAGE.json"), lineage)

    # --- IMPROVEMENT_LOOP_EVIDENCE.json -----------------------------------
    if loop_record is not None:
        _write_json(
            os.path.join(mdir, "IMPROVEMENT_LOOP_EVIDENCE.json"),
            _sanitize(loop_record))

    # --- technical views ---------------------------------------------------
    tech = export_technical_views(final_model, pkg_id, mdir)

    # --- MODEL_MANIFEST.json ------------------------------------------------
    _write_json(os.path.join(mdir, "MODEL_MANIFEST.json"), {
        "artifact": "MODEL_MANIFEST",
        "package_id": pkg_id,
        "model_id": final_model.get("model_id"),
        "model_version": final_model.get("model_version"),
        "r381_version": R381_VERSION,
        "kernel": f"{KERNEL_ID} {final_model.get('kernel_version')}",
        "template_id": tpl["template_id"],
        "origin": "ENGINE_TEMPLATE (r381 package-specific design)",
        "objects": final_model.get("objects"),
        "parameter_count": len(tpl["parameters"]),
        "source_of_truth": (
            "the parametric build program + parameter map "
            "(MODEL/PARAMETRIC_MODEL_SOURCE.py + PARAMETERS.json); "
            "STEP/STL/GLB/SVG below are DERIVED artifacts with real "
            "sha256 of real bytes"),
        "derived_artifacts": _shipping_artifacts(final_model),
        "views": _shipping_views(final_model, tech),
        "geometry_validation": {
            "valid": gv.get("valid"),
            "report": "MODEL/GEOMETRY_VALIDATION_REPORT.json"},
        "render_is_not_validation": True,
        "evidence_class": "COMPUTATIONAL_RESULT",
    })

    # --- README.json ---------------------------------------------------------
    _write_json(os.path.join(mdir, "README.json"), {
        "artifact": "MODEL_README",
        "package_id": pkg_id,
        "what_this_is": (
            "the package-specific parametric 3D engineering design "
            "(CEO R381): built from THIS package's own technical state "
            "through the deterministic CadQuery/OCCT pipeline and "
            "connected to the invention-improvement loop"),
        "how_to_regenerate": (
            "rebuild the portfolio release "
            "(premium_package_factory.r371.build_v5) — the build is "
            "deterministic: same program + same parameters -> same "
            "model_id and byte-identical derivatives (STEP headers "
            "epoch-normalized)"),
        "source_of_truth_rule": (
            "MODEL/PARAMETRIC_MODEL_SOURCE.py + PARAMETERS.json are the "
            "design; meshes and renders are derivatives"),
        "evidence_rules": (
            "all geometry is COMPUTATIONAL_RESULT with computation logs "
            "(KEY_DIMENSIONS.json); no file here claims a physical "
            "observation; rendering success is never technical "
            "validation (CEO R380/R381, Art. XXVIII/XXXVIII)"),
        "file_roles": _MODEL_JSON_ROLES,
    })

    # --- files listing for the package manifest -----------------------------
    files = []
    for fn in sorted(os.listdir(mdir)):
        fp = os.path.join(mdir, fn)
        if os.path.isfile(fp):
            files.append({
                "file": f"{MODEL_DIR}/{fn}",
                "role": _MODEL_JSON_ROLES.get(fn, None) or
                        _artifact_role(fn),
                "sha256": _sha256_file(fp),
                "bytes": os.path.getsize(fp)})
    return {"status": status, "model_id": final_model.get("model_id"),
            "files": files, "loop_outcome": (loop_record or {}).get(
                "outcome")}


def _artifact_role(fn: str) -> str:
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    if ext == "step":
        return ("3D engineering exchange derivative (B-rep) — hashed, "
                "epoch-normalized")
    if ext == "stl":
        return ("mesh derivative — independently watertight-checked by "
                "trimesh")
    if ext == "glb":
        return ("presentation/rendering derivative (a render is NOT "
                "validation)")
    if ext == "svg":
        return ("rendered engineering view (OCCT hidden-line) — "
                "presentation only")
    if ext == "py":
        return "parametric build program (source of truth)"
    return "3D design artifact"


# ---------------------------------------------------------------------------
# 9. TOP-LEVEL ENTRY (called by build_v5 per package)
# ---------------------------------------------------------------------------
def build_model_layer(pkg_id: str, package_dir: str,
                      work_dir: str) -> Dict[str, Any]:
    """The R381 3D layer for ONE package. Honest outcomes only:

      PRESENT_AND_VALIDATED  a package-specific model is built, measured
                             and validated; artifacts + provenance + the
                             improvement-loop evidence ship in MODEL/
      3D_NOT_APPLICABLE      the record itself shows a software-only
                             technology; MODEL/ carries the honest
                             classification and NOTHING that claims 3D
      BLOCKED_*              the model could not be produced/validated;
                             exact reasons recorded, never fabricated
    """
    dossier = load_dossier(pkg_id)
    classification = classify_3d_requirement(pkg_id, dossier)

    if classification["classification"] == "3D_NOT_APPLICABLE":
        mdir = os.path.join(package_dir, MODEL_DIR)
        os.makedirs(mdir, exist_ok=True)
        _write_json(os.path.join(mdir, "3D_DESIGN_STATUS.json"), {
            "artifact": "3D_DESIGN_STATUS",
            "r381_version": R381_VERSION,
            "package_id": pkg_id,
            "classification": "3D_NOT_APPLICABLE",
            "3d_design_status": "NOT_APPLICABLE",
            "status_meaning": (
                "the canonical engineering record itself shows a "
                "computational/algorithmic technology — no physical "
                "device geometry is a design variable of this "
                "technology. No 3D model, mesh or render is shipped, "
                "and none may be implied anywhere in this package."),
            "classification_basis": classification,
            "evidence_class": "SOURCE_DERIVED_CLASSIFICATION",
        })
        _write_json(os.path.join(mdir, "README.json"), {
            "artifact": "MODEL_README",
            "package_id": pkg_id,
            "what_this_is": (
                "the honest 3D-design classification for this package: "
                "NOT_APPLICABLE. CEO R381: 'Do not invent geometry "
                "where the technology does not meaningfully require "
                "it.' This directory intentionally contains ONLY the "
                "classification record."),
        })
        files = [{
            "file": f"{MODEL_DIR}/3D_DESIGN_STATUS.json",
            "role": "3D design classification: NOT_APPLICABLE (honest, "
                    "record-derived)",
            "sha256": _sha256_file(
                os.path.join(mdir, "3D_DESIGN_STATUS.json")),
            "bytes": os.path.getsize(
                os.path.join(mdir, "3D_DESIGN_STATUS.json"))},
            {"file": f"{MODEL_DIR}/README.json",
             "role": "model directory readme (NOT_APPLICABLE)",
             "sha256": _sha256_file(os.path.join(mdir, "README.json")),
             "bytes": os.path.getsize(
                 os.path.join(mdir, "README.json"))}]
        return {"status": "NOT_APPLICABLE", "classification":
                classification, "files": files, "model_id": None}

    tpl = _template_for(pkg_id)
    if tpl is None:
        mdir = os.path.join(package_dir, MODEL_DIR)
        os.makedirs(mdir, exist_ok=True)
        reason = (f"classified REQUIRED by the record but no R381 "
                  f"template exists for {pkg_id} — the CAD capability "
                  f"cannot yet produce a credible package-specific "
                  f"design for this technology (recorded honestly, "
                  f"not fabricated)")
        _write_json(os.path.join(mdir, "3D_DESIGN_STATUS.json"), {
            "artifact": "3D_DESIGN_STATUS",
            "r381_version": R381_VERSION,
            "package_id": pkg_id,
            "classification": classification["classification"],
            "3d_design_status": "BLOCKED_NO_TEMPLATE",
            "reason": reason,
            "classification_basis": classification,
        })
        return {"status": "BLOCKED_NO_TEMPLATE", "classification":
                classification, "files": [], "model_id": None,
                "reason": reason}

    bindings = _record_bindings(pkg_id, tpl, dossier)
    staging = os.path.join(work_dir, "r381_staging", pkg_id)
    os.makedirs(staging, exist_ok=True)

    # ---- base build (staging) ------------------------------------------
    base, base_rec = build_portfolio_model(
        pkg_id, tpl, out_dir=os.path.join(staging, "base"))
    base_valid = ((base or {}).get("geometry_validation") or
                  {}).get("valid")
    if not base_valid:
        # honest BLOCKED: the gates refused the design; reasons ship
        mdir = os.path.join(package_dir, MODEL_DIR)
        os.makedirs(mdir, exist_ok=True)
        gv = (base or {}).get("geometry_validation") or {}
        _write_json(os.path.join(mdir, "3D_DESIGN_STATUS.json"), {
            "artifact": "3D_DESIGN_STATUS",
            "r381_version": R381_VERSION,
            "package_id": pkg_id,
            "classification": classification["classification"],
            "3d_design_status": "BLOCKED_GEOMETRY_INVALID",
            "reason": ("the package-specific parametric design failed "
                       "the deterministic geometry gates at its "
                       "proposed parameter values: " + "; ".join(
                           str(r) for r in (gv.get("reasons") or [])[:5])),
            "classification_basis": classification,
        })
        _write_json(os.path.join(mdir, "GEOMETRY_VALIDATION_REPORT.json"),
                    dict(_sanitize(gv), package_id=pkg_id,
                         build_record=_sanitize(base_rec)))
        return {"status": "BLOCKED_GEOMETRY_INVALID", "classification":
                classification, "files": [], "model_id": None}

    # ---- the improvement loop (staging) ---------------------------------
    loop_record, kept_child = run_improvement_loop(
        pkg_id, tpl, base, out_dir=os.path.join(staging, "mutation"))

    # ---- the FINAL build ships into MODEL/ -------------------------------
    mdir = os.path.join(package_dir, MODEL_DIR)
    os.makedirs(mdir, exist_ok=True)
    if kept_child is not None:
        mut = tpl["mutation"]
        # refresh the DECLARED assembly to the child parameter set BEFORE
        # the rebuild so validation covers what is actually shipped
        final_params = {pid: p.get("value") for pid, p in
                        (base.get("parameter_map") or {}).items()}
        final_params[mut["param_id"]] = mut["new_value"]
        rebuild_base = copy.deepcopy(base)
        rebuild_base["objects"] = _objects_for_params(
            pkg_id, tpl, final_params)
        rebuild_base["interference_pairs"] = _pairs_for_params(
            pkg_id, tpl, final_params)
        final_model, final_rec = rebuild_with_mutation(
            rebuild_base, mut["param_id"], mut["new_value"],
            loop_record["mutation_id"],
            reason=mut.get("limiting_parameter_basis", ""),
            out_dir=mdir)
        final_params = {pid: p.get("value") for pid, p in
                        (final_model.get("parameter_map") or
                         {}).items()}
        final_model["objects"] = _objects_for_params(
            pkg_id, tpl, final_params)
        final_model["interference_pairs"] = _pairs_for_params(
            pkg_id, tpl, final_params)
        _normalize_step_files(final_model)
    else:
        final_model, final_rec = build_portfolio_model(
            pkg_id, tpl, out_dir=mdir)

    # ---- regeneration reproducibility (CEO validation item) -------------
    regen = check_regeneration(
        pkg_id, tpl, final_model,
        staging_dir=os.path.join(staging, "regen"))
    gv = final_model.get("geometry_validation") or {}
    gv.setdefault("checks", {})[
        "G9_regeneration_reproducibility"] = regen
    if regen.get("status") != "REPRODUCIBLE":
        gv["valid"] = False
        gv.setdefault("reasons", []).append(
            "G9 regeneration check: " + str(regen.get("status")) +
            " — " + "; ".join(regen.get("mismatches") or
                                   [regen.get("reason") or ""])[:200])
    final_model["geometry_validation"] = gv

    summary = write_model_dir(
        pkg_id, package_dir, final_model, tpl, classification, bindings,
        loop_record, base, final_rec)
    summary["classification"] = classification
    return summary


def _template_for(pkg_id: str) -> Optional[Dict[str, Any]]:
    """Registry accessor — P-13 (software-only) deliberately has NO
    template; the classifier owns that verdict, this only serves the
    REQUIRED packages."""
    return PORTFOLIO_TEMPLATES.get(pkg_id)
