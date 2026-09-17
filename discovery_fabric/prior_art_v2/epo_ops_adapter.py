"""
EPO OPS (Open Patent Services) Adapter
=======================================

EPO OPS provides bibliographic data, worldwide legal-status data, full text,
and images through a REST/XML/JSON interface. Free access tier: 4 GB/week.

ENDPOINTS (per https://developers.epo.org/):
  - published-data/publication/{format}/{number}/bibliography
  - published-data/publication/{format}/{number}/claims
  - published-data/publication/{format}/{number}/description
  - published-data/publication/{format}/{number}/equivalents  (INPADOC family)
  - published-data/publication/{format}/{number}/citations
  - published-data/search  (full-text search)
  - legal-status/publication/{format}/{number}
  - family/publication/{format}/{number}  (INPADOC family)

AUTH:
  OAuth 2.0 client credentials grant.
  Register at https://developers.epo.org/ to get consumer_key + consumer_secret.
  Token endpoint: https://ops.epo.org/3.2/auth/accesstoken

CITATION CATEGORIES (EPO Register):
  X — particularly relevant alone (novelty)
  I — particularly relevant to inventive step
  Y — relevant in combination (obviousness)
  A — background/state of art

These categories are GOLD for our 102/103 attack graph.
"""
from __future__ import annotations
import os, sys, json, ssl, urllib.request, urllib.error, urllib.parse, hashlib, time, base64, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ----------------------- CONSTANTS -----------------------
OPS_BASE = "https://ops.epo.org/3.2/rest-services"
OPS_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"

# EPO citation categories — GOLD for 102/103 attack
CITATION_CATEGORIES = {
    "X": "NOVELTY_RELEVANT",       # particularly relevant alone (102)
    "I": "INVENTIVE_STEP_RELEVANT", # particularly relevant to inventive step (103)
    "Y": "COMBINATION_RELEVANT",    # relevant in combination (103)
    "A": "BACKGROUND_ART",          # background/state of art
    "P": "PARALLEL patents",        # non-written disclosure
    "T": "THEORY",                  # theory/principle
    "E": "EARLIER",                 # potentially earlier application
    "&": "EARLIER_PATENT",          # earlier patent (102(e))
}

# Family types
FAMILY_TYPES = ["INPADOC", "DOCDB", "EXTEND"]


# ----------------------- AUTH -----------------------
def _load_epo_credentials() -> Tuple[str, str]:
    """Load EPO OPS OAuth credentials from .env.keys or env vars."""
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("EPO_OPS_CONSUMER_KEY="):
                key = line.split("=", 1)[1].strip()
            if line.startswith("EPO_OPS_CONSUMER_SECRET="):
                secret = line.split("=", 1)[1].strip()
    # Try env vars too
    key = os.environ.get("EPO_OPS_CONSUMER_KEY", "")
    secret = os.environ.get("EPO_OPS_CONSUMER_SECRET", "")
    return key, secret


# Token cache (in-memory, valid for 20 minutes per EPO docs)
_token_cache = {"token": "", "expires_at": 0.0}


def _get_oauth_token() -> Optional[str]:
    """Get OAuth 2.0 access token using client credentials grant."""
    key, secret = _load_epo_credentials()
    if not key or not secret:
        return None

    # Check cache
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    # Build Basic auth header
    credentials = f"{key}:{secret}"
    b64 = base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = b"grant_type=client_credentials"
    try:
        req = urllib.request.Request(OPS_TOKEN_URL, data=payload, method="POST", headers={
            "Authorization": f"Basic {b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        })
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read())
        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 1200))
        if token:
            _token_cache["token"] = token
            _token_cache["expires_at"] = time.time() + expires_in
            return token
    except Exception:
        pass
    return None


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class EPOPatentRecord:
    """Patent record from EPO OPS."""
    patent_number: str         # e.g., "US11912894B2"
    epodoc_number: str         # EPO format
    title: str = ""
    abstract: str = ""
    applicant: str = ""
    inventor: str = ""
    publication_date: str = ""
    priority_date: str = ""
    filing_date: str = ""
    cpc_codes: List[str] = field(default_factory=list)
    ipc_codes: List[str] = field(default_factory=list)
    family_id: str = ""
    family_type: str = "INPADOC"
    source: str = "EPO_OPS"
    retrieved_at_utc: str = ""
    content_hash: str = ""


