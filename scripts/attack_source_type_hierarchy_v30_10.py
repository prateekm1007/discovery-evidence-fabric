#!/usr/bin/env python3
"""
Article XVII adversarial attack on the v30.10 type-safe source hierarchy.

CEO v30.10 directive: "A security boundary should be enforced by object
construction, not by trusting a label inside the object."

This script attacks the InternalSource / ExternalSource type boundary with
masquerade attempts:

  1. External DOI disguised as INTERNAL_REPORT
  2. Patent disguised as INTERNAL_ANALYSIS
  3. MAUDE record disguised as internal
  4. External Source subclass overriding source_type
  5. Forged internal authorization (ExternalSource with source_type=INTERNAL_REPORT)
  6. InternalSource with DOI in content
  7. InternalSource with PMID in title
  8. InternalSource with patent number in identifier
  9. Direct ExternalSource construction without VerifiedEvidence
 10. Raw Source with external type -> register_source
 11. Raw Source with internal type -> register_source
 12. Valid VerifiedEvidence -> ExternalSource (positive control)
 13. Valid InternalSource (positive control)

Every masquerade must fail at CONSTRUCTION or REGISTRATION, not at render.
"""
import sys
import hashlib
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.evidence_identity import (
    deduplicate_records,
    VerifiedEvidence,
    EvidenceAuthorizationError,
    DOCUMENT_ID_CONFIRMED,
    EVENT_ID_CONFIRMED,
)
from epistemic_integrity.evidence_binding import (
    EvidenceBinding,
    Source,
    InternalSource,
    ExternalSource,
    SourceVerificationStates,
    ExternalIdentityVerification,
    _is_external_source_type,
    _is_internal_source_type,
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
print("ARTICLE XVII ADVERSARIAL ATTACK — v30.10 TYPE-SAFE SOURCE HIERARCHY")
print("=" * 78)

tmpdir = Path(tempfile.mkdtemp(prefix="v30_10_type_"))
binding = EvidenceBinding(tmpdir)
print(f"\nProduction EvidenceBinding registry: {tmpdir}")

# ===========================================================================
# Attack 1: External DOI disguised as INTERNAL_REPORT
# ===========================================================================
print("\n--- Attack 1: DOI disguised as INTERNAL_REPORT ---")
try:
    src = InternalSource(
        source_id="SRC-ATK-1",
        source_type="INTERNAL_REPORT",
        identifier="10.1234/test.disguised",
        title="Disguised DOI",
    )
    check("DOI in identifier refused by InternalSource constructor", False)
except ValueError as e:
    check("DOI in identifier refused by InternalSource constructor", True)
    check("error mentions INTERNAL_SOURCE_MASQUERADE_BLOCKED",
          "INTERNAL_SOURCE_MASQUERADE_BLOCKED" in str(e))

# ===========================================================================
# Attack 2: Patent disguised as INTERNAL_ANALYSIS
# ===========================================================================
print("\n--- Attack 2: Patent disguised as INTERNAL_ANALYSIS ---")
try:
    src = InternalSource(
        source_id="SRC-ATK-2",
        source_type="INTERNAL_ANALYSIS",
        identifier="US10232151B2",
        title="Disguised Patent",
    )
    check("Patent in identifier refused by InternalSource constructor", False)
except ValueError as e:
    check("Patent in identifier refused by InternalSource constructor", True)
    check("error mentions masquerade", "MASQUERADE" in str(e))

# ===========================================================================
# Attack 3: MAUDE record disguised as internal
# ===========================================================================
print("\n--- Attack 3: MAUDE record disguised as internal ---")
try:
    src = InternalSource(
        source_id="SRC-ATK-3",
        source_type="INTERNAL_REPORT",
        identifier="MDR1234567",
        title="Disguised MAUDE",
    )
    check("MDR key in identifier refused by InternalSource constructor", False)
except ValueError:
    check("MDR key in identifier refused by InternalSource constructor", True)

# ===========================================================================
# Attack 4: External Source subclass overriding source_type
# ===========================================================================
print("\n--- Attack 4: Subclass overriding source_type ---")
class ForgedInternalSource(InternalSource):
    """Attacker subclasses InternalSource to try to bypass the check."""
    def __post_init__(self):
        # Skip parent check
        pass

try:
    forged = ForgedInternalSource(
        source_id="SRC-ATK-4",
        source_type="INTERNAL_REPORT",
        identifier="10.1234/forged",
        title="Forged Subclass",
    )
    # If construction succeeded, try to register
    try:
        binding.register_source(forged)
        check("forged subclass refused by register_source", False)
    except (TypeError, ValueError):
        check("forged subclass refused by register_source", True)
except Exception as e:
    check("forged subclass construction or registration refused", True)

# ===========================================================================
# Attack 5: Forged internal authorization (ExternalSource with INTERNAL_REPORT)
# ===========================================================================
print("\n--- Attack 5: ExternalSource with source_type=INTERNAL_REPORT ---")
try:
    src = ExternalSource(
        source_id="SRC-ATK-5",
        source_type="INTERNAL_REPORT",  # WRONG — ExternalSource requires external type
        identifier="INT-FORGED",
        title="Forged External",
        _verified_evidence_authorization={"fake": True},
    )
    check("ExternalSource with INTERNAL_REPORT type refused", False)
except ValueError as e:
    check("ExternalSource with INTERNAL_REPORT type refused", True)
    check("error mentions external type requirement",
          "external type" in str(e).lower() or "ExternalSource" in str(e))

# ===========================================================================
# Attack 6: InternalSource with DOI in content
# ===========================================================================
print("\n--- Attack 6: DOI in content field ---")
try:
    src = InternalSource(
        source_id="SRC-ATK-6",
        source_type="INTERNAL_REPORT",
        identifier="INT-006",
        title="Internal Report",
        content="See https://doi.org/10.1234/external for details",
    )
    check("DOI URL in content refused by InternalSource", False)
except ValueError:
    check("DOI URL in content refused by InternalSource", True)

# ===========================================================================
# Attack 7: InternalSource with PMID in title
# ===========================================================================
print("\n--- Attack 7: PMID in title field ---")
try:
    src = InternalSource(
        source_id="SRC-ATK-7",
        source_type="INTERNAL_REPORT",
        identifier="INT-007",
        title="Analysis of PMID 12345678 findings",
    )
    check("PMID in title refused by InternalSource", False)
except ValueError:
    check("PMID in title refused by InternalSource", True)

# ===========================================================================
# Attack 8: InternalSource with patent number in identifier
# ===========================================================================
print("\n--- Attack 8: Patent number in identifier ---")
try:
    src = InternalSource(
        source_id="SRC-ATK-8",
        source_type="INTERNAL_ANALYSIS",
        identifier="EP2436419B1",
        title="Internal Analysis",
    )
    check("Patent in identifier refused by InternalSource", False)
except ValueError:
    check("Patent in identifier refused by InternalSource", True)

# ===========================================================================
# Attack 9: Direct ExternalSource construction without VerifiedEvidence
# ===========================================================================
print("\n--- Attack 9: ExternalSource without authorization ---")
try:
    src = ExternalSource(
        source_id="SRC-ATK-9",
        source_type="DOI",
        identifier="10.1/noauth",
        title="No Auth",
        # _verified_evidence_authorization NOT provided (defaults to None)
    )
    check("ExternalSource without authorization refused", False)
except ValueError as e:
    check("ExternalSource without authorization refused", True)
    check("error mentions EXTERNAL_SOURCE_REQUIRES_AUTHORIZATION",
          "EXTERNAL_SOURCE_REQUIRES_AUTHORIZATION" in str(e))

# Also try with explicit None
try:
    src = ExternalSource(
        source_id="SRC-ATK-9b",
        source_type="DOI",
        identifier="10.1/noauth2",
        title="No Auth Explicit",
        _verified_evidence_authorization=None,
    )
    check("ExternalSource with explicit None authorization refused", False)
except ValueError:
    check("ExternalSource with explicit None authorization refused", True)

# ===========================================================================
# Attack 10: Raw Source with external type -> register_source
# ===========================================================================
print("\n--- Attack 10: Raw Source with DOI -> register_source ---")
raw = Source(
    source_id="SRC-ATK-10",
    source_type="DOI",
    identifier="10.1/raw",
    title="Raw DOI Source",
)
try:
    binding.register_source(raw)
    check("raw Source with DOI refused by register_source", False)
except TypeError:
    check("raw Source with DOI refused by register_source", True)

# ===========================================================================
# Attack 11: Raw Source with internal type -> register_source
# ===========================================================================
print("\n--- Attack 11: Raw Source with INTERNAL_REPORT -> register_source ---")
raw_internal = Source(
    source_id="SRC-ATK-11",
    source_type="INTERNAL_REPORT",
    identifier="INT-RAW",
    title="Raw Internal Source",
)
try:
    binding.register_source(raw_internal)
    check("raw Source with INTERNAL_REPORT refused by register_source", False)
except TypeError:
    check("raw Source with INTERNAL_REPORT refused by register_source", True)

# ===========================================================================
# Attack 12 (positive): Valid VerifiedEvidence -> ExternalSource
# ===========================================================================
print("\n--- Attack 12 (positive): Valid VerifiedEvidence -> ExternalSource ---")
ve = deduplicate_records(
    [{"doi": "10.1/pos12", "title": "Positive", "abstract": "Stable"}], "Crossref"
)[0].as_verified_evidence()
src = binding.register_source_from_verified_evidence(
    ve, source_id="SRC-POS-12", title="Positive Paper"
)
check("valid VerifiedEvidence -> ExternalSource accepted", isinstance(src, ExternalSource))
check("ExternalSource carries _verified_evidence_authorization",
      src._verified_evidence_authorization is not None)
check("authorization records canonical_id",
      src._verified_evidence_authorization.get("canonical_id") == "10.1/pos12")

# ===========================================================================
# Attack 13 (positive): Valid InternalSource
# ===========================================================================
print("\n--- Attack 13 (positive): Valid InternalSource ---")
legit = InternalSource(
    source_id="SRC-POS-13",
    source_type="INTERNAL_REPORT",
    identifier="INT-LEGIT-001",
    title="Legitimate Internal Report",
    verification_states=SourceVerificationStates(
        identity_verified=True,
        content_verified=True,
        support_verified=True,
    ),
)
binding.register_source(legit)
check("legitimate InternalSource accepted by register_source", True)
check("InternalSource in registry", "SRC-POS-13" in binding.sources)

# ===========================================================================
# Attack 14: Verify registry contains only authorized sources
# ===========================================================================
print("\n--- Attack 14: Registry contains only authorized sources ---")
print(f"  Total sources: {len(binding.sources)}")
authorized = {"SRC-POS-12", "SRC-POS-13"}
actual = set(binding.sources.keys())
check("only authorized source_ids in registry",
      actual == authorized, f"(got {actual})")

# ===========================================================================
# Attack 15: Type hierarchy isinstance checks
# ===========================================================================
print("\n--- Attack 15: Type hierarchy isinstance checks ---")
check("InternalSource is a Source", isinstance(legit, Source))
check("ExternalSource is a Source", isinstance(src, Source))
check("InternalSource is NOT an ExternalSource",
      not isinstance(legit, ExternalSource))
check("ExternalSource is NOT an InternalSource",
      not isinstance(src, InternalSource))

# ===========================================================================
# Summary
# ===========================================================================
print("\n" + "=" * 78)
print(f"TYPE HIERARCHY ATTACK SUMMARY: {PASS} defended / {FAIL} breached")
print("=" * 78)
if FAIL > 0:
    print("❌ TYPE BOUNDARY BREACHED — fix before commit.")
    sys.exit(1)
else:
    print("✅ ALL TYPE HIERARCHY ATTACKS DEFENDED. v30.10 boundary holds.")
    print()
    print("PRINCIPLE:")
    print("  'A security boundary should be enforced by object construction,")
    print("   not by trusting a label inside the object.'")
    print()
    print("The external-vs-internal distinction is now encoded in the TYPE")
    print("of object, not in a source_type string label:")
    print("  - InternalSource: constructor refuses external content patterns")
    print("  - ExternalSource: constructor requires _verified_evidence_authorization")
    print("  - register_source() accepts ONLY InternalSource")
    print("  - register_source_from_verified_evidence() returns ExternalSource")
    sys.exit(0)
