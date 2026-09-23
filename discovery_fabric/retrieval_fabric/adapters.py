"""Fabric lane adapters — the multi-channel execution layer.

Directive section 4: every meaningful query fans out across channels:

    Discovery Query
          |
    Query Expansion / Mechanism Terms
          |
    Literature | Open-access | Preprints | Theses | Technical reports |
    Patents | Citation graphs | Repositories | Cross-domain sources
          |
    Canonical Record Resolution -> Dedup -> Source-Lineage Attribution
          -> Evidence Classification -> (per-lane) Relevance -> Ranking

Every source call goes through the registry ConnectorBase 7-step chain
(query -> live request -> parse -> normalize -> provenance -> retrieval
log -> health), so provider failures surface as explicit states (Art.
XXI.3) and every record carries source-level provenance (Art. XXI.9).
No lane may synthesize a record: records come ONLY from connector
results (LLM may propose queries, never records — test-enforced).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, SourceQueryResult,
)
from discovery_fabric.retrieval_fabric.canonical import Canonicalizer, CanonicalRecord
from discovery_fabric.retrieval_fabric.fabric_registry import (
    get_fabric_source, source_family,
)
from discovery_fabric.retrieval_fabric.publication_status import (
    label_publication_status, lane_for_publication_status,
)


# ---------------------------------------------------------------------------
# Lane-specific connector subclasses (type-scoped queries)
# ---------------------------------------------------------------------------

class CrossrefThesisConnector(
    __import__("discovery_fabric.source_registry.connectors.scientific",
               fromlist=["CrossrefConnector"]).CrossrefConnector):
    """Crossref scoped to dissertations (server-side filter, measured
    live 2026-09-05: filter=type:dissertation answers 200)."""

    def build_url(self, query: str) -> str:
        import urllib.parse
        q = urllib.parse.quote(query)
        return (f"https://api.crossref.org/works?query={q}"
                f"&rows={self.LIMIT}&select=DOI,title,container-title,"
                f"issued,type,publisher&filter=type:dissertation")


class DataciteThesisConnector(
    __import__("discovery_fabric.source_registry.connectors.open_discovery",
               fromlist=["DataciteConnector"]).DataciteConnector):
    """DataCite scoped to Dissertation resource type (server-side filter,
    measured live 2026-09-05)."""

    RESOURCE_TYPE_FILTER: Optional[str] = "Dissertation"


class OpenalexKeywordConnector(
    __import__("discovery_fabric.source_registry.connectors.scientific",
               fromlist=["OpenAlexConnector"]).OpenAlexConnector):
    """OpenAlex with the keyword-form query (no 'mechanism' suffix — the
    collision-measured meta-word defect, same discipline as the V1
    OpenAlex lane)."""
    LIMIT = 5


def _connector_for(source_id: str,
                   scoped: Optional[str] = None) -> Optional[ConnectorBase]:
    """Instantiate the fabric's connector for a source, honoring the
    registry wiring (the 7-step chain). Scoped connectors are used for
    type-filtered lane queries (thesis lane)."""
    from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
    rec = SOURCE_REGISTRY.get(source_id)
    if not rec or not rec.get("connector"):
        return None
    if scoped == "THESIS":
        if source_id == "crossref":
            return CrossrefThesisConnector()
        if source_id == "datacite":
            return DataciteThesisConnector()
    # dynamic import of the declared connector class
    path = rec["connector"]
    module_path, cls_name = path.split(":")
    import importlib
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, cls_name)
        return cls()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Patent lane — search + claim-level fetch with custody
# ---------------------------------------------------------------------------

@dataclass
class PatentClaimFetch:
    patent_id: str
    ok: bool
    claim_count: Optional[int] = None
    abstract_len: Optional[int] = None
    claims_excerpt: str = ""
    raw_payload_sha256: str = ""
    error: Optional[str] = None


def fetch_patent_claims_custoied(patent_id: str,
                                 retries: int = 1) -> PatentClaimFetch:
    """Claim-level retrieval for one patent: Google Patents page fetch
    (full text, not title) with an append-only retrieval-log entry
    (custody, Art. XXI.9). The search snippet is NEVER presented as
    claim text. 503/429 answers get one bounded retry with backoff
    (measured 2026-09-05: the page endpoint throttles bursts from this
    egress with Google 'Sorry...' 503 pages — TEMPORARILY_UNAVAILABLE,
    recorded honestly, never absence)."""
    from discovery_fabric.source_registry.retrieval_log import append_entry
    from discovery_fabric.source_registry.base import (
        STATUS_OK, STATUS_SEARCH_FAILED, STATUS_TIMEOUT,
    )
    import time as _time
    result: Dict[str, Any] = {}
    for attempt in range(retries + 1):
        try:
            from discovery_fabric.prior_art_v2.sources import \
                fetch_google_patent_full_claims
            result = fetch_google_patent_full_claims(patent_id)
        except Exception as exc:  # noqa: BLE001 — surfaced honestly
            result = {"patent_id": patent_id,
                      "error": f"{type(exc).__name__}: {exc}"}
        if result.get("claims"):
            break
        # provider-side block (error field set by the adapter on HTTP!=200)
        if attempt < retries:
            _time.sleep(2.0 * (attempt + 1))
    ok = bool(result.get("claims"))
    provider_error = result.get("error")
    status = STATUS_OK if ok else STATUS_SEARCH_FAILED
    append_entry(source_id="google_patents",
                 query=f"claims:{patent_id}",
                 url=f"https://patents.google.com/patent/{patent_id}/en",
                 status=status,
                 http_status=(200 if ok else None),
                 latency_ms=result.get("latency_ms"),
                 record_count=len(result.get("claims") or []),
                 raw_payload_sha256=(result.get("raw_html_sha256")
                                     or result.get("raw_payload_sha256")),
                 error=None if ok else
                 (str(provider_error) or
                  "no claims parsed from patent page (endpoint may be "
                  "throttled — TEMPORARILY_UNAVAILABLE, not absence)"))
    claims = result.get("claims") or []
    excerpt = "\n".join(claims[:3])[:2000]
    return PatentClaimFetch(
        patent_id=patent_id, ok=ok,
        claim_count=len(claims),
        abstract_len=result.get("abstract_len")
        or len(result.get("abstract") or ""),
        claims_excerpt=excerpt,
        raw_payload_sha256=(result.get("raw_html_sha256")
                            or result.get("raw_payload_sha256") or ""),
        error=(None if ok else (str(provider_error) if provider_error
                                else "claims not parsed")))


def patent_record_from_hit(hit: Dict[str, Any], query: str,
                           claim_fetch: Optional[PatentClaimFetch] = None
                           ) -> Dict[str, Any]:
    """The directive's patent record schema — every patent result needs:
    document_type=PATENT, publication_number, jurisdiction, priority_date,
    filing_date, publication_date, inventors, applicants, family_id,
    claim_text_available, source_url. Unknown fields stay None (honest,
    Art. VI/XXV) — never fabricated."""
    pid = hit.get("patent_id") or ""
    country = (pid[:2] if len(pid) >= 2 else "")
    raw_meta = hit.get("raw_metadata") or {}
    return {
        "record_id": f"patent:{pid}",
        "patent_number": pid,
        "publication_number": pid,  # directive patent schema field name
        "document_type": "PATENT",
        "title": hit.get("title") or "",
        "jurisdiction": country or None,
        "priority_date": raw_meta.get("priority_date"),
        "filing_date": None,  # not exposed by the xhr endpoint — UNKNOWN
        "publication_date": raw_meta.get("publication_date")
        or hit.get("publication_date"),
        "inventors": [raw_meta.get("inventor")] if raw_meta.get("inventor") else [],
        "applicants": hit.get("assignee_or_authors") or [],
        "family_id": None,  # not exposed by the xhr endpoint — UNKNOWN
        "claim_text_available": bool(claim_fetch and claim_fetch.ok),
        "claims_excerpt": (claim_fetch.claims_excerpt if claim_fetch and
                           claim_fetch.ok else ""),
        "snippet": (hit.get("snippet") or "")[:400],
        "source_url": hit.get("source_url") or "",
        "query": query,
        "raw_record_sha256": hit.get("raw_payload_sha256") or "",
        "limitations": [
            "Patent search hit: NOT a claim-chart novelty determination "
            "(Art. XXVIII / Art. XXI.2)",
            "family_id and filing_date not exposed by the public search "
            "endpoint — recorded UNKNOWN, never fabricated",
            "Patent existence does not establish commercial practice or "
            "technical viability",
        ],
    }


# ---------------------------------------------------------------------------
# Per-run health bookkeeping (directive section 5)
# ---------------------------------------------------------------------------

@dataclass
class LaneRunState:
    lane: str
    source_id: str
    queries: List[str] = field(default_factory=list)
    status: str = "NOT_RUN"          # connector STATUS_* vocabulary
    fabric_health: str = "NOT_RUN"   # directive's health vocabulary
    record_count: int = 0
    latency_ms: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lane": self.lane,
            "source_id": self.source_id,
            "queries": self.queries,
            "status": self.status,
            "fabric_health": self.fabric_health,
            "record_count": self.record_count,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


STATUS_TO_FABRIC_HEALTH = {
    "OK": "AVAILABLE",
    "EMPTY": "EMPTY_RESULT",          # provider answered: zero records
    "TIMEOUT": "TIMEOUT",
    "SEARCH_FAILED": "TEMPORARILY_UNAVAILABLE",
    "AUTH_FAILED": "AUTH_REQUIRED",
    "RATE_LIMITED": "RATE_LIMITED",
    "UNAVAILABLE": "TEMPORARILY_UNAVAILABLE",
    "PARSE_FAILED": "DEGRADED",
    "NOT_IMPLEMENTED": "DEGRADED",
    "GRAMMAR_MISMATCH": "DEGRADED",
    "NO_QUERY_FORMED": "NOT_RUN",
    "NOT_RUN": "NOT_RUN",
    # R522: a centrally excluded source was never queried. This is an
    # operational routing state, never a provider health verdict
    # (Art. XXI.3 / LXI) — it maps to itself, not TEMPORARILY_UNAVAILABLE.
    "EXCLUDED": "EXCLUDED",
}


def fabric_health_of(status: str) -> str:
    return STATUS_TO_FABRIC_HEALTH.get(status, "TEMPORARILY_UNAVAILABLE")


def run_stats(lane_states: List[LaneRunState]) -> Dict[str, Any]:
    """Per-run retrieval stats (directive section 5): sources_attempted/
    succeeded/failed/rate_limited + queries_per_source +
    result_counts_per_source. 'No relevant result found' is epistemically
    distinct from 'the source could not be queried' — this record keeps
    them distinct.

    R522: an EXCLUDED source was never queried (centralized routing
    authority), so it is not 'attempted', not 'failed', not 'empty', and
    never contributes a result count — it is tracked in sources_excluded
    separately. Converting a routing decision into a provider outcome
    would manufacture a state that never happened (Art. XXI.3 / LXI)."""
    excluded_states = [s for s in lane_states if s.status == "EXCLUDED"]
    queried = [s for s in lane_states if s.status != "EXCLUDED"]
    attempted = [s for s in queried if s.status not in ("NOT_RUN",)]
    succeeded = [s for s in attempted if s.status in ("OK", "EMPTY")]
    failed = [s for s in attempted
              if s.status not in ("OK", "EMPTY", "RATE_LIMITED")]
    rate_limited = [s for s in attempted if s.status == "RATE_LIMITED"]
    return {
        "sources_attempted": sorted({s.source_id for s in attempted}),
        "sources_succeeded": sorted({s.source_id for s in succeeded}),
        "sources_failed": sorted({s.source_id for s in failed}),
        "sources_rate_limited": sorted({s.source_id for s in rate_limited}),
        "sources_empty": sorted({s.source_id for s in queried
                                 if s.status == "EMPTY"}),
        "sources_excluded": sorted({s.source_id for s in excluded_states}),
        "queries_per_source": {
            s.source_id: len(s.queries) for s in queried if s.queries},
        "result_counts_per_source": {
            s.source_id: s.record_count for s in queried},
        "lane_states": [s.to_dict() for s in lane_states],
    }
