# R412 Gradient Arm v2 — Final Report (the sealed run)

**Result: 0/10 PRESENT_RECOVERY, cause DECOMPOSED (measured, not
asserted).** The run executed the sealed pipeline end-to-end on the
reconciled history: v2.1 seal (verified before every stage) → TVM
v2 construction (11 in-cap attempts + 1 honest
INCOMPLETE_BUDGET_SHORTFALL) → Art. XLIV freeze (empty map,
sha256-pinned) → GA-3 (exactly the 10 sealed allocation seeds in
priority order, ALL DEAD_AT_TVM_QUERY) → GA-4..GA-9 zero calls (no
measured movers) → finalize (the operator's Phase L comparison
table, every denominator present, emission-guarded).

## 1. The honest headline

The same 10 seeds, the sealed v1 budgets, the field-line TVM prompt,
the v2 lossless parser + evidence contract, raw proposal persistence,
and family-expanded queries — **zero admissible frontier entries,
zero rediscoveries**. The honest interpretation is a MEASURED
three-cause decomposition, not a single-cause story:

### Cause 1 — RETRIEVAL (dominant, measured from committed bytes)

The retrieved record pools carried almost no numeric evidence. Across
the ~120 persisted records (title+abstract, the exact text the
proposer saw), only **6–7 records contain any numeric value**; several
pools contain zero. The family-expanded queries (Phase E) measured
WORSE than the v1 plain query form on pool numeric density — the
evidence-grounded vocabulary terms tokenized from the basis spans
added noise ("dpwm", "smallest", "precisely") that degraded retrieval
relevance. This is a measured, regrettable instrument lesson of THIS
arm, disclosed, not retro-edited (Art. LIX: no mid-run change was
made after seeing it).

### Cause 2 — PROPOSER (measured)

**54 proposals, ZERO numeric-bearing** (no digit in span+value on any
proposal — the deterministic scan is committed in the construction
log's raw proposals). The pinned proposer (zai/glm-4-plus, this
workspace's only live transport) quoted paper TITLES as spans and
wrote "not reported" as values, or emitted empty arrays (5 rungs).
Where a pool's rare numeric record existed, it was not proposed. The
proposer correctly declined to fabricate numbers — and the contract
correctly refused to admit what was offered.

### Cause 3 — INSTRUMENT (functioning as designed; NOT the constraint)

The v2 admission gate rejected all 54 proposals with precise,
correct, non-numeric-evidence reasons:
`VALUE_TEXT_NOT_IN_QUOTED_SPAN` (26), `YEAR_NOT_IN_RECORD_TEXT` (12),
`VALUE_NOT_MEASURED_NUMERIC` (8), `SPAN_NOT_FOUND` (1), plus 7
defect-era rejections (see incidents). **Every rejection is a
rejection of non-evidence** — this is the verifier doing its
constitutional job (Art. VII: never weakened to rescue a claim).
Unlike v1, where 31/34 rejections were serialization-format failures
on REAL numeric proposals, v2's zero is not a parser problem: there
were no numbers to parse.

## 2. The v1-vs-v2 comparison (the operator's Phase L table)

| Measurement | R412 v1 | R412 v2 |
| --- | ---: | ---: |
| Seeds | 10 | 10 (byte-copied allocation) |
| TVM proposals | 34 | 54 |
| Numeric-bearing proposals | 31 | **0** |
| Valid frontier entries | 0 | 0 |
| Frontier domains | 0 | 0 |
| Present-capability rediscoveries | 0 | 0 |
| Causal descendants | 0 | 0 |
| Fresh novelty survivors | 0 | 0 |
| Attacker survivors | 0 | 0 |
| Buyer-grade inventions | 0 | 0 |

**Confound (disclosed on the table itself):** v1's proposer was
minimax/minimax-m3:free via OpenRouter (no credentials in this
workspace); v2's is zai/glm-4-plus (the only live transport here).
The two arms also differ in query construction (v1 plain, v2
family-expanded). Admission deltas are attributable to instrument +
proposer + retrieval; **no pure instrument attribution is claimed**.
The v2 parser's rescue capability is separately measured on the
frozen calibration corpus (v1 schema admits 3/33 value spans, the v2
parser 21/33 measured-numeric / 23/33 lossless — Phase C artifact).

## 3. What the run proves (positive results)

1. The v2 pipeline ran **end-to-end on the reconciled history**: the
   v2.1 seal resolved every v2.0 blocking field with verified values;
   the seal was re-verified before every stage; the v1 artifacts were
   never touched (output only under R412/GRADIENT_V2/RUN/).
2. **RAW persistence worked in production**: every construction
   attempt's raw LLM output, every raw proposal (admitted and
   rejected) with precise reasons, and every retrieved record pool
   are committed — the instrument comparison of the NEXT arm replays
   bytes, never prose (the v1 run's unpersisted-outputs defect is
   fixed forward and already paid for itself in the incident
   diagnostics).
