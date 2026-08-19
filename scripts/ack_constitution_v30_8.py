#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.8 production-boundary session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.8-production-evidence-boundary",
    intended_change=(
        "Wire VerifiedEvidence into the REAL production dossier path. Add "
        "EvidenceBinding.register_source_from_verified_evidence() — the "
        "production entry point for discovery-layer sources. Accepts ONLY "
        "VerifiedEvidence; TypeError on raw EvidenceIdentity. 5 defense "
        "layers: VerifiedEvidence.__post_init__, verify_integrity(), "
        "register_source type-check, register_source can_use_as_verified_evidence "
        "re-check, register_source verify_integrity() re-check. Add "
        "verify_integrity() method on EvidenceIdentity that cross-checks "
        "identity_confidence vs content_mismatch_audits — DETECTS "
        "object.__setattr__ forge (closes v30.7 known limitation). Add "
        "evidence_identity_adapter.py bridge module. Fix test_secret_scanning "
        "to scan only git-tracked files (CREDENTIALS_AND_MODELS.md is "
        "gitignored). Add 12-attack production-path Article XVII script "
        "(39 sub-checks). Honest classification: strongly defended, not "
        "mathematically unforgeable inside Python (runtime trust-boundary "
        "limitation). A proof-of-concept defense is not a production defense."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
