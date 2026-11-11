#!/usr/bin/env python3
"""Detail pass over the R6 red files: collect FAILED/ERROR node ids, one line each."""
import subprocess, sys, os, re

TESTS_DIR = os.path.join(os.path.dirname(__file__), "..", "tests")
REDS = [
    "test_f_series_integration.py", "test_patsnap_claims_regression.py",
    "test_r392_readiness.py", "test_r394_benchmark.py", "test_r401_operator_behavior.py",
    "test_r401_stream_a.py", "test_r416_evolution.py", "test_r418_bridge_gate.py",
    "test_r419_product_surface.py", "test_r419_render_pipeline.py", "test_r419_scipy_free_geometry.py",
    "test_r422_synthesis_rotation.py", "test_r423_async_render_gate.py", "test_r433_one_canonical_model.py",
    "test_r435_product_experience.py", "test_r441_visual_compiler.py",
    "test_r451_c21_states.py", "test_r452_blender_retirement.py", "test_r452_c2_sovereign_states.py",
    "test_r452_lazy_ocp_memory_guard.py", "test_r468_secrets_registry.py", "test_r470_audit_closes.py",
    "test_r472_audit_power_leg.py",
    "test_r491_key_wiring.py", "test_r492_key_wiring_completion.py", "test_r493_a2_gate_and_transport.py",
    "test_r505_strong_ring_and_recovery.py", "test_r506_yield_instrument.py", "test_r510_production_bridge.py",
    "test_r510_reality_loop.py", "test_r514_starvation_gate.py", "test_r515_improve_station.py",
    "test_r516_mechanism_attribution.py", "test_r516_operator_budget.py", "test_r520_ms_route.py",
    "test_r521_ef_switch.py", "test_r521_retrieval_timing.py", "test_r523_ts_purpose_retirement.py",
    "test_r525_gauntlet_purpose_retirement.py", "test_r525_synth_span_neutrality.py",
    "test_r531_memoization_identity.py", "test_r541_ranked_package_contract.py",
    "test_r542_finished_discovery_contract.py", "test_r543_backfill.py",
    "test_r543_finished_state_consistency.py", "test_r543_production_six_part_shape.py",
    "test_r544_one_conversation_e2e.py", "test_r545_typed_terminal_finished.py",
    "test_r546_infrastructure_terminal_producer_shape.py", "test_r549a_module_inventory_guard.py",
    "test_secret_scanning.py", "test_source_maturity_model.py",
]

def detail(fname):
    path = os.path.join("tests", fname)
    try:
        p = subprocess.run(
            ["python3", "-m", "pytest", "-p", "no:cacheprovider", "--tb=line", "-q", path],
            capture_output=True, text=True, timeout=50,
            env={**os.environ, "PYTHONPATH": os.path.abspath(".")},
        )
    except subprocess.TimeoutExpired:
        return "HUNG>50s"
    out = (p.stdout or "") + (p.stderr or "")
    fails = [l.strip()[:150] for l in out.splitlines()
             if l.startswith(("FAILED", "ERROR")) and "::" in l]
    errs = [l.strip()[:150] for l in out.splitlines() if "Error" in l and ":" in l]
    if fails:
        return " || ".join(fails[:6])
    if errs:
        return "ERR: " + " || ".join(errs[:3])
    return f"rc={p.returncode} no-FAILED-lines; tail: {out.strip().splitlines()[-1][:120] if out.strip() else 'EMPTY'}"

if __name__ == "__main__":
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    for f in REDS[lo:hi]:
        print(f"== {f}")
        print("   " + detail(f))
