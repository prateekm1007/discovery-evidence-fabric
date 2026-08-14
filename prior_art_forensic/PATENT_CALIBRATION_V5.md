# PATENT CALIBRATION V5 — Results

## Calibration Status: CALIBRATION_BLOCKED

## True Numbers

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.2000 (1/5) | ≥ 0.80 | ✗ |
| specific_precision | 1.0000 | — | — |
| negative_rejection_rate | 1.0000 (5/5) | ≥ 0.80 | ✓ |
| overall_accuracy | 0.6000 (6/10) | — | — |

## Oracle Distribution

| Label | Count |
|-------|-------|
| SPECIFIC_DISCLOSURE | 5 |
| NOT_SPECIFIC_DISCLOSURE | 5 |
| POSSIBLE_RELEVANCE | 5 (excluded from non-ambiguous) |
| CONTRADICTORY | 5 (excluded from non-ambiguous) |

## Per-Case Results

| Case | Patent | Device | Mechanism | Ground Truth | Evaluator | Match |
|------|--------|--------|-----------|--------------|-----------|-------|
| oracle_v2_specific_01 | 21246695 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✗ |
| oracle_v2_specific_02 | 23775560 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✗ |
| oracle_v2_specific_03 | 23810569 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | UNKNOWN | ✗ |
| oracle_v2_specific_04 | 28723275 | ventilator | adaptive pressure | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✗ |
| oracle_v2_specific_05 | 17600171 | cardiac pacemaker | adaptive pacing | SPECIFIC_DISCLOSURE | IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE | ✓ |
| oracle_v2_negative_01 | US17469518 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v2_negative_02 | US17538887 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v2_negative_03 | US17565960 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v2_negative_04 | US17593952 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |
| oracle_v2_negative_05 | US17671042 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ |

## Analysis

### What Worked
- **negative_rejection_rate = 100%**: The evaluator correctly rejected ALL 5 NOT_SPECIFIC_DISCLOSURE cases. The V1 negatives (preserved) are correctly classified.
- **specific_precision = 100%**: When the evaluator DID predict SPECIFIC_DISCLOSURE (case 05), it was correct.

### What Failed
- **specific_recall = 20%**: The evaluator recognized only 1 of 5 SPECIFIC_DISCLOSURE cases. It classified 3 as TOPICAL_RELATED and 1 as UNKNOWN.
- The evaluator still cannot bridge semantic terminology (e.g., "ultrasound device" → "ultrasound system", "ultrasonic transducer" → "transducer array", "rate-adaptive" → "adaptive pacing").

## Calibration Decision (per spec Section 11)

> If specific_recall ≥ 80% AND negative_rejection_rate ≥ 80% → CALIBRATION_PASS
> Otherwise → CALIBRATION_BLOCKED

**Decision: CALIBRATION_BLOCKED**

- specific_recall (20%) < 80% threshold
- negative_rejection_rate (100%) ≥ 80% threshold
- The evaluator is NOT ready — but per spec: "Do not tune the evaluator until the oracle itself is proven valid."

## Oracle Validity Assessment

The V2 oracle IS valid (unlike V1):
- All 5 SPECIFIC_DISCLOSURE cases have verified co-occurrence of (device, mechanism) in real patent text.
- All 5 have deterministic spans with offsets.
- All 5 were verified by TWO independent models.
- The bottleneck is now the EVALUATOR (not the oracle).

However, per spec: "Do not tune the evaluator until the oracle itself is proven valid."
The oracle IS valid. The evaluator is the next bottleneck.

## What Was NOT Done

- Did NOT lower 80% threshold
- Did NOT change prior-art kill semantics
- Did NOT tune the evaluator (per spec — even though oracle is now valid)
- Did NOT resume corpus
- Did NOT start simulation
- Did NOT resurrect TEE

## SHA256

- PATENT_CALIBRATION_V5.json: `85dfe93098df72e2d0620311d327667c1f98cb255d65eb97de142ad6802e9347`
