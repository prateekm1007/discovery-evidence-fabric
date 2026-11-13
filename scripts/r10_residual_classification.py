#!/usr/bin/env python3
"""r10_residual_classification.py — R10 P1-8b (owner): the residual
test-suite failure classification, with parent-commit falsification.

Method (measured 2026-11-13, both trees in temp git worktrees):
  1. the full suite ran in six CLI-order chunks at the R10 HEAD;
  2. every failing file re-ran in ISOLATION at HEAD;
  3. every failing file re-ran at the R9 BASE commit (2fc229ec1, the
     parent of the R10 code rebuild) with the SAME fixed test shims —
     a failure present at BOTH trees is PRE-EXISTING AT BASE and is
     NOT attributable to the R10 round (Art. XXV: attribution comes
     from measured bytes, never a hypothesis).

The round's repairs:
  * the 2 order-dependent truncation finish-reason failures are FIXED
    (root cause measured: the per-problem GOVERNOR's retry-cap state
    is a process-global; a prior file's storm left RETRY_CAP_EXCEEDED
    for the shared logical key, so the hermetic transport pins failed
    ONLY in full-suite order — the pins now reset the governor to
    their own scope in setUp; production behavior unchanged);
  * NINE collection errors FIXED (six test files' toscanini import
    shim bound the UPPERCASE package under the lowercase name —
    `import TOSCANINI` SUCCEEDS on a case-sensitive Linux checkout,
    shadowing the real package whose sessions module lives only in
    the lowercase directory; the shim now tries the canonical
    lowercase package FIRST and aliases only as fallback). These
    files were UNCOLLECTABLE before — their 16+7 failures NEVER RAN
    in the R9 round's count; they are exposed now and falsified
    pre-existing at base.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

HEAD = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                      capture_output=True, text=True).stdout.strip()

# the measured classification (the chunk runs + the base falsification,
# both executed this round; the chunk transcripts live in the session
# log, the verdicts below are the durable record)
PREEXISTING_AT_BASE = {
    "tests/test_r392_readiness.py": 4,
    "tests/test_r414_product_integration.py": 4,
    "tests/test_r416_evolution.py": 3,
    "tests/test_r423_async_render_gate.py": 5,
    "tests/test_r468_secrets_registry.py": 1,
    "tests/test_r506_yield_instrument.py": 2,
    "tests/test_r510_production_bridge.py": 3,
    "tests/test_r520_ms_route.py": 1,
    "tests/test_r521_ef_switch.py": 3,
    "tests/test_r523_ts_purpose_retirement.py": 1,
    "tests/test_r525_gauntlet_purpose_retirement.py": 1,
    "tests/test_r525_synth_span_neutrality.py": 2,
    "tests/test_r531_memoization_identity.py": 1,
    "tests/test_r542_finished_discovery_contract.py": 2,
    "tests/test_r544_one_conversation_e2e.py": 2,
    "tests/test_r549a_module_inventory_guard.py": 1,
    "tests/test_r6_audit_round_clean_output.py": 1,
    "tests/test_intervention_evidence_binding.py": 1,
    "tests/test_p05_claim_provenance.py": 1,
    "tests/test_patsnap_claims_regression.py": 1,
    "tests/test_secret_scanning.py": 1,
    "tests/test_source_maturity_model.py": 1,
}
ORDER_DEPENDENT = {
    "tests/test_f_series_integration.py": {
        "n_in_suite": 5,
        "n_in_isolation": 0,
        "mechanism": ("pass in file isolation at HEAD and at base; "
                      "fail only in full-suite order (the measured "
                      "mode: PACKAGE_DEFERRED.json present where the "
                      "pin expects a compiled package — the bridge "
                      "gate's compiled-package state does not "
                      "materialize under suite order); the R9 round "
                      "classified the same five as its 'integration "
                      "file failures' hypothesis — now measured as "
                      "ORDER-DEPENDENT, not deterministic"),
        "disposition": "flagged for the auditor; not R10-caused",
    },
}
FIXED_THIS_ROUND = {
    "truncation_finish_reason_2": {
        "tests": [
            "tests/test_composer_truncation_pin.py::"
            "TestTransportFinishReason::test_openai_stop_is_recorded",
            "tests/test_composer_truncation_pin.py::"
            "TestTransportFinishReason::"
            "test_openai_unknown_raw_value_rides_verbatim"],
        "root_cause": ("the per-problem governor's retry-cap state is "
                       "a process-global; a prior file's transport "
                       "storm left RETRY_CAP_EXCEEDED for the shared "
                       "logical key (measured: the flavor call raised "
                       "before recording, _take_finish_reason read the "
                       "stale value)"),
        "fix": ("the pins reset the governor to their own scope in "
                "setUp (llm_economy.reset_governor) — hermetic "
                "isolation, production behavior unchanged; verified: "
                "the chunk re-run shows the two failures GONE"),
    },
    "collection_errors_9": {
        "files": ["tests/test_r541_ranked_package_contract.py",
                  "tests/test_r542_finished_discovery_contract.py",
                  "tests/test_r543_backfill.py",
                  "tests/test_r543_finished_state_consistency.py",
                  "tests/test_r544_finished_state_rules.py",
                  "tests/test_r545_typed_terminal_finished.py"],
        "root_cause": ("the toscanini import shim bound the UPPERCASE "
                       "package under the lowercase name; on this "
                       "case-sensitive host `import TOSCANINI` "
                       "succeeds and shadows the real lowercase "
                       "package (sessions.py lives only there) — "
                       "`import toscanini.sessions` raised "
                       "ModuleNotFoundError at collection, so the "
                       "whole files NEVER RAN (the R9 count never saw "
                       "them)"),
        "fix": ("the shim tries the canonical lowercase package FIRST "
                "and aliases only as the win32 fallback; verified: "
                "r541 collects and passes (22 tests), the previously "
                "hidden failures are exposed and falsified "
                "pre-existing at base"),
    },
    "r10_plan_test_stale_assertion": {
        "file": "tests/test_r10_a0plus_simple_arm.py",
        "note": ("the plan pin asserted the pre-battery planning "
                 "state; the live battery's delivered records make "
                 "the plan empty — the pin now tests the CONTRACT "
                 "hermetically (an empty tmp pair dir -> everything "
                 "planned; a delivered typed record -> not planned)"),
    },
}

record = {
    "record": "r10_residual_classification/1.0.0",
    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "head_commit": HEAD,
    "base_commit": "2fc229ec1 (the R9 final; parent of the R10 rebuild)",
    "method": ("six CLI-order chunk runs at HEAD; per-file isolation "
               "at HEAD; per-file base runs in a temp worktree with "
               "the SAME fixed shims — a failure at BOTH trees is "
               "pre-existing at base, never attributed to R10 by "
               "hypothesis"),
    "preexisting_at_base": PREEXISTING_AT_BASE,
    "n_preexisting_files": len(PREEXISTING_AT_BASE),
    "n_preexisting_failures": sum(PREEXISTING_AT_BASE.values()),
    "order_dependent": ORDER_DEPENDENT,
    "fixed_this_round": FIXED_THIS_ROUND,
    "r10_caused_failures": [],
    "r10_caused_note": ("EVERY residual failure reproduces at the R9 "
                        "base with the same shims — zero failures are "
                        "attributable to the R10 round's code changes "
                        "(the falsification is byte-measured, not a "
                        "hypothesis)"),
    "auditor_note": ("the 22 pre-existing files' failures are the "
                     "R9-era fixture/behavior drift the R9 commit "
                     "disclosed (the Art. LXXX grounding floor "
                     "reaching fixture pipelines, the governor/"
                     "admission process-globals under suite order, "
                     "the inventory/scan guards); they are the "
                     "queued fixture-sweep follow-up, unchanged in "
                     "scope by R10"),
}

out = REPO / "eval" / "residual_failures_r10.json"
out.write_text(json.dumps(record, indent=1, default=str) + "\n",
               encoding="utf-8")
print("[r10res] wrote", out)
print(json.dumps({k: record[k] for k in
                  ("n_preexisting_files", "n_preexisting_failures",
                   "r10_caused_failures")}, indent=1))
