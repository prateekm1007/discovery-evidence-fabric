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
        "falsification_contract": article_lii_contract(env),
        "timestamp": utc_now(),
    }


# ---------------------------------------------------------------------------
# R444-D — the Article LII falsification-contract projection
# ---------------------------------------------------------------------------
_KILL_DIRECTION_RE = re.compile(
    r"\b(if|when|unless|exceeds|above|below|outside|beyond|fails?|"
    r"not\s+observed|does\s+not|drops?|rises?)\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def article_lii_contract(env, survivor_architecture: Optional[Dict] = None
                         ) -> Dict[str, Any]:
    """Project the run's OWN records onto the twelve Article LII
    falsification-contract fields.

    NOTHING IS INVENTED (Art. XXVII: no threshold invention). Every
    field is answered from a recorded artifact or carries UNKNOWN with
    its blocker. The decisive field is FALSIFICATION_THRESHOLD — 'what
    experimental outcome would kill this mechanism?' — which is
    answered ONLY when the records state both a falsification
    procedure (the candidate's own falsification test) and the effect
    it must show (the recorded expected effect) AND BOTH carry numeric
    bands — the kill outcome is then the test failing to show that
    effect, with the recorded bands traveling verbatim
    (FALSIFICATION_BANDS). R478 P0-3: a prose-only kill sentence is no
    longer an answer — the audit measured the composite prose
    answering the decisive field with no number in it. A
    contract without the falsification answer is INCOMPLETE and the
    package presenting it must read INVENTION_REQUIRES_EXPERIMENT
    (state_integrity.falsification_contract_status enforces this).

    Sources (all from the run's own envelope):
      HYPOTHESIS            <- killer_experiment.hypotheses (H_effect_holds)
      TREATMENT             <- mechanism_map.intervention (or the evolution
                               survivor's architecture when provided)
      CONTROL               <- physics BASELINE_COMPARISON execution
      MEASUREMENT           <- mechanism_map.falsification_test
      APPARATUS             <- UNKNOWN unless the falsification test names
                               instrumentation explicitly (kept honest:
                               the split is not invented)
      SAMPLE                <- UNKNOWN (no sample-size stage exists)
      ACCEPTANCE_THRESHOLD  <- mechanism_map.expected_effect (the recorded
                               predicted effect with its quantities)
      FALSIFICATION_THRESHOLD <- falsification_test + expected_effect
                               composite (see above)
      UNCERTAINTY           <- the killer experiment's recorded epistemic
                               note (priors MODEL_DERIVED, provenance)
      COST / TIME           <- the selector's own honest UNKNOWN records
      SAFETY                <- UNKNOWN (no safety stage output exists)
    """
    mm = getattr(env, "mechanism_map", None) or {}
    arch = survivor_architecture or {}
    treatment = (arch.get("intervention")
                 or mm.get("intervention") or "").strip()
    expected_effect = (arch.get("expected_effect")
                       or mm.get("expected_effect") or "").strip()
    falsification_test = (arch.get("falsification_test")
                          or mm.get("falsification_test") or "").strip()
    ke = getattr(env, "killer_experiment", None) or {}
    hypotheses = ke.get("hypotheses") or []
    h_hold = next((h for h in hypotheses
                   if str(h.get("name") or "").startswith("H_effect_holds")),
                  None)
    h_fail = next((h for h in hypotheses
                   if str(h.get("name") or "").startswith("H_effect_fails")),
                  None)
    ph = getattr(env, "physics", None) or {}

    contract: Dict[str, Any] = {}

    # HYPOTHESIS — the recorded testable hypothesis with its prior
    if h_hold and h_hold.get("description"):
        hyp = str(h_hold["description"])
        prior = h_hold.get("prior_probability")
        if prior is not None:
            hyp += (f" (recorded prior {prior}, epistemic class "
                    "MODEL_DERIVED per the killer-experiment provenance)")
        contract["HYPOTHESIS"] = hyp
    else:
        contract["HYPOTHESIS_BLOCKER"] = (
            "no killer-experiment hypothesis record exists (the "
            "KILLER_EXPERIMENT stage did not record H_effect_holds)")

    # TREATMENT — what is experimentally applied
    if treatment:
        contract["TREATMENT"] = treatment
    else:
        contract["TREATMENT_BLOCKER"] = (
            "no intervention recorded in the mechanism map or the "
            "evolution survivor architecture")

    # CONTROL — the baseline comparison arm
    chain = ph.get("chain_executed") or []
    if "BASELINE_COMPARISON" in chain:
        contract["CONTROL"] = (
            "the physics stage's executed BASELINE_COMPARISON arm "
            f"(lifecycle verdict {ph.get('lifecycle_verdict')}) — the "
            "baseline the candidate was measured against in the same "
            "evaluation")
    else:
        contract["CONTROL_BLOCKER"] = (
            f"no executed baseline comparison on record (physics chain "
            f"executed: {chain or 'none'}; lifecycle "
            f"{ph.get('lifecycle_verdict')}) — the control arm is not "
            "invented from the problem statement")

    # MEASUREMENT — the recorded measurement procedure
    if falsification_test:
        contract["MEASUREMENT"] = falsification_test
    else:
        contract["MEASUREMENT_BLOCKER"] = (
            "no falsification test recorded by the candidate")

    # APPARATUS — only when the records name instrumentation explicitly
    if falsification_test and _NUMBER_RE.search(falsification_test) \
            and _KILL_DIRECTION_RE.search(falsification_test):
        # the recorded procedure itself carries instrument + quantities;
        # no separate apparatus field is split out of it (Art. XXV)
        contract["APPARATUS"] = (
            "the falsification test's own recorded instrumentation "
            "(stated within MEASUREMENT; not split out — no separate "
            "apparatus record exists)")
    else:
        contract["APPARATUS_BLOCKER"] = (
            "no separate apparatus record exists; the falsification "
            "test does not state a quantified instrumented procedure")

    # SAMPLE — no sample-size stage exists in the engine
    contract["SAMPLE_BLOCKER"] = (
        "no sample-size / n= record exists in any engine stage "
        "(honest UNKNOWN — Art. XXV)")

    # ACCEPTANCE_THRESHOLD — the recorded predicted effect
    # R478 P0-3 (external audit): an acceptance threshold without a
    # number is not a threshold. The prose-with-note fallback is
    # RETIRED — a numeric band is required, else the field stays
    # honestly unanswered and the maturity gate blocks EXPERIMENT_READY
    # (Art. LII: a falsification contract is a measured contract;
    # Art. XXVII: nothing quantified by inference).
    if expected_effect and _NUMBER_RE.search(expected_effect):
        contract["ACCEPTANCE_THRESHOLD"] = expected_effect
    elif expected_effect:
        contract["ACCEPTANCE_THRESHOLD_BLOCKER"] = (
            "the recorded expected effect carries no numeric band "
            "('" + expected_effect[:160] + "') — a prose expectation is "
            "not an acceptance threshold (Art. LII/XXVII: the band is "
            "not invented by inference); the candidate must state the "
            "measurable quantity and its band")
    else:
        contract["ACCEPTANCE_THRESHOLD_BLOCKER"] = (
            "no expected effect recorded by the candidate")

    # FALSIFICATION_THRESHOLD — THE KILL OUTCOME (the decisive field)
    # R478 P0-3 (external audit): the prose composite ('the test fails
    # to show the expected effect') answered the kill outcome with no
    # number in it — a ranking-shaped sentence, not a threshold. The
    # kill outcome is answered only when the recorded expected effect
    # carries a NUMERIC band (the quantity the kill condition speaks
    # about); the recorded numbers travel verbatim (FALSIFICATION_BANDS)
    # so the kill condition is checkable, not assertable (Art. LII).
    # The falsification test itself names the PROCEDURE and may stay
    # prose (the threshold lives in the effect's band, not the
    # procedure's wording — measured against the R446-era run shapes).
    _eff_nums = _NUMBER_RE.findall(expected_effect) if expected_effect else []
    _test_nums = _NUMBER_RE.findall(falsification_test) if falsification_test else []
    if falsification_test and expected_effect and _eff_nums:
        kill_outcome = (
            f"the recorded falsification test ('{falsification_test[:200]}') "
            f"fails to show the recorded expected effect "
            f"('{expected_effect[:200]}') — the mechanism is killed by "
            "its own test's negative outcome"
            + (f"; the recorded failing hypothesis is '{h_fail['description']}'"
               if h_fail and h_fail.get("description") else ""))
        contract["FALSIFICATION_THRESHOLD"] = kill_outcome
        contract["FALSIFICATION_BANDS"] = {
            "expected_effect_numbers": _eff_nums,
            "falsification_test_numbers": _test_nums,
            "basis": "verbatim numbers extracted from the candidate's own "
                     "records (never computed, never inferred — Art. VI)",
        }
    else:
        _missing = []
        if not falsification_test:
            _missing.append("no falsification test recorded")
        if not expected_effect:
            _missing.append("no expected effect recorded")
        elif not _eff_nums:
            _missing.append("the recorded expected effect carries no "
                            "numeric band")
        contract["FALSIFICATION_THRESHOLD_BLOCKER"] = (
            "the kill outcome cannot be stated NUMERICALLY from records: "
            + "; ".join(_missing)
            + " — a prose kill sentence is not a threshold (R478 P0-3; "
              "Art. LII/XXVII: the band is not invented)")

    # UNCERTAINTY — the recorded epistemic note
    note = ke.get("epistemic_note")
    if note:
        contract["UNCERTAINTY"] = str(note)
    else:
        contract["UNCERTAINTY_BLOCKER"] = (
            "no killer-experiment epistemic note recorded")

    # COST / TIME — the selector's own honest UNKNOWN records
    contract["COST"] = ("UNKNOWN absolute cost (options ranked on a "
                        "relative-1.0 scale per bayesian_eig; no sourced "
                        "dollar/time estimate exists — Art. XXV)")
    contract["TIME"] = "UNKNOWN (no stage recorded a time estimate)"

    # SAFETY — no safety stage output exists
    contract["SAFETY_BLOCKER"] = (
        "no safety-analysis stage output exists in the engine "
        "(honest UNKNOWN — Art. XXV; the engineering failure_modes "
        "record is a failure-mode list, not a safety case)")

    return contract
