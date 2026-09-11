#!/usr/bin/env python3
"""scripts/r445_evolution_rerun.py — R445-C: re-run the THREE FROZEN
causal-evolution cases (unchanged, sha-pinned) through the CURRENT HEAD
engine with the transport blocker RESOLVED, and record the full
causal-evolution chain per case from the run's own lineage artifacts.

Why this script exists (R445 directive section C):
  R444's three dedicated adversarial evolution cases ended honestly
  TRANSPORT_BLOCKED (z-ai upstream 429 quota exhausted after the W11
  battery; Art. LXI: infrastructure, never a scientific rejection).
  R445 re-runs the SAME frozen cases — the cases file is READ-ONLY here
  (sha256 asserted against the R444 record: any rewrite is an error) —
  into a FRESH run directory so the R444 blocked attempts are preserved
  as history (Art. XI), with the provider pinned to the measured-healthy
  path.

Transport resolution (measured at this session's start, recorded in the
output artifact — never silent):
  zai    : re-probed, still HTTP 429 upstream quota -> unusable now
  nvidia : healthy (measured live: 0.5 s tiny call, 13.2 s realistic
           mechanism prompt; the 2026-08-30 latency collapse is gone)
  chosen : nvidia, via the documented ENGINE_*_PROVIDER operator-override
           pattern (recorded in every call's provenance, Art. XXVII)

Classification honesty (unchanged from R444): a case is
CAUSAL_EVOLUTION_DEMONSTRATED only when the run's OWN lineage record
shows >=2 generations AND a recorded causal delta AND a gen>=2
generation; anything else (including another transport failure) is
recorded honestly as NO_EVOLUTION with its stop reason — never
classified as evolved (tests/test_r444_state_integrity.py makes the
misclassification mechanically impossible).

Usage:
  NVIDIA_API_KEY=... python3 scripts/r445_evolution_rerun.py [--case <id>]
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# frozen instruments (Art. IX: untouched)
CASES_PATH = REPO_ROOT / "R444" / "EVOLUTION_CASES" / "FROZEN_CASES.json"
R444_CASES_SHA = "7c4c2654ee9146202bd92f636769122a03eb52c32f6957c84be086c9b2fc449b"
R444_RUNS_DIR = REPO_ROOT / "R444" / "EVOLUTION_CASES" / "RUNS"  # history, preserved

# this round's outputs
RUNS_DIR = REPO_ROOT / "R445" / "EVOLUTION_RUNS"
OUT = REPO_ROOT / "R445" / "EVOLUTION_RESULTS.json"

PROVIDER = os.environ.get("R445_EVOLUTION_PROVIDER", "nvidia")
# the operator model pin (R418 class: {PROVIDER}_MODEL routes the ladder's
# PRIMARY rung to the measured-capable model). Measured this session on
# the engine's own 16-field evolution-generation prompt shape:
#   llama-3.2-11b-vision   13.3 s, 15/16 field lines  <- pinned
#   nemotron-3-super-120b  24.1 s,  9/16 field lines
#   deepseek-v4-flash      >90 s stall on this prompt class
#   nemotron-3.5-content-safety: sub-second but unparseable field output
#   (the catalog default assigns it STRONG capability it does not have —
#   the attempt-1 blocked-run root cause, preserved as history)
MODEL_PIN = os.environ.get("R445_EVOLUTION_MODEL_PIN",
                            "meta/llama-3.2-11b-vision-instruct")
PINNED_VARS = (
    "ENGINE_SYNTHESIS_PROVIDER", "ENGINE_ATTACK_PROVIDER",
    "ENGINE_CAD_PROVIDER", "ENGINE_IMPROVEMENT_PROVIDER",
    "ENGINE_TECHNICAL_PROVIDER", "ENGINE_LLM_PROVIDER",
    "ENGINE_GRID_PROVIDERS", "ENGINE_ENSEMBLE_PROVIDERS",
)


def _log(msg: str) -> None:
    print(f"[r445-evolution] {msg}", flush=True)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
        capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", default=[],
                    help="case ids to run (default: all); repeatable")
    args = ap.parse_args()

    # frozen-cases integrity: the file MUST be byte-identical to the R444
    # instrument. A rewritten cases file is an error, not an input.
    cases_sha = _sha256(CASES_PATH)
    if cases_sha != R444_CASES_SHA:
        _log(f"FROZEN_CASES.json sha mismatch: {cases_sha} != {R444_CASES_SHA}")
        return 2
    _log(f"frozen cases sha256 verified: {cases_sha}")

    cases = json.loads(CASES_PATH.read_text())
    selected = [c for c in cases["cases"]
                if not args.case or c["case_id"] in args.case]
    if not selected:
        _log(f"no case matched: {args.case}")
        return 2

    # provider pin — the explicit operator override (recorded, never
    # silent; same documented pattern the W11 battery used for zai)
    for var in PINNED_VARS:
        os.environ[var] = PROVIDER
    # the R418 model pin: the ladder's PRIMARY rung routes here
    if PROVIDER == "nvidia" and MODEL_PIN:
        os.environ["NVIDIA_MODEL"] = MODEL_PIN
    key = os.environ.get("NVIDIA_API_KEY", "")
    if PROVIDER == "nvidia" and not key:
        _log("NVIDIA_API_KEY not set in environment")
        return 2

    from discovery_fabric.engine.run import EngineRun
    # reuse the R444 extraction/classification verbatim (no re-authoring)
    from r444_evolution_cases import _extract_chain, _classify

    results: Dict[str, Any] = {
        "results_version": "r445-evolution-results/1.0.0",
        "measured_at_head": _git_head(),
        "cases_file": str(CASES_PATH.relative_to(REPO_ROOT)),
        "cases_file_sha256": cases_sha,
        "frozen_instrument_unchanged": True,
        "r444_blocked_runs_preserved_at": str(
            R444_RUNS_DIR.relative_to(REPO_ROOT)),
        "transport_resolution": {
            "zai": ("re-probed this session: upstream 429 quota "
                    "(z-ai CLI live probe failed) — unusable"),
            "nvidia": ("measured healthy this session: 0.5 s tiny call, "
                       "13.2 s realistic mechanism prompt"),
            "chosen_provider": PROVIDER,
            "model_pin": MODEL_PIN,
            "model_pin_evidence": (
                "measured on the 16-field evolution-generation prompt "
                "shape: llama-3.2-11b-vision 13.3 s with 15/16 valid "
                "field lines; nemotron-3-super-120b 24.1 s with 9/16; "
                "deepseek-v4-flash stalled >90 s; nemotron-3.5-content-"
                "safety answers sub-second but without parseable field "
                "lines (the catalog STRONG-capability default misroutes "
                "generation tasks to it)"),
            "pinned_env_vars": list(PINNED_VARS),
            "note": ("the R444 blocker resolved by switching to the "
                     "measured-healthy provider via the documented "
                     "ENGINE_*_PROVIDER operator-override pattern, plus "
                     "the R418 NVIDIA_MODEL pin to the measured-capable "
                     "model and the R445 ENGINE_LLM_TIMEOUT_S bound "
                     "(stalling endpoints rotate in <=90 s instead of "
                     "holding 240 s per attempt); recorded in every "
                     "call's provenance"),
        },
        "per_case": {},
    }

    for case in selected:
        cid = case["case_id"]
        problem = case["problem"]
        run_dir = RUNS_DIR / problem["problem_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        if not (run_dir / "run_manifest.json").exists():
            # run_manifest.json is the TRUE completion marker: it is
            # written AFTER the evolution pipeline + release records.
            # final_state.json alone can exist from a killed slice where
            # the standard pipeline rejected but the evolution loop was
            # still mid-flight (measured: x03 slice-13 kill) — treating
            # it as complete skipped the evolution re-engagement.
            _log(f"{cid}: running (intentionally imperfect initial "
                 f"candidate: {case['intentional_imperfection']['naive_mechanism_class']})")
            # resumable across sandbox process reaping: EngineRun restores
            # completed stages from the persisted envelopes (the documented
            # battery pattern — re-invoke until final_state.json appears)
            run = EngineRun(problem, str(run_dir),
                            run_id=f"r445-evol:{problem['problem_id']}",
                            package_registry_path=str(
                                run_dir / "PACKAGE_ID_REGISTRY.json"),
                            resume=run_dir.exists())
            t0 = time.time()
            try:
                run.run()
            except Exception as exc:  # noqa: BLE001
                _log(f"{cid}: RUN_ERROR {type(exc).__name__}: {exc} "
                     f"(re-invoke to resume from persisted stages)")
                raise
            elapsed = round(time.time() - t0, 1)
        else:
            elapsed = None
            _log(f"{cid}: already run (complete manifest present)")
            mf = run_dir / "run_manifest.json"
            if mf.exists():
                try:
                    man = json.loads(mf.read_text())
                    elapsed = man.get("elapsed_s")
                except Exception:  # noqa: BLE001
                    pass
        chain = _extract_chain(run_dir)
        results["per_case"][cid] = {
            "case": {
                "problem_id": problem["problem_id"],
                "device": problem["device"],
                "failure_mode": problem["failure_mode"],
                "domain": problem["domain"],
            },
            "intentional_imperfection": case["intentional_imperfection"],
            "run_dir": str(run_dir.relative_to(REPO_ROOT)),
            "elapsed_s": elapsed,
            "chain": chain,
            "classification": _classify(chain),
        }
        OUT.write_text(json.dumps(results, indent=1, default=str))
        _log(f"{cid}: "
             f"{results['per_case'][cid]['classification']['classification']} "
             f"(n_gens={chain.get('n_generations')}, "
             f"final={chain.get('final_status')}, "
             f"stop_reason={chain.get('stop_reason')})")

    cl = [v["classification"]["classification"]
          for v in results["per_case"].values()]
    results["summary"] = {
        "n_cases_this_invocation": len(cl),
        "n_causal_evolution_demonstrated": cl.count(
            "CAUSAL_EVOLUTION_DEMONSTRATED"),
        "n_no_evolution": cl.count("NO_EVOLUTION"),
        "directive_target": ("at least 2/3 cases demonstrate the full chain "
                             "gen-1 -> diagnosed cause -> causal delta -> "
                             "gen-2 -> predicted effect -> re-evaluation -> "
                             "survivor or explicit kill; three honest "
                             "failures are an acceptable outcome"),
        "note": "NO_EVOLUTION (including transport) is an honest outcome; "
                "never classified as evolved (state-integrity validators)",
    }
    OUT.write_text(json.dumps(results, indent=1, default=str))
    _log(f"results -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
