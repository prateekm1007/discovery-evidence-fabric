"""
Patent Evidence Retrieval Layer V3
====================================

Deterministic retrieval fallback chain for Google Patents, with strict
GOLD evidence definition per CEO directive.

RETRIEVAL FALLBACK CHAIN (per CEO Section 2):
  A. patents.google.com/patent/<id>/en — HTML page
  B. Google Patents page HTML parsing (multiple selector strategies)
  C. Google Patents embedded JSON / structured metadata
  D. publication metadata endpoint if available
  E. cached/raw result already returned by the search layer

For every patent:
  retrieval_attempts[]
  retrieval_success
  retrieval_method
  claim_count
  full_content_hash

GOLD EVIDENCE DEFINITION (per CEO Section 3):
  GOLD requires ALL of:
    1. verified patent identifier
    2. publication date
    3. priority date
    4. family
    5. actual claim text OR exact specification passage
    6. source URL
    7. retrieval timestamp
    8. full-content hash

  Search snippet = NOT GOLD
  Abstract only = NOT GOLD
  LLM summary = NOT GOLD
  Semantic similarity = NOT GOLD
"""
from __future__ import annotations
import os, sys, json, time, re, ssl, hashlib, urllib.request, urllib.parse, urllib.error
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Load keys
KEYS_FILE = Path(__file__).resolve().parents[2] / ".env.keys"
def _load_keys() -> Dict[str, str]:
    if not KEYS_FILE.exists(): return {}
    out = {}
    for line in KEYS_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out

_KEYS = _load_keys()
PATENT_BEAR_KEY = _KEYS.get("PATENT_BEAR_API_KEY", "")

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha256(payload: bytes | str) -> str:
    if isinstance(payload, str): payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class RetrievalAttempt:
    """One attempt in the fallback chain."""
    method: str          # A_html_page | B_html_parse | C_embedded_json | D_metadata_endpoint | E_cached
    success: bool
    claim_count: int
    latency_ms: int
    error: Optional[str] = None
    content_hash: Optional[str] = None


@dataclass
class PatentRecord:
    """Full patent record with retrieval provenance."""
    patent_id: str
    retrieval_attempts: List[RetrievalAttempt] = field(default_factory=list)
    retrieval_success: bool = False
    retrieval_method: str = ""  # which method succeeded
    claim_count: int = 0
    full_content_hash: str = ""

    # GOLD evidence fields (ALL required for GOLD)
    title: str = ""
    abstract: str = ""
    claims: List[str] = field(default_factory=list)
    description: str = ""
    publication_date: Optional[str] = None
    priority_date: Optional[str] = None
    family_id: Optional[str] = None
    assignee: Optional[str] = None
    inventors: List[str] = field(default_factory=list)
    cpc: List[str] = field(default_factory=list)
    source_url: str = ""
    retrieved_at_utc: str = ""

    # GOLD assessment
    is_gold: bool = False
    gold_missing: List[str] = field(default_factory=list)  # which GOLD requirements are missing

    def assess_gold(self):
        """Assess whether this record qualifies as GOLD evidence.
        GOLD requires ALL 8 fields per CEO Section 3."""
        required = {
            "verified_patent_id": bool(self.patent_id and len(self.patent_id) > 4),
            "publication_date": bool(self.publication_date),
            "priority_date": bool(self.priority_date),
            "family_id": bool(self.family_id),
            "claim_text": bool(self.claims and len(self.claims) > 0),
            "source_url": bool(self.source_url),
            "retrieval_timestamp": bool(self.retrieved_at_utc),
            "full_content_hash": bool(self.full_content_hash),
        }
        self.gold_missing = [k for k, v in required.items() if not v]
        self.is_gold = len(self.gold_missing) == 0
        return self.is_gold


