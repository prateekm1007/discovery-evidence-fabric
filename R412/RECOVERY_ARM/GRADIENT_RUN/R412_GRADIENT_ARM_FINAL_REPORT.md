# R412 Gradient Arm — Final Report & Failure Learning

**Run:** `r412:gradient-recovery-v1` (sealed preregistration 5084673f;
runner repairs be265c14 / 5dee0972 / 270234a8 / 9a8f0dce, all pre- or
infra-disclosed)
**Date:** 2026-09-05T21:00Z
**Reviewer provenance:** AI_REVIEW (Art. LXVII)
**Population:** the ENTIRE frozen R411 population — raw accepted 550 →
unique scored 400 → {technical death 13, non-technical rejection 387,
no death cause 0, other 0}. The 13-subset is a separately reported
subset, never the headline.

## 1. Headline result (the sealed funnel, emission-guarded)

| denominator | count |
|---|---|
| raw_accepted | 550 |
| unique_scored | 400 |
| recorded_technical_death | 13 |
| recorded_nontechnical_rejection | 387 |
| recorded_no_death_cause | 0 |
| other_terminal_state | 0 |
| gradient_eligible (sealed GA-2) | 10 |
| gradient_attempted (GA-3 entries) | 10 |
| present_rediscoveries (PRESENT_RECOVERY) | 0 |
| future_dependent_radar | 0 |
| unresolved_availability | 0 |
| normal_pipeline_survivors | 0 |

**LIRY = 0.0** (survivors/attempted = 0/10; per-eligible 0/10).
**PRESENT_RECOVERY / gradient_attempted = 0/10 = 0.0.**
Zero is an acceptable outcome (Art. LXVIII) — and this zero is
**instrument-attributed, not science-attributed** (see §3).

## 2. Independent survival accounting (directive Phase F)

| stage count | value |
|---|---|
| TVM candidates discovered (proposals) | 34 |
| TVM entries admitted (span-verified) | **0** |
| mechanisms successfully backcast (GA-4 OK) | 0 |
| transfers technically feasible (GA-5 OK) | 0 |
| present capabilities demonstrated (GA-6) | 0 |
| causal architectures passing (GA-7 PASS) | 0 |
| fresh collision survivors (GA-8) | 0 |
| fresh attack survivors (GA-9) | 0 |
| normal-pipeline entrants | 0 |
| actual recovered inventions | 0 |
| future-only projections (radar) | 0 |
| cemetery outcomes (deaths at GA-3, recorded) | 10 |
| incomplete transports (during sealed stages) | 0 |
| orphaned infrastructure calls (incidents §5) | ~5–6 fabric+LLM |

`attacker_calibration_status = NOT_CALIBRATED` travels on this report
and on the sealed funnel (no attack ran — nothing reached GA-9; the
caveat is unconditional on the funnel per the sealed builder).

## 3. The proximate cause: the TVM construction instrument admitted
nothing

All 10 allocated seeds died at **GA-3 (DEAD_AT_TVM_QUERY)** — the
cheapest kill, exactly as sealed. The map they queried was empty:

- 12 rung constructions completed (the sealed 12-call cap; the 13th
  rung, `dimensional regime consistency validation`, honestly recorded
  `INCOMPLETE_BUDGET_SHORTFALL`).
- 132 records retrieved across the 12 rungs (9–12 per rung).
- **34 proposals, 0 admitted.** Rejection reasons (deterministic gate,
  sealed entry schema "value: number, year: int"):
  - `VALUE_OR_YEAR_NOT_NUMERIC` — 31/34 (91%)
  - `RECORD_ID_NOT_IN_RETRIEVED_POOL` — 2/34
  - `SPAN_NOT_VERBATIM_IN_RECORD` — 1/34

**Root-cause analysis (Art. XXXII, strongest alternative explanation
tested):** the pinned proposer (minimax/minimax-m3:free) DID find
relevant records with measurable values — 33/34 proposals passed the
span/pool identity checks — but wrote the `value`/`year` fields as
ranges or qualified numerics ("0.1–10", "2023 (study)"), which the
sealed entry schema (a NUMBER and an INT) correctly rejects. The
machinery's parsing was independently verified sound on synthetic
well-formed input (admitted 2/2) and malformed input (rejected 2/2)
before this conclusion was drawn. The same model followed the
field-line format perfectly in GA-1b (13/13 span-verified OK) — the
failure is specific to the TVM proposal prompt's pipe-delimited ENTRY
format, not to the model's ability to quote evidence verbatim.

**Therefore the honest interpretation of this zero:** the run does NOT
establish "no measured fast-movers exist on these rungs in the
literature" — it establishes "the sealed TVM instrument + the pinned
proposer produced no admissible entries". The 10 GA-3 deaths are
deaths-by-instrument (recorded per the sealed rule; the sealed rule
was applied faithfully), and any claim that the literature lacks
measured movers would be an Art. LXI contamination of an instrument
failure into a scientific absence.

**Learning (Art. LI — this is a state transition, not an archive):**
the recommended next arm, IF the owner authorizes it, is a NEW sealed
epistemic version (never a retro-edit; Art. XLIV/LIX) with the TVM
proposal prompt in the field-line format the same model demonstrably
follows (GA-1b: 13/13), everything else unchanged. A deterministic
"numeric normalization" of rejected values is NOT an acceptable
alternative — it would weaken the verifier to rescue the claims
(Art. VII).

## 4. Per-death failure classification (directive "failure learning")

