# V1.1 Production Standard — FROZEN

**Frozen:** 2026-08-17T16:58:45.409005+00:00
**Frozen by commit:** 37f79fe191b56f0d49b062ed0bab29b67378a81b
**Protocol version:** V1.1
**Status:** PRODUCTION — no more invention-by-invention changes

## The 18 Rules (Mechanically Enforced)

These rules apply to every one of the remaining 149 positions. They are not advisory — they are enforced by preflight, CI, and the deterministic state machine.

### 1. Protocol first
Verify V1.1 hash before work begins. `protocol/CONSTITUTION_REGISTRY.json` current_sha256 must match actual file hash.

### 2. Company moat map first
No invention may be generated from imagination before the company's technology/ownership/buyer graphs are established (Stages 1-4 of the pipeline).

### 3. Problem before solution
Prove the technical/commercial problem (Stage 5) before generating architectures (Stage 11).

### 4. Limitation freeze
Freeze L1…Ln (Stage 6, 08_LIMITATION_FREEZE.json) before prior-art adjudication. No moving the goalposts. Changes require a new version (V2, V3, ...).

### 5. Family-complete discovery
Discovery coverage, family coverage, and evidence coverage remain separate metrics. See SEARCH_COMPLETENESS_CERTIFICATE.json.

### 6. Primary evidence only for patent conclusions
LLMs can generate hypotheses, never establish patent facts. Patent conclusions require primary claim text (retrieved, not model-derived).

### 7. 102 = one reference
Every limitation must be EXPRESS or NECESSARILY_INHERENT in the same reference. 102 is NEVER a combination. (USPTO MPEP §2131)

### 8. 103 = separate analysis
Document: differences, analogous-art status, motivation/rationale, reasonable expectation of success, invention as a whole. (USPTO MPEP §2141)

### 9. Search incompleteness is a state, not a conclusion
If discovery is incomplete: `SEARCH_INCOMPLETE`. May NOT convert absence of evidence into `NOT_FOUND`.

### 10. Simulation must be decision-relevant
Engine chooses the correct physics/engineering model for the invention. Cannot recycle a generic simulation.

### 11. Fail-safe is mandatory
No buyer-facing architecture without an explicit failure/emergency state. Drainage preservation path MANDATORY for physical systems.

### 12. Buyer utility must be evidenced
"Interesting" is not commercial value. Every utility claim needs evidence + confidence.

### 13. Internal scores never masquerade as external validation
`BUYER_SENTIMENT_SOURCE = INTERNAL_SIMULATION` unless an actual external auditor/customer supplies evidence.

### 14. Deterministic final state
The LLM cannot select or override `FINAL_STATUS`. See `DETERMINISTIC_STATE_MACHINE.py`.

### 15. No silent promotion
A failed gate stays failed regardless of narrative strength. See `RETROACTIVE_INFLATION_SCANNER.py`.

### 16. Every number gets provenance
Source, assumption, calculation/model, confidence, and evidence pointer. CI fails on missing provenance.

### 17. External buyer test comes after the dossier is internally complete
Not instead of internal evidence. The external test is a separate evidence class.

### 18. All artifacts must pass CI/preflight before advancement
An invention cannot advance to the next position until preflight passes + retroactive scanner is clean.

## Enforcement

| Rule | Enforcement mechanism |
|------|----------------------|
| 1 | Constitution hash-pin check (preflight §X.0) |
| 2-4 | Pipeline stage order (preflight §9.1) |
| 5 | SEARCH_COMPLETENESS_CERTIFICATE.json (CI-SEARCH-COMPLETENESS-001) |
| 6 | Evidence ledger model_derived labeling (CI-INFLATION-001) |
| 7 | 102 single-reference check (CI-INFLATION-005) |
| 8 | 103 motivation state check (CI-INFLATION-006) |
| 9 | 103 three-state evidence (FOUND / NOT_FOUND_AFTER_COMPLETE_SEARCH / SEARCH_INCOMPLETE) |
| 10 | Simulation model_inputs + equations (preflight §9.8) |
| 11 | Fail-safe architecture check (preflight §9.7) |
| 12 | Buyer utility evidence pointers (CI-INFLATION-007) |
| 13 | BUYER_SENTIMENT_SOURCE field (V1.1 amendment) |
| 14 | DETERMINISTIC_STATE_MACHINE.py (V1.1 amendment) |
| 15 | RETROACTIVE_INFLATION_SCANNER.py (CI gate) |
| 16 | Number provenance fields (CI-INFLATION-002) |
| 17 | External evidence class separation (V1.1 amendment) |
| 18 | Preflight + scanner must pass before advancement |

## Freeze Statement

This standard is FROZEN. No changes may be made to these 18 rules without a new PCP (Protocol Change Proposal) following the Protocol Evolution Workflow. The coder may not change the standard invention-by-invention.

Invention #4 will be the first real production run of the 150-invention machine under this frozen standard.
