# Phase E — The First Physical Loop: Multi-Lumen Flow Rig Experiment

**Status:** PROTOCOL FROZEN (R396 Phase E, 2026-09-02). Booking pending
CEO confirmation of the execution vendor — a PROPOSED date and owner are
recorded below and in the worklog; nothing here claims a booked
experiment (Art. XXXVIII: AI may not claim that reality happened).

**Purpose.** Close the first REAL loop of the machine:
prediction -> physical measurement -> discrepancy -> parameter/model
update -> redesigned prediction -> HELD-OUT measurement. NIST/reference
data (the R390 water-viscosity event) is calibration-INPUT class, never
physical validation of the DEVICE (R396 Phase E, first paragraph).

**Reference case.** P-07 (portfolio 04_drainage_floor): the multi-lumen
drainage catheter whose floor path maintains drainage when the primary
lumen obstructs. The physics core V0 already predicts the four
failure-mode scenarios (NORMAL / PARTIAL / SEVERE / ALTERNATIVE_PATH —
R396/P07_FAILURE_MODE_CONTRACT.json). The experiment measures the REAL
pressure-flow behavior of extruded coupons of the same envelope.

---

## 1. Laboratory / vendor selection

Dual-track (fast academic path + accredited CRO path), selected on
measured capability against the protocol requirements (§3):

| Track | Candidate | Capability basis | Why |
|---|---|---|---|
| Fast path | University fluids / BME lab with a calibrated pressure-flow bench (bench + differential transducer + analytical balance + temperature control) | protocol requirements §3 are standard bench apparatus | lowest cost (order €10²–10³), direct instrument access, days not weeks; collaboration agreement required |
| CRO path | Nelson Labs (Leuven, BE) — medical-device testing, ISO/IEC 17025 + ISO 13485 environment, catheter performance testing | nelsonlabs.com catalog | accredited chain-of-custody + attestation paperwork ready for buyer dossiers; formal quote required (typ. €10³–10⁴ class) |
| CRO path (alt) | Vivitro Labs (Vancouver, CA) — cardiovascular device flow-loop characterization | vivitrolabs.com catalog | published pressure-flow characterization expertise |
| CRO path (alt) | BDC Labs (Boulder, US) — catheter testing | bdclabs.com catalog | US timezone alternative |

**Selection rule (frozen):** the vendor must (a) execute §2–§6
unchanged, (b) provide instrument identity + calibration records per
measurement (the Art. XXXVIII REALITY_EVENT schema: instrument serial,
calibration record, operator, organization, timestamps, raw data
sha256), (c) deliver raw data as CSV/time-series + per-reading
metadata. A vendor that cannot meet (b) is excluded regardless of
price.

**Owner (recorded in worklog):** CEO — decision authority and budget;
the coder prepares the protocol, the data-ingestion interface, and the
calibration update (already implemented: reality_calibration.py).

**Target dates (recorded in worklog, PROPOSED):**
- 2026-09-05 — quote requests out (CRO track) + university contact confirmed
- 2026-09-09 — vendor decision frozen
- 2026-09-16 — experiment execution (target week)
- 2026-09-18 — raw data ingested through the R370G one-door ledger

## 2. Specimens

- **Candidate coupons:** extruded medical-grade polymer (e.g. Pebax/
  silicone per P-07 materials basis) multi-lumen tubing: primary lumen
  1.0 mm + floor lumen 0.6 mm (the reference envelope; ±extrusion
  tolerance measured per specimen), 90 mm active length, n = 6.
- **Baseline coupons:** single-lumen 1.0 mm, 90 mm, n = 4.
- **Hold-out set:** 3 candidate + 2 baseline coupons from a DIFFERENT
  extrusion lot (or, if one lot only, cut and blinded by the operator,
  identified only by random codes) — never used for calibration.
- Every coupon is metrologized before testing: lumen diameters by
  optical microscopy (3 positions along the length), length, mass.

## 3. Apparatus (minimum requirements — any track)

1. Vertical/head-driven or pump-driven flow circuit, DI water, 310.15 K
   ± 0.5 K controlled and measured (the declared V0 fluid class).
2. Differential pressure transducer across the coupon, range 0–20 mmHg,
   calibration certificate current; resolution ≤ 0.1 mmHg.
3. Flow measurement: analytical balance + timed collection (gravimetric,
   recommended — direct SI traceability) or calibrated flow meter;
   resolution sufficient for 0.001–0.2 mL/min (the P-07 operating band).
