#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.6 content-integrity session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.6-content-integrity-hardening",
    intended_change=(
        "Close the CONTENT_MISMATCH gap disclosed as a known limitation in "
        "v30.5. Add DOCUMENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH and "
        "EVENT_ID_CONFIRMED_WITH_CONTENT_MISMATCH states. When two records "
        "share an authoritative ID but produce different content fingerprints, "
        "the merged record preserves identity (can_merge=True) but is BLOCKED "
        "from semantic evidence use (can_use_as_verified_evidence=False). "
        "All observed fingerprints retained in observed_content_fingerprints. "
        "ContentMismatchAudit records emitted per divergence. Add 7 CM tests "
        "in main() + 12-attack Article XVII script (46 sub-checks). Never "
        "collapse identity integrity and content integrity into one bit."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
