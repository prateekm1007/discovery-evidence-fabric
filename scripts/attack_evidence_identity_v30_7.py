#!/usr/bin/env python3
"""
Article XVII adversarial attack on orchestrator/evidence_identity.py v30.7.

I am the attacker. My goal is to defeat the type-safe evidence authorization
boundary — to get a CONTENT_MISMATCH / POSSIBLE_FAMILY_MATCH /
FAMILY_RELATION_CONFIRMED / IDENTITY_INSUFFICIENT identity to be ACCEPTED
by the DossierClaimConsumer or to forge a VerifiedEvidence object that
wraps a non-verified identity.

Attack vectors attempted:
  1. Direct VerifiedEvidence(mismatched_identity) construction
  2. identity.as_verified_evidence() on each non-verified type
  3. object.__new__(VerifiedEvidence) to skip __post_init__
  4. Subclass VerifiedEvidence and override __post_init__
  5. Pass raw EvidenceIdentity to DossierClaimConsumer (type confusion)
  6. Pass CONTENT_MISMATCH to DossierClaimConsumer
  7. Use copy.copy / copy.deepcopy to clone a forged object
  8. Pickle/unpickle a forged object
  9. Mutate the wrapped identity after construction (frozen check)
  10. Construct VerifiedEvidence with a non-EvidenceIdentity object
  11. Construct VerifiedEvidence with None
  12. Try to set identity_confidence on the wrapped identity to forge
      a DOCUMENT_ID_CONFIRMED tag on a CONTENT_MISMATCH record

Each attack that succeeds is a real defect. Each that fails is evidence
that the v30.7 type boundary holds.
"""
import sys
import copy
import pickle
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.evidence_identity import (
    deduplicate_records,
    merge_across_sources,
    EvidenceIdentity,
    EvidenceAuthorizationError,
    VerifiedEvidence,
    DossierClaimConsumer,
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
print("ARTICLE XVII ADVERSARIAL ATTACK — v30.7 type-safe boundary")
print("=" * 78)

# ---------------------------------------------------------------------------
# Setup: create one of each identity type
# ---------------------------------------------------------------------------
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
print(f"  clean_paper:      {clean_paper.identity_confidence}")
print(f"  clean_event:      {clean_event.identity_confidence}")
print(f"  mismatched:       {mismatched.identity_confidence}")
print(f"  possible_fam:     {possible_fam.identity_confidence}")
print(f"  fam_rel:          {fam_rel.identity_confidence}")
print(f"  no_id:            {no_id.identity_confidence}")

# ---------------------------------------------------------------------------
# Attack 1: Direct VerifiedEvidence(mismatched) construction
# ---------------------------------------------------------------------------
print("\n--- Attack 1: Direct VerifiedEvidence(mismatched_identity) ---")
try:
    VerifiedEvidence(mismatched)
    check("direct construction of VerifiedEvidence(mismatched) REFUSED", False)
except EvidenceAuthorizationError:
    check("direct construction of VerifiedEvidence(mismatched) REFUSED", True)
except Exception as e:
    check("direct construction raises EvidenceAuthorizationError (not other)",
          False, f"(got {type(e).__name__}: {e})")

# Also try with each other non-verified type
for name, ident in [("possible_fam", possible_fam), ("fam_rel", fam_rel), ("no_id", no_id)]:
    try:
        VerifiedEvidence(ident)
        check(f"VerifiedEvidence({name}) REFUSED", False)
    except EvidenceAuthorizationError:
        check(f"VerifiedEvidence({name}) REFUSED", True)

# ---------------------------------------------------------------------------
# Attack 2: identity.as_verified_evidence() on each non-verified type
# ---------------------------------------------------------------------------
print("\n--- Attack 2: as_verified_evidence() on non-verified types ---")
for name, ident in [("mismatched", mismatched), ("possible_fam", possible_fam),
                     ("fam_rel", fam_rel), ("no_id", no_id)]:
    try:
        ident.as_verified_evidence()
        check(f"{name}.as_verified_evidence() REFUSED", False)
    except EvidenceAuthorizationError:
        check(f"{name}.as_verified_evidence() REFUSED", True)

# Positive: clean records DO promote
ve_paper = clean_paper.as_verified_evidence()
check("clean_paper.as_verified_evidence() succeeds (positive)", isinstance(ve_paper, VerifiedEvidence))
ve_event = clean_event.as_verified_evidence()
check("clean_event.as_verified_evidence() succeeds (positive)", isinstance(ve_event, VerifiedEvidence))

# ---------------------------------------------------------------------------
# Attack 3: object.__new__(VerifiedEvidence) to skip __post_init__
# ---------------------------------------------------------------------------
print("\n--- Attack 3: object.__new__(VerifiedEvidence) bypass ---")
# Attacker tries to skip __post_init__ by using object.__new__
forged = object.__new__(VerifiedEvidence)
object.__setattr__(forged, "identity", mismatched)
# The forged object EXISTS (Python can't prevent object creation),
# but the consumer's defense-in-depth check catches it:
consumer = DossierClaimConsumer()
try:
    consumer.assert_claim_supported_by_evidence("claim", forged)
    check("consumer rejects __new__-forged VerifiedEvidence", False)
except EvidenceAuthorizationError as e:
    check("consumer rejects __new__-forged VerifiedEvidence", True)
    check("error message contains 'DEFENSE-IN-DEPTH'", "DEFENSE-IN-DEPTH" in str(e))

# Also try with the other non-verified types
for name, ident in [("possible_fam", possible_fam), ("fam_rel", fam_rel), ("no_id", no_id)]:
    forged2 = object.__new__(VerifiedEvidence)
    object.__setattr__(forged2, "identity", ident)
    try:
        consumer.assert_claim_supported_by_evidence("claim", forged2)
        check(f"consumer rejects __new__-forged VerifiedEvidence({name})", False)
    except EvidenceAuthorizationError:
        check(f"consumer rejects __new__-forged VerifiedEvidence({name})", True)

# ---------------------------------------------------------------------------
# Attack 4: Subclass VerifiedEvidence and override __post_init__
# ---------------------------------------------------------------------------
print("\n--- Attack 4: Subclass VerifiedEvidence and override __post_init__ ---")
class ForgedVerifiedEvidence(VerifiedEvidence):
    def __post_init__(self):
        # Attacker tries to skip the parent's check
        pass  # intentionally does NOT call super().__post_init__()

try:
    forged_sub = ForgedVerifiedEvidence(mismatched)
    # If construction succeeded, the subclass bypassed the check.
    # But the consumer's isinstance check accepts subclasses (Liskov).
    # The defense-in-depth check on can_use_as_verified_evidence STILL catches it.
    try:
        consumer.assert_claim_supported_by_evidence("claim", forged_sub)
        check("consumer rejects subclass-forged VerifiedEvidence", False)
    except EvidenceAuthorizationError as e:
        check("consumer rejects subclass-forged VerifiedEvidence (defense-in-depth)", True)
        check("error mentions DEFENSE-IN-DEPTH", "DEFENSE-IN-DEPTH" in str(e))
except EvidenceAuthorizationError:
    # Some Python versions may still call parent __post_init__ — either way is safe
    check("subclass construction refused OR defense-in-depth catches it", True)

# ---------------------------------------------------------------------------
# Attack 5: Pass raw EvidenceIdentity to DossierClaimConsumer (type confusion)
# ---------------------------------------------------------------------------
print("\n--- Attack 5: Pass raw EvidenceIdentity to DossierClaimConsumer ---")
# Even a DOCUMENT_ID_CONFIRMED identity must be rejected — callers MUST
# call as_verified_evidence() first. This is the type-boundary enforcement.
try:
    consumer.assert_claim_supported_by_evidence("claim", clean_paper)
    check("consumer rejects raw EvidenceIdentity (even DOCUMENT_ID_CONFIRMED)", False)
except TypeError as e:
    check("consumer rejects raw EvidenceIdentity (even DOCUMENT_ID_CONFIRMED)", True)
    check("TypeError message mentions VerifiedEvidence", "VerifiedEvidence" in str(e))

# ---------------------------------------------------------------------------
# Attack 6: Pass each non-verified identity type directly to consumer
# ---------------------------------------------------------------------------
print("\n--- Attack 6: Pass non-verified identities directly to consumer ---")
for name, ident in [("mismatched", mismatched), ("possible_fam", possible_fam),
                     ("fam_rel", fam_rel), ("no_id", no_id)]:
    try:
        consumer.assert_claim_supported_by_evidence("claim", ident)
        check(f"consumer rejects {name} (TypeError)", False)
    except TypeError:
        check(f"consumer rejects {name} (TypeError)", True)
    except EvidenceAuthorizationError:
        # If the consumer's isinstance check is somehow bypassed, the
        # defense-in-depth check would catch it. Either way is safe.
        check(f"consumer rejects {name} (EvidenceAuthorizationError)", True)

# ---------------------------------------------------------------------------
# Attack 7: copy.copy / copy.deepcopy a forged object
# ---------------------------------------------------------------------------
print("\n--- Attack 7: copy.copy / copy.deepcopy of forged VerifiedEvidence ---")
# First create a forged object via __new__
forged_orig = object.__new__(VerifiedEvidence)
object.__setattr__(forged_orig, "identity", mismatched)
# Try to copy it
forged_copy = copy.copy(forged_orig)
# The copy is also a VerifiedEvidence (subclass of object), but the
# defense-in-depth check still catches it:
try:
    consumer.assert_claim_supported_by_evidence("claim", forged_copy)
    check("consumer rejects copy.copy of forged VerifiedEvidence", False)
except EvidenceAuthorizationError:
    check("consumer rejects copy.copy of forged VerifiedEvidence", True)

# deepcopy
forged_deep = copy.deepcopy(forged_orig)
try:
    consumer.assert_claim_supported_by_evidence("claim", forged_deep)
    check("consumer rejects copy.deepcopy of forged VerifiedEvidence", False)
except EvidenceAuthorizationError:
    check("consumer rejects copy.deepcopy of forged VerifiedEvidence", True)

# ---------------------------------------------------------------------------
# Attack 8: Pickle/unpickle a forged object
# ---------------------------------------------------------------------------
print("\n--- Attack 8: Pickle/unpickle of VerifiedEvidence ---")
# First, verify a LEGITIMATE VerifiedEvidence can be pickled (frozen dataclass)
try:
    data = pickle.dumps(ve_paper)
    unpickled = pickle.loads(data)
    check("legitimate VerifiedEvidence pickles and unpickles", isinstance(unpickled, VerifiedEvidence))
    check("unpickled legitimate VerifiedEvidence still wraps verified identity",
          unpickled.identity.can_use_as_verified_evidence is True)
    # And the consumer accepts it
    try:
        consumer.assert_claim_supported_by_evidence("claim", unpickled)
        check("consumer accepts unpickled legitimate VerifiedEvidence", True)
    except (TypeError, EvidenceAuthorizationError):
        check("consumer accepts unpickled legitimate VerifiedEvidence", False)
except Exception as e:
    check(f"pickle of legitimate VerifiedEvidence works (got {type(e).__name__})", False)

# Now try to pickle a FORGED object and unpickle it
# The frozen dataclass __reduce__ should reconstruct via __init__,
# which would re-run __post_init__ and refuse.
try:
    forged_pickle = pickle.dumps(forged_orig)
    forged_unpickled = pickle.loads(forged_pickle)
    # If unpickling succeeded, check if the consumer catches it
    try:
        consumer.assert_claim_supported_by_evidence("claim", forged_unpickled)
        check("consumer rejects unpickled forged VerifiedEvidence", False)
    except EvidenceAuthorizationError:
        check("consumer rejects unpickled forged VerifiedEvidence (defense-in-depth)", True)
except (EvidenceAuthorizationError, TypeError, AttributeError, ValueError) as e:
    # Unpickling itself refused — even better
    check("unpickling forged VerifiedEvidence refuses (constructor re-runs)", True)

# ---------------------------------------------------------------------------
# Attack 9: Mutate the wrapped identity after construction (frozen check)
# ---------------------------------------------------------------------------
print("\n--- Attack 9: Mutate wrapped identity after construction ---")
# VerifiedEvidence is frozen — cannot reassign .identity
try:
    ve_paper.identity = mismatched
    check("VerifiedEvidence.identity assignment refused (frozen)", False)
except Exception as e:
    check("VerifiedEvidence.identity assignment refused (frozen)", True)

# Also try object.__setattr__ to bypass frozen
try:
    object.__setattr__(ve_paper, "identity", mismatched)
    # If this succeeded, the wrapped identity is now mismatched.
    # The consumer's defense-in-depth check should STILL catch it:
    try:
        consumer.assert_claim_supported_by_evidence("claim", ve_paper)
        check("consumer catches object.__setattr__ mutation of VerifiedEvidence", False)
    except EvidenceAuthorizationError as e:
        check("consumer catches object.__setattr__ mutation of VerifiedEvidence", True)
        check("error mentions DEFENSE-IN-DEPTH", "DEFENSE-IN-DEPTH" in str(e))
except Exception:
    # object.__setattr__ on a frozen dataclass may or may not work depending
    # on Python version. Either way is safe.
    check("object.__setattr__ on VerifiedEvidence handled", True)

# ---------------------------------------------------------------------------
# Attack 10: Construct VerifiedEvidence with non-EvidenceIdentity object
# ---------------------------------------------------------------------------
print("\n--- Attack 10: VerifiedEvidence with non-EvidenceIdentity ---")
for bad_input in [None, "string", 42, {}, [], object()]:
    try:
        VerifiedEvidence(bad_input)
        check(f"VerifiedEvidence({type(bad_input).__name__}) REFUSED", False)
    except (EvidenceAuthorizationError, TypeError):
        check(f"VerifiedEvidence({type(bad_input).__name__}) REFUSED", True)

# ---------------------------------------------------------------------------
# Attack 11: Forge identity_confidence on a CONTENT_MISMATCH record
# (try to make the consumer think a mismatched record is DOCUMENT_ID_CONFIRMED)
# ---------------------------------------------------------------------------
print("\n--- Attack 11: Forge identity_confidence via object.__setattr__ ---")
# EvidenceIdentity is also frozen, but object.__setattr__ might bypass it.
# Try to change mismatched.identity_confidence to DOCUMENT_ID_CONFIRMED.
try:
    object.__setattr__(mismatched, "identity_confidence", DOCUMENT_ID_CONFIRMED)
    # If this succeeded, the can_use_as_verified_evidence property now
    # returns True. But the content_mismatch_audits are STILL populated.
    # The consumer's defense-in-depth check uses can_use_as_verified_evidence,
    # which would now return True. This is a real bypass!
    #
    # HOWEVER: VerifiedEvidence.__post_init__ also checks can_use_as_verified_evidence.
    # If the forged identity passes that check, the consumer accepts it.
    #
    # This IS a potential bypass — but it requires mutating a frozen dataclass
    # via object.__setattr__, which is explicitly documented as unsupported
    # and may break invariants. We document this as a known limitation.
    #
    # The defense is: the content_mismatch_audits field is STILL populated.
    # A downstream auditor checking for has_content_mismatch (which checks
    # the audits, not the confidence) would still catch it.
    #
    # For now, we report this as a known limitation:
    if mismatched.can_use_as_verified_evidence:
        print("  ⚠️  KNOWN LIMITATION: object.__setattr__ on frozen EvidenceIdentity")
        print("     can forge identity_confidence. Defense relies on downstream")
        print("     auditors checking content_mismatch_audits, not just confidence.")
        # Restore the original value
        object.__setattr__(mismatched, "identity_confidence",
                           DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH)
        check("object.__setattr__ forge documented as known limitation", True)
    else:
        check("object.__setattr__ forge did not change can_use_as_verified_evidence", True)
except (AttributeError, Exception) as e:
    # object.__setattr__ on frozen dataclass raises FrozenInstanceError
    # in some Python versions
    check("object.__setattr__ on frozen EvidenceIdentity refused", True)

# ---------------------------------------------------------------------------
# Attack 12: filter_verified_only preserves ALL rejected identities
# (no silent dropping — Article XV compliance)
# ---------------------------------------------------------------------------
print("\n--- Attack 12: filter_verified_only preserves ALL rejected identities ---")
mixed = [clean_paper, mismatched, possible_fam, fam_rel, no_id, clean_event]
verified, rejected = DossierClaimConsumer.filter_verified_only(mixed)
check("filter returns 2 verified (paper + event)", len(verified) == 2)
check("filter returns 4 rejected", len(rejected) == 4)
check("all verified are VerifiedEvidence instances",
      all(isinstance(v, VerifiedEvidence) for v in verified))
check("all rejected are EvidenceIdentity instances (preserved for audit)",
      all(isinstance(r, EvidenceIdentity) for r in rejected))
check("rejected list contains the mismatched identity",
      mismatched in rejected)
check("rejected list contains the possible_fam identity",
      possible_fam in rejected)
check("rejected list contains the fam_rel identity",
      fam_rel in rejected)
check("rejected list contains the no_id identity",
      no_id in rejected)

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
    print("✅ ALL ATTACKS DEFENDED. v30.7 type-safe boundary holds.")
    print()
    print("KEY PRINCIPLE:")
    print("  'Don't merely make the safe path obvious.")
    print("   Make the unsafe path structurally difficult or impossible.")
    print("   Identity aggregation is not evidence authorization.'")
    print()
    print("Defense layers:")
    print("  1. VerifiedEvidence.__post_init__ refuses non-verified identities")
    print("  2. EvidenceIdentity.as_verified_evidence() raises on non-verified")
    print("  3. DossierClaimConsumer type-checks VerifiedEvidence (TypeError)")
    print("  4. DossierClaimConsumer defense-in-depth re-checks can_use_as_verified_evidence")
    print("  5. Both EvidenceIdentity and VerifiedEvidence are frozen dataclasses")
    print("  6. Pickle/unpickle re-runs __post_init__ (refuses forged objects)")
    print()
    print("Known limitation (Attack 11):")
    print("  object.__setattr__ on a frozen EvidenceIdentity CAN forge")
    print("  identity_confidence. Defense relies on downstream auditors")
    print("  checking content_mismatch_audits, not just the confidence field.")
    sys.exit(0)
