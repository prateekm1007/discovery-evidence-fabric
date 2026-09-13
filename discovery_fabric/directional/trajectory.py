"""Improvement-trajectory persistence (R450 §11).

    Candidate V1 -> failure F1 -> direction D1 -> mutation M1 ->
    result R1 -> causal update C1 -> Candidate V2 -> direction D2 -> ...

The trajectory is part of the INVENTION'S PROVENANCE: the machine
knows not only what it invented, but what interventions failed and
why. One file per run (IMPROVEMENT_TRAJECTORY.json), append-only
entries, every transition carrying ids + provenance — no hidden
parallel state, no second invention graph (the trajectory REFERENCES
the canonical generation records; it never duplicates them).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from discovery_fabric.directional.hypothesis import utc_now

TRAJECTORY_FILENAME = "IMPROVEMENT_TRAJECTORY.json"


def load_trajectory(run_dir: Path) -> Dict[str, Any]:
    p = Path(run_dir) / TRAJECTORY_FILENAME
    if p.exists():
        try:
            d = json.loads(p.read_text())
            if isinstance(d, dict):
                return d
        except Exception:  # noqa: BLE001 — corrupt -> fresh, disclosed
            pass
    return {
        "artifact_type": "IMPROVEMENT_TRAJECTORY",
        "schema_version": "trajectory/1.0",
        "created_at": utc_now(),
        "steps": [],
        "note": ("append-only: one step per (failure -> diagnosis -> "
                 "direction -> mutation -> evaluation -> observation -> "
                 "causal update) cycle; entries reference the canonical "
                 "generation records by id — this file never duplicates "
                 "invention state (no second canonical database)"),
    }


def append_step(run_dir: Path, step: Dict[str, Any]) -> Dict[str, Any]:
    """Append ONE trajectory step and persist. The step carries the
    full id chain; ids are never rewritten."""
    t = load_trajectory(run_dir)
    entry = dict(step)
    entry.setdefault("recorded_at", utc_now())
    t["steps"].append(entry)
    t["last_appended_at"] = utc_now()
    p = Path(run_dir) / TRAJECTORY_FILENAME
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(t, indent=1, ensure_ascii=False,
                            default=str))
    return t


def trajectory_summary(run_dir: Path) -> Dict[str, Any]:
    """Raw counters for the benchmark — no composite score (the
    directive: 'Do not invent a magical composite score. Report raw
    measurements first.')."""
    t = load_trajectory(run_dir)
    steps = t.get("steps") or []
    n = len(steps)
    supported = sum(1 for s in steps if _status(s, "hypothesis") ==
                    "SUPPORTED")
    falsified = sum(1 for s in steps if _status(s, "hypothesis") ==
                    "FALSIFIED")
    rejected = sum(1 for s in steps
                   if _status(s, "hypothesis") == "REJECTED")
    executed = sum(1 for s in steps
                   if _status(s, "hypothesis") == "EXECUTED")
    survived = sum(1 for s in steps
                   if (s.get("observation") or {}).get(
                       "gauntlet", {}).get("killed") is False)
    killed = sum(1 for s in steps
                 if (s.get("observation") or {}).get(
                     "gauntlet", {}).get("killed") is True)
    return {
        "n_steps": n,
        "hypotheses_rejected_by_ground_gate": rejected,
        "hypotheses_executed": executed,
        "hypotheses_supported_after_update": supported,
        "hypotheses_falsified_after_update": falsified,
        "mutations_survived_gauntlet": survived,
        "mutations_killed_by_gauntlet": killed,
        "successful_interventions_over_attempts": (
            f"{supported}/{executed}" if executed else "0/0"),
        "note": "raw counters only — no composite score computed",
    }


def _status(step: Dict[str, Any], key: str) -> Optional[str]:
    return ((step.get(key) or {}).get("status"))
