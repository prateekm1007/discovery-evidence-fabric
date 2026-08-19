#!/usr/bin/env python3
"""
Article XVII adversarial attack on orchestrator/evidence_identity.py v30.5.

I am the attacker. My goal is to find ANY input pattern that defeats the
new typed identity semantics:

  1. Make two DISTINCT patent publications merge into one evidence object
     (violation: family relation collapses distinct documents).
  2. Make the patent normalizer lose jurisdiction or kind code.
  3. Make a MISSING-identity record merge via fingerprint.
  4. Make family_relations point to the WRONG member.
  5. Make a family-only record merge with a document record.
  6. Make two different-jurisdiction patents with the SAME family_id merge
     into one record (the original sin we're fixing).

Each attack that succeeds is a real defect. Each that fails is evidence
that the v30.5 model holds.
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
    DOCUMENT_ID_CONFIRMED,
    EVENT_ID_CONFIRMED,
    FAMILY_RELATION_CONFIRMED,
    POSSIBLE_FAMILY_MATCH,
    IDENTITY_INSUFFICIENT,
    IDENTITY_CONFIRMED,  # deprecated alias
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
print("ARTICLE XVII ADVERSARIAL ATTACK — v30.5 typed identity")
print("=" * 78)

# ---------------------------------------------------------------------------
# Attack 1: Try to merge US10232151B2 and EP2436419B1 (same family)
# by exploiting any leftover bug in the merge logic.
# ---------------------------------------------------------------------------
print("\n--- Attack 1: Force US10232151B2 + EP2436419B1 (same family) to merge ---")
pb = [{"patent_number": "US10232151B2", "title": "Multi-Lumen Catheter", "family_id": "44785513"}]
ep = [{"doc_number":    "EP2436419B1",  "title": "Multi-Lumen Catheter", "family_id": "44785513"}]
pb_ids = deduplicate_records(pb, "PatentBear")
ep_ids = deduplicate_records(ep, "Espacenet")
merged, _ = merge_across_sources({"PatentBear": pb_ids, "Espacenet": ep_ids})
patents = [m for m in merged if m.record_type == "patent"]
check(
    "US+EP same-family patents remain 2 distinct documents",
    len(patents) == 2,
    f"(got {len(patents)})"
)
check(
    "neither auto-merged",
    all(not p.is_deduplicated for p in patents)
)
check(
    "both DOCUMENT_ID_CONFIRMED",
    all(p.identity_confidence == DOCUMENT_ID_CONFIRMED for p in patents)
)
check(
    "family_relations populated (each points to the other)",
    all(len(p.family_relations) == 1 for p in patents)
)

# ---------------------------------------------------------------------------
# Attack 2: Try to confuse the normalizer with mixed separators + URL form
# ---------------------------------------------------------------------------
print("\n--- Attack 2: Confuse normalizer with weird separator + URL variants ---")
variants = [
    "US-11912894-B2",
    "us 11912894 b2",
    "US/11912894/B2",
    "patent/US11912894B2/en",
    "US11912894B2",
    "uS11912894b2",
]
canonical = set()
for v in variants:
    canonical.add(normalize_patent_number(v))
check(
    "all 6 cosmetic variants normalize to US11912894B2",
    canonical == {"US11912894B2"},
    f"(got {canonical})"
)

# ---------------------------------------------------------------------------
# Attack 3: Try to merge a fingerprint-only record with a CONFIRMED record
# that shares the same fingerprint.
# ---------------------------------------------------------------------------
print("\n--- Attack 3: Fingerprint-only record must NOT merge with CONFIRMED record ---")
fam_only = [{"family_id": "", "title": "Same Title Same Abstract", "abstract": "X"}]
confirmed = [{"patent_number": "US9999999B2", "title": "Same Title Same Abstract", "abstract": "X"}]
fo_ids = deduplicate_records(fam_only, "PatentBear")
co_ids = deduplicate_records(confirmed, "Espacenet")
merged, _ = merge_across_sources({"PatentBear": fo_ids, "Espacenet": co_ids})
patents = [m for m in merged if m.record_type == "patent"]
check(
    "fingerprint-only + confirmed stay as 2 records",
    len(patents) == 2,
    f"(got {len(patents)})"
)
check(
    "fingerprint-only record is POSSIBLE_FAMILY_MATCH (not CONFIRMED)",
    any(p.identity_confidence == POSSIBLE_FAMILY_MATCH for p in patents)
)
check(
    "neither auto-merged",
    all(not p.is_deduplicated for p in patents)
)

# ---------------------------------------------------------------------------
# Attack 4: Try to make family_relations point to the WRONG member
# by injecting 4 family members and verifying each member links to exactly
# the other 3 (not to itself, not to non-members).
# ---------------------------------------------------------------------------
print("\n--- Attack 4: 4-member family — each links to the OTHER 3, not itself ---")
# 4 distinct sources — each returns one family member.
# (We deliberately use 4 sources because reusing "PatentBear" twice in a
# dict comprehension would overwrite the first entry — that's a test bug,
# not an implementation bug. In production, a single source returns all its
# records in ONE call to deduplicate_records, so this scenario is realistic.)
fam = [
    ({"patent_number": "US11111111B2", "title": "Fam", "family_id": "FAM001"}, "PatentBear"),
    ({"doc_number":    "EP22222222B1", "title": "Fam", "family_id": "FAM001"}, "Espacenet"),
    ({"doc_number":    "JP33333333A",  "title": "Fam", "family_id": "FAM001"}, "Lens_Patent"),
    ({"doc_number":    "WO4444444A1",  "title": "Fam", "family_id": "FAM001"}, "Google_Patents"),
]
sources = {src: deduplicate_records([rec], src) for rec, src in fam}
merged, _ = merge_across_sources(sources)
patents = [m for m in merged if m.record_type == "patent" and m.patent_family_id == "FAM001"]
check("4 family members remain 4 distinct documents", len(patents) == 4, f"(got {len(patents)})")
expected_canon = {"US11111111B2", "EP22222222B1", "JP33333333A", "WO4444444A1"}
for p in patents:
    check(
        f"member {p.canonical_id} links to OTHER 3 (not itself)",
        set(p.family_relations) == (expected_canon - {p.canonical_id}),
        f"(got {set(p.family_relations)})"
    )
    check(
        f"member {p.canonical_id} does NOT link to itself",
        p.canonical_id not in p.family_relations
    )

# ---------------------------------------------------------------------------
# Attack 5: Try to merge a family-only record with a document record
# by giving them the same family_id.
# ---------------------------------------------------------------------------
print("\n--- Attack 5: Family-only record + document record (same family_id) → must NOT merge ---")
fam_only = [{"family_id": "FAM999", "title": "Family Level Record"}]
doc_with_fam = [{"patent_number": "US88888888B2", "title": "Specific Member", "family_id": "FAM999"}]
fo = deduplicate_records(fam_only, "PatentBear")
dw = deduplicate_records(doc_with_fam, "Espacenet")
merged, _ = merge_across_sources({"PatentBear": fo, "Espacenet": dw})
patents = [m for m in merged if m.record_type == "patent"]
check(
    "family-only + specific document stay as 2 records",
    len(patents) == 2,
    f"(got {len(patents)})"
)
# The family-only record is FAMILY_RELATION_CONFIRMED; the document is DOCUMENT_ID_CONFIRMED
fam_rec = [p for p in patents if p.identity_confidence == FAMILY_RELATION_CONFIRMED]
doc_rec = [p for p in patents if p.identity_confidence == DOCUMENT_ID_CONFIRMED]
check("family-only record = FAMILY_RELATION_CONFIRMED", len(fam_rec) == 1)
check("document record = DOCUMENT_ID_CONFIRMED", len(doc_rec) == 1)
check(
    "neither auto-merged",
    all(not p.is_deduplicated for p in patents)
)

# ---------------------------------------------------------------------------
# Attack 6: Backward-compat alias — IDENTITY_CONFIRMED must equal
# DOCUMENT_ID_CONFIRMED (so legacy callers don't accidentally authorize
# family merges).
# ---------------------------------------------------------------------------
print("\n--- Attack 6: IDENTITY_CONFIRMED deprecated alias must NOT match FAMILY_RELATION_CONFIRMED ---")
check(
    "IDENTITY_CONFIRMED == DOCUMENT_ID_CONFIRMED",
    IDENTITY_CONFIRMED == DOCUMENT_ID_CONFIRMED
)
check(
    "IDENTITY_CONFIRMED != FAMILY_RELATION_CONFIRMED",
    IDENTITY_CONFIRMED != FAMILY_RELATION_CONFIRMED
)
check(
    "IDENTITY_CONFIRMED != EVENT_ID_CONFIRMED  (event IDs are their own type)",
    IDENTITY_CONFIRMED != EVENT_ID_CONFIRMED
)

# ---------------------------------------------------------------------------
# Attack 7: kind code confusion — try to confuse A1 vs A2 vs B1 vs B2
# ---------------------------------------------------------------------------
print("\n--- Attack 7: Kind codes A1/A2/B1/B2/C1 must remain distinct ---")
kind_variants = [
    ("US10232151A1", "application published"),
    ("US10232151A2", "application republished"),
    ("US10232151B1", "grant first publication"),
    ("US10232151B2", "grant corrected"),
    ("US10232151C1", "corrected grant"),
]
sources = {}
for pn, label in kind_variants:
    sources[label] = deduplicate_records([{"patent_number": pn, "title": "Same"}], "PatentBear")
merged, _ = merge_across_sources(sources)
patents = [m for m in merged if m.record_type == "patent"]
check(
    "5 kind-code variants remain 5 distinct documents",
    len(patents) == 5,
    f"(got {len(patents)})"
)
canon_set = {p.canonical_id for p in patents}
check(
    "all 5 canonical_ids preserved (A1, A2, B1, B2, C1)",
    canon_set == {"US10232151A1", "US10232151A2", "US10232151B1", "US10232151B2", "US10232151C1"},
    f"(got {canon_set})"
)

# ---------------------------------------------------------------------------
# Attack 8: parse_patent_components on adversarial inputs
# ---------------------------------------------------------------------------
print("\n--- Attack 8: parse_patent_components on adversarial inputs ---")
empty = parse_patent_components("")
check("empty input → empty tuple", empty == ("", "", ""), f"(got {empty})")
no_country = parse_patent_components("10232151")
check("no jurisdiction → ('', '10232151', '')", no_country == ("", "10232151", ""), f"(got {no_country})")
no_kind = parse_patent_components("US10232151")
check("no kind code → ('US', '10232151', '')", no_kind == ("US", "10232151", ""), f"(got {no_kind})")
long_kind = parse_patent_components("US10232151PCT")
check("long suffix → still parsed", long_kind[0] == "US" and long_kind[1] == "10232151")

# ---------------------------------------------------------------------------
# Attack 9: Cross-source same MDR key with different event metadata
# must merge (MDR key wins over event_type+date).
# ---------------------------------------------------------------------------
print("\n--- Attack 9: Same MDR key, different event metadata → MERGE (MDR wins) ---")
m1 = [{"mdr_report_key": "MDR001", "event_type": "Malfunction", "date_received": "2024-01-15"}]
m2 = [{"mdr_report_key": "MDR001", "event_type": "Injury", "date_received": "2024-09-30"}]
# Note: different event_type and date — but same MDR key
m1_ids = deduplicate_records(m1, "FDA_MAUDE_feed1")
m2_ids = deduplicate_records(m2, "FDA_MAUDE_feed2")
merged, _ = merge_across_sources({"FDA_MAUDE_feed1": m1_ids, "FDA_MAUDE_feed2": m2_ids})
events = [m for m in merged if m.record_type == "fda_event"]
check(
    "same MDR key with different metadata → 1 merged record",
    len(events) == 1,
    f"(got {len(events)})"
)
check(
    "merged record is EVENT_ID_CONFIRMED",
    events[0].identity_confidence == EVENT_ID_CONFIRMED
)
check(
    "merged record seen from 2 sources",
    events[0].is_deduplicated
)

# ---------------------------------------------------------------------------
# Attack 10: An identity attack — claim a paper's PMID, but supply a totally
# different title/abstract. The current model trusts PMID; the audit may
# want a future "MISMATCH" detection. Document this as a known limitation.
# ---------------------------------------------------------------------------
print("\n--- Attack 10 (known limitation): PMID authoritative, even if title differs ---")
# In v30.5, PMID is authoritative — if two records share a PMID, they merge
# regardless of title. This is the intended behavior (PMID IS the document).
# But this also means a corrupted record with the wrong PMID could
# contaminate a good record. NOTE this as a known limitation.
pmid_real = [{"pmid": "99999", "title": "Real Title", "abstract": "Real abstract"}]
pmid_spoof = [{"pmid": "99999", "title": "DIFFERENT TITLE", "abstract": "DIFFERENT"}]
r1 = deduplicate_records(pmid_real, "PubMed")
r2 = deduplicate_records(pmid_spoof, "EuropePMC")
merged, _ = merge_across_sources({"PubMed": r1, "EuropePMC": r2})
papers = [m for m in merged if m.record_type == "paper"]
check(
    "same PMID merges even with different title (PMID is authoritative)",
    len(papers) == 1,
    f"(got {len(papers)})"
)
# Document the limitation:
print("  ⚠️  KNOWN LIMITATION: PMID/DOI are trusted authoritatively. A corrupted")
print("     upstream record could contaminate a good record. Future work:")
print("     add CONTENT_MISMATCH flag when fingerprint diverges despite same ID.")

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
    print("✅ ALL ATTACKS DEFENDED. v30.5 typed identity model holds.")
    sys.exit(0)
