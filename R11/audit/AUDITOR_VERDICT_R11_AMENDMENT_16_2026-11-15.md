# R11 AUDITOR VERDICT — AMENDMENT 16 (2026-11-15): R16 @ 52c577ca9 — F31 FIXED, feasibility frontier isolated
Auditor: session auditor (Claude). Preflight: audit/preflight/PREFLIGHT_2026-11-15_r16.md. Companion: eval/auditor_judgments_r11_r16.json. Builder OFF audit branch (tip c03bd1189 unchanged).

## VERDICT
**Gate: NOT_MET — feasibility RESOLVED-FAIL is binding; novelty RESOLVED-PASS, now type-honest and strongest ever (2.433).** **F31 is CLOSED — the question-type generalization failure is fixed at the answer level.** The machine now answers intervention questions with mitigations and predictor questions with predictors (30/30 type-MATCH). The feasibility failure is isolated to heavy-mechanism interventions.

## 1. F31 CLOSED (credited — major milestone)
- SYS_A1_INT intervention contract committed (bbd8721e3, 11:08:55Z) **BEFORE** generation (0df01e578, 11:16:35Z) — pre-registration discipline (Art. 6), no holdout tuning.
- Type-aware dispatch: intervention → SYS_A1_INT (invent-the-mitigation + effectiveness falsifier), predictor → SYS_A1F_V3 (imported). Fail-closed question-type gate (MATCH/MISMATCH) in the critic path; the gate instrument's primary acceptance is type-credited (wrong-type novelty structurally unrewardable).
- **Verified from bytes**: bench-p02 proposes a nanocrystalline tin coating on the lead grid (a real mitigation, SnO₂ barrier replacing corrosion-prone antimony); bench-p04 proposes sinusoidal micro-oscillation impeller vanes to disrupt cavitation bubble formation (a real mitigation attacking the driving physics). These are mitigations, NOT monitoring observables. 30/30 type-MATCH, 30 critic-CLEAN. The predictor-only failure is fixed.

## 2. F30 OPEN-ISOLATED — the feasibility frontier is now characterized
Battery r10 (n=30, independent qwen judge k=3): novelty Δ **2.433** CI [1.784, 3.082] PASS (type-honest, strongest); feasibility |gap| **1.9** CI [1.418, 2.382] FAIL. **The split is decisive: predictor rows |gap| 1.167 (near parity) vs intervention rows 2.389.** Five gap=0 rows; bench-p02 is a counter-proof (sg=+1, more feasible than baseline); the heavy-mechanism interventions (bench-p04/p08/p10, sg=−4) carry the deficit. Five contract generations trace the lineage; the binding frontier is now **weight-bound mitigation design** — making heavy-mechanism interventions feasible-competitive while preserving novelty.

## 3. Gate decision
NOT_MET. Novelty RESOLVED-PASS (type-honest). Feasibility RESOLVED-FAIL (binding), isolated to heavy-mechanism interventions. The machine cleared the question-type frontier (F31); the remaining gap is feasibility of the hardest mitigations. A fresh sealed holdout (v2) is needed to confirm the type-aware machine generalizes (v1, burned, scored the predictor-only machine at 36.5%).

## 4. Gold-set self-check: 10/10; type-aware answers verified.

## 5. Ledger delta
F31 CLOSED; F30 OPEN-ISOLATED (heavy-mechanism intervention feasibility). V16 recorded. Progress 52–60% (F31 closed is a major milestone; novelty type-honest strongest; feasibility isolated, still failing).
