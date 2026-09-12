"""toscanini/dossier.py — R430.1: the Technology Dossier projection.

Directive sections 3–6, 10, 14–17:
  A first-class DOSSIER that exists as soon as the investigation has a
  canonical state — NOT gated on SYSTEM_3D or PACKAGE_READY. An
  incomplete dossier is an honest representation of incomplete state.

  Six tabs (section 4): Overview / Design / Evidence / Engineering /
  Experiment / Transfer. The internal 16-step engine gauntlet stays
  machinery; the dossier is the user-facing abstraction.

Constitutional contract (Art. X): the dossier is a PROJECTION of the
canonical invention/run state — session record, stage envelopes, CIO,
bridge report, package machine layer. It never authors state, never
mutates a run artifact, never fabricates a field: absent -> PENDING /
UNAVAILABLE / NOT_ESTABLISHED with the recorded reason (Art. XXV).

  availability states: AVAILABLE | PENDING | UNAVAILABLE |
                       NOT_ESTABLISHED
  (NOT_ESTABLISHED = the state was evaluated and is honestly negative:
   e.g. physical validation is not established; UNAVAILABLE = an
   artifact this tab would render does not exist on this run; PENDING
   = the investigation is still working toward it.)

Epistemic safety (section 8 / Art. XXVIII): frontend wording may never
upgrade a class; each tab carries the class of the artifact that
produced it. PHYSICAL_OBSERVED appears only from a REAL reality-loop
ledger (Art. XXXVIII).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from toscanini import cio as _cio_mod
from toscanini import run_state as _rs
from toscanini import sessions as store
from toscanini.sessions import _read_json

DOSSIER_TABS = ("overview", "design", "evidence", "engineering",
                "experiment", "transfer")

_AVAIL = ("AVAILABLE", "PENDING", "UNAVAILABLE", "NOT_ESTABLISHED")


def _pkg_dir(run_dir: Optional[Path]) -> Optional[Path]:
    if not run_dir or not run_dir.exists():
        return None
    # both package layouts the system persists: the engine's DOWNLOAD/
    # tree and the invention bridge's TECHNOLOGY_PACKAGE/ tree (R418;
    # historical zips at the run root also resolve below)
    for cand in ("DOWNLOAD", "TECHNOLOGY_PACKAGE",
                 "TECHNOLOGY_TRANSFER_PACKAGE"):
        d = run_dir / cand
        if d.exists() and any(d.iterdir()):
            return d
    zips = sorted(run_dir.glob("TECHNOLOGY_TRANSFER_PACKAGE*.zip")) or \
        sorted(run_dir.glob("TECHNOLOGY_PACKAGE_*.zip"))
    if zips:
        return run_dir
    return None


def _tab(avail: str, epi: str, note: str, **content) -> Dict[str, Any]:
    assert avail in _AVAIL, avail
    return {"availability": avail, "epistemic_class": epi,
            "note": note, **content}


# ---------------------------------------------------------------------------
# R435 — schema-scaffolding guard (defense in depth).
#
# The generation prompts carry placeholder field examples ("<the causal
# mechanism the architecture exploits>"). Older / weaker generation paths
# can echo those placeholders into a run record (OBSERVED live on the
# production deployment; the generator boundary now rejects echo —
# discovery_fabric/engine/evolution.py::_is_template_echo). This
# projection guard catches the SAME shape in records that predate the
# generator fix or arrive through any other path, so scaffolding can
# never be presented to a user as the finished invention.
#
# Four distinct honest states, never interchangeable:
#   * missing data          -> PENDING / UNAVAILABLE (recorded reason)
#   * generation failed     -> this guard: field suppressed +
#                              generation_failed flag, explicit note
#   * legitimate unknown    -> NOT_ESTABLISHED / UNKNOWN (Art. XXV)
#   * schema fallback       -> this guard: never rendered as content
# The projection still never MUTATES the underlying record (Art. X) —
# the suppression is presentation-layer only and the scaffolding value
# remains inspectable in the run artifact itself.
# ---------------------------------------------------------------------------
_SCAFFOLD_PHRASES = (
    "the causal mechanism the architecture exploits",
    "the specific engineering intervention on the device",
    "the measurable expected effect",
    "the cheapest concrete test that could kill it",
    "the operating regime the architecture assumes",
    "the new causal mechanism",
    "the new specific engineering intervention",
    "the new measurable expected effect",
)


def _scaffold_like(value: Any) -> bool:
    """True when a field value is prompt/schema scaffolding, not content."""
    if not isinstance(value, str) or not value.strip():
        return False
    v = value.strip()
    if v.startswith("<") and v.endswith(">") and len(v) > 8:
        return True
    stripped = v.strip("<>").strip().rstrip(".:")
    return stripped.lower() in _SCAFFOLD_PHRASES


def _suppress_scaffold(value: Any) -> Optional[str]:
    """None when the value is scaffolding (suppressed); the value when
    it is real content."""
    if _scaffold_like(value):
        return None
    return value if isinstance(value, str) else None


# ---------------------------------------------------------------------------
# Evidence ledger (section 10)
# ---------------------------------------------------------------------------
def evidence_ledger(session: Dict[str, Any]) -> Dict[str, Any]:
    """The evidence ledger from the run's own retrieved records. Every
    item exposes what the RETRIEVE envelope actually recorded: title,
    source, identifier/link, retrieval time, evidence class, and
    whether it influenced the surviving invention (the invention
    specification's own evidence index). Retrieved-but-unused items
    stay VISIBLY distinct from used evidence — never merged.

    R451-C2 (C2.5 / Article XXV): every exit carries a typed
    `retrieval_state`, and NUMERIC COUNTS exist ONLY when retrieval
    actually executed (the envelope exists). "The system never reached
    retrieval" and "the system searched and measured zero" are
    different facts; the first must never render as "0 sources
    retrieved" (Article XXI.3: provider failure is not absence;
    Article XXV: unknown must remain unknown).

      retrieval_state:
        NOT_REACHED  — the run stopped before retrieval executed
        PENDING      — the run is running and retrieval has not landed yet
        FAILED       — the run manifest records the RETRIEVE stage failed
        RETRIEVED    — the envelope exists; counts are MEASURED
                       (zero counts here are a real measured zero)
    """
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if not run_dir or not run_dir.exists():
        return _tab("PENDING", "UNKNOWN",
                    "evidence not retrieved yet — the ledger populates "
                    "as records are actually retrieved", items=[],
                    retrieval_state="NOT_REACHED",
                    retrieval_note=("the investigation has not reached "
                                    "evidence acquisition"))
    # the run manifest's failed_stages decide FAILED (same source
    # run_state._evidence_state reads — one truth, two consumers)
    manifest = _read_json(run_dir / "run_manifest.json") or {}
    retrieve_failed = bool((manifest.get("failed_stages") or {})
                           .get("RETRIEVE"))
    env = _read_json(run_dir / "envelope_RETRIEVE.json")
    if env is None:
        if session.get("status") in ("PENDING", "BUILDING_PROBLEM",
                                     "RUNNING"):
            return _tab("PENDING", "UNKNOWN",
                        "evidence retrieval in progress — nothing "
                        "fabricated before records exist", items=[],
                        retrieval_state="PENDING",
                        retrieval_note=("evidence acquisition has not "
                                        "completed yet"))
        if retrieve_failed:
            return _tab("UNAVAILABLE", "UNKNOWN",
                        "evidence retrieval FAILED (recorded in the run "
                        "manifest) — a transport/infrastructure state, "
                        "never a measured zero", items=[],
                        retrieval_state="FAILED",
                        retrieval_note=("retrieval executed and failed — "
                                        "no source count exists"))
        return _tab("UNAVAILABLE", "UNKNOWN",
                    "no retrieval envelope on this run — evidence was "
                    "not established (the run record is the truth)",
                    items=[],
                    retrieval_state="NOT_REACHED",
                    retrieval_note=("the investigation stopped before "
                                    "evidence could be acquired"))

    records = [r for r in (env.get("evidence") or [])
               if isinstance(r, dict)]
    # the invention's own evidence index decides USED IN DESIGN
    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json") or {}
    inv_ev = inv.get("evidence")
    used_ids: set = set()
    if isinstance(inv_ev, dict):
        for rid in (inv_ev.get("evidence_ids") or []):
            used_ids.add(str(rid))
        for item in (inv_ev.get("value") or []):
            if isinstance(item, dict):
                used_ids.add(str(item.get("id")))
    elif isinstance(inv_ev, list):
        for item in inv_ev:
            if isinstance(item, dict):
                used_ids.add(str(item.get("id")))

    items: List[Dict[str, Any]] = []
    for r in records:
        rid = str(r.get("id") or r.get("source_id") or "")
        items.append({
            "id": rid,
            "title": (r.get("title") or "")[:200],
            "source": r.get("source"),
            "source_uri": r.get("source_uri") or r.get("doi"),
            "doi": r.get("doi"),
            "publication_date": r.get("publication_date"),
            "retrieval_timestamp": r.get("retrieval_timestamp"),
            "evidence_class": r.get("epistemic_state")
            or r.get("epistemic_class") or "UNKNOWN",
            "provenance_id": r.get("content_hash"),
            "used_in_design": rid in used_ids if rid else False,
        })
    used = [i for i in items if i["used_in_design"]]
    status = ("AVAILABLE" if records else
              "NOT_ESTABLISHED" if session.get("status") == "COMPLETE"
              else "PENDING")
    return _tab(
        status, "RETRIEVED",
        ("every item is a custody-frozen record from this run's "
         "retrieval envelope; used-in-design is decided by the "
         "invention specification's own evidence index"),
        items=items,
        # the envelope exists: the counts are MEASURED (a zero here is
        # a real measured zero — Art. XXI.3/XXV the other way round)
        retrieval_state="RETRIEVED",
        retrieved_count=len(items),
        used_count=len(used),
        used_visible_distinction=True)


# ---------------------------------------------------------------------------
# Design tab (section 6) — the primary visual artifact, honestly
# ---------------------------------------------------------------------------
def _hero_eligibility(geom: Dict[str, Any]) -> Dict[str, Any]:
    """R436 Direction 3 — the semantic-failure hero suppression invariant,
    derived ONLY from the run's own records (the dossier is the canonical
    projection; the frontend renders, never re-derives — Art. X).

    A generic fallback object (R432 fallback_basis: the domain template
    or its repair path — the "slab with boxes" class) is NOT hero
    material: no substitute model may occupy the primary surface
    (blind-spot register BS-006/007/024/025). A CONCEPTUAL model whose
    recorded semantic_identity score FAILED (not_visualized components —
    the model does not faithfully represent the architecture) is
    likewise not hero material.

    NEVER suppressed:
      * engineering geometry (the earned engineering model — its
        semantic score is structurally "uncheckable by this gate" with
        no spec; that is UNKNOWN, not a failure finding — Art. XXV);
      * a conceptual model whose semantic identity PASSED (it
        materially communicates the architecture — state B);
      * legacy records with no scores and no fallback_basis (absence
        of evidence is not evidence of failure — Art. XXV).
    """
    fallback = bool(geom.get("fallback_basis"))
    scores = geom.get("scores") or {}
    semantic = scores.get("semantic_identity") or {}
    semantic_failed = (
        bool(geom.get("conceptual"))
        and semantic.get("passed") is False
    )
    if fallback:
        return {
            "eligible": False,
            "reason": (
                "generic fallback geometry — the domain template or its "
                "repair path stood in because a faithful model could not "
                "be built; a substitute object is never shown as the "
                "technology"),
            "rule": "R436 hero suppression: fallback_basis",
        }
    if semantic_failed:
        return {
            "eligible": False,
            "reason": (
                "the model does not faithfully represent the recorded "
                "architecture — components of the invention are not "
                "visualized in the geometry"),
            "rule": ("R436 hero suppression: semantic_identity FAIL "
                     "on conceptual geometry"),
            # the compacted CIO score carries not_visualized at the
            # TOP level of scores (R433 compaction) — read both places
            "not_visualized": (semantic.get("not_visualized")
                               or scores.get("not_visualized") or []),
        }
    return {
        "eligible": True,
        "reason": None,
        "rule": (
            "R436 hero suppression: no fallback_basis and semantic "
            "identity not failed (or not applicable)"),
    }


# ---------------------------------------------------------------------------
# R451-C2.1 — the typed geometry/visual state (the directive's six values)
# ---------------------------------------------------------------------------
# The operator directive: "the frontend must stop using the existence of
# a 3D file as a proxy for the state of discovery". The six states are
# DERIVED HERE, from canonical records only (the CIO geometry block, the
# bridge report outcome, the persisted render record + visual gate), and
# the UI consumes them verbatim — the browser never infers them from a
# missing file (auditor governance 7: frontend claims trace to backend
# truth; Art. X: one canonical authority).
#
#   upstream_not_reached        the pipeline never arrived at the
#                               engineering/geometry stage
#   geometry_not_applicable     engineering ran; the recorded bridge
#                               outcome says this invention class has no
#                               visualizable geometry (NOT_VISUALIZABLE)
#   geometry_generation_failed  engineering ran; the recorded bridge
#                               outcome says the geometry build failed
#                               (GEOMETRY_FAILED)
#   geometry_available          a canonical geometry artifact exists
#   visual_render_failed        geometry exists; the presentation render
#                               did not produce an approved render
#                               (renderer unavailable OR gate not passed
#                               — `presentation_cause` distinguishes)
#   visual_complete             render succeeded AND the visual gate
#                               verdict is PASS / COMPLETE_PASS
GEOMETRY_STATES = ("upstream_not_reached", "geometry_not_applicable",
                   "geometry_generation_failed", "geometry_available",
                   "visual_render_failed", "visual_complete")

# render-record statuses that mean the renderer produced pixels
_RENDERER_RAN = ("OK", "SUCCEEDED", "COMPLETE")


def _geometry_state(session: Dict[str, Any], geom: Dict[str, Any],
                    renders: Dict[str, Any], running: bool) -> Dict[str, Any]:
    """The typed geometry/visual state + its recorded detail. Every
    branch reads a RECORDED field; absence of records is classified as
    `upstream_not_reached` (the honest state), never as a failure."""
    has_geometry = bool(geom.get("present"))
    if has_geometry:
        status = str(renders.get("status") or "")
        verdict = ((renders.get("visual_gate") or {}).get("verdict")) \
            if isinstance(renders.get("visual_gate"), dict) else None
        if verdict in ("PASS", "COMPLETE_PASS"):
            return {"geometry_state": "visual_complete",
                    "presentation_cause": None,
                    "geometry_state_detail": None}
        if status in _RENDERER_RAN and verdict is not None:
            # the renderer produced pixels and the gate said no (State D)
            return {
                "geometry_state": "visual_render_failed",
                "presentation_cause": "gate_not_passed",
                "geometry_state_detail":
                    f"the render completed but the presentation "
                    f"integrity gate returned {verdict}",
            }
        if "SKIPPED" in status or status in (
                "FAILED", "RENDER_FAILED", "RENDER_TIMEOUT", "NOT_RUN",
                "INTERRUPTED"):
            cause = "renderer_unavailable"
            detail = renders.get("note") or \
                f"the presentation renderer recorded {status}"
            if "SKIPPED" in status or status == "INTERRUPTED":
                cause = "infrastructure"
            return {"geometry_state": "visual_render_failed",
                    "presentation_cause": cause,
                    "geometry_state_detail": detail}
        if status in ("RUNNING", "RENDERING", "PENDING"):
            return {"geometry_state": "geometry_available",
                    "presentation_cause": "rendering_in_progress",
                    "geometry_state_detail":
                    "the presentation render job is running"}
        # no render record at all: the geometry exists and the
        # presentation join has not produced an approved render yet —
        # exactly the BS-003 surface the R451 watchdog also checks
        return {"geometry_state": "geometry_available",
                "presentation_cause": "not_attempted",
                "geometry_state_detail":
                "no presentation render record exists for this geometry "
                "yet"}

    # ---- no geometry: the recorded bridge outcome decides -------------
    outcome = geom.get("bridge_outcome")
    if outcome == "NOT_VISUALIZABLE":
        return {"geometry_state": "geometry_not_applicable",
                "presentation_cause": None,
                "geometry_state_detail": geom.get("bridge_why") or
                "the recorded bridge outcome is NOT_VISUALIZABLE"}
    if outcome == "GEOMETRY_FAILED":
        return {"geometry_state": "geometry_generation_failed",
                "presentation_cause": None,
                "geometry_state_detail": geom.get("bridge_why") or
                "the recorded bridge outcome is GEOMETRY_FAILED"}
    # no bridge geometry outcome recorded: the pipeline did not arrive
    # at (or through) the engineering/geometry stage — including the
    # NO_INVENTION bridge outcome and every infrastructure stop
    detail = None
    if running:
        detail = ("the investigation has not reached the engineering "
                  "stage yet")
    elif geom.get("bridge_outcome") == "NO_INVENTION":
        detail = ("no invention-side artifacts were recorded on this "
                  "run — the engineering stage had nothing to visualize")
    return {"geometry_state": "upstream_not_reached",
            "presentation_cause": None,
            "geometry_state_detail": detail}


def design_tab(session: Dict[str, Any],
               cio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    running = session.get("status") in ("PENDING", "BUILDING_PROBLEM",
                                        "RUNNING")
    geom = (cio or {}).get("geometry") or {}
    renders = ((cio or {}).get("visualization") or {}).get("renders") or {}
    gst = _geometry_state(session, geom, renders, running)
    if geom.get("present"):
        return _tab(
            "AVAILABLE",
            "ENGINEERING_DEFINED" if not geom.get("conceptual")
            else "HYPOTHESIZED",
            ("interactive geometry from the canonical CAD source — the "
             "same parametric definition that builds the package "
             "models (no second geometry source, R430.1 section 17)"),
            geometry_class=geom.get("class"),
            conceptual=geom.get("conceptual"),
            glb=geom.get("glb"),
            glb_sha256=geom.get("glb_sha256"),
            step=geom.get("step"),
            stl=geom.get("stl"),
            key_dimensions=geom.get("key_dimensions")
            or (cio or {}).get("engineering", {}).get("key_dimensions"),
            components=geom.get("components"),
            parameters=[
                p for p in ((cio or {}).get("engineering")
                            or {}).get("parameters") or []
                if isinstance(p, dict) and p.get("envelope")],
            authority=geom.get("authority"),
            renders=renders,
            viewer_required=["rotate", "zoom", "pan", "reset",
                              "fullscreen"],
            section_view=bool(renders.get("section_png")),
            exploded_view=bool(renders.get("exploded_png")),
            # R432: the domain layer + the section-20 identity chain +
            # the honest generic-fallback disclosure (sections 3/15/23)
            domain_family=geom.get("domain_family"),
            quality_gates=geom.get("quality_gates"),
            artifact_identity=geom.get("artifact_identity"),
            fallback_basis=geom.get("fallback_basis"),
            geometry_spec=geom.get("geometry_spec"),
            # R433: the three separated scores (section 13) + the
            # generation evolution projection (sections 2/15) + the
            # NOT VISUALIZED disclosure (section 6)
            # R435: evolution `why` text that is prompt scaffolding is
            # suppressed row-by-row (same guard class as the overview
            # mechanism — never render scaffolding as invention state)
            # R436 Direction 3: the hero suppression invariant — the
            # primary surface shows the model ONLY when the geometry
            # earns it; the technical record (this tab) keeps every
            # field regardless (the GLB stays inspectable/downloadable
            # in the deep layer — the projection never hides the
            # artifact, only the stage placement)
            hero_eligibility=_hero_eligibility(geom),
            # R451-C2.1: the typed geometry/visual state — the UI's
            # States C/D/E consume THIS, never a missing-file inference
            geometry_state=gst["geometry_state"],
            presentation_cause=gst["presentation_cause"],
            geometry_state_detail=gst["geometry_state_detail"],
            scores=geom.get("scores"),
            not_visualized=(geom.get("scores") or {}).get(
                "not_visualized") or [],
            evolution=[
                {**row, "why": _suppress_scaffold(row.get("why"))}
                if isinstance(row, dict) else row
                for row in (geom.get("evolution") or [])
            ],
            generation_id=(geom.get("generation_id")
                           or ((geom.get("artifact_identity") or {})
                               .get("generation_id"))),
            generation_count=geom.get("generation_count"),
        )
    # honest unavailable block (directive section 6; R451-C2.1: the
    # note follows the TYPED state — the blanket "3D GEOMETRY
    # UNAVAILABLE" reading the operator directive removed is gone; the
    # tab states what actually happened per the recorded outcome)
    reason = gst.get("geometry_state_detail") \
        or geom.get("bridge_why") or geom.get("bridge_outcome") \
        or (geom.get("cad_pipeline_status")
            and f"cad pipeline status {geom.get('cad_pipeline_status')}")
    if gst["geometry_state"] == "upstream_not_reached":
        note = ("Engineering visualization not reached — the "
                "investigation has not produced engineering geometry "
                "on this run; the scientific rationale is preserved "
                "regardless")
    else:
        # geometry_not_applicable | geometry_generation_failed — the
        # State B copy, with the recorded reason as the detail
        note = "Engineering visualization not available on this " \
               "invention."
    reason = reason or ("no geometry was produced on this run — the "
                        "recorded class/bridge outcome is the truth")
    if running:
        return _tab("PENDING", "UNKNOWN", note,
                    reason=reason, render_reason=(reason or "")
                    if reason else None,
                    geometry_state=gst["geometry_state"],
                    presentation_cause=gst["presentation_cause"],
                    geometry_state_detail=gst["geometry_state_detail"])
    return _tab("UNAVAILABLE", "UNKNOWN", note,
                reason=reason,
                epistemic_status=(cio or {}).get("identity", {}).get(
                    "final_status") or "UNKNOWN",
                geometry_state=gst["geometry_state"],
                presentation_cause=gst["presentation_cause"],
                geometry_state_detail=gst["geometry_state_detail"])


# ---------------------------------------------------------------------------
# The six tabs
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# R451-C2.1 — the DISCOVERY PIPELINE projection (the stage strip)
# ---------------------------------------------------------------------------
# Seven product stages, each with a typed status derived ONLY from
# canonical records. This is the surface that answers "why don't I have
# a 3D model?" with the truth ("the system never got as far as
# inventing one") instead of a blanket "3D GEOMETRY UNAVAILABLE".
#
# Statuses (superset of the directive's two examples):
#   RECEIVED               the stage's recorded artifact exists
#   IN_PROGRESS            the run is active and work is at this stage
#   NOT_REACHED            execution has not arrived here (Art. XXV:
#                          not reached is NOT a measured zero)
#   STOPPED                execution arrived and did not complete; the
#                          recorded reason rides in `detail` (non-
#                          infrastructure: e.g. the presentation
#                          integrity gate returned FAIL)
#   PAUSED_INFRASTRUCTURE  execution arrived and stopped on
#                          infrastructure (transport, typed skip,
#                          retrieval failure) — Art. LXI: never a
#                          scientific statement
PIPELINE_STAGES = ("problem", "evidence", "mechanism", "invention",
                   "engineering", "visualization", "package")

# engine stages whose completion RECEIVES each product stage
_MECHANISM_ENGINE_STAGES = ("PREMISE_GATE", "SYNTHESIZE", "MECHANISM_SPACE",
                            "MULTI_SOURCE_DISCOVERY", "COLLISION")
_INVENTION_ENGINE_STAGES = ("PHYSICS", "ATTACK", "CONTRADICTION")
_ENGINEERING_ARTIFACTS = ("ENGINEERING_SPECIFICATION.json",
                          "BRIDGE_REPORT.json", "PARAMETRIC_MODEL.json")

# run statuses whose stop is infrastructure (Art. LXI) — mirrors
# user_state.py's transport/engine classes
_PIPELINE_INFRA_STATUSES = ("INTERRUPTED", "ERROR_TRANSPORT", "ERROR_BUILD",
                            "ERROR_RUN", "ERROR_STUCK",
                            "RUN_BLOCKED_TRANSPORT")


def _pipeline_row(key: str, label: str, received: bool, running: bool,
                  reached: bool, stage_failed: bool, stage_skipped: bool,
                  infra_stop: bool, detail: Optional[str]) -> Dict[str, Any]:
    """Coarse row status from canonical booleans; the detail line is
    verbatim from the records or None (never invented)."""
    if received:
        row = {"key": key, "label": label, "status": "RECEIVED"}
        if detail:
            row["detail"] = detail
        return row
    elif running and reached:
        row = {"key": key, "label": label, "status": "IN_PROGRESS"}
    elif stage_skipped:
        row = {"key": key, "label": label, "status": "STOPPED",
               "detail": detail or "the run recorded this stage as "
                                   "skipped/disabled"}
    elif stage_failed:
        row = ({"key": key, "label": label,
                "status": "PAUSED_INFRASTRUCTURE", "detail": detail}
               if infra_stop else
               {"key": key, "label": label, "status": "STOPPED",
                "detail": detail})
    elif reached:
        # arrived but its artifact is not recorded (live run mid-stage
        # or a terminal run whose stage produced nothing)
        row = ({"key": key, "label": label,
                "status": "PAUSED_INFRASTRUCTURE", "detail": detail}
               if infra_stop else
               {"key": key, "label": label,
                "status": "IN_PROGRESS" if running else "STOPPED",
                "detail": detail})
    else:
        row = {"key": key, "label": label, "status": "NOT_REACHED"}
    return row


def pipeline_projection(session: Dict[str, Any],
                        run_dir: Optional[Path],
                        running: bool,
                        state: Dict[str, Any],
                        evidence_tab: Dict[str, Any],
                        design_tab_data: Dict[str, Any],
                        ) -> List[Dict[str, Any]]:
    """The seven-stage DISCOVERY PIPELINE strip projection. Every cell
    is a recorded fact; nothing is inferred from a missing file (the
    design tab's typed geometry_state is consumed, never re-derived)."""
    stage_status = _rs._stage_status_map(session, run_dir)
    infra_stop = session.get("status") in _PIPELINE_INFRA_STATUSES

    def engine_row(stages) -> tuple:
        rec = [stage_status[s] for s in stages if s in stage_status]
        ok = any(_rs._classify_stage(s) == "DONE" for s in rec)
        failed = any(_rs._classify_stage(s) == "FAILED" for s in rec)
        skipped = any(_rs._classify_stage(s) == "SKIPPED" for s in rec)
        return ok, failed, skipped, bool(rec)

    # ---- 1. Problem — a session exists only after a problem was
    #         submitted: the strip's Problem row is the RECEIPT of the
    #         user's problem (the directive's blocked-run example shows
    #         "Problem ✓ RECEIVED" — the problem is saved even when the
    #         engine stopped before building anything from it)
    rows = [{"key": "problem", "label": "Problem",
             "status": "RECEIVED"}]

    # ---- 2. Evidence — the ledger's typed retrieval_state (C2.5)
    rstate = evidence_tab.get("retrieval_state") or "NOT_REACHED"
    if rstate == "RETRIEVED":
        n = evidence_tab.get("retrieved_count")
        rows.append(_pipeline_row(
            "evidence", "Evidence", received=True, running=running,
            reached=True, stage_failed=False, stage_skipped=False,
            infra_stop=infra_stop,
            # the envelope exists here: a numeric count (including a
            # measured zero) is the honest measured value (C2.5)
            detail=(f"{n} sources retrieved"
                    if isinstance(n, int) else None)))
    elif rstate == "PENDING":
        rows.append(_pipeline_row(
            "evidence", "Evidence", received=False, running=running,
            reached=True, stage_failed=False, stage_skipped=False,
            infra_stop=infra_stop, detail=None))
    elif rstate == "FAILED":
        rows.append({"key": "evidence", "label": "Evidence",
                     "status": "PAUSED_INFRASTRUCTURE",
                     "detail": evidence_tab.get("retrieval_note")
                     or "evidence retrieval recorded a transport-class "
                        "failure"})
    else:
        rows.append(_pipeline_row(
            "evidence", "Evidence", received=False, running=running,
            reached=False, stage_failed=False, stage_skipped=False,
            infra_stop=infra_stop, detail=None))

    # ---- 3. Mechanism — the engine's mechanism-stage records
    m_ok, m_failed, m_skipped, m_rec = engine_row(_MECHANISM_ENGINE_STAGES)
    rows.append(_pipeline_row(
        "mechanism", "Mechanism", received=m_ok, running=running,
        reached=m_rec or m_ok, stage_failed=m_failed,
        stage_skipped=m_skipped, infra_stop=infra_stop, detail=None))

    # ---- 4. Invention — the run's own invention record
    inv_state = (state.get("invention_state") or {}).get("state") or ""
    invention_artifacts = bool(
        (run_dir and (run_dir / "INVENTION_SPECIFICATION.json").exists())
        or inv_state == "EXISTS")
    i_ok, i_failed, i_skipped, i_rec = engine_row(
        _INVENTION_ENGINE_STAGES)
    rows.append(_pipeline_row(
        "invention", "Invention", received=invention_artifacts or i_ok,
        running=running, reached=i_rec or i_ok or invention_artifacts,
        stage_failed=i_failed, stage_skipped=i_skipped,
        infra_stop=infra_stop, detail=None))

    # ---- 5. Engineering — the engineering/geometry artifacts
    eng_artifacts = bool(
        run_dir and any((run_dir / a).exists()
                        for a in _ENGINEERING_ARTIFACTS))
    eng_received = eng_artifacts or \
        design_tab_data.get("geometry_state") in (
            "geometry_available", "visual_render_failed",
            "visual_complete")
    rows.append(_pipeline_row(
        "engineering", "Engineering", received=eng_received,
        running=running,
        reached=eng_received
        or design_tab_data.get("geometry_state")
        in ("geometry_not_applicable", "geometry_generation_failed"),
        stage_failed=design_tab_data.get("geometry_state")
        == "geometry_generation_failed",
        stage_skipped=False, infra_stop=infra_stop,
        detail=design_tab_data.get("geometry_state_detail")))

    # ---- 6. 3D visualization — the typed geometry_state decides
    gstate = design_tab_data.get("geometry_state") or "upstream_not_reached"
    gcause = design_tab_data.get("presentation_cause")
    if gstate == "visual_complete":
        rows.append({"key": "visualization", "label": "3D visualization",
                     "status": "RECEIVED"})
    elif gstate in ("geometry_available", "visual_render_failed"):
        if gcause in ("infrastructure", "renderer_unavailable"):
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "PAUSED_INFRASTRUCTURE",
                "detail": design_tab_data.get("geometry_state_detail")
                or "the presentation renderer is unavailable — the "
                   "engineering geometry remains available"})
        elif gcause == "rendering_in_progress":
            rows.append({"key": "visualization",
                         "label": "3D visualization",
                         "status": "IN_PROGRESS"})
        elif gcause == "gate_not_passed":
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "STOPPED",
                "detail": design_tab_data.get("geometry_state_detail")
                or "the render did not pass the presentation integrity "
                   "gate"})
        else:  # not_attempted — the join has not produced a render yet
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "STOPPED",
                "detail": design_tab_data.get("geometry_state_detail")
                or "no presentation render has been produced for this "
                   "geometry yet"})
    elif gstate in ("geometry_not_applicable",):
        rows.append({"key": "visualization",
                     "label": "3D visualization",
                     "status": "NOT_REACHED",
                     "detail": design_tab_data.get("geometry_state_detail")
                     or "engineering visualization is not applicable to "
                        "this invention"})
    else:  # upstream_not_reached | geometry_generation_failed
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": ("NOT_REACHED"
                       if gstate == "upstream_not_reached" else "STOPPED"),
            "detail": design_tab_data.get("geometry_state_detail")})

    # ---- 7. Package — the package machine layer's own terminal state.
    # A running run's PENDING means the state is OPEN, not that work is
    # at packaging — the row reads IN_PROGRESS only once the pipeline
    # frontier has reached engineering (the bridge builds the package
    # after geometry); before that it is honestly NOT_REACHED.
    pkg_block = state.get("package_state") or {}
    pkg_state = pkg_block.get("state") or "NOT_PRODUCED"
    if pkg_state == "READY":
        rows.append({"key": "package", "label": "Package",
                     "status": "RECEIVED"})
    elif pkg_state == "BLOCKED":
        rows.append({"key": "package", "label": "Package",
                     "status": "PAUSED_INFRASTRUCTURE",
                     "detail": pkg_block.get("blocked_reason")
                     or "the package build recorded a blocked state"})
    elif pkg_state == "PENDING" and running and eng_received:
        rows.append({"key": "package", "label": "Package",
                     "status": "IN_PROGRESS"})
    else:
        rows.append({"key": "package", "label": "Package",
                     "status": "NOT_REACHED"})
    return rows


