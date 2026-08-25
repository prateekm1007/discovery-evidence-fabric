# Engineering Specification — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C02
**Status:** MODELLED with one BLOCKING UNKNOWN (implantable CSF flow sensor)

---

## 1. Sensors

### 1.1 Pressure sensors
- **Range:** 0-50 mmHg
- **Accuracy:** ±0.5 mmHg
- **Commercial source:** Codman MicroSensor, Integra MicroSensor
- **Status:** EXTERNAL_SOURCE — these sensors are FDA-cleared for chronic ICP monitoring
- **Integration:** 1x global ICP sensor (intraventricular or subdural); optionally 1x per-segment distal pressure sensor

### 1.2 Flow sensors (BLOCKING UNKNOWN)
- **Range:** 0-1 mL/min per segment
- **Accuracy:** ±0.05 mL/min
- **Commercial source:** NONE for chronic implantable CSF flow measurement
- **Status:** BLOCKING UNKNOWN
- **Options under consideration:**
  - (a) Custom ultrasonic flow sensor (transit-time or Doppler) — 12-18 month development
  - (b) Infer flow from pressure differential across known resistance — lower accuracy, no custom hardware
  - (c) Eliminate per-segment flow sensing; rely on global ICP + actuator position — loses observability

## 2. Actuators

### 2.1 Variable orifice per segment
- **Range:** 0-100% open
- **Response time:** < 1 second
- **Status:** HYPOTHESIS — miniaturized variable orifice for chronic implantation needs development
- **Candidate mechanisms:**
  - MEMS electrothermal valve
  - Piezoelectric pinch valve
  - Electromagnetic solenoid (likely too power-hungry)
- **Power budget:** < 1 mW average (valve holds position with no power; only consumes power during transition)

## 3. Electronics

### 3.1 Microcontroller
- **Class:** ARM Cortex-M0+ or equivalent ultra-low-power
- **Power:** < 1 mW average
- **Status:** EXTERNAL_SOURCE

### 3.2 Power
- **Battery:** Saft LM-175 lithium thionyl chloride cell (5+ year life at < 1 mW average)
- **Status:** EXTERNAL_SOURCE

### 3.3 Communication
- **Telemetry:** MICS band (Medical Implant Communication Service, 402-405 MHz)
- **Status:** EXTERNAL_SOURCE

## 4. Software

### 4.1 Algorithm
- **Bayesian occlusion prediction:** per-segment posterior probability updated each sensor cycle
- **Redistribution policy:** proportional control with INV-2 cap
- **Status:** MODELLED — Python reference implementation complete (`05_simulator.py`); C port required for implantable

### 4.2 Verification
- 225 ablation runs (R288): rate-limiting confirmed as critical mechanism in 41/45 runs
- 5-seed preregistration (R282): PASS
- Sensor-dropout weakness fixed in V2.1 (R283)

## 5. Operating envelope

| Parameter | Value |
|-----------|-------|
| ICP range | 5-40 mmHg |
| Flow per segment | 0.1-0.5 mL/min |
| CSF temperature | 37°C |
| Implant duration | > 5 years (chronic) |
| Number of segments | 4 (default; configurable 2-8) |

## 6. Materials

- Catheter: medical-grade silicone (existing shunt material)
- Variable orifice: TBD (depends on actuator choice — see §2.1)
- Electronics housing: hermetic titanium (existing implantable packaging)
- Sensors: per §1

## 7. Manufacturing

- V0 bench prototype: $3-5K, 3-6 months (COTS components + acrylic manifold)
- V1 implantable prototype: $200-500K, 12-18 months (custom MEMS actuators + custom flow sensor + hermetic packaging)
- V2 pre-clinical: $1-2M, 12-24 months
- Clinical trial + PMA: $20-50M, 4-8 years

## 8. The blocking unknown (Article XXXIV — reality is the next bottleneck)

The implantable CSF flow sensor is the single largest engineering risk. Without it, the controller cannot observe per-segment flow and must rely on inferred estimates (less accurate, slower occlusion detection).

**Path forward:** Build V0 bench prototype with COTS flow sensors. Reproduce simulator findings on hardware. Then decide V1 implantable flow sensor path (custom ultrasonic vs. inference-only).

## 9. Provenance

- Source: `TTP_PACKAGES/P-01_PROTOTYPE/02_component_specification.json`, `03_sensor_specification.json`
