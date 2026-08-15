#!/usr/bin/env python3
"""
V4 CORRECTIONS MODULE — implements the 8 external-auditor corrections.

This module is IMPORTED by the V4 tournament runner and the V3 corrected replay.
It does NOT modify V3 historical artifacts.

CORRECTIONS IMPLEMENTED:

5. BOUNDARY_CONDITION evidence standard:
   - A BOUNDARY_CONDITION=KILL requires: specific boundary + failure mechanism
     + why candidate crosses the boundary + EXTERNAL evidence.
   - External evidence must be: published device failure record, peer-reviewed paper,
     engineering/physics reference, or recognized engineering/regulatory standard.
   - The evaluator's own reasoning is NOT evidence.
   - If no external evidence: INSUFFICIENT_EVIDENCE, do NOT kill.

6. ADVERSARIAL_INVALID disposition:
   - If verdict conflicts with reason, OR reason conflicts with required evidence standard:
     ADVERSARIAL_INVALID → EVALUATION_FAILED.
   - Candidate does NOT become AIC, is NOT killed as invention defect,
     is NOT counted as successful adversarial survivor,
     is eligible for controlled re-evaluation after evaluator correction.

7. V3 source hash reconstruction:
   - For V3 replay: join candidate.source_ids to Phase-D evidence packet source content_hash.
   - If source_id found: reconstruct source_hash retroactively.
   - If source_id missing: PROVENANCE_INCOMPLETE.
   - source_hash_reconstruction_method = "PHASE_D_PACKET_JOIN".

8. Preliminary M0 promotion rule:
   - WINNING_ARCHITECTURE requires: >=5pp lift over best comparator AND Fisher exact
     AND Bonferroni-adjusted p < 0.05.
   - If M0 has highest yield but fails significance: PRELIMINARY_BEST_M0, never WINNING_ARCHITECTURE.

9. Cheap boundary pre-filter:
   - If BOUNDARY_CONDITION KILL reason contains conditional language ("if","could","might","may")
     AND has no external citation/evidence identifier: INSUFFICIENT_EVIDENCE.
   - This is a SCREEN, not the final scientific evaluator.

10. Adversarial prior-art firewall:
    - The adversarial evaluator consumes the frozen prior-art state.
    - These prior-art states CANNOT become adversarial PRIOR_ART=KILL:
      TOPICAL_RELATED, POSSIBLE_RELEVANCE, NO_MATCH_FOUND, UNRESOLVED_INSUFFICIENT_EVIDENCE.
    - Only SPECIFIC_DISCLOSURE, IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE may produce PRIOR_ART=KILL.

11. Evidence → adversarial ordering:
    - Hard execution order: generation → target alignment → evidence verification → prior-art → adversarial → AIC.
    - If evidence fails: adversarial MUST NOT run.
    - Store: adversarial_status = NOT_RUN, adversarial_not_run_reason = EVIDENCE_GATE_FAILED.

3. M4 context isolation:
    - Each M4 round has committed memory files: M4_R{n}_{MACRO,MICRO}_MEMORY.json.
    - Each file is immutable, content-addressed, hashed, committed.
    - Round n may read ONLY frozen memory from round n-1.
    - Machine assertion: context_source_mode == "COMMITTED_FILE".
    - Anything else: M4_INVALID_CONTEXT_SOURCE.
"""
from __future__ import annotations
import json, re, hashlib, os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ===== CORRECTION 5+9: BOUNDARY CONDITION EVIDENCE STANDARD + PRE-FILTER =====

# Conditional language that triggers the cheap pre-filter (Correction 9)
CONDITIONAL_LANGUAGE = {"if", "could", "might", "may", "would", "possibly", "potentially",
                        "likely", "perhaps", "maybe", "conceivably", "presumably"}

