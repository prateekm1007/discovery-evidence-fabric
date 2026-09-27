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

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def _read_pkg_zip_json(run_dir: Optional[Path],
                       rel: str) -> Optional[Dict[str, Any]]:
    """Read one machine-layer JSON from the run-root package ZIP.

    Restart-resilience (R510 production closure): the promoted
    TECHNOLOGY_PACKAGE/ tree is not part of the durable snapshot, so
    after a container rebuild only the run-root ZIP carries the
    canonical machine layers. The ZIP is byte-complete and
    manifest-hashed — reading it read-only is recovery from the
    authority, never fabrication (Art. X/XXV). Returns None when no
    ZIP or no such member exists.
    """
    if not run_dir:
        return None
    try:
        zips = sorted(
            run_dir.glob("TECHNOLOGY_TRANSFER_PACKAGE*.zip")) or \
            sorted(run_dir.glob("TECHNOLOGY_PACKAGE_*.zip"))
        if not zips:
            return None
        import zipfile
        with zipfile.ZipFile(zips[0]) as zf:
            for name in ("TECHNOLOGY_PACKAGE/" + rel, rel):
                try:
                    raw = zf.read(name)
                except KeyError:
                    continue
                doc = json.loads(raw.decode("utf-8"))
                return doc if isinstance(doc, dict) else None
    except Exception:  # noqa: BLE001 — absent stays absent
        return None
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

    R452-C2: the measured outcome is TYPED at this boundary — the
    five-state vocabulary the directive names lives HERE, not in the
    browser. A measured zero and a measured positive are DIFFERENT
    typed states, decided by the backend from the envelope's own
    count; the UI consumes them verbatim and never re-derives them
    from a raw number (the same boundary rule as _geometry_state).

      retrieval_state:
        NOT_REACHED        — the run stopped before retrieval executed
        PENDING            — the run is running, retrieval has not landed
        FAILED             — the run manifest records RETRIEVE failed
        RETRIEVED_ZERO     — the envelope exists; retrieval MEASURED zero
        RETRIEVED_POSITIVE — the envelope exists; retrieval MEASURED > 0
        RETRIEVED          — (legacy 4-state era value) readable by
                             consumers, never emitted by this writer
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
    # R452-C2: the measured outcome is a TYPED state, decided here —
    # a measured zero (RETRIEVED_ZERO) and a measured positive
    # (RETRIEVED_POSITIVE) are different facts and must never be
    # collapsed into one another or into a not-reached state (Art.
    # XXV; the R452-C2 directive's five-state vocabulary).
    measured_state = "RETRIEVED_ZERO" if not items else "RETRIEVED_POSITIVE"
    return _tab(
        status, "RETRIEVED",
        ("every item is a custody-frozen record from this run's "
         "retrieval envelope; used-in-design is decided by the "
         "invention specification's own evidence index"),
        items=items,
        # the envelope exists: the counts are MEASURED (a zero here is
        # a real measured zero — Art. XXI.3/XXV the other way round)
        retrieval_state=measured_state,
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
#   geometry_available          a certified canonical geometry artifact
#                               exists (R451-C2.4 §2: the NINE mandatory
#                               proofs — identity, SHA, generation,
#                               container validity, explicit authority)
#   geometry_unverified         a geometry artifact candidate exists but
#                               its mandatory certification is
#                               incomplete (R451-C2.4 §2: the explicit
#                               typed unverified state — never a
#                               failure, never a silent pass)
#   visual_render_failed        geometry exists; the presentation render
#                               did not produce an approved render
#                               (renderer unavailable OR gate not passed
#                               — `presentation_cause` distinguishes)
#   visual_complete             render succeeded AND the visual gate
#                               verdict is PASS / COMPLETE_PASS —
#                               reachable ONLY through THE strict
#                               evaluator (R451-C2.4 §1: the CIO
#                               fallback can never produce it)
GEOMETRY_STATES = ("upstream_not_reached", "geometry_not_applicable",
                   "geometry_generation_failed", "geometry_available",
                   "geometry_unverified", "visual_render_failed",
                   "visual_complete")

# render-record statuses that mean the renderer produced pixels
_RENDERER_RAN = ("OK", "SUCCEEDED", "COMPLETE")

# ---------------------------------------------------------------------------
# R451-C2.3 (directive §1): the ARTIFACT CONTRACT lives in THE one
# canonical evaluator — toscanini/visual_join.py
# (evaluate_geometry_contract). The dossier and the watchdog consume the
# SAME implementation (directive §8: one evaluator, no second state
# machine). The authoritative conditions for geometry_available:
#
#   a canonical geometry artifact exists AND is non-zero AND carries a
#   valid artifact identity AND the generation identities match AND
#   every recorded SHA matches the bytes on disk AND the engineering
#   authority is explicit AND no contradicting terminal failure is
#   recorded.
#
# A route string ("/api/run/x/model") NEVER establishes geometry; a
# missing engineering class stays UNKNOWN; legacy boolean-only
# projections remain readable but never inherit the current
# ENGINEERING_DEFINED authority. The two boundary states
# (ENGINEERING_GEOMETRY_READY vs VISUAL_INPUT_READY) are separate
# contract fields — a valid STEP may establish the first and never the
# second (the visual boundary requires the actual canonical GLB).
# Infrastructure-class outcomes (BLOCKED_TRANSPORT, NO_MODEL_NO_LLM)
# are NEVER failures (Art. LXI).
# ---------------------------------------------------------------------------


def _geometry_artifact_contract(session: Dict[str, Any],
                                run_dir: Optional[Path],
                                geom: Dict[str, Any]) -> Dict[str, Any]:
    """Delegate to THE canonical evaluator (toscanini/visual_join.py).
    Kept as the dossier's import point so the strip and the design tab
    consume the same contract the watchdog attacks."""
    from toscanini import visual_join as _vj
    return _vj.evaluate_geometry_contract(session, run_dir, geom)


def _renders_cause(renders: Dict[str, Any]) -> Tuple[str, Optional[str],
                                                     Optional[str]]:
    """The pre-receipt fallback: the render-side state + cause from the
    CIO renders block alone. R451-C2.4 §1 SUPERSESSION — the weak
    fallback path is ELIMINATED: the strict evaluator is the only
    current-state authority, and a CIO-block gate verdict reached
    through this fallback is EXPLICITLY UNVERIFIED HISTORICAL STATE,
    never visual_complete. The unknown-authority + stale-CIO-PASS
    attack (unknown engineering authority + a stale CIO visual PASS
    -> NOT VISUAL_READY) is closed exactly here: this function can no
    longer return `visual_complete` in ANY branch. The render-side
    failure/pending facts stay readable as they always were. Returns
    (geometry_state, presentation_cause, detail)."""
    status = str(renders.get("status") or "")
    verdict = ((renders.get("visual_gate") or {}).get("verdict")) \
        if isinstance(renders.get("visual_gate"), dict) else None
    if verdict in ("PASS", "COMPLETE_PASS"):
        # R451-C2.4 §1: a CIO-block gate verdict without the strict
        # evaluator's verification is an explicitly unverified
        # historical render — READABLE, never visual_complete, never
        # current visual readiness
        return ("geometry_available", "legacy_render_unverified",
                "a historical render is recorded in the projection, "
                "but it predates (or bypasses) the verifiable identity "
                "chain — the presentation state is explicitly "
                "unverified (R451-C2.4 §1)")
    if status in _RENDERER_RAN and verdict is not None:
        # the renderer produced pixels and the gate said no (State D)
        return ("visual_render_failed", "gate_not_passed",
                f"the render completed but the presentation "
                f"integrity gate returned {verdict}")
    if "SKIPPED" in status or status in (
            "FAILED", "RENDER_FAILED", "RENDER_TIMEOUT", "NOT_RUN",
            "INTERRUPTED"):
        cause = "renderer_unavailable"
        detail = renders.get("note") or \
            f"the presentation renderer recorded {status}"
        if "SKIPPED" in status or status == "INTERRUPTED":
            cause = "infrastructure"
        return "visual_render_failed", cause, detail
    if status in ("RUNNING", "RENDERING", "PENDING"):
        return ("geometry_available", "rendering_in_progress",
                "the presentation render job is running")
    # no render record at all: the geometry exists and the
    # presentation join has not produced an approved render yet —
    # exactly the BS-003 surface the R451 watchdog also checks
    return ("geometry_available", "not_attempted",
            "no presentation render record exists for this geometry "
            "yet")


def _geometry_state(session: Dict[str, Any], geom: Dict[str, Any],
                    renders: Dict[str, Any], running: bool) -> Dict[str, Any]:
    """The typed geometry/visual state + its recorded detail (R451-C2.3
    edition). The geometry side comes from THE artifact contract
    (toscanini/visual_join.py::evaluate_geometry_contract — the one
    canonical evaluator, byte-verified chain, explicit engineering
    authority); the render side comes from the same module's join
    evaluator (the invocation receipt is the boundary authority) with
    the CIO renders block as the pre-receipt fallback. Every branch
    reads a RECORDED field; absence of records is classified as
    `upstream_not_reached` (the honest state), never as a failure."""
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    from toscanini import visual_join as _vj
    contract = _vj.evaluate_geometry_contract(session, run_dir, geom)
    gst = contract["geometry_state"]

    # ---- geometry absent: the contract's recorded chain decides -------
    if gst != "geometry_available":
        detail = None
        outcome = contract["bridge_outcome"]
        cad = contract["cad_outcome"]
        if outcome == _vj.BRIDGE_NOT_APPLICABLE:
            detail = geom.get("bridge_why") or \
                "the recorded bridge outcome is NOT_VISUALIZABLE"
        elif outcome == _vj.BRIDGE_GEOMETRY_FAILED:
            detail = geom.get("bridge_why") or \
                "the recorded bridge outcome is GEOMETRY_FAILED"
        elif cad in _vj.CAD_LEDGER_FAILED:
            detail = (f"the CAD pipeline ledger recorded {cad}")
        elif cad in _vj.CAD_LEDGER_NOT_APPLICABLE:
            detail = (f"the CAD pipeline ledger recorded {cad}")
        elif cad in _vj.CAD_LEDGER_INFRA:
            detail = (f"the geometry build was blocked by "
                      f"infrastructure (the CAD pipeline ledger "
                      f"recorded {cad})")
        elif contract["pm_only"]:
            if running:
                detail = ("the engineering definition is recorded; the "
                          "geometry artifact has not been produced yet")
            elif (session or {}).get("status") == "COMPLETE":
                detail = ("the run completed with the engineering "
                          "definition recorded but no geometry artifact "
                          "was produced")
        elif not running and outcome == "NO_INVENTION":
            detail = ("no invention-side artifacts were recorded on this "
                      "run — the engineering stage had nothing to visualize")
        elif not running and outcome == "NO_SURVIVOR":
            # R455-LEAN-1 §1: the run's own DISCOVERY_RELEASE.json
            # attests no surviving, promoted candidate. The pinned
            # NO_INVENTION copy above stays byte-identical (R451-C2.1
            # directive copy, Art. XI); the release-era refusal gets
            # its own honest sentence.
            detail = ("no surviving invention was recorded on this "
                      "run — the engineering stage had nothing to "
                      "visualize")
        elif running:
            detail = ("the investigation has not reached the engineering "
                      "stage yet")
        elif contract.get("geometry_state_detail"):
            # the contract's own verification verdict (route strings
            # that resolve to nothing, SHA mismatches, identity gaps)
            detail = contract["geometry_state_detail"]
        return {"geometry_state": gst,
                "presentation_cause": None,
                "geometry_state_detail": detail,
                "geometry_contract": contract}

    # ---- geometry artifact exists: the visual join decides the rest ---
    # the join runs ONLY when the contract's engineering authority is
    # explicit (R451-C2.3 §1: presence alone never claims authority —
    # UNKNOWN/CONCEPTUAL artifacts stay readable, never engineering)
    join = _vj.evaluate_visual_join(
        session, geom, renders, running,
        engineering_geometry_ready=contract["engineering_geometry_ready"],
        geometry_state="geometry_available",
        contract=contract)
    if join["visual_join_state"] is not None:
        jstate, cause = _vj.join_cause(
            join["visual_join_state"], join.get("visual_join_cause"))
        if jstate:
            detail = join.get("visual_join_detail")
            if jstate == "visual_complete":
                detail = None
            return {"geometry_state": jstate,
                    "presentation_cause": cause or None,
                    "geometry_state_detail": detail,
                    "geometry_contract": contract,
                    "visual_join": join}
    # pre-receipt fallback: the CIO renders block stays READABLE only
    # as explicitly unverified historical state (R451-C2.4 §1) — this
    # path can no longer produce visual_complete, so the strict
    # evaluator is the ONE current-state authority
    fstate, fcause, fdetail = _renders_cause(renders)
    return {"geometry_state": fstate,
            "presentation_cause": fcause,
            "geometry_state_detail": fdetail,
            "visual_join": join}


def design_tab(session: Dict[str, Any],
               cio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    running = session.get("status") in ("PENDING", "BUILDING_PROBLEM",
                                        "RUNNING")
    geom = (cio or {}).get("geometry") or {}
    renders = ((cio or {}).get("visualization") or {}).get("renders") or {}
    gst = _geometry_state(session, geom, renders, running)
    join = gst.get("visual_join") or {}
    contract = gst.get("geometry_contract") or \
        _geometry_artifact_contract(session, run_dir, geom)
    # R435 (restored at the PRs #4->#5 merge battery, Art. LXIV rule 2):
    # the generation evolution projection is INDEPENDENT of the artifact
    # contract — the rows are the BRIDGE_REPORT's own generation history,
    # and the scaffold guard applies on EVERY path. A branch that drops
    # the rows loses the recorded evolution narrative — exactly the
    # information-loss class the external audit measured.
    evolution_rows = [
        {**row, "why": _suppress_scaffold(row.get("why"))}
        if isinstance(row, dict) else row
        for row in (geom.get("evolution") or [])
    ]
    # R451-C2.2 (directive §2) + R451-C2.3 (directive §1): the promotion
    # into the AVAILABLE branch is the ARTIFACT CONTRACT's decision —
    # contract['geometry_state'] == 'geometry_available' means the
    # byte-verified chain established it. A run whose geometry block is
    # present only through PARAMETRIC_MODEL.json (a definition, not an
    # artifact), a route string, or a legacy boolean-only flag is NEVER
    # promoted; it takes the honest unavailable/pending branch below
    # with the contract's own detail.
    promoted = bool(geom.get("present")) and \
        contract["geometry_state"] == "geometry_available"
    if promoted:
        if contract.get("engineering_authority") == "ENGINEERING" and \
                not geom.get("conceptual"):
            epistemic = "ENGINEERING_DEFINED"
        elif contract.get("engineering_authority") == "CONCEPTUAL" or \
                geom.get("conceptual"):
            epistemic = "HYPOTHESIZED"
        else:
            epistemic = "UNKNOWN"
        return _tab(
            "AVAILABLE",
            epistemic,
            ("interactive geometry from the canonical CAD source — the "
             "same parametric definition that builds the package "
             "models (no second geometry source, R430.1 section 17)"
             if epistemic == "ENGINEERING_DEFINED" else
             "geometry artifact projected available — the engineering "
             "authority is "
             f"{contract.get('engineering_authority') or 'UNKNOWN'} "
             "by the recorded chain (R451-C2.3: presence alone never "
             "claims engineering authority)"),
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
            evolution=evolution_rows,
            hero_eligibility=_hero_eligibility(geom),
            # R451-C2.1: the typed geometry/visual state — the UI's
            # States C/D/E consume THIS, never a missing-file inference
            # R451-C2.2: the typed visual-join state rides beside it
            # (the invocation→render→gate→hero chain, derived from the
            # run's own records; the UI consumes, never re-derives)
            # R451-C2.2: the artifact contract rides with it (the
            # strip's Engineering milestone consumes the contract's
            # recorded chain verdict, never artifact presence alone)
            geometry_state=gst["geometry_state"],
            presentation_cause=gst["presentation_cause"],
            geometry_state_detail=gst["geometry_state_detail"],
            geometry_contract=contract,
            # R451-C2.3 §2: the two separated boundary states —
            # ENGINEERING_GEOMETRY_READY (verified artifact + explicit
            # engineering authority) and VISUAL_INPUT_READY (the
            # canonical GLB contract the Visual Compiler consumes).
            # A valid STEP establishes the first and NEVER the second.
            engineering_authority=contract.get("engineering_authority"),
            engineering_geometry_ready=contract.get(
                "engineering_geometry_ready"),
            visual_input_ready=contract.get("visual_input_ready"),
            visual_input_basis=contract.get("visual_input_basis"),
            visual_join_state=join.get("visual_join_state"),
            visual_join_detail=join.get("visual_join_detail"),
            visual_join_cause=join.get("visual_join_cause"),
            pending_render_job=join.get("pending_render_job"),
            scores=geom.get("scores"),
            not_visualized=(geom.get("scores") or {}).get(
                "not_visualized") or [],
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
    elif gst["geometry_state"] == "geometry_unverified":
        # R451-C2.4 §2: an artifact candidate exists but the mandatory
        # certification is incomplete — the honest note names the
        # missing proofs (never a failure claim, never a silent pass)
        note = ("A geometry artifact is present on this run, but its "
                "mandatory identity could not be certified — the "
                "engineering authority is not established.")
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
                    evolution=evolution_rows,
                    geometry_state=gst["geometry_state"],
                    presentation_cause=gst["presentation_cause"],
                    geometry_state_detail=gst["geometry_state_detail"],
                    visual_join_state=join.get("visual_join_state"),
                    visual_join_detail=join.get("visual_join_detail"))
    return _tab("UNAVAILABLE", "UNKNOWN", note,
                reason=reason,
                epistemic_status=(cio or {}).get("identity", {}).get(
                    "final_status") or "UNKNOWN",
                evolution=evolution_rows,
                geometry_state=gst["geometry_state"],
                presentation_cause=gst["presentation_cause"],
                geometry_state_detail=gst["geometry_state_detail"],
                visual_join_state=join.get("visual_join_state"),
                visual_join_detail=join.get("visual_join_detail"))


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
# R451-C2.2 §3: the stages whose OWN canonical record can establish the
# Mechanism milestone (the premise gate and the discovery sweep are
# search activity — a mechanism RECORD is the milestone)
_MECHANISM_RECORD_STAGES = ("SYNTHESIZE", "MECHANISM_SPACE", "COLLISION")
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


def _canonical_stage_record(run_dir: Optional[Path],
                            stages: Tuple[str, ...]) -> Tuple[bool, bool]:
    """R451-C2.2 (directive §3): the CANONICAL-RECORD predicate for a
    milestone family. Returns (record_ok, record_failed): the family's
    milestone is RECEIVED only when a canonical stage record EXISTS on
    disk AND its own recorded status is OK — 'some stage in the family
    finished' is NEVER the definition of a product milestone. A record
    whose status is a failure -> record_failed (a STOPPED row)."""
    if not run_dir:
        return False, False
    for stage in stages:
        env = _read_json(Path(run_dir) / f"envelope_{stage}.json") \
            if run_dir.exists() else None
        if not env:
            continue
        last = None
        for entry in env.get("stage_log") or []:
            if isinstance(entry, dict) and entry.get("stage") == stage:
                last = str(entry.get("status") or "")
        if last == "OK":
            return True, False
        if last and last != "OK" and not (
                last.startswith("SKIPPED") or last.startswith("DISABLED")):
            return False, True
    return False, False


# R451-C2.3 (directive §7): package classification consumes TYPED
# canonical codes ONLY. The blocked record's `stage` universe is the
# package compiler's own typed vocabulary (the ONE writer,
# package_compiler._blocked): QUALITY_GATE_BLOCKED /
# MODEL_VALIDATION_FAILED / COMPILE_ERROR. Free-text reasons are
# NEVER classified (no substring mapping — the recorded reason rides
# verbatim in the row detail). A typed infrastructure stage, when the
# compiler records one, is the ONLY path to the INFRASTRUCTURE class.
_PKG_TYPED_STAGES = ("QUALITY_GATE_BLOCKED", "MODEL_VALIDATION_FAILED",
                     "COMPILE_ERROR")
_PKG_TYPED_INFRA_STAGES = ("TRANSPORT_BLOCKED", "INFRASTRUCTURE_BLOCKED")
# the scientific-substance gate families: problem fidelity (B), evidence
# integrity (F), causal integrity (G), semantic audit (U) — typed gate
# IDs from the run's own release verdict
_SCIENTIFIC_GATE_PREFIXES = ("B-", "F-", "G-", "U-")


def _package_blocked_class(pkg_block: Dict[str, Any]) -> Tuple[str, str]:
    """R451-C2.2 (directive §4) + R451-C2.3 (directive §7): BLOCKED is
    NOT automatically PAUSED_INFRASTRUCTURE, and the class is decided
    by TYPED canonical codes only — never by free-text inference:
      VISUAL_GATE     the Article LXXII release verdict (outranks all)
      INFRASTRUCTURE  a TYPED infrastructure stage (reserved codes;
                      today's compiler records none — an honest
                      reservation, not a guess)
      SCIENTIFIC      the quality gate's scientific-substance gate
                      families (B-/F-/G-/U- typed gate IDs)
      PACKAGE_INTEGRITY the compiler's typed integrity stages
      UNKNOWN         any unlisted stage — recorded verbatim, never
                      guessed into infrastructure (Art. XXV)
    Returns (class, row_status): INFRASTRUCTURE pauses the row
    (PAUSED_INFRASTRUCTURE); every other class is a typed STOPPED."""
    stage = str(pkg_block.get("blocked_stage") or "")
    release = pkg_block.get("release_verdict") or {}
    verdict = str(release.get("verdict") or "")
    if verdict == "VISUAL_RELEASE_BLOCKED":
        # the Article LXXII release block is the strongest recorded
        # verdict — it outranks everything else
        return "VISUAL_GATE", "STOPPED"
    if stage in _PKG_TYPED_INFRA_STAGES:
        # Art. LXI: a TYPED infrastructure stage pauses the row —
        # never presented as a quality verdict
        return "INFRASTRUCTURE", "PAUSED_INFRASTRUCTURE"
    if stage == "QUALITY_GATE_BLOCKED":
        failed = [str(g) for g in release.get("failed_gates") or []]
        if any(g[:2] in _SCIENTIFIC_GATE_PREFIXES for g in failed):
            return "SCIENTIFIC", "STOPPED"
        return "PACKAGE_INTEGRITY", "STOPPED"
    if stage in ("MODEL_VALIDATION_FAILED", "COMPILE_ERROR"):
        return "PACKAGE_INTEGRITY", "STOPPED"
    # a blocked record with an unclassified stage: the record is shown
    # verbatim, the class is honest UNKNOWN — never guessed into infra
    return "UNKNOWN", "STOPPED"


# R451-C2.3 (directive §4): the canonical invention record's required
# validity state. The Invention milestone is RECEIVED only when a
# canonical record exists AND carries its required content AND the
# run's own adjudication did not reject it. Empty objects, malformed
# JSON, placeholder text, and synthetic minimal records NEVER
# establish Invention (each is a typed negative control in the
# battery).
_INV_CORE_FIELDS = ("invention_id", "problem", "mechanism",
                    "causal_chain")
_PLACEHOLDER_VALUES = {"", "tbd", "n/a", "na", "none", "null",
                       "placeholder", "todo", "tbc", "xxx",
                       "lorem ipsum", "example", "sample"}
_REJECTED_FINAL_STATUSES = ("REJECTED", "MALFORMED_OR_FALSE_PREMISE")


def _unwrap_tagged(value: Any) -> Any:
    """Read through the canonical epistemic-tag wrapper
    ({value, epistemic_class, ...}) — invention_spec.tagged's shape."""
    if isinstance(value, dict) and "value" in value and \
            "epistemic_class" in value:
        return value.get("value")
    return value


def _invention_field_text(value: Any) -> str:
    value = _unwrap_tagged(value)
    if isinstance(value, dict):
        value = value.get("value") if "value" in value else \
            json.dumps(value, sort_keys=True)
    if isinstance(value, (list, tuple)):
        value = " ".join(str(v) for v in value)
    return str(value or "").strip()


def _invention_record_validity(run_dir: Optional[Path],
                               final_status: Optional[str]) -> Dict[str, Any]:
    """The canonical invention record's validity verdict (typed):
      VALID                 the record parses, carries every required
                            core field with real content, and the
                            run's adjudication did not reject it
      INVALID_EMPTY         the record exists but is an empty object
      INVALID_MALFORMED     the record is unparseable / not an object
      INVALID_PLACEHOLDER   a required core field carries placeholder
                            text
      INVALID_MINIMAL       a synthetic minimal record — required core
                            fields absent
      INVALID_ADJUDICATION  the run's own adjudication recorded the
                            rejection (the record describes a candidate
                            that did not survive — never a milestone)
      ABSENT                no canonical invention record exists
    A SURVIVOR_SELECTION record naming a surviving candidate is the
    canonical invention record of the survivor-selection era and
    satisfies the milestone only with the survivor actually recorded.
    """
    final = str(final_status or "").upper()
    if final in _REJECTED_FINAL_STATUSES:
        return {"validity": "INVALID_ADJUDICATION", "basis":
                f"the run's recorded adjudication is {final}"}
    inv = surv = None
    inv_malformed = False
    inv_path = run_dir / "INVENTION_SPECIFICATION.json" if run_dir else None
    if inv_path is not None and inv_path.is_file():
        try:
            loaded = json.loads(inv_path.read_text(encoding="utf-8"))
            inv = loaded if isinstance(loaded, dict) else None
            if inv is None:
                inv_malformed = True
        except (OSError, ValueError):
            # the file EXISTS but is not parseable — a malformed record,
            # never silently read as absent (Art. XXV)
            inv_malformed = True
    surv = _read_json(run_dir / "SURVIVOR_SELECTION.json") \
        if run_dir else None
    if inv is None and surv is None and not inv_malformed:
        return {"validity": "ABSENT",
                "basis": "no canonical invention record exists"}
    if inv_malformed:
        return {"validity": "INVALID_MALFORMED",
                "basis": ("the invention record exists but is not "
                          "parseable JSON — malformed, never absent")}
    if inv is None and surv is not None:
        # the survivor-selection record is the era's canonical record —
        # a recorded surviving candidate establishes the milestone
        survivors = surv.get("survivors") or surv.get("surviving") or []
        named = bool(survivors) or bool(surv.get("surviving_candidate"))
        return {"validity": "VALID" if named else "INVALID_MINIMAL",
                "basis": "the survivor-selection record"
                if named else
                "the survivor-selection record names no surviving "
                "candidate"}
    if not isinstance(inv, dict):
        return {"validity": "INVALID_MALFORMED",
                "basis": ("the invention record is not a readable "
                          "JSON object")}
    if not inv:
        return {"validity": "INVALID_EMPTY",
                "basis": "the invention record is an empty object"}
    missing = []
    placeholder = []
    for field in _INV_CORE_FIELDS:
        text = _invention_field_text(inv.get(field))
        if not text:
            missing.append(field)
        elif text.lower() in _PLACEHOLDER_VALUES:
            placeholder.append(field)
    if placeholder:
        return {"validity": "INVALID_PLACEHOLDER", "basis":
                f"placeholder content in {', '.join(placeholder)}"}
    if missing:
        return {"validity": "INVALID_MINIMAL", "basis":
                f"required core fields absent: {', '.join(missing)}"}
    return {"validity": "VALID",
            "basis": "the canonical invention record carries its "
                     "required validity state"}


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

    # ---- 1. Problem — a RECORDED problem exists (R451-C2.2 §3: the
    #         predicate is the problem record, not the session's mere
    #         existence): the structured problem.json the engine ran
    #         on, or the session's own recorded problem text (the
    #         submission receipt — a blocked-before-build run still
    #         received its problem; the detail names the basis)
    problem_record = bool(run_dir and (run_dir / "problem.json").exists())
    problem_text = bool((session.get("user_text") or "").strip())
    if problem_record:
        rows = [{"key": "problem", "label": "Problem",
                 "status": "RECEIVED"}]
    elif problem_text:
        rows = [{"key": "problem", "label": "Problem",
                 "status": "RECEIVED",
                 "detail": "the submitted problem is saved"}]
    else:
        rows = [{"key": "problem", "label": "Problem",
                 "status": "NOT_REACHED"}]

    # ---- 2. Evidence — the ledger's typed retrieval_state (C2.5;
    # R452-C2 five-state vocabulary; the legacy RETRIEVED value stays
    # readable — era normalization, never a silent translation)
    rstate = evidence_tab.get("retrieval_state") or "NOT_REACHED"
    if rstate in ("RETRIEVED", "RETRIEVED_ZERO", "RETRIEVED_POSITIVE"):
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

    # ---- 3. Mechanism — a CANONICAL MECHANISM RECORD exists
    #         (R451-C2.2 §3: the record, not "any stage in the family
    #         finished" — a premise gate that always executes must
    #         never stand in for mechanism work)
    m_record_ok, m_record_failed = _canonical_stage_record(
        run_dir, _MECHANISM_RECORD_STAGES)
    m_any_failed, m_any_skipped, m_rec = False, False, False
    for s in _MECHANISM_ENGINE_STAGES:
        cls = _rs._classify_stage(stage_status.get(s, ""))
        if cls == "FAILED":
            m_any_failed = True
        elif cls == "SKIPPED":
            m_any_skipped = True
        if stage_status.get(s):
            m_rec = True
    rows.append(_pipeline_row(
        "mechanism", "Mechanism", received=m_record_ok, running=running,
        reached=m_record_ok or m_rec or m_record_failed,
        stage_failed=m_record_failed or m_any_failed,
        stage_skipped=m_any_skipped and not m_record_ok,
        infra_stop=infra_stop, detail=None))

    # ---- 4. Invention — the canonical invention record at its
    #         REQUIRED VALIDITY STATE (R451-C2.3 §4: an empty,
    #         malformed, placeholder, synthetic-minimal, or
    #         adjudication-rejected record NEVER establishes
    #         Invention; engine-stage credit never substitutes)
    inv_state = (state.get("invention_state") or {}).get("state") or ""
    inv_validity = _invention_record_validity(
        run_dir, (session or {}).get("final_status"))
    invention_received = inv_validity["validity"] == "VALID" or \
        (inv_state == "EXISTS" and
         inv_validity["validity"] in ("VALID",))
    i_ok, i_failed, i_skipped, i_rec = engine_row(
        _INVENTION_ENGINE_STAGES)
    inv_detail = None if invention_received else \
        f"the invention record's validity is " \
        f"{inv_validity['validity']}: {inv_validity['basis']}"
    rows.append(_pipeline_row(
        "invention", "Invention", received=invention_received,
        running=running,
        reached=invention_received or i_rec or i_ok
        or inv_validity["validity"] != "ABSENT",
        stage_failed=i_failed, stage_skipped=i_skipped,
        infra_stop=infra_stop, detail=inv_detail))

    # ---- 5. Engineering — the engineering REALIZATION exists AND its
    #         authoritative state says valid (R451-C2.3 §3: the
    #         realization is the byte-verified canonical geometry with
    #         explicit ENGINEERING authority — a BRIDGE_REPORT
    #         DESCRIBES a realization and NEVER constitutes it, so a
    #         valid-looking bridge report without the canonical
    #         geometry cannot receive this milestone; a CONCEPTUAL or
    #         UNKNOWN authority never does either)
    gstate = design_tab_data.get("geometry_state") or "upstream_not_reached"
    contract = design_tab_data.get("geometry_contract") or {}
    eng_valid_states = ("geometry_available", "visual_render_failed",
                        "visual_complete")
    eng_received = gstate in eng_valid_states and \
        contract.get("engineering_authority") == "ENGINEERING"
    eng_artifacts = bool(
        run_dir and any((run_dir / a).exists()
                        for a in _ENGINEERING_ARTIFACTS))
    rows.append(_pipeline_row(
        "engineering", "Engineering", received=eng_received,
        running=running,
        reached=eng_received or eng_artifacts
        or gstate in ("geometry_not_applicable",
                      "geometry_generation_failed",
                      "geometry_unverified"),
        stage_failed=gstate == "geometry_generation_failed",
        stage_skipped=False, infra_stop=infra_stop,
        detail=design_tab_data.get("geometry_state_detail")))

    # ---- 6. 3D visualization — the typed geometry_state + the visual
    #         join decide (R451-C2.2 §5: an invocation that never ran is
    #         an explicit STOPPED failure — never silence, never an
    #         infra pause unless infrastructure actually caused it)
    gstate = design_tab_data.get("geometry_state") or "upstream_not_reached"
    gcause = design_tab_data.get("presentation_cause")
    jstate = design_tab_data.get("visual_join_state")
    jdetail = design_tab_data.get("visual_join_detail")
    if gstate == "visual_complete":
        rows.append({"key": "visualization", "label": "3D visualization",
                     "status": "RECEIVED"})
    elif jstate == "INVOCATION_MISSING":
        # the no-silent-gap failure: geometry ready, invocation never
        # recorded, no job pending — a typed STOPPED with the recorded
        # failure (NOT an infra pause, NOT a scientific statement)
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": "STOPPED", "blocked_class": "JOIN_FAILURE",
            "detail": jdetail
            or "the geometry-to-visual invocation did not run — "
               "recorded as an explicit join failure"})
    elif jstate == "RENDER_RECORD_MISSING":
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": "STOPPED", "blocked_class": "JOIN_FAILURE",
            "detail": jdetail
            or "the invocation says the renderer produced pixels but "
               "no render record exists — join integrity failure"})
    elif jstate == "RELEASE_UNVERIFIED":
        # R451-C2.3 §5: the gate passed but the release chain fails
        # closed (identity mismatch / missing release artifacts / hero
        # not the canonical GLB) — a typed STOPPED, never visual-ready
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": "STOPPED", "blocked_class": "RELEASE_UNVERIFIED",
            "detail": jdetail
            or "the gate passed but the release chain could not be "
               "verified — not visual ready (fail closed)"})
    elif jstate == "VISUAL_INPUT_NOT_READY":
        # R451-C2.3 §2: engineering geometry ready, the canonical GLB
        # the visual boundary consumes is not verifiable — a valid
        # STEP alone never proves the Visual Compiler's input
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": "STOPPED", "blocked_class": "VISUAL_INPUT",
            "detail": jdetail
            or "the canonical GLB required for presentation rendering "
               "was not produced on this run"})
    elif jstate == "INVOCATION_PENDING":
        # an interrupted recovery-owed job pauses; a running job is live
        job = design_tab_data.get("pending_render_job")
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": ("PAUSED_INFRASTRUCTURE" if job == "INTERRUPTED"
                       else "IN_PROGRESS"),
            "detail": jdetail})
    elif gstate == "geometry_unverified":
        # R451-C2.4 §2: the artifact candidate's certification is
        # incomplete — a typed STOPPED with the named missing proofs
        # (never NOT_REACHED: the bytes exist; never visual-ready)
        rows.append({
            "key": "visualization", "label": "3D visualization",
            "status": "STOPPED", "blocked_class": "IDENTITY_UNVERIFIED",
            "detail": design_tab_data.get("geometry_state_detail")
            or "the geometry artifact's mandatory identity could not "
               "be certified — the presentation state is explicitly "
               "unverified"})
    elif gstate in ("geometry_available", "visual_render_failed"):
        if gcause in ("infrastructure", "renderer_unavailable"):
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "PAUSED_INFRASTRUCTURE"
                if gcause == "infrastructure" else "STOPPED",
                "blocked_class": gcause.upper(),
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
                "status": "STOPPED", "blocked_class": "VISUAL_GATE",
                "detail": design_tab_data.get("geometry_state_detail")
                or "the render did not pass the presentation integrity "
                   "gate"})
        elif gcause == "release_unverified":
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "STOPPED", "blocked_class": "RELEASE_UNVERIFIED",
                "detail": design_tab_data.get("geometry_state_detail")
                or "the presentation could not be verified against the "
                   "canonical geometry — fail closed"})
        elif gcause == "visual_input_missing":
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "STOPPED", "blocked_class": "VISUAL_INPUT",
                "detail": design_tab_data.get("geometry_state_detail")
                or "the canonical GLB required for presentation "
                   "rendering was not produced on this run"})
        elif gcause == "legacy_render_unverified":
            # R451-C2.4 §1: a CIO-block render verdict reached without
            # the strict evaluator — readable as explicitly unverified
            # historical state, never visual-ready
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "STOPPED",
                "blocked_class": "LEGACY_RENDER_UNVERIFIED",
                "detail": design_tab_data.get("geometry_state_detail")
                or "a historical render is recorded, but it predates "
                   "(or bypasses) the verifiable identity chain — the "
                   "presentation state is explicitly unverified"})
        else:  # not_attempted — the join has not produced a render yet
            rows.append({
                "key": "visualization", "label": "3D visualization",
                "status": "STOPPED", "blocked_class": "NOT_ATTEMPTED",
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

    # ---- 7. Package — the package machine layer's own terminal state
    #         (R451-C2.2 §4: BLOCKED is NOT automatically an
    #         infrastructure pause — the canonical blocked stage /
    #         reason / release verdict decide the class). A running
    #         run's PENDING means the state is OPEN, not that work is
    #         at packaging — the row reads IN_PROGRESS only once the
    #         pipeline frontier has reached engineering (the bridge
    #         builds the package after geometry); before that it is
    #         honestly NOT_REACHED.
    pkg_block = state.get("package_state") or {}
    pkg_state = pkg_block.get("state") or "NOT_PRODUCED"
    if pkg_state == "READY":
        rows.append({"key": "package", "label": "Package",
                     "status": "RECEIVED"})
    elif pkg_state == "BLOCKED":
        blocked_class, row_status = _package_blocked_class(pkg_block)
        rows.append({
            "key": "package", "label": "Package",
            "status": row_status, "blocked_class": blocked_class,
            "detail": (f"package build blocked — {blocked_class.lower()}"
                       f": {pkg_block.get('blocked_reason')}"
                       if pkg_block.get("blocked_reason") else
                       f"package build blocked — "
                       f"{blocked_class.lower()}")})
    elif pkg_state == "PENDING" and running and eng_received:
        rows.append({"key": "package", "label": "Package",
                     "status": "IN_PROGRESS"})
    elif pkg_state == "NOT_PRODUCED" and not running and eng_received:
        # the frontier reached engineering and the run ended without a
        # package record — arrived, did not produce (never NOT_REACHED:
        # the packaging stage sits directly downstream of the bridge)
        rows.append({
            "key": "package", "label": "Package", "status": "STOPPED",
            "detail": "no package record exists — the package stage "
                      "did not produce a record on this run"})
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
    if roadmap is None:
        roadmap = _read_pkg_zip_json(run_dir, "UNKNOWN_ROADMAP.json")
    if roadmap is None:
        # restart-resilience: the promoted TECHNOLOGY_PACKAGE/ tree is
        # not part of the durable snapshot (only the run-root ZIP is),
        # so after a container rebuild the tree is absent while the
        # byte-complete ZIP remains — read the roadmap from the ZIP
        # read-only instead of reporting absence (Art. XXV).
        roadmap = _read_pkg_zip_json(
            run_dir, "UNKNOWN_ROADMAP.json")
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
            {"statement": (u.get("unknown_statement")
                           or u.get("statement") or u.get("what")
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
            # string items only: a dict repr is not a statement
            # (Art. XXV — absence over a fabricated-looking value)
            unknowns = [{"statement": str(u)[:220], "classification":
                         None, "priority": None} for u in unc[:8]
                        if isinstance(u, str)]

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
            release_state = _json.loads(_hr.read_text(encoding="utf-8"))
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
    if not roadmap:
        roadmap = _read_pkg_zip_json(run_dir, "UNKNOWN_ROADMAP.json") or {}
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
        (u.get("unknown_statement") or u.get("statement")
         or u.get("what")) for u in
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
