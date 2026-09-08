"""toscanini/investigation.py — R430.1: the Technology Investigation
event stream.

Operator directive R430.1 sections 7, 9, 11, 13, 14:
  Replace raw LLM-token presentation with STRUCTURED DOMAIN EVENTS.
  The backend may keep internal LLM reasoning — the UI never sees it.
  Every event is a projection of a PERSISTED artifact (session record,
  stage envelope, lineage record, bridge report) — never fabricated,
  never inferred client-side (Art. X: the canonical invention/run state
  stays the single authority; this module PROJECTS it, it does not
  author a second truth).

Event schema (directive section 7):
    {
      "event_id":   deterministic hash of (investigation, seq, kind),
      "investigation_id": session id,
      "stage":      scientific stage (EVIDENCE, MECHANISM, CHALLENGE, ...),
      "kind":       event kind (stage.completed, candidate.rejected, ...),
      "status":     QUEUED | ACTIVE | COMPLETED | BLOCKED |
                    FAILED_INFRASTRUCTURE | FAILED_SCIENTIFIC | UNKNOWN,
      "summary":    one honest sentence derived from the artifact,
      "epistemic_class": RETRIEVED | INFERRED | HYPOTHESIZED | COMPUTED |
                    SIMULATED | ENGINEERING_DEFINED | PHYSICALLY_OBSERVED |
                    UNKNOWN,
      "basis_ref":  the persisted artifact this event derives from,
      "timestamp":  the artifact's OWN recorded time, never invented
    }

Constitutional anchors:
- Art. XXV / LXI: infrastructure failure (ERROR_*, INTERRUPTED,
  RUN_BLOCKED_TRANSPORT, stage FAILED_EXPLICIT machinery crashes) is
  NEVER collapsed with scientific failure (premise rejection, challenge
  kills). The two classes stay structurally distinct in every status.
- Art. XXVIII: epistemic classes are never promoted — an event's class
  is the class of the artifact that produced it, nothing else.
- Art. XXXVIII: PHYSICAL_OBSERVED can only appear from a REAL
  REALITY_LOOP ledger entry; fresh runs honestly never carry it.
- Art. LXVI: no invented numbers — summaries quote recorded counts.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from toscanini import sessions as store
from toscanini import run_state as _rs
from toscanini.sessions import _read_json  # same read discipline

# ---------------------------------------------------------------------------
# Directive section 7: the closed status vocabulary. Infrastructure and
# scientific failure are NEVER the same state (Art. LXI).
# ---------------------------------------------------------------------------
EVENT_STATUSES = (
    "QUEUED",
    "ACTIVE",
    "COMPLETED",
    "BLOCKED",
    "FAILED_INFRASTRUCTURE",
    "FAILED_SCIENTIFIC",
    "UNKNOWN",
)

# Directive section 8: the closed epistemic vocabulary. Frontend wording
# may never upgrade a class (Art. XXVIII).
EPISTEMIC_CLASSES = (
    "RETRIEVED",
    "INFERRED",
    "HYPOTHESIZED",
    "COMPUTED",
    "SIMULATED",
    "ENGINEERING_DEFINED",
    "PHYSICALLY_OBSERVED",
    "UNKNOWN",
)

_RUNNING_STATUSES = ("RUNNING", "PENDING", "BUILDING_PROBLEM", "RETRY")

# Session-level terminal statuses that are infrastructure-class, never
# scientific (Art. LXI; R415: RUN_BLOCKED_TRANSPORT is resumable).
_INFRA_TERMINAL = ("ERROR_TRANSPORT", "ERROR_BUILD", "ERROR_RUN",
                   "ERROR_STUCK", "INTERRUPTED")
_RESUMABLE_BLOCK = ("RUN_BLOCKED_TRANSPORT",)

# Engine stage -> (scientific stage label, default epistemic class).
# The class is the artifact class, chosen per what the stage PERSISTS:
# retrieval/freeze persist retrieved records; synthesis persists a
# MODEL-proposed mechanism (hypothesis); physics persists computed (or
# simulated) verdicts; engineering persists definitions.
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
    "ADJUDICATION": ("CHALLENGE", "COMPUTED"),
    "CLASSIFY": ("EPISTEMICS", "COMPUTED"),
    "NEXT_BEST_ACTION": ("EPISTEMICS", "COMPUTED"),
    "RANK": ("EPISTEMICS", "COMPUTED"),
}

_STAGE_SUMMARY = {
    "RETRIEVE": "evidence base retrieved and custody-frozen",
    "FREEZE": "evidence snapshot frozen with content hashes",
    "PREMISE_GATE": "problem premise checked against physical coherence",
    "SYNTHESIZE": "candidate mechanism proposed from the evidence",
    "VERIFY": "every claim bound to an exact evidence span",
    "MULTI_SOURCE_DISCOVERY": "prior art scanned across independent sources",
    "COLLISION": "prior-art collision check executed",
    "PHYSICS": "physics evaluated against the un-invented baseline",
    "ATTACK": "adversarial challenges executed against the candidate",
    "CONTRADICTION": "evidence contradictions resolved",
    "KILLER_EXPERIMENT": "decisive (falsification) experiment designed",
    "ADJUDICATION": "surviving architecture adjudicated",
    "CLASSIFY": "epistemic state classified from recorded evidence",
    "NEXT_BEST_ACTION": "next actions ranked by information value",
    "RANK": "final ranking recorded",
}


def _evt(investigation_id: str, seq: int, kind: str, stage: str,
         status: str, summary: str, epistemic_class: str,
         basis_ref: str, timestamp: Optional[str] = None,
         detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One structured event. event_id is DETERMINISTIC (same persisted
    state -> same event id), derived from the projection identity —
    never from wall-clock time (Art. VI: no manufactured provenance)."""
    eid = hashlib.sha256(
        f"{investigation_id}|{seq}|{kind}|{stage}".encode()
    ).hexdigest()[:16]
    return {
        "event_id": f"evt_{eid}",
        "investigation_id": investigation_id,
        "seq": seq,
        "stage": stage,
        "kind": kind,
        "status": status,
        "summary": summary,
        "epistemic_class": epistemic_class,
        "basis_ref": basis_ref,
        "timestamp": timestamp,
        **(detail or {}),
    }


