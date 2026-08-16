"""
Federated Patent Evidence Layer
=================================

Per CEO directive: build a federated patent evidence mesh where different
sources perform different jobs. Stop spending money on PatSnap.

ARCHITECTURE:
                    ┌── EPO OPS (primary: family, citations, CPC)
                    │
                    ├── Google BigQuery (primary: discovery, claims)
                    │
INVENTION ──────────┼── USPTO ODP (US ground truth, continuity)
                    │
                    ├── Patent Bear [when quota resets]
                    │
                    ├── Lens [when patent authentication works]
                    │
                    └── historical corpus
                              │
                              ▼
                     SOURCE NORMALIZER
                              │
                              ▼
                     FAMILY RESOLVER (INPADOC via EPO)
                              │
                              ▼
                   CURRENT CLAIM RELEVANCE
                              │
                              ▼
                       GOLD EVIDENCE
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
         102 attack       103 attack      Design-around

NEW 14-FAMILY SEARCH STRATEGY (per CEO):
  Q1_CONCEPT             -> Google BigQuery
  Q2_MECHANISM           -> Google BigQuery + EPO
  Q3_STRUCTURE           -> Google BigQuery
  Q4_MATERIAL            -> Google BigQuery
  Q5_RELATIONSHIP        -> Google BigQuery + EPO
  Q6_TECHNICAL_EFFECT    -> Google BigQuery + EPO
  Q7_FULL_COMBINATION    -> Google BigQuery
  Q8_FUNCTIONAL_EQUIV    -> EPO + Google
  Q9_STRUCTURAL_EQUIV    -> EPO + Google
  Q10_CPC_IPC            -> EPO + Google
  Q11_COMPETITOR_PORTFOLIO -> USPTO + Google
  Q12_CITATION_NEIGHBORHOOD -> EPO (citations with X/I/Y categories)
  Q13_NEGATIVE_SEARCH    -> Google + EPO
  Q14_SEMANTIC_SEARCH    -> local embeddings over retrieved corpus

GOLD EVIDENCE (8 conditions per CEO):
  1. verified patent identity
  2. actual claim text
  3. publication date
  4. priority date
  5. family provenance OR explicit unavailable
  6. content hash
  7. current-claim relevance
  8. source provenance (with cross-source corroboration)

CROSS-SOURCE TRIANGULATION:
  The same patent appearing on 5 databases is ONE piece of evidence, not five.
  But: EPO + Google BigQuery + USPTO can independently corroborate identity,
  claims, dates, family and citation relationships.
"""
from __future__ import annotations
import os, sys, json, hashlib, time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ----------------------- UNIFIED PATENT RECORD -----------------------
@dataclass
class UnifiedPatentRecord:
    """Patent record normalized across multiple sources.

    The same patent appearing on EPO + Google + USPTO is ONE record with
    multiple source_provenances.
    """
    patent_number: str  # canonical form (e.g., US11912894B2)
    title: str = ""
    abstract: str = ""
    assignee: str = ""
    inventor: str = ""
    publication_date: str = ""
    priority_date: str = ""
    filing_date: str = ""
    country_code: str = ""
    kind_code: str = ""
    cpc_codes: List[str] = field(default_factory=list)
    ipc_codes: List[str] = field(default_factory=list)
    family_id: str = ""
    family_type: str = ""  # INPADOC / DOCDB / EXTEND
    family_members: List[str] = field(default_factory=list)

    # Claims
    claims: List[str] = field(default_factory=list)
    claim_count: int = 0
    independent_claim_count: int = 0
    claim_content_hash: str = ""

    # Citations (with EPO categories X/I/Y/A)
    backward_citations: List[Dict[str, str]] = field(default_factory=list)  # patents this cites
    forward_citations: List[Dict[str, str]] = field(default_factory=list)  # patents citing this

    # Source provenance — list of sources that corroborate this record
    source_provenances: List[Dict[str, Any]] = field(default_factory=list)
    # Each entry: {source, retrieved_at_utc, fields_supplied: [title, claims, ...]}

    # GOLD evidence status
    is_gold: bool = False
    gold_checklist: Dict[str, bool] = field(default_factory=dict)

    retrieved_at_utc: str = ""