3. **The allocation discipline held**: exactly the 10 sealed seeds in
   priority order; the 3 ineligible and 387 non-technical candidates
   were never touched.
4. **The budget discipline held**: 11 in-cap LLM attempts + the 13th
   rung honestly INCOMPLETE_BUDGET_SHORTFALL (identical shape to v1's
   12+1); all ~18 failed transport calls are disclosed incident
   overhead ABOVE the cap, never converted into verdicts (Art. LXI).
5. **The evidence contract never blinked**: 0 admissions with zero
   fabricated precision, zero fuzzy span matches, zero
   investment-as-capability signals, zero two-truths entries.

## 4. Incidents (all quarantined, original bytes preserved)

1. **GATE_FIELD_DEFECT** (2026-09-06): the admission gate read
   `record_id` while the sealed prompt specifies `source_record_id`;
   7 rejections were infrastructure-manufactured, reclassified
   INCOMPLETE (Art. LXI), the gate fixed (pool check unchanged in
   strength), the defective entry's bytes quarantined.
2. **TRANSPORT_MISCLASSIFICATION**: 3 empty-content LLM calls
   initially recorded as parse failures; reclassified
   INCOMPLETE_TRANSPORT; the runner now checks call status before
   parsing.
3. **GATEWAY_OWNERSHIP_401**: the runner reused an already-alive
   gateway carrying a previous invocation's unknown key → 401 on
   every call; root-caused (upstream verified healthy by direct
   probe), fixed (--gateway always establishes a runner-owned
   gateway), 15 failed calls disclosed as incident overhead,
   incident-attributed failures do not consume the bounded retry.

## 5. Learning (Art. LI — a state transition, not an archive)

The next arm's measured bottleneck ordering:
1. **RETRIEVAL**: revert the TVM query to the v1 plain form (measured
   numeric-pool-density regression under family-expanded queries) or
   add numeric-abstract-bearing sources/lanes; without measured
   records in the pool, no admission schema can produce a frontier.
2. **PROPOSER discipline**: the strict contract is correct; a
   proposer that quotes titles and writes "not reported" produces
   nothing admittable — calibration against the 40-case corpus
   should extend to an end-to-end proposal-discipline corpus.
3. **The parser/evidence contract is exonerated** by this run: 54/54
   correct rejections, zero false admissions, zero weakened checks.

## 6. Epistemic status

- reviewer_provenance: **AI_REVIEW** on every artifact (Art. LXVII —
  an AI-run reconciliation and run is a genuine check, NOT human
  review).
- The attacker calibration caveat (NOT_CALIBRATED) travels on the
  funnel — no attack ran this arm (no survivors reached GA-9), so
  the caveat is dormant but present.
- Phase G of the standing directive honored: zero promotions, zero
  buyer-package artifacts; the run stops at this report.
- Every headline number regenerates from committed evidence
  (Art. LXII): the construction log, the frozen map, ga3.jsonl, the
  seal ledger, and the three incident artifacts.
