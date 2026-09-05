# Incident record — TVM_CONSTRUCTED.json fixture contamination (2026-09-05T20:17Z)

## What happened
The first execution of the new TestAllocationEnforcement tests
(tests/test_r412_recovery_arm.py) loaded the runner module via
importlib and monkeypatched ONLY `OUT_DIR`, while the module-level
path constants `TVM_FROZEN` / `TVM_CONSTRUCTED` (computed at import
time from the REAL repo root) remained un-patched. The tvm-build
tests therefore wrote their fixture rungs ("rung-C-*", "rung-a")
into the PRODUCTION path R412/RECOVERY_ARM/GRADIENT_RUN/
TVM_CONSTRUCTED.json. Art. IX violation (a test mutated production
state). The test paths were corrected minutes later in the same
session (TVM_FROZEN / TVM_CONSTRUCTED patched explicitly); this
file preserves the contaminated bytes as evidence (Art. XI).

## Verification before decontamination
- entries: 0 admitted, all fixture rungs; no real gradient TVM data
  present (the real tvm-build run of 2026-09-05T20:0xZ was killed
  by a session timeout BEFORE the stage's end-of-stage write, so it
  wrote nothing; its 5 rung attempts — 5 fabric calls + 5 LLM
  calls — are orphaned with no records: an infrastructure cost,
  disclosed in the final report, Art. LXI).
- The contaminated file was NEVER frozen (no tvm-freeze ran), NEVER
  queried (no ga3 ran), and NEVER read by GA-4. No sealed artifact
  consumed it.

## Remediation
- Contaminated file moved here (quarantined, preserved).
- Runner hardened: TVM_CONSTRUCTED is now written after EVERY rung
  attempt (per-rung checkpointing), so a session timeout can never
  orphan completed rung attempts again.
- The fresh tvm-build run starts from an empty map.