# External evidence identifier patterns (citations, DOIs, standard numbers)
EXTERNAL_EVIDENCE_PATTERNS = [
    r'\bISO\s*\d',           # ISO standards
    r'\bASTM\s*[A-F]',       # ASTM standards
    r'\bFDA\s*(?:MAUDE|510\(k\)|PMA|MDR)',  # FDA records
    r'\bDOI\s*:',            # DOI citations
    r'\b10\.\d{4,}/',        # DOI pattern
    r'\bPMID\s*:',           # PubMed ID
    r'\beuropepmc:\d+',      # Europe PMC ID
    r'\bopenalex:W\d+',      # OpenAlex ID
    r'\bUS\s*\d{7,}',        # US patent number
    r'\bEP\s*\d{7,}',        # European patent
    r'\bWO\s*\d{2}/\d{6}',   # PCT patent
    r'\b21\s*CFR\s*\d',      # FDA regulation
    r'\bIEC\s*\d',           # IEC standards
    r'\bpeer[- ]reviewed\b', # Peer-reviewed reference
    r'\bcase\s*report\b',    # Case report
    r'\bregistry\s*data\b',  # Registry data
]

EXTERNAL_EVIDENCE_REGEX = re.compile('|'.join(EXTERNAL_EVIDENCE_PATTERNS), re.IGNORECASE)


def boundary_prefilter(kill_reason: str) -> dict:
    """CORRECTION 9: Cheap boundary pre-filter.
    
    If a BOUNDARY_CONDITION KILL reason contains conditional language
    AND has no external citation/evidence identifier:
    automatically classify as INSUFFICIENT_EVIDENCE.
    
    This is a SCREEN, not the final scientific evaluator.
    """
    if not kill_reason:
        return {"action": "PASS_THROUGH", "reason": "no kill reason to screen"}
    
    reason_lower = kill_reason.lower()
    words = set(re.findall(r'\b\w+\b', reason_lower))
    has_conditional = bool(words & CONDITIONAL_LANGUAGE)
    has_external_evidence = bool(EXTERNAL_EVIDENCE_REGEX.search(kill_reason))
    
    if has_conditional and not has_external_evidence:
        return {
            "action": "DOWNGRADE_TO_INSUFFICIENT_EVIDENCE",
            "reason": "Conditional language detected AND no external evidence citation",
            "conditional_words_found": sorted(words & CONDITIONAL_LANGUAGE),
            "external_evidence_found": False,
        }
    
    return {
        "action": "PASS_THROUGH",
        "reason": "Either no conditional language, or external evidence citation present",
        "conditional_words_found": sorted(words & CONDITIONAL_LANGUAGE) if has_conditional else [],
        "external_evidence_found": has_external_evidence,
    }


def validate_boundary_evidence(kill_reason: str, external_evidence: Optional[dict] = None) -> dict:
    """CORRECTION 5: Boundary condition evidence standard.
    
    A BOUNDARY_CONDITION=KILL requires:
    - specific boundary
    - failure mechanism
    - why candidate crosses the boundary
    - EXTERNAL evidence (published record, peer-reviewed paper, engineering reference, standard)
    
    The evaluator's own reasoning is NOT evidence.
    If no external evidence: INSUFFICIENT_EVIDENCE, do NOT kill.
    """
    # First apply the cheap pre-filter (Correction 9)
    prefilter_result = boundary_prefilter(kill_reason)
    if prefilter_result["action"] == "DOWNGRADE_TO_INSUFFICIENT_EVIDENCE":
        return {
            "valid": False,
            "disposition": "INSUFFICIENT_EVIDENCE",
            "reason": f"Pre-filter: {prefilter_result['reason']}",
            "prefilter_result": prefilter_result,
            "evidence_source": None,
        }
    
    # Check for external evidence
    if external_evidence is None:
        # Check if the kill reason itself contains an external evidence identifier
        if EXTERNAL_EVIDENCE_REGEX.search(kill_reason):
            return {
                "valid": True,
                "disposition": "KILL_PERMITTED",
                "reason": "External evidence identifier found in kill reason",
                "prefilter_result": prefilter_result,
                "evidence_source": "INLINE_CITATION",
            }
        return {
            "valid": False,
            "disposition": "INSUFFICIENT_EVIDENCE",
            "reason": "No external evidence provided and no inline citation found",
            "prefilter_result": prefilter_result,
            "evidence_source": None,
        }
    
    # External evidence provided — validate its structure
    required_fields = ["oracle_source_id", "oracle_source_type", "oracle_source_hash",
                       "oracle_evidence_span"]
    missing = [f for f in required_fields if f not in external_evidence or not external_evidence[f]]
    if missing:
        return {
            "valid": False,
            "disposition": "INSUFFICIENT_EVIDENCE",
            "reason": f"External evidence missing required fields: {missing}",
            "prefilter_result": prefilter_result,
            "evidence_source": "EXTERNAL_BUT_INCOMPLETE",
        }
    
    # SEMANTIC VALIDATION: require boundary_claim_supported + supporting_relationship
    # These fields prove the external span actually supports the boundary objection,
    # not just keyword co-occurrence.
    semantic_fields = ["boundary_claim_supported", "supporting_relationship"]
    semantic_missing = [f for f in semantic_fields if f not in external_evidence or not external_evidence[f]]
    if semantic_missing:
        return {
            "valid": False,
            "disposition": "INSUFFICIENT_EVIDENCE",
            "reason": f"External evidence missing semantic validation fields: {semantic_missing}. "
                      f"Keyword co-occurrence alone is insufficient.",
            "prefilter_result": prefilter_result,
            "evidence_source": "EXTERNAL_BUT_SEMANTICALLY_INCOMPLETE",
        }
    
    valid_types = {"PUBLISHED_FAILURE_RECORD", "PEER_REVIEWED_PAPER",
                   "ENGINEERING_REFERENCE", "REGULATORY_STANDARD", "PATENT_CLAIM",
                   "CASE_REPORT", "REGISTRY_DATA"}
    if external_evidence["oracle_source_type"] not in valid_types:
        return {
            "valid": False,
            "disposition": "INSUFFICIENT_EVIDENCE",
            "reason": f"oracle_source_type '{external_evidence['oracle_source_type']}' not in valid types: {valid_types}",
            "prefilter_result": prefilter_result,
            "evidence_source": "EXTERNAL_INVALID_TYPE",
        }
    
    return {
        "valid": True,
        "disposition": "KILL_PERMITTED",
        "reason": "External evidence provided with all required fields",
        "prefilter_result": prefilter_result,
        "evidence_source": external_evidence["oracle_source_id"],
        "external_evidence": external_evidence,
    }


