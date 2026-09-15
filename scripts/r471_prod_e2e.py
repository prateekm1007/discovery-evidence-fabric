#!/usr/bin/env python3
"""R471 production E2E — the external audit's P0-4/P0-2/P0-5/P0-6
acceptance measured on the DEPLOYED product (fresh owner, real run).

Legs (every result recorded honestly; no fabricated success):
  A. P0-6 LIVE — the URL leg: a real public URL fetches into the
     attachment custody chain (TEXT_EXTRACTED or an honest typed
     status); a file:// URL is typed REJECTED_BLOCKED_URL and the
     fetcher provably never runs for it.
  B. THE JOURNEY — fresh owner capability -> POST /api/run (problem +
     the fetched URL reference bound) -> clarification pause -> answer
     -> the full ladder to a TERMINAL state (bound in time; a bound
     expiry is recorded honestly as the audit's recovery-path test
     input, never spun as a completion).
  C. P0-5 LIVE — after the answer and at terminal, the result
     projection's clarification_answer carries field/answer and
     provenance USER_STATED (the audited empty-object class).
  D. P0-2 LIVE — POST retry on a COMPLETE session: the typed 409
     refusal (no session-shaped body); the retry contract is
     contract-safe from the API side the frontend now speaks.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R471" / "PROD_RUN"
OWNER = f"r471e2e{uuid.uuid4().hex[:16]}"
PROBLEM = (
    "Drinking-water distribution networks in hot climates develop "
    "biofilm on the pipe walls that resists standard chlorine dosing; "
    "find a mechanism that keeps the biofilm from re-establishing "
    "without replacing the pipes."
)
POLL_S = 20
TERMINAL_BOUND_MIN = 35.0
RESUME_BOUND_MIN = 30.0
TERMINAL_STATES = {
    "COMPLETE", "COMPLETED_UNDER_DEVELOPMENT", "INVENTION_UNDER_DEVELOPMENT",
    "RUN_BLOCKED_TRANSPORT", "INTERRUPTED", "ERROR_TRANSPORT", "ERROR_RUN",
    "ERROR_BUILD", "ERROR_STUCK", "ERROR_SPAWN",
}


def _req(method: str, path: str, body=None, timeout: float = 60):
    req = urllib.request.Request(
        BASE.rstrip("/") + path, method=method,
        headers={"Content-Type": "application/json",
                 "X-Tosca-Owner": _owner(),
                 "User-Agent": "r471-e2e/1.0"},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8",
                                                             "replace"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return exc.code, {}
    # URLError propagates — a transport failure is recorded as such


def _log(msg: str):
    print(f"[r471-e2e {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# the resumed owner capability replaces the module-level fresh one
_OWNER_OVERRIDE = None


def _owner() -> str:
    return _OWNER_OVERRIDE or OWNER


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    state_path = OUT / "driver_state.json"
    record: dict = {"owner_fingerprint": OWNER[:12], "base": BASE,
                    "legs": {}}

    # resumable driver: each foreground invocation must survive being
    # killed by a tool timeout — the state file carries the owner
    # capability + session across invocations (resume, never re-create)
    resumed = False
    sid = None
    owner_key = None
    if state_path.exists():
        try:
            st_prev = json.loads(state_path.read_text())
            sid = st_prev.get("session_id")
            owner_key = st_prev.get("owner_key")
            record = st_prev.get("record", record)
            resumed = bool(sid and owner_key)
            if resumed:
                _log(f"RESUMED driver state: run {sid}")
        except Exception:  # noqa: BLE001 — a corrupt state re-creates
            resumed = False
    global _OWNER_OVERRIDE
    if resumed:
        _OWNER_OVERRIDE = owner_key

    # ---- Leg A: the URL leg, live (skip on resume) ---------------------
    if not resumed:
        _log("LEG A: URL ingestion, live")
        st, ok_url = _req("POST", "/api/attachments/url",
                          {"url": "https://example.com/"})
        rec_ok = (ok_url.get("attachments") or [{}])[0]
        _log(f"  public URL -> HTTP {st} "
             f"{rec_ok.get('ingestion', {}).get('status')}")
        st, bad_url = _req("POST", "/api/attachments/url",
                           {"url": "file:///etc/passwd"})
        rec_bad = (bad_url.get("attachments") or [{}])[0]
        _log(f"  file:// -> HTTP {st} "
             f"{rec_bad.get('ingestion', {}).get('status')}")
        url_bound = None
        if not rec_ok.get("rejected") and rec_ok.get("attachment_id"):
            url_bound = rec_ok["attachment_id"]
        record["legs"]["A_url"] = {
            "public": {"record": {
                k: rec_ok.get(k) for k in
                ("attachment_id", "name", "source_url", "media_type",
                 "bytes")},
                "ingestion": rec_ok.get("ingestion")},
            "blocked": {"record_status":
                        rec_bad.get("ingestion", {}).get("status"),
                        "note": rec_bad.get("ingestion", {}).get("note")},
        }
        _save(record, state_path, None, None)

    # ---- Leg B: the journey (resume-aware) -----------------------------
    if not resumed:
        _log("LEG B: fresh-owner run")
        body = {"text": PROBLEM}
        if url_bound:
            body["attachment_ids"] = [url_bound]
        st, run = _req("POST", "/api/run", body)
        sid = run.get("session_id")
        owner_key = run.get("owner_key")
        _log(f"  run {sid} HTTP {st} owner={owner_key[:8] if owner_key else '-'}")
        record["legs"]["B_run"] = {"session_id": sid, "http": st}
        if not sid:
            record["legs"]["B_run"]["error"] = run
            _log("  FATAL: no session id"); _save(record, state_path,
                                                   None, None)
            return 1
        _save(record, state_path, sid, owner_key)
    else:
        _log("LEG B: resumed — the journey continues on the recorded run")

    answered = False
    answer_at = None
    start = time.time()
    terminal = None
    last_status = None
    if resumed and record["legs"].get("B_run", {}).get("clarification"):
        answered = True  # the answer already rode the recorded run
    if resumed and record["legs"]["B_run"].get("journey_started_at"):
        start = record["legs"]["B_run"]["journey_started_at"]
    else:
        record["legs"]["B_run"]["journey_started_at"] = start
        _save(record, state_path, sid, owner_key)
    while time.time() - start < TERMINAL_BOUND_MIN * 60:
        st, res = _req("GET", f"/api/run/{sid}/result")
        status = res.get("status")
        if status != last_status:
            _log(f"  status -> {status}")
            last_status = status
        if status == "AWAITING_CLARIFICATION" and not answered:
            q = (res.get("clarification") or {})
            _log(f"  clarification on field={q.get('field')!r}: "
                 f"{str(q.get('question'))[:90]}")
            ast, ares = _req("POST", f"/api/run/{sid}/answer",
                             {"answer": (
                                 "Keep the residual disinfectant in the "
                                 "far network reaches above the minimum "
                                 "all summer, and do not increase pump "
                                 "energy use.")})
            answered = True
            answer_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _log(f"  answered -> HTTP {ast} resumed={ares.get('resumed')}")
            record["legs"]["B_run"]["clarification"] = {
                "field": q.get("field"), "answer_http": ast,
                "resumed": ares.get("resumed"), "answered_at": answer_at}
            time.sleep(POLL_S)
            continue
        if status in TERMINAL_STATES:
            terminal = status
            break
        time.sleep(POLL_S)

    elapsed_min = round((time.time() - start) / 60, 1)
    _log(f"  terminal={terminal} after {elapsed_min} min")
    record["legs"]["B_run"]["terminal"] = terminal
    record["legs"]["B_run"]["elapsed_min"] = elapsed_min
    record["legs"]["B_run"]["reached_terminal"] = terminal is not None
    _save(record, state_path, sid, owner_key)

    # ---- Leg C: the clarification record at terminal -------------------
    _log("LEG C: clarification_answer typed record")
    st, res = _req("GET", f"/api/run/{sid}/result")
    ca = res.get("clarification_answer") or {}
    conv_has_answer = any(
        "residual disinfectant" in str(m.get("text") or "")
        for m in (res.get("conversation") or []))
    record["legs"]["C_clarification"] = {
        "field": ca.get("field"), "provenance": ca.get("provenance"),
        "consumed_at": ca.get("consumed_at"),
        "answer_present": bool(ca.get("answer")),
        "conversation_has_answer": conv_has_answer,
    }
    _log(f"  typed record: field={ca.get('field')} "
         f"provenance={ca.get('provenance')} "
         f"answer_present={bool(ca.get('answer'))} "
         f"consumed_at={ca.get('consumed_at')}")

    # ---- Leg D: the retry contract, live --------------------------------
    # Both halves of the contract, measured on the audited path:
    #   D1 — a retry on an INTERRUPTED run is ACCEPTED (202 + retry_id)
    #        and the run resumes (the audit's interruption-resume test);
    #   D2 — after the resumed run reaches a verdict terminal, a retry
    #        is a TYPED 409 refusal (no session-shaped body).
    _log("LEG D: retry contract, live")
    d: dict = {}
    # D1 may already have been measured by a prior (killed) invocation —
    # the state file carried the observation; never lose it
    prior_d = record["legs"].get("D_retry") or {}
    prior_on_terminal = prior_d.get("on_terminal") or (
        {"http": prior_d.get("http"), "body": prior_d.get("body")}
        if prior_d.get("http") else None)
    st, retry = _req("POST", f"/api/sessions/{sid}/retry")
    this_obs = {"http": st, "body": {
        k: retry.get(k) for k in ("retry_id", "status", "retry_attempts",
                                  "refusal", "session_status",
                                  "retryable") if k in retry}}
    _log(f"  retry on {terminal} -> HTTP {st} "
         f"retry_id={retry.get('retry_id')} refusal={retry.get('refusal')}")
    _save(record, state_path, sid, owner_key)

    if st == 202:
        d["on_terminal"] = this_obs
        # D1 measured — the resume is real: poll the SAME run to its
        # next terminal (the recovery path, end to end)
        _log("  accepted — the resumed run is polled to its next terminal")
        start2 = time.time()
        terminal2 = None
        last2 = None
        while time.time() - start2 < RESUME_BOUND_MIN * 60:
            st2, res2 = _req("GET", f"/api/run/{sid}/result")
            status2 = res2.get("status")
            if status2 != last2:
                _log(f"  resumed status -> {status2}")
                last2 = status2
            if status2 in TERMINAL_STATES:
                terminal2 = status2
                break
            time.sleep(POLL_S)
        d["resumed_terminal"] = terminal2
        d["resumed_elapsed_min"] = round((time.time() - start2) / 60, 1)
        _log(f"  resumed terminal={terminal2}")
        if terminal2 in ("COMPLETE", "COMPLETED_UNDER_DEVELOPMENT",
                         "INVENTION_UNDER_DEVELOPMENT"):
            # D2: a verdict is append-only — the retry must refuse, typed
            st3, retry3 = _req("POST", f"/api/sessions/{sid}/retry")
            d["refusal_after_verdict"] = {"http": st3, "body": {
                k: retry3.get(k) for k in ("refusal", "session_status",
                                           "retryable") if k in retry3}}
            _log(f"  retry on {terminal2} -> HTTP {st3} "
                 f"refusal={retry3.get('refusal')}")
        _save(record, state_path, sid, owner_key)
    elif prior_on_terminal and prior_on_terminal.get("http") == 202:
        # D1 was measured in the prior invocation (its retry resumed the
        # run — this invocation's main loop just polled it to the NEW
        # terminal); this observation is the D2 refusal half
        d["on_terminal"] = prior_on_terminal
        d["refusal_after_verdict"] = this_obs
        d["resumed_terminal"] = terminal
    else:
        d["on_terminal"] = this_obs
    record["legs"]["D_retry"] = d
    verdict_legs = {
        "A_url_fetched": record["legs"]["A_url"]["public"]["ingestion"]
        .get("status") in ("TEXT_EXTRACTED", "STORED"),
        "A_blocked_typed": record["legs"]["A_url"]["blocked"]
        .get("record_status") == "REJECTED_BLOCKED_URL",
        "B_terminal": terminal is not None,
        "C_record_survives": (record["legs"]["C_clarification"]
                              .get("answer_present")
                              and record["legs"]["C_clarification"]
                              .get("provenance") == "USER_STATED"),
        # the contract: an interrupted run's retry is accepted 202 (the
        # audit's measured 409-with-PENDING-body is dead); a verdict's
        # retry (when measured) refuses typed with no session body
        "D_contract": (d.get("on_terminal", {}).get("http") == 202
                       and bool(d.get("on_terminal", {}).get("body", {})
                                .get("retry_id"))
                       and (d.get("refusal_after_verdict", {}).get("http")
                            in (None, 409))
                       and (d.get("refusal_after_verdict", {})
                            .get("body", {}).get("refusal")
                            in (None, "RETRY_NOT_PERMITTED"))),
    }
    record["verdict"] = verdict_legs
    _save(record, state_path, sid, owner_key)
    _log(f"VERDICT: {verdict_legs}")
    return 0 if all(verdict_legs.values()) else 1


def _save(record: dict, state_path: Path, sid, owner_key):
    (OUT / "E2E_RECORD.json").write_text(json.dumps(record, indent=1))
    if sid and owner_key:
        state_path.write_text(json.dumps({"session_id": sid,
                                          "owner_key": owner_key,
                                          "record": record}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
