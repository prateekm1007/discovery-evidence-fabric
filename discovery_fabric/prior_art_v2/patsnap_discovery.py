"""
PatSnap Patent Discovery Adapter
=================================

Real patent discovery using PatSnap's nested-search-patent endpoint.

POST https://connect.patsnap.com/search/patent/nested-search-patent

Returns: patent count, patent number, patent ID.

This is distinct from query-search-count (which only returns counts).

STATE MACHINE:
  SEARCH_EXECUTED              — HTTP 200, API returned data
  SEARCH_RETURNED_NO_RESULTS   — API succeeded but 0 patents matched
  SEARCH_RETURNED_PATENTS      — API succeeded, >=1 patent returned
  CLAIMS_RETRIEVED             — claims successfully retrieved for a patent
  SEARCH_INSUFFICIENT          — search ran but evidence still insufficient
  SOURCE_UNAVAILABLE           — endpoint not reachable / API error

FAILURE SUB-STATES (recorded raw + normalized):
  HTTP_ERROR                   — non-200 HTTP response
  RATE_LIMITED                 — 429 / explicit rate-limit response
  AUTH_FAILURE                 — 401 / invalid token
  PATSNAP_PERMISSION_ERROR     — 403 / "Insufficient balance" (error_code 67200005)
  NO_RESULTS                   — API OK but 0 patents
  CLAIM_UNAVAILABLE            — patent found but claims not retrievable

FAMILY COLLAPSE MODES (PatSnap documented):
  DOCDB                        — EPO's simple patent family
  INPADOC                      — Extended family (EPO + INPADOC)
  EXTEND                       — PatSnap extended family
  PBD                          — Publication Date (default; not a family mode)

We use DOCDB as the default family collapse — never country prefixes.
"""
from __future__ import annotations
import os, sys, json, ssl, urllib.request, urllib.error, urllib.parse, hashlib, time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ----------------------- CONSTANTS -----------------------
PATSNAP_BASE = "https://connect.patsnap.com"
ENDPOINT_NESTED_SEARCH = "/search/patent/nested-search-patent"
ENDPOINT_CLAIM_DATA = "/basic-patent-data/claim-data"

# Documented family collapse modes
FAMILY_COLLAPSE_MODES = ["DOCDB", "INPADOC", "EXTEND", "PBD"]
DEFAULT_FAMILY_MODE = "DOCDB"  # EPO simple patent family

# State machine
SEARCH_STATES = [
    "SEARCH_EXECUTED",
    "SEARCH_RETURNED_NO_RESULTS",
    "SEARCH_RETURNED_PATENTS",
    "CLAIMS_RETRIEVED",
    "SEARCH_INSUFFICIENT",
    "SOURCE_UNAVAILABLE",
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
    "NONE",  # no failure
]

# PatSnap error_code -> normalized substate
PATSNAP_ERROR_CODE_MAP = {
    67200005: "PATSNAP_PERMISSION_ERROR",  # Insufficient balance
    67200203: "RATE_LIMITED",               # API need a true rate
    401: "AUTH_FAILURE",
    403: "PATSNAP_PERMISSION_ERROR",
    429: "RATE_LIMITED",
}


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class DiscoveredPatent:
    """One patent discovered via PatSnap nested-search."""
    patent_number: str  # e.g., "US11912894B2"
    patent_id: str     # PatSnap internal UUID
    source: str = "PATSNAP_NESTED_SEARCH"
    query: str = ""
    query_id: str = ""           # PatSnap search request ID (if returned)
    retrieval_timestamp: str = ""
    title: str = ""
    assignee: str = ""
    publication_date: str = ""


@dataclass
class SearchAttempt:
    """One search attempt against PatSnap nested-search-patent."""
    query: str
    family_collapse: str = DEFAULT_FAMILY_MODE
    attempted: bool = False
    http_status: int = 0
    api_status: bool = False        # PatSnap's `status` field (true/false)
    api_error_code: int = 0
    api_error_msg: str = ""
    normalized_state: str = "SOURCE_UNAVAILABLE"  # SEARCH_STATES
    failure_substate: str = "NONE"                # FAILURE_SUBSTATES
    result_count: int = 0          # patents returned
    api_total_count: int = 0       # PatSnap's reported total
    patent_ids: List[str] = field(default_factory=list)
    patents: List[DiscoveredPatent] = field(default_factory=list)
    raw_response_excerpt: str = ""
    retrieval_timestamp: str = ""
    latency_ms: int = 0


