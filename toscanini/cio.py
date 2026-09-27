"""toscanini/cio.py — R414: the Canonical Invention Object (CIO).

Operator directive (product integration, sections 12-14, 16):
  The browser NEVER assembles an invention from separate API calls —
  it receives ONE object and renders it. One source of truth:

      Discovery Engine -> Canonical Invention Object
                      -> Website / PDF / 3D / ZIP / STEP / STL

  The reality status beside every invention (DESIGNED / SIMULATED /
  EVIDENCE-SUPPORTED / EXPERIMENTALLY VERIFIED) is NOT a frontend
  badge: these are FIELDS of the CIO, derived from what the run's own
  artifacts actually establish (Art. XXXVIII Reality Boundary, Art.
  LIII promotion ladder — no state may skip a level).

  Toscanini is not a patent court: the CIO carries the legal position
  copy and the builder REJECTS patentability language (§3 — the words
  "patentable", "legally novel", "patent guaranteed", "patent
  cleared", "FTO confirmed" may never appear unless explicitly
  counsel-derived, which this machine never claims).

Constitutional contract: every field is PROJECted from a persisted
run artifact (INVENTION_SPECIFICATION, PARAMETRIC_MODEL, MODEL/,
PHYSICS envelope, evidence pack, package manifests). Absent artifact
-> honest false/None (Art. VI, XXV). Nothing here grants epistemic
authority to LLM output (Art. XVIII).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Language guard (directive §3 — not a patent court)
# ---------------------------------------------------------------------------
BANNED_PHRASES = (
    "patentable", "legally novel", "patent guaranteed",
    "patent cleared", "fto confirmed", "patent valid",
    "legally protect", "patent approved", "guaranteed patent",
)
LEGAL_POSITION = (
    "Toscanini performs technology discovery — technical prior-art "
    "search, mechanism analysis, and evidence-grounded invention "
    "hypotheses. It does NOT determine legal patentability or freedom "
    "to operate. Patent counsel should conduct formal patentability "
    "and FTO analysis."
)
PREFERRED_NOVELTY_LANGUAGE = (
    "No materially similar mechanism identified in the searched "
    "evidence. Potential IP territory — formal legal review required."
)


def language_guard(text: str) -> Dict[str, Any]:
    """Scan generated copy for banned patentability words (directive
    §3). Returns {clean, violations} — the caller must refuse to ship
    text with violations rather than silently editing it."""
    t = (text or "").lower()
    violations = [p for p in BANNED_PHRASES if p in t]
    return {"clean": not violations, "violations": violations}


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _unwrap(field: Any) -> Any:
    """The invention spec wraps narrative fields as {value: X,
    epistemic_class, ...} — unwrap to the value (the wrapper's own
    epistemic_class is preserved separately where it matters)."""
    if isinstance(field, dict) and "value" in field and set(
            field.keys()) <= {"value", "epistemic_class", "origin_stage",
                              "evidence_ids", "note", "source_span",
                              "provenance"}:
        return field.get("value")
    return field


def _package_info(run_dir: Path) -> Dict[str, Any]:
    """Package presence from the run's own PACKAGE_REPORT + DOWNLOAD
    dir (the same derivation the session store uses — never from the
    session index, which may lag the worker).

    R418: when the buyer package was not produced (the honest pre-bridge
    state for evolution-survivor runs), the BRIDGE technology package
    (TECHNOLOGY_PACKAGE_*.zip, recorded in BRIDGE_REPORT.json) is the
    package the user receives — labeled with its own honest maturity and
    package_kind. A bridge package NEVER claims buyer-release posture
    (Art. IV: distinct artifact classes, never a weakened gate)."""
    report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
    zips = sorted((run_dir / "DOWNLOAD").glob("*.zip")) \
        if (run_dir / "DOWNLOAD").exists() else []
    complete = bool(report.get("complete") and zips)
    if complete:
        return {"complete": True, "maturity": report.get("maturity"),
                "zip_name": zips[0].name if zips else None,
                "package_kind": "TECHNOLOGY_TRANSFER_PACKAGE",
                "package_origin": "BUYER_RELEASE_CHAIN",
                "zip_path": str(zips[0]) if zips else None}
    # bridge fallback (R418)
    bridge = _bridge_package_info(run_dir)
    if bridge:
        return bridge
    return {"complete": False, "maturity": None, "zip_name": None,
            "package_kind": None, "zip_path": None,
            "package_origin": None}


def _bridge_package_info(run_dir: Path) -> Optional[Dict[str, Any]]:
    """The bridge technology transfer package, derived from
    BRIDGE_REPORT.json + the package ZIP on disk (the report is the
    record; the file is the artifact — both must agree). R423A Phase 3:
    both the historical TECHNOLOGY_PACKAGE_*.zip name and the current
    TECHNOLOGY_TRANSFER_PACKAGE_*.zip name resolve — historical run
    artifacts are never rewritten, new runs use the one canonical
    artifact name."""
    br = _read_json(run_dir / "BRIDGE_REPORT.json") or {}
    pkg = br.get("package_out") or {}
    zip_name = pkg.get("zip_name")
    zp = None
    if zip_name:
        zp = run_dir / zip_name
        if not zp.exists():
            zp = None
    if zp is None:
        # the report's name is stale or absent — resolve from disk by
        # BOTH naming generations (historical first, current second)
        for pattern in ("TECHNOLOGY_PACKAGE_*.zip",
                        "TECHNOLOGY_TRANSFER_PACKAGE_*.zip"):
            found = sorted(run_dir.glob(pattern))
            if found:
                zp = found[0]
                break
    if zp is None or not zp.exists():
        return None
    return {
        "complete": True,
        "maturity": pkg.get("package_maturity"),
        "zip_name": zp.name,
        "package_kind": "TECHNOLOGY_TRANSFER_PACKAGE",
        "package_origin": "INVENTION_BRIDGE",
        "zip_path": str(zp),
        "visualizability_class": pkg.get("visualizability_class"),
        "zip_sha256": pkg.get("zip_sha256"),
        "document_count": pkg.get("manifest_files"),
    }


def _package_document_count(run_dir: Path,
                            package: Dict[str, Any]) -> Optional[int]:
    """R422 (directive 3): the honest document count for the Downloads
    block — from the package's own records, never hardcoded. Bridge: the
    manifest file_count recorded in BRIDGE_REPORT. Buyer: the manifest
    inside the DOWNLOAD tree (MANIFEST.json carries file_count)."""
    try:
        if package.get("package_origin") == "BUYER_RELEASE_CHAIN":
            dl = run_dir / "DOWNLOAD"
            if dl.is_dir():
                m = _read_json(dl / "MANIFEST.json")
                if m and isinstance(m.get("file_count"), int):
                    return m["file_count"]
                return sum(1 for _ in dl.rglob("*"))
        count = package.get("document_count")
        if isinstance(count, int):
            return count
        # fall back to the bridge report's own count (the record)
        br = _read_json(run_dir / "BRIDGE_REPORT.json") or {}
        count = (br.get("package_out") or {}).get("manifest_files")
        return count if isinstance(count, int) else None
    except Exception:  # noqa: BLE001 — count stays absent, never guessed
        return None


def _compact_scores(scores: Optional[Dict[str, Any]]
                    ) -> Optional[Dict[str, Any]]:
    """R433 section 13 — the three SEPARATED score dimensions, each an
    independent record; deliberately NO combined number. The full check
    tables stay in the run record (BRIDGE_REPORT.json); the browser
    gets the dimensions, their failures, and NOT VISUALIZED."""
    if not scores:
        return None

    def _dim(key: str) -> Dict[str, Any]:
        d = (scores.get(key) or {}) if isinstance(scores, dict) else {}
        return {
            "score": d.get("score"),
            "passed": d.get("passed"),
            "failures": d.get("failures") or [],
        }

    return {
        "semantic_identity": _dim("semantic_identity"),
        "engineering_coherence": _dim("engineering_coherence"),
        "presentation_quality": _dim("presentation_quality"),
        "not_visualized": ((scores.get("semantic_identity") or {})
                           .get("not_visualized") or []),
        "note": ("three separated dimensions — never combined into one "
                 "score (R433 section 13)"),
    }


def _bridge_why(bridge_report: Dict[str, Any]) -> Optional[str]:
    """R418 (operator §4): when the artifact pane shows an unavailable
    state, the backend must answer WHY — the recorded reason from the
    bridge's own report (never a blanket sentence, never invented)."""
    outcome = bridge_report.get("outcome")
    if not outcome or outcome in ("COMPLETED", "ALREADY_COMPLETE",
                                  "PACKAGE_ADDED_TO_EXISTING_GEOMETRY",
                                  "CONCEPTUAL_FALLBACK"):
        return None
    if outcome == "NO_INVENTION":
        return ("no invention-side artifacts were recorded on this run — "
                "the bridge generates nothing (honest absence)")
    if outcome == "NO_SURVIVOR":
        # R455-LEAN-1 §1: the run's own release record attests no
        # surviving, promoted candidate — one honest record, no
        # artifacts (historical NO_INVENTION records stay readable).
        return ("this run recorded no surviving, promoted candidate — "
                "the bridge generates nothing (honest absence)")
    report = bridge_report.get("report") or {}
    steps = report.get("steps") or []
    geom = next((s for s in steps if s.get("step") == "GEOMETRY"), {})
    attempts = (geom.get("detail") or {}).get("attempts") or []
    why = "; ".join(
        f"{a.get('failure_class') or 'ATTEMPT'}: "
        f"{str(a.get('diagnosis') or a.get('error') or 'no detail')[:160]}"
        for a in attempts if a.get("status") != "OK") or \
        str(bridge_report.get("error") or
            bridge_report.get("note") or "no recorded attempt detail")
    return f"bridge outcome {outcome}: {why}"[:600]


