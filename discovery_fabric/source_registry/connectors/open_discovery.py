"""Open discovery connectors — DOAJ, Unpaywall, DataCite, OpenAIRE, CORE.

R409 (multi-source open retrieval fabric directive): the engine's retrieval
universe was Europe PMC + OpenAlex. These adapters add materially different
open/free source FAMILIES, each following the base-class 7-step proof chain
and Art. XXI.3 failure discipline (provider failure is NEVER absence).

Family map (independence rationale, see retrieval_fabric/lineage.py):
  doaj       — OA JOURNAL REGISTRY: journals submit article metadata to DOAJ
               directly (own application pipeline) — not a Crossref derivative.
  unpaywall  — OA LOCATION SERVICE: for a known DOI, measures WHERE the
               legally open full text lives (repository, publisher page,
               hybrid). Metadata derives from Crossref; the OA-location
               fact is Unpaywall's own measurement.
  datacite   — DOI REGISTRANT (repositories/datacites/theses): registry of
               DOIs registered by data centres and institutional
               repositories. Materially different population from Crossref's
               publisher-registered DOIs. The thesis lane depends on this.
  openaire   — REPOSITORY AGGREGATOR: aggregates institutional/subject
               repositories across Europe and beyond.
  core       — REPOSITORY AGGREGATOR (independent harvest from OpenAIRE's):
               harvests repositories directly, own content ranking.

Live measurements (2026-09-05, this egress): all five answered HTTP 200
without credentials. arXiv measured 429/timeout (hard throttled from this
network), Zenodo 403 (network-side block), EPO OPS 403 Fair Use — those are
recorded honestly by their own adapters/registry states, never silently
omitted.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceRecord, utc_now,
)


# ---------------------------------------------------------------------------
# DOAJ — Directory of Open Access Journals (article search)
# ---------------------------------------------------------------------------

class DoajConnector(ConnectorBase):
    """DOAJ v2 REST article search. No key required (OAI-PMH also exists).

    Coverage class: OPEN_ACCESS_JOURNAL_DISCOVERY. PEER_REVIEWED by DOAJ
    admission policy (journals must practice peer review to be listed).
    """

    SOURCE_ID = "doaj"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "malaria vector control"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://doaj.org/api/v2/search/articles/{q}"
                f"?page=1&pageSize={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        results = (payload or {}).get("results")
        if not isinstance(results, list):
            raise ValueError("doaj payload missing results list")
        out: List[SourceRecord] = []
        for r in results:
            bib = r.get("bibjson") or {}
            title = bib.get("title") or ""
            doi = ""
            for ident in (bib.get("identifier") or []):
                if str(ident.get("type", "")).lower() == "doi":
                    doi = str(ident.get("id", "")).lower()
                    if not doi.startswith("10."):
                        doi = f"10.{doi}" if doi else ""
            year = (bib.get("year") or "")[:4]
            fulltext = ""
            for link in (bib.get("link") or []):
                if link.get("type") in ("fulltext", "fulltext_pdf"):
                    fulltext = link.get("url") or ""
                    break
            journal = (bib.get("journal") or {}).get("title") or ""
            aid = r.get("id") or ""
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"doaj:{aid}",
                title=title,
                uri=fulltext or f"https://doaj.org/article/{aid}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "doaj_id": aid,
                    "doi": doi or None,
                    "title": title,
                    "journal": journal,
                    "publication_year": year or None,
                    "abstract": (bib.get("abstract") or "")[:4000] or None,
                    "fulltext_url": fulltext or None,
                    "authors": [a.get("name") for a in (bib.get("author") or [])][:20],
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "doaj.org/api/v2",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "DOAJ covers only journals admitted to the index "
                    "(peer-reviewed OA, no APC condition) — absence here is "
                    "not absence of the science (Art. XXV)",
                ],
            ))
        return out


# ---------------------------------------------------------------------------
# Unpaywall — DOI -> legally-open full-text location resolution
# ---------------------------------------------------------------------------

class UnpaywallConnector(ConnectorBase):
    """Unpaywall v2 per-DOI lookup. No key; requires a contact email.

    Role: FULLTEXT_RESOLUTION, not discovery. The fabric queries it for
    DOIs discovered elsewhere (the directive: 'take a DOI found anywhere
    and ask where the legally open full text is').
    """

    SOURCE_ID = "unpaywall"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "10.1038/nature12373"  # a canonical DOI, by design
    LIMIT = 1
    RATE_LIMIT_RETRIES = 1
    BACKOFF_BASE_SECONDS = 3.0

    #: Unpaywall 404s for a DOI it has no record of — that is a provider
    #: answer ("not in Unpaywall's corpus"), not an outage. Map it to
    #: EMPTY (ok=True) so absence semantics stay honest (Art. XXI.3).
    def definitive_empty(self, http_status: Optional[int], body: Optional[bytes]) -> bool:
        return http_status == 404

    def build_url(self, query: str) -> str:
        doi = (query or "").strip().lower()
        from discovery_fabric.source_registry.keys import load_key
        email = load_key("UNPAYWALL_EMAIL") or "discovery-fabric@example.org"
        return (f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}"
                f"?email={urllib.parse.quote(email)}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        # Unpaywall returns ONE object (not a list) for the queried DOI.
        if not isinstance(payload, dict) or "doi" not in payload:
            raise ValueError("unpaywall payload missing doi field")
        best = payload.get("best_oa_location") or {}
        out = [SourceRecord(
            source_id=self.SOURCE_ID,
            role="SCIENTIFIC",
            record_id=f"unpaywall:{payload.get('doi')}",
            title=payload.get("title") or "",
            uri=best.get("url_for_landing_page") or best.get("url") or "",
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "doi": payload.get("doi"),
                "title": payload.get("title") or "",
                "is_oa": payload.get("is_oa"),
                "oa_status": payload.get("oa_status"),
                "publication_year": payload.get("year"),
                "fulltext_url": (best.get("url_for_pdf")
                                 or best.get("url") or None),
                "host_type": best.get("host_type"),
                "repository_institution": best.get("repository_institution"),
                "license": best.get("license"),
            },
            provenance={
                "provider": self.SOURCE_ID,
                "api": "api.unpaywall.org/v2",
                "query": query,
                "raw_payload_sha256": raw_sha,
                "retrieved_at": utc_now(),
            },
            epistemic_state="OBSERVED",
            limitations=[
                "Unpaywall resolves a KNOWN DOI to OA locations; it is not "
                "a discovery index — metadata upstream derives from Crossref",
            ],
        )]
        return out


# ---------------------------------------------------------------------------
# DataCite — DOI registrant for repositories, datasets, theses
# ---------------------------------------------------------------------------

class DataciteConnector(ConnectorBase):
    """DataCite DOI search. No key required for public search.

    Coverage class: REPOSITORY_DOI_REGISTRY + THESIS coverage via
    resourceTypeGeneral=Dissertation / resourceType=Thesis. This is the
    registrant-side record for repository-registered DOIs (Zenodo, many
    institutional repositories) — a materially different population from
    Crossref's publisher DOIs.
    """

    SOURCE_ID = "datacite"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "seismic data"
    LIMIT = 5
    #: optional thesis/document-type scoping (set by the fabric lanes)
    RESOURCE_TYPE_FILTER: Optional[str] = None

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        url = (f"https://api.datacite.org/dois?query={q}"
               f"&page[size]={self.LIMIT}")
        if self.RESOURCE_TYPE_FILTER:
            url += (f"&types.resourceTypeGeneral="
                    f"{urllib.parse.quote(self.RESOURCE_TYPE_FILTER)}")
        return url

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        data = (payload or {}).get("data")
        if not isinstance(data, list):
            raise ValueError("datacite payload missing data list")
        out: List[SourceRecord] = []
        for d in data:
            attrs = d.get("attributes") or {}
            doi = (attrs.get("doi") or d.get("id") or "").lower()
            titles = attrs.get("titles") or []
            title = (titles[0].get("title") if titles and isinstance(titles[0], dict)
                     else str(titles[0]) if titles else "")
            types = attrs.get("types") or {}
            year = attrs.get("publicationYear")
            creators = [c.get("name") for c in (attrs.get("creators") or [])][:20]
            publisher = attrs.get("publisher")
            url = attrs.get("url") or (f"https://doi.org/{doi}" if doi else "")
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"datacite:{doi}",
                title=title,
                uri=url,
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "doi": doi or None,
                    "title": title,
                    "resource_type_general": types.get("resourceTypeGeneral"),
                    "resource_type": types.get("resourceType"),
                    "publication_year": year,
                    "authors": creators,
                    "publisher": publisher,
                    "abstract": ((attrs.get("descriptions") or [{}])[0].get("description")
                                 if attrs.get("descriptions") else None),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.datacite.org/dois",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "DataCite holds repository/datacentre-registered DOIs; "
                    "publisher-registered literature is Crossref's space — "
                    "neither covers the other (Art. XXV)",
                ],
            ))
        return out


# ---------------------------------------------------------------------------
# OpenAIRE — repository aggregator (publications + other research products)
# ---------------------------------------------------------------------------

def _oai_list(x: Any) -> List[Any]:
    """OpenAIRE's XML->JSON encoding: a repeated element is a list, a
    single element is a bare dict. Normalize both to list."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _oai_text(el: Any) -> str:
    """Extract the '$' text from an OpenAIRE element (dict-or-list)."""
    for item in _oai_list(el):
        if isinstance(item, dict):
            v = item.get("$", "")
            if v:
                return str(v)
    return ""


def _oai_classname(el: Any) -> str:
    for item in _oai_list(el):
        if isinstance(item, dict):
            v = item.get("@classname", "")
            if v:
                return str(v)
    return ""


class OpenaireConnector(ConnectorBase):
    """OpenAIRE search API (publications). No key required.

    Coverage class: REPOSITORY_AGGREGATOR. MEASURED payload shape (live,
    2026-09-05): response.results.result[] -> header.dri:objIdentifier.$
    + metadata.oaf:entity.oaf:result{title, creator, pid,
    dateofacceptance, children.instance{instancetype, webresource.url,
    hostedby, refereed, collectedfrom}}. Document type (Thesis,
    Article, ...) is read post-hoc from children.instance.instancetype
    (the API exposes NO server-side type filter — publicationtype /
    documenttype / instance.type params all measured HTTP 400 Illegal
    argument); instance-level refereed ("nonPeerReviewed") is carried
    for publication_status labeling.
    """

    SOURCE_ID = "openaire"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "marine aquaculture"
    LIMIT = 5

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://api.openaire.eu/search/publications?keywords={q}"
                f"&size={self.LIMIT}&format=json")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8", "replace"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        resp = (payload or {}).get("response") or {}
        results = (resp.get("results") or {})
        records = _oai_list(results.get("result")) if isinstance(results, dict) else []
        if not isinstance(results, dict):
            raise ValueError("openaire payload missing response.results")
        out: List[SourceRecord] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            header = r.get("header") or {}
            rid = header.get("dri:objIdentifier", {}).get("$", "")
            result = ((r.get("metadata") or {}).get("oaf:entity") or {}).get("oaf:result") or {}
            title = _oai_text(result.get("title"))
            creators = [str(c.get("$", "")) for c in _oai_list(result.get("creator"))
                        if isinstance(c, dict) and c.get("$")]
            doi = ""
            for p in _oai_list(result.get("pid")):
                if isinstance(p, dict) and p.get("$"):
                    doi = str(p["$"]).lower()
                    break
            year = _oai_text(result.get("dateofacceptance"))[:4]
            instancetypes: List[str] = []
            hostedby: List[str] = []
            refereed: str = ""
            url = ""
            for inst in _oai_list((result.get("children") or {}).get("instance")):
                if not isinstance(inst, dict):
                    continue
                cn = _oai_classname(inst.get("instancetype"))
                if cn:
                    instancetypes.append(cn)
                for hb in _oai_list(inst.get("hostedby")):
                    nm = hb.get("@name", "") if isinstance(hb, dict) else ""
                    if nm:
                        hostedby.append(str(nm))
                rf = _oai_classname(inst.get("refereed"))
                if rf and not refereed:
                    refereed = rf
                if not url:
                    wr = _oai_list(inst.get("webresource"))
                    if wr and isinstance(wr[0], dict):
                        url = _oai_text(wr[0].get("url"))
            if not url and doi:
                url = f"https://doi.org/{doi}"
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"openaire:{rid}",
                title=title,
                uri=url,
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "openaire_id": rid,
                    "doi": doi or None,
                    "title": title,
                    "instancetypes": [t for t in instancetypes if t],
                    "refereed": refereed or None,
                    "publication_year": year or None,
                    "authors": creators[:20],
                    "hosted_by": hostedby[:5],
                    "url": url or None,
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.openaire.eu/search",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                    "labeling_mode": "POST_HOC_INSTANCETYPE",
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Document-type labels are read post-hoc from record "
                    "instancetype (the API exposes no type filter — "
                    "measured 2026-09-05)",
                    "Aggregated repository metadata quality varies by "
                    "repository; instancetype is repository-declared",
                ],
            ))
        return out


