# R541 — ranked technology package example

scenario: a  ·  run_id: r541-ranked-pkg-battery-a  ·  n_admissible: 1  ·  n_complete_packages: 1  ·  FINISHED_DISCOVERY: True
completion contract: {"finished_discovery": true, "missing_components": [], "typed_terminal_state": "FINISHED_DISCOVERY"}
disposition rows: {"ranked": 3, "killed": 0, "excluded_by_gates": 2}

## Ranked discoveries

## #1 — porous titanium proximal catheter tip in the shunt lumen

candidate: primary:r541-ranked-pkg-battery-a  ·  admissible: True
evidence: verified_against_frozen_evidence (1 records)
mechanism: porous microstructure resists fluid-path tissue ingrowth. The proposed intervention realizes this mechanism by placing p
what would kill it: bench shunt flow loop; measure flow decay over 30 days
adversarial disposition: SURVIVED
engineering / model: conceptual / non-geometric · SYSTEM_3D
decisive experiment: falsification_test_from_candidate (status SPECIFIED)
rank basis: {"verdict_rank": 1, "physics_rank": 0, "quality_verdict": "CONDITIONAL", "physics_lifecycle": "BEATS_BASELINE", "deficient_count": 1, "uncertain_count": 3, "kil

**Technology package #1** `TECHNOLOGY_TRANSFER_PACKAGE_primary.zip` — candidate-bound, sha256 650c0a6901a1f050…

## Contract checks

- [PASS] n_admissible==1
- [PASS] n_complete_packages>=1
- [PASS] zero_kills
- [PASS] competing_excluded_by_gates==2
- [PASS] excluded_never_admissible
- [PASS] distinct_zip_names
- [PASS] distinct_sha256
- [PASS] candidate_binding
- [PASS] zip_hash_matches_disk
- [PASS] finished_discovery_correct
- [PASS] durable_ranked_result_present
- [PASS] no_cross_candidate_package
- [PASS] verify_ranked_result_set
- [PASS] completion_contract_finished