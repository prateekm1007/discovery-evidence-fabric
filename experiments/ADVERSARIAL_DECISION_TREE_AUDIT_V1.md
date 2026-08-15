# Adversarial Decision Tree Audit V1


## Decision Path

**Step 1**: evidence_gate (skip_if_evidence_failed())
  - If fails: NOT_RUN (correct — no adversarial call)
**Step 2**: llm_call (llm_chat())
  - If fails: EVALUATOR_CALL_FAILED (correct — not KILL)
**Step 3**: parse_response (regex pattern)
**Step 4**: prior_art_firewall (enforce_prior_art_firewall())
  - If applies: non-kill states → PRIOR_ART KILL overridden to SURVIVE (correct)
**Step 5**: boundary_evidence (evaluate_boundary_condition())
  - If no evidence: BOUNDARY_FAILURE KILL → INSUFFICIENT_EVIDENCE (correct)
**Step 6**: adversarial_invalid (check_adversarial_invalid())
  - If conflict: ADVERSARIAL_INVALID (correct — not KILL)
**Step 7**: overall_verdict (any KILLED remaining → overall KILLED)
  - **PROBLEM**: If ANY dimension is KILLED (even without evidence), overall is KILLED. No INSUFFICIENT_EVIDENCE option for non-boundary, non-prior-art dimensions.

## Critical Gap

Dimensions MECHANISM_VALIDITY, TRANSFER_LEGITIMACY, OBVIOUSNESS, ENGINEERING_FEASIBILITY, FALSIFIABILITY, REGULATORY_INCOMPATIBILITY have NO INSUFFICIENT_EVIDENCE state. The LLM can only respond PASS or KILLED. When uncertain, it defaults to KILLED.

### Dimensions with INSUFFICIENT_EVIDENCE: ['BOUNDARY_CONDITION (via V4 correction)']
### Dimensions WITHOUT INSUFFICIENT_EVIDENCE: ['UNSUPPORTED_MECHANISM', 'WEAK_TRANSFER', 'OBVIOUS_COMBINATION', 'CONTRADICTION', 'ENGINEERING_INFEASIBILITY', 'REGULATORY_INCOMPATIBILITY']

## Three-State Logic

- PASS: available for all dimensions
- KILL: available for all dimensions
- INSUFFICIENT_EVIDENCE: available ONLY for BOUNDARY_CONDITION (via V4 correction)
- missing: INSUFFICIENT_EVIDENCE is NOT available for 6 of 8 dimensions
- verdict: STRUCTURALLY_KILL_BIASED — the evaluator schema forces binary PASS/KILL on most dimensions