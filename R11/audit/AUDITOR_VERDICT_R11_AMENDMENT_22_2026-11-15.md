# R11 AUDITOR VERDICT — AMENDMENT 22 (2026-11-15): R22 @ ae4a0ab99 — n=30 achieved; Art. 29 live-fire passed; feasibility the binding frontier
Auditor: session auditor (Claude). Preflight: audit/preflight/PREFLIGHT_2026-11-15_r22.md. Companion: eval/auditor_judgments_r11_r22.json. Builder OFF audit branch (tip 915f39eb6). Art. 13 independent recompute applied.

## VERDICT
**Gate: NOT_MET — at full n=30, novelty RESOLVED-PASS (1.967, CI [1.23, 2.704]) but feasibility RESOLVED-FAIL (1.4, CI [0.963, 1.837]).** The machine invents novel things; they are not feasible-competitive. Feasibility is the binding frontier. **Art. 29 passed its live-fire test** (a mid-round race resolved by-the-book, zero duplicates). F34 closed.

## 1. n=30 gate-decisive measurement — verified (Art. 13 exact)
`battery_v4_n30_r21.json`: n=30 (first time ≥30), novelty Δ 1.967 CI [1.23, 2.704] (lower bound > 0.5 → resolved-PASS; the Art. 14 power concern is satisfied for novelty), feasibility |gap| 1.4 CI [0.963, 1.837] (entirely > 0.25 → resolved-FAIL). My independent recompute reproduces both exactly. The transport ladder recovered eval-new10 (90 slots, 86 first-try, 4 recovered, 0 dead), recomputed from committed draws. The full claim/execute/verify cycle completed: c-0002 EXECUTOR DONE + c-0005 VERIFIER DONE (peer recomputed from bytes, never re-ran).

## 2. Art. 29 live-fire — the mechanism works under real concurrency
The peer pushed 3 commits mid-execution; the executor's push was rejected; it stood down, diffed-against-remote, confirmed the work disjoint, rebased only disjoint work, and unioned the registry (5 claims, 2 sessions, trailers compliant). **Zero duplicates, zero clobber.** This is the owner's parallel-builders decision functioning exactly as designed under a live race. F34 closed (bootstrap claim c-0001 disclosed post-execution + peer VERIFIER c-0003). Art. 20 wired (ABLATION_REGISTRY.json; no duplicate wiring).

## 3. BOK generation-side lever — NEGATIVE result
`battery_int_bok_r21.json` (best-of-k variance-controlled generation): feasibility 1.667 CI [1.175, 2.158] — WORSE than the V4 re-judge (1.4). The generation-side variance lever did not improve feasibility. **F35 (LOW):** the BOK novelty mean is identical to V4 (1.967) despite a different A-side composition; the verifier must confirm the BOK A-side bytes were regenerated and scored from raw draws (not a novelty-column copy). Feasibility differs, so the answers differ.

## 4. The frontier
Novelty is solved (resolved-pass at n=30). Feasibility is the binding clause and the generation-side lever failed. The next lever must target feasibility DIRECTLY: feasibility-first best-of-k selection (select by feasibility parity, not novelty) or a feasibility-repair leg that reworks the bill to standard-practice parity while preserving the novel mechanism. Acceptance unchanged: feasibility |gap| ≤0.25 AND novelty Δ ≥0.5 on ≥30 pairs.

## 5. Gold-set self-check: 10/10; n=30 recomputed exact.

## 6. Ledger delta
F34 CLOSED; F30 OPEN-RESOLVED-FAIL (feasibility binding at n=30); F35 opened (low, BOK novelty-column verification); F25 live-fire passed; V22 recorded. Progress 55–62% (measurement certainty at n=30; novelty resolved-pass; mechanism proved; feasibility resolved-fail confirmed; BOK negative).
