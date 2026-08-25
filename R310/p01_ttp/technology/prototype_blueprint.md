# Prototype Blueprint — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C03
**Status:** V0 bench prototype FROZEN_FOR_BENCH_BUILD; V1 implantable BLOCKED on flow sensor

---

## 1. V0 bench prototype

### 1.1 Purpose
Reproduce simulator findings on real hardware. Validate that the control law works outside of pure simulation. Establish the falsification path before committing to V1 implantable development.

### 1.2 Bill of materials

| Component | Specification | Source | Est. cost |
|-----------|---------------|--------|-----------|
| Manifold | Acrylic, 4-segment, variable orifice per segment | Custom machine shop | $500 |
| Flow sensors (4x) | 0-5 mL/min, ±0.05 mL/min | COTS (Sensirion SLF3S-1300F) | $400 |
| Pinch valves (4x) | Solenoid, 0-100% PWM control | COTS (Takasago PK series) | $800 |
| Pressure sensor (1x) | 0-50 mmHg, ±0.5 mmHg | COTS (Honeywell 26PC) | $200 |
| Peristaltic pump | Mimics CSF production, 0.3 mL/min | COTS | $300 |
| Controller | Raspberry Pi 4 or Arduino Due | COTS | $100 |
| Tubing, fittings, reservoir | Silicone, luer locks, 500 mL reservoir | COTS | $200 |
| **Total** | | | **~$3-5K** |

### 1.3 Build time
3-6 months (1 engineer + 1 technician).

### 1.4 Test program
- 6 scenarios × 5 seeds = 30 runs
- 24 hours per run
- 720 bench-hours total
- See `transfer/buyer_protocol.md` for test fixtures

## 2. V1 implantable prototype

### 2.1 Purpose
First chronic implantable unit for pre-clinical animal studies.

### 2.2 Key differences from V0
- MEMS variable-orifice valves (not COTS solenoid pinch valves)
- Codman MicroSensor (not COTS Honeywell)
- Custom implantable flow sensor (NO COMMERCIAL OPTION — biggest engineering risk)
- Hermetic titanium electronics package
- Saft LM-175 battery
- MICS RF telemetry

### 2.3 Estimated cost and timeline
- Cost: $200-500K
- Timeline: 12-18 months
- Critical path: custom flow sensor development

### 2.4 The blocking unknown
No chronic implantable CSF flow sensor exists commercially. Three options:
- (a) Custom ultrasonic flow sensor (12-18 month development, $100-200K)
- (b) Infer flow from pressure differential across known resistance (lower accuracy, no custom hardware, but loses observability)
- (c) Eliminate per-segment flow sensing; rely on global ICP + actuator position (cheapest, but loses the per-segment observability that makes the predictive control law work)

**Recommendation:** Build V0 with COTS flow sensors first. Use V0 results to decide whether per-segment flow observability is essential (option a) or whether inference (option b) is sufficient.

## 3. Path to market

| Phase | Duration | Cost |
|-------|----------|------|
| V0 bench prototype | 3-6 months | $3-5K |
| V1 implantable prototype | 12-18 months | $200-500K |
| V2 pre-clinical (animal) | 12-24 months | $1-2M |
| Clinical trial + PMA | 4-8 years | $20-50M |
| **Total to market** | **5-10 years** | **$22-53M** |

## 4. What to build first

**V0 bench prototype.** Reproduce simulator findings on hardware. Specifically:
1. Confirm that multi-segment peak ICP is lower than single-segment baseline (simulator: 22 vs 59 mmHg)
2. Confirm that INV-2 is preserved in multi-segment but not in single-segment under progressive failure
3. Confirm that 24h survival FAILS in both designs (simulator finding) — establish that the simulator is honest
4. Test the hostile attack matrix (see `evidence/attacks/`)

Only after V0 confirms the simulator should V1 implantable development begin.

## 5. Provenance

- Source: `TTP_PACKAGES/P-01_PROTOTYPE/06_bench_prototype_design.json`, `07_test_fixtures.json`