def _sha_file(p: Path) -> Optional[str]:
    try:
        if p.exists() and p.is_file():
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
    except Exception:  # noqa: BLE001
        return None
    return None


def _geometry_file_route(session_id: str, f: Path) -> str:
    """The API route the UI uses to fetch one GEOMETRY file. The server
    restricts this route to engineering-geometry extensions (glb/step/
    stl/svg) — never envelopes or internal records."""
    return f"/api/run/{session_id}/geometry/{f.name}"


# ---------------------------------------------------------------------------
# The CIO builder
# ---------------------------------------------------------------------------
def _domain_summary(eng: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """R443: the canonical domain identity, consumed from the
    engineering specification (one authority — never re-derived here)."""
    if not eng:
        return None
    wd = eng.get("why_this_domain") or {}
    app = eng.get("applicability") or {}
    return {
        "domain": wd.get("domain") or eng.get("technology_domain"),
        "label": wd.get("label"),
        "basis": wd.get("basis"),
        "selection_basis": wd.get("selection_basis"),
        "source_refs": ["engineering_specification.why_this_domain"],
    }


def _applicability_summary(
        eng: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """R443: the canonical problem-context applicability state, consumed
    from the engineering specification (one authority). The CIO, the
    website and the package documents speak THIS decision."""
    if not eng:
        return None
    app = eng.get("applicability") or {}
    if not app:
        return None
    return {
        "context_class": app.get("context_class"),
        "basis": app.get("basis"),
        "score": app.get("score"),
        "buyer_type": ((app.get("requirements") or {}).get(
            "buyer_type") or {}).get("statement"),
        "regulatory": ((app.get("requirements") or {}).get(
            "regulatory") or {}).get("statement"),
        "source_refs": ["engineering_specification.applicability"],
    }


def build_cio(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build the Canonical Invention Object for one session. Returns
    None when the run has no invention-side artifacts yet (honest: no
    invention -> no CIO; the UI shows the run-state, never a fabricated
    invention object)."""
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if not run_dir or not run_dir.exists():
        return None

    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json")
    eng = _read_json(run_dir / "ENGINEERING_SPECIFICATION.json")
    pm = _read_json(run_dir / "PARAMETRIC_MODEL.json")
    cad_ledger = _read_json(run_dir / "CAD_PIPELINE_LEDGER.json")
    dex = _read_json(run_dir / "DECISIVE_EXPERIMENT.json")
    final_state = _read_json(run_dir / "final_state.json")
    phys_env = _read_json(run_dir / "envelope_PHYSICS.json")
    physics = (phys_env or {}).get("physics") or {}

    # no invention-side artifacts anywhere -> no CIO (directive §12: the
    # frontend renders the CIO; an empty object would still LOOK like an
    # invention surface — honest absence instead, Art. XXV).
    #
    # R455-LEAN-1 §1: `final_state.json` is the RUN's state record, not
    # invention-side state — EVERY engine run writes one, so counting it
    # here made the CIO exist (and with it `_invention_exists`) for a
    # run that produced no invention at all (the audit's measured
    # failure: 18/18 production runs bridged, 7 of them with
    # `invention_id: null`). The run-state record is still READ below
    # (identity hash); it just no longer MANUFACTURES invention
    # presence (Art. XXVIII: no silent semantic promotion).
    if not any((inv, eng, pm, cad_ledger, dex)):
        return None

    # geometry: MODEL/ dir (package path) or STEP/STL in the run dir
    model_dir = run_dir / "MODEL"
    glb = sorted(model_dir.glob("*.glb")) if model_dir.exists() else []
    step = sorted(run_dir.glob("*.step")) + \
        sorted(model_dir.glob("*.step")) if model_dir.exists() \
        else sorted(run_dir.glob("*.step"))
    stl = sorted(run_dir.glob("*.stl")) + \
        sorted(model_dir.glob("*.stl")) if model_dir.exists() \
        else sorted(run_dir.glob("*.stl"))
    svg_views = sorted(model_dir.glob("*.svg")) if model_dir.exists() \
        else []

    has_geometry = bool(glb or step or pm)

    # R418: the geometry CLASS — engineering (parametric CAD authority)
    # vs conceptual (bridge system/conceptual architecture) — derived
    # from the run's own records, never inferred from the GLB's
    # existence (Art. XXVIII: a conceptual model never silently
    # presents as engineering geometry).
    bridge_report = _read_json(run_dir / "BRIDGE_REPORT.json") or {}
    _br_vis = bridge_report.get("visualizability_class") or \
        ((bridge_report.get("geometry") or {}).get("visualizability_class"))
    # the gate-persisted geometry block (R432/R433 fields render from
    # here verbatim — the CIO is a projection, never a re-derivation)
    _br_geo = bridge_report.get("geometry") or {}
    if pm or (cad_ledger or {}).get("status") == "COMPLETED" and glb:
        geometry_class = "ENGINEERING_3D"
    elif _br_vis:
        geometry_class = _br_vis
    elif glb:
        geometry_class = "ENGINEERING_3D"
    else:
        geometry_class = None
    geometry_is_conceptual = geometry_class in (
        "SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D")

    # R419 (sections 5-6/16-17): the presentation render artifacts —
    # derived from the MODEL/3D/ directory itself (the files are the
    # authority, Art. X; render_record.json carries the provenance).
    # The frontend gallery and the ZIP carry the SAME files.
    render_dir = model_dir / "3D" if model_dir.exists() else None
    render_record = _read_json(render_dir / "render_record.json") \
        if render_dir and (render_dir / "render_record.json").exists() \
        else None
    renders: Dict[str, Any] = {}
    if render_dir and render_dir.exists():
        sid = session.get("session_id")
        present = {str(p.relative_to(render_dir))
                   for p in render_dir.rglob("*")
                   if p.is_file() and p.stat().st_size > 0}
        # R441: the full visual set (poster / dimension / orthographic /
        # turntable join hero / section / exploded); turntable frames are
        # projected as a count + first-frame URL (the gallery animates
        # client-side without twelve endpoints)
        # the artifact set is judged by the RECORD'S OWN era: a legacy
        # BLENDER_HEADLESS record against the legacy six, an R441
        # Visual Compiler record against the full visual set (no
        # silent contract drift between eras, Art. XI)
        legacy_pipeline = ((render_record or {}).get("render_pipeline")
                           == "BLENDER_HEADLESS")
        names = ("hero.png", "hero.glb", "section.png",
                 "exploded.png", "exploded.glb", "poster.png",
                 "dimension.png") \
            if not legacy_pipeline else \
            ("hero.png", "hero.glb", "section.png", "section.glb",
             "exploded.png", "exploded.glb")
        available = [n for n in names if n in present]
        ortho = sorted(n for n in present
                       if n.startswith("orthographic/"))
        turntable = sorted(n for n in present
                           if n.startswith("turntable/"))
        gate_record = _read_json(render_dir / "visual_gate.json") \
            if (render_dir / "visual_gate.json").exists() else None
        if available or render_record:
            renders = {
                "status": (render_record or {}).get("status",
                                                    "OK" if available
                                                    else "UNKNOWN"),
                "pipeline": (render_record or {}).get(
                    "render_pipeline", "VISUAL_COMPILER_HEADLESS_THREE"),
                "renderer_stack": (render_record or {}).get(
                    "renderer_stack"),
                "is_conceptual": geometry_is_conceptual,
                "missing": [n for n in names if n not in present],
                "presentation_rule": (
                    "presentation renders — the authoritative geometry is "
                    "the CadQuery/OCCT GLB; the visual set is the R441 "
                    "Visual Compiler output (same renderer family as this "
                    "website), gate-approved per Article LXXII"),
            }
            for n in available:
                key = n.replace(".", "_").replace("/", "_")
                renders[key] = f"/api/run/{sid}/render/{n}"
            if ortho:
                renders["orthographic"] = {
                    n.split("/")[1].replace(".png", ""):
                        f"/api/run/{sid}/render/{n}" for n in ortho}
            if turntable:
                renders["turntable_frame_count"] = len(turntable)
                renders["turntable_first"] = \
                    f"/api/run/{sid}/render/{turntable[0]}"
            # THE ARTICLE LXXII VERDICT, surfaced to the product: the
            # hero the buyer sees is the hero the gate approved
            if gate_record:
                renders["visual_gate"] = {
                    "verdict": gate_record.get("verdict"),
                    "hero_suppressed": gate_record.get("hero_suppressed"),
                    "failed_rules": gate_record.get("failed_rules", []),
                }
            if (render_record or {}).get("renderer_stack"):
                renders["renderer_stack"] = render_record["renderer_stack"]
            # legacy records (BLENDER_HEADLESS) carry the pinned build —
            # the projection discloses what the RECORD claims, never a
            # guessed engine (Art. VI)
            if (render_record or {}).get("blender_version"):
                renders["pinned_blender"] = \
                    render_record["blender_version"]
            if (render_record or {}).get("source_glb_sha256"):
                renders["source_glb_sha256"] = \
                    render_record["source_glb_sha256"]
            # R420 quality disclosure: the achieved render parameters are
            # projected (a degraded-quality attempt from the async
            # ladder is DISCLOSED, never passed off as full quality)
            # quality disclosure: the achieved parameters the record
            # itself carries are projected (a degraded-quality attempt
            # from the async ladder is DISCLOSED, never passed off as
            # full quality); samples exist only in legacy records
            # (rasterization has no Cycles samples — R441)
            if (render_record or {}).get("samples") is not None:
                renders["samples"] = render_record.get("samples")
            if (render_record or {}).get("resolution") is not None:
                renders["resolution"] = render_record.get("resolution")
    # R420 §1/§3: the async render job's own state, surfaced honestly
    # when the render artifacts are not (yet) on disk. Presentation
    # state ONLY — this changes no maturity/class field (operator §2;
    # a pending or skipped render is never a scientific statement).
    if not renders:
        job = _read_json(render_dir / "RENDER_JOB.json") \
            if render_dir and (render_dir / "RENDER_JOB.json").exists() \
            else None
        if job:
            status = job.get("status")
            note = None
            if status in ("RUNNING", "INTERRUPTED"):
                surface = "RENDERING" if status == "RUNNING" else status
                note = ("studio renders are being prepared — the async "
                        "render job is finishing this run's presentation "
                        "artifacts automatically")
            else:
                surface = status
            renders = {
                "status": surface,
                "pipeline": job.get("pipeline", "BLENDER_HEADLESS"),
                "is_conceptual": geometry_is_conceptual,
                "missing": ["hero.png", "hero.glb", "section.png",
                            "section.glb", "exploded.png", "exploded.glb"],
                "presentation_rule": (
                    "presentation renders — the authoritative geometry is "
                    "the CadQuery/OCCT GLB; renders are enhancements, "
                    "never the contract"),
            }
            if note:
                renders["note"] = note
            if job.get("enqueued_by"):
                renders["enqueued_by"] = job.get("enqueued_by")

    final = (session.get("final_status") or "").upper()
    survivor = final == "AUTOMATED_INVENTION_CANDIDATE" or bool(inv)

    # evidence classes (from the invention spec's own evidence index,
    # unwrapped from its {value: [...]} envelope)
    evidence = _unwrap((inv or {}).get("evidence")) or []
    if isinstance(evidence, dict):
        evidence = evidence.get("records") or []
    ev_classes: List[str] = []
    for e in evidence:
        if isinstance(e, dict):
            c = e.get("evidence_class") or e.get("epistemic_class")
            if isinstance(c, str):
                ev_classes.append(c)
    survivor_gate = (inv or {}).get("_survivor_gate") \
        if isinstance((inv or {}).get("_survivor_gate"), dict) else {}
    # R443 / TSC-008: evidence-supported status requires BOUND evidence
    # references — classification counts alone are not evidence (Art.
    # XXI.1); unbound/unresolvable references make the honest state NOT
    # evidence-supported (never silently granted).
    from discovery_fabric.engine.state_integrity import \
        evidence_supported_honest
    _bound_refs = [
        e for e in evidence
        if isinstance(e, dict) and (e.get("evidence_id")
                                    or e.get("id")
                                    or e.get("source"))]
    _es_raw = bool(
        (ev_classes and any(c in ("SOURCE_FACT", "EXTERNAL_PRECEDENT",
                                  "VERIFIED_EVIDENCE")
                            for c in ev_classes))
        or survivor_gate.get("evidence_verified")
        or evidence)
    _es = evidence_supported_honest(_es_raw, _bound_refs)
    evidence_supported = _es["evidence_supported"]
    evidence_supported_basis = _es

    # physics/simulation (COMPUTATIONAL_RESULT only — Art. LIII).
    # MECHANISM_NOT_SIMULATABLE is the R413 decision machine's honest
    # refusal (the mechanism's physics domain is not covered by a
    # validated solver) — that is NOT a simulation result, and must
    # never be counted as one.
    _NOT_SIM = (None, "NOT_APPLICABLE", "MECHANISM_NOT_SIMULATABLE")
    _verdict = physics.get("lifecycle_verdict")
    simulated = _verdict not in _NOT_SIM and bool(_verdict)

    # reality loop (physical observation requires REAL events — never
    # simulated into existence; in fresh runs this is honestly false)
    reality_loop_state = "NONE"
    rl = _read_json(run_dir / "REALITY_LOOP.json")
    if rl:
        reality_loop_state = rl.get("loop_verification_state") or \
            rl.get("state") or "NONE"

    package = _package_info(run_dir)
    # R447 Phase 2: the canonical package terminal state from the ONE
    # derivation (run_state.package_terminal_state — the same object
    # /state serves; the CIO consumes it, never re-derives its own
    # package terminal state, Art. X)
    from . import run_state as _rs
    package_terminal = _rs.package_terminal_state(session, run_dir)

    cio: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "kind": "CANONICAL_INVENTION_OBJECT",
        "run_id": session.get("session_id"),
        "legal_position": LEGAL_POSITION,
        "novelty_language": PREFERRED_NOVELTY_LANGUAGE,
        "identity": {
            "invention_id": _unwrap((inv or {}).get("invention_id"))
            if isinstance((inv or {}).get("invention_id"), dict)
            else (inv or {}).get("invention_id"),
            "problem": _unwrap((inv or {}).get("problem")) or
            session.get("user_text"),
            "mechanism": _unwrap((inv or {}).get("mechanism")),
            "novelty_hypothesis": _unwrap((inv or {}).get(
                "novelty_hypothesis")),
            "distinguishing_features": _unwrap((inv or {}).get(
                "distinguishing_features")),
            "survivor": survivor,
            "final_status": session.get("final_status"),
            # R443: the canonical domain + problem-context applicability
            # consumed VERBATIM from the engineering specification (one
            # authority: engineering_specification.why_this_domain +
            # .applicability — the CIO never re-guesses either)
            "domain": _domain_summary(eng),
            "applicability": _applicability_summary(eng),
        },
        "maturity": {
            # the directive §14 reality states — CIO FIELDS, not
            # frontend badges. Each is true ONLY when a run artifact
            # establishes it (Art. XXXVIII; no promotion without
            # evidence — Art. XXVIII).
            "design": has_geometry,
            "simulation": simulated,
            "evidence_supported": bool(evidence_supported and survivor),
            "evidence_supported_basis": (
                evidence_supported_basis if (evidence_supported
                                             and survivor) else
                {"evidence_supported": False,
                 "references_bound": False,
                 "basis": ("no bound evidence references resolve on "
                           "this run — the honest state is NOT "
                           "evidence-supported (TSC-008/Art. XXI.1)")}),
            "experimentally_verified": reality_loop_state in (
                "REAL_LOOP_VERIFIED", "REPEATED_REALITY_VERIFIED"),
            "maturity_ladder": [
                "DESIGNED" if has_geometry else None,
                "SIMULATED" if simulated else None,
                "EVIDENCE_SUPPORTED" if (evidence_supported and survivor)
                else None,
                "EXPERIMENTALLY_VERIFIED"
                if reality_loop_state in ("REAL_LOOP_VERIFIED",
                                          "REPEATED_REALITY_VERIFIED")
                else None],
            "reality_loop_state": reality_loop_state,
            "maturity_basis": {
                "design": (
                    f"{geometry_class} visualization produced ("
                    + ("parametric CAD with measured geometry"
                       if not geometry_is_conceptual else
                       "conceptual architecture only — engineering CAD "
                       "is not yet earned: no sourced geometry "
                       "parameters on this run")
                    + "); renders are derived artifacts, never "
                      "physical truth"
                    if has_geometry else
                    "no engineering geometry produced on this run "
                    "(honest absence)"),
                "simulation": ("PHYSICS stage executed with a "
                               "computational result (class "
                               "COMPUTATIONAL_RESULT)" if simulated else
                               "no simulation result recorded"),
                "evidence_supported": ("verified evidence records "
                                       "bound to the mechanism"
                                       if evidence_supported and survivor
                                       else "insufficient verified "
                                       "evidence"),
                "experimentally_verified": (
                    "a REAL external observation updated this "
                    "invention through the reality loop"
                    if reality_loop_state in ("REAL_LOOP_VERIFIED",
                                              "REPEATED_REALITY_VERIFIED")
                    else "no physical observation of this invention "
                         "exists (Art. LIII — reality cannot be "
                         "simulated into existence)"),
            },
        },
        "evidence": {
            "records": [
                {"id": e.get("id") or e.get("record_id"),
                 "title": (e.get("title") or "")[:160],
                 "source": e.get("source") or e.get("source_uri"),
                 "evidence_class": e.get("evidence_class")
                 or e.get("epistemic_class"),
                 "span": (e.get("span") or e.get("quote") or "")[:200]}
                for e in (evidence if isinstance(evidence, list) else [])
                [:20] if isinstance(e, dict)],
            "record_count": len(evidence) if isinstance(evidence, list)
            else 0,
            "prior_art": {
                "searched": bool((inv or {}).get("prior_art")),
                "note": "novelty SIGNAL from searched evidence — "
                        "never a legal novelty determination",
            },
        },
        "engineering": {
            "specification_present": bool(eng),
            "parameters": [
                {"param_id": p.get("param_id") or p.get("id"),
                 "value": p.get("value"),
                 "unit": p.get("unit"),
                 "category": p.get("category"),
                 "value_class": p.get("value_class"),
                 "envelope": (p.get("range_min"), p.get("range_max"))
                 if p.get("range_min") is not None else None}
                for p in (_unwrap((pm or {}).get("parameters"))
                          or _unwrap((eng or {}).get("parameters"))
                          or [])[:24]
                if isinstance(p, dict)],
            "assumptions": _unwrap((inv or {}).get("assumptions")),
            "failure_modes": _unwrap((inv or {}).get("failure_modes")),
            "constraints": _unwrap((inv or {}).get("constraints")),
            "causal_chain": _unwrap((inv or {}).get("causal_chain")),
        },
        "geometry": {
            "present": has_geometry,
            "class": geometry_class,
            "conceptual": geometry_is_conceptual,
            "glb": (f"/api/run/{session.get('session_id')}/model"
                    if glb else None),
            "glb_sha256": _sha_file(glb[0]) if glb else None,
            "step": [_geometry_file_route(session.get("session_id"), f)
                      for f in step[:4]],
            "stl": [_geometry_file_route(session.get("session_id"), f)
                    for f in stl[:4]],
            "svg_views": [_geometry_file_route(session.get("session_id"),
                                                f)
                          for f in svg_views[:6]],
            "parametric_model_present": bool(pm),
            "cad_pipeline_status": (cad_ledger or {}).get("status"),
            "bridge_outcome": bridge_report.get("outcome"),
            "bridge_why": _bridge_why(bridge_report),
            # R419 section 12: the named components (from the bridge
            # report — the geometry's own named nodes; the inspection
            # panel and the text↔component linkage render these)
            "components": (
                (bridge_report.get("geometry") or {}).get("components")
                if isinstance(
                    (bridge_report.get("geometry") or {}).get("components"),
                    list) else []),
            # R432/R433: the domain layer + the separated scores + the
            # evolution projection — persisted by the bridge gate in
            # BRIDGE_REPORT.json's geometry block; rendered verbatim
            # (the CIO never re-derives them, Art. X). The scores are
            # compacted (the full check tables live in the run record;
            # the browser gets the three dimensions + failures).
            "domain_family": _br_geo.get("domain_family"),
            "quality_gates": _br_geo.get("quality_gates"),
            "artifact_identity": _br_geo.get("artifact_identity"),
            "fallback_basis": _br_geo.get("fallback_basis"),
            "scores": _compact_scores(_br_geo.get("scores")),
            "evolution": _br_geo.get("evolution"),
            "generation_id": _br_geo.get("generation_id"),
            "generation_count": _br_geo.get("generation_count"),
            "authority": (
                "CONCEPTUAL architecture visualization (CadQuery/OCCT "
                "topology-only build, R418 invention bridge): this is "
                "NOT engineering geometry — no engineering dimensions "
                "are claimed; engineering CAD remains unearned until "
                "parameters are sourced (labels on the artifact)"
                if geometry_is_conceptual else
                "CadQuery/OCCT parametric build is the "
                "engineering geometry authority; meshes and renders "
                "are derived artifacts (R413 geometry authority "
                "boundary — a render can never originate or validate "
                "geometry)"),
        },
        "simulation": {
            "executed": simulated,
            "lifecycle_verdict": physics.get("lifecycle_verdict"),
            "baseline_outcome": (physics.get("baseline_comparison")
                                 or {}).get("outcome"),
            "epistemic_class": "COMPUTATIONAL_RESULT" if simulated
            else None,
            "assumption": "simulation results are computational "
                          "evidence, never physical observations",
        },
        # R419: viewer hints + the render gallery contract — the
        # frontend renders ONLY these pointers (never invents state);
        # the renders block is derived above from MODEL/3D/ itself.
        "visualization": {
            "viewer_required": ["orbit", "zoom", "pan", "reset",
                                "wireframe", "clip"],
            "renders": renders,
            "component_inspection": [
                {"from": "component name",
                 "explain": ["function", "mechanism", "evidence",
                             "simulation", "unknowns"]},
            ],
        },
        "reality_loop": {
            "state": reality_loop_state,
            "record": rl,
        },
        "downloads": {
            "package_zip": (
                f"/api/sessions/{session.get('session_id')}/package"
                if package.get("complete") else None),
            "package_maturity": package.get("maturity"),
            "package_kind": "TECHNOLOGY_TRANSFER_PACKAGE",
            # R447 Phase 2 — the CANONICAL package terminal state, the
            # ONE derivation consumed by /state, the CIO, and the
            # dossier transfer tab (run_state.package_terminal_state):
            # package_state / blocked_stage / blocked_reason /
            # release_verdict / next_action. The blocked reason is
            # never hidden on disk again (the R446-HF Case C defect);
            # the field names match the in-run cio_update vocabulary
            # (package_blocked / package_blocked_reason) so one
            # consumer contract covers both the live and reloaded CIO.
            "package_terminal": package_terminal,
            "package_blocked": bool(
                package_terminal.get("package_state") == "BLOCKED"),
            "package_blocked_reason": (
                package_terminal.get("blocked_stage")
                if package_terminal.get("package_state") == "BLOCKED"
                else None),
            # R422 (directive 3 — package UX): the REAL document count
            # from the package's own manifest (BRIDGE_REPORT
            # package_out.manifest file_count, or the buyer package's
            # DOWNLOAD tree) — never hardcoded, never guessed. The
            # run-inspector Downloads block renders this number.
            "document_count": _package_document_count(run_dir, package),
            # R423A Phase 3 — ONE package: the buyer- vs bridge-package
            # distinction is a MATURITY fact, not two customer products.
            # The single deliverable is the technology transfer package;
            # package_origin discloses which path produced it and the
            # maturity field carries the honest tier. The separate
            # counsel-package surface is REMOVED (the technical evidence
            # rides inside the one package; Toscanini is not a patent
            # court and no longer ships a second legal-flavored ZIP).
            "package_origin": (
                "BUYER_RELEASE_CHAIN" if package.get("package_kind")
                == "BUYER_PACKAGE" else "INVENTION_BRIDGE"),
            "package_kind_note": (
                "the technology transfer package for this run — one "
                "canonical deliverable; its maturity label is the "
                "honest state (" + str(package.get("maturity")
                or "UNKNOWN") + "), and the buyer release gates are "
                "untouched"),
            # R541: per-rank candidate-bound package download routes —
            # each ranked survivor's own package (?candidate=<id>),
            # never the shared run-level /package surface for all.
            # Derived from the session's own ranked_package_downloads
            # record; absent when no ranked packages exist (honest).
            "ranked_package_downloads": (
                session.get("ranked_package_downloads") or []),
        },
        "experiment": {
            "decisive_experiment": dex or _unwrap((inv or {}).get(
                "killer_experiment")),
            "status": "SPECIFIED_NOT_EXECUTED",
        },
        "provenance": {
            "run_dir": str(run_dir),
            "run_id": session.get("session_id"),
            "origin": session.get("origin"),
            "invention_spec_sha256": _sha_file(
                run_dir / "INVENTION_SPECIFICATION.json"),
            "parametric_model_sha256": _sha_file(
                run_dir / "PARAMETRIC_MODEL.json"),
            "final_state_sha256": _sha_file(
                run_dir / "final_state.json"),
            "provider_route_note": "see run_state.model_route — "
                                   "aggregated from persisted call "
                                   "records",
            "reviewer_provenance": "AI_REVIEW",
        },
    }

    # the language guard runs over the copy THIS object ships (the
    # invention spec's own text fields could carry banned words from a
    # model output — Art. XVIII: LLM output is content, never
    # authority; the product surface must not assert patentability)
    shipped_text = json.dumps({
        "mechanism": _unwrap((inv or {}).get("mechanism")),
        "novelty_hypothesis": _unwrap((inv or {}).get(
            "novelty_hypothesis")),
        "distinguishing_features": _unwrap((inv or {}).get(
            "distinguishing_features")),
    })
    guard = language_guard(shipped_text)
    cio["language_guard"] = guard
    if not guard["clean"]:
        # the object still ships (the run record is the authority) but
        # the violation is DISCLOSED on the object — never silently
        # edited (Art. XV); the UI hides the offending narrative fields
        cio["language_guard"]["action"] = (
            "banned patentability language detected in model-generated "
            "narrative fields; the narrative is quarantined from the "
            "product surface (deterministic copy is unaffected)")
    return cio
