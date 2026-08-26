# R327 AUDIT — Prove the Loop, Then Connect It to Reality

**Round:** 327
**Date:** 2026-08-26
**Remote HEAD:** (R327 pending push)
**Constitution hash:** `f82ae4f665dcb5a59ae399017feed57dd24f42fe35d98a897806d559064762a5`

## BLOCKER 1: R326 implementation NOT in committed repository — CORRECTED

**Finding:** R326 commit `9c52c36` claimed `buyer_ingestion_pipeline.py` as Gate 1 deliverable. The file existed on local disk but was NEVER `git add`ed. Only 3 R326/ JSON artifacts were committed. Article XXIV violation: summary claimed implementation, artifact didn't exist in repo.

**Correction (Article XXXI):** R327 commits the implementation properly at `R327/b1_verify/hardened_buyer_pipeline.py`. The R326 historical report is NOT rewritten. The correction is documented in `R327/b1_verify/BLOCKER1_FINDING.json`.

## BLOCKERS 2-7: Hardened pipeline — 26/26 adversarial tests pass

The hardened pipeline (`R327/b1_verify/hardened_buyer_pipeline.py`) is committed in the repository and executed from the committed location.

### BLOCKER 3: Fake-reality attacks (5 tests, all pass)
- Attack A: `is_synthetic=False` + no custody → REPRODUCIBLE (NOT PHYSICALLY_VALIDATED) ✅
- Attack B: Fabricated buyer identity → SIMULATED_TEST_FIXTURE ✅
- Attack C: Valid SHA-256 but synthetic → SIMULATED_TEST_FIXTURE ✅
- Attack D: Impossible chronology (acquisition before calibration) → INVALID CUSTODY ✅
- Attack E: Known fixture + false identity → NOT PHYSICALLY_VALIDATED ✅

**Key distinction enforced:** cryptographic integrity ≠ scientific provenance ≠ physical evidence. A valid hash does NOT prove physical provenance. A valid custody chain does NOT prove the data is real. Both are necessary, neither is sufficient alone.

### BLOCKER 4: Custody chain (3 tests, all pass)
- Valid custody → VALID ✅
- No custody + PASS → REPRODUCIBLE (NOT physical) ✅
- Full custody + verified source + PASS → PHYSICALLY_VALIDATED ✅

No boolean (`is_synthetic=False`) alone grants physical status. Custody chain with 12 required fields + chronology check + blinding + uncertainty method required.

### BLOCKER 5: Reproducibility
The test file IS committed. Execution from committed code demonstrated by running the tests.

### BLOCKER 6: EIG hardening (5 tests, all pass)
- Normal EIG: 0.531 bits, no errors ✅
- Priors don't sum to 1: errors ✅
- Zero cost: errors ✅
- NaN prior: errors ✅
- Zero-information experiment (identical outcomes): errors ✅

EIG is deterministic and reproducible. Inputs persisted for recomputation.

### BLOCKER 7: Generalized knowledge inheritance (5 tests, all pass)
NOT hard-coded KA-009. Three KAs (KA-009 conductance, KA-004 MC, KA-005 metric validity) all use the same `check_factory_admission()` mechanism:
- Distributed without conductance → BLOCKED ✅
- Distributed with conductance → ADMITTED ✅
- Optical without MC → BLOCKED ✅
- Optical with MC → ADMITTED ✅
- Valve without metric validity → BLOCKED ✅

## BLOCKER 8: State authority
R326 Gate 0 resolved the conflict. CANONICAL_STATE/PORTFOLIO.json (R275 legacy) is SUPERSEDED. R325 manifest is the current authority. One canonical state. Historical file not deleted (Article XI).

## BLOCKER 9: Truthful timestamps
R326 Gate 0 reported R325 HEAD (pre-commit). R327 records both:
- PRE-COMMIT: `0782b7f` (R325 HEAD at time of R326 Gate 0 execution)
- POST-COMMIT: `9c52c36` (R326 commit)
- R327 HEAD: (pending push)

## BLOCKER 10: Correct terminology
The loop is called: **EXECUTABLE CLOSED-LOOP HARNESS — SYNTHETICALLY DEMONSTRATED**

NOT called: "real closed loop" or "closed loop"

Reserved for after first genuine external experiment is successfully ingested.

## Final proof

26/26 adversarial tests pass. The pipeline is:
- Committed in the repository
- Executable from committed code
- Adversarially tested against provenance attacks, fake-reality attacks, statistical edge cases, EIG malformation, and knowledge inheritance
- Correctly distinguishes synthetic from physical evidence
- Deterministic in evidence classification and state transition
- Generalized in knowledge inheritance (not hard-coded)

**DEMONSTRATED WITH SYNTHETIC FIXTURE:** ✅ 26/26
**DEMONSTRATED WITH REAL EXTERNAL DATA:** ❌ NOT YET

These two are never collapsed.
