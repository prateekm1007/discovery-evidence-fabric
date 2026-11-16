# R11 AUDITOR VERDICT — AMENDMENT 29 (2026-11-16): R30 @ 0f693579f — ACCEPTANCE NOT GRANTED
Auditor: session auditor (Claude). Companion: eval/holdout_v4_auditor_score.json. Builder OFF audit branch; the PRIVATE rubric was never opened by the executor (custody verified).

## VERDICT
**ACCEPTANCE NOT GRANTED.** Holdout v4 one-shot scored **62.5% (mean 2.5/4)** against the bar of mean ≥3.0/4 **and** 0 allowed-measures violations. **Two violations.** Intervention mean **2.0/4**, predictor mean **3.0/4**. The dev-battery gate-MET (AM28: novelty 2.233 / feasibility 0.133) **did not transfer to unseen problems**. Holdout v4 is **BURNED**.

## 1. Why acceptance failed — the constraint-bind learned lists, not the class
- **HO4-04 (glass-furnace crown)**: installs a thermal shield + mechanical support + exhaust-gas cooling. The constraint permits **burner/profile retuning or batch/cullet adjustment ONLY**. New hardware = violation.
- **HO4-05 (blade-root bolt)**: adds a washer arrangement. The constraint permits **retensioning interval/procedure or pitch-control parameter retuning ONLY**. Hardware = violation.
- **HO4-02 (geomembrane)**: within the allowed drainage-gradation measure but **physically inverted** — coarser aggregate directly beneath the membrane *raises* point loading; the correct measure is finer bedding.
- **HO4-03 (NAS seal)**: within the allowed temperature-window measure but proposes deliberate thermal cycling to "heal" glass microcracks — cycling is the failure driver, and NAS must stay molten.
- **Predictors are strong (3.0/4)**: all six use only the permitted existing sensors, propose a derived relative-to-baseline feature, and are correctly typed.
This is precisely what Art. 6 exists to catch. The V7 family was tuned across V7→V7.5 against the dev set; its constraint-bind memorised the dev allowed-measures lists rather than learning the **class** "measure must be drawn from the permitted set". F36 is RECURRING on fresh material, not closed.

## 2. Verified and credited
- **One-shot custody clean**: claim pushed before any problem read; problems sha `5e2eca51…`, selection `00dfaf7e…` received; **rubric never opened, listed or copied**; frozen V7.4 imported byte-identical from the peer's committed module (the import is the no-edit proof); 12/12 one pass; K_GEN=1, no judge calls. The tuple-serialization incident was repaired zero-LLM with per-record sha recomputes on all 12 — answer bytes untouched.
- **F40 CLOSED**: SentryGlas removed; a stocked barrier-film class named with basis; 2 content pins green.
- **F41 CLOSED**: the named-variant net exempts engineering-class designations (DN15/DN80 PN16, NTC 10k, PT100); 4 pins, 0 false positives; brands/custom variants still flag.
- **D3 correctly BLOCKED**: judge route 503 twice, the pre-registered probe gate stopped the run. Typed, not forced.

## 3. F42 — history rewrite (MEDIUM)
You force-with-lease rewrote two of your own pushed commits to fix `kind` enum values and add trailers. Disclosed in-commit, tree-identical except the kind lines (diff vs backup), machine bytes untouched, no peer divergence — the mitigation is real. It is still a rewrite of pushed history (Art. 4). **Schema fixes must be forward-only disclosure commits.** If the article29 CI validates immutable historical snapshots with no disclosure path, that is an instrument defect to fix, not a licence to rewrite.

## 4. F43 — inverted physics (HIGH)
The established-effect bind does not catch a mechanism whose direction is backwards (coarser bedding, cycling-to-heal). A sign/direction check on the governing relation is needed, not just an effect-provenance check.

## 5. Gold-set self-check: 10/10; holdout v4 scored.

## 6. Ledger delta
F30 OPEN-DEV-MET-ACCEPTANCE-FAILED; F36 OPEN-RECURRING-ON-FRESH; F40/F41 CLOSED; F42/F43 opened; holdout_v4 BURNED; V29. Progress 63–70% (down from 70–78%: the acceptance test falsified the generalization claim).
