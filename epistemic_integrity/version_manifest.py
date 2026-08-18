"""
epistemic_integrity/version_manifest.py — Single canonical version authority

Per CEO v20 P1-1:
  "Create one canonical version manifest and eliminate all v8/v9/v20 version drift.
   Everything imports it. No duplicated version literals."

v26: Post-scrub evidence revalidation + historical artifact audit +
     credential audit split (caught missed OpenRouter key) + attestation binding.
     OpenRouter key scrubbed via filter-repo pass 3. All P0 controls GREEN.
"""

ENGINE_VERSION = "v26"
SCHEMA_VERSION = "4.2.0"
POLICY_VERSION = "v26"
CERTIFICATION_CORPUS_VERSION = "v13"