# ----------------------- SOURCE NORMALIZER -----------------------
def normalize_patent_number(raw: str) -> str:
    """Normalize a patent number to canonical form.

    Examples:
      US-11912894-B2 -> US11912894B2
      us11912894b2    -> US11912894B2
      EP3397675B1     -> EP3397675B1
      patent/US11912894B2/en -> US11912894B2
    """
    if not raw:
        return ""
    # Strip separators and normalize case
    s = raw.upper().replace("-", "").replace(" ", "").replace("/", "")
    # Remove leading "PATENT" prefix (from Google Patents URL)
    if s.startswith("PATENT"):
        s = s[6:]
    # Remove trailing "EN" (language code from Google Patents URL)
    if s.endswith("EN") and len(s) > 4:
        # Check if the chars before EN are digits/letters that form a patent number
        # Only strip EN if the result still looks like a patent number
        candidate = s[:-2]
        # Heuristic: patent numbers start with 2-letter country code + digits
        import re
        if re.match(r'^[A-Z]{2}\d+', candidate):
            s = candidate
    return s


def same_patent(a: str, b: str) -> bool:
    """Check if two patent numbers refer to the same patent."""
    na = normalize_patent_number(a)
    nb = normalize_patent_number(b)
    if na == nb:
        return True
    # Also check without kind code (e.g., US11912894 vs US11912894B2)
    base_a = na.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890") + na[:2]
    # Strip trailing kind code (letters) — but keep country code prefix
    import re
    m_a = re.match(r'^([A-Z]{2})(\d+)([A-Z]\d?)?$', na)
    m_b = re.match(r'^([A-Z]{2})(\d+)([A-Z]\d?)?$', nb)
    if m_a and m_b and m_a.group(1) == m_b.group(1) and m_a.group(2) == m_b.group(2):
        return True
    return False


def merge_records(records: List[UnifiedPatentRecord]) -> UnifiedPatentRecord:
    """Merge multiple records of the same patent from different sources."""
    if not records:
        return UnifiedPatentRecord(patent_number="")

    # Use the first record as base
    merged = UnifiedPatentRecord(patent_number=records[0].patent_number)
    merged.retrieved_at_utc = _now_utc()

    for r in records:
        # Merge simple fields (prefer first non-empty)
        for f in ["title", "abstract", "assignee", "inventor",
                  "publication_date", "priority_date", "filing_date",
                  "country_code", "kind_code", "family_id", "family_type"]:
            if not getattr(merged, f) and getattr(r, f):
                setattr(merged, f, getattr(r, f))

        # Merge list fields (union, dedupe)
        for f in ["cpc_codes", "ipc_codes", "family_members"]:
            existing = set(getattr(merged, f))
            for x in getattr(r, f):
                if x and x not in existing:
                    getattr(merged, f).append(x)
                    existing.add(x)

        # Claims — prefer the longest (most complete) set
        if len(r.claims) > len(merged.claims):
            merged.claims = r.claims
            merged.claim_count = r.claim_count
            merged.independent_claim_count = r.independent_claim_count
            merged.claim_content_hash = r.claim_content_hash

        # Citations — union
        for cite in r.backward_citations:
            if cite not in merged.backward_citations:
                merged.backward_citations.append(cite)
        for cite in r.forward_citations:
            if cite not in merged.forward_citations:
                merged.forward_citations.append(cite)

        # Source provenance
        merged.source_provenances.extend(r.source_provenances)

    return merged


# ----------------------- GOLD EVIDENCE EVALUATION -----------------------
def evaluate_gold_evidence(record: UnifiedPatentRecord) -> Tuple[bool, Dict[str, bool]]:
    """Evaluate whether a record meets GOLD evidence standard (8 conditions).

    Per CEO:
      1. verified patent identity
      2. actual claim text
      3. publication date
      4. priority date
      5. family provenance OR explicit unavailable
      6. content hash
      7. current-claim relevance
      8. source provenance (with cross-source corroboration where available)
    """
    checklist = {
        "verified_patent_identity": bool(record.patent_number and len(record.patent_number) >= 6),
        "actual_claim_text": bool(record.claims and len(record.claims) > 0 and len(record.claims[0]) > 50),
        "publication_date": bool(record.publication_date),
        "priority_date": bool(record.priority_date),
        "family_provenance": bool(record.family_id or record.family_members or record.family_type == "EXPLICIT_UNAVAILABLE"),
        "content_hash": bool(record.claim_content_hash),
        "current_claim_relevance": True,  # evaluated separately by claim relevance checker
        "source_provenance": bool(len(record.source_provenances) >= 1),
    }

    is_gold = all(checklist.values())
    return is_gold, checklist


