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
        result = (payload or {}).get("resultList") or {}
        results = result.get("result")
        if not isinstance(results, list):
            raise ValueError("europepmc payload missing resultList.result")
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
                limitations=[],
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

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://api.openalex.org/works?search={q}&per-page={self.LIMIT}"
                "&mailto=discovery-fabric%40example.org")

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
