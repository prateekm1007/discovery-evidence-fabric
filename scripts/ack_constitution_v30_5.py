#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.5 typed-identity session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.5-typed-identity-hardening",
    intended_change=(
        "Fix two identity-model defects from v30.4: (1) normalize_patent_number "
        "now preserves jurisdiction + publication_number + kind_code (no country/"
        "kind stripping — matches federated_evidence.py). (2) Split overloaded "
        "CONFIRMED into typed states: DOCUMENT_ID_CONFIRMED, EVENT_ID_CONFIRMED, "
        "FAMILY_RELATION_CONFIRMED, POSSIBLE_FAMILY_MATCH, IDENTITY_INSUFFICIENT. "
        "Family relation links records but NEVER merges two distinct patent "
        "publications into one evidence object. Add family_relations field + "
        "second-pass family linking. Add 6 adversarial tests + 10-attack "
        "Article XVII attack script."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
