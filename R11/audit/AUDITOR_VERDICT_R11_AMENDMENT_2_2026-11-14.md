# R11 AUDITOR VERDICT — AMENDMENT 2 (2026-11-14): deep audit of R2 @ 5569ecba8
Auditor: session auditor (Claude). Read-only against remote; companion record `eval/auditor_judgments_r11_r2.json`. Gate: **NOT_MET — both clauses now fail**. Holdout precondition (0 infeasible by auditor judging): **NOT_MET — 9/12 infeasible or invalid as written**.

## 1. Verified TRUE (evidence-checked)
- Push state: queue/dev12_r7 == 5569ecba8; ab59fd5b1 + 5569ecba8 contents match the report.
- Plausibility critic exists, anchors carry provenance (BUYER_DEFINED, citing the audit findings); the graphene candidate is VETOED in R2 p02's record. Calibration regression reports 4/4 defect sensitivity, 0/4 false-kill ON ITS CORPUS.
- pair_guard implemented: typed refusal + FABRIC_PAIR_WRITE_UNLOCK, versioned dirs writable — closes the near-miss mechanically (Art. XXXIX).
- R2 battery: 12/12 COMPLETE, 3-4 calls, median 46.4 s / max 59.4 s — budget held.
- Baseline-union comparator retired; lexical-recall overlap MEASURED and honestly disclosed (known 0.23-0.52 vs baseline 0.00-0.43); band-tuning refused as gaming. Named-technique KNOWN instrument passes its 4-specimen false-novelty corpus.
- Novelty search: 10 claims / 2 honest withdrawals (new07 DGA, sofc glass-ceramic).
- Ablation rescore on calibrated rubric: 2.75 / 2.75 / 2.73 / 2.27 — repair load-bearing on testability (3.8→2.3); judged pairs TYPED_SKIP (Art. LXI).
- Delivery selection A1_CRITIC_VALID in triples; heavy pipeline FROZEN_NO_NEW_WORK; owner_steps typed BLOCKED/NOT_PLACED honestly.

## 2. FALSE or unsupported claims
- **"Survivors intact" is FALSE.** All 12 chosen ideas differ from 1.0.0. The credit-register leads — UV-crosslinked EVOH (p09, a pair WINNER), ZrO2 composite seal + graded cathode (sofc, owner-cited), IL-polymer electrolyte (new01, a pair WINNER) — were DISCARDED by full re-ideation. Amendment 1's salvage directive was not implemented; the machine threw away its best novelty assets.
- **Calibration label provenance defect.** The regression corpus is labeled from the superseded 2W/7T/3L audit, not the authoritative auditor record (3W/6L/1T, per-axis, which the owner declared superseding). fu-001 (kurtosis-at-1Hz, fabricated-looking DOI) and fu-003 (PRPD-is-standard, sampling gap) are mislabeled "known-good". Art. L calibration must source labels from `eval/auditor_judgments_r11.json`.
- **"Only 4 replacements await re-judgment" understates the change.** 12 new answers required full re-judgment; done (this amendment).

