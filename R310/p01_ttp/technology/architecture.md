# Architecture / Design — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Version:** 1.2.0
**Authority:** Article XXXVI §2 C02
**Status:** MODELLED (reference implementation complete; implantable hardware blocking unknowns)

---

## 1. System architecture

### 1.1 Subsystems

1. **Multi-segment drainage catheter** with individual flow control (variable orifice per segment)
2. **Pressure/flow sensors per segment** (commercial pressure sensors; implantable flow sensors are a blocking unknown)
3. **Central controller** running the predictive redistribution algorithm
4. **Communication** between segments (if distributed) or central processing (if integrated)

### 1.2 Data flow

```
Sensor data → occlusion probability model → redistribution decision →
actuator commands → flow adjustment → sensor feedback
```

### 1.3 Control flow

Closed-loop: measure → predict → decide → actuate → measure.

### 1.4 Interfaces

- Sensor I/O (per-segment pressure + flow)
- Actuator drive (per-segment variable orifice)
- Alert/notification system (to external clinician)

## 2. Hydraulic architecture

The shunt is modeled as N parallel drainage segments, each with variable conductance G_i(t):

```
Q_total = sum(Q_i) = sum(G_i(t) * (P_ICP - P_distal))
P_ICP = Q_production / sum(G_active(t))
```

Where:
- Q_total = total CSF drainage rate
- Q_i = drainage rate through segment i
- G_i(t) = conductance of segment i at time t (declines with obstruction)
- P_ICP = intracranial pressure
- P_distal = distal pressure (typically 0 mmHg for ventriculoperitoneal shunt)
- Q_production = CSF production rate (~0.3 mL/min adult)

### 2.1 Default configuration (R277 simulator)

- N = 4 segments
- Q_production = 0.30 mL/min
- P_TARGET = 12 mmHg
- P_MIN = 5 mmHg
- P_MAX = 20 mmHg
- F_MAX_PER_SEG = 0.30 mL/min
- k_occl = 1/hr (obstruction rate)
- Lesion onset: 2-18h after start

## 3. Control law

### 3.1 Bayesian occlusion probability

For each segment i, maintain a posterior probability P(occluded_i | observations):

```
P(occluded_i | obs) ∝ P(obs | occluded_i) * P(occluded_i)
```

Observations: per-segment flow decline, pressure differential change.

### 3.2 Redistribution policy

When occlusion probability for segment i exceeds threshold:
1. Reduce commanded flow on segment i (preserve INV-2)
2. Increase commanded flow on healthy segments (preserve INV-1)
3. If redistribution insufficient, isolate segment i (set G_commanded_i = floor)

### 3.3 The dual invariant

The control law maintains:
- INV-1: P_MIN ≤ P_ICP ≤ P_MAX (global ICP band)
- INV-2: Q_i ≤ F_MAX_PER_SEG for all active i (no path overload)

**R277 finding:** Strict INV-1 (P_ICP ≤ 20) FAILS at peak ~22 mmHg under multi-segment progressive failure. The system enters "graceful degradation" state where INV-2 is preserved but INV-1 is violated by ~2 mmHg for several hours.

## 4. Reference implementation

`TTP_PACKAGES/P-01_PROTOTYPE/05_simulator.py` — Python simulator, ~650 lines, no external dependencies. Runs 25 scenarios (5 scenarios × 5 seeds) in <60 seconds.

### 4.1 Reproducibility

- 5-seed preregistration (R282): PASS
- 225 ablations + 180 comparisons (R288): rate-limiting confirmed as critical mechanism in 41/45 runs
- Sensor-dropout weakness fixed in V2.1 (R283)

## 5. Engineering specification summary

| Component | Specification | Status |
|-----------|---------------|--------|
| Pressure sensors | 0-50 mmHg range, ±0.5 mmHg accuracy | EXTERNAL_SOURCE (commercial: Codman MicroSensor) |
| Flow sensors | 0-1 mL/min range, ±0.05 mL/min accuracy | BLOCKING UNKNOWN (no chronic implantable CSF flow sensor exists commercially) |
| Actuators | Variable orifice, 0-100% open, <1s response | HYPOTHESIS (miniaturized variable orifice needs development) |
| Electronics | ARM Cortex-M0+ class, <1mW | EXTERNAL_SOURCE |
| Software | Bayesian occlusion prediction + INV-2-cap redistribution | MODELLED (Python reference complete; C port required for implantable) |

See `technology/engineering_spec.md` for full specification.

## 6. Provenance

- Source artifacts: `TTP_PACKAGES/P-01_PROTOTYPE/01_hydraulic_architecture.json`, `02_component_specification.json`, `03_sensor_specification.json`, `04_control_algorithm.json`
- Reference implementation: `TTP_PACKAGES/P-01_PROTOTYPE/05_simulator.py`
