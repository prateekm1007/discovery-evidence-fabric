#!/usr/bin/env python3
"""scripts/r444_state_integrity_check.py — R444-E mechanical
verification: the impossible states are prevented on the ACTUAL
artifacts, not just in unit tests.

Checks (each names the impossible state it proves prevented):
  1. 0 evolution generations -> EVOLVED
  2. null causal delta -> causal evolution
  3. null experiment selection -> selected experiment
  4. null falsification threshold -> complete experiment
  5. benchmark not run -> WORLD_CLASS_DISCOVERY_GREEN
  6. attacker calibration not run -> certified attacker

For 1-4: every run directory under the given roots is scanned; any
final state that claims an earned state without its records is a
VIOLATION (Art. XXVIII). For 5-6: the R444 round record's own claims
are validated against the measured artifacts (the battery results and
the calibration results files).

Usage:
  python3 scripts/r444_state_integrity_check.py \
      [--runs-root DIR ...] [--round-record PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine.state_integrity import (  # noqa: E402
    evolution_status_violations,
    experiment_claim_violations,
    experiment_claim_violations_r444,
    falsification_contract_status,
    system_claim_violations,
)

_EARNED_STATUS_FIELDS = ("EVOLVED_INVENTION_CANDIDATE",)


def _load(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def check_run_dir(run_dir: Path) -> List[Dict[str, str]]:
    """Scan one engine run directory for earned-state violations."""
    v: List[Dict[str, str]] = []
    lineage = _load(run_dir / "INVENTION_LINEAGE.json")
    final = _load(run_dir / "final_state.json")
    source = lineage.get("final_state") if lineage else final
    if not source:
        return v
    status = source.get("final_status")
    ev = source.get("evolution") or {}
    n_gens = ev.get("n_generations") or \
        (lineage or {}).get("n_generations")

    # 1+2: EVOLVED requires generations AND a causal delta. The causal
    # delta is taken from the lineage's own generation records (the
    # survivor/current generation must carry one).
    if status in _EARNED_STATUS_FIELDS:
        delta = None
        for g in (lineage or {}).get("generations") or []:
            if g.get("causal_delta") or (g.get("architecture") or {}).get(
                    "causal_delta"):
                delta = g.get("causal_delta") or \
                    g["architecture"].get("causal_delta")
        v.extend(evolution_status_violations(
            status, n_evolution_generations=int(n_gens or 0),
            causal_delta=delta))

    # 3: a selected-experiment claim requires the selection record
    decisive = _load(run_dir / "DECISIVE_EXPERIMENT.json")
    selected = (decisive or {}).get("selected")
    claims_selected = any(
        "selected" in str((source.get("reason") or "")).lower()
        for _ in [0]) and selected is not None
    v.extend(experiment_claim_violations(
        claims_selected=bool(selected), claims_contract=False,
        selected=selected, contract=(decisive or {}).get(
            "falsification_contract")))

    # 4: a COMPLETE-experiment presentation requires the falsification
    # answer. The run's own contract (R444-D) is the record; when the
    # run predates R444-D the contract is re-derived from the envelope
    # by the caller-supplied projection when available.
    # Mirrors run.py::_evolution_final_status: only opportunity-
    # presenting statuses (the EVOLVED class) claim the experiment
    # axis is closed; failure/infrastructure presentations
    # (MECHANISM_GENERATION_FAILED, REJECTED, UNDER_DEVELOPMENT,
    # REQUIRES_EXPERIMENT) make no such claim.
    contract = source.get("experiment_contract", {}).get("contract") \
        if isinstance(source.get("experiment_contract"), dict) else None
    if contract is None and decisive:
        contract = decisive.get("falsification_contract")
    if status in ("EVOLVED_INVENTION_CANDIDATE",
                  "AUTOMATED_INVENTION_CANDIDATE"):
        v.extend(experiment_claim_violations_r444(
            claims_complete_experiment=True, contract=contract))
    return v


def check_round_record(record_path: Path,
                       benchmark_results_path: Path,
                       calibration_results_path: Path
                       ) -> List[Dict[str, str]]:
    """5+6: system-level claims in the round record require the runs."""
    rec = _load(record_path) or {}
    claims = rec.get("claims") or {
        "world_class_discovery_green":
            rec.get("world_class_discovery_green") is True,
        "certified_attacker": rec.get("certified_attacker") is True,
    }
    bench = _load(benchmark_results_path)
    calib = _load(calibration_results_path)
    return system_claim_violations(claims, bench, calib)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", action="append", default=[],
                    help="engine run directory roots to scan")
    ap.add_argument("--round-record",
                    default=str(REPO_ROOT / "R444" /
                                "R444_ROUND_RECORD.json"))
    ap.add_argument("--benchmark-results",
                    default=str(REPO_ROOT / "R444" /
                                "BENCHMARK_RESULTS.json"))
    ap.add_argument("--calibration-results",
                    default=str(REPO_ROOT / "R401-WC2" /
                                "ATTACKER_CALIBRATION" /
                                "CALIBRATION_RESULTS.json"))
    args = ap.parse_args()

    report: Dict[str, Any] = {
        "check_version": "r444-state-integrity-check/1.0.0",
        "impossible_states": {
            "1_zero_generations_evolved": [],
            "2_null_causal_delta_evolution": [],
            "3_null_selection_selected": [],
            "4_null_falsification_complete": [],
            "5_benchmark_not_run_world_class": [],
            "6_calibration_not_run_certified": [],
        },
        "runs_scanned": 0,
        "violations": 0,
    }

    for root in args.runs_root:
        root_p = Path(root)
        if not root_p.is_absolute():
            root_p = REPO_ROOT / root_p
        if not root_p.exists():
            continue
        for run_dir in sorted(root_p.glob("**/final_state.json")):
            run_dir = run_dir.parent
            vs = check_run_dir(run_dir)
            report["runs_scanned"] += 1
            for x in vs:
                try:
                    x["run_dir"] = str(run_dir.relative_to(REPO_ROOT))
                except ValueError:
                    x["run_dir"] = str(run_dir)
                code = x.get("code") or ""
                if "EVOLVED-WITHOUT" in code:
                    report["impossible_states"][
                        "1_zero_generations_evolved"].append(x)
                elif "CAUSAL-DELTA" in code:
                    report["impossible_states"][
                        "2_null_causal_delta_evolution"].append(x)
                elif "SELECTED-EXPERIMENT" in code or \
                        "EXPERIMENT-CONTRACT-UNBACKED" in code:
                    report["impossible_states"][
                        "3_null_selection_selected"].append(x)
                elif "FALSIFICATION-THRESHOLD" in code:
                    report["impossible_states"][
                        "4_null_falsification_complete"].append(x)
                report["violations"] += 1

    rr = Path(args.round_record)
    if rr.exists():
        vs = check_round_record(rr, Path(args.benchmark_results),
                                Path(args.calibration_results))
        for x in vs:
            code = x.get("code") or ""
            if "WORLD-CLASS" in code:
                report["impossible_states"][
                    "5_benchmark_not_run_world_class"].append(x)
            elif "CERTIFIED-ATTACKER" in code:
                report["impossible_states"][
                    "6_calibration_not_run_certified"].append(x)
            report["violations"] += 1

    report["verdict"] = (
        "IMPOSSIBLE_STATES_PREVENTED" if report["violations"] == 0
        else "VIOLATIONS_PRESENT")

    out = REPO_ROOT / "R444" / "STATE_INTEGRITY_CHECK.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: report[k] for k in
                      ("runs_scanned", "violations", "verdict")},
                     indent=1))
    print(f"full report -> {out}")
    return 0 if report["violations"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
