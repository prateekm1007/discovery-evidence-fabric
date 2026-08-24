# P-01 Reference Implementation — README

## What this is

This directory contains the **PROTOTYPE_READY** reference implementation for P-01 (Predictive Occlusion-Isolation Controller).

It is the falsification engine for the dual-invariant claim. The decisive technical question:

> **Can the dual invariant actually be maintained when one or more paths progressively fail?**

## Honest answer from the simulator

**STRICT dual-invariant FAILS.** Peak ICP reaches ~22 mmHg (vs. 20 mmHg hard limit) under multi-segment progressive failure.

**GRACEFUL DEGRADATION succeeds.** INV-2 (no path overload) is preserved 100% of the time. INV-1 is mildly violated (peak 22 vs. 20) but far below catastrophic (>40 mmHg). The multi-segment system is **strictly superior to single-segment baseline** (peak 59 mmHg, 0/5 survive).

This finding is documented in `01_hydraulic_architecture.json` and must be reflected in element 1 of the parent TTP.

## Constitutional basis

- **Article XXX** (Never optimize the evaluator) — the simulator is hostile. It tries to break the dual-invariant, not flatter it.
- **Article XXVIII** (No silent semantic promotion) — passing the simulator does NOT promote the package to VALIDATED. It promotes only to PROTOTYPE_READY.
- **Article XXXV** (Closed-loop epistemic control) — the simulator is the "mechanistic simulator" slot. The "experiment" slot (bench prototype) is still empty.

## Files

| File | Purpose |
|------|---------|
| `01_hydraulic_architecture.json` | Hydraulic topology, physics model, design operating point, design limit identified by simulator |
| `02_component_specification.json` | Bill of materials (bench V0 and implantable V1) with commercial part numbers |
| `03_sensor_specification.json` | Pressure and flow sensor specs, redundancy strategy, failure modes |
| `04_control_algorithm.json` | Algorithm spec, tuning parameters, what buyer must tune on bench |
| `05_simulator.py` | The reference implementation. Run it. |
| `06_bench_prototype_design.json` | V0 bench prototype (3-6 months, $3-5K) and V1 implantable (12-18 months, $200-500K) |
| `07_test_fixtures.json` | Virtual patient cohort, bench fixtures, hostile test matrix |
| `08_acceptance_criteria.json` | Pre-registered pass/fail criteria — cannot be silently relaxed |
| `EXTERNAL_VALIDATION_HANDOFF/` | Folder for buyer/external lab to run validation without trusting us |
| `p01_simulator_results_ALLSCENARIOS.json` | Last simulator run output (25 runs across 5 scenarios × 5 seeds) |

## How to run

```bash
cd /home/z/my-project/discovery-evidence-fabric/TTP_PACKAGES/P-01_PROTOTYPE
python 05_simulator.py --all-scenarios
```

This runs 25 simulations (5 scenarios × 5 seeds) and writes results to `p01_simulator_results_ALLSCENARIOS.json`.

## What the buyer should do

1. **Read the simulator code.** It's ~650 lines of Python with no external dependencies. Audit the physics model, the controller, and the predictor.
2. **Run the simulator.** Reproduce the falsification finding on your own machine.
3. **Attack the simulator.** Try scenarios we didn't include. Try to break the dual-invariant further. If you find a scenario where INV-2 fails, that is a critical design defect.
4. **Tune the controller.** The three MODEL_DERIVED parameters (K_p, ISOLATE_THRESHOLD, PREDICTOR_WINDOW_SEC) are starting points. Buyer must re-tune on bench.
5. **Build V0 bench prototype.** See `06_bench_prototype_design.json`. ~3-6 months, ~$3-5K.
6. **Run bench tests against pre-registered acceptance criteria.** See `08_acceptance_criteria.json`. Cannot be silently relaxed.
7. **Decide whether to proceed to V1 implantable prototype.** This is a $200-500K, 12-18 month decision. The biggest unknown is the implantable flow sensor (no commercial option exists).

## Status

| Dimension | Status |
|-----------|--------|
| Reference implementation | COMPLETE (simulator runs, results reproducible) |
| Falsification attempt | COMPLETE (strict dual-invariant falsified, graceful degradation confirmed) |
| Bench prototype design | FROZEN (waiting for buyer to build) |
| Acceptance criteria | PRE-REGISTERED (cannot be silently relaxed) |
| External validation handoff | READY (see EXTERNAL_VALIDATION_HANDOFF/) |
| Bench validation | NOT YET RUN (next constitutionally-required action) |
| Clinical validation | NOT YET RUN (years away) |
| Regulatory approval | NOT YET RUN (years away) |

**State machine position:** `TECHNICALLY_SPECIFIED → PROTOTYPE_READY` ✅ (this round)

**Next state:** `PROTOTYPE_READY → VALIDATION_READY` requires bench prototype built and tests run against pre-registered acceptance criteria.
