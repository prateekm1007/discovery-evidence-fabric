#!/usr/bin/env python3
"""
Article XVII adversarial attack on v30.13 corrected anchor semantics.

CEO v30.13 directive: "A provenance anchor must prove history, not freeze
the future. We want immutable evidence, not an immutable repository."

v30.12 compared commit_anchor to CURRENT_HEAD and ledger_root_anchor to
CURRENT ledger root. This was TOO STRICT — evidence registered at Commit A
would become invalid after the repository advanced to Commit B.

v30.13 CORRECTS the semantics:
  - commit_anchor: verify the registration commit STILL EXISTS (not == HEAD)
  - registration_transition_hash: verify it EXISTS in the immutable ledger
  - ledger_root_anchor: preserved as historical metadata, NOT a verification target

Key test:
  register evidence at A → append legitimate commit B → reload → evidence VALID

Also test:
  alter artifact at A → BLOCK
  delete registration transition → BLOCK
  alter transition → BLOCK
"""
import sys
import json
import hashlib
import tempfile
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.evidence_identity import (
    deduplicate_records,
    VerifiedEvidence,
    DOCUMENT_ID_CONFIRMED,
)
from epistemic_integrity.evidence_binding import (
    EvidenceBinding,
    Source,
    InternalSource,
    ExternalSource,
    SourceVerificationStates,
    VerificationEnvelope,
    _compute_verification_envelope,
    _verify_envelope,
    _verify_commit_exists,
    _verify_transition_in_ledger,
    _get_current_git_commit,
    _get_current_ledger_root,
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
print("ARTICLE XVII ADVERSARIAL ATTACK — v30.13 CORRECTED ANCHOR SEMANTICS")
print("=" * 78)

# ===========================================================================
# Attack 1 (positive): register at A → reload → evidence VALID
# ===========================================================================
print("\n--- Attack 1 (positive): register at A → reload → VALID ---")
tmpdir1 = Path(tempfile.mkdtemp(prefix="v30_13_a1_"))
binding1 = EvidenceBinding(tmpdir1)
ve1 = deduplicate_records(
    [{"doi": "10.1/a1", "title": "Test A1", "abstract": "Content A1"}], "Crossref"
)[0].as_verified_evidence()
src1 = binding1.register_source_from_verified_evidence(
    ve1, source_id="SRC-A1", title="Test A1", content="Content A1"
)
binding1._save()

# Reload
binding1r = EvidenceBinding(tmpdir1)
src1r = binding1r.sources.get("SRC-A1")
check("evidence valid after reload (same commit)", isinstance(src1r, ExternalSource))
check("evidence has commit_anchor", src1r._verification_envelope.commit_anchor is not None)
check("commit_anchor still exists in repo",
      _verify_commit_exists(src1r._verification_envelope.commit_anchor))

# ===========================================================================
# Attack 2 (KEY TEST): register at A → append commit B → reload → VALID
# ===========================================================================
print("\n--- Attack 2 (KEY): register at A → append commit B → evidence VALID ---")
# This is the critical test. v30.12 would FAIL this because commit_anchor
# would not match CURRENT_HEAD after commit B is appended.
# v30.13 should PASS because we verify the commit EXISTS, not that it
# matches HEAD.

tmpdir2 = Path(tempfile.mkdtemp(prefix="v30_13_a2_"))
binding2 = EvidenceBinding(tmpdir2)
ve2 = deduplicate_records(
    [{"doi": "10.1/a2", "title": "Test A2", "abstract": "Content A2"}], "Crossref"
)[0].as_verified_evidence()
src2 = binding2.register_source_from_verified_evidence(
    ve2, source_id="SRC-A2", title="Test A2", content="Content A2"
)
binding2._save()

# Record the registration commit
registration_commit = src2._verification_envelope.commit_anchor
current_head_before = _get_current_git_commit()
check("registration commit == current HEAD at registration",
      registration_commit == current_head_before)

# Append a legitimate commit (create a new file and commit)
test_file = Path("/home/z/my-project/discovery-evidence-fabric") / "v30_13_advance_test.txt"
test_file.write_text(f"Legitimate advance commit for v30.13 test at {tmpdir2}")
subprocess.run(["git", "add", str(test_file)], cwd=str(Path(__file__).parent.parent), check=True)
subprocess.run(
    ["git", "commit", "-m", "test: v30.13 advance commit — evidence must survive"],
    cwd=str(Path(__file__).parent.parent), check=True,
    capture_output=True
)
current_head_after = _get_current_git_commit()
check("HEAD advanced after new commit", current_head_after != current_head_before)
check("registration commit still exists after advance",
      _verify_commit_exists(registration_commit))

# Reload the evidence — it should STILL be valid
binding2r = EvidenceBinding(tmpdir2)
src2r = binding2r.sources.get("SRC-A2")
check("evidence VALID after repository advanced (v30.13 key fix)",
      isinstance(src2r, ExternalSource),
      f"(got {type(src2r).__name__ if src2r else 'None'})")
if src2r:
    check("evidence commit_anchor is the original (not current HEAD)",
          src2r._verification_envelope.commit_anchor == registration_commit)
    check("evidence commit_anchor != current HEAD (proves historical, not current)",
          src2r._verification_envelope.commit_anchor != current_head_after)

# Clean up the advance commit — reset to the ORIGINAL commit (not HEAD~1,
# which could go to the wrong place if the script ran multiple times)
subprocess.run(
    ["git", "reset", "--hard", current_head_before],
    cwd=str(Path(__file__).parent.parent), check=True, capture_output=True
)
test_file.unlink(missing_ok=True)

# ===========================================================================
# Attack 3: alter artifact at registration commit → BLOCK
# ===========================================================================
print("\n--- Attack 3: alter auth dict + recompute → identifier mismatch ---")
tmpdir3 = Path(tempfile.mkdtemp(prefix="v30_13_a3_"))
binding3 = EvidenceBinding(tmpdir3)
ve3 = deduplicate_records(
    [{"doi": "10.1/a3", "title": "Test A3", "abstract": "Content A3"}], "Crossref"
)[0].as_verified_evidence()
binding3.register_source_from_verified_evidence(
    ve3, source_id="SRC-A3", title="Test A3"
)
binding3._save()

# Attacker: change canonical_id in auth dict + recompute envelope
with open(tmpdir3 / "source_registry.json") as f:
    data3 = json.load(f)
for src in data3["sources"]:
    if src["source_id"] == "SRC-A3":
        src["_verified_evidence_authorization"]["canonical_id"] = "10.1/FORGED"
        auth = src["_verified_evidence_authorization"]
        env = _compute_verification_envelope(
            auth,
            src["_verification_envelope"]["commit_anchor"],
            src["_verification_envelope"]["ledger_root_anchor"],
        )
        src["_verification_envelope"]["verification_hash"] = env.verification_hash
with open(tmpdir3 / "source_registry.json", "w") as f:
    json.dump(data3, f)

# Reload — identifier mismatch should BLOCK
try:
    binding3r = EvidenceBinding(tmpdir3)
    src3r = binding3r.sources.get("SRC-A3")
    check("altered auth canonical_id detected (BLOCK)", src3r is None)
except (ValueError, Exception):
    check("altered auth canonical_id detected (BLOCK)", True)

# ===========================================================================
# Attack 4: delete registration transition from ledger → BLOCK
# ===========================================================================
print("\n--- Attack 4: registration transition not in ledger → BLOCK ---")
tmpdir4 = Path(tempfile.mkdtemp(prefix="v30_13_a4_"))
binding4 = EvidenceBinding(tmpdir4)
ve4 = deduplicate_records(
    [{"doi": "10.1/a4", "title": "Test A4", "abstract": "Content A4"}], "Crossref"
)[0].as_verified_evidence()
binding4.register_source_from_verified_evidence(
    ve4, source_id="SRC-A4", title="Test A4"
)
binding4._save()

# Attacker: set a fake registration_transition_hash that doesn't exist in ledger
with open(tmpdir4 / "source_registry.json") as f:
    data4 = json.load(f)
for src in data4["sources"]:
    if src["source_id"] == "SRC-A4":
        fake_hash = "f" * 64
        src["_verification_envelope"]["registration_transition_hash"] = fake_hash
        src["_verified_evidence_authorization"]["registration_transition_hash"] = fake_hash
        # Recompute verification_hash
        auth = src["_verified_evidence_authorization"]
        env = _compute_verification_envelope(
            auth,
            src["_verification_envelope"]["commit_anchor"],
            src["_verification_envelope"]["ledger_root_anchor"],
        )
        src["_verification_envelope"]["verification_hash"] = env.verification_hash
with open(tmpdir4 / "source_registry.json", "w") as f:
    json.dump(data4, f)

# Reload — transition not in ledger should BLOCK
try:
    binding4r = EvidenceBinding(tmpdir4)
    src4r = binding4r.sources.get("SRC-A4")
    check("fake registration_transition_hash detected (BLOCK)", src4r is None)
except (ValueError, Exception):
    check("fake registration_transition_hash detected (BLOCK)", True)

# ===========================================================================
# Attack 5: commit_anchor doesn't exist → BLOCK
# ===========================================================================
print("\n--- Attack 5: registration commit doesn't exist → BLOCK ---")
tmpdir5 = Path(tempfile.mkdtemp(prefix="v30_13_a5_"))
binding5 = EvidenceBinding(tmpdir5)
ve5 = deduplicate_records(
    [{"doi": "10.1/a5", "title": "Test A5", "abstract": "Content A5"}], "Crossref"
)[0].as_verified_evidence()
binding5.register_source_from_verified_evidence(
    ve5, source_id="SRC-A5", title="Test A5"
)
binding5._save()

# Attacker: set a fake commit_anchor that doesn't exist
with open(tmpdir5 / "source_registry.json") as f:
    data5 = json.load(f)
for src in data5["sources"]:
    if src["source_id"] == "SRC-A5":
        fake_commit = "a" * 40
        src["_verification_envelope"]["commit_anchor"] = fake_commit
        auth = src["_verified_evidence_authorization"]
        env = _compute_verification_envelope(
            auth, fake_commit, src["_verification_envelope"]["ledger_root_anchor"]
        )
        src["_verification_envelope"]["verification_hash"] = env.verification_hash
with open(tmpdir5 / "source_registry.json", "w") as f:
    json.dump(data5, f)

# Reload — commit doesn't exist should BLOCK
try:
    binding5r = EvidenceBinding(tmpdir5)
    src5r = binding5r.sources.get("SRC-A5")
    check("non-existent commit_anchor detected (BLOCK)", src5r is None)
except (ValueError, Exception):
    check("non-existent commit_anchor detected (BLOCK)", True)

# ===========================================================================
# Attack 6 (positive): ledger_root_anchor is metadata, not verification target
# ===========================================================================
print("\n--- Attack 6 (positive): ledger_root_anchor is metadata ---")
# Changing ledger_root_anchor + recomputing hash should NOT block because
# ledger_root_anchor is now historical metadata, not compared to current.
tmpdir6 = Path(tempfile.mkdtemp(prefix="v30_13_a6_"))
binding6 = EvidenceBinding(tmpdir6)
ve6 = deduplicate_records(
    [{"doi": "10.1/a6", "title": "Test A6", "abstract": "Content A6"}], "Crossref"
)[0].as_verified_evidence()
binding6.register_source_from_verified_evidence(
    ve6, source_id="SRC-A6", title="Test A6"
)
binding6._save()

# Change ledger_root_anchor + recompute hash
with open(tmpdir6 / "source_registry.json") as f:
    data6 = json.load(f)
for src in data6["sources"]:
    if src["source_id"] == "SRC-A6":
        # Change ledger_root_anchor to a different (but still valid) value
        old_root = src["_verification_envelope"]["ledger_root_anchor"]
        new_root = hashlib.sha256(b"different_ledger_root").hexdigest()
        src["_verification_envelope"]["ledger_root_anchor"] = new_root
        # Recompute hash
        auth = src["_verified_evidence_authorization"]
        env = _compute_verification_envelope(
            auth,
            src["_verification_envelope"]["commit_anchor"],
            new_root,
        )
        src["_verification_envelope"]["verification_hash"] = env.verification_hash
with open(tmpdir6 / "source_registry.json", "w") as f:
    json.dump(data6, f)

# Reload — should NOT block because ledger_root_anchor is metadata
try:
    binding6r = EvidenceBinding(tmpdir6)
    src6r = binding6r.sources.get("SRC-A6")
    # v30.13: ledger_root_anchor is metadata, so changing it + recomputing
    # the hash is allowed (it doesn't affect the immutable anchors).
    # The evidence remains valid because commit_anchor + registration_transition_hash
    # are intact.
    check("ledger_root_anchor change does NOT block (metadata, not verification target)",
          isinstance(src6r, ExternalSource),
          f"(got {type(src6r).__name__ if src6r else 'None'})")
except (ValueError, Exception) as e:
    # If it blocked, that's a regression — v30.13 should NOT block on ledger_root_anchor
    check("ledger_root_anchor change does NOT block (metadata)", False,
          f"(blocked with: {e})")

# ===========================================================================
# Attack 7: Restart invariance — same evidence, same authorization
# ===========================================================================
print("\n--- Attack 7: Restart invariance ---")
tmpdir7 = Path(tempfile.mkdtemp(prefix="v30_13_a7_"))
binding7 = EvidenceBinding(tmpdir7)
ve7 = deduplicate_records(
    [{"doi": "10.1/a7", "title": "Test A7", "abstract": "Content A7"}], "Crossref"
)[0].as_verified_evidence()
src7 = binding7.register_source_from_verified_evidence(
    ve7, source_id="SRC-A7", title="Test A7", content="Content A7"
)
binding7._save()

binding7r = EvidenceBinding(tmpdir7)
src7r = binding7r.sources.get("SRC-A7")
check("restart: same source_id", src7.source_id == src7r.source_id)
check("restart: same identifier", src7.identifier == src7r.identifier)
check("restart: same source_class", src7.source_class == src7r.source_class)
check("restart: same commit_anchor", src7._verification_envelope.commit_anchor == src7r._verification_envelope.commit_anchor)
check("restart: same verification_hash", src7._verification_envelope.verification_hash == src7r._verification_envelope.verification_hash)
check("restart: is ExternalSource", isinstance(src7r, ExternalSource))
check("restart: is_dossier_grade", src7r.is_dossier_grade())

# ===========================================================================
# Summary
# ===========================================================================
print("\n" + "=" * 78)
print(f"CORRECTED ANCHOR SEMANTICS SUMMARY: {PASS} defended / {FAIL} breached")
print("=" * 78)
if FAIL > 0:
    print("❌ ANCHOR SEMANTICS BREACHED — fix before commit.")
    sys.exit(1)
else:
    print("✅ ALL ANCHOR SEMANTICS TESTS PASSED. v30.13 boundary holds.")
    print()
    print("PRINCIPLE:")
    print("  'A provenance anchor must prove history, not freeze the future.")
    print("   We want immutable evidence, not an immutable repository.'")
    print()
    print("v30.13 CORRECTED SEMANTICS:")
    print("  - commit_anchor: verify registration commit STILL EXISTS (not == CURRENT_HEAD)")
    print("  - registration_transition_hash: verify it EXISTS in immutable ledger")
    print("  - ledger_root_anchor: preserved as historical metadata (NOT verification target)")
    print()
    print("KEY RESULT (Attack 2):")
    print("  Evidence registered at Commit A remains VALID after repository")
    print("  advances to Commit B. Historical evidence survives legitimate")
    print("  future commits.")
    sys.exit(0)