@dataclass
class EPOClaimRecord:
    """Claims retrieved from EPO OPS."""
    patent_number: str
    claims: List[str] = field(default_factory=list)
    claim_count: int = 0
    independent_claim_count: int = 0
    source: str = "EPO_OPS"
    retrieved_at_utc: str = ""
    content_hash: str = ""


@dataclass
class EPOCitationRecord:
    """Citation from EPO OPS with category (X/I/Y/A)."""
    citing_patent: str
    cited_patent: str
    category: str  # X / I / Y / A / etc.
    category_meaning: str  # NOVELTY_RELEVANT / INVENTIVE_STEP_RELEVANT / etc.
    source: str = "EPO_OPS"
    retrieved_at_utc: str = ""


@dataclass
class EPOFamilyRecord:
    """INPADOC family from EPO OPS."""
    root_patent: str
    family_id: str = ""
    family_type: str = "INPADOC"
    family_members: List[str] = field(default_factory=list)
    source: str = "EPO_OPS"
    retrieved_at_utc: str = ""


@dataclass
class EPOSearchAttempt:
    """One search attempt against EPO OPS."""
    query: str
    attempted: bool = False
    http_status: int = 0
    api_status: bool = False
    api_error_msg: str = ""
    normalized_state: str = "SOURCE_UNAVAILABLE"  # SEARCH_RETURNED_PATENTS / SOURCE_UNAVAILABLE / etc.
    failure_substate: str = "NONE"  # AUTH_FAILURE / NO_RESULTS / etc.
    patents: List[EPOPatentRecord] = field(default_factory=list)
    patent_ids: List[str] = field(default_factory=list)
    total_count: int = 0
    retrieved_at_utc: str = ""


# ----------------------- OPS API CALLS -----------------------
def _ops_request(path: str, params: Dict = None, accept: str = "application/json") -> Tuple[int, bytes, str]:
    """Make an authenticated request to EPO OPS."""
    token = _get_oauth_token()
    if not token:
        return 401, b"", "AUTH_FAILURE: no EPO_OPS_CONSUMER_KEY/SECRET in .env.keys"

    url = OPS_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
        })
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:500]
        return e.code, body.encode(), f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, b"", f"EXCEPTION: {type(e).__name__}: {str(e)[:200]}"


def epo_ops_search(query: str, range_start: int = 1, range_end: int = 10) -> EPOSearchAttempt:
    """Search EPO OPS for patents matching a query.

    Uses the published-data/search endpoint.
    Query syntax: https://developers.epo.org/ops-3-2-published-data-services
    """
    attempt = EPOSearchAttempt(
        query=query[:500],
        attempted=True,
        retrieved_at_utc=_now_utc(),
    )

    token = _get_oauth_token()
    if not token:
        attempt.failure_substate = "AUTH_FAILURE"
        attempt.api_error_msg = "No EPO_OPS credentials. Register at developers.epo.org"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    # Build the search query in EPO format
    # Default to searching title/abstract/claims
    epo_query = f"ti all \"{query}\" or ab all \"{query}\" or cl all \"{query}\""
    params = {
        "q": epo_query[:1900],
        "Range": f"{range_start}-{range_end}",
    }

    status, body, err = _ops_request("/published-data/search", params=params)
    attempt.http_status = status

    if status != 200:
        attempt.api_status = False
        attempt.api_error_msg = err
        if status == 401:
            attempt.failure_substate = "AUTH_FAILURE"
        elif status == 403:
            attempt.failure_substate = "AUTH_FAILURE"
        elif status == 429:
            attempt.failure_substate = "RATE_LIMITED"
        else:
            attempt.failure_substate = "HTTP_ERROR"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    attempt.api_status = True
    try:
        data = json.loads(body)
        # Parse the JSON response — EPO returns a nested structure
        results = data.get("ops:world-patent-data", {}).get("ops:bibliography-search", {})
        total = int(results.get("@total-result-count", 0))
        attempt.total_count = total

        publications = results.get("ops:search-result", {}).get("exchange-document", [])
        if not isinstance(publications, list):
            publications = [publications] if publications else []

        for pub in publications:
            doc = pub.get("exchange-document", pub)
            num = doc.get("@doc-number", "")
            country = doc.get("@country", "")
            kind = doc.get("@kind", "")
            full_num = f"{country}{num}{kind}" if num else ""
            if full_num:
                attempt.patent_ids.append(full_num)
                attempt.patents.append(EPOPatentRecord(
                    patent_number=full_num,
                    epodoc_number=f"{country}{num}{kind}",
                    retrieved_at_utc=_now_utc(),
                ))

        if attempt.patent_ids:
            attempt.normalized_state = "SEARCH_RETURNED_PATENTS"
            attempt.failure_substate = "NONE"
        else:
            attempt.normalized_state = "SEARCH_RETURNED_NO_RESULTS"
            attempt.failure_substate = "NO_RESULTS"
    except Exception as e:
        attempt.api_error_msg = f"JSON parse error: {str(e)[:200]}"
        attempt.failure_substate = "EXCEPTION"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"

    return attempt


