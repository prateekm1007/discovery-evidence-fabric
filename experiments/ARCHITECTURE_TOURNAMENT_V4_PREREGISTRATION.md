# Architecture Tournament V4 — Pre-Registration

## Status: PRE-REGISTERED (not yet executed)

## Date: 2026-08-15

## V3 Historical Status

**ARCHITECTURE_TOURNAMENT_V3 = HISTORICAL_PILOT_NOT_PRODUCT_SELECTION**

V3 results are frozen at commit `70f68d3e81391970f3a95e83efd42f2bcc08521b`.
V3 results will NOT be modified.

The V3 corrected replay showed that the original adversarial evaluator was uncalibrated:
- Original V3: 0-5 AICs per arm (0-5% yield)
- Corrected replay: 54-67 AICs per arm (54-67% yield)

This 10-50x inflation under corrected rules confirms V3 was an artifact of an
overly aggressive adversarial evaluator, not a valid architecture comparison.

## Objective

Determine empirically which architecture produces the strongest validated
invention output, under corrected adversarial evaluation with
external-evidence-grounded calibration.

## Arms

| Arm | Description |
|-----|-------------|
| M0 | MACRO_ONLY — broad evidence, no Micro knowledge |
| M1 | MICRO_ONLY — device/experience-constrained, no Macro knowledge |
| M2 | MACRO_TO_MICRO — Macro memory → Micro candidates |
| M3 | MICRO_TO_MACRO — Micro memory → Macro candidates |
| M4 | RECURSIVE_MACRO_MICRO — 4 rounds, committed memory files |
| M4B | INFORMATION_MATCHED_NON_RECURSIVE_CONTROL |
| M4C | COMPUTE_MATCHED_NON_RECURSIVE_CONTROL |

## Frozen Hashes

| Hash | Value |
|------|-------|
| routing_policy_sha256 | `79a928166bce6fb9faf2368c9aba2ffc9f1aaeacc4e73bbade25218d4f76470d` |
| problem_corpus_root | `40adb5d0157f624a` |
| evidence_packets_root | `b9faf80e8aabf16b` |
| micro_seed_manifest_root | `a8b88c8fdcc961de` |
| ontology_hash | `cd824023412623c6` |
| v3_preregistration_sha256 | `50971eadc2464e0e7bbf14a68574e38c1b4a3ed0ab3ca4d30c097897e0d867e6` |
| v4_preregistration_sha256 | `8d86a3264509834366d6eb03b6ef6082782dd143696feea1fac2dc6a0e4d93d2` |

## Eight Auditor Corrections

### 1. Adversarial Calibration Oracles

The 35-case adversarial calibration suite MUST NOT obtain ground truth from the
evaluator being tested. Use external evidence by category:

- **BOUNDARY_CONDITION**: published device failure/MDR records, peer-reviewed case
  reports, engineering/physics literature, recognized engineering standards
- **PRIOR_ART**: real patent claims, same evidentiary standard as prior-art oracle
- **OBVIOUSNESS**: patent examiner rejections, prosecution records, publications
- **NON_OBVIOUSNESS**: cases with documented separation from cited prior art
- **MECHANISM_VALIDITY/TRANSFER**: source literature with identifiable mechanism passages

Every calibration case contains: `oracle_source_id`, `oracle_source_type`,
`oracle_source_hash`, `oracle_evidence_span`, `oracle_reason`, `expected_verdict`.

**An LLM-generated label is NOT an oracle.**

### 2. Calibration Acceptance Threshold

- Minimum: ≥80% accuracy on non-ambiguous cases
- No critical category may have <70% accuracy
- If threshold fails: `ADVERSARIAL_CALIBRATION_BLOCKED`
- Do not tune thresholds silently

### 3. M4 Context Isolation

Each M4 round has committed memory files:
- `M4_R0_MACRO_MEMORY.json`, `M4_R0_MICRO_MEMORY.json`
- `M4_R1_MACRO_MEMORY.json`, `M4_R1_MICRO_MEMORY.json`
- `M4_R2_MACRO_MEMORY.json`, `M4_R2_MICRO_MEMORY.json`
- `M4_R3_MACRO_MEMORY.json`, `M4_R3_MICRO_MEMORY.json`

Each file is: immutable, content-addressed, hashed, committed in round manifest.

Round n may read ONLY frozen memory from round n-1. No live Python variable
may substitute for the committed memory artifact.

Machine assertion: `context_source_mode == "COMMITTED_FILE"`.
Violation: `M4_INVALID_CONTEXT_SOURCE`.

### 5. Boundary Condition Evidence Standard

A `BOUNDARY_CONDITION=KILL` requires:
- specific boundary
- failure mechanism
- why candidate crosses the boundary
- **external evidence** (published record, peer-reviewed paper, engineering
  reference, or recognized standard)

The evaluator's own reasoning is NOT evidence.
If no external evidence: `INSUFFICIENT_EVIDENCE`. Do NOT kill.

### 6. ADVERSARIAL_INVALID Disposition

