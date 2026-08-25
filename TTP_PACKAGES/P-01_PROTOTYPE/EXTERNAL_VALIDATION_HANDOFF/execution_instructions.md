# P-01 External Validation — Execution Instructions

## Purpose

This document tells an external lab exactly how to validate P-01 without trusting the package owner. The protocol is **frozen** — once the lab receives the package, the owner cannot silently change the design, the protocol, or the acceptance criteria.

## Pre-flight checklist

Before starting validation:

1. **Verify file integrity.** Compute SHA-256 hashes of all files listed in `frozen_design.json`. Compare to the recorded hashes. If ANY hash mismatches, STOP and contact the package owner. Do not proceed with validation of a package whose integrity cannot be verified.

2. **Verify Python environment.** The simulator is pure Python 3.8+ with no external dependencies. Run:
   ```bash
   python --version
   python 05_simulator.py --scenario mild --seed 42
   ```
   The simulator should produce a JSON result file and print a summary. If it crashes, your Python environment is broken — fix it before proceeding.

3. **Reproduce simulator results.** Run the full sweep:
   ```bash
   python 05_simulator.py --all-scenarios
   ```
   Compare your results to `p01_simulator_results_ALLSCENARIOS.json` (already in this folder). Results should match within ±5% on all metrics. If they don't, your environment differs from ours — investigate before proceeding.

## Building the V0 bench prototype

Follow `06_bench_prototype_design.json`. Estimated time: 3-6 months. Estimated cost: $3-5K.

The lab may substitute commercial equivalents for any component, but MUST document substitutions and verify that substituted components meet or exceed the original specs.

## Running the validation

1. **Run reproducibility checks** (see `reproducibility_check.json`). All checks must pass before formal validation begins.

2. **Run formal validation.** 6 scenarios × 5 seeds = 30 bench runs. Each run is 24 hours. Total: 720 bench-hours (~30 days at 24/7).

   Scenarios (in order):
   - `healthy` (5 seeds)
   - `mild_1_of_4` (5 seeds)
   - `adversarial_2_of_4` (5 seeds)
   - `catastrophic_4_of_4` (5 seeds)
   - `sensor_failure` (5 seeds)
   - `actuator_failure` (5 seeds)

3. **Do not consult the package owner during validation.** If you have a question, write it down and continue. Questions are answered only after results are submitted.

4. **Record all data.** Sensor readings at 10 Hz, valve commands at 1 Hz, all events (isolations, alarms, fail-safes) with timestamps. Raw data is required — not just summary statistics.

## Submitting results

Format results per `result_submission_schema.json`. Submit:
- One JSON file per run (30 files total)
- One summary JSON file with per-scenario aggregates
- Raw data files (CSV or HDF5)

The package owner will publish results alongside the original claims. Discrepancies will be investigated jointly.

## After submission

The package owner will:
1. Confirm receipt and integrity of submitted files
2. Publish results alongside pre-registered predictions within 30 days
3. Acknowledge any refutations of the original claim
4. Propose design revisions if acceptance criteria are not met

The lab's name will be acknowledged in the package's provenance ledger (or kept anonymous if the lab prefers).
