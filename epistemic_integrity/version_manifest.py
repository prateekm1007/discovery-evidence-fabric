"""
epistemic_integrity/version_manifest.py — Single canonical version authority

Per CEO v20 P1-1:
  "Create one canonical version manifest and eliminate all v8/v9/v20 version drift.
   Everything imports it. No duplicated version literals."

v25: Bumped to v25 to reflect credential history scrub + detached runner integration
     + scanner pattern hardening (exact-length + hex boundaries).
"""

ENGINE_VERSION = "v25"
SCHEMA_VERSION = "4.1.0"
POLICY_VERSION = "v25"
CERTIFICATION_CORPUS_VERSION = "v12"

