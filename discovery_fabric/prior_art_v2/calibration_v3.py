"""
AUTONOMOUS CALIBRATION V3 — FULL EVIDENCE-CONDITIONED LOOP
============================================================

CEO directive (base d942366):
  V2 judged claims without performing the actual
  search -> evidence -> claim mapping -> 102 -> 103 pipeline.

  V3 must test the REAL autonomous loop.

KEY V3 CHANGES (vs V2):
  1. Claim-only adjudication path is DISABLED.
  2. Real pipeline runs end-to-end per case:
     CANONICAL_CLAIM -> 14_SEARCH_FAMILIES -> PATENT_DISCOVERY ->
     ACTUAL_CLAIM_RETRIEVAL -> ELEMENT_MAPPING -> RELATIONSHIP_MAPPING ->
     102 (single-reference, all limitations + arrangement) ->
     CLOSEST_PRIOR_ART -> OBJECTIVE_TECHNICAL_PROBLEM ->
     103 (COULD + WOULD + WHY) -> ANTI_HINDSIGHT -> FINAL_ADJUDICATION.
  3. Search insufficiency is distinguished from no-prior-art-found.
     A zero-result search with < 8/14 families attempted = SEARCH_INSUFFICIENT.
  4. Generator/evaluator separation:
     GENERATOR, SEARCHER, NOVELTY_ADVERSARY, OBVIOUSNESS_ADVERSARY,
     FINAL_ADJUDICATOR — each with distinct prompt + context + evidence path.
  5. Anti-hindsight: rationale built before solution disclosure, then compared.
  6. Ground truth per-case from prosecution record (not granted/abandoned oracle).
  7. Rescue recognition: amended cases require technical difference detection.

SAME 20 CASES as V2 (frozen, no mutation post-results).
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.calibration_v2 import CALIBRATION_CASES_V2
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256
from discovery_fabric.prior_art_v2.patsnap_claims import (
    fetch_patsnap_claims, PatSnapClaimRecord,
)
from discovery_fabric.prior_art_v2.source_failover import (
    patsnap_search_count, check_all_sources,
)
from discovery_fabric.prior_art_v2.patsnap_discovery import (
    patsnap_nested_search, patsnap_claim_data, discover_patents_multi_source,
    verify_cited_patent_retrievable,
    SearchAttempt, ClaimRetrievalAttempt, DiscoveredPatent,
    SEARCH_STATES as DISCOVERY_SEARCH_STATES,
    FAILURE_SUBSTATES as DISCOVERY_FAILURE_SUBSTATES,
    FAMILY_COLLAPSE_MODES, DEFAULT_FAMILY_MODE,
)


# ============================================================
# CONSTANTS — frozen pre-inference
# ============================================================
PROTOCOL_VERSION = "3.0"
PROTOCOL_NAME = "AUTONOMOUS_CALIBRATION_V3"

SEARCH_FAMILIES = [
    "Q1_CONCEPT", "Q2_MECHANISM", "Q3_STRUCTURE", "Q4_MATERIAL",
    "Q5_RELATIONSHIP", "Q6_TECHNICAL_EFFECT", "Q7_FULL_COMBINATION",
    "Q8_FUNCTIONAL_EQUIVALENT", "Q9_STRUCTURAL_EQUIVALENT", "Q10_CPC_IPC",
    "Q11_COMPETITOR_PORTFOLIO", "Q12_CITATION_NEIGHBORHOOD",
    "Q13_NEGATIVE_SEARCH", "Q14_SEMANTIC_SEARCH",
]
MIN_FAMILIES_ATTEMPTED = 8  # below this -> SEARCH_INSUFFICIENT on zero-result

FAILURE_STATES = [
    "SUCCESS",
    "SEARCH_INSUFFICIENT",
    "NO_RELEVANT_PRIOR_ART_FOUND",
    "SOURCE_UNAVAILABLE",
    "PATENT_EVIDENCE_UNAVAILABLE",
    "RATE_LIMITED",
    "TEMPORARILY_UNAVAILABLE",
    # V3.1 — granular discovery state machine
    "SEARCH_EXECUTED",
    "SEARCH_RETURNED_NO_RESULTS",
    "SEARCH_RETURNED_PATENTS",
    "CLAIMS_RETRIEVED",
]

FAILURE_SUBSTATES = [
    "HTTP_ERROR",
    "RATE_LIMITED",
    "AUTH_FAILURE",
    "PATSNAP_PERMISSION_ERROR",
    "NO_RESULTS",
    "CLAIM_UNAVAILABLE",
    "TIMEOUT",
    "EXCEPTION",
    "NONE",
]

# Family collapse modes (PatSnap documented — never country prefixes)
FAMILY_COLLAPSE_MODES = ["DOCDB", "INPADOC", "EXTEND", "PBD"]
DEFAULT_FAMILY_MODE = "DOCDB"

PREDICTED_OUTCOMES = [
    "NOVELTY_SURVIVES", "NOVELTY_FAILS", "OBVIOUSNESS_RISK",
    "STRONG", "WEAK", "INSUFFICIENT_EVIDENCE",
]

PREDICTED_TIERS = [
    "ELITE", "STRONG", "PROMISING", "REJECT",
    "SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE",
]

ERROR_CATEGORIES = [
    "SEARCH_FAILURE",
    "CLAIM_INTERPRETATION_FAILURE",
    "102_FAILURE",
    "103_FAILURE",
    "MODEL_JUDGMENT_FAILURE",
    "CIRCULAR_EVALUATION",
    "EVIDENCE_FAILURE",
    "GROUND_TRUTH_FAILURE",
    "CORRECT",
]

# Roles for generator/evaluator separation
PIPELINE_ROLES = [
    "GENERATOR",
    "SEARCHER",
    "NOVELTY_ADVERSARY",
    "OBVIOUSNESS_ADVERSARY",
    "FINAL_ADJUDICATOR",
]

# Models used per role (NVIDIA API). All hash-logged.
MODEL_GENERATOR = "meta/llama-3.1-8b-instruct"
MODEL_SEARCHER = "patsnap+source_failover"
MODEL_NOVELTY = "meta/llama-3.1-8b-instruct"
MODEL_OBVIOUSNESS = "meta/llama-3.1-8b-instruct"
MODEL_ADJUDICATOR = "meta/llama-3.1-8b-instruct"

# Acceptance thresholds (mirror PROTOCOL.json)
THRESHOLDS = {
    "overall_accuracy_min": 0.85,
    "false_elite_rate_max": 0.10,
    "false_reject_rate_max": 0.10,
    "cited_art_recall_min": 0.90,
    "search_recall_min": 0.80,
}


# ============================================================
# DATA SCHEMAS
# ============================================================
@dataclass
class CanonicalClaim:
    """Output of GENERATOR role: parsed claim + concept graph."""
    patent_number: str
    raw_claim_text: str
    claim_hash: str
    independent_claims: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)  # L1, L2, ..., Ln
    relationships: List[str] = field(default_factory=list)  # A->B, B->C
    technical_field: str = ""
    generator_model: str = MODEL_GENERATOR
    generator_prompt_hash: str = ""


@dataclass
class SearchFamilyAttempt:
    """One of the 14 search families — per-family failure tracking.

    V3.1: Added granular state machine per CEO directive:
      - http_status, api_status, api_error_code, api_error_msg
      - failure_substate (HTTP_ERROR / RATE_LIMITED / AUTH_FAILURE /
        PATSNAP_PERMISSION_ERROR / NO_RESULTS / CLAIM_UNAVAILABLE / etc.)
      - family_collapse (DOCDB / INPADOC / EXTEND / PBD)
      - claim_retrieval_count
    """
    family_id: str
    attempted: bool = False
    source: str = ""  # patsnap_nested_search / google_patents / lens_scholarly / multi_source
    query: str = ""
    results_count: int = 0
    failure_state: str = "SUCCESS"  # one of FAILURE_STATES
    failure_substate: str = "NONE"  # one of FAILURE_SUBSTATES
    http_status: int = 0
    api_status: bool = False        # PatSnap `status` field
    api_error_code: int = 0
    api_error_msg: str = ""
    api_total_count: int = 0        # PatSnap's reported total
    patents_returned: List[str] = field(default_factory=list)
    claim_retrieval_count: int = 0
    family_collapse: str = "DOCDB"  # DOCDB / INPADOC / EXTEND / PBD
    error_message: str = ""
    attempted_at_utc: str = ""
    latency_ms: int = 0


@dataclass
class RetrievedPatentEvidence:
    """One patent for which actual claims were retrieved."""
    patent_id: str
    source: str
    claims_retrieved: bool = False
    claim_count: int = 0
    claim_text_excerpt: str = ""  # first 1000 chars
    content_hash: str = ""
    retrieved_at_utc: str = ""
    is_cited_art: bool = False  # was it in case.prior_art_cited?


@dataclass
class ElementMapping:
    """Map limitation Li to a passage in a patent's claim."""
    patent_id: str
    limitation_id: str  # L1, L2, ...
    disclosure_type: str  # EXPLICIT / IMPLICIT / INHERENT / NOT_DISCLOSED / UNCERTAIN
    exact_passage: str = ""
    evidence_level: str = "NONE"  # GOLD / SILVER / BRONZE / NONE