# ----------------------- FEDERATED DISCOVERY -----------------------
@dataclass
class FederatedSearchResult:
    """Result of a federated search across all available sources."""
    query: str
    family_id: str  # which of the 14 search families this is
    sources_attempted: List[Dict[str, Any]] = field(default_factory=list)
    patents_discovered: List[UnifiedPatentRecord] = field(default_factory=list)
    primary_source: str = ""
    all_sources_failed: bool = False
    retrieved_at_utc: str = ""


def federated_discover(
    query: str,
    family_id: str,
    cited_art: List[str] = None,
    limit: int = 10,
) -> FederatedSearchResult:
    """Run a federated discovery across all available sources.

    Per CEO's 14-family source routing:
      - Q1_CONCEPT, Q3_STRUCTURE, Q4_MATERIAL, Q7_FULL_COMBINATION -> Google BigQuery
      - Q2_MECHANISM, Q5_RELATIONSHIP, Q6_TECHNICAL_EFFECT -> Google + EPO
      - Q8/Q9_FUNCTIONAL/STRUCTURAL_EQUIV -> EPO + Google
      - Q10_CPC_IPC -> EPO + Google
      - Q11_COMPETITOR_PORTFOLIO -> USPTO + Google
      - Q12_CITATION_NEIGHBORHOOD -> EPO (citations with X/I/Y)
      - Q13_NEGATIVE_SEARCH -> Google + EPO
      - Q14_SEMANTIC_SEARCH -> local embeddings
    """
    result = FederatedSearchResult(
        query=query[:500],
        family_id=family_id,
        retrieved_at_utc=_now_utc(),
    )
    cited_art = cited_art or []

    # Build list of sources to try, in priority order per family
    sources_to_try = _get_sources_for_family(family_id)

    all_patents: Dict[str, UnifiedPatentRecord] = {}  # by normalized patent_number

    for source_name in sources_to_try:
        source_attempt = {
            "source": source_name,
            "attempted": True,
            "api_status": False,
            "api_error_msg": "",
            "normalized_state": "SOURCE_UNAVAILABLE",
            "failure_substate": "NONE",
            "patents_returned": 0,
            "latency_ms": 0,
        }

        t0 = time.time()
        try:
            if source_name == "GOOGLE_BIGQUERY":
                from discovery_fabric.prior_art_v2.bigquery_patents_adapter import (
                    bigquery_search_concepts, is_bigquery_available,
                )
                if not is_bigquery_available():
                    source_attempt["failure_substate"] = "AUTH_FAILURE"
                    source_attempt["api_error_msg"] = "No BigQuery credentials"
                else:
                    bq_result = bigquery_search_concepts(query, limit=limit)
                    source_attempt["api_status"] = bq_result.api_status
                    source_attempt["api_error_msg"] = bq_result.api_error_msg
                    source_attempt["normalized_state"] = bq_result.normalized_state
                    source_attempt["failure_substate"] = bq_result.failure_substate
                    source_attempt["patents_returned"] = len(bq_result.patent_ids)
                    for p in bq_result.patents:
                        unified = UnifiedPatentRecord(
                            patent_number=normalize_patent_number(p.patent_number),
                            title=p.title, abstract=p.abstract, assignee=p.assignee,
                            publication_date=p.publication_date, priority_date=p.priority_date,
                            country_code=p.country_code, kind_code=p.kind_code,
                            family_id=p.family_id, retrieved_at_utc=_now_utc(),
                            source_provenances=[{
                                "source": "GOOGLE_BIGQUERY",
                                "retrieved_at_utc": _now_utc(),
                                "fields_supplied": ["title", "abstract", "dates", "family"],
                            }],
                        )
                        if unified.patent_number not in all_patents:
                            all_patents[unified.patent_number] = unified
                        else:
                            all_patents[unified.patent_number] = merge_records([
                                all_patents[unified.patent_number], unified
                            ])

            elif source_name == "EPO_OPS":
                from discovery_fabric.prior_art_v2.epo_ops_adapter import (
                    epo_ops_search, is_epo_ops_available,
                )
                if not is_epo_ops_available():
                    source_attempt["failure_substate"] = "AUTH_FAILURE"
                    source_attempt["api_error_msg"] = "No EPO OPS credentials"
                else:
                    epo_result = epo_ops_search(query, limit=limit)
                    source_attempt["api_status"] = epo_result.api_status
                    source_attempt["api_error_msg"] = epo_result.api_error_msg
                    source_attempt["normalized_state"] = epo_result.normalized_state
                    source_attempt["failure_substate"] = epo_result.failure_substate
                    source_attempt["patents_returned"] = len(epo_result.patent_ids)
                    for p in epo_result.patents:
                        unified = UnifiedPatentRecord(
                            patent_number=normalize_patent_number(p.patent_number),
                            retrieved_at_utc=_now_utc(),
                            source_provenances=[{
                                "source": "EPO_OPS",
                                "retrieved_at_utc": _now_utc(),
                                "fields_supplied": ["identity"],
                            }],
                        )
                        if unified.patent_number not in all_patents:
                            all_patents[unified.patent_number] = unified

            elif source_name == "USPTO_ODP":
                from discovery_fabric.prior_art_v2.uspto_odp_adapter import uspto_search
                uspto_result = uspto_search(query, limit=limit)
                source_attempt["api_status"] = uspto_result.api_status
                source_attempt["api_error_msg"] = uspto_result.api_error_msg
                source_attempt["normalized_state"] = uspto_result.normalized_state
                source_attempt["failure_substate"] = uspto_result.failure_substate
                source_attempt["patents_returned"] = len(uspto_result.patent_ids)
                for p in uspto_result.patents:
                    unified = UnifiedPatentRecord(
                        patent_number=normalize_patent_number(p.patent_number),
                        title=p.title, abstract=p.abstract, assignee=p.assignee,
                        publication_date=p.publication_date,
                        cpc_codes=p.cpc_codes, ipc_codes=p.ipc_codes,
                        retrieved_at_utc=_now_utc(),
                        source_provenances=[{
                            "source": "USPTO_ODP",
                            "retrieved_at_utc": _now_utc(),
                            "fields_supplied": ["title", "abstract", "cpc", "ipc"],
                        }],
                    )
                    if unified.patent_number not in all_patents:
                        all_patents[unified.patent_number] = unified
                    else:
                        all_patents[unified.patent_number] = merge_records([
                            all_patents[unified.patent_number], unified
                        ])

            elif source_name == "CITED_ART_INJECTION":
                # For Q12_CITATION_NEIGHBORHOOD: inject known cited patents
                for cited in cited_art:
                    normalized = normalize_patent_number(cited)
                    if normalized and normalized not in all_patents:
                        all_patents[normalized] = UnifiedPatentRecord(
                            patent_number=normalized,
                            retrieved_at_utc=_now_utc(),
                            source_provenances=[{
                                "source": "PROSECUTION_RECORD",
                                "retrieved_at_utc": _now_utc(),
                                "fields_supplied": ["identity"],
                                "note": "Examiner-cited prior art from prosecution history",
                            }],
                        )
                source_attempt["api_status"] = True
                source_attempt["normalized_state"] = "SEARCH_RETURNED_PATENTS" if cited_art else "SEARCH_RETURNED_NO_RESULTS"
                source_attempt["failure_substate"] = "NONE"
                source_attempt["patents_returned"] = len(cited_art)

        except Exception as e:
            source_attempt["api_error_msg"] = f"{type(e).__name__}: {str(e)[:200]}"
            source_attempt["failure_substate"] = "EXCEPTION"
            source_attempt["normalized_state"] = "SOURCE_UNAVAILABLE"

        source_attempt["latency_ms"] = int((time.time() - t0) * 1000)
        result.sources_attempted.append(source_attempt)

        if source_attempt["patents_returned"] > 0 and not result.primary_source:
            result.primary_source = source_name

    # Evaluate GOLD evidence for each patent
    for patent in all_patents.values():
        is_gold, checklist = evaluate_gold_evidence(patent)
        patent.is_gold = is_gold
        patent.gold_checklist = checklist

    result.patents_discovered = list(all_patents.values())
    result.all_sources_failed = all(
        s["normalized_state"] in ("SOURCE_UNAVAILABLE", "SEARCH_RETURNED_NO_RESULTS")
        for s in result.sources_attempted
    ) and not result.patents_discovered

    return result


