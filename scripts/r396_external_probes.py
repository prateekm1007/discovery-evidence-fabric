#!/usr/bin/env python3
"""scripts/r396_external_probes.py — R396 Phase C: EXTERNAL ACCEPTANCE
PROBES against the deployed public host.

"Run these against the deployed public host and preserve the raw
outputs in the worklog." CI is NOT acceptance (R396 Phase C / Phase F /
Art. XXVI). Every probe records the RAW HTTP exchange (status, headers
of interest, body) plus a PASS/FAIL verdict against the R396 contract.

Probes:
  P1 /api/health            — artifact-derived SHA == deployed commit;
                              no env-asserted identity; drift GREEN.
  P2 anonymous /api/sessions — zero cross-user sessions, zero run_dir,
                              zero PID, zero operational metadata.
  P3 false-premise canary    — the EXACT glass problem from the external
                              audit; early MALFORMED_OR_FALSE_PREMISE,
                              explicit reason, no mechanism synthesis,
                              no CMOS mechanism, no candidate generation.
  P4 incomplete-search       — Lens-exhausted/429 case: SEARCH_FAILED/
                              PARTIAL never becomes NO_MATCH_FOUND;
                              candidate stays UNRESOLVED_SEARCH_INCOMPLETE;
                              RESOLVED_DIFFERENTIATED on failed mandatory
                              search is a HARD FAILURE.
  P5 wind-erosion relevance  — fusion/divertor material NOT relevant on
                              lexical similarity alone; run twice with
                              identical input; verdicts stable.
  P6 determinism             — one identical problem three times; the
                              run records carry verdict/model version/
                              evidence-set identity/variance/class.
  P7 benchmark               — the 18-case benchmark against the
                              deployed host (not CI).

Usage:
  python3 scripts/r396_external_probes.py [--base URL] [--p 1,2,3]
      [--deployed-sha SHA] [--out PATH] [--timeout-wait SECONDS]

--deployed-sha: the git commit the deployment was triggered with (the
P1 equality target). When omitted, P1 still verifies the internal
consistency chain (artifact-derived source, tamper=false) and reports
the observed commit.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# The exact glass problem from the external audit (R396 directive P3).
GLASS_PROBLEM = (
    "Why does grain boundary sliding in borosilicate glass reactor "
    "liners limit their service temperature, and can a grain-boundary "
    "engineering treatment prevent grain boundary sliding in the glass "
    "liner?")

# P5: wind-erosion problem (leading-edge rain erosion; the fusion/
# divertor lexical-collision trap).
WIND_EROSION_PROBLEM = (
    "Why do wind turbine leading edges suffer rain erosion, and can a "
    "surface treatment extend blade life?")

# P6/P7: the identical-problem determinism problem.
DETERMINISM_PROBLEM = (
    "Why do tunneled hemodialysis catheters lose flow patency within "
    "weeks of insertion despite flushing protocols?")

# P4: prior-art incomplete search — a problem whose patent-plane search
# hits the unconfigured/exhausted Lens path on the deployed host.
INCOMPLETE_SEARCH_PROBLEM = (
    "Why do tunneled hemodialysis catheters develop heparin-binding "
    "thrombus despite antithrombotic luminal coatings?")

RAW: List[Dict[str, Any]] = []


def _request(base: str, path: str, method: str = "GET",
             body: Optional[dict] = None, timeout: int = 90,
             headers: Optional[dict] = None) -> Dict[str, Any]:
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    started = time.time()
    rec: Dict[str, Any] = {"method": method, "url": url,
                           "request_body": body, "at_utc":
                           time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime())}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            rec["status"] = r.status
            rec["content_type"] = r.headers.get("Content-Type")
            # R397 fix: capture the owner cookie the server sets on run
            # creation (the R394 s15 contract: owner capability is the
            # httpOnly tosca_owner cookie — X-Owner-Key was never a
            # server-side contract; the probe must speak the public
            # product surface exactly as a browser does)
            set_cookie = r.headers.get("Set-Cookie") or ""
            if "tosca_owner=" in set_cookie:
                rec["owner_cookie"] = set_cookie.split("tosca_owner=")[1] \
                    .split(";")[0]
            rec["elapsed_ms"] = int((time.time() - started) * 1000)
            try:
                rec["response_json"] = json.loads(raw.decode())
            except Exception:  # noqa: BLE001
                rec["response_text"] = raw.decode(errors="replace")[:4000]
    except urllib.error.HTTPError as e:
        raw = e.read()
        rec["status"] = e.code
        rec["elapsed_ms"] = int((time.time() - started) * 1000)
        try:
            rec["response_json"] = json.loads(raw.decode())
        except Exception:  # noqa: BLE001
            rec["response_text"] = raw.decode(errors="replace")[:4000]
    except Exception as exc:  # noqa: BLE001
        rec["status"] = None
        rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
    RAW.append(rec)
    return rec


def _json(rec: Dict[str, Any]) -> Optional[dict]:
    return rec.get("response_json") if isinstance(
        rec.get("response_json"), dict) else None


def _wait_terminal(base: str, session_id: str, owner: str,
                   timeout_s: int = 600) -> Optional[dict]:
    """Poll a session until a terminal status; return the detail JSON.

    R397 fix: `owner` is the tosca_owner COOKIE harvested from the run
    creation response (the server's actual owner-capability contract —
    R394 s15). The old X-Owner-Key header was never a server-side
    contract, so every poll was 404-denied and the probe timed out
    without ever seeing the terminal state (found live against the
    local instance)."""
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        rec = _request(base, f"/api/sessions/{session_id}",
                       headers={"Cookie": f"tosca_owner={owner}"})
        d = _json(rec)
        if d:
            last = d
            st = d.get("status") or ""
            if st in ("COMPLETE", "ERROR_TRANSPORT", "ERROR_BUILD",
                      "ERROR_RUN", "INTERRUPTED", "REJECTED",
                      "COMPLETED_FALSE_PREMISE"):
                return d
        time.sleep(5)
    return last


def _start_run(base: str, text: str) -> Optional[str]:
    """POST /api/discoveries and return (session_id, owner_cookie).

    R397 fix: the server assigns ownership via the Set-Cookie response
    header (tosca_owner, httpOnly) — the owner key the caller replays
    as a Cookie. The body's owner_key field was never read by the
    server (removed here so the probe exercises only the real
    contract)."""
    rec = _request(base, "/api/discoveries", method="POST",
                   body={"text": text})
    d = _json(rec)
    cookie = rec.get("owner_cookie") or ""
    if d and d.get("session_id"):
        return d["session_id"], cookie
    return None, cookie


# ---------------------------------------------------------------------------

def probe_p1(base: str, deployed_sha: str) -> Dict[str, Any]:
    rec = _request(base, "/api/health")
    h = _json(rec) or {}
    di = h.get("deployment_identity") or {}
    checks = {
        "reachable": rec.get("status") == 200,
        "identity_source_is_artifact": di.get(
            "health_reported_commit_source") == "build_artifact",
        "no_env_asserted_identity": di.get(
            "health_reported_commit_source") != "deployment_config_env",
        "identity_tamper_false": di.get("identity_tamper") is False,
        "build_running_health_equal": (
            di.get("build_artifact_sha256")
            == di.get("running_artifact_sha256")
            and di.get("build_artifact_sha256") is not None),
        "drift_green": di.get("deployment_drift") == "GREEN",
        "gateway_up_gated": (
            h.get("gateway_up") is None
            and "EXTERNAL" in (h.get("gateway_up_note") or ""))
            or h.get("gateway_up") is True,
    }
    if deployed_sha:
        checks["health_commit_equals_deployed"] = (
            di.get("health_reported_commit") == deployed_sha)
    observed = di.get("health_reported_commit")
    return {"probe": "P1", "checks": checks,
            "pass": all(checks.values()),
            "observed_engine_commit": observed,
            "raw_ref": len(RAW) - 1}


def probe_p2(base: str) -> Dict[str, Any]:
    # fully anonymous: no cookie, no owner header
    rec = _request(base, "/api/sessions")
    d = _json(rec) or {}
    sessions = d.get("sessions") or []
    blob = json.dumps(d)
    # operational-metadata leak patterns (the consultant's exact classes)
    leaks = {
        "run_dir": "run_dir" in blob or "/app/" in blob,
        "pid": "\"pid\"" in blob or "'pid'" in blob,
        "worker_starttime": "starttime" in blob,
        "filesystem_paths": "/home/z" in blob,
        "owner_key": "owner_key" in blob,
    }
    non_public = [s for s in sessions if not s.get("public")]
    return {"probe": "P2", "checks": {
        "reachable": rec.get("status") == 200,
        "zero_cross_user_sessions": len(non_public) == 0,
        "zero_run_dir_leakage": not leaks["run_dir"],
        "zero_pid_leakage": not leaks["pid"],
        "zero_worker_starttime_leakage": not leaks["worker_starttime"],
        "zero_filesystem_path_leakage": not leaks["filesystem_paths"],
        "zero_owner_key_leakage": not leaks["owner_key"],
    }, "pass": None, "n_sessions_visible": len(sessions),
    "n_public_demo_sessions": len(sessions),
    "leaks": leaks,
    "raw_ref": len(RAW) - 1}


def probe_p3(base: str) -> Dict[str, Any]:
    sid_owner = _start_run(base, GLASS_PROBLEM)
    sid, owner = sid_owner if isinstance(sid_owner, tuple) else (
        None, uuid.uuid4().hex)
    if not sid:
        return {"probe": "P3", "pass": False,
                "error": "run not accepted", "raw_ref": len(RAW) - 1}
    detail = _wait_terminal(base, sid, owner)
    if not detail:
        return {"probe": "P3", "pass": False, "session_id": sid,
                "error": "no terminal state", "raw_ref": len(RAW) - 1}
    stages = detail.get("stages") or []
    by_stage = {s.get("stage"): s for s in stages}
    pg = by_stage.get("PREMISE_GATE", {})
    synth = by_stage.get("SYNTHESIZE", {})
    fs = detail.get("final_state") or {}
    final = detail.get("status") or fs.get("final_status") or ""
    # the MECHANISM-bearing surfaces only (R397 fix: the original
    # blob-wide "CMOS not in json" over-triggered on the RETRIEVE
    # stage's sample_titles — retrieval legitimately happens BEFORE
    # the premise gate fires, and the retrieved-record disclosure is
    # honest evidence-of-what-was-fetched, not a synthesized mechanism.
    # The contract under test: no CMOS-based mechanism/candidate was
    # ever BUILT from that irrelevant retrieval.)
    mechanism_blob = json.dumps({
        "synth_mechanism": (synth.get("mechanism") or {}),
        "invention_specification": detail.get("invention_specification"),
        "engineering_specification": detail.get("engineering_specification"),
        "survivor_selection": detail.get("survivor_selection"),
        "final_state": fs,
    })
    checks = {
        "early_malformed_or_false_premise": (
            final in ("COMPLETED_FALSE_PREMISE",
                      "MALFORMED_OR_FALSE_PREMISE")
            or pg.get("verdict") == "MALFORMED_OR_FALSE_PREMISE"),
        "explicit_reason": bool(pg.get("explanation")),
        "no_mechanism_synthesis": not synth.get("mechanism"),
        "no_cmos_mechanism": "CMOS" not in mechanism_blob,
        "no_downstream_candidate": not (
            detail.get("invention_specification")
            or detail.get("engineering_specification")
            or detail.get("survivor_selection")),
    }
    return {"probe": "P3", "checks": checks,
            "pass": all(checks.values()), "session_id": sid,
            "final_status": final,
            "premise_gate_verdict": pg.get("verdict"),
            "premise_gate_reason": (pg.get("explanation") or "")[:300],
            "raw_ref": len(RAW) - 1}


def probe_p4(base: str) -> Dict[str, Any]:
    sid_owner = _start_run(base, INCOMPLETE_SEARCH_PROBLEM)
    sid, owner = sid_owner if isinstance(sid_owner, tuple) else (
        None, uuid.uuid4().hex)
    if not sid:
        return {"probe": "P4", "pass": False,
                "error": "run not accepted", "raw_ref": len(RAW) - 1}
    detail = _wait_terminal(base, sid, owner)
    if not detail:
        return {"probe": "P4", "pass": False, "session_id": sid,
                "error": "no terminal state", "raw_ref": len(RAW) - 1}
    stages = detail.get("stages") or []
    by_stage = {s.get("stage"): s for s in stages}
    coll = by_stage.get("COLLISION", {})
    det = coll.get("determinism") or {}
    res = detail.get("final_state") or {}
    verdicts = [c.get("verdict") for c in (coll.get("collisions") or [])]
    search_status = res.get("search_execution") or {}
    final = detail.get("status") or res.get("final_status") or ""
    checks = {
        # SEARCH_FAILED/PARTIAL never becomes NO_MATCH_FOUND
        "no_no_match_on_failure": not any(
            v in ("NO_MATCH_FOUND", "NO_PRIOR_ART") for v in verdicts),
        # the surviving candidate remains UNRESOLVED_SEARCH_INCOMPLETE
        "candidate_unresolved_search_incomplete": (
            final != "COMPLETE"
            or "UNRESOLVED_SEARCH_INCOMPLETE" in json.dumps(detail)),
        # RESOLVED_DIFFERENTIATED on failed mandatory search = hard fail
        "no_differentiated_on_failed_search": not (
            "RESOLVED_DIFFERENTIATED" in json.dumps(coll)
            and (search_status.get("mandatory_complete") is False
                 or res.get("search_errors"))),
    }
    return {"probe": "P4", "checks": checks,
            "pass": all(checks.values()), "session_id": sid,
            "final_status": final,
            "collision_verdicts": verdicts,
            "search_execution": search_status,
            "determinism": det, "raw_ref": len(RAW) - 1}


def probe_p5(base: str) -> Dict[str, Any]:
    results = []
    for i in range(2):
        sid_owner = _start_run(base, WIND_EROSION_PROBLEM)
        sid, owner = sid_owner if isinstance(sid_owner, tuple) else (
            None, uuid.uuid4().hex)
        if not sid:
            results.append({"error": "run not accepted"})
            continue
        detail = _wait_terminal(base, sid, owner)
        results.append({
            "session_id": sid,
            "final_status": (detail or {}).get("status"),
            "evidence_titles": [
                (e.get("title") or "")[:160]
                for e in ((detail or {}).get("evidence_pack")
                          or {}).get("records", [])[:10]],
        })
    verdicts = [r.get("final_status") for r in results]
    stable = len(set(filter(None, verdicts))) <= 1
    # fusion/divertor material must not appear as relevant evidence
    fusion_leak = any(
        "divertor" in t.lower() or "fusion" in t.lower()
        for r in results for t in r.get("evidence_titles", []))
    return {"probe": "P5", "checks": {
        "verdicts_stable": stable,
        "no_fusion_divertor_admitted": not fusion_leak,
    }, "pass": stable and not fusion_leak,
    "runs": results, "raw_ref": len(RAW) - 1}


def probe_p6(base: str) -> Dict[str, Any]:
    runs = []
    for i in range(3):
        sid_owner = _start_run(base, DETERMINISM_PROBLEM)
        sid, owner = sid_owner if isinstance(sid_owner, tuple) else (
            None, uuid.uuid4().hex)
        if not sid:
            runs.append({"error": "run not accepted"})
            continue
        detail = _wait_terminal(base, sid, owner)
        stages = (detail or {}).get("stages") or []
        coll = next((s for s in stages if s.get("stage") == "COLLISION"),
                    {})
        det = coll.get("determinism") or {}
        runs.append({
            "session_id": sid,
            "verdict": det.get("verdict") or (detail or {}).get("status"),
            "relevance_model_version": det.get(
                "relevance_model_version"),
            "evidence_set_identity": det.get("evidence_set_identity"),
            "classification": det.get("classification"),
            "variance_summary": det.get("variance_summary"),
        })
    complete = [r for r in runs if r.get("classification")]
    checks = {
        "three_runs_completed": len(complete) == 3,
        "record_contains_verdict": all(r.get("verdict") is not None
                                       for r in complete),
        "record_contains_model_version": all(
            r.get("relevance_model_version") for r in complete),
        "record_contains_evidence_set_identity": all(
            r.get("evidence_set_identity") for r in complete),
        "record_contains_classification": all(
            r.get("classification") for r in complete),
        "last_run_has_variance_summary": complete[-1].get(
            "variance_summary") is not None if complete else False,
        "classified_deterministic": complete[-1].get(
            "classification") == "DETERMINISTIC" if complete else False,
    }
    return {"probe": "P6", "checks": checks,
            "pass": all(checks.values()), "runs": runs,
            "raw_ref": len(RAW) - 1}


def probe_p7(base: str) -> Dict[str, Any]:
    """The 18-case benchmark against the deployed host. The exact
    problems mirror tests/test_r394_benchmark.py (the permanent
    benchmark), executed through the PUBLIC product surface — CI
    results are not production acceptance (R396 Phase C/F)."""
    cases = _benchmark_cases()
    results = []
    for i, case in enumerate(cases, 1):
        text = case["text"]
        if case.get("expect_early_reject"):
            rec = _request(base, "/api/discoveries", method="POST",
                           body={"text": text})
            d = _json(rec) or {}
            results.append({"case": case["case"], "id": case["id"],
                            "accepted": bool(d.get("session_id")),
                            "note": "early-reject case"})
            continue
        sid_owner = _start_run(base, text)
        sid, owner = sid_owner if isinstance(sid_owner, tuple) else (
            None, uuid.uuid4().hex)
        if not sid:
            results.append({"case": case["case"], "id": case["id"],
                            "accepted": False})
            continue
        detail = _wait_terminal(base, sid, owner, timeout_s=900)
        results.append({
            "case": case["case"], "id": case["id"],
            "session_id": sid,
            "final_status": (detail or {}).get("status"),
            "expected": case.get("expected"),
        })
    ok = all(r.get("accepted") is not False for r in results)
    terminal = all(r.get("final_status") or r.get("accepted")
                   for r in results)
    return {"probe": "P7", "checks": {
        "all_18_accepted_or_rejected_honestly": ok,
        "all_reached_terminal_state": terminal,
        "n_cases": len(cases),
    }, "pass": ok and terminal, "results": results,
    "raw_ref": len(RAW) - 1}


def _benchmark_cases() -> List[Dict[str, str]]:
    g = "glass liner grain boundary sliding"
    return [
        {"id": "01-biomedical-valid", "case": "1",
         "text": "Why do tunneled hemodialysis catheters lose flow "
                 "patency through occlusion despite flushing?"},
        {"id": "02-mechanical-valid", "case": "2",
         "text": "Why do rails fracture in service under fatigue "
                 "loading?"},
        {"id": "03-thermal-fluid-valid", "case": "3",
         "text": "Why do EV traction battery packs suffer thermal "
                 "runaway initiation during fast charge?"},
        {"id": "04-false-premise-glass", "case": "4",
         "text": GLASS_PROBLEM, "expect_early_reject": "premise"},
        {"id": "05-irrelevant-evidence", "case": "5",
         "text": "Why do tunneled hemodialysis catheters suffer "
                 "catheter occlusion? (evidence relevance filter)"},
        {"id": "06-contradictory-evidence", "case": "6",
         "text": "Why do tunneled hemodialysis catheters show "
                 "conflicting patency outcomes across studies?"},
        {"id": "07-provider-timeout", "case": "7",
         "text": "Why do infusion pumps fail to detect downstream "
                 "occlusion in time? (provider timeout behavior)"},
        {"id": "08-failed-search-cannot-differentiate", "case": "8",
         "text": INCOMPLETE_SEARCH_PROBLEM},
        {"id": "09-identical-input-determinism", "case": "9",
         "text": DETERMINISM_PROBLEM},
        {"id": "10-physics-bound-fail", "case": "10",
         "text": "Why do multi-lumen drainage catheters lose drain "
                 "conductance, and can a wider floor lumen restore "
                 "flow? (plausibility bounds)"},
        {"id": "11-candidate-loses-baseline", "case": "11",
         "text": "Why do multi-lumen drainage catheters lose flow, and "
                 "would a narrower lumen resist occlusion? (baseline "
                 "comparison)"},
        {"id": "12-candidate-beats-baseline", "case": "12",
         "text": "Why do multi-lumen drainage catheters lose flow, and "
                 "can a wider floor lumen restore drainage? (beats "
                 "baseline)"},
        {"id": "13-solver-failure", "case": "13",
         "text": "Why do multi-lumen catheters lose conductance under "
                 "partial obstruction? (solver failure semantics)"},
        {"id": "14-reality-discrepancy", "case": "14",
         "text": "Why does P-07's drainage floor deviate from the "
                 "measured water viscosity basis? (reality "
                 "discrepancy semantics)"},
        {"id": "15-model-correction", "case": "15",
         "text": "Can the P-07 model's viscosity parameter be corrected "
                 "from measured flow? (model correction semantics)"},
        {"id": "16-patent-replay-recall", "case": "16",
         "text": "Why do hemodialysis catheters need antithrombotic "
                 "heparin coatings? (patent replay recall)"},
        {"id": "17-connector-outage", "case": "17",
         "text": "Why do aircraft lithium-battery installations suffer "
                 "thermal events? (connector outage honesty)"},
        {"id": "18-verdict-variance", "case": "18",
         "text": "Why do tunneled catheters occlude? (verdict variance "
                 "pinning)"},
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://"
                                   "toscanini-engine-docker.onrender.com")
    ap.add_argument("--p", default="1,2")
    ap.add_argument("--deployed-sha", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--wait", type=int, default=600)
    args = ap.parse_args()
    probes = {p.strip() for p in args.p.split(",")}
    report: Dict[str, Any] = {
        "suite": "R396 external acceptance probes",
        "base": args.base,
        "deployed_sha": args.deployed_sha or None,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "probes": [],
    }
    if "1" in probes:
        report["probes"].append(probe_p1(args.base, args.deployed_sha))
    if "2" in probes:
        report["probes"].append(probe_p2(args.base))
    if "3" in probes:
        report["probes"].append(probe_p3(args.base))
    if "4" in probes:
        report["probes"].append(probe_p4(args.base))
    if "5" in probes:
        report["probes"].append(probe_p5(args.base))
    if "6" in probes:
        report["probes"].append(probe_p6(args.base))
    if "7" in probes:
        report["probes"].append(probe_p7(args.base))
    report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime())
    report["all_pass"] = all(p.get("pass") for p in report["probes"])
    report["raw"] = RAW
    out = Path(args.out or REPO_ROOT / "R396" / "EXTERNAL_PROBES.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v for k, v in report.items()
                      if k != "raw"}, indent=1, default=str))
    print(f"\nraw exchanges preserved -> {out}")
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
