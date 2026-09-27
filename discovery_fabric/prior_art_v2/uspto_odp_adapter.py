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
# 2026-08-30 measured reality (CEO resolve-unavailable directive):
# - legacy api.patentsview.org/patents/query is RETIRED — it now serves an
#   HTML SPA page with HTTP 200, which is why uspto_search died with
#   'JSON parse error: Expecting value' (a masked endpoint retirement,
#   not a transient parse failure).
# - the replacement PatentsView API (search.patentsview.org) and the USPTO
#   ODP API (api.uspto.gov) BOTH require API keys (403 'Missing
#   Authentication Token' measured). No credential is provisioned.
# The adapter therefore: (a) validates content-type before parsing so a
# retired endpoint can never masquerade as a parse error (Art. XXI.3);
# (b) reads USPTO_ODP_API_KEY / PATENTSVIEW_API_KEY from .env.keys so the
# path is ready the day a credential arrives; absent key -> AUTH_FAILED.
USPTO_PV_BASE = "https://search.patentsview.org/api/v1"
_PV_ENDPOINTS_MEASURED_RETIRED = "2026-08-30"


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
    """Load USPTO/PatentsView API key from .env.keys or env vars.

    Accepts USPTO_ODP_API_KEY or PATENTSVIEW_API_KEY (either unlocks the
    new PatentsView search API; absent -> callers fail AUTH_FAILED)."""
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    if keys_file.exists():
        for line in keys_file.read_text(encoding="utf-8").splitlines():
            for name in ("USPTO_ODP_API_KEY", "PATENTSVIEW_API_KEY"):
                if line.startswith(name + "="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return val
    return os.environ.get("USPTO_ODP_API_KEY", "") or \
        os.environ.get("PATENTSVIEW_API_KEY", "")


def _http_get(url: str, headers: Dict = None, timeout: int = 15,
              response_content_type: list = None) -> Tuple[int, bytes, str]:
    """HTTP GET with USPTO auth if available.

    response_content_type: mutable out-param; the caller uses it to detect
    retired endpoints that answer 200 with HTML (masked-failure control).
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    h = {"User-Agent": "Patent-Evidence-Mesh/1.0", "Accept": "application/json"}
    if headers:
        h.update(headers)

    api_key = _load_uspto_key()
    if api_key:
        h["X-Api-Key"] = api_key
        h["X-USPTO-API-Key"] = api_key

    try:
        req = urllib.request.Request(url, method="GET", headers=h)
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body_bytes = resp.read()
        if response_content_type is not None:
            response_content_type.append(
                dict(resp.headers).get("Content-Type", ""))
        return resp.status, body_bytes, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:500]
        return e.code, body.encode(), f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, b"", f"EXCEPTION: {type(e).__name__}: {str(e)[:200]}"


def _http_get_json(url: str, headers: Dict = None, timeout: int = 15):
    """GET that also returns response Content-Type so callers can refuse to
    parse HTML as JSON (retired-endpoint mask, caught live 2026-08-30 when
    api.patentsview.org began serving an SPA page with HTTP 200)."""
    ctypes: list = []
    status, body, err = _http_get(url, headers=headers, timeout=timeout,
                                  response_content_type=ctypes)
    return status, body, err, (ctypes[0] if ctypes else "")


# ----------------------- API CALLS -----------------------
def uspto_search(query: str, limit: int = 10) -> USPTOSearchAttempt:
    """Search USPTO patents via the PatentsView API (new endpoint).

    2026-08-30 measured reality (live probe, custody-logged):
    - legacy api.patentsview.org/patents/query is RETIRED (serves an HTML
      SPA page with HTTP 200) — previously masqueraded as 'JSON parse
      error'; now detected via content-type guard -> ENDPOINT_RETIRED.
    - the replacement API (search.patentsview.org) and USPTO ODP
      (api.uspto.gov) both require API keys (403 measured). Without a key
      the attempt fails AUTH_FAILED immediately — no burn, no mask.
    """
    attempt = USPTOSearchAttempt(
        query=query[:500],
        attempted=True,
        retrieved_at_utc=_now_utc(),
    )

    if not _load_uspto_key():
        attempt.api_status = False
        attempt.failure_substate = "AUTH_FAILURE"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        attempt.api_error_msg = (
            "PatentsView legacy endpoint retired 2026-08-30 (HTML page "
            "measured); replacement API requires an unprovisioned "
            "PATENTSVIEW_API_KEY / USPTO_ODP_API_KEY")
        return attempt

    # New PatentsView API shape: POST /patent/ with structured query.
    pv_body = {
        "q": {"_text_any": {"patent_title": query,
                            "patent_abstract": query}},
        "f": ["patent_number", "patent_title", "patent_abstract",
              "patent_date", "assignees"],
        "o": {"size": limit},
    }
    url = f"{USPTO_PV_BASE}/patent/"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    h = {"User-Agent": "Patent-Evidence-Mesh/1.0",
         "Accept": "application/json",
         "Content-Type": "application/json",
         "X-Api-Key": _load_uspto_key()}
    try:
        req = urllib.request.Request(url, data=json.dumps(pv_body).encode(),
                                     headers=h, method="POST")
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        status, body, ctype = resp.status, resp.read(), \
            dict(resp.headers).get("Content-Type", "")
    except urllib.error.HTTPError as e:
        status, body, ctype = e.code, e.read(), \
            dict(e.headers).get("Content-Type", "")
    except Exception as e:
        status, body, ctype = 0, b"", ""

    attempt.http_status = status

    if status != 200:
        attempt.api_status = False
        attempt.api_error_msg = f"HTTP {status}: {body[:200]!r}"
        if status in (401, 403):
            attempt.failure_substate = "AUTH_FAILURE"
        elif status == 429:
            attempt.failure_substate = "RATE_LIMITED"
        else:
            attempt.failure_substate = "HTTP_ERROR"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        return attempt

    # content-type guard: a retired/misrouted endpoint answering 200 with
    # HTML is ENDPOINT_RETIRED, never a JSON parse crash (Art. XXI.3).
    if "json" not in (ctype or "").lower():
        attempt.api_status = False
        attempt.failure_substate = "ENDPOINT_RETIRED"
        attempt.normalized_state = "SOURCE_UNAVAILABLE"
        attempt.api_error_msg = (
            f"expected JSON, received Content-Type {ctype!r} — endpoint "
            f"retired or misrouted (measured {_PV_ENDPOINTS_MEASURED_RETIRED})")
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
