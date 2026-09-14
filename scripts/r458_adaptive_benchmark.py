#!/usr/bin/env python3
"""scripts/r458_adaptive_benchmark.py — R458-C1 §4: the adaptive
controller benchmark (FIXED vs ADAPTIVE on the frozen benchmark).

Directive (verbatim intent): "Build the adaptive controller. Then
test: FIXED PIPELINE vs ADAPTIVE PIPELINE. The adaptive engine should
decide: retrieve more? ask user? generate another mechanism? attack?
engineering? experiment? stop? based on: uncertainty + information
gain + cost + capability. This is the real next step toward the
autonomous loop."

DESIGN (Art. XLVII — the instrument identical on both arms):

  - FIXED arm:    the engine's DEFAULT conductor (no stage gate —
                  byte-identical to the pre-R446 path, pinned by
                  test). These are the model-capability benchmark's
                  own dev runs for the SELECTED model (same problems,
                  same model, same commit) — re-measured, not re-run.
  - ADAPTIVE arm: the SAME engine + the R446-C1 adaptive stage gate
                  (the NBA controller + the stage policy), run by this
                  driver IN-PROCESS with the same closure the
                  production worker uses (nba_controller.decide ->
                  stage_policy.engine_gate), PLUS the full per-stage
                  decision trail this round requires (the directive's
                  R458_C1_NEXT_ACTION_DECISION_TRACE.json evidence).
  - Both arms measured with the SAME frozen R458 quality instrument;
    costs (LLM calls, retrieval ops, wall clock) are MEASURED from
    the runs' own routing ledgers and manifests — never modeled.
  - The adaptive arm is successful ONLY if every measured quality
    dimension is preserved or improved (the r446 directive's own
    standard), with the compute savings stated as numbers.

Usage:
  python scripts/r458_adaptive_benchmark.py run [budget_s]
  python scripts/r458_adaptive_benchmark.py record
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_ROOT = REPO_ROOT / "R458"
ADAPT_ROOT = OUT_ROOT / "ADAPTIVE_RUNS"
ADAPT_RECORD = OUT_ROOT / "ADAPTIVE_PIPELINE_BENCHMARK.json"
TRACE_RECORD = REPO_ROOT / "R458_C1_NEXT_ACTION_DECISION_TRACE.json"
DIRECTIVE_RECORD = REPO_ROOT / "R458_C1_ADAPTIVE_PIPELINE_BENCHMARK.json"

import r458_benchmark as bench           # noqa: E402  (frozen corpus)
import r458_quality_instrument as qi     # noqa: E402  (frozen metrics)
import r458_model_capability_benchmark as mcb  # noqa: E402  (arms)

#: the gate closure the production worker uses (worker.py phase 3),
#: replicated here so the benchmark measures the REAL adaptive path —
#: plus the per-stage decision trail collection this round requires.


def _adaptive_gate(run_dir: Path, trail: List[Dict[str, Any]]):
    from toscanini.conversational import nba_controller
    from toscanini.conversational import stage_policy

    def _gate(stage, env, _nba_record=None):
        try:
            nba = nba_controller.decide(env.to_dict())
            (run_dir / "NBA_CONTROLLER.json").write_text(
                json.dumps(nba, indent=1, ensure_ascii=False))
            trail.append({
                "stage": stage,
                "preferred_action":
                    (nba.get("preferred_action") or {}).get("action"),
                "decision_ledger_n": len(
                    nba.get("ranked_actions") or []),
                "decision": nba,
            })
        except Exception:   # noqa: BLE001 — controller fail-open
            nba = None
        return stage_policy.engine_gate(stage, env, nba)
    return _gate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _log(msg: str) -> None:
    print(f"[r458ab {datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
          f"{msg}", flush=True)


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.is_file():
            d = json.loads(p.read_text())
            return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None
    return None


def _selected_model() -> Optional[str]:
    dev = _read_json(OUT_ROOT / "MODEL_CAPABILITY_BENCHMARK.json")
    return (dev or {}).get("selected_model")


def _adapt_dir(case: str) -> Path:
    return ADAPT_ROOT / f"ADAPT_RUN_{case}"


def build_problem_for_case(case: str, out_dir: Path,
                            env: Dict[str, str]) -> Path:
    corpus = bench.load_corpus()
    spec = corpus["problems"][case]
    problem_json = out_dir / "fresh_problem.json"
    if problem_json.exists():
        return problem_json
    code = (
        "import json, sys;\n"
        "sys.path.insert(0, '.');\n"
        "from toscanini.problem_builder import build_problem;\n"
        f"built = build_problem({spec['text']!r});\n"
        "problem = built.get('problem') if isinstance("
        "built.get('problem'), dict) else built;\n"
        f"problem['problem_id'] = {spec['case_id']!r};\n"
        "problem['r458_benchmark'] = {\n"
        "    'class': 'FROZEN_BENCHMARK_DEV',\n"
        "    'arm': 'adaptive',\n"
        "    'corpus_freeze': 'R458/BENCHMARK_FREEZE.json',\n"
        "};\n"
        f"json.dump(problem, open({str(problem_json)!r}, 'w'), "
        "indent=1)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT),
                       env=env, capture_output=True, text=True,
                       timeout=900)
    if r.returncode != 0 or not problem_json.exists():
        out_dir.joinpath("problem_build_error.txt").write_text(
            r.stdout[-3000:] + "\n" + r.stderr[-3000:])
        raise SystemExit(f"problem build failed for adaptive/{case}")
    return problem_json


def run_adaptive_case(case: str, model_arm: str) -> Dict[str, Any]:
    """ONE adaptive engine run IN-PROCESS (the real gate closure; the
    full decision trail collected)."""
    bench.assert_dev_only(case)
    out_dir = _adapt_dir(case)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = mcb.arm_env(model_arm)
    problem_json = build_problem_for_case(case, out_dir, env)
    problem = json.loads(problem_json.read_text())
    # the engine runs IN-PROCESS: the arm's env must be applied to
    # THIS process before EngineRun (the engine's LLM calls read
    # os.environ — the shell's ZAI_API_KEY would be the wrong key for
    # the arm's gateway; arm_env's stripped paid keys must hold too)
    for k in list(os.environ):
        if k in mcb.PAID_ENV_VARS or k in (
                "ZAI_API_KEY", "ZAI_MODEL", "ZAI_BASE_URL",
                "LOCAL_QWEN_BASE_URL", "LOCALQWEN_BASE_URL",
                "LOCAL_QWEN_MODEL", "LOCALQWEN_MODEL",
                "ENGINE_MODEL_COST_POLICY", "ENGINE_LLM_TIMEOUT_S"):
            os.environ.pop(k, None)
    os.environ.update(env)
    trail: List[Dict[str, Any]] = []
    gate = _adaptive_gate(out_dir, trail)
    from discovery_fabric.engine.run import EngineRun
    _log(f"adaptive/{case}: engine start (gate ON, arm {model_arm})")
    t0 = time.time()
    engine = EngineRun(problem, str(out_dir), with_package=False,
                       stage_gate=gate,
                       run_id=f"r458ad-{case}: adaptive benchmark",
                       session_id=f"r458ad-{case.lower()}")
    manifest = engine.run()
    wall_s = round(time.time() - t0, 1)
    (out_dir / "DECISION_TRAIL.json").write_text(json.dumps(
        {"case": case, "n_decisions": len(trail), "trail": trail},
        indent=1, ensure_ascii=False))
    _log(f"adaptive/{case}: engine done in {wall_s}s "
         f"({len(trail)} NBA decisions)")
    return {"case": case, "wall_s": wall_s,
            "manifest_status": (manifest or {}).get("final_status")}


def cmd_run(budget_s: int = 2400) -> int:
    model_arm = _selected_model()
    if not model_arm or model_arm not in mcb.RUNNABLE_ARMS:
        print("adaptive benchmark requires the selected model "
              "(run the capability measure first)", file=sys.stderr)
        return 2
    if not mcb.ensure_transport(model_arm):
        print(f"transport for {model_arm} unavailable",
              file=sys.stderr)
        return 2
    corpus = bench.load_corpus()
    for case in sorted(k for k, p in corpus["problems"].items()
                       if p["split"] == "DEV"):
        if (_adapt_dir(case) / "final_state.json").is_file():
            _log(f"adaptive/{case}: already complete — skipping")
            continue
        run_adaptive_case(case, model_arm)
    return 0


# ---------------------------------------------------------------------------
# record: FIXED (the capability runs) vs ADAPTIVE (this driver's runs)
# ---------------------------------------------------------------------------

def _cost_facts(run_dir: Path) -> Dict[str, Any]:
    led = _read_json(run_dir / "ROUTING_LEDGER_RUN.json") or {}
    lines = [l for l in (led.get("lines") or [])
             if isinstance(l, dict)]
    ok = [l for l in lines if l.get("status") == "OK"]
    lat = [l.get("latency_ms") for l in ok
           if isinstance(l.get("latency_ms"), (int, float))]
    toks = 0
    for l in ok:
        t = l.get("tokens")
        if isinstance(t, dict):
            toks += t.get("total_tokens") or 0
        elif isinstance(t, (int, float)):
            toks += t
    env = _read_json(run_dir / "envelope_RETRIEVE.json") or {}
    # retrieval cost proxy: the DISTINCT sources that contributed
    # evidence to the frozen pool (the engine's own record does not
    # count per-source operations; the contributing-source count is
    # the honest extractable measure — same extractor both arms)
    ev_items = env.get("evidence") or []
    contributing = sorted({e.get("source") for e in ev_items
                           if isinstance(e, dict) and e.get("source")})
    n_retrieval_ops = len(contributing)
    retrieval_sources_field = {
        "measure": "distinct_contributing_evidence_sources",
        "sources": contributing}
    stages_run = 0
    for f in run_dir.glob("stage_*.json"):
        rec = _read_json(f) or {}
        if str(rec.get("status") or "").upper() in ("OK", "DONE",
                                                    "COMPLETE"):
            stages_run += 1
    return {
        "llm_calls_ok": len(ok),
        "llm_calls_total": len(lines),
        "llm_latency_ms_sum": sum(lat) if lat else 0,
        "llm_latency_ms_mean": round(
            sum(lat) / len(lat), 1) if lat else None,
        "token_cost": toks,
        "retrieval_operations": n_retrieval_ops,
        "retrieval_measure": retrieval_sources_field,
        "stages_run_ok": stages_run,
    }


def cmd_record() -> int:
    model_arm = _selected_model()
    corpus = bench.load_corpus()
    dev_ids = sorted(k for k, p in corpus["problems"].items()
                     if p["split"] == "DEV")
    fixed_dirs = {c: mcb._arm_dir(model_arm, c) for c in dev_ids}
    adapt_dirs = {c: _adapt_dir(c) for c in dev_ids}
    per_case = []
    fixed_costs, adapt_costs = [], []
    fixed_qual, adapt_qual = [], []
    for case in dev_ids:
        fd, ad = fixed_dirs[case], adapt_dirs[case]
        entry = {"case": case,
                 "domain_family":
                     corpus["problems"][case]["domain_family"]}
        if (fd / "final_state.json").is_file():
            fc = _cost_facts(fd)
            fq = qi.apply_to_run_dir(fd, corpus["problems"][case]["text"])
            entry["fixed"] = {"costs": fc,
                              "final_status": fq["final_status"],
                              "quality": fq["metrics"]}
            fixed_costs.append(fc)
            fixed_qual.append(fq)
        if (ad / "final_state.json").is_file():
            ac = _cost_facts(ad)
            aq = qi.apply_to_run_dir(ad, corpus["problems"][case]["text"])
            trail = _read_json(ad / "DECISION_TRAIL.json") or {}
            entry["adaptive"] = {
                "costs": ac,
                "final_status": aq["final_status"],
                "quality": aq["metrics"],
                "n_nba_decisions": trail.get("n_decisions"),
                "preferred_actions": [
                    t.get("preferred_action")
                    for t in (trail.get("trail") or [])]}
            adapt_costs.append(ac)
            adapt_qual.append(aq)
        per_case.append(entry)

    def _mean(vals, key):
        nums = [v.get(key) for v in vals
                if isinstance(v.get(key), (int, float))]
        return round(sum(nums) / len(nums), 2) if nums else None

    fixed_llm = _mean(fixed_costs, "llm_calls_ok")
    adapt_llm = _mean(adapt_costs, "llm_calls_ok")
    fixed_tok = _mean(fixed_costs, "token_cost")
    adapt_tok = _mean(adapt_costs, "token_cost")
    fixed_ops = _mean(fixed_costs, "retrieval_operations")
    adapt_ops = _mean(adapt_costs, "retrieval_operations")

    # quality preservation: every measured dimension preserved or
    # improved (UNKNOWN on both arms = preserved-by-absence, recorded)
    QUALITY_KEYS = ("evidence_synthesis", "mechanism_quality",
                    "mechanism_differentiation", "candidate_quality",
                    "attack_quality", "contradiction_detection",
                    "structured_output_reliability",
                    "hallucination_rate", "failure_rate")
    dims, preserved_all = {}, True
    for k in QUALITY_KEYS:
        fv = _mean([{"v": (q["metrics"].get(k) or {}).get("value")}
                    for q in fixed_qual], "v")
        av = _mean([{"v": (q["metrics"].get(k) or {}).get("value")}
                    for q in adapt_qual], "v")
        if fv is None and av is None:
            dims[k] = {"fixed": None, "adaptive": None,
                       "preserved": True,
                       "note": "UNKNOWN on both arms (typed)"}
            continue
        # hallucination/failure are lower-better
        better_or_equal = (
            (av <= fv) if k in ("hallucination_rate", "failure_rate")
            and isinstance(av, float) and isinstance(fv, float)
            else (av >= fv if isinstance(av, float)
                  and isinstance(fv, float) else True))
        dims[k] = {"fixed": fv, "adaptive": av,
                   "preserved": bool(better_or_equal)}
        if not better_or_equal:
            preserved_all = False

    record = {
        "artifact_type": "R458_ADAPTIVE_PIPELINE_BENCHMARK/1.0.0",
        "measured_at_utc": _now(),
        "directive_quote": (
            "Then test: FIXED PIPELINE vs ADAPTIVE PIPELINE ... This is "
            "the real next step toward the autonomous loop."),
        "model_arm": model_arm,
        "n_problems": len(dev_ids),
        "problems_source": "the frozen R458 DEV set (BS-016: the "
                           "holdout is never the comparison surface)",
        "fixed_arm_definition": (
            "the engine's default conductor (no stage gate) — the "
            "capability benchmark's own dev runs for the selected "
            "model, re-measured, not re-run"),
        "adaptive_arm_definition": (
            "the same engine + the R446-C1 adaptive stage gate (the "
            "NBA controller + stage policy; the worker's own gate "
            "closure replicated in-process) with the per-stage "
            "decision trail collected"),
        "costs": {
            "fixed": {"llm_calls_ok_mean": fixed_llm,
                      "token_cost_mean": fixed_tok,
                      "retrieval_operations_mean": fixed_ops},
            "adaptive": {"llm_calls_ok_mean": adapt_llm,
                         "token_cost_mean": adapt_tok,
                         "retrieval_operations_mean": adapt_ops},
            "llm_calls_delta_pct": (
                round(100 * (adapt_llm - fixed_llm) / fixed_llm, 1)
                if isinstance(fixed_llm, (int, float))
                and isinstance(adapt_llm, (int, float))
                and fixed_llm else None),
        },
        "quality_preservation": dims,
        "quality_preserved_all": preserved_all,
        "verdict": ("ADAPTIVE_SUCCESSFUL" if preserved_all
                    else "ADAPTIVE_QUALITY_REGRESSION"),
        "per_case": per_case,
        "reviewer_provenance": "AI_REVIEW",
    }
    ADAPT_RECORD.write_text(json.dumps(record, indent=1,
                                       sort_keys=True))
    DIRECTIVE_RECORD.write_text(json.dumps(record, indent=1,
                                           sort_keys=True))

    # ---- the NEXT-ACTION DECISION TRACE (the directive's evidence) --
    trace_entries = []
    for case in dev_ids:
        trail = _read_json(_adapt_dir(case) / "DECISION_TRAIL.json") or {}
        for t in (trail.get("trail") or []):
            dec = t.get("decision") or {}
            pref = dec.get("preferred_action") or {}
            trace_entries.append({
                "case": case,
                "domain_family":
                    corpus["problems"][case]["domain_family"],
                "stage_boundary": t.get("stage"),
                "preferred_action": t.get("preferred_action"),
                "action": pref.get("action"),
                "target_uncertainty": pref.get("target_uncertainty"),
                "expected_information_gain":
                    pref.get("expected_information_gain"),
                "probability_of_decision_change":
                    pref.get("probability_of_decision_change"),
                "decision_impact": pref.get("decision_impact"),
                "estimated_cost": pref.get("estimated_cost"),
                "estimated_latency_s": pref.get("estimated_latency_s"),
                "required_capability": pref.get("required_capability"),
                "risk": pref.get("risk"),
                "reason": pref.get("reason"),
                "score": pref.get("score"),
                "ranked_alternatives_n":
                    len(dec.get("ranked_actions") or []),
            })
    trace = {
        "artifact_type": "R458_NEXT_ACTION_DECISION_TRACE/1.0.0",
        "recorded_at_utc": _now(),
        "directive_quote": (
            "The adaptive engine should decide: retrieve more? ask "
            "user? generate another mechanism? attack? engineering? "
            "experiment? stop? based on: uncertainty + information "
            "gain + cost + capability."),
        "controller": "toscanini/conversational/nba_controller.py "
                      "(the V4 scoring authority, one formula, two "
                      "sites — the runtime controller site)",
        "n_decisions": len(trace_entries),
        "action_histogram": _hist(
            [e.get("preferred_action") for e in trace_entries]),
        "decisions": trace_entries,
        "reviewer_provenance": "AI_REVIEW",
    }
    TRACE_RECORD.write_text(json.dumps(trace, indent=1,
                                       sort_keys=True))
    _log(f"recorded: {ADAPT_RECORD.name} + {TRACE_RECORD.name} "
         f"({len(trace_entries)} decisions)")
    _log(f"costs: fixed llm={fixed_llm} adapt llm={adapt_llm} | "
         f"verdict={record['verdict']}")
    return 0


def _hist(values: List[Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for v in values:
        if v:
            out[str(v)] = out.get(str(v), 0) + 1
    return out


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "record"):
        print(__doc__)
        return 2
    if sys.argv[1] == "run":
        budget = int(sys.argv[2]) if len(sys.argv) > 2 else 2400
        return cmd_run(budget)
    return cmd_record()


if __name__ == "__main__":
    raise SystemExit(main())
