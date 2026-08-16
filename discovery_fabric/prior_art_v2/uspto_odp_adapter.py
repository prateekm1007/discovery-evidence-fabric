"""
USPTO Open Data Portal (ODP) Adapter
======================================

USPTO migrated PatentsView into the Open Data Portal in March 2026.
The ODP provides REST APIs for:
  - patent metadata (grant & application)
  - claim text (Patent Claims Research Dataset)
  - continuity (parent/child relationships)
  - assignments
  - prosecution history
  - office actions
  - PTAB proceedings
  - citations

Endpoints:
  - https://api.uspto.gov/api/v1/patent/grants
  - https://api.uspto.gov/api/v1/patent/applications
  - https://api.uspto.gov/api/v1/patent/continuity
  - https://api.uspto.gov/api/v1/patent/assignment
  - https://api.uspto.gov/api/v1/patent/citations

AUTH:
  - Public endpoints: API key from https://uspto.gov/subscription-center
  - Higher rate limits require registration
  - Patent Claims Research Dataset: downloadable CSV from uspto.gov
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


USPTO_ODP_BASE = "https://api.uspto.gov/api/v1"
USPTO_PV_BASE = "https://api.patentsview.org/patents"


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class USPTOPatentRecord:
    """Patent record from USPTO ODP."""
    patent_number: str
    application_number: str = ""
    title: str = ""
    abstract: str = ""
    assignee: str = ""
    inventor: str = ""
    publication_date: str = ""
    grant_date: str = ""
    priority_date: str = ""
    filing_date: str = ""
    cpc_codes: List[str] = field(default_factory=list)
    ipc_codes: List[str] = field(default_factory=list)
    uspc_codes: List[str] = field(default_factory=list)
    family_id: str = ""
    source: str = "USPTO_ODP"
    retrieved_at_utc: str = ""
    content_hash: str = ""


@dataclass
class USPTOClaimRecord:
    """Claims from USPTO Patent Claims Research Dataset."""
    patent_number: str
    claims: List[str] = field(default_factory=list)
    claim_count: int = 0
    independent_claim_count: int = 0
    source: str = "USPTO_PCRD"
    retrieved_at_utc: str = ""
    content_hash: str = ""


@dataclass
class USPTOSearchAttempt:
    """One USPTO ODP search attempt."""
    query: str
    attempted: bool = False
    http_status: int = 0
    api_status: bool = False
    api_error_msg: str = ""
    normalized_state: str = "SOURCE_UNAVAILABLE"
    failure_substate: str = "NONE"
    patents: List[USPTOPatentRecord] = field(default_factory=list)
    patent_ids: List[str] = field(default_factory=list)
    total_count: int = 0
    retrieved_at_utc: str = ""


# ----------------------- AUTH -----------------------
def _load_uspto_key() -> str:
    """Load USPTO ODP API key from .env.keys or env vars."""
    keys_file = Path("/home/z/my-project/discovery-evidence-fabric/.env.keys")
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("USPTO_ODP_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("USPTO_ODP_API_KEY", "")


def _http_get(url: str, headers: Dict = None, timeout: int = 15) -> Tuple[int, bytes, str]:
    """HTTP GET with USPTO auth if available."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    h = {"User-Agent": "Patent-Evidence-Mesh/1.0", "Accept": "application/json"}
    if headers:
        h.update(headers)

    api_key = _load_uspto_key()
    if api_key:
        h["X-USPTO-API-Key"] = api_key

    try:
        req = urllib.request.Request(url, method="GET", headers=h)
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:500]
        return e.code, body.encode(), f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, b"", f"EXCEPTION: {type(e).__name__}: {str(e)[:200]}"


# ----------------------- API CALLS -----------------------
def uspto_search(query: str, limit: int = 10) -> USPTOSearchAttempt:
    """Search USPTO ODP for patents matching a query."""
    attempt = USPTOSearchAttempt(
        query=query[:500],
        attempted=True,
        retrieved_at_utc=_now_utc(),
    )

    # Try PatentsView-style query
    pv_query = json.dumps({
        "_text_phrase": {"patent_title": query},
        "_or": [{"_text_phrase": {"patent_abstract": query}}],
    })
    url = f"{USPTO_PV_BASE}/query?q={urllib.parse.quote(pv_query)}&f=" + urllib.parse.quote(
        json.dumps(["patent_number", "patent_title", "patent_abstract",
                    "patent_date", "patent_type", "assignees"])
    ) + f"&o={{\"size\":{limit}}}"

    status, body, err = _http_get(url)
    attempt.http_status = status

    if status != 200:
        attempt.api_status = False
        attempt.api_error_msg = err
        if status == 401 or status == 403:
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
        patents_data = data.get("patents", [])
        for p in patents_data:
            num = p.get("patent_number", "")
            if num:
                attempt.patent_ids.append(num)
                assignees = p.get("assignees", [])
                assignee = assignees[0].get("assignee_organization", "") if assignees else ""
                attempt.patents.append(USPTOPatentRecord(
                    patent_number=num,
                    title=p.get("patent_title", "") or "",
                    abstract=p.get("patent_abstract", "") or "",
                    assignee=assignee,
                    publication_date=p.get("patent_date", "") or "",
                    retrieved_at_utc=_now_utc(),
                    content_hash=_sha256(json.dumps(p, sort_keys=True, default=str)),
                ))
        attempt.total_count = len(attempt.patents)
        if attempt.total_count > 0:
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


def uspto_get_patent(patent_number: str) -> Optional[USPTOPatentRecord]:
    """Retrieve full bibliographic data for a US patent."""
    pv_query = json.dumps({"_eq": {"patent_number": patent_number}})
    url = f"{USPTO_PV_BASE}/query?q={urllib.parse.quote(pv_query)}&f=" + urllib.parse.quote(
        json.dumps(["patent_number", "patent_title", "patent_abstract", "patent_date",
                    "patent_type", "assignees", "inventors", "cpcs", "ipcs", "uspcs",
                    "patent_first_named_assignee_id", "application_number"])
    )
    status, body, err = _http_get(url)
    if status != 200:
        return None

    try:
        data = json.loads(body)
        patents = data.get("patents", [])
        if not patents:
            return None
        p = patents[0]

        cpc = [c.get("cpc_section_id", "") + c.get("cpc_subsection_id", "")
               for c in p.get("cpcs", []) if isinstance(c, dict)]
        ipc = [i.get("ipc_section_id", "") + i.get("ipc_subsection_id", "")
               for i in p.get("ipcs", []) if isinstance(i, dict)]

        return USPTOPatentRecord(
            patent_number=p.get("patent_number", patent_number),
            application_number=p.get("application_number", ""),
            title=p.get("patent_title", "") or "",
            abstract=p.get("patent_abstract", "") or "",
            publication_date=p.get("patent_date", "") or "",
            cpc_codes=cpc,
            ipc_codes=ipc,
            retrieved_at_utc=_now_utc(),
            content_hash=_sha256(json.dumps(p, sort_keys=True, default=str)),
        )
    except Exception:
        return None


def uspto_get_continuity(patent_number: str) -> List[Dict[str, str]]:
    """Retrieve parent/child continuity relationships for a US patent."""
    url = f"{USPTO_ODP_BASE}/patent/continuity?patent_number={urllib.parse.quote(patent_number)}"
    status, body, err = _http_get(url)
    if status != 200:
        return []

    try:
        data = json.loads(body)
        return data.get("continuity", [])
    except Exception:
        return []


def is_uspto_available() -> bool:
    """Check if USPTO ODP is available (always public, no key required for basic search)."""
    # USPTO is public — but rate-limited without an API key
    return True
