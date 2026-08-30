"""Scientific literature connectors: PubMed (E-utilities), Europe PMC, Crossref,
OpenAlex, Semantic Scholar.

All follow the base-class failure discipline (Art. XXI.3) and provenance
custody (Art. XXI.9). The EuropePMC connector here is the REGISTRY-grade
implementation (explicit failure statuses); the a2 pipeline's own retrieval
(a2/retrieve.py) is deliberately untouched — its behavior is frozen pipeline
surface.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, utc_now,
)


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


class PubMedConnector(ConnectorBase):
    SOURCE_ID = "pubmed"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "pacemaker lead fracture"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                f"?db=pubmed&term={q}&retmode=json&retmax={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        result = (payload or {}).get("esearchresult") or {}
        if "error" in result:
            raise ValueError(f"pubmed error: {result['error']}")
        ids = result.get("idlist") or []
        # esearch returns ids only; titles fetched via esummary would double
        # requests. Record ids as records; enrichment is a separate call path.
        return [
            SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"pmid:{pid}",
                title=f"PubMed PMID {pid}",
                uri=f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "pmid": pid,
                    "total_count": result.get("count"),
                    "translation_set": None,  # not fetched
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "eutils.ncbi.nlm.nih.gov",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "esearch returns identifiers only; metadata requires a "
                    "second esummary/efetch call (not yet chained)",
                ],
            )
            for pid in ids
        ]


class EuropePmcConnector(ConnectorBase):
    SOURCE_ID = "europepmc"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "pacemaker lead fracture"
    LIMIT = 10

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return ("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                f"?query={q}&format=json&pageSize={self.LIMIT}&resultType=core")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        # 2026-08-30 defect fixed (found by the resolve-unavailable live
        # probe): EuropePMC answers a zero-hit query with hitCount=0 and NO
        # resultList.result key — a DEFINITIVE provider answer. The old
        # code raised ValueError here, misclassifying definitive empties as
        # PARSE_FAILED (Art. XXI.3: provider answer is not provider
        # failure; this exact bug caused a false UNAVAILABLE in the
        # 2026-08-29 health report).
        body = payload or {}
        result = body.get("resultList") or {}
        results = result.get("result")
        if results is None:
            if isinstance(body.get("hitCount"), int) and body.get("hitCount") == 0:
                return []  # definitive EMPTY: provider answered zero hits
            raise ValueError("europepmc payload missing resultList.result "
                             "and hitCount is not a definitive zero")
        if not isinstance(results, list):
            raise ValueError("europepmc resultList.result is not a list")
        out = []
        for r in results:
            abstract = _clean(r.get("abstractText", "") or "")
            rid = r.get("id") or r.get("pmid") or ""
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"europepmc:{rid}",
                title=r.get("title", "") or "",
                uri=f"https://europepmc.org/article/{r.get('source', 'MED')}/{rid}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "pmid": r.get("pmid"),
                    "pmcid": r.get("pmcid"),
                    "doi": r.get("doi"),
                    "title": r.get("title"),
                    "abstract": abstract[:4000] or None,
                    "pub_type": r.get("pubType"),
                    "publication_date": r.get("firstPublicationDate"),
                    "journal": r.get("journalTitle"),
                    "cited_by_count": r.get("citedByCount"),
                    "author_string": r.get("authorString"),
                    "is_open_access": (r.get("isOpenAccess") or "").lower() == "y",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.ebi.ac.uk/europepmc/webservices/rest",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Abstract-level evidence: full text may contain methods "
                    "and constraints not present in the abstract",
                    "Publication existence is not clinical evidence of "
                    "safety or effectiveness",
                    "Citation counts are bibliometric signals, not "
                    "validity measures",
                ],
            ))
        return out


class CrossrefConnector(ConnectorBase):
    SOURCE_ID = "crossref"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "pacemaker lead fracture"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://api.crossref.org/works?query={q}"
                f"&rows={self.LIMIT}&select=DOI,title,container-title,issued,type,publisher")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        msg = (payload or {}).get("message") or {}
        items = msg.get("items")
        if not isinstance(items, list):
            raise ValueError("crossref payload missing message.items")
        out = []
        for r in items:
            doi = r.get("DOI") or ""
            title = (r.get("title") or [""])[0]
            issued = ((r.get("issued") or {}).get("date-parts") or [[None]])[0]
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"doi:{doi}",
                title=title,
                uri=f"https://doi.org/{doi}" if doi else "https://api.crossref.org/works",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "doi": doi,
                    "title": title,
                    "container_title": (r.get("container-title") or [None])[0],
                    "type": r.get("type"),
                    "publisher": r.get("publisher"),
                    "issued_year": issued[0] if issued else None,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.crossref.org",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=["Metadata-only; no abstracts for many records"],
            ))
        return out


class OpenAlexConnector(ConnectorBase):
    SOURCE_ID = "openalex"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "pacemaker lead fracture"
    LIMIT = 5
    # 2026-08-30: budget-window recovery. OpenAlex's 2025+ credit system
    # measured 'Insufficient budget ... $0 remaining' from this egress;
    # a registered contact email (polite pool) earns a higher free daily
    # budget. OPENALEX_EMAIL in .env.keys switches us onto it the day it
    # is provisioned; the placeholder keeps today's behavior.
    BACKOFF_BASE_SECONDS = 5.0

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        from discovery_fabric.source_registry.keys import load_key
        email = load_key("OPENALEX_EMAIL") or "discovery-fabric@example.org"
        return (f"https://api.openalex.org/works?search={q}&per-page={self.LIMIT}"
                f"&mailto={urllib.parse.quote(email)}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        results = (payload or {}).get("results")
        if not isinstance(results, list):
            raise ValueError("openalex payload missing results list")
        from discovery_fabric.connectors.openalex.mapper import openalex_work_to_evidence_item
        out = []
        for w in results:
            item = openalex_work_to_evidence_item(w, retrieval_method="source_registry_health")
            oid = item["id"]
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=oid,
                title=item.get("title") or "",
                uri=item.get("source_uri") or "https://api.openalex.org/works",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "openalex_id": oid,
                    "doi": item.get("source_specific", {}).get("doi"),
                    "publication_year": item.get("publication_year") or (item.get("source_specific") or {}).get("publication_year"),
                    "cited_by_count": (item.get("source_specific") or {}).get("cited_by_count"),
                    "abstract": (item.get("abstract") or "")[:4000] or None,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.openalex.org",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Abstracts are inverted-index reconstructions",
                    "Credit-budget model: 429 'Insufficient budget' measured "
                    "this session — availability resets per provider policy",
                ],
            ))
        return out


class SemanticScholarConnector(ConnectorBase):
    SOURCE_ID = "semantic_scholar"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "pacemaker lead fracture"
    LIMIT = 5
    # 2026-08-30: 429 recovery via bounded backoff (unauthenticated tier is
    # burst-limited); S2_API_KEY in .env.keys switches to the key tier the
    # day it is provisioned (header auth — never a URL param).
    BACKOFF_BASE_SECONDS = 3.0

    def request_headers(self) -> Dict[str, str]:
        from discovery_fabric.source_registry.keys import load_key
        key = load_key("S2_API_KEY")
        return {"x-api-key": key} if key else {}

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}"
                f"&limit={self.LIMIT}&fields=title,year,externalIds,citationCount,abstract")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        data = (payload or {}).get("data")
        if not isinstance(data, list):
            raise ValueError("semantic scholar payload missing data list")
        out = []
        for r in data:
            ext = r.get("externalIds") or {}
            sid = r.get("paperId") or ""
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"s2:{sid}",
                title=r.get("title") or "",
                uri=f"https://www.semanticscholar.org/paper/{sid}" if sid else "",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "paper_id": sid,
                    "doi": ext.get("DOI"),
                    "pmid": ext.get("PubMed"),
                    "year": r.get("year"),
                    "citation_count": r.get("citationCount"),
                    "abstract": (r.get("abstract") or "")[:4000] or None,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.semanticscholar.org/graph/v1",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Unauthenticated tier is burst-limited (429 measured); "
                    "reliable use requires an API key (not provisioned)",
                ],
            ))
        return out


class ArxivConnector(ConnectorBase):
    """arXiv preprint server — SCIENTIFIC role (preprints).

    Measured live 2026-08-30: https://export.arxiv.org/api/query answers
    200 Atom XML (the http:// variant and burst probing measured 429 —
    arXiv asks for ~3s courtesy between calls; enforced below).

    Terms (arXiv API ToU): retrieval for research with attribution is
    permitted; the API is rate-limited by courtesy interval, not keys.

    Epistemic note: PREPRINT evidence class — NOT peer-reviewed. Records
    carry that limitation structurally.
    """

    SOURCE_ID = "arxiv"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "flow diversion stent"
    LIMIT = 5
    _COURTESY_SECONDS = 3.0
    _last_request_ts: float = 0.0
    BACKOFF_BASE_SECONDS = 4.0

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://export.arxiv.org/api/query?search_query=all:{q}"
                f"&max_results={self.LIMIT}")

    def _request(self, url, timeout=25):
        # arXiv courtesy interval: the API asks clients to wait ~3 seconds
        # between calls; enforced client-side (bounded, burst-safe).
        import time as _time
        delta = _time.time() - ArxivConnector._last_request_ts
        if delta < self._COURTESY_SECONDS:
            _time.sleep(self._COURTESY_SECONDS - delta)
        try:
            return super()._request(url, timeout=timeout)
        finally:
            ArxivConnector._last_request_ts = _time.time()

    def parse_payload(self, raw: bytes, query: str) -> Any:
        import xml.etree.ElementTree as ET
        text = raw.decode("utf-8", "replace")
        if "<feed" not in text:
            raise ValueError("arxiv payload missing Atom <feed> root")
        ns = {"a": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        root = ET.fromstring(text)
        entries = []
        for e in root.findall("a:entry", ns):
            def _t(tag):
                el = e.find(f"a:{tag}", ns)
                return el.text.strip() if el is not None and el.text else ""
            links = {l.get("title", ""): l.get("href", "")
                     for l in e.findall("a:link", ns)}
            authors = [a.find("a:name", ns).text
                       for a in e.findall("a:author", ns)
                       if a.find("a:name", ns) is not None]
            entries.append({
                "id": _t("id"),
                "title": " ".join(_t("title").split()),
                "summary": _t("summary"),
                "published": _t("published"),
                "updated": _t("updated"),
                "authors": authors,
                "primary_category": (e.find("arxiv:primary_category", ns).get("term")
                                     if e.find("arxiv:primary_category", ns) is not None else ""),
                "pdf_url": links.get("pdf", ""),
            })
        return {"entries": entries}

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload.get("entries", []):
            aid = (r.get("id") or "").rsplit("/", 1)[-1]
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"arxiv:{aid}",
                title=r.get("title") or "",
                uri=r.get("id") or (f"https://arxiv.org/abs/{aid}" if aid else ""),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "arxiv_id": aid,
                    "doi": f"10.48550/arxiv.{aid.split('v')[0]}" if aid else None,
                    "published": r.get("published"),
                    "updated": r.get("updated"),
                    "authors": (r.get("authors") or [])[:20],
                    "primary_category": r.get("primary_category"),
                    "abstract": (r.get("summary") or "")[:4000] or None,
                    "pdf_url": r.get("pdf_url"),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "export.arxiv.org/api/query",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "PREPRINT: not peer-reviewed; findings may be revised "
                    "or withdrawn",
                    "PREPRINT_SERVER_BIAS: arXiv coverage is "
                    "physics/math/CS/quant-bio skewed — absence of an "
                    "arXiv record is not absence of the science",
                ],
            ))
        return out


class ElsevierScopusConnector(ConnectorBase):
    """Elsevier Scopus Search API — SCIENTIFIC role.

    Measured 2026-08-29 with the provisioned ELSEVIER_API_KEY: HTTP 200
    with real search-results; the no-key control answers 401
    AUTHENTICATION_ERROR (the key is what authorizes — positive and
    negative control both measured).

    Auth: X-ELS-APIKey HEADER (never a URL param) so the credential cannot
    land in the retrieval-log URL field (S-01 discipline).

    Scopus quirk handled honestly: a zero-match query still returns HTTP
    200 with an EMPTY "entry" list — that flows to EMPTY through the base
    (a definitive provider answer). A 401 (invalid/expired key) or 429
    (quota) stays AUTH_FAILED / RATE_LIMITED (Art. XXI.3).
    """

    SOURCE_ID = "elsevier_scopus"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "hydrocephalus shunt"
    LIMIT = 5

    def request_headers(self) -> Dict[str, str]:
        from discovery_fabric.source_registry.keys import load_key
        key = load_key("ELSEVIER_API_KEY")
        return {"X-ELS-APIKey": key} if key else {}

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return ("https://api.elsevier.com/content/search/scopus"
                f"?query={q}&count={self.LIMIT}&view=STANDARD")

    def _key_provisioned(self) -> bool:
        from discovery_fabric.source_registry.keys import load_key
        return bool(load_key("ELSEVIER_API_KEY"))

    def search(self, query: str, timeout: int = 25):
        if not self._key_provisioned():
            from discovery_fabric.source_registry.base import SourceQueryResult
            from discovery_fabric.source_registry.retrieval_log import append_entry
            out = SourceQueryResult(
                source_id=self.SOURCE_ID, status="AUTH_FAILED", ok=False,
                error="ELSEVIER_API_KEY not provisioned in .env.keys",
                query=query, retrieved_at=utc_now(),
            )
            try:
                append_entry(
                    source_id=self.SOURCE_ID, query=query,
                    url=self.build_url(query), status=out.status,
                    http_status=None, latency_ms=0, record_count=0,
                    raw_payload_sha256=None, error=out.error,
                )
            except Exception:  # noqa: BLE001
                pass
            return out
        return self._execute(query, timeout=timeout)

    def parse_payload(self, raw: bytes, query: str) -> Any:
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or "search-results" not in data:
            # service-error / status bodies must not parse as results
            raise ValueError(f"unexpected scopus payload shape: {list(data)[:5] if isinstance(data, dict) else type(data)}")
        return data

    def extract_total_hits(self, payload: Any) -> Any:
        sr = (payload or {}).get("search-results") or {}
        try:
            return int(sr.get("opensearch:totalResults"))
        except (TypeError, ValueError):
            return None

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        sr = (payload or {}).get("search-results") or {}
        entries = sr.get("entry") or []
        out: List[SourceRecord] = []
        for r in entries:
            if not isinstance(r, dict):
                continue
            # Scopus signals an error entry as {"service-error": ...} or an
            # entry with status text instead of dc:identifier — skip those
            # honestly rather than fabricating a record.
            if "service-error" in r or not r.get("dc:identifier"):
                continue
            eid = str(r.get("dc:identifier") or "").replace("SCOPUS_ID:", "")
            doi = r.get("prism:doi") or None
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"scopus:{eid}",
                title=r.get("dc:title") or "",
                uri=(f"https://www.scopus.com/record/display.uri?eid=2-s2.0-{eid}&origin=inward"
                     if eid else ""),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "scopus_eid": eid,
                    "doi": doi,
                    "creator": r.get("dc:creator"),
                    "publication_name": r.get("prism:publicationName"),
                    "publication_date": r.get("prism:coverDate"),
                    "citedby_count": r.get("citedby-count"),
                    "abstract": _clean(r.get("abstract") or "")[:4000] or None,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.elsevier.com/content/search/scopus",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Subscription-boundary opacity: some full-text "
                    "representations require entitlement this key may not "
                    "carry (not measured, not claimed)",
                ],
            ))
        return out
