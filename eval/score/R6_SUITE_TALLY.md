# R6 full-suite tally (post-reconciliation), measured 2026-11-11 14:3x-15:0x UTC

Scope: every file in `tests/` except `test_engine_integration.py` (the R6
runs own the live-engine measurement; the suite file was excluded per the
prior session's method), run PER FILE under the sandbox wall cap
(scripts/r6_pytest_chunk.py: one file = one pytest process, `timeout 45`).

## Headline

- 253 test files: **209 green, 44 red** at HEAD `17872b168`.
- The **8 R6-caused red files** found by the pre-fix sweep are all GREEN
  after the reconciliation re-land (`17872b168`; dangling-commit history
  disclosed in that commit message).
- Every remaining red file is **pre-existing at the pre-R6 base
  `7fd214eb4`** (measured in a worktree there), a **transport-down hang**
  (the upstream quota outage window), or a **collection error** that also
  fails collection at the base. Corroboration: the R514-era commit
  034d2f6f7's own message records "r401-TestIndependentAttack x5,
  r510-dryrun x9, f_series R440.17 x10, r422 x3, toscanini-module
  collection errors" as pre-existing then.

## Classification of the 44 red files

Class A - transport-down hangs (upstream quota 429 window; the same
files pass when the transport is up, per the disclosed 30bffef61 note):

    test_r392_readiness.py, test_r394_benchmark.py, test_r416_evolution.py,
    test_r422_synthesis_rotation.py, test_r510_reality_loop.py   [5 files]

Class B - collection errors, rc=2 (import-time failures, red at base too):

    test_r541_ranked_package_contract.py, test_r543_backfill.py,
    test_r543_finished_state_consistency.py,
    test_r543_production_six_part_shape.py,
    test_r545_typed_terminal_finished.py,
    test_r546_infrastructure_terminal_producer_shape.py          [6 files]

Class C - measured red at the pre-R6 base 7fd214eb4 as well (prune
fallout, stale fixtures, environment drift; NOT introduced by R6 — the
base-worktree runs recorded these exact failures):

    test_f_series_integration.py (the R514 commit already recorded f_series
        reds in R5), test_patsnap_claims_regression.py (PATENT_BEAR is
        NO_KEY in the current environment — the multi-provider vault the
        owner will restore is absent; the probe honestly reports NO_KEY),
    test_r401_stream_a.py, test_r418_bridge_gate.py,
    test_r419_product_surface.py, test_r419_render_pipeline.py,
    test_r419_scipy_free_geometry.py, test_r423_async_render_gate.py,
    test_r433_one_canonical_model.py, test_r435_product_experience.py,
    test_r441_visual_compiler.py, test_r451_c21_states.py,
    test_r452_blender_retirement.py, test_r452_c2_sovereign_states.py,
    test_r452_lazy_ocp_memory_guard.py, test_r468_secrets_registry.py,
    test_r470_audit_closes.py, test_r472_audit_power_leg.py,
    test_r493_a2_gate_and_transport.py, test_r505_strong_ring_and_recovery.py,
    test_r506_yield_instrument.py, test_r510_production_bridge.py,
    test_r516_mechanism_attribution.py, test_r516_operator_budget.py,
    test_r521_ef_switch.py, test_r521_retrieval_timing.py,
    test_r525_synth_span_neutrality.py, test_r531_memoization_identity.py,
    test_r542_finished_discovery_contract.py,
    test_r544_one_conversation_e2e.py,
    test_r549a_module_inventory_guard.py, test_secret_scanning.py,
    test_source_maturity_model.py                               [33 files]

## The 8 R6-caused files, now green (for the record)

    test_r401_operator_behavior.py (anchor-domain fixtures state the shared
        mechanism — same contract as the operator prompt),
    test_r491_key_wiring.py / test_r492_key_wiring_completion.py
        (repo-derivation intent kept; the location-measuring path-ban
        removed with disclosure),
    test_r514_starvation_gate.py / test_r515_improve_station.py
        (floor 2->3 pins + STARVED boundary + 3-distinct admits),
    test_r520_ms_route.py, test_r523_ts_purpose_retirement.py,
    test_r525_gauntlet_purpose_retirement.py (zai re-admission state +
        retained retirement mechanism via injected-scope pins).

Method note: per-file runs isolate hangs (a file killed at 45 s cannot
sink a chunk) at the cost of pytest startup overhead; the counts above are
FILE-level, and the per-file failed-node counts ride the chunk runner's
output in the session transcript. The suite is re-runnable end-to-end with
`python3 scripts/r6_pytest_chunk.py <start> <end>` over 0..253.