def epo_ops_get_bibliography(patent_number: str) -> Optional[EPOPatentRecord]:
    """Retrieve bibliographic data for a patent from EPO OPS."""
    token = _get_oauth_token()
    if not token:
        return None

    # Normalize to epodoc format (country+number+kind)
    # US11912894B2 -> US/11912894/B2
    path = f"/published-data/publication/epodoc/{patent_number}/bibliography"
    status, body, err = _ops_request(path)
    if status != 200:
        return None

    try:
        data = json.loads(body)
        doc = data.get("ops:world-patent-data", {}).get("exchange-document", {})
        if not doc:
            return None

        # Extract fields
        country = doc.get("@country", "")
        num = doc.get("@doc-number", "")
        kind = doc.get("@kind", "")
        full_num = f"{country}{num}{kind}" if num else patent_number

        # Bibliographic data
        bib = doc.get("bibliographic-data", {})

        # Title
        title_arr = bib.get("invention-title", {})
        if isinstance(title_arr, dict):
            title = title_arr.get("$", "")
        else:
            title = str(title_arr)

        # Abstract
        abstract = ""
        abs_data = doc.get("abstract", {})
        if isinstance(abs_data, dict):
            abstract = abs_data.get("p", {}).get("$", "") if isinstance(abs_data.get("p"), dict) else str(abs_data)[:500]

        # Dates
        dates = bib.get("dates-of-publication", {}).get("date-of-publication", {})
        pub_date = dates.get("$", "") if isinstance(dates, dict) else ""

        # Priority
        prio = bib.get("priority-claims", {}).get("priority-claim", [])
        if isinstance(prio, dict):
            prio = [prio]
        priority_date = prio[0].get("priority-claim", {}).get("$", "") if prio else ""

        # CPC/IPC
        cpc = []
        ipc = []
        class_data = bib.get("patent-classifications", {})
        cpc_data = class_data.get("cpc-classification", [])
        if isinstance(cpc_data, dict):
            cpc_data = [cpc_data]
        for c in cpc_data:
            code = c.get("classification-cpc", {}).get("text", "")
            if code:
                cpc.append(code)

        ipc_data = class_data.get("ipc-classification", [])
        if isinstance(ipc_data, dict):
            ipc_data = [ipc_data]
        for i in ipc_data:
            code = i.get("classification-ipc", {}).get("text", "")
            if code:
                ipc.append(code)

        # Family ID
        family_id = doc.get("@family-id", "")

        record = EPOPatentRecord(
            patent_number=full_num,
            epodoc_number=f"{country}{num}{kind}",
            title=title,
            abstract=abstract,
            publication_date=pub_date,
            priority_date=priority_date,
            cpc_codes=cpc,
            ipc_codes=ipc,
            family_id=family_id,
            retrieved_at_utc=_now_utc(),
            content_hash=_sha256(json.dumps(doc, sort_keys=True)),
        )
        return record
    except Exception:
        return None


