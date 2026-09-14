"""
epistemic_integrity/__init__.py — Epistemic Firewall Package

This package implements the deterministic epistemic firewall required for
dossier-grade integrity. Per CEO directive:

  "A malicious or careless language model must be unable to construct a false
   dossier claim from the repository because the evidence firewall rejects
   the claim before generation.

   We are not trying to make hallucination less likely.
   We are making unsupported claims structurally impossible to publish."

R456-LEAN-2 disposition (the owner's Art. LXV determination, executed
with per-item consumers in archive/r456-lean/MANIFEST.json): the live
package carries ONLY measured-consumer modules —

  CI-called (.github/workflows/epistemic_certification.yml):
    - credential_audit_split.py, historical_artifact_audit.py,
      post_scrub_evidence_revalidation.py, attestation_binding.py,
      research_authorization_gate.py, post_scrub_certification_capsule.py
    - their import closure: path_utils.py, version_manifest.py,
      epistemic_preflight.py, gauntlet/ (the hallucination gauntlet)
  test-consumed:
    - state_transition_ledger.py (tests/test_r412_g5_reconciliation.py)
    - constitution_loader.py (pre-commit hook; test_r419_english_only;
      the Constitution's enforcement point #1)
  engine-consumed:
    - invention_loop_engine/bayesian_eig.py — the live KILLER_EXPERIMENT
      canon, path-loaded by discovery_fabric/engine/adapters.py
  data: credential_false_positive_registry.json,
      real_production_certification_corpus.json, approved_*/

The pre-R396 certification machinery (claim/evidence registries, the
dossier firewall, the supersession engine, the v1 corpus builders and
22 of the 24 invention_loop_engine modules) is ARCHIVED_TO
archive/r455-lean's successor archive/r456-lean/ — importable history,
zero live consumers (Art. LXIV; the full per-item accounting and the
measured-consumer evidence live in that MANIFEST).
"""

__version__ = "1.0.0"
