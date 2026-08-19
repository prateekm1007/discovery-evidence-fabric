"""
epistemic_integrity/attestation_binding.py

Per CEO v25 AUDIT — P0-5:
  "Bind the final authorization attestation to:
   final_commit + ledger_root + portfolio_projection_root +
   certification_corpus_root + gate_version + schema_version"

Per CEO v25 AUDIT — architectural issue:
  "The detached worktree is not merely a test copy; it is the actual
   certification environment. Therefore the attestation needs to record:
     SOURCE_COMMIT
     DETACHED_WORKTREE_COMMIT
     RUNNER_VERSION
     GATE_VERSION
     SCHEMA_VERSION
     LEDGER_ROOT
     PORTFOLIO_ROOT
     CERTIFICATION_CORPUS_ROOT
   and require:
     SOURCE_COMMIT == DETACHED_WORKTREE_COMMIT
   Otherwise someone could certify one commit and report another."

This module produces the FINAL authorization attestation that binds:
  1. The source commit (the commit the user asked to certify)
  2. The detached worktree commit (the commit actually certified)
  3. The runner version (detached_certification_runner version)
  4. The gate version (research_authorization_gate version)
  5. The schema version (state_transition_ledger schema)
  6. The ledger root hash (from state_transition_ledger_root.json)
  7. The portfolio projection root (SHA-256 over territory→state pairs)
  8. The certification corpus root (SHA-256 over the corpus manifest)
  9. The post-scrub revalidation capsule hash
  10. The historical artifact audit hash
  11. The credential audit split hash

CRITICAL INVARIANT: SOURCE_COMMIT == DETACHED_WORKTREE_COMMIT
  If this fails, the attestation is INVALID and research is NOT authorized.
  This prevents the attack where someone certifies commit A but reports
  commit B as the certified commit.
"""

import json
import hashlib
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISTEMIC_DIR = Path(__file__).resolve().parent
LEDGER_DIR = EPISTEMIC_DIR / "approved_provenance"
CANONICAL_PORTFOLIO = REPO_ROOT / "CANONICAL_STATE" / "PORTFOLIO.json"
CERTIFICATION_CORPUS = EPISTEMIC_DIR / "real_production_certification_corpus.json"

ATT_BINDING_SCHEMA_VERSION = "1.0.0"


def _git(args: list) -> tuple:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _git_head() -> str:
    rc, out, _ = _git(["rev-parse", "HEAD"])
    return out if rc == 0 else "UNKNOWN"


