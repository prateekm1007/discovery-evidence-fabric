# AUTONOMOUS CALIBRATION V3.4 — PROTOCOL

**Status**: `CALIBRATION_BLOCKED` (pre-registered, frozen before inference)
**Base commit**: `1e93a51`
**Protocol SHA-256**: `80ea371692acd1eec178b34ad113049f4cc10ddff707a0c2eddf678904db483f`

## V3.3 Frozen (True Numbers)

| Metric | Value | Threshold | Pass? |
|---|---|---|---|
| Accuracy | 60% | ≥85% | ✗ |
| False-elite | 0% | ≤10% | ✓ |
| False-reject | 20% | ≤10% | ✗ |
| Cited-art recall | 100% | ≥90% | ✓ |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 60% | ≥85% | ✗ |
| 103 accuracy | 15% | ≥80% | ✗ |

**2/7 thresholds met.** 102 and 103 are the dominant failures.

## V3.4 Critical Fixes

### Fix 1: Passage-Grounded 102

Every claim limitation requires:
- `limitation_id`
- `reference_id`
- `disclosure_type` (EXPRESS / NECESSARILY_INHERENT / NOT_DISCLOSED / UNCERTAIN)
- `exact_passage` (verbatim from reference)
- `claim_number / paragraph`
- `mapping_rationale`
- `mapping_confidence`

**Forbidden disclosure types:** POSSIBLE / PLAUSIBLE / TOPICAL / SEMANTICALLY_SIMILAR

### Fix 2: Inherency Firewall

INHERENCY requires **NECESSARY** — not LIKELY / PROBABLE / POSSIBLE.

Machine assertion: `inherency_necessity_proof`. If missing → NOT_DISCLOSED / UNCERTAIN.

### Fix 3: Arrangement Firewall

After element mapping, verify the reference discloses the **REQUIRED RELATIONSHIPS**.

`A disclosed + B disclosed` ≠ `A+B arranged as claimed` unless arrangement is actually supported.

### Fix 4: NoveltyEvidenceV34 Decision Object

```
single_reference
all_limitations_mapped
all_relationships_mapped
passage_evidence
inherency_necessity
arrangement_supported
uncertainties
final_result
```

**102_KILL legal only if:**
- `all_limitations_mapped = TRUE`
- AND `all_relationships_mapped = TRUE`
- AND `all_mapping_types ∈ {EXPRESS, NECESSARILY_INHERENT}`
- AND `uncertainty_count = 0`

### Fix 5: False-Reject Forensic

For the 7 V3.3 false-reject cases, audit:
- `old_102_mapping`
- `correct_mapping`
- `bad_inference`
- `source_passage`
- `root_cause`

Classify: ELEMENT_OVERCLAIM / ARRANGEMENT_OVERCLAIM / INHERENCY_ERROR / REFERENCE_MISMATCH / CLAIM_INTERPRETATION_ERROR / LLM_JUDGMENT_ERROR

### Fix 6: ObviousnessEvidenceV34 (Independent 103)

Fields: `closest_prior_art` + `objective_problem` + `difference_elements` + `secondary_reference` + `motivation` + `technical_compatibility` + `reasonable_expectation` + `teaching_away` + `could` + `would` + `why` + `technical_effect` + `hindsight`

**103 adversary does NOT see:** generator rationale, commercial rationale, final invention explanation.

**103 adversary receives ONLY:** canonical claim + verified evidence + prior-art mappings + technical context.

### Fix 7: COULD/WOULD Rule

103 requires:
- `COULD = TRUE`
- AND `WOULD = TRUE`
- AND `MOTIVATION_SUPPORTED = TRUE`
- AND `EXPECTED_SUCCESS_SUPPORTED = TRUE`

If any missing → `103 = INSUFFICIENT_EVIDENCE` (not OBVIOUSNESS_RISK).

### Fix 8: Pre/Post-Disclosure Two-Pass

- **Pass A:** Hide the claimed solution's novelty thesis.
- **Pass B:** Reveal the full claim.
- Compare: motivation, difference, combination, expected success.
- Large divergence → `HINDSIGHT_RISK_HIGH`.

### Fix 9: Cited-Art Mapping Accuracy

For each calibration case with examiner-cited reference, system must reproduce:
- cited reference
- claim mapping
- reason it matters

Recall alone is not enough.

### Fix 10: Search Recall ≥80%

For missed references, identify:
- query-family miss
- terminology miss
- classification miss
- citation miss
- semantic miss
- source failure

Fix the relevant search family, not the aggregate number.

## Acceptance Gate

| Metric | Threshold |
|---|---|
| Overall accuracy | ≥ 85% |
| False-elite rate | ≤ 10% |
| False-reject rate | ≤ 10% |
| Cited-art recall | ≥ 90% |
| Search recall | ≥ 80% |
| 102 accuracy | ≥ 85% |
| 103 accuracy | ≥ 80% |

## Output Artifacts

`PROTOCOL.json` · `PROTOCOL.sha256` · `102_FORENSIC.json` · `103_FORENSIC.json` · `SEARCH_RECALL.json` · `CLAIM_MAPPINGS.json` · `CASE_RESULTS.json` · `ERROR_ANALYSIS.json` · `METRICS.json` · `REPORT.md`

## Stop Condition

DO NOT RUN 50→5. STOP FOR CEO AUDIT.
