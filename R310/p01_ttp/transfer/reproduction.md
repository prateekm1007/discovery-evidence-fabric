# Reproduction Guide — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C10

---

## 1. What a competent third party needs to reproduce

A competent engineering team (1 engineer + 1 technician) should be able to reproduce the P-01 simulator results WITHOUT our assistance, using only the artifacts in this TTP.

## 2. Reproduction steps

### 2.1 Software reproduction (simulator)
1. Install Python 3.8+ with numpy and scipy
2. Run `05_simulator.py --self-test` to verify the simulator runs
3. Run `05_simulator.py --scenarios all --seeds 5` to reproduce the 25-scenario baseline
4. Compare output to `p01_simulator_results_ALLSCENARIOS.json` (preserved raw results)
5. Expected: results match within floating-point tolerance (relative error < 1e-6)

### 2.2 Ablation reproduction (225 ablations)
1. Run `05_simulator.py --ablations full` (takes ~10 minutes)
2. Compare output to the preserved 225-ablation results
3. Expected: rate-limiting confirmed as critical mechanism in 41/45 runs (per R288)

### 2.3 Hardware reproduction (V0 bench prototype)
1. Procure components per `technology/prototype_blueprint.md` §1.2
2. Assemble per `transfer/installation.md` §2
3. Calibrate per `transfer/installation.md` §2.3
4. Run the 30-run test program (6 scenarios × 5 seeds × 24h, 720 bench-hours)
5. Compare results to simulator predictions
6. Expected: multi-segment peak ICP lower than single-segment baseline (simulator: 22 vs 59 mmHg)

## 3. What could go wrong (and how to debug)

### 3.1 Simulator does not reproduce
- **Cause:** Different numpy/scipy version producing different floating-point behavior
- **Fix:** Pin numpy/scipy versions in requirements.txt; use the same seed protocol

### 3.2 Hardware peak ICP does not match simulator
- **Cause:** Hardware has friction, compliance, and noise that the simulator does not model
- **Fix:** This is expected. The simulator is a lower bound. Hardware results should be WORSE than simulator (higher peak ICP, lower INV-2 preservation). If hardware results are BETTER than simulator, something is wrong with the simulator.

### 3.3 Bayesian predictor false-positive rate too high
- **Cause:** Tuned parameters (know-how) not transferred
- **Fix:** Engineer-to-engineer training on the tuned parameters (see `differentiation/know_how.md`)

## 4. Reproduction package contents

The reproduction package includes:
- `05_simulator.py` — executable Python simulator (~650 lines, no external dependencies)
- `01_hydraulic_architecture.json` — full hydraulic model specification
- `02_component_specification.json` — component specifications
- `03_sensor_specification.json` — sensor specifications
- `04_control_algorithm.json` — control law specification
- `06_bench_prototype_design.json` — V0 bench prototype design
- `07_test_fixtures.json` — test fixture specifications
- `08_acceptance_criteria.json` — acceptance criteria
- `p01_simulator_results_ALLSCENARIOS.json` — preserved raw results (25 scenarios)
- `p01_simulator_results_mild_42.json` — preserved raw results (specific scenario)
- `EXTERNAL_VALIDATION_HANDOFF/` — frozen protocol for external validation

## 5. Minimum reproducible claim

The minimum claim that a competent third party should be able to reproduce:

> "Running the P-01 simulator on the 25-scenario baseline (5 scenarios × 5 seeds), the multi-segment configuration achieves peak ICP of ~22 mmHg under progressive multi-segment failure, compared to ~59 mmHg for the single-segment baseline. INV-2 (no path overload) is preserved in 5/5 scenarios for multi-segment. Neither configuration achieves 24h survival (both break at ~14h)."

If the third party cannot reproduce this minimum claim, the package is defective and should be returned for correction.

## 6. CEO test (Article XXXVI §16)

> Could you take this folder tomorrow, hand it to a competent engineering team, and have them start evaluating the technology without needing us to explain away gaps?

For P-01: **PARTIAL YES.** The simulator reproduces. The V0 bench prototype is buildable from COTS. The blocking unknowns (implantable flow sensor, 24h survival, clinical validation) are honestly disclosed in `technology/known_limitations.md`.

The answer is not a full YES until the V0 bench prototype confirms the simulator findings on hardware.
