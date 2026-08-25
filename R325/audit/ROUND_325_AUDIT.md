# ROUND 325 AUDIT — Close the Loop

**Round:** 325
**Date:** 2026-08-26
**Remote HEAD:** (R325 pending push)

---

## What R325 delivered

### P0 — Canonical portfolio manifest (frozen)
15 entries (14 active + 1 vacancy). Each has 16 fields: identity, mechanism, current_state, evidence_classes, executable_artifact, external_solver, verification_status, known_failures, unknowns, buyer_action, real_world_experiment, expected_information_gain, decision_consequences, knowledge_atoms_consumed, knowledge_atoms_created, next_machine_action. No prose dashboard may override.

### P1/P2 — Bidirectional buyer protocol + simulated buyer return

**The most important R325 deliverable.** The machine demonstrated it can:
1. **Receive** experimental data (INBOUND protocol with raw_data_hash, result, uncertainty, provenance)
2. **Ingest** the result
3. **Classify** evidence (PHYSICALLY_VALIDATED / FALSIFIED / INSUFFICIENT_RESOLUTION)
4. **Transition** state (EXPERIMENT_READY → TECHNICALLY_EVALUABLE / CEMETERY / repeat)
5. **Create** knowledge atom from the result
6. **Select** next experiment (EIG/cost optimization)

**Three simulated cases for P-02:**
- Case A (PASS): 45.7% reduction → TECHNICALLY_EVALUABLE → KA-010 created → next: P-20
- Case B (FAIL): 8.6% reduction → CEMETERY → KA-011 created → next: P-20
- Case C (AMBIGUOUS): 25.8% reduction (CI spans pass/fail) → repeat with n=30 → KA-012 created → next: P-20 (higher EIG/cost)

**The machine did NOT allow ambiguous to become PASS.** This is the end-to-end AI loop.

### P3 — Machine chooses next experiment
EIG/cost analysis across 8 experiment-ready candidates. P-20 selected (EIG/cost = 1.7, highest). The machine considers: untested mechanism (higher info gain), lower cost, shorter timeline, lower risk.

### P4 — External simulators as first-class evidence sources
Each solver record: solver, version, source, license, equations, numerical method, known approximations, known limitations, input_hash, mesh_hash, parameter_hash, solver_config_hash, output_hash, runtime, convergence, sensitivity, reference_case, candidate_case. Distinction between official benchmark execution and candidate-specific execution preserved.

### P5 — TTR brutal audit
- P-01: 18/22 PASS. "Computationally verified; physical prototype validation outstanding."
- P-15: 16/22 PASS. "Computational robustness ≠ physical validation. NOT independently validated."
- P-16: 19/22 PASS. "Independently validated. HG approximation preserved. Physical outstanding."
- **No candidate is fully validated.** All limitations explicit. No ambiguity.

### P6 — Language corrected
Experiment packages called "experiment-ready technology packages" not "working." A company can inspect, reproduce computational evidence, and know exactly what experiment will prove or kill it. That is NOT the same as "this technology works."

### P7 — Cemetery packages as product
P-14, P-17, P-19 each have: negative knowledge, falsification evidence, failure mechanism, applicability boundary, future-candidate prohibition. P-19's conductance-matching lesson (KA-009) automatically prevents the factory from repeating the same experimental mistake.

---

## CEO checklist

| Objective | Status |
|-----------|--------|
| 15 portfolio slots | 14 active + 1 vacancy |
| Canonical manifest | ✅ frozen, 16 fields per candidate |
| Bidirectional buyer protocol | ✅ OUTBOUND + INBOUND defined |
| Simulated buyer return | ✅ 3 cases (PASS/FAIL/AMBIGUOUS) demonstrated |
| Machine chooses next experiment | ✅ EIG/cost analysis, P-20 selected |
| External simulators as evidence sources | ✅ first-class with hashes + limitations |
| TTR brutal audit | ✅ all limitations explicit, no ambiguity |
| Cemetery packages as product | ✅ negative knowledge + prohibitions |
| Knowledge atoms executable | ✅ trigger → rule → action |
| End-to-end closed loop | ✅ **DEMONSTRATED** (simulated) |

## The number that matters

**3 TTR** (computationally verified, physical outstanding)
**8 experiment-ready** (buyer contracts complete, machine can ingest results)
**3 cemetery** (reusable negative knowledge, future prohibitions)
**1 evaluation-ready** (chemistry program needed)
**1 vacancy** (honest)

**The loop is now closed (simulated).** The machine can: receive experimental data → classify evidence → transition state → create knowledge atom → select next experiment. All without human interpretation.

The next real test: when a CEO-provided buyer returns actual experimental data, the machine processes it through this protocol autonomously.