# ---------------------------------------------------------------------------
# CORE — repository aggregator (independent harvest)
# ---------------------------------------------------------------------------

class CoreConnector(ConnectorBase):
    """CORE v3 works search — measured 2026-09-05 answering anonymously
    (no key) from this egress. CORE harvests repositories directly and
    maintains its own ranking; CORE_API_KEY (header auth) upgrades the
    tier if ever provisioned, never in URLs.

    Coverage class: REPOSITORY_AGGREGATOR (independent of OpenAIRE's
    harvest). CORE relevance ranking for long natural-language queries is
    weak (measured: a 7-word mechanism query matched 9.7M works); the
    fabric sends SHORT keyword-form queries only.
    """

    SOURCE_ID = "core"
    ROLES = ("SCIENTIFIC",)
    HEALTH_QUERY = "graphene sensor"
    LIMIT = 5

    def request_headers(self) -> Dict[str, str]:
        from discovery_fabric.source_registry.keys import load_key
        key = load_key("CORE_API_KEY")
        return {"Authorization": f"Bearer {key}"} if key else {}

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (f"https://api.core.ac.uk/v3/search/works?q={q}"
                f"&limit={self.LIMIT}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8", "replace"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        results = (payload or {}).get("results")
        if not isinstance(results, list):
            raise ValueError("core payload missing results list")
        out: List[SourceRecord] = []
        for r in results:
            rid = str(r.get("id") or "")
            title = r.get("title") or ""
            doi = (r.get("doi") or "").lower()
            year = r.get("year_published") or r.get("published")
            if isinstance(year, int):
                year = str(year)
            elif isinstance(year, str):
                year = year[:4]
            else:
                year = None
            repository = (r.get("repository") or {})
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="SCIENTIFIC",
                record_id=f"core:{rid}",
                title=title,
                uri=(f"https://core.ac.uk/works/{rid}" if rid else
                     (f"https://doi.org/{doi}" if doi else "")),
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "core_id": rid,
                    "doi": doi or None,
                    "title": title,
                    "publication_year": year,
                    "repository": (repository.get("name")
                                   if isinstance(repository, dict) else repository),
                    "document_type": (r.get("document_type")
                                      or (r.get("output_type")
                                          or [None])[0]
                                      if isinstance(r.get("output_type"), list)
                                      else r.get("output_type")),
                    "abstract": (r.get("abstract") or "")[:4000] or None,
                    "fulltext_links": [l.get("url") for l in (r.get("fulltext_links") or [])][:5],
                    "authors": [a.get("name") for a in (r.get("authors") or [])][:20],
                    "arxiv_id": r.get("arxivId"),
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.core.ac.uk/v3",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                    "tier": "anonymous" if not self.request_headers() else "key",
                },
                epistemic_state="OBSERVED",
                limitations=[
                    "Anonymous tier measured live 2026-09-05; per-query "
                    "quotas may rate-limit without notice (recorded honestly "
                    "when measured)",
                    "Aggregated repository metadata quality varies; "
                    "document_type is repository-declared and unverified",
                ],
            ))
        return out


__all__ = [
    "DoajConnector", "UnpaywallConnector", "DataciteConnector",
    "OpenaireConnector", "CoreConnector",
]
