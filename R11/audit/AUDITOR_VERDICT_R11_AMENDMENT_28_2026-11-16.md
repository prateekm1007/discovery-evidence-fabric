# R11 AUDITOR VERDICT — AMENDMENT 28 (2026-11-16): R29 @ 7a1b7e050 — GATE MET ON THE DEV BATTERY (first time)
Auditor: session auditor (Claude). Companion: eval/auditor_r29_full30_gate_read.json + audit/holdout_v4/. Builder OFF audit branch; every battery row left PENDING-AUDITOR (Art. 10) — correct.

## VERDICT
**GATE MET ON THE DEV BATTERY — for the first time.** Auditor per-axis read of all 30 rows (18 interventions incl. the 10 converted rows read from the tuned dirs + 12 V5 predictors): **novelty Δ 2.233 CI [2.045, 2.422] (≥0.5 MET) / feasibility |gap| 0.133 CI [0.004, 0.262] (≤0.25 MET on the owner's mean form; the CI upper bound 0.262 is marginally above 0.25 and is disclosed).**
**ACCEPTANCE IS NOT YET GRANTED.** Art. 6: this 30-pair set is the DEV set the V7 family was tuned against across V7→V7.1→V7.2→V7.3→V7.4. A gate met on the tuning set is not acceptance. **Holdout v4 is authored, sealed and registered** as the acceptance test.

## 1. The conversion worked — verified row by row
- **bench-p06 premise flaw FIXED**: flushing through the existing tapping point with a catalog solenoid + timer, not flow reversal — topologically valid for a dead-end main. gap 2 → 0.
- **bench-p10 F38 CLOSED by mechanism change**: a commercial sodium-barrier film bilayer replaces the 8h-on/4h-off duty cycle; the ~33% curtailment is gone, so there is no operational loss left to price. gap 0.
- **7 of 10 flagged rows converted to gap 0** (p01, p04, p06, p08, p10, new01, sofc-tc): catalog parts + procedure changes, effects from established practice.
- **3 residual gap-1 rows**: p09 ("commercial hydrophilic silica nanoparticle sheet" — catalog reality unproven), p11 ("existing hydraulic ports" on a machine-tool spindle housing — premise assumption), new03 (0.1 mm bypass-lumen catheter + bellows = a new infusion-set design with a regulatory path).
- **Predictors (12)**: all use existing sensors with declared EDGE computation, or the constraint-permitted existing microphone array (new12) ⇒ feasibility 4 under the calibrated F39 standard; new04 gap 1 (condenser approach uses T_evap, not in the allowed BMS list).

## 2. Holdout v4 — the acceptance instrument (auditor-authored, sealed)
12 fresh problems (6 intervention with explicit allowed-measures lists, 6 predictor with existing-sensor + failure-defining quantity), domain-disjoint from v1/v2/v3 and the dev batteries. **Fully auditor-authored problems AND rubric** — removes the v3 builder-authored-problems caveat. selection_sha256 `00dfaf7e…`. One-shot: builder claims `holdout-v4-generation`, receives problems only, generates once with the **frozen V7.4 machine** (no contract edits), peer verifies, auditor scores. **Acceptance bar: mean ≥3.0/4 and 0 allowed-measures violations.** Burn after.

## 3. New findings
- **F40 (LOW)**: bench-p10 names DuPont SentryGlas as a "sodium-barrier film" — SentryGlas is an ionoplast structural interlayer, not an ion-barrier product. The class exists (SiOx-coated PET); the exemplar's property is misattributed.
- **F41 (LOW)**: the catalog-v2 named-variant scan false-positives on size designations (DN15/DN50 PN16). A size/pressure class is not a brand marker.
- **F39 STILL OPEN**: the machine's feasibility axis is uncalibrated on BOTH classes (F_A=1–2 for procedure/firmware on existing hardware). c-0026 recalibration is pre-registered but not run. The auditor read governs.

## 4. Duplicate-lane discipline
The reporting session executed AM27 D1–D4 in parallel with the peer, found its lane was a duplicate (claim ID even taken), aborted the rebase and preserved everything out-of-repo rather than pushing over living state. Correct Art. 29 behaviour. Its two disclosures are accepted: the pre-existing `test_r416_evolution` failures (verified on a clean base) and the disk-full episode (6.9 G of pytest scratch mimicking dozens of test failures).

## 5. Gold-set self-check: 10/10; full 30-pair read.

## 6. Ledger delta
F30 MET-ON-DEV-PENDING-ACCEPTANCE; F38 CLOSED; F40/F41 opened; F39 open; holdout_v4 SEALED_REGISTERED; V28. Progress 70–78%.
