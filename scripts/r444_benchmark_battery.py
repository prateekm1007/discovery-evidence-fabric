#!/usr/bin/env python3
"""scripts/r444_benchmark_battery.py — R444-A: run the existing W11
machinery (frozen 12-problem cross-domain benchmark + the R444
software/ML extension, frozen before this run) against the CURRENT HEAD
engine, and record the per-problem fields the R444 directive requires.

What this driver IS:
  - a thin driver over scripts/r401wc2_benchmark_run.py's OWN functions
    (_run_arm, _measure, _subprocess_env) — the SAME engine entry path
    and the SAME common measurement instrument the W11 machinery
    defined. No new framework, no new metric, no new threshold
    (the R444 directive: 'Do not build another benchmark framework
    unless the current one is actually broken' — it is not broken; a
    smoke problem ran end-to-end at HEAD before this battery).

What this driver records per problem (the R444 directive's own list):
  problem, domain, problem-existence result, evidence count, evidence
  quality, mechanism generated, distinctness result, attack result,
  evolution result, engineering realization, experiment state, final
  epistemic state, failure class, time, token/cost where available.

Success definition — DECLARED BEFORE THE RUN (Art. LIX; the R444
directive: 'Do not give yourself a success rate unless the success
definition is declared before the run'):
  - The run reports the frozen benchmark's own headline (MD-EST per
    problem; fraction of problems with MD-EST >= 3; mean MD-EST) with
    NO new threshold and NO self-assigned success rate.
  - Honest per-problem states are the result: REJECTED /
    INVENTION_REQUIRES_EXPERIMENT / EVOLVED_INVENTION_CANDIDATE /
    infrastructure INCOMPLETE_* states are all acceptable outcomes.
  - The battery's own success criterion is COVERAGE, not quality:
    every problem ends with a typed record (run completed or typed
    BLOCKED state). A problem that ends without a typed record is a
    driver defect; a problem that ends REJECTED is a result.

Usage:
  python3 scripts/r444_benchmark_battery.py [--frozen-only|--extension-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# the W11 machinery — imported, not duplicated
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "r401wc2_benchmark_run",
    str(REPO_ROOT / "scripts" / "r401wc2_benchmark_run.py"))
W11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W11)

FROZEN = REPO_ROOT / "R401-WC2" / "BENCHMARK" / "FROZEN_BENCHMARK.json"
EXTENSION = REPO_ROOT / "R444" / "BENCHMARK_EXTENSION" / "FROZEN_EXTENSION.json"
FROZEN_RUNS = REPO_ROOT / "R401-WC2" / "BENCHMARK" / "RUNS"
EXT_RUNS = REPO_ROOT / "R444" / "BENCHMARK_EXTENSION" / "RUNS"
OUT = REPO_ROOT / "R444" / "BENCHMARK_RESULTS.json"

GATEWAY_CALL_LOG = REPO_ROOT / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"


def _log(msg: str) -> None:
    print(f"[r444-battery] {msg}", flush=True)


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _gateway_call_count() -> int:
    """Count of recorded gateway calls (token/cost proxy — the gateway
    log records every call; token counts are recorded where the
    upstream returns them)."""
    try:
        return sum(1 for _ in GATEWAY_CALL_LOG.open("rb"))
    except FileNotFoundError:
        return 0


# ---------------------------------------------------------------------------
# per-problem R444 record: extract the directive's required fields from
# the run's OWN artifacts (nothing is invented; missing = honest null)
# ---------------------------------------------------------------------------
def _r444_problem_record(problem: Dict[str, Any], run_dir: Path,
                         sheet: Dict[str, Any],
                         calls_before: int, calls_after: int
                         ) -> Dict[str, Any]:
    def _j(name: str) -> Dict[str, Any]:
        p = run_dir / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                return {}
        return {}

    final = _j("final_state.json")
    env = _j("candidate_envelope.json")
    premise = _j("stage_PREMISE_GATE.json")
    retrieve_meta = _j("stage_RETRIEVE.json")
    verify = _j("envelope_VERIFY.json")
    mechanism_space = _j("envelope_MECHANISM_SPACE.json")
    lineage = _j("INVENTION_LINEAGE.json")
    eng_spec = _j("ENGINEERING_SPECIFICATION.json")
    decisive = _j("DECISIVE_EXPERIMENT.json")
    inv_spec = _j("INVENTION_SPECIFICATION.json")
    package_failed = _j("PACKAGE_FAILED.json")
    package_deferred = _j("PACKAGE_DEFERRED.json")

    # problem-existence result (Art. XX gate — the premise verdict)
    premise_verdict = (premise.get("premise_verdict")
                       or (env.get("premise_gate") or {}).get("verdict")
                       or final.get("premise_verdict"))

    # evidence count + quality
    retrieved = retrieve_meta.get("retrieved_count")
    custody = (env.get("stage_log") or [])
    ev_counts = sheet.get("evidence_counts") or {}

    # mechanism generated (the run's own records: synthesis mechanism
    # map + mechanism-space candidates)
    mm = (env.get("mechanism_map") or {})
    ms = (mechanism_space.get("mechanism_space") or {})
    n_ms_candidates = len(ms.get("candidates") or [])

    # attack result
    attack_overall = final.get("adversarial_overall")

    # evolution result — the lineage's own typed record
    ev_summary = (final.get("evolution") or {})
    generations = lineage.get("generations") or []
    gen_records = []
    for g in generations:
        arch = g.get("architecture") or {}
        gen_records.append({
            "gen": g.get("gen"),
            "origin": g.get("origin"),
            "state": g.get("state"),
            "maturity": g.get("maturity"),
            "challenge": g.get("challenge"),
            "diagnosed_failure_cause": (g.get("diagnosis") or {}).get("cause"),
            "diagnosed_failure_basis": (g.get("diagnosis") or {}).get("basis"),
            "causal_delta": g.get("causal_delta") or arch.get("causal_delta"),
            "mechanism": (arch.get("mechanism") or "")[:300],
            "intervention": (arch.get("intervention") or "")[:300],
            "predicted_effect": (arch.get("expected_effect") or "")[:300],
        })
    evolution_result = {
        "n_generations": lineage.get("n_generations"),
        "stop_reason": lineage.get("stop_reason"),
        "survivor_reached": lineage.get("survivor_reached"),
        "generations": gen_records,
    }

    # engineering realization
    eng_subsystems = (eng_spec.get("subsystems")
                      or (eng_spec.get("engineering") or {}).get("subsystems"))
    eng_tech_class = eng_spec.get("technology_class")
    cad_ledgers = sorted(
        p.name for p in run_dir.glob("CAD_PIPELINE_LEDGER_gen-*.json"))
    glbs = sorted(
        p.name for p in run_dir.glob("**/canonical*.glb"))
    engineering = {
        "engineering_specification_present": bool(eng_spec),
        "technology_class": eng_tech_class,
        "subsystems_present": bool(eng_subsystems),
        "cad_ledgers": cad_ledgers,
        "canonical_glbs": glbs,
    }

    # experiment state (R444-D fields; falsification threshold presence
    # is checked by the state-integrity enforcement, recorded here)
    sel = (decisive.get("selected") or {})
    inv_ke = (inv_spec.get("killer_experiment") or {})
    experiment = {
        "decisive_experiment_selected": bool(sel),
        "selected_experiment": (sel.get("experiment") or "")[:200],
        "killer_experiment_options": len(
            inv_ke.get("options_ranked") or []),
        "falsification_test_present": bool(
            mm.get("falsification_test")
            or inv_ke.get("falsification_test")),
    }

    # failure class (Art. LXI vocabulary: scientific vs infrastructure)
    failed_stages = final.get("failed_stages") or {}
    failure_class = None
    if failed_stages:
        failure_class = {
            "failed_stages": failed_stages,
            "package_state": (
                "PACKAGE_FAILED" if package_failed else
                "PACKAGE_DEFERRED" if package_deferred else
                "PACKAGE_PRODUCED" if (run_dir / "BUYER_PACKAGE.zip"
                                       ).exists() else "NO_PACKAGE_STAGE"),
            "class": (
                "INCOMPLETE_INFRASTRUCTURE_FAILURE"
                if any("transport" in str(v).lower() or "CALL_FAILED" in str(v)
                       for v in failed_stages.values())
                else "ENGINE_RUN_STAGE_FAILURE"),
        }

    # final epistemic state
    epistemic = {
        "final_status": final.get("final_status"),
        "epistemic_state": final.get("epistemic_state"),
        "reason": (final.get("reason") or "")[:400],
        "evidence_verified": final.get("evidence_verified"),
        "prior_art_status": final.get("prior_art_status"),
        "adjudication_verdict": final.get("adjudication_verdict"),
    }

    return {
        "problem": {
            "problem_id": problem["problem_id"],
            "device": problem["device"],
            "failure_mode": problem["failure_mode"],
            "domain": problem["domain"],
        },
        "problem_existence_result": premise_verdict,
        "evidence": {
            "retrieved_count": retrieved,
            "custody_records": sheet.get("evidence_n_items"),
            "classification_counts": ev_counts,
            "support_rate": sheet.get("evidence_support_rate"),
            "contradiction_rate": sheet.get("contradiction_rate"),
        },
        "mechanism_generated": {
            "synthesis_intervention": (mm.get("intervention") or "")[:300],
            "synthesis_mechanism": (mm.get("mechanism") or "")[:300],
            "mechanism_space_candidates": n_ms_candidates,
            "n_candidates_generated": sheet.get("n_candidates_generated"),
        },
        "distinctness_result": {
            "n_materially_distinct": sheet.get("n_materially_distinct"),
            "material_distinctness_rate": sheet.get(
                "material_distinctness_rate"),
        },
        "attack_result": {
            "adversarial_overall": attack_overall,
            "attack_survival": sheet.get("attack_survival"),
        },
        "evolution_result": evolution_result,
        "engineering_realization": engineering,
        "experiment_state": experiment,
        "final_epistemic_state": epistemic,
        "failure_class": failure_class,
        "time": {
            "runtime_s": sheet.get("runtime_s"),
        },
        "cost": {
            "gateway_calls_delta": calls_after - calls_before,
            "note": "call count from the gateway JSONL log; token counts "
                    "are recorded where the upstream transport returns "
                    "them (zai gateway logs usage when available)",
        },
        "frozen_metric_sheet": sheet,
    }


# ---------------------------------------------------------------------------
# battery
# ---------------------------------------------------------------------------
def _run_problem(problem: Dict[str, Any], runs_root: Path,
                 arm: str = "r401") -> Dict[str, Any]:
    pid = problem["problem_id"]
    run_dir = runs_root / arm / pid
    run_dir.mkdir(parents=True, exist_ok=True)
    marker = run_dir / "MEASUREMENT.json"
    r444_marker = run_dir / "R444_RECORD.json"
    if marker.exists() and r444_marker.exists():
        _log(f"{pid}: already measured (resumed)")
        return json.loads(r444_marker.read_text())
    calls_before = _gateway_call_count()
    res = W11._run_arm(arm, problem, run_dir)
    calls_after = _gateway_call_count()
    sheet = W11._measure(arm, run_dir, res)
    sheet["problem"] = {k: problem[k] for k in (
        "problem_id", "device", "failure_mode", "domain")}
    sheet["returncode"] = res.get("returncode")
    sheet["resumed"] = res.get("resumed")
    marker.write_text(json.dumps(sheet, indent=1, default=str))
    rec = _r444_problem_record(problem, run_dir, sheet,
                               calls_before, calls_after)
    r444_marker.write_text(json.dumps(rec, indent=1, default=str))
    _log(f"{pid}: final_status={rec['final_epistemic_state'].get('final_status')} "
         f"runtime={rec['time'].get('runtime_s')}s "
         f"calls={calls_after - calls_before}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen-only", action="store_true")
    ap.add_argument("--extension-only", action="store_true")
    args = ap.parse_args()

    frozen_hash = _sha256_file(FROZEN)
    extension_hash = _sha256_file(EXTENSION)
    frozen = json.loads(FROZEN.read_text())
    extension = json.loads(EXTENSION.read_text())
    _log(f"frozen benchmark: {len(frozen['problems'])} problems, "
         f"sha256={frozen_hash[:16]}...")
    _log(f"r444 extension: {len(extension['problems'])} problems, "
         f"sha256={extension_hash[:16]}...")

    problems: List[Dict[str, Any]] = []
    runs_roots: Dict[str, Path] = {}
    if not args.extension_only:
        problems += frozen["problems"]
    if not args.frozen_only:
        problems += extension["problems"]

    # the W11 runner's subprocess env pins the zai provider — apply the
    # same pins to THIS process (the gateway is already running)
    for k, v in W11._subprocess_env().items():
        os.environ[k] = v

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                          capture_output=True, text=True).stdout.strip()
    battery: Dict[str, Any] = {
        "battery_version": "r444-benchmark-battery/1.0.0",
        "measured_at_head": head,
        "frozen_benchmark_sha256": frozen_hash,
        "r444_extension_sha256": extension_hash,
        "arm": "r401 (the HEAD engine — the current production engine)",
        "success_definition_declared_before_run": (
            "COVERAGE, not quality: every problem ends with a typed "
            "record. The frozen benchmark's own headline (MD-EST; "
            "fraction of problems with MD-EST >= 3; mean MD-EST) is "
            "reported with no new threshold and no self-assigned "
            "success rate. REJECTED / INVENTION_REQUIRES_EXPERIMENT / "
            "EVOLVED_INVENTION_CANDIDATE / typed INCOMPLETE_* states "
            "are all honest outcomes (Art. LXI)."),
        "problems": {},
    }

    t0 = time.time()
    for problem in problems:
        pid = problem["problem_id"]
        runs_root = (FROZEN_RUNS if pid.startswith("bench-p")
                     else EXT_RUNS)
        try:
            rec = _run_problem(problem, runs_root)
            battery["problems"][pid] = rec
        except Exception as exc:  # noqa: BLE001
            _log(f"{pid}: DRIVER DEFECT — {type(exc).__name__}: {exc}")
            battery["problems"][pid] = {
                "problem": {"problem_id": pid,
                            "domain": problem.get("domain")},
                "driver_defect": f"{type(exc).__name__}: {exc}",
            }
        # persist after every problem (resumable, honest partial state)
        battery["measured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())
        battery["elapsed_s_total"] = round(time.time() - t0, 1)
        OUT.write_text(json.dumps(battery, indent=1, default=str))

    # the frozen benchmark's own headline, computed over ALL measured
    # problems with the SAME instrument (no new threshold)
    done = [r for r in battery["problems"].values()
            if r.get("frozen_metric_sheet")]
    if done:
        sheets = [r["frozen_metric_sheet"] for r in done]
        battery["headline"] = {
            "n_problems_measured": len(done),
            "mean_candidates": round(sum(
                s.get("n_candidates_generated") or 0
                for s in sheets) / len(done), 2),
            "mean_materially_distinct": round(sum(
                s.get("n_materially_distinct") or 0
                for s in sheets) / len(done), 2),
            "mean_md_est": round(sum(
                s.get("md_est_count") or 0 for s in sheets) / len(done), 2),
            "n_md_est_threshold_pass": sum(
                1 for s in sheets if s.get("md_est_threshold_pass")),
            "headline": (
                "fraction of problems with MD-EST >= 3: "
                f"{sum(1 for s in sheets if s.get('md_est_threshold_pass'))}"
                f"/{len(done)}"),
            "by_domain": {
                r["problem"]["domain"]: (
                    r["final_epistemic_state"].get("final_status"))
                for r in done},
        }
    OUT.write_text(json.dumps(battery, indent=1, default=str))
    _log(f"battery written -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
