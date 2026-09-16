"""toscanini/event_journal.py — R431: the persisted append-only
scientific event journal.

R430.1's SSE is a live transport; R431 §2 requires the events to be
PERSISTED WHEN THE UNDERLYING OPERATION ACTUALLY OCCURS — one
append-only journal per run, written by the single writer (the run
worker / its engine callback), fsync'd line by line:

    { "event_id":   deterministic hash of (run, seq, kind)
      "run_id":     session id
      "seq":        line number (deterministic order)
      "stage":      scientific stage (EVIDENCE, MECHANISM, ...)
      "kind":       evidence.retrieved, stage.SYNTHESIZE, geometry.created, ...
      "status":     QUEUED|ACTIVE|COMPLETED|BLOCKED|FAILED_INFRASTRUCTURE|
                    FAILED_SCIENTIFIC|UNKNOWN  (investigation vocabulary)
      "summary":    one honest sentence from the real artifact
      "epistemic_class": RETRIEVED|INFERRED|... (never upgraded)
      "basis_ref":  the persisted artifact this event derives from
      "timestamp":  the artifact's own time when recorded, else the
                    write time (the moment the operation occurred)
      "payload_ref": optional artifact path with detail }

No synthetic progress. No client-side inference. No wall-clock
fabrication — a timestamp is either the artifact's own recorded time
or the append time, never an invented one.

The journal NEVER mutates scientific truth (R431 §4): it records
events; canonical state stays the envelopes/state files. The
/events endpoint merges the journal (live truth) with the R430.1
investigation projection (terminal truth) and reconciles by
event_id.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

JOURNAL_NAME = "EVENT_JOURNAL.jsonl"

# stage -> (scientific stage, epistemic class) — the SAME mapping the
# investigation projection uses (one vocabulary, two projections).
_STAGE_META = {
    "RETRIEVE": ("EVIDENCE", "RETRIEVED"),
    "FREEZE": ("EVIDENCE", "RETRIEVED"),
    "PREMISE_GATE": ("PROBLEM", "COMPUTED"),
    "SYNTHESIZE": ("MECHANISM", "HYPOTHESIZED"),
    "VERIFY": ("EVIDENCE", "RETRIEVED"),
    "MULTI_SOURCE_DISCOVERY": ("PRIOR_ART", "RETRIEVED"),
    "COLLISION": ("PRIOR_ART", "COMPUTED"),
    "PHYSICS": ("PHYSICS", "COMPUTED"),
    "ATTACK": ("CHALLENGE", "COMPUTED"),
    "CONTRADICTION": ("EVIDENCE", "RETRIEVED"),
    "KILLER_EXPERIMENT": ("EXPERIMENT", "COMPUTED"),
    # R481: the IMPROVE stage — the loop closure. The child mechanism
    # is MODEL-proposed from the kill basis: the same epistemic class
    # as SYNTHESIZE (a hypothesis, never computed evidence).
    "IMPROVE": ("MECHANISM", "HYPOTHESIZED"),
    "ADJUDICATION": ("CHALLENGE", "COMPUTED"),
    "CLASSIFY": ("EPISTEMICS", "COMPUTED"),
    "NEXT_BEST_ACTION": ("EPISTEMICS", "COMPUTED"),
    "RANK": ("EPISTEMICS", "COMPUTED"),
}


def journal_path(run_dir: str) -> Path:
    return Path(run_dir) / JOURNAL_NAME


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record(run_dir: str, run_id: str, kind: str, stage: str, status: str,
           summary: str, epistemic_class: str, basis_ref: str,
           payload_ref: Optional[str] = None,
           timestamp: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Append ONE event (fsync). Returns the event, or None on a
    write failure (the journal is fail-open: a journaling failure
    NEVER blocks the run — Art. LXI).

    R465: an EMPTY run_dir is a typed no-op (returns None, writes
    nothing). The journal is PER-RUN by contract; a pre-run-dir write
    used to land in a CWD-relative EVENT_JOURNAL.jsonl that no reader
    ever served — cross-run pollution on the engine's working
    directory (retired; pre-run events ride their own persisted
    artifacts and the owner-scoped forensics instead)."""
    if not run_dir:
        return None
    try:
        p = journal_path(run_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        seq = 1
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                seq = sum(1 for line in f if line.strip()) + 1
        import hashlib
        eid = "evt_" + hashlib.sha256(
            f"{run_id}|{seq}|{kind}|{stage}".encode()).hexdigest()[:16]
        event = {
            "event_id": eid,
            "run_id": run_id,
            "seq": seq,
            "stage": stage,
            "kind": kind,
            "status": status,
            "summary": summary,
            "epistemic_class": epistemic_class,
            "basis_ref": basis_ref,
            "timestamp": timestamp or _now(),
            "payload_ref": payload_ref,
        }
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return event
    except OSError:
        return None


def read(run_dir: str) -> List[Dict[str, Any]]:
    """The journal, in seq order. Unreadable/absent -> empty (honest)."""
    p = journal_path(run_dir)
    if not p.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue  # a torn line is skipped, never fatal
    except OSError:
        return []
    return out


# ---------------------------------------------------------------------------
# Callback adapters: real operations -> journal events
# ---------------------------------------------------------------------------

def phase_callback(run_dir, run_id: str) -> Callable[[Dict], None]:
    """The on_event adapter for problem_builder.build_problem — every
    emitted phase event is a REAL step in progress; the per-source
    completion events land in the journal the moment each source
    finishes (R431 section 3: SOURCE 1, SOURCE 2, ... visible live,
    without waiting for the whole retrieval stage).

    R465: `run_dir` may be a callable (a resolver) — it is evaluated
    LAZILY at each event. The retrieval window runs BEFORE the run
    directory exists (the problem id names it); the eager string
    capture froze an empty path for the whole window, so every
    phase-2 event was journaled to a CWD-relative file no reader ever
    served. With the resolver, events written after the session's
    run_dir is recorded land in the run's own journal; events before
    that moment are typed-dropped by record() (the empty-path guard)."""
    # map of source -> last querying event seq (for summary continuity)
    seen_sources: Dict[str, int] = {}

    def _path() -> str:
        return str(run_dir()) if callable(run_dir) else str(run_dir or "")

    def cb(ev: Dict[str, Any]) -> None:
        phase = str(ev.get("phase") or "")
        label = str(ev.get("label") or "")
        if phase == "RETRIEVE_SOURCE_DONE":
            src = str(ev.get("source") or "?")
            status = str(ev.get("status") or "UNKNOWN")
            count = ev.get("count")
            ok = status == "OK"
            record(
                _path(), run_id,
                kind="evidence.retrieved" if ok else
                     "evidence.retrieval_failed",
                stage="EVIDENCE",
                status="COMPLETED" if ok else "FAILED_INFRASTRUCTURE",
                summary=(f"Source '{src}' retrieval completed — "
                         f"{count} records"
                         if ok else
                         f"Source '{src}' retrieval did not complete "
                         f"(status {status}) — infrastructure, not "
                         f"absence"),
                epistemic_class="RETRIEVED",
                basis_ref=f"evidence pack (session {run_id})",
                payload_ref=None,
            )
            return
        if phase in ("EXTRACT", "RETRIEVE_EVIDENCE", "EVIDENCE_BOUND"):
            kind = {"EXTRACT": "problem.extract",
                    "RETRIEVE_EVIDENCE": "evidence.retrieval_started",
                    "EVIDENCE_BOUND": "evidence.bound"}[phase]
            record(_path(), run_id, kind=kind,
                   stage="PROBLEM" if phase == "EXTRACT" else "EVIDENCE",
                   status="ACTIVE" if phase == "RETRIEVE_EVIDENCE"
                          else "COMPLETED",
                   summary=label[:240],
                   epistemic_class="INFERRED" if phase == "EXTRACT"
                                   else "RETRIEVED",
                   basis_ref=f"evidence pack (session {run_id})")
    return cb


def engine_callback(run_dir: str, run_id: str) -> Callable[[str, Dict], None]:
    """The EngineRun event_callback — called by _persist_envelope with
    (stage, envelope_dict) the moment each stage's envelope lands on
    disk. The event's status/summary/timestamp come from the stage's
    OWN stage_log entry — never inferred (R431 section 2)."""

    def cb(stage: str, envelope: Dict[str, Any]) -> None:
        meta = _STAGE_META.get(stage, (stage, "UNKNOWN"))
        entry = None
        for e in reversed(envelope.get("stage_log") or []):
            if e.get("stage") == stage:
                entry = e
                break
        status = "COMPLETED"
        if entry:
            st = str((entry.get("status") or "")).upper()
            if st == "FAILED_EXPLICIT":
                status = "FAILED_INFRASTRUCTURE"
            elif st in ("RUNNING", "IN_PROGRESS"):
                status = "ACTIVE"
        summary = f"engine stage {stage} persisted its envelope"
        if entry and entry.get("at"):
            summary = f"engine stage {stage} recorded at {entry['at']}"
        record(
            run_dir, run_id,
            kind=f"stage.{stage}",
            stage=meta[0],
            status=status,
            summary=summary,
            epistemic_class=meta[1],
            basis_ref=f"envelope_{stage}.json",
            timestamp=(entry or {}).get("at"),
            payload_ref=f"envelope_{stage}.json",
        )
    return cb


def record_bridge_outcomes(run_dir: str, run_id: str,
                           gate: Dict[str, Any]) -> None:
    """Worker phase 3.5: geometry/package creation events from the
    bridge gate's own persisted report."""
    outcome = gate.get("outcome")
    if outcome in ("COMPLETED", "PACKAGE_ADDED_TO_EXISTING_GEOMETRY",
                   "ALREADY_COMPLETE"):
        record(run_dir, run_id, kind="geometry.created", stage="GEOMETRY",
               status="COMPLETED",
               summary=("3D technology model generated by the "
                        "deterministic geometry builders"),
               epistemic_class="ENGINEERING_DEFINED",
               basis_ref="BRIDGE_REPORT.json",
               payload_ref="BRIDGE_REPORT.json")
    if outcome in ("CONCEPTUAL_FALLBACK", "COMPLETED",
                   "PACKAGE_ADDED_TO_EXISTING_GEOMETRY",
                   "ALREADY_COMPLETE"):
        record(run_dir, run_id, kind="package.completed", stage="TRANSFER",
               status="COMPLETED",
               summary="technology transfer package assembled",
               epistemic_class="ENGINEERING_DEFINED",
               basis_ref="BRIDGE_REPORT.json",
               payload_ref="BRIDGE_REPORT.json")


def record_terminal(run_dir: str, run_id: str, terminal: str,
                    basis: str) -> None:
    """The run's terminal state — infrastructure vs scientific NEVER
    collapsed (Art. LXI)."""
    infra = terminal.startswith("ERROR_") or terminal in (
        "INTERRUPTED", "RUN_BLOCKED_TRANSPORT")
    record(run_dir, run_id, kind="investigation.terminal",
           stage="EPISTEMICS",
           status=("FAILED_INFRASTRUCTURE" if infra
                   else "COMPLETED" if terminal == "COMPLETE"
                   else "FAILED_SCIENTIFIC"),
           summary=f"investigation terminal state {terminal}",
           epistemic_class="UNKNOWN" if infra else "COMPUTED",
           basis_ref=basis)


def merge_with_projection(journal: List[Dict[str, Any]],
                          projected: List[Dict[str, Any]]
                          ) -> List[Dict[str, Any]]:
    """R431 section 4 parity: the /events response = journal (live
    truth) + projection (terminal truth), deduplicated by event_id,
    deterministic order (timestamp then seq). Journal events win on
    id collision (they carry the real occurrence time)."""
    by_id: Dict[str, Dict[str, Any]] = {}
    for ev in projected:
        by_id[ev.get("event_id") or id(ev)] = ev
    for ev in journal:
        by_id[ev.get("event_id") or id(ev)] = ev
    merged = list(by_id.values())

    def _key(ev: Dict[str, Any]):
        ts = str(ev.get("timestamp") or "")
        try:
            seq = int(ev.get("seq") or 0)
        except (TypeError, ValueError):
            seq = 0
        return (ts, seq, str(ev.get("event_id") or ""))

    return sorted(merged, key=_key)


def reconcile(run_dir: str) -> Dict[str, Any]:
    """R431 section 4: journal <-> persisted artifacts reconciliation.
    Every journal event's basis_ref must exist on disk; every engine
    envelope present must have a journal stage event. RED on any
    unexplained discrepancy."""
    d = Path(run_dir)
    journal = read(run_dir)
    problems: List[str] = []
    stage_kinds = {e.get("kind") for e in journal
                   if str(e.get("kind") or "").startswith("stage.")}
    envelopes = sorted(d.glob("envelope_*.json")) if d.exists() else []
    for env in envelopes:
        stage = env.stem.replace("envelope_", "")
        if f"stage.{stage}" not in stage_kinds:
            problems.append(f"envelope {stage} present without a journal "
                            f"event")
    for ev in journal:
        ref = str(ev.get("basis_ref") or "")
        if ref.startswith("envelope_") and not (d / ref).is_file():
            problems.append(f"journal event {ev.get('event_id')} cites "
                            f"absent basis {ref}")
    return {
        "artifact": "EVENT_JOURNAL_RECONCILIATION",
        "journal_events": len(journal),
        "envelopes": len(envelopes),
        "stage_events": len(stage_kinds),
        "problems": problems,
        "verdict": "RECONCILED" if not problems else "DISCREPANCY",
    }
