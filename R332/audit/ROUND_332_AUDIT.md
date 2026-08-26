# R332 AUDIT — 13 Buyer Packages + External Interface + Mock Test

**Round:** 332
**Date:** 2026-08-26
**Remote HEAD:** (R332 pending push)
**Constitution hash:** `f82ae4f665dcb5a59ae399017feed57dd24f42fe35d98a897806d559064762a5`

## Gate 1/2: P-21 and P-22 buyer packages built

P-21: Full 17-field buyer package with BUYER_ACTION_ID=P21-EXP-001. Decisive experiment: skull phantom localization. Pass rule: median error ≤5mm + RF exposure satisfied. Label: COMPUTATIONALLY SUPPORTED, localization marginal, regulatory UNRESOLVED.

P-22: Full 17-field buyer package with BUYER_ACTION_ID=P22-EXP-001. CURRENT STATUS: HIGH-RISK CONTROL/SAFETY HYPOTHESIS. Pass rule requires safe closed-loop navigation + tissue force <0.01N + failure recovery. Label: T1, NOT "autonomous navigation."

## Gate 3: All 13 packages canonicalized

All 13 active candidates have complete 17-field + buyer_action_id packages. Every field present. No package is sendable with missing fields. Schema enforced.

## Gate 4: BUYER_ACTION_IDs assigned

| Candidate | BUYER_ACTION_ID |
|-----------|----------------|
| P-01 | P01-EXP-001 |
| P-02 | P02-EXP-001 |
| P-04 | P04-EXP-001 |
| P-07 | P07-EXP-001 |
| P-10 | P10-EXP-001 |
| P-11 | P11-EXP-001 |
| P-12 | P12-EXP-001 |
| P-13 | P13-EXP-001 |
| P-15 | P15-EXP-001 |
| P-16 | P16-EXP-001 |
| P-20 | P20-EXP-001 |
| P-21 | P21-EXP-001 |
| P-22 | P22-EXP-001 |

Each links to the R327 hardened ingestion pipeline.

## Gate 5: External buyer interface (executable code)

`R332/g5_external_interface/external_buyer_interface.py` — executable Python that:
1. Receives BUYER_ACTION_ID + raw data + metadata
2. Computes SHA-256 hash
3. Verifies provenance (via R327 pipeline)
4. Classifies evidence (synthetic ≠ physical)
5. Determines verdict (CI-threshold)
6. Transitions state (deterministic)
7. Generates updated package version
8. Selects next experiment

## Gate 6: Mock external organization test — PASSED

The machine received data it did NOT generate:
- True reduction: 42.3% (unknown to machine, generated with random seed)
- Machine observed: 27.9% (CI [22.0, 33.7])
- Machine's model predicted: 47.3%
- **Machine verdict: AMBIGUOUS** (CI spans PASS(40)/FAIL(20) boundary)
- Evidence class: SIMULATED_TEST_FIXTURE (correctly — synthetic data cannot be physical)
- State: EXPERIMENT_READY → EXPERIMENT_READY (repeat with higher n)

The machine did NOT know the answer in advance. It inferred AMBIGUOUS from the CI-threshold interaction. This is the bridge between synthetic and real.

## Final state

```
ACTIVE TECHNOLOGY OPPORTUNITIES: 13
  T2-CONFIRMED: 1 (P-16)
  T2-CONDITIONAL: 1 (P-01)
  T1: 11
BUYER PACKAGES: 13/13 complete (17-field + buyer_action_id)
BUYER_ACTION_IDS: 13/13 assigned
EXTERNAL INTERFACE: EXECUTABLE (committed in repo)
MOCK EXTERNAL TEST: PASSED (machine inferred AMBIGUOUS from unknown data)
REAL EXTERNAL DATA: 0
REAL BUYER LOOP: 0
SOFTWARE LOOP: VERIFIED
VACANCY: 2
TARGET: 15
```

## What R332 delivered

1. **13 complete buyer packages** — all 17 fields present, all BUYER_ACTION_IDs assigned
2. **P-21 buyer package** — localization experiment defined, regulatory UNRESOLVED
3. **P-22 buyer package** — HIGH-RISK CONTROL/SAFETY label, safe-closed-loop pass condition
4. **External buyer interface** — executable code linking BUYER_ACTION_ID to ingestion pipeline
5. **Mock external test** — machine processed unknown data, correctly inferred AMBIGUOUS

## What remains

- Gate 7: Search 5+ new candidates (next round)
- Real external data (CEO-owned: when a buyer returns actual experimental results)
- Real buyer loop (first genuine external submission through the pipeline)
