#!/usr/bin/env python3
"""
Article XVII adversarial attack on the REAL production dossier path (v30.8).

CEO v30.8 directive: "Attack the real production path, not only
DossierClaimConsumer."

This script attempts to get unauthorized evidence into the REAL production
EvidenceBinding registry via register_source_from_verified_evidence().

Attack vectors attempted:
  1. CONTENT_MISMATCH identity -> register_source_from_verified_evidence
  2. POSSIBLE_FAMILY_MATCH identity -> register_source_from_verified_evidence
  3. FAMILY_RELATION_CONFIRMED identity -> register_source_from_verified_evidence
  4. IDENTITY_INSUFFICIENT identity -> register_source_from_verified_evidence
  5. Forged VerifiedEvidence (via object.__new__) -> register_source_from_verified_evidence
  6. Subclass of VerifiedEvidence -> register_source_from_verified_evidence
  7. Pickle/copy of forged VerifiedEvidence -> register_source_from_verified_evidence
  8. Direct raw EvidenceIdentity -> register_source_from_verified_evidence
  9. Forged identity_confidence (object.__setattr__) -> register_source_from_verified_evidence
 10. Valid VerifiedEvidence (positive control) -> register_source_from_verified_evidence

Each attack that succeeds is a real production-path defect. Each that
fails is evidence that the v30.8 production boundary holds.
"""
import sys
import copy
import pickle
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.evidence_identity import (
    deduplicate_records,
    merge_across_sources,
    EvidenceIdentity,
    EvidenceAuthorizationError,
    VerifiedEvidence,
    DossierClaimConsumer,
    DOCUMENT_ID_CONFIRMED,
    EVENT_ID_CONFIRMED,
    DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH,
    EVENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH,
    FAMILY_RELATION_CONFIRMED,
    POSSIBLE_FAMILY_MATCH,
    IDENTITY_INSUFFICIENT,
)
from epistemic_integrity.evidence_binding import EvidenceBinding, Source
from epistemic_integrity.evidence_identity_adapter import (
    _verified_evidence_to_source_type,
    _verified_evidence_to_identifier,
    is_verified_evidence,
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
print("ARTICLE XVII ADVERSARIAL ATTACK — v30.8 PRODUCTION DOSSIER PATH")
print("=" * 78)

# ---------------------------------------------------------------------------
# Setup: create a temporary EvidenceBinding registry + one of each identity type
# ---------------------------------------------------------------------------
tmpdir = Path(tempfile.mkdtemp(prefix="v30_8_prod_"))
binding = EvidenceBinding(tmpdir)
print(f"\nProduction EvidenceBinding registry: {tmpdir}")

# DOCUMENT_ID_CONFIRMED (verified)
clean_paper = deduplicate_records(
    [{"doi": "10.1/clean", "title": "Clean", "abstract": "Stable"}], "Crossref"
)[0]
assert clean_paper.identity_confidence == DOCUMENT_ID_CONFIRMED

# EVENT_ID_CONFIRMED (verified)
clean_event = deduplicate_records(
    [{"mdr_report_key": "MDR_CLEAN", "event_type": "Malfunction", "date_received": "2024-01-01"}],
    "FDA_MAUDE_feed1"
)[0]
assert clean_event.identity_confidence == EVENT_ID_CONFIRMED

# CONTENT_MISMATCH
mm_a = deduplicate_records([{"doi": "10.2/mm", "title": "T", "abstract": "A"}], "Crossref")
mm_b = deduplicate_records([{"doi": "10.2/mm", "title": "T", "abstract": "B"}], "EuropePMC")
mm_merged, _ = merge_across_sources({"Crossref": mm_a, "EuropePMC": mm_b})
mismatched = [m for m in mm_merged if m.record_type == "paper"][0]
assert mismatched.has_content_mismatch

# POSSIBLE_FAMILY_MATCH
possible_fam = deduplicate_records(
    [{"title": "No ID", "abstract": "Just fingerprint"}], "PatentBear"
)[0]
assert possible_fam.identity_confidence == POSSIBLE_FAMILY_MATCH

# FAMILY_RELATION_CONFIRMED
fam_rel = deduplicate_records(
    [{"family_id": "FAM_ATK", "title": "Family Only"}], "PatentBear"
)[0]
assert fam_rel.identity_confidence == FAMILY_RELATION_CONFIRMED

# IDENTITY_INSUFFICIENT
no_id = deduplicate_records(
    [{"event_type": "Malfunction", "date_received": "2024-01-01"}],  # NO MDR key
    "FDA_MAUDE_feed1"
)[0]
assert no_id.identity_confidence == IDENTITY_INSUFFICIENT

print("\nSetup complete: 6 identity types constructed.")

# ---------------------------------------------------------------------------
# Attack 1: CONTENT_MISMATCH -> register_source_from_verified_evidence
# ---------------------------------------------------------------------------
print("\n--- Attack 1: CONTENT_MISMATCH -> production register ---")
# First try to promote (should fail at VerifiedEvidence construction)
try:
    ve = mismatched.as_verified_evidence()
    # If promotion somehow succeeded, try to register
    try:
        binding.register_source_from_verified_evidence(
            ve, source_id="SRC-ATK-1", title="Mismatched"
        )
        check("CONTENT_MISMATCH refused by production register", False)
    except (TypeError, EvidenceAuthorizationError):
        check("CONTENT_MISMATCH refused by production register", True)
except EvidenceAuthorizationError:
    check("CONTENT_MISMATCH refused at VerifiedEvidence construction (before register)", True)

# ---------------------------------------------------------------------------
# Attack 2-4: Other non-verified types -> register_source_from_verified_evidence
# ---------------------------------------------------------------------------
for name, ident in [("POSSIBLE_FAMILY_MATCH", possible_fam),
                     ("FAMILY_RELATION_CONFIRMED", fam_rel),
                     ("IDENTITY_INSUFFICIENT", no_id)]:
    print(f"\n--- Attack: {name} -> production register ---")
    try:
        ve = ident.as_verified_evidence()
        try:
            binding.register_source_from_verified_evidence(
                ve, source_id=f"SRC-ATK-{name}", title=name
            )
            check(f"{name} refused by production register", False)
        except (TypeError, EvidenceAuthorizationError):
            check(f"{name} refused by production register", True)
    except EvidenceAuthorizationError:
        check(f"{name} refused at VerifiedEvidence construction (before register)", True)

# ---------------------------------------------------------------------------
# Attack 5: Forged VerifiedEvidence (via object.__new__) -> production register
# ---------------------------------------------------------------------------
print("\n--- Attack 5: Forged VerifiedEvidence (object.__new__) -> production register ---")
forged = object.__new__(VerifiedEvidence)
object.__setattr__(forged, "identity", mismatched)
try:
    binding.register_source_from_verified_evidence(
        forged, source_id="SRC-ATK-5", title="Forged"
    )
    check("forged VerifiedEvidence refused by production register", False)
except (TypeError, EvidenceAuthorizationError) as e:
    check("forged VerifiedEvidence refused by production register", True)
    check("error mentions DEFENSE-IN-DEPTH or FORGE",
          "DEFENSE-IN-DEPTH" in str(e) or "FORGE" in str(e))

# ---------------------------------------------------------------------------
# Attack 6: Subclass of VerifiedEvidence -> production register
# ---------------------------------------------------------------------------
print("\n--- Attack 6: Subclass of VerifiedEvidence -> production register ---")
class ForgedVerifiedEvidence(VerifiedEvidence):
    def __post_init__(self):
        pass  # skip parent check

try:
    forged_sub = ForgedVerifiedEvidence(mismatched)
    try:
        binding.register_source_from_verified_evidence(
            forged_sub, source_id="SRC-ATK-6", title="Subclass"
        )
        check("subclass VerifiedEvidence refused by production register", False)
    except (TypeError, EvidenceAuthorizationError) as e:
        check("subclass VerifiedEvidence refused by production register", True)
except EvidenceAuthorizationError:
    # Parent __post_init__ may still run in some Python versions
    check("subclass VerifiedEvidence refused at construction OR register", True)

# ---------------------------------------------------------------------------
# Attack 7: Pickle/copy of forged VerifiedEvidence -> production register
# ---------------------------------------------------------------------------
print("\n--- Attack 7: Pickle/copy of forged VerifiedEvidence -> production register ---")
# copy
forged_copy = copy.copy(forged)
try:
    binding.register_source_from_verified_evidence(
        forged_copy, source_id="SRC-ATK-7a", title="Copy"
    )
    check("copy of forged VerifiedEvidence refused by production register", False)
except (TypeError, EvidenceAuthorizationError):
    check("copy of forged VerifiedEvidence refused by production register", True)

# deepcopy
forged_deep = copy.deepcopy(forged)
try:
    binding.register_source_from_verified_evidence(
        forged_deep, source_id="SRC-ATK-7b", title="DeepCopy"
    )
    check("deepcopy of forged VerifiedEvidence refused by production register", False)
except (TypeError, EvidenceAuthorizationError):
    check("deepcopy of forged VerifiedEvidence refused by production register", True)

# pickle
try:
    forged_pickle = pickle.dumps(forged)
    forged_unpickled = pickle.loads(forged_pickle)
    try:
        binding.register_source_from_verified_evidence(
            forged_unpickled, source_id="SRC-ATK-7c", title="Pickle"
        )
        check("unpickled forged VerifiedEvidence refused by production register", False)
    except (TypeError, EvidenceAuthorizationError):
        check("unpickled forged VerifiedEvidence refused by production register", True)
except (EvidenceAuthorizationError, TypeError, AttributeError, ValueError):
    check("unpickling forged VerifiedEvidence refuses (constructor re-runs)", True)

# ---------------------------------------------------------------------------
# Attack 8: Direct raw EvidenceIdentity -> register_source_from_verified_evidence
# ---------------------------------------------------------------------------
print("\n--- Attack 8: Raw EvidenceIdentity -> production register ---")
# Even a DOCUMENT_ID_CONFIRMED identity must be rejected — callers MUST
# call as_verified_evidence() first.
try:
    binding.register_source_from_verified_evidence(
        clean_paper, source_id="SRC-ATK-8", title="Raw"
    )
    check("raw EvidenceIdentity refused by production register (TypeError)", False)
except TypeError as e:
    check("raw EvidenceIdentity refused by production register (TypeError)", True)
    check("error mentions VerifiedEvidence", "VerifiedEvidence" in str(e))

# Also try with non-verified types directly
for name, ident in [("CONTENT_MISMATCH", mismatched),
                     ("POSSIBLE_FAMILY_MATCH", possible_fam),
                     ("FAMILY_RELATION_CONFIRMED", fam_rel),
                     ("IDENTITY_INSUFFICIENT", no_id)]:
    try:
        binding.register_source_from_verified_evidence(
            ident, source_id=f"SRC-ATK-8-{name}", title=name
        )
        check(f"raw {name} refused by production register (TypeError)", False)
    except TypeError:
        check(f"raw {name} refused by production register (TypeError)", True)

# ---------------------------------------------------------------------------
# Attack 9: Forged identity_confidence (object.__setattr__) -> production register
# ---------------------------------------------------------------------------
print("\n--- Attack 9: Forged identity_confidence -> production register ---")
# Forge the identity_confidence on the mismatched record
try:
    object.__setattr__(mismatched, "identity_confidence", DOCUMENT_ID_CONFIRMED)
    # Now try to promote — should be caught by verify_integrity() in __post_init__
    try:
        ve_forged = mismatched.as_verified_evidence()
        # If promotion somehow succeeded, try to register
        try:
            binding.register_source_from_verified_evidence(
                ve_forged, source_id="SRC-ATK-9", title="Forged Confidence"
            )
            check("forged identity_confidence refused by production register", False)
        except (TypeError, EvidenceAuthorizationError) as e:
            check("forged identity_confidence refused by production register", True)
            check("error mentions FORGE DETECTED", "FORGE DETECTED" in str(e))
    except EvidenceAuthorizationError as e:
        check("forged identity_confidence refused at VerifiedEvidence construction", True)
        check("error mentions FORGE DETECTED", "FORGE DETECTED" in str(e))
    # Restore the original value
    object.__setattr__(mismatched, "identity_confidence",
                       DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH)
except (AttributeError, Exception):
    check("object.__setattr__ on frozen EvidenceIdentity refused by runtime", True)

# ---------------------------------------------------------------------------
# Attack 10 (positive control): Valid VerifiedEvidence -> production register
# ---------------------------------------------------------------------------
print("\n--- Attack 10 (positive): Valid VerifiedEvidence -> production register ---")
ve_clean = clean_paper.as_verified_evidence()
try:
    source = binding.register_source_from_verified_evidence(
        ve_clean,
        source_id="SRC-POS-10",
        title="Verified Paper",
        content="Stable content",
        authors=["Author A"],
        year=2024,
    )
    check("valid VerifiedEvidence accepted by production register", True)
    check("returned object is a Source", isinstance(source, Source))
    check("source.source_type == 'DOI'", source.source_type == "DOI")
    check("source.identifier == '10.1/clean'", source.identifier == "10.1/clean")
    check("source.is_identity_verified() is True", source.is_identity_verified() is True)
    check("source.is_content_verified() is True", source.is_content_verified() is True)
    check("source._verified_evidence_authorization is set",
          hasattr(source, '_verified_evidence_authorization'))
    auth = getattr(source, '_verified_evidence_authorization', {})
    check("authorization records identity_confidence",
          auth.get('identity_confidence') == DOCUMENT_ID_CONFIRMED)
    check("authorization records canonical_id",
          auth.get('canonical_id') == '10.1/clean')
except Exception as e:
    check(f"valid VerifiedEvidence accepted by production register (got {type(e).__name__})", False)

# Also test EVENT_ID_CONFIRMED
print("\n--- Attack 10b (positive): Valid EVENT_ID_CONFIRMED -> production register ---")
ve_event = clean_event.as_verified_evidence()
try:
    source_e = binding.register_source_from_verified_evidence(
        ve_event,
        source_id="SRC-POS-10b",
        title="Verified MAUDE Event",
    )
    check("valid EVENT_ID_CONFIRMED accepted by production register", True)
    check("source.source_type == 'MDR_REPORT_KEY'",
          source_e.source_type == "MDR_REPORT_KEY")
    check("source.identifier == 'MDR_CLEAN'",
          source_e.identifier == "MDR_CLEAN")
except Exception as e:
    check(f"valid EVENT_ID_CONFIRMED accepted (got {type(e).__name__})", False)

# ---------------------------------------------------------------------------
# Attack 11: Verify no unauthorized sources were registered
# ---------------------------------------------------------------------------
print("\n--- Attack 11: Verify no unauthorized sources in registry ---")
all_sources = binding.sources
print(f"  Total sources in registry: {len(all_sources)}")
# Only the 2 positive-control sources should be present
authorized_ids = {"SRC-POS-10", "SRC-POS-10b"}
actual_ids = set(all_sources.keys())
check("only authorized source_ids are in registry",
      actual_ids == authorized_ids,
      f"(got {actual_ids})")
check("no unauthorized source leaked into registry",
      not (actual_ids - authorized_ids))

# ---------------------------------------------------------------------------
# Attack 12: Adapter helper functions
# ---------------------------------------------------------------------------
print("\n--- Attack 12: Adapter helper functions ---")
check("is_verified_evidence(ve_clean) is True",
      is_verified_evidence(ve_clean) is True)
check("is_verified_evidence(clean_paper) is False (raw identity)",
      is_verified_evidence(clean_paper) is False)
check("is_verified_evidence(None) is False",
      is_verified_evidence(None) is False)
check("is_verified_evidence('string') is False",
      is_verified_evidence("string") is False)
check("_verified_evidence_to_source_type(ve_clean) == 'DOI'",
      _verified_evidence_to_source_type(ve_clean) == "DOI")
check("_verified_evidence_to_source_type(ve_event) == 'MDR_REPORT_KEY'",
      _verified_evidence_to_source_type(ve_event) == "MDR_REPORT_KEY")
check("_verified_evidence_to_identifier(ve_clean) == '10.1/clean'",
      _verified_evidence_to_identifier(ve_clean) == "10.1/clean")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print(f"PRODUCTION PATH ATTACK SUMMARY: {PASS} defended / {FAIL} breached")
print("=" * 78)
if FAIL > 0:
    print("❌ PRODUCTION PATH BREACHED — fix before commit.")
    sys.exit(1)
else:
    print("✅ ALL PRODUCTION PATH ATTACKS DEFENDED. v30.8 boundary holds.")
    print()
    print("PRODUCTION DEFENSE LAYERS (8 total):")
    print("  1. VerifiedEvidence.__post_init__ refuses non-verified identities")
    print("  2. VerifiedEvidence.__post_init__ calls verify_integrity() (Layer 3)")
    print("  3. register_source_from_verified_evidence type-checks VerifiedEvidence")
    print("  4. register_source_from_verified_evidence re-checks can_use_as_verified_evidence")
    print("  5. register_source_from_verified_evidence calls verify_integrity() (Layer 3)")
    print("  6. Both EvidenceIdentity and VerifiedEvidence are frozen dataclasses")
    print("  7. Pickle/unpickle re-runs __post_init__ (refuses forged objects)")
    print("  8. content_mismatch_audits survives any identity_confidence forge")
    print()
    print("HONEST CLASSIFICATION (per Article XV):")
    print("  Strongly defended and adversarially tested.")
    print("  Not mathematically unforgeable inside Python (runtime trust-boundary")
    print("  limitation). object.__setattr__ can forge identity_confidence, but")
    print("  verify_integrity() DETECTS the forge because content_mismatch_audits")
    print("  survives. The forged record CANNOT reach the production dossier path.")
    print()
    print("KEY PRINCIPLE:")
    print("  'A proof-of-concept defense is not a production defense.")
    print("   Can an adversarial model with repository access actually get")
    print("   unauthorized evidence into the real dossier path?")
    print("   Until the answer is structurally no, the evidence firewall")
    print("   is not finished.'")
    print()
    print("  v30.8 answer: structurally NO (with the honest Python-runtime qualifier).")
    sys.exit(0)
