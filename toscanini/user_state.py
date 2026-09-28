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
  COMPLETED — NO SURVIVOR            (R472: the challenge verdict is
                              AUTHENTICATED-kill — the machine's own
                              gauntlet killed the candidate; ONE frame,
                              the same words the workspace banner uses)
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

from .run_state import (OUTCOME_KILLED_BY_CHALLENGE,
                        OUTCOME_LABELS, OUTCOME_NO_DEFENSIBLE,
                        OUTCOME_REQUIRES_EXPERIMENT, OUTCOME_RUN_BLOCKED,
                        OUTCOME_SURVIVED, learning_card, terminal_outcome)

# Machine -> user translation (CEO directive 2). The machine taxonomy
# stays intact internally; this is the product-surface projection.
_TRANSPORT_ERRORS = ("ERROR_TRANSPORT", "RUN_BLOCKED_TRANSPORT")
_ENGINE_ERRORS = ("ERROR_BUILD", "ERROR_RUN")

_USER_STATE_LABELS = {
    "RUNNING": "Running",
    "COMPLETED_PACKAGE": "Completed — package ready",
    "COMPLETED_CANDIDATE": "Completed — candidate found",
    "COMPLETED_EVOLVED": "Completed — evolved invention found",
    "COMPLETED_GENERATION_FAILED":
        "Completed — architecture generation failed",
    "COMPLETED_UNDER_DEVELOPMENT":
        "Completed — invention in development",
    # R472 (external audit third pass, §2C terminal de-collision):
    # the killed frame in ONE sentence — the same words the R470
    # workspace banner uses. The old headline ("Completed — invention
    # in development") next to that banner asked the user to reconcile
    # two frames for one state; the auditor measured the collision on
    # a fresh killed run.
    "COMPLETED_KILLED":
        "Run finished — no candidate survived the challenge gauntlet",
    "COMPLETED_FALSE_PREMISE": "Completed — false premise",
    "COMPLETED_UNKNOWN": "Completed — outcome unknown",
    "AWAITING_CLARIFICATION": "Action needed — answer Toscanini's question below",
    "INTERRUPTED": "Interrupted — recoverable",
    # Article LXXIV (Constitution v2.6.0): UNKNOWN is first-class,
    # never rendered as a failure (observation failure ≠ execution
    # failure).
    "UNKNOWN_STALLED": "Stalled — outcome unknown, not a failure",
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
    "COMPLETED_KILLED": ("The run finished and the machine's own "
                          "adversarial challenge killed the candidate — "
                          "every cause and every generation's lesson is "
                          "on the record below. Nothing was fabricated "
                          "to fill its place."),
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
    "AWAITING_CLARIFICATION": ("The investigation paused BEFORE spending "
                               "compute because one answer from you "
                               "materially changes what to look for. "
                               "Nothing is running while the question is "
                               "open — type your answer below and the "
                               "same investigation resumes instantly."),
    "INTERRUPTED": ("The worker process could not start, or died before "
                    "reaching a verdict (restart, crash, or a failed "
                    "spawn). The run is recoverable through the same "
                    "worker path — retry from the run page. Nothing was "
                    "concluded about the problem, and its cause is "
                    "recorded on the run's own diagnostics."),
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
    # Article LXXIV (Constitution v2.6.0): a stalled feed is not a
    # verdict — UNKNOWN is first-class and distinct from FAILED.
    "UNKNOWN_STALLED": ("The worker stopped reporting progress, so the "
                        "run's outcome is genuinely unknown — it is not "
                        "recorded as failed (observation failure is not "
                        "execution failure). The run is saved and "
                        "resumable; reconnecting or retrying recovers "
                        "its durable state."),
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
            lin = _json.loads(p.read_text(encoding="utf-8"))
            n = lin.get("n_generations")
            cur = lin.get("current_invention") or {}
            if n and cur:
                return (f"{n} architecture generations explored; "
                        f"current invention GEN {cur.get('gen')} "
                        f"(maturity {cur.get('maturity')})")
    except Exception:  # noqa: BLE001 — absent stays absent
        pass
    return ""


def _challenge_verdict(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """R452: the challenge-aware terminal verdict for the positive
    final statuses. Returns the terminal_outcome dict ONLY when the
    lineage verdict DEMOTES the presentation (invention_found=False —
    killed-by-challenge or an unverified promoted generation); None
    when the run keeps its positive presentation (a verified survivor)
    or no lineage exists (the legacy branches keep their behavior —
    never fabricated)."""
    try:
        out = terminal_outcome(session, _run_dir(session))
    except Exception:  # noqa: BLE001 — projection must never crash the view
        return None
    if out.get("invention_found") is False:
        return out
    return None


def user_state(session: Dict[str, Any]) -> str:
    """The user-facing state key for one session record.

    R452 (external audit B1): for the POSITIVE final statuses the
    lineage's challenge verdict is authoritative — a lineage whose
    generations were killed and never replaced by a VERIFIED survivor
    can never surface as CANDIDATE FOUND / EVOLVED (the audit measured
    the promotion 7/7 in production). Those records present as
    UNDER_DEVELOPMENT at the key layer too; the outcome + decision line
    carry the killed-by-challenge truth verbatim."""
    status = session.get("status") or ""
    final = (session.get("final_status") or "").upper()
    pkg = session.get("package") or {}
    if status in ("PENDING", "BUILDING_PROBLEM", "RUNNING"):
        return "RUNNING"
    if status == "COMPLETE":
        if final in ("INVENTION_REQUIRES_EXPERIMENT",
                     "EVOLVED_INVENTION_CANDIDATE",
                     "AUTOMATED_INVENTION_CANDIDATE",
                     "INVENTION_UNDER_DEVELOPMENT"):
            verdict = _challenge_verdict(session)
            if verdict is not None and not verdict.get("invention_found"):
                # R472 (terminal de-collision): when the demotion IS a
                # genuine adversarial kill (the SAME typed outcome
                # constant the workspace banner keys on — one source of
                # truth in run_state, never a string literal here), the
                # headline says the kill in ONE frame — never
                # "invention in development" next to a no-survivor
                # banner. Capability-class demotions (the attack never
                # rendered a verdict; promotion was blocked) keep the
                # under-development frame honestly.
                if verdict.get("outcome") == OUTCOME_KILLED_BY_CHALLENGE:
                    return "COMPLETED_KILLED"
                return "COMPLETED_UNDER_DEVELOPMENT"
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
    if status == "ERROR_SPAWN":
        # R463: a spawn failure is NOT an engine failure — the discovery
        # pipeline never ran (Art. LXI: distinct infrastructure classes
        # stay distinct). It lands in the recoverable family with the
        # spawn cause carried on the session's error line.
        return "INTERRUPTED"
    if status == "ERROR_STUCK":
        # Article LXXIV (Constitution v2.6.0, the amendment's exact
        # case): no worker progress for >3h with the cause not captured
        # is an OBSERVATION fact — the run's outcome is UNKNOWN, never
        # FAILED. The canonical machine (execution_states.mapping)
        # pins the same semantics; the product surface must agree.
        return "UNKNOWN_STALLED"
    if status == "AWAITING_CLARIFICATION":
        # R459 (external product audit P0-1, measured live on production:
        # session ts_7fdb31b19012): the one-question pause is an ACTIVE
        # state — the engine is waiting for the user's answer, and the
        # projection must never read it as a terminal outcome. The
        # pre-R459 fallthrough rendered "Completed — outcome unknown
        # (finished: true)" on a run that was waiting for input.
        return "AWAITING_CLARIFICATION"
    if status == "RUN_BLOCKED_TRANSPORT":
        return "BLOCKED_TRANSPORT"   # R415 (directive §8): infrastructure
        # blocked ≠ discovery failure — distinct projection, never a kill
    if status in _TRANSPORT_ERRORS:
        return "FAILED_TRANSPORT"
    if status in _ENGINE_ERRORS or (status.startswith("ERROR")
                                    and status != "ERROR_STUCK"):
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


def _contract_finished_flag(session: Dict[str, Any]) -> Optional[bool]:
    """R543-1: the customer-facing finished flag when the durable
    completion contract exists (the sole authority chain:
    COMPLETION_CONTRACT.json -> completion_states() -> finished).

    Returns None when no recorded contract/completion_states exists
    (legacy session, or a run that never reached the run-tail verifier)
    — the caller falls back to the state-key derivation. When recorded:

      FINISHED_DISCOVERY=true  => finished=true
      FINISHED_DISCOVERY=false => finished=false

    for EVERY typed terminal (MECHANISM_STARVED, RUN_BLOCKED_*,
    REJECTED, INCOMPLETE_DISCOVERY, ...). The contract is the only
    FINISHED_DISCOVERY authority: a typed terminal may remain a
    terminal STATE, but it must never be represented as a finished
    discovery by a second Boolean.

    Read order (R544: the contract itself first — a stale
    recorded completion_states, whether on the session record or in
    final_state, can NEVER override the contract's own answer;
    R545: a typed terminal's own honest final_status is authority for
    its OWN answer even when no contract was recorded — the key-prefix
    legacy fallback may never turn a typed terminal's finished=false
    into finished=true):

      1. session['completion_contract'] — the durable contract
         record, projected live through completion_states(). A stale
         FINISHED_DISCOVERY=true sitting in a recorded
         completion_states field loses to a contract false, and a
         stale false loses to a contract true.
      2. session['completion_states'] — the worker's run-tail
         refresh (the contract's projection, persisted).
      3. session['final_state']['completion_states'] — the engine's
         own final_state.json record (the contract's projection
         since R544, re-persisted post-contract).
       4. typed terminal (R545/R546): the record's OWN typed terminal
          evidence answers its finished flag — read in producer
          shape (status first: the real worker's infrastructure
          terminals write the typed state into status and often
          record NO final_status at all; final_status second: the
          engine's typed scientific terminals):
          * a WAITING_EXTERNAL terminal status (RUN_BLOCKED_* —
            execution_states.py's infrastructure class) answers
            finished=False: the run is infrastructure-blocked and
            resumable, never a completed discovery;
          * a recorded final_status that is a typed non-completion
            outcome (MECHANISM_STARVED, REJECTED, ...) with no
            completion answer recorded answers finished=False;
          * completion-like values are governed by the canonical
            completion authority (rules 1-3) and fall through
            unchanged; a terminal record with no typed terminal
            evidence stays unresolved (None, no manufactured
            answer).
            answer).

    Scope (R543 Step 6 POS pin): the contract governs TERMINAL records
    only. A non-terminal status (PENDING / BUILDING_PROBLEM / RUNNING /
    #    AWAITING_CLARIFICATION) is an explicitly represented
    state — the run has not ended, so a lingering contract answer can
    only describe a PREVIOUS terminal state of a reused record, never
    the live run. Honoring it would be the stale-snapshot error, so
    the flag returns None here and the live key governs (finished is
    false while the run is live)."""
    if (session.get("status") or "") in (
            "PENDING", "BUILDING_PROBLEM", "RUNNING",
            "AWAITING_CLARIFICATION"):
        return None
    # 1. the durable contract itself (the authority — projected
    #    live; a stale recorded Boolean can never override it)
    contract = session.get("completion_contract")
    if isinstance(contract, dict):
        try:
            from discovery_fabric.engine import (
                completion_contract as _cc)
            states = _cc.completion_states(contract)
            if "FINISHED_DISCOVERY" in states:
                return bool(states.get("FINISHED_DISCOVERY"))
        except Exception:  # noqa: BLE001 — projection must not crash
            pass
    # 2. the session record's own completion_states (worker refresh —
    #    the contract's projection, persisted at the run tail)
    states = session.get("completion_states")
    if isinstance(states, dict) and "FINISHED_DISCOVERY" in states:
        return bool(states.get("FINISHED_DISCOVERY"))
    # 3. the engine's final_state record (the contract's projection
    #    since R544, re-persisted post-contract)
    fs = session.get("final_state")
    if isinstance(fs, dict):
        fs_states = fs.get("completion_states")
        if isinstance(fs_states, dict) and "FINISHED_DISCOVERY" in fs_states:
            return bool(fs_states.get("FINISHED_DISCOVERY"))
    final_status = str(session.get("final_status") or "").strip()
    status = str(session.get("status") or "")
    # 4. R545/R546: the typed terminal's OWN honest answer (status
    # FIRST, final_status SECOND — the real worker's infrastructure
    # final_status SECOND — the real worker's infrastructure terminals
    # write the typed state into status and often record NO
    # final_status at all; the R545 form read final_status first and
    # missed exactly that shape):
    #
    #   4a. status is a typed infrastructure terminal
    #       (RUN_BLOCKED_* — the execution_states.py §2 WAITING_
    #       EXTERNAL class) -> finished=False. The record answers
    #       itself: infrastructure blocked, resumable, never a
    #       completed discovery; the BLOCKED_TRANSPORT / COMPLETED_*
    #       key-prefix inference may not turn it into True.
    #   4b. final_status is a typed scientific non-completion
    #       terminal (MECHANISM_STARVED, REJECTED, ...) with no
    #       completion answer recorded -> finished=False from its own
    #       honest terminal (the R545 rule, unchanged).
    #   4c. no typed terminal evidence at all -> None: the legacy key
    #       derivation governs; no completion answer is manufactured.
    from . import execution_states as _es
    if _es.mapping(status) is _es.ExecutionState.WAITING_EXTERNAL:
        # The WAITING_EXTERNAL terminal class (the canonical
        # execution_states.py §2 mapping — no second taxonomy):
        #   * the transient pre-clarification state was already
        #     answered None by rule 0 above;
        #   * the worker's RUN_BLOCKED_* terminal branches (the
        #     transport-exhausted and pre-retrieval capability
        #     refusals) ended the run in the resumable infrastructure
        #     class (Art. LXI: infrastructure state, never a
        #     scientific verdict) — the record answers finished=False
        #     from its own typed terminal; the BLOCKED_TRANSPORT /
        #     COMPLETED_* key-prefix inference may not promote it.
        return False
    if final_status and status in (
            "COMPLETE", "ERROR_CANCELED", "ERROR_STARVED",
            "ERROR_BLOCKED", "ERROR_STUCK", "INTERRUPTED"):
        # the engine's own completion vocabulary (the canonical
        # completion authority names its successful outcomes this
        # way; see run.py's final-state writer + completion_contract):
        completion_like = (
            final_status == "AUTOMATED_INVENTION_CANDIDATE"
            or final_status == "FINISHED_DISCOVERY"
            or final_status.endswith("_COMPLETE")
            or final_status.endswith("_COMPLETED"))
        if not completion_like:
            return False
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
        or key in ("INTERRUPTED", "BLOCKED_TRANSPORT", "UNKNOWN_STALLED")
    # R543-1: when the durable completion contract is recorded, ITS
    # FINISHED_DISCOVERY is the authority for the customer-facing
    # finished flag (never a second key-prefix Boolean). FINISHED_
    # DISCOVERY=false (starved/blocked/rejected/incomplete) forces
    # finished=false; true only when the six-part contract verified.
    _contract_flag = _contract_finished_flag(session)
    if _contract_flag is not None:
        finished = _contract_flag
    found = key in ("COMPLETED_PACKAGE", "COMPLETED_CANDIDATE",
                    "COMPLETED_EVOLVED")
    # R416: the product surface never renders a bare reject dead-end;
    # challenge losses live on the generation records.
    # R452 (external audit B1/AT-7): the lineage's challenge verdict is
    # AUTHORITATIVE over final_status — a killed/unverified lineage is
    # never "found something", and a GENUINE adversarial kill surfaces
    # as rejected=true (typed outcome, never a bare dead-end sentence).
    verdict = _challenge_verdict(session)
    outcome_info = terminal_outcome(session, _run_dir(session))
    if verdict is not None:
        found = False
        rejected = bool(verdict.get("invention_rejected"))
    else:
        rejected = False

    # the one-line decision: what did the engine decide?
    # R416: the decision line follows what ACTUALLY happened (honest
    # cause attribution — a mechanism-generation failure is never
    # described as an adversarial rejection)
    gen_note = _generation_note(session)
    if rejected:
        decision = ("the machine's own adversarial challenge killed this "
                    "invention and no verified survivor replaced it — "
                    "the generation records show exactly what was killed "
                    "and why")
    elif verdict is not None and not found:
        decision = (verdict.get("basis") or gen_note or
                    "architectures were explored and challenged; none is "
                    "presented as a verified candidate")
    elif found and pkg.get("maturity"):
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
    elif key == "AWAITING_CLARIFICATION":
        decision = ("waiting for your answer — one question decides what "
                    "the investigation looks for next")
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
        "outcome": outcome_info.get("outcome"),
        "outcome_label": OUTCOME_LABELS.get(
            outcome_info.get("outcome"), "Investigating"),
        # R472 (audit P0-4): the no-survivor learning card — what was
        # tested, the strongest failed hypothesis, the key missing
        # evidence, and 2-3 ranked next actions; None for every
        # non-no-survivor terminal (the projection decides, the surface
        # renders)
        "learning_card": learning_card(session, _run_dir(session)),
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
                      "problem_id", "owner_key", "spawn_diagnostics")


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