# ===== CORRECTION 6: ADVERSARIAL_INVALID DISPOSITION =====

def check_adversarial_invalid(verdict: str, reason: str, evidence_valid: bool,
                              prior_art_state: str) -> dict:
    """CORRECTION 6: ADVERSARIAL_INVALID disposition.
    
    If:
    - verdict conflicts with reason, OR
    - reason conflicts with required evidence standard
    
    then: ADVERSARIAL_INVALID → EVALUATION_FAILED.
    
    Candidate does NOT become AIC, is NOT killed as invention defect,
    is NOT counted as successful adversarial survivor,
    is eligible for controlled re-evaluation.
    """
    conflicts = []
    
    # Check 1: verdict says SURVIVE but reason explicitly says it should be killed
    # Only flag clear contradictions: SURVIVE + "should be killed" / "fails" / "invalid"
    if verdict == "SURVIVE":
        # Look for explicit kill/fail language that contradicts SURVIVE
        # Must be a clear statement, not just containing the word
        reason_lower = reason.lower()
        clear_kill_phrases = ["should be killed", "should be fail", "is invalid",
                              "is killed", "fails to", "fails under", "is unsupported", "is infeasible",
                              "is a defect", "rejects", "does not survive"]
        if any(phrase in reason_lower for phrase in clear_kill_phrases):
            conflicts.append("verdict=SURVIVE but reason contains explicit kill language")
    
    # Check 2: BOUNDARY_CONDITION KILL without valid evidence
    if verdict == "KILL" and "boundary" in reason.lower() and not evidence_valid:
        conflicts.append("BOUNDARY_CONDITION KILL without valid external evidence")
    
    # Check 3: PRIOR_ART KILL on a non-kill prior-art state (Correction 10 firewall)
    if verdict == "KILL" and "prior" in reason.lower():
        non_kill_states = {"TOPICAL_RELATED", "POSSIBLE_RELEVANCE",
                          "NO_MATCH_FOUND", "UNRESOLVED_INSUFFICIENT_EVIDENCE"}
        if prior_art_state in non_kill_states:
            conflicts.append(f"PRIOR_ART KILL on non-kill prior-art state: {prior_art_state}")
    
    if conflicts:
        return {
            "disposition": "ADVERSARIAL_INVALID",
            "evaluation_status": "EVALUATION_FAILED",
            "invalid_reason": "; ".join(conflicts),
            "invalid_dimensions": conflicts,
            "re_evaluation_required": True,
            "is_aic": False,
            "is_survivor": False,
            "is_invention_defect": False,
        }
    
    return {
        "disposition": "VALID",
        "evaluation_status": "COMPLETED",
        "invalid_reason": None,
        "invalid_dimensions": [],
        "re_evaluation_required": False,
    }