def build_dossier(session: Dict[str, Any]) -> Dict[str, Any]:
    """The Technology Dossier for one investigation. Exists from the
    first moment the investigation has a canonical state (even PENDING)
    — directive section 3: never gated on 3D or package readiness."""
    sid = session.get("session_id")
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if run_dir and not run_dir.exists():
        run_dir = None
    running = session.get("status") in ("PENDING", "BUILDING_PROBLEM",
                                        "RUNNING")
    state = _rs.canonical_run_state(session)
    try:
        cio = _cio_mod.build_cio(session)
    except Exception:  # noqa: BLE001 — dossier stands on run_state
        cio = None

    # ---- machine-layer package artifacts (R425 elite layer), when the
    # bridge produced them — the SAME canonical fields the ZIP carries
    pkg_dir = _pkg_dir(run_dir)
    trace = _read_json(pkg_dir / "ENGINEERING_TRACEABILITY.json") \
        if pkg_dir else None
    roadmap = _read_json(pkg_dir / "UNKNOWN_ROADMAP.json") \
        if pkg_dir else None
    dex_contract = _read_json(pkg_dir / "04_DECISIVE_EXPERIMENT.json") \
        if pkg_dir else None
    eng_def = _read_json(pkg_dir / "02_ENGINEERING_DEFINITION.json") \
        if pkg_dir else None
    manifest = _read_json(pkg_dir / "PACKAGE_MANIFEST.json") \
        if pkg_dir else None

    evidence_state = state.get("evidence_state") or {}
    mechanism_state = state.get("mechanism_state") or {}
    invention_state = state.get("invention_state") or {}
    attack_state = state.get("attack_state") or {}
    experiment_state = state.get("experiment_state") or {}
    package_state = state.get("package_state") or {}
    generations = state.get("generations") or {}
    outcome = state.get("outcome") or ""
    # the decisive experiment object: run-dir DECISIVE_EXPERIMENT.json,
    # else the KILLER_EXPERIMENT envelope's own record
    dex_obj = _read_json(run_dir / "DECISIVE_EXPERIMENT.json") \
        if run_dir else None
    if dex_obj is None and run_dir:
        ke_env = _read_json(run_dir / "envelope_KILLER_EXPERIMENT.json")
        dex_obj = (ke_env or {}).get("killer_experiment")

    # ------------------------------------------------------------------
    # OVERVIEW (directive section 5)
    # ------------------------------------------------------------------
    unknowns = []
    if roadmap:
        unknowns = [
            {"statement": (u.get("statement") or u.get("what")
                           or "")[:220],
             "classification": u.get("classification"),
             "priority": u.get("priority")}
            for u in (roadmap.get("unknowns") or [])[:8]
            if isinstance(u, dict)]
    elif (cio or {}).get("identity"):
        inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json") \
            if run_dir else None
        unc = (inv or {}).get("uncertainties")
        if isinstance(unc, dict):
            unc = unc.get("value")
        if isinstance(unc, list):
            unknowns = [{"statement": str(u)[:220], "classification":
                         None, "priority": None} for u in unc[:8]]

    strongest_evidence = None
    ev_items = ((cio or {}).get("evidence") or {}).get("records") or []
    for r in ev_items:
        if r.get("evidence_class") in ("SOURCE_FACT", "EXTERNAL_PRECEDENT",
                                       "VERIFIED_EVIDENCE"):
            strongest_evidence = r
            break
    if strongest_evidence is None and ev_items:
        strongest_evidence = ev_items[0]

    # the strongest challenge: the attack envelope's own recorded
    # challenges — a FAIL verdict outranks everything else
    challenges = None
    if run_dir:
        ar_env = _read_json(run_dir / "envelope_ATTACK.json") or {}
        ar = ar_env.get("attack_results")
        ch_list = []
        if isinstance(ar, dict):
            ch_list = [{"challenge": dim, "verdict": verdict,
                        "response": (ar.get("reason") or "")[:240]}
                       for dim, verdict in (ar.get("attacks")
                                            or {}).items()]
            if ar.get("overall"):
                challenges = f"overall verdict {ar.get('overall')}"
        elif isinstance(ar, list):
            ch_list = [{"challenge": (a.get("challenge")
                                       or a.get("attack") or "")[:200],
                        "verdict": a.get("verdict") or a.get("result"),
                        "response": (a.get("response") or "")[:240]}
                       for a in ar[:6] if isinstance(a, dict)]
        if not challenges and ch_list:
            fails = [c for c in ch_list if c.get("verdict") == "FAIL"]
            pick = (fails or ch_list)[0]
            challenges = pick.get("challenge") or pick.get("verdict")

    experiment_summary = (
        (dex_obj or {}).get("name")
        or (dex_obj or {}).get("description")
        or (dex_obj or {}).get("hypothesis")
        or ((cio or {}).get("experiment") or {}).get(
            "decisive_experiment", {}).get("name")
        if isinstance(((cio or {}).get("experiment") or {}).get(
            "decisive_experiment"), dict)
        else None)
    if experiment_summary is None:
        cex = ((cio or {}).get("experiment") or {}).get(
            "decisive_experiment")
        experiment_summary = (cex.get("name")
                              or cex.get("description")
                              or cex.get("hypothesis")) \
            if isinstance(cex, dict) else None

    if running:
        overview_avail, overview_epi = "AVAILABLE", "COMPUTED"
        overview_note = ("the dossier updates as the investigation "
                         "records real backend events — nothing here is "
                         "fabricated")
    else:
        overview_avail, overview_epi = "AVAILABLE", "COMPUTED"
        overview_note = ("derived from the run's persisted artifacts — "
                         "every field traces to a record")

    # R435 scaffolding guard: mechanism / challenge / experiment text that
    # is prompt scaffolding (generation echo) is suppressed at the
    # projection layer and replaced by an explicit generation-incomplete
    # state — a distinct honest state from missing data (PENDING) and
    # from a legitimate unknown (NOT_ESTABLISHED / UNKNOWN).
    raw_mechanism = ((cio or {}).get("identity", {}).get("mechanism")
                     or mechanism_state.get("mechanism"))
    # R436 fix: the CIO mechanism is frequently the canonical MECHANISM
    # OBJECT (mechanism/intervention/expected_effect — the shape
    # INVENTION_SPECIFICATION.mechanism.value carries). Project the
    # mechanism SENTENCE before the scaffold guard: a dict is not
    # scaffolding, and a REAL dict-shaped mechanism misreported as a
    # generation failure is exactly the honest-state defect the guard
    # exists to prevent (observed live: both ts_387d8467cbb5 and the
    # fresh R436 EV run carry real mechanisms the overview suppressed).
    if isinstance(raw_mechanism, dict):
        raw_mechanism = (raw_mechanism.get("mechanism")
                         or raw_mechanism.get("value"))
    mechanism = _suppress_scaffold(raw_mechanism)
    mechanism_generation_failed = (
        raw_mechanism is not None and mechanism is None)
    challenges = _suppress_scaffold(challenges) if challenges else challenges
    experiment_summary = (_suppress_scaffold(experiment_summary)
                          if experiment_summary else experiment_summary)
    if mechanism_generation_failed:
        overview_note = ("the architecture generator did not produce a "
                         "usable mechanism for the surviving generation "
                         "(schema placeholder echo, rejected at the "
                         "projection boundary) — the run record keeps "
                         "the raw field; it is not presented as the "
                         "invention")

    overview = _tab(
        overview_avail, overview_epi, overview_note,
        problem=session.get("user_text"),
        # the mechanism field the PACKAGE also builds from: the
        # INVENTION_SPECIFICATION's mechanism (the canonical invention
        # state, Art. X) — the SYNTHESIZE envelope's mechanism_map is
        # the intermediate stage record and only a fallback
        mechanism=mechanism,
        mechanism_generation_failed=mechanism_generation_failed,
        invention_state=invention_state.get("state")
        or invention_state.get("maturity")
        or (generations.get("current_invention") or {}).get("maturity"),
        strongest_evidence=strongest_evidence,
        strongest_challenge=challenges,
        maturity=(cio or {}).get("maturity"),
        key_unknowns=unknowns,
        decisive_experiment=experiment_summary,
        epistemic_status=(cio or {}).get("identity", {}).get(
            "final_status") or "UNKNOWN",
        status_line=_status_line(session, cio, state),
    )

    # ------------------------------------------------------------------
    # DESIGN / EVIDENCE / ENGINEERING / EXPERIMENT / TRANSFER
    # ------------------------------------------------------------------
    design = design_tab(session, cio)
    evidence = evidence_ledger(session)

    eng_present = bool((cio or {}).get("engineering", {})
                       .get("specification_present")) or bool(eng_def)
    if eng_present:
        engineering = _tab(
            "AVAILABLE", "ENGINEERING_DEFINED",
            ("the engineering definition the package carries — same "
             "canonical source (R430.1 section 16)"),
            parameters=((cio or {}).get("engineering")
                        or {}).get("parameters"),
            failure_modes=((cio or {}).get("engineering")
                           or {}).get("failure_modes"),
            constraints=((cio or {}).get("engineering")
                         or {}).get("constraints"),
            assumptions=((cio or {}).get("engineering")
                         or {}).get("assumptions"),
            causal_chain=((cio or {}).get("engineering")
                          or {}).get("causal_chain"),
            traceability=(
                {"coverage": (trace or {}).get("coverage"),
                 "state": (trace or {}).get("state")}
                if trace else None),
            build_steps=(eng_def or {}).get("build_steps"),
        )
    elif running:
        engineering = _tab(
            "PENDING", "UNKNOWN",
            "engineering definition pending — the investigation has "
            "not reached the engineering stage")
    else:
        engineering = _tab(
            "UNAVAILABLE", "UNKNOWN",
            "no engineering definition on this run — parameters were "
            "not sourced (the recorded reason is the truth, never a "
            "gap in wording)")

    if experiment_state.get("decisive_experiment_present") \
            or dex_contract or dex_obj:
        experiment = _tab(
            "AVAILABLE", "COMPUTED",
            ("the decisive (falsification) experiment contract — "
             "buyer-runnable fields or explicit "
             "NOT_DEFINED_IN_CANONICAL_STATE (R430.1 section 5 / R425)"),
            recorded=dex_obj,
            contract=(dex_contract or {}).get("contract"),
            contract_completeness=(dex_contract or {}).get(
                "contract_completeness"),
            status="SPECIFIED_NOT_EXECUTED",
            execution_note=("specifying a decisive experiment is the "
                            "machine's job; executing it is a physical "
                            "act Toscanini never claims (Art. XXXVIII)"),
        )
    elif running:
        experiment = _tab(
            "PENDING", "UNKNOWN",
            "decisive experiment design pending")
    else:
        experiment = _tab(
            "NOT_ESTABLISHED", "UNKNOWN",
            "no decisive experiment was established on this run")

    pkg = _cio_mod._package_info(run_dir) if run_dir \
        and run_dir.exists() else None
    pkg_complete = bool((pkg or {}).get("complete"))
    # R443: the Article-LXXII typed release state — the download link
    # carries it so the button is never a silent "complete package"
    # while the visual release is blocked (render skipped + package
    # complete + plain download = the ambiguous state, eliminated)
    release_state = None
    if run_dir and Path(run_dir).exists():
        _hr = Path(run_dir) / "MODEL" / "3D" / "HERO_RELEASE_STATE.json"
        try:
            import json as _json
            release_state = _json.loads(_hr.read_text())
        except Exception:  # noqa: BLE001 — honest absent
            release_state = None
    release_blocked = bool((release_state or {}).get("release_blocked"))
    if pkg_complete:
        transfer = _tab(
            "AVAILABLE",
            "ENGINEERING_DEFINED",
            ("the technology transfer package for this investigation"
             if not release_blocked else
             "the engineering evaluation draft for this investigation — "
             "the Visual Quality Gate did not pass/run (Article LXXII): "
             "the package contains zero visual artifacts by design and "
             "the buyer release is blocked until the visual gate passes"),
            download=(f"/api/sessions/{sid}/package"
                      if not release_blocked else
                      f"/api/sessions/{sid}/package"
                      "?release=engineering_draft"),
            package_state=("RELEASED" if not release_blocked else
                           "ENGINEERING_DRAFT_VISUAL_RELEASE_PENDING"),
            visual_gate_verdict=((release_state or {}).get(
                "gate_verdict") if release_blocked else None),
            package_maturity=(pkg or {}).get("maturity"),
            package_kind=(pkg or {}).get("package_kind"),
            zip_name=(pkg or {}).get("zip_name"),
            document_count=((cio or {}).get("downloads")
                            or {}).get("document_count"),
            package_origin=((cio or {}).get("downloads")
                           or {}).get("package_origin"),
            completeness=(manifest or {}).get("completeness")
            or (manifest or {}).get("package_completeness"),
            evidence_coverage=(
                {"used_in_design": evidence.get("used_count"),
                 "retrieved": evidence.get("retrieved_count")}
            if evidence.get("availability") == "AVAILABLE" else None),
            validation_state=(cio or {}).get("maturity"),
            decisive_experiment=experiment_summary,
            key_unknowns=unknowns,
            build_requirements=(eng_def or {}).get("build_steps"),
            primary_action="DOWNLOAD TECHNOLOGY PACKAGE",
        )
    elif running:
        transfer = _tab(
            "PENDING", "UNKNOWN",
            "technology package pending — built automatically when the "
            "investigation completes with a surviving architecture")
    else:
        # R447 Phase 2: the canonical terminal object (run_state.
        # package_terminal_state) — the blocked stage/reason and the
        # typed next_action from the run's OWN records (the compiler's
        # PACKAGE_BUILD_BLOCKED.json + the persisted gate verdict),
        # never a generic guess (the R446-HF Case C defect: the reason
        # existed on disk but no product route surfaced it)
        blocked_stage = package_state.get("blocked_stage")
        blocked_reason = package_state.get("blocked_reason")
        next_action = (package_state.get("next_action") or {})
        if blocked_stage:
            why = (f"the package build was BLOCKED at {blocked_stage}"
                   + (f" — {blocked_reason}"
                      if blocked_reason else "")
                   + f". {next_action.get('text', '')}".rstrip(".")
                   + ".")
        else:
            why = (next_action.get("text")
                   or ("no technology package on this run — the "
                       "recorded reason is the truth"))
        transfer = _tab(
            "NOT_ESTABLISHED", "UNKNOWN", why,
            package_state=package_state.get("package_state"),
            package_blocked_stage=blocked_stage,
            package_blocked_reason=(blocked_reason
                                    if isinstance(blocked_reason, str)
                                    else None),
            package_next_action=next_action.get("action"),
            package_release_verdict=(
                (package_state.get("release_verdict") or {})
                .get("verdict")),
        )

    # ------------------------------------------------------------------
    # FALSIFICATION DOSSIER (directive section 14) — only when a
    # candidate was scientifically rejected. Infrastructure failures
    # get the VALIDATION INCOMPLETE card instead (never the same state,
    # Art. LXI).
    # ------------------------------------------------------------------
    falsification = _falsification(session, run_dir, generations,
                                   outcome)

    # R451-C2.1: the DISCOVERY PIPELINE strip projection — consumed by
    # the run page's top strip; answers "why don't I have a 3D model?"
    # from recorded facts only
    pipeline = pipeline_projection(session, run_dir, running, state,
                                   evidence, design)

    return {
        "kind": "TECHNOLOGY_DOSSIER",
        "schema_version": "1.0.0",
        "investigation_id": sid,
        "derived_from": (
            "canonical run state (session record, stage envelopes, "
            "CIO, bridge report, package machine layer) — a "
            "projection, never a second source of truth (Art. X)"),
        "running": running,
        "pipeline": pipeline,
        "tabs": {
            "overview": overview,
            "design": design,
            "evidence": evidence,
            "engineering": engineering,
            "experiment": experiment,
            "transfer": transfer,
        },
        "falsification": falsification,
    }


