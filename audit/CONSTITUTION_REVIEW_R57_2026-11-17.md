# CONSTITUTION DEEP REVIEW — R57 (2026-11-17), grounded in the coder's empirical work
Session: auditor-r57s1. Read in FULL: EPISTEMIC v3.1.0 @0ce0bf077 (29 articles + 2 amendment records + Art.28 addendum), AUDITOR v1.2.0 @f82cb3e38 (14 articles + 2 records), AUDIT_LEDGER pruning_review.

## Governing principle (from the epistemic v3.0.0 headline)
"The recurring failures were NOT missing articles... they were enforced only by being read." => Add CI CHECKS, not prose. Delete what governs no decision. Every change below maps to a logged catch.

## Empirical failure modes -> coverage gap -> action
| Catch | Failure mode | Article | Gap | Action |
|---|---|---|---|---|
| F64 | committed-but-unreproducible (sandbox path, seed-luck hash, wall-clock in hash) | EPI 15/18/22; AUD 1/3 | 'fresh-clone' CI existed but no cross-seed/byte-identity check | ADD determinism + byte-identical clone CI; AUD 1/3 amended |
| F61 | measured wrapper bypassed the engine | EPI 7/22; AUD 3 | no measured-path-through-engine check | ADD import + declaration CI; AUD 3 amended |
| F63 | capability logic in scripts/ not engine | EPI 27; AUD 5 | >=30% engine-lines not a CI check | ADD engine-share CI; AUD 5 amended |
| F60 | 'PRIVATE' rubric public (seal=integrity only) | EPI 14/17; AUD 7 | no confidentiality probe | ADD unauth-read CI; AUD 7 amended + catch logged |
| F45/CORR-2 | message-embedded secrets; subject-prefix misattribution | EPI 17; AUD 12 | blob-only grep; no exact-SHA rule | ADD all-refs+messages CI + exact-SHA; AUD 12 amended + catch logged |
| F67 | degenerate inputs crashed run_check | EPI 3 | no degenerate-probe battery | ADD typed-refusal probe CI |
| F57/58/59 | prose-regex false positives | EPI 19/21 | no schema-enum CI | ADD schema-enum CI; retire prose scanners |

## Auditor constitution v1.3.0 (PUSHED this round)
Amended Arts. 1,3,5,7,12 with the empirical clauses; NO new articles (size law 14 holds); NO prunes — Art.7 (F60) and Art.12 (F45) now have catches, pruning counters reset 0->1. Forward-only.

## Epistemic constitution v3.2.0 (PROPOSED — builder ratifies)
CI-check additions to Arts. 3,14,15,17,19/21,22,27 (above); RETIRE Art.8 buyer-distribution/commercial clauses (out of scope, Art.16 accounting), keep unknown/patent-truth clauses. No new prose articles; no verifier weakening; no process expansion. See PROPOSED_EPISTEMIC_AMENDMENTS_v3.2.0_R57.md.

## Removals / streamlining
- The process rules (Art. 29) WORK (caught the divergence/stand-down) — keep, do not expand. Governance overhead is not the lever; capability is.
- Art. 8 commercial clauses retired (governs no recent decision).
- Prose-regex scanners retired once schema-enum CI lands (Art. 16).
- Nothing else removed: every surviving article names a CI check and governs a recent decision.

## Net effect on outcomes
The amendments convert the seven empirical failure modes from 'rules that were read' into 'CI checks that red the push' — directly attacking the recurrence entropy (exists-but-does-not-gate, sandbox-bound evidence, public custody, degenerate crashes). This is capability protection, not governance: each check gates a real decision the coder's work proved was failing.