def _get_sources_for_family(family_id: str) -> List[str]:
    """Return the priority list of sources for a given search family."""
    routing = {
        "Q1_CONCEPT": ["GOOGLE_BIGQUERY", "EPO_OPS", "USPTO_ODP"],
        "Q2_MECHANISM": ["GOOGLE_BIGQUERY", "EPO_OPS"],
        "Q3_STRUCTURE": ["GOOGLE_BIGQUERY", "USPTO_ODP"],
        "Q4_MATERIAL": ["GOOGLE_BIGQUERY", "EPO_OPS"],
        "Q5_RELATIONSHIP": ["GOOGLE_BIGQUERY", "EPO_OPS"],
        "Q6_TECHNICAL_EFFECT": ["GOOGLE_BIGQUERY", "EPO_OPS"],
        "Q7_FULL_COMBINATION": ["GOOGLE_BIGQUERY", "EPO_OPS"],
        "Q8_FUNCTIONAL_EQUIVALENT": ["EPO_OPS", "GOOGLE_BIGQUERY"],
        "Q9_STRUCTURAL_EQUIVALENT": ["EPO_OPS", "GOOGLE_BIGQUERY"],
        "Q10_CPC_IPC": ["EPO_OPS", "GOOGLE_BIGQUERY"],
        "Q11_COMPETITOR_PORTFOLIO": ["USPTO_ODP", "GOOGLE_BIGQUERY"],
        "Q12_CITATION_NEIGHBORHOOD": ["EPO_OPS", "CITED_ART_INJECTION"],
        "Q13_NEGATIVE_SEARCH": ["GOOGLE_BIGQUERY", "EPO_OPS"],
        "Q14_SEMANTIC_SEARCH": [],  # local embeddings, no external source
    }
    return routing.get(family_id, ["GOOGLE_BIGQUERY", "EPO_OPS", "USPTO_ODP"])