def _status_line(session: Dict, cio: Optional[Dict],
                 state: Dict) -> str:
    """Directive section 5's TECHNOLOGY STATUS block — honest states
    only, never wording that implies physical validation (Art.
    XXXVIII)."""
    m = (cio or {}).get("maturity") or {}
    outcome = state.get("outcome") or ""
    lines = []
    if outcome == "FALSE_PREMISE_INCOHERENT":
        lines.append("The problem premise was rejected as physically "
                     "incoherent.")
    elif outcome in ("INVENTION_SURVIVED", "INVENTION_REQUIRES_EXPERIMENT",
                     "INVENTION_UNDER_DEVELOPMENT"):
        lines.append("Candidate survives current computational "
                     "challenge.")
    lines.append(f"Engineering definition: "
                 f"{'AVAILABLE' if (cio or {}).get('engineering', {}).get('specification_present') else 'NOT ESTABLISHED'}")
    lines.append(f"3D geometry: "
                 f"{'AVAILABLE' if ((cio or {}).get('geometry') or {}).get('present') else 'NOT PRODUCED'}")
    lines.append("Physical validation: "
                 + ("NOT ESTABLISHED"
                    if not m.get("experimentally_verified")
                    else "ESTABLISHED VIA REALITY LOOP"))
    dex_present = bool(((cio or {}).get("experiment") or {}).get(
        "decisive_experiment"))
    lines.append(f"Decisive experiment: "
                 f"{'DEFINED' if dex_present else 'NOT DEFINED'}")
    n_unknown = len(((cio or {}) or {}).get("key_unknowns") or [])
    if n_unknown:
        lines.append(f"{n_unknown} material unknowns remain.")
    return " ".join(lines)