@dataclass
class ClaimRetrievalAttempt:
    """One claim retrieval attempt via PatSnap claim-data."""
    patent_number: str
    patent_id: str = ""
    attempted: bool = False
    http_status: int = 0
    api_status: bool = False
    api_error_code: int = 0
    api_error_msg: str = ""
    normalized_state: str = "SOURCE_UNAVAILABLE"
    failure_substate: str = "NONE"
    claims: List[str] = field(default_factory=list)
    claim_count: int = 0
    independent_claim_count: int = 0
    content_hash: str = ""
    retrieval_timestamp: str = ""
    latency_ms: int = 0


# ----------------------- API CLIENT -----------------------
def _load_api_key() -> str:
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    if not keys_file.exists():
        return ""
    for line in keys_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("PATSNAP_EUREKA_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def _make_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _normalize_failure(http_status: int, api_error_code: int, api_error_msg: str) -> str:
    """Map raw HTTP+API error to a FAILURE_SUBSTATES value."""
    if api_error_code in PATSNAP_ERROR_CODE_MAP:
        return PATSNAP_ERROR_CODE_MAP[api_error_code]
    if http_status in PATSNAP_ERROR_CODE_MAP:
        return PATSNAP_ERROR_CODE_MAP[http_status]
    if http_status == 429:
        return "RATE_LIMITED"
    if http_status == 401:
        return "AUTH_FAILURE"
    if http_status == 403:
        return "PATSNAP_PERMISSION_ERROR"
    if http_status >= 500:
        return "HTTP_ERROR"
    if http_status >= 400:
        return "HTTP_ERROR"
    return "EXCEPTION"


def patsnap_nested_search(
    query: str,
    limit: int = 10,
    family_collapse: str = DEFAULT_FAMILY_MODE,
    timeout_s: int = 20,
) -> SearchAttempt:
    """
    Discover patents via PatSnap nested-search-patent endpoint.

    POST /search/patent/nested-search-patent
    Returns SearchAttempt with per-attempt state + failure_substate.
    """
    api_key = _load_api_key()
    attempt = SearchAttempt(
        query=query[:500],
        family_collapse=family_collapse,
        attempted=True,
        retrieval_timestamp=_now_utc(),
    )

    if not api_key:
        attempt.failure_substate = "AUTH_FAILURE"
        attempt.api_error_msg = "No PATSNAP_EUREKA_API_KEY in .env.keys"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    # Build query_text with TACD: prefix (Title, Abstract, Claims, Description)
    # Use the family_collapse parameter as collapse_by
    query_text = f"TACD: {query[:2900]}"
    payload = json.dumps({
        "query_text": query_text,
        "collapse_by": family_collapse,  # DOCDB / INPADOC / EXTEND / PBD
        "collapse_type": "ALL",
        "collapse_order": "LATEST",
        "limit": limit,
        "page": 1,
    }).encode("utf-8")

    url = PATSNAP_BASE + ENDPOINT_NESTED_SEARCH
    ctx = _make_ssl_context()

    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=timeout_s, context=ctx)
        body = resp.read()
        attempt.http_status = resp.status
        attempt.latency_ms = int((time.time() - t0) * 1000)
        attempt.raw_response_excerpt = body.decode("utf-8", errors="ignore")[:1000]

        data = json.loads(body)
        attempt.api_status = bool(data.get("status", False))
        attempt.api_error_code = int(data.get("error_code", 0))
        attempt.api_error_msg = data.get("error_msg", "")

        if not attempt.api_status:
            # API returned an error
            attempt.failure_substate = _normalize_failure(
                attempt.http_status, attempt.api_error_code, attempt.api_error_msg
            )
            attempt.normalized_state = "SOURCE_UNAVAILABLE"
            return attempt

        # API succeeded — extract patents from data
        data_section = data.get("data", {})
        if isinstance(data_section, dict):
            attempt.api_total_count = int(data_section.get("total_search_result_count", 0) or 0)
            patents_list = data_section.get("patents", []) or data_section.get("list", []) or []
        elif isinstance(data_section, list):
            patents_list = data_section
        else:
            patents_list = []

        for p in patents_list[:limit]:
            if not isinstance(p, dict):
                continue
            patent = DiscoveredPatent(
                patent_number=p.get("pn", "") or p.get("patent_number", "") or "",
                patent_id=p.get("patent_id", "") or p.get("id", "") or "",
                source="PATSNAP_NESTED_SEARCH",
                query=query[:200],
                query_id=str(data_section.get("query_id", "")) if isinstance(data_section, dict) else "",
                retrieval_timestamp=_now_utc(),
                title=p.get("title", "")[:300],
                assignee=p.get("assignee", "") or "",
                publication_date=p.get("publication_date", "") or p.get("pd", "") or "",
            )
            if patent.patent_number:
                attempt.patents.append(patent)
                attempt.patent_ids.append(patent.patent_number)

        attempt.result_count = len(attempt.patents)
        if attempt.result_count == 0:
            attempt.normalized_state = "SEARCH_RETURNED_NO_RESULTS"
            attempt.failure_substate = "NO_RESULTS"
        else:
            attempt.normalized_state = "SEARCH_RETURNED_PATENTS"
            attempt.failure_substate = "NONE"

    except urllib.error.HTTPError as e:
        attempt.http_status = e.code
        attempt.latency_ms = int((time.time() - t0) * 1000)
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")[:500]
        except Exception:
            pass
        attempt.api_error_msg = body
        attempt.failure_substate = _normalize_failure(e.code, 0, body)
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
    except urllib.error.URLError as e:
        attempt.latency_ms = int((time.time() - t0) * 1000)
        attempt.api_error_msg = str(e)[:300]
        attempt.failure_substate = "HTTP_ERROR"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
    except Exception as e:
        attempt.latency_ms = int((time.time() - t0) * 1000)
        attempt.api_error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        attempt.failure_substate = "EXCEPTION"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"

    return attempt