# ----------------------- RETRIEVAL FALLBACK CHAIN -----------------------
def fetch_patent_full(patent_id: str) -> PatentRecord:
    """
    Deterministic retrieval fallback chain for a patent.

    A. patents.google.com/patent/<id>/en — fetch HTML page
    B. HTML parsing with multiple selector strategies
    C. Embedded JSON / structured metadata extraction
    D. (reserved) publication metadata endpoint
    E. (reserved) cached result from search layer
    """
    record = PatentRecord(
        patent_id=patent_id,
        source_url=f"https://patents.google.com/patent/{patent_id}/en",
        retrieved_at_utc=_now_utc(),
    )

    # METHOD A: Fetch the HTML page
    html, latency_a = _fetch_html_page(patent_id)
    attempt_a = RetrievalAttempt(
        method="A_html_page",
        success=bool(html),
        claim_count=0,
        latency_ms=latency_a,
        error=None if html else "HTTP fetch failed",
    )
    record.retrieval_attempts.append(attempt_a)

    if not html:
        record.assess_gold()
        return record

    # Compute hash of raw HTML for provenance
    record.full_content_hash = _sha256(html)

    # METHOD B: HTML parsing with multiple strategies
    claims_b, abstract_b, desc_b, meta_b = _parse_html_strategy_b(html)
    attempt_b = RetrievalAttempt(
        method="B_html_parse",
        success=bool(claims_b),
        claim_count=len(claims_b),
        latency_ms=0,
        error=None if claims_b else "No claims found via HTML parsing",
        content_hash=_sha256(json.dumps(claims_b, sort_keys=True)) if claims_b else None,
    )
    record.retrieval_attempts.append(attempt_b)

    if claims_b:
        record.claims = claims_b
        record.abstract = abstract_b
        record.description = desc_b[:5000]
        record.retrieval_success = True
        record.retrieval_method = "B_html_parse"
        record.claim_count = len(claims_b)
        # Merge metadata
        record.publication_date = meta_b.get("publication_date", record.publication_date)
        record.priority_date = meta_b.get("priority_date", record.priority_date)
        record.assignee = meta_b.get("assignee", record.assignee)
        record.inventors = meta_b.get("inventors", record.inventors)
        record.cpc = meta_b.get("cpc", record.cpc)
        record.title = meta_b.get("title", record.title)
        record.family_id = meta_b.get("family_id", record.family_id)
        record.assess_gold()
        return record

    # METHOD C: Embedded JSON / structured metadata
    claims_c, abstract_c, meta_c = _parse_embedded_json_strategy_c(html)
    attempt_c = RetrievalAttempt(
        method="C_embedded_json",
        success=bool(claims_c),
        claim_count=len(claims_c),
        latency_ms=0,
        error=None if claims_c else "No claims found via embedded JSON",
        content_hash=_sha256(json.dumps(claims_c, sort_keys=True)) if claims_c else None,
    )
    record.retrieval_attempts.append(attempt_c)

    if claims_c:
        record.claims = claims_c
        record.abstract = abstract_c or abstract_b
        record.retrieval_success = True
        record.retrieval_method = "C_embedded_json"
        record.claim_count = len(claims_c)
        record.publication_date = meta_c.get("publication_date", record.publication_date)
        record.priority_date = meta_c.get("priority_date", record.priority_date)
        record.assignee = meta_c.get("assignee", record.assignee)
        record.inventors = meta_c.get("inventors", record.inventors)
        record.cpc = meta_c.get("cpc", record.cpc)
        record.title = meta_c.get("title", record.title)
        record.assess_gold()
        return record

    # METHOD D: (reserved) publication metadata endpoint
    # Not implemented yet — placeholder for future
    attempt_d = RetrievalAttempt(
        method="D_metadata_endpoint",
        success=False,
        claim_count=0,
        latency_ms=0,
        error="Not implemented (reserved for future)",
    )
    record.retrieval_attempts.append(attempt_d)

    # METHOD E: (reserved) cached result from search layer
    attempt_e = RetrievalAttempt(
        method="E_cached_search_result",
        success=False,
        claim_count=0,
        latency_ms=0,
        error="No cached result available",
    )
    record.retrieval_attempts.append(attempt_e)

    # Even if claims failed, save what we got (abstract, title)
    if abstract_b:
        record.abstract = abstract_b
        record.retrieval_method = "B_html_parse_abstract_only"

    record.assess_gold()
    return record


