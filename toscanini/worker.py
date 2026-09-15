"""Discovery run worker — executes ONE UI discovery end-to-end.

Runs as a detached subprocess started by the server:

    python3 -m toscanini.worker <session_id>

Phases (all real, all persisted — the UI streams them from artifacts):
  0. job lifecycle: RUNNING + worker identity (pid/starttime) recorded
     durably (R392 directive 7 — restart never fakes success or spin)
  1. ensure LLM transport (disclosed if unavailable)
  2. evidence-bound problem build (live retrieval; MODEL_DERIVED extraction)
  3. EngineRun through the full 13-stage chain + automatic package on
     survivor (canonical factory, QA gates — the SAME path as the 15
     portfolio packages; nothing about the dossier is edited manually)
  4. terminal status recorded from the run manifest (never fabricated)
  5. durable snapshot of the epistemic record (R392 directive 5)

Art. XXV: transport/infrastructure failure -> status ERROR_* with reason;
NEVER a research kill.

R415 (P0 directive §§1, 8, 9):
  - The preflight is LADDER-AWARE: the probe is a real completion through
    the routing registry's fallback ladder (model A -> B -> C across
    providers), so a single retired model (410 GONE) no longer kills the
    run — the cascade moves to the next rung and every hop is recorded.
  - A genuinely exhausted transport (every rung failed) terminates as
    RUN_BLOCKED_TRANSPORT — a distinct infrastructure state that is
    NEVER a discovery verdict (Art. LXI), keeps the user's problem
    saved, and stays resumable through the retry path.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import gateway as gw  # noqa: E402
from toscanini import problem_builder  # noqa: E402
from toscanini import sessions as store  # noqa: E402


def _serialize_run():
    """R459-reaudit (P1-1): the binary run.lock is superseded by the
    run-capacity semaphore in store (N flock'd slots, default 3;
    arrival-priority queue; kernel-released on process death). This
    wrapper keeps the historical call site and holds ONE slot for the
    whole run — the heavy-render full-capacity exclusion and the
    transport-cascade protection are unchanged in kind."""
    handle = store.acquire_run_slot()
    if handle is None:  # unreachable with timeout_s=0; kept fail-closed
        raise RuntimeError("run slot acquire returned None")
    return handle


def _register_running(session_id: str) -> None:
    """R392 directive 7: the job is RUNNING with an identity a later
    process can verify — /proc pid + starttime. A restart marks this
    session INTERRUPTED (recoverable), never COMPLETE, never spinning."""
    starttime = store._proc_stat_starttime(os.getpid())
    store.update_session(session_id, status="RUNNING",
                         worker_pid=os.getpid(),
                         worker_starttime=starttime)


def _snapshot(session_id: str, reason: str) -> None:
    """Best-effort durable snapshot (R392 directive 5). Failures are
    disclosed through the health endpoint (durable.last_error), never
    silently swallowed and never fatal to the run itself."""
    try:
        from toscanini import durable
        durable.snapshot(reason)
    except Exception as exc:  # noqa: BLE001
        print(f"  [worker] durable snapshot failed ({reason}): "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)


def _route_detail(probe: dict) -> str:
    """R415 (directive §1): the typed failure record for the blocked-
    transport terminal state — provider, HTTP status, model, attempt,
    timestamp, failure_class — taken from the probe's own recorded route
    (the cascade records every hop; this projects the last ones). Never
    a bare "failed"; never a key."""
    route = probe.get("route") or []
    if not route:
        return ""
    parts = []
    for hop in route[-3:]:
        parts.append(
            f"provider={hop.get('provider_attempted')} "
            f"model={hop.get('model')} "
            f"attempt={hop.get('attempts')} "
            f"failure_class={hop.get('failure_type')} "
            f"timestamp={hop.get('timestamp')}")
    return " | ".join(parts)


def _load_problem_understanding(session_id: str):
    """R461 (independent audit P0-5): load this session's PERSISTED
    Problem Understanding INPUT record, or return None when there is
    none (first run) or it is unreadable (rebuild then — the historical
    path, unchanged).

    Why this exists — the measured failure (production, 2026-09-14,
    run ts_1090d724ca33, boot 23:36:13Z): the worker rebuilds the PU
    from user_text on every resume, and the session's clarification
    answer field is cleared the moment the answer merges. A container
    restart in the run's active window therefore resurrected the
    pre-answer pause state and the engine re-asked a question the user
    had already answered. The persisted record is the only durable
    carrier of the merged USER_STATED fields between pauses; loading
    it here makes the merge survive any restart (the file itself rides
    the durable payload as of this round — durable.py).

    The session_id in the filename is the binding: user_text is
    immutable per session, so a record under this name belongs to this
    problem — no content-matching heuristic is added (Art. X: one
    authority, no second guessing of the record)."""
    path = store.STORE_DIR / f"problem_understanding_{session_id}.json"
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or not raw:
        return None
    return raw


def _mechanism_identity(run_dir) -> dict:
    """R467 (audit P0-5): the run's recorded mechanism identity — the
    SAME fields the canonical projection reads
    (run_state._mechanism_state <- envelope_SYNTHESIZE.mechanism_map:
    mechanism / intervention / expected_effect). This is an identity
    COMPARISON between a parent and a child round, never a new state
    derivation — no second authority is created (Art. X)."""
    import json as _json
    try:
        p = Path(str(run_dir)) / "envelope_SYNTHESIZE.json"
        if not p.exists():
            return {}
        mm = (_json.loads(p.read_text()) or {}).get("mechanism_map") or {}
        out = {}
        for k in ("mechanism", "intervention", "expected_effect"):
            v = mm.get(k)
            if isinstance(v, str) and v.strip():
                out[k] = v.strip()[:300]
        return out
    except (OSError, ValueError):
        return {}


# R470 (the engineer's review F5): the PUBLIC entry point — the spawn
# site imports this name, not the private underscore symbol (private
# cross-module imports couple callers to internals and break under
# refactor). One implementation, two names (the private callers keep
# working; Art. X — no second authority).
mechanism_identity = _mechanism_identity


def record_directive_outcome(session_id: str, run_dir) -> None:
    """R467 (audit P0-5): "a 'what changed because of your direction'
    card in the UI" — computed FROM THE RUNS' OWN RECORDS, never
    asserted. When this session is a steered child (parent_session_id
    set), compare the child's recorded mechanism identity with the
    parent's and persist a typed directive_outcome on the session.
    No-change is recorded honestly as no-change (the audit's measured
    complaint was an UNDISCLOSED same-mechanism re-derivation — the
    answer is the typed comparison, not a flattering one).

    R470 (external re-audit P0-5, the SEMANTICS leg): the card now
    judges COMPLIANCE WITH THE DIRECTIVE, not mere change — the
    re-audit's measured case was a card that said "changed" while the
    child's mechanism stayed inside the explicitly forbidden territory.
    When an exclusion-class constraint is on the record (the spawn
    site's typed derivation from the parent's recorded identity), the
    typed verdict comes from the ONE shared compliance instrument
    (directive_compliance.compliance_verdict — the same function the
    SYNTHESIZE stage's mechanical check uses, Art. X): COMPLIED_CHANGED
    / MOVED_BUT_IN_TERRITORY / NOT_COMPLIED_SAME_AS_PARENT / NO_BASELINE
    / NO_CHILD_MECHANISM / NOT_APPLICABLE. Every outcome is stated as
    recorded — no verdict is softened."""
    try:
        s = store.get_session(session_id) or {}
        parent_id = s.get("parent_session_id")
        if not parent_id:
            return
        parent = store.get_session(str(parent_id)) or {}
        p_id = _mechanism_identity(parent.get("run_dir"))
        c_id = _mechanism_identity(run_dir)
        directive_words = ""
        for e in (s.get("conversation") or []):
            t = str((e or {}).get("text") or "")
            if t.startswith("["):
                directive_words = t.split("] ", 1)[-1].strip()
                break
        if not directive_words:
            directive_words = str((s.get("user_text") or "").rsplit(
                "Direction for this round: ", 1)[-1]).strip()
        # the constraint: the session copy first, else the run-dir
        # record (the durable input record the worker wrote at spawn)
        constraint = s.get("directive_constraint")
        if not (isinstance(constraint, dict)
                and constraint.get("forbidden_mechanism")):
            try:
                import json as _json
                _cp = Path(str(run_dir)) / "DIRECTIVE_CONSTRAINT.json"
                if _cp.exists():
                    _loaded = _json.loads(_cp.read_text())
                    # the engineer's pass-2 F3/F4: only a valid dict
                    # record overrides the session copy — a corrupt
                    # file never NULLS a typed derivation-failure
                    # record the session already holds
                    if isinstance(_loaded, dict):
                        constraint = _loaded
            except (OSError, ValueError):
                constraint = None
        from discovery_fabric.engine.directive_compliance import (
            compliance_verdict as _compliance_verdict)
        _cv = _compliance_verdict(constraint, p_id.get("mechanism"),
                                  c_id.get("mechanism"))
        verdict = _cv["verdict"]
        territory = _cv.get("territory") or {}
        changed = _cv.get("mechanism_changed")
        if verdict == "COMPLIED_CHANGED":
            summary = ("Your direction moved the mechanism, and out of "
                       "the territory it excluded: the parent round "
                       f"recorded '{p_id.get('mechanism')}'; this round "
                       f"recorded '{c_id.get('mechanism')}'.")
        elif verdict == "MOVED_BUT_IN_TERRITORY":
            summary = ("The mechanism moved, but it still restates the "
                       "mechanism your direction excluded ('"
                       + str((constraint or {}).get(
                           "forbidden_mechanism")) + "'). Your "
                       "direction is on the record — and so is this "
                       "shortfall, stated exactly as measured.")
        elif verdict == "NOT_COMPLIED_SAME_AS_PARENT":
            summary = ("This round re-derived the same mechanism "
                       "family as the parent ('"
                       + str(c_id.get("mechanism")) + "') — your "
                       "direction explicitly asked away from it, and "
                       "the round did not comply.")
        elif verdict == "CONSTRAINT_DERIVATION_FAILED":
            summary = ("The engine could not derive the machine-checkable "
                       "form of your direction from the parent round's "
                       "record (the constraint record is on file with "
                       "the failure typed) — your direction is on the "
                       "record and rode the round's problem text; this "
                       "card just cannot claim compliance either way.")
        elif verdict == "NO_BASELINE":
            summary = ("The parent round recorded no mechanism to "
                       "compare against; this round recorded "
                       f"'{c_id.get('mechanism')}'.")
        elif verdict == "NO_CHILD_MECHANISM":
            summary = ("This round did not reach a recorded mechanism "
                       "— there is nothing to compare yet (the "
                       "directive and the inherited answers are on "
                       "the record).")
        elif verdict == "NOT_APPLICABLE":
            # no exclusion-class constraint — the change comparison
            # still stands (an honest visibility record without a
            # compliance claim)
            changed = bool(
                p_id.get("mechanism") and c_id.get("mechanism")
                and p_id["mechanism"].lower() != c_id["mechanism"].lower())
            if changed:
                summary = ("Your direction changed the mechanism: the "
                           "parent round recorded '"
                           + str(p_id.get('mechanism')) + "'; this "
                           "round recorded '"
                           + str(c_id.get('mechanism')) + "'.")
            elif p_id.get("mechanism") and c_id.get("mechanism"):
                summary = ("This round re-derived the same mechanism "
                           "family as the parent ('"
                           + str(c_id.get("mechanism")) + "') — your "
                           "direction is on the record, but it did not "
                           "move the dominant mechanism.")
            elif c_id.get("mechanism"):
                summary = ("The parent round recorded no mechanism to "
                           "compare against; this round recorded "
                           f"'{c_id.get('mechanism')}'.")
            else:
                summary = ("This round did not reach a recorded "
                           "mechanism — there is nothing to compare "
                           "yet (the directive and the inherited "
                           "answers are on the record).")
        else:
            # the engineer's pass-2 F1: verdict-enum drift fails LOUD —
            # an unrecognized verdict is recorded as uninterpretable,
            # never silently degraded into the flattering change
            # comparison (the exact undisclosed-territory class the
            # re-audit measured)
            summary = ("The engine recorded a compliance verdict this "
                       "card does not recognize ('" + str(verdict) +
                       "') — stated as measured, not softened.")
            try:
                from toscanini import worker_forensics as _wfx_v
                _wfx_v.attach_session(
                    session_id,
                    durable_root=_wfx_v.durable_root()).event(
                        "DIRECTIVE_VERDICT_UNINTERPRETED",
                        verdict=str(verdict))
            except Exception:  # noqa: BLE001 — fail-open, never fatal
                pass
        store.update_session(
            session_id,
            directive_outcome={
                "parent_session_id": str(parent_id),
                "directive": directive_words or None,
                "parent_mechanism": p_id.get("mechanism"),
                "child_mechanism": c_id.get("mechanism"),
                "child_intervention": c_id.get("intervention"),
                "mechanism_changed": changed,
                "compliance_verdict": verdict,
                "territory": territory or None,
                "summary": summary,
                "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                             time.gmtime()),
                "method": ("R470: directive_compliance.compliance_verdict "
                           "over envelope_SYNTHESIZE.mechanism_map "
                           "identities — compliance with the typed "
                           "directive constraint, computed from the "
                           "runs' records, never asserted"),
            })
    except Exception:  # noqa: BLE001 — typed, never fatal to terminal
        print(f"  [worker] directive_outcome computation failed: "
              f"{session_id}", file=sys.stderr)


def merge_stored_clarification(session: dict, session_id: str, pu: dict):
    """R471 (external audit P0-5, PARALLEL-LINE UNION): merge the
    session's stored clarification answer into the Problem
    Understanding INPUT record as USER_STATED — and NEVER clear it from
    the session.

    The OLD path wrote clarification_answer={} after the merge, so the
    result payload exposed an EMPTY typed field after reload, and a
    worker death between the clear and the PU persist could re-ask a
    question the user had already answered. Both R471 lines fixed this
    independently; the union keeps BOTH field vocabularies so either
    line's tests read their marks: the sibling's consumed_at +
    merged_into (consumption marked in place) and this line's applied_at
    + the full answer spread (every prior field, e.g. the answer
    route's provenance/answered_at, survives the merge untouched). The
    merge itself is IDEMPOTENT (problem_understanding.
    apply_clarification_answer dedupes on field+answer), so a retried
    run re-executes this block without duplicating the record."""
    answer = session.get("clarification_answer") or {}
    if not (isinstance(answer, dict) and answer.get("field")
            and answer.get("answer")):
        return pu
    from toscanini.conversational import problem_understanding as _pu_mod
    pu = _pu_mod.apply_clarification_answer(
        pu, answer["field"], answer["answer"])
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    store.update_session(session_id, clarification_answer={
        **answer,
        "provenance": "USER_STATED",
        "applied_at": answer.get("applied_at") or now,
        "consumed_at": answer.get("consumed_at") or now,
        "merged_into": "problem_understanding_input",
    })
    return pu


def merge_attachments_typed(session: dict, session_id: str, pu: dict,
                            forensics=None):
    """R459 (audit P0-3): the session's staged attachments merge into
    the Problem Understanding INPUT record as typed USER_EVIDENCE
    (server-side extraction, content hash on record).

    R465 (the R463-C2 open item, closed): the merge outcome is TYPED
    and OBSERVABLE in every state. The previous block was fail-open and
    swallowed its own exceptions, so a silent empty-merge was
    indistinguishable from a success — the exact reason the audit's
    P0-3 acceptance could not be verified end-to-end. Now:

      merged          -> the PU record carries user_evidence (the
                         /events projection derives the ledger event
                         from that persisted artifact) and the
                         owner-scoped forensics record ATTACHMENTS_MERGED
      merge failed    -> forensics ATTACHMENTS_MERGE_INCOMPLETE with the
                         typed exception class; the run continues on
                         the user's own words — disclosed, never silent
      staged, none
      resolved        -> forensics ATTACHMENTS_MERGE_INCOMPLETE with the
                         bound=0 reason (owner-scoped resolution found
                         no readable record)
      nothing staged  -> no events (nothing was staged — no outcome to
                         disclose; the ledger never records noise)

    The events-ledger journal write happens only when a run journal
    already exists (run_dir set): a pre-run-dir write would land in a
    CWD-relative path — the R431-era defect this round retires (the
    journal is per-run by contract). Attachments never kill a run; a
    failure is disclosed, never silent (Art. XV/LXI). Summaries carry
    counts, hashes, and typed reasons — never document content."""
    staged = list(session.get("attachment_ids") or [])
    outcome = {"staged": len(staged), "resolved": 0, "merged": False,
               "reason": None}
    if not staged:
        return pu, outcome
    bound: list = []
    run_dir = str(session.get("run_dir") or "")
    try:
        from toscanini import attachments as _att_mod
        bound = _att_mod.resolve_bindings(session,
                                          session.get("owner_key") or "")
        outcome["resolved"] = len(bound)
        if bound:
            from toscanini.conversational import problem_understanding \
                as _pu_mod
            pu = _pu_mod.apply_attachments(pu, bound)
            outcome["merged"] = True
    except Exception as exc:  # noqa: BLE001 — attachments must never
        # kill a run; the failure is TYPED here, never silent
        outcome["reason"] = type(exc).__name__
    if not outcome["merged"] and outcome["reason"] is None:
        outcome["reason"] = ("staged attachment id(s) resolved to no "
                             "readable record")
    if run_dir:
        # the run journal exists — the outcome belongs on it too
        try:
            from toscanini import event_journal as _journal
            if outcome["merged"]:
                hashes = ", ".join(str(a.get("sha256") or "")[:12]
                                   for a in bound)
                _journal.record(run_dir, session_id,
                                kind="attachment.ingested",
                                stage="PROBLEM", status="COMPLETED",
                                summary=(f"{len(bound)} user document(s) "
                                         "joined the investigation's "
                                         "record as typed USER_EVIDENCE "
                                         "(content hashes: "
                                         f"{hashes})"),
                                epistemic_class="SOURCE_FACT",
                                basis_ref="attachments ledger")
            else:
                _journal.record(run_dir, session_id,
                                kind="attachment.ingested",
                                stage="PROBLEM", status="UNKNOWN",
                                summary=("the user-evidence merge did "
                                         f"not complete "
                                         f"({outcome['reason']}); the "
                                         "run continues on the user's "
                                         "own words — the staged "
                                         "documents stay on record "
                                         "with their content hashes"),
                                epistemic_class="SOURCE_FACT",
                                basis_ref="attachments ledger")
        except Exception:  # noqa: BLE001 — journaling is fail-open
            pass
    if forensics is not None:
        try:
            forensics.event(
                "ATTACHMENTS_MERGED" if outcome["merged"]
                else "ATTACHMENTS_MERGE_INCOMPLETE",
                staged=outcome["staged"], resolved=outcome["resolved"],
                typed=(outcome["reason"] or "merged"),
                stage="UNDERSTANDING_PROBLEM")
        except Exception:  # noqa: BLE001 — forensics is fail-open
            pass
    return pu, outcome


def run(session_id: str) -> None:
    # R419c heartbeat: the FIRST line in the worker log for every run —
    # R463: the log is the run's OWN per-session file
    # (ENGINE_RUNS/worker_logs/{sid}.log) and its tail is served to the
    # session's owner via /api/run/{id}/worker-diagnostics (no operator
    # key — the owner capability is the authority), so a worker that
    # dies before phase 0 is VISIBLE to the person who owns the run,
    # not silent (observed live: sessions stuck PENDING with an empty
    # log tail gave no evidence of even attempting the import chain)
    print(f"[worker] start sid={session_id} pid={os.getpid()} "
          f"blender={os.environ.get('BLENDER_PATH', '') or 'unset'}",
          file=sys.stderr, flush=True)

    # R422 (directive 2 — the a5a7 anomaly): the DURABLE forensic ledger.
    # Every phase boundary, heartbeat, and death (exception OR SIGTERM) is
    # appended + fsync'd to TOSCANINI_UI/worker_forensics/ledger.jsonl
    # BEFORE the worker proceeds — so a transient worker death leaves
    # diff-able evidence that rides the durable snapshot push out of the
    # container instead of dying with it. Fail-open: a forensics failure
    # NEVER blocks the run (the product gains no new failure mode).
    from toscanini import worker_forensics as _fx
    with _fx.WorkerForensics(session_id=session_id, kind="run",
                             durable_root=_fx.durable_root()) as forensics:
        with _fx.heartbeat_loop(forensics):
            _run_inner(session_id, forensics)


def _phase4_terminal_state(run_dir, final, manifest):
    """R446-C1 Task 4: the phase-4 terminal decision, bound to the
    canonical completion marker (run_manifest.json — R445-C: the TRUE
    completion marker; final_state.json is persisted PRE-evolution and
    is NOT completion evidence). Returns (status, final_status, error):
    COMPLETE only when the on-disk marker proves the run() tail
    executed; INTERRUPTED (recoverable) otherwise — never a scientific
    verdict either way (Art. LXI)."""
    from toscanini import completion as _completion
    marker_state = _completion.completion_marker_state(run_dir)
    if marker_state["completion"] != _completion.COMPLETE_MARKED:
        return ("INTERRUPTED",
                (final or {}).get("final_status"),
                ("run ended without the canonical completion marker "
                 "(run_manifest.json): "
                 + str(marker_state.get("reason", ""))[:300]))
    return ("COMPLETE",
            (final or {}).get("final_status")
            or (manifest or {}).get("final_status", "UNKNOWN"),
            None)


def _run_inner(session_id: str, forensics) -> None:
    forensics.event("PHASE_STARTED", stage="SESSION_LOOKUP", phase=0)
    s = store.get_session(session_id)
    if not s:
        print(f"session {session_id} not found", file=sys.stderr)
        forensics.event("WORKER_ABORT", reason="session not found",
                        stage="SESSION_LOOKUP")
        sys.exit(2)

    # --- phase 0: job lifecycle (durable, restart-safe) ----------------------
    forensics.event("PHASE_STARTED", stage="REGISTER_RUNNING", phase=0)
    _register_running(session_id)

    # Hold ONE run-capacity slot for the whole run (R459-reaudit P1-1:
    # up to TOSCANINI_RUN_SLOTS engine runs execute concurrently; the
    # arrival-priority queue keeps start order honest).
    forensics.event("PHASE_STARTED", stage="ACQUIRING_RUN_LOCK", phase=0,
                    note=f"capacity={store.run_slot_count()} slots")
    _lock_handle = _serialize_run()
    forensics.event("PHASE_STARTED", stage="TRANSPORT_PROBE", phase=1,
                    note="run slot acquired")

    # --- phase 1: transport -------------------------------------------------
    # R415 (P0 directive §§1, 6-9): the probe is a REAL completion through
    # the routing registry's fallback LADDER — llm_registry.generate()
    # now cascades across (provider, model) rungs, so one retired model
    # (HTTP 410 GONE) demotes that model and the next rung serves the run.
    # The probe failing means EVERY rung failed.
    #
    # R422 (LLM chokepoint directive — transport reliability): the free-tier
    # models flap per-model (OBSERVED live 2026-09-08 06:29-06:35Z: two
    # rungs INVALID_RESPONSE at 06:30, a fresh probe OK on rung 2 at 06:34).
    # A single 10 s retry is too eager to declare the routes exhausted:
    # the backoff ladder is now 3 attempts (probe / +10 s / +30 s) — still
    # bounded, still honest, and a transport that recovers within ~40 s
    # no longer burns a user's run into RUN_BLOCKED_TRANSPORT.
    _PROBE_BACKOFF_S = (0, 10, 30)
    g = gw.ensure_gateway()
    probeable = g["status"] in ("UP", "ALREADY_UP", "EXTERNAL")
    probe = None
    if probeable:
        for i, backoff in enumerate(_PROBE_BACKOFF_S):
            if backoff:
                print(f"  [worker] probe attempt {i + 1} after {backoff} s "
                      f"backoff", file=sys.stderr)
                time.sleep(backoff)
            forensics.event("TRANSPORT_PROBE", attempt=i + 1,
                            stage="TRANSPORT_PROBE")
            probe = gw.preflight_probe()
            if probe.get("status") == "OK":
                break
            print(f"  [worker] transport probe failed "
                  f"({probe.get('status')})", file=sys.stderr)
    else:
        probe = {"status": "NO_TRANSPORT", "error": str(g)}
    if probe.get("status") != "OK":
        # directive §1: the failure record carries provider / endpoint /
        # HTTP status / model / attempt / timestamp / failure_class from
        # the probe's own typed route (never a bare "failed")
        route_detail = _route_detail(probe)
        forensics.event("TERMINAL_STATE", terminal="RUN_BLOCKED_TRANSPORT",
                        stage="TRANSPORT_PROBE",
                        route_tail=_route_detail(probe)[:500])
        store.update_session(
            session_id, status="RUN_BLOCKED_TRANSPORT",
            error=(f"Discovery temporarily blocked by infrastructure. "
                   f"Your problem is saved and ready to resume. "
                   f"[transport exhausted: gateway={g.get('status')} "
                   f"probe={probe.get('status')} {route_detail} "
                   f"{probe.get('error', '')}")[:400])
        _snapshot(session_id, f"terminal:RUN_BLOCKED_TRANSPORT:{session_id}")
        return

    # --- phase 1.9: the conversational problem understanding (R446-C1) ------
    # Directive §3: BEFORE the discovery pipeline begins, produce the
    # structured interpretation (PROBLEM_UNDERSTANDING contract) with
    # every inferred field explicitly typed. Directive §4: ask at most
    # ONE information-efficient clarification, and ONLY when the answer
    # materially changes the search space — otherwise run autonomously.
    forensics.event("PHASE_STARTED", stage="UNDERSTANDING_PROBLEM",
                    phase=1.9)
    try:
        from toscanini.conversational import problem_understanding as _pu_mod
        from toscanini.conversational import clarification as _cl_mod
        from toscanini.conversational import conversation_memory as _cm_mod
        # R461 (independent audit P0-5, reproduced live): the persisted
        # Problem Understanding INPUT record is the truth this run
        # already earned — a restart must not silently rebuild it from
        # user_text alone, or every USER_STATED merge (a clarification
        # answer, a steering directive) is lost and the engine re-asks
        # a question the user already answered. A persisted record is
        # loaded; only its ABSENCE rebuilds (the historical path).
        # R463 (measured live on production, run ts_fa75e009ed5e): the
        # call previously passed a second argument the R461 loader does
        # not take — a TypeError fired on EVERY fresh run, the
        # disclosed fallback skipped problem understanding entirely,
        # and the defect was invisible until the R463 owner-scoped
        # per-session worker log surfaced it. The record binding is the
        # session_id filename (user_text is immutable per session);
        # the loader takes the session_id alone.
        pu = _load_problem_understanding(session_id)
        if pu is None:
            pu = _pu_mod.build_problem_understanding(
                s["user_text"], session_id=session_id)
        # conversation memory: the user's opening message is CONTEXT
        # (recorded, classified) — it can never mutate canonical
        # scientific state (directive §12; the guard is structural)
        _ctx = _cm_mod.record_conversation_context(
            s, s["user_text"])
        store.update_session(session_id,
                             **_cm_mod.guard_session_update(
                                 {"conversation": _ctx["conversation"]}
                             )["allowed"])
        # a stored clarification answer (from a prior pause) merges as
        # USER_STATED before the need is re-evaluated (R471 audit P0-5:
        # NEVER cleared — see merge_stored_clarification).
        pu = merge_stored_clarification(s, session_id, pu)
        # R459 (audit P0-2): a conversational steering directive (from
        # the action contract) merges as USER_STATED context on the NEW
        # round's input record — the engine decides what it means
        # scientifically; the directive never mutates a verdict.
        _directive = s.get("user_directive") or {}
        if isinstance(_directive, dict) and _directive.get("directive"):
            pu = _pu_mod.apply_user_directive(
                pu, str(_directive["directive"]),
                str(_directive.get("verb") or ""))
            store.update_session(session_id, user_directive={})
        # R459 (audit P0-3): bound attachments merge as typed
        # USER_EVIDENCE — R465: the outcome is TYPED and OBSERVABLE in
        # every state (merged / failed-with-reason / bound=0 reason);
        # the fail-open block that swallowed its own exceptions is
        # retired (a silent empty-merge was indistinguishable from a
        # success — the class that kept the audit's P0-3 unverifiable)
        pu, _att_outcome = merge_attachments_typed(
            s, session_id, pu, forensics=forensics)
        need = _cl_mod.evaluate_clarification_need(pu)
        if need["needed"] and not s.get("clarification_answer"):
            # directive §4: ONE useful clarification, then pause. The
            # problem is saved; the answer resumes the SAME worker
            # path (POST /api/run/{id}/answer re-enqueues). No LLM
            # extraction or retrieval compute is burned while the
            # question is open (the pause is BEFORE phase 2).
            store.update_session(
                session_id, status="AWAITING_CLARIFICATION",
                clarification={
                    "field": need["field"],
                    "question": need["question"],
                    "decision_changed": need["decision_changed"],
                    "score": need["score"],
                    "asked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime()),
                })
            _pu_path = store.STORE_DIR / \
                f"problem_understanding_{session_id}.json"
            try:
                import json as _json
                _pu_path.write_text(_json.dumps(pu, indent=1,
                                                ensure_ascii=False))
            except Exception:  # noqa: BLE001 — input record, fail-open
                pass
            try:
                from toscanini import event_journal as _journal
                _journal.record(
                    str(s.get("run_dir") or ""), session_id,
                    kind="clarification.requested", stage="PROBLEM",
                    status="BLOCKED",
                    summary=("one clarification materially changes the "
                             "search space: " +
                             str(need["question"])[:200]),
                    epistemic_class="INFERRED",
                    basis_ref=f"problem_understanding (session "
                              f"{session_id})")
            except Exception:  # noqa: BLE001 — journaling is fail-open
                pass
            forensics.event("CLARIFICATION_REQUESTED",
                            field=need["field"],
                            question=str(need["question"])[:200])
            _snapshot(session_id,
                      f"awaiting_clarification:{session_id}")
            return
        # persist the PU alongside the session (the run-dir copy lands
        # in phase 2.1 once the run dir exists — one record, two views;
        # the session copy is per-session, never shared)
        try:
            import json as _json
            _pu_path = store.STORE_DIR / \
                f"problem_understanding_{session_id}.json"
            _pu_path.write_text(_json.dumps(pu, indent=1,
                                            ensure_ascii=False))
        except Exception:  # noqa: BLE001 — input record, fail-open
            pass
        # R461 (audit P0-5): the EARLIEST durable checkpoint of real
        # progress — the merged input record + the run's live state —
        # pushed the moment it exists. Before this, every restart
        # inside the run's active window resurrected the last
        # pause/terminal snapshot (measured: the user's clarification
        # answer silently discarded by a 23:36:13Z restart).
        _snapshot(session_id,
                  f"problem_understanding_merged:{session_id}")
        s = store.get_session(session_id) or s
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal:
        # the PU layer is an INPUT RECORD; a failure here degrades to
        # the pre-R446 autonomous flow (recorded honestly, Art. XV)
        forensics.event("PROBLEM_UNDERSTANDING_ERROR",
                        error_class=type(exc).__name__,
                        error=str(exc)[:200])
        print(f"  [worker] problem understanding failed (continuing "
              f"without it): {type(exc).__name__}: {exc}", file=sys.stderr)

    # --- phase 2: evidence-bound problem ------------------------------------
    forensics.event("PHASE_STARTED", stage="BUILDING_PROBLEM", phase=2)
    try:
        # R431: the live event journal — every real phase event lands
        # persisted the moment it occurs (per-source retrieval events
        # included; the journal is the SSE/refresh-recovery source)
        from toscanini import event_journal as _journal
        # R465: the run_dir does not exist until phase 2 completes (the
        # problem id names it) — the callback resolves it LAZILY at
        # write time. The eager string capture journaled the whole
        # phase-2 retrieval window into a CWD-relative path that no
        # reader ever served (typed-dropped by the journal now).
        def _run_dir_resolver() -> str:
            _cur = store.get_session(session_id) or {}
            return str(_cur.get("run_dir") or "")
        _phase_cb = _journal.phase_callback(_run_dir_resolver,
                                            session_id)
        # run_dir is created below; the journal writer mkdirs lazily
        built = problem_builder.build_problem(s["user_text"],
                                              on_event=_phase_cb)
    except Exception as exc:  # noqa: BLE001
        forensics.event("TERMINAL_STATE", terminal="ERROR_BUILD",
                        stage="BUILDING_PROBLEM",
                        error_class=type(exc).__name__)
        store.update_session(session_id, status="ERROR_BUILD",
                             error=f"{type(exc).__name__}: {exc}"[:400])
        _snapshot(session_id, f"terminal:ERROR_BUILD:{session_id}")
        return
    problem = built["problem"]
    # R470 (audit P0-5, the POWER leg): a steered child whose directive
    # rejects the parent's mechanism carries that mechanism into the
    # engine problem as an EXPLICIT EXCLUSION — the synthesis prompt and
    # the mechanism-space operators are instructed to derive a DIFFERENT
    # mechanism. Provenance rides on the problem record (never a silent
    # constraint); the field is absent for unsteered runs (the prompt is
    # byte-identical to the pre-R470 shape).
    _rej = s.get("rejected_mechanism")
    if isinstance(_rej, dict) and str(_rej.get("mechanism") or "").strip():
        problem["rejected_mechanism"] = str(_rej["mechanism"])[:400]
        problem["rejected_mechanism_provenance"] = {
            k: _rej.get(k) for k in (
                "parent_session_id", "parent_final_status", "directive")
            if _rej.get(k) is not None}
        forensics.event("MECHANISM_EXCLUSION_ACTIVE",
                        parent=_rej.get("parent_session_id"),
                        directive=str(_rej.get("directive") or "")[:120])
    store.save_evidence_pack(session_id, built["evidence_pack"])
    run_dir = store.ENGINE_RUNS / f"toscanini_ui_{problem['problem_id']}"
    store.update_session(session_id,
                         problem_id=problem["problem_id"],
                         run_dir=str(run_dir),
                         domain=built["domain"])
    # R470 (external re-audit P0-5, the POWER leg): a typed directive
    # constraint (built at the spawn site from the parent's RECORDED
    # mechanism identity) rides the problem into the engine — the
    # SYNTHESIZE stage excludes the forbidden identity from the search
    # (one recorded repair retry on violation), and the outcome layer
    # judges COMPLIANCE against the same record. The run-dir copy is
    # the durable input record (next to the persisted PU); the session
    # copy stays untouched. Fail-open: the constraint is an input
    # record — its absence degrades to the pre-R470 behavior honestly.
    try:
        _dc = (s.get("directive_constraint")
               if isinstance(s, dict) else None)
        if isinstance(_dc, dict) and _dc.get("forbidden_mechanism"):
            import json as _json
            (run_dir / "DIRECTIVE_CONSTRAINT.json").write_text(
                _json.dumps(_dc, indent=1, ensure_ascii=False))
            problem["directive_constraint"] = _dc
            forensics.event("DIRECTIVE_CONSTRAINT_APPLIED",
                            verb=str(_dc.get("verb") or ""),
                            forbidden_terms=len(
                                _dc.get("forbidden_terms") or []))
    except Exception as exc:  # noqa: BLE001 — input record, fail-open
        forensics.event("DIRECTIVE_CONSTRAINT_WRITE_FAILED",
                        error_class=type(exc).__name__)

    # --- phase 2.1: enrich + persist the PU into the run dir (R446-C1) --
    # The MODEL_DERIVED LLM extraction merges into the PU contract with
    # every merged field typed MODEL_DERIVED_LLM; USER_STATED fields are
    # never overridden (disagreements recorded). The run-dir copy is the
    # one the product event layer and the run contract read.
    try:
        from toscanini.conversational import problem_understanding as _pu_mod
        pu = _pu_mod.enrich_with_extraction(pu, built.get("extraction") or {})
        _pu_mod.persist(pu, run_dir)
    except Exception as exc:  # noqa: BLE001 — input record, fail-open
        print(f"  [worker] PU enrichment/persist failed (disclosed): "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)

    # --- phase 3: the engine — now with the adaptive stage gate ----------
    # Directive §5/§8: the NBA controller decides from the CURRENT
    # recorded envelope at every stage boundary; the stage policy turns
    # that decision into RUN/SKIP/DEFER/BLOCK/STOP. Absent gate → the
    # engine's default full-chain behavior (identical to pre-R446).
    forensics.event("PHASE_STARTED", stage="ENGINE_RUN", phase=3,
                    problem_id=problem["problem_id"])
    from discovery_fabric.engine.run import EngineRun
    try:
        # R431: the engine journals each stage the moment its envelope
        # is persisted (the event_callback contract)
        from toscanini import event_journal as _journal
        _engine_cb = _journal.engine_callback(str(run_dir), session_id)

        def _stage_gate(stage, env, _nba_record=None):
            # directive §8: the action must ACTUALLY determine the next
            # execution path — the controller recomputes from the
            # CURRENT recorded envelope before every stage and the
            # policy consumes its preferred action
            import json as _json
            from toscanini.conversational import nba_controller
            from toscanini.conversational import stage_policy
            try:
                nba = nba_controller.decide(env.to_dict())
                engine._nba_record = nba
                # persist the controller record (last-wins; it is the
                # run's own controller trail, read by the run contract)
                (run_dir / "NBA_CONTROLLER.json").write_text(
                    _json.dumps(nba, indent=1, ensure_ascii=False))
            except Exception:  # noqa: BLE001 — controller fail-open
                nba = None
            return stage_policy.engine_gate(stage, env, nba)

        engine = EngineRun(problem, str(run_dir), with_package=True,
                           event_callback=_engine_cb,
                           session_id=session_id,
                           stage_gate=_stage_gate)
        manifest = engine.run()
    except Exception as exc:  # noqa: BLE001
        forensics.event("TERMINAL_STATE", terminal="ERROR_RUN",
                        stage="ENGINE_RUN",
                        error_class=type(exc).__name__)
        store.update_session(session_id, status="ERROR_RUN",
                             error=f"{type(exc).__name__}: {exc}"[:400],
                             traceback=traceback.format_exc()[-2000:])
        _snapshot(session_id, f"terminal:ERROR_RUN:{session_id}")
        return

    # --- phase 3.5: the automatic artifact contract (R418) -----------------
    # Operator P0 product correction: every completed run with an
    # invention gets its visual artifact + technology package
    # automatically — Case A (artifact exists -> render), Case B
    # (invention exists, artifact missing -> generate), Case C (not
    # visualizable -> conceptual fallback, labeled). No operator
    # script, no copied JSON, no manual post-processing. A bridge
    # failure is an honest typed record — it NEVER changes the run's
    # epistemic state (Art. VI/XV/LXI) and never blocks completion.
    #
    # R446-C1 §23 (lazy execution): the expensive-artifact policy is
    # consulted FIRST — a killed candidate (the recorded challenge
    # verdict is authoritative, R452) generates NO artifacts, and the
    # refusal is a typed decision record (SKIP / NOT_REQUIRED with the
    # directive's own example semantics), never a silent code path.
    forensics.event("PHASE_STARTED", stage="BRIDGE_GATE", phase=3.5)
    _artifact_policy = None
    try:
        from toscanini.conversational import stage_policy as _sp
        _env_state = (engine.env.to_dict()
                      if getattr(engine, "env", None) is not None else {})
        import json as _json_l
        _lineage = None
        if (run_dir / "INVENTION_LINEAGE.json").is_file():
            _lineage = _json_l.loads(
                (run_dir / "INVENTION_LINEAGE.json").read_text())
        _artifact_policy = _sp.expensive_artifact_policy(
            _env_state, _lineage)
        if _artifact_policy.get("decision") != "RUN":
            _json_l.dump(_artifact_policy,
                         open(run_dir / "EXPENSIVE_ARTIFACT_POLICY.json",
                              "w"), indent=1, ensure_ascii=False)
            forensics.event("ARTIFACT_POLICY_REFUSED",
                            decision=_artifact_policy.get("decision"),
                            skip_class=_artifact_policy.get("skip_class"),
                            reason=str(
                                _artifact_policy.get("reason"))[:200])
            print(f"  [worker] artifact policy refused "
                  f"({_artifact_policy.get('decision')}/"
                  f"{_artifact_policy.get('skip_class')}): "
                  f"{str(_artifact_policy.get('reason'))[:160]}",
                  file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — policy fail-open (the
        # bridge's own gates still govern; the failure is disclosed)
        print(f"  [worker] artifact policy consultation failed "
              f"(disclosed): {type(exc).__name__}: {exc}", file=sys.stderr)
    if _artifact_policy is not None and \
            _artifact_policy.get("decision") != "RUN":
        # the refusal record stands on its own; the bridge is NOT
        # invoked (no CAD, no visual package, no buyer PDF for a dead
        # candidate — directive §23) and the session records the typed
        # outcome so the product surface can render the honest reason
        store.update_session(session_id,
                             bridge_outcome="SKIPPED_POLICY",
                             bridge_case="ARTIFACT_POLICY")
    else:
        try:
            from toscanini import bridge_gate
            gate = bridge_gate.ensure_artifacts(session_id)
            print(f"  [worker] bridge gate: {gate.get('outcome')}",
                  file=sys.stderr)
            forensics.event("BRIDGE_GATE_OUTCOME",
                            outcome=gate.get("outcome"),
                            case=gate.get("case"))
            # R431: geometry/package events from the gate's own record
            try:
                from toscanini import event_journal as _journal
                _journal.record_bridge_outcomes(
                    str(run_dir), session_id, gate)
            except Exception:  # noqa: BLE001 — journaling is fail-open
                pass
            store.update_session(
                session_id,
                bridge_outcome=gate.get("outcome"),
                bridge_case=gate.get("case"))
            # R422 (UI copy reconciliation, server-side companion): when
            # the async artifact gate lands a package on a run whose
            # completion snapshot recorded package_available=false, the
            # session's package field is refreshed HERE — from the run
            # dir's own package report (the authority, Art. X) — so the
            # stored user_state_view and the product surface can never
            # disagree about package existence.
            # Presentation-snapshot only: no scientific field is touched.
            try:
                from toscanini import cio as _cio_mod
                refreshed = _cio_mod._package_info(run_dir)
                if refreshed.get("complete"):
                    store.update_session(
                        session_id,
                        package={"zip_name": refreshed.get("zip_name"),
                                 "maturity": refreshed.get("maturity"),
                                 "package_kind":
                                     refreshed.get("package_kind"),
                                 "complete": True})
            except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
                print(f"  [worker] package-field refresh failed: "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
            forensics.event("BRIDGE_GATE_ERROR",
                            error_class=type(exc).__name__)
            print(f"  [worker] bridge gate failed: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            store.update_session(
                session_id, bridge_outcome="GATE_ERROR",
                bridge_error=f"{type(exc).__name__}: {exc}"[:400])

    # --- phase 4: honest terminal status -------------------------------------
    forensics.event("PHASE_STARTED", stage="TERMINAL_STATUS", phase=4)
    final = None
    fs_path = run_dir / "final_state.json"
    if fs_path.exists():
        import json
        final = json.loads(fs_path.read_text())
    # R446-C1 Task 4: the canonical completion authority — the marker is
    # verified ON DISK (defense in depth: engine.run() returns the
    # manifest it persisted — this check binds the user-visible COMPLETE
    # to the bytes, not the return value). INTERRUPTED (recoverable) on
    # a missing/incomplete marker — NEVER COMPLETE (Art. XXV/LXI).
    status, final_status, phase4_error = _phase4_terminal_state(
        run_dir, final, manifest)
    if status == "INTERRUPTED":
        forensics.event(
            "TERMINAL_STATE", terminal="INTERRUPTED",
            stage="TERMINAL_STATUS",
            reason=phase4_error[:400],
            marker_authority="run_manifest.json")
        store.update_session(
            session_id, status=status,
            final_status=final_status,
            error=phase4_error)
        _snapshot(session_id, f"terminal:INTERRUPTED:{session_id}")
        return
    # R455-LEAN-1 §2: the pre-retrieval capability gate's terminal is a
    # RUN_BLOCKED_* family member — the session carries the SAME
    # infrastructure-class status the transport probe uses (the product
    # surface then renders the blocked state, never a COMPLETE with a
    # hidden failure and never a scientific verdict, Art. LXI).
    if final_status == "RUN_BLOCKED_CAPABILITY":
        forensics.event(
            "TERMINAL_STATE", terminal="RUN_BLOCKED_CAPABILITY",
            stage="TERMINAL_STATUS",
            reason="pre-retrieval capability gate (R455-LEAN-1 §2): the "
                   "synthesis route can only serve STRONG via "
                   "CHEAP_EMERGENCY_FALLBACK — zero retrieval calls "
                   "spent; resumable on a capable route")
        store.update_session(
            session_id, status="RUN_BLOCKED_CAPABILITY",
            final_status=final_status,
            error=("Discovery paused before spending: the available "
                   "model route cannot serve this run's reasoning "
                   "class (requested STRONG; only a degraded fallback "
                   "exists). Your problem is saved and ready to resume "
                   "on a capable route — this is an infrastructure "
                   "state, not a verdict about your problem."))
        record_directive_outcome(session_id, run_dir)
        _snapshot(session_id, f"terminal:RUN_BLOCKED_CAPABILITY:{session_id}")
        return
    store.update_session(
        session_id, status="COMPLETE",
        final_status=final_status)
    # R467 (audit P0-5): the "what changed because of your direction"
    # record — typed comparison of the child's mechanism identity with
    # the parent's, from the runs' own records (never asserted)
    record_directive_outcome(session_id, run_dir)
    # R431: the terminal event (infra vs scientific never collapsed)
    try:
        from toscanini import event_journal as _journal
        _journal.record_terminal(
            str(run_dir), session_id, "COMPLETE", "run manifest")
    except Exception:  # noqa: BLE001 — journaling is fail-open
        pass

    # --- phase 4.5: R420 — the automatic async render handoff ----------------
    # Operator §1: when the in-worker render was skipped or failed for a
    # typed infrastructure reason (RENDER_SKIPPED_LOW_MEMORY /
    # RENDER_TIMEOUT / RENDER_FAILED / ...), the production worker
    # AUTOMATICALLY enqueues the async artifact-render job. This runs at
    # the END of the run — the gauntlet worker's memory is freed by now,
    # so the async guard decides honestly whether the instance can
    # render. No operator intervention, no copied JSON, no user-side
    # regeneration: invention -> GLB -> render decision -> async job
    # when required -> persisted render record -> CIO -> website. A
    # failure here is disclosed in the log, never fatal to the terminal
    # record (the run is complete; presentation followup is typed).
    forensics.event("PHASE_STARTED", stage="RENDER_FOLLOWUP", phase=4.5)
    try:
        from toscanini import artifact_worker
        followup = artifact_worker.auto_enqueue(
            session_id, enqueued_by="production_worker")
        if followup:
            print(f"  [worker] render followup enqueued "
                  f"({followup.get('followup_reason')}): "
                  f"job={followup.get('status')} "
                  f"pid={followup.get('worker_pid')}", file=sys.stderr)
            store.update_session(
                session_id,
                render_followup="enqueued",
                render_followup_reason=followup.get("followup_reason"))
        else:
            print("  [worker] render followup not needed "
                  "(artifacts complete, nothing to render, or the async "
                  "job already spoke)", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
        print(f"  [worker] render followup enqueue failed: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)

    # --- phase 5: durable epistemic record -----------------------------------
    forensics.event("PHASE_STARTED", stage="FINAL_SNAPSHOT", phase=5)
    _snapshot(session_id, f"terminal:COMPLETE:{session_id}")
    forensics.event("TERMINAL_STATE", terminal="COMPLETE", phase=5)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 -m toscanini.worker <session_id>", file=sys.stderr)
        sys.exit(2)
    run(sys.argv[1])
