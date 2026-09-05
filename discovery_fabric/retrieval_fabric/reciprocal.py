"""Reciprocal discovery — citation, author, and recommendation expansion.

Directive section 6: for every high-value seed, expand
  citation: seed -> references -> citing papers -> related papers
  author:   seed -> author works
  recommendation: seed -> S2 recommended papers

All expansion goes through REAL provider endpoints (Semantic Scholar
academic graph). Budgeted (the unauthenticated tier measured RATE_LIMITED
429 live 2026-09-05); every outcome is recorded honestly. The expanded
records are ADAPTER RESULTS (never LLM-fabricated) and are labeled with
their expansion derivation for provenance.
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    STATUS_OK, STATUS_RATE_LIMITED, STATUS_SEARCH_FAILED, STATUS_TIMEOUT,
    STATUS_UNAVAILABLE, utc_now, sha256_bytes,
)

_SSL = ssl.create_default_context()

_S2_GRAPH = "https://api.semanticscholar.org/graph/v1"
_S2_REC = "https://api.semanticscholar.org/recommendations/v1"

# Budget discipline: the unauthenticated S2 pool is shared and burst-
# limited (429 measured live). The fabric makes at most this many S2
# reciprocal calls per run, with spacing, and records every 429.
MAX_S2_CALLS_PER_RUN = 4
_S2_SPACING_SECONDS = 1.5


def _s2_headers() -> Dict[str, str]:
    from discovery_fabric.source_registry.keys import load_key
    key = load_key("S2_API_KEY")
    h = {"User-Agent": "retrieval-fabric/2.0",
         "Accept": "application/json"}
    if key:
        h["x-api-key"] = key
    return h


def _s2_get(url: str, timeout: int = 25) -> Dict[str, Any]:
    """One S2 GET with honest status mapping + retrieval-log custody."""
    from discovery_fabric.source_registry.retrieval_log import append_entry
    t0 = time.time()
    status, body, http_status, error = STATUS_SEARCH_FAILED, None, None, None
    try:
        req = urllib.request.Request(url, headers=_s2_headers())
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
        body = resp.read()
        status, http_status = STATUS_OK, resp.status
    except urllib.error.HTTPError as e:
        http_status = e.code
        if e.code == 429:
            status = STATUS_RATE_LIMITED
        elif e.code in (401, 403):
            status = "AUTH_FAILED"
        elif e.code == 404:
            status = "EMPTY"
        else:
            status = STATUS_UNAVAILABLE
        error = f"HTTP {e.code}"
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        status = (STATUS_TIMEOUT if "timed out" in error.lower()
                  else STATUS_SEARCH_FAILED)
    latency = int((time.time() - t0) * 1000)
    raw_sha = sha256_bytes(body) if body is not None else None
    append_entry(source_id="semantic_scholar", query=url.split("?")[0][-80:],
                 url=url, status=status, http_status=http_status,
                 latency_ms=latency,
                 record_count=(len(json.loads(body).get("data", []))
                               if status == STATUS_OK and body else 0),
                 raw_payload_sha256=raw_sha, error=error,
                 retrieval_role="RECIPROCAL")
    data = None
    if status == STATUS_OK and body is not None:
        try:
            data = json.loads(body)
        except Exception:  # noqa: BLE001
            status = "PARSE_FAILED"
    return {"status": status, "data": data, "http_status": http_status,
            "error": error, "latency_ms": latency,
            "raw_payload_sha256": raw_sha}


def _paper_fields() -> str:
    return ("title,year,externalIds,citationCount,publicationTypes,abstract,"
            "venue,authors")


def _to_record(paper: Dict[str, Any], query: str, expansion: str,
               raw_sha: str) -> Dict[str, Any]:
    ext = paper.get("externalIds") or {}
    authors = [a.get("name") for a in (paper.get("authors") or [])][:20]
    return {
        "record_id": f"s2:{paper.get('paperId')}",
        "paper_id": paper.get("paperId"),
        "doi": ext.get("DOI"),
        "pmid": ext.get("PubMed"),
        "arxiv_id": ext.get("ArXiv"),
        "title": paper.get("title") or "",
        "publication_year": paper.get("year"),
        "citation_count": paper.get("citationCount"),
        "publication_types": paper.get("publicationTypes") or [],
        "abstract": (paper.get("abstract") or "")[:4000] or None,
        "authors": authors,
        "venue": paper.get("venue"),
        "expansion_derivation": expansion,
        "query": query,
        "raw_payload_sha256": raw_sha,
    }


def expand_citations(seed_paper_id: str, limit: int = 5) -> Dict[str, Any]:
    """seed -> papers that CITE the seed."""
    url = (f"{_S2_GRAPH}/paper/{urllib.parse.quote(seed_paper_id)}/citations"
           f"?limit={limit}&fields={_paper_fields()}")
    r = _s2_get(url)
    records = []
    if r["status"] == STATUS_OK and r.get("data"):
        for item in (r["data"].get("data") or []):
            cp = item.get("citingPaper") or {}
            records.append(_to_record(cp, seed_paper_id, "CITATION_EXPANSION",
                                      r["raw_payload_sha256"] or ""))
    return {**r, "records": records, "expansion": "citations"}


def expand_references(seed_paper_id: str, limit: int = 5) -> Dict[str, Any]:
    """seed -> papers the seed CITES."""
    url = (f"{_S2_GRAPH}/paper/{urllib.parse.quote(seed_paper_id)}/references"
           f"?limit={limit}&fields={_paper_fields()}")
    r = _s2_get(url)
    records = []
    if r["status"] == STATUS_OK and r.get("data"):
        for item in (r["data"].get("data") or []):
            rp = item.get("citedPaper") or {}
            records.append(_to_record(rp, seed_paper_id, "REFERENCE_EXPANSION",
                                      r["raw_payload_sha256"] or ""))
    return {**r, "records": records, "expansion": "references"}


def expand_recommendations(seed_paper_id: str, limit: int = 5) -> Dict[str, Any]:
    """seed -> S2's related-paper recommendations."""
    url = (f"{_S2_REC}/papers/forpaper/{urllib.parse.quote(seed_paper_id)}"
           f"?limit={limit}&fields={_paper_fields()}")
    r = _s2_get(url)
    records = []
    if r["status"] == STATUS_OK and r.get("data"):
        for p in (r["data"].get("recommendedPapers") or []):
            records.append(_to_record(p, seed_paper_id, "RECOMMENDATION",
                                      r["raw_payload_sha256"] or ""))
    return {**r, "records": records, "expansion": "recommendations"}


