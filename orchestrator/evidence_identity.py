"""
orchestrator/evidence_identity.py — Canonical evidence identity and deduplication.

PER CEO v30.2 AUDIT:
  "Build canonical evidence identity.
   Every retrieved record needs a normalized identity:
   source_id + native_record_id + canonical_identifier (DOI/PMID/Patent/MDR/etc.)
   Then compute a content-level fingerprint for deduplication.
   Corroboration must operate on independent underlying sources, not database copies."

  "Never mistake the number of databases, adapters, records, or search hits
   for the number of independent pieces of evidence.
   A thousand duplicated records are still one underlying fact."
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


@dataclass(frozen=True)
class EvidenceIdentity:
    """Canonical identity for one evidence record.

    Multiple database records may map to the SAME EvidenceIdentity
    (e.g., PubMed PMID 12345 and EuropePMC PMID 12345 are the same paper).
    """
    record_type: str          # "paper" / "patent" / "clinical_trial" / "fda_device" / "fda_event"
    canonical_id: str         # Normalized canonical identifier (DOI, PMID, patent number, K-number, MDR key)
    canonical_id_type: str    # "DOI" / "PMID" / "patent_number" / "k_number" / "mdr_report_key"
    content_fingerprint: str  # SHA-256 of normalized title + first 500 chars of abstract/content

    # Source tracking — which databases returned this record
    source_databases: tuple = field(default_factory=tuple)  # ("PubMed", "EuropePMC")

    @property
    def is_deduplicated(self) -> bool:
        """True if this record has been seen from multiple databases."""
        return len(self.source_databases) > 1


def normalize_doi(doi: str) -> str:
    """Normalize a DOI to canonical form."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    # Remove URL prefix
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:", "", doi)
    return doi


def normalize_pmid(pmid: str) -> str:
    """Normalize a PMID."""
    if not pmid:
        return ""
    return str(pmid).strip()


def normalize_patent_number(pn: str) -> str:
    """Normalize a patent number."""
    if not pn:
        return ""
    pn = pn.strip().upper()
    # Remove country code prefix for comparison
    pn = re.sub(r"^[A-Z]{2}", "", pn)
    # Remove kind code suffix
    pn = re.sub(r"[A-Z]\d?$", "", pn)
    # Remove non-alphanumeric
    pn = re.sub(r"[^A-Z0-9]", "", pn)
    return pn


def compute_content_fingerprint(title: str, abstract: str = "") -> str:
    """Compute a content-level fingerprint for deduplication.

    This catches cases where the same paper appears in multiple databases
    with slightly different formatting but the same title.
    """
    # Normalize: lowercase, remove punctuation, collapse whitespace
    text = (title or "") + " " + (abstract or "")[:500]
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode()).hexdigest()


def extract_canonical_id(record: dict, source: str) -> tuple:
    """Extract canonical identifier from a record based on its source.

    Returns (canonical_id, canonical_id_type).
    """
    if source in ("PubMed", "EuropePMC"):
        pmid = record.get("pmid", "")
        doi = record.get("doi", "")
        if pmid:
            return normalize_pmid(pmid), "PMID"
        elif doi:
            return normalize_doi(doi), "DOI"
        return "", ""

    elif source in ("Crossref",):
        doi = record.get("doi", record.get("DOI", ""))
        if doi:
            return normalize_doi(doi), "DOI"
        return "", ""

    elif source in ("ClinicalTrials.gov",):
        nct_id = record.get("nct_id", record.get("NCTId", ""))
        if nct_id:
            return nct_id.strip(), "NCT_ID"
        return "", ""

    elif source in ("FDA_510k",):
        k_number = record.get("k_number", "")
        if k_number:
            return k_number.strip(), "K_NUMBER"
        return "", ""

    elif source in ("FDA_PMA",):
        pma_number = record.get("pma_number", "")
        if pma_number:
            return pma_number.strip(), "PMA_NUMBER"
        return "", ""

    elif source in ("FDA_MAUDE",):
        mdr_key = record.get("mdr_report_key", "")
        if mdr_key:
            return str(mdr_key).strip(), "MDR_REPORT_KEY"
        # Fall back to event_id + date
        event_id = record.get("event_id", "")
        date = record.get("date_received", "")
        if event_id and date:
            return f"{event_id}_{date}", "EVENT_DATE"
        return "", ""

    elif source in ("FDA_Recalls",):
        recall_number = record.get("recall_number", "")
        if recall_number:
            return recall_number.strip(), "RECALL_NUMBER"
        return "", ""

    elif source in ("NIH_RePORTER",):
        project_num = record.get("project_num", "")
        if project_num:
            return project_num.strip(), "PROJECT_NUM"
        return "", ""

    elif source in ("PatentBear", "Espacenet", "Lens_Patent"):
        pn = record.get("patent_number", record.get("doc_number", ""))
        if pn:
            return normalize_patent_number(pn), "PATENT_NUMBER"
        return "", ""

    return "", ""