def _falsification(session: Dict, run_dir: Optional[Path],
                   generations: Dict, outcome: str) -> Optional[Dict]:
    """Directive section 14: the honest failure artifact. Present ONLY
    when a scientific rejection actually happened (premise rejected, or
    a generation was challenged and killed). Infrastructure failure ->
    VALIDATION INCOMPLETE (separate block, never a scientific claim)."""
    status = session.get("status") or ""
    infra = status in ("ERROR_TRANSPORT", "ERROR_BUILD", "ERROR_RUN",
                       "ERROR_STUCK", "INTERRUPTED",
                       "RUN_BLOCKED_TRANSPORT") or \
        (status == "COMPLETE" and outcome == "RUN_BLOCKED")
    if infra:
        return {
            "kind": "VALIDATION_INCOMPLETE",
            "cause": "infrastructure failure",
            "detail": ((session.get("error")
                        or "the recorded failure detail")[:400]),
            "scientific_conclusions": "NOT ESTABLISHED",
            "note": ("the challenge could not be completed because of "
                     "infrastructure; no scientific conclusion was "
                     "assigned (Art. LXI)"),
        }

    killed = [g for g in (generations.get("generations") or [])
              if (g.get("challenge") or {}).get("killed")]
    if outcome == "FALSE_PREMISE_INCOHERENT":
        pg = (_read_json(run_dir / "envelope_PREMISE_GATE.json")
              or {}).get("premise_gate") or {} if run_dir else {}
        return {
            "kind": "FALSIFICATION_DOSSIER",
            "initial_candidate": session.get("user_text"),
            "challenge_condition": "premise gate — physical coherence "
                                   "of the stated problem",
            "observed_failure": "the premise was evaluated against "
                                "physical coherence and rejected "
                                "BEFORE synthesis",
            "rejected_mechanism": None,
            "why_it_failed": (pg.get("explanation")
                              or "recorded on the premise gate envelope"),
            "what_remains_unknown": ("whether a reformulated premise "
                                     "is coherent — reformulate and "
                                     "run again"),
            "epistemic_class": "COMPUTED",
            "basis": "envelope_PREMISE_GATE.json + final_state.json",
        }
    if killed:
        g = killed[-1]
        ch = g.get("challenge") or {}
        diag = g.get("diagnosis") or {}
        return {
            "kind": "FALSIFICATION_DOSSIER",
            "initial_candidate": (g.get("architecture") or {}).get(
                "mechanism") or (g.get("architecture") or {}).get(
                "intervention"),
            "challenge_condition": str(
                ch.get("kill_stage") or "the challenge gauntlet"),
            "observed_failure": ch.get("kill_reason")
            or ch.get("attack_overall") or "recorded on the lineage",
            "rejected_mechanism": (g.get("architecture") or {}).get(
                "mechanism"),
            "why_it_failed": diag.get("cause")
            or (diag.get("basis") or ["recorded on the lineage"])[0],
            "what_remains_unknown": (g.get("stop_note")
                                     or (generations.get("stop_reason")
                                         or "the recorded stop reason")),
            "epistemic_class": "COMPUTED",
            "basis": f"INVENTION_LINEAGE.json#gen={g.get('gen')}",
            "auditable": True,
        }
    if status == "COMPLETE" and outcome == "NO_DEFENSIBLE_INVENTION":
        # honest evolution state (R416): never a dead-end sentence —
        # the generations record is the failure artifact
        return {
            "kind": "DEVELOPMENT_RECORD",
            "note": ("architectures were explored and the machine "
                     "stopped honestly — the lineage and cemetery "
                     "records are the auditable artifact"),
            "stop_reason": generations.get("stop_reason"),
            "basis": "INVENTION_LINEAGE.json",
        }
    return None


