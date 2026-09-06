# R412 GRADIENT ARM V3 — FINAL REPORT
## The Frontier Evidence Acquisition Layer and the benchmark gate that stopped it

**Arm:** `r412/gradient-v3` (branched from `r412/gradient-v2` at `e7e130b1`, per the operator directive)
**Objective (operator directive 2026-09-06):** determine whether a better frontier-evidence acquisition system can expose real quantitative capabilities that the v2 proposer could not see — NOT to manufacture a nonzero result.
**Terminal state:** `BENCHMARK_GATE_FAIL` — an honest stop at the pre-registered gate, with zero proposer (LLM) calls spent.
**reviewer_provenance:** AI_REVIEW on every artifact in this arm (Art. LXVII).

---

## 1. What this arm was

The operator's audit of the v2 arm found the machine could explain its own failure: 0/10 recoveries, ~6-7 numerically informative records out of ~120, a proposer quoting titles and writing "not reported", and a parser exonerated with nothing to parse. The directive ordered a retrieval-first rebuild — the Frontier Evidence Acquisition Layer — before any further discovery spend, with a frozen deterministic benchmark as the gate.

This arm built and sealed, before its first retrieval call:

- **The record-level diagnostic** over the committed v2 pools (`RETRIEVAL_DIAGNOSTIC_V2_POOLS.json`): the v2 bottleneck was MECHANICAL, not lexical — the abstract-bearing scholarly connectors' records never entered any pool (title-normalization defect), crossref (the only consistently-OK scholarly source) is metadata-only, S2/OpenAlex were rate-limited, and the persisted v2 pools carried no year and no source attribution. The v1-vs-v2 query-wording comparison was a comparison of two query forms on top of a broken acquisition layer.
- **FEAL** (`discovery_fabric/r412/frontier_evidence.py`, 1162 lines, LLM-free): three separately-attributable retrieval lanes (A: the v1 plain form byte-identical as the control column; B: capability requirement + the operator's frozen measurement terminology; C: frontier-domain transfer with the capability rung as bridge), full pool persistence (the v2 schema's missing fields: source, source family, year via multi-field fallback, doi, patent number), deterministic numeric-evidence extraction (closed unit vocabulary + the tvm_v2 lossless value parser, byte-exact spans), the Frontier Evidence Score (evidence-property-based, component-traced, never a novelty score), capability trajectories with velocity, cross-source corroboration states (SINGLE_SOURCE_SIGNAL / MULTI_SOURCE_SIGNAL / REPLICATED_TRAJECTORY / UNKNOWN), and multi-level capability derivation (L1 exact rung / L2 family / L3 measurement dimension — several families per death, derived from committed evidence, never invented).
- **The frozen benchmark** (`RETRIEVAL_BENCHMARK/`): 48 records acquired by direct connector calls with a query form distinct from every lane form ("{capability} experimental comparison"), labels authored by the coder reading each record before the evaluator existed and before FEAL ever ran on them (Art. VIII).
- **The preregistration** (`R412_GRADIENT_V3_PREREGISTRATION.json`): population pin, the byte-copied 10-seed allocation, instrument pins, pre-registered gate thresholds (each a stated monotone multiple of the v2 measured baseline — ENGINEERING class, Art. XXVII), the lane plan (39 queries), proposer independence (P1 = the sealed v2.1 prompt byte-reused; P2 = an explicit numeric-evidence scan procedure; same pools, same verifier — retrieval-vs-proposer separation, not model independence), the adoption-gap instrument (10 closed categories, UNRESOLVED legitimate), budgets (26 construction calls max = 13 rungs x 2 configs; downstream byte-copied from the sealed v1 budgets), 10 stopping rules, and the success criteria (per-unit-retrieval-cost exposure / rediscoveries per seed / buyer-grade inventions — explicitly NOT TVM entry count).

## 2. What ran

