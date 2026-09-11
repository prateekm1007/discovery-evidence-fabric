#!/usr/bin/env python3
"""scripts/r445_production_verify.py — R445-E: the FRESH PRODUCTION
VERIFICATION at the deployed SHA.

Runs ONE benchmark problem through the REAL production user path (the
deployed Render service) exactly as the R444 driver does — POST /api/run
{ text } -> poll GET /api/run/{id}/result -> the CIO -> the model ->
the package release decision — and records the typed outcomes to
R445/PRODUCTION_RUNS.json.

Slice-resumable (the sandbox reaps processes between tool invocations):
the session id + the owner cookie persist to R445/PRODUCTION_SESSION.json
after the POST, so a re-invocation RESUMES polling the SAME run instead
of submitting a new one (the cookie is presented exactly as the original
browser session would present it — the user path, not an operator
backdoor; persisting it locally is transport bookkeeping, never engine
state).

Case selection: bench-p03-phe-biofouling (the R444 F1 case — the
canonical-domain fix's flagship: in R444 production the package was
blocked by the domain-vocabulary divergence; at the R445 SHA the same
problem's domain identity must flow coherently to the package). The
R445-A/B/D/C code paths (canonical domain ladder, package compiler,
gates) all execute in the deployed engine on this one run.

Usage:
  python3 scripts/r445_production_verify.py   (re-invoke to resume)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

# reuse the R444 verified user-path implementation verbatim
import r444_production_verify as pv  # noqa: E402

OUT = REPO_ROOT / "R445" / "PRODUCTION_RUNS.json"
SESSION = REPO_ROOT / "R445" / "PRODUCTION_SESSION.json"
CASE = "bench-p03-phe-biofouling"

# one slice's polling budget (the caller re-invokes to continue)
SLICE_POLL_S = 540


def _log(msg: str) -> None:
    print(f"[r445-prod] {msg}", flush=True)


def _resume() -> Optional[Dict[str, Any]]:
    if not SESSION.exists():
        return None
    try:
        return json.loads(SESSION.read_text())
    except Exception:  # noqa: BLE001
        return None


def _poll_slice(session_id: str, cookie: Optional[str],
                deadline_s: float) -> Dict[str, Any]:
    """Poll until terminal state, slice deadline, or pv timeout."""
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < deadline_s:
        r = pv._req(f"/api/run/{session_id}/result", timeout=60,
                    cookie=cookie)
        last = r
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            status = str(body.get("status") or "").upper()
            if status in ("COMPLETE", "FAILED", "ERROR", "DONE"):
                return r
        time.sleep(pv.POLL_INTERVAL_S)
    return {"http_status": "SLICE_DEADLINE", "last": last}


def main() -> int:
    frozen = json.loads(
        (REPO_ROOT / "R401-WC2" / "BENCHMARK" /
         "FROZEN_BENCHMARK.json").read_text())
    problem = next(
        (p for p in frozen["problems"] if p["problem_id"] == CASE), None)
    if problem is None:
        _log(f"case {CASE} not found in frozen benchmark")
        return 2

    sess = _resume()
    if sess and sess.get("session_id") and sess.get("cookie"):
        session_id = sess["session_id"]
        cookie = sess["cookie"]
        _log(f"resuming session {session_id} (persisted cookie)")
        submitted = sess.get("submit_http")
    else:
        text = pv._problem_text(problem)
        _log(f"{CASE}: submitting ({len(text)} chars)")
        create = pv._req("/api/run", {"text": text}, timeout=120)
        if create.get("http_status") not in (200, 201, 202):
            OUT.write_text(json.dumps({
                "report_version": "r445-production-verify/1.0.0",
                "case": CASE, "submit": create,
                "outcome": "SUBMIT_FAILED"}, indent=1, default=str))
            return 1
        body = create.get("body") or {}
        session_id = body.get("session_id") or body.get("id") or \
            body.get("run_id")
        if not session_id:
            OUT.write_text(json.dumps({
                "report_version": "r445-production-verify/1.0.0",
                "case": CASE, "submit": create,
                "outcome": "NO_SESSION_ID"}, indent=1, default=str))
            return 1
        cookie = create.get("set_cookie")
        submitted = create.get("http_status")
        SESSION.write_text(json.dumps({
            "session_id": session_id, "cookie": cookie,
            "submit_http": submitted, "case": CASE}, indent=1))
        _log(f"{CASE}: session {session_id} — polling "
             f"(cookie {'set' if cookie else 'ABSENT'})")

    result = _poll_slice(session_id, cookie, SLICE_POLL_S)
    if result.get("http_status") == "SLICE_DEADLINE":
        _log("slice deadline — re-invoke to resume polling "
             "(session + cookie persisted)")
        return 3  # the caller re-invokes; state is on disk

    # terminal state reached: the artifact chain (same cookie — user path)
    cio = pv._req(f"/api/run/{session_id}/cio", timeout=60, cookie=cookie)
    model = pv._req(f"/api/run/{session_id}/model", timeout=120,
                    cookie=cookie)
    final_body = (result.get("body") or {}) \
        if result.get("http_status") == 200 else {}
    rec = {
        "problem_id": problem["problem_id"],
        "domain": problem["domain"],
        "run_id": session_id,
        "submit_http": submitted,
        "poll_http": result.get("http_status"),
        "user_visible_state": {
            "status": final_body.get("status"),
            "final_status": final_body.get("final_status")
            or (final_body.get("outcome") or {}).get("final_status"),
            "stage": final_body.get("stage"),
        },
        "cio_http": cio.get("http_status"),
        "cio_summary": (cio.get("body") or {}).get("summary")
        or {k: (cio.get("body") or {}).get(k) for k in
            ("mechanism", "technology_class", "n_components")},
        "glb_http": model.get("http_status"),
        "outcome": ("RUN_COMPLETED" if result.get("http_status") == 200
                    else "POLL_FAILED"),
    }
    report = {
        "report_version": "r445-production-verify/1.0.0",
        "base_url": pv.BASE,
        "deployed_sha_expected": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True).stdout.strip(),
        "case": CASE,
        "case_rationale": (
            "the R444 F1 case: at R444's SHA the production package was "
            "blocked by A-INTERNAL-DIVERGENT ['GENERIC_ARCHITECTURE', "
            "'thermal']; this run exercises the R445 canonical-domain "
            "fix end-to-end in the DEPLOYED engine (problem -> canonical "
            "domain -> mechanism -> engineering spec -> geometry -> CIO "
            "-> package)"),
        "version_check": pv._req("/api/version", timeout=120),
        "runs": [rec],
    }
    OUT.write_text(json.dumps(report, indent=1, default=str))
    SESSION.unlink(missing_ok=True)
    _log(f"results -> {OUT}")
    _log(f"outcome: {rec['outcome']} | user-visible final: "
         f"{rec['user_visible_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
