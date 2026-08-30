"""Government technical-report connectors — NASA NTRS + DOE OSTI.

CEO Toscanini directive 2026-08-30 (free/open priority sources): custody-
grade government R&D evidence. Both endpoints were MEASURED live before
this file was written (probe artifacts, this session):

- NASA NTRS  : https://ntrs.nasa.gov/api/citations/search?q=...&page.size=N
               200 application/json; results[] with title, copyright,
               subjectCategories, distributionDate, otherReportNumbers...
- DOE OSTI   : https://www.osti.gov/api/v1/records?query=...&rows=N
               200 application/XML; <records><record><osti_id>...
               (note: api.osti.gov does not resolve from this egress;
               www.osti.gov/api/v1 is the measured working route)

Terms: both are US-government open-data services; retrieval, caching and
internal research use are permitted by their published terms (recorded in
the registry entries). Provenance: query + record id + payload sha256 go
through the same hash-chained retrieval log as every other source.

Epistemic class: OBSERVED (published technical reports). Negative
findings and lessons-learned ARE represented in these corpora (the CEO's
negative-evidence directive) but not structurally separated — failure
class stays MIXED (1), not failure-native.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase,
    SourceRecord,
    utc_now,
)

NTRS_LIMITATIONS = [
    "TECHNICAL_REPORT: engineering conclusions are report-grade, not "
    "peer-review-grade; internal review depth varies by center and era",
    "EXPORT_CONTROL: NTRS records carry export-control metadata; presence "
    "of a citation is not permission to redistribute the full document",
    "NEGATIVE_RESULTS_UNLABELED: failure analyses and lessons-learned "
    "exist in the corpus but are not structurally flagged — absence of a "
    "failure label is not absence of failure content",
]

OSTI_LIMITATIONS = [
    "TECHNICAL_REPORT: DOE-funded research outputs; report-grade evidence",
    "CORPUS_SCOPE: indexed outputs are DOE-funded research — absence of an "
    "OSTI record is not evidence a technology was never researched",
    "NEGATIVE_RESULTS_UNLABELED: lessons-learned present but not "
    "structurally separated",
]


class NasaNtrsConnector(ConnectorBase):
    """NASA Technical Reports Server — aerospace/materials/propulsion R&D."""

    SOURCE_ID = "nasa_ntrs"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "battery thermal runaway"
    LIMIT = 10

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://ntrs.nasa.gov/api/citations/search?q={q}"
                f"&page.size={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ValueError("nasa_ntrs payload missing results list")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload.get("results", []):
            rid = r.get("id") or ""
            title = (r.get("title") or [""])[0] if isinstance(r.get("title"), list) \
                else (r.get("title") or "")
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"ntrs:{rid}",
                title=str(title),
                uri=f"https://ntrs.nasa.gov/citations/{rid}" if rid else "",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "ntrs_id": rid,
                    "publication_date": r.get("publicationDate"),
                    "distribution_date": r.get("distributionDate"),
                    "subject_categories": r.get("subjectCategories"),
                    "report_numbers": r.get("otherReportNumbers"),
                    "funding_numbers": r.get("fundingNumbers"),
                    "copyright": r.get("copyright"),
                    "abstract": self._abstract(r),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "ntrs.nasa.gov/api/citations/search",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(NTRS_LIMITATIONS),
            ))
        return out

    @staticmethod
    def _abstract(r: Dict[str, Any]) -> Any:
        ab = r.get("abstract") or r.get("abstracts")
        if isinstance(ab, list) and ab:
            first = ab[0]
            if isinstance(first, dict):
                return (first.get("abstract") or "")[:4000] or None
            return str(first)[:4000]
        return (str(ab)[:4000] or None) if ab else None


class DoeOstiConnector(ConnectorBase):
    """DOE Office of Scientific and Technical Information — energy/materials
    R&D records.

    Measured live 2026-08-30 (this session):
    - https://www.osti.gov/api/v1/records?q=...&rows=N  -> 200 with a
      top-level JSON ARRAY of records (native v1 shape).
    - api.osti.gov does not resolve from this egress.
    - CRITICAL QUIRK MEASURED 2026-08-30 (found by the QUERY_RELEVANCE
      battery): the `query=` parameter is SILENTLY IGNORED — completely
      different queries return byte-identical record sets (lithium
      battery safety vs concrete pavement -> same 5 records: lignin,
      superconducting magnets...). The correct parameter is `q=`.
      Status-OK-plus-irrelevant-records is the Lens-DSL defect class;
      pinned by test_free_priority_sources.py regression.
    - `format=xml` + %20-encoded query silently returns JSON anyway
      (Content-Type flip-flops) — the connector asserts the parsed shape,
      never trusting the Content-Type.
    """

    SOURCE_ID = "doe_osti"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "lithium battery safety"
    LIMIT = 10

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://www.osti.gov/api/v1/records?q={q}"
                f"&rows={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8", "replace"))
        if not isinstance(payload, list):
            raise ValueError("doe_osti native JSON is not a record array")
        return {"records": payload}

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload.get("records", []):
            if not isinstance(r, dict):
                continue
            oid = str(r.get("osti_id") or "")
            authors = r.get("authors") or []
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"osti:{oid}",
                title=(r.get("title") or "").strip(),
                uri=f"https://www.osti.gov/biblio/{oid}" if oid else "",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "osti_id": oid,
                    "doi": self._norm_doi(r.get("doi")),
                    "publication_date": r.get("publication_date"),
                    "entry_date": r.get("entry_date"),
                    "product_type": r.get("product_type"),
                    "report_number": r.get("report_number"),
                    "research_orgs": r.get("research_orgs"),
                    "sponsor_orgs": r.get("sponsor_orgs"),
                    "subjects": r.get("subjects"),
                    "authors": authors[:20],
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "www.osti.gov/api/v1/records",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(OSTI_LIMITATIONS),
            ))
        return out

    @staticmethod
    def _norm_doi(v: Any) -> Any:
        if not v:
            return None
        m = re.search(r"10\.\d{4,9}/\S+", str(v))
        return m.group(0) if m else str(v)