def expand_author_works(author_name: str, limit: int = 5) -> Dict[str, Any]:
    """author name -> author search -> recent works (author works lane)."""
    # step 1: author search
    url = (f"{_S2_GRAPH}/author/search?query={urllib.parse.quote(author_name)}"
           f"&limit=1")
    r = _s2_get(url)
    if r["status"] != STATUS_OK or not r.get("data"):
        return {**r, "records": [], "expansion": "author_works"}
    authors = r["data"].get("data") or []
    if not authors:
        return {**r, "records": [], "expansion": "author_works"}
    author_id = authors[0].get("authorId")
    if not author_id:
        return {**r, "records": [], "expansion": "author_works"}
    time.sleep(_S2_SPACING_SECONDS)
    # step 2: author's papers
    url2 = (f"{_S2_GRAPH}/author/{author_id}/papers"
            f"?limit={limit}&fields={_paper_fields()}")
    r2 = _s2_get(url2)
    records = []
    if r2["status"] == STATUS_OK and r2.get("data"):
        for p in (r2["data"].get("data") or []):
            records.append(_to_record(p, author_name, "AUTHOR_WORKS",
                                      r2["raw_payload_sha256"] or ""))
    return {**r2, "records": records, "expansion": "author_works",
            "author_id": author_id, "author_search_status": r["status"]}


class ReciprocalBudget:
    """Tracks S2 call budget for one run (bounded, honest)."""

    def __init__(self, max_calls: int = MAX_S2_CALLS_PER_RUN) -> None:
        self.max_calls = max_calls
        self.calls_used = 0

    def can_call(self) -> bool:
        return self.calls_used < self.max_calls

    def record_call(self) -> None:
        self.calls_used += 1
        time.sleep(_S2_SPACING_SECONDS)


def reciprocal_expansion(seed_paper_id: str,
                         author_names: Optional[List[str]] = None,
                         budget: Optional[ReciprocalBudget] = None) -> Dict[str, Any]:
    """Run bounded reciprocal expansion for one high-value seed.
    Returns {records, calls: [...], budget_exhausted: bool} — every call
    outcome recorded (Art. XXI.3), never silently skipped."""
    budget = budget or ReciprocalBudget()
    calls: List[Dict[str, Any]] = []
    records: List[Dict[str, Any]] = []
    # 1. references (what the seed builds on)
    if budget.can_call():
        budget.record_call()
        r = expand_references(seed_paper_id)
        calls.append({k: r[k] for k in ("status", "expansion", "error",
                                        "latency_ms")})
        records.extend(r["records"])
    else:
        calls.append({"expansion": "references",
                      "status": "SKIPPED_BUDGET_EXHAUSTED"})
    # 2. citations (who builds on the seed)
    if budget.can_call():
        budget.record_call()
        r = expand_citations(seed_paper_id)
        calls.append({k: r[k] for k in ("status", "expansion", "error",
                                        "latency_ms")})
        records.extend(r["records"])
    else:
        calls.append({"expansion": "citations",
                      "status": "SKIPPED_BUDGET_EXHAUSTED"})
    # 3. recommendations (related papers)
    if budget.can_call():
        budget.record_call()
        r = expand_recommendations(seed_paper_id)
        calls.append({k: r[k] for k in ("status", "expansion", "error",
                                        "latency_ms")})
        records.extend(r["records"])
    else:
        calls.append({"expansion": "recommendations",
                      "status": "SKIPPED_BUDGET_EXHAUSTED"})
    # 4. author works (first seed author)
    if author_names and budget.can_call():
        budget.record_call()
        r = expand_author_works(author_names[0])
        calls.append({k: r[k] for k in ("status", "expansion", "error",
                                        "latency_ms")})
        records.extend(r["records"])
    return {
        "seed_paper_id": seed_paper_id,
        "records": records,
        "calls": calls,
        "budget": {"max": budget.max_calls, "used": budget.calls_used},
        "retrieved_at": utc_now(),
    }
