"""
epistemic_integrity/post_scrub_certification_capsule.py

Per CEO v26 AUDIT — directive 3:
  "Produce a deterministic post-scrub certification capsule containing:
   final_commit + ledger_root + portfolio_root + corpus_root +
   all 13 gate results + verifier/schema versions."

This is the SINGLE CANONICAL capsule that binds the entire certification.
It is DETERMINISTIC: same inputs → same capsule_hash.

The capsule is produced by running the gate and capturing the attestation,
then augmenting it with the P0 control capsule hashes.

Two certifiers running this module on the same commit must produce
identical capsule_hash values. Any divergence indicates either:
  - different ledger state
  - different git state
  - different code
  - different P0 control results

EPISTEMIC INTEGRITY NOTE:
  This capsule establishes AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE.
  It does NOT establish ALL_HISTORICAL_EVIDENCE_PRESERVED_EXACTLY.
  The HISTORICAL_PROVENANCE_LIMITATION is bound into the capsule hash.
"""

import json
import hashlib
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISTEMIC_DIR = Path(__file__).resolve().parent
LEDGER_DIR = EPISTEMIC_DIR / "approved_provenance"
CANONICAL_PORTFOLIO = REPO_ROOT / "CANONICAL_STATE" / "PORTFOLIO.json"
CERTIFICATION_CORPUS = EPISTEMIC_DIR / "real_production_certification_corpus.json"
HISTORICAL_LIMITATION = LEDGER_DIR / "HISTORICAL_PROVENANCE_LIMITATION.json"

