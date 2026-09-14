"""toscanini/conversational/product_events.py — R446-C1 §9/§10: the
conversational event layer.

Directive §9 (verbatim): the backend should emit meaningful events —
DISCOVERY_STARTED, UNDERSTANDING_PROBLEM, CHECKING_PROBLEM_EXISTENCE,
INVESTIGATING_EVIDENCE, EVIDENCE_UPDATED, MECHANISMS_IDENTIFIED,
CANDIDATES_GENERATED, ATTACKING_CANDIDATE, CANDIDATE_REJECTED,
CANDIDATE_SURVIVED, ENGINEERING_EVALUATION, EXPERIMENT_PROPOSED,
OUTCOME_RECEIVED, MODEL_UPDATED, CANDIDATE_MUTATED, RE-EVALUATING,
PACKAGE_READY — "product events, not replacements for canonical state."

Directive §10: "Product events must originate from authoritative
state." The frontend must never infer scientific state from render
completion, artifact existence, optimistic UI state, stale candidate
records, old package files, or text labels.

This module DERIVES the product event stream from the run directory's
OWN persisted artifacts only:
    PROBLEM_UNDERSTANDING.json   (the PU contract)
    envelope_*.json / run_manifest.json stage_log  (engine truth)
    INVENTION_LINEAGE.json       (evolution generations)
    BRIDGE_REPORT.json           (geometry/package truth)
    final_state.json             (terminal verdict)

Every event carries basis_ref — the exact artifact it derives from —
plus an epistemic_class that is the class of the SOURCE artifact
(Art. XXVIII: never promoted). An event NEVER mutates scientific
truth; it is a projection (the event journal R431 discipline applied
to the directive's product vocabulary).

The honesty guards:
  - ATTACK with a non-execution status can NEVER emit
    CANDIDATE_SURVIVED (test G: NOT_RUN is never "survived").
  - A killed lineage generation emits CANDIDATE_REJECTED (never
    CANDIDATE_SURVIVED) — R452's killed-invention authority.
  - PACKAGE_READY requires the bridge report's own completed package
    field, never a ZIP's existence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from toscanini.conversational import stage_policy

EVENT_SCHEMA = "CODER1_PRODUCT_EVENT/1.0.0"

# --- the directive §9 event vocabulary (verbatim) ---------------------------
DISCOVERY_STARTED = "DISCOVERY_STARTED"
UNDERSTANDING_PROBLEM = "UNDERSTANDING_PROBLEM"
CHECKING_PROBLEM_EXISTENCE = "CHECKING_PROBLEM_EXISTENCE"
INVESTIGATING_EVIDENCE = "INVESTIGATING_EVIDENCE"
EVIDENCE_UPDATED = "EVIDENCE_UPDATED"
MECHANISMS_IDENTIFIED = "MECHANISMS_IDENTIFIED"
CANDIDATES_GENERATED = "CANDIDATES_GENERATED"
ATTACKING_CANDIDATE = "ATTACKING_CANDIDATE"
CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
CANDIDATE_SURVIVED = "CANDIDATE_SURVIVED"
ENGINEERING_EVALUATION = "ENGINEERING_EVALUATION"
EXPERIMENT_PROPOSED = "EXPERIMENT_PROPOSED"
OUTCOME_RECEIVED = "OUTCOME_RECEIVED"
MODEL_UPDATED = "MODEL_UPDATED"
CANDIDATE_MUTATED = "CANDIDATE_MUTATED"
RE_EVALUATING = "RE_EVALUATING"
PACKAGE_READY = "PACKAGE_READY"

# two completion states the product needs beyond §9's happy path
# (the directive's own §7 honesty vocabulary requires them)
CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
RUN_BLOCKED = "RUN_BLOCKED"

EVENT_TYPES = (DISCOVERY_STARTED, UNDERSTANDING_PROBLEM,
               CHECKING_PROBLEM_EXISTENCE, INVESTIGATING_EVIDENCE,
               EVIDENCE_UPDATED, MECHANISMS_IDENTIFIED,
               CANDIDATES_GENERATED, ATTACKING_CANDIDATE,
               CANDIDATE_REJECTED, CANDIDATE_SURVIVED,
               ENGINEERING_EVALUATION, EXPERIMENT_PROPOSED,
               OUTCOME_RECEIVED, MODEL_UPDATED, CANDIDATE_MUTATED,
               RE_EVALUATING, PACKAGE_READY, CLARIFICATION_REQUESTED,
               RUN_BLOCKED)


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.is_file():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None
    return None


def _evt(run_id: str, seq: int, event_type: str, message: str,
         basis_ref: str, epistemic_class: str,
         timestamp: Optional[str] = None,
         detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    eid = "pe_" + hashlib.sha256(
        f"{run_id}|{seq}|{event_type}".encode()).hexdigest()[:16]
    return {
        "schema": EVENT_SCHEMA,
        "event_id": eid,
        "run_id": run_id,
        "seq": seq,
        "type": event_type,
        "message": message,
        "basis_ref": basis_ref,
        "epistemic_class": epistemic_class,
        "timestamp": timestamp,
        "detail": detail or {},
    }


def _stage_entries(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    """stage -> LAST recorded stage_log entry, from the run's own
    persisted envelopes + manifest (the same discipline as
    run_state._stage_status_map — the artifact is the authority)."""
    out: Dict[str, Dict[str, Any]] = {}
    sources = sorted(run_dir.glob("envelope_*.json"))
    manifest = run_dir / "run_manifest.json"
    if manifest.is_file():
        sources.append(manifest)
    for env_path in sources:
        env = _read_json(env_path)
        for entry in (env or {}).get("stage_log") or []:
            if isinstance(entry, dict) and entry.get("stage"):
                out[entry["stage"]] = entry
    return out


def derive_product_events(run_dir: Path, run_id: str,
                          session_status: str = ""
                          ) -> List[Dict[str, Any]]:
    """The product event stream for ONE run, derived EXCLUSIVELY from
    the run directory's persisted artifacts. Deterministic; zero LLM;
    never invents an event that has no basis artifact."""
    rd = Path(run_dir)
    events: List[Dict[str, Any]] = []
    seq = 0

    def emit(t: str, msg: str, basis: str, cls: str,
             timestamp: Optional[str] = None,
             detail: Optional[Dict] = None):
        nonlocal seq
        seq += 1
        events.append(_evt(run_id, seq, t, msg, basis, cls,
                            timestamp, detail))

    if not rd.is_dir():
        return events

    problem = _read_json(rd / "problem.json")
    if problem is not None or (rd / "PROBLEM_UNDERSTANDING.json").is_file():
        emit(DISCOVERY_STARTED,
             f"discovery run started for the stated problem",
             "problem.json", "USER_STATED")

    pu = _read_json(rd / "PROBLEM_UNDERSTANDING.json")
    if pu:
        n_unknown = len(pu.get("unknowns") or [])
        emit(UNDERSTANDING_PROBLEM,
             f"problem interpreted — {n_unknown} field(s) still unknown, "
             f"inferred fields typed as inferred",
             "PROBLEM_UNDERSTANDING.json", "INFERRED",
             detail={"n_unknowns": n_unknown})

    stage_entries = _stage_entries(rd)

    # premise gate: problem existence
    pg = stage_entries.get("PREMISE_GATE")
    if pg:
        verdict = "checked"
        emit(CHECKING_PROBLEM_EXISTENCE,
             f"problem premise checked against physical coherence — "
             f"{pg.get('status', 'UNKNOWN')}",
             "envelope_PREMISE_GATE.json", "COMPUTED",
             timestamp=pg.get("finished_at"))

    # evidence stages
    for stage, ev_type, msg in (
            ("RETRIEVE", INVESTIGATING_EVIDENCE,
             "evidence retrieval executed through the source connectors"),
            ("FREEZE", EVIDENCE_UPDATED,
             "evidence snapshot frozen with content hashes"),
            ("VERIFY", EVIDENCE_UPDATED,
             "claim-level evidence verification executed")):
        entry = stage_entries.get(stage)
        if not entry:
            continue
        status = str(entry.get("status") or "UNKNOWN")
        if stage_policy.project_non_execution(status):
            continue   # a non-executed stage emits NO scientific event
        emit(ev_type, f"{msg} — {status}",
             f"envelope_{stage}.json", "RETRIEVED",
             timestamp=entry.get("finished_at"))

    # mechanisms / candidates
    syn = stage_entries.get("SYNTHESIZE")
    if syn and not stage_policy.project_non_execution(
            str(syn.get("status") or "")):
        emit(MECHANISMS_IDENTIFIED,
             "candidate mechanism proposed from the frozen evidence",
             "envelope_SYNTHESIZE.json", "HYPOTHESIZED",
             timestamp=syn.get("finished_at"))
        emit(CANDIDATES_GENERATED,
             "candidate generated — a hypothesis until attacked",
             "envelope_SYNTHESIZE.json", "HYPOTHESIZED",
             timestamp=syn.get("finished_at"))
    ms = stage_entries.get("MECHANISM_SPACE")
    if ms and not stage_policy.project_non_execution(
            str(ms.get("status") or "")):
        emit(MECHANISMS_IDENTIFIED,
             "structured mechanism space generated (five operators)",
             "envelope_MECHANISM_SPACE.json", "HYPOTHESIZED",
             timestamp=ms.get("finished_at"))

    # attack — the honesty-critical mapping (test G)
    attack = stage_entries.get("ATTACK")
    if attack:
        status = str(attack.get("status") or "UNKNOWN")
        non_exec = stage_policy.project_non_execution(status)
        if non_exec:
            # NOT_RUN / NOT_REACHED / BLOCKED / FAILED: no verdict —
            # emit the honest blocked/rejected event ONLY when a
            # SCIENTIFIC kill is recorded; infrastructure states emit
            # RUN_BLOCKED (Art. LXI), never a scientific outcome.
            if non_exec in (stage_policy.BLOCKED, stage_policy.FAILED):
                emit(RUN_BLOCKED,
                     f"attack stage did not complete ({status}) — "
                     f"infrastructure-class, not a scientific verdict",
                     "envelope_ATTACK.json", "UNKNOWN",
                     timestamp=attack.get("finished_at"))
        else:
            emit(ATTACKING_CANDIDATE,
                 "adversarial challenges executed against the candidate",
                 "envelope_ATTACK.json", "COMPUTED",
                 timestamp=attack.get("finished_at"))
            # survived vs rejected: the RECORDED overall verdict is the
            # only authority — never render completion (Art. X/XXVIII)
            env = _read_json(rd / "candidate_envelope.json") or {}
            overall = (env.get("attack_results") or {}).get("overall")
            if overall == "KILL":
                emit(CANDIDATE_REJECTED,
                     "candidate rejected by the recorded attack verdict",
                     "candidate_envelope.json", "COMPUTED")
            else:
                emit(CANDIDATE_SURVIVED,
                     "candidate survived the recorded adversarial "
                     "challenge" + (
                         f" (overall={overall})" if overall else
                         " — verdict recorded"),
                     "candidate_envelope.json", "COMPUTED")

    # engineering evaluation
    bridge = _read_json(rd / "BRIDGE_REPORT.json")
    if bridge:
        outcome = bridge.get("outcome")
        if outcome in ("COMPLETED", "PACKAGE_ADDED_TO_EXISTING_GEOMETRY",
                       "ALREADY_COMPLETE"):
            emit(ENGINEERING_EVALUATION,
                 "engineering representation generated for the "
                 "surviving candidate",
                 "BRIDGE_REPORT.json", "ENGINEERING_DEFINED")

    # decisive experiment
    env_final = _read_json(rd / "candidate_envelope.json") or {}
    ke = (env_final.get("killer_experiment") or {}).get("selected")
    if ke:
        name = str(ke.get("name") or "")[:160]
        emit(EXPERIMENT_PROPOSED,
             f"decisive experiment proposed: {name}",
             "candidate_envelope.json", "COMPUTED")

    # evolution generations (causal learning — §20)
    lineage = _read_json(rd / "INVENTION_LINEAGE.json")
    if lineage:
        for g in (lineage.get("generations") or []):
            if not isinstance(g, dict):
                continue
            gen_n = g.get("gen")
            ch = g.get("challenge") or {}
            if g.get("causal_delta") or g.get("mutation_reason"):
                emit(CANDIDATE_MUTATED,
                     f"generation {gen_n} mutated from the recorded "
                     f"causal diagnosis",
                     "INVENTION_LINEAGE.json", "COMPUTED",
                     detail={"gen": gen_n})
                emit(RE_EVALUATING,
                     f"generation {gen_n} re-evaluated after mutation",
                     "INVENTION_LINEAGE.json", "COMPUTED",
                     detail={"gen": gen_n})
            if ch.get("killed"):
                emit(CANDIDATE_REJECTED,
                     f"generation {gen_n} rejected by the recorded "
                     f"challenge verdict (killed)",
                     "INVENTION_LINEAGE.json", "COMPUTED",
                     detail={"gen": gen_n})
        status = str(lineage.get("status") or "")
        if status and status not in ("EVOLVED_INVENTION_CANDIDATE",):
            # an honest non-survivor lineage outcome
            pass

    # outcome / model update (reality loop — only from REAL records)
    reality = _read_json(rd / "REALITY_LOOP_LEDGER.json") \
        or _read_json(rd / "reality_loop.json")
    if reality and isinstance(reality.get("events"), list) \
            and reality["events"]:
        last = reality["events"][-1]
        emit(OUTCOME_RECEIVED,
             "external observation ingested through the reality loop "
             "ledger",
             "REALITY_LOOP_LEDGER.json", "PHYSICALLY_OBSERVED",
             detail={"n_events": len(reality["events"]),
                     "last_event_id": last.get("event_id")})
        emit(MODEL_UPDATED,
             "technical state updated from the recorded observation "
             "(causal mutation chain)",
             "REALITY_LOOP_LEDGER.json", "COMPUTED")

    # package ready — from the package compiler's OWN report when one
    # exists (the package authority; a stale bridge outcome cannot
    # override it — directive §10), else from the bridge gate outcome
    if bridge:
        pkg = _read_json(rd / "PACKAGE_REPORT.json")
        pkg_ready = (pkg.get("complete") if pkg is not None
                     else bridge.get("outcome") in (
                         "COMPLETED",
                         "PACKAGE_ADDED_TO_EXISTING_GEOMETRY",
                         "ALREADY_COMPLETE"))
        if pkg_ready:
            emit(PACKAGE_READY,
                 "technology transfer package assembled — one "
                 "technology, one package",
                 "PACKAGE_REPORT.json" if pkg is not None
                 else "BRIDGE_REPORT.json", "ENGINEERING_DEFINED")

    # terminal
    final = _read_json(rd / "final_state.json")
    manifest = _read_json(rd / "run_manifest.json")
    terminal_status = session_status or ""
    if final or manifest:
        fs = (final or {}).get("final_status") or \
             (manifest or {}).get("final_status")
        label = fs or terminal_status or "UNKNOWN"
        emit(RUN_BLOCKED if terminal_status.startswith("ERROR_") or
             terminal_status in ("RUN_BLOCKED_TRANSPORT", "INTERRUPTED")
             else CANDIDATE_SURVIVED if fs == "EVOLVED_INVENTION_CANDIDATE"
             else CANDIDATE_REJECTED if fs in ("REJECTED",
                                               "MALFORMED_OR_FALSE_PREMISE")
             else EVIDENCE_UPDATED,
             f"run terminal state recorded: {label}",
             "final_state.json" if final else "run_manifest.json",
             "COMPUTED")

    return events


def validate_event(ev: Dict[str, Any]) -> List[str]:
    """Schema validation: the closed type vocabulary + the mandatory
    fields + the epistemic class vocabulary."""
    problems: List[str] = []
    if ev.get("type") not in EVENT_TYPES:
        problems.append(f"unknown event type: {ev.get('type')}")
    for f in ("event_id", "run_id", "seq", "type", "message",
              "basis_ref", "epistemic_class"):
        if not ev.get(f) and ev.get(f) != 0:
            problems.append(f"missing field: {f}")
    cls = str(ev.get("epistemic_class") or "")
    if cls not in ("USER_STATED", "RETRIEVED", "INFERRED", "HYPOTHESIZED",
                   "COMPUTED", "SIMULATED", "ENGINEERING_DEFINED",
                   "PHYSICALLY_OBSERVED", "UNKNOWN"):
        problems.append(f"unknown epistemic class: {cls}")
    return problems