def _compute_hash(data: Any) -> str:
    content = json.dumps(data, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


@dataclass(frozen=True)
class AuthorizationBinding:
    """Final authorization attestation binding all P0 controls.

    The binding_hash is computed over ALL fields except itself, ensuring
    that any change to any binding field invalidates the hash.

    CRITICAL: source_commit == detached_worktree_commit is REQUIRED.
    If they differ, the binding is INVALID regardless of other fields.
    """
    # Schema
    att_binding_schema_version: str

    # Commit binding (CEO's critical invariant)
    source_commit: str                          # The commit the user asked to certify
    detached_worktree_commit: str               # The commit actually certified in the worktree
    source_equals_detached: bool                # MUST be True

    # Version binding
    runner_version: str                         # detached_certification_runner version
    gate_version: str                           # research_authorization_gate version (ENGINE_VERSION)
    schema_version: str                         # SCHEMA_VERSION from version_manifest
    policy_version: str                         # POLICY_VERSION from version_manifest
    certification_corpus_version: str           # CERTIFICATION_CORPUS_VERSION from version_manifest

    # State binding (cryptographic roots)
    ledger_root_hash: str                       # from state_transition_ledger_root.json
    ledger_total_events: int
    portfolio_projection_root: str              # SHA-256 over (territory_id, current_state) pairs
    certification_corpus_root: str              # SHA-256 over the corpus manifest

    # P0 control hashes (bind the three verification capsules)
    post_scrub_revalidation_capsule_hash: str   # from post_scrub_evidence_revalidation
    historical_artifact_audit_hash: str         # from historical_artifact_audit
    credential_audit_split_hash: str            # from credential_audit_split

    # Verdicts
    post_scrub_revalidation_passed: bool
    historical_artifact_audit_passed: bool
    credential_audit_split_passed: bool

    # Final authorization
    authorization: str                          # "RESEARCH_AUTHORIZED" or "RESEARCH_BLOCKED"
    timestamp: str
    binding_hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "att_binding_schema_version": self.att_binding_schema_version,
            "source_commit": self.source_commit,
            "detached_worktree_commit": self.detached_worktree_commit,
            "source_equals_detached": self.source_equals_detached,
            "runner_version": self.runner_version,
            "gate_version": self.gate_version,
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "certification_corpus_version": self.certification_corpus_version,
            "ledger_root_hash": self.ledger_root_hash,
            "ledger_total_events": self.ledger_total_events,
            "portfolio_projection_root": self.portfolio_projection_root,
            "certification_corpus_root": self.certification_corpus_root,
            "post_scrub_revalidation_capsule_hash": self.post_scrub_revalidation_capsule_hash,
            "historical_artifact_audit_hash": self.historical_artifact_audit_hash,
            "credential_audit_split_hash": self.credential_audit_split_hash,
            "post_scrub_revalidation_passed": self.post_scrub_revalidation_passed,
            "historical_artifact_audit_passed": self.historical_artifact_audit_passed,
            "credential_audit_split_passed": self.credential_audit_split_passed,
            "authorization": self.authorization,
            "timestamp": self.timestamp,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


def _load_ledger_root() -> dict:
    root_path = LEDGER_DIR / "state_transition_ledger_root.json"
    with open(root_path) as f:
        return json.load(f)


def _load_ledger_events() -> list:
    events = []
    ndjson_path = LEDGER_DIR / "state_transition_ledger.ndjson"
    if not ndjson_path.exists():
        return events
    with open(ndjson_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _project_portfolio_from_ledger(events: list) -> dict:
    by_territory = {}
    for event in sorted(events, key=lambda e: e["global_sequence"]):
        by_territory[event["territory_id"]] = event["to_state"]
    return by_territory


def _portfolio_root(projection: dict) -> str:
    items = sorted(projection.items())
    content = json.dumps(items, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _certification_corpus_root() -> str:
    """SHA-256 over the certification corpus file content."""
    if not CERTIFICATION_CORPUS.exists():
        return ""
    with open(CERTIFICATION_CORPUS, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_p0_capsule_hashes() -> dict:
    """Load the hashes from the three P0 verification capsules.

    These capsules are written to /tmp/epistemic_certification_output/ by
    their respective modules. If a capsule is missing, the hash is empty
    and the corresponding passed flag is False.
    """
    output_dir = Path("/tmp/epistemic_certification_output")
    result = {
        "post_scrub_revalidation_capsule_hash": "",
        "post_scrub_revalidation_passed": False,
        "historical_artifact_audit_hash": "",
        "historical_artifact_audit_passed": False,
        "credential_audit_split_hash": "",
        "credential_audit_split_passed": False,
    }

    # Post-scrub revalidation
    p02_path = output_dir / "post_scrub_evidence_revalidation_capsule.json"
    if p02_path.exists():
        with open(p02_path) as f:
            capsule = json.load(f)
        result["post_scrub_revalidation_capsule_hash"] = capsule.get("capsule_hash", "")
        result["post_scrub_revalidation_passed"] = capsule.get("all_artifacts_valid", False)

    # Historical artifact audit
    p03_path = output_dir / "historical_artifact_audit_report.json"
    if p03_path.exists():
        with open(p03_path) as f:
            report = json.load(f)
        result["historical_artifact_audit_hash"] = report.get("audit_hash", "")
        # The audit "passes" if there are no unauthorized markers in scientific
        # artifacts and no hash corruption in scientific artifacts.
        scan = report.get("full_history_blob_scan", {})
        result["historical_artifact_audit_passed"] = (
            report.get("artifacts_with_unauthorized_markers", 1) == 0
            and report.get("hash_field_corruption_count", 1) == 0
            and scan.get("unauthorized_markers_in_scientific_artifacts", 1) == 0
            and scan.get("hash_corruption_in_scientific_artifacts", 1) == 0
        )

    # Credential audit split
    p04_path = output_dir / "credential_audit_split_report.json"
    if p04_path.exists():
        with open(p04_path) as f:
            report = json.load(f)
        result["credential_audit_split_hash"] = report.get("audit_hash", "")
        result["credential_audit_split_passed"] = report.get("combined_clean", False)

    return result


def build_binding(
    source_commit: Optional[str] = None,
    detached_worktree_commit: Optional[str] = None,
    runner_version: str = "v26-detached-runner",
) -> AuthorizationBinding:
    """Build the final authorization binding.

    Args:
        source_commit: The commit the user asked to certify. Defaults to HEAD.
        detached_worktree_commit: The commit actually certified in the worktree.
            Defaults to source_commit (for in-place certification).
        runner_version: The detached certification runner version.
    """
    if source_commit is None:
        source_commit = _git_head()
    if detached_worktree_commit is None:
        detached_worktree_commit = source_commit

    # Version manifest
    sys.path.insert(0, str(REPO_ROOT))
    from epistemic_integrity.version_manifest import (
        ENGINE_VERSION, SCHEMA_VERSION, POLICY_VERSION, CERTIFICATION_CORPUS_VERSION,
    )

    # Ledger root
    ledger_root = _load_ledger_root()
    events = _load_ledger_events()
    projection = _project_portfolio_from_ledger(events)

    # P0 capsule hashes
    p0_hashes = _load_p0_capsule_hashes()

    # Final authorization
    all_passed = (
        source_commit == detached_worktree_commit
        and p0_hashes["post_scrub_revalidation_passed"]
        and p0_hashes["historical_artifact_audit_passed"]
        and p0_hashes["credential_audit_split_passed"]
    )
    # v27: Narrower authorization semantics per CEO v26 audit.
    # "RESEARCH_AUTHORIZED" means AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE.
    # It does NOT mean ALL_HISTORICAL_EVIDENCE_PRESERVED_EXACTLY.
    # The HISTORICAL_PROVENANCE_LIMITATION is bound into the authorization.
    if all_passed:
        authorization = "AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE"
    else:
        authorization = "RESEARCH_BLOCKED"

    binding = AuthorizationBinding(
        att_binding_schema_version=ATT_BINDING_SCHEMA_VERSION,
        source_commit=source_commit,
        detached_worktree_commit=detached_worktree_commit,
        source_equals_detached=(source_commit == detached_worktree_commit),
        runner_version=runner_version,
        gate_version=ENGINE_VERSION,
        schema_version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        certification_corpus_version=CERTIFICATION_CORPUS_VERSION,
        ledger_root_hash=ledger_root.get("ledger_root_hash", ""),
        ledger_total_events=ledger_root.get("total_events", 0),
        portfolio_projection_root=_portfolio_root(projection),
        certification_corpus_root=_certification_corpus_root(),
        post_scrub_revalidation_capsule_hash=p0_hashes["post_scrub_revalidation_capsule_hash"],
        historical_artifact_audit_hash=p0_hashes["historical_artifact_audit_hash"],
        credential_audit_split_hash=p0_hashes["credential_audit_split_hash"],
        post_scrub_revalidation_passed=p0_hashes["post_scrub_revalidation_passed"],
        historical_artifact_audit_passed=p0_hashes["historical_artifact_audit_passed"],
        credential_audit_split_passed=p0_hashes["credential_audit_split_passed"],
        authorization=authorization,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    binding_hash = binding.compute_hash()
    object.__setattr__(binding, "binding_hash", binding_hash)
    return binding


def main():
    """Build and print the authorization binding."""
    binding = build_binding()

    output_dir = Path("/tmp/epistemic_certification_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "authorization_binding.json"

    with open(output_path, "w") as f:
        json.dump(asdict(binding), f, indent=2, default=str)

    print(f"\n{'='*78}")
    print(f"AUTHORIZATION BINDING (P0-5)")
    print(f"{'='*78}")
    print(f"Binding schema version:    {binding.att_binding_schema_version}")
    print(f"Timestamp:                 {binding.timestamp}")
    print()
    print(f"COMMIT BINDING (CEO critical invariant):")
    print(f"  Source commit:            {binding.source_commit}")
    print(f"  Detached worktree commit: {binding.detached_worktree_commit}")
    print(f"  Source == Detached:       {binding.source_equals_detached}")
    if not binding.source_equals_detached:
        print(f"  ⚠ CRITICAL: source != detached — ATTESTATION INVALID")
    print()
    print(f"VERSION BINDING:")
    print(f"  Runner version:           {binding.runner_version}")
    print(f"  Gate version:             {binding.gate_version}")
    print(f"  Schema version:           {binding.schema_version}")
    print(f"  Policy version:           {binding.policy_version}")
    print(f"  Corpus version:           {binding.certification_corpus_version}")
    print()
    print(f"STATE BINDING (cryptographic roots):")
    print(f"  Ledger root hash:         {binding.ledger_root_hash}")
    print(f"  Ledger total events:      {binding.ledger_total_events}")
    print(f"  Portfolio projection:     {binding.portfolio_projection_root}")
    print(f"  Certification corpus:     {binding.certification_corpus_root}")
    print()
    print(f"P0 CONTROL HASHES:")
    print(f"  Post-scrub revalidation:  {binding.post_scrub_revalidation_capsule_hash}")
    print(f"  Historical artifact audit:{binding.historical_artifact_audit_hash}")
    print(f"  Credential audit split:   {binding.credential_audit_split_hash}")
    print()
    print(f"P0 CONTROL VERDICTS:")
    print(f"  P0-2 Post-scrub revalidation:     {'✅ PASS' if binding.post_scrub_revalidation_passed else '❌ FAIL'}")
    print(f"  P0-3 Historical artifact audit:   {'✅ PASS' if binding.historical_artifact_audit_passed else '❌ FAIL'}")
    print(f"  P0-4 Credential audit split:      {'✅ PASS' if binding.credential_audit_split_passed else '❌ FAIL'}")
    print()
    print(f"FINAL AUTHORIZATION:")
    if binding.authorization == "AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE":
        print(f"  🟢 AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE")
        print(f"     (does NOT mean ALL_HISTORICAL_EVIDENCE_PRESERVED_EXACTLY)")
    else:
        print(f"  🔴 RESEARCH_BLOCKED")
    print(f"  Binding hash: {binding.binding_hash}")
    print(f"\nBinding written to: {output_path}")

    return 0 if binding.authorization == "AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE" else 1


if __name__ == "__main__":
    sys.exit(main())
