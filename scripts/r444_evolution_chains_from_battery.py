#!/usr/bin/env python3
"""scripts/r444_evolution_chains_from_battery.py — R444-C: extract the
full causal-evolution chains (generation N, diagnosed failure cause,
causal delta, new mechanism, predicted effect, re-evaluation,
generation N+1) from the BATTERY run directories — the fresh benchmark
problems whose initial candidates were rejected by the gauntlet and
evolved.

The extraction is FROM THE RUNS' OWN INVENTION_LINEAGE.json records
(never re-authored). Chains with 0 generations / null causal delta are
recorded as NO_EVOLUTION (never claimed as evolved).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

BATTERY_RESULTS = REPO_ROOT / "R444" / "BENCHMARK_RESULTS.json"
OUT = REPO_ROOT / "R444" / "EVOLUTION_CHAINS_BATTERY.json"


def _j(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def _chain_for(run_dir: Path) -> Dict[str, Any]:
    lineage = _j(run_dir / "INVENTION_LINEAGE.json")
    if not lineage:
        return {"present": False}
    gens: List[Dict[str, Any]] = []
    for g in lineage.get("generations") or []:
        arch = g.get("architecture") or {}
        diag = g.get("diagnosis") or {}
        gens.append({
            "generation": g.get("gen"),
            "origin": g.get("origin"),
            # diagnosed failure cause — why this generation failed
            "diagnosed_failure_cause": diag.get("cause"),
            "diagnosed_failure_basis": diag.get("basis"),
            # the causal delta introduced (null on gen 1)
            "causal_delta": g.get("causal_delta")
            or arch.get("causal_delta"),
            # the new mechanism + predicted effect
            "mechanism": (arch.get("mechanism") or "")[:300],
            "intervention": (arch.get("intervention") or "")[:300],
            "predicted_effect": (arch.get("expected_effect") or "")[:300],
            # the re-evaluation (challenge) this generation faced
            "challenge": g.get("challenge") or {},
            "state": g.get("state"),
            "maturity": g.get("maturity"),
        })
    fs = lineage.get("final_state") or {}
    return {
        "present": True,
        "n_generations": lineage.get("n_generations"),
        "stop_reason": lineage.get("stop_reason"),
        "survivor_reached": lineage.get("survivor_reached"),
        "final_status": fs.get("final_status"),
        "generations": gens,
    }


def main() -> int:
    battery = _j(BATTERY_RESULTS)
    problems = battery.get("problems") or {}
    out: Dict[str, Any] = {
        "extraction_version": "r444-evolution-chains/1.0.0",
        "source": "the R444 benchmark battery run directories (the "
                  "frozen 12 + the 4 software/ML extension problems)",
        "per_problem": {},
    }
    roots = {
        "bench-p": REPO_ROOT / "R401-WC2" / "BENCHMARK" / "RUNS" / "r401",
        "bench-x": REPO_ROOT / "R444" / "BENCHMARK_EXTENSION" / "RUNS"
                   / "r401",
    }
    n_evolved_chains = 0
    for pid in problems:
        root = roots[pid[:7]]
        run_dir = root / pid
        chain = _chain_for(run_dir)
        entry = {
            "domain": (problems[pid].get("problem") or {}).get("domain"),
            "final_status": chain.get("final_status")
            or (problems[pid].get("final_epistemic_state") or {}).get(
                "final_status"),
            "chain": chain,
        }
        # classification: the directive's impossible state is
        # mechanically impossible; the classification here re-derives
        # the rule from the record (evidence, not assertion)
        n_gens = int(chain.get("n_generations") or 0) if chain.get(
            "present") else 0
        delta = any(g.get("causal_delta") for g in
                    (chain.get("generations") or []))
        if n_gens >= 2 and delta:
            entry["classification"] = "CAUSAL_EVOLUTION_DEMONSTRATED"
            n_evolved_chains += 1
        else:
            entry["classification"] = (
                "NO_EVOLUTION"
                + ("_TRANSPORT_BLOCKED"
                   if chain.get("stop_reason") == "TRANSPORT_BLOCKED"
                   else ""))
        out["per_problem"][pid] = entry

    out["summary"] = {
        "n_problems": len(problems),
        "n_causal_evolution_demonstrated": n_evolved_chains,
        "n_no_evolution": len(problems) - n_evolved_chains,
        "impossible_state_prevention": (
            "generation_count = 0 / causal_delta = null is never "
            "classified as evolved — evolution_status_violations (R443) "
            "+ the R444-D contract gate (run.py) + "
            "tests/test_r444_state_integrity.py"),
    }
    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out["summary"], indent=1))
    print(f"chains -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
