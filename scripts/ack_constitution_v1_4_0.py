#!/usr/bin/env python3
"""Acknowledge constitution v1.4.0 with Articles XXIII-XXXIV."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')
from epistemic_integrity.constitution_loader import acknowledge_constitution
ack = acknowledge_constitution(
    agent="main",
    session="v1.4.0-articles-xxiii-xxxiv",
    intended_change="Add Articles XXIII-XXXIV (12 anti-gaming/anti-entropy/anti-hallucination principles) "
                    "plus the Master Principle to the Epistemic Constitution. Version bumped to 1.4.0. "
                    "These principles codify lessons from the R6 benchtop protocol hardening cycle: "
                    "local-vs-remote confusion, threshold drift, semantic promotion, "
                    "implementation-vs-mechanism conflation, self-certification, "
                    "and productive-looking avoidance of reality.",
)
print(f"Acknowledged v{ack['constitution_version']}")
print(f"Hash: {ack['constitution_hash']}")
