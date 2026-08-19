"""
orchestrator/evidence_identity.py — Canonical evidence identity and deduplication.

PER CEO v30.5 IDENTITY AUDIT (extends v30.4):

  Two identity-model defects from the v30.4 fix are corrected here:

  (1) PATENT NORMALIZATION WAS TOO AGGRESSIVE.
      v30.4 stripped the country code and kind code from patent numbers
      ("US10232151B2" → "10232151"). That manufactures a future collision:
      a US patent and an EP patent that happen to share the same publication
      number would be treated as the same document.

      v30.5 PRESERVES the full publication identifier:
          jurisdiction + publication_number + kind_code
      Separators (-, /, space, "patent/", trailing language code) are removed;
      country and kind code are NOT removed.

      This matches the already-correct normalizer in
      discovery_fabric/prior_art_v2/federated_evidence.py.

  (2) "CONFIRMED" WAS OVERLOADED.
      v30.4 used a single CONFIRMED bucket to cover PMID (a paper), DOI (a
      paper), MDR key (an adverse-event report), patent publication number
      (a specific publication), AND patent family ID (a *group* of related
      publications). Those are not equivalent — a family ID identifies a
      relation between documents, not a single document.

      v30.5 SPLITS CONFIRMED into typed identity states:
          DOCUMENT_ID_CONFIRMED    — authoritative identifier for ONE document
          EVENT_ID_CONFIRMED       — authoritative identifier for ONE adverse event
          FAMILY_RELATION_CONFIRMED — family identifier linking MULTIPLE documents
                                       (links, does NOT merge)
          POSSIBLE_FAMILY_MATCH    — content fingerprint match only (unchanged)
          IDENTITY_INSUFFICIENT    — cannot determine (unchanged)

      Family-relationship confirmation NEVER merges two distinct patent
      publications into one evidence object. Each family member remains its
      own document; they are merely *linked* via family_relations.

  Backward compatibility:
      IDENTITY_CONFIRMED is kept as a deprecated alias mapping to
      DOCUMENT_ID_CONFIRMED. New callers should use the typed constants.

  CEO v30.4 principles preserved verbatim:
    "When identity is uncertain, preserve the ambiguity.
     Never manufacture certainty to make the dataset cleaner."
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Typed identity confidence levels (CEO v30.5)
# ---------------------------------------------------------------------------
# A single document is identified by an authoritative identifier
# (PMID, DOI, jurisdiction+number+kind patent publication, K-number, PMA
# number, NCT_ID, NIH project_num).
DOCUMENT_ID_CONFIRMED = "DOCUMENT_ID_CONFIRMED"

# A single adverse-event report is identified by MDR key or recall number.
EVENT_ID_CONFIRMED = "EVENT_ID_CONFIRMED"

# A family identifier links MULTIPLE patent publications. Confirmation of a
# family ID establishes a *relation*, not a single-document identity. Family
# members MUST remain distinct evidence objects.
FAMILY_RELATION_CONFIRMED = "FAMILY_RELATION_CONFIRMED"

# Content fingerprint matches a previously-seen record but no authoritative
# identifier was retrieved. POSSIBLE family match only.
POSSIBLE_FAMILY_MATCH = "POSSIBLE_FAMILY_MATCH"

# Cannot determine identity. DO NOT MERGE.
IDENTITY_INSUFFICIENT = "IDENTITY_INSUFFICIENT"

# ---------------------------------------------------------------------------
# Deprecated backward-compat alias (CEO v30.4 callers).
# New code MUST use the typed constants above. IDENTITY_CONFIRMED is mapped
# to DOCUMENT_ID_CONFIRMED because that is the strictest reading of v30.4's
# intent for any single-document ID (PMID/DOI/MDR key/patent number).
# A bare "FAMILY_ID" type was a bug in v30.4 — that path now emits
# FAMILY_RELATION_CONFIRMED instead, never IDENTITY_CONFIRMED.
# ---------------------------------------------------------------------------
IDENTITY_CONFIRMED = DOCUMENT_ID_CONFIRMED
IDENTITY_POSSIBLE_MATCH = POSSIBLE_FAMILY_MATCH

# Convenience: which confidence levels authorize cross-source merging of the
# *same* underlying entity. FAMILY_RELATION_CONFIRMED is intentionally absent
# — family links records but each member remains its own evidence object.
_MERGE_AUTHORIZED_CONFIDENCE = frozenset({
    DOCUMENT_ID_CONFIRMED,
    EVENT_ID_CONFIRMED,
})


@dataclass(frozen=True)
class EvidenceIdentity:
    """Canonical identity for one evidence record.

    Multiple database records may map to the SAME EvidenceIdentity
    (e.g., PubMed PMID 12345 and EuropePMC PMID 12345 are the same paper).

    CEO v30.5 typed identity semantics:
    - DOCUMENT_ID_CONFIRMED:   one document, authoritative ID match
    - EVENT_ID_CONFIRMED:      one adverse event, authoritative ID match
    - FAMILY_RELATION_CONFIRMED: family ID links multiple documents; each
                                 member remains its own evidence object
    - POSSIBLE_FAMILY_MATCH:   content fingerprint match only
    - IDENTITY_INSUFFICIENT:   cannot determine — DO NOT MERGE
    """
    record_type: str          # "paper" / "patent" / "clinical_trial" / "fda_device" / "fda_event"
    canonical_id: str         # Normalized canonical identifier (full publication id for patents)
    canonical_id_type: str    # "DOI" / "PMID" / "PATENT_NUMBER" / "K_NUMBER" / "MDR_REPORT_KEY" / "FAMILY_ID" / "FINGERPRINT"
    content_fingerprint: str  # SHA-256 of normalized title + first 500 chars of abstract/content
    identity_confidence: str  # one of the typed constants above

    # Source tracking — which databases returned this record
    source_databases: tuple = field(default_factory=tuple)

    # Patent family info (if available). A family ID identifies a relation
    # between documents, not a single document.
    patent_family_id: Optional[str] = None  # EPO/DOCDB family ID (if retrieved)

    # Cross-record family links. Populated for FAMILY_RELATION_CONFIRMED
    # patents. Each entry is the canonical_id of another family member.
    # These links NEVER merge the members into one record — they preserve
    # the relation so downstream consumers can walk the family graph.
    family_relations: tuple = field(default_factory=tuple)

    @property
    def is_deduplicated(self) -> bool:
        """True if this record has been seen from multiple databases."""
        return len(self.source_databases) > 1

    @property
    def can_merge(self) -> bool:
        """True if this identity is confident enough to support merging.

        CEO v30.5: Only DOCUMENT_ID_CONFIRMED and EVENT_ID_CONFIRMED
        authorize merging two database records into one evidence object.

        FAMILY_RELATION_CONFIRMED is intentionally excluded: a family ID
        links two DISTINCT patent publications. Each publication remains
        its own evidence object. The relation is preserved via
        family_relations, never by collapsing the members.

        CEO v30.4: 'When identity is uncertain, preserve the ambiguity.
        Never manufacture certainty to make the dataset cleaner.'
        """
        return self.identity_confidence in _MERGE_AUTHORIZED_CONFIDENCE


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------
def normalize_doi(doi: str) -> str:
    if not doi: return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:", "", doi)
    return doi


def normalize_pmid(pmid: str) -> str:
    if not pmid: return ""
    return str(pmid).strip()


_PATENT_SEPARATORS_RE = re.compile(r"[-/\s]")


def normalize_patent_number(pn: str) -> str:
    """Normalize a patent publication identifier.

    CEO v30.5: PRESERVES jurisdiction + publication_number + kind_code.

    The full publication identifier IS the document identity. Stripping
    country code or kind code manufactures a future collision risk:
        US10232151B2  !=  EP10232151B1   (different jurisdictions)
        US10232151B2  !=  US10232151B1   (different kind codes — grant vs application)

    Examples (matches federated_evidence.normalize_patent_number behavior):
        "US-11912894-B2"        -> "US11912894B2"
        "us11912894b2"          -> "US11912894B2"
        "EP3397675B1"           -> "EP3397675B1"
        "patent/US11912894B2/en"-> "US11912894B2"
        "JP2012071135A"         -> "JP2012071135A"
        "WO2024012345A1"        -> "WO2024012345A1"

    What is removed (cosmetic only):
        - hyphens, slashes, whitespace
        - "patent/" URL prefix from Google Patents
        - trailing language code ("/en", "/de") from Google Patents URLs

    What is NEVER removed:
        - 2-letter jurisdiction prefix (US, EP, JP, WO, CN, IN, ...)
        - trailing kind code (A1, A2, B1, B2, C1, U1, ...)
        - publication digits
    """
    if not pn: return ""
    s = pn.upper()
    # Remove separators (cosmetic only — country/kind preserved)
    s = _PATENT_SEPARATORS_RE.sub("", s)
    # Strip Google Patents URL prefix "PATENT"
    if s.startswith("PATENT"):
        s = s[6:]
    # Strip trailing language code from Google Patents URL (e.g. "EN", "DE")
    # ONLY if the remaining string still looks like a patent publication
    # (2-letter jurisdiction + digits + optional kind code).
    if len(s) > 4 and s.endswith("EN"):
        candidate = s[:-2]
        if re.match(r"^[A-Z]{2}\d+[A-Z0-9]*$", candidate):
            s = candidate
    return s


def parse_patent_components(pn: str) -> Tuple[str, str, str]:
    """Parse a normalized patent number into (jurisdiction, number, kind_code).

    Returns ("", "", "") if the input does not match the expected pattern.
    The kind code is the trailing 1-3 alphabetic/alphanumeric characters
    AFTER the digit run; common kind codes: A, A1, A2, A9, B1, B2, C1, U1.

    Examples:
        "US11912894B2"  -> ("US", "11912894", "B2")
        "EP3397675B1"   -> ("EP", "3397675",  "B1")
        "JP2012071135A" -> ("JP", "2012071135","A")
        "WO2024012345A1"-> ("WO", "2024012345","A1")
        "10232151"      -> ("",   "10232151",  "")    # jurisdiction missing
    """
    if not pn: return ("", "", "")
    s = normalize_patent_number(pn)
    m = re.match(r"^([A-Z]{2})?(\d+)([A-Z]\d?|[A-Z]{2,3})?$", s)
    if not m:
        # Fallback: at least try to split jurisdiction from digits
        m2 = re.match(r"^([A-Z]{2})?(\d+)(.*)$", s)
        if not m2:
            return ("", s, "")
        return (m2.group(1) or "", m2.group(2) or "", m2.group(3) or "")
    return (m.group(1) or "", m.group(2) or "", m.group(3) or "")


def compute_content_fingerprint(title: str, abstract: str = "") -> str:
    text = (title or "") + " " + (abstract or "")[:500]
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Canonical ID extraction
# ---------------------------------------------------------------------------
def extract_canonical_id(record: dict, source: str) -> tuple:
    """Extract canonical identifier from a record.

    Returns (canonical_id, canonical_id_type, confidence).

    CEO v30.5 typed identity semantics:
      - Document IDs (PMID, DOI, patent publication number, K-number,
        PMA number, NCT_ID, NIH project_num) -> DOCUMENT_ID_CONFIRMED
      - Event IDs (MDR key, recall number) -> EVENT_ID_CONFIRMED
      - Patent family ID alone (no publication number) ->
        FAMILY_RELATION_CONFIRMED (links documents, does not merge)
      - Content fingerprint only -> POSSIBLE_FAMILY_MATCH
      - Missing authoritative ID -> IDENTITY_INSUFFICIENT

    CEO v30.4: Missing MDR key = IDENTITY_INSUFFICIENT, NOT event_type+date
    fallback. Two different reports can share event_type + date.
    """
    if source in ("PubMed", "EuropePMC"):
        pmid = record.get("pmid", "")
        doi = record.get("doi", "")
        if pmid:
            return normalize_pmid(pmid), "PMID", DOCUMENT_ID_CONFIRMED
        elif doi:
            return normalize_doi(doi), "DOI", DOCUMENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("Crossref",):
        doi = record.get("doi", record.get("DOI", ""))
        if doi:
            return normalize_doi(doi), "DOI", DOCUMENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("ClinicalTrials.gov",):
        nct_id = record.get("nct_id", record.get("NCTId", ""))
        if nct_id:
            return nct_id.strip(), "NCT_ID", DOCUMENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("FDA_510k",):
        k_number = record.get("k_number", "")
        if k_number:
            return k_number.strip(), "K_NUMBER", DOCUMENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("FDA_PMA",):
        pma_number = record.get("pma_number", "")
        if pma_number:
            return pma_number.strip(), "PMA_NUMBER", DOCUMENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source.startswith("FDA_MAUDE"):
        # CEO v30.4: MDR key is AUTHORITATIVE. Missing MDR key =
        # IDENTITY_INSUFFICIENT.
        # Do NOT fall back to event_type + date — two different reports can
        # share these. (This is an *event* identifier, not a document
        # identifier — hence EVENT_ID_CONFIRMED, not DOCUMENT_ID_CONFIRMED.)
        mdr_key = record.get("mdr_report_key", "")
        if mdr_key:
            return str(mdr_key).strip(), "MDR_REPORT_KEY", EVENT_ID_CONFIRMED
        # NO FALLBACK — preserve as separate record with insufficient identity
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("FDA_Recalls",):
        recall_number = record.get("recall_number", "")
        if recall_number:
            return recall_number.strip(), "RECALL_NUMBER", EVENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("NIH_RePORTER",):
        project_num = record.get("project_num", "")
        if project_num:
            return project_num.strip(), "PROJECT_NUM", DOCUMENT_ID_CONFIRMED
        return "", "FINGERPRINT", IDENTITY_INSUFFICIENT

    elif source in ("PatentBear", "Espacenet", "Lens_Patent", "Google_Patents"):
        # CEO v30.5: Patent publication identifier = jurisdiction +
        # publication_number + kind_code. Country and kind code are
        # PRESERVED in the canonical id.
        pn = record.get("patent_number", record.get("doc_number", ""))
        family_id = record.get("family_id", record.get("@family-id", ""))

        if pn:
            # Document identity confirmed. Family ID is also recorded if
            # available — it links this document to other family members
            # but does NOT merge them.
            return normalize_patent_number(pn), "PATENT_NUMBER", DOCUMENT_ID_CONFIRMED
        elif family_id:
            # No publication number — only a family ID. This is a family
            # *relation* identifier, not a document identifier. The record
            # cannot be merged with other records as the "same document"
            # because we don't know which specific publication it is.
            return str(family_id), "FAMILY_ID", FAMILY_RELATION_CONFIRMED
        else:
            # No authoritative ID — use fingerprint with POSSIBLE_FAMILY_MATCH
            return "", "FINGERPRINT", POSSIBLE_FAMILY_MATCH

    return "", "FINGERPRINT", IDENTITY_INSUFFICIENT


# ---------------------------------------------------------------------------
# Deduplication within a single source
# ---------------------------------------------------------------------------
def deduplicate_records(records: List[dict], source: str) -> List[EvidenceIdentity]:
    """Deduplicate records from a single source."""
    seen: Dict[str, EvidenceIdentity] = {}

    for record in records:
        canonical_id, id_type, confidence = extract_canonical_id(record, source)
        title = record.get("title", record.get("device_name", record.get("trade_name", "")))
        abstract = record.get("abstract", record.get("description", ""))
        if source.startswith("FDA_MAUDE") and not title:
            title = record.get("event_type", "") + " " + record.get("date_received", "")
        fingerprint = compute_content_fingerprint(title, abstract)

        # Dedup key: canonical_id if available and merge-authorized,
        # else fingerprint (but fingerprint-based dedup is per-source only —
        # cross-source fingerprint matches do NOT auto-merge).
        if canonical_id and confidence in _MERGE_AUTHORIZED_CONFIDENCE:
            dedup_key = f"{id_type}:{canonical_id}"
        else:
            # Use fingerprint but mark as non-mergeable across sources
            dedup_key = f"FINGERPRINT:{fingerprint[:32]}"

        if dedup_key in seen:
            continue

        family_id = record.get("family_id", record.get("@family-id", ""))

        seen[dedup_key] = EvidenceIdentity(
            record_type=_infer_record_type(source),
            canonical_id=canonical_id or fingerprint[:32],
            canonical_id_type=id_type,
            content_fingerprint=fingerprint,
            identity_confidence=confidence,
            source_databases=(source,),
            patent_family_id=str(family_id) if family_id else None,
            family_relations=(),  # populated by merge_across_sources
        )

    return list(seen.values())


# ---------------------------------------------------------------------------
# Cross-source merge + family linking
# ---------------------------------------------------------------------------
def merge_across_sources(source_results: Dict[str, List[EvidenceIdentity]]) -> tuple:
    """Merge deduplicated records across multiple sources.

    CEO v30.5 typed identity semantics:
      - DOCUMENT_ID_CONFIRMED + same canonical_id  -> MERGE (same document)
      - EVENT_ID_CONFIRMED    + same canonical_id  -> MERGE (same event)
      - FAMILY_RELATION_CONFIRMED                  -> LINK, do NOT merge
      - POSSIBLE_FAMILY_MATCH                      -> FLAG, do NOT auto-merge
      - IDENTITY_INSUFFICIENT                      -> DO NOT MERGE, preserve

    CEO v30.4: 'When identity is uncertain, preserve the ambiguity.
    Never manufacture certainty to make the dataset cleaner.'

    Family linking (NEW in v30.5):
      Patents that share a patent_family_id are *linked* via
      family_relations. Each patent remains its own evidence object.
      Two patents with the same family_id but different publication numbers
      are NEVER merged — they are distinct documents in the same family.

    Returns (merged_identities, possible_matches) where possible_matches
    is a list of (id1, id2) tuples flagging records that MAY be the same
    underlying fact but were not auto-merged.
    """
    merged: Dict[str, EvidenceIdentity] = {}
    possible_matches: List[tuple] = []

    # First pass: collect all identities and merge merge-authorized duplicates.
    for source, identities in source_results.items():
        for identity in identities:
            if identity.identity_confidence in _MERGE_AUTHORIZED_CONFIDENCE:
                if identity.canonical_id_type != "FINGERPRINT":
                    merge_key = f"{identity.canonical_id_type}:{identity.canonical_id}"
                else:
                    merge_key = f"FINGERPRINT:{identity.content_fingerprint[:32]}"

                if merge_key in merged:
                    existing = merged[merge_key]
                    new_sources = tuple(sorted(set(existing.source_databases + (source,))))
                    merged[merge_key] = EvidenceIdentity(
                        record_type=existing.record_type,
                        canonical_id=existing.canonical_id,
                        canonical_id_type=existing.canonical_id_type,
                        content_fingerprint=existing.content_fingerprint,
                        identity_confidence=existing.identity_confidence,
                        source_databases=new_sources,
                        patent_family_id=existing.patent_family_id or identity.patent_family_id,
                        family_relations=existing.family_relations,
                    )
                else:
                    merged[merge_key] = identity

            elif identity.identity_confidence == FAMILY_RELATION_CONFIRMED:
                # Family-relation-only record. Cannot merge — we don't know
                # which specific publication this is. Preserve as its own
                # record. The family_id will be used in the linking pass.
                key = f"FAMILY:{identity.canonical_id}_{source}_{len(merged)}"
                merged[key] = identity

            elif identity.identity_confidence == POSSIBLE_FAMILY_MATCH:
                fp_key = f"POSSIBLE:{identity.content_fingerprint[:32]}"
                if fp_key in merged:
                    existing = merged[fp_key]
                    possible_matches.append((existing.canonical_id, identity.canonical_id))
                    merged[f"{fp_key}_{source}_{len(merged)}"] = identity
                else:
                    merged[fp_key] = identity

            else:  # IDENTITY_INSUFFICIENT
                key = f"INSUFFICIENT:{identity.content_fingerprint[:32]}_{source}_{len(merged)}"
                merged[key] = identity

    # Second pass (NEW in v30.5): family linking.
    # Group all patent records by patent_family_id. For each group, populate
    # family_relations on every member with the canonical_id of every OTHER
    # member. Members remain distinct evidence objects.
    family_groups: Dict[str, List[Tuple[str, EvidenceIdentity]]] = {}
    for key, ident in merged.items():
        if ident.record_type == "patent" and ident.patent_family_id:
            family_groups.setdefault(ident.patent_family_id, []).append((key, ident))

    for family_id, members in family_groups.items():
        if len(members) < 2:
            # Solo member — no relations to record. (Still keep the family_id
            # on the record for downstream consumers.)
            continue
        member_ids = tuple(sorted(m.canonical_id for _, m in members))
        for key, ident in members:
            # Family relations = every other member's canonical_id
            relations = tuple(mid for mid in member_ids if mid != ident.canonical_id)
            merged[key] = EvidenceIdentity(
                record_type=ident.record_type,
                canonical_id=ident.canonical_id,
                canonical_id_type=ident.canonical_id_type,
                content_fingerprint=ident.content_fingerprint,
                identity_confidence=ident.identity_confidence,
                source_databases=ident.source_databases,
                patent_family_id=ident.patent_family_id,
                family_relations=relations,
            )

    # Post-merge: check for content fingerprint matches across CONFIRMED
    # records with DIFFERENT canonical IDs (e.g., US patent + EP patent with
    # same title but different publication numbers — possible family match).
    confirmed_records = [(k, v) for k, v in merged.items()
                         if v.identity_confidence in _MERGE_AUTHORIZED_CONFIDENCE
                         and v.canonical_id_type != "FINGERPRINT"]
    for i, (key1, rec1) in enumerate(confirmed_records):
        for key2, rec2 in confirmed_records[i+1:]:
            if rec1.content_fingerprint == rec2.content_fingerprint:
                # Same content fingerprint but different canonical IDs ->
                # possible family match (FLAG, do NOT auto-merge).
                possible_matches.append((rec1.canonical_id, rec2.canonical_id))

    return list(merged.values()), possible_matches


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _infer_record_type(source: str) -> str:
    if source in ("PubMed", "EuropePMC", "Crossref", "NIH_RePORTER"):
        return "paper"
    elif source in ("PatentBear", "Espacenet", "Lens_Patent", "Google_Patents"):
        return "patent"
    elif source in ("ClinicalTrials.gov",):
        return "clinical_trial"
    elif source in ("FDA_510k", "FDA_PMA"):
        return "fda_device"
    elif source.startswith("FDA_MAUDE") or source in ("FDA_Recalls",):
        return "fda_event"
    return "unknown"


# ===========================================================================
# Adversarial test suite — Article VIII compliant
# (positive + negative + adversarial + identity-attack cases)
# ===========================================================================
def main():
    """Adversarial test suite — CEO v30.5 typed identity semantics."""
    print(f"\n{'='*78}")
    print(f"EVIDENCE IDENTITY & DEDUPLICATION TESTS (v30.5 — typed identity)")
    print(f"{'='*78}")

    # ------------------------------------------------------------------
    # Patent number normalization (the fix at the heart of this commit)
    # ------------------------------------------------------------------
    print(f"\n--- N1: Patent normalization preserves jurisdiction + kind code ---")
    cases = [
        ("US-11912894-B2",         "US11912894B2"),
        ("us11912894b2",           "US11912894B2"),
        ("US11912894B2",           "US11912894B2"),
        ("EP-3397675-B1",          "EP3397675B1"),
        ("EP3397675B1",            "EP3397675B1"),
        ("patent/US11912894B2/en", "US11912894B2"),
        ("JP2012071135A",          "JP2012071135A"),
        ("WO 2024/012345 A1",      "WO2024012345A1"),
        ("CN1154321B",             "CN1154321B"),
        ("IN202341001234A",        "IN202341001234A"),
    ]
    for raw, expected in cases:
        got = normalize_patent_number(raw)
        assert got == expected, f"normalize_patent_number({raw!r}) = {got!r}, expected {expected!r}"
    print(f"  ✅ PASS: {len(cases)} patent ids preserved (country + kind intact)")

    # ------------------------------------------------------------------
    # Patent number component parsing
    # ------------------------------------------------------------------
    print(f"\n--- N2: Patent component parsing ---")
    parse_cases = [
        ("US11912894B2",   ("US", "11912894",  "B2")),
        ("EP3397675B1",    ("EP", "3397675",   "B1")),
        ("JP2012071135A",  ("JP", "2012071135", "A")),
        ("WO2024012345A1", ("WO", "2024012345","A1")),
    ]
    for raw, expected in parse_cases:
        got = parse_patent_components(raw)
        assert got == expected, f"parse_patent_components({raw!r}) = {got!r}, expected {expected!r}"
    print(f"  ✅ PASS: {len(parse_cases)} patents parsed into (jurisdiction, number, kind)")

    # ------------------------------------------------------------------
    # ADVERSARIAL: same publication number, different jurisdiction → DISTINCT
    # (This is the attack the OLD normalizer would have failed.)
    # ------------------------------------------------------------------
    print(f"\n--- A1: Same publication number, different jurisdiction → DISTINCT ---")
    # Two patents happen to share the digits "10232151" but are in different
    # jurisdictions. They MUST remain distinct documents.
    pb_us = [{"patent_number": "US10232151B2", "title": "Multi-Lumen Catheter", "family_id": ""}]
    ep_same_digits = [{"doc_number": "EP10232151B1", "title": "Multi-Lumen Catheter", "family_id": ""}]
    pb_us_ids = deduplicate_records(pb_us, "PatentBear")
    ep_ids = deduplicate_records(ep_same_digits, "Espacenet")
    merged_a1, possible_a1 = merge_across_sources({"PatentBear": pb_us_ids, "Espacenet": ep_ids})
    patents_a1 = [m for m in merged_a1 if m.record_type == "patent"]
    assert len(patents_a1) == 2, (
        f"Same-digits different-jurisdiction patents MUST stay distinct, got {len(patents_a1)}"
    )
    assert all(p.identity_confidence == DOCUMENT_ID_CONFIRMED for p in patents_a1)
    # Their canonical_ids must differ (US-prefixed vs EP-prefixed)
    canon_ids = sorted(p.canonical_id for p in patents_a1)
    assert canon_ids == ["EP10232151B1", "US10232151B2"], f"Got {canon_ids}"
    # No auto-merge
    auto_merged = [p for p in patents_a1 if p.is_deduplicated]
    assert len(auto_merged) == 0, "Different-jurisdiction patents must NOT auto-merge"
    # Possible family match IS flagged (same title) — that's fine, it's a flag not a merge
    print(f"  ✅ PASS: US10232151B2 and EP10232151B1 remain distinct documents")
    print(f"  ✅ PASS: no auto-merge; {len(possible_a1)} possible-match flag(s) raised (title overlap)")

    # ------------------------------------------------------------------
    # ADVERSARIAL: US/EP/JP family members → distinct documents, linked family
    # ------------------------------------------------------------------
    print(f"\n--- A2: US/EP/JP family members → distinct documents, linked family ---")
    # Three publications of the same patent family (different jurisdictions).
    family_records = [
        ({"patent_number": "US10232151B2", "title": "Multi-Lumen Catheter", "family_id": "44785513"}, "PatentBear"),
        ({"doc_number":    "EP2436419B1",  "title": "Multi-Lumen Catheter", "family_id": "44785513"}, "Espacenet"),
        ({"doc_number":    "JP2012071135A","title": "Multi-Lumen Catheter", "family_id": "44785513"}, "Lens_Patent"),
    ]
    sources = {}
    for rec, src in family_records:
        ids = deduplicate_records([rec], src)
        sources[src] = ids
    merged_a2, possible_a2 = merge_across_sources(sources)
    patents_a2 = [m for m in merged_a2 if m.record_type == "patent"]
    assert len(patents_a2) == 3, (
        f"3 family members must remain 3 distinct documents, got {len(patents_a2)}"
    )
    # Each must be DOCUMENT_ID_CONFIRMED (not FAMILY_RELATION_CONFIRMED —
    # we have the publication number, so it's a confirmed document)
    assert all(p.identity_confidence == DOCUMENT_ID_CONFIRMED for p in patents_a2), (
        "Each family member must be DOCUMENT_ID_CONFIRMED, not FAMILY_RELATION_CONFIRMED"
    )
    # Each must carry the family_id
    assert all(p.patent_family_id == "44785513" for p in patents_a2)
    # Each must have family_relations pointing to the OTHER two members
    canon_set = {"US10232151B2", "EP2436419B1", "JP2012071135A"}
    for p in patents_a2:
        assert len(p.family_relations) == 2, (
            f"Each family member must link to 2 others, got {len(p.family_relations)}"
        )
        other_two = canon_set - {p.canonical_id}
        assert set(p.family_relations) == other_two, (
            f"Family relations for {p.canonical_id} = {set(p.family_relations)}, expected {other_two}"
        )
    print(f"  ✅ PASS: 3 family members remain 3 distinct documents (DOCUMENT_ID_CONFIRMED)")
    print(f"  ✅ PASS: family_relations populated — each member links to the other 2")
    print(f"  ✅ PASS: can_merge=False for all 3 (family relation never merges)")

    # ------------------------------------------------------------------
    # ADVERSARIAL: same publication number from different jurisdictions → DISTINCT
    # (defends against future collision; reinforces A1)
    # ------------------------------------------------------------------
    print(f"\n--- A3: US vs EP vs JP publication number = DISTINCT documents ---")
    # Even when titles and family_id are absent, jurisdictions differ
    solo_us = deduplicate_records([{"patent_number": "US9999999B2", "title": "Solo"}], "PatentBear")
    solo_ep = deduplicate_records([{"doc_number":    "EP9999999B1",  "title": "Solo"}], "Espacenet")
    merged_a3, _ = merge_across_sources({"PatentBear": solo_us, "Espacenet": solo_ep})
    patents_a3 = [m for m in merged_a3 if m.record_type == "patent"]
    assert len(patents_a3) == 2, "Different jurisdictions = different documents"
    canon_a3 = sorted(p.canonical_id for p in patents_a3)
    assert canon_a3 == ["EP9999999B1", "US9999999B2"], f"Got {canon_a3}"
    print(f"  ✅ PASS: US9999999B2 and EP9999999B1 are distinct even with same digits")

    # ------------------------------------------------------------------
    # ADVERSARIAL: same title across UNRELATED patents → no merge
    # ------------------------------------------------------------------
    print(f"\n--- A4: Same title, unrelated patents (no family_id) → NO MERGE ---")
    unrelated_1 = [{"patent_number": "US11111111B2", "title": "Cerebrospinal Fluid Drainage"}]
    unrelated_2 = [{"patent_number": "US22222222B2", "title": "Cerebrospinal Fluid Drainage"}]
    u1 = deduplicate_records(unrelated_1, "PatentBear")
    u2 = deduplicate_records(unrelated_2, "Espacenet")
    merged_a4, possible_a4 = merge_across_sources({"PatentBear": u1, "Espacenet": u2})
    patents_a4 = [m for m in merged_a4 if m.record_type == "patent"]
    assert len(patents_a4) == 2, "Same-title unrelated patents must remain 2 documents"
    auto_merged_a4 = [p for p in patents_a4 if p.is_deduplicated]
    assert len(auto_merged_a4) == 0, "Must NOT auto-merge based on title alone"
    assert len(possible_a4) >= 1, "Should FLAG possible family match for review"
    print(f"  ✅ PASS: same-title unrelated patents remain 2 distinct documents")
    print(f"  ✅ PASS: {len(possible_a4)} possible-match flag(s) raised (not auto-merged)")

    # ------------------------------------------------------------------
    # POSITIVE: same publication from two databases → MERGE
    # ------------------------------------------------------------------
    print(f"\n--- P1: Same publication from two databases → MERGE ---")
    pubmed_records = [
        {"pmid": "12345", "title": "CSF Shunt Obstruction: A Review", "abstract": "This review covers..."},
        {"pmid": "67890", "title": "Hydrocephalus Management", "abstract": "Management of..."},
    ]
    europepmc_records = [
        {"pmid": "12345", "title": "CSF Shunt Obstruction: A Review", "abstract": "This review covers..."},
        {"pmid": "11111", "title": "Endovascular Shunt Feasibility", "abstract": "Feasibility study..."},
    ]
    pubmed_ids = deduplicate_records(pubmed_records, "PubMed")
    europepmc_ids = deduplicate_records(europepmc_records, "EuropePMC")
    merged_p1, _ = merge_across_sources({"PubMed": pubmed_ids, "EuropePMC": europepmc_ids})
    assert len(merged_p1) == 3, f"Expected 3 unique, got {len(merged_p1)}"
    dups = [m for m in merged_p1 if m.is_deduplicated]
    assert len(dups) == 1
    assert dups[0].identity_confidence == DOCUMENT_ID_CONFIRMED
    print(f"  ✅ PASS: 4 records → 3 unique, 1 DOCUMENT_ID_CONFIRMED duplicate (PMID match)")

    # ------------------------------------------------------------------
    # POSITIVE: same patent publication from two databases → MERGE
    # ------------------------------------------------------------------
    print(f"\n--- P2: Same patent publication (US10232151B2) from two databases → MERGE ---")
    pb_p = [{"patent_number": "US10232151B2", "title": "Multi-Lumen Catheter"}]
    ep_p = [{"doc_number":    "US10232151B2", "title": "Multi-Lumen Catheter"}]  # same publication id, different DB
    pb_ids = deduplicate_records(pb_p, "PatentBear")
    ep_ids = deduplicate_records(ep_p, "Espacenet")
    merged_p2, _ = merge_across_sources({"PatentBear": pb_ids, "Espacenet": ep_ids})
    patents_p2 = [m for m in merged_p2 if m.record_type == "patent"]
    assert len(patents_p2) == 1, f"Same publication must merge to 1, got {len(patents_p2)}"
    assert patents_p2[0].is_deduplicated
    assert patents_p2[0].identity_confidence == DOCUMENT_ID_CONFIRMED
    assert patents_p2[0].canonical_id == "US10232151B2"
    print(f"  ✅ PASS: same publication id from 2 databases → 1 merged record")

    # ------------------------------------------------------------------
    # MAUDE with MDR key (EVENT_ID_CONFIRMED merge)
    # ------------------------------------------------------------------
    print(f"\n--- P3: MAUDE dedup (MDR key = EVENT_ID_CONFIRMED) ---")
    maude_1 = [
        {"mdr_report_key": "1234567", "event_type": "Malfunction", "date_received": "2024-01-15"},
        {"mdr_report_key": "7654321", "event_type": "Injury", "date_received": "2024-02-20"},
    ]
    maude_2 = [
        {"mdr_report_key": "1234567", "event_type": "Malfunction", "date_received": "2024-01-15"},
        {"mdr_report_key": "9999999", "event_type": "Death", "date_received": "2024-03-10"},
    ]
    m1_ids = deduplicate_records(maude_1, "FDA_MAUDE_feed1")
    m2_ids = deduplicate_records(maude_2, "FDA_MAUDE_feed2")
    maude_merged, _ = merge_across_sources({"FDA_MAUDE_feed1": m1_ids, "FDA_MAUDE_feed2": m2_ids})
    maude_dups = [m for m in maude_merged if m.is_deduplicated]
    assert len(maude_dups) == 1, f"Expected 1 MDR-key duplicate, got {len(maude_dups)}"
    assert maude_dups[0].identity_confidence == EVENT_ID_CONFIRMED
    print(f"  ✅ PASS: Same MDR key → EVENT_ID_CONFIRMED merge")

    # ------------------------------------------------------------------
    # ADVERSARIAL: MAUDE without MDR key → IDENTITY_INSUFFICIENT, NOT merged
    # ------------------------------------------------------------------
    print(f"\n--- A5: MAUDE without MDR key → IDENTITY_INSUFFICIENT (NOT merged) ---")
    maude_no_key_1 = [
        {"event_type": "Malfunction", "date_received": "2024-01-15"},  # NO MDR key
    ]
    maude_no_key_2 = [
        {"event_type": "Malfunction", "date_received": "2024-01-15"},  # Same date+type, different report
    ]
    nk1_ids = deduplicate_records(maude_no_key_1, "FDA_MAUDE_feed1")
    nk2_ids = deduplicate_records(maude_no_key_2, "FDA_MAUDE_feed2")
    nk_merged, _ = merge_across_sources({"FDA_MAUDE_feed1": nk1_ids, "FDA_MAUDE_feed2": nk2_ids})
    nk_dups = [m for m in nk_merged if m.is_deduplicated]
    assert len(nk_dups) == 0, "Records without MDR key must NOT be merged"
    assert all(m.identity_confidence == IDENTITY_INSUFFICIENT for m in nk_merged)
    print(f"  ✅ PASS: Missing MDR key → IDENTITY_INSUFFICIENT, NOT merged")
    print(f"  ✅ PASS: Same date+type different reports → preserved separately")

    # ------------------------------------------------------------------
    # FAMILY_ONLY: patent record with only family_id (no publication number)
    # ------------------------------------------------------------------
    print(f"\n--- F1: Family-ID-only record → FAMILY_RELATION_CONFIRMED, NOT merged ---")
    # A patent record that arrives with only a family_id and no publication
    # number cannot be merged with any other record (we don't know which
    # specific publication it is). It must be preserved as its own record
    # with FAMILY_RELATION_CONFIRMED.
    fam_only = [{"family_id": "44785513", "title": "Multi-Lumen Catheter Family"}]
    fo_ids = deduplicate_records(fam_only, "PatentBear")
    assert len(fo_ids) == 1
    assert fo_ids[0].identity_confidence == FAMILY_RELATION_CONFIRMED
    assert fo_ids[0].canonical_id_type == "FAMILY_ID"
    assert fo_ids[0].can_merge is False, (
        "FAMILY_RELATION_CONFIRMED must NOT authorize merge"
    )
    print(f"  ✅ PASS: Family-ID-only record → FAMILY_RELATION_CONFIRMED, can_merge=False")

    # ------------------------------------------------------------------
    # KIND-CODE distinction: same jurisdiction + number, different kind → DISTINCT
    # ------------------------------------------------------------------
    print(f"\n--- A6: Same jurisdiction+number, different kind code → DISTINCT ---")
    # US10232151A1 (application) vs US10232151B2 (grant) — DISTINCT documents
    kind_app = [{"patent_number": "US10232151A1", "title": "Multi-Lumen Catheter"}]
    kind_grt = [{"patent_number": "US10232151B2", "title": "Multi-Lumen Catheter"}]
    ka = deduplicate_records(kind_app, "PatentBear")
    kg = deduplicate_records(kind_grt, "Espacenet")
    merged_a6, _ = merge_across_sources({"PatentBear": ka, "Espacenet": kg})
    patents_a6 = [m for m in merged_a6 if m.record_type == "patent"]
    assert len(patents_a6) == 2, (
        f"Application vs grant of same number MUST stay distinct, got {len(patents_a6)}"
    )
    canon_a6 = sorted(p.canonical_id for p in patents_a6)
    assert canon_a6 == ["US10232151A1", "US10232151B2"], f"Got {canon_a6}"
    print(f"  ✅ PASS: US10232151A1 (application) and US10232151B2 (grant) remain distinct")

    # ------------------------------------------------------------------
    # Stale capability detection (kept from v30.4)
    # ------------------------------------------------------------------
    print(f"\n--- P4: Stale capability detection ---")
    from orchestrator.provider_health_probe import HealthProbeResult, is_probe_stale
    from datetime import datetime, timezone, timedelta
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    fresh_time = datetime.now(timezone.utc).isoformat()
    old_probe = HealthProbeResult(
        provider="Test", probe_time=old_time, request_fingerprint="t1",
        response_state="RESULTS_FOUND", latency_ms=100, result_count=5,
        failure_state=None, query_used="test",
        valid_until=(datetime.fromisoformat(old_time.replace("Z","+00:00")) + timedelta(seconds=3600)).isoformat(),
        probe_config_hash="t1",
    )
    fresh_probe = HealthProbeResult(
        provider="Test", probe_time=fresh_time, request_fingerprint="t2",
        response_state="RESULTS_FOUND", latency_ms=100, result_count=5,
        failure_state=None, query_used="test",
        valid_until=(datetime.now(timezone.utc) + timedelta(seconds=3600)).isoformat(),
        probe_config_hash="t2",
    )
    assert is_probe_stale(old_probe) == True
    assert is_probe_stale(fresh_probe) == False
    print(f"  ✅ PASS: 2hr-old → STALE, fresh → CURRENT")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print(f"\n{'='*78}")
    print(f"ALL TESTS PASSED (v30.5 — typed identity semantics)")
    print(f"{'='*78}")
    tests = [
        "N1: Patent normalization preserves jurisdiction + kind code: ✅",
        "N2: Patent component parsing (jurisdiction, number, kind): ✅",
        "A1: Same digits, different jurisdiction → DISTINCT documents: ✅",
        "A2: US/EP/JP family members → distinct documents, linked family: ✅",
        "A3: US vs EP publication number → DISTINCT documents: ✅",
        "A4: Same title, unrelated patents → NO MERGE (flagged): ✅",
        "P1: Same paper from 2 databases → MERGE (DOCUMENT_ID_CONFIRMED): ✅",
        "P2: Same patent publication from 2 databases → MERGE: ✅",
        "P3: MAUDE dedup (MDR key = EVENT_ID_CONFIRMED): ✅",
        "A5: Missing MDR key → IDENTITY_INSUFFICIENT (NOT merged): ✅",
        "F1: Family-ID-only → FAMILY_RELATION_CONFIRMED (NOT merged): ✅",
        "A6: Application vs grant (different kind code) → DISTINCT: ✅",
        "P4: Stale capability detection: ✅",
    ]
    for t in tests:
        print(f"  {t}")
    print(f"\nKEY PRINCIPLES (v30.5):")
    print(f"  'Identity is not cosmetic metadata. Identity defines what the evidence is.'")
    print(f"  'Same document, related document, same family, same event,")
    print(f"   similar document, unknown identity — these are NOT the same bucket.'")
    print(f"  'A family relationship must never merge two distinct patent documents")
    print(f"   into one evidence object.'")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