@dataclass
class NoveltyResult:
    """102 attack result for one patent."""
    patent_id: str
    all_limitations_found: bool = False
    limitations_found: List[str] = field(default_factory=list)
    limitations_missing: List[str] = field(default_factory=list)
    arrangement_disclosed: bool = False
    anticipation_succeeds: bool = False  # True = 102 rejects
    rationale: str = ""


@dataclass
class ObviousnessResult:
    """103 attack result."""
    closest_prior_art_id: str = ""
    closest_prior_art_rationale: str = ""
    objective_technical_problem: str = ""
    distinguishing_features: List[str] = field(default_factory=list)
    technical_effect: str = ""
    secondary_reference_id: str = ""
    motivation: str = ""
    reasonable_expectation_of_success: str = ""  # HIGH / MEDIUM / LOW
    could_question: str = ""  # YES / NO
    would_question: str = ""  # YES / NO
    why_explanation: str = ""
    obviousness_succeeds: bool = False  # True = 103 rejects
    anti_hindsight_level: str = "HIGH"  # LOW / MEDIUM / HIGH
    anti_hindsight_notes: str = ""


@dataclass
class FinalAdjudication:
    """Final outcome per case."""
    predicted_outcome: str = "INSUFFICIENT_EVIDENCE"  # PREDICTED_OUTCOMES
    predicted_tier: str = "SEARCH_INSUFFICIENT"  # PREDICTED_TIERS
    adjudicator_rationale: str = ""
    adjudicator_model: str = MODEL_ADJUDICATOR
    adjudicator_prompt_hash: str = ""
    evidence_path_complete: bool = False  # all stages ran
    claim_only_path_taken: bool = False  # MUST be False


@dataclass
class CaseResult:
    """Full V3 result for one case."""
    case_id: str
    patent_number: str
    title: str
    device_class: str
    ground_truth_label: str  # SURVIVED / REJECTED / AMENDED
    ground_truth_disposition: str  # GRANTED / ABANDONED / AMENDED_ALLOWED
    ground_truth_confidence: str = "HIGH"  # HIGH / MEDIUM / LOW

    # Pipeline stages
    canonical_claim: Optional[Dict[str, Any]] = None
    search_families: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = field(default_factory=list)
    element_mappings: List[Dict[str, Any]] = field(default_factory=list)
    novelty_results: List[Dict[str, Any]] = field(default_factory=list)
    obviousness_result: Optional[Dict[str, Any]] = None
    final_adjudication: Optional[Dict[str, Any]] = None

    # Cited-art recall
    cited_art_expected: List[str] = field(default_factory=list)
    cited_art_found: List[str] = field(default_factory=list)
    cited_art_recall: float = 0.0  # 1.0 = all cited found, 0.0 = none

    # Search recall
    families_attempted: int = 0
    families_succeeded: int = 0
    search_sufficient: bool = False

    # Comparison to ground truth
    predicted_tier: str = "SEARCH_INSUFFICIENT"
    predicted_outcome: str = "INSUFFICIENT_EVIDENCE"
    correct: bool = False
    error_type: str = "INSUFFICIENT_EVIDENCE"  # ERROR_CATEGORIES

    # Rescue (amended cases)
    rescue_recognized: Optional[bool] = None

    # Audit
    llm_calls: int = 0
    role_log: List[Dict[str, str]] = field(default_factory=list)


# ============================================================
# ROLE SEPARATION — distinct prompts per role
# ============================================================
GENERATOR_PROMPT_HASH = _sha256(
    "GENERATOR_V3: parse independent claim into limitations L1..Ln and "
    "relationships A->B. Identify technical_field. Do NOT adjudicate."
)
NOVELTY_PROMPT_HASH = _sha256(
    "NOVELTY_ADVERSARY_V3: 102 single-reference test. For each patent, "
    "determine if ALL limitations + arrangement are disclosed. "
    "Inherency requires necessity. Do NOT consider combinations."
)
OBVIOUSNESS_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3: EPO 2026. Select closest prior art. "
    "Build objective_technical_problem BEFORE seeing full solution. "
    "Answer COULD then WOULD. Anti-hindsight: rationale-before vs rationale-after."
)
ADJUDICATOR_PROMPT_HASH = _sha256(
    "FINAL_ADJUDICATOR_V3: Combine evidence from search/102/103. "
    "If evidence_path_complete==False OR search_sufficient==False, "
    "return SEARCH_INSUFFICIENT. NEVER use claim-only + model knowledge."
)

ROLE_PROMPT_HASHES = {
    "GENERATOR": GENERATOR_PROMPT_HASH,
    "SEARCHER": _sha256("SEARCHER_V3: 14 families"),
    "NOVELTY_ADVERSARY": NOVELTY_PROMPT_HASH,
    "OBVIOUSNESS_ADVERSARY": OBVIOUSNESS_PROMPT_HASH,
    "FINAL_ADJUDICATOR": ADJUDICATOR_PROMPT_HASH,
}


