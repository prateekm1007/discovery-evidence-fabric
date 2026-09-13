"""The canonical EvidenceRecord — ONE evidence representation for every
source (R449 directive Phase 3: "Do not create separate semantic truth
systems per source").

Constitutional anchors:
  Art. II   — every dossier-grade proposition binds to the SMALLEST
              exact evidence span capable of proving it.
  Art. III  — the claimant cannot define what the evidence says: the
              `proposition` field is the interpretation layer's CLAIM
              about the span; `exact_span` is custody (source, document,
              version, location, verbatim text, content hash). The LLM
              may interpret the span; it may NEVER redefine it.
  Art. VI   — no manufactured provenance: every field either comes from
              the live retrieval or is explicitly UNKNOWN.
  Art. XII  — the custody chain is complete: evidence_id -> span ->
              row identity -> dataset revision -> source identity ->
              retrieval timestamp -> content hash.
  Art. XXI.9— every record enters provenance custody or it is noise.
  Art. XXV  — admissibility unknowns stay unknown (PENDING states are
              legitimate; BLOCKED is fail-closed).

Span custody (directive Phase 4): source + document + version + location
+ exact text + content hash. The interpretive layer (LLM) proposes
propositions/entities/mechanisms; the custody layer guarantees the bytes.

Admissibility is FAIL-CLOSED: a record with an unverified license, a
schema violation, or an unadjudicated relevance is NOT ADMITTED — it is
PENDING_* or BLOCKED_* and can never silently become evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

#: maximum verbatim span bytes kept in the record (the span itself is
#: NEVER truncated for hashing purposes — a truncated span is a
#: different span; long fields hash whole, carry a bounded prefix for
#: display, and the custody verifier re-fetches the full row)
SPAN_DISPLAY_LIMIT = 600

#: admissibility vocabulary (closed; every record carries exactly one)
ADMISSIBILITY_STATES = [
    "ADMITTED",                          # license verified + schema valid
                                         # + relevance adjudicated relevant
    "PENDING_CORROBORATION",             # single-source claim; no second
                                         # independent family yet
    "PENDING_RELEVANCE",                 # relevance not yet adjudicated
    "BLOCKED_LICENSE_UNVERIFIED",        # the source's license/access state
                                         # was never verified (Art. XXVII-
                                         # class: no promotion without the
                                         # registry's verified state)
    "BLOCKED_SCHEMA_INVALID",            # did not validate against the
                                         # source's declared schema
    "BLOCKED_RELEVANCE_REJECTED",        # adjudicated NOT relevant (keyword
                                         # collision — Art. XXI.4)
    "BLOCKED_SOURCE_FAILURE",            # retrieval-state failure class
                                         # (provider error, timeout — never
                                         # absence, Art. XXI.3)
]

#: the six evidence-source families (operator's reconnaissance taxonomy)
SOURCE_FAMILIES = [
    "E1_patent_intelligence",
    "E2_scientific_intelligence",
    "E3_engineering_intelligence",
    "E4_materials_intelligence",
    "E5_chemical_intelligence",
    "E6_domain_intelligence",
]

EVIDENCE_FABRIC_VERSION = "evidence_fabric/1.0.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class ExactSpan:
    """Custody: WHERE the evidence bytes live, verbatim.

    location is machine-checkable: (dataset, config, split, row_idx,
    field, retrieval_query). MEASURED LIVE (this round): the search
    endpoint's row_idx is NOT a stable address (the datasets-server
    search index numbers rows differently from the /rows storage
    order, and load-balanced nodes can disagree); the filter
    endpoint's row_idx IS aligned with /rows offsets. The backward
    trace therefore verifies by ENDPOINT: filter -> pinned row
    re-fetch; search -> retrieval replay (the same query re-issued,
    the document_ref located among the results, the span bytes
    compared). The LLM may interpret the span; it can never redefine
    these bytes (Art. II/III).
    """

    dataset_id: str                       # e.g. baber/WOPTO
    config: str = "default"
    split: str = "train"
    row_idx: int = -1                     # as returned by the serving
                                          # endpoint (retrieval
                                          # provenance; a stable address
                                          # only for filter-served rows)
    field: str = ""                       # the exact column the span is
                                          # from
    text: str = ""                        # VERBATIM bytes (bounded copy)
    text_sha256: str = ""                 # hash of the FULL field value
    document_ref: str = ""                # provider-native record id
                                         # (publication_number / mol_id / ...)
    truncated: bool = False               # display text bounded, hash whole
    retrieval_query: str = ""             # the query that retrieved this
                                          # row (the replay anchor for
                                          # search-served custody)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceIdentity:
    """WHO provided the bytes, at which version."""

    source_id: str                        # registry id (e.g. "wopto")
    family: str = ""                      # SOURCE_FAMILIES entry
    url: str = ""                         # dataset url
    dataset_revision: str = ""            # git sha of the dataset repo at
                                         # retrieval time (pinning, Art. XLIV)
    retrieval_endpoint: str = ""          # datasets-server route used
    connector_state: str = "SUCCESS"      # the state-contract value


@dataclass
class Provenance:
    """The origin chain — never manufactured (Art. VI)."""

    origin_description: str = ""          # e.g. "exported from Google
                                         # Patents Public Data" (card text)
    card_license: Optional[str] = None    # license declared on the card
    license_verified: bool = False        # the registry verified the text
    license_basis: str = "UNVERIFIED"     # CARD_DECLARATION_ONLY | LICENSE_FILE
    retrieved_via: str = "hf_datasets_server"  # transport
    cross_source_corroboration: str = "NONE"   # NONE | CORROBORATED(id..) |
                                         # CONTRADICTED(id..) | PENDING


@dataclass
class Admissibility:
    """Fail-closed admission state + the recorded reasons."""

    state: str = "PENDING_RELEVANCE"
    reasons: List[str] = field(default_factory=list)

    def is_admitted(self) -> bool:
        return self.state == "ADMITTED"


@dataclass
class EvidenceRecord:
    """THE canonical evidence representation (directive Phase 3)."""

    evidence_id: str
    source_identity: SourceIdentity
    source_version: str                   # dataset_revision (+ split/config)
    source_type: str                      # family id
    retrieval_timestamp: str
    content_hash: str                     # sha256 of the exact span text
    exact_span: ExactSpan
    # ---- interpretation layer (the LLM proposes; custody guarantees) --
    proposition: str = ""                 # what the span is claimed to
                                          # establish (Art. III: a CLAIM,
                                          # never self-authoritative)
    technical_entities: List[str] = field(default_factory=list)
    mechanisms: List[str] = field(default_factory=list)
    measurements: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    # ---- custody + admission -------------------------------------------
    provenance: Provenance = field(default_factory=Provenance)
    admissibility: Admissibility = field(default_factory=Admissibility)
    relevance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_identity": asdict(self.source_identity),
            "source_version": self.source_version,
            "source_type": self.source_type,
            "retrieval_timestamp": self.retrieval_timestamp,
            "content_hash": self.content_hash,
            "exact_span": self.exact_span.to_dict(),
            "proposition": self.proposition,
            "technical_entities": list(self.technical_entities),
            "mechanisms": list(self.mechanisms),
            "measurements": list(self.measurements),
            "conditions": list(self.conditions),
            "citations": list(self.citations),
            "provenance": asdict(self.provenance),
            "admissibility": {
                "state": self.admissibility.state,
                "reasons": list(self.admissibility.reasons),
            },
            "relevance": dict(self.relevance),
        }

    # -- engine-compatibility surface (a2 evidence item schema; ADDITIVE
    #    fields only — the same contract discipline as retrieval_fabric
    #    V1 -> V2: downstream stages keep working unchanged) -------------
    def to_engine_item(self) -> Dict[str, Any]:
        span = self.exact_span
        display = span.text[:SPAN_DISPLAY_LIMIT]
        if self.measurements and len(display) < 200:
            # structured (filter-mode) record: render the properties into
            # the abstract the synthesis prompt sees — the span stays the
            # custody anchor; the measurements are same-row columns
            parts = [f"{m['field']}={m['value']}" for m in self.measurements[:8]]
            display = (display + " | computed properties: "
                       + ", ".join(parts))[:SPAN_DISPLAY_LIMIT]
        return {
            "id": self.evidence_id,
            "source_type": _engine_source_type(self.source_type),
            "source": self.source_identity.source_id,
            "source_id": span.document_ref or f"{span.row_idx}",
            "source_uri": self.source_identity.url,
            "title": _title_of(self),
            "abstract": display,
            "doi": "",
            "publication_date": None,
            "retrieval_timestamp": self.retrieval_timestamp,
            "retrieval_method": "evidence_fabric_federated_query",
            "content_hash": self.content_hash,
            "provenance": {
                "provider": self.source_identity.source_id,
                "dataset_revision": self.source_identity.dataset_revision,
                "connector_state": self.source_identity.connector_state,
                "license_verified": self.provenance.license_verified,
            },
            "epistemic_state": self.admissibility.state,
            # ---- evidence-fabric additive fields ----
            "evidence_fabric": {
                "version": EVIDENCE_FABRIC_VERSION,
                "family": self.source_type,
                "exact_span": {
                    "dataset_id": span.dataset_id,
                    "config": span.config,
                    "split": span.split,
                    "row_idx": span.row_idx,
                    "field": span.field,
                    "text_sha256": span.text_sha256,
                    "document_ref": span.document_ref,
                },
                "proposition": self.proposition,
                "admissibility": self.admissibility.state,
                "measurements": self.measurements[:8],
            },
        }


_ENGINE_SOURCE_TYPES = {
    "E1_patent_intelligence": "patent",
    "E2_scientific_intelligence": "scientific_paper",
    "E3_engineering_intelligence": "dataset",
    "E4_materials_intelligence": "dataset",
    "E5_chemical_intelligence": "dataset",
    "E6_domain_intelligence": "dataset",
}


def _engine_source_type(family: str) -> str:
    return _ENGINE_SOURCE_TYPES.get(family, "other")


def _title_of(rec: "EvidenceRecord") -> str:
    span = rec.exact_span
    if span.field == "title_text" and span.text:
        return span.text[:300]
    if span.document_ref:
        return f"{rec.source_identity.source_id}:{span.document_ref}"
    return f"{span.dataset_id} row {span.row_idx} ({span.field})"


def make_evidence_id(dataset_id: str, config: str, split: str,
                     row_idx: int, field_name: str, text_sha256: str) -> str:
    """Deterministic evidence identity: the same bytes at the same
    location are the same evidence; different bytes are different
    evidence. No randomness, no timestamps (Art. VI)."""
    basis = f"{dataset_id}|{config}|{split}|{row_idx}|{field_name}|{text_sha256}"
    return "ev:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def build_evidence_record(
        *,
        source: Dict[str, Any],
        row: Dict[str, Any],
        row_idx: int,
        text_field: str,
        document_field: str,
        retrieval_endpoint: str,
        connector_state: str,
        license_verified: bool,
        license_basis: str,
        card_license: Optional[str],
        origin_description: str,
        measurement_fields: Optional[List[str]] = None,
        retrieval_query: str = "") -> Optional[EvidenceRecord]:
    """Normalize ONE source row into the canonical representation.

    `source` is a registry entry (EVIDENCE_SOURCE_REGISTRY.json record);
    `row` is the raw row dict from the datasets-server response. The span
    text is the row's text_field value, hashed WHOLE (a truncated span is
    a different span); the display copy may be bounded.
    measurement_fields: for structured (filter-mode) sources, the row's
    numeric/identity columns recorded as same-row measurements (each
    verifiable by the same row re-fetch — the custody chain covers them).
    Returns None when the row lacks the text field (schema-invalid ->
    recorded by the caller as BLOCKED_SCHEMA_INVALID in the run report,
    never silently dropped).
    """
    text = row.get(text_field)
    if text is None or not str(text).strip():
        return None
    text = str(text)
    text_sha = sha256_text(text)
    doc_ref = str(row.get(document_field) or "") or ""
    dataset_id = str(source.get("dataset_id") or source.get("source_id", ""))
    config = str(source.get("config") or "default")
    split = str(source.get("split") or "train")
    span = ExactSpan(
        dataset_id=dataset_id, config=config, split=split, row_idx=row_idx,
        field=text_field, text=text[:SPAN_DISPLAY_LIMIT], text_sha256=text_sha,
        document_ref=doc_ref, truncated=len(text) > SPAN_DISPLAY_LIMIT,
        retrieval_query=retrieval_query)
    ident = SourceIdentity(
        source_id=str(source.get("source_id", "")),
        family=str(source.get("family", "")),
        url=str(source.get("source_url", "")),
        dataset_revision=str(source.get("dataset_revision") or ""),
        retrieval_endpoint=retrieval_endpoint,
        connector_state=connector_state)
    prov = Provenance(
        origin_description=origin_description,
        card_license=card_license,
        license_verified=license_verified,
        license_basis=license_basis)
    if not license_verified:
        adm = Admissibility(state="BLOCKED_LICENSE_UNVERIFIED",
                            reasons=["source license/access state not "
                                     "verified in the registry (fail-closed)"])
    else:
        adm = Admissibility(state="PENDING_RELEVANCE",
                            reasons=["relevance adjudication pending"])
    measurements: List[Dict[str, Any]] = []
    for mf in (measurement_fields or []):
        if mf in row and row[mf] is not None:
            measurements.append({
                "field": mf,
                "value": row[mf],
                "basis": "same-row column (verifiable by the identical "
                         "row re-fetch as the span)",
            })
    return EvidenceRecord(
        evidence_id=make_evidence_id(dataset_id, config, split, row_idx,
                                     text_field, text_sha),
        source_identity=ident,
        source_version=(f"{ident.dataset_revision}@{config}/{split}"
                        if ident.dataset_revision else f"{config}/{split}"),
        source_type=ident.family or "E6_domain_intelligence",
        retrieval_timestamp=utc_now(),
        content_hash=text_sha,
        exact_span=span,
        measurements=measurements,
        provenance=prov,
        admissibility=adm)


def verify_span_custody(record: Dict[str, Any],
                        refetched_row: Optional[Dict[str, Any]],
                        search_rows: Optional[List[Dict[str, Any]]] = None
                        ) -> Dict[str, Any]:
    """The skeptic's backward trace (directive Phase 7).

    VERIFICATION IS ENDPOINT-AWARE (measured live this round):
      - /filter-served records: row_idx aligns with /rows offsets
        (verified: QM9 filter row_idx == /rows offset) -> the pinned
        row is re-fetched and the span bytes compared directly.
      - /search-served records: row_idx is NOT a stable address — the
        datasets-server's search index numbers rows differently from
        the /rows storage order (measured: colabfit search row_idx
        2131 = Cu3P while /rows offset 2131 = C3N; WOPTO returned
        different row_idx for the SAME publication across nodes
        minutes apart) -> verification anchors on document_ref inside
        a re-issued search, and the row_idx stays recorded as
        retrieval provenance, never as a stable address.

    This function NEVER trusts the record's own claim about its bytes
    (Art. III): it compares re-fetched bytes. A missing re-fetch is
    UNKNOWN, never pass (Art. XXV).
    """
    span = (record.get("exact_span") or {})
    endpoint = ((record.get("source_identity") or {})
                .get("retrieval_endpoint") or "")
    text_sha = span.get("text_sha256")
    doc_ref = span.get("document_ref") or ""
    # ---- basis 1: pinned-row re-fetch (filter-mode records) ----------
    if refetched_row is not None:
        text = refetched_row.get(span.get("field", ""))
        if text is None:
            return {"verdict": "FAIL", "basis": "ROW_IDX",
                    "reason": "field absent in refetched row"}
        sha = sha256_text(str(text))
        ok = sha == text_sha
        return {"verdict": "PASS" if ok else "FAIL",
                "basis": "ROW_IDX",
                "refetched_sha256": sha,
                "recorded_sha256": text_sha,
                "reason": "" if ok else "span bytes differ at pinned "
                                          "location"}
    # ---- basis 2: document-anchored search re-issue -------------------
    if search_rows:
        want_field = span.get("field", "")
        doc_field = _doc_field_of(record)
        for r in search_rows:
            row = (r.get("row") or {}) if isinstance(r, dict) else {}
            if doc_field and doc_ref and \
                    str(row.get(doc_field) or "") == doc_ref:
                text = row.get(want_field)
                if text is None:
                    return {"verdict": "FAIL",
                            "basis": "DOCUMENT_ANCHORED",
                            "reason": "document found but span field "
                                      "absent"}
                sha = sha256_text(str(text))
                ok = sha == text_sha
                return {"verdict": "PASS" if ok else "FAIL",
                        "basis": "DOCUMENT_ANCHORED",
                        "refetched_sha256": sha,
                        "recorded_sha256": text_sha,
                        "reason": "" if ok else
                                  "document found but span bytes differ"}
        return {"verdict": "UNKNOWN", "basis": "DOCUMENT_ANCHORED",
                "reason": "document_ref not present in the re-issued "
                          "search results (index state or ranking "
                          "drift — UNKNOWN, never a forgery claim)"}
    return {"verdict": "UNKNOWN",
            "basis": endpoint or "UNSPECIFIED",
            "reason": "row not re-fetched"}


#: which column is the document identity, per registry source_id (the
#: registry is the authority; this map is the loader-side fallback for
#: already-serialized records)
_DOC_FIELDS = {
    "wopto": "publication_number",
    "uspto_patents": "id",
    "colabfit_mp": "property_id",
    "lemat_rho": "immutable_id",
    "qm9": "mol_id",
    "chemrag_reactions": "id",
    "openfoam_cases": "text",
}


def _doc_field_of(record: Dict[str, Any]) -> str:
    sid = (record.get("source_identity") or {}).get("source_id") or ""
    return _DOC_FIELDS.get(sid, "id")


SCHEMA_JSON = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/prateekm1007/discovery-evidence-fabric/"
           "discovery_fabric/evidence_fabric/evidence_record",
    "title": "EvidenceRecord",
    "description": (
        "The ONE canonical evidence representation for every source "
        "(R449 directive Phase 3). Interpretation fields (proposition, "
        "technical_entities, mechanisms, measurements, conditions, "
        "citations) are CLAIMS about the span; exact_span is custody "
        "(Art. II/III: the LLM may interpret the span, never redefine "
        "it). Admissibility is fail-closed."),
    "type": "object",
    "required": ["evidence_id", "source_identity", "source_version",
                 "source_type", "retrieval_timestamp", "content_hash",
                 "exact_span", "provenance", "admissibility"],
    "properties": {
        "evidence_id": {"type": "string",
                        "pattern": "^ev:[0-9a-f]{24}$"},
        "source_identity": {"type": "object",
                            "required": ["source_id", "family", "url",
                                         "dataset_revision"],
                            "properties": {
                                "source_id": {"type": "string"},
                                "family": {"enum": SOURCE_FAMILIES},
                                "url": {"type": "string"},
                                "dataset_revision": {"type": "string"},
                                "retrieval_endpoint": {"type": "string"},
                                "connector_state": {"type": "string"}}},
        "source_version": {"type": "string"},
        "source_type": {"enum": SOURCE_FAMILIES},
        "retrieval_timestamp": {"type": "string"},
        "content_hash": {"type": "string",
                         "pattern": "^[0-9a-f]{64}$"},
        "exact_span": {"type": "object",
                       "required": ["dataset_id", "config", "split",
                                    "row_idx", "field", "text",
                                    "text_sha256"],
                       "properties": {
                           "dataset_id": {"type": "string"},
                           "config": {"type": "string"},
                           "split": {"type": "string"},
                           "row_idx": {"type": "integer", "minimum": 0},
                           "field": {"type": "string"},
                           "text": {"type": "string"},
                           "text_sha256": {"type": "string",
                                           "pattern": "^[0-9a-f]{64}$"},
                           "document_ref": {"type": "string"},
                           "truncated": {"type": "boolean"}}},
        "proposition": {"type": "string"},
        "technical_entities": {"type": "array", "items": {"type": "string"}},
        "mechanisms": {"type": "array", "items": {"type": "string"}},
        "measurements": {"type": "array",
                         "items": {"type": "object"}},
        "conditions": {"type": "array", "items": {"type": "string"}},
        "citations": {"type": "array", "items": {"type": "string"}},
        "provenance": {"type": "object",
                       "required": ["origin_description", "license_verified",
                                    "license_basis"],
                       "properties": {
                           "origin_description": {"type": "string"},
                           "card_license": {"type": ["string", "null"]},
                           "license_verified": {"type": "boolean"},
                           "license_basis": {"enum": [
                               "UNVERIFIED", "CARD_DECLARATION_ONLY",
                               "LICENSE_FILE"]},
                           "retrieved_via": {"type": "string"},
                           "cross_source_corroboration": {
                               "type": "string"}}},
        "admissibility": {"type": "object",
                          "required": ["state"],
                          "properties": {
                              "state": {"enum": ADMISSIBILITY_STATES},
                              "reasons": {"type": "array",
                                          "items": {"type": "string"}}}},
        "relevance": {"type": "object"},
    },
}


def validate_record(record: Dict[str, Any]) -> List[str]:
    """Hermetic structural validation (no jsonschema dependency at engine
    runtime; the same rules as SCHEMA_JSON, hand-enforced — returns the
    violation list, empty = valid)."""
    errors: List[str] = []
    eid = record.get("evidence_id")
    if not isinstance(eid, str) or not eid.startswith("ev:") or \
            len(eid) != 27:
        errors.append("evidence_id malformed")
    si = record.get("source_identity") or {}
    for k in ("source_id", "family", "url", "dataset_revision"):
        if not si.get(k):
            errors.append(f"source_identity.{k} missing")
    if si.get("family") not in SOURCE_FAMILIES:
        errors.append("source_identity.family not in vocabulary")
    if record.get("source_type") not in SOURCE_FAMILIES:
        errors.append("source_type not in vocabulary")
    span = record.get("exact_span") or {}
    for k in ("dataset_id", "config", "split", "field", "text",
              "text_sha256"):
        if not span.get(k) and span.get(k) != 0:
            errors.append(f"exact_span.{k} missing")
    if not isinstance(span.get("row_idx"), int) or span.get("row_idx", -1) < 0:
        errors.append("exact_span.row_idx invalid")
    ch = record.get("content_hash")
    if not isinstance(ch, str) or len(ch) != 64:
        errors.append("content_hash malformed")
    elif span.get("text_sha256") and ch != span.get("text_sha256"):
        errors.append("content_hash != exact_span.text_sha256 (span "
                      "custody broken — the record hash must BE the span "
                      "hash)")
    prov = record.get("provenance") or {}
    if not prov.get("license_basis"):
        errors.append("provenance.license_basis missing")
    adm = (record.get("admissibility") or {})
    if adm.get("state") not in ADMISSIBILITY_STATES:
        errors.append("admissibility.state not in vocabulary")
    return errors
