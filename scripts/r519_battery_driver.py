#!/usr/bin/env python3
"""
R519 BATTERY DRIVER — submits the pre-registered blind problems to the
canonical production Space through the REAL user path, one arm at a time
(auditor directive R519 S10-13; Art. LXXIV durable execution; Art. LXXIX
blind discipline; Art. XLVII arm identity).

The arm is an EXPLICIT, recorded deployment state — never a per-request
tweak (SYNTHESIZE/MECHANISM_SPACE expose no per-request provider lever;
require_provider is wired only to attack/calibration endpoints):
  baseline  = pre-R518 build (commit a74c3a94; atria default pin active)
  optimized = R519 build (single retirement authority; atria retired from
              ordinary SYNTHESIS/ATTACK, zai from post-rank purposes)
R519_EXPECT_COMMIT gates submission: the Space must serve EXACTLY the
arm's build SHA (engine_commit), else the driver refuses (wrong build =
no blind battery on it).

Env (all have R519 defaults; the ARM selects the session files):
  R519_ARM            baseline | optimized   (REQUIRED — no default)
  R519_MANIFEST       default R519/BATTERY_PROBLEMS.json
  R519_SESSIONS       default R519/BATTERY_SESSIONS_<ARM>.json
  R519_REDACTED       default R519/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R519_BATTERY_NAME   default R519-routing-AB-<ARM>
  R519_TAG            default R519-BATTERY
  R519_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)

Modes:
  preflight      — health + identity (records deployed engine_commit;
                   refuses unless it matches R519_EXPECT_COMMIT)
  submit         — re-verify manifest sha + disjointness (fail-closed),
                   then submit each problem via POST /api/run; persist
                   the session file IMMEDIATELY (R489 lesson). Session
                   files are LOCAL ONLY (owner capabilities never
                   committed — BS-021; only the redacted mirror is).
  answer         — answer AWAITING_CLARIFICATION runs with the problem's
                   OWN verbatim summary bytes (R484 precedent: zero NEW
                   bytes authored; blindness intact by construction).
  poll [budget]  — observe-only polling; observation loss is NEVER
                   execution failure (typed OBSERVER states, Art. LXXIV).
  redact         — write the redacted custody mirror (session ids only).

Harvest lives in scripts/r519_harvest_ab.py (per-arm rows + A/B
comparison). Zero human bytes: no problem text is altered at
submission; the declaration prefix is machine-additive and
byte-auditable (verbatim summary is the suffix). No gate/threshold/
prompt tuning touches the scored set for the battery's duration; any
tuning voids the battery (Art. LXXIX). Repetitions re-submit the same
frozen problems as NEW sessions (R519_SESSIONS points at a fresh file
per wave; no re-selection between reps).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

ARM = os.environ.get("R519_ARM", "").strip().lower()
if ARM not in ("baseline", "optimized"):
    print("FATAL: R519_ARM must be 'baseline' or 'optimized' "
          "(explicit arm, never a default)")
    sys.exit(2)

MANIFEST = REPO / os.environ.get("R519_MANIFEST",
                                 "R519/BATTERY_PROBLEMS.json")
SESSIONS = REPO / os.environ.get("R519_SESSIONS",
                                 f"R519/BATTERY_SESSIONS_{ARM.upper()}.json")
REDACTED = REPO / os.environ.get(
    "R519_REDACTED", f"R519/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json")
BATTERY_NAME = os.environ.get("R519_BATTERY_NAME",
                              f"R519-routing-AB-{ARM}")
BATTERY_TAG = os.environ.get("R519_TAG", "R519-BATTERY")
EXPECT_COMMIT = os.environ.get("R519_EXPECT_COMMIT", "")
# Wave scheduling (R519 §11 tested fix): after the 4-way concurrent
# resume deaths, answers are STAGGERED (one at a time, each verified
# past TRANSPORT_PROBE before the next). R519_ONLY="2,3,4" restricts
# this wave to the listed manifest selection_index values. Scheduling
# only — problem set, prompts, budgets, and measurement are untouched
# (not tuning; Art. LXXIX void conditions unaffected).
ONLY = {int(x) for x in os.environ.get("R519_ONLY", "").split(",")
        if x.strip().isdigit()}

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
POLL_INTERVAL_S = 60
DEFAULT_BUDGET_MIN = 25
TERMINAL_STATES = {"COMPLETE", "ERROR_RUN", "ERROR_STUCK",
                   "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
                   "RUN_BLOCKED_CAPABILITY", "RUN_BLOCKED"}


def _req(method, path, body=None, headers=None, timeout=90):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {HF_TOKEN}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def _norm_tokens(text):
    import re
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def _ngrams(text, n=8):
    t = _norm_tokens(text)
    return {" ".join(t[i:i + n]) for i in range(len(t) - n + 1)}


def _corpus_grams():
    import glob
    grams = set()
    c = json.loads((REPO / "R458" / "BENCHMARK_CORPUS.json")
                   .read_text(encoding="utf-8"))
    for p in c["problems"].values():
        grams |= _ngrams(json.dumps(p, sort_keys=True))
    with open(REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json",
              encoding="utf-8") as f:
        c = json.load(f)
    for case in c["cases"]:
        grams |= _ngrams(json.dumps(case, sort_keys=True))
    for f in glob.glob(str(REPO / "R446" / "*.json")) + \
            glob.glob(str(REPO / "R412" / "*.json")):
        grams |= _ngrams(open(f, encoding="utf-8",
                              errors="replace").read())
    return grams


def preflight():
    if not HF_TOKEN:
        print("FATAL: HF_TOKEN absent from env (Art. LXXIII lookup "
              "order exhausted before asking)")
        return 2
    if not EXPECT_COMMIT:
        print("FATAL: R519_EXPECT_COMMIT absent — the arm build SHA "
              "must be named before any submission (Art. XLVII)")
        return 2
    try:
        st, h = _req("GET", "/api/health")
        if st != 200 or not h.get("ok"):
            print(f"PREFLIGHT REFUSED: health not ok: {st}")
            return 2
        print(f"health ok=true | commit={h.get('commit') or h.get('engine_commit')}")
    except Exception as e:
        print(f"PREFLIGHT REFUSED: health unreachable: {e}")
        return 2
    try:
        st, v = _req("GET", "/api/version")
        eng = (v.get("engine_commit") or "")[:12]
        print(f"version engine_commit={eng} "
              f"const={v.get('constitution_version')}")
        if not (v.get("engine_commit") or "").startswith(EXPECT_COMMIT):
            print(f"PREFLIGHT REFUSED: deployed {eng} != expected "
                  f"{EXPECT_COMMIT} (no blind battery on the wrong "
                  f"build — Art. XLVII)")
            return 2
    except Exception as e:
        print(f"PREFLIGHT REFUSED: version probe: {e}")
        return 2
    print(f"PREFLIGHT OK (arm={ARM} battery={BATTERY_NAME})")
    return 0


def submit():
    if not HF_TOKEN:
        print("FATAL: HF_TOKEN absent from env")
        return 2
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if m.get("selection_status") != "OK":
        print("manifest selection_status != OK — refusing")
        return 2
    grams = _corpus_grams()
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8")) \
        if SESSIONS.exists() else {
            "battery": BATTERY_NAME,
            "arm": ARM,
            "expected_commit": EXPECT_COMMIT,
            "manifest_sha256":
                hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            "submissions": []}
    subs = {s.get("problem_index") for s in sessions["submissions"]}
    for p in m["problems"]:
        idx = p["selection_index"]
        if ONLY and idx not in ONLY:
            print(f"#{idx} not in R519_ONLY wave filter — skip")
            continue
        if idx in subs:
            print(f"#{idx} already submitted ({p['source_id']}) — skip")
            continue
        verbatim = p["summary_verbatim"]
        if hashlib.sha256(verbatim.encode()).hexdigest() != \
                p["verbatim_summary_sha256"]:
            print(f"#{idx} HASH MISMATCH vs manifest — refusing")
            return 2
        if _ngrams(verbatim) & grams:
            print(f"#{idx} CORPUS COLLISION at submit-time — refusing")
            return 2
        prefix = (f"[{BATTERY_TAG} declared_family={p['declared_family']} "
                  f"source={p['source_id']} battery={BATTERY_NAME}]\n\n")
        try:
            st, resp = _req("POST", "/api/run",
                            {"text": prefix + verbatim}, timeout=180)
        except urllib.error.HTTPError as e:
            print(f"#{idx} submit HTTP {e.code}")
            return 2
        except Exception as e:
            print(f"#{idx} submit OBSERVER {type(e).__name__} "
                  f"(run may exist server-side; re-run submit to "
                  f"reconcile — server state is the authority)")
            return 2
        sid = resp.get("session_id") or resp.get("run_id")
        okey = resp.get("owner_key")
        sessions["submissions"].append({
            "problem_index": idx, "source_id": p["source_id"],
            "declared_family": p["declared_family"],
            "session_id": sid, "owner_key": okey,
            "submitted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime()),
            "response": {k: v for k, v in resp.items()
                         if k != "owner_key"}})
        # LOCAL ONLY (never committed — BS-021; the redacted mirror
        # is the committable custody record, written by redact mode).
        with open(SESSIONS, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=1)
        print(f"#{idx} submitted -> session {sid} (LOCAL session file "
              f"updated; owner_key {'present' if okey else 'ABSENT'})")
        time.sleep(5)
    print("submit complete (session file is LOCAL-ONLY, never commit)")
    return 0


def answer_clarifications():
    if not HF_TOKEN:
        print("FATAL: HF_TOKEN absent from env")
        return 2
    if not SESSIONS.exists():
        print("no sessions file")
        return 2
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8"))
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_idx = {p["selection_index"]: p for p in m["problems"]}
    one = os.environ.get("R519_ANSWER_ONE", "").strip()
    for s in sessions["submissions"]:
        if one and str(s["problem_index"]) != one:
            print(f"#{s['problem_index']} deferred (R519_ANSWER_ONE={one})")
            continue
        sid = s.get("session_id")
        if not sid:
            continue
        verbatim = by_idx[s["problem_index"]]["summary_verbatim"]
        try:
            st, res = _req("GET", f"/api/run/{sid}/result",
                           headers={"X-Tosca-Owner":
                                    s.get("owner_key") or ""})
            status = res.get("status") or res.get("state")
            if status != "AWAITING_CLARIFICATION":
                print(f"#{s['problem_index']} {sid}: {status}")
                continue
            q = res.get("clarification") or {}
            st2, _ = _req("POST", f"/api/run/{sid}/answer",
                          {"answer": verbatim[:2000],
                           "field": q.get("field") or ""},
                          headers={"X-Tosca-Owner":
                                   s.get("owner_key") or ""})
            print(f"#{s['problem_index']} {sid}: clarification "
                  f"'{q.get('field')}' answered with own verbatim "
                  f"text (HTTP {st2}; zero new bytes)")
        except urllib.error.HTTPError as e:
            print(f"#{s['problem_index']} {sid}: HTTP {e.code} "
                  f"(typed; run continues server-side)")
        except Exception as e:
            print(f"#{s['problem_index']} {sid}: OBSERVER "
                  f"{type(e).__name__}")
        time.sleep(3)
    return 0


def poll(budget_min=DEFAULT_BUDGET_MIN):
    if not HF_TOKEN:
        print("FATAL: HF_TOKEN absent from env")
        return 2
    if not SESSIONS.exists():
        print("no sessions file")
        return 2
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8"))
    deadline = time.time() + budget_min * 60
    states = {}
    while time.time() < deadline:
        for s in sessions["submissions"]:
            sid = s.get("session_id")
            if not sid:
                continue
            try:
                st, res = _req("GET", f"/api/run/{sid}/result",
                               headers={"X-Tosca-Owner":
                                        s.get("owner_key") or ""})
                state = res.get("state") or res.get("status") \
                    or f"HTTP_{st}"
            except urllib.error.HTTPError as e:
                state = f"HTTP_{e.code}"
            except Exception as e:
                state = f"POLL_INTERRUPTED:{type(e).__name__}"
            states[sid] = state
        print(time.strftime("%H:%M:%S"), json.dumps(states))
        if states and all(str(v).upper() in TERMINAL_STATES
                          for v in states.values()):
            break
        time.sleep(POLL_INTERVAL_S)
    print("poll window ended (observation states are observer facts; "
          "terminal authority = the durable branch)")
    return 0


def redact():
    if not SESSIONS.exists():
        print("no sessions file")
        return 2
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8"))
    redacted = {
        "battery": sessions.get("battery"),
        "arm": sessions.get("arm"),
        "expected_commit": sessions.get("expected_commit"),
        "manifest_sha256": sessions.get("manifest_sha256"),
        "note": ("REDACTED custody: session ids only; owner "
                 "capabilities are LOCAL-ONLY and never committed "
                 "(BS-021)"),
        "submissions": [
            {"problem_index": s.get("problem_index"),
             "source_id": s.get("source_id"),
             "declared_family": s.get("declared_family"),
             "session_id": s.get("session_id"),
             "submitted_at_utc": s.get("submitted_at_utc")}
            for s in sessions.get("submissions", [])]}
    REDACTED.write_text(json.dumps(redacted, indent=1),
                        encoding="utf-8")
    print(f"wrote {REDACTED} (committable; no capabilities inside)")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    if mode == "preflight":
        sys.exit(preflight())
    elif mode == "submit":
        sys.exit(submit())
    elif mode == "answer":
        sys.exit(answer_clarifications())
    elif mode == "poll":
        sys.exit(poll(int(sys.argv[2]) if len(sys.argv) > 2
                      else DEFAULT_BUDGET_MIN))
    elif mode == "redact":
        sys.exit(redact())
    else:
        print("modes: preflight | submit | answer | poll [budget] | "
              "redact")
        sys.exit(1)
