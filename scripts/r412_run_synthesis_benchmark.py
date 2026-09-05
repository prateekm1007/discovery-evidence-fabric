#!/usr/bin/env python3
"""scripts/r412_run_synthesis_benchmark.py — P0-3 driver.

Runs the pre-registered synthesis-model benchmark
(discovery_fabric/r412/synthesis_benchmark.py) over the frozen R411
evidence pools:

  1. per model (env-pinned, same as the calibration runner): one
     extraction pass over the three frozen problems (the frozen
     CROSS_DOMAIN_FORCING prompt, the R411 contract, 2600 tokens);
  2. deterministic downstream verifiers over every accepted candidate
     (no-fabrication gate already at parse; engineering gate; the R412
     collision screen; pairwise distinctness);
  3. the attacker (minimax-m3, the R411 instrument, measured
     NOT_CALIBRATED) on candidates passing every deterministic gate,
     CAPPED at 3 per model (disclosed cap);
  4. per-model metrics + the headline: qualified causal technology per
     unit compute (and the survival variant with its caveat).

Output: R412/SYNTHESIS_BENCHMARK/r412_synthesis_benchmark.json
"""
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "R412" / "CALIBRATION"))

from discovery_fabric.r412.synthesis_benchmark import (  # noqa: E402
    ATTACK_CAP_PER_MODEL, BENCHMARK_VERSION, FROZEN_DOMAINS,
    MODEL_PASSES, build_problem_prompt, downstream_verdicts,
    distinctness_analysis, json_load, load_frozen_problem,
    model_metrics, run_model_pass)

RUN = REPO / "R411" / "DISCOVERY_RUN"
OUT_DIR = REPO / "R412" / "SYNTHESIS_BENCHMARK"
ATTACKER_PINS = {
    "ENGINE_LLM_PROVIDER": "openrouter",
    "OPENROUTER_MODEL": "minimax/minimax-m3:free",
}


def _with_gateway(fn):
    """Run fn with the zai gateway up (child process; the calibration
    runner's lifecycle pattern)."""
    from calibration_runner import _ZaiGateway
    with _ZaiGateway():
        return fn()


def _run_attacks(qualified, problems):
    """Attack the qualified candidates with the R411 instrument
    (uncalibrated — the caveat travels with the results)."""
    from discovery_fabric.r411.attack import attack_candidate
    pool_by_domain = {p["domain_id"]: p for p in problems}
    results = []
    for cand in qualified[:ATTACK_CAP_PER_MODEL]:
        problem = pool_by_domain[cand.get("domain_id")]
        pa = {"relevant_records": []}  # benchmark scope: own-pool screen
        rec = attack_candidate(
            cand, problem["pool"], pa, generator_provider=None)
        results.append(rec)
    return results


