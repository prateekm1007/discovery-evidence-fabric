# R541 — ranked technology package example

scenario: c  ·  run_id: r541-ranked-pkg-battery-c  ·  n_admissible: 3  ·  n_complete_packages: 3  ·  FINISHED_DISCOVERY: True
completion contract: {"finished_discovery": true, "missing_components": [], "typed_terminal_state": "FINISHED_DISCOVERY"}
disposition rows: {"ranked": 3, "killed": 0, "excluded_by_gates": 0}

## Ranked discoveries

## #1 — porous titanium proximal catheter tip in the shunt lumen

candidate: primary:r541-ranked-pkg-battery-c  ·  admissible: True
evidence: verified_against_frozen_evidence (1 records)
mechanism: porous microstructure resists fluid-path tissue ingrowth. The proposed intervention realizes this mechanism by placing p
what would kill it: bench shunt flow loop; measure flow decay over 30 days
adversarial disposition: SURVIVED
engineering / model: conceptual / non-geometric · SYSTEM_3D
decisive experiment: falsification_test_from_candidate (status SPECIFIED)
rank basis: {"verdict_rank": 1, "physics_rank": 0, "quality_verdict": "CONDITIONAL", "physics_lifecycle": "BEATS_BASELINE", "deficient_count": 1, "uncertain_count": 3, "kil

**Technology package #1** `TECHNOLOGY_TRANSFER_PACKAGE_primary.zip` — candidate-bound, sha256 b498934b1c87b982…

## #2 — porous titanium proximal catheter tip in the shunt lumen

candidate: cand:MS:A:r541  ·  admissible: True
evidence: verified_against_frozen_evidence (1 records)
mechanism: porous titanium microstructure resists tissue ingrowth in the catheter tip
what would kill it: bench shunt loop with choroid plexus tissue analog; measure flow decay over 30 days vs silicone control catheter
adversarial disposition: SURVIVED
engineering / model: conceptual / non-geometric · SYSTEM_3D
decisive experiment: falsification_test_from_candidate (status SPECIFIED)
rank basis: {"verdict_rank": 1, "physics_rank": 0, "quality_verdict": "CONDITIONAL", "physics_lifecycle": "BEATS_BASELINE", "deficient_count": 1, "uncertain_count": 4, "kil

**Technology package #2** `TECHNOLOGY_TRANSFER_PACKAGE_mech-DIRECT_TRANSFER-1.zip` — candidate-bound, sha256 2d31a1f937b63e8e…

## #3 — apply a two-kilovolt electrostatic field to the channel walls

candidate: cand:MS:B:r541  ·  admissible: True
evidence: verified_against_frozen_evidence (1 records)
mechanism: electrostatic repulsion of charged dust at the channel wall surface
what would kill it: measure particle deposition rate under 2 kV vs 0 kV; expect a 90 percent reduction
adversarial disposition: SURVIVED
engineering / model: conceptual / non-geometric · SYSTEM_3D
decisive experiment: falsification_test_from_candidate (status SPECIFIED)
rank basis: {"verdict_rank": 1, "physics_rank": 0, "quality_verdict": "CONDITIONAL", "physics_lifecycle": "BEATS_BASELINE", "deficient_count": 1, "uncertain_count": 4, "kil

**Technology package #3** `TECHNOLOGY_TRANSFER_PACKAGE_mech-OPERATOR_B-1.zip` — candidate-bound, sha256 543c19e3719f965b…

## Contract checks

- [PASS] n_admissible>=2
- [PASS] n_complete_packages>=2
- [PASS] distinct_zip_names
- [PASS] distinct_sha256
- [PASS] candidate_binding
- [PASS] zip_hash_matches_disk
- [PASS] finished_discovery_correct
- [PASS] durable_ranked_result_present
- [PASS] no_cross_candidate_package
- [PASS] verify_ranked_result_set
- [PASS] completion_contract_finished