def patsnap_claim_data(
    patent_number: str = "",
    patent_id: str = "",
    timeout_s: int = 20,
) -> ClaimRetrievalAttempt:
    """
    Retrieve claims via PatSnap basic-patent-data/claim-data.

    GET /basic-patent-data/claim-data?patent_number=X  OR  ?patent_id=X
    Returns ClaimRetrievalAttempt with per-attempt state.
    """
    api_key = _load_api_key()
    attempt = ClaimRetrievalAttempt(
        patent_number=patent_number,
        patent_id=patent_id,
        attempted=True,
        retrieval_timestamp=_now_utc(),
    )

    if not api_key:
        attempt.failure_substate = "AUTH_FAILURE"
        attempt.api_error_msg = "No PATSNAP_EUREKA_API_KEY"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    if not patent_number and not patent_id:
        attempt.failure_substate = "EXCEPTION"
        attempt.api_error_msg = "Neither patent_number nor patent_id provided"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    # Build URL
    if patent_number:
        url = f"{PATSNAP_BASE}{ENDPOINT_CLAIM_DATA}?patent_number={urllib.parse.quote(patent_number)}"
    else:
        url = f"{PATSNAP_BASE}{ENDPOINT_CLAIM_DATA}?patent_id={urllib.parse.quote(patent_id)}"

    ctx = _make_ssl_context()
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=timeout_s, context=ctx)
        body = resp.read()
        attempt.http_status = resp.status
        attempt.latency_ms = int((time.time() - t0) * 1000)

        data = json.loads(body)
        attempt.api_status = bool(data.get("status", False))
        attempt.api_error_code = int(data.get("error_code", 0))
        attempt.api_error_msg = data.get("error_msg", "")

        if not attempt.api_status:
            attempt.failure_substate = _normalize_failure(
                attempt.http_status, attempt.api_error_code, attempt.api_error_msg
            )
            attempt.normalized_state = "SOURCE_UNAVAILABLE"
            return attempt

        records = data.get("data", [])
        if not records or not isinstance(records, list):
            attempt.failure_substate = "CLAIM_UNAVAILABLE"
            attempt.normalized_state = "SOURCE_UNAVAILABLE"
            return attempt

        record = records[0]
        claims_data = record.get("claims", [])
        if not claims_data:
            attempt.failure_substate = "CLAIM_UNAVAILABLE"
            attempt.normalized_state = "SOURCE_UNAVAILABLE"
            return attempt

        claim_entry = claims_data[0]
        raw_html = claim_entry.get("claim_text", "")

        # Parse claims from HTML — reuse logic from patsnap_claims
        import re
        def _strip_html(text):
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        def _parse_claims(html):
            claims = []
            pattern = r'<div class="(?:indep|dep)-clm" num="(\d+)"[^>]*>(.*?)</div>'
            matches = re.findall(pattern, html, re.DOTALL)
            current_num = None
            current_parts = []
            for num, content in matches:
                if num != current_num:
                    if current_num is not None and current_parts:
                        text = " ".join(_strip_html(p) for p in current_parts)
                        claims.append(text[:3000])
                    current_num = num
                    current_parts = [content]
                else:
                    current_parts.append(content)
            if current_num is not None and current_parts:
                text = " ".join(_strip_html(p) for p in current_parts)
                claims.append(text[:3000])
            if not claims:
                text = _strip_html(html)
                parts = re.split(r'(?=\b\d+\.\s+[A-Z])', text)
                for part in parts:
                    part = part.strip()
                    if re.match(r'^\d+\.\s+', part) and len(part) > 10:
                        claims.append(part[:3000])
            return claims

        claims = _parse_claims(raw_html)
        attempt.claims = claims
        attempt.claim_count = record.get("claim_count", len(claims))
        attempt.independent_claim_count = claim_entry.get("claim_independent_count", 0)
        attempt.content_hash = _sha256(raw_html)
        attempt.normalized_state = "CLAIMS_RETRIEVED"
        attempt.failure_substate = "NONE"

    except urllib.error.HTTPError as e:
        attempt.http_status = e.code
        attempt.latency_ms = int((time.time() - t0) * 1000)
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")[:500]
        except Exception:
            pass
        attempt.api_error_msg = body
        attempt.failure_substate = _normalize_failure(e.code, 0, body)
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
    except Exception as e:
        attempt.latency_ms = int((time.time() - t0) * 1000)
        attempt.api_error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        attempt.failure_substate = "EXCEPTION"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"

    return attempt


