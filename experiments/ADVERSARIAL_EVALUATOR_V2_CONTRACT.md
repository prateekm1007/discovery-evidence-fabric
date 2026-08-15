# Adversarial Evaluator V2 Contract

**Frozen BEFORE first V5 API call.**

## Root Cause (V1)
- BINARY_PASS_KILL_SCHEMA_NO_INSUFFICIENT_EVIDENCE
- V1 kill_bias_rate: 0.7143
- V1 false_kill_avg: 0.6043

## Three-State Logic
| State | Definition |
|-------|-----------|
| PASS | Evidence supports the candidate on this dimension |
| KILL | Specific evidence demonstrates candidate fails; requires kill_claim, source_id, source_hash, evidence_span |
| INSUFFICIENT_EVIDENCE | Available evidence insufficient to determine; NOT KILL, NOT PASS |

## Critical Rules
- Absence of evidence is not evidence of failure
- Do not infer KILL solely because candidate lacks proof
- Do not infer PASS solely because no contradiction was found
- Use INSUFFICIENT_EVIDENCE when evidence cannot establish either PASS or KILL

## Neutral Framing
- V1: "Attack this candidate" → V2: "Evaluate the candidate against the evidence"
- V1: "adversarial reviewer" → V2: "neutral evidence evaluator"
- Goal: discrimination, not destruction

## Overall Verdict Logic
- OVERALL_KILL: at least one dimension has VALID KILL
- OVERALL_INSUFFICIENT_EVIDENCE: no valid KILL AND at least one INSUFFICIENT_EVIDENCE
- OVERALL_PASS: all dimensions PASS

## Firewalls (unchanged from V1)
- Prior-art firewall: non-kill states cannot yield PRIOR_ART=KILL
- Boundary firewall: KILL requires semantic external evidence resolver
- Invalid verdict: ADVERSARIAL_INVALID (not KILL)
- API failure: EVALUATOR_CALL_FAILED (not KILL)

## Acceptance Gate
- determinate_accuracy >= 80%
- false_kill_rate <= 20%
- false_survival_rate <= 20%
- critical-category determinate accuracy >= 70%
- call_failure_rate <= 20%
- coverage must be reported