def main() -> int:
    problems = [load_frozen_problem(d, RUN) for d in FROZEN_DOMAINS]

    # sanity: the frozen prompts are identical across models (the
    # comparability contract, checked before any call)
    prompts = [build_problem_prompt(p)[0] for p in problems]
    prompt_hashes = []
    import hashlib
    for p in prompts:
        prompt_hashes.append(hashlib.sha256(p.encode()).hexdigest())

    model_results = []
    for model_id, pins in MODEL_PASSES.items():
        env_keys = {k: v for k, v in pins.items()
                    if k not in ("needs_gateway",)}
        saved = {k: os.environ.get(k, "") for k in env_keys}
        for k, v in env_keys.items():
            os.environ[k] = v
        try:
            if pins.get("needs_gateway") == "yes":
                model_pass = _with_gateway(
                    lambda: run_model_pass(model_id, problems, RUN))
            else:
                model_pass = run_model_pass(model_id, problems, RUN)
        finally:
            for k, v in saved.items():
                if v:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

        downstream = downstream_verdicts(model_pass, problems)
        accepted = [c for pr in model_pass["per_problem"]
                    if pr.get("status") == "OK"
                    for c in pr["accepted"]]
        distinctness = distinctness_analysis(accepted)

        # attacker stage (capped, uncalibrated instrument disclosed)
        attack_results = []
        if downstream["qualified"]:
            saved_a = {k: os.environ.get(k, "") for k in ATTACKER_PINS}
            for k, v in ATTACKER_PINS.items():
                os.environ[k] = v
            try:
                attack_results = _run_attacks(
                    downstream["qualified"], problems)
            finally:
                for k, v in saved_a.items():
                    if v:
                        os.environ[k] = v
                    else:
                        os.environ.pop(k, None)

        metrics = model_metrics(
            model_pass, downstream, distinctness, attack_results)
        model_results.append({
            "model_id": model_id,
            "env_pins": env_keys,
            "extraction_pass": model_pass,
            "downstream": {
                "per_candidate": downstream["per_candidate"],
                "qualified_candidate_ids": [
                    c["candidate_id"] for c in downstream["qualified"]],
            },
            "distinctness": distinctness,
            "attack_results": [
                {k: a.get(k) for k in (
                    "candidate_id", "verdict", "kill_surfaces",
                    "final_objection", "attacker_provider",
                    "attacker_model", "independence_mode",
                    "prompt_hash", "output_hash")}
                for a in attack_results],
            "metrics": metrics,
        })

    report = {
        "artifact_type": "R412_SYNTHESIS_BENCHMARK",
        "benchmark_version": BENCHMARK_VERSION,
        "subject_inputs": {
            "problems": FROZEN_DOMAINS,
            "evidence_source": "R411 frozen DISCOVERY_RUN pools",
            "prompt_task": "CROSS_DOMAIN_FORCING (the R411 s6 call)",
            "prompt_sha256": prompt_hashes,
            "candidate_contract": (
                "the unmodified R411 extraction prompt, system string, "
                "and 2600-token cap; the unmodified parse gate — no "
                "prompt tuning (Art. LIX)"),
        },
        "verifiers": {
            "deterministic": [
                "no-fabrication parse gate (R411)",
                "engineering gate (R411 structural)",
                "early collision screen (R412 P0-2, own pool)",
                "pairwise mechanism distinctness (mechanism_space v2)",
            ],
            "llm": (
                "the R411 attacker (minimax-m3) on deterministically "
                "qualified candidates, capped at "
                f"{ATTACK_CAP_PER_MODEL} per model; the instrument is "
                "measured NOT_CALIBRATED (R412/P0-1) — survival is "
                "recorded, not a selection criterion"),
            "not_run": (
                "the F4a evidence span-verification proposer (cost-"
                "bounded benchmark; evidence support is measured at "
                "the deterministic citation level)"),
        },
        "models": model_results,
        "reviewer_provenance": "AI_REVIEW",
        "honest_notes": [
            "model selection is NOT performed by this benchmark "
            "(Art. LIX: measurement, not selection; any selection is a "
            "separate recorded operator decision)",
            "the pools are R411 campaign inputs; models are stateless "
            "per call — the same inputs are fresh for every arm",
            "wall_seconds measure the generation pass only (the "
            "deterministic verifiers run in milliseconds and are "
            "excluded; the attacker stage is excluded — it is the "
            "same instrument for every arm)",
            "the headline metric is qualified causal technology per "
            "unit compute; the survival variant carries the "
            "NOT_CALIBRATED attacker caveat",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "r412_synthesis_benchmark.json"
    out.write_text(json.dumps(report, indent=1))
    print(f"written: {out}")
    for m in model_results:
        met = m["metrics"]
        print(f"  {met['model_id']}: calls={met['calls']} "
              f"accepted={met['candidates_accepted']} "
              f"distinct={met['distinct_mechanisms']} "
              f"qualified={met['qualified_deterministic']} "
              f"survived={met['attacker_survived']} "
              f"wall={met['wall_seconds']}s "
              f"qualified/s={met['qualified_per_compute_second']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