# ----------------------- MULTI-SOURCE DISCOVERY FALLBACK -----------------------
def discover_patents_multi_source(
    query: str,
    limit: int = 10,
    family_collapse: str = DEFAULT_FAMILY_MODE,
) -> Dict[str, Any]:
    """
    Try PatSnap nested-search first; if it fails, fall back to Google Patents.

    Returns a unified dict with:
      - attempts: list of SearchAttempt (one per source tried)
      - patents: list of DiscoveredPatent (unified)
      - primary_source: which source supplied the patents
      - all_sources_failed: bool
    """
    attempts = []
    patents = []
    primary_source = ""

    # 1. PatSnap nested-search
    ps_attempt = patsnap_nested_search(
        query=query, limit=limit, family_collapse=family_collapse
    )
    attempts.append({"source": "PATSNAP_NESTED_SEARCH", "attempt": asdict(ps_attempt)})
    if ps_attempt.normalized_state == "SEARCH_RETURNED_PATENTS":
        patents.extend(ps_attempt.patents)
        primary_source = "PATSNAP_NESTED_SEARCH"

    # 2. Google Patents fallback (if PatSnap failed or returned nothing)
    if not patents:
        try:
            from discovery_fabric.prior_art_v2.sources import search_google_patents
            gp_result = search_google_patents(query, num_results=limit)
            gp_attempt_dict = {
                "source": "GOOGLE_PATENTS",
                "attempted": True,
                "http_status": 200 if gp_result.success else 503,
                "api_status": gp_result.success,
                "api_error_msg": gp_result.error or "",
                "normalized_state": "SEARCH_RETURNED_PATENTS" if gp_result.success and gp_result.hits
                                   else ("SEARCH_RETURNED_NO_RESULTS" if gp_result.success else "SOURCE_UNAVAILABLE"),
                "failure_substate": "NONE" if gp_result.success else "HTTP_ERROR",
                "patent_ids": [h.patent_id for h in gp_result.hits if h.patent_id],
            }
            attempts.append(gp_attempt_dict)
            if gp_result.success and gp_result.hits:
                for h in gp_result.hits:
                    if h.patent_id:
                        patents.append(DiscoveredPatent(
                            patent_number=h.patent_id,
                            patent_id="",  # Google Patents doesn't expose PatSnap ID
                            source="GOOGLE_PATENTS",
                            query=query[:200],
                            retrieval_timestamp=_now_utc(),
                            title=h.title,
                            assignee=h.assignee_or_authors[0] if h.assignee_or_authors else "",
                            publication_date=h.publication_date or "",
                        ))
                primary_source = "GOOGLE_PATENTS"
        except Exception as e:
            attempts.append({
                "source": "GOOGLE_PATENTS",
                "attempted": True,
                "api_status": False,
                "api_error_msg": f"{type(e).__name__}: {str(e)[:200]}",
                "normalized_state": "SOURCE_UNAVAILABLE",
                "failure_substate": "EXCEPTION",
                "patent_ids": [],
            })

    return {
        "query": query[:500],
        "family_collapse": family_collapse,
        "attempts": attempts,
        "patents": [asdict(p) for p in patents],
        "primary_source": primary_source,
        "all_sources_failed": len(patents) == 0,
    }


