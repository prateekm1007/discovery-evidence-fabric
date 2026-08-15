# TOP-20 Invention Generation Report

Generated: 2026-08-15T12:31:17.089264+00:00

Root hash: `11845b310c9d6157`


## Summary

| Metric | Value |
|--------|-------|
| Input AICs | 20 |
| Inventions generated | 20 |
| Survived (INVENTION_CANDIDATE) | 0 |
| Refinement exhausted | 3 |
| Failed | 17 |
| Convergent inventions | 0 |
| Total refinement rounds | 6 |

## Conversion Metrics

| Metric | Value |
|--------|-------|
| aic_to_invention_conversion_rate | 0.15 |
| mean_refinement_rounds | 0.3 |
| prior_art_distribution | {'ADJACENT_PRIOR_ART': 3} |
| adversarial_distribution | {'KILLED': 3, 'UNKNOWN': 17} |
| experiment_ready_rate | 0.1 |
| falsifier_present_rate | 0.15 |

## Per-Invention Lineage

| Invention ID | Parent AIC | Status | Nucleus | Refinement | LLM Calls |
|-------------|-----------|--------|---------|-----------|-----------|
| INV_TOP20_001 | M0_fd_042 | REFINEMENT_EXHAUSTED | A dual-chip MEMS pressure sensor system with a dynamically c | 2 | 13 |
| INV_TOP20_002 | M4C_fd_042 | PASS3_NO_ARCHITECTURES |  | 0 | 3 |
| INV_TOP20_003 | M0_fd_060 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_004 | M4_fd_060 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_005 | M4C_fd_040 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_006 | M3_fd_098 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_007 | M4C_fd_070 | REFINEMENT_EXHAUSTED | A microfluidic capillary wick structure integrated into the  | 2 | 13 |
| INV_TOP20_008 | M4_fd_056 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_009 | M0_fd_040 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_010 | M3_fd_019 | REFINEMENT_EXHAUSTED | A shape-memory polymer valve leaflet with a bilayer structur | 2 | 13 |
| INV_TOP20_011 | M3_fd_022 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_012 | M4B_fd_054 | PASS2_NO_MECHANISMS |  | 0 | 2 |
| INV_TOP20_013 | M4_fd_019 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_014 | M4B_fd_069 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_015 | M4B_fd_049 | PASS2_NO_MECHANISMS |  | 0 | 2 |
| INV_TOP20_016 | M1_fd_013 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_017 | M2_fd_043 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |
| INV_TOP20_018 | M1_fd_022 | PASS2_NO_MECHANISMS |  | 0 | 2 |
| INV_TOP20_019 | M1_fd_008 | PASS2_NO_MECHANISMS |  | 0 | 2 |
| INV_TOP20_020 | M2_fd_028 | PASS1_RECONSTRUCT_FAILED |  | 0 | 1 |

## Prior-Art Distribution

- ADJACENT_PRIOR_ART: 3

## Adversarial Distribution

- UNKNOWN: 17
- KILLED: 3

## What Additional Invention Value Did the Engine Create?

The invention synthesis engine transformed AICs (which are brief proposed modifications) 
into structured invention candidates with:

- Specific inventive nucleus (not vague improvement)
- Causal chain (failure → cause → intervention → mechanism → effect → response)
- System architecture (components, interfaces, materials, control logic)
- Design parameters (provenance-tagged: EVIDENCE_DERIVED / ENGINEERING_DERIVED / HYPOTHESIS)
- Boundary conditions (failure containment)
- Predictions (observable, baseline, expected direction/magnitude, falsifier)
- Experiment plan (controls, falsification condition, cost, duration, information gain)
- Adversarial analysis (7 dimensions)
- Prior-art assessment (NO_MATCH_FOUND / ADJACENT / SPECIFIC_DISCLOSURE_RISK / UNRESOLVED)
- Refinement history (generation → attack → refinement → attack)

The AIC said 'add a sensor.' The invention specifies WHERE, WHAT SIGNAL, 
HOW DISAGREEMENT IS DETECTED, HOW THE CONTROLLER RESPONDS, and WHAT FALSIFIES IT.


## Governance

- V3 historical artifacts NOT modified (root hash 4d10e01c5c246133 preserved)
- No V4 candidates generated
- No novelty or patentability claimed
- PATENTABILITY_STATUS: NOT_ESTABLISHED on every invention
- Model-agnostic routing (Mistral primary, NVIDIA fallback)