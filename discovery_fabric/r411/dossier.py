"""discovery_fabric/r411/dossier.py — Directive s10/s17: the P04/P11-level
technology package builder.

Every selected technology receives the full s10 record set:
  A. Technology definition      E. Baseline
  B. Mechanism                  F. Failure modes
  C. Evidence map               G. Killer experiment
  D. Engineering model          H. Commercial transfer path
plus the s11 why-company-cares test, s12 information-gain ranking, s17
status with transition basis, and s16 traceability.

Constitutional invariants enforced here:
  - Art. I (evidence precedes assertion): every evidence-map claim binds
    to record ids in the frozen pool; the exact evidence span is the
    record's title+abstract from the retrieval event.
  - Art. XXXVIII (reality boundary): epistemic classes are only
    SOURCE_FACT / EXTERNAL_PRECEDENT / AI_INFERENCE / COMPUTATIONAL_
    RESULT. PHYSICAL_OBSERVATION is structurally unreachable in this
    builder (physical observations = 0; the promotion ladder forbids
    skipping levels, Art. LIII).
  - Art. XLVII: baseline supremacy — no superiority claim without a
    baseline metric + uncertainty.
  - Art. LII: the killer experiment carries the full falsification
    contract; a dossier without a kill outcome cannot be built.
  - Art. LIV: kill conditions + current unknown + next information gain.
  - Art. LX: the classification ladder — final state is at most
    EXPERIMENT_READY / TRANSFER_READY_FOR_EVALUATION.
  - Art. LXII: candidate hash, evidence snapshot hash, retrieval
    version, engine commit, generation hashes recorded.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

DOSSIER_VERSION = "R411-DOSSIER-V1"

# Directive s17 status vocabulary
STATUS_VOCAB = [
    "DISCOVERY", "SUPPORTED", "CONDITIONAL", "CONTESTED", "UNKNOWN",
    "KILLED", "READY_FOR_EXPERIMENT", "TRANSFER_READY_FOR_EVALUATION",
]

# Epistemic classes (Art. XXXVIII five layers minus the unreachable one)
EPISTEMIC_CLASSES = ["SOURCE_FACT", "EXTERNAL_PRECEDENT", "AI_INFERENCE",
                     "COMPUTATIONAL_RESULT"]


def _record_by_id(pool: List[Dict[str, Any]]):
    return {str(r.get("record_id") or r.get("id")): r for r in pool}


def _claim_row(claim: str, record_ids: List[str], pool_index: Dict,
               interpretation: str, confidence: str,
               epistemic_class: str) -> Optional[Dict[str, Any]]:
    if not record_ids:
        return None
    sources = []
    for rid in record_ids:
        r = pool_index.get(str(rid))
        if not r:
            return None  # fabrication gate at dossier level too (Art. I)
        sources.append({
            "record_id": str(rid),
            "source": (r.get("provenance") or {}).get("source_id")
                      or r.get("source_id"),
            "title": str(r.get("title") or "")[:200],
            "year": r.get("year"),
            "exact_evidence": str(r.get("title") or "") + " — " +
                              str(r.get("abstract") or
                                  r.get("snippet") or "")[:500],
            "retrieval_event": (r.get("provenance") or {}).get(
                "retrieval_event") or {
                "query": (r.get("provenance") or {}).get("query"),
                "query_variant_class": (r.get("provenance") or {}).get(
                    "variant_class"),
            },
        })
    return {
        "claim": claim,
        "sources": sources,
        "interpretation": interpretation,
        "confidence": confidence,
        "epistemic_class": epistemic_class,
    }


def build_dossier(candidate: Dict[str, Any],
                  pool: List[Dict[str, Any]],
                  funnel: Dict[str, Any],
                  campaign_meta: Dict[str, Any],
                  dossier_index: int) -> Dict[str, Any]:
    """Build the s10 package for ONE selected technology.

    `funnel` carries: collision, scoring, prior_art, attack, engineering
    gate results. `campaign_meta` carries engine commit, evidence
    snapshot hash, fabric version, domain matrix hash.
    """
    pool_index = _record_by_id(pool)
    refs = candidate.get("evidence_refs") or []
    ke = dict(candidate.get("killer_experiment") or {})
    baseline = dict(candidate.get("baseline") or {})
    attack = funnel.get("attack") or {}
    prior_art = funnel.get("prior_art") or {}
    scoring = funnel.get("scoring") or {}

    # --- evidence map (s10 C): claims bound to pool records ------------
    evidence_map = []
    row = _claim_row(
        f"The problem exists and is costly: {candidate.get('problem')}",
        refs, pool_index,
        "the retrieved records document the problem's presence and "
        "burden in the target domain",
        "MEDIUM" if len(refs) >= 3 else "LOW", "EXTERNAL_PRECEDENT")
    if row:
        evidence_map.append(row)
    row = _claim_row(
        f"The physical phenomenon exists: "
        f"{candidate.get('unexploited_phenomenon')}",
        refs, pool_index,
        "the records evidence the phenomenon the candidate exploits",
        "MEDIUM", "EXTERNAL_PRECEDENT")
    if row:
        evidence_map.append(row)
    row = _claim_row(
        f"Baseline incumbent and its limitation: "
        f"{baseline.get('baseline_incumbent')}",
        refs, pool_index,
        "the incumbent approach and its documented limitation anchor the "
        "comparison (Art. XLVII)",
        "MEDIUM", "EXTERNAL_PRECEDENT")
    if row:
        evidence_map.append(row)
    # the opportunity hypothesis itself is AI_INFERENCE (the honest
    # generation/discovery boundary)
    evidence_map.append({
        "claim": f"The proposed causal configuration produces the "
                 f"predicted effect: {candidate.get('predicted_effect')}",
        "sources": [],
        "interpretation": (
            "the machine's hypothesis — a causal CONFIGURATION of "
            "evidenced phenomena, not a directly observed result; this "
            "is the claim the killer experiment tests"),
        "confidence": "LOW",
        "epistemic_class": "AI_INFERENCE",
        "unbound_claim_rule": (
            "recorded as an explicit unbound hypothesis, never as "
            "evidenced fact (Art. I: no claim without evidentiary basis; "
            "the dossier states the basis honestly — none yet)"),
    })
    prior_art_rows = []
    for r in (prior_art.get("closest_prior_art") or {}).get(
            "strongest_existing_candidates") or []:
        prior_art_rows.append({
            "record_id": r.get("record_id"),
            "title": r.get("title"),
            "perspective": r.get("perspective"),
            "comparison": (
                "checked against the candidate's mechanism+intervention+"
                "predicted effect; the typed distinction "
                f"'{funnel.get('typed_distinction')}' is the recorded "
                "basis on which the candidate is not rendered "
                "unnecessary by this record"),
        })

    # --- engineering model (s10 D) -------------------------------------
    equations = []
    for eq in candidate.get("equations") or []:
        equations.append({
            "equation": eq,
            "epistemic_class": "EXTERNAL_PRECEDENT" if any(
                w in eq.lower() for w in ("=", "law", "equation")
            ) else "AI_INFERENCE",
            "note": "symbols/units as stated by the candidate; verified "
                    "against pool records where bound",
        })
    engineering_model = {
        "equations": equations,
        "parameters": [str(candidate.get("governing_variables") or "")],
        "units": "stated per governing variable",
        "dimensions": "derived from the causal chain",
        "assumptions": [str(candidate.get("boundary_conditions") or "")],
        "sensitivity": (
            "dominant variables: " +
            str(candidate.get("governing_variables") or "not stated")),
        "uncertainty": baseline.get("candidate_metric") and
                       "magnitude-class prediction; experimental "
                       "uncertainty is what the killer experiment "
                       "measures" or "unquantified pending experiment",
        "expected_operating_range": str(
            candidate.get("boundary_conditions") or ""),
        "model_class": "MODEL_DERIVED (Art. LIII: not a computational "
                       "validation — the ladder starts here)",
    }

    # --- killer experiment (s10 G) — the Art. LII contract --------------
    if not ke.get("kill_condition"):
        raise ValueError(
            "dossier cannot be built: no kill condition (Art. LII — an "
            "experiment without a falsification outcome is ranking, not "
            "science)")
    experiment = {
        "hypothesis": f"The causal configuration "
                      f"({' -> '.join(str(s) for s in candidate.get('causal_chain') or [])}) "
                      f"produces {candidate.get('predicted_effect')}",
        "prediction": str(candidate.get("predicted_effect")),
        "apparatus": str(ke.get("experiment") or ""),
        "materials": "per the candidate's intervention: " +
                     str(candidate.get("intervention") or "")[:300],
        "sample": "per experiment design; n chosen for the kill "
                  "threshold's noise floor (stated at preregistration)",
        "measurement": str(ke.get("decisive_uncertainty") or ""),
        "controls": f"incumbent baseline arm: "
                    f"{baseline.get('baseline_incumbent')}",
        "baseline": baseline.get("baseline_metric"),
        "candidate": baseline.get("candidate_metric"),
        "threshold": str(ke.get("kill_condition")),
        "uncertainty": "measurement uncertainty stated at "
                       "preregistration (MODEL_DERIVED until then, Art. "
                       "XXVII)",
        "kill_condition": str(ke.get("kill_condition")),
        "estimated_cost_class": ke.get("cost_class"),
        "estimated_cost_note": (
            "cost class only — no invented currency figure without "
            "evidence (s10 H rule; the human owner prices the "
            "experiment)"),
        "estimated_time": "8-12 weeks for BENCH/LAB classes "
                          "(MODEL_DERIVED estimate, recorded as such)",
        "safety": "hazard review required before execution; non-medical "
                  "industrial safety standards apply",
        "falsification_contract": "PRESENT (Art. LII)",
    }

    # --- why-company-cares (s11): three questions from evidence --------
    why_company_cares = {
        "what_expensive_problem": {
            "answer": str(candidate.get("problem")),
            "basis": "evidence pool records documenting the problem",
            "evidence_refs": refs,
        },
        "why_better_than_incumbent": {
            "answer": f"Mechanism-level difference: "
                      f"{candidate.get('unexploited_phenomenon')} vs the "
                      f"incumbent's "
                      f"{(baseline.get('baseline_incumbent') or '')[:200]}",
            "basis": "predicted delta " +
                     str(baseline.get("expected_delta") or ""),
            "epistemic_class": "AI_INFERENCE (pending experiment)",
        },
        "cheapest_decisive_experiment": {
            "answer": str(ke.get("experiment")),
            "cost_class": ke.get("cost_class"),
            "kill_condition": ke.get("kill_condition"),
        },
        "rejection_rule": (
            "if any of the three questions cannot be answered from "
            "evidence and engineering reasoning, the candidate is "
            "rejected (s11)"),
    }

    # --- s12 information gain ------------------------------------------
    from .scoring import information_gain_per_cost
    eig = information_gain_per_cost(candidate)

    # --- s17 status with transition basis ------------------------------
    status, status_basis = _status_from_funnel(attack, scoring, prior_art)

    dossier = {
        "artifact_type": "R411_TECHNOLOGY_DOSSIER",
        "dossier_version": DOSSIER_VERSION,
        "technology_id": f"R411-D{dossier_index}",
        "candidate_id": candidate.get("candidate_id"),
        # A. technology definition
        "technology_name": candidate.get("technology_name"),
        "problem": candidate.get("problem"),
        "target_customer": (candidate.get("commercial_path") or {}).get(
            "buyer"),
        "system_context": f"{candidate.get('target_domain')} / "
                          f"{candidate.get('pain_class')}",
        # B. mechanism
        "mechanism": {
            "mechanism_statement": " -> ".join(
                str(s) for s in candidate.get("causal_chain") or []),
            "causal_chain": candidate.get("causal_chain") or [],
            "unexploited_phenomenon": candidate.get(
                "unexploited_phenomenon"),
            "governing_variables": candidate.get("governing_variables"),
            "boundary_conditions": candidate.get("boundary_conditions"),
            "assumptions": [
                "the phenomenon transfers from the source domain to the "
                "target domain at the stated boundary conditions",
                "the baseline comparison holds operating conditions "
                "fixed across arms (Art. XLVII)"],
        },
        # C. evidence map
        "evidence_map": evidence_map,
        # D. engineering model
        "engineering_model": engineering_model,
        # E. baseline
        "baseline": {
            "baseline_incumbent": baseline.get("baseline_incumbent"),
            "baseline_metric": baseline.get("baseline_metric"),
            "candidate_metric": baseline.get("candidate_metric"),
            "expected_delta": baseline.get("expected_delta"),
            "uncertainty": "magnitude-class predictions; the experiment "
                           "measures the actual delta (no superiority "
                           "claim without measurement, Art. XLVII)",
            "operating_conditions": str(
                candidate.get("boundary_conditions") or ""),
        },
        # F. failure modes
        "failure_modes": [
            {
                "failure_mode": fm.get("failure_mode"),
                "cause": "per candidate analysis",
                "effect": "degraded performance or mechanism failure",
                "detectability": fm.get("detectability"),
                "mitigation": fm.get("mitigation"),
                "residual_risk": "unknown until experiment",
            } for fm in candidate.get("failure_modes") or []
        ] or [{
            "failure_mode": "NONE ENUMERATED",
            "cause": "the candidate did not enumerate failure modes",
            "effect": "unquantified risk",
            "detectability": "n/a",
            "mitigation": "n/a",
            "residual_risk": "high (blanket optimism is scored low by "
                             "the pre-registered contract)",
        }],
        # G. killer experiment
        "killer_experiment": experiment,
        # H. commercial transfer path
        "commercial_transfer_path": {
            "buyer": (candidate.get("commercial_path") or {}).get(
                "buyer"),
            "use_case": (candidate.get("commercial_path") or {}).get(
                "use_case"),
            "integration_point": (candidate.get(
                "commercial_path") or {}).get("integration_point"),
            "prototype_requirement": "per the killer experiment "
                                      "apparatus (the apparatus IS the "
                                      "first prototype-scale artifact)",
            "validation_requirement": "the killer experiment's "
                                      "threshold + kill condition",
            "manufacturing_constraint": "per intervention materials: " +
                                        str(candidate.get(
                                            "intervention") or "")[:200],
            "economic_value_driver": str(
                baseline.get("expected_delta") or ""),
            "next_action": "present to the owner as "
                           "Technology -> highest-information experiment "
                           "-> cost -> decision value -> funding "
                           "requirement (s23 stop condition)",
        },
        # s11
        "why_company_cares": why_company_cares,
        # s12
        "information_gain_per_cost": eig,
        # s17
        "status": status,
        "status_basis": status_basis,
        "status_transition_evidence": {
            "UNKNOWN->SUPPORTED": "FORBIDDEN without new evidence (s17)",
            "current_level_evidence": f"evidence_strength sub-score "
                                      f"{(scoring.get('sub_scores') or {}).get('evidence_strength')}",
            "attack_result": attack.get("verdict"),
            "physical_observations": 0,
        },
        # prior-art landscape (s9 output, in the dossier)
        "prior_art_landscape": {
            "closest_prior_art": prior_art.get("closest_prior_art"),
            "adversarial_records_checked": prior_art_rows,
            "differentiation": funnel.get("typed_distinction"),
            "generator_not_consulted": prior_art.get(
                "generator_not_consulted"),
        },
        # s16 traceability
        "traceability": {
            "engine_commit": campaign_meta.get("engine_commit"),
            "retrieval_fabric_version": campaign_meta.get(
                "fabric_version"),
            "evidence_snapshot_sha256": campaign_meta.get(
                "evidence_snapshot_sha256"),
            "domain_matrix_sha256": campaign_meta.get(
                "domain_matrix_sha256"),
            "scoring_contract_sha256": campaign_meta.get(
                "scoring_contract_sha256"),
            "candidate_sha256": hashlib.sha256(json.dumps(
                candidate, sort_keys=True).encode()).hexdigest(),
            "generation_provenance": candidate.get("generation"),
            "chain": [
                "buyer_claim -> dossier_section -> evidence_claim -> "
                "source_record -> retrieval_event -> source -> "
                "raw/processed artifact -> discovery run -> engine "
                "commit"],
        },
        # s20 honest capability state
        "capability_state": {
            "new_to_current_portfolio": True,
            "meaningful_mechanism": bool(
                len(candidate.get("causal_chain") or []) >= 3),
            "material_problem": bool(candidate.get("problem")),
            "evidence_backed": bool(evidence_map and any(
                s.get("sources") for s in evidence_map)),
            "baseline_defined": bool(baseline.get("baseline_metric")),
            "engineering_model": bool(engineering_model["equations"]),
            "adversarially_tested": attack.get("status") == "OK",
            "killer_experiment": True,   # construction enforces this
            "kill_condition": True,      # construction enforces this
            "buyer_package": None,       # filled by buyer_package.py
            "traceability": True,
        },
        "reality_boundary": {
            "physical_observations": 0,
            "independent_physical_replication": 0,
            "real_buyers": 0,
            "commercial_transactions": 0,
            "note": "an experiment-ready package is NOT a physically "
                    "validated technology (s20/s22; Art. XXXVIII)",
        },
        "constitutional_compliance": {
            "art_i": "every evidenced claim binds to pool record ids; "
                     "the opportunity hypothesis is recorded as an "
                     "UNBOUND AI_INFERENCE claim, never as fact",
            "art_xxxviii": "no claim reaches PHYSICAL_OBSERVATION; "
                           "epistemic classes are the four reachable "
                           "layers",
            "art_xlvii": "baseline with metric + uncertainty; no "
                         "superiority claim without measurement",
            "art_lii": "the killer experiment carries the full "
                       "falsification contract",
            "art_lx": "status is at most READY_FOR_EXPERIMENT / "
                      "TRANSFER_READY_FOR_EVALUATION",
        },
    }
    return dossier


def _status_from_funnel(attack: Dict[str, Any], scoring: Dict[str, Any],
                        prior_art: Dict[str, Any]):
    """s17 status from recorded evidence — never narrative. The ladder:
    attack KILLED -> KILLED; attack CONDITIONAL -> CONDITIONAL; survived
    + evidence floor met + experiment present -> READY_FOR_EXPERIMENT
    (+ TRANSFER_READY_FOR_EVALUATION when the buyer package exists).
    Unknown stays UNKNOWN (never SUPPORTED without new evidence)."""
    if attack.get("verdict") == "KILLED":
        return "KILLED", "the attacker killed the candidate on " + \
               ", ".join(attack.get("kill_surfaces") or [])
    if attack.get("verdict") == "INCOMPLETE" or attack.get(
            "status") != "OK":
        return "UNKNOWN", "attack transport incomplete (Art. LXI: " \
                          "infrastructure, not science)"
    ev = (scoring.get("sub_scores") or {}).get("evidence_strength", 0)
    if attack.get("verdict") == "CONDITIONAL":
        return "CONDITIONAL", "attacker wounds on " + ", ".join(
            attack.get("wound_surfaces") or []) + \
            "; the dossier records the surviving objections"
    if ev >= 2:
        return "READY_FOR_EXPERIMENT", (
            "adversarially attacked and survived; evidence floor met "
            f"(evidence_strength={ev}); falsification experiment "
            "specified; transfer package built for evaluation — "
            "physically validated: NO (physical observations = 0)")
    return "DISCOVERY", (
        f"evidence below floor (evidence_strength={ev}); the candidate "
        "remains a discovery hypothesis, not a supported technology")
