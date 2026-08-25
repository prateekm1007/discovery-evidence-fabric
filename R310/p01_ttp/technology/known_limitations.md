# Known Limitations — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C09
**Status:** HONEST DISCLOSURE per Article XV

---

## 1. The strict dual-invariant claim was FALSIFIED (R277)

**Initial claim:** The controller maintains P_ICP ≤ 20 mmHg (INV-1) AND no path overloaded (INV-2) under multi-segment progressive failure.

**Simulator finding:** Peak ICP reaches ~22 mmHg, violating INV-1 by ~2 mmHg. INV-2 is preserved (5/5 scenarios).

**Status:** FALSIFIED. The controller does NOT maintain the strict dual invariant. It maintains INV-2 but violates INV-1 by a small margin under worst-case multi-segment failure.

## 2. The 24h survival claim was OVERCLAIMED then CORRECTED (R277)

**Initial claim (R277 first audit):** "Graceful degradation, survival 5/5."

**Actual simulator data:** Survival = 0/5 in ALL scenarios. Both multi-segment and single-segment break at ~14h when ICP has been out-of-band for >1 hour cumulative.

**Status:** SELF-CORRECTED per Article XXXI. The honest finding is that P-01 is a partial improvement (lower peak ICP, preserved INV-2) but does NOT solve the 24h survival problem.

## 3. The implantable flow sensor does not exist

The controller's predictive algorithm depends on per-segment flow observation. No chronic implantable CSF flow sensor exists commercially. Three workarounds are under consideration (see `technology/engineering_spec.md`), but each has trade-offs:

- Custom ultrasonic: 12-18 month development, $100-200K
- Pressure-differential inference: lower accuracy, slower detection
- Eliminate per-segment flow: loses observability, weakens the predictive algorithm

Without resolving this, V1 implantable development is blocked.

## 4. The 24h survival failure is not yet resolved

Both P-01 (multi-segment) and the baseline (single-segment) fail 24h survival under the R277 test scenarios. P-01 is better (peak 22 vs 59 mmHg) but neither is sufficient. Next iteration needed:

- Increase F_MAX_PER_SEG (more capacity per path)
- Increase N_SEGMENTS (more redundancy)
- Add accumulator buffer (CSF storage during peak demand)
- Or accept that 24h survival is not achievable and re-specify the criterion

This is unresolved. Article XXXIV applies — coding won't fix it; bench testing will.

## 5. The model is hydraulic-only

The R277 simulator models hydraulic flow distribution. It does NOT model:

- Biological fouling (protein adsorption, cell adhesion)
- Material degradation (silicone fatigue, valve wear)
- Sensor drift over years
- Patient-specific anatomy (only generic adult CSF physiology)
- Realistic obstruction morphology (only linear conductance decline)

These must be addressed in V0 bench testing and V1 implantable development.

## 6. Theeconomic claim is MODELLED only

The economic model (see `economics/value_model.md`) is based on published shunt revision surgery costs ($35K-$50K per revision) and an assumed 30% reduction in revision rate. The 30% reduction is MODELLED, not measured. Path to PUBLICLY_VERIFIED requires V0 bench testing + clinical data. Path to BUYER_VERIFIED requires buyer-specific data under NDA.

## 7. No clinical data exists

P-01 has zero clinical data. The simulator is the only evidence. The path to clinical evidence is:

- V0 bench (this package)
- V1 implantable (12-18 months)
- V2 pre-clinical animal (12-24 months)
- Clinical trial (4-8 years)

The package being transferred is the technology and the simulator evidence, NOT a clinical claim.

## 8. The hostile attack matrix has not been run on hardware

The simulator's hostile attack matrix (see `evidence/attacks/`) includes:
- INV-2 attacker (fast lesion)
- INV-1 attacker (slow all-segment)
- Predictor false-positive (noise spikes)
- Predictor false-negative (very slow lesion)
- Communication failure

These have been run in simulation. They have NOT been run on hardware. V0 bench testing must include the hostile matrix.

## 9. What this package does NOT claim

- Does NOT claim P-01 solves shunt obstruction (it doesn't — both designs fail 24h survival)
- Does NOT claim clinical benefit (no clinical data exists)
- Does NOT claim the dual invariant holds strictly (it doesn't — INV-1 violated by ~2 mmHg)
- Does NOT claim the implantable hardware is buildable today (flow sensor is blocking unknown)
- Does NOT claim the economic value is verified (it is MODELLED only)

## 10. What this package DOES claim

- The control law is designed and specified
- The reference implementation runs and is reproducible
- The simulator honestly reports its own falsification (strict dual-invariant fails)
- The partial improvement (peak 22 vs 59 mmHg; INV-2 preserved) is real and reproducible
- The path to V0 bench prototype is defined and buildable with COTS components
- The path to clinical evidence is defined (5-10 years, $22-53M)

## 11. Provenance

- Self-correction log: `TTP_PACKAGES/P-01_FULL_TTP.json` §1_executive_technology_brief.self_correction_log_R277
- Simulator falsification data: `TTP_PACKAGES/P-01_PROTOTYPE/p01_simulator_results_ALLSCENARIOS.json`
