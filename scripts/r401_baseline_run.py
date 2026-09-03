#!/usr/bin/env python3
"""scripts/r401_baseline_run.py — R401-WC PHASE 1: freeze
R401_BASELINE (write-once, never overwritten).

Runs the CURRENT PRODUCTION PIPELINE UNCHANGED on the SAME held-out
problem the R401 mechanism-space run uses, at the canonical commit
HEAD = 7dbebe94 (engine code identical to the deployed 930eca8b
artifact — R400-E: zero engine-code changes in R400), in a DETACHED
git worktree so the R401A working-tree changes cannot leak into the
baseline (Art. IX: the baseline observes the committed pipeline; the
pipeline is not modified by the observation).

Captured metrics (from the run's OWN persisted artifacts — never
narratives): evidence classification counts, mechanism support,
material distinctness of the generated candidates (the R401
structural comparator applied to the baseline's own outputs — the
same instrument on both arms), candidate count, CAD rate, physics
rate, baseline rate, attack survival, testable prediction rate,
KEEP/KILL, runtime, LLM calls, retrieval calls, network cost
(latency-weighted, disclosed basis).

Usage:
  python3 scripts/r401_baseline_run.py [--fresh]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

BASELINE_COMMIT = "7dbebe940fe73f47a420b4f0ca2f9e5188d22ca4"
WORKTREE = Path("/home/z/my-project/baseline_wt_r401")
R401_DIR = REPO_ROOT / "R401"
OUT_PATH = R401_DIR / "R401_BASELINE.json"
GATEWAY_PORT = 8787
GATEWAY_LOG = REPO_ROOT / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"

PROBLEM = {
    "problem_id": "r401_core_proof",
    "device": "peritoneal dialysis catheter",
    "failure": ("omental wrapping and fibrin clogging obstruct the "
                "catheter under low abdominal-flow conditions despite "
                "flushing protocols"),
    "failure_mode": "obstruction",
    "constraint": ("sustain drainage above 0.5 mL/min at normal "
                   "intra-abdominal pressure without systemic "
                   "anticoagulation"),
    "held_out": ("NOT one of the 18-case production benchmark "
                 "(r396_external_probes._benchmark_cases)"),
}

RUNNER_TEMPLATE = '''
import json, sys
sys.path.insert(0, r"{wt}")
from discovery_fabric.engine.run import EngineRun
run = EngineRun({problem!r}, {run_dir!r}, run_id={run_id!r},
                package_registry_path={registry!r},
                resume={resume})
final = run.run()
print("FINAL_STATE:" + json.dumps(final, default=str))
'''


def _subprocess_env() -> Dict[str, str]:
    e = dict(os.environ)
    e["ZAI_API_KEY"] = _load_key()
    # OPERATOR OVERRIDES (the engine's own documented mechanism for
    # degraded-endpoint situations; every pin is recorded in the
    # per-call provider ledger, never silent): NVIDIA measured TODAY
    # as an infinite-hang endpoint (chat/completions: no response at
    # 15-40s x3; catalog 200 OK) — the zai local gateway is the
    # healthy registered transport. Same pin R400-C used ("zai
    # glm-4-plus via sandbox local-gateway; the deployed contract pins
    # nvidia — recorded, not conflated").
    for var in ("ENGINE_SYNTHESIS_PROVIDER",
                "ENGINE_ATTACK_PROVIDER",
                "ENGINE_CAD_PROVIDER",
                "ENGINE_IMPROVEMENT_PROVIDER",
                "ENGINE_TECHNICAL_PROVIDER"):
        e[var] = "zai"
    e["ENGINE_GRID_PROVIDERS"] = "zai"
    e["ENGINE_ENSEMBLE_PROVIDERS"] = "zai"
    return e


def _log(msg: str) -> None:
    print(f"[r401-baseline] {msg}", flush=True)


def _load_key() -> str:
    kv = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
    return kv.get("ZAI_API_KEY", "")


def _gateway_alive() -> bool:
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        f"http://127.0.0.1:{GATEWAY_PORT}/healthz", method="GET")
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def _start_gateway(key: str):
    subprocess.run(["pkill", "-f", "zai_gateway.mjs"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = key
    env["ZAI_API_KEY"] = key
    proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", str(GATEWAY_PORT)],
        cwd=str(REPO_ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    for _ in range(30):
        time.sleep(0.5)
        if _gateway_alive():
            return proc
    proc.terminate()
    return None


def _setup_worktree(fresh: bool) -> None:
    if fresh and WORKTREE.exists():
        subprocess.run(["git", "worktree", "remove", "--force",
                        str(WORKTREE)], cwd=str(REPO_ROOT),
                       capture_output=True, timeout=60)
    if not WORKTREE.exists():
        r = subprocess.run(
            ["git", "worktree", "add", "--detach", str(WORKTREE),
             BASELINE_COMMIT], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"worktree add failed: {r.stderr[:300]}")
    head = subprocess.run(["git", "rev-parse", "HEAD"],
                          cwd=str(WORKTREE), capture_output=True,
                          text=True).stdout.strip()
    if head != BASELINE_COMMIT:
        raise RuntimeError(
            f"worktree HEAD {head} != baseline commit {BASELINE_COMMIT}")
    # local secrets for the retrieval providers (never committed; the
    # worktree is temporary and removed afterwards)
    keys = REPO_ROOT / ".env.keys"
    if keys.exists():
        shutil.copy(keys, WORKTREE / ".env.keys")
    dirty = subprocess.run(["git", "status", "--short"],
                           cwd=str(WORKTREE), capture_output=True,
                           text=True).stdout.strip()
    _log(f"worktree at {head}; status: {dirty or 'clean (+copied .env.keys)'}")


def _run_engine(run_dir: Path, run_id: str) -> Dict[str, Any]:
    resume = (run_dir / "envelope_RETRIEVE.json").exists() and \
             not (run_dir / "final_state.json").exists()
    runner = WORKTREE / "_r401_baseline_engine.py"
    runner.write_text(RUNNER_TEMPLATE.format(
        wt=str(WORKTREE), problem=PROBLEM, run_dir=str(run_dir),
        run_id=run_id, registry=str(run_dir / "PACKAGE_ID_REGISTRY.json"),
        resume=resume))
    started = time.time()
    proc = subprocess.run(
        [sys.executable, str(runner)], cwd=str(WORKTREE),
        env=_subprocess_env(),
        capture_output=True, text=True, timeout=3600)
    elapsed = round(time.time() - started, 1)
    out = proc.stdout or ""
    final = {}
    for line in out.splitlines():
        if line.startswith("FINAL_STATE:"):
            try:
                final = json.loads(line[len("FINAL_STATE:"):])
            except Exception:  # noqa: BLE001
                final = {"parse_error": True, "raw": line[:200]}
    log_path = run_dir / "RUNNER_STDOUT.log"
    log_path.write_text(out[-20000:] + "\n---STDERR---\n" +
                        (proc.stderr or "")[-20000:])
    if proc.returncode != 0:
        _log(f"engine subprocess rc={proc.returncode} — see {log_path}")
    _log(f"engine run {'(resumed) ' if resume else ''}finished in "
         f"{elapsed}s; final_status="
         f"{(final or {}).get('final_status')}")
    runner.unlink(missing_ok=True)
    return {"final": final, "elapsed_s": elapsed,
            "returncode": proc.returncode, "resumed": resume}


def _llm_calls_delta(before_count: int) -> Dict[str, Any]:
    if not GATEWAY_LOG.exists():
        return {"llm_calls": None, "note": "gateway log absent"}
    lines = GATEWAY_LOG.read_text().splitlines()
    entries: List[Dict[str, Any]] = []
    for ln in lines[before_count:]:
        try:
            entries.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            pass
    lat = sum(e.get("latency_ms") or 0 for e in entries)
    models = sorted({str(e.get("model")) for e in entries if e.get("model")})
    statuses: Dict[str, int] = {}
    for e in entries:
        s = str(e.get("status"))
        statuses[s] = statuses.get(s, 0) + 1
    return {"llm_calls": len(entries),
            "llm_latency_ms_total": lat,
            "llm_models": models,
            "llm_statuses": statuses}


def _retrieval_calls(run_dir: Path) -> Dict[str, Any]:
    # the worktree engine writes its own custody log (module-relative
    # REPO_ROOT = the worktree)
    p = WORKTREE / "artifacts" / "source_health" / "retrieval_log.jsonl"
    if not p.exists():
        return {"retrieval_calls": 0,
                "note": "worktree retrieval log absent"}
    entries = []
    for ln in p.read_text().splitlines():
        try:
            entries.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            pass
    run_tag = "r401_baseline"
    mine = [e for e in entries if run_tag in str(e.get("run_id") or "")]
    if not mine:
        mine = entries  # fall back to all entries; disclosed below
    lat = sum(int(e.get("latency_ms") or 0) for e in mine)
    by_source: Dict[str, int] = {}
    for e in mine:
        s = str(e.get("source_id"))
        by_source[s] = by_source.get(s, 0) + 1
    return {"retrieval_calls": len(mine),
            "retrieval_latency_ms_total": lat,
            "retrieval_by_source": by_source,
            "filter_basis": ("run_id filter" if len(mine) != len(entries)
                             else "all worktree entries (run_id not "
                                  "tagged on every entry — disclosed)")}


def _content_hash(c: Dict[str, Any]) -> str:
    """Deterministic sha256 over the candidate's own text fields (a
    real content hash — byte-identical candidates collapse, differing
    ones never collide on a missing-key None)."""
    import hashlib
    basis = json.dumps(
        {k: c.get(k) for k in ("mechanism", "intervention",
                               "predicted_effect",
                               "testable_prediction")},
        sort_keys=True, default=str)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _baseline_candidates(run_dir: Path) -> List[Dict[str, Any]]:
    """The baseline's own generated candidates (grid + primary), wrapped
    into the R401 comparator's field shape — the SAME instrument on both
    arms; no field is invented (missing fields stay missing)."""
    out: List[Dict[str, Any]] = []
    eg_path = run_dir / "EXPLORATION_GRID.json"
    if eg_path.exists():
        eg = json.loads(eg_path.read_text())
        for c in (eg.get("candidates") or []):
            f = c.get("fields") or {}
            out.append({
                "candidate_id": c.get("candidate_id"),
                "intervention": f.get("intervention", ""),
                "mechanism": f.get("mechanism", ""),
                "predicted_effect": f.get("expected_effect", ""),
                "testable_prediction": f.get("falsification_test", ""),
                "candidate_state": "CANDIDATE",
                "origin": f"grid:{c.get('angle')}",
            })
    # the primary mechanism (SYNTHESIZE stage output) — the HEAD
    # mechanism_map is a FLAT dict of string fields (verified at
    # 7dbebe94: run.py builds mm with mechanism/intervention/
    # expected_effect/falsification_test as strings)
    env_path = run_dir / "envelope_SYNTHESIZE.json"
    if env_path.exists():
        env = json.loads(env_path.read_text())
        mech_map = env.get("mechanism_map") or {}
        if mech_map.get("mechanism"):
            out.append({
                "candidate_id": "primary_mechanism",
                "intervention": mech_map.get("intervention", ""),
                "mechanism": mech_map.get("mechanism", ""),
                "predicted_effect": mech_map.get("expected_effect", ""),
                "testable_prediction":
                    mech_map.get("falsification_test", ""),
                "candidate_state": "CANDIDATE",
                "origin": "primary",
            })
    for c in out:
        c["candidate_hash"] = _content_hash(c)
    return out


def _distinctness_measurement(
        cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """R401 Phase 10 instrument applied to the baseline outputs.

    NOTE: baseline candidates carry no mechanism_graph (the baseline
    pipeline generates no structured graphs — itself the measured
    weakness), so the graph dimension is uninformative and the
    comparator falls back to the informative text dimensions
    (intervention / predicted_effect / boundary / failure)."""
    if not cands:
        return {"n_input": 0, "n_kept": 0, "material_distinctness_rate":
                None, "note": "no candidates generated"}
    from discovery_fabric.engine.mechanism_space import \
        deduplicate_candidates
    res = deduplicate_candidates(cands)
    n_in = res.get("n_input", 0)
    n_kept = res.get("n_kept", 0)
    rate = round(n_kept / n_in, 3) if n_in else None
    return {
        "n_input": n_in,
        "n_kept": n_kept,
        "kept_ids": res.get("kept_ids"),
        "material_distinctness_rate": rate,
        "dedup_events": [
            {"dropped": e.get("dropped_id"),
             "reason": (e.get("reason") or "")[:140]}
            for e in (res.get("dedup_events") or [])],
        "retain_events": [
            {"retained": e.get("retained_id"),
             "differing_dimensions": ((e.get("difference_basis") or {}) 
                                       .get("differing_dimensions")),
             "reason": (e.get("reason") or "")[:120]}
            for e in (res.get("retain_events") or [])][:12],
        "instrument_note": (
            "the R401 structural comparator (mechanism_space."
            "deduplicate_candidates) applied to the BASELINE's own "
            "candidate texts; baseline candidates carry no "
            "mechanism_graph (the measured weakness), so the graph "
            "dimension is uninformative and text dimensions decide"),
    }


def _pipeline_metrics(run_dir: Path, run_result: Dict[str, Any],
                      cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    grid_ids = {c.get("candidate_id") for c in cands
                if c.get("origin", "").startswith("grid:")}
    specs = list(run_dir.glob("INVENTION_SPECIFICATION_grid-*.json"))
    attacks = list(run_dir.glob("ENGINEERING_ATTACK_grid-*.json"))
    attacks += list(run_dir.glob("ENGINEERING_ATTACK_mech-*.json"))
    failed = list(run_dir.glob("PACKAGE_FAILED*.json"))
    final = run_result.get("final") or {}
    fs_path = run_dir / "final_state.json"
    final_state = final
    if fs_path.exists():
        final_state = json.loads(fs_path.read_text())
    # evidence classification (the run's own VERIFY record)
    ev_class = {}
    env_v = run_dir / "envelope_VERIFY.json"
    if env_v.exists():
        ec = (json.loads(env_v.read_text())
              .get("evidence_classification") or {})
        ev_class = {
            "counts": ec.get("counts") or {},
            "n_items": ec.get("n_items"),
            "mechanism_support": ec.get("mechanism_support") or {},
        }
    counts = ev_class.get("counts") or {}
    n_ev = ev_class.get("n_items") or 0
    supporting = (counts.get("DIRECT_SUPPORT") or 0) + (
        counts.get("PARTIAL_SUPPORT") or 0)
    physics = {}
    ph_path = run_dir / "stage_PHYSICS.json"
    if ph_path.exists():
        physics = json.loads(ph_path.read_text())
    n_preds = sum(1 for c in cands if c.get("testable_prediction"))
    keep_kill = {
        "final_status": final_state.get("final_status"),
        "reason": (final_state.get("reason") or "")[:200],
        "package_failed_records": [f.name for f in failed],
    }
    return {
        "candidate_count": len(cands),
        "grid_candidate_count": len(grid_ids),
        "cad_rate": {
            "n_with_engineering_spec": len(specs),
            "rate": round(len(specs) / len(cands), 3) if cands else None,
            "basis": "INVENTION_SPECIFICATION_grid-*.json persisted"},
        "physics": {
            "lifecycle_verdict": physics.get("lifecycle_verdict"),
            "chain": physics.get("chain"),
            "n_reaching_physics": 1 if physics.get("lifecycle_verdict")
            else 0,
            "physics_rate": round(
                (1 if physics.get("lifecycle_verdict") else 0) /
                len(cands), 3) if cands else None},
        "baseline_rate": {
            "beats_baseline": 1 if physics.get("lifecycle_verdict") ==
            "BEATS_BASELINE" else 0,
            "rate": round(
                (1 if physics.get("lifecycle_verdict") == "BEATS_BASELINE"
                 else 0) / len(cands), 3) if cands else None},
        "attack": {
            "n_attack_records": len(attacks),
            "attack_survival": None,  # filled by caller from envelopes
            "attack_files": [a.name for a in attacks][:12]},
        "testable_prediction_rate": round(n_preds / len(cands), 3)
        if cands else None,
        "evidence_classification": ev_class,
        "evidence_precision": {
            "value": round(supporting / n_ev, 3) if n_ev else None,
            "definition": ("(DIRECT_SUPPORT + PARTIAL_SUPPORT) / "
                           "classified items — the run's own VERIFY "
                           "classification; CONTRADICTORY counted "
                           "separately, never as support")},
        "contradiction_rate": round(
            (counts.get("CONTRADICTORY") or 0) / n_ev, 3) if n_ev else None,
        "mechanism_support": ev_class.get("mechanism_support") or {},
        "keep_kill": keep_kill,
        "runtime_s": run_result.get("elapsed_s"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--run-dir", default="")
    args = ap.parse_args()

    if OUT_PATH.exists():
        _log(f"REFUSING TO OVERWRITE {OUT_PATH} (R401_BASELINE is "
             "frozen, write-once)")
        return 3

    key = _load_key()
    if not key:
        _log("no ZAI_API_KEY — the run would record PROVIDER_UNAVAILABLE "
             "(honest, but the baseline is only meaningful with a live "
             "transport); refusing to burn the freeze")
        return 2

    _setup_worktree(args.fresh)

    gw_before = 0
    if GATEWAY_LOG.exists():
        gw_before = len(GATEWAY_LOG.read_text().splitlines())
    # stale-gateway discipline (measured live by the R401A driver): a
    # gateway whose parent run was killed mid-request stays LISTENING
    # with a wedged handler — every LLM call then blocks on the socket
    # read. ALWAYS terminate stale listeners and start a fresh child
    # this process owns.
    gateway = _start_gateway(key)
    if not _gateway_alive():
        _log("FATAL: gateway not listening — infrastructure failure, not "
             "an honest run state (Art. XXIX)")
        return 2

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir = Path(args.run_dir) if args.run_dir else None
    if run_dir is None:
        # reuse an existing incomplete baseline run (resume) if present
        cands = sorted(
            (WORKTREE / "ENGINE_RUNS").glob("r401_baseline_*")) \
            if (WORKTREE / "ENGINE_RUNS").exists() else []
        incomplete = [p for p in cands
                      if not (p / "final_state.json").exists()]
        run_dir = incomplete[-1] if incomplete else \
            WORKTREE / "ENGINE_RUNS" / f"r401_baseline_{stamp}"
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if (run_dir / "final_state.json").exists():
        _log(f"run already complete in {run_dir} — extracting only")
        run_result: Dict[str, Any] = {"final": {}, "elapsed_s": None,
                                      "returncode": 0}
    else:
        _log(f"running the BASELINE pipeline (HEAD {BASELINE_COMMIT[:8]}) "
             f"on the held-out problem -> {run_dir}")
        run_result = _run_engine(run_dir, f"r401_baseline:{stamp}")

    cands = _baseline_candidates(run_dir)
    metrics = _pipeline_metrics(run_dir, run_result, cands)
    metrics["distinctness"] = _distinctness_measurement(cands)
    metrics["llm"] = _llm_calls_delta(gw_before)
    metrics["retrieval"] = _retrieval_calls(run_dir)
    metrics["network_cost_basis"] = (
        "network cost is instrumented as call counts + summed latency_ms "
        "(retrieval custody log + gateway call log); byte-level transfer "
        "is not recorded by either instrument — disclosed, not approximated")

    # attack survival from the run's own attack records
    surv = 0
    n_att = 0
    for a in sorted(run_dir.glob("ENGINEERING_ATTACK_*.json")):
        try:
            rec = json.loads(a.read_text())
        except Exception:  # noqa: BLE001
            continue
        n_att += 1
        v = (rec.get("verdict") or rec.get("outcome") or
             rec.get("result") or "")
        if str(v).upper() in ("SURVIVED", "PASS", "OK", "PASS_ATTACK"):
            surv += 1
    metrics["attack"]["attack_survival"] = {
        "n_attacks": n_att, "n_survived": surv,
        "rate": round(surv / n_att, 3) if n_att else None}

    final_state = run_result.get("final") or {}
    fs_path = run_dir / "final_state.json"
    if fs_path.exists():
        final_state = json.loads(fs_path.read_text())

    record: Dict[str, Any] = {
        "suite": "R401_BASELINE (frozen, write-once)",
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime()),
        "baseline_commit": BASELINE_COMMIT,
        "baseline_commit_equivalence": (
            "engine code at 7dbebe94 is byte-identical to the deployed "
            "930eca8b artifact's engine (R400-E: zero engine-code changes "
            "in R400; verified: git diff 930eca8b 7dbebe94 -- "
            "discovery_fabric/ is empty)"),
        "problem": PROBLEM,
        "run_dir": str(run_dir),
        "execution_surface": (
            "detached git worktree at the exact baseline commit; zai "
            "local gateway (glm-4-plus) as the LLM transport via the "
            "engine's documented ENGINE_*_PROVIDER operator overrides "
            "(NVIDIA measured degraded TODAY: completions hang with no "
            "response at 15-40s; every pin is ledgered per call, never "
            "silent); live external retrieval sources; package registry "
            "redirected to the run dir (sandbox override — canonical "
            "state untouched, Art. IX)"),
        "returncode": run_result.get("returncode"),
        "final_status": final_state.get("final_status"),
        "final_state": {k: final_state.get(k) for k in (
            "final_status", "epistemic_state", "reason",
            "premise_verdict", "evidence_verified", "prior_art_status",
            "collision_novelty_risk", "adversarial_outcome")},
        "metrics": metrics,
        "candidates": [
            {k: c.get(k) for k in ("candidate_id", "origin", "mechanism",
                                   "intervention", "predicted_effect",
                                   "testable_prediction")}
            for c in cands],
        "fidelity_note": (
            "the baseline is the pipeline AS COMMITTED at 7dbebe94, "
            "observed from a detached worktree — the R401A working-tree "
            "changes cannot leak into this measurement; the distinctness "
            "instrument is applied post-hoc to the baseline's own "
            "outputs (same instrument both arms)"),
    }

    R401_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=1, default=str))
    _log(f"R401_BASELINE frozen -> {OUT_PATH}")

    # preserve the run's own artifacts (canonical custody)
    art = R401_DIR / "BASELINE_RUN_ARTIFACTS"
    art.mkdir(exist_ok=True)
    keep = ["final_state.json", "EXPLORATION_GRID.json",
            "stage_PHYSICS.json", "envelope_VERIFY.json",
            "envelope_SYNTHESIZE.json", "envelope_RETRIEVE.json",
            "CHEAP_SCREEN.json", "SURVIVOR_GATE.json", "problem.json"]
    for f in run_dir.iterdir():
        if f.name in keep or f.name.startswith(
                ("INVENTION_SPECIFICATION_", "ENGINEERING_ATTACK_",
                 "PACKAGE_FAILED", "envelope_")):
            shutil.copy(f, art / f.name)
    _log(f"baseline artifacts preserved -> {art}")

    if gateway:
        gateway.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
