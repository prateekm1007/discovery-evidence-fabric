# PROPOSED EPISTEMIC AMENDMENTS v3.2.0 (auditor R57, 2026-11-17) — FOR BUILDER RATIFICATION
Authority: owner directive (deep constitutional review grounded in the coder's empirical work). The auditor proposes; the BUILDER ratifies on queue/dev12_r7 (the auditor never pushes there). Philosophy (v3.0.0 headline): the recurring failures were UNENFORCED rules, not missing rules — so this amendment ADDS CI CHECKS to existing articles and RETIRES out-of-scope clauses; it adds NO new prose articles. Forward-only (Art. 4/16).

## A. CI-check additions (each grounded in a logged catch)
- Art. 3 (Fail closed) CI += a DEGENERATE-INPUT probe battery for every physics relation (T=0 K, rho=0, Magnus floor, zero divisor, etc.) asserting a TYPED REFUSED verdict, never an uncaught exception through run_check. [F67/F-V5: arrhenius/npsh/dewpoint crashed ZeroDivisionError; fixed c-0073, auditor live-verified]
- Art. 14 (Invention Gate / sealed holdout) CI += a CONFIDENTIALITY probe: an unauthenticated read of any *_PRIVATE.json rubric must NOT return 200; the selection seal protects INTEGRITY only. A publicly readable rubric burns the set for confidentiality. [F60: v7/v8 rubrics unauth HTTP 200]
- Art. 15 (Infra failure & reproducibility) CI += CROSS-SEED DETERMINISM: content hashes (candidate_id/candidate_hash/structured_hash) identical across PYTHONHASHSEED 1/2/3/random; hashed inputs exclude wall-clock timestamps and hash-order containers (sets serialize sorted); fresh-clone reproduction is BYTE-IDENTICAL, not merely 'runs'. [F64: seed-luck hashes + sandbox-bound driver]
- Art. 17 (Secrets & credential custody) CI += ALL-REFS + FULL-HISTORY scan INCLUDING commit messages (blob-only grep misses message-embedded keys); credential/finding attribution by EXACT SHA, never subject prefix. [F45/CORR-2: OpenRouter key in 76c23fef7 message, misattributed to v28 by subject prefix]
- Art. 19/21 (Metric unit tests / Label integrity) CI += STRUCTURED-SCHEMA-ENUM validation (measure_class/signals_used/principle_id from the problem's allowed sets); prose-regex scanners RETIRED (Art. 16); diversity axes COMPUTED deterministically, never LLM-judged. [F57/F58/F59: prose-regex false positives; QDAIF lesson]
- Art. 22 (Real-bytes acceptance) CI += MEASURED-PATH declaration: the holdout/measurement driver imports the engine (mechanism_space) and the run ledger names the measured path; a wrapper-only measurement is flagged. [F61: holdouts measured a 559-line wrapper, not the 3716-line engine]
- Art. 27 (Capability budget) CI += ENGINE-LINE SHARE >=30% per round (owner rule); capability logic lives in discovery_fabric/engine/, not scripts/. [F63: 0%/6.6%/24.8% rounds; capability logic script-housed]

## B. Retirements (Art. 16 accounting — out of scope for the invention machine, governs no recent decision)
- Art. 8: RETIRE the buyer-distribution-repository / commercial-figures clauses (the machine produces engineering interventions + predictors, not commercial market figures; same rationale as v3.0.0 retiring LXX/LXXII). KEEP 'unknown must remain unknown', 'no silent semantic promotion', and 'patent evidence is not patent truth' (capability-relevant for P5 rediscovery). Record the split in the retirement ledger with successor = Art. 8 (trimmed).
- No other retirements proposed: every other article names a CI check and governs a recent decision. Art. 29 (coordination) caught real collisions (the divergence stand-down worked) — KEEP unchanged; do NOT add more process rules (the owner wants capability, not governance).

## C. What this amendment deliberately does NOT do
- Adds no new prose articles (the v3.0.0 lesson: enforcement, not prose).
- Does not weaken any verifier or gate.
- Does not expand process/governance overhead.
**Builder wiring:** ratify on queue/dev12_r7, wire each new CI check into the queue surface, update the enforcement map, record the Art. 8 split in the retirement ledger, and bump the constitution version to v3.2.0 with this amendment record. An article whose new CI check is not wired is flagged (v3.0.0 builder-acknowledgment rule).