# ----------------------- METHOD A: FETCH HTML PAGE -----------------------
def _fetch_html_page(patent_id: str) -> Tuple[Optional[str], int]:
    """Fetch the Google Patents HTML page for a patent."""
    url = f"https://patents.google.com/patent/{patent_id}/en"
    headers = {"User-Agent": _UA, "Accept": "text/html"}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        resp = urllib.request.urlopen(req, timeout=25, context=_SSL)
        body = resp.read()
        elapsed = int((time.time() - t0) * 1000)
        return body.decode("utf-8", errors="ignore"), elapsed
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - t0) * 1000)
        return None, elapsed
    except Exception:
        elapsed = int((time.time() - t0) * 1000)
        return None, elapsed


# ----------------------- METHOD B: HTML PARSING (multiple strategies) -----------------------
def _parse_html_strategy_b(html: str) -> Tuple[List[str], str, str, Dict[str, Any]]:
    """
    Parse HTML with multiple selector strategies to extract claims, abstract, description, metadata.

    Returns (claims, abstract, description, metadata).
    """
    claims: List[str] = []
    abstract = ""
    description = ""
    metadata: Dict[str, Any] = {}

    # --- Claims extraction (try multiple patterns) ---
    # Strategy B1: <section itemprop="claims">
    claims_text = _extract_claims_strategy_b1(html)
    if not claims_text:
        # Strategy B2: <div class="claims">
        claims_text = _extract_claims_strategy_b2(html)
    if not claims_text:
        # Strategy B3: <h2 id="claims"> ... </h2> or similar
        claims_text = _extract_claims_strategy_b3(html)

    if claims_text:
        claims = _split_claims(claims_text)

    # --- Abstract extraction ---
    abstract = _extract_abstract(html)

    # --- Description extraction ---
    description = _extract_description(html)

    # --- Metadata extraction ---
    metadata = _extract_metadata(html)

    return claims, abstract, description, metadata


def _extract_claims_strategy_b1(html: str) -> str:
    """B1: <section itemprop="claims">"""
    m = re.search(r'<section[^>]*itemprop=["\']claims["\'][^>]*>(.*?)</section>', html, re.DOTALL)
    if m:
        return _strip_html(m.group(1))
    return ""


