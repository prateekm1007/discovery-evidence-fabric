#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.9 real-loophole-closing session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.9-real-dossier-loophole-closing",
    intended_change=(
        "Close the raw-Source bypass loophole found by CEO v30.9 audit. "
        "P0-1: register_source() now rejects external Source types "
        "(PMID/DOI/PATENT/URL/BOOK/K_NUMBER/PMA_NUMBER/MDR_REPORT_KEY/"
        "RECALL_NUMBER/NCT_ID/PROJECT_NUM) unless they carry "
        "_verified_evidence_authorization (set by "
        "register_source_from_verified_evidence). P0-2: "
        "render_dossier_claim() now requires Evidence proof binding — "
        "source-only claims BLOCKED (was: if not evidence and not sources). "
        "P0-3: render_dossier_claim() now explicitly calls is_dossier_grade() "
        "+ re-verifies content_hash + span_hash + checks "
        "_verified_evidence_authorization for external sources + requires "
        "content_hash when content is present (closes known gap). "
        "P0-4: 12-attack real-loophole Article XVII script (51 sub-checks). "
        "Honest disclosure: INTERNAL_REPORT bypasses is_identity_verified() "
        "by design (legitimate internal path); defense relies on P0-2 + P0-3. "
        "Never certify the gate you wrote — attack the actual route an "
        "adversarial model would take."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
