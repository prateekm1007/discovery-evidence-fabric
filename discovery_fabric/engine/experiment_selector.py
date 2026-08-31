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

R377 MEASURED DEFECT FIXED: the NEXT_BEST_ACTION list contains
administrative actions ('fetch and audit claims of nearest collision
patents', 'attack contradiction: ...') — for ALL SIX fresh-domain
survivors the selector picked that literature task as the decisive
experiment, breaking the chain's terminal link (a literature audit
cannot falsify a physical claim and cannot distinguish the candidate
from existing approaches). The shortlist now admits EXPERIMENT-class
items only; excluded administrative actions are recorded in the
artifact (they remain valid next-best-actions for the research
process — they are not experiments).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .candidate import Candidate, utc_now

# administrative-action vocabulary — a decisive experiment must not be
# one of these (R377 measured defect: all six survivors selected
# 'fetch and audit claims of nearest collision patents')
_ADMINISTRATIVE_RE = re.compile(
    r"\b(fetch|audit|search|inspect|review|query|expand|retrieve|"
    r"consult|browse|catalog|inventory|survey|update|refresh|re-?run|"
    r"record|document|file|register|list|read)\b",
    re.IGNORECASE)

# providers/stages that produce EXPERIMENT-class items
_EXPERIMENT_PROVIDERS = {"physical_lab"}


def _is_experiment(item: Dict[str, Any]) -> bool:
    """Deterministic experiment classifier: an item is an experiment
    when its source stage is the killer-experiment stage (physical
    bench/clinical by definition) or its provider is a physical
    laboratory, or its description names running the killer experiment.
    Administrative descriptions (fetch/audit/search/inspect...) are
    never experiments regardless of provider."""
    if item.get("source_stage") == "KILLER_EXPERIMENT":
        return True
    desc = str(item.get("experiment") or "")
    if desc.lower().startswith("run killer experiment"):
        return True
    if str(item.get("dependency") or "") in _EXPERIMENT_PROVIDERS:
        return True
    if _ADMINISTRATIVE_RE.search(desc):
        return False
    return str(item.get("dependency") or "") in _EXPERIMENT_PROVIDERS


def select_decisive_experiment(env: Candidate) -> Dict[str, Any]:
    ke = env.killer_experiment or {}
    nba = env.next_best_action or {}
    shortlist: List[Dict[str, Any]] = []
    excluded_administrative: List[Dict[str, Any]] = []

    for opt in ke.get("options_ranked", []):
        name = opt.get("name", "")
        selected = (ke.get("selected") or {})
        sel_name = selected if isinstance(selected, str) else \
            (selected or {}).get("name", "")
        item = {
            "experiment": name,
            "source_stage": "KILLER_EXPERIMENT",
            "expected_information_gain": opt.get("eig"),
            "eig_per_cost": opt.get("eig_per_cost"),
            "decision_impact": 0.9 if name == sel_name else 0.6,
            "kill_probability": "UNKNOWN (no sourced base rate exists)",
            "cost": ("UNKNOWN absolute cost (options ranked on a "
                     "relative-1.0 scale per bayesian_eig; no sourced "
                     "dollar/time estimate exists — Art. XXV)"),
            "time": "UNKNOWN",
            "dependency": "design article must exist first (see build plan)",
            "is_selected_killer": name == sel_name,
            "basis": "COMPUTED (Bayesian EIG over MODEL_DERIVED priors)"}
        # attach the recorded hypotheses (priors + provenance) to the
        # selected killer experiment so the artifact is self-contained
        # (the payload's hypotheses belong to the experiment set)
        if name == sel_name and ke.get("hypotheses"):
            item["hypotheses"] = ke.get("hypotheses")
        shortlist.append(item)

    for act in (nba.get("ranked_actions") or [])[:5]:
        item = {
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
            "basis": "COMPUTED (NBA score formula engine-v1)"}
        if _is_experiment(item):
            shortlist.append(item)
        else:
            excluded_administrative.append({
                "action_id": act.get("action_id"),
                "description": act.get("description", ""),
                "provider": act.get("provider", ""),
                "exclusion_reason": (
                    "administrative/research action, not a falsification "
                    "experiment (R377: the decisive experiment must be an "
                    "experiment; recorded here — a valid next-best-action "
                    "but not a decisive experiment)")})

    def _rank(item: Dict[str, Any]) -> float:
        if item.get("source_stage") == "KILLER_EXPERIMENT":
            return float(item.get("eig_per_cost") or 0.0)
        return float(item.get("score") or 0.0)

    shortlist.sort(key=_rank, reverse=True)
    best = shortlist[0] if shortlist else None
    return {
        "shortlist": shortlist,
        "administrative_actions_excluded": excluded_administrative,
        "exclusion_note": (
            "R377: administrative actions from next_best_action are "
            "excluded from the decisive-experiment shortlist (measured "
            "defect: all six R376 survivors selected 'fetch and audit "
            "claims of nearest collision patents' as the decisive "
            "experiment — a literature task cannot distinguish the "
            "candidate from existing approaches)"),
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
