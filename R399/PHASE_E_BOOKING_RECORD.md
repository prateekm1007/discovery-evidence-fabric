# R399 Phase E — Experiment Booking Record (PROPOSED, PENDING CEO CONFIRMATION)

**Status (Art. XXXVIII):** NOTHING in this record claims a booked
experiment or that reality happened. This record consolidates the nine
fields the R399 directive requires THIS WEEK — every value is PROPOSED
and awaits the CEO's vendor confirmation, which is the one action this
record cannot take itself. The frozen protocol is
`R396/PHASE_E_EXPERIMENT_PROTOCOL.md` (§1–§7); this record references
it section-by-section rather than duplicating it.

| Field | Value | Basis |
|---|---|---|
| **Lab / vendor** | PROPOSED, dual-track: (fast) a university fluids/BME lab with a calibrated pressure-flow bench; (CRO) Nelson Labs (Leuven) — primary CRO candidate; alternates Vivitro Labs (Vancouver), BDC Labs (Boulder) | protocol §1 capability table + the frozen selection rule (execute §2–§6 unchanged; per-measurement instrument identity + calibration + custody chain per the Art. XXXVIII REALITY_EVENT schema; raw CSV + per-reading metadata) |
| **Owner** | PROPOSED: CEO (vendor confirmation + contract); execution day-to-day: the selected vendor's named operator (recorded per measurement in the custody chain); engine-side ingestion owner: the R370G one-door ledger (no manual file drops) | the custody chain requires a named operator per measurement; the engine-side path is already implemented |
| **Protocol** | FROZEN: R396/PHASE_E_EXPERIMENT_PROTOCOL.md §2–§7 (specimens, apparatus, measurement matrix, uncertainty budget, acceptance, non-goals) | frozen 2026-09-02; unchanged by R399 |
| **Pressure ranges** | ΔP setpoints 0–20 mmHg (transducer class, ±0.1 mmHg resolution); setpoint matrix per protocol §4 | protocol §3–§4 |
| **Geometries** | Candidate: multi-lumen extruded medical-grade polymer, primary 1.0 mm + floor 0.6 mm (the P-07 reference envelope), 90 mm active, n=6; Baseline: single-lumen 1.0 mm, 90 mm, n=4; Hold-out: 3 candidate + 2 baseline from a different extrusion lot | protocol §2 |
| **Measurement variables** | pressure-flow curves per coupon + the four failure-mode scenarios (NORMAL / PARTIAL / SEVERE / ALTERNATIVE_PATH obstruction states), temperature-controlled (±0.5 K, declared V0 fluid class) | protocol §4 |
| **Uncertainty** | GUM budget per protocol §5 (transducer certificate, balance, temperature; drift checks at 0 and full scale; a control coupon must reproduce within its own uncertainty before candidate data counts) | protocol §5 |
| **Acceptance threshold** | prediction-vs-measurement median relative error ≤ ±20% (NORMAL) / ≤ ±30% (obstruction) — the P-07 package's own declared tolerances (Art. XXVII threshold provenance); the invention's reason-to-exist: floor flow under full primary obstruction > 0 for every candidate coupon | protocol §6 |
| **Experiment date** | PROPOSED: 2026-09-16 (target week); 2026-09-05 quotes out; 2026-09-09 vendor frozen; 2026-09-18 raw data ingested | protocol §1 target dates |

**The decision the CEO owns:** confirm the vendor track (fast-path
university vs. CRO) — everything else is frozen and machine-ready.

**What the machine does the day data arrives:** prediction → measurement
→ discrepancy → deterministic parameter update (reality_calibration.py,
the R390-validated code path) → redesigned prediction → held-out
retest, with REAL_LOOP_VERIFIED derived mechanically from the ledgers —
never assigned.
