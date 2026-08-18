"""
epistemic_integrity/__init__.py — Epistemic Firewall Package

This package implements the deterministic epistemic firewall required for
dossier-grade integrity. Per CEO directive:

  "A malicious or careless language model must be unable to construct a false
   dossier claim from the repository because the evidence firewall rejects
   the claim before generation.

   We are not trying to make hallucination less likely.
   We are making unsupported claims structurally impossible to publish."

Modules:
  - evidence_classes.py: 9-class evidence taxonomy with enforced wording
  - claim_registry.py: Claim ID assignment + storage + lookup
  - evidence_binding.py: Bidirectional Claim <-> Evidence <-> Source binding
  - provenance_validator.py: Validates every claim traces to commit + hash
  - supersession_engine.py: Enforces CURRENT/SUPERSEDED/INVALIDATED/HISTORICAL/FROZEN
  - dossier_firewall.py: Generator consumes ONLY approved canonical set
  - epistemic_preflight.py: E1-E15 mandatory checks
  - gauntlet/: 18 adversarial hallucination tests (H1-H18)
"""

__version__ = "1.0.0"
