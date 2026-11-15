# R11 AUDITOR VERDICT — AMENDMENT 8 (2026-11-15): deep audit of R8 @ 86fab54a6 (00:46Z window)
Auditor: session auditor (Claude). Preflight: audit/preflight/PREFLIGHT_2026-11-15_r8.md. Companion: eval/auditor_judgments_r11_r8.json. Builder stayed OFF the audit branch (tip 76c368f94 unchanged).

## VERDICT
**Gate: NOT_MET — both clauses unresolved at n=10, UNCHANGED.** Novelty Δ +0.8 (t-CI [0.14,1.46]; z-CI [0.23,1.37]) — point estimate passes 0.5, unresolved. Feasibility |gap| 0.5 (t-CI [0.12,0.88]) — unresolved. Substance 7 A1 / 2 baseline / 1 tie — single-rater, provisional. Holdout precondition MET — 0/12 infeasible. **The D6 battery ran but is NOT gate-decisive evidence (F26, critical).** The gate still rests on the auditor's n=10 per-axis judgment of the delivery vs the curated standard-practice baseline.

## 1. F26 CRITICAL — the battery does not measure the gate
The 30-pair battery completed 28/30 JUDGE_VALID (25 A1 / 3 baseline, Wilson [0.728,0.963], calibration 0.90). But it cannot resolve the Art. LXXXVI gate, for four independent reasons verified from bytes:
1. **Self-judged (F2 regression).** call_ledger_summary shows ONE rung — xkiro/mistralai/ministral-14b (50 ok / 31 failed) — for BOTH generation and judgment; every result's judge = ["xkiro","mistralai/ministral-14b"]; spread_gate spread_ok=FALSE; d6_acceptance no_single_provider_bursts=FALSE. The model graded its own output — the exact defect F2 was opened for in R11 1.0.0.
2. **Wrong baseline.** a1_state = baseline_state = GENERATED — both arms are fresh 14B generations. The gate compares A1 against the CURATED standard-practice baseline, not a 14B-generated baseline. The battery measures pipeline-A1 vs pipeline-baseline, a different comparison.
3. **No per-axis scores.** The battery emits W/L preference only; the gate needs per-axis novelty delta + feasibility gap. The D3 gate_recompute itself falls back to the auditor's n=10 deltas.
4. **Weak proxy.** D3 second-rater agreement κ=0.25 (7/9; disagreements dev-fu-001, eval-new04 typed) — the machine judge agrees with the auditor barely better than chance. The "25/3, p<0.0001" is the model's self-consistency, not independent evidence. **NOT ACCEPTED.**
The coder correctly deferred the tally to auditor re-judgment (Art. XXVI) — that discipline is right; the battery as run simply is not the gate measurement.

## 2. Credited — four-layer infra fix chain (real capability)
The loop now runs end-to-end after four measured fixes: ① preflight probe demanded bare {"prefer":"tie"} while the validator requires the full rubric key set → a LIVE window was misjudged dead (3 probes fixed); ② localqwen local rung absent in sandbox → generator hard-pin xkiro (F27: proper fix is cascade availability awareness); ③ the earlier "RPM cap" diagnosis was WRONG and is corrected (Art. XV) — real cause was the retry governor scope=None process-level cap 6 never reset → per-pair/per-judge scope; ④ xkiro mistral systematic missing keys → retry names the missing keys → full legal JSON. Each layer measured before fixing, diagnostic bytes preserved. This is honest, capable debugging.

## 3. D4 / D5 — typed blocked
D4 20/20 independent re-judgment: calibration PASS 0.90, but the re-judgment lap hit 17-18/20 TRANSPORT_FAILED — the battery+calibration ~150-call burst exhausted the window; 429 persistent >25 min (measured to 02:29Z, eval/xkiro_budget_window_state_r11.json). D5 panel queued behind (exit 4). Both need a fresh budget window. Typed, pools unspent.

## 4. What resolves the gate
Independent per-axis auditor judgment on ≥30 pairs of (A1 delivery answer) vs (CURATED standard-practice baseline), with judge≠generator for any machine input. The battery must be re-pointed at the curated baselines + an independent judge + per-axis scoring, OR the auditor re-judges the delivery + freshly authored standard baselines for the 18 fresh problems offline. The n=10 point estimate (+0.8) is promising; n≥30 with the right comparison is decisive.

## 5. Gold-set self-check: 10/10 consistent (delivery).

## 6. Ledger delta
F2 OPEN-REGRESSED; F26 CRITICAL opened (battery not gate-decisive); F27 localqwen (low, mitigated). V8 recorded (gate unchanged; battery tally NOT accepted). OA1 rounds_open=7 (escalated). Progress 50–55% (infra reliability up; gate measurement still broken — F26).