def _stage_stage_log_entry(env: Optional[Dict[str, Any]],
                           stage: str) -> Optional[Dict[str, Any]]:
    if not env:
        return None
    for entry in reversed(env.get("stage_log") or []):
        if entry.get("stage") == stage:
            return entry
    return None


def _stage_status_class(entry: Optional[Dict[str, Any]],
                        session_status: str) -> str:
    """Stage-log status -> event status. A stage that COMPLETED carries
    COMPLETED even when its verdict content is negative — the verdict is
    scientific CONTENT, not a machinery failure. A stage_log
    FAILED_EXPLICIT is an exception in the machinery: infrastructure by
    Art. LXI (a scientific rejection is recorded as a verdict inside a
    completed stage, never as a crash)."""
    if not entry:
        return "UNKNOWN"
    st = (entry.get("status") or "UNKNOWN").upper()
    if st in ("OK", "PASS", "DONE"):
        return "COMPLETED"
    if st in ("RUNNING", "IN_PROGRESS"):
        return "ACTIVE" if session_status in _RUNNING_STATUSES else "UNKNOWN"
    if st == "FAILED_EXPLICIT":
        return "FAILED_INFRASTRUCTURE"
    return "UNKNOWN"


def _envelope_summary(stage: str, env: Optional[Dict[str, Any]]) -> str:
    """Stage-specific one-line summary quoting RECORDED counts/verdicts
    only (Art. LXVI: no invented numbers)."""
    base = _STAGE_SUMMARY.get(stage)
    if not env:
        return base or f"{stage.lower().replace('_', ' ')} recorded"
    if stage == "RETRIEVE":
        n = len(env.get("evidence") or [])
        if n:
            return f"{base} — {n} records"
        return base
    if stage == "PREMISE_GATE":
        v = (env.get("premise_gate") or {}).get("verdict")
        return f"{base} — verdict {v}" if v else base
    if stage == "SYNTHESIZE":
        mm = env.get("mechanism_map") or {}
        m = mm.get("mechanism")
        return f"{base} — {m}" if m else base
    if stage == "ATTACK":
        ar = env.get("attack_results")
        if isinstance(ar, dict):
            ov = ar.get("overall")
            n = len(ar.get("attacks") or {})
            return f"{base} — overall {ov}, {n} dimensions" if ov else base
        if isinstance(ar, list):
            return f"{base} — {len(ar)} challenges"
        return base
    if stage == "KILLER_EXPERIMENT":
        ke = env.get("killer_experiment") or {}
        name = ke.get("name") or ke.get("description")
        return f"{base} — {name}" if name else base
    if stage == "ADJUDICATION":
        v = ((env.get("adjudication") or {}).get("council") or {}).get(
            "verdict")
        return f"{base} — verdict {v}" if v else base
    if stage == "CLASSIFY":
        es = env.get("epistemic_state")
        if isinstance(es, dict):
            es = es.get("epistemic_state") or es.get("final_status")
        return f"{base} — {es}" if es else base
    if stage == "MULTI_SOURCE_DISCOVERY":
        pa = env.get("prior_art")
        if isinstance(pa, dict):
            pa = pa.get("results") or []
        if isinstance(pa, list) and pa:
            return f"{base} — {len(pa)} references"
        return base
    if stage == "PHYSICS":
        ph = env.get("physics") or {}
        v = ph.get("lifecycle_verdict")
        if v and v not in ("NOT_APPLICABLE", "MECHANISM_NOT_SIMULATABLE"):
            return f"physics simulated against the baseline — {v}"
        if v == "MECHANISM_NOT_SIMULATABLE":
            return ("physics domain not covered by a validated solver — "
                    "honest refusal, not a simulation result")
        return base
    if stage == "COLLISION":
        cr = env.get("collision_results")
        if isinstance(cr, dict) and cr:
            return f"{base} — {len(cr)} evidence universes compared"
        if isinstance(cr, list) and cr:
            return f"{base} — {len(cr)} comparisons"
        return base
    return base


