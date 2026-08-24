# P-01 External Validation — Blind Evaluation Protocol

## Purpose

Prevent confirmation bias. The lab analyst should not know which seed produced which result until after analysis is complete. This ensures the analyst applies the same evaluation criteria uniformly.

## Blinding procedure

1. **Seed masking.** Before sending results to the analyst, the lab's data manager renames each result file with a random blinded ID (e.g., `run_001.json`, `run_002.json`, ..., `run_030.json`). The mapping from blinded ID → (scenario, seed) is stored in a separate file accessible only to the data manager.

2. **Scenario masking (optional, recommended).** For an even stronger blind, the analyst is not told which scenario each run belongs to. The analyst evaluates each run only against the universal acceptance criteria (AC-01: INV-2 holds, AC-05: system survives). Per-scenario criteria (AC-02, AC-03) are evaluated by the data manager after the analyst's universal-criteria evaluation is complete.

3. **Analyst commitment.** Before unblinding, the analyst writes down their evaluation: for each blinded run, did it pass/fail each universal AC? This commitment is timestamped and hashed. It cannot be silently revised after unblinding.

4. **Unblinding.** The data manager reveals the mapping. Per-scenario criteria are now evaluated. Results are tabulated.

5. **Discrepancy review.** If the analyst's universal-criteria evaluation differs from the data manager's per-scenario evaluation, the discrepancy is documented and investigated.

## What blind evaluation protects against

- **Confirmation bias.** Analyst might unconsciously apply looser criteria to runs they suspect came from the "promising" scenario.
- **Hindsight bias.** After seeing results, analyst might claim they "knew all along" the design was good/bad.
- **Selective reporting.** Without blinding, analyst might be tempted to highlight favorable runs and downplay unfavorable ones.

## What blind evaluation does NOT protect against

- **Lab selection bias.** If the lab chose to participate only because they expected favorable results, blinding doesn't fix this.
- **Protocol deviation.** If the lab subtly modified the protocol (e.g., "we ran for 23 hours instead of 24 because of a fire drill"), blinding doesn't detect this. Raw data audit does.

## Audit trail

The blinding procedure itself must be auditable:
- The random seed used to generate blinded IDs is recorded
- The mapping file is hashed before and after evaluation
- The analyst's pre-unblinding commitment is hashed and timestamped

These records are part of the validation package and must be preserved for at least 7 years (typical FDA record retention).
