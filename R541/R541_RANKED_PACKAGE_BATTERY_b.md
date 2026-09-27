# R541 — ranked technology package example

scenario: b  ·  run_id: r541-ranked-pkg-battery-b  ·  n_admissible: 1  ·  n_complete_packages: 1  ·  FINISHED_DISCOVERY: True
completion contract: {"finished_discovery": true, "missing_components": [], "typed_terminal_state": "FINISHED_DISCOVERY"}
disposition rows: {"ranked": 3, "killed": 2, "excluded_by_gates": 0}

## Ranked discoveries

## #1 — porous titanium proximal catheter tip in the shunt lumen

candidate: primary:r541-ranked-pkg-battery-b  ·  admissible: True
evidence: verified_against_frozen_evidence (1 records)
mechanism: porous microstructure resists fluid-path tissue ingrowth. The proposed intervention realizes this mechanism by placing p
what would kill it: bench shunt flow loop; measure flow decay over 30 days
adversarial disposition: SURVIVED
engineering / model: conceptual / non-geometric · SYSTEM_3D
decisive experiment: falsification_test_from_candidate (status SPECIFIED)
rank basis: {"verdict_rank": 1, "physics_rank": 0, "quality_verdict": "CONDITIONAL", "physics_lifecycle": "BEATS_BASELINE", "deficient_count": 1, "uncertain_count": 3, "kil

**Technology package #1** `TECHNOLOGY_TRANSFER_PACKAGE_primary.zip` — candidate-bound, sha256 78f7519412f4fead…

## Contract checks

- [PASS] n_admissible==1
- [PASS] n_complete_packages>=1
- [PASS] killed_by_challenge==2
- [PASS] distinct_zip_names
- [PASS] distinct_sha256
- [PASS] candidate_binding
- [PASS] zip_hash_matches_disk
- [PASS] finished_discovery_correct
- [PASS] durable_ranked_result_present
- [PASS] no_cross_candidate_package
- [PASS] verify_ranked_result_set
- [PASS] completion_contract_finished