def _stage_epistemic(stage: str, env: Optional[Dict[str, Any]]) -> str:
    """The honest class for one stage event. PHYSICS upgrades to
    SIMULATED only when a simulation verdict was actually recorded
    (Art. LIII / XXVIII — never a silent promotion)."""
    sci, default = _STAGE_META[stage]
    if stage == "PHYSICS" and env:
        v = (env.get("physics") or {}).get("lifecycle_verdict")
        if v and v not in ("NOT_APPLICABLE", "MECHANISM_NOT_SIMULATABLE"):
            return "SIMULATED"
    return default


def investigation_events(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The FULL structured event history for one investigation, derived
    deterministically from persisted artifacts. This is the projection
    the UI replays on refresh (directive section 12) — the same list is
    served by GET /api/run/{id}/events and streamed incrementally by
    the SSE 'science' events."""
    sid = session.get("session_id") or ""
    status = session.get("status") or "PENDING"
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    if run_dir and not run_dir.exists():
        run_dir = None
    running = status in _RUNNING_STATUSES
    events: List[Dict[str, Any]] = []
    seq = 0

    def emit(**kw) -> None:
        nonlocal seq
        seq += 1
        events.append(_evt(sid, seq, **kw))

    # 1. investigation created — the session record itself
    emit(kind="investigation.created", stage="INVESTIGATION",
         status="COMPLETED",
         summary="investigation created — problem recorded",
         epistemic_class="UNKNOWN",
         basis_ref="sessions.json",
         timestamp=session.get("created_at"))

    # 2. problem normalized — problem_builder's persisted output
    problem_built = bool(run_dir and (run_dir / "problem.json").exists())
    if status == "BUILDING_PROBLEM" or (running and not problem_built):
        emit(kind="problem.normalized", stage="PROBLEM", status="ACTIVE",
             summary=("normalizing the problem and binding it to the "
                      "evidence base"),
             epistemic_class="INFERRED",
             basis_ref="session status BUILDING_PROBLEM",
             timestamp=None)
    elif problem_built:
        emit(kind="problem.normalized", stage="PROBLEM",
             status="COMPLETED",
             summary=("problem normalized to a structured hypothesis "
                      "(MODEL_DERIVED extraction, flagged as such)"),
             epistemic_class="INFERRED",
             basis_ref="run_dir/problem.json",
             timestamp=str((run_dir / "problem.json").stat().st_mtime)
             if run_dir else None)

    # 3. engine stage events — one per persisted envelope, canonical order
    stage_status: Dict[str, str] = {}
    envelopes: Dict[str, Optional[Dict[str, Any]]] = {}
    if run_dir:
        from toscanini.sessions import STAGES
        for stage in STAGES:
            env = _read_json(run_dir / f"envelope_{stage}.json")
            if env is None:
                continue
            envelopes[stage] = env
            entry = _stage_stage_log_entry(env, stage)
            stage_status[stage] = (entry or {}).get("status") or "UNKNOWN"
            sci, _cls = _STAGE_META.get(stage, (stage, "UNKNOWN"))
            emit(kind=f"stage.{stage.lower()}",
                 stage=sci,
                 status=_stage_status_class(entry, status),
                 summary=_envelope_summary(stage, env),
                 epistemic_class=_stage_epistemic(stage, env),
                 basis_ref=f"run_dir/envelope_{stage}.json",
                 timestamp=(entry or {}).get("finished_at")
                 or (entry or {}).get("started_at"))

    # 4. generation events — the challenge/rebuild narrative (R416
    # lineage records; the machine WORKS the problem across generations)
    if run_dir:
        lineage = _read_json(run_dir / "INVENTION_LINEAGE.json") or {}
        for g in lineage.get("generations") or []:
            if not isinstance(g, dict):
                continue
            gen = g.get("gen")
            arch = g.get("architecture") or {}
            ch = g.get("challenge") or {}
            gen_label = f"architecture {int(gen):02d}" if gen else \
                "architecture"
            emit(kind="candidate.proposed", stage="MECHANISM",
                 status="COMPLETED",
                 summary=(f"candidate {gen_label} proposed — "
                          f"{(arch.get('mechanism') or 'mechanism')}"
                          .strip()),
                 epistemic_class="HYPOTHESIZED",
                 basis_ref=f"run_dir/INVENTION_LINEAGE.json#gen={gen}",
                 detail={"generation": gen,
                         "intervention": arch.get("intervention")})
            if ch.get("killed"):
                # honest scientific rejection of THIS generation
                emit(kind="candidate.rejected", stage="CHALLENGE",
                     status="FAILED_SCIENTIFIC",
                     summary=(f"candidate {gen_label} rejected under "
                              f"{ch.get('kill_stage') or 'challenge'}"
                              + (f" — {ch.get('kill_reason')}"
                                 if ch.get("kill_reason") else "")),
                     epistemic_class="COMPUTED",
                     basis_ref=(f"run_dir/INVENTION_LINEAGE.json"
                                f"#gen={gen}/challenge"),
                     detail={"generation": gen,
                             "kill_stage": ch.get("kill_stage"),
                             "diagnosis_cause": ((g.get("diagnosis")
                                                  or {}).get("cause"))})
            elif ch.get("survived"):
                emit(kind="candidate.survived", stage="CHALLENGE",
                     status="COMPLETED",
                     summary=f"candidate {gen_label} survived the "
                             f"challenge gauntlet",
                     epistemic_class="COMPUTED",
                     basis_ref=(f"run_dir/INVENTION_LINEAGE.json"
                                f"#gen={gen}/challenge"),
                     detail={"generation": gen})
            if g.get("change_delta") and (gen or 0) > 1:
                emit(kind="candidate.rebuilt", stage="REBUILD",
                     status="COMPLETED",
                     summary=(f"candidate rebuilt as {gen_label} — "
                              f"{g.get('change_delta')}"),
                     epistemic_class="HYPOTHESIZED",
                     basis_ref=(f"run_dir/INVENTION_LINEAGE.json"
                                f"#gen={gen}/change_delta"),
                     detail={"generation": gen,
                             "reason": g.get("reason_for_change")})

    # 5. engineering / geometry / package events (the bridge gate's own
    # persisted report — geometry is ENGINEERING_DEFINED when the class
    # says so, HYPOTHESIZED conceptual visualization otherwise; never a
    # silent promotion, Art. XXVIII)
    if run_dir:
        bridge = _read_json(run_dir / "BRIDGE_REPORT.json")
        if bridge:
            outcome = bridge.get("outcome")
            geom = bridge.get("geometry") or {}
            vclass = bridge.get("visualizability_class") or \
                geom.get("visualizability_class")
            if vclass or geom.get("glb"):
                gclass = ("ENGINEERING_DEFINED"
                          if vclass == "ENGINEERING_3D"
                          else "HYPOTHESIZED")
                label = vclass or "3D"
                emit(kind="geometry.generated", stage="ENGINEERING",
                     status="COMPLETED",
                     summary=(f"3D geometry generated — class {label}"
                              + (" (conceptual visualization, not "
                                 "engineering CAD)" if gclass ==
                                 "HYPOTHESIZED" else "")),
                     epistemic_class=gclass,
                     basis_ref="run_dir/BRIDGE_REPORT.json",
                     detail={"visualizability_class": vclass,
                             "glb": geom.get("glb")})
            eng = bridge.get("engineering") or {}
            if eng.get("present") or outcome == "BRIDGE_COMPLETE":
                emit(kind="engineering.definition", stage="ENGINEERING",
                     status="COMPLETED",
                     summary="engineering definition created from the "
                             "canonical invention state",
                     epistemic_class="ENGINEERING_DEFINED",
                     basis_ref="run_dir/BRIDGE_REPORT.json")
        # the package event derives from the SAME derivation the CIO
        # uses (engine DOWNLOAD path or bridge TECHNOLOGY_PACKAGE path)
        pkg = None
        try:
            from toscanini import cio as _cio_mod
            pkg = _cio_mod._package_info(run_dir)
        except Exception:  # noqa: BLE001 — event layer never raises
            pkg = None
        if pkg and pkg.get("complete"):
            mat = pkg.get("maturity") or "maturity not yet established"
            emit(kind="package.ready", stage="TRANSFER",
                 status="COMPLETED",
                 summary=(f"technology transfer package built — "
                          f"{pkg.get('package_kind') or 'package'} "
                          f"({mat})"),
                 epistemic_class="ENGINEERING_DEFINED",
                 basis_ref="run_dir package tree + BRIDGE_REPORT.json",
                 detail={"zip_name": pkg.get("zip_name"),
                         "maturity": pkg.get("maturity")})

    # 6. terminal event — infra vs scientific NEVER collapsed (Art. LXI)
    outcome_obj = _rs.terminal_outcome(session, run_dir)
    outcome = outcome_obj.get("outcome")
    if status == "RUN_BLOCKED_TRANSPORT":
        emit(kind="investigation.blocked", stage="INVESTIGATION",
             status="BLOCKED",
             summary=("discovery temporarily blocked by infrastructure — "
                      "the problem is saved and resumable; no scientific "
                      "conclusion was assigned"),
             epistemic_class="UNKNOWN",
             basis_ref=f"session status RUN_BLOCKED_TRANSPORT",
             detail={"resumable": True,
                     "error": (session.get("error") or "")[:300]})
    elif status in _INFRA_TERMINAL:
        emit(kind="investigation.interrupted", stage="INVESTIGATION",
             status="FAILED_INFRASTRUCTURE",
             summary=(f"investigation interrupted by infrastructure "
                      f"({status}) — scientific conclusions not "
                      f"established"),
             epistemic_class="UNKNOWN",
             basis_ref=f"session status {status}",
             detail={"error": (session.get("error") or "")[:300]})
    elif status == "COMPLETE":
        if outcome == "FALSE_PREMISE_INCOHERENT":
            emit(kind="investigation.rejected", stage="INVESTIGATION",
                 status="FAILED_SCIENTIFIC",
                 summary=("the problem's premise is physically "
                          "incoherent — nothing to invent; this is a "
                          "recorded scientific verdict, not a machinery "
                          "failure"),
                 epistemic_class="COMPUTED",
                 basis_ref="final_state.json final_status="
                           "MALFORMED_OR_FALSE_PREMISE")
        else:
            final = session.get("final_status") or "UNKNOWN"
            pkg_ready = bool((session.get("package") or {}).get("complete"))
            emit(kind="investigation.completed", stage="INVESTIGATION",
                 status="COMPLETED",
                 summary=(f"investigation completed — {final}"
                          + ("; technology package ready"
                             if pkg_ready else "")),
                 epistemic_class="COMPUTED",
                 basis_ref="final_state.json",
                 detail={"outcome": outcome,
                         "outcome_label": _rs.OUTCOME_LABELS.get(
                             outcome, outcome)})
    elif running:
        emit(kind="investigation.running", stage="INVESTIGATION",
             status="ACTIVE",
             summary="investigation in progress on the server — you can "
                     "leave and return; nothing is lost",
             epistemic_class="UNKNOWN",
             basis_ref=f"session status {status}")

    return events


# ---------------------------------------------------------------------------
# Directive section 9: the collapsible gauntlet — compact cards the UI
# renders collapsed by default. Grouped, not 16 raw tabs.
# ---------------------------------------------------------------------------
def gauntlet_projection(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group the event stream into the directive's compact scientific
    gauntlet: Evidence / Mechanism / Challenge / Rebuild / Experiment /
    Engineering / 3D / Transfer. Each card: mark (done/active/failed/
    pending), one-line summary, and the machine-readable events for the
    expanded view. Every state comes from a backend event — the gauntlet
    never fabricates progress (directive section 11)."""
    groups = [
        ("EVIDENCE", "Evidence", ("EVIDENCE",)),
        ("MECHANISM", "Mechanism", ("MECHANISM", "PROBLEM")),
        ("PRIOR_ART", "Prior art", ("PRIOR_ART",)),
        ("PHYSICS", "Physics", ("PHYSICS",)),
        ("CHALLENGE", "Challenge", ("CHALLENGE",)),
        ("REBUILD", "Rebuild", ("REBUILD",)),
        ("EXPERIMENT", "Experiment", ("EXPERIMENT",)),
        ("ENGINEERING", "Engineering", ("ENGINEERING",)),
        ("TRANSFER", "Transfer", ("TRANSFER",)),
    ]
    out = []
    for stage_id, label, stages in groups:
        group_events = [e for e in events if e.get("stage") in stages]
        if not group_events and stage_id not in ("EXPERIMENT",
                                                 "ENGINEERING",
                                                 "TRANSFER"):
            # unreached group: only shown once something exists, EXCEPT
            # the directive's fixed early trio which renders as pending
            continue
        if not group_events:
            out.append({"stage": stage_id, "label": label, "mark": "○",
                        "state": "PENDING", "summary": "pending",
                        "events": []})
            continue
        last = group_events[-1]
        if any(e["status"] in ("FAILED_SCIENTIFIC",) for e in group_events):
            state, mark = "FAILED_SCIENTIFIC", "✕"
        elif any(e["status"] == "FAILED_INFRASTRUCTURE"
                 for e in group_events):
            state, mark = "FAILED_INFRASTRUCTURE", "⚠"
        elif any(e["status"] == "ACTIVE" for e in group_events):
            state, mark = "ACTIVE", "●"
        elif any(e["status"] == "COMPLETED" for e in group_events):
            state, mark = "COMPLETED", "✓"
        else:
            state, mark = "UNKNOWN", "○"
        out.append({
            "stage": stage_id,
            "label": label,
            "mark": mark,
            "state": state,
            "summary": last.get("summary"),
            "events": [e["event_id"] for e in group_events],
        })
    return out


def build_investigation(session: Dict[str, Any]) -> Dict[str, Any]:
    """The full Technology Investigation projection (directive section
    1): the durable parent object the workspace renders. A PROJECTION
    of the canonical run state — never a second source of truth."""
    events = investigation_events(session)
    sid = session.get("session_id")
    outcome_obj = _rs.terminal_outcome(
        session,
        Path(session["run_dir"]) if session.get("run_dir") else None)
    return {
        "kind": "TECHNOLOGY_INVESTIGATION",
        "schema_version": "1.0.0",
        "investigation_id": sid,
        "created_at": session.get("created_at"),
        "problem": session.get("user_text"),
        "status": session.get("status"),
        "outcome": outcome_obj,
        "gauntlet": gauntlet_projection(events),
        "events": events,
        "projection_note": (
            "every event derives from a persisted run artifact "
            "(session record, stage envelopes, invention lineage, "
            "bridge report); nothing is fabricated and no internal "
            "reasoning is exposed (R430.1 s7)"),
    }
