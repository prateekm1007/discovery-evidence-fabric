# Mechanism Specification — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Version:** 1.2.0 (R277 self-corrected)
**Authority:** Article XXXVI §2 C01
**Status:** MODELLED (with R277 self-correction: strict dual-invariant FALSIFIED by simulator)

---

## 1. What this candidate is, in mechanism terms

P-01 is a **control law** for a multi-segment CSF shunt system. The mechanism is not a device architecture — it is a predictive redistribution algorithm that maintains two simultaneous safety invariants while draining CSF:

- **INV-1:** Global ICP remains within a target band (P_MIN ≤ P_ICP ≤ P_MAX).
- **INV-2:** No surviving drainage path is overloaded (each segment's flow ≤ F_MAX).

The controller predicts impending obstruction on each segment from flow/pressure trends, then pre-emptively redistributes drainage to healthy segments before the at-risk segment fails completely.

## 2. The causal chain

```
Flow/pressure trends (per segment)
        ↓
Bayesian occlusion probability estimate (per segment)
        ↓
Pre-emptive flow redistribution (reduce at-risk, increase healthy)
        ↓
Global ICP stability (INV-1) + path overload prevention (INV-2)
```

## 3. Operating states

| State | Description |
|-------|-------------|
| Normal | All segments healthy. Flow distributed normally. |
| Warning | One or more segments show elevated occlusion probability (>threshold). Flow proactively reduced on at-risk segments, redistributed to healthy segments. |
| Isolation | Segment occlusion probability exceeds critical threshold. Segment isolated. All flow redistributed to healthy segments respecting dual invariant. |
| Graceful degradation | Multi-segment failure exceeds design capacity. INV-2 preserved (no path overload). INV-1 violated (P_ICP 20-25 mmHg). System continues operating for several hours but does NOT meet 24h survival — breaks at ~14h. |
| Fail safe | Complete controller failure. Reverts to passive pressure-reactive drainage (standard shunt behavior). |
| Recovery | Isolated segment recovered (flow restored). System returns to normal. |

## 4. Physics basis

Hydraulic flow distribution in a multi-segment drainage network with variable conductance:

```
P_ICP = Q_production / sum(G_active)
```

Occlusion modeled as conductance decline over time. See `technology/architecture.md` for full hydraulic model.

## 5. The R277 self-correction (Article XXXI)

The initial R277 audit overclaimed "graceful degradation, survival 5/5." Re-analysis of actual simulator JSON data showed survival=0/5 across ALL scenarios. Corrected per Article XXXI.

**Honest finding:** Strict INV-1 FAILS at peak ~22 mmHg under multi-segment progressive failure. The system ALSO fails the 24h survival criterion — in BOTH multi-segment AND single-segment baseline. P-01 is a PARTIAL IMPROVEMENT (peak 22 mmHg vs 59 mmHg baseline; INV-2 preserved 5/5), not a complete solution.

## 6. What the mechanism is NOT

- Not a device architecture (the control law could be implemented on any multi-segment shunt hardware).
- Not a sensor innovation (uses existing commercial pressure sensors; implantable flow sensor is a blocking unknown — see `technology/engineering_spec.md`).
- Not a complete solution to shunt obstruction (both P-01 and baseline fail 24h survival; P-01 is better but not sufficient).

## 7. Provenance

- Source artifacts: `TTP_PACKAGES/P-01_PROTOTYPE/01_hydraulic_architecture.json`, `04_control_algorithm.json`, `05_simulator.py`
- R277 simulator results: `TTP_PACKAGES/P-01_PROTOTYPE/p01_simulator_results_ALLSCENARIOS.json`
- Self-correction log: `TTP_PACKAGES/P-01_FULL_TTP.json` §1_executive_technology_brief.self_correction_log_R277
