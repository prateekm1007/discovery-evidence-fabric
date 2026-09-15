#!/usr/bin/env python3
"""R471 — Atria ENGINEER session: the P0-2 retry-contract state machine
(the 2026-09-16 external audit's named core-workflow failure).

CTO spec -> Atria (Atria-Dawn-Preview) drafts the implementation ->
CTO reviews, integrates, tests. The session is recorded as an evidence
artifact (R471/ATRIA_ENGINEER_RETRY.json), tokens on the operator's
nine-key ring (key 8 excluded, probe-typed invalid at R470).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R471" / "ATRIA_ENGINEER_RETRY.json"
KEY = os.environ.get("ATRIA_API_KEY", "").strip()

SYSTEM = """You are the delegated code/engineer for the Toscanini discovery
engine (round R471). The CTO has specified a fix; you implement it EXACTLY.
Constitutional constraints that are NON-NEGOTIABLE:
1. A completed verdict is APPEND-ONLY history: it is NEVER retryable
   (re-running a completed investigation must be a NEW session).
2. A live worker is NEVER interrupted or double-spawned: a session whose
   recorded worker pid is verifiably alive must refuse retry, typed.
3. Every state transition you write is TYPED and honest: a refusal says
   its reason in a machine-readable field; nothing pretends a recovery
   happened that did not.
4. pid identity is judged with the existing starttime mechanism (a reused
   pid can never masquerade as the original worker).
5. No new dependencies; stdlib only; keep the module's existing public
   names and behaviors that the tests pin (retry_session returning the
   updated session dict on acceptance, None for not-found).
Output EXACTLY one python code block: the FULL new content of the two
functions reconcile_stale_active() and retry_session() plus the new
_RETRY_REASONS dict, positioned as a coherent replacement block inside
toscanini/sessions.py (do NOT rewrite the whole module). Nothing else."""

SPEC = """CTO SPEC — R471 sessions.py retry v2 (the audit P0-2 failure:
a worker death during a deploy left a session PENDING; the retry endpoint
returned 409 "status 'PENDING' is not retryable" and the frontend threw;
the run was unrecoverable from the product surface).

CONTEXT (existing module facts you must rely on, not re-derive):
- ACTIVE_STATUSES = ("PENDING", "BUILDING_PROBLEM", "RUNNING")
- RETRYABLE_STATUSES = ERROR_STATUSES + ("INTERRUPTED", "RUN_BLOCKED_TRANSPORT")
- worker_alive(session) -> True/False/None (None = no pid recorded)
- _worker_spawn_cause(session_id) -> Optional[dict] (typed death evidence)
- PENDING_REGISTER_GRACE_MINUTES = 10
- update_session(sid, **fields) exists; get_session(sid) exists.
- marker freshness: s.get("updated_at") or s.get("created_at") or ""
  compared as ISO-8601 Zulu strings against a cutoff built with
  datetime.utcnow() - timedelta(...).

WRITE THESE THREE PIECES:

A. _RETRY_REASONS = {
  "COMPLETE_APPEND_ONLY": "completed verdicts are append-only history -
     start a new run instead",
  "WORKER_ALIVE": "the investigation is currently running - retry opens
     when it pauses, finishes, or fails",
  "REGISTRATION_GRACE_OPEN": "the worker is still starting - retry opens
     if it fails to register within the grace window",
}

B. def reconcile_stale_active(session_id) -> Optional[Dict[str, Any]]:
   Targeted, single-session reconciliation (safe at REQUEST time, unlike
   the global sweeps): fetch the session; return None if not found.
   - If status not in ACTIVE_STATUSES: return the session unchanged.
   - If a pid is recorded and worker_alive() is True: return unchanged.
   - If a pid is recorded and worker_alive() is False: update to
     status="INTERRUPTED" with error text naming the dead pid (reuse the
     phrasing style of mark_interrupted_sessions) and keep last_error
     semantics; return the UPDATED session.
   - If no pid is recorded: compute the registration grace cutoff the
     same way mark_unregistered_pending does. If the marker is missing or
     FRESH (>= cutoff): return the session unchanged (the worker may
     still be importing). If the marker is older than the cutoff: update
     to status="INTERRUPTED" with the typed no-registration error text
     (same honest shape as mark_unregistered_pending, including the
     spawn-cause line from _worker_spawn_cause when available) and
     spawn_diagnostics=that diagnosis; return the UPDATED session.

