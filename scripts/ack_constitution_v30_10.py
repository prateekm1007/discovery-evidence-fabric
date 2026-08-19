#!/usr/bin/env python3
"""Acknowledge the constitution for the v30.10 type-safe source hierarchy session."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')

from epistemic_integrity.constitution_loader import acknowledge_constitution

ack = acknowledge_constitution(
    agent="main",
    session="v30.10-type-safe-source-hierarchy",
    intended_change=(
        "Replace source_type string-label boundary with TYPE-SAFE source "
        "hierarchy. Add InternalSource(Source) subclass — constructor "
        "refuses external content patterns (DOI/PMID/patent/K-number/PMA/"
        "MDR/NCT/URLs). Add ExternalSource(Source) subclass — constructor "
        "requires _verified_evidence_authorization as a REAL field (not "
        "setattr). register_source() accepts ONLY InternalSource (TypeError "
        "on raw Source or ExternalSource). register_source_from_verified_"
        "evidence() returns ExternalSource. DossierFirewall render path "
        "type-checks InternalSource/ExternalSource instances (not source_type "
        "string). Defense-in-depth: register_source re-runs masquerade check "
        "even for InternalSource subclasses that override __post_init__. "
        "15-attack masquerade Article XVII script (26 sub-checks). A security "
        "boundary should be enforced by object construction, not by trusting "
        "a label inside the object."
    ),
)
print(f"Acknowledged constitution v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
print(f"Session: {ack['session']}")
