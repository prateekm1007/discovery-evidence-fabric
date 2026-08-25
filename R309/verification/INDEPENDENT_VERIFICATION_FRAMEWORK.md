# Independent Verification Framework — R309

**Authority:** Article XXXVI §7
**Purpose:** Make "verification" mean something other than "we ran our own model again."

---

## 1. The core distinction

A second run of our own implementation is **not** independent verification (Article XXVI: no self-certification).

Independence requires one of:

1. **Different code path, same algorithm.** Reimplemented from the specification by a different author, with no shared codebase. Suitable when no standard engine exists for the mechanism class.
2. **External solver from the Standard Simulator Registry.** The same physical mechanism is solved by an established external engine (SimVascular, FEBio, COPASI, MCell, MCX, PyTissueOptics, scikit-learn). This is the **preferred** path (Article XXXVI §6).
3. **Published reference case.** The model's output is compared to a published experimental measurement, peer-reviewed benchmark, or analytical solution. The reference case must be cited with full provenance.

A candidate may combine paths (e.g., MCX + published 940nm tissue-transmission measurements for P-16), and this combination is the strongest form of verification.

---

## 2. The state machine

```
VERIFICATION_NOT_ATTEMPTED
        ↓
VERIFICATION_PREREGISTERED
        │  (engine selected, tolerance declared,
        │   reference case cited, timestamp recorded)
        ↓
VERIFICATION_RUNNING
        │  (independent solver invoked;
        │   cannot return to NOT_ATTEMPTED)
        ↓
    ┌───┴───┐
    │       │
    ▼       ▼
MODEL_VERIFIED          MODEL_DISAGREEMENT
(within tolerance,      (outside tolerance;
 raw outputs preserved)  AI investigates)
                              │
                              ▼
                    ROOT CAUSE ANALYSIS
                    (implementation bug?
                     model assumption?
                     parameter mismatch?
                     genuine physics gap?)
                              │
                              ▼
                    REPAIR (if credible)
                              │
                              ▼
                    RE-PREREGISTER
                    (new tolerance, justified)
                              │
                              ▼
                    VERIFICATION_PREREGISTERED
```

A candidate may not enter `TECHNOLOGY_TRANSFER_READY` while in `MODEL_DISAGREEMENT`.

---

## 3. Preregistration requirements

Before the comparison is run, the following must be frozen in a timestamped artifact:

```json
{
  "candidate_id": "P-16",
  "verification_id": "P-16-VERIF-001",
  "engine_id": "SIM_MCX",
  "engine_version": "MCX 2024.x",
  "engine_repo_commit": "<git SHA>",
  "reference_case": "Published NIR 940nm transmission through 5mm tissue phantom (Jacques 2013)",
  "reference_case_citation": "<full citation>",
  "metric": "fluence_at_detector_mW_per_cm2",
  "frozen_tolerance_relative": 0.10,
  "frozen_tolerance_absolute": "0.05 mW/cm^2",
  "preregistration_timestamp": "2026-08-25T14:30:00Z",
  "preregistration_author": "autonomous_ai_loop_v4",
  "constitutional_basis": "Article XXXVI §7; Article VIII (certification must attack itself)"
}
```

Tolerance may not be widened after the comparison is run (Article VIII, Article XXVIII — no silent semantic promotion).

---

## 4. The comparison

The comparison must produce:

1. **Our implementation's output** — the candidate's reference implementation, run on the reference case.
2. **Independent solver's output** — the external engine's output on the same reference case.
3. **Difference metric** — the quantitative comparison (relative and absolute).
4. **Verdict** — `MODEL_VERIFIED` if within tolerance, `MODEL_DISAGREEMENT` if outside.
5. **Raw outputs** — both runs' full output preserved (not just summary statistics).

---

## 5. Root cause analysis (on disagreement)

If `MODEL_DISAGREEMENT`, the AI must diagnose which of four causes:

