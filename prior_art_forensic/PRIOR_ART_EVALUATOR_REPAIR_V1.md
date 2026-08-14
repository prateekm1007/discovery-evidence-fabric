# PRIOR-ART EVALUATOR REPAIR V1

## Status: HOLDOUT_CONSTRUCTION_BLOCKED

## Frozen Evaluator Configuration

| Parameter | Value |
|-----------|-------|
| Primary model | mistral-large-latest |
| Primary provider | Mistral API |
| Secondary model | glm-4-plus |
| Secondary provider | z-ai CLI (glm-4-plus) |
| Temperature | 0.0 |
| Parser | line-based with truncation normalization |
| Ontology map | TERM_ONTOLOGY (18 entries covering 10 device/mechanism pairs) |
| Evaluator version | evaluator_repair_v1_frozen |

## Repair Summary

The repaired evaluator addresses:
1. **Terminology normalization** — bounded ontology with 18 entries covering 10 device/mechanism pairs
2. **Device/component/system relationships** — explicit equivalence mappings (e.g., "glucose sensor" = "continuous glucose monitor")
3. **Claim + linked specification reasoning** — evaluator may combine tightly linked patent sections when functional relationship is explicit
4. **Functional relationship extraction** — explicit indicators: "configured to", "comprises", "wherein", "permeable to", etc.

Every resolved equivalence points to: source text span, ontology mapping, mapping confidence.

No generic semantic similarity is used.

## Development Test Results (V3 development set)

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.8000 | ≥ 0.80 | ✓ |
| negative_rejection | 1.0000 | ≥ 0.80 | ✓ |
| specific_precision | 1.0000 | — | — |
| **DEV PASS** | | | **✓** |

### Dev Case Details

| Case | Device | Mechanism | Ground Truth | Primary | Secondary | Match | Failure Mode |
|------|--------|-----------|--------------|---------|-----------|-------|--------------|
| oracle_v3_specific_01 | continuous glucose monitor | biocompatible membrane | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_02 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | TOPICAL_RELATED | ✗ | RELATIONSHIP_EXTRACTION_FAILURE |
| oracle_v3_specific_03 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_04 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_05 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| oracle_v3_negative_01 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_02 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_03 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_04 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_05 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |

### Dev Failure Modes

{
  "TRUE_POSITIVE": 4,
  "RELATIONSHIP_EXTRACTION_FAILURE": 1,
  "TRUE_NEGATIVE": 5
}

## Holdout Status

- SPECIFIC holdout cases mined: 9 (target: 10)
- NOT_SPECIFIC holdout cases mined: 12 (target: 10)
- Patents scanned: 81241

**Status: HOLDOUT_CONSTRUCTION_BLOCKED** — only 9 SPECIFIC holdout cases available (need 10 per spec Section 3)

Per spec: "If fewer than 10 valid positives can be obtained: do NOT substitute 2/5/etc. Continue mining or declare: HOLDOUT_CONSTRUCTION_BLOCKED"

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (6/6 regression PASS)
- No broad semantic similarity
- No corpus generation
- No simulation
- TEE still quarantined
