"""toscanini/actions.py — R459: the engine side of the conversational
action contract (external product audit P0-2).

The R458 contract defined the wire protocol and left execution to the
engine. This module implements the SMALLEST honest execution semantics
that make conversational steering real without inventing scientific
machinery:

    user directive -> typed action record (provenance) -> a NEW
    investigation round on the same problem, carrying the directive as
    typed USER_STATED context -> the engine's own pipeline decides what
    it means scientifically.

Design invariants:
  * Append-only history (the R422 rule): a COMPLETED verdict is a
    research outcome. An action NEVER mutates or re-runs a finished
    session in place — it opens a NEW session in the same investigation
    thread (parent_session_id), seeded with the original problem, the
    user's directive, and any bound attachments.
  * Art. X / §12 discipline: the directive is CONTEXT (classified,
    guarded through the conversation-memory guard) — it can steer the
    search; it can never grant itself a scientific verdict.
  * Art. LXI: a refused action is a typed refusal, never a verdict
    about the candidate.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# the canonical verbs (R458 contract; ASK is frontend-routed to the
# read-only ask endpoint and never reaches the ledger as an action)
COMPUTATION_VERBS = {
    "RESEARCH", "FIND_EVIDENCE", "COMPARE_MECHANISMS", "ATTACK",
    "CHANGE_MECHANISM", "REQUEST_ENGINEERING", "REQUEST_EXPERIMENT",
    "UPLOAD_EVIDENCE",
}
PRESENTATION_VERBS = {"REVIEW_PACKAGE"}
KNOWN_VERBS = COMPUTATION_VERBS | PRESENTATION_VERBS | {"CLARIFY"}

_TERMINAL = ("COMPLETE", "INTERRUPTED")


def _terminal(status: str) -> bool:
    return status == "COMPLETE" or status.startswith("RUN_BLOCKED") \
        or status.startswith("ERROR") or status == "INTERRUPTED"


def directive_text(verb: str, params: Dict[str, Any]) -> str:
    """One human-readable directive line, stored as context. Built from
    the verb's canonical meaning + the user's own words (never the UI's
    paraphrase alone)."""
    parts = [str(params.get("direction") or params.get("focus") or
                 params.get("topic") or "").strip()]
    target = params.get("target")
    if target and verb == "ATTACK":
        parts.append(f"(target: {target})")
    preserve = params.get("preserve")
    if preserve:
        parts.append(f"(preserve: {', '.join(map(str, preserve))})")
    mode = params.get("mode")
    if mode:
        parts.append(f"(mode: {mode})")
    return f"[{verb}] " + " ".join(p for p in parts if p)


def ledger_path(run_dir: Optional[str]) -> Optional[Path]:
    if not run_dir:
        return None
    p = Path(run_dir)
    if not p.exists():
        return None
    return p / "ACTION_LEDGER_RUN.json"


def record_action(run_dir: Optional[str], entry: Dict[str, Any]) -> None:
    """Append-only action ledger in the run dir (provenance custody for
    conversational steering). Fail-open: a ledger write failure never
    blocks the accepted action, and the session-side record still
    carries it (the session is the durable authority)."""
    p = ledger_path(run_dir)
    if not p:
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"actions": []}
        if isinstance(data, dict) and isinstance(data.get("actions"), list):
            data["actions"].append(entry)
            data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime())
            p.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001 — disclosed via session record
        pass


def accept_action(session: Dict[str, Any], verb: str,
                  params: Dict[str, Any]) -> Dict[str, Any]:
    """Classify one action request against the session's state.

    Returns one of:
      {accepted: True, reenqueue: True,  new_session required}
      {accepted: True, reenqueue: False}              (presentation verb)
      {accepted: False, code, message}                (typed refusal)
    """
    status = session.get("status") or ""
    verb = (verb or "").strip().upper()

    if verb not in KNOWN_VERBS:
        return {"accepted": False, "code": "UNKNOWN_ACTION",
                "message": f"unknown action {verb!r}"}
    if verb == "ASK":
        return {"accepted": False, "code": "USE_ASK",
                "message": "questions go to the read-only ask endpoint"}
    if verb == "CLARIFY":
        return {"accepted": False, "code": "USE_ANSWER",
                "message": ("answers to the investigation's question go "
                            "to the answer flow")}
    if status == "AWAITING_CLARIFICATION":
        return {"accepted": False, "code": "ANSWER_PENDING",
                "message": ("the investigation is waiting for your answer "
                            "to its question — send the answer first")}
    if not _terminal(status):
        return {"accepted": False, "code": "RUN_IN_PROGRESS",
                "message": ("the investigation is already running — it "
                            "cannot be steered mid-flight yet; once it "
                            "pauses or finishes, actions open the next "
                            "round")}

    # presentation verbs need no new round
    if verb in PRESENTATION_VERBS:
        return {"accepted": True, "reenqueue": False}

    return {"accepted": True, "reenqueue": True}
