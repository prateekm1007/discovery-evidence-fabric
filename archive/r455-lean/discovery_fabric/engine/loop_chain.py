"""R406 Step 10 — the canonical AI closed-loop chain, machine-enforced.

Directive (R406 Step 10): "The canonical chain must become:
DISCOVERY -> EVIDENCE -> MECHANISM -> ENGINEERING -> SIMULATION ->
PREDICTION -> PHYSICAL EXPERIMENT -> OBSERVATION -> MODEL UPDATE ->
BASELINE COMPARISON -> KEEP / MODIFY / KILL -> LEARNING MEMORY ->
NEXT DISCOVERY. Every transition needs a machine-readable event. The
absence of physical data must prevent the state from being promoted."

Constitutional basis: Art. XXXVII (loop states: NONE /
SYNTHETIC_LOOP_VERIFIED / REAL_LOOP_VERIFIED — REAL requires an external
observation), Art. XXXVIII (the Reality Boundary: AI may not claim that
reality happened unless reality produced the evidence; REALITY_EVENT
schema; forbidden transitions), Art. LIII (the promotion ladder — no
state may skip a level), Art. LX (the discovery classification ladder —
each transition requires evidence).

Enforcement model:
  - A package's loop state is DERIVED from its committed transition
    events (never assigned by narrative).
  - Any transition at or beyond PHYSICAL EXPERIMENT requires a
    REALITY_EVENT whose source_type is not CONTROLLED_REHEARSAL, with
    the full Art. XXXVIII provenance (raw_data_sha256, attestation,
    custody_chain, provenance_validated=true).
  - The OBSERVATION state requires evidence_class PHYSICAL_OBSERVATION.
  - The MODEL UPDATE state requires a model-vs-measurement record whose
    actual_measurement is non-null and whose source is the same reality
    event (Art. XXXVII: posterior updated by external observation, not
    by coder narrative).
  - Without a qualifying REALITY_EVENT the chain is capped at
    PREDICTION with promotion_blocked_reason = "NO_PHYSICAL_DATA".
  - loop_verification_state mapping: a chain that reached MODEL UPDATE
    through a real event maps to REAL_LOOP_VERIFIED; a chain exercised
    end-to-end with CONTROLLED_REHEARSAL events maps to
    SYNTHETIC_LOOP_VERIFIED; anything less maps to NONE. Demotions are
    forbidden (Art. XXXVII).
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

# The canonical chain (R406 Step 10, verbatim order).
LOOP_STATES: List[str] = [
    "DISCOVERY",
    "EVIDENCE",
    "MECHANISM",
    "ENGINEERING",
    "SIMULATION",
    "PREDICTION",
    "PHYSICAL_EXPERIMENT",
    "OBSERVATION",
    "MODEL_UPDATE",
    "BASELINE_COMPARISON",
    "KEEP_MODIFY_KILL",
    "LEARNING_MEMORY",
    "NEXT_DISCOVERY",
]

# States whose entry requires reality-produced evidence.
_PHYSICAL_STATES = {"PHYSICAL_EXPERIMENT", "OBSERVATION", "MODEL_UPDATE",
                    "BASELINE_COMPARISON", "KEEP_MODIFY_KILL",
                    "LEARNING_MEMORY", "NEXT_DISCOVERY"}

_REALITY_EVENT_REQUIRED_FIELDS = (
    "event_id", "event_type", "package_id", "source_type", "organization",
    "operator", "acquisition_timestamp", "raw_artifact_ref",
    "raw_data_sha256", "attestation", "custody_chain",
    "provenance_validated",
)

_REAL_SOURCE_TYPES = {"EXTERNAL_HUMAN", "EXTERNAL_INSTRUMENT",
                      "EXTERNAL_SYSTEM"}
# CONTROLLED_REHEARSAL is a valid source_type for rehearsal chains, but
# NEVER qualifies a chain for promotion past PREDICTION (Art. XXXVIII).

BLOCK_REASON_NO_PHYSICAL = "NO_PHYSICAL_DATA"


def _event_id_ok(event_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_:.@/-]{4,128}", event_id or ""))


def validate_reality_event(event: Dict[str, Any]) -> List[str]:
    """Art. XXXVIII REALITY_EVENT schema validation. Returns a list of
    violations (empty = valid)."""
    problems: List[str] = []
    if not isinstance(event, dict):
        return ["REALITY_EVENT is not an object"]
    for field in _REALITY_EVENT_REQUIRED_FIELDS:
        if field not in event:
            problems.append(f"missing field: {field}")
    st = event.get("source_type")
    if st not in {"EXTERNAL_HUMAN", "EXTERNAL_INSTRUMENT",
                  "EXTERNAL_SYSTEM", "CONTROLLED_REHEARSAL"}:
        problems.append(f"invalid source_type: {st!r}")
    if event.get("provenance_validated") is not True:
        problems.append("provenance_validated is not true")
    cc = event.get("custody_chain")
    if not (isinstance(cc, list) and len(cc) > 0):
        problems.append("custody_chain empty or not a list")
    att = event.get("attestation")
    if not isinstance(att, dict) or not att.get("attestation_text") \
            or not att.get("attestation_hash"):
        problems.append("attestation missing text/hash")
    raw = event.get("raw_data_sha256")
    if not isinstance(raw, str) or not re.fullmatch(r"[0-9a-f]{64}", raw or ""):
        problems.append("raw_data_sha256 is not a sha256 hex digest")
    if not _event_id_ok(str(event.get("event_id", ""))):
        problems.append("invalid event_id")
    return problems


def validate_transition(chain_so_far: List[Dict[str, Any]],
                        event: Dict[str, Any]) -> List[str]:
    """Validate one transition event against the chain built so far.

    chain_so_far: the list of previously accepted events (each carrying
      from_state -> to_state).
    event: the candidate transition event; must carry from_state,
      to_state, event_id, evidence_ref, evidence_class, and — for states
      requiring reality — a REALITY_EVENT payload.
    """
    problems: List[str] = []
    if not isinstance(event, dict):
        return ["event is not an object"]
    for field in ("event_id", "from_state", "to_state", "evidence_ref",
                  "evidence_class"):
        if field not in event:
            problems.append(f"missing field: {field}")
    if problems:
        return problems
    frm, to = event.get("from_state"), event.get("to_state")
    if frm not in LOOP_STATES or to not in LOOP_STATES:
        problems.append(f"unknown state in {frm!r} -> {to!r}")
        return problems
    if chain_so_far:
        last_to = chain_so_far[-1].get("to_state")
        if frm != last_to:
            problems.append(
                f"non-contiguous transition: chain head is {last_to!r}, "
                f"event claims from_state {frm!r}")
    else:
        if frm != LOOP_STATES[0]:
            problems.append(f"first transition must start at {LOOP_STATES[0]}")
    # only forward transitions (KILL exits are recorded at
    # KEEP_MODIFY_KILL with decision KILL; the chain itself stays
    # append-only per Art. XXXVII)
    if LOOP_STATES.index(to) != LOOP_STATES.index(frm) + 1:
        problems.append(
            f"state skip or regression: {frm} -> {to} (the chain may only "
            "advance one canonical state at a time, Art. LIII)")
    if to in _PHYSICAL_STATES:
        re_ = event.get("REALITY_EVENT")
        if not isinstance(re_, dict):
            problems.append(
                f"transition into {to} requires a REALITY_EVENT "
                "(absence of physical data blocks promotion)")
        else:
            problems.extend(
                f"REALITY_EVENT: {p}" for p in validate_reality_event(re_))
            if re_.get("source_type") == "CONTROLLED_REHEARSAL":
                problems.append(
                    "CONTROLLED_REHEARSAL may demonstrate the machinery but "
                    "may NEVER promote a chain past PREDICTION "
                    "(Art. XXXVIII controlled-rehearsal rule)")
            if to == "OBSERVATION" and \
                    event.get("evidence_class") != "PHYSICAL_OBSERVATION":
                problems.append(
                    "the OBSERVATION state requires evidence_class "
                    "PHYSICAL_OBSERVATION")
        if to == "MODEL_UPDATE":
            mm = event.get("MODEL_MEASUREMENT_RECORD")
            if not isinstance(mm, dict) or mm.get("actual_measurement") is None:
                problems.append(
                    "the MODEL_UPDATE state requires a model-vs-measurement "
                    "record with a non-null actual_measurement tied to the "
                    "same reality event")
    if not _event_id_ok(str(event.get("event_id", ""))):
        problems.append("invalid event_id")
    return problems


def derive_loop_state(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive the package's current chain state from its events.

    Returns {current_state, loop_verification_state,
    promotion_blocked, promotion_blocked_reason, accepted_events,
    validation_problems}. A single invalid event caps the chain at the
    last valid state and reports the problem (fail-closed, Art. XIV)."""
    accepted: List[Dict[str, Any]] = []
    problems: List[str] = []
    for ev in events:
        p = validate_transition(accepted, ev)
        if p:
            problems.extend(f"event {ev.get('event_id')}: {x}" for x in p)
            break
        accepted.append(ev)
    if not accepted:
        return {
            "current_state": None,
            "loop_verification_state": "NONE",
            "promotion_blocked": True,
            "promotion_blocked_reason": "NO_EVENTS",
            "accepted_events": [],
            "validation_problems": problems,
        }
    head = accepted[-1]["to_state"]
    has_real = any(
        ev.get("REALITY_EVENT", {}).get("source_type") in _REAL_SOURCE_TYPES
        for ev in accepted)
    reached_update = LOOP_STATES.index(head) >= LOOP_STATES.index("MODEL_UPDATE")
    if has_real and reached_update:
        lvs = "REAL_LOOP_VERIFIED"
    elif any(ev.get("REALITY_EVENT", {}).get("source_type")
             == "CONTROLLED_REHEARSAL" for ev in accepted) \
            and reached_update:
        lvs = "SYNTHETIC_LOOP_VERIFIED"
    else:
        lvs = "NONE"
    blocked = LOOP_STATES.index(head) < LOOP_STATES.index("NEXT_DISCOVERY")
    reason = None
    if problems:
        reason = "INVALID_TRANSITION"
    elif head == "PREDICTION" and not has_real:
        reason = BLOCK_REASON_NO_PHYSICAL
    elif blocked and not has_real:
        reason = BLOCK_REASON_NO_PHYSICAL
    return {
        "current_state": head,
        "loop_verification_state": lvs,
        "promotion_blocked": bool(blocked or problems),
        "promotion_blocked_reason": reason,
        "accepted_events": [e["event_id"] for e in accepted],
        "validation_problems": problems,
    }


def chain_digest(events: List[Dict[str, Any]]) -> str:
    """Stable content digest of a chain record (causal-mutation guard)."""
    blob = json.dumps(events, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def load_chain(path: str) -> Dict[str, Any]:
    with open(path) as f:
        rec = json.load(f)
    events = rec.get("events", [])
    derived = derive_loop_state(events)
    return {**rec, "derived": derived, "chain_digest": chain_digest(events)}
