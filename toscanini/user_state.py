"""user_state.py — R394: user-facing run-state semantics (CEO directive 2).

The machine retains its richer internal taxonomy (PENDING / BUILDING_
PROBLEM / RUNNING / COMPLETE / INTERRUPTED / ERROR_TRANSPORT / ERROR_
BUILD / ERROR_RUN / ERROR_STUCK; final_status REJECTED /
AUTOMATED_INVENTION_CANDIDATE / UNKNOWN). The PRODUCT surface translates
it to exactly one coherent user state:

  RUNNING
  COMPLETED — PACKAGE READY          (candidate found AND package built)
  COMPLETED — CANDIDATE FOUND        (candidate, no package yet)
  COMPLETED — CANDIDATE REJECTED     (engine rejected — a real result)
  COMPLETED — OUTCOME UNKNOWN        (terminal, no recorded verdict)
  INTERRUPTED — RECOVERABLE          (worker died; retryable)
  FAILED — TRANSPORT
  FAILED — ENGINE

Derivation is BACKEND-side from the session record's own fields (status,
final_status, package.complete) — the UI never hand-writes state copy,
never shows raw machine-state combinations, and a user always knows:
did it finish, was something found, was it rejected, is there a package,
and why. Plus a one-line DECISION summary derived from the same record.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .run_state import (OUTCOME_LABELS, OUTCOME_NO_DEFENSIBLE,
                        OUTCOME_REQUIRES_EXPERIMENT, OUTCOME_RUN_BLOCKED,
                        OUTCOME_SURVIVED, terminal_outcome)

# Machine -> user translation (CEO directive 2). The machine taxonomy
# stays intact internally; this is the product-surface projection.
_TRANSPORT_ERRORS = ("ERROR_TRANSPORT",)
_ENGINE_ERRORS = ("ERROR_BUILD", "ERROR_RUN", "ERROR_STUCK")

_USER_STATE_LABELS = {
    "RUNNING": "Running",
    "COMPLETED_PACKAGE": "Completed — package ready",
    "COMPLETED_CANDIDATE": "Completed — candidate found",
    "COMPLETED_REJECTED": "Completed — candidate rejected",
    "COMPLETED_FALSE_PREMISE": "Completed — false premise",
    "COMPLETED_UNKNOWN": "Completed — outcome unknown",
    "INTERRUPTED": "Interrupted — recoverable",
    "FAILED_TRANSPORT": "Failed — transport",
    "FAILED_ENGINE": "Failed — engine",
}

# What the state MEANS for the user (why) — shipped with the state so
# the UI renders one coherent sentence, never a bare machine label.
_USER_STATE_EXPLANATIONS = {
    "RUNNING": ("The engine is working through the discovery pipeline "
                "(understand, evidence, attack, engineer). You can leave "
                "and come back."),
    "COMPLETED_PACKAGE": ("The run finished, a candidate survived the full "
                          "adversarial chain, and a buyer technology "
                          "package was produced — downloadable from the "
                          "run page."),
    "COMPLETED_CANDIDATE": ("The run finished and the engine recorded an "
                            "invention candidate, but no buyer package was "
                            "produced on this run (the release gate was "
                            "not reached — an honest result, not a failure)."),
    "COMPLETED_REJECTED": ("The run finished and the engine REJECTED the "
                           "candidate — the adversarial chain found the "
                           "idea not defensible enough to package. That is "
                           "a real discovery result: kills are recorded to "
                           "the mechanism cemetery and improve future runs."),
    "COMPLETED_FALSE_PREMISE": ("The engine checked the problem's premises "
                                "BEFORE inventing and found them "
                                "physically/scientifically incoherent — no "
                                "candidate was synthesized because the "
                                "problem as stated cannot occur. This is a "
                                "real result, not a crash: reformulating "
                                "the premise is the fix."),
    "COMPLETED_UNKNOWN": ("The run reached a terminal state without a "
                          "recorded verdict — the outcome could not be "
                          "established from the run's own artifacts."),
    "INTERRUPTED": ("The worker died before reaching a verdict (restart "
                    "or crash). The run is recoverable through the same "
                    "worker path — retry from the run page."),
    "FAILED_TRANSPORT": ("The run could not reach the language-model "
                         "transport — no evidence synthesis was possible. "
                         "Retryable once the transport responds."),
    "FAILED_ENGINE": ("The engine itself failed during the run (build or "
                      "pipeline stage). The failure is recorded in the "
                      "run's artifacts; retryable."),
}


def user_state(session: Dict[str, Any]) -> str:
    """The user-facing state key for one session record."""
    status = session.get("status") or ""
    final = (session.get("final_status") or "").upper()
    pkg = session.get("package") or {}
    if status in ("PENDING", "BUILDING_PROBLEM", "RUNNING"):
        return "RUNNING"
    if status == "COMPLETE":
        if pkg.get("complete"):
            return "COMPLETED_PACKAGE"
        if final == "AUTOMATED_INVENTION_CANDIDATE":
            return "COMPLETED_CANDIDATE"
        if final == "MALFORMED_OR_FALSE_PREMISE":
            return "COMPLETED_FALSE_PREMISE"
        if final == "REJECTED":
            return "COMPLETED_REJECTED"
        return "COMPLETED_UNKNOWN"
    if status == "INTERRUPTED":
        return "INTERRUPTED"
    if status in _TRANSPORT_ERRORS:
        return "FAILED_TRANSPORT"
    if status in _ENGINE_ERRORS or status.startswith("ERROR"):
        return "FAILED_ENGINE"
    return "RUNNING" if status in ("", None) else "COMPLETED_UNKNOWN"


def _run_dir(session: Dict[str, Any]):
    """Resolve the session's run dir for artifact-derived projections
    (the outcome consults the run's own package report when the session
    index lags the worker — Art. X: the run dir is the authority)."""
    from pathlib import Path
    rd = session.get("run_dir")
    try:
        p = Path(rd) if rd else None
        return p if p and p.exists() else None
    except Exception:  # noqa: BLE001 — absent stays absent
        return None


def user_state_view(session: Dict[str, Any]) -> Dict[str, Any]:
    """The full user-state projection for one session (label, meaning,
    decision line, finish flags) — derived from the session record's own
    fields (plus its run dir's package report when present — the run
    dir is the authority, Art. X), never hand-written per-run copy."""
    key = user_state(session)
    final = (session.get("final_status") or "") or ""
    pkg = session.get("package") or {}
    finished = key.startswith("COMPLETED") or key.startswith("FAILED") \
        or key == "INTERRUPTED"
    found = key in ("COMPLETED_PACKAGE", "COMPLETED_CANDIDATE")
    rejected = key == "COMPLETED_REJECTED"

    # the one-line decision: what did the engine decide?
    if found and pkg.get("maturity"):
        decision = f"candidate found — package at {pkg['maturity']} maturity"
    elif found:
        decision = "candidate found — no package on this run"
    elif key == "COMPLETED_FALSE_PREMISE":
        decision = "the problem's premise is physically incoherent — nothing to invent"
    elif rejected:
        decision = "no defensible invention — candidate rejected"
    elif key == "COMPLETED_UNKNOWN":
        decision = "outcome not established"
    elif key == "RUNNING":
        decision = "investigating"
    elif key == "INTERRUPTED":
        decision = "interrupted before a verdict"
    elif key == "FAILED_TRANSPORT":
        decision = "could not reach the model transport"
    else:
        decision = "engine failure"
    error = session.get("error")
    if error and (key.startswith("FAILED") or key == "INTERRUPTED"):
        decision = f"{decision} ({str(error)[:140]})"

    return {
        "user_state": key,
        "label": _USER_STATE_LABELS[key],
        "meaning": _USER_STATE_EXPLANATIONS[key],
        "decision": decision,
        "finished": finished,
        "found_something": found,
        "rejected": rejected,
        "package_available": bool(pkg.get("complete")),
        "machine_status": session.get("status"),  # never shown as the state
        # R414 (directive §18): the four terminal outcome states. The
        # granular user_state above stays the sub-detail; the outcome is
        # the product-level terminal truth, derived by run_state from
        # recorded fields only.
        "outcome": terminal_outcome(session, _run_dir(session)).get(
            "outcome"),
        "outcome_label": OUTCOME_LABELS.get(
            terminal_outcome(session, _run_dir(session)).get("outcome"),
            "Investigating"),
    }


def with_user_state(session: Dict[str, Any]) -> Dict[str, Any]:
    """Attach the user-state projection to a session record (list rows
    and detail payloads both carry it; the UI renders THIS, never raw
    machine-state combinations)."""
    out = dict(session)
    out["user_state_view"] = user_state_view(session)
    return out


# R394 section 15: operational internals NEVER reach a customer response.
# Measured on the public deployment (consultant claim 3,
# CONFIRMED_CURRENT): /api/sessions exposed worker_pid and run_dir
# (/app/ENGINE_RUNS/...) to anonymous callers. These fields are
# process/filesystem identity — they are not removed from the STORE
# (the operator's durable record keeps them for liveness checks), only
# from every API projection.
OPERATIONAL_FIELDS = ("worker_pid", "worker_starttime", "run_dir",
                      "problem_id", "owner_key")


def strip_operational_fields(session: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the session projection without worker pids,
    filesystem paths, or internal run slugs."""
    out = dict(session)
    for f in OPERATIONAL_FIELDS:
        out.pop(f, None)
    return out


def public_session_view(session: Dict[str, Any]) -> Dict[str, Any]:
    """The FULL customer-facing projection: user state + stripped
    internals. Every API response that carries a session record goes
    through this (R394 s15/s16).

    R414: the user-state projection (including the four-outcome
    terminal state) is derived FIRST — while the run_dir is still
    present so the outcome can consult the run's own package report —
    and the operational fields are stripped AFTER. Stripping first
    made the outcome fall back to the (lagging) session index, which
    disagreed with the detail view (Art. X: one authority, not two
    projections of it)."""
    projected = with_user_state(session)
    stripped = strip_operational_fields(projected)
    return stripped


# raw final_status -> readable language (CEO directive 16: "raw labels
# such as AUTOMATED_INVENTION_CANDIDATE should be translated")
FINAL_STATUS_READABLE = {
    "AUTOMATED_INVENTION_CANDIDATE": "Invention candidate (automated)",
    "REJECTED": "Rejected — not defensible enough to package",
    "MALFORMED_OR_FALSE_PREMISE": "False premise — the problem as stated "
                                  "cannot physically occur",
    "UNKNOWN": "Outcome unknown",
}
