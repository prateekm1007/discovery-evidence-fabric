#!/usr/bin/env python3
"""R472 — the learning-card LIVE production check (audit P0-4's live
leg): one fresh-owner run on production, polled to its terminal; when
the terminal is a scientific no-survivor class, the result surface
MUST carry the learning card (what_was_tested, strongest_failed
hypothesis, key missing evidence, ranked typed next actions).

The driver plays the user honestly (R471 discipline): fresh owner,
one problem, the clarification answered in one sentence, no capability
abuse. Resumable: the state file carries the owner capability + session
across invocations (a kill never loses the run; BS-021: the state file
records fingerprints only, the owner capability stays memory/state-only
and is NEVER committed in raw form — sanitized on exit).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = Path("/home/z/my-project/repos/discovery-evidence-fabric/R472/PROD_LIVE")
OUT.mkdir(parents=True, exist_ok=True)
STATE = OUT / "card_check_state.json"

OWNER = f"r472card{uuid.uuid4().hex[:14]}"
_OWNER_OVERRIDE = None

PROBLEM = (
    "Find a passive, low-cost way to keep residual disinfectant above "
    "the minimum effective concentration in the far reaches of a "
    "branching small-town water distribution network through a 3-month "
    "summer peak, without increasing pumping energy.")

TERMINAL = {"COMPLETE", "INTERRUPTED", "ERROR_TRANSPORT",
            "RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY",
            "MALFORMED_OR_FALSE_PREMISE"}
POLL_S = 25
BOUND_MIN = 40.0
ANSWER = ("Keep the residual disinfectant in the far network reaches "
          "above the minimum all summer, and do not increase pump "
          "energy use.")


def _owner() -> str:
    return _OWNER_OVERRIDE or OWNER


def _req(method, path, body=None, timeout=60):
    req = urllib.request.Request(
        BASE.rstrip("/") + path, method=method,
        headers={"Content-Type": "application/json",
                 "X-Tosca-Owner": _owner(),
                 "User-Agent": "r472-card-check/1.0"},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8",
                                                        "replace"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8",
                                                          "replace"))
        except Exception:  # noqa: BLE001
            return exc.code, {}


def _log(msg):
    print(f"[r472-card {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _save(rec):
    # BS-021: fingerprints only in the record; the owner capability
    # lives in the state file (runtime artifact, never committed raw)
    (OUT / "CARD_CHECK_RECORD.json").write_text(json.dumps(rec, indent=1))
    STATE.write_text(json.dumps({
        "session_id": rec.get("session_id"),
        "owner_key": rec.get("_owner_key"),
        "record": {k: v for k, v in rec.items() if not k.startswith("_")},
        "started_at": rec.get("started_at")}, indent=1))


def main() -> int:
    rec: dict = {"owner_fingerprint": OWNER[:10], "base": BASE,
                 "problem_chars": len(PROBLEM),
                 "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}
    sid = owner_key = None
    answered = False
    if STATE.exists():
        st = json.loads(STATE.read_text())
        sid = st.get("session_id")
        owner_key = st.get("owner_key")
        if sid and owner_key:
            globals()["_OWNER_OVERRIDE"] = owner_key
            rec.update(st.get("record") or {})
            answered = bool(rec.get("answered"))
            _log(f"resuming session {sid} (answered={answered})")
    if not sid:
        st, run = _req("POST", "/api/run", {"text": PROBLEM})
        sid, owner_key = run.get("session_id"), run.get("owner_key")
        _log(f"run {sid} HTTP {st} owner={owner_key[:8] if owner_key else '-'}")
        if not sid:
            _save(rec)
            return 1
        rec["session_id"] = sid
        rec["_owner_key"] = owner_key
        rec["started_at"] = time.time()
        _save(rec)

    start = rec.get("started_at") or time.time()
    rec["started_at"] = start
    terminal = None
    while time.time() - start < BOUND_MIN * 60:
        st, res = _req("GET", f"/api/run/{sid}/result")
        status = res.get("status")
        if status != rec.get("last_status"):
            _log(f"status -> {status}")
            rec["last_status"] = status
        if status == "AWAITING_CLARIFICATION" and not answered:
            q = res.get("clarification") or {}
            _log(f"clarification field={q.get('field')!r}")
            ast, _ = _req("POST", f"/api/run/{sid}/answer",
                          {"answer": ANSWER})
            answered = True
            rec["answered"] = True
            rec["answer_http"] = ast
            _log(f"answered -> HTTP {ast}")
        if status in TERMINAL:
            terminal = status
            break
        time.sleep(POLL_S)

    rec["terminal"] = terminal
    rec["elapsed_min"] = round((time.time() - start) / 60, 1)
    _log(f"terminal={terminal} after {rec['elapsed_min']} min")

    card = None
    if terminal:
        st, res = _req("GET", f"/api/run/{sid}/result")
        usv = res.get("user_state_view") or {}
        card = usv.get("learning_card")
        rec["outcome"] = usv.get("outcome")
        rec["outcome_label"] = usv.get("outcome_label")
        rec["decision"] = usv.get("decision")
        if card:
            rec["learning_card"] = {
                "kind": card.get("kind"),
                "what_was_tested": card.get("what_was_tested"),
                "strongest_failed_hypothesis":
                    card.get("strongest_failed_hypothesis"),
                "key_missing_evidence": card.get("key_missing_evidence"),
                "ranked_next_actions": [
                    {"rank": a.get("rank"),
                     "action_kind": a.get("action_kind"),
                     "action": a.get("action")}
                    for a in (card.get("ranked_next_actions") or [])],
                "basis": card.get("basis")}
        # the no-survivor classes that MUST carry the card
        no_survivor = usv.get("outcome") in (
            "INVENTION_KILLED_BY_CHALLENGE", "NO_DEFENSIBLE_INVENTION",
            "INVENTION_UNDER_DEVELOPMENT") and not (
            res.get("package") or {}).get("complete")
        rec["card_contract"] = {
            "terminal": terminal,
            "outcome": usv.get("outcome"),
            "no_survivor_class": no_survivor,
            "card_present": card is not None,
            "verdict": ("CARD_LIVE" if card else (
                "N_A_SURVIVOR_OR_PACKAGE" if not no_survivor else
                "CONTRACT_MISS"))}
        _log(f"card_contract: {rec['card_contract']}")

    _save(rec)
    # sanitize the state file before exit (BS-021: no raw capability
    # persists after a terminal verdict)
    if terminal:
        sanitized = json.loads(STATE.read_text())
        sanitized["owner_key"] = "<sanitized at terminal>"
        STATE.write_text(json.dumps(sanitized, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