CAPSULE_SCHEMA_VERSION = "2.0.0"


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


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _portfolio_root() -> str:
    """SHA-256 over canonical portfolio's (territory_id, current_state) pairs."""
    portfolio = _load_json(CANONICAL_PORTFOLIO)
    pairs = []
    for t in portfolio.get("territories", []):
        pairs.append((t["id"], t.get("current_state", "")))
    pairs.sort()
    content = json.dumps(pairs, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _ledger_projection_root() -> str:
    """SHA-256 over ledger's projected (territory_id, current_state) pairs."""
    events = []
    ndjson_path = LEDGER_DIR / "state_transition_ledger.ndjson"
    if ndjson_path.exists():
        with open(ndjson_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
    by_territory = {}
    for event in sorted(events, key=lambda e: e["global_sequence"]):
        by_territory[event["territory_id"]] = event["to_state"]
    pairs = sorted(by_territory.items())
    content = json.dumps(pairs, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _certification_corpus_root() -> str:
    """SHA-256 over the certification corpus file content."""
    if not CERTIFICATION_CORPUS.exists():
        return ""
    with open(CERTIFICATION_CORPUS, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _historical_limitation_root() -> str:
    """SHA-256 over the HISTORICAL_PROVENANCE_LIMITATION file content.

    This binds the limitation into the capsule hash, ensuring that any change
    to the limitation (e.g., removing it to falsely claim historical equivalence)
    would change the capsule hash.
    """
    if not HISTORICAL_LIMITATION.exists():
        return ""
    with open(HISTORICAL_LIMITATION, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@dataclass(frozen=True)
class PostScrubCertificationCapsule:
    """Single deterministic capsule binding the entire certification.

    The capsule_hash is computed over ALL fields except itself.
    Two certifiers running on the same commit must produce identical hashes.
    """
    # Schema
    capsule_schema_version: str

    # Commit binding
    certified_commit: str
    generated_at: str

    # Version binding
    gate_version: str
    schema_version: str
    policy_version: str
    certification_corpus_version: str

    # State binding (cryptographic roots)
    ledger_root_hash: str
    ledger_total_events: int
    portfolio_canonical_root: str
    portfolio_ledger_projection_root: str
    certification_corpus_root: str

    # Historical provenance limitation binding (v27)
    historical_provenance_limitation_root: str
    historical_provenance_limitation_active: bool

    # All 13 gate results
    gate_results: List[Dict[str, Any]]

    # P0 control capsule hashes (bind the three verification capsules)
    post_scrub_revalidation_capsule_hash: str
    historical_artifact_audit_hash: str
    credential_audit_split_hash: str

    # Final authorization (narrower semantics per CEO v26)
    authorization: str  # AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE
    authorization_does_NOT_mean: str  # ALL_HISTORICAL_EVIDENCE_PRESERVED_EXACTLY

    # Overall
    all_gates_green: bool
    capsule_hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "capsule_schema_version": self.capsule_schema_version,
            "certified_commit": self.certified_commit,
            "gate_version": self.gate_version,
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "certification_corpus_version": self.certification_corpus_version,
            "ledger_root_hash": self.ledger_root_hash,
            "ledger_total_events": self.ledger_total_events,
            "portfolio_canonical_root": self.portfolio_canonical_root,
            "portfolio_ledger_projection_root": self.portfolio_ledger_projection_root,
            "certification_corpus_root": self.certification_corpus_root,
            "historical_provenance_limitation_root": self.historical_provenance_limitation_root,
            "historical_provenance_limitation_active": self.historical_provenance_limitation_active,
            "gate_results": self.gate_results,
            "post_scrub_revalidation_capsule_hash": self.post_scrub_revalidation_capsule_hash,
            "historical_artifact_audit_hash": self.historical_artifact_audit_hash,
            "credential_audit_split_hash": self.credential_audit_split_hash,
            "authorization": self.authorization,
            "authorization_does_NOT_mean": self.authorization_does_NOT_mean,
            "all_gates_green": self.all_gates_green,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


def build_capsule(certified_commit: Optional[str] = None) -> PostScrubCertificationCapsule:
    """Build the deterministic post-scrub certification capsule.

    This function runs the gate (in-process, NOT subprocess) and captures
    all 13 gate results, then binds them with the state roots and P0 control
    hashes into a single deterministic capsule.

    Args:
        certified_commit: The commit being certified. Defaults to HEAD.
    """
    if certified_commit is None:
        certified_commit = _git_head()

    # Version manifest
    sys.path.insert(0, str(REPO_ROOT))
    from epistemic_integrity.version_manifest import (
        ENGINE_VERSION, SCHEMA_VERSION, POLICY_VERSION, CERTIFICATION_CORPUS_VERSION,
    )

    # Run the gate to get all 13 gate results
    from epistemic_integrity.research_authorization_gate import ResearchAuthorizationGate
    gate = ResearchAuthorizationGate()
    attestation = gate.check_all()

    # Extract gate results (list of dicts with check_id, check_name, passed, details)
    gate_results = []
    for check in attestation.checks:
        gate_results.append({
            "check_id": check.get("check_id", ""),
            "check_name": check.get("check_name", ""),
            "passed": check.get("passed", False),
            "details": check.get("details", ""),
        })

    all_gates_green = (
        len(attestation.blocking_reasons) == 0
        and all(g["passed"] for g in gate_results)
    )

    # Load state roots
    ledger_root = _load_json(LEDGER_DIR / "state_transition_ledger_root.json")

    # Load P0 control capsule hashes
    output_dir = Path("/tmp/epistemic_certification_output")
    p02 = _load_json(output_dir / "post_scrub_evidence_revalidation_capsule.json")
    p03 = _load_json(output_dir / "historical_artifact_audit_report.json")
    p04 = _load_json(output_dir / "credential_audit_split_report.json")

    # Load historical limitation
    limitation = _load_json(HISTORICAL_LIMITATION)
    limitation_active = limitation.get("status") == "ACTIVE"

    # Authorization (narrower semantics per CEO v26)
    if all_gates_green:
        authorization = "AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE"
    else:
        authorization = "RESEARCH_BLOCKED"

    capsule = PostScrubCertificationCapsule(
        capsule_schema_version=CAPSULE_SCHEMA_VERSION,
        certified_commit=certified_commit,
        generated_at=datetime.now(timezone.utc).isoformat(),
        gate_version=ENGINE_VERSION,
        schema_version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        certification_corpus_version=CERTIFICATION_CORPUS_VERSION,
        ledger_root_hash=ledger_root.get("ledger_root_hash", ""),
        ledger_total_events=ledger_root.get("total_events", 0),
        portfolio_canonical_root=_portfolio_root(),
        portfolio_ledger_projection_root=_ledger_projection_root(),
        certification_corpus_root=_certification_corpus_root(),
        historical_provenance_limitation_root=_historical_limitation_root(),
        historical_provenance_limitation_active=limitation_active,
        gate_results=gate_results,
        post_scrub_revalidation_capsule_hash=p02.get("capsule_hash", ""),
        historical_artifact_audit_hash=p03.get("audit_hash", ""),
        credential_audit_split_hash=p04.get("audit_hash", ""),
        authorization=authorization,
        authorization_does_NOT_mean="ALL_HISTORICAL_EVIDENCE_PRESERVED_EXACTLY",
        all_gates_green=all_gates_green,
    )
    capsule_hash = capsule.compute_hash()
    object.__setattr__(capsule, "capsule_hash", capsule_hash)
    return capsule


def main():
    """Build and print the certification capsule."""
    capsule = build_capsule()

    output_dir = Path("/tmp/epistemic_certification_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "post_scrub_certification_capsule.json"

    with open(output_path, "w") as f:
        json.dump(asdict(capsule), f, indent=2, default=str)

    print(f"\n{'='*78}")
    print(f"POST-SCRUB CERTIFICATION CAPSULE (v27 — deterministic)")
    print(f"{'='*78}")
    print(f"Certified commit:           {capsule.certified_commit}")
    print(f"Capsule schema version:     {capsule.capsule_schema_version}")
    print(f"Generated at:               {capsule.generated_at}")
    print(f"Gate version:               {capsule.gate_version}")
    print(f"Schema version:             {capsule.schema_version}")
    print(f"Policy version:             {capsule.policy_version}")
    print(f"Corpus version:             {capsule.certification_corpus_version}")
    print()
    print(f"STATE BINDING (cryptographic roots):")
    print(f"  Ledger root hash:              {capsule.ledger_root_hash}")
    print(f"  Ledger total events:           {capsule.ledger_total_events}")
    print(f"  Portfolio canonical root:      {capsule.portfolio_canonical_root}")
    print(f"  Portfolio ledger projection:   {capsule.portfolio_ledger_projection_root}")
    print(f"  Certification corpus root:     {capsule.certification_corpus_root}")
    print()
    print(f"HISTORICAL PROVENANCE LIMITATION:")
    print(f"  Limitation root:               {capsule.historical_provenance_limitation_root}")
    print(f"  Limitation active:             {capsule.historical_provenance_limitation_active}")
    print()
    print(f"ALL 13 GATE RESULTS:")
    for g in capsule.gate_results:
        marker = "✅" if g["passed"] else "❌"
        print(f"  {marker} {g['check_id']:5s} {g['check_name']:40s} {g['details'][:60]}")
    print()
    print(f"P0 CONTROL CAPSULE HASHES:")
    print(f"  Post-scrub revalidation:       {capsule.post_scrub_revalidation_capsule_hash}")
    print(f"  Historical artifact audit:     {capsule.historical_artifact_audit_hash}")
    print(f"  Credential audit split:        {capsule.credential_audit_split_hash}")
    print()
    print(f"FINAL AUTHORIZATION:")
    if capsule.all_gates_green:
        print(f"  🟢 {capsule.authorization}")
    else:
        print(f"  🔴 {capsule.authorization}")
    print(f"  Does NOT mean: {capsule.authorization_does_NOT_mean}")
    print()
    print(f"Capsule hash: {capsule.capsule_hash}")
    print(f"\nCapsule written to: {output_path}")

    return 0 if capsule.all_gates_green else 1


if __name__ == "__main__":
    sys.exit(main())
