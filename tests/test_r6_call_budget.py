"""R6 P0-6: deterministic LLM call-ledger extraction from run artifacts.

Zero LLM. Synthetic envelope fixtures stage the exact shapes measured on
this workspace (operator_results[llm_status], synthesis_span_timings,
runtime_attribution.llm, call_provenance markers) plus synthetic
ROUTING_LEDGER_RUN.json lines in the recorded ledger schema (attempt,
generate_call_id, task, engine_stage, fallback_to, failure_class,
call_class).

v3 supersedes v2 (owner directive 2026-11-11, P0-6): logical_calls and
provider_attempts are SEPARATE measures; the twelve-call target applies
to the LOGICAL measure; observed post-rank stages (POST_RANK_* / IMPROVE)
get rows and enter the totals. v2's mixed "llm_calls" key was the defect
(envelope counters and ledger rows summed into one number).
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
    # no ledger: envelopes measure the LOGICAL measure only
    assert res["stages"]["MECHANISM_SPACE"]["logical_calls"] == 4
    assert res["stages"]["ATTACK"]["logical_calls"] == 1
    # provider attempts are NOT_MEASURED without the run ledger
    assert res["stages"]["MECHANISM_SPACE"]["provider_attempts"] \
        == "NOT_MEASURED"
    assert res["stages"]["ATTACK"]["provider_attempts"] == "NOT_MEASURED"
    # COMPOSE measured NOT_MEASURED for a MS-starved-shaped fixture
    assert "COMPOSE" in res["logical_stages_not_measured"]
    assert res["total_logical_calls"] == "NOT_MEASURED"
    assert res["within_target"] is None


def test_not_a_run_dir(tmp_path):
    res = CB.count_run(tmp_path / "absent")
    assert res["outcome"] == "BLOCKED_NOT_A_RUN_DIR"


def test_empty_envelopes_yield_not_measured(tmp_path):
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["MECHANISM_SPACE"]["logical_calls"] == "NOT_MEASURED"
    assert res["total_logical_calls"] == "NOT_MEASURED"
    assert res["within_target"] is None


# ---------------------------------------------------------------------------
# audit P0-9 / P0-6 cases: the instrument must undercount nothing and
# assume nothing; the two measures are separate; post-rank stages are in
# scope; the twelve-call target certifies the LOGICAL measure only
# ---------------------------------------------------------------------------

def _ledger(path: Path, lines) -> None:
    path.write_text(json.dumps({"run_id": "r1", "lines": lines}),
                    encoding="utf-8")


def _line(stage="ATTACK", cid="gen_1", attempt=1, fail=False,
          task="operator_instantiation", fallback_to=None, ok=None):
    l = {"call_class": "RUN_OWNED", "engine_stage": stage,
         "attempt": attempt, "task": task,
         "generate_spans": {"generate_call_id": cid},
         "error": "", "failure_class": None, "fallback_to": fallback_to,
         "ok": bool(ok) if ok is not None else not fail}
    if fail:
        l["failure_class"] = "MODEL_FAILURE"
        l["error"] = "boom"
    return l


def test_missing_attack_evidence_is_not_measured_never_zero(tmp_path):
    """1. Missing ATTACK/COLLISION/VERIFY/PHYSICS/RANK/RETRIEVE
    evidence (no ledger, no envelope markers, no stage record) must be
    NOT_MEASURED on BOTH measures — never a silent zero."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    for st in ("ATTACK", "VERIFY", "RANK", "RETRIEVE"):
        assert res["stages"][st]["logical_calls"] == "NOT_MEASURED", st
        assert res["stages"][st]["provider_attempts"] == "NOT_MEASURED", st
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
    assert res["stages"]["ATTACK"]["logical_calls"] == 3


