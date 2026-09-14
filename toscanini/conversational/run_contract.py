"""toscanini/conversational/run_contract.py — R446-C1 §11: the clean
high-level run contract.

Directive (verbatim intent): "The frontend should need approximately:
run_id, current_state, human_progress, next_action, artifacts,
blocking_reason, uncertainties. It should not need to interpret
internal ledgers. Do not create another competing state store. Use
canonical state."

This module PROJECTS the canonical state (run_state.py's DiscoveryRun
projection + the completion marker + the NBA controller record) into
the ~7-field contract. It is a VIEW: it holds no state of its own, it
invents no fields, and every projected value traces to a persisted
artifact (Art. X — one canonical authority, many projections).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from toscanini.conversational import product_events
from toscanini.conversational import stage_policy

CONTRACT_VERSION = "CODER1_RUN_CONTRACT/1.0.0"


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.is_file():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None
    return None


def _blocking_reason(session: Dict[str, Any],
                     run_dir: Optional[Path]) -> Optional[Dict[str, Any]]:
    """The honest blocker: infrastructure states and owner gates only
    (Art. LXI / LXV) — a scientific rejection is an OUTCOME, not a
    blocker, and is carried by current_state instead."""
    status = str(session.get("status") or "")
    if status.startswith("ERROR_") or status in (
            "RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY",
            "INTERRUPTED"):
        return {
            "kind": "INFRASTRUCTURE",
            "state": status,
            "detail": str(session.get("error") or "")[:400],
            "resumable": status in ("RUN_BLOCKED_TRANSPORT",
                                    "RUN_BLOCKED_CAPABILITY",
                                    "INTERRUPTED"),
        }
    if status == "AWAITING_CLARIFICATION":
        q = session.get("clarification") or {}
        return {
            "kind": "CLARIFICATION",
            "state": status,
            "question": q.get("question"),
            "field": q.get("field"),
            "resumable": True,
        }
    if run_dir and (run_dir / "BRIDGE_REPORT.json").is_file():
        bridge = _read_json(run_dir / "BRIDGE_REPORT.json") or {}
        if str(bridge.get("outcome") or "").startswith("SKIPPED"):
            return {
                "kind": "ARTIFACT_CAPABILITY",
                "state": bridge.get("outcome"),
                "detail": str(bridge.get("reason") or "")[:300],
                "resumable": True,
            }
    return None


def _artifacts(session: Dict[str, Any],
               run_dir: Optional[Path]) -> List[Dict[str, Any]]:
    """Artifact pointers derived from the run's OWN records (never
    from directory guessing: each entry cites the report that
    declared it)."""
    out: List[Dict[str, Any]] = []
    if not run_dir:
        return out
    cio = _read_json(run_dir / "CIO.json") \
        or _read_json(run_dir / "CANONICAL_INVENTION_OBJECT.json")
    if cio and cio.get("present"):
        out.append({"kind": "canonical_invention_object",
                    "basis": "CIO.json"})
    bridge = _read_json(run_dir / "BRIDGE_REPORT.json")
    if bridge:
        if bridge.get("glb_path") or bridge.get("geometry_complete"):
            out.append({"kind": "geometry_model",
                        "basis": "BRIDGE_REPORT.json"})
        pkg = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
        if pkg.get("complete") or bridge.get("outcome") == "COMPLETED":
            out.append({"kind": "technology_package",
                        "basis": "PACKAGE_REPORT.json"})
    ke = (_read_json(run_dir / "candidate_envelope.json")
          or {}).get("killer_experiment") if \
        (run_dir / "candidate_envelope.json").is_file() else None
    if (ke or {}).get("selected"):
        out.append({"kind": "decisive_experiment",
                    "basis": "candidate_envelope.json"})
    return out


def _uncertainties(run_dir: Optional[Path]) -> List[Dict[str, Any]]:
    """The live uncertainty list: the PU's unknowns + the envelope's
    recorded unresolved contradictions — both from persisted records."""
    out: List[Dict[str, Any]] = []
    if not run_dir:
        return out
    pu = _read_json(run_dir / "PROBLEM_UNDERSTANDING.json")
    for u in (pu or {}).get("unknowns") or []:
        out.append({"source": "problem_understanding",
                    "field": u.get("field"),
                    "why": u.get("why_unknown")})
    env = _read_json(run_dir / "candidate_envelope.json")
    for c in ((env or {}).get("contradictions") or {}) \
            .get("contradictions") or []:
        if isinstance(c, dict) and c.get("currently_unresolved"):
            out.append({"source": "contradiction_queue",
                        "field": c.get("contradiction_id"),
                        "why": str(c.get("description") or "")[:200]})
    return out


def _next_action(session: Dict[str, Any],
                 run_dir: Optional[Path]) -> Optional[Dict[str, Any]]:
    """The single preferred next action — the NBA controller's record
    when a live one exists, else the persisted NEXT_BEST_ACTION stage
    output (the end-of-run epistemic record)."""
    if not run_dir:
        return None
    nba = _read_json(run_dir / "NBA_CONTROLLER.json")
    if nba and nba.get("preferred_action"):
        pa = dict(nba["preferred_action"])
        pa["authority"] = "runtime NBA controller (live)"
        return pa
    env = _read_json(run_dir / "candidate_envelope.json")
    persisted = ((env or {}).get("next_best_action") or {}) \
        .get("selected_best")
    if persisted:
        pa = dict(persisted)
        pa["authority"] = "engine NEXT_BEST_ACTION stage record"
        return pa
    return None


def high_level_run_contract(session: Dict[str, Any],
                            run_dir: Optional[Path]) -> Dict[str, Any]:
    """The ~7-field product contract. Derived; never authoritative."""
    rd = Path(run_dir) if run_dir else None

    # current_state: the session status is the live authority; the
    # completion marker gates any COMPLETE claim (R446-C1 Task 4).
    status = str(session.get("status") or "PENDING")
    current_state = {
        "state": status,
        "final_status": session.get("final_status"),
        "complete_marker": None,
    }
    if rd:
        from toscanini import completion
        marker = completion.completion_marker_state(rd)
        current_state["complete_marker"] = marker.get("completion")
        current_state["marker_reason"] = marker.get("reason")
    else:
        current_state["complete_marker"] = "NOT_MARKED"
        current_state["marker_reason"] = "no run_dir recorded"

    # human_progress: the product phases, projected from the same
    # canonical stage statuses run_state already derives (no second
    # derivation logic — delegate).
    human_progress: List[Dict[str, Any]] = []
    if rd:
        try:
            from toscanini import run_state as _rs
            stage_status = _rs._stage_status_map(session, rd)
            human_progress = _rs.phase_progression(session, rd,
                                                   stage_status)
        except Exception:  # noqa: BLE001 — projection is fail-open
            human_progress = []

    # the event stream (§9/§10) rides along for the conversation feed
    events = product_events.derive_product_events(
        rd, str(session.get("session_id") or session.get("id") or ""),
        status) if rd else []

    return {
        "schema": CONTRACT_VERSION,
        "run_id": str(session.get("session_id") or session.get("id")
                      or ""),
        "current_state": current_state,
        "human_progress": human_progress,
        "next_action": _next_action(session, rd),
        "artifacts": _artifacts(session, rd),
        "blocking_reason": _blocking_reason(session, rd),
        "uncertainties": _uncertainties(rd),
        "events": events,
        "projection_note": "derived view of canonical state "
                           "(run_manifest/envelopes/lineage/bridge); "
                           "never a second state store (Art. X)",
    }
