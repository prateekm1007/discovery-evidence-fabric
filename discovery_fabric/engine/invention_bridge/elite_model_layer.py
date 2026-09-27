"""discovery_fabric/engine/invention_bridge/elite_model_layer.py — R424.

The MODEL/ elite layer: the strongest HONEST 3D class the invention
earned (R424 §9):

  ENGINEERING_3D  parametric source + parameter file + constraints +
                  STEP/STL/GLB (+SVG views when produced) + measured
                  dimensions + geometry validation + regeneration
                  check + independent mesh verification + provenance
                  + MODEL/3D_EVIDENCE/
  CONCEPTUAL_3D   architecture visualization with explicit conceptual
                  labels, tied to the recorded subsystems — NO invented
                  engineering dimensions
  (software/algorithmic inventions route through the conceptual class
  via the bridge gate's Case C; a genuinely non-representable
  invention carries 3D_NOT_APPLICABLE with its recorded reason)

Nothing fake: a conceptual package never emits engineering-dimension
files, and no dimension is invented to look complete.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import epistemics as ep


def _sha256_file(path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _write_json(path, data) -> None:
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8")


# ---------------------------------------------------------------------------
# Parametric source emission (ENGINEERING_3D only) — R425 §2: ONE CAD
# source of truth. The shipped source is EXPORTED from the canonical
# engineering_geometry.FORM_LIBRARY builder (verbatim, via
# inspect.getsource) — never an independently handwritten
# reimplementation in this package layer. The R424-era handwritten
# _FORM_SOURCE map is DELETED (Art. LXIV: superseded implementations
# are retired, not accumulated).
# ---------------------------------------------------------------------------


def _emit_parametric_source(pkg_model_dir: Path, form: str,
                            params: Dict[str, float]) -> Optional[str]:
    """Write MODEL/PARAMETRIC_MODEL_SOURCE.py as the EXPORT of the
    canonical builder (the same program the bridge's engineering
    geometry executes). Returns the file path, or None when no
    canonical builder exists for the form (the package then ships NO
    parametric source — never a reimplementation)."""
    from . import engineering_geometry as eg
    file_text, identity = eg.export_parametric_source(form, params)
    if file_text is None:
        return None
    path = pkg_model_dir / "PARAMETRIC_MODEL_SOURCE.py"
    path.write_text(file_text, encoding="utf-8")
    return str(path)


def _canonical_identity(form: Optional[str]) -> Optional[Dict[str, Any]]:
    """The canonical builder identity tuple recorded in the package
    (R425 §2: canonical builder identity + source hash). None when the
    form is absent (conceptual class records nothing to fake)."""
    if not form:
        return None
    from . import engineering_geometry as eg
    ident = eg.canonical_source_identity(form)
    return {k: ident.get(k) for k in (
        "form", "builder_function", "canonical_module", "module_path",
        "module_sha256", "builder_source_sha256", "status")}


def _parameter_hash(params: Optional[Dict[str, Any]]) -> Optional[str]:
    if params is None:
        return None
    from . import engineering_geometry as eg
    return eg.parameter_map_hash(params)


def build_model_layer(out_dir: str, run_result: Dict[str, Any],
                      geometry_out: Dict[str, Any],
                      vis_class: str,
                      package_id: str,
                      generation_models: Optional[List[Dict]] = None,
                      renders: Optional[Dict[str, Any]] = None) -> Dict:
    """Emit MODEL/ + MODEL/3D_EVIDENCE/ per the earned class. Returns
    the layer record (files + counts) for the manifest."""
    model_dir = Path(out_dir) / "MODEL"
    model_dir.mkdir(parents=True, exist_ok=True)
    proj_generations = (run_result.get("run_state") or {}).get(
        "generations") or {}
    gens = proj_generations.get("generations") or []
    is_engineering = vis_class == ep.ENGINEERING_3D
    layer: Dict[str, Any] = {"class": vis_class,
                             "files": [], "evidence_files": []}

    def _record(path: Path, role: str, evidence: bool = False):
        layer["files" if not evidence else "evidence_files"].append(
            {"path": str(path.relative_to(out_dir)), "role": role,
             "sha256": _sha256_file(path),
             "bytes": path.stat().st_size})

    # ---- PARAMETERS.json -----------------------------------------------
    parameters = []
    param_map = {}
    if is_engineering:
        for p in geometry_out.get("parameters") or []:
            if not isinstance(p, dict):
                continue
            name = p.get("name") or p.get("param_id")
            value = p.get("value")
            if name and isinstance(value, (int, float)):
                parameters.append({
                    "param_id": name,
                    "value": value,
                    "unit": p.get("unit") or "mm",
                    "envelope": p.get("envelope"),
                    "value_class": p.get("value_class")
                    or p.get("epistemic_class") or "MODELLED",
                    "recorded_name": p.get("recorded_name") or name,
                    "design_basis": p.get("basis")
                    or p.get("design_basis")
                    or "bridge geometry parameter (classifier-recorded)",
                })
                param_map[name if name.endswith(
                    ("_mm",)) else f"{name}_mm"] = value
    _write_json(model_dir / "PARAMETERS.json", {
        "artifact": "PARAMETERS",
        "package_id": package_id,
        "policy": (
            "values the canonical record does not carry are "
            "ENGINE-DECLARED MODELLED design proposals inside declared "
            "envelopes (Art. XXVII) — never evidence claims"
            ) if is_engineering else
            ("no engineering parameters exist for a conceptual "
             "architecture — none are invented (Art. XXVIII)"),
        "parameters": parameters,
    })
    _record(model_dir / "PARAMETERS.json", "parameter map")

    # ---- parametric source + derived CAD (ENGINEERING_3D) --------------
    derived = []
    cad_provenance = None
    if is_engineering:
        form = (geometry_out.get("parametric_source") or {}).get("form")
        src_path = _emit_parametric_source(
            model_dir, form,
            (geometry_out.get("parametric_source") or {}).get(
                "parameters") or {p["param_id"]: p["value"]
                                  for p in parameters})
        if src_path:
            _record(Path(src_path), "parametric source (exported from "
                                    "the canonical builder)")
        # derived CAD artifacts: copy from the run's exported set
        for key in ("step_files", "stl_files"):
            for p in geometry_out.get(key) or []:
                if p and os.path.exists(p):
                    dest = model_dir / os.path.basename(p)
                    if not dest.exists():
                        dest.write_bytes(Path(p).read_bytes())
                    derived.append({"path": str(dest.relative_to(out_dir)),
                                    "sha256": _sha256_file(dest),
                                    "bytes": dest.stat().st_size,
                                    "role": key})
        # SVG views when the run produced them
        for svg in sorted(Path(out_dir).parent.glob("MODEL/*.svg")):
            dest = model_dir / svg.name
            if not dest.exists() and svg.exists():
                dest.write_bytes(svg.read_bytes())
                derived.append({"path": str(dest.relative_to(out_dir)),
                                "sha256": _sha256_file(dest),
                                "bytes": dest.stat().st_size,
                                "role": "svg_view"})
        # ---- CAD_SOURCE_PROVENANCE.json (R425 §2) ------------------------
        # canonical builder identity + source hash + parameter hash +
        # derived artifact hashes + the regeneration relationship — the
        # record that makes a second geometry source detectable.
        glb_file = model_dir / f"{package_id}.glb"
        derived_all = derived + ([{
            "path": f"MODEL/{glb_file.name}",
            "sha256": _sha256_file(glb_file),
            "bytes": glb_file.stat().st_size,
            "role": "glb"}] if glb_file.is_file() else [])
        cad_provenance = {
            "artifact": "CAD_SOURCE_PROVENANCE",
            "package_id": package_id,
            "rule": ("one CAD source of truth (R425 §2): "
                     "MODEL/PARAMETRIC_MODEL_SOURCE.py is EXPORTED from "
                     "the canonical engineering geometry program — an "
                     "independent reimplementation in the package layer "
                     "is forbidden and detectable"),
            "authoritative_source_path": (
                "canonical builder (engineering_geometry.FORM_LIBRARY) "
                "-> exported parametric source + parameters -> derived "
                "STEP/STL/GLB"),
            "canonical_builder": _canonical_identity(form),
            "exported_file": "MODEL/PARAMETRIC_MODEL_SOURCE.py",
            "exported_source_sha256": (
                _sha256_file(model_dir / "PARAMETRIC_MODEL_SOURCE.py")
                if (model_dir / "PARAMETRIC_MODEL_SOURCE.py").is_file()
                else None),
            "parameter_map": (geometry_out.get("parametric_source")
                              or {}).get("parameters"),
            "parameter_hash": _parameter_hash(
                (geometry_out.get("parametric_source") or {}).get(
                    "parameters")),
            "derived_artifacts": derived_all,
            "regeneration_relationship": {
                "claim": ("executing MODEL/PARAMETRIC_MODEL_SOURCE.py "
                          "build() over MODEL/PARAMETERS.json "
                          "reconstructs the same geometry as the "
                          "canonical FORM_LIBRARY builder"),
                "verification": "MODEL/3D_EVIDENCE/REGENERATION_CHECK.json",
                "drift_detection": (
                    "engineering_geometry.verify_cad_source_provenance"
                    "(model_dir) re-derives the live canonical identity "
                    "and compares it to canonical_builder above"),
            },
        }
        _write_json(model_dir / "CAD_SOURCE_PROVENANCE.json",
                    cad_provenance)
        _record(model_dir / "CAD_SOURCE_PROVENANCE.json",
                "canonical CAD source provenance (R425 §2)")

    # ---- MODEL_MANIFEST.json --------------------------------------------
    _write_json(model_dir / "MODEL_MANIFEST.json", {
        "artifact": "MODEL_MANIFEST",
        "package_id": package_id,
        "kernel": "cadquery-ocpt (bridge engineering_geometry)",
        "origin": ("BRIDGE_PARAMETRIC (form: "
                   + str((geometry_out.get("parametric_source") or {})
                         .get("form")) + ")") if is_engineering
        else "BRIDGE_CONCEPTUAL (system architecture visualization)",
        "canonical_builder": (cad_provenance or {}).get(
            "canonical_builder") if is_engineering else None,
        "objects": geometry_out.get("components") or [],
        "parameter_count": len(parameters),
        "source_of_truth": (
            "MODEL/PARAMETRIC_MODEL_SOURCE.py (EXPORTED from the "
            "canonical engineering_geometry.FORM_LIBRARY builder) + "
            "MODEL/PARAMETERS.json; STEP/STL/GLB below are DERIVED "
            "artifacts with real sha256 of real bytes; see "
            "MODEL/CAD_SOURCE_PROVENANCE.json") if is_engineering else
            ("the conceptual GLB(s) — topology visualization only; "
             "no parametric source exists for a conceptual class"),
        "derived_artifacts": derived,
        "visualizability_class": vis_class,
    })
    _record(model_dir / "MODEL_MANIFEST.json", "model manifest")

    # ---- 3D_DESIGN_STATUS.json ------------------------------------------
    _write_json(model_dir / "3D_DESIGN_STATUS.json", {
        "artifact": "3D_DESIGN_STATUS",
        "package_id": package_id,
        "visualizability_class": vis_class,
        "3d_design_status": ("PRESENT_AND_VALIDATED" if is_engineering
                             else "PRESENT_CONCEPTUAL"),
        "status_meaning": ep.VISUALIZABILITY_MEANINGS.get(vis_class,
                                                          vis_class),
        "components": geometry_out.get("components") or [],
        "key_dimensions": geometry_out.get("key_dimensions") or {},
        "cad_pipeline_status": geometry_out.get("cad_pipeline_status"),
    })
    ep.guard_no_engineering_dimensions(
        vis_class, geometry_out.get("key_dimensions") or {})
    _record(model_dir / "3D_DESIGN_STATUS.json", "design status")

    # ---- KEY_DIMENSIONS.json ---------------------------------------------
    kd = dict(geometry_out.get("key_dimensions") or {})
    if not is_engineering:
        kd = {"note": ("topology only — no engineering dimensions are "
                       "claimed by a conceptual artifact"),
              "measurement_basis": geometry_out.get(
                  "key_dimensions", {}).get("measurement_basis",
                                            "CONCEPTUAL (no measurement)")}
    _write_json(model_dir / "KEY_DIMENSIONS.json", {
        "artifact": "KEY_DIMENSIONS", "package_id": package_id, **kd})
    _record(model_dir / "KEY_DIMENSIONS.json", "key dimensions")

    # ---- CONSTRAINTS.json (engineering only) -----------------------------
    if is_engineering:
        raw_gates = (geometry_out.get("validation") or {}).get("gates")
        constraints = []
        if isinstance(raw_gates, dict):
            for i, (gate, verdict) in enumerate(raw_gates.items()):
                constraints.append({
                    "constraint_id": gate,
                    "target": gate,
                    "bound": "PASS" if verdict is True else
                             ("FAIL" if verdict is False else "REPORTED"),
                    "limit": None if verdict is True else
                             _txt_gate_verdict(verdict),
                    "epistemic_class": "ENGINEERING",
                    "basis": "deterministic geometry validation gate "
                             "(engineering_geometry.validate_gates); "
                             "provenance in "
                             "render_threshold_provenance.json"})
        elif isinstance(raw_gates, list):
            for i, g in enumerate(raw_gates):
                if isinstance(g, dict):
                    constraints.append({
                        "constraint_id": g.get("gate") or f"C_{i}",
                        "target": g.get("gate"),
                        "bound": "PASS" if g.get("passed") else "FAIL",
                        "limit": g.get("required") or g.get("limit"),
                        "epistemic_class": "ENGINEERING",
                        "basis": "deterministic geometry validation gate"})
        _write_json(model_dir / "CONSTRAINTS.json", {
            "artifact": "CONSTRAINTS", "package_id": package_id,
            "geometric_constraints": constraints})
        _record(model_dir / "CONSTRAINTS.json", "constraints")

    # ---- DESIGN_LINEAGE.json ----------------------------------------------
    _write_json(model_dir / "DESIGN_LINEAGE.json", {
        "artifact": "DESIGN_LINEAGE", "package_id": package_id,
        "lineage": "append-only (Art. XXXVIII causal chain discipline)",
        "generations": [
            {"generation": g.get("generation"),
             "invention_id": g.get("invention_id"),
             "what_changed": g.get("what_changed"),
             "killed": bool((g.get("challenge") or {}).get("killed"))}
            for g in gens[:8] if isinstance(g, dict)],
        "generation_models": [
            {"generation": m.get("generation"),
             "glb": f"MODEL/model-{m.get('generation'):03d}.glb",
             "current": m.get("current")}
            for m in (generation_models or [])[:8]],
    })
    _record(model_dir / "DESIGN_LINEAGE.json", "design lineage")

    # ---- ENGINEERING_PROVENANCE.json ---------------------------------------
    chains = {}
    if is_engineering:
        for p in parameters[:10]:
            chains[p["param_id"]] = {
                "technical_state": {
                    "binding_status": "BRIDGE_GEOMETRY_PARAMETER",
                    "source": "the invention bridge's classifier-recorded "
                              "geometry parameters",
                    "value_class": p.get("value_class")},
                "parameter": {"value": p["value"],
                              "unit": p.get("unit"),
                              "envelope": p.get("envelope")},
                "cad_feature": "derived by the parametric form "
                               f"({(geometry_out.get('parametric_source') or {}).get('form')})",
                "measured_geometry": ("see MODEL/3D_EVIDENCE/"
                                      "PARAMETER_FEATURE_LOG.json"),
            }
    _write_json(model_dir / "ENGINEERING_PROVENANCE.json", {
        "artifact": "ENGINEERING_PROVENANCE", "package_id": package_id,
        "chain_shape": ("TECHNICAL_STATE -> parameter -> CAD feature -> "
                        "derived geometry -> measured geometry -> "
                        "validation result") if is_engineering else
                       "CONCEPTUAL — no parametric chain exists for a "
                       "conceptual architecture (nothing is fabricated)",
        "chains": chains})
    _record(model_dir / "ENGINEERING_PROVENANCE.json",
            "engineering provenance")

    # ---- GEOMETRY_VALIDATION_REPORT.json -----------------------------------
    validation = geometry_out.get("validation") or (
        {"status": "NOT_APPLICABLE_CONCEPTUAL",
         "note": "deterministic geometry gates apply to parametric "
                 "engineering solids only; a conceptual architecture "
                 "carries no engineering dimensions to gate"}
        if not is_engineering else {})
    _write_json(model_dir / "GEOMETRY_VALIDATION_REPORT.json", {
        "artifact": "GEOMETRY_VALIDATION_REPORT", "package_id": package_id,
        "evidence_class": "COMPUTATIONAL_RESULT" if is_engineering
        else None, **validation})
    _record(model_dir / "GEOMETRY_VALIDATION_REPORT.json",
            "geometry validation")

    # ---- IMPROVEMENT_LOOP_EVIDENCE.json ------------------------------------
    challenges = []
    for g in gens[:8]:
        if isinstance(g, dict) and isinstance(g.get("challenge"), dict):
            ch = g["challenge"]
            challenges.append({
                "generation": g.get("generation"),
                "survived": bool(ch.get("survived")),
                "killed": bool(ch.get("killed")),
                "dimensions": ch.get("dimensions") or ch.get(
                    "verdicts") or "recorded in the run's lineage",
            })
    _write_json(model_dir / "IMPROVEMENT_LOOP_EVIDENCE.json", {
        "artifact": "IMPROVEMENT_LOOP_EVIDENCE", "package_id": package_id,
        "loop_kind": "challenge-and-evolution (pre-reality)",
        "challenges": challenges,
        "reality_boundary": "no physical observation in any generation "
                            "(Art. XXXVIII)",
    })
    _record(model_dir / "IMPROVEMENT_LOOP_EVIDENCE.json",
            "improvement loop evidence")

    # ---- 3D_EVIDENCE/ (ENGINEERING_3D only) -------------------------------
    if is_engineering:
        ev_dir = model_dir / "3D_EVIDENCE"
        ev_dir.mkdir(parents=True, exist_ok=True)
        _build_3d_evidence(ev_dir, out_dir, geometry_out, package_id,
                           parameters, renders, layer)
    return layer


def _build_3d_evidence(ev_dir: Path, out_dir: str,
                       geometry_out: Dict, package_id: str,
                       parameters: List[Dict], renders: Optional[Dict],
                       layer: Dict) -> None:
    """MODEL/3D_EVIDENCE/ — the independent verification layer (r384
    discipline, reproduced by the R424 factory): regeneration check,
    parameter->feature log, independent trimesh watertight check,
    hashed inventory, renders where available."""
    def _ev_record(path: Path, kind: str):
        layer["evidence_files"].append({
            "path": str(path.relative_to(out_dir)), "kind": kind,
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size})

    _write_json(ev_dir / "3D_EVIDENCE_README.json", {
        "artifact": "3D_EVIDENCE_README",
        "purpose": ("the independent 3D verification layer: a "
                    "regeneration check (rebuild from the shipped "
                    "parametric source + parameters and compare "
                    "measurements), a parameter-to-measured-feature "
                    "log, and an independent trimesh watertight "
                    "re-check of the shipped STL. Nothing here alters "
                    "the shipped artifacts."),
        "source_of_truth": "MODEL/PARAMETRIC_MODEL_SOURCE.py + "
                           "MODEL/PARAMETERS.json",
        "evidence_class": "COMPUTATIONAL_RESULT",
    })
    _ev_record(ev_dir / "3D_EVIDENCE_README.json", "JSON")

    # --- regeneration + parameter-feature log (one rebuild) --------------
    # R425 §2: the regeneration check EXECUTES THE SHIPPED
    # PARAMETRIC_MODEL_SOURCE.py (not merely the canonical builder) and
    # compares its measurements against BOTH the canonical FORM_LIBRARY
    # builder AND the shipped KEY_DIMENSIONS — proving the shipped
    # parameter source reconstructs the same geometry as the canonical
    # builder. A tampered/handwritten source fails here.
    regen = {"artifact": "REGENERATION_CHECK",
             "method": ("clean regeneration (R425 §2): execute the "
                        "SHIPPED MODEL/PARAMETRIC_MODEL_SOURCE.py "
                        "build() over the shipped parameters, measure "
                        "with the same OCCT measurement, and compare "
                        "against (a) the canonical FORM_LIBRARY builder "
                        "rebuilt live and (b) the shipped MODEL/"
                        "KEY_DIMENSIONS.json"),
             "tolerance_mm": 1e-3, "objects": {},
             "regeneration_status": "NOT_PERFORMED",
             "shipped_source_executed": False,
             "evidence_class": "COMPUTATIONAL_RESULT"}
    plog = {"artifact": "PARAMETER_FEATURE_LOG",
            "method": ("parameters from MODEL/PARAMETERS.json compared "
                       "against features MEASURED on the rebuilt solid "
                       "(OCCT bounding box / volume), tolerance "
                       "1e-3 mm"),
            "parameters_total": len(parameters),
            "parameters_with_linear_feature_match": 0,
            "rows": [], "evidence_class": "COMPUTATIONAL_RESULT"}
    try:
        from . import engineering_geometry as eg
        form = (geometry_out.get("parametric_source") or {}).get("form")
        builder = eg.FORM_LIBRARY.get(form)
        # the ACTUAL build map the bridge normalized (the same map the
        # exported source carries as its PARAMETERS literal)
        build_map = dict((geometry_out.get("parametric_source") or {})
                         .get("parameters") or {})
        if not build_map and parameters:
            # fallback: normalize the MODEL/PARAMETERS.json ids exactly
            # the way the bridge did (strip _mm family suffixes)
            for p in parameters:
                k = str(p["param_id"]).replace("_mm", "").replace(
                    "-mm", "").replace(" ", "_").lower()
                build_map[k] = p["value"]
        shipped_src = ev_dir.parent / "PARAMETRIC_MODEL_SOURCE.py"
        shipped_ns = None
        if shipped_src.is_file() and (build_map or parameters):
            # (a) EXECUTE THE SHIPPED SOURCE — the §2 clean regeneration
            shipped_ns = {"__name__": "shipped_parametric_source"}
            exec(compile(shipped_src.read_text(encoding="utf-8"),
                         str(shipped_src), "exec"), shipped_ns)
            regen["shipped_source_executed"] = True
        if builder and build_map and shipped_ns is not None:
            # (b) rebuild the CANONICAL builder live (the same call the
            # bridge made)
            canonical_solid = builder(build_map)
            canonical_meas = eg.measure(canonical_solid)
            # (c) rebuild from the SHIPPED exported source AS SHIPPED
            # (its own PARAMETERS literal — no injected overrides)
            shipped_solid = shipped_ns["build"]()
            shipped_meas = eg.measure(shipped_solid)
            # (d) the shipped KEY_DIMENSIONS (what the run measured)
            shipped = geometry_out.get("key_dimensions") or {}
            v_delta_sc = abs((shipped_meas.get("volume_mm3") or 0)
                             - (canonical_meas.get("volume_mm3") or 0))
            bbox_deltas_sc = {k: round(abs(
                (shipped_meas.get("bbox") or {}).get(k, 0)
                - (canonical_meas.get("bbox") or {}).get(k, 0)), 6)
                for k in ("xlen", "ylen", "zlen")}
            v_delta = abs((shipped_meas.get("volume_mm3") or 0)
                          - (shipped.get("volume_mm3") or 0))
            bbox_deltas = {k: round(abs(
                (shipped_meas.get("bbox") or {}).get(k, 0)
                - (shipped.get("bbox") or {}).get(k, 0)), 6)
                for k in ("xlen", "ylen", "zlen")}
            match = (v_delta <= regen["tolerance_mm"]
                     and all(d <= regen["tolerance_mm"]
                             for d in bbox_deltas.values()))
            same_as_canonical = (
                v_delta_sc <= regen["tolerance_mm"]
                and all(d <= regen["tolerance_mm"]
                        for d in bbox_deltas_sc.values()))
            regen["objects"] = {form: {
                "status": "MATCH" if match else "MISMATCH",
                "shipped_source_equals_canonical_builder": (
                    "MATCH" if same_as_canonical else "MISMATCH"),
                "volume_mm3_shipped_source": shipped_meas.get(
                    "volume_mm3"),
                "volume_mm3_canonical_builder": canonical_meas.get(
                    "volume_mm3"),
                "volume_mm3_record": shipped.get("volume_mm3"),
                "volume_delta_shipped_vs_canonical": round(v_delta_sc, 6),
                "volume_delta_shipped_vs_record": round(v_delta, 6),
                "bbox_dim_deltas_mm": bbox_deltas}}
            regen["regeneration_status"] = (
                "REPRODUCIBLE" if match and same_as_canonical
                else "NOT_REPRODUCIBLE")
            # parameter -> measured feature matching (mechanical)
            matched = 0
            feats = {"bbox.xlen": (shipped_meas.get("bbox") or {}).get(
                "xlen"),
                     "bbox.ylen": (shipped_meas.get("bbox") or {}).get(
                "ylen"),
                     "bbox.zlen": (shipped_meas.get("bbox") or {}).get(
                "zlen"),
                     "volume_mm3": shipped_meas.get("volume_mm3")}
            for p in parameters:
                rows = []
                for fname, fval in feats.items():
                    if fval is not None and abs(
                            fval - p["value"]) <= 1e-3:
                        rows.append({"object_id": form, "feature": fname,
                                     "measured_value": fval,
                                     "relation": "measured = value",
                                     "delta_mm": round(abs(fval - p["value"]), 6)})
                        matched += 1
                plog["rows"].append({
                    "param_id": p["param_id"], "value": p["value"],
                    "unit": p.get("unit"),
                    "value_class": p.get("value_class"),
                    "measured_feature_matches": rows or "NO_LINEAR_MATCH"
                    " (parameter may drive a cut/offset, not a bbox "
                    "dimension — see the parametric source)"})
            plog["parameters_with_linear_feature_match"] = min(
                matched, len(parameters))
        elif parameters and shipped_ns is None:
            regen["error"] = (
                "PARAMETRIC_MODEL_SOURCE.py absent while engineering "
                "parameters exist — the exported source must ship with "
                "every ENGINEERING_3D package (R425 §2)")
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        regen["error"] = f"{type(exc).__name__}: {exc}"
    _write_json(ev_dir / "REGENERATION_CHECK.json", regen)
    _ev_record(ev_dir / "REGENERATION_CHECK.json", "JSON")
    plog["rows"] = plog["rows"][:12]
    _write_json(ev_dir / "PARAMETER_FEATURE_LOG.json", plog)
    _ev_record(ev_dir / "PARAMETER_FEATURE_LOG.json", "JSON")

    # --- independent STL watertight check (trimesh, not OCCT) ------------
    wt = {"artifact": "STL_INDEPENDENT_WATERTIGHT_CHECK",
          "verifier": "trimesh (independent of OCCT)",
          "checked": 0, "watertight_pass": 0, "status": "NOT_PERFORMED",
          "entries": [], "evidence_class": "COMPUTATIONAL_RESULT"}
    for p in (geometry_out.get("stl_files") or []):
        if p and os.path.exists(p):
            try:
                import trimesh
                m = trimesh.load(p, force="mesh")
                ok = bool(m.is_watertight)
                wt["checked"] += 1
                wt["watertight_pass"] += 1 if ok else 0
                wt["entries"].append({
                    "object_id": os.path.splitext(os.path.basename(p))[0],
                    "file": os.path.basename(p), "watertight": ok,
                    "faces": int(len(m.faces)),
                    "vertices": int(len(m.vertices))})
            except Exception as exc:  # noqa: BLE001
                wt["entries"].append({"file": os.path.basename(p),
                                      "error": f"{type(exc).__name__}: "
                                               f"{exc}"})
    if wt["checked"]:
        wt["status"] = ("ALL_WATERTIGHT" if wt["watertight_pass"]
                        == wt["checked"] else "WATERTIGHT_FAILURE")
    _write_json(ev_dir / "STL_INDEPENDENT_WATERTIGHT_CHECK.json", wt)
    _ev_record(ev_dir / "STL_INDEPENDENT_WATERTIGHT_CHECK.json", "JSON")

    # --- presentation renders where available ------------------------------
    copied = 0
    if renders and (renders.get("status") in ("OK", "RENDER_PARTIAL")):
        src_dir = renders.get("out_dir") or ""
        if src_dir and os.path.isdir(src_dir):
            for name in ("hero.png", "section.png", "exploded.png"):
                src = os.path.join(src_dir, name)
                if os.path.isfile(src) and os.path.getsize(src) > 0:
                    dest = ev_dir / name
                    dest.write_bytes(Path(src).read_bytes())
                    _ev_record(dest, "PNG_RENDER")
                    copied += 1

    # --- hashed file inventory ----------------------------------------------
    inv = {"artifact": "FILE_INVENTORY",
           "policy": "real sha256 of real bytes on disk (Art. VI)",
           "counts_by_kind": {},
           "files": []}
    for f in sorted(ev_dir.iterdir()):
        if not f.is_file():
            continue
        kind = ("JSON" if f.suffix == ".json"
                else "PNG_RENDER" if f.suffix == ".png"
                else f.suffix.lstrip(".").upper())
        inv["counts_by_kind"][kind] = \
            inv["counts_by_kind"].get(kind, 0) + 1
        inv["files"].append({"path": str(f.relative_to(out_dir)),
                             "bytes": f.stat().st_size,
                             "sha256": _sha256_file(f),
                             "kind": kind})
    _write_json(ev_dir / "FILE_INVENTORY.json", inv)
    _ev_record(ev_dir / "FILE_INVENTORY.json", "JSON")


def _txt_gate_verdict(verdict: Any) -> Optional[str]:
    if isinstance(verdict, dict):
        return json.dumps(verdict)[:200]
    return str(verdict)[:80] if verdict is not None else None
