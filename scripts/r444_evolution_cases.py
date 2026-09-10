#!/usr/bin/env python3
"""scripts/r444_evolution_cases.py — R444-C: run the three frozen
evolution cases (intentionally imperfect initial candidates) through
the CURRENT HEAD engine and record the full causal-evolution chain per
case: generation N, diagnosed failure cause, causal delta, new
mechanism, predicted effect, re-evaluation, generation N+1.

The record is extracted FROM THE RUN'S OWN LINEAGE ARTIFACTS (never
re-authored). A case with 0 evolution generations / null causal delta
is recorded as NO_EVOLUTION — the state-integrity validators make the
EVOLVED misclassification mechanically impossible.

Usage:
  python3 scripts/r444_evolution_cases.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CASES_PATH = REPO_ROOT / "R444" / "EVOLUTION_CASES" / "FROZEN_CASES.json"
RUNS_DIR = REPO_ROOT / "R444" / "EVOLUTION_CASES" / "RUNS"
OUT = REPO_ROOT / "R444" / "EVOLUTION_RESULTS.json"


def _log(msg: str) -> None:
    print(f"[r444-evolution] {msg}", flush=True)


def _j(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def _extract_chain(run_dir: Path) -> Dict[str, Any]:
    """The full generation chain from the run's own records."""
    lineage = _j(run_dir / "INVENTION_LINEAGE.json")
    final = _j(run_dir / "final_state.json")
    source = lineage.get("final_state") if lineage else final
    gens: List[Dict[str, Any]] = []
    for g in lineage.get("generations") or []:
        arch = g.get("architecture") or {}
        gens.append({
            "generation": g.get("gen"),
            "origin": g.get("origin"),
            "invention_id": g.get("invention_id"),
            "parent_id": g.get("parent_id"),
            "state": g.get("state"),
            "maturity": g.get("maturity"),
            # diagnosed failure cause — the RECORDED diagnosis of why
            # this generation did not survive
            "diagnosed_failure_cause": (g.get("diagnosis") or {}).get("cause"),
            "diagnosed_failure_basis": (g.get("diagnosis") or {}).get("basis"),
            # the causal delta THIS generation introduced (null for gen 1)
            "causal_delta": g.get("causal_delta")
            or arch.get("causal_delta"),
            # the new mechanism + predicted effect
            "mechanism": (arch.get("mechanism") or "")[:400],
            "intervention": (arch.get("intervention") or "")[:400],
            "predicted_effect": (arch.get("expected_effect") or "")[:400],
            # the re-evaluation this generation faced
            "challenge": g.get("challenge") or {},
            "fresh_evidence": {
                "n_items": (g.get("fresh_evidence") or {}).get("n_items"),
                "snapshot_version": (g.get("fresh_evidence") or {}).get(
                    "snapshot_version"),
            } if g.get("fresh_evidence") else None,
        })
    # the survivor + the presentation decision
    ev = (source or {}).get("evolution") or {}
    contract = (source or {}).get("experiment_contract") or None
    return {
        "n_generations": lineage.get("n_generations"),
        "stop_reason": lineage.get("stop_reason"),
        "survivor_reached": lineage.get("survivor_reached"),
        "generations": gens,
        "final_status": (source or {}).get("final_status"),
        "final_reason": (source or {}).get("reason"),
        "experiment_contract": contract,
        "evolution_summary": ev,
    }


def _classify(chain: Dict[str, Any]) -> Dict[str, Any]:
    """Honest classification: EVOLVED requires >=1 generation beyond
    the baseline AND a recorded causal delta on the surviving lineage
    (the R443 validators + the R444-D contract gate compose in
    run.py; this classifier re-derives the same rule from the record
    so the round record shows the evidence, not the assertion)."""
    n_gens = int(chain.get("n_generations") or 0)
    delta_present = any(
        g.get("causal_delta") for g in chain.get("generations") or [])
    gen2plus = [g for g in chain.get("generations") or []
                if int(g.get("generation") or 0) >= 2]
    if n_gens >= 2 and delta_present and gen2plus:
        return {
            "classification": "CAUSAL_EVOLUTION_DEMONSTRATED",
            "evidence": (
                f"{n_gens} generations recorded; the causal delta is "
                "present on the lineage; the full chain "
                "(gen N diagnosis -> causal delta -> gen N+1 mechanism "
                "-> predicted effect -> re-evaluation) is extracted "
                "above from the run's own INVENTION_LINEAGE.json"),
        }
    return {
        "classification": "NO_EVOLUTION",
        "evidence": (
            f"n_generations={n_gens}, causal_delta_present={delta_present}"
            + (f", stop_reason={chain.get('stop_reason')}"
               if chain.get("stop_reason") else "")
            + " — recorded honestly; never classified as evolved "
              "(the R443/R444 state-integrity validators make the "
              "misclassification mechanically impossible)"),
    }


def main() -> int:
    cases = json.loads(CASES_PATH.read_text())
    results: Dict[str, Any] = {
        "results_version": "r444-evolution-results/1.0.0",
        "measured_at_head": _git_head(),
        "cases_file_sha256": _sha256(CASES_PATH),
        "per_case": {},
    }
    # the same provider pins the W11 battery uses (the documented zai
    # transport path; recorded in every run's provenance — never silent)
    for var in ("ENGINE_SYNTHESIS_PROVIDER", "ENGINE_ATTACK_PROVIDER",
                "ENGINE_CAD_PROVIDER", "ENGINE_IMPROVEMENT_PROVIDER",
                "ENGINE_TECHNICAL_PROVIDER", "ENGINE_LLM_PROVIDER"):
        import os
        os.environ.setdefault(var, "zai")
    import os
    os.environ.setdefault("ENGINE_GRID_PROVIDERS", "zai")
    os.environ.setdefault("ENGINE_ENSEMBLE_PROVIDERS", "zai")
    from discovery_fabric.engine.run import EngineRun
    for case in cases["cases"]:
        cid = case["case_id"]
        problem = case["problem"]
        run_dir = RUNS_DIR / problem["problem_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        if not (run_dir / "final_state.json").exists():
            _log(f"{cid}: running (intentionally imperfect initial "
                 f"candidate: {case['intentional_imperfection']['naive_mechanism_class']})")
            run = EngineRun(problem, str(run_dir),
                            run_id=f"r444-evol:{problem['problem_id']}",
                            package_registry_path=str(
                                run_dir / "PACKAGE_ID_REGISTRY.json"))
            t0 = time.time()
            run.run()
            elapsed = round(time.time() - t0, 1)
        else:
            elapsed = None
            _log(f"{cid}: already run (resumed)")
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
        _log(f"{cid}: {results['per_case'][cid]['classification']['classification']}"
             f" (n_gens={chain.get('n_generations')}, "
             f"final={chain.get('final_status')})")

    # summary
    cl = [v["classification"]["classification"]
          for v in results["per_case"].values()]
    results["summary"] = {
        "n_cases": len(cl),
        "n_causal_evolution_demonstrated": cl.count(
            "CAUSAL_EVOLUTION_DEMONSTRATED"),
        "n_no_evolution": cl.count("NO_EVOLUTION"),
        "note": "NO_EVOLUTION is an honest outcome; the directive's "
                "impossible state (0 generations + null delta "
                "classified as evolved) is mechanically prevented "
                "(tests/test_r444_state_integrity.py)",
    }
    OUT.write_text(json.dumps(results, indent=1, default=str))
    _log(f"results -> {OUT}")
    return 0


def _git_head() -> str:
    import subprocess
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
        capture_output=True, text=True).stdout.strip()


def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