If verdict conflicts with reason, OR reason conflicts with required evidence standard:
- `ADVERSARIAL_INVALID` → `EVALUATION_FAILED`
- Candidate does NOT become AIC
- Is NOT killed as an invention defect
- Is NOT counted as a successful adversarial survivor
- Is eligible for controlled re-evaluation after evaluator correction

Records: `invalid_dimension`, `invalid_reason`, `re_evaluation_required = true`.

### 7. V3 Source Hash Reconstruction

For V3 replay: join `candidate.source_ids` to Phase-D evidence packet source `content_hash`.
- If source_id found: reconstruct `source_hash` retroactively
- If source_id missing: `PROVENANCE_INCOMPLETE`
- `source_hash_reconstruction_method = "PHASE_D_PACKET_JOIN"`
- Do not create a new retrieval universe for V3 replay

### 8. Preliminary M0 Promotion Rule

`WINNING_ARCHITECTURE` requires:
- ≥5 percentage-point lift over best preregistered comparator
- Fisher exact test
- Bonferroni-adjusted p < 0.05

If M0 has highest yield but fails significance: `PRELIMINARY_BEST_M0`.
Never: `WINNING_ARCHITECTURE`.

### 9. Cheap Boundary Pre-Filter

Deterministic pre-filter before the LLM `BOUNDARY_CONDITION` evaluator.

If a KILL reason contains conditional language (`if`, `could`, `might`, `may`)
AND has no external citation/evidence identifier:
- Automatically classify: `INSUFFICIENT_EVIDENCE`
- Do not permit such a reason to become KILL
- This is a SCREEN, not the final scientific evaluator

### 10. Adversarial Prior-Art Firewall

The adversarial evaluator consumes the frozen prior-art state.

**Non-kill states** (CANNOT become adversarial `PRIOR_ART=KILL`):
- `TOPICAL_RELATED`
- `POSSIBLE_RELEVANCE`
- `NO_MATCH_FOUND`
- `UNRESOLVED_INSUFFICIENT_EVIDENCE`

**Kill states** (may produce `PRIOR_ART=KILL`):
- `SPECIFIC_DISCLOSURE`
- `IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE`

Regression cases required for every state.

### 11. Evidence → Adversarial Order

Hard execution order:
```
generation → target_alignment → evidence_verification → prior_art → adversarial → aic
```

If evidence fails: adversarial MUST NOT run.
Store: `adversarial_status = NOT_RUN`, `adversarial_not_run_reason = EVIDENCE_GATE_FAILED`.

## V4 Start Gate

V4 may begin only if ALL of the following pass:

| Condition | Status |
|-----------|--------|
| V3 forensic audit complete | ✅ |
| Items 5-8 regression pass | ✅ (37/37 tests) |
| V3 corrected replay complete | ✅ |
| Adversarial calibration pass | ❌ PENDING (35-case suite not yet built) |
| M4 context isolation tests pass | ✅ |
| M4C compute matching tests pass | ✅ |
| Source provenance tests pass | ✅ |

**Current status: `TOURNAMENT_BLOCKED`** — adversarial calibration suite must be
built and pass ≥80% threshold before V4 execution.

## AIC Definition

A candidate becomes an `AUTOMATED_INVENTION_CANDIDATE` only if:
- Evidence passes (verified spans + mechanism evidence)
- Target aligned
- Specific prior-art passes
- All adversarial dimensions pass
- Falsification exists
- Provenance complete

Do not call generated hypotheses AICs.
Do not call them novel.
Do not call them patentable.

## Primary Metric

`AIC_YIELD = AICs / 100 candidate opportunities`

## Recursive Lift

M4 may claim `RECURSIVE_LIFT_CANDIDATE` ONLY IF:
- M4 > M4B
- M4 > M4C
- M4 ≥ best independent baseline + 5pp
- Preregistered statistical comparison passes

Otherwise classify exactly:
- `INFORMATION_BUDGET_EFFECT_ONLY`
- `COMPUTE_BUDGET_EFFECT_ONLY`
- `RECURSIVE_LIFT_NOT_DETECTED`
- `NO_WINNER`

## Model Agnosticism

No model is hard-coded into architecture code.
Approved routing pools: Mistral, NVIDIA.
Router may switch intra-provider or inter-provider due to: 429, timeout, 5xx,
provider outage, materially excessive latency.
Every candidate records exact provider/model provenance.
Routing policy remains frozen for V4.

## Invariants

1. V3 remains `HISTORICAL_PILOT_NOT_PRODUCT_SELECTION` — do not change V3 results
2. Do not generate V4 candidates until all start-gate conditions pass
3. Do not rerun 700 V3 candidates
4. Do not modify Micro-2 or Macro-1
5. Do not start simulation
6. Adversarial calibration suite must use EXTERNAL evidence, never LLM labels
7. M4 context isolation requires committed files, not live variables
8. Evidence→adversarial ordering is hard (skip adversarial if evidence fails)
9. Prior-art firewall: non-kill states cannot become PRIOR_ART=KILL
10. Boundary KILL requires external evidence; conditional language without citation is screened
11. WINNING_ARCHITECTURE requires Fisher exact + Bonferroni p<0.05 + ≥5pp lift
