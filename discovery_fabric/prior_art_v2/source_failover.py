"""
Source-Independent Patent Evidence Failover
============================================

Per CEO directive: build a source-independent evidence failover path so
the rescue loop can continue when one patent provider is down.

SOURCE HIERARCHY (per CEO Section 1):
  1. Lens Patent API (POST /patent/search)
  2. PatSnap / Eureka Open Platform
  3. Google Patents (xhr + deep-fetch)
  4. Patent Bear (MCP)

Scholarly sources are SEPARATE and cannot satisfy patent-evidence requirements.

SOURCE-INDEPENDENT GOLD (per CEO Section 5):
  GOLD_PATENT_EVIDENCE = DIRECTLY_RELEVANT + actual claim text +
  verified patent identifier + priority date + publication date +
  family + source hash

  The source can be: Lens Patent OR PatSnap OR Google Patents OR Patent Bear.

STATUS VALUES:
  GOOGLE_PATENTS_TEMPORARILY_UNAVAILABLE
  LENS_PATENT_UNAVAILABLE
  PATSNAP_SEARCH_COUNT_AVAILABLE (count only, no claims)
  PATSNAP_API_UNAVAILABLE
  PATENT_BEAR_RATE_LIMITED
  CROSS_SOURCE_CONFIRMED
  SINGLE_SOURCE
  SOURCE_CONFLICT
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re, ssl, urllib.request, urllib.error
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.sources import (
    search_google_patents, search_lens_scholarly,
    search_patent_bear, _now_utc, _sha256,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import fetch_patent_full


# ----------------------- SOURCE STATUS -----------------------
@dataclass
class SourceStatus:
    """Status of one patent source."""
    source_id: str
    status: str  # AVAILABLE / TEMPORARILY_UNAVAILABLE / UNAVAILABLE / RATE_LIMITED / SEARCH_COUNT_ONLY
    http_status: int = 0
    error: str = ""
    can_retrieve_claims: bool = False
    can_search: bool = False
    checked_at: str = ""


def check_all_sources() -> List[SourceStatus]:
    """Check all patent sources and return their status."""
    statuses = []

    # 1. Google Patents
    gp_status = _check_google_patents()
    statuses.append(gp_status)

    # 2. Lens Patent API
    lens_status = _check_lens_patent()
    statuses.append(lens_status)

    # 3. PatSnap
    ps_status = _check_patsnap()
    statuses.append(ps_status)

    # 4. Patent Bear
    pb_status = _check_patent_bear()
    statuses.append(pb_status)

    return statuses


def _check_google_patents() -> SourceStatus:
    """Check Google Patents availability."""
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        url = "https://patents.google.com/xhr/query?url=q%3Dtest%26num%3D1&exp="
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return SourceStatus(
            source_id="GOOGLE_PATENTS",
            status="AVAILABLE",
            http_status=resp.status,
            can_retrieve_claims=True,
            can_search=True,
            checked_at=_now_utc(),
        )
    except urllib.error.HTTPError as e:
        if e.code == 503:
            return SourceStatus(
                source_id="GOOGLE_PATENTS",
                status="TEMPORARILY_UNAVAILABLE",
                http_status=503,
                error="HTTP 503 — service temporarily unavailable",
                can_retrieve_claims=False,
                can_search=False,
                checked_at=_now_utc(),
            )
        return SourceStatus(
            source_id="GOOGLE_PATENTS", status="UNAVAILABLE",
            http_status=e.code, error=str(e),
            checked_at=_now_utc(),
        )
    except Exception as e:
        return SourceStatus(
            source_id="GOOGLE_PATENTS", status="UNAVAILABLE",
            error=str(e)[:100], checked_at=_now_utc(),
        )


def _check_lens_patent() -> SourceStatus:
    """Check Lens Patent API (not scholarly)."""
    from pathlib import Path
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    token = ""
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("LENS_API_TOKEN="):
                token = line.split("=", 1)[1].strip()
                break
    if not token:
        return SourceStatus(source_id="LENS_PATENT", status="NO_TOKEN", checked_at=_now_utc())

    import urllib.request, ssl, json
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        url = "https://api.lens.org/patent/search"
        payload = json.dumps({
            "query": {"bool": {"must": [{"match": {"title": "test"}}]}},
            "size": 1,
        }).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return SourceStatus(
            source_id="LENS_PATENT", status="AVAILABLE",
            http_status=resp.status, can_search=True, can_retrieve_claims=True,
            checked_at=_now_utc(),
        )
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return SourceStatus(
                source_id="LENS_PATENT", status="UNAVAILABLE",
                http_status=401, error="Authentication failed — token for scholarly only",
                checked_at=_now_utc(),
            )
        return SourceStatus(
            source_id="LENS_PATENT", status="UNAVAILABLE",
            http_status=e.code, error=str(e), checked_at=_now_utc(),
        )
    except Exception as e:
        return SourceStatus(
            source_id="LENS_PATENT", status="UNAVAILABLE",
            error=str(e)[:100], checked_at=_now_utc(),
        )


def _check_patsnap() -> SourceStatus:
    """Check PatSnap search-count endpoint."""
    from pathlib import Path
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    key = ""
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("PATSNAP_EUREKA_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        return SourceStatus(source_id="PATSNAP", status="NO_KEY", checked_at=_now_utc())

    import urllib.request, ssl, json
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        url = "https://connect.patsnap.com/search/patent/query-search-count/v2"
        payload = json.dumps({
            "query_text": "TACD: test",
            "collapse_by": "PBD",
            "collapse_type": "ALL",
            "collapse_order": "LATEST",
        }).encode()
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = json.loads(resp.read())
        if data.get("status"):
            return SourceStatus(
                source_id="PATSNAP", status="SEARCH_COUNT_ONLY",
                http_status=200, can_search=True, can_retrieve_claims=False,
                error="Search count works but full search + claims need API tier",
                checked_at=_now_utc(),
            )
        else:
            return SourceStatus(
                source_id="PATSNAP", status="UNAVAILABLE",
                http_status=200, error=data.get("error_msg", ""),
                checked_at=_now_utc(),
            )
    except Exception as e:
        return SourceStatus(
            source_id="PATSNAP", status="UNAVAILABLE",
            error=str(e)[:100], checked_at=_now_utc(),
        )


def _check_patent_bear() -> SourceStatus:
    """Check Patent Bear MCP quota."""
    from pathlib import Path
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    key = ""
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("PATENT_BEAR_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        return SourceStatus(source_id="PATENT_BEAR", status="NO_KEY", checked_at=_now_utc())

    result = search_patent_bear("test", 1)
    if result.success:
        return SourceStatus(
            source_id="PATENT_BEAR", status="AVAILABLE",
            can_search=True, can_retrieve_claims=True,
            checked_at=_now_utc(),
        )
    elif result.error and "rate" in result.error.lower():
        return SourceStatus(
            source_id="PATENT_BEAR", status="RATE_LIMITED",
            error=result.error, can_search=False, can_retrieve_claims=False,
            checked_at=_now_utc(),
        )
    else:
        return SourceStatus(
            source_id="PATENT_BEAR", status="UNAVAILABLE",
            error=result.error or "Unknown error",
            checked_at=_now_utc(),
        )


# ----------------------- PATSNAP SEARCH COUNT -----------------------
def patsnap_search_count(query: str) -> Optional[int]:
    """Search PatSnap for patent count (works with current key tier)."""
    from pathlib import Path
    keys_file = Path(__file__).resolve().parents[2] / ".env.keys"
    key = ""
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            if line.startswith("PATSNAP_EUREKA_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        return None

    import urllib.request, ssl, json
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = "https://connect.patsnap.com/search/patent/query-search-count/v2"
    # Use TACD: prefix for Title, Abstract, Claims, Description search
    query_text = f"TACD: {query[:2900]}"  # max 3000 chars
    payload = json.dumps({
        "query_text": query_text,
        "collapse_by": "PBD",
        "collapse_type": "ALL",
        "collapse_order": "LATEST",
    }).encode()

    try:
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read())
        if data.get("status"):
            return data.get("data", {}).get("total_search_result_count", 0)
    except Exception:
        pass
    return None


# ----------------------- MULTI-SOURCE RETRIEVAL -----------------------
@dataclass
class MultiSourceResult:
    """Result from multi-source patent retrieval."""
    query: str
    source_statuses: List[Dict[str, Any]] = field(default_factory=list)
    google_patents_hits: List[Dict[str, Any]] = field(default_factory=list)
    lens_scholarly_hits: List[Dict[str, Any]] = field(default_factory=list)
    patsnap_count: Optional[int] = None
    patent_bear_hits: List[Dict[str, Any]] = field(default_factory=list)
    gold_patents: List[Dict[str, Any]] = field(default_factory=list)
    cross_source_confirmed: List[str] = field(default_factory=list)
    single_source: List[str] = field(default_factory=list)
    source_conflicts: List[Dict[str, Any]] = field(default_factory=list)


def multi_source_search(query: str, num_per_source: int = 5) -> MultiSourceResult:
    """
    Search all available patent sources with failover.
    Records source status and cross-source confirmation.
    """
    result = MultiSourceResult(query=query)

    # Check all sources
    statuses = check_all_sources()
    result.source_statuses = [asdict(s) for s in statuses]

    # Try Google Patents (if available)
    gp_status = next((s for s in statuses if s.source_id == "GOOGLE_PATENTS"), None)
    if gp_status and gp_status.can_search:
        gp_result = search_google_patents(query, num_per_source)
        if gp_result.success:
            for h in gp_result.hits:
                hit = asdict(h)
                hit["source_id"] = "GOOGLE_PATENTS"
                result.google_patents_hits.append(hit)

    # Try Lens Scholarly (NPL — separate from patent)
    lens_result = search_lens_scholarly(query, num_per_source)
    if lens_result.success:
        for h in lens_result.hits:
            hit = asdict(h)
            hit["source_id"] = "LENS_SCHOLARLY"
            result.lens_scholarly_hits.append(hit)

    # Try PatSnap search-count (count only)
    ps_count = patsnap_search_count(query)
    if ps_count is not None:
        result.patsnap_count = ps_count

    # Try Patent Bear (if quota available)
    pb_status = next((s for s in statuses if s.source_id == "PATENT_BEAR"), None)
    if pb_status and pb_status.can_search:
        pb_result = search_patent_bear(query, num_per_source)
        if pb_result.success:
            for h in pb_result.hits:
                hit = asdict(h)
                hit["source_id"] = "PATENT_BEAR"
                result.patent_bear_hits.append(hit)

    # Deep-fetch GOLD from Google Patents hits
    all_patent_hits = result.google_patents_hits + result.patent_bear_hits
    for h in all_patent_hits[:5]:
        pid = h.get("patent_id")
        if not pid:
            continue
        record = fetch_patent_full(pid)
        if record.is_gold and record.claims:
            gold = {
                "patent_id": pid,
                "title": record.title,
                "claims": record.claims,
                "publication_date": record.publication_date,
                "priority_date": record.priority_date,
                "family_id": record.family_id,
                "source_url": record.source_url,
                "source_hash": record.full_content_hash,
                "retrieved_at_utc": _now_utc(),
                "source_id": h.get("source_id", "GOOGLE_PATENTS"),
                "is_gold": True,
            }
            result.gold_patents.append(gold)

    # Cross-source confirmation
    all_pids = {}
    for h in result.google_patents_hits:
        pid = h.get("patent_id")
        if pid:
            all_pids.setdefault(pid, []).append("GOOGLE_PATENTS")
    for h in result.patent_bear_hits:
        pid = h.get("patent_id")
        if pid:
            all_pids.setdefault(pid, []).append("PATENT_BEAR")

    for pid, sources in all_pids.items():
        if len(set(sources)) > 1:
            result.cross_source_confirmed.append(pid)
        else:
            result.single_source.append(pid)

    return result