# ----------------------- KNOWN-CITED-PATENT TEST -----------------------
def verify_cited_patent_retrievable(cited_patent_number: str) -> Dict[str, Any]:
    """
    Direct test: can we retrieve a known examiner-cited patent end-to-end?

    Steps:
      1. Search by patent number (via patent_number as query)
      2. Retrieve claims via claim-data

    Returns EXPECTED_CITED_PATENT_RETRIEVED = TRUE/FALSE with full trace.
    """
    # Step 1: try direct claim retrieval (we already know the patent number)
    claim_attempt = patsnap_claim_data(patent_number=cited_patent_number)

    result = {
        "cited_patent_number": cited_patent_number,
        "claim_retrieval": asdict(claim_attempt),
        "expected_cited_patent_retrieved": claim_attempt.normalized_state == "CLAIMS_RETRIEVED",
        "trace": [],
    }
    result["trace"].append({
        "step": "CLAIM_DATA_DIRECT",
        "source": "PATSNAP_CLAIM_DATA",
        "patent_number": cited_patent_number,
        "state": claim_attempt.normalized_state,
        "failure_substate": claim_attempt.failure_substate,
        "http_status": claim_attempt.http_status,
        "api_error_code": claim_attempt.api_error_code,
        "api_error_msg": claim_attempt.api_error_msg,
        "claims_count": claim_attempt.claim_count,
        "content_hash_prefix": claim_attempt.content_hash[:16],
    })

    # Step 2: if direct retrieval failed, try discovery first (find patent_id, then claim-data)
    if not result["expected_cited_patent_retrieved"]:
        # Try Google Patents fallback for claim retrieval
        try:
            from discovery_fabric.prior_art_v2.sources import fetch_google_patent_full_claims
            google_claims = fetch_google_patent_full_claims(cited_patent_number)
            if "claims" in google_claims and google_claims["claims"]:
                result["trace"].append({
                    "step": "GOOGLE_PATENTS_FULL_CLAIMS",
                    "source": "GOOGLE_PATENTS",
                    "patent_number": cited_patent_number,
                    "state": "CLAIMS_RETRIEVED",
                    "failure_substate": "NONE",
                    "http_status": 200,
                    "claims_count": len(google_claims["claims"]),
                })
                result["expected_cited_patent_retrieved"] = True
                # Update claim_attempt with Google data
                claim_attempt.claims = google_claims["claims"]
                claim_attempt.claim_count = len(google_claims["claims"])
                claim_attempt.normalized_state = "CLAIMS_RETRIEVED"
                claim_attempt.failure_substate = "NONE"
                claim_attempt.source = "GOOGLE_PATENTS"
                result["claim_retrieval"] = asdict(claim_attempt)
            else:
                result["trace"].append({
                    "step": "GOOGLE_PATENTS_FULL_CLAIMS",
                    "source": "GOOGLE_PATENTS",
                    "patent_number": cited_patent_number,
                    "state": "SOURCE_UNAVAILABLE",
                    "failure_substate": "HTTP_ERROR",
                    "http_status": 503,
                    "api_error_msg": google_claims.get("error", "unknown"),
                })
        except Exception as e:
            result["trace"].append({
                "step": "GOOGLE_PATENTS_FULL_CLAIMS",
                "source": "GOOGLE_PATENTS",
                "state": "SOURCE_UNAVAILABLE",
                "failure_substate": "EXCEPTION",
                "api_error_msg": str(e)[:200],
            })

    return result
