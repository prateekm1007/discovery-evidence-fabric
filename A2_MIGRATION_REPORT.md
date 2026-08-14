# A2 Migration Report

## Status: COMPLETE

## Forensic Inventory

| Component | Classification | Reason |
|-----------|---------------|--------|
| EvidenceItem Schema | KEEP | Canonical schema, needed for A2 |
| OpenAlex Mapper | KEEP | Working connector |
| Knowledge Graph | UNPROVEN | Scaffolding only, not implemented |
| Mechanism Extraction | QUARANTINE | TEE negative signal (Task 7) |
| Discovery Modes | QUARANTINE | TEE operators, not validated |
| Adversarial Review | KEEP | Needed for A2 adversarial step |
| Prior Art | KEEP | Needed for A2 prior-art step |
| Reports | KEEP | Historical record |

## Old Active Path
```
SOURCE CONNECTORS → EVIDENCE NORMALIZER → KNOWLEDGE GRAPH →
MECHANISM EXTRACTION → DISCOVERY OPERATORS → CANDIDATES
```
Status: scaffolding only, never executed end-to-end. TEE mechanism extraction quarantined.

## New Active Path (A2)
```
RETRIEVE → FREEZE → SYNTHESIZE (LLM) → VERIFY EVIDENCE →
PRIOR-ART SEARCH → ADVERSARIAL CHALLENGE → EPISTEMIC CLASSIFICATION →
INVENTION_CANDIDATE | REJECTED | UNKNOWN
```

## TEE Dependencies Removed from Active Runtime
- MechanismExtractionEngine: NOT imported by any A2 module
- MechanismAbstractionEngine: NOT imported by any A2 module
- CrossDomainTransferEngine: NOT imported by any A2 module
- Regression test: `test_2_a2_no_tee_dependency` PASSES

## A2 Contract
1. INPUT: medical-device problem (10 frozen problems)
2. RETRIEVE: Europe PMC search → EvidenceItem
3. FREEZE: snapshot with content hashes
4. SYNTHESIZE: LLM generates candidate (deepseek-v4-flash, temp=0.3)
5. VERIFY: every assertion must have source_id + source_hash + verbatim span
6. PRIOR-ART: search Europe PMC, never claim "nobody has done this"
7. ADVERSARIAL: 8-dimension challenge (mechanism, transfer, obvious, prior art, contradiction, boundary, feasibility, regulatory)
8. CLASSIFY: epistemic state (OBSERVED → ... → INVENTION_CANDIDATE), no silent promotion

## Smoke Test Result (p01: Cardiac Pacemaker battery failure)
- **Result: REJECTED**
- Evidence verification: FAILED (mechanism span not verbatim)
- Prior art: LIKELY_PRIOR_ART_EXISTS (6 results found)
- Adversarial: KILLED (3/8 dimensions killed)
- Epistemic state: OBSERVED (promotion blocked)

## Tests
All 11 tests PASS:
1. A2 executes end-to-end ✓
2. A2 does not import quarantined TEE code ✓
3. Source hashes preserved ✓
4. Evidence spans preserved ✓
5. Missing evidence blocks promotion ✓
6. Missing prior-art blocks final qualification ✓
7. Missing adversarial blocks final qualification ✓
8. Provenance reconstructable ✓
9. Snapshot reproducible ✓
10. No semantic similarity to evidence ✓
11. No historical TEE result can enter A2 ✓

## Known Limitations
- n=10 problems (not scaled)
- Evaluator has non-determinism (temp=0.3)
- Only Europe PMC searched (no patents, no ClinicalTrials.gov)
- No simulation layer yet
- No invention corpus generation yet

## Commit
Will be pushed after this report.
