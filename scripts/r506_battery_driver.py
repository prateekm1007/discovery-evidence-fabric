#!/usr/bin/env python3
"""
R506 BATTERY DRIVER — submits the pre-registered blind problems to the
canonical production Space through the REAL user path and drives the yield
battery to terminal (directive section 3; Art. LXXIV durable execution).

Modes:
  preflight      — health + identity + ring check; refuses to submit unless ok
  submit         — re-verify manifest hashes + disjointness (fail-closed),
                   then submit each problem via POST /api/run; persist
                   session/owner capability records IMMEDIATELY (the R489
                   lesson: capability lost with its container is unrecoverable)
  poll [budget]  — observe-only polling; observation loss is NEVER execution
                   failure (typed OBSERVER states per Art. LXXIV)
  harvest        — durable-branch session-id-verified harvest of terminal
                   runs + the yield instrument per run ->
                   R506/YIELD_MEASUREMENT.json

Zero human bytes: no problem text is altered at submission; the declaration
prefix is machine-additive and byte-auditable (verbatim summary is the
suffix). No gate/threshold/prompt tuning touches the scored set for the
battery's duration; any tuning voids the battery (draft Art. LXXIX).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Battery-2 generalization (R510-C13): every battery identity resolves from
# env with the R506 frozen defaults — default behavior byte-identical.
MANIFEST = REPO / os.environ.get("R506_MANIFEST", "R506/BATTERY_PROBLEMS.json")
SESSIONS = REPO / os.environ.get("R506_SESSIONS", "R506/BATTERY_SESSIONS.json")
MEASUREMENT = REPO / os.environ.get("R506_MEASUREMENT",
                                    "R506/YIELD_MEASUREMENT.json")
BATTERY_NAME = os.environ.get("R506_BATTERY_NAME", "R506-discovery-yield")
BATTERY_TAG = os.environ.get("R506_BATTERY_TAG", "R506-BATTERY")
YIELD_ROW_PREFIX = os.environ.get("R506_YIELD_ROW_PREFIX", "YIELD_ROW_")
INSTRUMENT = REPO / "scripts" / "r506_discovery_yield.py"
WORKTREE = Path(os.environ.get("R506_DURABLE_WORKTREE",
                               "/home/z/my-project/r506_durable"))

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
POLL_INTERVAL_S = 60
DEFAULT_BUDGET_MIN = 30


def _req(method, path, body=None, headers=None, timeout=60):
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
    grams = set()
    sys.path.insert(0, str(REPO))
    import glob
    c = json.load(open(REPO / "R458" / "BENCHMARK_CORPUS.json"))
    for p in c["problems"].values():
        grams |= _ngrams(json.dumps(p, sort_keys=True))
    c = json.load(open(REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json"))
    for case in c["cases"]:
        grams |= _ngrams(json.dumps(case, sort_keys=True))
    for f in glob.glob(str(REPO / "R446" / "*.json")) + \
             glob.glob(str(REPO / "R412" / "*.json")):
        grams |= _ngrams(open(f, encoding="utf-8", errors="replace").read())
    return grams


def preflight():
    ok, fails = True, []
    # health
    try:
        st, h = _req("GET", "/api/health")
        if st != 200 or not h.get("ok"):
            ok = False
            fails.append(f"health not ok: {st} {json.dumps(h)[:200]}")
        else:
            print(f"health ok=true | commit={h.get('commit') or h.get('engine_commit')} "
                  f"| unorouter={h.get('unorouter',{}).get('status','?')} "
                  f"| atria={h.get('atria',{}).get('status','?')} "
                  f"| xkiro={h.get('xkiro',{}).get('status','?')}")
    except Exception as e:
        ok = False
        fails.append(f"health unreachable: {e}")
    # version identity
    try:
        st, v = _req("GET", "/api/version")
        print(f"version: {json.dumps(v)[:200]}")
    except Exception as e:
        fails.append(f"version probe: {e}")
    if not ok:
        print("PREFLIGHT REFUSED:", fails)
        return 2
    print("PREFLIGHT OK — pinned ring healthy")
    return 0


def submit():
    m = json.load(open(MANIFEST))
    if m.get("selection_status") != "OK":
        print("manifest selection_status != OK — refusing")
        return 2
    grams = _corpus_grams()
    sessions = json.load(open(SESSIONS)) if SESSIONS.exists() else {
        "battery": BATTERY_NAME, "manifest_sha256":
            hashlib.sha256(open(MANIFEST, "rb").read()).hexdigest(),
        "submissions": []}
    subs = {s.get("problem_index") for s in sessions["submissions"]}
    for p in m["problems"]:
        idx = p["selection_index"]
        if idx in subs:
            print(f"#{idx} already submitted ({p['source_id']}) — skip")
            continue
        verbatim = p["summary_verbatim"]
        # fail-closed re-verification BEFORE submission
        if hashlib.sha256(verbatim.encode()).hexdigest() != p["verbatim_summary_sha256"]:
            print(f"#{idx} HASH MISMATCH vs manifest — refusing")
            return 2
        shared = _ngrams(verbatim) & grams
        if shared:
            print(f"#{idx} CORPUS COLLISION at submit-time: {sorted(shared)[:2]} — refusing")
            return 2
        prefix = (f"[{BATTERY_TAG} declared_family={p['declared_family']} "
                  f"source={p['source_id']} battery={BATTERY_NAME}]\n\n")
        text = prefix + verbatim
        try:
            st, resp = _req("POST", "/api/run", {"text": text})
        except urllib.error.HTTPError as e:
            print(f"#{idx} submit HTTP {e.code}: {e.read()[:200]}")
            return 2
        sid = resp.get("session_id") or resp.get("run_id")
        okey = resp.get("owner_key")
        rec = {"problem_index": idx, "source_id": p["source_id"],
               "declared_family": p["declared_family"],
               "session_id": sid, "owner_key": okey,
               "submitted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime()),
               "response": {k: v for k, v in resp.items() if k != "owner_key"}}
        sessions["submissions"].append(rec)
        # IMMEDIATE durable write of the capability record (R489 lesson)
        with open(SESSIONS, "w") as f:
            json.dump(sessions, f, indent=1)
        print(f"#{idx} submitted -> session {sid} (capability persisted; "
              f"owner_key {'present' if okey else 'ABSENT'})")
        time.sleep(5)
    # custody: push the sessions file to the durable branch
    _push_custody()
    return 0


def _push_custody():
    """Push a REDACTED custody record (session ids only, NO owner keys).
    Owner capabilities are deliberately non-durable (BS-021 by design — the
    R489 record); the durable-branch harvest needs session ids only."""
    if not (GITHUB_TOKEN and WORKTREE.exists() and SESSIONS.exists()):
        return
    try:
        sessions = json.load(open(SESSIONS))
        redacted = {"battery": sessions.get("battery"),
                    "manifest_sha256": sessions.get("manifest_sha256"),
                    "note": "REDACTED custody: session ids only; owner "
                            "capabilities are deliberately non-durable "
                            "(BS-021 by design, the R489 record)",
                    "submissions": [{"problem_index": s.get("problem_index"),
                                     "source_id": s.get("source_id"),
                                     "declared_family": s.get("declared_family"),
                                     "session_id": s.get("session_id"),
                                     "submitted_at_utc": s.get("submitted_at_utc")}
                                    for s in sessions.get("submissions", [])]}
        dst = WORKTREE / "battery" / (BATTERY_NAME + "_SESSIONS_REDACTED.json")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "w") as f:
            json.dump(redacted, f, indent=1)
        subprocess.run(["git", "-C", str(WORKTREE), "add", "battery/"],
                       check=True, timeout=60)
        subprocess.run(["git", "-C", str(WORKTREE), "commit", "-m",
                        BATTERY_NAME + " battery custody (REDACTED): session "
                        "ids only; owner capabilities deliberately "
                        "non-durable per BS-021/R489"],
                       capture_output=True, timeout=120)
        r = subprocess.run(["git", "-C", str(WORKTREE), "push", "origin",
                            "HEAD:runtime-state-hf"], capture_output=True,
                           text=True, timeout=180)
        print("custody push (redacted):", "OK" if r.returncode == 0
              else f"failed (typed; local copy remains): {r.stderr[-200:]}")
    except Exception as e:
        print(f"custody push typed failure (local copy remains): {e}")


def answer_clarifications():
    """Mechanically answer AWAITING_CLARIFICATION runs with the problem's OWN
    verbatim summary (the R484 precedent: 'the clarification answered with
    the EXACT predecessor text') — zero NEW bytes authored. Disclosed in the
    measurement record."""
    if not SESSIONS.exists():
        print("no sessions file")
        return 2
    sessions = json.load(open(SESSIONS))
    m = json.load(open(MANIFEST))
    by_idx = {p["selection_index"]: p for p in m["problems"]}
    for s in sessions["submissions"]:
        sid = s.get("session_id")
        p = by_idx[s["problem_index"]]
        verbatim = p["summary_verbatim"]
        try:
            st, res = _req("GET", f"/api/run/{sid}/result",
                           headers={"X-Tosca-Owner": s.get("owner_key") or ""})
            status = res.get("status") or res.get("state")
            if status != "AWAITING_CLARIFICATION":
                print(f"#{s['problem_index']} {sid}: status {status} — no answer needed")
                continue
            q = res.get("clarification") or {}
            field = q.get("field") or ""
            answer = verbatim[:2000]  # the run's own submitted bytes, verbatim
            st2, resp2 = _req("POST", f"/api/run/{sid}/answer",
                              {"answer": answer, "field": field},
                              headers={"X-Tosca-Owner": s.get("owner_key") or ""})
            print(f"#{s['problem_index']} {sid}: clarification '{field}' "
                  f"answered with the problem's own verbatim text (HTTP {st2})")
        except urllib.error.HTTPError as e:
            print(f"#{s['problem_index']} {sid}: HTTP {e.code} "
                  f"(typed; run continues server-side)")
        except Exception as e:
            print(f"#{s['problem_index']} {sid}: OBSERVER {type(e).__name__}")
        time.sleep(3)
    return 0


def poll(budget_min=DEFAULT_BUDGET_MIN):
    if not SESSIONS.exists():
        print("no sessions file")
        return 2
    sessions = json.load(open(SESSIONS))
    deadline = time.time() + budget_min * 60
    states = {}
    while time.time() < deadline:
        for s in sessions["submissions"]:
            sid = s.get("session_id")
            if not sid:
                continue
            try:
                st, res = _req("GET", f"/api/run/{sid}/result")
                state = res.get("state") or res.get("status") or f"HTTP_{st}"
            except urllib.error.HTTPError as e:
                state = f"HTTP_{e.code}"
            except Exception as e:
                state = f"POLL_INTERRUPTED:{type(e).__name__}"  # observer state
            states[sid] = state
        print(time.strftime("%H:%M:%S"), json.dumps(states))
        if states and all(
                str(v).upper() in ("COMPLETE", "ERROR_RUN", "ERROR_STUCK",
                                   "INTERRUPTED", "RUN_BLOCKED_CAPABILITY")
                for v in states.values()):
            break
        time.sleep(POLL_INTERVAL_S)
    print("poll window ended (observation states above are observer facts; "
          "terminal authority = the durable branch)")
    return 0


def harvest():
    if not SESSIONS.exists():
        print("no sessions file")
        return 2
    sessions = json.load(open(SESSIONS))
    rows = []
    for s in sessions["submissions"]:
        sid = s.get("session_id")
        slug = _find_slug_by_session(sid)
        if not slug:
            rows.append({"problem_index": s["problem_index"],
                         "source_id": s["source_id"],
                         "session_id": sid,
                         "harvest": "NOT_YET_ON_DURABLE_BRANCH_OR_UNKNOWN"})
            continue
        out = REPO / os.environ.get("R506_YIELD_DIR", "R506") / \
            f"{YIELD_ROW_PREFIX}{s['problem_index']}_{slug}.json"
        r = subprocess.run(
            [sys.executable, str(INSTRUMENT), "--run-dir",
             str(WORKTREE / "runs" / slug), "--out", str(out)],
            capture_output=True, text=True)
        if r.returncode != 0:
            rows.append({"problem_index": s["problem_index"],
                         "session_id": sid, "run_slug": slug,
                         "harvest": f"INSTRUMENT_ERROR: {r.stderr[-200:]}"})
            continue
        row = json.load(open(out))["rows"][0]
        rows.append({"problem_index": s["problem_index"],
                     "source_id": s["source_id"],
                     "declared_family": s["declared_family"],
                     "run_slug": slug, "row_file": str(out.relative_to(REPO)),
                     "row": row})
    measurement = {
        "artifact_type": "R506_YIELD_MEASUREMENT",
        "battery": BATTERY_NAME,
        "instrument": "r506_discovery_yield/1.0.0",
        "instrument_sha256": hashlib.sha256(
            open(INSTRUMENT, "rb").read()).hexdigest(),
        "manifest_sha256": hashlib.sha256(
            open(MANIFEST, "rb").read()).hexdigest(),
        "harvested_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": rows,
        "aggregate": _aggregate(rows),
        "reviewer_provenance": "AI_REVIEW",
    }
    with open(MEASUREMENT, "w") as f:
        json.dump(measurement, f, indent=1, ensure_ascii=False)
    print(f"wrote {MEASUREMENT}")
    return 0


def _find_slug_by_session(sid):
    if not WORKTREE.exists():
        return None
    runs = WORKTREE / "runs"
    for slug in sorted(os.listdir(runs)) if runs.exists() else []:
        mf = runs / slug / "run_manifest.json"
        fs = runs / slug / "final_state.json"
        for f in (mf, fs):
            if f.exists():
                try:
                    d = json.load(open(f))
                    if d.get("session_id") == sid:
                        return slug
                except Exception:
                    pass
    # also try git-side durable branch (fresh commits may not be fetched)
    try:
        r = subprocess.run(
            ["git", "-C", str(WORKTREE), "log", "origin/runtime-state-hf",
             "--format=%H", "-S", sid, "--", "runs"], capture_output=True,
            text=True, timeout=120)
        if r.stdout.strip():
            subprocess.run(["git", "-C", str(WORKTREE), "fetch", "origin",
                            "runtime-state-hf"], capture_output=True,
                           timeout=120)
            return None  # re-harvest after fetch on next invocation
    except Exception:
        pass
    return None


def _aggregate(rows):
    full = [r for r in rows if isinstance(r.get("row"), dict)]
    if not full:
        return {"n_rows": len(rows), "n_harvested_rows": 0,
                "note": "no terminal rows harvested yet — typed, never failure"}
    ORDER = ["fresh_submitted", "premise_coherent", "evidence_verified",
             "mechanisms_found", "candidates_generated_distinct",
             "attack_survivors", "contradiction_survivors",
             "experimentally_discriminated", "mutated_survivors", "buyer_ready"]
    n = len(full)
    funnel = []
    for name in ORDER:
        reached = sum(1 for r in full if (r["row"].get(name) or {}).get("reached"))
        funnel.append({"transition": name, "reached": reached, "of_n": n,
                       "rate": round(reached / n, 4) if n else None})
    drops = {}
    for r in full:
        row = r["row"]
        if row.get("lost_at"):
            k = f"{row['lost_at']}::{row.get('typed_drop_reason')}"
            drops.setdefault(k, 0)
            drops[k] += 1
    ranked = sorted([{"lost_at::reason": k, "n_runs": v}
                     for k, v in drops.items()], key=lambda d: -d["n_runs"])
    fams = {}
    for r in full:
        f = r.get("declared_family") or "ABSENT"
        fams.setdefault(f, {"n": 0, "survived_all": 0})
        fams[f]["n"] += 1
        if r["row"].get("survived_all"):
            fams[f]["survived_all"] += 1
    return {"n_rows": len(rows), "n_harvested_rows": n, "funnel": funnel,
            "dropoff_attribution_ranked": ranked,
            "yield_per_100_fresh_by_family": fams}


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
    elif mode == "harvest":
        sys.exit(harvest())
    else:
        print("modes: preflight | submit | answer | poll [budget_min] | harvest")
        sys.exit(1)