| Cause | Diagnosis | Resolution |
|-------|-----------|------------|
| Implementation bug | Our code or the external engine has a bug. Diff the implementations. | Fix the bug. Re-preregister. Re-run. |
| Model assumption | Our model assumes something the external solver does not (e.g., diffusion approximation vs. full Monte Carlo). | Either justify the assumption (with published evidence) or upgrade the model. Re-preregister. Re-run. |
| Parameter mismatch | Both models are correct but parameters differ (e.g., tissue optical properties). | Align parameters. Re-preregister. Re-run. |
| Genuine physics gap | Our model and the external solver disagree because our model is wrong about the physics. | This is the most serious case. The candidate's mechanism itself is in question. Either redesign the mechanism or move to cemetery. |

The root cause analysis is preserved as an artifact. The candidate does not progress until the disagreement is resolved and the model is re-verified.

---

## 6. Worked example: P-16 (R309)

**Background (R308):** P-16 (NIR photovoltaic at 940nm) was reported PASS at 744 μW. Internal model uses diffusion approximation. R308 audit found a 60–70% disagreement between diffusion approximation and Kubelka–Munk. Both are internal approximations.

**R309 protocol:**

1. **Preregistration:** Declare tolerance (10% relative, 0.05 mW/cm² absolute) against published 940nm tissue-transmission measurements (Jacques 2013). Declare MCX as the Monte Carlo tiebreaker. Declare PyTissueOptics as the independent implementation. Timestamp before any comparison.

2. **Run our implementation:** Diffusion approximation model, predict fluence at the PV cell for the reference case (5mm tissue phantom, 940nm source).

3. **Run MCX:** Same phantom, same source. MCX is the Monte Carlo gold standard for tissue optics.

4. **Run PyTissueOptics:** Same phantom, same source. Independent Python implementation.

5. **Compare to published measurement:** Jacques 2013 (or equivalent) for 940nm, 5mm tissue.

6. **Verdict:**
   - If our implementation, MCX, PyTissueOptics, and the published measurement all agree within tolerance → `MODEL_VERIFIED`. P-16 progresses.
   - If our implementation disagrees with MCX/PyTissueOptics/published → `MODEL_DISAGREEMENT`. Root cause analysis. If diffusion approximation is the cause (likely), either justify it (with published evidence of when diffusion is valid) or upgrade the model to Monte Carlo. Re-preregister. Re-run.

7. **Do NOT choose the attractive result.** If the diffusion approximation gives a flattering 744 μW but MCX gives 300 μW, the answer is 300 μW (or whatever the published measurement supports). P-16's final economic claim must use the verified number, not the attractive number.

---

## 7. Verification ledger

Each verification is recorded in:

```
R309/verification/VERIFICATION_LEDGER.jsonl
```

Each line is one verification attempt. Append-only. Fields:

```json
{
  "verification_id": "P-16-VERIF-001",
  "candidate_id": "P-16",
  "preregistration_timestamp": "...",
  "engine_id": "SIM_MCX",
  "reference_case": "...",
  "frozen_tolerance": {...},
  "our_output": {...},
  "independent_output": {...},
  "difference": {...},
  "verdict": "MODEL_VERIFIED | MODEL_DISAGREEMENT",
  "raw_output_paths": ["...", "..."],
  "root_cause_analysis": "..." (if disagreement),
  "repair_path": "..." (if disagreement),
  "re_verification_id": "..." (if repaired and re-verified),
  "constitutional_basis": "Article XXXVI §7"
}
```

---

## 8. What this article does NOT say

- It does **not** say that every model must agree with the external solver. Disagreement is information. The point is to surface it, not to hide it (Article XV).
- It does **not** say that the external solver is always right. The external solver can also have bugs. But the burden of proof falls on us to demonstrate why our model is correct when it disagrees with an established engine.
- It does **not** say that running the external solver is sufficient. The comparison to a published reference case is also required. The external solver itself must be validated against something we did not write.

The point is: **our model is not verified by our model.**
