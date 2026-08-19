#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.11 persistence/restart session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.11-persistence-restart-boundary",
    intended_change=(
        "Close the persistence/restart gap. v30.10 type hierarchy exists "
        "in RAM but _save() strips private fields and _load() reconstructs "
        "base Source — the type boundary disappears after restart. v30.11 "
        "fixes: (1) source_class discriminator field persisted explicitly; "
        "_load() reconstructs InternalSource/ExternalSource based on "
        "source_class, not inferred from source_type. (2) VerificationEnvelope "
        "dataclass with evidence_identity_hash, content_hash, "
        "source_databases_hash, verification_hash, authorization_version. "
        "Cryptographically binds _verified_evidence_authorization fields. "
        "On reload, verification_hash is recomputed and compared — tamper "
        "detection. (3) _save() no longer strips private fields — "
        "authorization provenance survives serialization. (4) 8-attack "
        "round-trip Article XVII script (37 sub-checks): ExternalSource "
        "round-trip, InternalSource round-trip, forged auth dict tamper "
        "detection, raw Source JSON rejection, source_class tamper "
        "detection, verification_hash tamper detection, restart invariance. "
        "(5) Article XXII added to Constitution: never confuse your viewport "
        "with reality — must verify remote state before declaring historical "
        "loss. An epistemic invariant must survive serialization, restart, "
        "migration, and hostile mutation."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