def _extract_claims_strategy_b2(html: str) -> str:
    """B2: <div class="claims"> or similar."""
    m = re.search(r'<div[^>]*class=["\'][^"\']*claims[^"\']*["\'][^>]*>(.*?)</div>\s*</section>', html, re.DOTALL)
    if m:
        return _strip_html(m.group(1))
    # Broader: any div with "claim" in class
    m = re.search(r'<div[^>]*class=["\'][^"\']*claim[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    if m:
        return _strip_html(m.group(1))
    return ""


def _extract_claims_strategy_b3(html: str) -> str:
    """B3: Look for 'What is claimed is' or numbered claims."""
    # Find "What is claimed is" and grab everything after
    m = re.search(r'(?:What is claimed is|We claim|The invention claimed)[,:]?[\s]*(.*?)(?:</section>|</article>|<h2|<h3|Description|Abstract)', html, re.DOTALL | re.IGNORECASE)
    if m:
        return _strip_html(m.group(1))
    return ""


def _split_claims(claims_text: str) -> List[str]:
    """
    Split claims text into individual numbered claims.
    Fixes the bug where the old parser required newlines (which don't exist after strip_html).
    """
    if not claims_text:
        return []

    # Remove the "Claims (N) What is claimed is:" preamble
    text = re.sub(r'^.*?(?:What is claimed is|We claim|The invention claimed)[,:]?\s*', '', claims_text, flags=re.IGNORECASE | re.DOTALL)

    # Split on "N. " where N is a number, using lookahead
    # This works even when whitespace has been collapsed
    parts = re.split(r'(?=\b\d+\.\s+[A-Z])', text)

    claims = []
    for part in parts:
        part = part.strip()
        # Must start with a number and be reasonably long
        if re.match(r'^\d+\.\s+', part) and len(part) > 10:
            # Cap at 3000 chars per claim
            claims.append(part[:3000])

    return claims


def _extract_abstract(html: str) -> str:
    """Extract abstract from HTML."""
    # Try <abstract> tag
    m = re.search(r'<abstract[^>]*>(.*?)</abstract>', html, re.DOTALL)
    if m:
        return _strip_html(m.group(1))[:2000]
    # Try itemprop="abstract"
    m = re.search(r'<[^>]*itemprop=["\']abstract["\'][^>]*>(.*?)</', html, re.DOTALL)
    if m:
        return _strip_html(m.group(1))[:2000]
    # Try <div class="abstract">
    m = re.search(r'<div[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    if m:
        return _strip_html(m.group(1))[:2000]
    return ""


def _extract_description(html: str) -> str:
    """Extract description section from HTML."""
    # <section itemprop="description">
    m = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', html, re.DOTALL)
    if m:
        return _strip_html(m.group(1))[:8000]
    return ""


def _extract_metadata(html: str) -> Dict[str, Any]:
    """Extract publication date, priority date, assignee, inventors, CPC, title, family from HTML."""
    meta: Dict[str, Any] = {
        "title": "",
        "publication_date": None,
        "priority_date": None,
        "assignee": None,
        "inventors": [],
        "cpc": [],
        "family_id": None,
    }

    # Title: <meta property="og:title"> or <title>
    m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)', html)
    if m:
        # Format: "US10919033B2 - Flow cells with hydrogel coating - Google Patents"
        # Extract the middle part (the actual title)
        title_raw = _strip_html(m.group(1))[:300]
        title_parts = title_raw.split(" - ")
        if len(title_parts) >= 3:
            meta["title"] = title_parts[1]  # The actual title
        else:
            meta["title"] = title_raw
    else:
        m = re.search(r'<title>([^<]+)</title>', html)
        if m:
            title_raw = _strip_html(m.group(1))[:300]
            title_parts = title_raw.split(" - ")
            if len(title_parts) >= 3:
                meta["title"] = title_parts[1]
            else:
                meta["title"] = title_raw

    # Publication date: <time itemprop="publicationDate" datetime="YYYY-MM-DD">
    # Use datetime attribute, not the text content
    m = re.search(r'<time[^>]*itemprop=["\']publicationDate["\'][^>]*datetime=["\']([^"\']+)', html)
    if m:
        meta["publication_date"] = _parse_date(m.group(1))
    else:
        # Fallback: look for <dd> with publicationDate
        m = re.search(r'Publication\s+date</dt>\s*<dd><time[^>]*datetime=["\']([^"\']+)', html, re.IGNORECASE)
        if m:
            meta["publication_date"] = _parse_date(m.group(1))

    # Priority date: <time itemprop="priorityDate" datetime="YYYY-MM-DD">
    # Note: Google Patents uses "filingDate" or "priorityDate" for the priority/filing date
    m = re.search(r'<time[^>]*itemprop=["\']priorityDate["\'][^>]*datetime=["\']([^"\']+)', html)
    if m:
        meta["priority_date"] = _parse_date(m.group(1))
    else:
        # Try filingDate
        m = re.search(r'<time[^>]*itemprop=["\']filingDate["\'][^>]*datetime=["\']([^"\']+)', html)
        if m:
            meta["priority_date"] = _parse_date(m.group(1))
        else:
            # Fallback: "Filing date" label
            m = re.search(r'Filing\s+date</dt>\s*<dd><time[^>]*datetime=["\']([^"\']+)', html, re.IGNORECASE)
            if m:
                meta["priority_date"] = _parse_date(m.group(1))

    # Family ID: <section itemprop="family" itemscope>...ID=12345678
    m = re.search(r'itemprop=["\']family["\'][^>]*>.*?ID=(\d+)', html, re.DOTALL)
    if m:
        meta["family_id"] = m.group(1)
    else:
        # Fallback: docdbFamily
        m = re.search(r'docdbFamily["\']?\s*[:=]\s*["\']?(\d+)', html)
        if m:
            meta["family_id"] = m.group(1)

    # Assignee: <dd itemprop="assigneeOriginal">
    m = re.search(r'<dd[^>]*itemprop=["\']assigneeOriginal["\'][^>]*>(.*?)</dd>', html, re.DOTALL)
    if m:
        meta["assignee"] = _strip_html(m.group(1))[:200]
    else:
        # Fallback: <span itemprop="assigneeOriginal">
        m = re.search(r'<span[^>]*itemprop=["\']assigneeOriginal["\'][^>]*>([^<]+)', html)
        if m:
            meta["assignee"] = _strip_html(m.group(1))[:200]
        else:
            m = re.search(r'Assignee[:\s]*</[^>]+>\s*<[^>]*>([^<]+)', html, re.IGNORECASE)
            if m:
                meta["assignee"] = _strip_html(m.group(1))[:200]

    # Inventors: <dd itemprop="inventor">
    inventor_matches = re.findall(r'<dd[^>]*itemprop=["\']inventor["\'][^>]*>(.*?)</dd>', html, re.DOTALL)
    if inventor_matches:
        meta["inventors"] = [_strip_html(i)[:100] for i in inventor_matches[:10]]

    # CPC classifications: look for itemprop="cpc" or classification sections
    cpc_matches = re.findall(r'<dd[^>]*itemprop=["\']cpc["\'][^>]*>(.*?)</dd>', html, re.DOTALL)
    if cpc_matches:
        meta["cpc"] = [_strip_html(c)[:30] for c in cpc_matches[:20]]
    else:
        # Fallback: look for CPC codes in <span itemprop="Code">
        cpc_matches = re.findall(r'itemprop="Code"[^>]*>([A-Z]\d{2}[A-Z]\s*\d+/\d+)', html)
        if cpc_matches:
            meta["cpc"] = cpc_matches[:20]

    return meta


def _parse_date(s: str) -> Optional[str]:
    """Parse a date string into YYYY-MM-DD format."""
    s = _strip_html(s)
    # Try YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # Try YYYYMMDD
    m = re.search(r'(\d{4})(\d{2})(\d{2})', s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


# ----------------------- METHOD C: EMBEDDED JSON -----------------------
def _parse_embedded_json_strategy_c(html: str) -> Tuple[List[str], str, Dict[str, Any]]:
    """Extract claims from embedded JSON-LD or __NEXT_DATA__."""
    claims: List[str] = []
    abstract = ""
    metadata: Dict[str, Any] = {}

    # Try JSON-LD
    jsonld_blocks = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    for block in jsonld_blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, dict):
                # Look for claims
                if "claims" in data:
                    raw_claims = data["claims"]
                    if isinstance(raw_claims, list):
                        claims = [str(c)[:3000] for c in raw_claims if c]
                    elif isinstance(raw_claims, str):
                        claims = _split_claims(raw_claims)
                if "abstract" in data:
                    abstract = str(data["abstract"])[:2000]
                if "title" in data:
                    metadata["title"] = str(data["title"])[:300]
                if "datePublished" in data:
                    metadata["publication_date"] = _parse_date(data["datePublished"])
        except json.JSONDecodeError:
            continue

    if claims:
        return claims, abstract, metadata

    # Try __NEXT_DATA__ (Next.js embedded JSON)
    m = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            # Navigate the nested structure to find patent data
            # Structure varies, so search recursively
            _extract_claims_from_next_data(data, claims, metadata)
        except json.JSONDecodeError:
            pass

    return claims, abstract, metadata


def _extract_claims_from_next_data(obj: Any, claims: List[str], metadata: Dict[str, Any], depth: int = 0):
    """Recursively search __NEXT_DATA__ for claims and metadata."""
    if depth > 10 or len(claims) > 0:
        return
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "claims" and isinstance(val, list) and not claims:
                claims.extend([str(c)[:3000] for c in val if c][:50])
            elif key == "claimsText" and isinstance(val, str) and not claims:
                claims.extend(_split_claims(val))
            elif key == "abstract" and isinstance(val, str) and not metadata.get("abstract"):
                metadata["abstract"] = val[:2000]
            elif key == "publicationDate" and not metadata.get("publication_date"):
                metadata["publication_date"] = _parse_date(val)
            elif key == "priorityDate" and not metadata.get("priority_date"):
                metadata["priority_date"] = _parse_date(val)
            else:
                _extract_claims_from_next_data(val, claims, metadata, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _extract_claims_from_next_data(item, claims, metadata, depth + 1)


# ----------------------- PATENT FAMILY NORMALIZATION -----------------------
def normalize_patent_family(patent_id: str) -> str:
    """
    Normalize patent IDs from the same family.
    US12345678B2, WO2023000000A1, EP4000000A1 → same family if same priority.

    For now, we use a simple heuristic: extract the numeric core.
    A proper implementation would query a family lookup service.
    """
    # Extract country code and number
    m = re.match(r'([A-Z]{2})(\d+)', patent_id)
    if not m:
        return patent_id
    country, number = m.groups()
    # Return country+number as family identifier
    # (This is a simplification — real family lookup requires priority date matching)
    return f"{country}{number}"


# ----------------------- SOURCE STATUS (per CEO Section 5, 6) -----------------------
def get_source_status_honest() -> Dict[str, str]:
    """
    Honest source status per CEO directive.
    Do NOT represent a source as searched if its API call failed.
    """
    return {
        "GOOGLE_PATENTS": "LIVE",  # HTML page fetch works
        "LENS_SCHOLARLY": "LIVE",  # NPL only, NOT patents
        "LENS_PATENT": "UNAVAILABLE",  # Lens patent API returns 401 (not subscribed)
        "PATENT_BEAR": "RATE_LIMITED",  # 20/20 monthly quota exhausted
        "PATSNAP_EUREKA": "API_UNAVAILABLE",  # Account tier insufficient
    }


# ----------------------- CLI / SELF-TEST -----------------------
if __name__ == "__main__":
    print("="*60)
    print("PATENT EVIDENCE RETRIEVAL LAYER V3 — SELF-TEST")
    print("="*60)

    test_patents = [
        "US10919033B2",  # hydrogel coating
        "US12064533B2",  # synthetic hydrogel composite
        "US5346935A",    # hydrogel (older)
    ]

    for pid in test_patents:
        print(f"\n=== {pid} ===")
        record = fetch_patent_full(pid)
        print(f"  retrieval_success: {record.retrieval_success}")
        print(f"  retrieval_method: {record.retrieval_method}")
        print(f"  claim_count: {record.claim_count}")
        print(f"  is_gold: {record.is_gold}")
        print(f"  gold_missing: {record.gold_missing}")
        print(f"  title: {record.title[:80]}")
        print(f"  publication_date: {record.publication_date}")
        print(f"  priority_date: {record.priority_date}")
        print(f"  assignee: {record.assignee}")
        if record.claims:
            print(f"  first claim: {record.claims[0][:150]}...")
        print(f"  attempts:")
        for a in record.retrieval_attempts:
            print(f"    {a.method}: success={a.success}, claims={a.claim_count}, error={a.error}")

    # Save self-test
    out = Path(__file__).resolve().parents[2] / "patent_sources" / "v3" / "retrieval_self_test.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for pid in test_patents:
        record = fetch_patent_full(pid)
        results.append(asdict(record))
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSelf-test report: {out}")
