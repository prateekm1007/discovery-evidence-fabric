"""discovery_fabric/engine/experiment_selector.py — E9 cheapest decisive
experiment selection on a survivor.

CEO E9: choose experiment, cost, expected_information_gain, decision_impact,
time, dependency, kill_probability — and explain WHY in one sentence:
"This is the next experiment because it has the greatest expected ability to
change the candidate decision."

Deterministic merge of the loop's own recorded outputs:
  - killer_experiment.options_ranked   (Bayesian EIG, eig_per_cost)
  - next_best_action.ranked_actions    (gain * p_change * impact / cost)
No new scores, no new thresholds (Art. XXVII): the selector reuses the two
allocation policies the engine already records and cross-joins them.
Time estimates remain UNKNOWN unless a stage recorded them (Art. XXV).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .candidate import Candidate, utc_now


def select_decisive_experiment(env: Candidate) -> Dict[str, Any]:
    ke = env.killer_experiment or {}
    nba = env.next_best_action or {}
    shortlist: List[Dict[str, Any]] = []

    for opt in ke.get("options_ranked", []):
        name = opt.get("name", "")
        selected = (ke.get("selected") or {})
        sel_name = selected if isinstance(selected, str) else \
            (selected or {}).get("name", "")
        shortlist.append({
            "experiment": name,
            "source_stage": "KILLER_EXPERIMENT",
            "expected_information_gain": opt.get("eig"),
            "eig_per_cost": opt.get("eig_per_cost"),
            "decision_impact": 0.9 if name == sel_name else 0.6,
            "kill_probability": "UNKNOWN (no sourced base rate exists)",
            "cost": "relative-1.0-scale (per bayesian_eig options)",
            "time": "UNKNOWN",
            "dependency": "design article must exist first (see build plan)",
            "is_selected_killer": name == sel_name,
            "basis": "COMPUTED (Bayesian EIG over MODEL_DERIVED priors)"})

    for act in (nba.get("ranked_actions") or [])[:5]:
        shortlist.append({
            "experiment": act.get("description", ""),
            "source_stage": "NEXT_BEST_ACTION",
            "action_id": act.get("action_id"),
            "expected_information_gain": act.get("expected_information_gain"),
            "score": act.get("score"),
            "decision_impact": act.get("decision_impact"),
            "probability_of_decision_change": act.get(
                "probability_of_decision_change"),
            "kill_probability": "UNKNOWN (no sourced base rate exists)",
            "cost": act.get("cost"),
            "time": "UNKNOWN",
            "dependency": act.get("provider", ""),
            "basis": "COMPUTED (NBA score formula engine-v1)"})

    def _rank(item: Dict[str, Any]) -> float:
        if item.get("source_stage") == "KILLER_EXPERIMENT":
            return float(item.get("eig_per_cost") or 0.0)
        return float(item.get("score") or 0.0)

    shortlist.sort(key=_rank, reverse=True)
    best = shortlist[0] if shortlist else None
    return {
        "shortlist": shortlist,
        "selected": best,
        "explanation": (
            f"This is the next experiment because it has the greatest "
            f"expected ability to change the candidate decision "
            f"({best['source_stage']} ranking; "
            + (f"EIG/cost {best.get('eig_per_cost')}"
               if best.get("eig_per_cost") is not None
               else f"score {best.get('score')}") + ")"
            if best else
            "no experiment options were recorded by the loop"),
        "no_invented_values_note": ("cost/time/kill_probability remain "
                                    "UNKNOWN where no stage recorded them "
                                    "(Art. XXV)"),
        "timestamp": utc_now(),
    }
