# P-16 Independent Verification Protocol — R309

**Candidate:** P-16 NIR Photovoltaic (940nm)
**Authority:** Article XXXVI §6 (Standard simulator registry), §7 (Independent verification), §8 (Economics must use verified number)
**Phase:** B
**Status:** R308 reported 744 μW PASS, but internal model disagreement (diffusion approximation vs. Kubelka–Munk differ 60–70%) means the verification has NOT happened yet.

---

## 1. Why this protocol exists

R308 closed P-16 as BUYER_TESTABLE based on an internal model using the **diffusion approximation**. The R308 audit found:

- Diffusion approximation: predicts ~744 μW at the PV cell
- Kubelka–Munk: predicts ~250–300 μW (60–70% lower)
- Both are **internal approximations** — neither is independent verification (Article XXVI: no self-certification)
- The attractive number (744 μW) cannot be the headline claim without independent confirmation

This protocol resolves the disagreement using **MCX** (Monte Carlo gold standard for tissue optics) and **PyTissueOptics** (independent Python implementation), compared to **published 940nm tissue-transmission measurements** (Jacques 2013 or equivalent).

The CEO directive is explicit:

> Use **MCX** as the Monte Carlo tiebreaker and **PyTissueOptics** as an independent implementation. Then compare to published measurements. Do not choose the attractive result.

---

## 2. The reference case

**Published reference:** Jacques SL, "Optical properties of biological tissues: a review," *Phys Med Biol* 58:R37–R61 (2013). Equivalent published 940nm tissue-transmission measurements acceptable.

**Phantom geometry:**
- Tissue slab thickness: 5 mm (representative of scalp + skull + dura distance to implanted PV cell)
- Source: 940 nm point source, 1 mW total power, isotropic emission at tissue surface
- Detector: PV cell at 5 mm depth, 1 cm² active area, directly below source
- Tissue optical properties at 940 nm (from Jacques 2013, brain tissue surrogate):
  - μa (absorption coefficient): 0.05 cm⁻¹
  - μs (scattering coefficient): 8.0 cm⁻¹
  - g (anisotropy): 0.9
  - n (refractive index): 1.4

**Metric:** Fluence at detector position (mW/cm²)

---

## 3. Preregistration (must be timestamped BEFORE any MCX run)

```json
{
  "verification_id": "P-16-VERIF-001",
  "candidate_id": "P-16",
  "preregistration_timestamp": "<MUST be recorded before MCX run>",
  "preregistration_author": "autonomous_ai_loop_v4",
  "engine_primary": "SIM_MCX",
  "engine_secondary": "SIM_PYTISSOPT",
  "reference_case": "Jacques 2013, 940nm, 5mm tissue phantom",
  "reference_case_citation": "Jacques SL, Phys Med Biol 58:R37-R61 (2013)",
  "phantom_geometry": {
    "tissue_thickness_mm": 5,
    "source_wavelength_nm": 940,
    "source_power_mW": 1,
    "detector_area_cm2": 1,
    "tissue_optical_properties": {
      "mu_a_per_cm": 0.05,
      "mu_s_per_cm": 8.0,
      "g": 0.9,
      "n": 1.4
    }
  },
  "metric": "fluence_at_detector_mW_per_cm2",
  "frozen_tolerance_relative": 0.10,
  "frozen_tolerance_absolute": "0.05 mW/cm^2",
  "constitutional_basis": "Article XXXVI §6, §7; Article VIII (certification must attack itself)",
  "tolerance_may_not_be_widened_after_run": true,
  "anti_pattern_forbidden": "Choosing the attractive 744 μW result if MCX/published measurement disagrees. Article XV (must disclose inconvenient results); Article XXVIII (no silent semantic promotion)."
}
```

---

## 4. The four-model comparison

Run four independent computations on the **same** reference case:

| # | Model                          | Implementation                                  | Output                                  |
|---|--------------------------------|-------------------------------------------------|-----------------------------------------|
| 1 | Our internal (diffusion approx)| P-16 reference implementation                   | `our_output.json`                       |
| 2 | MCX (Monte Carlo gold standard)| MCX from `https://github.com/fangq/mcx`         | `mcx_output.json`                       |
| 3 | PyTissueOptics (independent)   | PyTissueOptics from `github.com/DCC-Lab/PyTissueOptics` | `pytissopt_output.json`         |
| 4 | Published measurement          | Jacques 2013 (or equivalent)                    | `published_reference.json`              |

All four outputs are stored as raw artifacts under `evidence/independent_verification/`.

---

## 5. Verdict logic

```
ALL FOUR agree within tolerance (10% relative, 0.05 mW/cm² absolute)
  → MODEL_VERIFIED
  → P-16's headline power claim = the verified number (NOT necessarily 744 μW)
  → P-16 may progress to TECHNOLOGY_TRANSFER_READY

OUR DIFFUSION APPROXIMATION disagrees with MCX + PyTissueOptics + published
  (likely outcome, given R308 60-70% disagreement)
  → MODEL_DISAGREEMENT
  → Root cause analysis (Section 6)
  → Repair: upgrade our model from diffusion approximation to Monte Carlo (use MCX output as our model)
  → Re-preregister with new model
  → Re-verify
  → If re-verification passes, P-16 progresses with the LOWER (verified) number

MCX DISAGREES with PyTissueOptics + published
  → MCX bug or PyTissueOptics bug
  → Diff MCX and PyTissueOptics implementations
  → Fix the bug, re-run both
  → Re-verify

MCX + PyTissueOptics AGREE but BOTH disagree with published measurement
  → Phantom mismatch (optical properties, geometry, or source spectrum)
  → Align phantom parameters
  → Re-run all four
  → Re-verify
```