def epo_ops_get_claims(patent_number: str) -> Optional[EPOClaimRecord]:
    """Retrieve claims for a patent from EPO OPS."""
    token = _get_oauth_token()
    if not token:
        return None

    path = f"/published-data/publication/epodoc/{patent_number}/claims"
    status, body, err = _ops_request(path)
    if status != 200:
        return None

    try:
        data = json.loads(body)
        claims_node = data.get("ops:world-patent-data", {}).get("ftxt:fulltext-documents", {}).get("ftxt:fulltext-document", {})
        if not claims_node:
            return None

        claims_data = claims_node.get("description", {}).get("claims", {})
        claim_list = claims_data.get("claim", [])
        if isinstance(claim_list, dict):
            claim_list = [claim_list]

        claims = []
        for c in claim_list:
            text = c.get("claim-text", {})
            if isinstance(text, dict):
                claims.append(text.get("$", "")[:3000])
            elif isinstance(text, list):
                claims.append(" ".join(t.get("$", "") if isinstance(t, dict) else str(t) for t in text)[:3000])

        return EPOClaimRecord(
            patent_number=patent_number,
            claims=claims,
            claim_count=len(claims),
            independent_claim_count=sum(1 for c in claims if "comprising" in c.lower() or "consisting" in c.lower()),
            retrieved_at_utc=_now_utc(),
            content_hash=_sha256(json.dumps(claims, sort_keys=True)),
        )
    except Exception:
        return None


def epo_ops_get_citations(patent_number: str) -> List[EPOCitationRecord]:
    """Retrieve citations for a patent, with EPO categories (X/I/Y/A)."""
    token = _get_oauth_token()
    if not token:
        return []

    path = f"/published-data/publication/epodoc/{patent_number}/citations"
    status, body, err = _ops_request(path)
    if status != 200:
        return []

    try:
        data = json.loads(body)
        docs = data.get("ops:world-patent-data", {}).get("exchange-document", {})
        if not docs:
            return []

        citations = []
        cites_node = docs.get("bibliographic-data", {}).get("references-cited", {})
        cites = cites_node.get("citation", [])
        if isinstance(cites, dict):
            cites = [cites]

        for c in cites:
            cited_doc = c.get("document-id", {})
            phase = c.get("@cited-phase", "")
            category = c.get("@citation-category", "")

            if isinstance(cited_doc, dict):
                cited_num = f"{cited_doc.get('@country','')}{cited_doc.get('@doc-number','')}{cited_doc.get('@kind','')}"
                if cited_num:
                    citations.append(EPOCitationRecord(
                        citing_patent=patent_number,
                        cited_patent=cited_num,
                        category=category,
                        category_meaning=CITATION_CATEGORIES.get(category, "UNKNOWN"),
                        retrieved_at_utc=_now_utc(),
                    ))
        return citations
    except Exception:
        return []


def epo_ops_get_family(patent_number: str, family_type: str = "INPADOC") -> Optional[EPOFamilyRecord]:
    """Retrieve INPADOC family for a patent."""
    token = _get_oauth_token()
    if not token:
        return None

    path = f"/family/publication/epodoc/{patent_number}"
    status, body, err = _ops_request(path)
    if status != 200:
        return None

    try:
        data = json.loads(body)
        family_node = data.get("ops:world-patent-data", {}).get("patent-family", {})
        if not family_node:
            return None

        members = family_node.get("family-member", [])
        if isinstance(members, dict):
            members = [members]

        family_id = family_node.get("@family-id", "")
        member_ids = []
        for m in members:
            pub = m.get("publication-reference", {}).get("document-id", [])
            if isinstance(pub, dict):
                pub = [pub]
            for p in pub:
                if p.get("@document-id-type") == "epodoc":
                    num = f"{p.get('@country','')}{p.get('@doc-number','')}{p.get('@kind','')}"
                    if num:
                        member_ids.append(num)

        return EPOFamilyRecord(
            root_patent=patent_number,
            family_id=family_id,
            family_type=family_type,
            family_members=member_ids,
            retrieved_at_utc=_now_utc(),
        )
    except Exception:
        return None


def is_epo_ops_available() -> bool:
    """Check if EPO OPS is available (credentials present)."""
    return _get_oauth_token() is not None