def test_ledger_counts_distinct_attempts_including_retries_and_failures(
        tmp_path):
    """3. Provider attempts: retries and transport-failed attempts are
    INCLUDED (one line each, distinct generate_call_id). Logical calls:
    a retry chain groups into ONE call intent."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(cid="gen_a", attempt=1),
        _line(cid="gen_b", attempt=2, fail=True),
        _line(cid="gen_c", attempt=1),
        _line(cid="gen_d", attempt=2, fail=True),
        _line(stage="SYNTHESIZE", cid="gen_s1", task="synthesize")])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["ATTACK"]["provider_attempts"] == 4
    assert res["stages"]["ATTACK"]["logical_calls"] == 2
    assert res["stages"]["SYNTHESIZE"]["provider_attempts"] == 1
    assert res["stages"]["SYNTHESIZE"]["logical_calls"] == 1
    s = res["run_ledger_summary"]
    assert s["retries_included"] == 2
    assert s["failures_included"] == 2
    assert s["run_owned_distinct_attempts"] == 5


def test_ledger_identical_metadata_distinct_ids_counts_both(tmp_path):
    """4. Two attempts with byte-identical metadata but distinct call
    ids are two provider attempts — identity, not metadata, is the
    dedup key. Both at attempt 1, so two logical calls too."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    l1 = _line(cid="gen_x", attempt=1)
    l2 = json.loads(json.dumps(l1))
    l2["generate_spans"]["generate_call_id"] = "gen_y"
    _ledger(d / "ROUTING_LEDGER_RUN.json", [l1, l2])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["ATTACK"]["provider_attempts"] == 2
    assert res["stages"]["ATTACK"]["logical_calls"] == 2
    assert res["run_ledger_summary"]["run_owned_distinct_attempts"] == 2


def test_retry_chain_with_fallback_is_one_logical_call_two_attempts(
        tmp_path):
    """P0-6: attempt 1 fails (transport error), the fallback provider
    serves attempt 2 — the fallback is the SAME logical call (one
    intent, two provider requests)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(cid="gen_a", attempt=1, fail=True),
        _line(cid="gen_b", attempt=2, fallback_to="backup-provider",
              ok=True)])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    att = res["stages"]["ATTACK"]
    assert att["provider_attempts"] == 2
    assert att["logical_calls"] == 1


def test_unrecorded_chain_head_is_flagged_not_fabricated(tmp_path):
    """P0-6: when the first recorded line of a (stage, task) key is
    already attempt>1, its chain head was not recorded — ONE logical
    call, FLAGGED (never a fabricated head)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(cid="gen_orphan", attempt=2, fail=True)])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    att = res["stages"]["ATTACK"]
    assert att["logical_calls"] == 1
    assert res["run_ledger_summary"]["unrecorded_chain_heads"] == 1