---

## 6. Root cause analysis (if MODEL_DISAGREEMENT)

The most likely outcome is that our diffusion approximation disagrees with MCX/PyTissueOptics/published. The diagnosis is:

**Root cause:** Diffusion approximation is valid only when:
1. Source is far from detector (≫ 1 mean free path), AND
2. Scattering ≫ absorption (μs ≫ μa)

At 940 nm in 5 mm tissue:
- Source-to-detector distance (5 mm) is comparable to transport mean free path (~1.4 mm), violating condition 1.
- μs/μa = 160, satisfying condition 2.

The first condition is violated, so the diffusion approximation overestimates fluence near the source. This explains the 60–70% disagreement: the diffusion approximation predicts too much light reaches the detector.

**Resolution:** Replace the diffusion approximation in P-16's reference implementation with MCX Monte Carlo (or a pre-computed MCX lookup table for the relevant optical property range). Re-preregister with the Monte Carlo model as "our implementation." Re-verify against PyTissueOptics + published measurement.

If re-verification passes, P-16's headline power claim becomes the Monte Carlo number (~250–300 μW if the diffusion approximation was indeed overestimating, or whatever MCX actually predicts).

---

## 7. Economic implications

The verified power output drives the economic model:

| Scenario                                  | Headline power | Economic claim            | Article XXXVI §8 status      |
|-------------------------------------------|---------------:|---------------------------|------------------------------|
| Diffusion approximation (R308, unverified)| 744 μW         | Strongest case            | FORBIDDEN as headline        |
| MCX-verified (likely lower)               | ~300 μW        | Realistic case            | MODELLED → PUBLICLY_VERIFIED |
| MCX + published measurement agree         | verified value | Verified case             | PUBLICLY_VERIFIED            |

**The economic claim must use the verified number.** Article XXXVI §8: "A package may not enter TECHNOLOGY_TRANSFER_READY if its central value claim is MODELLED only and no path to PUBLICLY_VERIFIED exists."

The path from MODELLED to PUBLICLY_VERIFIED for P-16 is:
1. Run MCX → MODELLED (our model output, matched to Monte Carlo)
2. Match MCX to PyTissueOptics → cross-verified MODELLED
3. Match both to published 940nm tissue-transmission measurement → PUBLICLY_VERIFIED

This is the documented upgrade path. P-16 may enter TECHNOLOGY_TRANSFER_READY when step 3 completes.

---

## 8. Anti-patterns (forbidden)

1. **Choosing the attractive result.** If diffusion approximation gives 744 μW but MCX gives 300 μW, the answer is 300 μW. Choosing 744 μW because it is more attractive violates Article XV (must disclose inconvenient results) and Article XXVIII (no silent semantic promotion).

2. **Widening the tolerance after the run.** Article VIII: certification must attack itself. The 10% relative / 0.05 mW/cm² absolute tolerance is frozen at preregistration. If the comparison fails, the answer is MODEL_DISAGREEMENT, not "let's relax the tolerance."

3. **Skipping the published measurement comparison.** Running MCX alone is not sufficient. MCX itself must be validated against something we did not write (Article XXVI). The published 940nm tissue-transmission measurement is the ground truth.

4. **Treating MCX as infallible.** MCX can have bugs. The PyTissueOptics cross-check exists precisely to catch MCX bugs. If MCX and PyTissueOptics disagree, both must be examined.

5. **Filing P-16 as TECHNOLOGY_TRANSFER_READY without resolving the disagreement.** The MODEL_DISAGREEMENT state blocks progression (Article XXXVI §7). The block is not lifted until root cause is diagnosed and the model is re-verified.

---

## 9. What this protocol demonstrates

P-16 is the canonical case for the entire Article XXXVI §6/§7 framework. If this protocol works:

- The standard simulator registry has teeth.
- Independent verification means something other than "we ran our own model again."
- The attractive-result anti-pattern is enforceable.
- The economic model can be tied to a verified physical number, not an internal approximation.

If this protocol fails (e.g., we cannot get MCX to run, or we cannot find a published reference), the framework itself needs review. P-16 is the test case.

---

## 10. Execution checklist

- [ ] Preregistration timestamped BEFORE any MCX run
- [ ] MCX installed from `https://github.com/fangq/mcx`, version pinned
- [ ] PyTissueOptics installed from `github.com/DCC-Lab/PyTissueOptics`, version pinned
- [ ] Published 940nm tissue-transmission reference identified (Jacques 2013 or equivalent)
- [ ] Phantom geometry, optical properties, source spectrum frozen in preregistration
- [ ] Tolerance frozen (10% relative, 0.05 mW/cm² absolute)
- [ ] Run our diffusion approximation model on reference case → `our_output.json`
- [ ] Run MCX on reference case → `mcx_output.json`
- [ ] Run PyTissueOptics on reference case → `pytissopt_output.json`
- [ ] Extract published measurement value → `published_reference.json`
- [ ] Compute pairwise differences
- [ ] Render verdict (MODEL_VERIFIED or MODEL_DISAGREEMENT)
- [ ] If MODEL_DISAGREEMENT: run Section 6 root cause analysis
- [ ] If repair needed: upgrade model to Monte Carlo, re-preregister, re-verify
- [ ] Update P-16 manifest.json with verified power output
- [ ] Update P-16 economic model with verified number (PUBLICLY_VERIFIED tier)
- [ ] Append verification entry to `R309/verification/VERIFICATION_LEDGER.jsonl`
- [ ] CEO test for P-16: could a competent engineering team take this folder and reproduce the verified number? Until yes, P-16 is not TECHNOLOGY_TRANSFER_READY.
