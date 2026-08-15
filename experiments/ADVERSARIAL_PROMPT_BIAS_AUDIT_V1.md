# Adversarial Prompt Bias Audit V1

Prompt hash: `eac82daaf1efed3a`


## Findings: 10 (3 CRITICAL)

| Severity | Finding | Evidence | Impact |
|----------|---------|----------|--------|
| HIGH | PROMPT_USES_ATTACK_LANGUAGE | Prompt says 'Attack this candidate' | Frames the task as adversarial/attacking, not neutral evalua |
| CRITICAL | BINARY_PASS_KILL_SCHEMA_NO_INSUFFICIENT_EVIDENCE | Response schema only offers 'PASS | KILLED' with no INSUFFIC | Forces the evaluator to choose PASS or KILL when evidence is |
| MEDIUM | NEGATIVE_FRAMING_UNSUPPORTED_MECHANISM | Dimension 'UNSUPPORTED_MECHANISM' asks: 'Is the mechanism un | Question is phrased to elicit a negative/KILL response. A ne |
| MEDIUM | NEGATIVE_FRAMING_WEAK_TRANSFER | Dimension 'WEAK_TRANSFER' asks: 'Is the transfer from source | Question is phrased to elicit a negative/KILL response. A ne |
| MEDIUM | NEGATIVE_FRAMING_OBVIOUS_COMBINATION | Dimension 'OBVIOUS_COMBINATION' asks: 'Is this an obvious co | Question is phrased to elicit a negative/KILL response. A ne |
| MEDIUM | NEGATIVE_FRAMING_ENGINEERING_INFEASIBILITY | Dimension 'ENGINEERING_INFEASIBILITY' asks: 'Is this enginee | Question is phrased to elicit a negative/KILL response. A ne |
| HIGH | ADVERSARIAL_REVIEWER_IDENTITY | System prompt: 'You are an adversarial reviewer' | Identity primes the model to find faults, not to neutrally e |
| CRITICAL | NO_INSUFFICIENT_EVIDENCE_INSTRUCTION | Prompt never mentions INSUFFICIENT_EVIDENCE or uncertainty h | Evaluator has no guidance on what to do when evidence is amb |
| MEDIUM | STRONG_VERB_KILLED | Uses 'KILLED' instead of 'FAIL' or 'INSUFFICIENT' | Binary strong verb leaves no room for nuance. 'KILLED' impli |
| CRITICAL | NO_NOT_PROVEN_VS_FALSE_DISTINCTION | Prompt does not distinguish 'not proven' from 'false' | Evaluator cannot express 'I cannot determine this' — forced  |

## Root Cause

**BINARY_PASS_KILL_SCHEMA_NO_INSUFFICIENT_EVIDENCE**

The adversarial prompt uses a binary PASS/KILLED schema with no INSUFFICIENT_EVIDENCE option. When evidence is ambiguous, the evaluator cannot express 'I cannot determine this' — it is forced to choose PASS or KILLED. Combined with the 'attack' framing and negative dimension phrasing, this creates systematic KILL bias across all model families.

### Evidence

- Average false-kill rate across 6 models: 0.6877 (all above 40%)
- Average false-survival rate across 6 models: 0.0079 (near zero)
- Neutrality test kill bias: 0.7143
- 6 of 8 dimensions lack INSUFFICIENT_EVIDENCE state
- Prompt uses 'attack' framing and negative dimension phrasing
- Same directional error (over-kill) across unrelated model families (Llama, GLM, Gemma, MiniMax, Nemotron)

### Fix Required

- Add INSUFFICIENT_EVIDENCE as a third state for ALL dimensions (not just BOUNDARY_CONDITION)
- Change prompt from 'attack' framing to 'neutral evidence evaluation'
- Rephrase dimensions from negative ('Is the mechanism unsupported?') to neutral ('Is the mechanism supported by evidence?')
- Add explicit instruction: 'If evidence is insufficient to determine, respond INSUFFICIENT_EVIDENCE'
- Add instruction: 'Absence of evidence is not evidence of failure'