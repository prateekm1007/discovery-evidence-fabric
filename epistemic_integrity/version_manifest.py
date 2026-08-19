"""
epistemic_integrity/version_manifest.py — Single canonical version authority

Per CEO v20 P1-1:
  "Create one canonical version manifest and eliminate all v8/v9/v20 version drift.
   Everything imports it. No duplicated version literals."

v28: Epistemic Constitution (19 Articles) encoded as first-class machine state.
     constitution_loader.py enforces acknowledgment before gate/dossier/commit.
     Pre-commit hook blocks commits without constitution acknowledgment.
     Constitution hash bound into certification capsule.
"""

ENGINE_VERSION = "v28"
SCHEMA_VERSION = "4.4.0"
POLICY_VERSION = "v28"
CERTIFICATION_CORPUS_VERSION = "v15"

