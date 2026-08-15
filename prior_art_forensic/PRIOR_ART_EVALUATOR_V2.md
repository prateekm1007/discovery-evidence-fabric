# PRIOR-ART EVALUATOR V2

## Status: V2_DEV_FAIL

## V2 Hypotheses (per spec Section 2)

| Hypothesis | Description | V2 Improvement |
|------------|-------------|----------------|
| H1: Terminology bridging | V1 missed cases where patent uses synonym not in ontology | V2 expands ontology with more synonyms |
| H2: Component/system mapping | V1 missed component→system relationships | V2 adds component→system mappings (e.g., probe→ultrasound system) |
| H3: Claim + linked specification reasoning | V1 failed on SPECIFICATION_LINKAGE cases | V2 prompt explicitly instructs combining claim+specification |
| H4: Functional relationship extraction | V1 returned POSSIBLE_RELEVANCE when relationship was present | V2 adds more functional indicators + implicit relationship detection |

## Frozen Evaluator Configuration

| Parameter | Value |
|-----------|-------|
| Primary model | mistral-large-latest |
| Primary provider | Mistral API |
| No primary fallback | True |
| Secondary model | glm-4-plus |
| Secondary provider | z-ai CLI |
| Temperature | 0.0 |
| Prompt hash | 89111f1581b7c704 |
| Ontology version | 40171c0fbbbef96a |
| Parser version | frozen_v2_markdown_truncation_fallback |
| Evaluator version | evaluator_v2_frozen_mistral_only |

## V2 Development Test (NEW dev set, not V1 dev or V1 holdout)

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.7778 | >= 0.80 | ✗ |
| negative_rejection | 1.0000 | >= 0.80 | ✓ |
| specific_precision | 1.0000 | — | — |
| call_failed | 3 | 0 | ✗ |
| **DEV PASS** | | | **✗** |

### V2 Dev Case Details

| Case | Device | Mechanism | GT | Primary | Secondary | Match | Mode |
|------|--------|-----------|----|---------|-----------|-------|------|
| 21232932 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 22661520 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 19514422 | intraocular lens | antimicrobial coating | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | TOPICAL_RELATED | ✗ | RELATIONSHIP_EXTRACTION |
| 24465160 | ventilator | adaptive pressure | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 25850278 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 19520973 | intraocular lens | antimicrobial coating | SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✗ | FALSE_NEGATIVE |
| 23023486 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 22325962 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 24470417 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | POSSIBLE_RELEVANCE | ✗ | CALL_FAILED |
| 20585608 | coronary stent | drug-eluting coating | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 17452281 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17463727 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17464461 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17469518 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | NO_MATCH_FOUND | ✗ | CALL_FAILED |
| 17471846 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17477161 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17488446 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17523403 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17523848 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | NO_MATCH_FOUND | ✗ | CALL_FAILED |
| 17527153 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |

### V2 Dev Failure Modes

{
  "TRUE_POSITIVE": 7,
  "RELATIONSHIP_EXTRACTION": 1,
  "FALSE_NEGATIVE": 1,
  "CALL_FAILED": 3,
  "TRUE_NEGATIVE": 8
}

## V1 vs V2 Comparison

| Metric | V1 Dev | V1 Holdout | V2 Dev |
|--------|--------|------------|--------|
| specific_recall | 1.0000 | 0.7778 | 0.7778 |
| negative_rejection | 1.0000 | 1.0000 | 1.0000 |
| specific_precision | 1.0000 | 1.0000 | 1.0000 |
| call_failed | 0 | 3 | 3 |
| PASS | ✓ | ✗ | ✗ |

## Exit State: V2_DEV_FAIL

Per spec Section 5: "If fail: V2_DEV_FAIL. Stop."

V2 did NOT proceed to holdout mining or holdout test.

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (6/6 regression PASS, 11/11 tests PASS)
- No generic semantic similarity
- No similarity-only prior-art promotion
- No lowering of specific-disclosure standard
- No corpus generation
- No simulation
- TEE still quarantined
- V1 frozen — not modified
- V1 holdout remains sealed historical evidence
