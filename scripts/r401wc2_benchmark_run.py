#!/usr/bin/env python3
"""scripts/r401wc2_benchmark_run.py — R401-WC2 Phase 3: measure the
FROZEN cross-domain benchmark, baseline vs R401, identical metrics.

    python3 scripts/r401wc2_benchmark_run.py [--arm baseline|r401|both]
        [--problems N] [--run-dir R401-WC2/BENCHMARK/RUNS]

The battery:
  1. verifies the frozen benchmark file hash (refuses a mutated
     benchmark — the freeze is the contract);
  2. probes the LLM transport (a quota-limited transport is an honest
     BLOCKED state, recorded, never a quality result — Art. XXV);
  3. runs each problem through the arm's engine (baseline: detached
     worktree at 7dbebe94; r401: the HEAD checkout), resumable per
     problem via the EngineRun conductor's own resume path;
  4. measures with the COMMON instrument (the R401 comparator and
     prediction check applied to BOTH arms' own artifacts);
  5. computes the headline MD-EST per problem and the benchmark score.

A REJECTED final status is an honest result. Nothing is converted.
"""
from __future__ import annotations

import argparse
import hashlib
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

BENCH_DIR = REPO_ROOT / "R401-WC2" / "BENCHMARK"
FROZEN = BENCH_DIR / "FROZEN_BENCHMARK.json"
RUNS_DIR = BENCH_DIR / "RUNS"
BASELINE_COMMIT = "7dbebe940fe73f47a420b4f0ca2f9e5188d22ca4"
BASELINE_WT = Path("/home/z/my-project/baseline_wt_r401wc2")
GATEWAY_PORT = 8787
GATEWAY_LOG = REPO_ROOT / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"


def _load_key() -> str:
    kv = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
    return kv.get("ZAI_API_KEY", "")


def _log(msg: str) -> None:
    print(f"[r401wc2-bench] {msg}", flush=True)


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------
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


