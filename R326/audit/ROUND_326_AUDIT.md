# ROUND 326 AUDIT — From Simulated Loop to Real Closed Loop

**Round:** 326
**Date:** 2026-08-26
**Remote HEAD:** (R326 pending push)

---

## 12 Gates — all executed

### Gate 0: Governance ✅
- HEAD = origin/main = `0782b7f` (verified via API)
- Constitution hash: `f82ae4f6...`
- State conflict resolved: CANONICAL_STATE/PORTFOLIO.json (R275 legacy) SUPERSEDED by R325 manifest (current). Not overwritten — marked superseded per Article XI.
- One authoritative current-state: R325 manifest.

### Gate 1: Real inbound buyer-data path ✅
Executable Python code (`scripts/r326/buyer_ingestion_pipeline.py`) implements: file → SHA-256 → protocol → candidate → equipment → analysis → result → uncertainty → evidence → state transition. Not a JSON description — actual executable code.

### Gate 2: Real provenance testing ✅
4 adversarial tests:
- Correct hash → PASS ✅
- One byte changed → hash mismatch → BLOCK ✅
- Wrong candidate → BLOCK ✅
- Missing calibration → BLOCK ✅

### Gate 3: Deterministic evidence classes ✅
8 classes defined (SIMULATED_TEST_FIXTURE through FALSIFIED). Adversarial test: synthetic data with PASS verdict → classified as SIMULATED_TEST_FIXTURE, NOT PHYSICALLY_VALIDATED. The pipeline enforces this — synthetic can never elevate to physical.

### Gate 4: Statistical semantics ✅
5 test cases covering all CI-threshold interactions:
- CI entirely in PASS → PASS
- CI entirely in FAIL → FAIL
- CI spans PASS boundary → AMBIGUOUS
- CI spans FAIL boundary → AMBIGUOUS
- CI spans both → AMBIGUOUS

The machine does NOT choose the desired interpretation. The CI determines the verdict deterministically.

### Gate 5: EIG as executable math ✅
Actual Shannon entropy calculation: H(prior) - E[H(posterior)]. Not hand-authored scores. Two tests:
- Basic: EIG=0.531 bits (2 hypotheses, 2 outcomes, 50/50 prior)
- High EIG + huge cost → low selection_value (penalized correctly)

### Gate 6: Knowledge loop executable ✅
KA-009 (conductance matching) tested:
- Distributed hydraulic candidate without conductance verification → VIOLATION (factory blocks admission)
- Distributed hydraulic candidate WITH verification → NO VIOLATION (admitted)

Knowledge atoms change future execution.

### Gate 7: Deterministic state transition ✅
4 tests:
- EXPERIMENT_READY + PASS + PHYSICAL → TECHNICALLY_EVALUABLE
- EXPERIMENT_READY + FAIL + budget=0 → CEMETERY
- EXPERIMENT_READY + FAIL + budget=1 → EXPERIMENT_READY (repair)
- EXPERIMENT_READY + AMBIGUOUS → EXPERIMENT_READY (repeat)

State is DERIVED from evidence, not asserted in JSON.

### Gate 8: Bidirectional loop in executable code ✅
`ingest_buyer_submission()` function implements the full OUTBOUND→INBOUND pipeline in executable Python. Not a JSON description.

### Gate 9: Synthetic clearly labeled ✅
`is_synthetic` flag. When True: evidence_class = SIMULATED_TEST_FIXTURE regardless of verdict. Warning printed: "SYNTHETIC/TEST ONLY — does NOT constitute physical validation."

### Gate 10: Patent/legal boundary preserved ✅
No patent-court subsystem added. Legal/IP material remains buyer-diligence context only.

### Gate 11: TTR audit arithmetic ✅
22 fields per candidate. Every field has exactly one status (PASS/FAIL/UNKNOWN/BLOCKED/NOT_APPLICABLE). Every non-PASS carries a reason. No unexplained denominator.

### Gate 12: Final proof ✅
19 adversarial tests, 19 passed. Full chain demonstrated:
```
TEST FIXTURE → SHA-256 → INGEST → PROVENANCE CHECK → EVIDENCE CLASSIFICATION 
→ DETERMINISTIC STATE TRANSITION → KNOWLEDGE ATOM → INHERITED FACTORY RULE 
→ NEW EXPERIMENT SELECTION → REPRODUCIBLE EIG CALCULATION
```

**Demonstration type: DEMONSTRATED WITH SYNTHETIC FIXTURE.**
**Real external data: FALSE.**

The loop is executable but not yet closed with real data. The next real test: when CEO supplies actual experimental data, the machine processes it through this executable pipeline autonomously.

---

## What R326 proved

The machine has an **executable** buyer-data ingestion pipeline that:
1. Accepts machine-readable experimental submissions
2. Verifies provenance (cryptographic hash + protocol/candidate/calibration checks)
3. Fails closed on tampering, wrong candidate, missing calibration
4. Classifies evidence deterministically (synthetic ≠ physical, always)
5. Determines verdict from CI-threshold interaction (not point estimate)
6. Transitions state deterministically (AI does not choose the state)
7. Creates knowledge atoms from results
8. Enforces inherited factory rules on future candidates
9. Calculates EIG using actual Shannon entropy (not hand-authored scores)
10. Selects next experiment based on EIG/cost/time/risk

**All in executable Python code, not JSON descriptions.**

## The distinction

**DEMONSTRATED WITH SYNTHETIC FIXTURE:** 19/19 adversarial tests pass. The pipeline is executable and correct.

**DEMONSTRATED WITH REAL EXTERNAL DATA:** NOT YET. No real buyer data has been processed. The loop is executable but not yet closed with reality.

These two are never collapsed.
