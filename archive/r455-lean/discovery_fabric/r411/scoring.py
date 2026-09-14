"""discovery_fabric/r411/scoring.py — Directive s2: the pre-registered
high-value scoring contract.

FROZEN BEFORE ANY CANDIDATE EXISTS (Art. LIX pre-registration discipline;
directive s2: "Do not allow the LLM to decide that an invention is 'high
value' by narrative judgment after seeing the candidate").

Design rules:
  1. The 13 dimensions are each measured by DETERMINISTIC functions of
     recorded candidate state (evidence pool facts, funnel records,
     structural completeness) — never by LLM narrative judgment. Where a
     dimension depends on candidate content the LLM authored (e.g. the
     engineering model), the score measures STRUCTURAL presence and
     evidence binding, not perceived quality.
  2. The composite is a fixed weighted sum over normalized [0,4] anchored
     sub-scores. Weights are policy inputs recorded here (Art. XXVII).
  3. THE SCORE NEVER SUBSTITUTES FOR EVIDENCE (directive s2, final rule):
     a candidate whose evidence_strength sub-score is below the evidence
     floor gets confidence = LOW regardless of composite, and can never
     be selected as a finalist. High theoretical score + weak mechanism
     evidence stays low-confidence, mechanically.
  4. Cost-to-learn (directive s12) is a first-class ranking input:
     final ranking = information_gain_per_cost, computed from the
     recorded experiment design (cost class) and the uncertainty the
     experiment resolves (Art. LVI).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

SCORING_CONTRACT_VERSION = "R411-SCORING-V1"

# Anchored 0-4 rubric per dimension (pre-registered; the campaign code
# maps recorded state onto these anchors deterministically).
DIMENSIONS = {
    "technical_problem_severity": {
        "weight": 1.2,
        "measure": "evidence-pool records documenting the problem's "
                   "severity/cost (count + explicit severity language), "
                   "deterministically counted",
    },
    "economic_consequence": {
        "weight": 1.3,
        "measure": "evidence records carrying quantified cost/loss figures "
                   "(currency, percentage, downtime) near the problem",
    },
    "incumbent_cost": {
        "weight": 1.0,
        "measure": "baseline existence + evidence of incumbent's "
                   "cost/burden (documented baseline artifacts)",
    },
    "performance_headroom": {
        "weight": 1.2,
        "measure": "predicted delta vs baseline present with magnitude "
                   "class + governing variables + equations",
    },
    "mechanism_plausibility": {
        "weight": 1.2,
        "measure": "structural: causal-chain step count, governing "
                   "variables, equations, boundary conditions present; "
                   "physics vocabulary matched to the claimed effect",
    },
    "evidence_strength": {
        "weight": 1.6,
        "measure": "number AND family-independence of fabric evidence "
                   "records backing the mechanism claims (binding "
                   "enforced: refs must exist in the frozen pool)",
    },
    "engineering_feasibility": {
        "weight": 1.1,
        "measure": "structural: design variables, realization path, "
                   "materials/components referenced in evidence pool",
    },
    "implementation_complexity": {
        "weight": 0.9,
        "measure": "deterministic complexity token count (moving parts, "
                   "regimes, subsystems) — LOWER complexity scores HIGHER",
    },
    "validation_cost": {
        "weight": 1.0,
        "measure": "experiment apparatus class from the recorded killer "
                   "experiment (bench/lab/pilot/field) — cheaper scores "
                   "HIGHER",
    },
    "commercial_adoption_path": {
        "weight": 1.1,
        "measure": "buyer/use-case/integration-point present + evidence "
                   "records showing industrial adoption of adjacent "
                   "technologies",
    },
    "differentiation": {
        "weight": 1.4,
        "measure": "prior-art distance from the adversarial search: "
                   "closest art found + typed distinction surviving the "
                   "collision gate",
    },
    "cross_domain_opportunity": {
        "weight": 0.8,
        "measure": "recorded cross-domain transition (source domain -> "
                   "target domain differs) with target-domain evidence "
                   "records",
    },
    "failure_risk": {
        "weight": 0.9,
        "measure": "known failure modes enumerated with detection + "
                   "mitigation — MORE enumerated-with-mitigation scores "
                   "HIGHER (blanket optimism scores LOWER)",
    },
}

# Evidence floor (directive s2 final rule): below this evidence_strength
# anchor, confidence is LOW and the candidate can NEVER be a finalist,
# whatever the composite says.
EVIDENCE_FLOOR = 2

# Confidence vocabulary
CONFIDENCE_LEVELS = ["LOW", "MEDIUM", "HIGH"]


def scoring_contract() -> Dict[str, Any]:
    """The frozen contract artifact (committed before the campaign runs)."""
    return {
        "contract_version": SCORING_CONTRACT_VERSION,
        "dimensions": DIMENSIONS,
        "composite_rule": (
            "score = sum(weight_i * sub_i) / sum(weight_i), sub_i in "
            "[0,4] anchored; deterministic function of recorded state; "
            "no LLM narrative input"),
        "evidence_floor": EVIDENCE_FLOOR,
        "evidence_floor_rule": (
            "evidence_strength sub-score < EVIDENCE_FLOOR => confidence "
            "LOW and finalist-ineligible regardless of composite (the "
            "score never substitutes for evidence)"),
        "ranking_rule": (
            "final ranking = information_gain_per_cost = resolved_"
            "uncertainty_class / validation_cost_class (Art. LVI), "
            "tie-broken by composite score"),
        "frozen_before_candidates": True,
        "contract_sha256": hashlib.sha256(json.dumps(
            DIMENSIONS, sort_keys=True).encode()).hexdigest(),
    }


# ---------------------------------------------------------------------------
# Deterministic sub-score measurement helpers (each maps recorded state
# onto the 0-4 anchors; all inputs are candidate/pool/funnel records)
# ---------------------------------------------------------------------------

SEVERITY_TERMS = ["critical", "severe", "catastrophic", "major failure",
                  "unscheduled", "downtime", "outage", "loss of", "failure",
                  "degradation", "emergency", "replacement cost", "billion",
                  "million", "% loss", "efficiency loss", "waste"]

COST_PATTERN_TERMS = ["cost", "$", "usd", "eur", "million", "billion",
                      "percent", "%", "kwh", "mwh", "gj", "tonne",
                      "downtime", "per year", "annually", "gwp", "co2"]


def _text_of_pool(records: List[Dict[str, Any]], ref_ids: List[str]) -> str:
    by_id = {str(r.get("record_id") or r.get("id")): r for r in records}
    parts = []
    for rid in ref_ids:
        r = by_id.get(str(rid))
        if r:
            parts.append(" ".join(str(r.get(k) or "") for k in (
                "title", "abstract", "snippet", "summary")))
    return " ".join(parts).lower()


def _anchor_from_count(n: int, thresholds: List[int]) -> int:
    """Map a count onto 0-4 using pre-registered thresholds."""
    for i, th in enumerate(thresholds):
        if n >= th:
            return i + 1
    return 0


def measure_evidence_strength(candidate: Dict[str, Any],
                              pool: List[Dict[str, Any]]) -> int:
    """0-4: number AND family-independence of backing records.

    Anchors (pre-registered): 0 refs; 1: >=1 valid ref; 2: >=3 refs;
    3: >=5 refs OR >=3 refs across >=2 source families; 4: >=5 refs
    across >=3 families.
    """
    refs = candidate.get("evidence_refs") or []
    by_id = {str(r.get("record_id") or r.get("id")): r for r in pool}
    families = set()
    valid = 0
    for rid in refs:
        r = by_id.get(str(rid))
        if r:
            valid += 1
            prov = r.get("provenance") or {}
            fam = prov.get("source_family") or prov.get("family") or \
                r.get("family") or ""
            if fam:
                families.add(fam)
    if valid >= 5 and len(families) >= 3:
        return 4
    if (valid >= 5 and len(families) >= 2) or (valid >= 3 and len(families) >= 2):
        return 3
    if valid >= 3:
        return 2
    if valid >= 1:
        return 1
    return 0


def measure_problem_severity(pool_text: str) -> int:
    hits = sum(1 for t in SEVERITY_TERMS if t in pool_text)
    return _anchor_from_count(hits, [2, 6, 12, 24])


def measure_economic_consequence(pool_text: str) -> int:
    hits = sum(1 for t in COST_PATTERN_TERMS if t in pool_text)
    return _anchor_from_count(hits, [2, 5, 10, 18])


def measure_mechanism_plausibility(candidate: Dict[str, Any]) -> int:
    present = 0
    chain = candidate.get("causal_chain") or []
    if isinstance(chain, list) and len(chain) >= 3:
        present += 1
    if candidate.get("governing_variables"):
        present += 1
    if candidate.get("equations") or candidate.get("engineering_model", {}).get("equations"):
        present += 1
    if candidate.get("boundary_conditions"):
        present += 1
    return present  # 0-4 by structural completeness


def measure_performance_headroom(candidate: Dict[str, Any]) -> int:
    delta = candidate.get("expected_delta") or \
        (candidate.get("baseline") or {}).get("expected_delta")
    base = candidate.get("baseline") or {}
    score = 0
    if delta:
        score += 2
    if base.get("baseline_metric") and base.get("candidate_metric"):
        score += 1
    if base.get("uncertainty"):
        score += 1
    return min(score, 4)


def measure_implementation_complexity(candidate: Dict[str, Any]) -> int:
    """LOWER complexity => HIGHER score. Complexity tokens counted
    deterministically from the mechanism + intervention text."""
    text = " ".join(str(candidate.get(k) or "") for k in
                    ("mechanism", "intervention", "system_context")).lower()
    tokens = sum(1 for t in [
        "multi-stage", "multi-stage", "cascade", "array of", "plural",
        "high-precision", "cleanroom", "vacuum", "cryogenic", "high-pressure",
        "high-temperature", "lithography", "reactor", "plasma", "laser array",
        "robotic", "closed-loop", "adaptive control", "machine learning",
        "neural", "real-time feedback", "microfabricat", "nanofabricat",
    ] if t in text)
    # 0 tokens -> 4; 1-2 -> 3; 3-4 -> 2; 5-6 -> 1; 7+ -> 0
    return max(0, 4 - _anchor_from_count(tokens, [1, 3, 5, 7]))


COST_CLASS_TO_SCORE = {
    "BENCH": 4,       # < ~25 kUSD, commodity instruments
    "LAB": 3,         # ~25-150 kUSD, custom apparatus
    "PILOT": 1,       # ~150 k-2 MUSD, process-scale
    "FIELD": 0,       # > 2 MUSD / multi-site
    "UNKNOWN": 0,
}


def measure_validation_cost(candidate: Dict[str, Any]) -> int:
    exp = candidate.get("killer_experiment") or {}
    return COST_CLASS_TO_SCORE.get(exp.get("cost_class") or "UNKNOWN", 0)


def measure_failure_risk(candidate: Dict[str, Any]) -> int:
    fms = candidate.get("failure_modes") or []
    with_mitigation = 0
    for fm in fms:
        if isinstance(fm, dict) and fm.get("mitigation"):
            with_mitigation += 1
    if not fms:
        return 0  # blanket optimism — no enumerated failure modes
    return _anchor_from_count(with_mitigation, [1, 3, 5, 7])


def measure_commercial_path(candidate: Dict[str, Any]) -> int:
    score = 0
    for f in ("buyer", "use_case", "integration_point"):
        if (candidate.get("commercial_path") or {}).get(f):
            score += 1
    if candidate.get("target_customer"):
        score += 1
    return min(score, 4)


def score_candidate(candidate: Dict[str, Any],
                    pool: List[Dict[str, Any]],
                    funnel: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic composite + confidence gating.

    `funnel` carries the collision/prior-art/attack results used by the
    differentiation dimension (deterministic: closest art distance +
    typed distinction survived).
    """
    ref_ids = candidate.get("evidence_refs") or []
    pool_text = _text_of_pool(pool, ref_ids)

    subs: Dict[str, int] = {
        "technical_problem_severity": measure_problem_severity(pool_text),
        "economic_consequence": measure_economic_consequence(pool_text),
        "incumbent_cost": 2 if (candidate.get("baseline") or {}).get(
            "baseline_metric") else (1 if candidate.get("baseline") else 0),
        "performance_headroom": measure_performance_headroom(candidate),
        "mechanism_plausibility": measure_mechanism_plausibility(candidate),
        "evidence_strength": measure_evidence_strength(candidate, pool),
        "engineering_feasibility": min(
            2 + (1 if candidate.get("design_variables") else 0) +
            (1 if candidate.get("engineering_model") else 0), 4),
        "implementation_complexity": measure_implementation_complexity(
            candidate),
        "validation_cost": measure_validation_cost(candidate),
        "commercial_adoption_path": measure_commercial_path(candidate),
        "differentiation": _differentiation_score(funnel),
        "cross_domain_opportunity": 3 if candidate.get(
            "cross_domain_transition") else 0,
        "failure_risk": measure_failure_risk(candidate),
    }
    total_w = sum(d["weight"] for d in DIMENSIONS.values())
    composite = round(sum(
        DIMENSIONS[k]["weight"] * v for k, v in subs.items()
    ) / total_w, 3)

    ev = subs["evidence_strength"]
    confidence = "LOW" if ev < EVIDENCE_FLOOR else (
        "MEDIUM" if ev >= EVIDENCE_FLOOR and composite >= 1.5 else "LOW")
    if confidence == "MEDIUM" and composite >= 2.6 and ev >= 3:
        confidence = "HIGH"

    return {
        "contract_version": SCORING_CONTRACT_VERSION,
        "sub_scores": subs,
        "composite": composite,
        "confidence": confidence,
        "evidence_floor_applied": ev < EVIDENCE_FLOOR,
        "finalist_eligible": confidence != "LOW",
        "measurement_rule": (
            "deterministic functions of recorded state (pool text hits, "
            "structural completeness, funnel records); no LLM narrative "
            "judgment (pre-registered contract "
            f"{SCORING_CONTRACT_VERSION})"),
    }


