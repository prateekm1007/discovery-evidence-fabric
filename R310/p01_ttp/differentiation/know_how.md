# Trade-Secret / Know-How Components — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C19

---

## 1. Components NOT in public artifacts (trade-secret / know-how)

### Know-how 1: Bayesian occlusion probability tuning
- **Description:** The specific prior probabilities, likelihood functions, and update rates for the per-segment Bayesian occlusion probability estimator. The algorithm structure is in `04_control_algorithm.json`, but the tuned parameters (learned from 225 ablation runs) are not in the public artifacts.
- **Why it is necessary:** Without the tuned parameters, the predictor either over-reacts (false positives → unnecessary redistributions) or under-reacts (false negatives → missed obstructions). The tuning is the result of extensive simulation that would need to be repeated by anyone implementing from scratch.
- **Form of transfer:** Engineer-to-engineer training (1-2 days) + written parameter documentation under NDA + reference to the 225-ablation provenance.
- **Risk if not transferred:** Buyer would need to re-run the 225 ablations to re-tune, adding 2-4 weeks of engineering time.

### Know-how 2: INV-2 cap tuning
- **Description:** The specific proportional gain and INV-2 cap values that balance INV-1 maintenance against INV-2 preservation. The control law structure is public; the specific gain values are tuned.
- **Why it is necessary:** Wrong gains cause either INV-1 violation (ICP out of band) or INV-2 violation (path overload). Both defeat the purpose.
- **Form of transfer:** Written documentation under NDA + reference to the R288 225-ablation results.
- **Risk if not transferred:** Buyer would need to re-tune, adding 1-2 weeks of engineering time.

### Know-how 3: Simulator scenario generation
- **Description:** The specific scenario generator (5 scenarios × 5 seeds × 5 disturbance types) used to produce the 225-ablation evidence base. The simulator code is public (`05_simulator.py`), but the scenario generation methodology and seed protocol are documented separately.
- **Why it is necessary:** Reproducing the evidence base requires the same scenarios. Different scenarios would produce different results.
- **Form of transfer:** Written documentation + reference to `p01_simulator_results_ALLSCENARIOS.json` (raw outputs preserved).
- **Risk if not transferred:** Buyer could not reproduce the specific 225-ablation evidence base.

## 2. Components in public artifacts (NOT trade-secret)

To prevent the buyer from over-valuing secrets, the following are explicitly in the public TTP and therefore NOT trade-secret:

- The control law structure (Bayesian prediction + proportional redistribution + INV-2 cap)
- The hydraulic architecture (4-segment parallel drainage, variable orifice per segment)
- The component specifications (sensor ranges, actuator specs, electronics class)
- The simulator code (`05_simulator.py`, ~650 lines, no external dependencies)
- The simulator results (raw JSON outputs preserved)
- The bench prototype BOM (COTS components, $3-5K total)
- The prior-art landscape (this dossier)
- The economic model (with evidence-tier labels)

## 3. Boundary

What is being transferred as trade-secret: the **tuned parameters** and **scenario generation methodology** that make the public algorithm produce the specific evidence base documented in this package.

What is NOT being transferred as trade-secret: the algorithm structure, the architecture, the simulator code, the results, the prior art, the economics.

The trade-secret components are necessary to reproduce the specific evidence base, but the public components are sufficient to understand what the technology is and how it works.