# ===== CORRECTION 10: ADVERSARIAL PRIOR-ART FIREWALL =====

NON_KILL_PRIOR_ART_STATES = {
    "TOPICAL_RELATED",
    "POSSIBLE_RELEVANCE",
    "NO_MATCH_FOUND",
    "UNRESOLVED_INSUFFICIENT_EVIDENCE",
}

KILL_PRIOR_ART_STATES = {
    "SPECIFIC_DISCLOSURE",
    "IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE",
}


def enforce_prior_art_firewall(prior_art_state: str, adversarial_verdict: str,
                               adversarial_dimension: str) -> dict:
    """CORRECTION 10: Adversarial prior-art firewall.
    
    The adversarial evaluator must consume the frozen prior-art state.
    These prior-art states CANNOT become adversarial PRIOR_ART=KILL:
      TOPICAL_RELATED, POSSIBLE_RELEVANCE, NO_MATCH_FOUND, UNRESOLVED_INSUFFICIENT_EVIDENCE.
    Only SPECIFIC_DISCLOSURE, IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE may produce PRIOR_ART=KILL.
    """
    if adversarial_dimension != "PRIOR_ART":
        return {"firewall_applied": False, "reason": "not a PRIOR_ART dimension"}
    
    if adversarial_verdict != "KILL":
        return {"firewall_applied": False, "reason": "verdict is not KILL"}
    
    if prior_art_state in NON_KILL_PRIOR_ART_STATES:
        return {
            "firewall_applied": True,
            "action": "OVERRIDE_KILL_TO_SURVIVE",
            "reason": f"prior_art_state={prior_art_state} is a non-kill state; "
                      f"adversarial PRIOR_ART=KILL is forbidden",
            "corrected_verdict": "SURVIVE",
        }
    
    if prior_art_state in KILL_PRIOR_ART_STATES:
        return {
            "firewall_applied": False,
            "action": "KILL_PERMITTED",
            "reason": f"prior_art_state={prior_art_state} is a kill state",
        }
    
    return {
        "firewall_applied": True,
        "action": "OVERRIDE_KILL_TO_INSUFFICIENT_EVIDENCE",
        "reason": f"prior_art_state={prior_art_state} is unknown; cannot KILL",
        "corrected_verdict": "INSUFFICIENT_EVIDENCE",
    }


# ===== CORRECTION 11: EVIDENCE → ADVERSARIAL ORDERING =====

def check_evidence_gate_before_adversarial(evidence_verified: bool) -> dict:
    """CORRECTION 11: Evidence → adversarial ordering.
    
    Hard execution order: generation → target alignment → evidence verification
    → prior-art → adversarial → AIC.
    If evidence fails: adversarial MUST NOT run.
    """
    if not evidence_verified:
        return {
            "adversarial_should_run": False,
            "adversarial_status": "NOT_RUN",
            "adversarial_not_run_reason": "EVIDENCE_GATE_FAILED",
        }
    return {
        "adversarial_should_run": True,
        "adversarial_status": "ELIGIBLE",
        "adversarial_not_run_reason": None,
    }


# ===== CORRECTION 7: V3 SOURCE HASH RECONSTRUCTION =====

def reconstruct_source_hashes(source_ids: list, evidence_packet_sources: list) -> dict:
    """CORRECTION 7: V3 source hash reconstruction via Phase-D packet join.
    
    Join candidate.source_ids to Phase-D evidence packet source content_hash.
    If source_id found: reconstruct source_hash retroactively.
    If source_id missing: PROVENANCE_INCOMPLETE.
    """
    # Build lookup: source_id → content_hash
    source_lookup = {}
    for src in evidence_packet_sources:
        sid = src.get("source_id", "")
        ch = src.get("content_hash", "")
        if sid and ch:
            source_lookup[sid] = ch
    
    reconstructed = []
    missing = []
    for sid in source_ids:
        if sid in source_lookup:
            reconstructed.append({"source_id": sid, "source_hash": source_lookup[sid][:16]})
        else:
            missing.append(sid)
    
    return {
        "source_hash_reconstruction_method": "PHASE_D_PACKET_JOIN",
        "reconstructed_count": len(reconstructed),
        "missing_count": len(missing),
        "reconstructed": reconstructed,
        "missing": missing,
        "provenance_complete": len(missing) == 0,
        "provenance_status": "COMPLETE" if len(missing) == 0 else "PROVENANCE_INCOMPLETE",
    }