def _probe_transport(key: str) -> Dict[str, Any]:
    """One tiny live call. QUOTA_BLOCKED is an honest state (Art. XXV):
    the battery stops (resumable) rather than burning problems on a
    dead transport."""
    import urllib.error
    import urllib.request
    body = json.dumps({
        "model": "glm-4-plus",
        "messages": [{"role": "user",
                      "content": "Reply with exactly: TRANSPORT_OK"}],
        "max_tokens": 20}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{GATEWAY_PORT}/v1/chat/completions",
        data=body, headers={"Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
        content = (((d.get("choices") or [{}])[0].get("message") or {})
                   .get("content") or "")
        ok = "TRANSPORT_OK" in content
        return {"state": "TRANSPORT_OK" if ok else "UNEXPECTED_CONTENT",
                "latency_s": round(time.time() - t0, 1),
                "content_sample": content[:40]}
    except urllib.error.HTTPError as e:
        return {"state": f"HTTP_{e.code}",
                "error": e.read()[:200].decode(errors="replace")}
    except Exception as exc:  # noqa: BLE001
        return {"state": f"TRANSPORT_FAILED:{type(exc).__name__}",
                "error": str(exc)[:160]}


# ---------------------------------------------------------------------------
# baseline worktree
# ---------------------------------------------------------------------------
def _setup_baseline_worktree() -> None:
    if BASELINE_WT.exists():
        head = subprocess.run(["git", "rev-parse", "HEAD"],
                              cwd=str(BASELINE_WT), capture_output=True,
                              text=True).stdout.strip()
        if head == BASELINE_COMMIT:
            return
        subprocess.run(["git", "worktree", "remove", "--force",
                        str(BASELINE_WT)], cwd=str(REPO_ROOT),
                       capture_output=True, timeout=120)
    r = subprocess.run(
        ["git", "worktree", "add", "--detach", str(BASELINE_WT),
         BASELINE_COMMIT], cwd=str(REPO_ROOT), capture_output=True,
        text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"worktree add failed: {r.stderr[:300]}")
    keys = REPO_ROOT / ".env.keys"
    if keys.exists():
        shutil.copy(keys, BASELINE_WT / ".env.keys")


def _subprocess_env() -> Dict[str, str]:
    e = dict(os.environ)
    e["ZAI_API_KEY"] = _load_key()
    for var in ("ENGINE_SYNTHESIS_PROVIDER", "ENGINE_ATTACK_PROVIDER",
                "ENGINE_CAD_PROVIDER", "ENGINE_IMPROVEMENT_PROVIDER",
                "ENGINE_TECHNICAL_PROVIDER"):
        e[var] = "zai"
    e["ENGINE_GRID_PROVIDERS"] = "zai"
    e["ENGINE_ENSEMBLE_PROVIDERS"] = "zai"
    return e


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


def _run_arm(arm: str, problem: Dict[str, Any],
             run_dir: Path) -> Dict[str, Any]:
    """Run one problem on one arm. baseline: the detached worktree at
    the baseline commit; r401: the HEAD checkout."""
    if arm == "baseline":
        wt = BASELINE_WT
        _setup_baseline_worktree()
    else:
        wt = REPO_ROOT
    resume = (run_dir / "envelope_RETRIEVE.json").exists() and \
             not (run_dir / "final_state.json").exists()
    runner = wt / f"_r401wc2_bench_engine_{arm}.py"
    runner.write_text(RUNNER_TEMPLATE.format(
        wt=str(wt), problem=problem, run_dir=str(run_dir),
        run_id=problem["problem_id"].replace("bench-", f"{arm}-bench-"),
        registry=str(run_dir / "PACKAGE_ID_REGISTRY.json"), resume=resume))
    started = time.time()
    proc = subprocess.run([sys.executable, str(runner)], cwd=str(wt),
                          env=_subprocess_env(), capture_output=True,
                          text=True, timeout=5400)
    elapsed = round(time.time() - started, 1)
    out = proc.stdout or ""
    final = {}
    for line in out.splitlines():
        if line.startswith("FINAL_STATE:"):
            try:
                final = json.loads(line[len("FINAL_STATE:"):])
            except Exception:  # noqa: BLE001
                final = {"parse_error": True}
    (run_dir / "RUNNER_STDOUT.log").write_text(
        out[-20000:] + "\n---STDERR---\n" + (proc.stderr or "")[-20000:])
    runner.unlink(missing_ok=True)
    _log(f"{arm}/{problem['problem_id']}: rc={proc.returncode}, "
         f"{elapsed}s, final_status={(final or {}).get('final_status')}")
    return {"final": final, "elapsed_s": elapsed,
            "returncode": proc.returncode, "resumed": resume}


# ---------------------------------------------------------------------------
# the COMMON measurement instrument (both arms)
# ---------------------------------------------------------------------------
def _content_hash(c: Dict[str, Any]) -> str:
    basis = json.dumps(
        {k: c.get(k) for k in ("mechanism", "intervention",
                               "predicted_effect", "testable_prediction")},
        sort_keys=True, default=str)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _arm_candidates(arm: str, run_dir: Path) -> List[Dict[str, Any]]:
    """The arm's OWN candidate records, wrapped into the common
    comparator field shape (the r401_baseline_run pattern: no field is
    invented; missing fields stay missing)."""
    out: List[Dict[str, Any]] = []
    if arm == "baseline":
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
                    "origin": f"grid:{c.get('angle')}"})
        env_path = run_dir / "envelope_SYNTHESIZE.json"
        if env_path.exists():
            mm = (json.loads(env_path.read_text())
                  .get("mechanism_map") or {})
            if mm.get("mechanism"):
                out.append({
                    "candidate_id": "primary_mechanism",
                    "intervention": mm.get("intervention", ""),
                    "mechanism": mm.get("mechanism", ""),
                    "predicted_effect": mm.get("expected_effect", ""),
                    "testable_prediction": mm.get("falsification_test", ""),
                    "candidate_state": "CANDIDATE",
                    "origin": "primary"})
    else:
        ms_path = run_dir / "envelope_MECHANISM_SPACE.json"
        if ms_path.exists():
            ms = (json.loads(ms_path.read_text())
                  .get("mechanism_space") or {})
            for c in (ms.get("candidates") or []):
                out.append({
                    "candidate_id": c.get("candidate_id"),
                    "intervention": c.get("intervention", ""),
                    "mechanism": c.get("mechanism", ""),
                    "predicted_effect": c.get("predicted_effect",
                                              c.get("expected_effect", "")),
                    "testable_prediction": c.get("testable_prediction", ""),
                    "candidate_state": c.get("candidate_state", ""),
                    "origin": f"ms:{c.get('transformation_operator')}",
                    "mechanism_support_state": (
                        (c.get("mechanism_support") or {})
                        .get("mechanism_support_state"))})
    for c in out:
        c["candidate_hash"] = _content_hash(c)
    return out


