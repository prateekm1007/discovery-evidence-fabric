# PATENT CALIBRATION V6 — Results

## Calibration Status: EVALUATOR_REPAIR_REQUIRED

## True Numbers

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.6000 (3/5) | ≥ 0.80 | ✗ |
| specific_precision | 1.0000 | — | — |
| negative_rejection_rate | 1.0000 (5/5) | ≥ 0.80 | ✓ |
| overall_accuracy | 0.8000 (8/10) | — | — |
| parse_failures | 0 | — | — |
| ambiguous_cases_excluded | 10 | — | — |

## Exit Rule (per spec Section 10)

- If oracle validity fails → CALIBRATION_BLOCKED
- If oracle validity passes but evaluator <80% → EVALUATOR_REPAIR_REQUIRED
- If oracle validity passes AND specific_recall ≥80% AND negative_rejection_rate ≥80% → CALIBRATION_PASS

**Oracle validity: VALID** (all 5 SPECIFIC cases pass deterministic validator + dual-model audit)
**specific_recall: 60%** (below 80%)
**negative_rejection_rate: 100%** (above 80%)

**Decision: EVALUATOR_REPAIR_REQUIRED**

## Per-Case Results

| Case | Patent | Device | Mechanism | Ground Truth | Evaluator | Match |
|------|--------|--------|-----------|--------------|-----------|-------|
| oracle_v3_specific_01 | 20300116 | continuous glucose monitor | biocompatible membrane | SPECIFIC_DISCLOSURE | IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE | ✓ |
| oracle_v3_specific_02 | 21246695 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✗ |
| oracle_v3_specific_03 | 22095037 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | POSSIBLE_RELEVANCE | ✗ |
| oracle_v3_specific_04 | 23695666 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ |
| oracle_v3_specific_05 | 22839593 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ |
| oracle_v3_negative_01 | US17469518 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v3_negative_02 | US17538887 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v3_negative_03 | US17565960 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v3_negative_04 | US17593952 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v3_negative_05 | US17671042 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |

## Analysis

### What Worked
- **negative_rejection_rate = 100%**: All 5 NOT_SPECIFIC_DISCLOSURE cases correctly rejected
- **specific_precision = 100%**: When evaluator predicted SPECIFIC, it was always correct
- **3/5 SPECIFIC cases recognized**: cases 01, 04, 05 correctly identified as SPECIFIC/IDENTICAL

### What Failed
- **2/5 SPECIFIC cases missed**: 
  - Case 02 (ultrasound+transducer, corpus 21246695): evaluator said TOPICAL_RELATED
  - Case 03 (spinal fusion+pedicle screw, corpus 22095037): evaluator said POSSIBLE_RELEVANCE
- The evaluator still cannot bridge semantic terminology in some cases

## Improvement vs V5
- V5 specific_recall: 20% (1/5)
- V6 specific_recall: 60% (3/5)
- Improvement: +40pp (from using V3 oracle with better relationship_spans)

## What Was NOT Done

- Did NOT lower 80% threshold
- Did NOT change prior-art kill semantics
- Did NOT tune evaluator prompt (per spec)
- Did NOT resume corpus
- Did NOT start simulation
- Did NOT resurrect TEE

## SHA256

- PATENT_CALIBRATION_V6.json: `d48385ee4008e45c16c181ab4e6334491274d8ee0c5c362ad7a3a2868b11106e`