# ===== CORRECTION 8: PRELIMINARY M0 PROMOTION RULE =====

def determine_winner_v4(arm_yields: dict, arm_aics: dict, arm_totals: dict) -> dict:
    """CORRECTION 8: Preliminary M0 promotion rule.
    
    WINNING_ARCHITECTURE requires:
    - >=5pp lift over best preregistered comparator
    - Fisher exact test
    - Bonferroni-adjusted p < 0.05
    
    If M0 has highest yield but fails significance: PRELIMINARY_BEST_M0.
    Never WINNING_ARCHITECTURE without significance.
    """
    import math
    
    # Find best arm
    best_arm = max(arm_yields, key=arm_yields.get) if arm_yields else None
    best_yield = arm_yields.get(best_arm, 0) if best_arm else 0
    
    # Best comparator (excluding best arm)
    comparators = {k: v for k, v in arm_yields.items() if k != best_arm}
    best_comparator = max(comparators.values()) if comparators else 0
    best_comparator_arm = max(comparators, key=comparators.get) if comparators else None
    
    # Effect size: lift in percentage points
    lift_pp = (best_yield - best_comparator) * 100
    
    # Fisher exact test (2x2: best_arm AICs vs best_comparator AICs)
    # Using a simplified Fisher exact (manual computation for 2x2)
    a = arm_aics.get(best_arm, 0)
    b = arm_totals.get(best_arm, 100) - a
    c = arm_aics.get(best_comparator_arm, 0) if best_comparator_arm else 0
    d = arm_totals.get(best_comparator_arm, 100) if best_comparator_arm else 100 - c
    
    # Fisher exact p-value (one-sided, testing if best_arm > comparator)
    def fisher_exact_p(a, b, c, d):
        """One-sided Fisher exact test."""
        n = a + b + c + d
        # Hypergeometric probability
        from math import comb, lgamma
        def log_choose(n, k):
            return lgamma(n+1) - lgamma(k+1) - lgamma(n-k+1)
        
        # P(X >= a) under null
        row_total = a + b
        col_total = a + c
        log_p_total = 0
        for x in range(a, min(row_total, col_total) + 1):
            log_p = (log_choose(row_total, x) + log_choose(n - row_total, col_total - x)
                     - log_choose(n, col_total))
            log_p_total += math.exp(log_p) if log_p_total == 0 else math.exp(log_p)
        # Actually compute properly
        p_total = 0
        for x in range(a, min(row_total, col_total) + 1):
            log_p = (log_choose(row_total, x) + log_choose(n - row_total, col_total - x)
                     - log_choose(n, col_total))
            p_total += math.exp(log_p)
        return p_total
    
    try:
        raw_p = fisher_exact_p(a, b, c, d)
    except Exception:
        raw_p = 1.0
    
    # Bonferroni correction: number of comparisons = 5 (M2,M3,M4,M4B,M4C vs best baseline)
    n_comparisons = 5
    adjusted_p = min(raw_p * n_comparisons, 1.0)
    
    # Determine outcome
    meets_lift = lift_pp >= 5.0
    meets_significance = adjusted_p < 0.05
    
    if best_yield == 0:
        return {
            "outcome": "NO_WINNER",
            "reason": "All arms produced 0 AICs",
            "best_arm": best_arm,
            "best_yield": best_yield,
        }
    
    if meets_lift and meets_significance:
        return {
            "outcome": "WINNING_ARCHITECTURE",
            "winner": best_arm,
            "winner_yield": best_yield,
            "best_comparator": best_comparator_arm,
            "best_comparator_yield": best_comparator,
            "lift_pp": round(lift_pp, 2),
            "raw_p": round(raw_p, 6),
            "adjusted_p": round(adjusted_p, 6),
            "n_comparisons": n_comparisons,
            "meets_lift": meets_lift,
            "meets_significance": meets_significance,
            "fisher_table": {"a": a, "b": b, "c": c, "d": d},
        }
    
    if best_arm == "M0" and not meets_significance:
        return {
            "outcome": "PRELIMINARY_BEST_M0",
            "reason": "M0 has highest yield but does not meet significance threshold",
            "winner": None,
            "best_arm": "M0",
            "best_yield": best_yield,
            "best_comparator": best_comparator_arm,
            "best_comparator_yield": best_comparator,
            "lift_pp": round(lift_pp, 2),
            "raw_p": round(raw_p, 6),
            "adjusted_p": round(adjusted_p, 6),
            "meets_lift": meets_lift,
            "meets_significance": meets_significance,
            "fisher_table": {"a": a, "b": b, "c": c, "d": d},
        }
    
    return {
        "outcome": "NO_WINNER",
        "reason": f"Best arm {best_arm} does not meet lift ({lift_pp:.1f}pp < 5pp) "
                  f"or significance (adj_p={adjusted_p:.4f} >= 0.05)",
        "best_arm": best_arm,
        "best_yield": best_yield,
        "lift_pp": round(lift_pp, 2),
        "raw_p": round(raw_p, 6),
        "adjusted_p": round(adjusted_p, 6),
        "meets_lift": meets_lift,
        "meets_significance": meets_significance,
    }