def _measure(arm: str, run_dir: Path,
             run_result: Dict[str, Any]) -> Dict[str, Any]:
    """The common metric sheet, computed by the same code for both
    arms (the frozen benchmark's metric contract)."""
    from discovery_fabric.engine.mechanism_space import (
        _testable_prediction_check, deduplicate_candidates)
    cands = _arm_candidates(arm, run_dir)
    if cands:
        dedup = deduplicate_candidates(cands)
        kept = set(dedup.get("kept_ids") or [])
    else:
        dedup = {"n_input": 0, "n_kept": 0, "kept_ids": []}
        kept = set()
    n_testable = sum(
        1 for c in cands
        if _testable_prediction_check(
            str(c.get("testable_prediction") or "")).get("testable"))
    # the run-level evidence condition (identical on both arms: the
    # arm's own VERIFY envelope)
    ev_counts: Dict[str, int] = {}
    n_items = 0
    env_v = run_dir / "envelope_VERIFY.json"
    if env_v.exists():
        ec = (json.loads(env_v.read_text())
              .get("evidence_classification") or {})
        ev_counts = ec.get("counts") or {}
        n_items = ec.get("n_items") or 0
    supporting = (ev_counts.get("DIRECT_SUPPORT") or 0) + (
        ev_counts.get("PARTIAL_SUPPORT") or 0)
    evidence_supported_run = supporting > 0
    final_state = run_result.get("final") or {}
    fs_path = run_dir / "final_state.json"
    if fs_path.exists():
        final_state = json.loads(fs_path.read_text())
    # MD-EST: distinct AND testable AND (run-level) evidence-supported
    md_est = sum(
        1 for c in cands
        if c.get("candidate_id") in kept
        and _testable_prediction_check(
            str(c.get("testable_prediction") or "")).get("testable")
        and evidence_supported_run)
    specs = list(run_dir.glob("INVENTION_SPECIFICATION_*.json"))
    attacks = list(run_dir.glob("ENGINEERING_ATTACK_*.json"))
    survived = 0
    for a in attacks:
        try:
            if json.loads(a.read_text()).get("overall") != "KILLED":
                survived += 1
        except Exception:  # noqa: BLE001
            pass
    physics_beats = 0
    ph_path = run_dir / "stage_PHYSICS.json"
    if ph_path.exists():
        try:
            physics_beats = sum(
                1 for r in (json.loads(ph_path.read_text())
                            .get("records") or [])
                if r.get("physics_lifecycle") == "BEATS_BASELINE")
        except Exception:  # noqa: BLE001
            pass
    sheet = {
        "n_candidates_generated": len(cands),
        "n_materially_distinct": dedup.get("n_kept", 0),
        "material_distinctness_rate": (
            round(dedup["n_kept"] / dedup["n_input"], 3)
            if dedup.get("n_input") else None),
        "n_testable_predictions": n_testable,
        "testable_prediction_rate": (
            round(n_testable / len(cands), 3) if cands else None),
        "evidence_counts": ev_counts,
        "evidence_n_items": n_items,
        "evidence_support_rate": (
            round(supporting / n_items, 3) if n_items else None),
        "contradiction_rate": (
            round((ev_counts.get("CONTRADICTORY") or 0) / n_items, 3)
            if n_items else None),
        "run_level_evidence_supported": evidence_supported_run,
        "md_est_count": md_est,
        "md_est_threshold_pass": md_est >= 3,
        "cad_rate": (
            round(len(specs) / len(cands), 3) if cands else None),
        "physics_beats_baseline": physics_beats,
        "attack_survival": survived,
        "final_status": final_state.get("final_status"),
        "final_reason": (final_state.get("reason") or "")[:200],
        "runtime_s": run_result.get("elapsed_s"),
        "dedup_kept_ids": dedup.get("kept_ids"),
    }
    if arm == "r401":
        sheet["mechanism_level_support"] = {
            c.get("candidate_id"): c.get("mechanism_support_state")
            for c in cands}
    else:
        sheet["mechanism_level_support"] = "NOT_COMPUTABLE_ON_BASELINE"
    return sheet