# ---------------------------------------------------------------------------
# Package <-> Dossier consistency (directive section 16)
# ---------------------------------------------------------------------------
def dossier_package_consistency(session: Dict[str, Any]) -> Dict[str, Any]:
    """Acceptance check: the Dossier and the downloaded package must
    derive from the SAME canonical state. This compares the dossier
    projection against the package's own machine-layer records — both
    derived from the run artifacts; any disagreement is a defect (no
    duplicated independently authored state)."""
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    checks: List[Dict[str, Any]] = []
    ok = True
    if not run_dir or not run_dir.exists() or not _pkg_dir(run_dir):
        return {"consistent": None, "checks": checks,
                "note": "no package on this run — nothing to compare "
                        "(honest, not a pass)"}
    d = build_dossier(session)
    pkg_dir = _pkg_dir(run_dir)
    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json") or {}
    eng_def = _read_json(pkg_dir / "02_ENGINEERING_DEFINITION.json") or {}
    dex = _read_json(pkg_dir / "04_DECISIVE_EXPERIMENT.json") or {}
    roadmap = _read_json(pkg_dir / "UNKNOWN_ROADMAP.json") or {}
    manifest = _read_json(pkg_dir / "PACKAGE_MANIFEST.json") or {}

    def check(name: str, a: Any, b: Any, cmp: str = "eq") -> None:
        nonlocal ok
        if cmp == "eq":
            passed = a == b
        elif cmp == "prefix":
            passed = str(b or "").startswith(str(a or "")) if a \
                else True
        elif cmp == "link":
            # both sides derive from the SAME canonical field — the
            # check asserts identity linkage (run_id binding), not
            # byte equality of two projections of one field
            passed = bool(a) and bool(b)
        else:  # pragma: no cover
            passed = False
        if not passed:
            ok = False
        checks.append({"field": name, "dossier": str(a)[:120],
                       "package": str(b)[:120], "consistent": passed})

    # problem: the package builds its problem statement from the SAME
    # canonical field the dossier renders (run_result.user_text ==
    # session.user_text); the manifest binds the package to this run.
    check("problem", d["tabs"]["overview"]["problem"],
          session.get("user_text"), "eq")
    check("package_run_binding", d["investigation_id"],
          manifest.get("run_id"), "eq")
    # mechanism
    check("mechanism", d["tabs"]["overview"]["mechanism"],
          (inv.get("mechanism") or {}).get("value")
          if isinstance(inv.get("mechanism"), dict)
          else inv.get("mechanism"), "eq")
    # evidence ids (the used set must match)
    ledger = d["tabs"]["evidence"]
    inv_ev = inv.get("evidence")
    used_pkg: set = set()
    if isinstance(inv_ev, dict):
        used_pkg = {str(x) for x in (inv_ev.get("evidence_ids") or [])}
    used_dossier = {i["id"] for i in (ledger.get("items") or [])
                    if i.get("used_in_design")}
    check("evidence_used_ids", sorted(used_dossier), sorted(used_pkg))
    # engineering state
    check("engineering_state",
          d["tabs"]["engineering"]["availability"] == "AVAILABLE",
          bool(eng_def))
    # experiment
    check("experiment_defined",
          d["tabs"]["experiment"]["availability"] == "AVAILABLE",
          bool(dex.get("contract")))
    # unknowns
    dossier_unknowns = [
        u.get("statement") for u in
        (d["tabs"]["overview"].get("key_unknowns") or [])]
    pkg_unknowns = [
        (u.get("statement") or u.get("what")) for u in
        (roadmap.get("unknowns") or [])[:len(dossier_unknowns) or None]
        if isinstance(u, dict)]
    check("unknowns", dossier_unknowns, pkg_unknowns)
    # epistemic status + maturity binding
    check("epistemic_status",
          d["tabs"]["overview"]["epistemic_status"],
          session.get("final_status") or "UNKNOWN")
    check("package_maturity",
          d["tabs"]["transfer"].get("package_maturity"),
          manifest.get("package_maturity"))
    return {"consistent": ok, "checks": checks,
            "note": ("both projections derive from the same run "
                     "artifacts; disagreement means one author drifted "
                     "— a defect, never a rendering choice")}