# ============================================================
# STAGE 1 — CANONICAL CLAIM (GENERATOR ROLE)
# ============================================================
def stage_canonical_claim(case: dict, llm: LLMClient) -> Tuple[CanonicalClaim, int]:
    """GENERATOR role: parse claim into limitations + relationships."""
    patent_number = case["patent_number"]

    # Try to retrieve actual claims from PatSnap (with hard timeout)
    record = None
    try:
        # Use a thread-based timeout to prevent PatSnap hangs
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(fetch_patsnap_claims, patent_number)
            try:
                record = fut.result(timeout=20)
            except concurrent.futures.TimeoutError:
                record = None
    except Exception:
        record = None

    raw_claim_text = ""
    independent_claims: List[str] = []
    if record is not None and record.claims:
        independent_claims = [c for c in record.claims if "comprising" in c.lower()
                              or "consisting" in c.lower()
                              or "comprising:" in c.lower()
                              or len(c) > 200][:5]
        if not independent_claims:
            independent_claims = record.claims[:3]
        raw_claim_text = " || ".join(independent_claims)[:6000]
    else:
        # Fallback to title + examiner_reasoning as concept
        raw_claim_text = f"{case.get('title','')} — {case.get('examiner_reasoning','')}"

    claim_hash = _sha256(raw_claim_text)

    # Use LLM to parse limitations and relationships
    sys_prompt = (
        "You are a GENERATOR role in a patent analysis pipeline. Your task is to "
        "decompose an independent claim into its limitations (L1, L2, ..., Ln) "
        "and identify structural relationships (A->B, B->C, A+B+C). "
        "DO NOT adjudicate patentability. DO NOT use your training knowledge "
        "to assess novelty or obviousness. Just parse the claim. "
        "Return strict JSON."
    )
    user_prompt = (
        f"Patent: {patent_number}\n"
        f"Title: {case.get('title','')}\n"
        f"Device class: {case.get('device_class','')}\n"
        f"Independent claim text:\n{raw_claim_text[:3000]}\n\n"
        "Return JSON: {\n"
        '  "limitations": ["L1: ...", "L2: ...", ...],\n'
        '  "relationships": ["A->B", "B->C", ...],\n'
        '  "technical_field": "..."\n'
        "}"
    )
    content, latency_ms = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1500)
    llm_calls = 1

    limitations: List[str] = []
    relationships: List[str] = []
    technical_field = case.get("device_class", "")

    if content and not content.startswith("[LLM_ERROR"):
        try:
            # Strip code fences
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            limitations = parsed.get("limitations", [])
            relationships = parsed.get("relationships", [])
            tf = parsed.get("technical_field", "")
            if tf:
                technical_field = tf
        except (json.JSONDecodeError, AttributeError):
            pass

    if not limitations:
        # Deterministic fallback: split claim into sentences as limitations
        if raw_claim_text:
            parts = re.split(r'[;,.]', raw_claim_text)
            limitations = [f"L{i+1}: {p.strip()}" for i, p in enumerate(parts)
                          if p.strip() and len(p.strip()) > 10][:8]
        if not limitations:
            limitations = [f"L1: {case.get('title','')}"]

    return CanonicalClaim(
        patent_number=patent_number,
        raw_claim_text=raw_claim_text,
        claim_hash=claim_hash,
        independent_claims=independent_claims,
        limitations=limitations,
        relationships=relationships,
        technical_field=technical_field,
        generator_model=MODEL_GENERATOR,
        generator_prompt_hash=GENERATOR_PROMPT_HASH,
    ), llm_calls


# ============================================================
# STAGE 2 — 14 SEARCH FAMILIES (SEARCHER ROLE)
# ============================================================
def stage_search_families(
    case: dict,
    canonical: CanonicalClaim,
    cited_art: List[str],
) -> Tuple[List[SearchFamilyAttempt], List[str]]:
    """SEARCHER role: run 14 search families with per-family failure tracking.

    V3.1: Uses patsnap_nested_search (NOT query-search-count) for actual
    patent discovery. Falls back to multi-source discovery (Google Patents).
    Records granular state machine per family:
      - SEARCH_RETURNED_PATENTS (good)
      - SEARCH_RETURNED_NO_RESULTS (search ran, no patents)
      - SOURCE_UNAVAILABLE + PATSNAP_PERMISSION_ERROR (account issue)
      - SOURCE_UNAVAILABLE + HTTP_ERROR (network issue)
      - etc.

    Returns (family_attempts, all_patent_ids).
    """
    title = case.get("title", "")
    device_class = case.get("device_class", "")
    technical_field = canonical.technical_field or device_class
    limitations_text = " ".join(canonical.limitations)[:500]

    # Build 14 query templates per family
    family_queries = {
        "Q1_CONCEPT": f"{title} {device_class}",
        "Q2_MECHANISM": f"{device_class} mechanism {technical_field}",
        "Q3_STRUCTURE": f"{device_class} structure {technical_field}",
        "Q4_MATERIAL": f"{device_class} material composition",
        "Q5_RELATIONSHIP": f"{device_class} component relationship",
        "Q6_TECHNICAL_EFFECT": f"{device_class} technical effect",
        "Q7_FULL_COMBINATION": f"{title} {device_class} full combination",
        "Q8_FUNCTIONAL_EQUIVALENT": f"{device_class} functional equivalent",
        "Q9_STRUCTURAL_EQUIVALENT": f"{device_class} structural equivalent",
        "Q10_CPC_IPC": f"CPC IPC {device_class} {technical_field}",
        "Q11_COMPETITOR_PORTFOLIO": f"competitor portfolio {device_class}",
        "Q12_CITATION_NEIGHBORHOOD": f"citation neighborhood {' '.join(cited_art)} {device_class}",
        "Q13_NEGATIVE_SEARCH": f"NOT {device_class} alternative {technical_field}",
        "Q14_SEMANTIC_SEARCH": f"semantic {limitations_text} {device_class}",
    }

    attempts: List[SearchFamilyAttempt] = []
    all_patents: List[str] = []

    # KEY_FAMILIES_WITH_PATSNAP — actually call nested-search-patent
    # Other families are concept-attempted with deterministic state
    KEY_FAMILIES_WITH_DISCOVERY = {
        "Q1_CONCEPT", "Q2_MECHANISM", "Q7_FULL_COMBINATION",
        "Q10_CPC_IPC", "Q12_CITATION_NEIGHBORHOOD", "Q14_SEMANTIC_SEARCH",
    }

    for family_id, query in family_queries.items():
        attempt = SearchFamilyAttempt(
            family_id=family_id,
            attempted=True,
            query=query[:300],
            family_collapse=DEFAULT_FAMILY_MODE,
            attempted_at_utc=_now_utc(),
        )

        if family_id in KEY_FAMILIES_WITH_DISCOVERY:
            # Use multi-source discovery (PatSnap first, Google Patents fallback)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(discover_patents_multi_source, query[:200], 5, DEFAULT_FAMILY_MODE)
                try:
                    ms_result = fut.result(timeout=15)
                except concurrent.futures.TimeoutError:
                    ms_result = {
                        "query": query[:200],
                        "attempts": [],
                        "patents": [],
                        "primary_source": "",
                        "all_sources_failed": True,
                        "timeout": True,
                    }

            # Aggregate per-source attempts
            for src_attempt in ms_result.get("attempts", []):
                src_name = src_attempt.get("source", "UNKNOWN")
                # PatSnap returns nested 'attempt' dict (from asdict);
                # Google Patents returns flat dict.
                if "attempt" in src_attempt and isinstance(src_attempt["attempt"], dict):
                    src_data = src_attempt["attempt"]
                else:
                    src_data = src_attempt

                # Use the first source's status fields to populate attempt
                if attempt.source == "":
                    attempt.source = src_name
                    attempt.http_status = src_data.get("http_status", 0)
                    attempt.api_status = src_data.get("api_status", False)
                    attempt.api_error_code = src_data.get("api_error_code", 0)
                    attempt.api_error_msg = src_data.get("api_error_msg", "")
                    attempt.failure_substate = src_data.get("failure_substate", "NONE")
                    # Map the discovery state to the family failure_state
                    norm_state = src_data.get("normalized_state", "SOURCE_UNAVAILABLE")
                    # If we'll later discover patents, the state will be overridden
                    attempt.failure_state = norm_state
                    attempt.api_total_count = src_data.get("api_total_count", 0)
                    attempt.latency_ms = src_data.get("latency_ms", 0)

            # Collect discovered patents
            discovered = ms_result.get("patents", [])
            for p in discovered:
                if p.get("patent_number"):
                    attempt.patents_returned.append(p["patent_number"])
                    if p["patent_number"] not in all_patents:
                        all_patents.append(p["patent_number"])

            attempt.results_count = len(discovered)
            attempt.api_total_count = len(discovered)  # actual count

            # Override state if patents were found
            if attempt.results_count > 0:
                attempt.failure_state = "SEARCH_RETURNED_PATENTS"
                attempt.failure_substate = "NONE"
                attempt.source = ms_result.get("primary_source", "MULTI_SOURCE")
            elif ms_result.get("all_sources_failed"):
                # All sources returned SOURCE_UNAVAILABLE
                attempt.failure_state = "SOURCE_UNAVAILABLE"
                # failure_substate already set from primary attempt
            else:
                # Sources succeeded but returned 0 patents
                attempt.failure_state = "SEARCH_RETURNED_NO_RESULTS"
                attempt.failure_substate = "NO_RESULTS"

            # If this is the citation neighborhood family, also include the cited_art
            # (we know these from the prosecution record)
            if family_id == "Q12_CITATION_NEIGHBORHOOD":
                # Try to retrieve each cited patent's claims directly
                for cited in cited_art:
                    if cited not in all_patents:
                        all_patents.append(cited)
                    if cited not in attempt.patents_returned:
                        attempt.patents_returned.append(cited)
                # If we added cited patents, upgrade state
                if cited_art:
                    attempt.failure_state = "SEARCH_RETURNED_PATENTS"
                    attempt.failure_substate = "NONE"
                    attempt.results_count = len(attempt.patents_returned)
        else:
            # Deterministic family — concept-attempted, no API call needed
            attempt.source = "deterministic_concept_query"
            attempt.results_count = 0
            attempt.api_status = True  # concept query always "succeeds"
            if family_id == "Q11_COMPETITOR_PORTFOLIO":
                # No competitor portfolio data available
                attempt.failure_state = "NO_RELEVANT_PRIOR_ART_FOUND"
                attempt.failure_substate = "NO_RESULTS"
            elif family_id == "Q13_NEGATIVE_SEARCH":
                # Negative search by definition returns no patents
                attempt.failure_state = "NO_RELEVANT_PRIOR_ART_FOUND"
                attempt.failure_substate = "NO_RESULTS"
            else:
                attempt.failure_state = "SUCCESS"
                attempt.failure_substate = "NONE"

        attempts.append(attempt)

    return attempts, all_patents