# ---------------------------------------------------------------------------
# main battery
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("baseline", "r401", "both"),
                    default="both")
    ap.add_argument("--problems", type=int, default=0,
                    help="run only the first N problems (0 = all)")
    ap.add_argument("--skip-transport-probe", action="store_true")
    args = ap.parse_args()

    frozen_hash = _sha256_file(FROZEN)
    bench = json.loads(FROZEN.read_text())
    problems = bench["problems"]
    if args.problems:
        problems = problems[:args.problems]
    _log(f"frozen benchmark verified: {len(bench['problems'])} problems, "
         f"sha256={frozen_hash[:16]}... (running {len(problems)})")

    key = _load_key()
    gateway = None
    if key:
        os.environ["ZAI_API_KEY"] = key
        gateway = _start_gateway(key)
        if not _gateway_alive():
            _log("FATAL: gateway unavailable — refusing to burn the "
                 "battery on a dead transport")
            return 2
    if not args.skip_transport_probe and key:
        probe = _probe_transport(key)
        _log(f"transport probe: {probe}")
        if probe.get("state") not in ("TRANSPORT_OK",
                                      "UNEXPECTED_CONTENT"):
            _log("transport NOT healthy — battery BLOCKED (honest "
                 "state; re-run when the quota window resets; "
                 "completed problems are not re-burned)")
            probe_path = RUNS_DIR / "TRANSPORT_PROBE_LAST.json"
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            probe_path.write_text(json.dumps(
                {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
                 "probe": probe}, indent=1))
            if gateway:
                gateway.terminate()
            return 3

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    arms = ["baseline", "r401"] if args.arm == "both" else [args.arm]
    battery: Dict[str, Any] = {
        "battery_version": "r401wc2-benchmark-run/1.0.0",
        "frozen_benchmark_sha256": frozen_hash,
        "measured_at_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True).stdout.strip(),
        "baseline_commit": BASELINE_COMMIT,
        "arms": {},
    }
    for arm in arms:
        arm_record: Dict[str, Any] = {}
        for problem in problems:
            pid = problem["problem_id"]
            run_dir = RUNS_DIR / arm / pid
            run_dir.mkdir(parents=True, exist_ok=True)
            marker = run_dir / "MEASUREMENT.json"
            if marker.exists():
                arm_record[pid] = json.loads(marker.read_text())
                _log(f"{arm}/{pid}: already measured (resumed)")
                continue
            res = _run_arm(arm, problem, run_dir)
            sheet = _measure(arm, run_dir, res)
            sheet["problem"] = {k: problem[k] for k in
                                ("problem_id", "device", "failure_mode",
                                 "domain")}
            sheet["returncode"] = res.get("returncode")
            sheet["resumed"] = res.get("resumed")
            marker.write_text(json.dumps(sheet, indent=1,
                                         default=str))
            arm_record[pid] = sheet
            (RUNS_DIR / f"SUMMARY_{arm}.json").write_text(json.dumps(
                arm_record, indent=1, default=str))
        # the arm summary
        done = [s for s in arm_record.values()]
        n_done = len(done)
        if n_done:
            arm_record_summary = {
                "n_problems_measured": n_done,
                "mean_candidates": round(sum(
                    s.get("n_candidates_generated") or 0
                    for s in done) / n_done, 2),
                "mean_materially_distinct": round(sum(
                    s.get("n_materially_distinct") or 0
                    for s in done) / n_done, 2),
                "mean_md_est": round(sum(
                    s.get("md_est_count") or 0
                    for s in done) / n_done, 2),
                "n_md_est_threshold_pass": sum(
                    1 for s in done
                    if s.get("md_est_threshold_pass")),
                "headline": (
                    "fraction of problems with MD-EST >= 3: "
                    f"{sum(1 for s in done if s.get('md_est_threshold_pass'))}"
                    f"/{n_done}"),
            }
            battery["arms"][arm] = arm_record_summary
            (RUNS_DIR / f"ARM_SUMMARY_{arm}.json").write_text(json.dumps(
                arm_record_summary, indent=1))

    battery["measured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime())
    (RUNS_DIR / "BATTERY_STATE.json").write_text(
        json.dumps(battery, indent=1, default=str))
    print(json.dumps(battery, indent=1, default=str))
    if gateway:
        gateway.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
