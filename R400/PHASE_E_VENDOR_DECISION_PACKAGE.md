# R400 Phase E — Vendor Decision Package (DECISION PENDING CEO ACTION)

**Status (Art. XXXVIII):** NOTHING in this package claims a booked
experiment, a signed contract, or that reality happened. This is the
R400-D consolidation: the ONE decision the CEO owns, the complete
record fields for each candidate track, and the ready-to-send quote
request. The frozen protocol is `R396/PHASE_E_EXPERIMENT_PROTOCOL.md`
(§1–§7, unchanged); the R399 booking record
(`R399/PHASE_E_BOOKING_RECORD.md`) remains the prior PROPOSED state.

**The one decision:** confirm the vendor track —
**(A) accredited CRO** (Nelson Labs Leuven primary; BDC Labs / Vivitro
Labs alternates) or **(B) fast-path university fluids/BME lab** —
and authorize the quote round. Everything else is frozen and
machine-ready.

---

## 1. Why this is the critical-path item (R400-D)

The R400 directive elevates the first real experiment to
critical-path. The booking record is not equivalent to a measurement:
until a vendor signs, the machine has zero Article XXXVIII
PHYSICAL_OBSERVATION events, zero REAL_LOOP_VERIFIED packages, and the
P-07 physics chain (validated end-to-end in R400-C above) rests
entirely on MODEL_DERIVED inputs. The causal chain the machine will
execute the day data arrives — PREDICTION → MEASUREMENT → ERROR →
PARAMETER UPDATE → NEW PREDICTION → HELD-OUT MEASUREMENT — is
implemented (reality_calibration.py, the R370G one-door ledger, the
REALITY_EVENT schema) and rehearsed (R390 NIST water-viscosity event,
CONTROLLED_REHEARSAL class). No synthetic measurement can satisfy
this gate; the gate is open exactly once a vendor is chosen.

## 2. The vendor decision — candidate tracks, complete R400-D fields

### Track A (primary recommendation): Nelson Labs — Leuven, Belgium

| R400-D field | Value |
|---|---|
| **vendor** | Nelson Labs Europe (Leuven, BE) — medical-device testing; ISO/IEC 17025 + ISO 13485 environment; catheter performance testing catalog (nelsonlabs.com/locations/nelson-labs-europe) |
| **facility** | Nelson Labs Europe BV, Leuven site — accredited physical-test laboratory (facility identity + accreditation scope to be attached to the quote response) |
| **protocol** | FROZEN: R396/PHASE_E_EXPERIMENT_PROTOCOL.md §2–§7 — specimens, apparatus, matrix, uncertainty, acceptance, non-goals (executed UNCHANGED per the §1 selection rule) |
| **operator** | the vendor's named operator per measurement (recorded in the custody chain at acquisition time; the quote requires the operator be identified per run) |
| **specimen identity** | candidate multi-lumen extruded medical-grade polymer (Pebax/silicone class per P-07 materials basis), n=6 + hold-out 3; metrologized (optical microscopy 3-position lumen diameters, length, mass) BEFORE test |
| **geometry** | candidate: primary 1.0 mm + floor 0.6 mm, 90 mm active (P-07 reference envelope, per-specimen ±extrusion tolerance measured); baseline: single-lumen 1.0 mm, 90 mm, n=4 + hold-out 2 (different lot / blinded) |
| **instrument** | per §3: differential pressure transducer 0–20 mmHg (cert current, ≤0.1 mmHg resolution), gravimetric balance + timed collection (SI-traceable, ≤1% combined), temperature probe 310.15 K ±0.5 K, calibrated obstruction fixture (50%/90% primary-lumen area reduction, floor lumen untouched); instrument serials + calibration records per measurement (Art. XXXVIII) |
| **measurement variables** | pressure-flow curves per coupon + the four failure-mode scenarios (NORMAL / PARTIAL / SEVERE / ALTERNATIVE_PATH), ΔP setpoints 2/4/8/12 mmHg (NORMAL) and 4/8/12 mmHg (obstruction), 3 replicates per point, randomized order, 60 s steady-state criterion |
| **pressure/flow conditions** | ΔP 0–20 mmHg transducer class; the P-07 operating band 0.001–0.2 mL/min flow resolution requirement |
| **uncertainty** | GUM budget per §5: instrument Type B (certificates) + Type A (replicate SD); positive-control reference capillary must reproduce within its own uncertainty BEFORE coupon data counts |
| **acceptance thresholds** | held-out median relative error ≤ ±20% (NORMAL) / ≤ ±30% (obstruction) — the P-07 package's own declared tolerances (Art. XXVII provenance); failure-mode reality check: candidate ALTERNATIVE_PATH flow > 0, baseline ≈ 0 |
| **custody/provenance** | Art. XXXVIII REALITY_EVENT schema: organization, operator, acquisition timestamps, instrument identity + serial + calibration record, custody chain steps, raw CSV + per-reading metadata, raw-data sha256, acquisition attestation — delivered by the vendor (a vendor that cannot meet this is EXCLUDED regardless of price, frozen §1 rule) |
| **planned measurement date** | PROPOSED 2026-09-16 target week (re-baselined below) |
| **commercial basis** | Nelson Labs pricing policy: studies > $5,000 may require 50% prepayment (nelsonlabs.com/general-pricing-and-fee-policies); formal quote required, typ. €10³–10⁴ class |

