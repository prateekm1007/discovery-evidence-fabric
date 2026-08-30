"""CROSS-SOURCE IDENTITY RESOLUTION + CONTRADICTION DETECTION.

CEO directive 2026-08-30 (maturity-model machinery gap #1, audit step 6-10):

    record -> canonical_entity -> source_records[] -> provenance[]

The same paper / patent / device / trial must resolve to ONE canonical
entity across sources; counts may only be reported post-deduplication
(Art. XXI.6); contradictions between sources about the same entity must
be DETECTED and surfaced, never silently averaged (Art. XV).

Identity policy (Art. II — exact, never fuzzy):
- PAPER:   DOI (arXiv DOIs normalized to bare arXiv id form), PMID
- PATENT:  normalized patent number (uppercase country code + digits,
           kind codes stripped: US1234567B2 -> US1234567)
- DEVICE:  FDA K-number / P-number (uppercase, stripped)
- TRIAL:   NCT id (uppercase)
- RECALL:  campaign id (source-prefixed — NHTSA vs FDA campaigns are
           different namespaces and are NOT merged)
Records with NO extractable identity key are UNRESOLVED (Art. XXV) —
they are reported as unresolved, never silently merged by title.

Contradiction policy (Art. III — surface, never adjudicate):
- same canonical entity + same comparable field + different exact values
  from different source records = CONTRADICTION with both provenances
- time-varying fields (citation counts, entry dates, abstracts, counts
  that legitimately drift as providers update) are EXEMPT — listed in
  TIME_VARYING_FIELDS so the exemption is explicit and reviewable
- titles are compared after total normalization (case, punctuation,
  whitespace) — residual differences are SOFT divergences, flagged but
  not hard contradictions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Identity keys
# ---------------------------------------------------------------------------

_PATENT_RE = re.compile(r"^([A-Z]{2})\s*#?(\d{6,})\s*[A-Z]\d?$")
_KNUM_RE = re.compile(r"^\s*#?\s*(K|P|DEN)[0-9]{5,7}\s*$", re.I)
_NCT_RE = re.compile(r"^\s*(NCT)\s*#?\s*(\d{8})\s*$", re.I)


def normalize_doi(v: Any) -> Optional[str]:
    if not v or not isinstance(v, str):
        return None
    d = v.strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)\s*", "", d)
    # arXiv DOI -> bare arXiv id form so preprints merge across the
    # arXiv source and literature sources that carry the DOI
    m = re.match(r"^10\.48550/arxiv\.(\S+)$", d)
    if m:
        return f"arxiv:{m.group(1).split('v')[0]}"
    if re.match(r"^10\.\d{4,9}/\S+$", d):
        return d
    return None


def normalize_patent_number(v: Any) -> Optional[str]:
    """US1234567B2 / US 12,345,678 A1 / 1234567 -> canonical 'US1234567'."""
    if not v or not isinstance(v, str):
        return None
    s = v.strip().upper().replace(",", "").replace(" ", "")
    m = re.match(r"^([A-Z]{2})(\d{6,})(?:[A-Z]\d?)?$", s)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    if s.isdigit() and 6 <= len(s) <= 9:
        return f"US{s}"  # bare US grant number (Google Patents convention)
    return None


def normalize_knumber(v: Any) -> Optional[str]:
    if not v or not isinstance(v, str):
        return None
    s = v.strip().upper().lstrip("#").strip()
    return s if re.match(r"^(K|P|DEN)\d{5,7}$", s) else None


def normalize_nct(v: Any) -> Optional[str]:
    if not v or not isinstance(v, str):
        return None
    s = v.strip().upper().replace(" ", "").lstrip("#")
    return s if re.match(r"^NCT\d{8}$", s) else None


def normalize_title(v: Any) -> Optional[str]:
    """Total deterministic normalization (NOT fuzzy matching): lowercase,
    strip punctuation, collapse whitespace. Two titles match iff their
    normalizations are identical."""
    if not v or not isinstance(v, str):
        return None
    s = v.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split()) or None


ENTITY_KINDS = ("PAPER", "PATENT", "DEVICE", "TRIAL", "RECALL", "OTHER")


def extract_identity_keys(record: Dict[str, Any]) -> Tuple[str, List[str]]:
    """(entity_kind, identity_keys) from a source record dict.

    Accepts SourceRecord-shaped dicts (normalized/provenance) or engine
    evidence-envelope dicts (doi at top level). Returns kind OTHER with
    NO keys when nothing extractable — the caller reports UNRESOLVED.
    """
    norm = record.get("normalized") or {}
    rid = record.get("record_id") or record.get("id") or ""
    sid = record.get("source_id") or record.get("source") or ""

    keys: List[str] = []

    # PAPER: doi / pmid / arxiv id
    doi = norm.get("doi") or record.get("doi")
    nd = normalize_doi(doi)
    if nd:
        # arXiv-form DOIs normalize to 'arxiv:<id>' — key them identically
        # to records from the arxiv source itself so they merge (same key
        # namespace, no doi:/arxiv: double-prefix mismatch)
        keys.append(nd if nd.startswith("arxiv:") else f"doi:{nd}")
    pmid = norm.get("pmid") or record.get("pmid")
    if pmid:
        keys.append(f"pmid:{str(pmid).strip()}")
    arxiv_id = norm.get("arxiv_id")
    if arxiv_id:
        keys.append(f"arxiv:{str(arxiv_id).split('v')[0]}")
    if rid.startswith("arxiv:"):
        keys.append(f"arxiv:{rid.split(':', 1)[1].split('v')[0]}")
    if keys:
        return "PAPER", keys

    # PATENT: normalized patent number from several field shapes
    for cand in (norm.get("patent_number"), norm.get("publication_number"),
                 record.get("patent_number")):
        pn = normalize_patent_number(cand)
        if pn:
            keys.append(f"patent:{pn}")
    if not keys and rid and ":" in rid:
        body = rid.split(":", 1)[1]
        pn = normalize_patent_number(body)
        if pn and "patent" in sid.lower() or (pn and sid in (
                "google_patents", "lens_patent", "patentbear", "epo_ops",
                "uspto_odp", "wipo_patentscope", "google_bigquery_patents")):
            keys.append(f"patent:{pn}")
    if keys:
        return "PATENT", keys

    # DEVICE: k-number
    for cand in (norm.get("k_number"), norm.get("k_numbers"), record.get("k_number")):
        kn = normalize_knumber(cand if isinstance(cand, str) else None)
        if kn:
            keys.append(f"knum:{kn}")
    if keys:
        return "DEVICE", keys

    # TRIAL: NCT id
    nct = normalize_nct(norm.get("nct_id") or record.get("nct_id"))
    if nct:
        return "TRIAL", [f"nct:{nct}"]

    # RECALL: campaign id (source-namespaced — never merged cross-source:
    # an FDA recall K-campaign and an NHTSA campaign are different worlds)
    camp = norm.get("nhtsa_campaign_number") or norm.get("recall_number")
    if camp:
        return "RECALL", [f"{sid or record.get('source', 'src')}:campaign:{str(camp).upper()}"]

    return "OTHER", []


# ---------------------------------------------------------------------------
# Canonical entity registry
# ---------------------------------------------------------------------------

@dataclass
class CanonicalEntity:
    entity_id: str                       # stable: first identity key seen
    kind: str
    identity_keys: set = field(default_factory=set)
    source_records: List[Dict[str, Any]] = field(default_factory=list)
    # each: {source_id, record_id, raw_payload_sha256, retrieved_at,
    #        provenance, comparable-field snapshot}

    def add(self, record: Dict[str, Any], keys: List[str]) -> None:
        self.identity_keys.update(keys)
        self.source_records.append({
            "source_id": record.get("source_id") or record.get("source"),
            "record_id": record.get("record_id") or record.get("id"),
            "raw_payload_sha256": (record.get("raw_payload_sha256")
                                   or record.get("content_hash")),
            "retrieved_at": (record.get("retrieved_at")
                             or record.get("retrieval_timestamp")),
            "provenance": record.get("provenance"),
        })


class EntityRegistry:
    """record -> canonical_entity -> source_records[] -> provenance[]"""

    def __init__(self) -> None:
        self._by_key: Dict[str, str] = {}       # identity key -> entity_id
        self.entities: Dict[str, CanonicalEntity] = {}
        self.unresolved: List[Dict[str, Any]] = []

    def resolve(self, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        for rec in records:
            kind, keys = extract_identity_keys(rec)
            if not keys:
                self.unresolved.append({
                    "source_id": rec.get("source_id") or rec.get("source"),
                    "record_id": rec.get("record_id") or rec.get("id"),
                    "reason": "NO_IDENTITY_KEY",
                })
                continue
            target_id = None
            for k in keys:
                if k in self._by_key:
                    target_id = self._by_key[k]
                    break
            if target_id is None:
                target_id = keys[0]
                self.entities[target_id] = CanonicalEntity(
                    entity_id=target_id, kind=kind)
            ent = self.entities[target_id]
            ent.add(rec, keys)
            for k in keys:
                self._by_key[k] = target_id
        return self.report()

    def report(self) -> Dict[str, Any]:
        multi = [e for e in self.entities.values()
                 if len({r["source_id"] for r in e.source_records}) > 1]
        return {
            "records_considered": sum(len(e.source_records)
                                      for e in self.entities.values())
            + len(self.unresolved),
            "canonical_entities": len(self.entities),
            "cross_source_entities": len(multi),
            "unresolved_records": len(self.unresolved),
            "unresolved_disclosed": self.unresolved[:20],
            "dedup_note": ("counts across sources are comparable ONLY at "
                           "canonical-entity level (Art. XXI.6); unresolved "
                           "records are disclosed, never title-merged"),
        }


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------

TIME_VARYING_FIELDS = {
    "cited_by_count", "citation_count", "citedByCount",  # providers update
    "entry_date", "retrieved_at", "retrieval_timestamp",
    "abstract",  # truncation policies differ; not comparable
    "enrollment_count", "record_count", "total_hits",
    "crawled_at", "indexed_at", "updated",
}
SOFT_FIELDS = {"title", "journal"}  # normalized compare; residual = soft


def _comparable(record: Dict[str, Any]) -> Dict[str, Any]:
    norm = dict(record.get("normalized") or {})
    for k in ("doi", "pmid", "title", "publication_date", "publication_year",
              "patent_number", "nct_id", "k_number", "overall_status"):
        if k in record:
            norm.setdefault(k, record[k])
    return norm


def detect_contradictions(
        records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Same canonical entity + same comparable field + different exact
    values from different source records -> surfaced contradiction.

    Exemptions are explicit: TIME_VARYING_FIELDS never contradict;
    SOFT_FIELDS produce SOFT_DIVERGENCE entries after total normalization.
    """
    registry = EntityRegistry()
    # keep original normalized payloads per entity for comparison
    originals: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]] = {}
    for rec in records:
        kind, keys = extract_identity_keys(rec)
        if not keys:
            continue
        registry.resolve([rec])
        target = registry._by_key.get(keys[0])
        if target:
            originals.setdefault(target, []).append((
                {"source_id": rec.get("source_id") or rec.get("source"),
                 "record_id": rec.get("record_id") or rec.get("id"),
                 "raw_payload_sha256": rec.get("raw_payload_sha256")
                 or rec.get("content_hash")},
                _comparable(rec),
            ))

    contradictions: List[Dict[str, Any]] = []
    for eid, entries in originals.items():
        if len({s["source_id"] for s, _ in entries}) < 2:
            continue
        fields: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for src_ref, snap in entries:
            for fname, val in snap.items():
                if fname in TIME_VARYING_FIELDS or val is None:
                    continue
                key = normalize_title(val) if fname in SOFT_FIELDS \
                    else str(val).strip()
                fields.setdefault(fname, {}).setdefault(key, []).append(src_ref)
        for fname, values in fields.items():
            if len(values) <= 1:
                continue
            severity = "SOFT_DIVERGENCE" if fname in SOFT_FIELDS \
                else "CONTRADICTION"
            contradictions.append({
                "entity_id": eid,
                "field": fname,
                "severity": severity,
                "values": values,
                "policy": ("surfaced, not adjudicated (Art. III); time-varying "
                           "fields exempt by explicit list"),
            })
    return contradictions