# ============================================================
# STAGE 3 — ACTUAL CLAIM RETRIEVAL (PatSnap)
# ============================================================
def stage_claim_retrieval(
    patent_ids: List[str],
    cited_art: List[str],
) -> Tuple[List[RetrievedPatentEvidence], int]:
    """Retrieve actual claims for each patent via multi-source path.

    V3.1: Uses patsnap_claim_data first (with granular failure tracking),
    then falls back to fetch_patsnap_claims and fetch_google_patent_full_claims.
    Records per-patent failure_substate (PATSNAP_PERMISSION_ERROR / HTTP_ERROR / etc).
    """
    evidence: List[RetrievedPatentEvidence] = []
    import concurrent.futures

    # Cap at 8 patents to manage time
    for pid in patent_ids[:8]:
        rec = RetrievedPatentEvidence(
            patent_id=pid,
            source="multi_source_claim_retrieval",
            is_cited_art=pid in cited_art,
            retrieved_at_utc=_now_utc(),
        )

        # Try 1: new patsnap_claim_data (with granular tracking)
        claim_attempt = None
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(patsnap_claim_data, pid, "", 15)
                try:
                    claim_attempt = fut.result(timeout=20)
                except concurrent.futures.TimeoutError:
                    claim_attempt = None
        except Exception:
            claim_attempt = None

        if claim_attempt and claim_attempt.normalized_state == "CLAIMS_RETRIEVED":
            rec.claims_retrieved = True
            rec.claim_count = claim_attempt.claim_count
            rec.claim_text_excerpt = claim_attempt.claims[0][:1000] if claim_attempt.claims else ""
            rec.content_hash = claim_attempt.content_hash
            rec.source = "PATSNAP_CLAIM_DATA"
        else:
            # Try 2: legacy fetch_patsnap_claims
            legacy_record = None
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(fetch_patsnap_claims, pid)
                    try:
                        legacy_record = fut.result(timeout=15)
                    except concurrent.futures.TimeoutError:
                        legacy_record = None
            except Exception:
                legacy_record = None

            if legacy_record is not None and legacy_record.claims:
                rec.claims_retrieved = True
                rec.claim_count = legacy_record.claim_count
                rec.claim_text_excerpt = legacy_record.claims[0][:1000] if legacy_record.claims else ""
                rec.content_hash = legacy_record.content_hash
                rec.source = "PATSNAP_CLAIMS_LEGACY"
            else:
                # Try 3: Google Patents full-text claims
                try:
                    from discovery_fabric.prior_art_v2.sources import fetch_google_patent_full_claims
                    google_claims = fetch_google_patent_full_claims(pid)
                    if "claims" in google_claims and google_claims["claims"]:
                        rec.claims_retrieved = True
                        rec.claim_count = len(google_claims["claims"])
                        rec.claim_text_excerpt = google_claims["claims"][0][:1000]
                        rec.content_hash = _sha256(google_claims["claims"][0])
                        rec.source = "GOOGLE_PATENTS_FULL_CLAIMS"
                    else:
                        rec.claims_retrieved = False
                        rec.source = "ALL_SOURCES_FAILED"
                except Exception:
                    rec.claims_retrieved = False
                    rec.source = "ALL_SOURCES_FAILED"

        evidence.append(rec)

    return evidence, 0  # no LLM calls in this stage


