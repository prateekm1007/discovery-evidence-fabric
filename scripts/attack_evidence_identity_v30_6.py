#!/usr/bin/env python3
"""
Article XVII adversarial attack on orchestrator/evidence_identity.py v30.6.

I am the attacker. My goal is to defeat the CONTENT_MISMATCH logic:

  1. Make two records with the SAME canonical_id and DIFFERENT fingerprints
     silently merge as DOCUMENT_ID_CONFIRMED (no mismatch detected).
  2. Make a CONTENT_MISMATCH record be used as verified semantic evidence.
  3. Make the audit record lose information about which source diverged.
  4. Make a 3-source majority consensus override the mismatch.
  5. Make the primary fingerprint be the divergent one (information loss).
  6. Make family-relation records trigger CONTENT_MISMATCH (wrong trigger).
  7. Make the divergence detection miss when 3+ sources all differ.
  8. Make the audit record's detected_at timestamp missing or malformed.
  9. Make a CONTENT_MISMATCH record contaminate a clean record via family.
  10. Make the system forget about a mismatch after a 3rd matching source.

Each attack that succeeds is a real defect. Each that fails is evidence
that the v30.6 model holds.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.evidence_identity import (
    normalize_patent_number,
    parse_patent_components,
    deduplicate_records,
    merge_across_sources,
    EvidenceIdentity,
    ContentMismatchAudit,
    DOCUMENT_ID_CONFIRMED,
    EVENT_ID_CONFIRMED,
    DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH,
    EVENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH,
    FAMILY_RELATION_CONFIRMED,
    POSSIBLE_FAMILY_MATCH,
    IDENTITY_INSUFFICIENT,
)

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ DEFENDED: {name}")
    else:
        FAIL += 1
        print(f"  ❌ BREACHED: {name} {detail}")


print("=" * 78)
print("ARTICLE XVII ADVERSARIAL ATTACK — v30.6 content integrity")
print("=" * 78)

# ---------------------------------------------------------------------------
# Attack 1: Try to make same-DOI-different-content silently merge as CONFIRMED
# (the original v30.5 bug). Send divergent content and check the result is
# NOT plain DOCUMENT_ID_CONFIRMED.
# ---------------------------------------------------------------------------
print("\n--- Attack 1: Same DOI + different content must NOT be plain DOCUMENT_ID_CONFIRMED ---")
a = [{"doi": "10.1/atk1", "title": "T", "abstract": "A"}]
b = [{"doi": "10.1/atk1", "title": "T", "abstract": "B"}]
ia = deduplicate_records(a, "Crossref")
ib = deduplicate_records(b, "EuropePMC")
merged, _ = merge_across_sources({"Crossref": ia, "EuropePMC": ib})
papers = [m for m in merged if m.record_type == "paper"]
check(
    "exactly 1 merged record (identity preserved)",
    len(papers) == 1
)
if papers:
    check(
        "NOT plain DOCUMENT_ID_CONFIRMED (must be CONTENT_MISMATCH)",
        papers[0].identity_confidence != DOCUMENT_ID_CONFIRMED,
        f"(got {papers[0].identity_confidence})"
    )
    check(
        "IS DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH",
        papers[0].identity_confidence == DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH
    )

# ---------------------------------------------------------------------------
# Attack 2: Try to use a CONTENT_MISMATCH record as verified evidence
# ---------------------------------------------------------------------------
print("\n--- Attack 2: CONTENT_MISMATCH record must NOT be usable as verified evidence ---")
check(
    "can_use_as_verified_evidence=False",
    papers[0].can_use_as_verified_evidence is False
)
check(
    "has_content_mismatch=True",
    papers[0].has_content_mismatch is True
)
check(
    "can_merge=True (identity still preserved)",
    papers[0].can_merge is True
)

# ---------------------------------------------------------------------------
# Attack 3: Audit record must preserve which source diverged
# ---------------------------------------------------------------------------
print("\n--- Attack 3: Audit record preserves divergent source ---")
if papers and papers[0].content_mismatch_audits:
    audit = papers[0].content_mismatch_audits[0]
    check(
        "audit.canonical_id matches the DOI",
        audit.canonical_id == "10.1/atk1"
    )
    check(
        "audit.canonical_id_type == 'DOI'",
        audit.canonical_id_type == "DOI"
    )
    check(
        "audit.primary_fingerprint != audit.divergent_fingerprint",
        audit.primary_fingerprint != audit.divergent_fingerprint
    )
    check(
        "audit.divergent_source is set (not empty)",
        audit.divergent_source != ""
    )
    check(
        "audit.detected_at is set (ISO timestamp)",
        "T" in audit.detected_at and ":" in audit.detected_at
    )
    check(
        "audit.divergent_record_summary is non-empty",
        audit.divergent_record_summary != ""
    )

# ---------------------------------------------------------------------------
# Attack 4: 3-source majority consensus must NOT override mismatch
# ---------------------------------------------------------------------------
print("\n--- Attack 4: 3-source majority (2v1) does NOT override mismatch ---")
m1 = [{"doi": "10.2/atk4", "title": "T", "abstract": "Majority"}]
m2 = [{"doi": "10.2/atk4", "title": "T", "abstract": "Majority"}]
m3 = [{"doi": "10.2/atk4", "title": "T", "abstract": "Minority"}]
i1 = deduplicate_records(m1, "Crossref")
i2 = deduplicate_records(m2, "EuropePMC")
i3 = deduplicate_records(m3, "PubMed")
merged, _ = merge_across_sources({"Crossref": i1, "EuropePMC": i2, "PubMed": i3})
papers = [m for m in merged if m.record_type == "paper"]
check(
    "1 merged record",
    len(papers) == 1
)
if papers:
    check(
        "still CONTENT_MISMATCH despite 2-of-3 majority",
        papers[0].identity_confidence == DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH
    )
    check(
        "still can_use_as_verified_evidence=False",
        papers[0].can_use_as_verified_evidence is False
    )
    check(
        "exactly 1 audit (1 divergence from primary)",
        len(papers[0].content_mismatch_audits) == 1
    )

# ---------------------------------------------------------------------------
# Attack 5: Primary fingerprint must be the FIRST-seen, not the divergent
# ---------------------------------------------------------------------------
print("\n--- Attack 5: Primary fingerprint = first-seen (not divergent) ---")
# Crossref returns content A first, EuropePMC returns content B.
# The merged record's content_fingerprint should be A (the primary).
a_rec = [{"doi": "10.3/atk5", "title": "T", "abstract": "FIRST"}]
b_rec = [{"doi": "10.3/atk5", "title": "T", "abstract": "SECOND"}]
ia = deduplicate_records(a_rec, "Crossref")
ib = deduplicate_records(b_rec, "EuropePMC")
merged, _ = merge_across_sources({"Crossref": ia, "EuropePMC": ib})
papers = [m for m in merged if m.record_type == "paper"]
if papers:
    from orchestrator.evidence_identity import compute_content_fingerprint
    expected_primary = compute_content_fingerprint("T", "FIRST")
    check(
        "content_fingerprint = first-seen (FIRST)",
        papers[0].content_fingerprint == expected_primary
    )
    check(
        "audit.primary_fingerprint = first-seen",
        papers[0].content_mismatch_audits[0].primary_fingerprint == expected_primary
    )
    check(
        "audit.divergent_fingerprint = second-seen (SECOND)",
        papers[0].content_mismatch_audits[0].divergent_fingerprint
        == compute_content_fingerprint("T", "SECOND")
    )

# ---------------------------------------------------------------------------
# Attack 6: Family-relation records must NOT trigger CONTENT_MISMATCH
# (family members are DIFFERENT documents with DIFFERENT canonical_ids;
#  they should never be compared by fingerprint for mismatch purposes)
# ---------------------------------------------------------------------------
print("\n--- Attack 6: Family-relation records do NOT trigger CONTENT_MISMATCH ---")
# Two patents in the same family but with DIFFERENT publication numbers.
# They have different content (different titles) but should NOT be tagged
# CONTENT_MISMATCH — they're different documents, not the same document
# with divergent bytes.
fam1 = [{"patent_number": "US11111111B2", "title": "US Member", "family_id": "FAM001"}]
fam2 = [{"doc_number":    "EP22222222B1", "title": "EP Member", "family_id": "FAM001"}]
i1 = deduplicate_records(fam1, "PatentBear")
i2 = deduplicate_records(fam2, "Espacenet")
merged, _ = merge_across_sources({"PatentBear": i1, "Espacenet": i2})
patents = [m for m in merged if m.record_type == "patent"]
check(
    "2 distinct patent documents (not merged)",
    len(patents) == 2
)
for p in patents:
    check(
        f"patent {p.canonical_id} is DOCUMENT_ID_CONFIRMED (not CONTENT_MISMATCH)",
        p.identity_confidence == DOCUMENT_ID_CONFIRMED,
        f"(got {p.identity_confidence})"
    )
    check(
        f"patent {p.canonical_id} has 0 content_mismatch_audits",
        len(p.content_mismatch_audits) == 0
    )

# ---------------------------------------------------------------------------
# Attack 7: 3 sources all different must produce 2 audits (not 1, not 0)
# ---------------------------------------------------------------------------
print("\n--- Attack 7: 3 sources all different -> 2 audits ---")
s1 = [{"doi": "10.4/atk7", "title": "T", "abstract": "ONE"}]
s2 = [{"doi": "10.4/atk7", "title": "T", "abstract": "TWO"}]
s3 = [{"doi": "10.4/atk7", "title": "T", "abstract": "THREE"}]
i1 = deduplicate_records(s1, "Crossref")
i2 = deduplicate_records(s2, "EuropePMC")
i3 = deduplicate_records(s3, "PubMed")
merged, _ = merge_across_sources({"Crossref": i1, "EuropePMC": i2, "PubMed": i3})
papers = [m for m in merged if m.record_type == "paper"]
check(
    "1 merged record",
    len(papers) == 1
)
if papers:
    check(
        "CONTENT_MISMATCH",
        papers[0].identity_confidence == DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH
    )
    check(
        "3 observed fingerprints (1 primary + 2 divergent)",
        len(papers[0].observed_content_fingerprints) == 3,
        f"(got {len(papers[0].observed_content_fingerprints)})"
    )
    check(
        "2 audit records (one per divergence)",
        len(papers[0].content_mismatch_audits) == 2,
        f"(got {len(papers[0].content_mismatch_audits)})"
    )

# ---------------------------------------------------------------------------
# Attack 8: A 3rd matching source must NOT "clear" a previous mismatch
# ---------------------------------------------------------------------------
print("\n--- Attack 8: 3rd matching source does NOT clear mismatch ---")
# Source 1: A, Source 2: B (mismatch), Source 3: A (matches primary).
# The mismatch from Source 2 must NOT be cleared by Source 3 matching.
s1 = [{"doi": "10.5/atk8", "title": "T", "abstract": "PRIMARY"}]
s2 = [{"doi": "10.5/atk8", "title": "T", "abstract": "DIVERGENT"}]
s3 = [{"doi": "10.5/atk8", "title": "T", "abstract": "PRIMARY"}]  # matches primary
i1 = deduplicate_records(s1, "Crossref")
i2 = deduplicate_records(s2, "EuropePMC")
i3 = deduplicate_records(s3, "PubMed")
merged, _ = merge_across_sources({"Crossref": i1, "EuropePMC": i2, "PubMed": i3})
papers = [m for m in merged if m.record_type == "paper"]
if papers:
    check(
        "still CONTENT_MISMATCH (3rd source did NOT clear it)",
        papers[0].identity_confidence == DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH
    )
    check(
        "still can_use_as_verified_evidence=False",
        papers[0].can_use_as_verified_evidence is False
    )
    check(
        "still 1 audit (the divergence from source 2)",
        len(papers[0].content_mismatch_audits) == 1
    )
    check(
        "3 source_databases retained",
        len(papers[0].source_databases) == 3
    )

# ---------------------------------------------------------------------------
# Attack 9: MAUDE event mismatch must use EVENT_ID variant, not DOCUMENT_ID
# ---------------------------------------------------------------------------
print("\n--- Attack 9: MAUDE mismatch uses EVENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH ---")
m1 = [{"mdr_report_key": "MDR_ATK9", "event_type": "Malfunction", "date_received": "2024-01-01"}]
m2 = [{"mdr_report_key": "MDR_ATK9", "event_type": "Death", "date_received": "2024-12-31"}]
i1 = deduplicate_records(m1, "FDA_MAUDE_feed1")
i2 = deduplicate_records(m2, "FDA_MAUDE_feed2")
merged, _ = merge_across_sources({"FDA_MAUDE_feed1": i1, "FDA_MAUDE_feed2": i2})
events = [m for m in merged if m.record_type == "fda_event"]
check(
    "1 merged event record",
    len(events) == 1
)
if events:
    check(
        "EVENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH (not DOCUMENT_ID variant)",
        events[0].identity_confidence == EVENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH,
        f"(got {events[0].identity_confidence})"
    )
    check(
        "can_merge=True (identity preserved)",
        events[0].can_merge is True
    )
    check(
        "can_use_as_verified_evidence=False (bytes blocked)",
        events[0].can_use_as_verified_evidence is False
    )

# ---------------------------------------------------------------------------
# Attack 10: Content mismatch on a PATENT publication number
# ---------------------------------------------------------------------------
print("\n--- Attack 10: Patent pub + altered content -> DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH ---")
p1 = [{"patent_number": "US99999999B2", "title": "Original", "abstract": "Original spec"}]
p2 = [{"patent_number": "US99999999B2", "title": "Original", "abstract": "ALTERED spec"}]
i1 = deduplicate_records(p1, "PatentBear")
i2 = deduplicate_records(p2, "Espacenet")
merged, _ = merge_across_sources({"PatentBear": i1, "Espacenet": i2})
patents = [m for m in merged if m.record_type == "patent"]
check(
    "1 merged patent record",
    len(patents) == 1
)
if patents:
    check(
        "DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH",
        patents[0].identity_confidence == DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH
    )
    check(
        "canonical_id preserved (US99999999B2)",
        patents[0].canonical_id == "US99999999B2"
    )
    check(
        "can_use_as_verified_evidence=False",
        patents[0].can_use_as_verified_evidence is False
    )

# ---------------------------------------------------------------------------
# Attack 11: Same content + same ID must NOT trigger mismatch (regression)
# ---------------------------------------------------------------------------
print("\n--- Attack 11: Same content + same ID -> NO mismatch (regression) ---")
a = [{"doi": "10.6/atk11", "title": "Same", "abstract": "Same"}]
b = [{"doi": "10.6/atk11", "title": "Same", "abstract": "Same"}]
ia = deduplicate_records(a, "Crossref")
ib = deduplicate_records(b, "EuropePMC")
merged, _ = merge_across_sources({"Crossref": ia, "EuropePMC": ib})
papers = [m for m in merged if m.record_type == "paper"]
if papers:
    check(
        "DOCUMENT_ID_CONFIRMED (no mismatch)",
        papers[0].identity_confidence == DOCUMENT_ID_CONFIRMED
    )
    check(
        "0 observed_content_fingerprints",
        len(papers[0].observed_content_fingerprints) == 0
    )
    check(
        "0 content_mismatch_audits",
        len(papers[0].content_mismatch_audits) == 0
    )
    check(
        "can_use_as_verified_evidence=True",
        papers[0].can_use_as_verified_evidence is True
    )

# ---------------------------------------------------------------------------
# Attack 12: A mismatched record's family_id must still be preserved
# (mismatch doesn't lose family info)
# ---------------------------------------------------------------------------
print("\n--- Attack 12: Mismatched record preserves family_id ---")
p1 = [{"patent_number": "US77777777B2", "title": "T", "abstract": "A", "family_id": "FAM_ATK12"}]
p2 = [{"patent_number": "US77777777B2", "title": "T", "abstract": "B", "family_id": "FAM_ATK12"}]
i1 = deduplicate_records(p1, "PatentBear")
i2 = deduplicate_records(p2, "Espacenet")
merged, _ = merge_across_sources({"PatentBear": i1, "Espacenet": i2})
patents = [m for m in merged if m.record_type == "patent" and m.canonical_id == "US77777777B2"]
if patents:
    check(
        "family_id preserved despite mismatch",
        patents[0].patent_family_id == "FAM_ATK12"
    )
    check(
        "still CONTENT_MISMATCH",
        patents[0].identity_confidence == DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH
    )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print(f"ATTACK SUMMARY: {PASS} defended / {FAIL} breached")
print("=" * 78)
if FAIL > 0:
    print("❌ IMPLEMENTATION BREACHED — fix before commit.")
    sys.exit(1)
else:
    print("✅ ALL ATTACKS DEFENDED. v30.6 content-integrity model holds.")
    print()
    print("KEY PRINCIPLE:")
    print("  'Identity proves what the record CLAIMS to be.")
    print("   It does not prove that the bytes we received are truthful,")
    print("   intact, or the right content.")
    print("   Never collapse identity integrity and content integrity")
    print("   into one bit.'")
    sys.exit(0)