4. Temperature probe at the fluid, calibration certificate current.
5. Obstruction fixture: calibrated mechanical reduction of the PRIMARY
   lumen only (precision mandrel/pin set) at 50% and 90% nominal area
   reduction, leaving the floor lumen untouched.
6. Data: continuous or per-reading CSV with timestamp, ΔP, flow,
   temperature, coupon id, obstruction state, operator, instrument
   serials.

## 4. Measurement matrix (pressure-flow + failure modes)

For each coupon (candidate AND baseline):

| Condition | ΔP setpoints (mmHg) | Replicates |
|---|---|---|
| NORMAL (unobstructed) | 2, 4, 8, 12 | 3 per setpoint |
| PARTIAL (primary 50% area reduction) | 4, 8, 12 | 3 |
| SEVERE (primary 90% area reduction) | 4, 8, 12 | 3 |
| ALTERNATIVE_PATH (primary 100% occluded) | 4, 8, 12 | 3 |

Steady state criterion: 60 s stable within instrument noise before each
reading. Order randomized within each coupon to decorrelate drift.
Hold-out coupons: the SAME matrix, executed after the calibration set,
by the same protocol.

## 5. Measured variables + uncertainty budget (per GUM)

| Variable | Instrument | Type B (instrument) | Type A (replicates) |
|---|---|---|---|
| Flow Q (mL/min) | gravimetric balance + timer (or flow meter) | balance certificate + timer resolution, combined ≤ 1% | SD of the 3 replicates per point |
| ΔP (mmHg) | differential transducer | certificate, ≤ 0.1 mmHg | drift check at 0 and full scale |
| Temperature (K) | probe | certificate, ≤ 0.1 K | — |
| Lumen diameter (mm) | optical microscope | scale calibration, ≤ 0.01 mm | 3-position SD per coupon |

The rig itself is characterized FIRST with a reference capillary of
known conductance (measured independently or certified) — a positive
control that must reproduce within its own uncertainty before any
coupon data is accepted (Art. XXXII: test the alternative explanation
"the rig is miscalibrated" BEFORE trusting device data).

## 6. Acceptance threshold + the loop closure criteria

1. **Pre-calibration prediction error:** |predicted Q − measured Q| /
   measured Q per point, using the as-shipped model (water-class
   viscosity 1.0 mPa·s, nominal geometry). Recorded, whatever it is.
2. **Calibration update:** viscosity + effective-diameter (and, if the
   data supports it, an entrance-loss correction term) updated from the
   CALIBRATION SET ONLY, through the deterministic inversion path
   (reality_calibration.py — the same code path validated on the R390
   story; no manual parameter edits).
3. **Held-out validation (the decisive number):** post-calibration
   prediction error on the HOLD-OUT set, per condition. **Acceptance:
   median relative error ≤ ±20% on NORMAL and ≤ ±30% on obstruction
   conditions**, AND the error must be LOWER than the pre-calibration
   error by a quantified margin (the R394 §14 improvement metric).
   The ±20% band is the P-07 package's own declared tolerance (Art.
   XXVII: threshold provenance = the package's engineering record, not
   an invented number); ±30% on obstruction conditions carries the
   additional uniform-stenosis-model uncertainty (disclosed limitation
   of V0).
4. **Failure-mode reality check:** the measured ALTERNATIVE_PATH flow
   must be > 0 for candidate coupons (the invention's reason-to-exist)
   and ≈ 0 for baseline coupons. If either fails, the DISCREPANCY is
   recorded and drives the model update — it is never explained away.
5. Everything enters the machine as REALITY_EVENTs through the R370G
   one-door ledger with instrument identity, calibration records,
   operator, custody chain, raw-data sha256 — the Art. XXXVIII schema.
   REAL_LOOP_VERIFIED for P-07 remains machine-derived (never manually
   assigned) from the completed causal chain.

## 7. What this experiment is NOT

- Not a clinical trial, not biocompatibility, not sterilization
  validation — it is the decisive pressure-flow physics loop only.
- Not a re-derivation of the portfolio: the buyer chain (Art. XXXIX)
  is untouched; results flow into the model-calibration machinery and
  (later, with the CEO's explicit release decision) into V-class
  mutation addenda per the existing portfolio governance.
- Not self-certified: the measurement is performed by an external
  organization on their calibrated instruments; the coder's role is
  protocol, ingestion, and honest reporting of discrepancies.