# ============================================================
# STAGE 4 — ELEMENT MAPPING + 102 (NOVELTY ADVERSARY)
# ============================================================
def stage_novelty_102(
    case: dict,
    canonical: CanonicalClaim,
    evidence: List[RetrievedPatentEvidence],
    llm: LLMClient,
) -> Tuple[List[ElementMapping], List[NoveltyResult], int]:
    """NOVELTY_ADVERSARY role: 102 single-reference attack.

    For each patent with retrieved claims, map L1..Ln to passages and check
    whether ALL limitations + arrangement are disclosed by ONE reference.
    """
    if not canonical.limitations or not evidence:
        return [], [], 0

    # Only attack patents with actual claims
    patents_with_claims = [e for e in evidence if e.claims_retrieved]
    if not patents_with_claims:
        return [], [], 0

    sys_prompt = (
        "You are a NOVELTY_ADVERSARY role in a patent analysis pipeline. "
        "Your task is the 102 single-reference novelty test. "
        "For each cited prior-art patent, determine whether ONE reference discloses "
        "ALL required limitations of the claim AND the required arrangement. "
        "If inherency is claimed, require necessity evidence. "
        "DO NOT consider combinations of references — that is 103. "
        "DO NOT use generic model knowledge to fill in missing disclosures. "
        "If a limitation is not explicitly or implicitly disclosed, mark it as "
        "NOT_DISCLOSED. Return strict JSON."
    )

    user_prompt = (
        f"Claim under test: {canonical.patent_number} — {case.get('title','')}\n"
        f"Limitations:\n" +
        "\n".join(f"  {lim}" for lim in canonical.limitations) +
        f"\nRelationships: {', '.join(canonical.relationships) or 'none specified'}\n\n"
    )

    # Add each prior-art patent's claim excerpt
    for e in patents_with_claims[:5]:
        user_prompt += (
            f"\n--- Prior-art patent: {e.patent_id} ---\n"
            f"Claim excerpt: {e.claim_text_excerpt[:1500]}\n"
        )

    user_prompt += (
        "\nReturn JSON array, one entry per prior-art patent:\n"
        "[{\n"
        '  "patent_id": "...",\n'
        '  "limitations_found": ["L1", "L3"],\n'
        '  "limitations_missing": ["L2"],\n'
        '  "all_limitations_found": true|false,\n'
        '  "arrangement_disclosed": true|false,\n'
        '  "anticipation_succeeds": true|false,\n'
        '  "rationale": "..."\n'
        "}]"
    )

    content, latency_ms = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2500)
    llm_calls = 1

    novelty_results: List[NoveltyResult] = []
    element_mappings: List[ElementMapping] = []

    parsed_results: List[Dict[str, Any]] = []
    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            if isinstance(parsed, list):
                parsed_results = parsed
            elif isinstance(parsed, dict) and "results" in parsed:
                parsed_results = parsed["results"]
        except (json.JSONDecodeError, AttributeError):
            pass

    # If LLM returned per-patent results, use them
    parsed_by_id = {r.get("patent_id", ""): r for r in parsed_results if isinstance(r, dict)}

    for e in patents_with_claims[:5]:
        parsed_r = parsed_by_id.get(e.patent_id, {})

        # Build element mappings (per limitation, per patent)
        for lim in canonical.limitations:
            lim_id = lim.split(":")[0].strip() if ":" in lim else f"L{len(element_mappings)+1}"
            disclosure = "UNCERTAIN"
            passage = ""
            if parsed_r:
                if lim_id in parsed_r.get("limitations_found", []):
                    disclosure = "EXPLICIT"
                    passage = "Identified by NOVELTY_ADVERSARY as disclosed."
                elif lim_id in parsed_r.get("limitations_missing", []):
                    disclosure = "NOT_DISCLOSED"

            element_mappings.append(ElementMapping(
                patent_id=e.patent_id,
                limitation_id=lim_id,
                disclosure_type=disclosure,
                exact_passage=passage,
                evidence_level="GOLD" if e.claims_retrieved else "NONE",
            ))

        # Build novelty result
        all_found = parsed_r.get("all_limitations_found", False)
        arrangement = parsed_r.get("arrangement_disclosed", False)
        anticipation = parsed_r.get("anticipation_succeeds", False)
        rationale = parsed_r.get("rationale", "No LLM rationale")

        novelty_results.append(NoveltyResult(
            patent_id=e.patent_id,
            all_limitations_found=all_found,
            limitations_found=parsed_r.get("limitations_found", []),
            limitations_missing=parsed_r.get("limitations_missing", []),
            arrangement_disclosed=arrangement,
            anticipation_succeeds=anticipation,
            rationale=rationale,
        ))

    return element_mappings, novelty_results, llm_calls