def _differentiation_score(funnel: Dict[str, Any]) -> int:
    """0-4 from the prior-art stage: closest art distance + surviving
    typed distinction + attacker survival (all recorded, deterministic)."""
    pa = funnel.get("prior_art") or {}
    closest = pa.get("closest_prior_art") or {}
    dist = closest.get("distance_class") or "UNKNOWN"
    dist_score = {"NO_OVERLAP": 4, "FAR": 3, "NEAR": 1,
                  "COVERING": 0, "UNKNOWN": 0}.get(dist, 0)
    typed = funnel.get("typed_distinction") or ""
    typed_score = 0
    if typed and typed != "NO_MEANINGFUL_DISTINCTION":
        typed_score = {"NEW_MECHANISM": 2, "NEW_CAUSAL_CONFIGURATION": 2,
                       "NEW_IMPLEMENTATION": 1, "NEW_CONTROL_STRATEGY": 1,
                       "NEW_MATERIAL_CONFIGURATION": 1,
                       "NEW_MEASUREMENT_METHOD": 2,
                       "NEW_APPLICATION": 1}.get(typed, 0)
    attack = funnel.get("attack") or {}
    survived = attack.get("survived")
    attack_score = 2 if survived is True else (
        1 if attack.get("verdict") == "CONDITIONAL" else 0)
    return min(dist_score + typed_score + attack_score, 4)


def information_gain_per_cost(candidate: Dict[str, Any]) -> float:
    """Art. LVI / directive s12: EIG / validation cost.

    resolved_uncertainty_class (1-4) from the killer experiment design
    (does it resolve the mechanism's decisive uncertainty?) divided by
    cost_class rank (1-4). Deterministic from recorded state.
    """
    exp = candidate.get("killer_experiment") or {}
    cost_rank = {"BENCH": 1, "LAB": 2, "PILOT": 3, "FIELD": 4}.get(
        exp.get("cost_class") or "UNKNOWN", 4)
    eig = 0
    if exp.get("kill_condition"):
        eig += 2  # a falsification contract exists (Art. LII)
    if exp.get("decisive_uncertainty"):
        eig += 1
    if exp.get("hypothesis") and exp.get("prediction"):
        eig += 1
    return round(eig / cost_rank, 3) if cost_rank else 0.0