C. def retry_session(session_id) -> Optional[Dict[str, Any]]:
   The retry contract v2 (reconcile-then-retry, typed refusals):
   - s = get_session; return None if not found.
   - FIRST call reconcile_stale_active(session_id) and re-fetch s.
   - If the (possibly reconciled) status is "COMPLETE": return the typed
     refusal {"error": <one honest sentence>, "status": "COMPLETE",
              "retryable": False, "reason": "COMPLETE_APPEND_ONLY"}.
   - If status is now in RETRYABLE_STATUSES (this covers reconciled
     INTERRUPTED and all ERROR_*/RUN_BLOCKED states): ACCEPT — build
     retry_id = "retry_" + uuid4().hex[:8], attempts+1, update_session(
     status="PENDING", error=None, retry_attempts=attempts,
     last_error=<the pre-update s.get("error")>, worker_pid=None,
     worker_starttime=None, last_retry_id=retry_id), then return the
     UPDATED session dict (it must carry retry_attempts and last_retry_id).
   - Else if status is an ACTIVE status and worker_alive() is True:
     return the typed refusal with reason "WORKER_ALIVE".
   - Else if status is an ACTIVE status with no pid and the marker is
     fresh (inside the grace window): return the typed refusal with
     reason "REGISTRATION_GRACE_OPEN" and an extra key
     "grace_minutes": PENDING_REGISTER_GRACE_MINUTES.
   - Else (active, no pid, marker missing — undecidable): return the
     typed refusal with reason "REGISTRATION_GRACE_OPEN" as well (never
     guess a death the evidence does not show).
   Refusal error sentences must be plain product language a user can
   read (no stack vocabulary), one sentence each, ending with what to do
   next where sensible. Keep the docstring honest about WHY: the audit
   measured a 409 refusal on a stale-PENDING session whose worker died
   during a deploy; retry is now self-healing for the dead-worker classes
   and typed-refusing for the live/undecidable classes.
"""

CURRENT = (REPO / "toscanini" / "sessions.py").read_text()


def call_atria(system: str, user: str, max_tokens: int = 16000) -> dict:
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        "https://api.atria-asi.ai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                out = json.load(r)
            ch = out["choices"][0]
            return {"finish_reason": ch.get("finish_reason"),
                    "content": ch["message"].get("content") or "",
                    "completion_tokens":
                        out.get("usage", {}).get("completion_tokens"),
                    "attempts": attempt + 1}
        except Exception as exc:  # noqa: BLE001
            last_err = repr(exc)
            time.sleep(6)
    return {"finish_reason": "ERROR", "content": "",
            "completion_tokens": 0, "error": last_err}


def main() -> int:
    if not KEY:
        print("FATAL: ATRIA_API_KEY unset (Article LXXIII vault first)")
        return 2
    OUT.parent.mkdir(exist_ok=True)
    user = ("CTO SPEC FOLLOWS.\n\n" + SPEC +
            "\n\nCURRENT toscanini/sessions.py (for context; output only "
            "the replacement block):\n\n" + CURRENT)
    print("[engineer session] calling Atria (P0-2 retry contract)...")
    r = call_atria(SYSTEM, user)
    print(f"finish={r.get('finish_reason')} "
          f"tokens={r.get('completion_tokens')} "
          f"content={len(r.get('content') or '')} chars")
    draft_path = REPO / "R471" / "atria_draft_sessions_retry.py.raw"
    draft_path.write_text(r.get("content") or "")
    rec = {"round": "R471", "session": "engineer-1",
           "task": "P0-2 retry-contract state machine (sessions.py)",
           "spec_chars": len(SPEC), "prompt_chars": len(user),
           "response": r, "draft_saved": str(draft_path),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    OUT.write_text(json.dumps(rec, indent=2))
    print(f"artifact -> {OUT}")
    print(f"draft -> {draft_path}")
    return 0 if r.get("finish_reason") == "stop" else 1


if __name__ == "__main__":
    sys.exit(main())
