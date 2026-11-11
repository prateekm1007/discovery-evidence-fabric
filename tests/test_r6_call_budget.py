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


# ---------------------------------------------------------------------------
# audit P0-9 cases: the instrument must undercount nothing and assume
# nothing (missing evidence is NOT_MEASURED; distinct attempts are
# counted by identity, retries/failures/fallbacks included)
# ---------------------------------------------------------------------------

def _ledger(path: Path, lines) -> None:
    path.write_text(json.dumps({"run_id": "r1", "lines": lines}),
                    encoding="utf-8")


def _line(stage="ATTACK", cid="gen_1", attempt=1, fail=False):
    l = {"call_class": "RUN_OWNED", "engine_stage": stage,
         "attempt": attempt,
         "generate_spans": {"generate_call_id": cid},
         "error": "", "failure_class": None, "fallback_to": None}
    if fail:
        l["failure_class"] = "MODEL_FAILURE"
        l["error"] = "boom"
    return l


def test_missing_attack_evidence_is_not_measured_never_zero(tmp_path):
    """1. Missing ATTACK/COLLISION/VERIFY/PHYSICS/RANK/RETRIEVE
    evidence (no ledger, no envelope markers, no stage record) must be
    NOT_MEASURED — never a silent zero."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    for st in ("ATTACK", "VERIFY", "RANK", "RETRIEVE"):
        assert res["stages"][st]["llm_calls"] == "NOT_MEASURED", st
        assert st in res["stages_not_measured"]


def test_repeated_metadata_on_distinct_calls_is_not_collapsed(tmp_path):
    """2. Identical call_provenance metadata on DISTINCT occurrence
    sites counts per occurrence (the old content-dedup defect)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    marker = {"call_provenance": {"engine_stage": "ATTACK",
                                  "prompt_hash": "same",
                                  "output_hash": "same"}}
    (d / "envelope_ATTACK.json").write_text(
        json.dumps({"attacks": [marker, dict(marker), dict(marker)]}),
        encoding="utf-8")
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["ATTACK"]["llm_calls"] == 3


def test_ledger_counts_distinct_attempts_including_retries_and_failures(
        tmp_path):
    """3. Retries and transport-failed attempts are INCLUDED: distinct
    generate_call_id, one line each."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(cid="gen_a"), _line(cid="gen_b", attempt=2, fail=True),
        _line(cid="gen_c"), _line(cid="gen_d", attempt=2, fail=True),
        _line(stage="SYNTHESIZE", cid="gen_s1")])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["ATTACK"]["llm_calls"] == 4
    assert res["stages"]["SYNTHESIZE"]["llm_calls"] == 1
    s = res["run_ledger_summary"]
    assert s["retries_included"] == 2
    assert s["failures_included"] == 2


def test_ledger_identical_metadata_distinct_ids_counts_both(tmp_path):
    """4. Two attempts with byte-identical metadata but distinct call
    ids are two calls — identity, not metadata, is the dedup key."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    l1 = _line(cid="gen_x")
    l2 = json.loads(json.dumps(l1))
    l2["generate_spans"]["generate_call_id"] = "gen_y"
    _ledger(d / "ROUTING_LEDGER_RUN.json", [l1, l2])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["ATTACK"]["llm_calls"] == 2
    assert res["run_ledger_summary"]["run_owned_distinct_attempts"] == 2


def test_compose_counts_repair_calls_and_no_call_states(tmp_path):
    """5. COMPOSE: n_llm_calls includes the repair call; a typed
    no-call state is a measured 0; a missing record is NOT_MEASURED."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    (d / "ANSWER_COMPOSED.json").write_text(json.dumps(
        {"state": "COMPOSED_CONTRACT_INVALID", "n_llm_calls": 2}),
        encoding="utf-8")
    assert CB.count_run(tmp_path / "run")["stages"]["COMPOSE"]["llm_calls"] == 2
    (d / "ANSWER_COMPOSED.json").write_text(json.dumps(
        {"state": "NO_ADMISSIBLE_CANDIDATES", "n_llm_calls": 0}),
        encoding="utf-8")
    assert CB.count_run(tmp_path / "run")["stages"]["COMPOSE"]["llm_calls"] == 0
    (d / "ANSWER_COMPOSED.json").unlink()
    assert CB.count_run(tmp_path / "run")["stages"]["COMPOSE"]["llm_calls"] \
        == "NOT_MEASURED"


def test_retrieve_measured_from_ledger_never_assumed(tmp_path):
    """6. RETRIEVE: measured from the ledger when present (0 is a
    measurement, not a transport assumption); NOT_MEASURED without
    any retrieval LLM evidence."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(stage="RETRIEVE", cid="g1"), _line(stage="RETRIEVE",
                                                   cid="g2")])
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["RETRIEVE"]["llm_calls"] == 2
    (d / "ROUTING_LEDGER_RUN.json").unlink()
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["RETRIEVE"]["llm_calls"] == "NOT_MEASURED"


def test_deterministic_execution_is_a_recorded_zero(tmp_path):
    """7. COLLISION/PHYSICS: a recorded execution with no LLM
    evidence is an honest 0 (execution evidence present)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    (d / "stage_COLLISION.json").write_text('{"novelty_risk": "LOW"}',
                                            encoding="utf-8")
    (d / "stage_PHYSICS.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["COLLISION"]["llm_calls"] == 0
    assert res["stages"]["PHYSICS"]["llm_calls"] == 0


def test_total_blocks_when_any_stage_unmeasured(tmp_path):
    """8. The twelve-call target is a MEASURED target: a missing stage
    blocks the total (never certified from partial records)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["total_llm_calls"] == "NOT_MEASURED"
    assert res["within_target"] is None
