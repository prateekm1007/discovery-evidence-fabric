"""
epistemic_integrity/version_manifest.py — Single canonical version authority

Per CEO v20 P1-1:
  "Create one canonical version manifest and eliminate all v8/v9/v20 version drift.
   Everything imports it. No duplicated version literals."

v27: HISTORICAL_PROVENANCE_LIMITATION encoded as first-class machine state.
     Dossier firewall enforces limitation on every rendered claim.
     Deterministic post-scrub certification capsule (all 13 gate results).
     GitHub Actions workflow for independent CI reproduction.
     Authorization narrowed to AUTHORIZED_TO_RESUME_UNDER_POST_SCRUB_EPISTEMIC_STATE
     (explicitly NOT ALL_HISTORICAL_EVIDENCE_PRESERVED_EXACTLY).
"""

ENGINE_VERSION = "v27"
SCHEMA_VERSION = "4.3.0"
POLICY_VERSION = "v27"
CERTIFICATION_CORPUS_VERSION = "v14"

