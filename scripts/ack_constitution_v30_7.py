#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.7 type-safe boundary session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.7-type-safe-evidence-boundary",
    intended_change=(
        "Harden the API boundary between identity aggregation and evidence "
        "authorization. Add VerifiedEvidence type that wraps EvidenceIdentity "
        "but can ONLY be constructed from records where "
        "can_use_as_verified_evidence=True. Constructor raises "
        "EvidenceAuthorizationError for CONTENT_MISMATCH / "
        "POSSIBLE_FAMILY_MATCH / FAMILY_RELATION_CONFIRMED / "
        "IDENTITY_INSUFFICIENT. Add DossierClaimConsumer proof-of-concept "
        "that type-hints VerifiedEvidence (not EvidenceIdentity). Add "
        "as_verified_evidence() factory method. Add 10 TB tests in main() + "
        "12-attack Article XVII script (47 sub-checks). Defense-in-depth "
        "catches __new__/subclass/copy/pickle bypass attempts. Make the "
        "unsafe path structurally difficult or impossible."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
