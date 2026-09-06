"""Canonical record resolution + deduplication with source-provenance
preservation (directive sections 3 + 9 + 14).

Canonical identity rules (deterministic, weakest evidence preserved):
  1. PATENT publication number (normalized: uppercase, no separators)
  2. DOI (normalized: lowercase, strip https://doi.org/ prefix)
  3. arXiv id (mapped to the DataCite DOI form when both appear)
  4. normalized title + year fingerprint (last resort; recorded as
     TITLE_FINGERPRINT basis, never silently equal to DOI-level identity)

Dedup NEVER destroys source provenance: the merged record carries ALL
source appearances (indexing_sources) + the origin record's raw fields.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)
_TITLE_RE = re.compile(r"[a-z0-9]+")


def normalize_doi(doi: Optional[str]) -> str:
    if not doi:
        return ""
    d = str(doi).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = d.rstrip(".,;")
    return d if _DOI_RE.fullmatch(d) else ""


def normalize_patent_number(pid: Optional[str]) -> str:
    if not pid:
        return ""
    p = re.sub(r"[^A-Za-z0-9]", "", str(pid)).upper()
    return p


def title_fingerprint(title: Optional[str], year: Optional[Any] = None) -> str:
    words = _TITLE_RE.findall((title or "").lower())
    core = " ".join(words[:12])
    y = str(year or "")[:4]
    h = hashlib.sha256(f"{core}|{y}".encode("utf-8")).hexdigest()[:16]
    return h


@dataclass
class CanonicalRecord:
    """One deduplicated record with FULL multi-source provenance."""

    canonical_id: str
    identity_basis: str                    # PATENT_NUMBER | DOI | TITLE_FINGERPRINT
    title: str = ""
    doi: str = ""
    patent_number: str = ""
    publication_year: Optional[str] = None
    # provenance attribution (directive section 3):
    origin_source: str = ""                # first source that yielded the record
    indexing_sources: List[str] = field(default_factory=list)
    record_ids_by_source: Dict[str, str] = field(default_factory=dict)
    queries_by_source: Dict[str, str] = field(default_factory=dict)
    publication_status: str = "UNKNOWN"
    evidence_lane: str = "REPOSITORY"
    document_type: str = ""                # PATENT for patent lane; else source type evidence
    source_type_evidence: List[str] = field(default_factory=list)
    best_record: Dict[str, Any] = field(default_factory=dict)  # richest normalized record
    fulltext_url: Optional[str] = None
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "identity_basis": self.identity_basis,
            "title": self.title,
            "doi": self.doi,
            "patent_number": self.patent_number,
            "publication_year": self.publication_year,
            "origin_source": self.origin_source,
            "indexing_sources": sorted(set(self.indexing_sources)),
            "record_ids_by_source": self.record_ids_by_source,
            "queries_by_source": self.queries_by_source,
            "publication_status": self.publication_status,
            "evidence_lane": self.evidence_lane,
            "document_type": self.document_type,
            "source_type_evidence": self.source_type_evidence,
            "fulltext_url": self.fulltext_url,
            "limitations": self.limitations,
            "best_record": self.best_record,
        }


def _pick_abstract(rec: Dict[str, Any]) -> str:
    for key in ("abstract", "summary"):
        v = rec.get(key)
        if v and len(str(v)) >= 50:
            return str(v)
    return ""


class Canonicalizer:
    """Resolve fabric records into canonical records, preserving every
    source appearance. merge precedence for the representative record:
    the record with the longest abstract (richest evidence), ties broken
    by source order (deterministic)."""

    def __init__(self) -> None:
        self._by_key: Dict[str, CanonicalRecord] = {}
        self._by_title: Dict[str, str] = {}
        self.merge_events: List[Dict[str, Any]] = []

    def add(self, source_id: str, record: Dict[str, Any],
            query: str, publication_status: str, evidence_lane: str,
            document_type: str, source_type_evidence: str,
            fulltext_url: Optional[str] = None,
            limitations: Optional[List[str]] = None) -> CanonicalRecord:
        normalized = record
        doi = normalize_doi((normalized.get("doi") or "")
                            if isinstance(normalized, dict) else "")
        patent = normalize_patent_number(
            normalized.get("patent_number") if isinstance(normalized, dict) else None)
        if document_type == "PATENT" and patent:
            key, basis = f"patent:{patent}", "PATENT_NUMBER"
        elif doi:
            key, basis = f"doi:{doi}", "DOI"
        else:
            arxiv_id = (normalized.get("arxiv_id") or
                        (normalized.get("arxiv_id") if isinstance(normalized, dict) else None))
            if arxiv_id:
                key, basis = f"arxiv:{str(arxiv_id)}", "ARXIV_ID"
            else:
                fp = title_fingerprint(normalized.get("title"),
                                       normalized.get("publication_year")
                                       or normalized.get("year"))
                key, basis = f"title:{fp}", "TITLE_FINGERPRINT"
        rec = self._by_key.get(key)
        if rec is None:
            # a DOI-keyed record may also match an earlier
            # TITLE_FINGERPRINT record of the same paper: unify via the
            # title index (title key -> canonical key).
            # BLANK-TITLE GUARD (R412 gradient-v3 pre-seal repair,
            # 2026-09-06): title_fingerprint of a blank title is a
            # CONSTANT — without this guard every blank-title record
            # from every source aliases to one dedup key and collapses
            # into a single canonical record (measured: arXiv 5 records
            # -> 1 blank-title survivor, excluded from the engine pool).
            # A blank title is NOT identity evidence (Art. II): it must
            # never merge or index.
            _title_text = (normalized.get("title") or "").strip()
            if _title_text:
                tkey = title_fingerprint(_title_text,
                                         normalized.get("publication_year")
                                         or normalized.get("year"))
                existing_canonical = self._by_title.get(tkey)
                if existing_canonical:
                    rec = self._by_key[existing_canonical]
                    self.merge_events.append({
                        "merged": key, "into": existing_canonical,
                        "basis": "TITLE_FINGERPRINT_TO_EXISTING",
                    })
            if rec is None:
                rec = CanonicalRecord(canonical_id=key, identity_basis=basis,
                                      title=(normalized.get("title") or ""))
                self._by_key[key] = rec
                if _title_text and tkey and basis != "TITLE_FINGERPRINT":
                    self._by_title[tkey] = key
        # attribute this appearance
        if source_id not in rec.indexing_sources:
            rec.indexing_sources.append(source_id)
        rid = (record.get("record_id") or
               record.get("id") or "")
        rec.record_ids_by_source.setdefault(source_id, str(rid))
        rec.queries_by_source.setdefault(source_id, query)
        if not rec.origin_source:
            rec.origin_source = source_id
        # keep the richest representative record
        if (len(_pick_abstract(normalized)) >
                len(_pick_abstract(rec.best_record))):
            rec.best_record = normalized
        elif not rec.best_record:
            # R412 gradient-v3 gate-fail decomposition repair
            # (2026-09-06, incident
            # R412-GRADIENT-V3-NORM-METADATA-FIELDS): a metadata-only
            # source (crossref, google_patents) never won the
            # longest-abstract comparison, so best_record stayed EMPTY
            # and every field only that source carried (issued_year,
            # publication_date, snippet) was silently dropped for the
            # whole canonical record. A record's representative must
            # never be emptier than any of its appearances: the FIRST
            # appearance seeds best_record; a strictly-richer abstract
            # still replaces it (precedence unchanged).
            rec.best_record = normalized
        if not rec.doi and doi:
            rec.doi = doi
        if not rec.patent_number and patent:
            rec.patent_number = patent
        if not rec.publication_year:
            # R412 gradient-v3 gate-fail decomposition repair
            # (2026-09-06, incident R412-GRADIENT-V3-NORM-METADATA-
            # FIELDS): crossref persists the year as `issued_year` and
            # the patent adapters as `publication_date` — neither key
            # was read here, so 388/483 v3 pool records lost their
            # year (measured from committed pool bytes). Read every
            # field form the connectors actually emit; the value
            # stays a verbatim provider string, never a guess.
            rec.publication_year = (
                normalized.get("publication_year")
                or normalized.get("year")
                or normalized.get("issued_year")
                or normalized.get("publication_date"))
        if not rec.title:
            rec.title = normalized.get("title") or ""
        if not rec.fulltext_url and fulltext_url:
            rec.fulltext_url = fulltext_url
        if publication_status and rec.publication_status == "UNKNOWN":
            rec.publication_status = publication_status
        if document_type and not rec.document_type:
            rec.document_type = document_type
        if evidence_lane and rec.evidence_lane == "REPOSITORY":
            rec.evidence_lane = evidence_lane
        if source_type_evidence and \
                source_type_evidence not in rec.source_type_evidence:
            rec.source_type_evidence.append(source_type_evidence)
        if limitations:
            for lim in limitations:
                if lim not in rec.limitations:
                    rec.limitations.append(lim)
        return rec

    def canonical_records(self) -> List[CanonicalRecord]:
        return list(self._by_key.values())
