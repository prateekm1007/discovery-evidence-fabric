"""toscanini/run_state.py — R414: the canonical DiscoveryRun object.

Operator directive (product integration, sections 1, 4, 5, 18):
  Every legitimate user query creates a discovery RUN that progresses
  through explicit states; the frontend reads THIS state and never
  infers that an invention exists because a GLB exists. Every terminal
  run lands in exactly one of four outcomes:

    INVENTION_SURVIVED            credible candidate progressed toward a
                                  technology package
    INVENTION_REQUIRES_EXPERIMENT strong enough conceptually, decisive
                                  physical evidence missing
    NO_DEFENSIBLE_INVENTION        the territory was explored and
                                  nothing survived
    RUN_BLOCKED                    infrastructure/evidence/provider
                                  failure prevented a scientifically
                                  meaningful conclusion

Constitutional contract (Art. X, XXV, LXI, LXVIII):
  - The run directory's persisted artifacts are the AUTHORITY; this
    module only PROJECTS them (it invents nothing).
  - RUN_BLOCKED is reserved for infrastructure-class terminations — a
    scientific rejection is NO_DEFENSIBLE_INVENTION, never RUN_BLOCKED
    (Art. LXI: infrastructure failure is never scientific rejection,
    and the converse holds here too).
  - The outcome is derived from RECORDED fields only; absence of a
    field is never evidence (Art. XXV).
  - No quota pressure: an honest NO_DEFENSIBLE_INVENTION is a real
    result, never softened into a survivor (Art. LXVIII).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# The four terminal outcomes (directive §18) + the non-terminal PENDING
# ---------------------------------------------------------------------------
OUTCOME_PENDING = "PENDING"
OUTCOME_SURVIVED = "INVENTION_SURVIVED"
OUTCOME_REQUIRES_EXPERIMENT = "INVENTION_REQUIRES_EXPERIMENT"
OUTCOME_NO_DEFENSIBLE = "NO_DEFENSIBLE_INVENTION"
OUTCOME_RUN_BLOCKED = "RUN_BLOCKED"

OUTCOME_LABELS = {
    OUTCOME_PENDING: "Investigating",
    OUTCOME_SURVIVED: "Invention survived",
    OUTCOME_REQUIRES_EXPERIMENT: "Invention requires experiment",
    OUTCOME_NO_DEFENSIBLE: "No defensible invention survived this run",
    OUTCOME_RUN_BLOCKED: "Run blocked — infrastructure, not a verdict",
}

_RUNNING_STATUSES = ("PENDING", "BUILDING_PROBLEM", "RUNNING", "")
_BLOCKED_STATUSES = ("INTERRUPTED", "ERROR_TRANSPORT", "ERROR_BUILD",
                     "ERROR_RUN", "ERROR_STUCK")

# Engine stage -> product phase (directive §5: each UI state must
# correspond to a real backend stage). The canonical engine STAGE_ORDER
# is the authority; this map only groups it for display.
PHASES = [
    ("INVESTIGATING", "Investigating your problem",
     ["BUILDING_PROBLEM"]),
    ("GATHERING_EVIDENCE", "Gathering evidence",
     ["RETRIEVE", "FREEZE", "VERIFY"]),
    ("MAPPING_MECHANISMS", "Mapping mechanisms",
     ["PREMISE_GATE", "SYNTHESIZE", "MECHANISM_SPACE",
      "MULTI_SOURCE_DISCOVERY", "COLLISION"]),
    ("STRESS_TESTING", "Stress-testing",
     ["PHYSICS", "ATTACK", "CONTRADICTION"]),
    ("PREPARING_PACKAGE", "Preparing technology package",
     ["KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
      "NEXT_BEST_ACTION", "RANK", "PACKAGE"]),
]


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            data = json.loads(p.read_text())
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 — honest absent, never crash the UI
        return None
    return None


def _stage_status_map(session: Dict[str, Any],
                      run_dir: Optional[Path]) -> Dict[str, str]:
    """stage -> recorded status, from the run's own persisted records:
    the per-stage envelopes' stage_log entries (live during a run) and
    the run manifest's stage log (written at finalize). The LAST entry
    per stage wins. NOT from inference."""
    out: Dict[str, str] = {}
    if not run_dir or not run_dir.exists():
        return out
    sources: List[Path] = sorted(run_dir.glob("envelope_*.json"))
    manifest = run_dir / "run_manifest.json"
    if manifest.exists():
        sources.append(manifest)
    for env_path in sources:
        env = _read_json(env_path)
        for entry in (env or {}).get("stage_log") or []:
            if isinstance(entry, dict) and entry.get("stage"):
                out[entry["stage"]] = str(entry.get("status") or "UNKNOWN")
    return out


def _classify_stage(status: str) -> str:
    s = (status or "").upper()
    if s == "OK":
        return "DONE"
    if s.startswith("SKIPPED") or s.startswith("DISABLED"):
        return "SKIPPED"
    if s in ("", "UNKNOWN"):
        return "NOT_REACHED"
    return "FAILED"


def _envelope(run_dir: Optional[Path], stage: str) -> Optional[Dict]:
    if not run_dir:
        return None
    return _read_json(run_dir / f"envelope_{stage}.json")


def _walk_providers(obj: Any, found: List[Dict[str, Any]],
                    depth: int = 0) -> None:
    """Bounded recursive scan for persisted provider/model records
    (model_route is aggregated from what the run ACTUALLY recorded —
    never from configuration). Depth-limited to keep the scan cheap on
    large envelopes."""
    if depth > 4:
        return
    if isinstance(obj, dict):
        pid = obj.get("provider") or obj.get("provider_id")
        if isinstance(pid, str) and pid and not str(pid).startswith("$"):
            rec = {"provider": pid}
            for k_src, k_dst in (("model", "model"), ("status", "status"),
                                 ("latency_ms", "latency_ms"),
                                 ("purpose", "purpose"),
                                 ("failure_type", "failure_type")):
                v = obj.get(k_src)
                if isinstance(v, (str, int)) and v:
                    rec[k_dst] = v
            if rec not in found:
                found.append(rec)
        for v in obj.values():
            _walk_providers(v, found, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:60]:
            _walk_providers(v, found, depth + 1)


def _model_route(session: Dict[str, Any],
                 run_dir: Optional[Path]) -> Dict[str, Any]:
    """Which providers/models actually executed work on this run, from
    persisted bytes: the evidence pack's extraction call, the run
    envelopes' provider records, and the preflight transport the worker
    verified (the gateway probe is recorded in the evidence pack llm
    block when a run exists)."""
    calls: List[Dict[str, Any]] = []
    ep = session.get("evidence_pack") or {}
    llm = ep.get("llm") or (ep.get("problem") or {}).get("llm") or {}
    if isinstance(llm, dict) and llm.get("provider"):
        calls.append({"role": "evidence_extraction",
                      "provider": llm.get("provider"),
                      "model": llm.get("model"),
                      "status": llm.get("status")})
    if run_dir and run_dir.exists():
        for env_path in sorted(run_dir.glob("envelope_*.json")):
            env = _read_json(env_path)
            if env:
                found: List[Dict[str, Any]] = []
                _walk_providers(env, found)
                for rec in found[:8]:
                    rec = dict(rec)
                    rec["role"] = env_path.stem.replace("envelope_", "")
                    if rec not in calls:
                        calls.append(rec)
    return {
        "calls": calls[:24],
        "call_count": len(calls),
        "note": ("aggregated from persisted run artifacts (envelopes, "
                 "evidence pack); configuration is never reported as "
                 "execution"),
    }


def _evidence_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    ep = session.get("evidence_pack") or {}
    retrieval = ep.get("retrieval") or []
    env = _envelope(run_dir, "RETRIEVE") or {}
    evidence = env.get("evidence") or []
    sources = sorted({(e.get("source") or "?") for e in evidence
                      if isinstance(e, dict)}) if evidence else []
    failed = {}
    if run_dir:
        manifest = _read_json(run_dir / "run_manifest.json") or {}
        failed = manifest.get("failed_stages") or {}
    retrieve_failed = bool(failed.get("RETRIEVE"))
    return {
        "state": ("FAILED" if retrieve_failed else
                  "GATHERED" if (evidence or retrieval) else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "records_found": len(evidence) or len(retrieval) or 0,
        "sources": sources[:10],
        "retrieval_route": ep.get("routing") or
        (ep.get("retrieval_route") or "UNKNOWN"),
        "provider_outcomes": ep.get("provider_outcomes") or [],
    }


def _mechanism_state(session: Dict, run_dir: Optional[Path],
                     stage_status: Dict[str, str]) -> Dict:
    syn = _envelope(run_dir, "SYNTHESIZE") or {}
    mm = syn.get("mechanism_map") or {}
    ms = _envelope(run_dir, "MECHANISM_SPACE") or {}
    candidates = ms.get("candidates") or []
    ok = any(_classify_stage(stage_status.get(s, "")) == "DONE"
             for s in ("SYNTHESIZE", "MECHANISM_SPACE"))
    failed = any(_classify_stage(stage_status.get(s, "")) == "FAILED"
                 for s in ("SYNTHESIZE", "MECHANISM_SPACE"))
    return {
        "state": ("FAILED" if failed else
                  "GENERATED" if ok or mm else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "mechanism": mm.get("mechanism"),
        "intervention": mm.get("intervention"),
        "expected_effect": mm.get("expected_effect"),
        "candidate_count": (len(candidates)
                            if isinstance(candidates, list) else 0),
    }


def _invention_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    final = (session.get("final_status") or "").upper()
    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json") \
        if run_dir else None
    surv = _read_json(run_dir / "SURVIVOR_SELECTION.json") \
        if run_dir else None
    pkg = session.get("package") or {}
    exists = bool(inv or surv or final == "AUTOMATED_INVENTION_CANDIDATE")
    return {
        "state": ("EXISTS" if exists else
                  "REJECTED" if final in ("REJECTED",
                                          "MALFORMED_OR_FALSE_PREMISE")
                  else "PENDING" if session.get("status") in
                  _RUNNING_STATUSES else "NONE"),
        "final_status": session.get("final_status"),
        "specification_present": bool(inv),
        "survivor_recorded": bool(surv or
                                  final == "AUTOMATED_INVENTION_CANDIDATE"),
        "package_built": bool(pkg.get("complete")),
    }


def _physics_state(session: Dict, run_dir: Optional[Path],
                   stage_status: Dict[str, str]) -> Dict:
    env = _envelope(run_dir, "PHYSICS") or {}
    ph = env.get("physics") or {}
    st = _classify_stage(stage_status.get("PHYSICS", ""))
    # MECHANISM_NOT_SIMULATABLE is the R413 decision machine's honest
    # refusal (no validated solver covers the mechanism's domain) —
    # reported as NOT_SIMULATABLE, never counted as a simulation
    verdict = ph.get("lifecycle_verdict")
    not_sim = verdict in (None, "NOT_APPLICABLE",
                          "MECHANISM_NOT_SIMULATABLE")
    state = ("SIMULATED" if st == "DONE" and not not_sim
             else "NOT_SIMULATABLE" if verdict == "MECHANISM_NOT_SIMULATABLE"
             else "FAILED" if st == "FAILED"
             else "SKIPPED" if st == "SKIPPED"
             else "PENDING" if session.get("status") in
             _RUNNING_STATUSES else "NOT_APPLICABLE")
    return {
        "state": state,
        "lifecycle_verdict": verdict,
        "baseline_outcome": (ph.get("baseline_comparison") or {}).get(
            "outcome"),
        "epistemic_class": "COMPUTATIONAL_RESULT"
        if (state == "SIMULATED") else None,
        "note": ("the physics decision system's honest refusal: the "
                 "mechanism's domain has no validated solver (R413 "
                 "registry)" if verdict == "MECHANISM_NOT_SIMULATABLE"
                 else None),
    }


def _novelty_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    pa_env = _envelope(run_dir, "MULTI_SOURCE_DISCOVERY") or {}
    prior_art = pa_env.get("prior_art")
    if isinstance(prior_art, dict):
        prior_art = prior_art.get("results") or []
    col = _envelope(run_dir, "COLLISION") or {}
    return {
        "state": ("SEARCHED" if prior_art is not None else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "prior_art_count": len(prior_art) if isinstance(prior_art, list)
        else 0,
        "collision_results_present": bool(col.get("collision_results")),
        "language_rule": ("novelty signals only — legal patentability "
                          "is NEVER asserted (not a patent court)"),
    }


def _attack_state(session: Dict, run_dir: Optional[Path],
                  stage_status: Dict[str, str]) -> Dict:
    env = _envelope(run_dir, "ATTACK") or {}
    ar = env.get("attack_results") or {}
    overall = ar.get("overall") if isinstance(ar, dict) else None
    st = _classify_stage(stage_status.get("ATTACK", ""))
    independence = None
    if isinstance(ar, dict):
        independence = ar.get("independence_mode") or \
            ar.get("independence")
    return {
        "state": ("EXECUTED" if st == "DONE" else
                  "FAILED" if st == "FAILED" else
                  "SKIPPED" if st == "SKIPPED" else
                  "PENDING" if session.get("status") in _RUNNING_STATUSES
                  else "NOT_REACHED"),
        "overall": overall,
        "independence": independence,
    }


def _experiment_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    ke = _envelope(run_dir, "KILLER_EXPERIMENT") or {}
    experiment = ke.get("killer_experiment") or {}
    dex = _read_json(run_dir / "DECISIVE_EXPERIMENT.json") \
        if run_dir else None
    spec = experiment or dex or None
    executed = bool(
        (experiment.get("status") if isinstance(experiment, dict)
         else None) in ("EXECUTED", "COMPLETE", "RUN"))
    return {
        "state": ("SPECIFIED_NOT_EXECUTED" if spec and not executed
                  else "EXECUTED" if executed
                  else "PENDING" if session.get("status") in
                  _RUNNING_STATUSES else "NOT_SPECIFIED"),
        "decisive_experiment_present": bool(spec),
        "note": ("the decisive physical experiment is the run's own "
                 "falsification contract (Art. LII); in this machine it "
                 "is specified for survivors and executed only through "
                 "the reality-loop interface"),
    }


def _package_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    # R414 fix: package presence from the run's own PACKAGE_REPORT +
    # DOWNLOAD dir (the worker persists it there; the session INDEX may
    # lag — the run dir is the authority, Art. X)
    pkg = {"complete": False, "maturity": None, "zip_name": None}
    if run_dir and run_dir.exists():
        report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
        dl = run_dir / "DOWNLOAD"
        zips = sorted(dl.glob("*.zip")) if dl.exists() else []
        pkg = {"complete": bool(report.get("complete") and zips),
               "maturity": report.get("maturity"),
               "zip_name": zips[0].name if zips else None}
    session_pkg = session.get("package") or {}
    complete = bool(pkg.get("complete") or session_pkg.get("complete"))
    return {
        "state": ("READY" if complete
                  else "PENDING" if session.get("status") in
                  _RUNNING_STATUSES else "NOT_PRODUCED"),
        "maturity": pkg.get("maturity") or session_pkg.get("maturity"),
        "zip_name": pkg.get("zip_name") or session_pkg.get("zip_name"),
        "counsel_package_available": True,  # R414: always exportable
        # (it is a technical-evidence export, not a legal document)
    }


def _failure_state(session: Dict, run_dir: Optional[Path]) -> Dict:
    status = session.get("status") or ""
    manifest = _read_json(run_dir / "run_manifest.json") \
        if run_dir else None
    failed_stages = (manifest or {}).get("failed_stages") or {}
    infra = status in _BLOCKED_STATUSES or status.startswith("ERROR")
    return {
        "state": ("INFRASTRUCTURE" if infra else
                  "STAGE_FAILURES" if failed_stages else
                  "NONE" if status == "COMPLETE" else "PENDING"),
        "error": session.get("error"),
        "failed_stages": {k: (v.get("status") if isinstance(v, dict)
                              else str(v))[:60]
                          for k, v in failed_stages.items()},
        "machine_status": status,
        "note": ("infrastructure failures are never scientific "
                 "rejections (Art. LXI) — RUN_BLOCKED exists so the "
                 "product can say THIS honestly"),
    }


def phase_progression(session: Dict, run_dir: Optional[Path],
                      stage_status: Dict[str, str]) -> List[Dict]:
    """The directive §5 UI phases, each mapped to REAL backend stages;
    a phase is DONE only when its stages are done, IN_PROGRESS while any
    runs, FAILED if any failed. Never fabricated progress."""
    running = session.get("status") in _RUNNING_STATUSES
    out: List[Dict] = []
    reached_any = False
    # the INVESTIGATING phase is the problem build: DONE when the run
    # dir carries a problem.json (the build's own artifact), never
    # while it is still being written
    problem_built = bool(run_dir and (run_dir / "problem.json").exists())
    for phase_id, label, stages in PHASES:
        if phase_id == "INVESTIGATING":
            phase_state = ("DONE" if problem_built else
                           "IN_PROGRESS" if running else "NOT_STARTED")
            out.append({"phase": phase_id, "label": label,
                        "state": phase_state, "stages": {}})
            if problem_built:
                reached_any = True
            continue
        states = [_classify_stage(stage_status.get(s, ""))
                  for s in stages if s in stage_status]
        phase_state = "NOT_STARTED"
        if states:
            if any(s == "FAILED" for s in states):
                phase_state = "FAILED"
            elif all(s == "DONE" for s in states):
                phase_state = "DONE"
                reached_any = True
            elif any(s == "DONE" for s in states):
                phase_state = "IN_PROGRESS"
                reached_any = True
            else:
                phase_state = "IN_PROGRESS" if reached_any \
                    else "NOT_STARTED"
        out.append({"phase": phase_id, "label": label,
                    "state": phase_state,
                    "stages": {s: stage_status.get(s)
                               for s in stages if s in stage_status}})
    return out


def terminal_outcome(session: Dict, run_dir: Optional[Path] = None) -> Dict:
    """The directive §18 four-state outcome + the recorded BASIS for it.
    PENDING while the run is live. Derived from recorded fields only."""
    status = session.get("status") or ""
    final = (session.get("final_status") or "").upper()
    pkg = session.get("package") or {}

    if status in _RUNNING_STATUSES:
        return {"outcome": OUTCOME_PENDING, "basis":
                f"machine status {status or 'PENDING'} — run in flight"}

    if status == "COMPLETE" and \
            final == "AUTOMATED_INVENTION_CANDIDATE":
        pkg_complete = bool(pkg.get("complete"))
        if not pkg_complete and run_dir and run_dir.exists():
            report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
            zips = sorted((run_dir / "DOWNLOAD").glob("*.zip")) \
                if (run_dir / "DOWNLOAD").exists() else []
            pkg_complete = bool(report.get("complete") and zips)
        if pkg_complete:
            return {"outcome": OUTCOME_SURVIVED,
                    "basis": ("final_status="
                              "AUTOMATED_INVENTION_CANDIDATE and the "
                              "technology package was built (recorded "
                              "package.complete=true)")}
        return {"outcome": OUTCOME_REQUIRES_EXPERIMENT,
                "basis": ("final_status="
                          "AUTOMATED_INVENTION_CANDIDATE but no "
                          "technology package on this run; the decisive "
                          "physical experiment is specified, not "
                          "executed (recorded fields: package.complete="
                          "false)")}
    if status == "COMPLETE" and final in ("REJECTED",
                                          "MALFORMED_OR_FALSE_PREMISE"):
        return {"outcome": OUTCOME_NO_DEFENSIBLE,
                "basis": f"final_status={final} — a real discovery "
                         f"result (the adversarial chain killed or "
                         f"premise-gated the candidate)"}
    if status == "COMPLETE":
        return {"outcome": OUTCOME_RUN_BLOCKED,
                "basis": ("terminal without a recorded verdict "
                          "(final_status empty/UNKNOWN) — a scientific "
                          "conclusion was not reached")}
    # INTERRUPTED / ERROR_* : infrastructure-class terminations
    return {"outcome": OUTCOME_RUN_BLOCKED,
            "basis": f"machine status {status} — infrastructure, "
                     f"never a scientific rejection (Art. LXI)"}


def canonical_run_state(session: Dict) -> Dict[str, Any]:
    """The directive §4 DiscoveryRun object. Backend-derived from the
    session record + run-dir artifacts; the frontend READS this and
    never re-derives states client-side."""
    run_dir = Path(session["run_dir"]) if session.get("run_dir") else None
    stage_status = _stage_status_map(session, run_dir)
    outcome = terminal_outcome(session, run_dir)
    return {
        "run_id": session.get("session_id"),
        "user_problem": session.get("user_text"),
        "created_at": session.get("created_at"),
        "status": session.get("status"),
        "model_route": _model_route(session, run_dir),
        "retrieval_route": _evidence_state(session, run_dir).get(
            "retrieval_route"),
        "evidence_state": _evidence_state(session, run_dir),
        "mechanism_state": _mechanism_state(session, run_dir,
                                            stage_status),
        "invention_state": _invention_state(session, run_dir),
        "physics_state": _physics_state(session, run_dir, stage_status),
        "novelty_state": _novelty_state(session, run_dir),
        "attack_state": _attack_state(session, run_dir, stage_status),
        "experiment_state": _experiment_state(session, run_dir),
        "package_state": _package_state(session, run_dir),
        "provenance": {
            "run_dir": session.get("run_dir"),
            "origin": session.get("origin"),
            "engine_authority": ("the run directory's persisted "
                                 "artifacts are authoritative; this "
                                 "object is their projection (Art. X)"),
        },
        "failure_state": _failure_state(session, run_dir),
        "outcome": outcome["outcome"],
        "outcome_label": OUTCOME_LABELS[outcome["outcome"]],
        "outcome_basis": outcome["basis"],
        "phase_progression": phase_progression(session, run_dir,
                                               stage_status),
        "schema_version": "1.0.0",
    }
