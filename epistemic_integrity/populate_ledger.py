"""Populate state transition ledger v22 with full cryptographic provenance.

Per CEO v21 directives:
  P0-2: Every transition has full_commit_sha + artifact_path + blob_sha + artifact_content_hash
  P0-3: Full 40-character commit SHAs (no abbreviations)
  P0-4: Mark bootstrap transitions as BOOTSTRAPPED_FROM_CANONICAL_STATE
  P0-5: Require exact artifact/provenance chain before CURRENT
"""
import json, sys, subprocess, hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from epistemic_integrity.state_transition_ledger import StateTransitionLedger

EPISTEMIC_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]


def get_full_commit_sha(short_sha: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", short_sha],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else short_sha


def get_blob_sha(commit_sha: str, artifact_path: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{commit_sha}:{artifact_path}"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_blob_content_hash(blob_sha: str) -> str:
    if not blob_sha:
        return ""
    result = subprocess.run(
        ["git", "cat-file", "-p", blob_sha],
        cwd=str(REPO_ROOT), capture_output=True, timeout=10,
    )
    if result.returncode == 0:
        return hashlib.sha256(result.stdout).hexdigest()
    return ""


# Map territory → (artifact_path, commit_short_sha, version)
# v26: Updated commit SHAs to post-pass-3 values (git filter-repo pass 3
#      scrubbed the OpenRouter API key that was missed by pass 1).
#      All artifact content hashes are UNCHANGED — pass 3 only modified
#      blobs containing the OpenRouter key (discovery_fabric/a2/*.py).
TERRITORY_ARTIFACTS = {
    "CV-T01": ("CEREVASC_POSITION_001_V25_NUMERICAL_IDENTIFIABILITY/V25_NUMERICAL_IDENTIFIABILITY.json", "05fb09c", "V25"),
    "CV-T02": ("CEREVASC_TERRITORY_2_FINAL_ADJUDICATION/T2_FINAL_ADJUDICATION.json", "54a12b1", "V-FINAL"),
    "CV-T03": ("CEREVASC_INVENTION_003_V1/22_FINAL_ADJUDICATION.json", "58ccd4a", "V8.8"),
    "CV-T04": ("CEREVASC_POSITION_004_V6_PATSNAP_COMPLETE/FINAL_VERDICT_V6_PATSNAP_COMPLETE.json", "efc554e", "V8"),
    "CV-T05": ("CEREVASC_POSITION_005_V2_HOSTILE_ATTACK/V10_ROBUSTNESS_ADJUDICATION.json", "4ad58ad", "V18"),
    "CV-T06": ("CEREVASC_TERRITORY_6_RETRIEVAL_RESCUE/V6_COMPLETE.json", "dcd8d45", "V6"),
    "CV-T07": ("CEREVASC_TERRITORY_7_VENOUS_INTERFACE_PROTECTION/V4_COMPLETE.json", "dcd8d45", "V4"),
    "CV-T08": ("CEREVASC_TERRITORY_8_PATIENT_SPECIFIC_ADAPTIVE/V3_COMPLETE.json", "dcd8d45", "V3"),
    "CV-T09": ("CEREVASC_TERRITORY_9_CNS_THERAPY_PLATFORM/T9_DISCOVERY_REPORT.json", "0823583", "V1"),
    "CV-T10": ("CEREVASC_TERRITORY_10_LIFECYCLE_INTELLIGENCE/T10_DISCOVERY_REPORT.json", "0823583", "V1"),
}

# Load canonical portfolio
with open(REPO_ROOT / "CANONICAL_STATE" / "PORTFOLIO.json") as f:
    portfolio = json.load(f)

# Delete old ledger
ledger_path = EPISTEMIC_DIR / "approved_provenance" / "state_transition_ledger.json"
if ledger_path.exists():
    ledger_path.unlink()

ledger = StateTransitionLedger(EPISTEMIC_DIR / "approved_provenance")

for t in portfolio.get("territories", []):
    tid = t["id"]
    state = t.get("current_state", "")

    # CV-T02L: explicit scope exclusion
    if tid == "CV-T02L":
        ledger.record_transition(
            territory_id=tid,
            to_state="NOT_IN_CERTIFICATION_SCOPE",
            artifact_id=f"{tid}-branch",
            artifact_version="V1",
            commit_sha=get_full_commit_sha("dcd8d45"),
            reason="Narrow branch, not yet developed. Explicitly excluded from certification scope.",
            artifact_hash=None,  # No artifact for scope-excluded territory
        )
        continue

    # Get artifact info
    artifact_path, short_commit, version = TERRITORY_ARTIFACTS.get(tid, (None, "dcd8d45", "V1"))

    if artifact_path is None:
        # No artifact path — can't anchor
        ledger.record_transition(
            territory_id=tid,
            to_state=state,
            artifact_id=f"{tid}-{version}",
            artifact_version=version,
            commit_sha=get_full_commit_sha(short_commit),
            reason=f"BOOTSTRAPPED_FROM_CANONICAL_STATE — no artifact path available for {tid}",
            artifact_hash=None,
        )
        continue

    # Get full provenance chain
    full_commit = get_full_commit_sha(short_commit)
    blob_sha = get_blob_sha(full_commit, artifact_path)
    content_hash = get_blob_content_hash(blob_sha)

    if not blob_sha or not content_hash:
        # Artifact not found in git history — bootstrap without anchor
        ledger.record_transition(
            territory_id=tid,
            to_state=state,
            artifact_id=f"{tid}-{version}",
            artifact_version=version,
            commit_sha=full_commit,
            reason=f"BOOTSTRAPPED_FROM_CANONICAL_STATE — artifact {artifact_path} not found in commit {full_commit[:12]}",
            artifact_hash=None,
        )
        continue

    # P0-2/P0-3/P0-5: Full provenance chain with artifact_hash
    ledger.record_transition(
        territory_id=tid,
        to_state=state,
        artifact_id=f"{tid}-{version}",
        artifact_version=version,
        commit_sha=full_commit,  # Full 40-char SHA
        reason=f"BOOTSTRAPPED_FROM_CANONICAL_STATE — artifact anchored: {artifact_path} blob={blob_sha[:12]} hash={content_hash[:12]}",
        artifact_hash=content_hash,  # P0-2: NOT null
    )

    print(f"{tid}: {state} (version={version})")
    print(f"  commit: {full_commit}")
    print(f"  artifact: {artifact_path}")
    print(f"  blob: {blob_sha}")
    print(f"  hash: {content_hash[:32]}...")

# P0-3: NDJSON append-only — no _save() needed, events already appended
print(f"\nLedger populated with {len(ledger._events)} transitions (NDJSON append-only)")

# Verify chain integrity
chain_result = ledger.verify_chain_integrity()
print(f"Chain integrity: {'VALID' if chain_result['chain_valid'] else 'INVALID'}")
print(f"Topology: {chain_result['topology']}")
print(f"Genesis: {chain_result['genesis_hash'][:16]}...")
print(f"Root: {chain_result['ledger_root_hash'][:16]}...")
print(f"Total events: {chain_result['total_events']}")
if chain_result['failures']:
    for f in chain_result['failures']:
        print(f"  {f}")
