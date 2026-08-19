"""
epistemic_integrity/evidence_identity_adapter.py — Bridge between the
discovery-layer evidence identity model (orchestrator/evidence_identity.py)
and the production dossier evidence model (epistemic_integrity/evidence_binding.py).

CEO v30.8: This adapter is the PRODUCTION BOUNDARY between discovery and
dossier. It provides:

  1. Re-exports VerifiedEvidence and EvidenceAuthorizationError from
     orchestrator/evidence_identity.py so that epistemic_integrity modules
     can import them without a direct cross-package dependency at module
     load time (avoids circular imports).

  2. Mapping functions that convert a VerifiedEvidence into the fields
     needed to construct a production Source object:
       - _verified_evidence_to_source_type(ve) -> str
       - _verified_evidence_to_identifier(ve) -> str

This adapter exists as a SEPARATE module so that:
  - epistemic_integrity/evidence_binding.py imports from this adapter
    (lazy import inside the method, not at module load)
  - The adapter imports from orchestrator/evidence_identity.py
  - No circular dependency is created

Article XVII: This adapter IS a P0 control boundary. Every attempt to
bypass it must be adversarially tested.
"""

# Re-export the type-safe evidence types from the discovery layer.
# These are imported at module load time because the adapter's whole
# purpose is to bridge the two packages.
from orchestrator.evidence_identity import (
    VerifiedEvidence,
    EvidenceAuthorizationError,
    EvidenceIdentity,
    DOCUMENT_ID_CONFIRMED,
    EVENT_ID_CONFIRMED,
)


def _verified_evidence_to_source_type(verified: VerifiedEvidence) -> str:
    """Map a VerifiedEvidence's canonical_id_type to a production Source.source_type.

    Production Source.source_type values (per evidence_binding.py):
      "PMID" / "DOI" / "PATENT" / "URL" / "BOOK" / "INTERNAL_REPORT" /
      "INTERNAL_ANALYSIS"

    Discovery-layer canonical_id_type values (per evidence_identity.py):
      "DOI" / "PMID" / "PATENT_NUMBER" / "K_NUMBER" / "PMA_NUMBER" /
      "MDR_REPORT_KEY" / "RECALL_NUMBER" / "NCT_ID" / "PROJECT_NUM" /
      "FAMILY_ID" / "FINGERPRINT"

    Mapping:
      DOI              -> DOI
      PMID             -> PMID
      PATENT_NUMBER    -> PATENT
      K_NUMBER         -> K_NUMBER  (FDA 510k)
      PMA_NUMBER       -> PMA_NUMBER
      MDR_REPORT_KEY   -> MDR_REPORT_KEY
      RECALL_NUMBER    -> RECALL_NUMBER
      NCT_ID           -> NCT_ID
      PROJECT_NUM      -> PROJECT_NUM
      (others)         -> URL  (fallback for unknown types)
    """
    id_type = verified.canonical_id_type
    # Direct mappings (most common)
    if id_type in ("DOI", "PMID"):
        return id_type
    if id_type == "PATENT_NUMBER":
        return "PATENT"
    # FDA / clinical / NIH types pass through with their native name
    if id_type in ("K_NUMBER", "PMA_NUMBER", "MDR_REPORT_KEY",
                   "RECALL_NUMBER", "NCT_ID", "PROJECT_NUM"):
        return id_type
    # FINGERPRINT and FAMILY_ID should never reach here — they cannot
    # become VerifiedEvidence. But defensively, map to URL.
    return "URL"


def _verified_evidence_to_identifier(verified: VerifiedEvidence) -> str:
    """Extract the production Source.identifier from a VerifiedEvidence.

    For most types, this is just verified.canonical_id. For patents,
    the canonical_id already includes jurisdiction + number + kind_code
    (preserved per v30.5). For DOIs, the canonical_id is already
    normalized (lowercase, no URL prefix).
    """
    return verified.canonical_id


def is_verified_evidence(obj) -> bool:
    """Type-check helper. Returns True iff obj is a VerifiedEvidence instance.

    CEO v30.8: Used by defense-in-depth checks in the production path.
    """
    return isinstance(obj, VerifiedEvidence)
