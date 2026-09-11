#!/usr/bin/env python3
"""scripts/r446_production_verify.py — R446-C1 Task 3: fresh production
discovery across THREE materially different problem classes.

The R445 production proof ran the F1 repair case (bench-p03, thermal).
This driver proves the discovery path is not accidentally coupled to
that exact case by running THREE fresh production samples:

  bench-p11-spindle-thermal-drift  (physical/thermal — precision
                                    machining spindle thermal drift)
  bench-p04-pump-cavitation        (mechanical — centrifugal pump
                                    impeller cavitation)
  bench-x01-rl-reward-hacking      (software/ML — PPO policy reward
                                    hacking in robotic pick-and-place)

For EACH run the driver records the full chain (the directive's list):
  problem -> evidence -> candidate -> attack -> evolution/diagnosis ->
  technical state -> CIO -> package state
plus the user-visible terminal state, the canonical completion check
(run_manifest.json IS on the server's run dir — the completion axis is
read through the session's own status + the result endpoint), and the
FULL CIO HTTP body persisted verbatim (the Task 1 production-shaped
evidence: the extractor's typed verdict runs on the REAL bytes).

Slice-resumable (the sandbox reaps processes between invocations): each
case's session id + owner cookie persist to R446/PRODUCTION_SESSION.json
so a re-invocation RESUMES polling the SAME run instead of submitting a
new one (the cookie is presented exactly as the original browser session
would present it — the user path, not an operator backdoor).

The acceptance is COVERAGE + TRUTHFUL STATE, not forced inventions: a
run that honestly ends INVENTION_REQUIRES_EXPERIMENT or NO_DEFENSIBLE_
INVENTION or RUN_BLOCKED is recorded exactly as the product states it.

Usage:
  python3 scripts/r446_production_verify.py   (re-invoke to resume)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

import r444_production_verify as pv  # noqa: E402  (the verified user-path impl)
from r446_cio_extraction import summarize_for_record  # noqa: E402

OUT = REPO_ROOT / "R446" / "PRODUCTION_RUNS.json"
RUNS_DIR = REPO_ROOT / "R446" / "PRODUCTION_RUNS"
SESSION = REPO_ROOT / "R446" / "PRODUCTION_SESSION.json"

CASES = [
    "bench-p11-spindle-thermal-drift",
    "bench-p04-pump-cavitation",
    "bench-x01-rl-reward-hacking",
]

SLICE_POLL_S = 540


def _log(msg: str) -> None:
    print(f"[r446-prod] {msg}", flush=True)


def _resume() -> Optional[Dict[str, Any]]:
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            return None
    return None


def _poll_slice(session_id: str, cookie: Optional[str],
                deadline_s: float) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < deadline_s:
        r = pv._req(f"/api/run/{session_id}/result", timeout=60,
                    cookie=cookie)
        last = r
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            status = str(body.get("status") or "").upper()
            if status in ("COMPLETE", "FAILED", "ERROR", "DONE",
                          "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
                          "ERROR_RUN", "ERROR_BUILD"):
                return r
        time.sleep(pv.POLL_INTERVAL_S)
    return {"http_status": "SLICE_DEADLINE", "last": last}


# ---------------------------------------------------------------------------
# the full-chain projection (the directive's per-run record)
# ---------------------------------------------------------------------------
def _chain_record(problem: Dict[str, Any], result_body: Dict[str, Any],
                  cio_body: Any, cio_resp: Dict[str, Any],
                  model_resp: Dict[str, Any],
                  session_id: str) -> Dict[str, Any]:
    """problem -> evidence -> candidate -> attack -> evolution ->
    technical state -> CIO -> package state, projected from the run's
    OWN recorded fields (the result endpoint's session detail + the
    CIO's own body — never re-derived, Art. X)."""
    rs = result_body.get("run_state") or {}
    inv = result_body.get("invention_specification") or {}
    eng = result_body.get("engineering_specification") or {}
    dex = result_body.get("decisive_experiment") or {}
    gens = rs.get("generations") or []

    def _unwrap_v(field: Any) -> Any:
        if isinstance(field, dict) and "value" in field and set(
                field.keys()) <= {"value", "epistemic_class",
                                  "origin_stage", "evidence_ids", "note",
                                  "source_span", "provenance"}:
            return field.get("value")
        return field

    chain: Dict[str, Any] = {
        "problem": {
            "problem_id": problem["problem_id"],
            "problem_class": problem.get("domain"),
            "submitted_text": pv._problem_text(problem),
        },
        "evidence": {
            "state": (rs.get("evidence_state") or {}),
            "record_count": ((rs.get("evidence_state") or {}).get(
                "record_count")),
        },
        "candidate": {
            "mechanism_state": rs.get("mechanism_state"),
            "gen1_mechanism": (_unwrap_v(inv.get("mechanism"))
                               if isinstance(inv.get("mechanism"), dict)
                               else inv.get("mechanism")),
            "invention_id": inv.get("invention_id")
            if not isinstance(inv.get("invention_id"), dict)
            else _unwrap_v(inv.get("invention_id")),
        },
        "attack": {
            "state": rs.get("attack_state"),
            "note": ("the abstain/escalate gate is IN FORCE: a raw KILL "
                     "travels as ESCALATED_OBJECTION, never terminal "
                     "authority (the calibration state is "
                     "NOT_CALIBRATED)"),
        },
        "evolution_diagnosis": {
            "state": rs.get("evolution_state"),
            "n_generations": len(gens),
            "generations": [
                {"gen": g.get("gen"),
                 "maturity": g.get("maturity"),
                 "has_causal_delta": bool(g.get("causal_delta"))}
                for g in gens[:6]],
            "outcome": rs.get("outcome"),
            "outcome_label": rs.get("outcome_label"),
        },
        "technical_state": {
            "engineering_specification_present": bool(eng),
            "canonical_domain": ((eng.get("why_this_domain") or {}).get(
                "canonical_family") or (eng.get("why_this_domain") or {})
                .get("domain")),
            "n_parameters": len(eng.get("parameters") or [])
            if isinstance(eng.get("parameters"), list) else None,
            "decisive_experiment_present": bool(dex),
            "falsification_contract_present": bool(
                (dex.get("falsification_contract") or {})
                if isinstance(dex, dict) else None),
        },
        "cio": summarize_for_record(
            cio_resp.get("http_status"), cio_body),
        "package_state": {
            "downloads": (cio_body or {}).get("downloads")
            if isinstance(cio_body, dict) else None,
            "package_state": rs.get("package_state"),
            "bridge_outcome": ((cio_body or {}).get("geometry") or {}
                               ).get("bridge_outcome")
            if isinstance(cio_body, dict) else None,
        },
        "glb_http": model_resp.get("http_status"),
        "user_visible_state": {
            "status": result_body.get("status"),
            "final_status": result_body.get("final_status"),
        },
        "run_id": session_id,
    }
    return chain


def _run_case(problem: Dict[str, Any], report: Dict[str, Any],
              completed: List[str]) -> Optional[Dict[str, Any]]:
    case_id = problem["problem_id"]
    if case_id in completed:
        _log(f"{case_id}: already recorded (resume)")
        return None

    sess = _resume()
    if sess and sess.get("case") == case_id and sess.get("session_id") \
            and sess.get("cookie"):
        session_id = sess["session_id"]
        cookie = sess["cookie"]
        submitted = sess.get("submit_http")
        _log(f"{case_id}: resuming session {session_id} "
             f"(persisted cookie)")
    else:
        text = pv._problem_text(problem)
        _log(f"{case_id}: submitting ({len(text)} chars)")
        create = pv._req("/api/run", {"text": text}, timeout=120)
        if create.get("http_status") not in (200, 201, 202):
            return {"case_id": case_id, "outcome": "SUBMIT_FAILED",
                    "submit": create}
        body = create.get("body") or {}
        session_id = body.get("session_id") or body.get("id") or \
            body.get("run_id")
        if not session_id:
            return {"case_id": case_id, "outcome": "NO_SESSION_ID",
                    "submit": create}
        cookie = create.get("set_cookie")
        submitted = create.get("http_status")
        SESSION.write_text(json.dumps({
            "case": case_id, "session_id": session_id,
            "cookie": cookie, "submit_http": submitted}, indent=1))
        _log(f"{case_id}: session {session_id} — polling "
             f"(cookie {'set' if cookie else 'ABSENT'})")

    result = _poll_slice(session_id, cookie, SLICE_POLL_S)
    if result.get("http_status") == "SLICE_DEADLINE":
        _log(f"{case_id}: slice deadline — re-invoke to resume")
        return None  # the caller re-invokes; state is on disk

    cio_resp = pv._req(f"/api/run/{session_id}/cio", timeout=60,
                       cookie=cookie)
    model_resp = pv._req(f"/api/run/{session_id}/model", timeout=120,
                         cookie=cookie)
    result_body = (result.get("body") or {}) \
        if result.get("http_status") == 200 else {}

    # the FULL CIO body persisted verbatim (the Task 1 evidence + the
    # owner's inspectable record)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    cio_path = RUNS_DIR / f"{session_id}_cio.json"
    cio_path.write_text(json.dumps(cio_resp.get("body"), indent=1,
                                   default=str))

    rec = _chain_record(problem, result_body, cio_resp.get("body"),
                        cio_resp, model_resp, session_id)
    rec["case_id"] = case_id
    rec["outcome"] = ("RUN_COMPLETED"
                      if result.get("http_status") == 200
                      else f"POLL_{result.get('http_status')}")
    rec["cio_body_persisted"] = str(cio_path.relative_to(REPO_ROOT))
    _log(f"{case_id}: {rec['outcome']} | user-visible: "
         f"{rec['user_visible_state']} | outcome: "
         f"{rec['evolution_diagnosis'].get('outcome')} | CIO: "
         f"{rec['cio']['cio_extraction_state']}")
    return rec


def main() -> int:
    frozen = json.loads(
        (REPO_ROOT / "R401-WC2" / "BENCHMARK" /
         "FROZEN_BENCHMARK.json").read_text())
    extension = json.loads(
        (REPO_ROOT / "R444" / "BENCHMARK_EXTENSION" /
         "FROZEN_EXTENSION.json").read_text())
    full = {p["problem_id"]: p
            for p in frozen["problems"] + extension["problems"]}

    report: Dict[str, Any] = {}
    if OUT.exists():
        try:
            report = json.loads(OUT.read_text())
        except Exception:  # noqa: BLE001
            report = {}
    completed = [r.get("case_id") for r in report.get("runs", [])
                 if r.get("outcome") == "RUN_COMPLETED"]

    if not report:
        report = {
            "report_version": "r446-production-verify/1.0.0",
            "base_url": pv.BASE,
            "purpose": (
                "fresh production discovery across three materially "
                "different problem classes (thermal / mechanical / "
                "software-ML) — decoupling proof from the R445 F1 "
                "repair case; acceptance is coverage + truthful state, "
                "never forced inventions"),
            "cases": CASES,
            "version_check": pv._req("/api/version", timeout=120),
            "runs": [],
        }

    for case_id in CASES:
        problem = full.get(case_id)
        if problem is None:
            _log(f"{case_id}: not found in frozen corpora")
            continue
        rec = _run_case(problem, report, completed)
        if rec is None:
            continue  # slice deadline: re-invoke
        report.setdefault("runs", []).append(rec)
        OUT.write_text(json.dumps(report, indent=1, default=str))
        SESSION.unlink(missing_ok=True)

    runs = report.get("runs", [])
    report["n_runs"] = len(runs)
    report["n_completed"] = sum(
        1 for r in runs if r.get("outcome") == "RUN_COMPLETED")
    report["classes_covered"] = sorted({
        (r.get("problem") or {}).get("problem_class")
        for r in runs if r.get("outcome") == "RUN_COMPLETED"})
    OUT.write_text(json.dumps(report, indent=1, default=str))
    SESSION.unlink(missing_ok=True)
    _log(f"report -> {OUT} ({report['n_completed']}/{report['n_runs']} "
         f"completed, classes: {report.get('classes_covered')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