## 3. R2 auditor judgments (all 12 read in full; 10 gate pairs vs the SAME baselines)
| problem | a1 R2 (n,f,t,c) | base (n,f,t,c) | Δn | |Δf| | infeasible/invalid | pref |
|---|---|---|---|---|---|---|
| bench-p02 | 2,2,1,2 | 1,3,3,3 | +1 | 1 | YES (Cu dissolves at positive potential; Pourbaix at cell voltage; 15-yr test) | baseline |
| bench-p09 | 1,3,2,2 | 1,2,2,2 | 0 | 1 | no (novelty down; crystallinity mislabel) | a1 |
| dev-fu-001 | 1,3,3,3 | 2,3,4,3 | −1 | 0 | no (converges on baseline idea) | baseline |
| dev-fu-003 | 2,2,2,1 | 1,3,3,2 | +1 | 1 | YES (predictor question → VPI rewind; "3x user-stated" fabricated) | baseline |
| dev-fu-005 | 2,3,3,2 | 2,3,2,1 | 0 | 0 | no ("field trials confirm" fabricated; test now executable) | a1 |
| eval-new01 | 2,2,2,2 | 1,2,2,2 | +1 | 0 | YES (osmosis driving vapor = category error) | a1 |
| eval-new02 | 1,0,2,1 | 2,3,4,3 | −1 | 3 | YES (1-10 kHz from 1-min samples: Nyquist-impossible) | baseline |
| eval-new04 | 1,2,2,1 | 1,3,4,3 | 0 | 1 | YES (condenser ΔP not in BMS list; "user-approved" fabricated) | baseline |
| eval-new05 | 2,2,2,3 | 1,3,3,3 | +1 | 1 | YES (1A×10ms=0.0028mAh not 10mAh; balancing direction inverted) | baseline |
| eval-new07 | 2,0,2,1 | 1,2,3,1 | +1 | 2 | YES (kHz band from 15-min averages; PD→0.1% load harmonics absurd) | baseline |
Excluded (no baseline), scored for the precondition: **fu-004** (0,2,2,0) predictor question → Cu-Ni retubing; back-pressure indicator outside allowed signals; C70600 self-declared standard yet NOVELTY_CLAIMED. **sofc** (2,1,1,3) LSM (electronic conductor) as hermetic seal = short/crossover; 500 cycles at 5°C/min ≠ 100 h.
- Gate: novelty Δ mean **+0.3 < 0.5 FAIL** (was +0.6 provisional); feasibility |gap| mean **1.0 > 0.25 FAIL**. **NOT_MET.** Substance preference: baseline 7, A1 3.
- Holdout precondition: **9/12 infeasible or invalid** (p02, fu-003, fu-004, new01, new02, new04, new05, new07, sofc); clean: p09, fu-001, fu-005. 1.0.0 had 5; **R2 regressed deliverable quality**.

## 4. Root cause (capability, not governance)
The critic is ANCHOR-OVERFIT: it kills the four exact 1.0.0 patterns it was calibrated on, then full re-ideation reintroduces the SAME defect classes in new forms (sampling-rate measurability: new02/new07; question-type drift: fu-003/fu-004; fabricated user labels: 4 answers; unverifiable DOIs: reused thesis DOI, npj Flexible Electronics for transformer PD; arithmetic: new05 ×3600, sofc 100 h). The LI prior wiring exists but inspected R2 records show empty prior_killed_classes — verify the ledger is actually consumed. The machine novelty instrument swung from baseline-pinned-0 to everything-equal (delta 0.0, baseline=A1=2.1) — still degenerate; machine feasibility 3.75 vs auditor 1.9.

## 5. Still-open prior directions (verified NOT done at HEAD)
P0-1 decoder TIE→win bug STILL PRESENT in scripts/r11_a0plus_compare.py. P0-2 judge≠generator not enforced; no independent re-judge. P0-3 rubric pinned eff419506 dirty=True, novelty pinned eff419506, rubric_version still 1.0.0 after comparator replacement. P0-4 DOI resolution / user-label audit / executable-test checks absent. P0-5 salvage leg absent. P1-7 earned concurrency absent (R2 hit dead-rung cascade stalls; pin-override workaround). P1-8 live prior-art absent (C70600 recall gap). P1-9 ≥30 fresh pairs absent. P2-10 CI workflows exist but 0 check-runs on this branch. P2-11 cross-family panel absent.

## 6. Verdict
Instrumentation discipline advanced (guard, typed states, honest disclosures, retirement accounting). Invention capability REGRESSED: the loop destroyed its best leads and shipped 9/12 infeasible/invalid answers. The next round must preserve leads, repair in place, and generalize the critic to defect CLASSES — measured against the authoritative auditor labels, with the R2 outputs themselves as the adversarial regression corpus (Art. XXX).
