"""
Prior-Art Source Adapter V2

Three independent prior-art sources for the autonomous patentability loop:

  1. GOOGLE_PATENTS  — global patent corpus (xhr/query API, no auth)
  2. LENS_SCHOLARLY  — non-patent literature (Bearer token from user)
  3. PATSNAP_EUREKA  — PROVISIONAL: API tier upgrade required

All sources return a unified PriorArtHit schema so the downstream
Searcher/Mapper/Adversary agents can consume them uniformly.

PROVENANCE RULES (forensic-grade):
  - Every hit includes source_id, source_url, retrieved_at_utc, raw_payload_sha256
  - Every hit includes the original query string used to retrieve it
  - Token/key values are NEVER written to disk — only presence + length
"""
from __future__ import annotations
import os, sys, json, time, ssl, hashlib, urllib.request, urllib.parse, urllib.error, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------------- KEYS / CONFIG -----------------------
KEYS_FILE = Path("/home/z/my-project/discovery-evidence-fabric/.env.keys")

def _load_keys() -> Dict[str, str]:
    if not KEYS_FILE.exists():
        return {}
    out = {}
    for line in KEYS_FILE.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out

_KEYS = _load_keys()
LENS_TOKEN = _KEYS.get("LENS_API_TOKEN", "")
PATSNAP_KEY = _KEYS.get("PATSNAP_EUREKA_API_KEY", "")
PATENT_BEAR_KEY = _KEYS.get("PATENT_BEAR_API_KEY", "")

# SSL context (permissive for testing; tighten for production)
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

# User agent — PatSnap and Google expect a real UA
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ----------------------- DATA SCHEMA -----------------------
@dataclass
class PriorArtHit:
    """Unified schema for prior-art hits from any source."""
    source_id: str                     # GOOGLE_PATENTS | LENS_SCHOLARLY | PATSNAP_EUREKA
    source_url: str                    # Direct URL to the patent/paper
    retrieved_at_utc: str              # ISO 8601 UTC timestamp
    query: str                         # The query that produced this hit
    raw_payload_sha256: str            # SHA-256 of raw JSON payload (provenance)
    title: str
    snippet: str                       # 50-300 char excerpt
    assignee_or_authors: List[str]     # Assignees (patent) or authors (NPL)
    publication_date: Optional[str]    # YYYY-MM-DD or YYYY
    patent_id: Optional[str] = None    # Patent number (patents only)
    doi: Optional[str] = None          # DOI (NPL only)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceQueryResult:
    """Result of querying one source."""
    source_id: str
    success: bool
    latency_ms: int
    hits: List[PriorArtHit] = field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[int] = None
    rate_limit_remaining: Optional[int] = None