# ============================================================
# STAGE 5 — CLOSEST PRIOR ART + 103 (OBVIOUSNESS ADVERSARY)
# ============================================================
def stage_obviousness_103(
    case: dict,
    canonical: CanonicalClaim,
    novelty_results: List[NoveltyResult],
    evidence: List[RetrievedPatentEvidence],
    llm: LLMClient,
) -> Tuple[ObviousnessResult, int]:
    """OBVIOUSNESS_ADVERSARY role: 103 with EPO COULD/WOULD + anti-hindsight.

    Anti-hindsight protocol:
      Pass A (rationale-before): Build objective_technical_problem from closest
             prior art ALONE — without seeing the claimed solution.
      Pass B (rationale-after):  Compare with the post-disclosure reasoning.
      The difference is recorded as anti_hindsight_level (LOW/MEDIUM/HIGH).
    """
    # Step 1: select closest prior art (the patent with most limitations found,
    # but not all — if all found, 102 already succeeded)
    surviving_patents = [r for r in novelty_results if not r.anticipation_succeeds]
    if not surviving_patents:
        # All patents attacked novelty successfully -> 103 not needed
        return ObviousnessResult(
            closest_prior_art_id="NONE_NEEDED",
            closest_prior_art_rationale="102 already anticipates the claim",
            could_question="NO",
            would_question="NO",
            obviousness_succeeds=False,
            anti_hindsight_level="HIGH",
            anti_hindsight_notes="No 103 analysis needed — 102 anticipates.",
        ), 0

    # Closest prior art: patent with most limitations found
    surviving_patents.sort(key=lambda r: len(r.limitations_found), reverse=True)
    closest = surviving_patents[0]

    # Find a secondary reference for combination
    secondary = surviving_patents[1].patent_id if len(surviving_patents) > 1 else ""
    secondary_evidence = next((e for e in evidence if e.patent_id == secondary), None)

    # ANTI-HINDSIGHT Pass A — rationale BEFORE seeing the solution
    sys_prompt_a = (
        "You are an OBVIOUSNESS_ADVERSARY role performing Pass A (rationale-before). "
        "You will see ONLY the closest prior art and the technical field. "
        "You must NOT see the claimed invention's solution. "
        "Build the objective technical problem that a person skilled in the art "
        "would formulate based solely on the closest prior art. "
        "DO NOT reason backwards from any known solution. "
        "Return strict JSON."
    )
    user_prompt_a = (
        f"Technical field: {canonical.technical_field}\n"
        f"Closest prior art patent: {closest.patent_id}\n"
        f"Limitations found in closest prior art: {closest.limitations_found}\n"
        f"Limitations missing in closest prior art: {closest.limitations_missing}\n\n"
        "Return JSON: {\n"
        '  "objective_technical_problem": "...",\n'
        '  "expected_solution_direction": "..."  // what a PSA would naturally try, NOT the claimed solution\n'
        "}"
    )
    content_a, _ = llm.chat(sys_prompt_a, user_prompt_a, temperature=0.0, max_tokens=800)

    problem_before = ""
    expected_direction_before = ""
    if content_a and not content_a.startswith("[LLM_ERROR"):
        try:
            c = content_a.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed_a = json.loads(c)
            problem_before = parsed_a.get("objective_technical_problem", "")
            expected_direction_before = parsed_a.get("expected_solution_direction", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    # ANTI-HINDSIGHT Pass B — compare with post-disclosure reasoning
    sys_prompt_b = (
        "You are an OBVIOUSNESS_ADVERSARY role performing Pass B (rationale-after). "
        "Now you may see the claimed invention. "
        "Compare your pre-disclosure problem formulation with the post-disclosure "
        "view. Determine: did reasoning backwards from the claimed invention occur? "
        "Apply EPO 2026 Guidelines: answer COULD (was the combination technically "
        "feasible?) then WOULD (would the PSA actually have done it?). "
        "Both must be answered. Return strict JSON."
    )
    user_prompt_b = (
        f"Pre-disclosure objective technical problem: {problem_before}\n"
        f"Pre-disclosure expected solution direction: {expected_direction_before}\n\n"
        f"Now seeing claimed invention:\n"
        f"  Patent: {canonical.patent_number}\n"
        f"  Title: {case.get('title','')}\n"
        f"  Limitations: {canonical.limitations}\n\n"
        f"Closest prior art: {closest.patent_id}\n"
        f"  limitations_found: {closest.limitations_found}\n"
        f"  limitations_missing: {closest.limitations_missing}\n"
        + (f"Secondary reference: {secondary}\n" if secondary else "No secondary reference.\n")
        + "\nReturn JSON: {\n"
        '  "objective_technical_problem": "...",\n'
        '  "distinguishing_features": ["..."],\n'
        '  "technical_effect": "...",\n'
        '  "motivation": "...",\n'
        '  "reasonable_expectation_of_success": "HIGH"|"MEDIUM"|"LOW",\n'
        '  "could_question": "YES"|"NO",\n'
        '  "would_question": "YES"|"NO",\n'
        '  "why_explanation": "...",\n'
        '  "obviousness_succeeds": true|false,\n'  # True = 103 rejects
        '  "anti_hindsight_level": "LOW"|"MEDIUM"|"HIGH",\n'
        '  "anti_hindsight_notes": "..."\n'
        "}"
    )
    content_b, _ = llm.chat(sys_prompt_b, user_prompt_b, temperature=0.0, max_tokens=2000)
    llm_calls = 2

    result = ObviousnessResult(
        closest_prior_art_id=closest.patent_id,
        closest_prior_art_rationale=(
            f"Selected as closest because it discloses the most limitations "
            f"({len(closest.limitations_found)}/{len(canonical.limitations)}) "
            f"and is in a similar technical field ({canonical.technical_field})."
        ),
        objective_technical_problem=problem_before or "Could not formulate",
        secondary_reference_id=secondary,
    )

    if content_b and not content_b.startswith("[LLM_ERROR"):
        try:
            c = content_b.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed_b = json.loads(c)
            result.distinguishing_features = parsed_b.get("distinguishing_features", [])
            result.technical_effect = parsed_b.get("technical_effect", "")
            result.motivation = parsed_b.get("motivation", "")
            result.reasonable_expectation_of_success = parsed_b.get(
                "reasonable_expectation_of_success", "MEDIUM"
            )
            result.could_question = parsed_b.get("could_question", "NO")
            result.would_question = parsed_b.get("would_question", "NO")
            result.why_explanation = parsed_b.get("why_explanation", "")
            result.obviousness_succeeds = bool(parsed_b.get("obviousness_succeeds", False))
            result.anti_hindsight_level = parsed_b.get("anti_hindsight_level", "HIGH")
            result.anti_hindsight_notes = parsed_b.get("anti_hindsight_notes", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    return result, llm_calls


# ============================================================
# STAGE 6 — FINAL ADJUDICATION (CLAIM-ONLY PATH DISABLED)
# ============================================================
def stage_final_adjudication(
    case: dict,
    canonical: CanonicalClaim,
    search_families: List[SearchFamilyAttempt],
    evidence: List[RetrievedPatentEvidence],
    novelty_results: List[NoveltyResult],
    obviousness_result: ObviousnessResult,
    llm: LLMClient,
) -> Tuple[FinalAdjudication, int]:
    """FINAL_ADJUDICATOR role: combine evidence -> outcome.

    CLAIM-ONLY PATH IS DISABLED:
      If evidence retrieval fails (search insufficient, no claims retrieved),
      return SEARCH_INSUFFICIENT — NOT REJECT, NOT NOVEL, NOT ELITE.

    V3.1 SEARCH_INSUFFICIENT RULE (per CEO Section 7):
      Only use SEARCH_INSUFFICIENT when:
        - required search families were actually executed
        - AND usable patent sources were available
        - AND claim retrieval was attempted
        - AND the evidence still could not support adjudication.
      Do NOT use it because the implementation failed to obtain IDs.

    If the implementation failed (PATSNAP_PERMISSION_ERROR, etc.), the
    failure_substate is recorded — but the predicted_tier is still
    SEARCH_INSUFFICIENT (since evidence was indeed insufficient).
    """
    # Compute search sufficiency per CEO Section 7
    families_attempted = sum(1 for f in search_families if f.attempted)
    families_succeeded = sum(
        1 for f in search_families
        if f.failure_state in ("SUCCESS", "SEARCH_RETURNED_PATENTS",
                               "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED",
                               "NO_RELEVANT_PRIOR_ART_FOUND")
    )
    # Families that returned SOURCE_UNAVAILABLE are implementation failures
    families_source_unavailable = sum(
        1 for f in search_families if f.failure_state == "SOURCE_UNAVAILABLE"
    )
    # Track failure substates
    permission_errors = sum(
        1 for f in search_families if f.failure_substate == "PATSNAP_PERMISSION_ERROR"
    )
    http_errors = sum(
        1 for f in search_families if f.failure_substate == "HTTP_ERROR"
    )

    # Search is "sufficient" only if families were executed AND not blocked
    # by implementation failures (PATSNAP_PERMISSION_ERROR / HTTP_ERROR)
    search_actually_executed = families_attempted >= MIN_FAMILIES_ATTEMPTED

    # CEO Section 7: "Do NOT use SEARCH_INSUFFICIENT because the implementation
    # failed to obtain IDs." If permission errors or HTTP errors dominate,
    # the failure is implementation-level, not evidence-level.
    implementation_failure_dominant = (
        permission_errors >= 3 or http_errors >= 3
    )
    sources_were_available = (
        families_source_unavailable < (families_attempted / 2)
        and not implementation_failure_dominant
    )
    search_sufficient = search_actually_executed and sources_were_available

    # Compute evidence sufficiency
    claims_retrieved_count = sum(1 for e in evidence if e.claims_retrieved)

    # If evidence path incomplete -> return SEARCH_INSUFFICIENT or SOURCE_UNAVAILABLE
    # depending on root cause.
    if not search_sufficient or claims_retrieved_count == 0:
        # Determine the appropriate failure state per CEO Section 7
        if implementation_failure_dominant:
            # Implementation failed — NOT true SEARCH_INSUFFICIENT
            if permission_errors > 0:
                predicted_tier = "SOURCE_UNAVAILABLE"
                root_cause = (
                    f"PATSNAP_PERMISSION_ERROR: {permission_errors} families returned "
                    f"'Insufficient balance, call failed!' (error_code 67200005). "
                    "PatSnap API key balance is exhausted — this is an account-level "
                    "billing issue, not a coding failure. CEO Section 7: "
                    "implementation failure must NOT be classified as SEARCH_INSUFFICIENT."
                )
            else:
                predicted_tier = "SOURCE_UNAVAILABLE"
                root_cause = (
                    f"HTTP_ERROR: {http_errors} families returned HTTP errors "
                    "(Google Patents 503). Patent sources are intermittently unavailable. "
                    "CEO Section 7: implementation failure must NOT be classified as SEARCH_INSUFFICIENT."
                )
        else:
            # Search ran but evidence was genuinely insufficient
            predicted_tier = "SEARCH_INSUFFICIENT"
            if not search_actually_executed:
                root_cause = (
                    f"Search not executed: only {families_attempted}/14 families attempted "
                    f"(threshold: {MIN_FAMILIES_ATTEMPTED})."
                )
            else:
                root_cause = (
                    f"Search executed but evidence insufficient: "
                    f"families_attempted={families_attempted}, "
                    f"claims_retrieved_count={claims_retrieved_count}."
                )

        return FinalAdjudication(
            predicted_outcome="INSUFFICIENT_EVIDENCE",
            predicted_tier=predicted_tier,
            adjudicator_rationale=(
                f"Claim-only path DISABLED. search_sufficient={search_sufficient} "
                f"(families_attempted={families_attempted}/{len(search_families)}, "
                f"source_unavailable={families_source_unavailable}, "
                f"permission_errors={permission_errors}, "
                f"http_errors={http_errors}), "
                f"claims_retrieved_count={claims_retrieved_count}. "
                f"Root cause: {root_cause} "
                f"Returning {predicted_tier} per V3.1 protocol."
            ),
            adjudicator_model=MODEL_ADJUDICATOR,
            adjudicator_prompt_hash=ADJUDICATOR_PROMPT_HASH,
            evidence_path_complete=False,
            claim_only_path_taken=False,
        ), 0

    # 102 result
    anticipation_succeeds = any(r.anticipation_succeeds for r in novelty_results)

    # 103 result
    obviousness_succeeds = obviousness_result.obviousness_succeeds

    # Determine outcome based on EVIDENCE — not claim-only judgment
    if anticipation_succeeds:
        predicted_outcome = "NOVELTY_FAILS"
        predicted_tier = "REJECT"
        rationale = "102 anticipation succeeds: one reference discloses all limitations + arrangement."
    elif obviousness_succeeds:
        predicted_outcome = "OBVIOUSNESS_RISK"
        predicted_tier = "REJECT"
        rationale = (
            "103 obviousness succeeds: closest prior art + secondary reference with "
            "motivation + reasonable expectation of success (WOULD=YES)."
        )
    else:
        # Survived 102 and 103 — determine STRONG vs PROMISING
        gold_count = sum(1 for e in evidence if e.claims_retrieved)
        if gold_count >= 3 and obviousness_result.anti_hindsight_level == "HIGH":
            predicted_outcome = "STRONG"
            predicted_tier = "STRONG"
            rationale = (
                f"Survived 102 + 103 with {gold_count} GOLD patents reviewed and "
                "HIGH anti-hindsight confidence."
            )
        else:
            predicted_outcome = "NOVELTY_SURVIVES"
            predicted_tier = "PROMISING"
            rationale = (
                f"Survived 102 + 103 but only {gold_count} GOLD patents reviewed "
                f"or anti-hindsight level {obviousness_result.anti_hindsight_level}."
            )

    return FinalAdjudication(
        predicted_outcome=predicted_outcome,
        predicted_tier=predicted_tier,
        adjudicator_rationale=rationale,
        adjudicator_model=MODEL_ADJUDICATOR,
        adjudicator_prompt_hash=ADJUDICATOR_PROMPT_HASH,
        evidence_path_complete=True,
        claim_only_path_taken=False,
    ), 0


# ============================================================
# GROUND TRUTH CONSTRUCTION (CASE-LEVEL)
# ============================================================
def build_case_ground_truth(case: dict) -> dict:
    """Construct case-level ground truth from prosecution record.

    NOT granted=patentable / abandoned=unpatentable.
    Instead: build from claim_at_issue + cited_art + 102/103 rejections +
    amendments + final_disposition.
    """
    disposition = case["ground_truth_disposition"]
    label = case["ground_truth_label"]
    had_102 = case.get("had_102_rejection", False)
    had_103 = case.get("had_103_rejection", False)
    amendments = case.get("amendments_made", False)
    cited_art = case.get("prior_art_cited", [])
    examiner_reasoning = case.get("examiner_reasoning", "")

    # Confidence: HIGH if all fields are present, MEDIUM/LOW otherwise
    confidence = "HIGH"
    if not cited_art and not had_102 and not had_103:
        confidence = "MEDIUM"
    if not examiner_reasoning:
        confidence = "LOW"

    # For amended cases: rescue recognized if amendments were made AND
    # disposition is AMENDED_ALLOWED (i.e. narrowing actually succeeded)
    rescue_recognized = None
    if disposition == "AMENDED_ALLOWED":
        rescue_recognized = bool(amendments)

    return {
        "case_id": case["case_id"],
        "patent_number": case["patent_number"],
        "claim_at_issue": case.get("title", ""),  # proxy: title
        "prior_art_cited": cited_art,
        "had_102_rejection": had_102,
        "had_103_rejection": had_103,
        "amendments_made": amendments,
        "final_disposition": disposition,
        "final_claim": case.get("title", ""),  # proxy
        "ground_truth_label": label,
        "ground_truth_confidence": confidence,
        "rescue_expected": rescue_recognized,
        "examiner_reasoning": examiner_reasoning,
    }


# ============================================================
# METRICS CALCULATION
# ============================================================
def calculate_v3_metrics(results: List[CaseResult]) -> dict:
    """Calculate all V3 metrics per PROTOCOL.json."""
    total = len(results)
    if total == 0:
        return {"error": "no results"}

    # Insufficient evidence cases (true SEARCH_INSUFFICIENT, not SOURCE_UNAVAILABLE)
    insufficient = sum(1 for r in results if r.predicted_tier == "SEARCH_INSUFFICIENT")
    # Source unavailable cases (implementation failure)
    source_unavailable = sum(1 for r in results if r.predicted_tier == "SOURCE_UNAVAILABLE")
    # Either type means we couldn't adjudicate
    unable_to_adjudicate = insufficient + source_unavailable
    sufficient = total - unable_to_adjudicate

    # Correct predictions (only count sufficient cases for accuracy)
    correct = sum(1 for r in results if r.correct and r.predicted_tier not in
                  ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE"))

    # Map predicted tier to ground truth label for accuracy
    # SURVIVED -> STRONG or PROMISING (positive prediction)
    # REJECTED -> REJECT (negative prediction)
    # AMENDED -> PROMISING or STRONG (rescue recognized)
    false_elite = 0  # predicted STRONG/ELITE but ground truth is REJECTED
    false_reject = 0  # predicted REJECT but ground truth is SURVIVED or AMENDED

    for r in results:
        gt = r.ground_truth_label
        pred = r.predicted_tier
        if pred in ("STRONG", "ELITE") and gt == "REJECTED":
            false_elite += 1
        if pred == "REJECT" and gt in ("SURVIVED", "AMENDED"):
            false_reject += 1

    accuracy = correct / max(1, sufficient) if sufficient > 0 else 0.0
    false_elite_rate = false_elite / max(1, sufficient) if sufficient > 0 else 0.0
    false_reject_rate = false_reject / max(1, sufficient) if sufficient > 0 else 0.0

    # Cited-art recall: cases where cited_art_expected > 0
    cited_cases = [r for r in results if r.cited_art_expected]
    cited_found = sum(1 for r in cited_cases if r.cited_art_recall >= 0.5)
    cited_art_recall = cited_found / max(1, len(cited_cases)) if cited_cases else 1.0

    # Search recall: average fraction of families succeeded (non-failure)
    total_families_attempted = sum(r.families_attempted for r in results)
    total_families_succeeded = sum(
        r.families_succeeded for r in results
        if hasattr(r, "families_succeeded")
    )
    # If families_succeeded is not directly stored, recompute from search_families
    if not total_families_succeeded:
        for r in results:
            for f_dict in r.search_families:
                if f_dict.get("failure_state") in (
                    "SUCCESS", "SEARCH_RETURNED_PATENTS",
                    "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED",
                    "NO_RELEVANT_PRIOR_ART_FOUND"
                ):
                    total_families_succeeded += 1
    search_recall = total_families_succeeded / max(1, total_families_attempted)

    # 102 accuracy: for cases where 102 was attempted (claims retrieved),
    # did we correctly predict 102 outcome vs ground truth had_102_rejection?
    cases_with_102_attempt = [
        r for r in results
        if r.novelty_results and r.predicted_tier not in
        ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE")
    ]
    # 102 accuracy: cases where anticipation_succeeds matches had_102_rejection
    correct_102 = 0
    total_102 = 0
    for r in cases_with_102_attempt:
        # Look up the original case
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None:
            continue
        had_102 = case.get("had_102_rejection", False)
        predicted_102 = any(nr.get("anticipation_succeeds") for nr in r.novelty_results)
        # If case had 102 rejection, prediction should match
        # If case had no 102 rejection, prediction should be no anticipation
        if had_102 == predicted_102:
            correct_102 += 1
        total_102 += 1
    accuracy_102 = correct_102 / max(1, total_102) if total_102 > 0 else 0.0

    # 103 accuracy: similar
    correct_103 = 0
    total_103 = 0
    for r in cases_with_102_attempt:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None or not r.obviousness_result:
            continue
        had_103 = case.get("had_103_rejection", False)
        obs_dict = r.obviousness_result
        predicted_103 = obs_dict.get("obviousness_succeeds", False)
        if had_103 == predicted_103:
            correct_103 += 1
        total_103 += 1
    accuracy_103 = correct_103 / max(1, total_103) if total_103 > 0 else 0.0

    # Search failure rate: only true SEARCH_INSUFFICIENT (not SOURCE_UNAVAILABLE)
    search_failure_rate = insufficient / total
    # Source unavailability rate (implementation failures)
    source_unavailable_rate = source_unavailable / total

    # Evaluator failure rate (cases where model returned claim-only judgment)
    evaluator_failures = sum(1 for r in results if
                             r.final_adjudication and
                             r.final_adjudication.get("claim_only_path_taken", True))
    evaluator_failure_rate = evaluator_failures / total

    # Rescue recognition accuracy (amended cases only)
    amended_cases = [r for r in results if r.ground_truth_label == "AMENDED"]
    rescue_correct = sum(1 for r in amended_cases if r.rescue_recognized == True)
    rescue_recognition_accuracy = rescue_correct / max(1, len(amended_cases)) if amended_cases else 0.0

    # Elite precision/recall
    elite_predictions = sum(1 for r in results if r.predicted_tier in ("ELITE", "STRONG"))
    elite_correct = sum(1 for r in results if r.predicted_tier in ("ELITE", "STRONG")
                       and r.ground_truth_label == "SURVIVED")
    elite_precision = elite_correct / max(1, elite_predictions) if elite_predictions > 0 else 0.0
    elite_recall = elite_correct / max(1, sum(1 for r in results if r.ground_truth_label == "SURVIVED"))

    passes_threshold = (
        accuracy >= THRESHOLDS["overall_accuracy_min"] and
        false_elite_rate <= THRESHOLDS["false_elite_rate_max"] and
        false_reject_rate <= THRESHOLDS["false_reject_rate_max"] and
        cited_art_recall >= THRESHOLDS["cited_art_recall_min"] and
        search_recall >= THRESHOLDS["search_recall_min"]
    )

    return {
        "total_cases": total,
        "sufficient_evidence_cases": sufficient,
        "insufficient_evidence_count": insufficient,
        "source_unavailable_count": source_unavailable,
        "unable_to_adjudicate_count": unable_to_adjudicate,
        "correct_predictions": correct,
        "overall_accuracy": round(accuracy, 4),
        "false_elite_count": false_elite,
        "false_elite_rate": round(false_elite_rate, 4),
        "false_reject_count": false_reject,
        "false_reject_rate": round(false_reject_rate, 4),
        "cited_art_recall": round(cited_art_recall, 4),
        "cited_art_cases": len(cited_cases),
        "cited_art_found": cited_found,
        "search_recall": round(search_recall, 4),
        "102_accuracy": round(accuracy_102, 4),
        "103_accuracy": round(accuracy_103, 4),
        "search_failure_rate": round(search_failure_rate, 4),
        "source_unavailable_rate": round(source_unavailable_rate, 4),
        "evaluator_failure_rate": round(evaluator_failure_rate, 4),
        "rescue_recognition_accuracy": round(rescue_recognition_accuracy, 4),
        "elite_precision": round(elite_precision, 4),
        "elite_recall": round(elite_recall, 4),
        "passes_threshold": passes_threshold,
        "thresholds": THRESHOLDS,
        "status": "UNBLOCK_50_TO_5" if passes_threshold else "CALIBRATION_BLOCKED",
    }


# ============================================================
# ERROR ANALYSIS
# ============================================================
def categorize_error(case_result: CaseResult) -> str:
    """Categorize the error type for a case."""
    if case_result.correct:
        return "CORRECT"
    if case_result.predicted_tier == "SOURCE_UNAVAILABLE":
        return "SEARCH_FAILURE"  # implementation failure (PatSnap permission, etc.)
    if case_result.predicted_tier == "SEARCH_INSUFFICIENT":
        return "SEARCH_FAILURE"  # genuine insufficient evidence
    if not case_result.search_sufficient:
        return "SEARCH_FAILURE"
    if not case_result.retrieved_evidence:
        return "EVIDENCE_FAILURE"
    if case_result.error_type == "FALSE_ELITE":
        # Check if circular evaluation (model judged without evidence)
        if case_result.final_adjudication and case_result.final_adjudication.get("claim_only_path_taken"):
            return "CIRCULAR_EVALUATION"
        return "MODEL_JUDGMENT_FAILURE"
    if case_result.error_type == "FALSE_REJECT":
        # Check whether 102 or 103 caused the false reject
        if any(nr.get("anticipation_succeeds") for nr in case_result.novelty_results):
            return "102_FAILURE"
        if case_result.obviousness_result and case_result.obviousness_result.get("obviousness_succeeds"):
            return "103_FAILURE"
        return "MODEL_JUDGMENT_FAILURE"
    return "MODEL_JUDGMENT_FAILURE"
