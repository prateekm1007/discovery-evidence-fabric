#!/usr/bin/env python3
"""Acknowledge constitution for v30.13."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')
from epistemic_integrity.constitution_loader import acknowledge_constitution
ack = acknowledge_constitution(
    agent="main",
    session="v30.13-corrected-anchor-semantics",
    intended_change="Correct external-anchor semantics: verify historical existence (commit EXISTS, transition EXISTS in ledger) instead of current-state match (HEAD == registration_commit). Historical evidence survives legitimate future commits. A provenance anchor must prove history, not freeze the future.",
)
print(f"Acknowledged v{ack['constitution_version']} hash={ack['constitution_hash'][:16]}")
