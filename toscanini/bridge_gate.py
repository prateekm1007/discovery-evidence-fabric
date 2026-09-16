"""toscanini/bridge_gate.py — R418: the automatic artifact contract.

R423A Phase 2 (2026-09-08): the gate OWNS the render REQUEST and its
state, and NEVER runs Blender inline. DISCOVERY COMPLETE does not mean
PRESENTATION RENDER COMPLETE: the gate records the render request
(RENDER_REQUESTED / ALREADY_PRESENT) and hands execution to the async
artifact job, which waits for the run worker to exit and then renders
under the quality ladder. The run's terminal state no longer waits for
premium rendering (measured before: the in-worker render budget was up
to 300 s inside phase 3.5, BEFORE terminal COMPLETE).

Operator P0 product correction (2026-09-07), sections 2-5:

    When a run ends with an invention, the product surface must never
    show "No 3D on this run" or "Invention, no package yet". The three
    legitimate cases are EXACTLY:

      Case A — a visual artifact already exists
               -> nothing to generate; the projections render it.
      Case B — an invention exists, a visual artifact does not
               -> AUTOMATICALLY generate it (this gate; conceptual
                  classes via the invention bridge, honest labels).
      Case C — generation genuinely cannot create a visual artifact
               -> the conceptual architecture WITH the conceptual 3D
                  artifact (explicit labels; engineering CAD remains
                  unearned, never faked).

    Package generation is likewise AUTOMATIC the moment the current
    invention is sufficiently defined — invention EXISTENCE is separate
    from package MATURITY is separate from BUYER-READINESS (§5). The
    bridge technology package carries its own honest maturity label
    (e.g. EARLY_TECHNICAL_EVALUATION); the buyer-package quality and
    release gates are NOT touched, weakened, or bypassed (Art. IV/VII
    — the bridge package is a distinct artifact class, never a
    laundered buyer release).

Invocation contract:
    Called by the production WORKER (toscanini/worker.py phase 3.5)
    automatically after every engine run — no operator script, no
    copied JSON, no post-run manual processing. Idempotent: a run
    whose BRIDGE_REPORT.json exists is never re-bridged (resume-safe).
    The render stage is REQUESTED here and EXECUTED by the async
    artifact job (toscanini/artifact_worker.py) — the gate never
    blocks on a Blender subprocess.

Constitutional contract:
    - The run directory's artifacts remain the AUTHORITY (Art. X);
      this gate only ADDS artifacts (MODEL/, TECHNOLOGY_PACKAGE/,
      BRIDGE_REPORT.json) and the projections derive from them.
    - A bridge failure is an honest typed record (BRIDGE_REPORT.json
      with outcome + error), never a fabricated artifact and never a
      change to the run's epistemic state (Art. VI/XXV/LXI).
    - Conceptual classes never claim engineering authority (Art.
      XXVIII); the report carries class + basis everywhere.
    - reviewer_provenance=AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import cio as _cio
from . import sessions as store

# R455-LEAN-1 §1: the survivor gate. A run whose canonical DISCOVERY
# RELEASE record does not attest a surviving, promoted candidate gets
# NOTHING from this gate — no bridge, no geometry, no render job, no
# package. The audited failure (EXT-AUDIT-LEAN-R454 §0.2/§B.4):
# `_invention_exists` was true whenever `build_cio` returned non-None,
# and `build_cio` returned non-None whenever ANY invention-side file
# existed — including `final_state.json`, which EVERY run writes. So
# 18/18 production runs were bridged and 16 fully rendered, including
# all 7 `INCOMPLETE_INFERENCE_FAILURE` runs with `invention_id: null`
# — the machine asserted a technology that does not exist (Art.
# XXV/XXVIII: a placeholder object is not honest absence; artifact
# generation is not evidence of invention).
BRIDGE_GATE_VERSION = "1.3.0"  # R478: survivor_attested exported (one gate, server+bridge)

# The release-record statuses that attest NO promoted candidate
# (discovery_fabric/engine/release.py's closed vocabulary). Everything
# else (RELEASED / HELD_FOR_HUMAN_REVIEW / PACKAGE_INCOMPLETE /
# PACKAGE_DEFERRED_TO_COMPILER / PIPELINE_FAILED) implies the
# spec-side gauntlet was passed by a promoted candidate — those runs
# keep the R418 automatic-artifact contract (Art. V: fail closed,
# never become a universal rejector).
_NON_SURVIVOR_RELEASE_STATUSES = (
    "DISCOVERY_INCOMPLETE",
    "NOT_A_SURVIVOR",
    "DISABLED_BY_CONFIG",
)

_CONCEPTUAL_CLASSES = ("SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D")

_RENDER_ARTIFACTS = ("hero.png", "section.png", "exploded.png")


def _renders_present(run_dir: Path) -> bool:
    """The R419 presentation artifacts exist (hero/section/exploded PNGs
    under MODEL/3D/). The GLB variants are enhancements; the PNGs are
    the observable contract (operator section 5)."""
    d = run_dir / "MODEL" / "3D"
    return bool(d.exists()) and all(
        (d / n).is_file() and (d / n).stat().st_size > 0
        for n in _RENDER_ARTIFACTS)


def _request_renders(session_id: str, run_dir: Path,
                     cio_obj: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """R423A Phase 2 — the render REQUEST the gate owns. The Blender
    EXECUTION belongs to the async artifact job (it waits for the run
    worker to exit, acquires the run lock, walks the quality ladder).
    The gate records a typed request state; it NEVER launches Blender.

    Returns the typed record (RENDER_REQUESTED with the job identity,
    ALREADY_PRESENT, or RENDER_REQUEST_FAILED — never an exception).
    """
    if _renders_present(run_dir):
        return {"stage": "RENDER", "status": "ALREADY_PRESENT",
                "note": "presentation artifacts already on disk — "
                        "nothing requested (idempotent)"}
    if not _has_model(run_dir):
        return None  # nothing renderable — no request is fabricated
    try:
        from toscanini import artifact_worker
        record = artifact_worker.enqueue(
            session_id, enqueued_by="bridge_gate")
        return {
            "stage": "RENDER",
            "status": "RENDER_REQUESTED",
            "job": {
                "status": record.get("status"),
                "enqueued_at": record.get("enqueued_at"),
                "worker_pid": record.get("worker_pid"),
                "readback": record.get("readback"),
            },
            "execution": "async artifact job (waits for the run worker "
                         "to exit, then renders through the quality "
                         "ladder; poll the CIO visualization.renders)",
            "note": ("DISCOVERY COMPLETE does not mean PRESENTATION "
                     "RENDER COMPLETE — the render runs asynchronously "
                     "after the run's terminal state"),
        }
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        return {"stage": "RENDER", "status": "RENDER_REQUEST_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "note": ("the async render job could not be requested — "
                         "the run record and package are unaffected "
                         "(Art. LXI: presentation failure is never a "
                         "run failure); the boot render recovery sweep "
                         "re-attempts at next boot")}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _has_model(run_dir: Path) -> bool:
    """A visual artifact already exists (Case A): any GLB under MODEL/
    (the cad_pipeline's per-generation engineering models, an earlier
    bridge pass, or a package GLB)."""
    model_dir = run_dir / "MODEL"
    if model_dir.exists() and any(model_dir.glob("*.glb")):
        return True
    return bool(list(run_dir.glob("*.glb")))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.is_file():
            return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — corrupt record reads as absent
        return None
    return None


def survivor_attested(discovery_release, survivor_selection):
    """R478 (external audit P1-12) — the ONE survivor attestation,
    shared by the bridge gate and the server download gate (Art. X).
    PURE: no filesystem, no clock — callers pass the parsed
    DISCOVERY_RELEASE.json and SURVIVOR_SELECTION.json records (None
    when absent). Semantics are EXACTLY _survivor_recorded's, unchanged:
    a run attests a surviving, promoted candidate only when
      1. discovery_release is not None AND its status is not None AND
         status not in _NON_SURVIVOR_RELEASE_STATUSES;
      2. invention_id is non-null;
      3. invention_spec_hash is truthy OR a SURVIVOR_SELECTION record
         was passed.
    Returns (attested, evidence) — the evidence carries the fields the
    bridge persists verbatim on refusal (Art. XV), plus
    "survivor_selection_passed" for leg 3."""
    status = (discovery_release or {}).get("status")
    inv_id = (discovery_release or {}).get("invention_id")
    spec_hash = (discovery_release or {}).get("invention_spec_hash")
    non_survivor = (status in _NON_SURVIVOR_RELEASE_STATUSES
                    or status is None)
    survivor_selection_passed = bool(
        spec_hash or survivor_selection is not None)
    attested = (discovery_release is not None and not non_survivor
                and bool(inv_id) and survivor_selection_passed)
    evidence = {
        "authority": "DISCOVERY_RELEASE.json",
        "status": status,
        "invention_id": inv_id,
        "invention_spec_hash_present": bool(spec_hash),
        "survivor_selection_present": survivor_selection is not None,
        "non_survivor_statuses": list(_NON_SURVIVOR_RELEASE_STATUSES),
        "survivor_selection_passed": survivor_selection_passed,
    }
    return attested, evidence


def _survivor_recorded(run_dir: Path) -> Dict[str, Any]:
    """R455-LEAN-1 §1 — the survivor test, derived from canonical state.

    THE authority is the run's own DISCOVERY_RELEASE.json (written by
    the engine's Directive-2 tail on EVERY run — the single place a
    downstream system looks to discover what exists). The gate may
    only produce artifacts when that record attests a surviving,
    promoted candidate:

      1. `status` is NOT a non-survivor status (DISCOVERY_INCOMPLETE /
         NOT_A_SURVIVOR / DISABLED_BY_CONFIG);
      2. `invention_id` is non-null;
      3. the specification identity is present (`invention_spec_hash`),
         or a SURVIVOR_SELECTION record exists on disk.

    When the release record is ABSENT entirely (pre-release-era run
    records and test fixtures only — the current engine always writes
    it), the legacy `_invention_exists` check decides, now that
    `build_cio` no longer counts `final_state.json` as invention-side
    state (the two directed changes together close the always-true
    hole).

    Returns {"recorded": bool, "evidence": {...}} — the evidence is
    persisted verbatim on any refusal (Art. XV).
    """
    rel = _read_json(run_dir / "DISCOVERY_RELEASE.json")
    if rel is not None:
        # R478 (external audit P1-12): the attestation is the ONE gate
        # the server download route also consumes (Art. X) — same
        # semantics, single implementation.
        surv = _read_json(run_dir / "SURVIVOR_SELECTION.json")
        attested, evidence = survivor_attested(rel, surv)
        return {"recorded": bool(attested), "evidence": evidence}
    return {
        "recorded": True,  # no release record -> legacy path decides
        "evidence": {
            "authority": None,
            "note": ("no DISCOVERY_RELEASE.json on this run record "
                     "(pre-release-era record) — the legacy "
                     "invention-side check decides; final_state.json "
                     "no longer manufactures invention presence"),
        },
    }


def _invention_exists(detail: Dict[str, Any], cio_obj: Optional[Dict]) -> bool:
    """R455-LEAN-1 §1: LEGACY fallback, used ONLY when the run carries
    no DISCOVERY_RELEASE.json (the current engine writes one on every
    run — see `_survivor_recorded`). An invention exists when the run
    recorded invention-side state: a CIO (invention specification /
    engineering specification / parametric model / CAD ledger /
    decisive experiment — never `final_state.json` alone, which every
    run writes), or recorded evolution generations. Absence is honest
    absence (Art. XXV) — no invention, no bridge, no fabricated
    artifact."""
    if cio_obj is not None:
        return True
    rs = detail.get("run_state") or {}
    gens = (rs.get("generations") or {}).get("generations") or []
    if isinstance(gens, list) and gens:
        return True
    return bool(detail.get("invention_specification"))


def _record(run_dir: Path, outcome: str, report: Dict[str, Any]) -> Dict:
    persisted = {
        "stage": "BRIDGE_GATE",
        "bridge_gate_version": BRIDGE_GATE_VERSION,
        "outcome": outcome,
        "at": _now(),
        "reviewer_provenance": "AI_REVIEW",
    } | report
    (run_dir / "BRIDGE_REPORT.json").write_text(json.dumps(persisted, indent=2))
    return persisted


def ensure_artifacts(session_id: str) -> Dict[str, Any]:
    """The automatic post-run artifact gate. Returns the persisted
    BRIDGE_REPORT content (read back from disk — the file is the
    authority, Art. X)."""
    session = store.get_session(session_id)
    if not session:
        return {"outcome": "NO_SESSION", "note": "session not found"}
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if not run_dir or not run_dir.exists():
        return {"outcome": "NO_RUN_DIR",
                "note": "run directory absent — nothing to bridge"}

    # idempotent / resume-safe: a completed bridge pass is never re-run
    prior = run_dir / "BRIDGE_REPORT.json"
    if prior.exists():
        try:
            return json.loads(prior.read_text())
        except Exception:  # noqa: BLE001 — corrupt record -> redo
            pass

    detail = store.session_detail(session_id) or {}
    cio_obj = _cio.build_cio(session)

    # R455-LEAN-1 §1: the survivor gate decides FIRST. A run whose own
    # release record does not attest a surviving, promoted candidate
    # gets exactly ONE honest record and NOTHING else — no GLB, no
    # render job, no package (the audit's top deletion: the machine
    # must stop asserting technologies that do not exist).
    survivor = _survivor_recorded(run_dir)
    if not survivor["recorded"]:
        return _record(run_dir, "NO_SURVIVOR", {
            "survivor_gate": survivor["evidence"],
            "note": ("this run recorded no surviving, promoted "
                      "candidate (its own DISCOVERY_RELEASE.json is "
                      "the authority) — the bridge generates nothing: "
                      "no geometry, no render job, no package (Art. "
                      "XXV: honest absence; Art. XXVIII: artifact "
                      "generation is never evidence of invention; "
                      "R455-LEAN-1: no survivor, no artifact)"),
        })

    if not _invention_exists(detail, cio_obj):
        # legacy path (no release record on the run): honest — no
        # invention-side state on this run (e.g. FALSE_PREMISE or a
        # transport-blocked run) — no artifact is fabricated
        return _record(run_dir, "NO_INVENTION", {
            "note": ("no invention-side artifacts on this run — the "
                      "bridge generates nothing (Art. XXV: absence is "
                      "honest absence, never a placeholder object)"),
        })

    # Case A: a visual artifact already exists — the geometry stage is
    # skipped, but the PACKAGE contract still applies (§5: a package is
    # produced the moment the invention is sufficiently defined; if the
    # buyer package completed, the gate has nothing to add at all).
    already_has_model = _has_model(run_dir)

    from discovery_fabric.engine.invention_bridge.bridge import (
        bridge as run_bridge)
    from discovery_fabric.engine.invention_bridge import epistemics as ep

    # R424 §11: the REAL engine identity for every package this gate
    # builds — resolved from the baked artifact identity (the hosted
    # authority, R396 A) and threaded into the factory. A package may
    # never carry a lazy "unknown" while the identity is available.
    engine_identity = None
    try:
        from toscanini import artifact_identity as _aid
        engine_identity = _aid.resolve_engine_commit()
    except Exception:  # noqa: BLE001 — factory has honest fallbacks
        engine_identity = None

    if already_has_model:
        # Case A: geometry exists (cad_pipeline engineering models or a
        # package GLB). If a package also exists, the R418 contract is
        # satisfied — the R419 RENDER contract is satisfied by REQUEST:
        # missing presentation artifacts are requested from the async
        # job (R423A Phase 2: the gate never runs Blender inline).
        buyer_zip = list((run_dir / "DOWNLOAD").glob("*.zip")) \
            if (run_dir / "DOWNLOAD").exists() else []
        bridge_zip = list(run_dir.glob("TECHNOLOGY_PACKAGE_*.zip")) + \
            list(run_dir.glob("TECHNOLOGY_TRANSFER_PACKAGE_*.zip"))
        if buyer_zip or bridge_zip:
            render_record = _request_renders(session_id, run_dir, cio_obj)
            return _record(run_dir, "ALREADY_COMPLETE", {
                "case": "A",
                "geometry_present": True,
                "package_present": True,
                "renders": render_record or {"status": "ALREADY_PRESENT"},
                "note": ("visual artifact and package both present — "
                         "the projections render them (Case A); "
                         "missing R419 renders are requested from the "
                         "async job"),
            })
        # geometry exists but no package -> build the bridge package
        # around the EXISTING geometry (classification still runs —
        # recorded; the geometry stage is skipped, disclosed).
        result = run_bridge(
            detail, cio_obj, str(run_dir),
            glb_endpoint=f"/api/run/{session_id}/model",
            package_endpoint=f"/api/run/{session_id}/package",
            build_renders=False,
            engine_identity=engine_identity,
            run_id=session_id,
        )
        outcome = "PACKAGE_ADDED_TO_EXISTING_GEOMETRY"
        render_record = _request_renders(session_id, run_dir, cio_obj)
        persisted = _record(run_dir, outcome, {
            "case": "A+package",
            "visualizability": result.get("visualizability"),
            "geometry_outcome": "SKIPPED_ALREADY_PRESENT",
            "renders": render_record or {"status": "ALREADY_PRESENT"},
            "package_out": _package_summary(result.get("package_out")),
            "report": result.get("report"),
        })
        return persisted

    # Case B: invention exists, no visual artifact -> generate it.
    # R423A Phase 2: build_renders=False — the Blender stage is NOT run
    # inline; the gate requests the async render job after the package
    # is built (render state is owned HERE, execution is async).
    result = run_bridge(
        detail, cio_obj, str(run_dir),
        glb_endpoint=f"/api/run/{session_id}/model",
        package_endpoint=f"/api/run/{session_id}/package",
        build_renders=False,
        engine_identity=engine_identity,
        run_id=session_id,
    )

    geometry_out = result.get("geometry_out")
    vis = result.get("visualizability") or {}
    vis_class = vis.get("visualizability_class")

    if geometry_out is None and vis_class == ep.NOT_VISUALIZABLE:
        # Case C: the classifier's honest verdict is that this invention
        # is not visualizable in engineering terms (algorithmic, no
        # physical site). The operator's product rule: the user still
        # gets the conceptual architecture WITH a conceptual 3D
        # artifact, explicitly labeled. Engineering CAD remains
        # unearned — the label says so; nothing is faked.
        try:
            from discovery_fabric.engine.invention_bridge import (
                conceptual_geometry,)
            built = conceptual_geometry.build_system_architecture(
                ["algorithmic core", "data interface",
                 "actuation / effector boundary"],
                vis.get("intervention_site", ""))
            model_dir = run_dir / "MODEL"
            model_dir.mkdir(parents=True, exist_ok=True)
            (model_dir / "model-001.glb").write_bytes(built["glb_bytes"])
            # R419 sections 5-6 (R423A Phase 2 form): the Case C
            # conceptual fallback gets its presentation renders via the
            # SAME async request path as A/B (never inline Blender)
            render_record = _request_renders(
                session_id, run_dir, {"geometry": {
                    "visualizability_class": "CONCEPTUAL_3D"}})
            return _record(run_dir, "CONCEPTUAL_FALLBACK", {
                "case": "C",
                "classification": vis,
                "fallback_model": "MODEL/model-001.glb",
                "fallback_class": "CONCEPTUAL_3D",
                "renders": render_record or {"status": "ALREADY_PRESENT"},
                "fallback_basis": (
                    "the classifier recorded NOT_VISUALIZABLE "
                    "(algorithmic invention, no physical intervention "
                    "site); the product contract (operator §4 Case C) "
                    "requires the conceptual architecture with an "
                    "explicitly conceptual 3D artifact — engineering "
                    "CAD remains unearned and unlabeled-as-engineering"),
                "package_out": _package_summary(result.get("package_out")),
                "report": result.get("report"),
            })
        except Exception as exc:  # noqa: BLE001 — typed, never silent
            return _record(run_dir, "CONCEPTUAL_FALLBACK_FAILED", {
                "case": "C",
                "classification": vis,
                "error": f"{type(exc).__name__}: {exc}",
                "note": ("the conceptual fallback itself failed — an "
                         "engine defect, disclosed; the run record is "
                         "unaffected (Art. XV)"),
            })

    if geometry_out is None:
        # the bridge genuinely failed (geometry attempts exhausted) —
        # the honest typed record; the product surface shows the
        # failure reason, never a placeholder
        return _record(run_dir, "BRIDGE_GEOMETRY_FAILED", {
            "case": "B",
            "visualizability": vis,
            "report": result.get("report"),
            "note": ("the bridge could not build a visual artifact "
                     "after diagnosis/repair attempts — the failure "
                     "attempts are recorded in the report (never a "
                     "silent 'No 3D')"),
        })

    vis_class = geometry_out.get("visualizability_class") or vis_class
    # R423A Phase 2: the render REQUEST (execution is the async job's)
    render_record = _request_renders(session_id, run_dir, cio_obj)
    persisted = _record(run_dir, "COMPLETED", {
        "case": "B",
        "visualizability_class": vis_class,
        "conceptual": vis_class in _CONCEPTUAL_CLASSES,
        "visualizability": vis,
        "geometry": {
            "model_glbs": sorted(
                p.name for p in (run_dir / "MODEL").glob("model-*.glb")
            ) if (run_dir / "MODEL").exists() else [],
            "glb_sha256": geometry_out.get("glb_sha256"),
            "components": geometry_out.get("components") or [],
            "key_dimensions": geometry_out.get("key_dimensions") or {},
            "generation_models": [
                {"generation": m.get("generation"),
                 "glb": f"MODEL/model-{m.get('generation'):03d}.glb",
                 "current": m.get("current")}
                for m in geometry_out.get("generation_models") or []],
            # R432: the domain layer (family + gates + identity + the
            # honest fallback basis) — persisted for the CIO projection
            "domain_family": geometry_out.get("domain_family"),
            "quality_gates": geometry_out.get("quality_gates"),
            "artifact_identity": geometry_out.get("artifact_identity"),
            "fallback_basis": geometry_out.get("fallback_basis"),
            # R433: the three SEPARATED scores (section 13) + the
            # evolution projection (sections 2/15) + NOT VISUALIZED
            # (section 6) — the dossier renders these verbatim
            "scores": geometry_out.get("scores"),
            "evolution": geometry_out.get("evolution"),
            "generation_id": geometry_out.get("generation_id"),
            "generation_count": geometry_out.get("generation_count"),
        },
        "renders": render_record or geometry_out.get("renders"),
        "package_out": _package_summary(result.get("package_out")),
        "report": result.get("report"),
    })
    return persisted


def _package_summary(package_out: Optional[Dict[str, Any]]) -> Optional[Dict]:
    if not package_out:
        return None
    return {
        "zip_name": os.path.basename(package_out.get("zip_path", "")),
        "zip_sha256": package_out.get("zip_sha256"),
        "zip_bytes": package_out.get("zip_bytes"),
        "package_maturity": package_out.get("package_maturity"),
        "visualizability_class": package_out.get("visualizability_class"),
        "manifest_files": (package_out.get("manifest") or {}).get("file_count"),
        "package_kind": "TECHNOLOGY_TRANSFER_PACKAGE (bridge) — the ONE "
                        "canonical technology-transfer artifact for "
                        "this run, honestly maturity-labeled; distinct "
                        "from the buyer release chain (Art. IV: no "
                        "weakened gates)",
    }