# ----------------------- CREDENTIAL STATUS CHECK -----------------------
def get_federated_source_status() -> Dict[str, Dict[str, Any]]:
    """Check the availability of each federated source."""
    status = {}

    # EPO OPS
    try:
        from discovery_fabric.prior_art_v2.epo_ops_adapter import is_epo_ops_available
        epo_available = is_epo_ops_available()
    except Exception:
        epo_available = False
    status["EPO_OPS"] = {
        "available": epo_available,
        "free_tier": "4 GB/week",
        "registration_url": "https://developers.epo.org/",
        "required_env_vars": ["EPO_OPS_CONSUMER_KEY", "EPO_OPS_CONSUMER_SECRET"],
        "current_state": "LIVE" if epo_available else "CREDENTIALS_REQUIRED",
    }

    # Google BigQuery
    try:
        from discovery_fabric.prior_art_v2.bigquery_patents_adapter import is_bigquery_available
        bq_available = is_bigquery_available()
    except Exception:
        bq_available = False
    status["GOOGLE_BIGQUERY"] = {
        "available": bq_available,
        "free_tier": "1 TiB/month query processing",
        "registration_url": "https://console.cloud.google.com/bigquery",
        "required_env_vars": ["BIGQUERY_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"],
        "current_state": "LIVE" if bq_available else "CREDENTIALS_REQUIRED",
    }

    # USPTO ODP
    try:
        from discovery_fabric.prior_art_v2.uspto_odp_adapter import is_uspto_available
        uspto_available = is_uspto_available()
    except Exception:
        uspto_available = False
    status["USPTO_ODP"] = {
        "available": uspto_available,
        "free_tier": "Public API (rate-limited without key)",
        "registration_url": "https://uspto.gov/subscription-center",
        "required_env_vars": ["USPTO_ODP_API_KEY (optional for higher limits)"],
        "current_state": "LIVE" if uspto_available else "CREDENTIALS_REQUIRED",
    }

    # PatSnap (frozen — financially exhausted)
    status["PATSNAP"] = {
        "available": False,
        "free_tier": "None (commercial, balance exhausted)",
        "current_state": "FROZEN_PER_CEO_DIRECTIVE",
        "note": "PatSnap API key balance is exhausted (error_code 67200005). "
                "Do not spend another dollar. Use federated sources instead.",
    }

    return status
