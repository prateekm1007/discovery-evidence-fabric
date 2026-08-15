# Invention Engine V2 — Forensic Invalidation

**Status: INVALID_UNCORRECTED_ADVERSARIAL_GATE**

**V2 commit:** `26fb7b6d8cad16c68deb5874089c24a336f1b956`
**V2 root hash:** `95720bc41ef6fe39`

## Validity Assessment

| Dimension | Valid | Reason |
|-----------|-------|--------|
| **scientific_result_valid** | **false** | Adversarial/prior-art gates were not calibrated. LLM fabricated patent citations. Generation and adjudication used the same model. |
| **security_result_valid** | **true** | All hard-coded secrets removed. Secret-scanning test passes. Environment-only credentials. |
| **operational_result_valid** | **true** | Full pipeline executed. Per-stage checkpointing worked. Operational failures distinguished from scientific rejections. |

## Why the 0/15 Result Is Invalid

The V2 result of 0/15 invention candidates (0% conversion rate) is **NOT** evidence that AICs cannot become inventions. It is an artifact of an uncalibrated evaluation pipeline:

### 1. Circular evaluation (generation = adjudication)
V2 used `meta/llama-3.1-8b-instruct` as BOTH the generation model AND the adjudication model. The same model that generated the invention also judged it. This is circular — the model's self-consistency does not constitute independent scientific evaluation.

### 2. 96 adversarial kills had zero external evidence
The V2 adversarial evaluator produced KILL verdicts across 7 dimensions for 15 architectures (105 total dimension-verdicts). **None** of these KILLs cited external evidence:
- No published device failure records
- No peer-reviewed papers
- No engineering standards
- No patent claims
- No content hashes
- No source URLs

The evaluator's own reasoning was treated as evidence, violating V4 Correction 5 (boundary-condition evidence standard).

### 3. Fabricated patent citations
The V2 prior-art assessment was performed by the same LLM. It invented patent numbers that were never retrieved from any real database:

| Invention | Fabricated Citations |
|-----------|---------------------|
| INV_V2_001 | "US 2018/0244441 A1", "WO 2015/144444 A1" |
| INV_V2_002 | "US Patent 9,945,661 B2", "US Patent 10,444,111 B2" |
| INV_V2_005 | "US Patent 9,945,654", "US Patent 10,555,871" |

These are **UNVERIFIED_MODEL_CITATION** — they cannot be used as prior-art evidence. They are preserved as evidence of the failure mode.

### 4. Prior-art firewall not enforced
V4 Correction 10 requires that prior-art references originate from the frozen prior-art retrieval subsystem, not from the LLM. Allowed states:
- NO_MATCH_FOUND, TOPICAL_RELATED, POSSIBLE_RELEVANCE, UNRESOLVED → cannot kill
- SPECIFIC_DISCLOSURE, IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE → can kill

V2 did not enforce this. The LLM generated its own "ADJACENT_PRIOR_ART" classification with fabricated citations, and this was treated as a valid prior-art assessment.

### 5. Model not calibrated
The calibrated evaluator (`evaluator_v1_frozen`, prompt_hash `70bb690572d1fec1`, ontology `c8ae93b52fb2c09d`, Mistral-only) was not used. Llama-3.1-8B was substituted as the adjudication model without any calibration against external evidence. No 35-case calibration suite was run. The adversarial verdicts have unknown accuracy.

### 6. Protocol freeze not structurally before execution
The V2 protocol (`INVENTION_GENERATION_PROTOCOL_V2.json`) was committed in the **same commit** as the V2 results. There is no cryptographic proof that the protocol was frozen before the first API call. The protocol-commit-precedes-results-commit invariant was not enforced.

## What IS Valid

### Security (valid)
- All hard-coded API keys removed from source code
- Secret-scanning regression test added (scans for `nvapi-`, `ghp_`, `sk-or-v1-`, `csk-` patterns)
- Environment-only credential access enforced
- 69/69 tests pass including 4 secret-scanning tests

### Operational (valid)
- Full pipeline executed (5 architectures, 3 refinement rounds, 7 adversarial dimensions)
- Per-stage checkpointing retained lineage even when later stages failed
- Operational failures (5 PASS3_CALL_FAILED) distinguished from scientific rejections (15 INVENTION_KILLED)
- 20/20 AICs attempted, 15 reached final gate

## V2 Artifact Preservation

All V2 artifacts are **preserved unchanged** as historical evidence of the failure mode:

- `inventions/v2/raw/INV_V2_001..020.json` (20 raw invention records)
- `inventions/v2/candidates/INV_V2_001..020.json` (20 candidate dossiers)
- `inventions/v2/reports/INV_V2_001..020.md` (20 human-readable reports)
- `inventions/v2/checkpoints/` (per-stage lineage)
- `experiments/TOP20_INVENTION_GENERATION_V2_RESULTS.json`
- `experiments/TOP20_INVENTION_GENERATION_V2_REPORT.md`
- `experiments/INVENTION_GENERATION_PROTOCOL_V2.json`

**Not modified. Not deleted.**

## Required Remediation Before Any Future Invention Run

1. **V4 corrections 5-8** must be implemented and tested:
   - Boundary-condition evidence standard (external evidence required for KILL)
   - Prior-art firewall (non-kill states cannot become PRIOR_ART=KILL)
   - ADVERSARIAL_INVALID disposition (verdict/reason/evidence conflicts)
   - Evidence → adversarial ordering (skip adversarial if evidence fails)

2. **35-case adversarial calibration suite** must be built with external evidence:
   - 5 mechanism-validity, 5 transfer, 5 boundary, 5 obviousness, 5 non-obviousness, 5 specific prior-art, 5 topical-only prior-art
   - Oracle evidence must be external (published records, patents, papers, standards)
   - Acceptance: ≥80% aggregate, ≥70% in every critical category

3. **Generation ≠ adjudication**: fast model for generation, calibrated strong model for adjudication

4. **Calibrated evaluator** (`evaluator_v1_frozen`, Mistral-only) must be used for adjudication

5. **Protocol commit precedes results commit**: protocol must be committed in a separate commit before any results

6. **Prior-art references** must originate from frozen prior-art retrieval subsystem (not LLM)

7. **V3 corrected replay** must be run on frozen V3 candidates (historical analysis, not new synthesis)

## Do NOT

- Interpret the 0/15 V2 result as evidence that AICs cannot become inventions
- Process AIC 21–416
- Run another invention-generation experiment until calibration passes
- Use any V2 model-generated patent citation as prior-art evidence
- Substitute a weaker model or weaker evidence standard to make the experiment run