### Track A alternates (same record structure, frozen §1 table)

- **BDC Labs** (Boulder, US) — catheter testing services
  (bdclabs.com/testing-services/catheter-testing); US-timezone
  alternative.
- **Vivitro Labs** (Vancouver, CA) — cardiovascular device flow-loop
  characterization (vivitrolabs.com/services/catheters-and-delivery-sys…).
- **Tentamus** (DE/network) — EN ISO 11070 flow characterization of
  catheters (tentamus.com/lab-analyses/mechanical-testing) — the
  closest standard-method capability match found in the vendor
  research.

### Track B (fast path): university fluids/BME lab

Same record fields; capability basis = standard bench apparatus (§3
requirements are ordinary lab equipment); cost order €10²–10³;
days-not-weeks; direct instrument access; requires a collaboration
agreement; custody paperwork is weaker than the accredited CRO chain
(mitigated by the Art. XXXVIII per-measurement metadata requirement,
which the selection rule enforces on BOTH tracks).

**Method-precedent (both tracks):** Fricker et al. 2007, "Pressure
drop through generic lumens of hemodialysis catheters" (PubMed
17667226) — the air-based rapid pressure-drop-vs-flow methodology for
generic lumens; the exact measurement class this protocol executes
with water at 310.15 K.

## 3. Ready-to-send quote request (CRO track, 2026-09-05)

> **Subject:** Quote request — multi-lumen catheter pressure-flow
> characterization, n=15 coupons, EN ISO 11070-class flow testing
>
> We request a quote for pressure-flow characterization of extruded
> multi-lumen polymer tubing coupons against a frozen protocol:
>
> - **Specimens:** 6 multi-lumen candidate coupons (primary 1.0 mm +
>   floor 0.6 mm, 90 mm active), 4 single-lumen baseline coupons
>   (1.0 mm, 90 mm), 5 hold-out coupons (3 candidate + 2 baseline,
>   different lot/blinded). Pre-test metrology: optical lumen
>   diameters (3 positions), length, mass.
> - **Conditions:** DI water at 310.15 K ± 0.5 K; differential
>   pressure 0–20 mmHg (resolution ≤ 0.1 mmHg, current calibration
>   certificate); gravimetric flow measurement (balance + timed
>   collection) or calibrated flow meter for 0.001–0.2 mL/min.
> - **Matrix:** 4 obstruction states (unobstructed; primary-lumen 50%,
>   90%, 100% area reduction by calibrated fixture, floor lumen
>   untouched) × ΔP setpoints (2/4/8/12 mmHg unobstructed;
>   4/8/12 mmHg obstructed) × 3 replicates, randomized order, 60 s
>   steady-state criterion.
> - **Deliverables:** raw CSV per reading (timestamp, ΔP, flow,
>   temperature, coupon id, obstruction state, operator, instrument
>   serials) + per-measurement instrument identity and calibration
>   records + named operator + acquisition timestamps + custody chain
>   documentation. A reference capillary positive control is run
>   first. Quotes that cannot deliver the per-measurement metadata
>   cannot be accepted.
> - **Timeline:** execution target week 2026-09-16; raw data
>   delivery within 48 h of execution.

## 4. Re-baselined timeline (honest, from today)

| Milestone | Was (R399 PROPOSED) | Now |
|---|---|---|
| Quote requests out | 2026-09-05 | **2026-09-05 — HOLDABLE if the CEO confirms the track today/tomorrow** |
| Vendor decision frozen | 2026-09-09 | 2026-09-09 |
| Experiment execution | 2026-09-16 | 2026-09-16 (target week) |
| Raw data ingested | 2026-09-18 | 2026-09-18 (one-door ledger) |

If the track confirmation slips past 2026-09-07, the execution date
moves a week and the R400-D gate stays OPEN — recorded, not
explained away.

## 5. What the machine does the day data arrives (already built)

`ingest` (R370G one-door ledger) → REALITY_EVENT validation
(instrument identity, calibration, custody, attestation, sha256) →
evidence classification → deterministic parameter update
(reality_calibration.py — the code path validated on the R390 NIST
event) → redesigned prediction → held-out retest → REAL_LOOP_VERIFIED
derived mechanically from the completed causal chain. No manual
parameter edits, no manual state assignment (Art. XXXVIII).
