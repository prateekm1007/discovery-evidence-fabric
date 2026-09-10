"""user_state.py — R394: user-facing run-state semantics (CEO directive 2).

The machine retains its richer internal taxonomy (PENDING / BUILDING_
PROBLEM / RUNNING / COMPLETE / INTERRUPTED / ERROR_TRANSPORT / ERROR_
BUILD / ERROR_RUN / ERROR_STUCK; final_status REJECTED /
AUTOMATED_INVENTION_CANDIDATE / MECHANISM_GENERATION_FAILED /
EVOLVED_INVENTION_CANDIDATE / INVENTION_UNDER_DEVELOPMENT / UNKNOWN).
The PRODUCT surface translates it to exactly one coherent user state
(R416: the wording follows what ACTUALLY happened — a mechanism-
generation failure is never described as an adversarial rejection,
and the terminal always presents the current invention):

  RUNNING
  COMPLETED — PACKAGE READY          (candidate found AND package built)
  COMPLETED — CANDIDATE FOUND        (candidate, no package yet)
  COMPLETED — EVOLVED INVENTION      (an evolution generation survived)
  COMPLETED — INVENTION IN DEVELOPMENT (architectures explored; the
                              current invention is presented with its
                              honest maturity — never "candidate
                              rejected" as a dead end)
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
_TRANSPORT_ERRORS = ("ERROR_TRANSPORT", "RUN_BLOCKED_TRANSPORT")
_ENGINE_ERRORS = ("ERROR_BUILD", "ERROR_RUN", "ERROR_STUCK")

_USER_STATE_LABELS = {
    "RUNNING": "Running",
    "COMPLETED_PACKAGE": "Completed — package ready",
    "COMPLETED_CANDIDATE": "Completed — candidate found",
    "COMPLETED_EVOLVED": "Completed — evolved invention found",
    "COMPLETED_GENERATION_FAILED":
        "Completed — architecture generation failed",
    "COMPLETED_UNDER_DEVELOPMENT":
        "Completed — invention in development",
    "COMPLETED_FALSE_PREMISE": "Completed — false premise",
    "COMPLETED_UNKNOWN": "Completed — outcome unknown",
    "INTERRUPTED": "Interrupted — recoverable",
    "BLOCKED_TRANSPORT": "Blocked by infrastructure — saved and resumable",
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
    "COMPLETED_GENERATION_FAILED": ("The engine could not generate an "
                          "invention architecture on this run — a "
                          "transport-class failure, never a scientific "
                          "rejection (the typed failure record is on "
                          "the run page). Your problem is saved and "
                          "resumable."),
    "COMPLETED_EVOLVED": ("The run challenged its first architecture, "
                          "diagnosed why it failed, and evolved the "
                          "next architecture through an explicit causal "
                          "change — this generation survived the "
                          "challenge gauntlet. Its maturity label says "
                          "exactly what is verified so far."),
    "COMPLETED_UNDER_DEVELOPMENT": ("The engine explored multiple "
                          "architecture generations. The current "
                          "invention is presented with its honest "
                          "maturity and full challenge history — "
                          "nothing is softened, and the machine keeps "
                          "the diagnosed causes on record so the next "
                          "generation can build on them."),
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
    "BLOCKED_TRANSPORT": ("Discovery temporarily blocked by "
                          "infrastructure. Your problem is saved and "
                          "ready to resume. No conclusion was reached — "
                          "this is not a rejection. Toscanini exhausted "
                          "every available model route (each failure is "
                          "recorded with its provider and failure class) "
                          "and will attempt the run again on retry."),
    "FAILED_TRANSPORT": ("The run could not reach the language-model "
                         "transport — no evidence synthesis was possible. "
                         "Retryable once the transport responds."),
    "FAILED_ENGINE": ("The engine itself failed during the run (build or "
                      "pipeline stage). The failure is recorded in the "
                      "run's artifacts; retryable."),
}


def _generation_note(session: Dict[str, Any]) -> str:
    """R416: a one-line honest note from the run's lineage record (the
    run dir is the authority — Art. X). Absent when no lineage exists
    (never fabricated)."""
    from pathlib import Path
    import json as _json
    rd = session.get("run_dir")
    try:
        p = Path(rd) / "INVENTION_LINEAGE.json" if rd else None
        if p and p.exists():
            lin = _json.loads(p.read_text())
            n = lin.get("n_generations")
            cur = lin.get("current_invention") or {}
            if n and cur:
                return (f"{n} architecture generations explored; "
                        f"current invention GEN {cur.get('gen')} "
                        f"(maturity {cur.get('maturity')})")
    except Exception:  # noqa: BLE001 — absent stays absent
        pass
    return ""


def user_state(session: Dict[str, Any]) -> str:
    """The user-facing state key for one session record."""
    status = session.get("status") or ""
    final = (session.get("final_status") or "").upper()
    pkg = session.get("package") or {}
    if status in ("PENDING", "BUILDING_PROBLEM", "RUNNING"):
        return "RUNNING"
    if status == "COMPLETE":
        if final == "INVENTION_REQUIRES_EXPERIMENT":
            # R443 / TSC-008: the surviving baseline fallback — the
            # idea is alive and requires its experiment (never EVOLVED,
            # never rejected)
            return "COMPLETED_PACKAGE" if pkg.get("complete") \
                else "COMPLETED_CANDIDATE"
        if final == "EVOLVED_INVENTION_CANDIDATE":
            # R416: an evolution generation survived — package state
            # decides the packaging wording; the evolution story rides
            # on the run page's generations timeline either way.
            return "COMPLETED_PACKAGE" if pkg.get("complete") \
                else "COMPLETED_EVOLVED"
        if final == "INVENTION_UNDER_DEVELOPMENT":
            return "COMPLETED_UNDER_DEVELOPMENT"
        if pkg.get("complete"):
            return "COMPLETED_PACKAGE"
        if final == "AUTOMATED_INVENTION_CANDIDATE":
            return "COMPLETED_CANDIDATE"
        if final == "MALFORMED_OR_FALSE_PREMISE":
            return "COMPLETED_FALSE_PREMISE"
        if final == "REJECTED":
            # R416 honest-cause fix: this state now says the invention
            # is IN DEVELOPMENT (the architecture was challenged and
            # killed; the run page shows the generation record and the
            # diagnosed cause) — never "the adversarial chain found the
            # idea not defensible enough" as a bare dead end. When the
            # evolution engine is enabled this path is only reached by
            # legacy/pre-R416 session records.
            return "COMPLETED_UNDER_DEVELOPMENT"
        if final == "MECHANISM_GENERATION_FAILED":
            return "COMPLETED_GENERATION_FAILED"
        return "COMPLETED_UNKNOWN"
    if status == "INTERRUPTED":
        return "INTERRUPTED"
    if status == "RUN_BLOCKED_TRANSPORT":
        return "BLOCKED_TRANSPORT"   # R415 (directive §8): infrastructure
        # blocked ≠ discovery failure — distinct projection, never a kill
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
        or key in ("INTERRUPTED", "BLOCKED_TRANSPORT")
    found = key in ("COMPLETED_PACKAGE", "COMPLETED_CANDIDATE",
                    "COMPLETED_EVOLVED")
    rejected = False   # R416: the product surface never renders a bare
    # reject dead-end; challenge losses live on the generation records

    # the one-line decision: what did the engine decide?
    # R416: the decision line follows what ACTUALLY happened (honest
    # cause attribution — a mechanism-generation failure is never
    # described as an adversarial rejection)
    gen_note = _generation_note(session)
    if found and pkg.get("maturity"):
        decision = f"invention found — package at {pkg['maturity']} maturity"
        if gen_note:
            decision = f"{decision}; {gen_note}"
    elif found:
        decision = "invention found — no package on this run"
        if gen_note:
            decision = f"{decision}; {gen_note}"
    elif key == "COMPLETED_FALSE_PREMISE":
        decision = "the problem's premise is physically incoherent — nothing to invent"
    elif key == "COMPLETED_GENERATION_FAILED":
        decision = ("the engine could not generate an architecture "
                    "(transport-class) — not a scientific rejection; "
                    "retry resumable")
    elif key == "COMPLETED_UNDER_DEVELOPMENT":
        decision = (gen_note or
                    "architecture challenged — the generation record "
                    "shows what was diagnosed and what comes next")
    elif key == "COMPLETED_UNKNOWN":
        decision = "outcome not established"
    elif key == "RUNNING":
        decision = "investigating"
    elif key == "INTERRUPTED":
        decision = "interrupted before a verdict"
    elif key == "BLOCKED_TRANSPORT":
        decision = "discovery temporarily blocked by infrastructure — "\
                   "your problem is saved and ready to resume"
    elif key == "FAILED_TRANSPORT":
        decision = "could not reach the model transport"
    else:
        decision = "engine failure"
    error = session.get("error")
    if error and (key.startswith("FAILED") or key in ("INTERRUPTED",
                                                    "BLOCKED_TRANSPORT")):
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
    "EVOLVED_INVENTION_CANDIDATE": "Evolved invention candidate",
    "INVENTION_UNDER_DEVELOPMENT": "Invention in development",
    "MECHANISM_GENERATION_FAILED": "Mechanism generation failed (a "
                                  "generation gap — not a rejection)",
    "REJECTED": "Challenged and killed — the generation record shows "
                "the diagnosed cause",
    "MALFORMED_OR_FALSE_PREMISE": "False premise — the problem as stated "
                                  "cannot physically occur",
    "UNKNOWN": "Outcome unknown",
}