All 10 attempted seeds: `death_stage = GA3_TVM_QUERY`, `proximate =
empty TVM on the queried rung`, `root = instrument admission failure
(proposer numeric formatting)`, `class = other/infrastructure` — NOT
"no frontier" (the frontier was never scientifically excluded):

1. `C-wind-2` (eligible, priority 1) — rung `active alignment actuation
   control bandwidth`: 6 proposals, all `VALUE_OR_YEAR_NOT_NUMERIC`.
2. `C-power_electronics-1` (eligible) — `device switching energy`: 1
   proposal, `SPAN_NOT_VERBATIM_IN_RECORD`.
3. `C-chemical_process-1~3` (eligible) — `control oriented dynamic
   modeling`: 3 proposals, all `VALUE_OR_YEAR_NOT_NUMERIC`.
4. `C-batteries_ev-1~3` (eligible) — `differential measurement
   instrumentation`: 3 proposals, all `VALUE_OR_YEAR_NOT_NUMERIC`.
5. `C-carbon_capture-2~3` (special route) — `amine substitution
   novelty margin`: 1 proposal, `RECORD_ID_NOT_IN_RETRIEVED_POOL`.
6. `C-carbon_capture-7~3` (special route) — `primary evidence
   quantified prediction`: 1 proposal,
   `RECORD_ID_NOT_IN_RETRIEVED_POOL`.
7. `C-data_center_thermal-1~2` (special route) — `predictive novelty
   differentiation`: 3 proposals, all `VALUE_OR_YEAR_NOT_NUMERIC`.
8. `C-power_electronics-6~2` (special route) — `maximum power point
   tracking efficiency`: 4 proposals, all
   `VALUE_OR_YEAR_NOT_NUMERIC`.
9. `C-semiconductor_fab-7~4` (special route) — `control oriented
   modeling`: 6 proposals, all `VALUE_OR_YEAR_NOT_NUMERIC`.
10. `C-wind-2~2` (special route) — `novelty of defect detection
    method`: 2 proposals, all `VALUE_OR_YEAR_NOT_NUMERIC`.

No death reached a frontier, backcast, precondition, future-dependency,
duplicate-mechanism, prior-art, causal-novelty, attacker, or
engineering stage — those failure classes were never exercised in this
run. The 3 GA-2-ineligible seeds (`C-batteries_ev-1`,
`C-heat_exchanger-1~4`, `C-machining-1~4`) were never attempted (no
death cause manufactured); the 387 non-technical rejections were never
eligible.

## 5. Infrastructure incidents (disclosed, quarantined, remediated)

1. **2026-09-05T20:17Z — test-fixture contamination of
   `TVM_CONSTRUCTED.json`** (Art. IX violation by the first version of
   the new allocation tests; quarantined with bytes preserved at
   `incidents/`; the real run had written nothing; no sealed artifact
   consumed the contaminated file). Remediation: all module path
   constants are patched in tests; runner hardened with per-rung
   checkpointing.
2. **Session-timeout orphans:** the first TVM construction invocation
   was killed by the 570 s session timeout after 5 rung attempts
   (end-of-stage write had not happened — 5 fabric + 5 LLM calls
   orphaned with no records); a background `nohup` attempt was killed
   by session teardown (0–1 further orphaned call). These ~5–6 calls
   are incident overhead ABOVE the sealed caps (13 GA-1b + 12 TVM
   recorded calls, both exactly within budget); they produced no
   entries and no verdicts.

## 6. What was actually proven (positive results of the run)

1. The sealed gradient arm ran **end-to-end for the first time**:
   seal → GA-1b → GA-2 → tvm-build → tvm-freeze → GA-3 → (GA-4..GA-9
   no-ops on an empty map) → finalize, with every stage re-verifying
   the seal and every unit checkpointed.
2. The **allocation discipline held in production**: exactly the 10
   sealed seeds were attempted in priority order; the 3 ineligible
   and 387 non-technical candidates were never touched (no death
   cause manufactured).
3. **GA-1b's span-gated extraction works** with the pinned model:
   13/13 verbatim-grounded extractions from frozen death records —
   evidence recovery, zero invention.
4. The **TVM instrument's failure mode is now measured** (0/34
   admission; 91% numeric-format non-compliance) — a real
   instrument-calibration datum for the next arm, and a demonstrated
   enforcement that NO LLM-asserted number entered the map (the
   sealed hard rule held: rejected entries counted as nothing).
5. The **temporal control arm is preserved** (0/13, hash
   e7c4ecd5…, byte-identical, re-verified at every stage invocation).

## 7. Phase G — no buyer promotion

Zero survivors → zero promotions. No artifact of this run approaches a
buyer package, and nothing in this run may be cited as one (the normal
pipeline entry requires GA-7/8/9 passage that never occurred). The run
STOPS at this report; physical spend and commercial contact remain
human decisions (Art. XXXVIII).

## 8. Call accounting (actual)

| stage | sealed cap | recorded actual | notes |
|---|---|---|---|
| GA-1b LLM | 13 | 13 | no retries needed |
| TVM fabric | 12 | 12 | +~5–6 orphaned (incidents §5) |
| TVM LLM | 12 | 12 | +~5–6 orphaned (incidents §5) |
| GA-4..GA-9 | 10 each | 0 | no FAST_MOVERS_RANKED seeds |
| out_tokens_per_llm_call | 2600 | 2600 | pinned, unchanged |
