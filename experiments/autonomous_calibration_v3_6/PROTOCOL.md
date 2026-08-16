# AUTONOMOUS CALIBRATION V3.6 — PROTOCOL

**Status**: `CALIBRATION_BLOCKED` (pre-registered, frozen before inference)
**Base commit**: `1b5a8ca`
**Protocol SHA-256**: `c33b89c48d086f6da8e374a0df705c2cbc0de4400f83143cca717b1c2b71c7c1`

## Why V3.6

V3.5 identified the root cause: **motivation_insufficient=85%, expectation_insufficient=90%**.
The LLM is too conservative in finding motivation/expectation evidence.

V3.6 fixes the **evidence model** — not the threshold.

## V3.5 Frozen

| Metric | Value |
|---|---|
| Accuracy | 75% |
| False-elite | 0% |
| False-reject | 5% |
| 102 accuracy | 85% |
| 103 accuracy | 25% |
| Motivation insufficient | 85% |
| Expectation insufficient | 90% |

## V3.6 Key Changes

### 1. Better Models
- `google/gemma-4-31b-it` (31B params) for legal reasoning
- `deepseek-ai/deepseek-v4-flash-0731` as fallback

### 2. Motivation Evidence Graph (Edge-Based)

No free-form "motivation = yes" without supporting edges.

Each edge: `source_id` + `exact_span` + `date_valid` + `evidence_type` + `strength` + `reason`

### 3. 12 Motivation Evidence Types

- REFERENCE_TEACHING
- KNOWN_PROBLEM
- DESIGN_INCENTIVE
- MARKET_FORCE
- PREDICTABLE_SUBSTITUTION
- COMPATIBILITY_SAME_FUNCTION
- COMMON_GENERAL_KNOWLEDGE
- EXPLICIT_REFERENCE_CROSS_LINK
- KNOWN_TRADEOFF
- PERFORMANCE_IMPROVEMENT
- COST_SIZE_SPEED_SAFETY_INCENTIVE
- REGULATORY_ENGINEERING_CONSTRAINT

### 4. 10 Motivation Search Families

M1-M10 covering: same_problem, same_disadvantage, same_desired_improvement,
same_component_improved_property, known_substitution, same_CPC_IPC_same_technical_effect,
citation_linked_combination, explicit_cross_reference, assignee_competitor_implementation,
market_manufacturing_regulatory_pressure.

### 5. Expectation Evidence Graph (Separate from Motivation)

`modification → mechanism_compatibility → predicted_result → evidence_result_reasonably_expected`

### 6. Combination Compatibility Test

5 dimensions: technical / operating_regime / material / functional / architecture.

EPO: combining may not be obvious where essential features are inherently incompatible.

### 7. Pre-Filing Date Firewall

Every evidence item must pass `publication_date < relevant_date` or be valid
common-general-knowledge evidence.

### 8. Do NOT Turn Insufficient Into Obvious

- `MOTIVATION_INSUFFICIENT` → not OBVIOUS
- `EXPECTATION_INSUFFICIENT` → not OBVIOUS
- 103 = `INSUFFICIENT_EVIDENCE` unless independent evidence closes the missing edge

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
| Motivation evidence recall | ≥ 80% |
| Expectation evidence recall | ≥ 80% |

## Stop Condition

DO NOT RUN 50→5. STOP FOR CEO AUDIT.