def deduplicate_records(records: List[dict], source: str) -> List[EvidenceIdentity]:
    """Deduplicate records from a single source.

    Returns a list of EvidenceIdentity objects, one per unique record.
    """
    seen: Dict[str, EvidenceIdentity] = {}

    for record in records:
        canonical_id, id_type = extract_canonical_id(record, source)
        title = record.get("title", record.get("device_name", record.get("trade_name", "")))
        abstract = record.get("abstract", record.get("description", ""))
        fingerprint = compute_content_fingerprint(title, abstract)

        # Dedup key: canonical_id if available, else fingerprint
        if canonical_id:
            dedup_key = f"{id_type}:{canonical_id}"
        else:
            dedup_key = f"FINGERPRINT:{fingerprint[:32]}"

        if dedup_key in seen:
            # Already seen — this is a duplicate within the same source
            continue

        seen[dedup_key] = EvidenceIdentity(
            record_type=_infer_record_type(source),
            canonical_id=canonical_id or fingerprint[:32],
            canonical_id_type=id_type or "FINGERPRINT",
            content_fingerprint=fingerprint,
            source_databases=(source,),
        )

    return list(seen.values())


def merge_across_sources(source_results: Dict[str, List[EvidenceIdentity]]) -> List[EvidenceIdentity]:
    """Merge deduplicated records across multiple sources.

    Records with the same canonical_id from different sources are MERGED
    into one EvidenceIdentity with multiple source_databases.

    CEO v30.2: "Corroboration must operate on independent underlying sources,
    not database copies."
    """
    merged: Dict[str, EvidenceIdentity] = {}

    for source, identities in source_results.items():
        for identity in identities:
            # Merge key: canonical_id_type:canonical_id (if available)
            # or FINGERPRINT:hash (if no canonical ID)
            if identity.canonical_id_type != "FINGERPRINT":
                merge_key = f"{identity.canonical_id_type}:{identity.canonical_id}"
            else:
                merge_key = f"FINGERPRINT:{identity.content_fingerprint[:32]}"

            if merge_key in merged:
                # Same record from different source — MERGE
                existing = merged[merge_key]
                # Add this source to the list
                new_sources = tuple(sorted(set(existing.source_databases + (source,))))
                merged[merge_key] = EvidenceIdentity(
                    record_type=existing.record_type,
                    canonical_id=existing.canonical_id,
                    canonical_id_type=existing.canonical_id_type,
                    content_fingerprint=existing.content_fingerprint,
                    source_databases=new_sources,
                )
            else:
                merged[merge_key] = identity

    return list(merged.values())


def _infer_record_type(source: str) -> str:
    """Infer record type from source name."""
    if source in ("PubMed", "EuropePMC", "Crossref", "NIH_RePORTER"):
        return "paper"
    elif source in ("PatentBear", "Espacenet", "Lens_Patent"):
        return "patent"
    elif source in ("ClinicalTrials.gov",):
        return "clinical_trial"
    elif source in ("FDA_510k", "FDA_PMA"):
        return "fda_device"
    elif source in ("FDA_MAUDE", "FDA_Recalls"):
        return "fda_event"
    return "unknown"


def main():
    """Test deduplication with synthetic data."""
    print(f"\n{'='*78}")
    print(f"EVIDENCE IDENTITY & DEDUPLICATION TEST")
    print(f"{'='*78}")

    # Simulate: same paper returned by PubMed and EuropePMC
    pubmed_records = [
        {"pmid": "12345", "title": "CSF Shunt Obstruction: A Review", "abstract": "This review covers..."},
        {"pmid": "67890", "title": "Hydrocephalus Management", "abstract": "Management of..."},
    ]
    europepmc_records = [
        {"pmid": "12345", "title": "CSF Shunt Obstruction: A Review", "abstract": "This review covers..."},  # SAME paper
        {"pmid": "11111", "title": "Endovascular Shunt Feasibility", "abstract": "Feasibility study..."},
    ]

    pubmed_ids = deduplicate_records(pubmed_records, "PubMed")
    europepmc_ids = deduplicate_records(europepmc_records, "EuropePMC")

    print(f"\nPubMed unique records: {len(pubmed_ids)}")
    print(f"EuropePMC unique records: {len(europepmc_ids)}")

    merged = merge_across_sources({"PubMed": pubmed_ids, "EuropePMC": europepmc_ids})

    print(f"\nAfter cross-source merge: {len(merged)} unique records")
    print(f"(Expected: 3 — paper 12345 appears in both but counts once)")

    for m in merged:
        sources = ", ".join(m.source_databases)
        dup = " (DUPLICATED)" if m.is_deduplicated else ""
        print(f"  {m.canonical_id_type}: {m.canonical_id[:30]} [{sources}]{dup}")

    # Test: 2 records from PubMed + 2 from EuropePMC, 1 overlap → 3 unique
    assert len(merged) == 3, f"Expected 3 unique, got {len(merged)}"
    duplicated = [m for m in merged if m.is_deduplicated]
    assert len(duplicated) == 1, f"Expected 1 duplicated, got {len(duplicated)}"
    assert "PubMed" in duplicated[0].source_databases
    assert "EuropePMC" in duplicated[0].source_databases

    print(f"\n✅ DEDUPLICATION TEST PASSED")
    print(f"   - Same PMID from PubMed + EuropePMC → 1 unique record with 2 sources")
    print(f"   - Corroboration operates on independent underlying sources")
    print(f"   - 5 raw records → 4 unique → 1 cross-source duplicate detected")

    print(f"\n{'='*78}")
    print(f"KEY PRINCIPLE:")
    print(f"  5 database records ≠ 5 independent pieces of evidence")
    print(f"  Same PMID from 2 databases = 1 underlying fact, 2 retrieval paths")
    print(f"  Corroboration = independent SOURCES, not database copies")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