1. **The three lanes, 39/39 queries** through the byte-identical v1/v2 fabric plumbing with the pre-seal repaired connectors (arxiv/openalex/semantic_scholar title normalization + the canonicalizer blank-title guard — root-caused in the diagnostic, disclosed in the prereg's plumbing disclosure). Every pool byte persisted per query (content-keyed, resumable, committed).
2. **The benchmark evaluation** (`RETRIEVAL_BENCHMARK_EVALUATION.json`), deterministic over the committed pool bytes: union pool 483 deduplicated records; 72 numeric-bearing; **GATE VERDICT: FAIL** — 6 of 9 pre-registered thresholds failed (recall_numeric 0.1429 vs 0.25; recall_measurement 0.1481 vs 0.25; numeric_bearing 0.1491 vs 0.15; abstract_bearing 0.4865 vs 0.6; year_recovery 0.3313 vs 0.5; baseline_recovery 0.0559 vs 0.1; passed: measurement_bearing 0.4037, source_identity 1.0, domain_diversity 13).
3. **The mandated decomposition** (`GATE_FAIL_DECOMPOSITION.json`): three causes, measured from committed bytes.

## 3. Why the gate failed (the decomposition)

**Cause 1 — GENUINE (dominant): the sealed lane query forms do not retrieve the reference records.** The 12 unmatched numeric-bearing reference records are europepmc (9) and core (3) papers; europepmc was queried on every invocation (OK or honest EMPTY — never a provider failure) and did not return them for the lane query strings. The corpus's distinct acquisition form ("{capability} experimental comparison") outperformed all three sealed lane forms on reference recall. The query form is the dominant retrieval variable — consistent with the v2 arm's own finding that the plain v1 form beat the family-expanded form on pool numeric density. This is a real, measured scientific result about query construction, and it is the reason the gate cannot pass on this preregistration even with every instrument repaired.

**Cause 2 — INSTRUMENT (deflated the rate metrics): the normalization layer dropped metadata-only sources' fields.** crossref's `issued_year` (212/483 records lost their year), the patent adapters' `publication_date` and `snippet` (176/483 lost year AND their only text), because `best_record` was only assigned to longer-abstract records. Four rate metrics were infrastructure-deflated. Quarantined as incident `R412-GRADIENT-V3-NORM-METADATA-FIELDS`, repaired, and pinned by 6 new tests (103/103 retrieval battery green). The repairs exist for the NEXT arm; they cannot resurrect this verdict, and no counterfactual rate is asserted (the dropped fields were never persisted — Art. XXV).

**Cause 3 — INFRASTRUCTURE INCOMPLETE (Art. XXI.3):** OpenAlex returned HTTP 429 on all 39 invocations — a $0-remaining provider budget ("This request costs $0.001 but you only have $0 remaining. Resets at midnight UTC", verbatim in the decomposition) — never counted as absence; SemanticScholar throttled (28/39) with 9 throttle-shaped parse failures and 2 recoveries; CORE throttled 19/117 lane-state attempts (and its 0/109 year recovery is UNRESOLVED — the connector maps the field, a live probe is 429-blocked, unknown stays unknown).

## 4. What the engine would have been fed

The deterministic trajectory layer (directive items 5-6, LLM-free) over the committed pools: **65 trajectories (21 multi-point, 2 with a computable capability velocity), corroboration 19 SINGLE_SOURCE_SIGNAL / 2 REPLICATED_TRAJECTORY / 44 UNKNOWN; 163/488 records Frontier-Evidence-Score positive.** The cost metric (directive item 14): **18.46 numeric-bearing records exposed per 100 fabric source-calls (390 measured attempts — v3 persisted the per-invocation source states; v2's pools never did, so the per-cost number is v3-only)**. The measurable v2-vs-v3 comparison is the pool rate: v2 exposed 4 numerically-informative records out of 152 unique pool records (2.6%, measured by the committed diagnostic); v3 exposed 72/483 (14.9%) — a 5.7x improvement in pool numeric density, still below the pre-registered 0.15 threshold by 0.0009 and below it materially once the zero-text patent records are excluded from the denominator in principle (a counterfactual NOT asserted — Art. XXV). The gate did exactly what it was built to do: it refused to spend discovery budget on a starved evidence layer.

## 5. The incident ledger (all quarantined, original bytes preserved, Art. XI)

1. **`R412-GRADIENT-V3-LANE-C-UNKNOWN-DOMAIN`** (pre-proposer, mid-run): lane C treated the ga1b epistemic state "UNKNOWN" as a literal search domain; fixed with a closed invalid-token filter (a rung with no valid recorded frontier domain emits zero lane-C queries and records the miss); the polluted pool file deleted in the same change; plan re-sealed before resumption; completed unpolluted queries kept their bytes (content-keyed resumption).
2. **`R412-GRADIENT-V3-EVAL-SOURCE-CALL-COUNT`** (pre-verdict): the evaluator coerced a list field with `int()` and crashed before any threshold was evaluated; no verdict was influenced; fixed; prereg rebuilt before the evaluation ran.
3. **`R412-GRADIENT-V3-NORM-METADATA-FIELDS`** (post-verdict diagnosis): the normalization defect above; repaired + pinned by tests for the next arm; this arm's verdict unaffected and unresurrectable.

## 6. Budget honesty

- LLM calls: **0** (the gate stopped the arm before the first proposer call — the pre-registered order held in production).
- Retrieval: 39 fabric invocations, 390 source-call attempts, every pool byte committed.
- No TVM v3 construction, no GA stages, no adoption-gap calls, no causal transfer — all gated behind the benchmark PASS that never came. The 26-call construction budget and the byte-copied downstream budgets were registered and never spent.

## 7. Learning recorded (Art. LI — negative knowledge as a state transition)

1. **The query form is the dominant retrieval variable, again.** Plain form > family-expanded (v2's finding); comparison-targeted form > all three sealed v3 lane forms on reference recall. The next arm's lane plan should derive query forms from the MEASUREMENT-CONTEXT structure of the target evidence (comparison/baseline/versus/achieves), not only capability+terminology — and should register it BEFORE the benchmark freeze.
2. **The normalization layer must be treated as part of the measured instrument.** Three of this arm's four rate failures were deflated by field-dropping that pre-dated the arm. The repairs are pinned by tests; the next arm's diagnostic should recompute the pool property rates from its own first bytes before the gate runs.
3. **OpenAlex is a metered budget, not an open source.** A $0-exhausted provider silently removed the main abstract-bearing scholarly lane for a full run window. Provider-budget state belongs in the pre-run source-health check (the existing health probe measures availability, not remaining budget).
4. **The v1→v2→v3 instrument sequence is now two generations of the same lesson: measure the acquisition layer BEFORE attributing anything to the proposer.** v2's parser was exonerated by an empty map; v3's gate stopped the arm before the proposer was ever consulted. The next arm inherits: a proven field-complete persistence schema, a proven LLM-free extraction stack, and a benchmark whose recall floor it must now genuinely beat.

## 8. Sealed-artifact integrity

`r412/gradient-v2` (`e7e130b1`), R411, the temporal control arm, and all v2 run artifacts: untouched (git-verified — zero tracked changes under `R412/GRADIENT_V2/`; this arm's output lives only under `R412/GRADIENT_V3/`). The v1/v2/temporal seals were re-verified live at arm start; the 10-seed allocation was never expanded; no 500-call budget was touched.
