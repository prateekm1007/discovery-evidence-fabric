#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.12 external anchor session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.12-external-anchor-authenticity",
    intended_change=(
        "Fix the v30.11 self-authentication flaw. The v30.11 envelope was "
        "a self-authenticating hash — an attacker who can edit the persisted "
        "JSON can change both the authorization fields AND the verification_hash "
        "(recomputing it). Both would agree. This is integrity checking, NOT "
        "authenticity. v30.12 adds EXTERNAL ANCHORS to the VerificationEnvelope: "
        "commit_anchor (git commit SHA at registration time) and "
        "ledger_root_anchor (ledger Merkle root at registration time). These "
        "cannot be forged by editing JSON. On reload, _verify_envelope checks "
        "3 layers: (1) internal consistency (v30.11 hash check), (2) commit_anchor "
        "matches current git commit, (3) ledger_root_anchor matches current "
        "ledger root. Also added defense layer 4: Source identifier must match "
        "auth dict canonical_id (catches full recompute attack). Also fixed "
        "CI/local gate parity: CI workflow updated from '13 gates' to '14 gates' "
        "to match local certification (G14 = constitution check). 9-attack "
        "external anchor Article XVII script (18 sub-checks). A hash proves "
        "consistency. An external anchor proves authenticity."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