# ----------------------- HELPERS -----------------------
def _sha256(payload: bytes | str) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _strip_html(text: str) -> str:
    """Strip HTML tags + collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 20) -> Tuple[int, bytes, int]:
    """HTTP GET with timing. Returns (status, body, latency_ms)."""
    h = {"User-Agent": _UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    t0 = time.time()
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
        body = resp.read()
        return resp.status, body, int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        body = b""
        try: body = e.read()
        except: pass
        return e.code, body, int((time.time() - t0) * 1000)

def _http_post(url: str, payload: bytes, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[int, bytes, int]:
    """HTTP POST with timing. Returns (status, body, latency_ms)."""
    h = {"User-Agent": _UA, "Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        h.update(headers)
    t0 = time.time()
    req = urllib.request.Request(url, data=payload, headers=h, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
        body = resp.read()
        return resp.status, body, int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        body = b""
        try: body = e.read()
        except: pass
        return e.code, body, int((time.time() - t0) * 1000)


# ----------------------- SOURCE 1: GOOGLE PATENTS -----------------------
def search_google_patents(query: str, num_results: int = 8) -> SourceQueryResult:
    """
    Search Google Patents via the public xhr/query endpoint.
    No authentication required.
    Returns up to `num_results` PriorArtHit objects.
    """
    # Google Patents xhr API expects the query string in the `url` parameter,
    # URL-encoded. Format: q=<query>&num=<n>
    inner_qs = f"q={urllib.parse.quote(query)}&num={num_results}"
    outer_qs = urllib.parse.urlencode({"url": inner_qs, "exp": ""})
    url = f"https://patents.google.com/xhr/query?{outer_qs}"

    status, body, latency = _http_get(url, timeout=20)

    if status != 200:
        return SourceQueryResult(
            source_id="GOOGLE_PATENTS",
            success=False,
            latency_ms=latency,
            error=f"HTTP {status}",
            error_code=status,
        )

    try:
        data = json.loads(body)
    except Exception as e:
        return SourceQueryResult(
            source_id="GOOGLE_PATENTS",
            success=False,
            latency_ms=latency,
            error=f"JSON parse error: {e}",
        )

    hits: List[PriorArtHit] = []
    cluster = data.get("results", {}).get("cluster", [])
    for block in cluster:
        for r in block.get("result", []):
            p = r.get("patent", {})
            pid_raw = r.get("id", "")  # e.g. "patent/US11576774B2/en"
            pid = pid_raw.replace("patent/", "").replace("/en", "") if pid_raw else None
            title = _strip_html(p.get("title", ""))
            snippet = _strip_html(p.get("snippet", ""))[:400]
            assignee = p.get("assignee") or p.get("assignee_harmonized", {}).get("name")
            assignees = [assignee] if assignee else []
            pub_date = p.get("publication_date") or p.get("priority_date")
            source_url = f"https://patents.google.com/patent/{pid}/en" if pid else ""

            hit = PriorArtHit(
                source_id="GOOGLE_PATENTS",
                source_url=source_url,
                retrieved_at_utc=_now_utc(),
                query=query,
                raw_payload_sha256=_sha256(json.dumps(p, sort_keys=True)),
                title=title,
                snippet=snippet,
                assignee_or_authors=assignees,
                publication_date=pub_date,
                patent_id=pid,
                raw_metadata={
                    "publication_date": p.get("publication_date"),
                    "priority_date": p.get("priority_date"),
                    "inventor": p.get("inventor"),
                    "assignee_harmonized": p.get("assignee_harmonized"),
                    "country_code": (pid[:2] if pid else None),
                },
            )
            hits.append(hit)

    return SourceQueryResult(
        source_id="GOOGLE_PATENTS",
        success=True,
        latency_ms=latency,
        hits=hits,
    )


def fetch_google_patent_full_claims(patent_id: str) -> Dict[str, Any]:
    """
    Deep-fetch the full claims + abstract for a single patent.
    Returns dict with: patent_id, abstract, claims (list of strings), fetched_at_utc
    """
    url = f"https://patents.google.com/patent/{patent_id}/en"
    status, body, latency = _http_get(url, timeout=25)
    if status != 200:
        return {"patent_id": patent_id, "error": f"HTTP {status}", "latency_ms": latency}

    html = body.decode("utf-8", errors="ignore")

    # Extract abstract
    abstract = ""
    m = re.search(r'<abstract[^>]*>(.*?)</abstract>', html, re.DOTALL)
    if m:
        abstract = _strip_html(m.group(1))[:1500]

    # Extract claims section
    claims_text = ""
    m = re.search(r'<section[^>]*itemprop=["\']claims["\'][^>]*>(.*?)</section>', html, re.DOTALL)
    if m:
        claims_text = _strip_html(m.group(1))

    # Split into numbered claims
    claims_list = []
    # Pattern: "1. ...", "2. ..." etc.
    parts = re.split(r'\n\s*(?=\d+\.\s)', claims_text)
    for part in parts:
        part = part.strip()
        if re.match(r'^\d+\.\s', part):
            claims_list.append(part[:2000])

    # Extract description (background + summary) for context
    description = ""
    m = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', html, re.DOTALL)
    if m:
        description = _strip_html(m.group(1))[:5000]

    return {
        "patent_id": patent_id,
        "source_url": url,
        "abstract": abstract,
        "claims": claims_list,
        "description_excerpt": description,
        "fetched_at_utc": _now_utc(),
        "latency_ms": latency,
        "raw_html_sha256": _sha256(body),
    }


# ----------------------- SOURCE 2: LENS SCHOLARLY -----------------------
def _lens_string_query(query: str) -> str:
    """Lucene-style title-scoped string query for the Lens APIs.

    MEASURED DEFECT FIXED (2026-08-29, Art. XXXI memory): the structured
    DSL body {"query": {"bool": {"must": [{"match": {"title": ...}}]}}}
    does NOT 400 on api.lens.org — it is silently ignored (total=756812,
    max_score=0.0) and the API returns the newest records REGARDLESS of
    relevance (an astrophysics paper answered a CSF-shunt query). The
    STRING form 'title:(...)' is the only measured-correct relevance
    binding. A regression test pins this: the request body MUST use the
    string form, never the DSL form.
    """
    return f"title:({query})"


def search_lens_scholarly(query: str, num_results: int = 8) -> SourceQueryResult:
    """
    Search Lens Scholarly API (non-patent literature).
    Uses Bearer token from .env.keys.
    """
    if not LENS_TOKEN:
        return SourceQueryResult(
            source_id="LENS_SCHOLARLY",
            success=False,
            latency_ms=0,
            error="LENS_API_TOKEN not configured",
        )

    url = "https://api.lens.org/scholarly/search"
    payload = json.dumps({
        "query": _lens_string_query(query),
        "size": num_results,
        "sort": [{"date_published": "desc"}],
        "include": ["title", "authors", "date_published", "year_published",
                    "external_ids", "abstract", "source", "lens_id"],
    }).encode()

    headers = {"Authorization": f"Bearer {LENS_TOKEN}"}
    status, body, latency = _http_post(url, payload, headers=headers, timeout=25)

    if status != 200:
        return SourceQueryResult(
            source_id="LENS_SCHOLARLY",
            success=False,
            latency_ms=latency,
            error=f"HTTP {status}: {body.decode('utf-8', errors='ignore')[:200]}",
            error_code=status,
        )

    try:
        data = json.loads(body)
    except Exception as e:
        return SourceQueryResult(
            source_id="LENS_SCHOLARLY",
            success=False,
            latency_ms=latency,
            error=f"JSON parse error: {e}",
        )

    hits: List[PriorArtHit] = []
    for record in data.get("data", []):
        title = record.get("title", "")
        abstract = record.get("abstract", "") or ""
        snippet = (abstract[:400] if abstract else title)[:400]

        authors = []
        for a in (record.get("authors") or [])[:10]:
            name = " ".join(filter(None, [a.get("first_name"), a.get("last_name")]))
            if name:
                authors.append(name)

        doi = None
        for ext_id in (record.get("external_ids") or []):
            if ext_id.get("type") == "doi":
                doi = ext_id.get("value")
                break

        lens_id = record.get("lens_id", "")
        source_url = f"https://www.lens.org/scholar/article/{lens_id}" if lens_id else ""

        hit = PriorArtHit(
            source_id="LENS_SCHOLARLY",
            source_url=source_url,
            retrieved_at_utc=_now_utc(),
            query=query,
            raw_payload_sha256=_sha256(json.dumps(record, sort_keys=True)),
            title=title,
            snippet=snippet,
            assignee_or_authors=authors,
            publication_date=str(record.get("year_published") or record.get("date_published") or ""),
            doi=doi,
            raw_metadata={
                "lens_id": lens_id,
                "year_published": record.get("year_published"),
                "source_title": (record.get("source") or {}).get("title"),
                "publisher": (record.get("source") or {}).get("publisher"),
            },
        )
        hits.append(hit)

    return SourceQueryResult(
        source_id="LENS_SCHOLARLY",
        success=True,
        latency_ms=latency,
        hits=hits,
    )


# ----------------------- SOURCE 2b: LENS PATENT -----------------------
def search_lens_patent(query: str, num_results: int = 8) -> SourceQueryResult:
    """
    Search Lens PATENT API (POST api.lens.org/patent/search).

    Measured 2026-08-29 (string-query form, NO include parameter —
    'include' is rejected by the patent endpoint with
    'Unrecognized fields' 400s; the default response already carries
    biblio/doc_key/abstract/legal_status/families):
      - the provisioned LENS_API_TOKEN authenticates (200);
      - title:(...) string queries bind relevance correctly (48 total
        for 'hydrocephalus shunt valve');
      - invention_title is a LIST of {text, lang} objects;
        applicants live at biblio.parties.applicants[].extracted_name.value.
    The scholarly-side adapter is search_lens_scholarly. Per CEO Section 4
    (elite_v3): the two Lens resources are SEPARATE sources, never merged.
    """
    if not LENS_TOKEN:
        return SourceQueryResult(
            source_id="LENS_PATENT",
            success=False,
            latency_ms=0,
            error="LENS_API_TOKEN not configured",
        )

    url = "https://api.lens.org/patent/search"
    payload = json.dumps({
        "query": _lens_string_query(query),
        "size": num_results,
        "sort": [{"date_published": "desc"}],
    }).encode()

    headers = {"Authorization": f"Bearer {LENS_TOKEN}"}
    status, body, latency = _http_post(url, payload, headers=headers, timeout=25)

    if status != 200:
        return SourceQueryResult(
            source_id="LENS_PATENT",
            success=False,
            latency_ms=latency,
            error=f"HTTP {status}: {body.decode('utf-8', errors='ignore')[:200]}",
            error_code=status,
        )

    try:
        data = json.loads(body)
    except Exception as e:
        return SourceQueryResult(
            source_id="LENS_PATENT",
            success=False,
            latency_ms=latency,
            error=f"JSON parse error: {e}",
        )

    def _title_of(record: dict) -> str:
        biblio = record.get("biblio") or {}
        it = biblio.get("invention_title")
        if isinstance(it, list):
            for item in it:
                if isinstance(item, dict) and item.get("text"):
                    return str(item["text"])
            return ""
        return str(it or record.get("title") or "")

    def _applicants_of(record: dict) -> List[str]:
        parties = ((record.get("biblio") or {}).get("parties") or {})
        out = []
        for a in (parties.get("applicants") or [])[:10]:
            name = ((a.get("extracted_name") or {}).get("value")
                    if isinstance(a, dict) else None)
            if name:
                out.append(str(name))
        return out

    hits: List[PriorArtHit] = []
    for record in data.get("data", []):
        title = _title_of(record)
        abstract = record.get("abstract") or ""
        if isinstance(abstract, list):  # some records: [{text, lang}]
            abstract = abstract[0].get("text", "") if abstract else ""
        snippet = (abstract[:400] if abstract else title)[:400]

        doc_key = record.get("doc_key") or ""
        lens_id = record.get("lens_id") or ""
        source_url = f"https://www.lens.org/patent/{lens_id}" if lens_id else ""

        hit = PriorArtHit(
            source_id="LENS_PATENT",
            source_url=source_url,
            retrieved_at_utc=_now_utc(),
            query=query,
            raw_payload_sha256=_sha256(json.dumps(record, sort_keys=True)),
            title=title,
            snippet=snippet,
            assignee_or_authors=_applicants_of(record),
            publication_date=str(record.get("date_published") or ""),
            patent_id=doc_key or lens_id,
            raw_metadata={
                "lens_id": lens_id,
                "doc_key": doc_key,
                "jurisdiction": record.get("jurisdiction"),
                "kind": record.get("kind"),
                "doc_number": record.get("doc_number"),
                "legal_status": record.get("legal_status"),
                "date_published": record.get("date_published"),
            },
        )
        hits.append(hit)

    return SourceQueryResult(
        source_id="LENS_PATENT",
        success=True,
        latency_ms=latency,
        hits=hits,
    )


def fetch_lens_patent_full_abstract(doc_key: str) -> Dict[str, Any]:
    """Deep-fetch ONE patent record's FULL abstract by doc_key (R377).

    MEASURED CONTEXT (TOSCANINI/R377_PATENT_TEXT_FETCH.json): during the
    six fresh-domain runs every Google claims fetch failed — the engine
    built https://patents.google.com/patent/<LENS doc_key>/en which
    404s (Google's canonical id has no underscores/date suffix), and
    the corrected id is 503-blocked from this ASN anyway — so every
    family adjudicated at ABSTRACT tier on a 400-char TRUNCATED
    snippet while the Lens record carries the full abstract. This
    endpoint re-queries Lens by doc_key and returns the complete
    abstract text (more evidence for the SAME adjudication rules —
    Art. VII: evidence expanded, thresholds untouched).
    """
    if not LENS_TOKEN:
        return {"doc_key": doc_key, "error": "LENS_API_TOKEN not configured"}
    url = "https://api.lens.org/patent/search"
    payload = json.dumps({
        "query": f'doc_key:("{doc_key}")',
        "size": 1,
    }).encode()
    headers = {"Authorization": f"Bearer {LENS_TOKEN}"}
    status, body, latency = _http_post(url, payload, headers=headers,
                                       timeout=25)
    if status != 200:
        return {"doc_key": doc_key, "error": f"HTTP {status}",
                "latency_ms": latency}
    try:
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        return {"doc_key": doc_key, "error": f"JSON parse error: {exc}"}
    recs = data.get("data") or []
    if not recs:
        return {"doc_key": doc_key, "error": "NO_RECORD",
                "latency_ms": latency}
    rec = recs[0]
    abstract = rec.get("abstract") or ""
    if isinstance(abstract, list):
        abstract = abstract[0].get("text", "") if abstract else ""
    biblio = rec.get("biblio") or {}
    it = biblio.get("invention_title")
    title = ""
    if isinstance(it, list):
        for item in it:
            if isinstance(item, dict) and item.get("text"):
                title = str(item["text"])
                break
    elif isinstance(it, str):
        title = it
    return {
        "doc_key": doc_key,
        "title": title,
        "abstract_full": str(abstract),
        "abstract_len": len(str(abstract)),
        "lens_id": rec.get("lens_id"),
        "fetched_at_utc": _now_utc(),
        "latency_ms": latency,
        "raw_payload_sha256": _sha256(json.dumps(rec, sort_keys=True)),
    }


def google_patents_canonical_id(patent_id: str) -> str:
    """Canonicalize a Lens doc_key to the Google Patents id form.

    MEASURED DEFECT (R377): 'US_20260253984_A1_20260827' (Lens doc_key)
    was used verbatim in the claims-fetch URL — Google serves 404 for
    it; the canonical form is 'US20260253984A1' (country + number +
    kind code, no underscores, no date suffix). Deterministic parse:
    underscore-split, drop any all-digit trailing segment (the doc_key
    date suffix), join the rest.
    """
    pid = (patent_id or "").strip()
    if not pid:
        return ""
    parts = [p for p in pid.split("_") if p]
    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 8:
        parts = parts[:-1]  # '20260827' date suffix
    return "".join(parts)


# ----------------------- SOURCE 3: PATSNAP EUREKA (PROVISIONAL) -----------------------
def search_patsnap_eureka(query: str, num_results: int = 8) -> SourceQueryResult:
    """
    PatSnap Eureka API — PROVISIONAL.

    The API key is valid PatSnap format, but the account tier doesn't include
    API access. This function probes the endpoint and returns a structured
    PROVISIONAL result that the loop can route around.

    When the user upgrades to an API-tier subscription, this function will
    automatically start returning real hits (no code changes required).
    """
    if not PATSNAP_KEY:
        return SourceQueryResult(
            source_id="PATSNAP_EUREKA",
            success=False,
            latency_ms=0,
            error="PATSNAP_EUREKA_API_KEY not configured",
        )

    url = "https://connect.patsnap.com/api/v1/chat/completions"
    payload = json.dumps({
        "model": "eureka-2-pro",
        "messages": [
            {"role": "system", "content": "You are a patent prior-art searcher. Return JSON only."},
            {"role": "user", "content": f"Find {num_results} patents or scholarly works matching: {query}. Return as JSON array with fields: title, patent_id_or_doi, assignee_or_authors, publication_date, snippet."},
        ],
        "temperature": 0.0,
        "max_tokens": 1500,
    }).encode()

    headers = {"Authorization": f"Bearer {PATSNAP_KEY}"}
    status, body, latency = _http_post(url, payload, headers=headers, timeout=45)

    body_str = body.decode("utf-8", errors="ignore")

    # Probe for the known tier-insufficient error
    try:
        data = json.loads(body_str)
        if isinstance(data, dict):
            err_code = data.get("error_code")
            err_msg = data.get("error_msg", "")
            if err_code == 67200203 or "true rate" in err_msg.lower():
                return SourceQueryResult(
                    source_id="PATSNAP_EUREKA",
                    success=False,
                    latency_ms=latency,
                    error=f"PATSNAP_API_TIER_INSUFFICIENT: {err_msg}",
                    error_code=err_code,
                )
            if err_code == 67200008 or "apikey not Pass" in err_msg:
                return SourceQueryResult(
                    source_id="PATSNAP_EUREKA",
                    success=False,
                    latency_ms=latency,
                    error=f"PATSNAP_AUTH_HEADER_INVALID: {err_msg}",
                    error_code=err_code,
                )
            if err_code == 67200202 or "apikey auth error" in err_msg.lower():
                # R379: the CEO-provided fresh key (sk-…) was probed
                # live and rejected with 67200202 "apikey auth error!"
                # (HTTP 200) — a distinct auth-class failure from the
                # historical BALANCE_EXHAUSTED 67200005. Recorded
                # precisely so the health report shows the exact
                # unblock action needed (credential/tier verification),
                # never a generic HTTP error.
                return SourceQueryResult(
                    source_id="PATSNAP_EUREKA",
                    success=False,
                    latency_ms=latency,
                    error=f"PATSNAP_KEY_REJECTED_AUTH: {err_msg}",
                    error_code=err_code,
                )
            # If we get here, the API returned a real chat response — parse it
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message", {}).get("content", "")
                # Try to parse the JSON array from the model's response
                try:
                    # Strip markdown code fences if present
                    msg_clean = re.sub(r"^```(?:json)?\s*", "", msg.strip())
                    msg_clean = re.sub(r"\s*```$", "", msg_clean)
                    items = json.loads(msg_clean)
                    if isinstance(items, list):
                        hits = []
                        for item in items[:num_results]:
                            hits.append(PriorArtHit(
                                source_id="PATSNAP_EUREKA",
                                source_url=item.get("patent_id_or_doi") or item.get("url") or "",
                                retrieved_at_utc=_now_utc(),
                                query=query,
                                raw_payload_sha256=_sha256(json.dumps(item, sort_keys=True)),
                                title=item.get("title", ""),
                                snippet=item.get("snippet", "")[:400],
                                assignee_or_authors=[item.get("assignee_or_authors")] if item.get("assignee_or_authors") else [],
                                publication_date=item.get("publication_date"),
                                patent_id=item.get("patent_id_or_doi") if "patent" in str(item.get("patent_id_or_doi", "")).lower() else None,
                                doi=item.get("patent_id_or_doi") if "10." in str(item.get("patent_id_or_doi", "")) else None,
                            ))
                        return SourceQueryResult(
                            source_id="PATSNAP_EUREKA",
                            success=True,
                            latency_ms=latency,
                            hits=hits,
                        )
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    return SourceQueryResult(
        source_id="PATSNAP_EUREKA",
        success=False,
        latency_ms=latency,
        error=f"HTTP {status}: {body_str[:200]}",
        error_code=status,
    )


# ----------------------- SOURCE 4: PATENT_BEAR (MCP) -----------------------
# R378: persistent quota meter. The CEO statement (2026-08-31):
# "Use PatentBear for patents. Investors have provided unlimited
# investment for it." The ACCOUNT upgrade is a CEO-side action; until
# the provider meter itself changes, the measured meter (monthly_remaining
# in every response) remains the authority. The guard below reserves a
# small floor of searches so the last queries can never be burned
# silently by a batch run (metered-source policy, K-series).
PATENTBEAR_METER_PATH = Path(__file__).resolve().parents[2] / \
    "patent_sources" / "patentbear_meter.json"
PATENTBEAR_RESERVE_FLOOR = int(os.environ.get("PATENTBEAR_RESERVE_FLOOR", "2"))


def patentbear_meter_state() -> Dict[str, Any]:
    """Read the persisted meter (remaining/quota as last reported by
    the provider). Missing file = UNKNOWN (never guessed)."""
    try:
        return json.loads(PATENTBEAR_METER_PATH.read_text())
    except Exception:  # noqa: BLE001 — missing/corrupt = UNKNOWN
        return {"monthly_remaining": None, "updated_at": None,
                "note": "no provider-reported meter state recorded yet"}


def _patentbear_update_meter(remaining: Any) -> None:
    """Persist the provider-reported remaining quota after a call."""
    try:
        PATENTBEAR_METER_PATH.parent.mkdir(parents=True, exist_ok=True)
        PATENTBEAR_METER_PATH.write_text(json.dumps({
            "monthly_remaining": remaining,
            "updated_at": _now_utc(),
            "reserve_floor": PATENTBEAR_RESERVE_FLOOR,
        }, indent=1))
    except Exception:  # noqa: BLE001 — meter persistence is best-effort
        pass


def search_patent_bear(query: str, num_results: int = 8) -> SourceQueryResult:
    """
    Search Patent Bear via MCP (Model Context Protocol) JSON-RPC endpoint.

    Patent Bear exposes a Supabase Edge Function backend at api.patentbear.com
    that is accessed via MCP at https://www.patentbear.com/mcp using Bearer auth.

    MCP tools available:
      - search_patents: keyword/identifier search across patents, publications, NPL
      - get_patent_record: full text fetch by patent id

    Rate limit: 20 searches/month on this key (tracked in usage response);
    CEO 2026-08-31: investors fund unlimited usage — the account upgrade
    is pending; the provider-reported meter remains the authority. The
    persistent meter guard reserves PATENTBEAR_RESERVE_FLOOR searches
    (default 2) so batch runs can never silently burn the last queries.
    """
    meter = patentbear_meter_state()
    remaining = meter.get("monthly_remaining")
    if isinstance(remaining, (int, float)) and remaining <= PATENTBEAR_RESERVE_FLOOR:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=0,
            error=(f"RATE_LIMITED: provider meter shows "
                   f"{int(remaining)} remaining; reserve floor "
                   f"{PATENTBEAR_RESERVE_FLOOR} enforced "
                   "(metered-source policy)"),
            error_code=429,
        )
    if not PATENT_BEAR_KEY:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=0,
            error="PATENT_BEAR_API_KEY not configured",
        )

    url = "https://www.patentbear.com/mcp"
    # Cap at 25 (Patent Bear max_hits limit)
    max_hits = min(num_results, 25)
    # Patent Bear has query length limits — truncate to 200 chars to avoid HTTP 502
    truncated_query = query[:200]

    # Patent Bear's "scope=all" sometimes returns HTTP 502 (upstream NPL index issue).
    # Default to "patents" which is more reliable; NPL is already covered by LENS_SCHOLARLY.
    def _do_search(scope_value: str) -> Tuple[int, bytes, int]:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000) % 1000000,
            "method": "tools/call",
            "params": {
                "name": "search_patents",
                "arguments": {
                    "query": truncated_query,
                    "max_hits": max_hits,
                    "scope": scope_value,
                    "sort": "relevance",
                }
            }
        }).encode()
        return _http_post(url, payload, headers=headers, timeout=30)

    headers = {
        "Authorization": f"Bearer {PATENT_BEAR_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18",
    }

    # Try "all" first, fall back to "patents" on 502
    status, body, latency = _do_search("all")
    used_fallback = False
    if status == 200:
        try:
            data_check = json.loads(body)
            if "error" in data_check and "502" in str(data_check.get("error", {}).get("message", "")):
                # Fallback to patents-only
                status, body, latency = _do_search("patents")
                used_fallback = True
        except Exception:
            pass

    if status != 200:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=latency,
            error=f"HTTP {status}: {body.decode('utf-8', errors='ignore')[:200]}",
            error_code=status,
        )

    try:
        data = json.loads(body)
    except Exception as e:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=latency,
            error=f"JSON parse error: {e}",
        )

    # Check for MCP error
    if "error" in data:
        err = data["error"]
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=latency,
            error=f"MCP error {err.get('code')}: {err.get('message','')[:200]}",
            error_code=err.get("code"),
        )

    # Extract text content from MCP response
    result = data.get("result", {})
    content = result.get("content", [])
    if not content:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=latency,
            error="Empty MCP content",
        )

    text_content = ""
    for c in content:
        if c.get("type") == "text":
            text_content = c.get("text", "")
            break

    if not text_content:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=latency,
            error="No text content in MCP response",
        )

    # Parse the text content as JSON (Patent Bear returns JSON-encoded search results)
    try:
        search_data = json.loads(text_content)
    except json.JSONDecodeError as e:
        return SourceQueryResult(
            source_id="PATENT_BEAR",
            success=False,
            latency_ms=latency,
            error=f"Search results parse error: {e}",
        )

    # Build PriorArtHit objects
    hits: List[PriorArtHit] = []
    for record in search_data.get("hits", []):
        pid = record.get("id", "")  # e.g. "US10919033B2"
        title = record.get("title", "")
        abstract = record.get("abstract", "") or ""

        # Build snippet from abstract + matched text
        snippet_parts = [abstract[:300]] if abstract else []
        snippet_data = record.get("snippet", {}) or {}
        for field in ("abstract", "claimsText", "descriptionText"):
            for s in snippet_data.get(field, [])[:2]:
                snippet_parts.append(_strip_html(s)[:200])
        snippet = " | ".join(snippet_parts)[:600]

        # Authors/assignee
        assignee = record.get("assignee") or record.get("assigneeName")
        assignees = [assignee] if assignee else []
        # For NPL articles, use authors
        if record.get("source_type") == "article":
            authors = record.get("authors", [])
            if authors:
                assignees = authors

        pub_date = record.get("publication_date") or record.get("issue_date")
        if pub_date:
            pub_date = pub_date[:10]  # YYYY-MM-DD

        source_url = record.get("source_url") or record.get("url", "")
        doi = record.get("doi")
        # If source_type is article and has DOI, set doi
        if record.get("source_type") == "article" and not doi:
            doi = record.get("externalIds", {}).get("doi") if isinstance(record.get("externalIds"), dict) else None

        hit = PriorArtHit(
            source_id="PATENT_BEAR",
            source_url=source_url,
            retrieved_at_utc=_now_utc(),
            query=query,
            raw_payload_sha256=_sha256(json.dumps(record, sort_keys=True)),
            title=title,
            snippet=snippet,
            assignee_or_authors=assignees,
            publication_date=pub_date,
            patent_id=pid if record.get("source_type") in ("patent", "publication") else None,
            doi=doi,
            raw_metadata={
                "source_type": record.get("source_type"),
                "patent_number": record.get("patent_number"),
                "inventors": record.get("inventors", []),
                "cpc": record.get("cpc", []),
                "publication_date": record.get("publication_date"),
                "issue_date": record.get("issue_date"),
                "assignee": record.get("assignee"),
                "full_text_url": record.get("full_text_url"),
                "snippet_raw": snippet_data,
            },
        )
        hits.append(hit)

    # Track usage in error field if rate limit hit (informational)
    usage = search_data.get("usage", {})
    # R378: persist the provider-reported meter after every response —
    # the guard on the next call reads it (never burns the reserve floor)
    _patentbear_update_meter(usage.get("monthly_remaining"))

    return SourceQueryResult(
        source_id="PATENT_BEAR",
        success=True,
        latency_ms=latency,
        hits=hits,
        rate_limit_remaining=usage.get("monthly_remaining"),
    )


def fetch_patent_bear_record(patent_id: str) -> Dict[str, Any]:
    """
    Fetch the full text of a patent via Patent Bear MCP get_patent_record tool.
    Returns dict with: patent_id, title, abstract, claims (list), description, fetched_at_utc
    """
    if not PATENT_BEAR_KEY:
        return {"patent_id": patent_id, "error": "PATENT_BEAR_API_KEY not configured"}

    url = "https://www.patentbear.com/mcp"
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1000000,
        "method": "tools/call",
        "params": {
            "name": "get_patent_record",
            "arguments": {
                "id": patent_id,
                "format": "both",
                "fields": "abstract,claims,description",
            }
        }
    }).encode()

    headers = {
        "Authorization": f"Bearer {PATENT_BEAR_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18",
    }
    status, body, latency = _http_post(url, payload, headers=headers, timeout=30)
    if status != 200:
        return {"patent_id": patent_id, "error": f"HTTP {status}", "latency_ms": latency}

    try:
        data = json.loads(body)
        if "error" in data:
            return {"patent_id": patent_id, "error": f"MCP: {data['error'].get('message','')[:200]}"}
        content = data.get("result", {}).get("content", [])
        for c in content:
            if c.get("type") == "text":
                record = json.loads(c.get("text", "{}"))
                record["patent_id"] = patent_id
                record["fetched_at_utc"] = _now_utc()
                record["latency_ms"] = latency
                record["raw_payload_sha256"] = _sha256(body)
                return record
    except Exception as e:
        return {"patent_id": patent_id, "error": f"Parse error: {e}", "latency_ms": latency}

    return {"patent_id": patent_id, "error": "No content", "latency_ms": latency}


# ----------------------- UNIFIED SEARCH -----------------------
def search_all_sources(query: str, num_per_source: int = 8) -> Dict[str, SourceQueryResult]:
    """
    Query ALL prior-art sources in parallel.
    Returns a dict mapping source_id -> SourceQueryResult.
    """
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(search_google_patents, query, num_per_source): "GOOGLE_PATENTS",
            ex.submit(search_lens_scholarly, query, num_per_source): "LENS_SCHOLARLY",
            ex.submit(search_patsnap_eureka, query, num_per_source): "PATSNAP_EUREKA",
            ex.submit(search_patent_bear, query, num_per_source): "PATENT_BEAR",
        }
        results: Dict[str, SourceQueryResult] = {}
        for f in as_completed(futures):
            sid = futures[f]
            try:
                results[sid] = f.result()
            except Exception as e:
                results[sid] = SourceQueryResult(
                    source_id=sid,
                    success=False,
                    latency_ms=0,
                    error=f"EXCEPTION: {e}",
                )
    return results


def get_source_status() -> Dict[str, Dict[str, Any]]:
    """Return current status of each source (for audit / loop metadata)."""
    return {
        "GOOGLE_PATENTS": {
            "endpoint": "https://patents.google.com/xhr/query",
            "auth": "none",
            "status": "LIVE",
            "verified_at": _now_utc(),
        },
        "LENS_SCHOLARLY": {
            "endpoint": "https://api.lens.org/scholarly/search",
            "auth": "Bearer token",
            "token_present": bool(LENS_TOKEN),
            "token_length": len(LENS_TOKEN),
            "status": "LIVE" if LENS_TOKEN else "NO_TOKEN",
            "verified_at": _now_utc(),
        },
        "PATSNAP_EUREKA": {
            "endpoint": "https://connect.patsnap.com/api/v1/chat/completions",
            "auth": "Bearer token",
            "token_present": bool(PATSNAP_KEY),
            "token_length": len(PATSNAP_KEY),
            "status": "PROVISIONAL_TIER_INSUFFICIENT" if PATSNAP_KEY else "NO_TOKEN",
            "error_code": 67200203,
            "verified_at": _now_utc(),
        },
        "PATENT_BEAR": {
            "endpoint": "https://www.patentbear.com/mcp",
            "auth": "Bearer token (MCP JSON-RPC)",
            "token_present": bool(PATENT_BEAR_KEY),
            "token_length": len(PATENT_BEAR_KEY),
            "status": "LIVE" if PATENT_BEAR_KEY else "NO_TOKEN",
            "protocol": "MCP 2025-06-18",
            "tools": ["search_patents", "get_patent_record"],
            "rate_limit": "20 searches/month on this key tier",
            "verified_at": _now_utc(),
        },
    }


# ----------------------- CLI / SELF-TEST -----------------------
if __name__ == "__main__":
    print("="*60)
    print("PRIOR-ART SOURCE ADAPTER V2 — SELF-TEST")
    print("="*60)
    print(f"LENS token present: {bool(LENS_TOKEN)} (len={len(LENS_TOKEN)})")
    print(f"PATSNAP key present: {bool(PATSNAP_KEY)} (len={len(PATSNAP_KEY)})")
    print(f"PATENT_BEAR key present: {bool(PATENT_BEAR_KEY)} (len={len(PATENT_BEAR_KEY)})")

    test_query = "hydrogel coating nanofiber reinforcement medical device"

    print(f"\nTest query: {test_query}")
    print("\nQuerying 4 sources in parallel...")

    results = search_all_sources(test_query, num_per_source=5)

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    for sid, r in results.items():
        print(f"\n[{sid}]")
        print(f"  success:     {r.success}")
        print(f"  latency:     {r.latency_ms} ms")
        print(f"  hits:        {len(r.hits)}")
        if r.error:
            print(f"  error:       {r.error[:200]}")
        if r.error_code:
            print(f"  error_code:  {r.error_code}")
        for h in r.hits[:3]:
            print(f"    - {h.patent_id or h.doi or '?'}: {h.title[:100]}")
            print(f"      snippet: {h.snippet[:200]}")

    # Save self-test output
    out = Path("/home/z/my-project/discovery-evidence-fabric/patent_sources/v2/adapter_self_test.json")
    out.write_text(json.dumps({
        "test_query": test_query,
        "timestamp": _now_utc(),
        "source_status": get_source_status(),
        "results": {
            sid: {
                "success": r.success,
                "latency_ms": r.latency_ms,
                "hit_count": len(r.hits),
                "error": r.error,
                "error_code": r.error_code,
                "hits": [asdict(h) for h in r.hits],
            } for sid, r in results.items()
        },
    }, indent=2))
    print(f"\nSelf-test report: {out}")
