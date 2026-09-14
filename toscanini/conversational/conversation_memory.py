"""toscanini/conversational/conversation_memory.py — R446-C1 §12:
conversation memory is NOT scientific truth.

Directive (verbatim intent): "Chat history can provide context. It
cannot mutate canonical scientific state. If the user says 'We proved
candidate B.' that does not change the invention state. Only
authoritative evidence/state transitions can do that."

This module is the MECHANICAL GUARD:

  1. classify_user_message(text) — deterministic classification of a
     conversational message into:
       QUESTION            asks about the run/invention (answer path:
                           run_qa, read-only)
       ASSERTION_PROOF     claims an outcome was proven/validated
       ASSERTION_PREFERENCE  expresses a preference/constraint
       ASSERTION_CORRECTION  corrects a PU input field (the ONLY
                           conversation class that may update the
                           Problem Understanding INPUT record, typed
                           USER_STATED — it is an input, not a
                           scientific state)
       NEW_PROBLEM         a new problem statement
       OTHER               conversational filler

  2. guard_session_update(fields) — the whitelist/blacklist the
     session store may accept from the CONVERSATION path. Scientific
     fields (final_status, problem_id verdicts, evidence, bridge
     outcomes...) are REFUSED on the conversation path; they only
     change through the worker/engine (the authoritative transitions).

The guard is enforced by returning a typed refusal record — never by
silently dropping the message (Art. XXV: refusal is recorded, and the
user's assertion is preserved as conversation context).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# --- classification vocabulary (closed) -------------------------------------
QUESTION = "QUESTION"
ASSERTION_PROOF = "ASSERTION_PROOF"
ASSERTION_PREFERENCE = "ASSERTION_PREFERENCE"
ASSERTION_CORRECTION = "ASSERTION_CORRECTION"
NEW_PROBLEM = "NEW_PROBLEM"
OTHER = "OTHER"

CLASSIFICATIONS = (QUESTION, ASSERTION_PROOF, ASSERTION_PREFERENCE,
                   ASSERTION_CORRECTION, NEW_PROBLEM, OTHER)

_PROOF_RE = re.compile(
    r"\b(we|i)\s+(?:have\s+|already\s+)?(?:proved|proven|validated|"
    r"demonstrated|confirmed|verified)\b|\bproof\b|\bvalidated\b",
    re.IGNORECASE)

_QUESTION_RE = re.compile(
    r"\?\s*$|^\s*(what|why|how|when|which|who|where|is|are|can|does|"
    r"do|did|should|could|would|will)\b", re.IGNORECASE)

_CORRECTION_RE = re.compile(
    r"\b(actually|correction|to be clear|i meant|rather than|"
    r"instead of|the goal is|what i want is|prioritize)\b",
    re.IGNORECASE)

_PREFERENCE_RE = re.compile(
    r"\b(prefer|instead|rather|keep|preserve|avoid|don't|do not|"
    r"must not|weight|focus on)\b", re.IGNORECASE)

# The scientific session fields the conversation path can NEVER write.
# (problem_id/run_dir/status and the presentation fields are written by
# the WORKER path; the conversation path only appends to context.)
FORBIDDEN_CONVERSATION_FIELDS = frozenset({
    "status", "final_status", "problem_id", "run_dir", "domain",
    "evidence_pack", "bridge_outcome", "bridge_case", "bridge_error",
    "package", "render_followup", "render_followup_reason",
    "worker_pid", "worker_starttime", "error", "traceback",
    "result", "result_path",
})

# Fields the conversation path MAY write (context + clarification
# state only).
ALLOWED_CONVERSATION_FIELDS = frozenset({
    "conversation", "clarification", "clarification_answer",
    "clarification_history",
})


def classify_user_message(text: str) -> Dict[str, Any]:
    """Deterministic classification. Zero LLM. The classification is
    CONTEXT ONLY — it decides which HANDLER the message routes to; it
    never itself changes scientific state."""
    t = (text or "").strip()
    low = t.lower()
    if not t:
        return {"classification": OTHER, "affects_canonical_state":
                False, "reason": "empty message"}

    if _PROOF_RE.search(t):
        return {
            "classification": ASSERTION_PROOF,
            "affects_canonical_state": False,
            "reason": "a conversational proof claim is NOT an "
                      "authoritative evidence/state transition — it "
                      "is preserved as context only (directive §12)",
            "required_for_state_change":
                "a REALITY_EVENT through the reality-boundary gate "
                "(Art. XXXVIII) or an engine state transition",
        }
    if _QUESTION_RE.search(t):
        return {"classification": QUESTION,
                "affects_canonical_state": False,
                "reason": "read-only Q&A over the run's own records "
                          "(run_qa path)"}
    if _CORRECTION_RE.search(t):
        return {"classification": ASSERTION_CORRECTION,
                "affects_canonical_state": False,
                "may_update_input_record": "problem_understanding",
                "reason": "a correction may update the Problem "
                          "Understanding INPUT record (typed "
                          "USER_STATED) — an input, never a "
                          "scientific verdict"}
    if _PREFERENCE_RE.search(t):
        return {"classification": ASSERTION_PREFERENCE,
                "affects_canonical_state": False,
                "may_update_input_record": "problem_understanding",
                "reason": "a preference may refine the input contract; "
                          "scientific state still requires the engine"}
    if len(t) > 60 and not _QUESTION_RE.match(t):
        return {"classification": NEW_PROBLEM,
                "affects_canonical_state": False,
                "reason": "a new problem statement routes to a NEW "
                          "discovery run (POST /api/run), never into "
                          "the current run's state"}
    return {"classification": OTHER, "affects_canonical_state": False,
            "reason": "general conversational context"}


def guard_session_update(fields: Dict[str, Any],
                         path: str = "conversation") -> Dict[str, Any]:
    """The mechanical guard: which fields may the CONVERSATION path
    write to the session store. Returns {allowed, refused} — the
    refused fields ride along as a typed record so the refusal is
    auditable, never silent (Art. XV/XXV)."""
    if path != "conversation":
        raise ValueError("this guard governs the conversation path only")
    allowed: Dict[str, Any] = {}
    refused: List[Dict[str, Any]] = []
    for k, v in (fields or {}).items():
        if k in ALLOWED_CONVERSATION_FIELDS:
            allowed[k] = v
        else:
            refused.append({
                "field": k,
                "reason": "scientific/worker-owned field — "
                          "conversation memory cannot mutate canonical "
                          "state (directive §12; Art. X)",
            })
    return {"allowed": allowed, "refused": refused,
            "guard_version": "conversation_memory/1.0.0"}


def record_conversation_context(session: Dict[str, Any],
                                 text: str,
                                 classification: Optional[Dict] = None
                                 ) -> Dict[str, Any]:
    """Append one message to the session's conversation context with
    its classification stamped. This NEVER touches scientific fields
    (the append itself is guarded by guard_session_update's
    vocabulary)."""
    cls = classification or classify_user_message(text)
    entry = {
        "role": "user",
        "text": (text or "")[:2000],
        "classification": cls["classification"],
        "affects_canonical_state": False,
    }
    history = session.get("conversation") or []
    if not isinstance(history, list):
        history = []
    history.append(entry)
    return {"conversation": history, "classification": cls}