def test_different_task_keys_do_not_group(tmp_path):
    """P0-6: lines with a DIFFERENT task key are separate logical
    calls even adjacent at the same stage (operator pairs are separate
    intents)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(stage="MECHANISM_SPACE", cid="g1", task="operator_a"),
        _line(stage="MECHANISM_SPACE", cid="g2", task="operator_b"),
        _line(stage="MECHANISM_SPACE", cid="g3", task="operator_a",
              attempt=1)])
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["MECHANISM_SPACE"]["logical_calls"] == 3
    assert res["stages"]["MECHANISM_SPACE"]["provider_attempts"] == 3


def test_compose_counts_repair_calls_and_no_call_states(tmp_path):
    """5. COMPOSE: n_llm_calls includes the repair call; a typed
    no-call state is a measured 0 on BOTH measures; a missing record
    is NOT_MEASURED on both."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    (d / "ANSWER_COMPOSED.json").write_text(json.dumps(
        {"state": "COMPOSED_CONTRACT_INVALID", "n_llm_calls": 2}),
        encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["COMPOSE"]["logical_calls"] == 2
    # a positive logical measure without the ledger: provider attempts
    # are NOT_MEASURED, never assumed
    assert res["stages"]["COMPOSE"]["provider_attempts"] == "NOT_MEASURED"
    (d / "ANSWER_COMPOSED.json").write_text(json.dumps(
        {"state": "NO_ADMISSIBLE_CANDIDATES", "n_llm_calls": 0}),
        encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["COMPOSE"]["logical_calls"] == 0
    assert res["stages"]["COMPOSE"]["provider_attempts"] == 0
    (d / "ANSWER_COMPOSED.json").unlink()
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["COMPOSE"]["logical_calls"] == "NOT_MEASURED"
    assert res["stages"]["COMPOSE"]["provider_attempts"] == "NOT_MEASURED"


def test_retrieve_measured_from_ledger_never_assumed(tmp_path):
    """6. RETRIEVE: measured from the ledger when present (0 is a
    measurement, not a transport assumption); NOT_MEASURED without
    any retrieval LLM evidence."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    _ledger(d / "ROUTING_LEDGER_RUN.json", [
        _line(stage="RETRIEVE", cid="g1", task="retrieve"),
        _line(stage="RETRIEVE", cid="g2", task="retrieve")])
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["RETRIEVE"]["provider_attempts"] == 2
    assert res["stages"]["RETRIEVE"]["logical_calls"] == 2
    (d / "ROUTING_LEDGER_RUN.json").unlink()
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["RETRIEVE"]["logical_calls"] == "NOT_MEASURED"
    assert res["stages"]["RETRIEVE"]["provider_attempts"] == "NOT_MEASURED"


def test_deterministic_execution_is_a_recorded_zero(tmp_path):
    """7. COLLISION/PHYSICS: a recorded execution with no LLM
    evidence is an honest 0 on both measures (execution evidence
    present)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    (d / "stage_COLLISION.json").write_text('{"novelty_risk": "LOW"}',
                                             encoding="utf-8")
    (d / "stage_PHYSICS.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["COLLISION"]["provider_attempts"] == 0
    assert res["stages"]["COLLISION"]["logical_calls"] == 0
    assert res["stages"]["PHYSICS"]["provider_attempts"] == 0
    assert res["stages"]["PHYSICS"]["logical_calls"] == 0


def test_total_blocks_when_any_stage_unmeasured(tmp_path):
    """8. The twelve-call target is a MEASURED target: a missing stage
    blocks the total (never certified from partial records)."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    assert res["total_logical_calls"] == "NOT_MEASURED"
    assert res["total_provider_attempts"] == "NOT_MEASURED"
    assert res["within_target"] is None


def _full_ledger(d: Path):
    """A complete observed pipeline ledger: one provider line per
    expected stage plus two observed post-rank stages."""
    lines = [
        _line(stage="RETRIEVE", cid="r1", task="retrieve"),
        _line(stage="MECHANISM_SPACE", cid="m1", task="operator_a"),
        _line(stage="MECHANISM_SPACE", cid="m2", attempt=2,
              task="operator_a", fail=True),
        _line(stage="SYNTHESIZE", cid="s1", task="synthesize"),
        _line(stage="ATTACK", cid="a1", task="adversarial"),
        _line(stage="VERIFY", cid="v1", task="verify"),
        _line(stage="RANK", cid="k1", task="rank"),
        _line(stage="COMPOSE", cid="c1", task="answer_compose"),
        _line(stage="POST_RANK_GAUNTLET", cid="pg1", task="gauntlet"),
        _line(stage="POST_RANK_IMPROVE", cid="pi1", task="improve"),
        _line(stage="POST_RANK_IMPROVE", cid="pi2", attempt=2,
              task="improve", fail=True),
    ]
    (d / "stage_COLLISION.json").write_text('{"novelty_risk": "LOW"}',
                                             encoding="utf-8")
    (d / "stage_PHYSICS.json").write_text("{}", encoding="utf-8")
    _ledger(d / "ROUTING_LEDGER_RUN.json", lines)


def test_post_rank_stages_get_rows_and_enter_the_totals(tmp_path):
    """P0-6: the engine records post-rank work in the same run ledger
    (POST_RANK_GAUNTLET / POST_RANK_IMPROVE); the v2 instrument
    stopped at RANK and dropped all post-rank spend. Observed
    post-rank stages get rows and enter both totals."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    (d / "ANSWER_COMPOSED.json").write_text(json.dumps(
        {"state": "COMPOSED_CONTRACT_VALID", "n_llm_calls": 1}),
        encoding="utf-8")
    _full_ledger(d)
    res = CB.count_run(tmp_path / "run")
    assert "POST_RANK_GAUNTLET" in res["stages"]
    assert "POST_RANK_IMPROVE" in res["stages"]
    assert "POST_RANK_TECH_IMPROVEMENT" not in res["stages"]  # conditional
    assert res["stages"]["POST_RANK_GAUNTLET"]["provider_attempts"] == 1
    assert res["stages"]["POST_RANK_IMPROVE"]["provider_attempts"] == 2
    assert res["stages"]["POST_RANK_IMPROVE"]["logical_calls"] == 1
    # logical total: 1+1+1+1+0+1+0+1+1(COMPOSE)+1+1 = 9
    assert res["total_logical_calls"] == 9
    # provider total: 1+2+1+1+0+1+0+1+1(COMPOSE)+1+2 = 11
    assert res["total_provider_attempts"] == 11
    assert res["within_target"] is True