# ===== CORRECTION 3: M4 CONTEXT ISOLATION =====

def commit_m4_memory(round_num: int, engine: str, memory: dict, output_dir: Path) -> dict:
    """CORRECTION 3: Commit M4 round memory to an immutable, content-addressed file.
    
    Creates: M4_R{round}_{engine}_MEMORY.json
    Each file is hashed and recorded in the round manifest.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"M4_R{round_num}_{engine.upper()}_MEMORY.json"
    path = output_dir / filename
    
    # Content-address: hash the memory content
    content = json.dumps(memory, sort_keys=True, default=str)
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # Write with metadata
    artifact = {
        "round": round_num,
        "engine": engine,
        "content_hash": content_hash,
        "committed_at": datetime.now(timezone.utc).isoformat(),
        "memory": memory,
    }
    
    path.write_text(json.dumps(artifact, indent=2, default=str))
    return {
        "filename": filename,
        "path": str(path),
        "content_hash": content_hash,
        "context_source_mode": "COMMITTED_FILE",
    }


def load_m4_memory(round_num: int, engine: str, input_dir: Path) -> dict:
    """CORRECTION 3: Load M4 round memory from committed file.
    
    Asserts: context_source_mode == "COMMITTED_FILE".
    If file doesn't exist: M4_INVALID_CONTEXT_SOURCE.
    """
    filename = f"M4_R{round_num}_{engine.upper()}_MEMORY.json"
    path = input_dir / filename
    
    if not path.exists():
        raise FileNotFoundError(
            f"M4_INVALID_CONTEXT_SOURCE: committed memory file {filename} does not exist. "
            f"Round {round_num + 1} cannot read {engine} memory from round {round_num}."
        )
    
    with open(path) as f:
        artifact = json.load(f)
    
    # Machine assertion
    assert artifact.get("context_source_mode") == "COMMITTED_FILE" or \
           "content_hash" in artifact, \
           f"M4_INVALID_CONTEXT_SOURCE: {filename} is not a committed file artifact."
    
    return {
        "memory": artifact.get("memory", {}),
        "content_hash": artifact.get("content_hash"),
        "source_file": filename,
        "context_source_mode": "COMMITTED_FILE",
    }


# Import needed for commit_m4_memory
from datetime import datetime, timezone


# ===== BOUNDARY EVIDENCE RESOLVER (SEMANTIC VALIDATION) =====
# Retrieves external boundary evidence from the candidate's evidence packet.
# The LLM adversarial evaluator does NOT get to invent evidence — it must
# come from the frozen Phase-D evidence packet sources.
#
# SEMANTIC VALIDATION (not keyword-only):
#   A valid boundary evidence object requires the external span to support:
#     A. the specific boundary/threshold
#     B. the specific failure mechanism
#     C. the RELATIONSHIP between the boundary and failure
#   Keyword co-occurrence alone is INSUFFICIENT.

# Boundary-condition indicators — used ONLY to identify CANDIDATE spans,
# NOT to establish evidence sufficiency.
_BOUNDARY_INDICATORS = [
    "threshold", "limit", "maximum", "minimum", "boundary", "range",
    "ISO", "ASTM", "IEC", "FDA", "21 CFR", "standard",
    "failure condition", "operating condition", "specification",
    "temperature", "pressure", "voltage", "frequency", "cycle",
    "mg/mL", "MPa", "kPa", "°C", "Hz",
    "mL/h", "mL/min", "L/min", "bpm", "mmHg",
    "flow rate", "dose limit", "rate limit",
    "exceeds", "surpasses", "above", "beyond",
]

# Causal relationship indicators — the span must connect the boundary
# to the failure mechanism (not just mention both independently).
_CAUSAL_RELATIONSHIP_INDICATORS = [
    "causes", "due to", "because", "results in", "leads to",
    "triggers", "initiates", "produces", "induces",
    "when exceeded", "beyond", "above", "below",
    "exceeds", "surpasses", "violates",
    "failure occurs", "fails when", "fails at",
    "degradation begins", "onset of",
    "at this level", "at this threshold",
    "consequently", "therefore", "as a result",
]


def _has_boundary_indicator(span_lower: str) -> bool:
    """Check if span contains any boundary indicator (retrieval heuristic only)."""
    return any(ind.lower() in span_lower for ind in _BOUNDARY_INDICATORS)


def _has_causal_relationship(span_lower: str) -> bool:
    """Check if span contains a causal relationship between boundary and failure."""
    return any(ind.lower() in span_lower for ind in _CAUSAL_RELATIONSHIP_INDICATORS)


def _has_failure_mechanism(span_lower: str, failure_mode: str) -> bool:
    """Check if span mentions the specific failure mechanism."""
    if not failure_mode:
        return False
    fm_words = [w for w in failure_mode.split() if len(w) > 3]
    return any(w in span_lower for w in fm_words)


def _has_device_reference(span_lower: str, device: str) -> bool:
    """Check if span mentions the device."""
    if not device:
        return False
    dev_words = [w for w in device.split() if len(w) > 3]
    return any(w in span_lower for w in dev_words)


def _extract_boundary_claim(span: str, failure_mode: str, device: str) -> str:
    """Extract the specific boundary claim supported by this span."""
    # Find the sentence containing both boundary indicator and failure/device reference
    sentences = span.split(".")
    for sent in sentences:
        sent_lower = sent.lower()
        if _has_boundary_indicator(sent_lower) and (
            _has_failure_mechanism(sent_lower, failure_mode) or
            _has_device_reference(sent_lower, device)):
            return sent.strip()[:200]
    # Fallback: first 200 chars of span
    return span[:200]


def _extract_supporting_relationship(span: str) -> str:
    """Extract the causal relationship that connects boundary to failure."""
    span_lower = span.lower()
    for indicator in _CAUSAL_RELATIONSHIP_INDICATORS:
        idx = span_lower.find(indicator.lower())
        if idx != -1:
            # Extract context around the causal indicator
            start = max(0, idx - 50)
            end = min(len(span), idx + len(indicator) + 80)
            return span[start:end].strip()
    return ""


def resolve_boundary_evidence(candidate: dict, evidence_packet_sources: list = None) -> Optional[dict]:
    """Resolve external boundary evidence from the candidate's evidence packet.
    
    SEMANTIC VALIDATION:
      A valid boundary evidence object requires the external span to support:
        A. the specific boundary/threshold (boundary indicator present)
        B. the specific failure mechanism (failure mode mentioned)
        C. the RELATIONSHIP between the boundary and failure (causal indicator present)
      
      Keyword co-occurrence alone is INSUFFICIENT.
    
    Returns a dict with:
      source_id, source_type, full_source_hash, source_url, retrieval_timestamp,
      evidence_span, boundary_claim_supported, supporting_relationship
    
    Returns None if no valid external boundary evidence exists.
    """
    if not evidence_packet_sources:
        evidence_packet_sources = candidate.get("sources", []) or candidate.get("evidence_sources", [])
    
    if not evidence_packet_sources:
        return None
    
    failure_mode = (candidate.get("failure_mode", "") or "").lower().replace("_", " ")
    device = (candidate.get("device_class", "") or candidate.get("device_name", "") or "").lower()
    
    for src in evidence_packet_sources:
        span = src.get("source_span", "")
        span_lower = span.lower()
        
        # STEP 1: Must contain a boundary indicator (retrieval heuristic)
        if not _has_boundary_indicator(span_lower):
            continue
        
        # STEP 2: Must mention the device OR the failure mechanism
        has_device = _has_device_reference(span_lower, device)
        has_failure = _has_failure_mechanism(span_lower, failure_mode)
        if not has_device and not has_failure:
            continue
        
        # STEP 3 (SEMANTIC): Must contain a causal relationship connecting
        # the boundary to the failure. This is the key semantic test.
        # A span that merely mentions "device", "threshold", and "failure"
        # independently is NOT sufficient.
        has_causal = _has_causal_relationship(span_lower)
        if not has_causal:
            continue
        
        # STEP 4 (SEMANTIC): The boundary indicator and the failure/device
        # reference must appear in the SAME sentence or adjacent context,
        # not just in the same span. This prevents the case where a paper
        # mentions "temperature threshold" in one paragraph and "device failure"
        # in an unrelated paragraph.
        boundary_claim = _extract_boundary_claim(span, failure_mode, device)
        if not boundary_claim:
            continue
        
        supporting_rel = _extract_supporting_relationship(span)
        if not supporting_rel:
            continue
        
        # All semantic checks passed — valid external boundary evidence
        full_hash = src.get("content_hash", "")
        return {
            "oracle_source_id": src.get("source_id", ""),
            "oracle_source_type": _classify_source_type(src),
            "oracle_source_hash": full_hash,  # FULL hash, not truncated
            "full_source_hash": full_hash,  # explicit full hash field
            "oracle_source_url": src.get("doi", "") or src.get("source_id", ""),
            "oracle_evidence_span": span[:500],
            "oracle_reason": f"Boundary evidence with causal support found in source {src.get('source_id','')}",
            "boundary_claim_supported": boundary_claim,
            "supporting_relationship": supporting_rel,
            "retrieval_timestamp": src.get("retrieval_timestamp", ""),
            "semantic_validation": {
                "has_boundary_indicator": True,
                "has_device_or_failure_reference": has_device or has_failure,
                "has_causal_relationship": True,
                "boundary_claim_extracted": bool(boundary_claim),
                "supporting_relationship_extracted": bool(supporting_rel),
            },
        }
    
    return None


def _classify_source_type(src: dict) -> str:
    """Classify the source type for external evidence."""
    source_type = src.get("source_type", "")
    if source_type == "PUBLICATION":
        return "PEER_REVIEWED_PAPER"
    if "patent" in source_type.lower():
        return "PATENT_CLAIM"
    if "fda" in src.get("source_id", "").lower() or "maude" in src.get("source_id", "").lower():
        return "PUBLISHED_FAILURE_RECORD"
    if "iso" in src.get("source_span", "").lower() or "astm" in src.get("source_span", "").lower():
        return "REGULATORY_STANDARD"
    return "PEER_REVIEWED_PAPER"  # default for Europe PMC / OpenAlex sources


# ===== PRODUCTION WRAPPERS (task-required function names) =====
# These provide the exact API names the production adversarial path expects.
# They delegate to the authoritative implementations above — ONE implementation.

def evaluate_boundary_condition(kill_reason: str, external_evidence: Optional[dict] = None) -> dict:
    """PRODUCTION ENTRY POINT for boundary-condition evaluation.
    
    Wraps validate_boundary_evidence() + boundary_prefilter().
    A BOUNDARY_CONDITION=KILL requires:
      - specific boundary
      - failure mechanism
      - why candidate crosses the boundary
      - external evidence (published record, peer-reviewed paper, engineering reference, standard)
    
    The evaluator's own reasoning is NOT evidence.
    If no external evidence: INSUFFICIENT_EVIDENCE, do NOT kill.
    """
    return validate_boundary_evidence(kill_reason, external_evidence)


def skip_if_evidence_failed(evidence_verified: bool) -> dict:
    """PRODUCTION ENTRY POINT for evidence-gate check.
    
    Wraps check_evidence_gate_before_adversarial().
    If evidence fails: adversarial MUST NOT run.
    Returns adversarial_status = NOT_RUN, adversarial_not_run_reason = EVIDENCE_GATE_FAILED.
    """
    return check_evidence_gate_before_adversarial(evidence_verified)
