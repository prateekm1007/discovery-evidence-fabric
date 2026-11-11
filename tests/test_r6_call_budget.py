"""R6 item 1: deterministic LLM call-count extraction from run artifacts.

Zero LLM. Synthetic envelope fixtures stage the exact shapes measured on
this workspace (operator_results[llm_status], synthesis_span_timings,
runtime_attribution.llm, call_provenance markers).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts import r6_call_budget as CB  # noqa: E402


def test_measured_total_within_target(tmp_path):
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "envelope_MECHANISM_SPACE.json").write_text(json.dumps({
        "mechanism_space": {
            "operator_results": [{"llm_status": "OK", "operator": "x"},
                                 {"llm_status": "OK", "operator": "y"},
                                 {"llm_status": "OK", "operator": "z"}],
            "runtime_attribution": {"llm": {"n_llm_calls": 1}},
        }}), encoding="utf-8")
    (d / "envelope_SYNTHESIZE.json").write_text(json.dumps({
        "mechanism_map": {"raw_candidate": {
            "synthesis_span_timings": {"n_llm_chat_calls": 1}}}}),
        encoding="utf-8")
    (d / "envelope_ATTACK.json").write_text(json.dumps({
        "attack_results": {"transport": {
            "call_provenance": {"engine_stage": "ATTACK",
                                "call_class": "RUN_OWNED"}}}}),
        encoding="utf-8")
    (d / "final_state.json").write_text(json.dumps({"final_status": "X"}),
                                        encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["outcome"] == "SCORED"
    assert res["stages"]["MECHANISM_SPACE"]["llm_calls"] == 4
    assert res["stages"]["ATTACK"]["llm_calls"] == 1
    # COMPOSE measured NOT_MEASURED for a MS-starved-shaped fixture
    assert "COMPOSE" in res["stages_not_measured"]


def test_not_a_run_dir(tmp_path):
    res = CB.count_run(tmp_path / "absent")
    assert res["outcome"] == "BLOCKED_NOT_A_RUN_DIR"


def test_empty_envelopes_yield_not_measured(tmp_path):
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["MECHANISM_SPACE"]["llm_calls"] == "NOT_MEASURED"
    assert res["total_llm_calls"] == "NOT_MEASURED"
    assert res["within_target"] is None