def test_target_certifies_the_logical_measure_only(tmp_path):
    """P0-6: provider attempts can exceed 12 (retries/fallbacks) while
    the LOGICAL measure is within the design budget — the twelve-call
    target certifies the logical measure only, and the record states
    so explicitly."""
    d = tmp_path / "run" / "pipeline"
    d.mkdir(parents=True)
    # Scenario: provider > 12 with logical <= 12 must certify the
    # target. ONE stage, one logical chain, 14 provider attempts
    # (attempt 1 + 13 retries of the same intent).
    lines = [_line(stage="MECHANISM_SPACE", cid="m_0", task="op",
                   attempt=1)]
    for i in range(1, 14):
        lines.append(_line(stage="MECHANISM_SPACE", cid=f"m_{i}",
                           task="op", attempt=i + 1, fail=True))
    (d / "stage_COLLISION.json").write_text('{"novelty_risk": "LOW"}',
                                             encoding="utf-8")
    (d / "stage_PHYSICS.json").write_text("{}", encoding="utf-8")
    _ledger(d / "ROUTING_LEDGER_RUN.json", lines)
    (d / "final_state.json").write_text("{}", encoding="utf-8")
    (d / "ANSWER_COMPOSED.json").write_text(json.dumps(
        {"state": "COMPOSED_CONTRACT_VALID", "n_llm_calls": 1}),
        encoding="utf-8")
    res = CB.count_run(tmp_path / "run")
    ms = res["stages"]["MECHANISM_SPACE"]
    assert ms["provider_attempts"] == 14
    assert ms["logical_calls"] == 1
    assert res["target_applies_to"] == "logical_calls"
    assert "LOGICAL" in res["target_statement"]
    # the OTHER expected stages are unmeasured, blocking the total:
    assert res["total_logical_calls"] == "NOT_MEASURED"
    # a fully measured low-logical/high-provider run certifies True:
    _full_ledger(d)
    # OVERWRITE the MS chain with the 13-attempt single chain
    lines = [_line(stage="MECHANISM_SPACE", cid="m_0", task="op",
                   attempt=1)]
    for i in range(1, 13):
        lines.append(_line(stage="MECHANISM_SPACE", cid=f"m_{i}",
                           task="op", attempt=i + 1, fail=True))
    full = [_line(stage="RETRIEVE", cid="r1", task="retrieve"),
            _line(stage="SYNTHESIZE", cid="s1", task="synthesize"),
            _line(stage="ATTACK", cid="a1", task="adversarial"),
            _line(stage="VERIFY", cid="v1", task="verify"),
            _line(stage="RANK", cid="k1", task="rank"),
            _line(stage="COMPOSE", cid="c1", task="answer_compose")]
    _ledger(d / "ROUTING_LEDGER_RUN.json", lines + full)
    res = CB.count_run(tmp_path / "run")
    assert res["stages"]["MECHANISM_SPACE"]["provider_attempts"] == 13
    assert res["stages"]["MECHANISM_SPACE"]["logical_calls"] == 1
    # logical total: 1 + 1 + 1 + 1 + 1 + 1 + 1(COMPOSE) + 0 + 0 = 7
    assert res["total_logical_calls"] == 7
    # provider total exceeds 12 — and the target does NOT certify it
    assert res["total_provider_attempts"] >= 13
    assert res["within_target"] is True
    assert res["target_applies_to"] == "logical_calls"
