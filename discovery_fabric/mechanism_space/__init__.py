"""R401 Phases 7-11 — the structured mechanism space.

Constitutional frame: this module is the STRUCTURAL layer of invention:
evidence-grounded mechanism graphs, five transformation operators with
MACHINE-VERIFIABLE fidelity (a wording change FAILS, a synonym change
FAILS, a paragraph expansion FAILS), structural material distinctness,
and mechanism-level (not phenomenon-level) evidence verification.

It makes NO scientific claims by itself: every candidate carries
provenance; every operator move carries a derivation trace; every
verification verdict cites the evidence records that produced it.
Downstream CAD/physics execution is OUT of this module (routing only)
so that this layer stays deterministic and testable offline.
"""
from .schema import (evidence_record, mechanism_candidate, OPERATORS,
                     EVIDENCE_FIELDS, CANDIDATE_FIELDS)
from .graph import structure_hash, content_hash, validate_graph
from .operators import apply_operator, operator_fidelity, OPERATOR_SPECS
from .distinctness import structural_dedup
from .verification import verify_mechanism_evidence

__all__ = [
    "evidence_record", "mechanism_candidate", "OPERATORS",
    "EVIDENCE_FIELDS", "CANDIDATE_FIELDS",
    "structure_hash", "content_hash", "validate_graph",
    "apply_operator", "operator_fidelity", "OPERATOR_SPECS",
    "structural_dedup", "verify_mechanism_evidence",
]
