"""tests/test_r6_yield_instrument_v2.py — hermetic pins for the owner
audit round 2026-11-13 P0: the discovery-yield instrument must never
award discovery credit when no admissible attack occurred.

WHAT IS PINNED:
  1. The historical false record R506/YIELD_MEASUREMENT.json rows[0]
     (attack_overall = EVALUATOR_CALL_FAILED, attack_survivors.count = 1)
     replays through v2 as ZERO survivors.
  2. Every infrastructure / non-verdict state is incomplete with a typed
     reason: EVALUATOR_CALL_FAILED, ATTACK_INCOMPLETE, NOT_RUN,
     parse failure, UNCERTAIN, ESCALATED_OBJECTION.
  3. An explicit survivor verdict is necessary but not sufficient:
     admissible provider independence AND a calibrated instrument
     attestation are both required.
  4. SEPARATE_CONTEXT is recorded as SEPARATE_CONTEXT_ONLY, never as
     independent adversarial validation.
  5. candidates_generated_distinct requires n_distinct >= 2; a single
     distinct mechanism is INSUFFICIENT; INDETERMINATE is a separate
     class and never contributes to the count.
  6. The attack-survivor transition cannot be reached when the distinctness
     transition did not reach (PRIOR_DISTINCTNESS_NOT_REACHED).
  7. Every transition carries file + JSON pointer + sha256, and every lost
     transition carries a typed reason from the instrument vocabulary.
  8. v1.0.0/v1.1.0 files are untouched (the frozen lineage still runs).

Hermetic: durable-byte fixtures on tmp_path; zero network, zero LLM.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
V2_PATH = REPO / "scripts" / "r516_discovery_yield.py"
V1_PATH = REPO / "scripts" / "r506_discovery_yield.py"
V11_PATH = REPO / "scripts" / "r515_discovery_yield.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


Y2 = _load("r516_discovery_yield", V2_PATH)


def _durable_run(tmp_path: Path, *, attack=None, distinct=None,
                 mechanisms=True, final_status="REJECTED") -> Path:
    root = tmp_path / "durable"
    run = root / "runs" / "case1"
    run.mkdir(parents=True)
    (run / "run_manifest.json").write_text(json.dumps({
        "session_id": "s1", "final_status": final_status,
        "stage_order": [], "failed_stages": {}}), encoding="utf-8")
    (run / "problem.json").write_text(json.dumps({
        "problem_id": "p1", "canonical_family": "mechanical"}),
        encoding="utf-8")
    (run / "final_state.json").write_text(json.dumps({
        "final_status": final_status}), encoding="utf-8")
    if mechanisms:
        ms = {"state": "CANDIDATES", "n_candidates_generated": 3,
              "distinctness": distinct or {"n_distinct": 2,
                                           "n_indeterminate": 0,
                                           "n_equivalent_merged": 0,
                                           "n_input": 3, "n_retained": 2,
                                           "instrument_version":
                                           "mechanism_distinctness/2.0.0"}}
    else:
        ms = {"state": "NO_CANDIDATES", "n_candidates_generated": 0,
              "distinctness": distinct or {}}
    (run / "envelope_MECHANISM_SPACE.json").write_text(
        json.dumps({"mechanism_space": ms}), encoding="utf-8")
    (run / "envelope_ATTACK.json").write_text(
        json.dumps({"attack_results": attack or {}}), encoding="utf-8")
    return root


def _live_attack(**overrides):
    a = {
        "overall": "SURVIVED",
        "state": "ATTACK_RUN",
        "attack_version": "independent_attack/3.0.0",
        "generator_provider": "zai",
        "attacker_provider": "xkiro",
        "attacker_model": "mistralai/ministral-14b",
        "independence_mode": "SEPARATE_PROVIDER",
        "calibration": {"state": "CALIBRATED",
                        "instrument": "independent_attack/3.0.0",
                        "n_cases": 30},
        "items": [{"verdict": "SURVIVE"}, {"verdict": "SURVIVE"}],
    }
    a.update(overrides)
    return a


# ---------------------------------------------------------------------------
# 1. Historical replay — the concrete R506 false survivor
# ---------------------------------------------------------------------------
def test_historical_r506_row_replays_as_zero():
    p = REPO / "R506" / "YIELD_MEASUREMENT.json"
    if not p.exists():
        pytest.skip("R506 historical measurement absent on this host")
    doc = json.loads(p.read_text(encoding="utf-8"))
    recorded = doc["rows"][0]["row"]["attack_survivors"]
    assert recorded["attack_overall"] == "EVALUATOR_CALL_FAILED"
    assert recorded["count"] == 1, "the frozen v1 record is the false case"
    out = Y2.classify_attack_survival(recorded, distinct_reached=True)
    assert out["reached"] is False
    assert out["count"] == 0
    assert out["typed_drop_reason"] == "ATTACK_INCOMPLETE_TRANSPORT"


def test_historical_r506_full_instrument_counts_zero(tmp_path):
    root = _durable_run(
        tmp_path,
        mechanisms=False,
        attack={"overall": "EVALUATOR_CALL_FAILED",
                "attacker_provenance":
                    "RUN_LEVEL_A2_GAUNTLET_NOT_SEALED_BAR_CALIBRATED"})
    src = Y2._base.ByteSource("fs", root=str(root))
    row = Y2.build_funnel_row(src, "case1")
    dist = row["candidates_generated_distinct"]
    att = row["attack_survivors"]
    assert dist["reached"] is False
    assert dist["typed_drop_reason"] == "NO_CANDIDATES"
    assert att["reached"] is False
    assert att["count"] == 0, "v1 counted EVALUATOR_CALL_FAILED as 1"
    assert att["typed_drop_reason"] == "PRIOR_DISTINCTNESS_NOT_REACHED"
    assert row["instrument"] == "r506_discovery_yield/2.0.0"


# ---------------------------------------------------------------------------
# 2. Infrastructure / non-verdict states are never survival
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("overall,reason", [
    ("EVALUATOR_CALL_FAILED", "ATTACK_INCOMPLETE_TRANSPORT"),
    ("ATTACK_INCOMPLETE", "ATTACK_INCOMPLETE_TRANSPORT"),
    ("TRANSPORT_FAILED", "ATTACK_INCOMPLETE_TRANSPORT"),
    ("NOT_RUN", "ATTACK_NOT_RUN"),
    ("PARSE_FAILED", "ATTACK_PARSE_FAILURE"),
    ("UNCERTAIN", "ATTACK_UNCERTAIN"),
    ("ESCALATED_OBJECTION", "ATTACK_ESCALATED_NOT_SURVIVAL"),
    ("KILLED", "ATTACK_KILLED"),
])
def test_non_survivor_states_are_typed_incomplete(overall, reason):
    out = Y2.classify_attack_survival({"overall": overall},
                                      distinct_reached=True)
    assert out["reached"] is False
    assert out["count"] == 0
    assert out["typed_drop_reason"] == reason
    assert out["typed_drop_reason"] in Y2.REASONS


def test_missing_attack_record_is_not_run():
    out = Y2.classify_attack_survival(None, distinct_reached=True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "ATTACK_NOT_RUN"


def test_unknown_verdict_is_never_survival():
    out = Y2.classify_attack_survival({"overall": "LOOKS_FINE"},
                                      distinct_reached=True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "ATTACK_VERDICT_UNRECOGNIZED"


# ---------------------------------------------------------------------------
# 3. Explicit survivor verdict is necessary but not sufficient
# ---------------------------------------------------------------------------
def test_calibrated_separate_provider_survivor_counts():
    out = Y2.classify_attack_survival(_live_attack(),
                                      distinct_reached=True)
    assert out["reached"] is True
    assert out["count"] == 2, "explicit per-candidate survivor items"
    assert out["extra"]["attestation"] == (
        "RECORD_ATTESTS_CALIBRATED_SEPARATE_PROVIDER_ATTACK")


def test_survivor_without_calibration_is_incomplete():
    a = _live_attack()
    a.pop("calibration")
    out = Y2.classify_attack_survival(a, distinct_reached=True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "ATTACK_CALIBRATION_UNAVAILABLE"
    assert out["extra"]["calibration_state"] == "UNKNOWN"


def test_survivor_with_unknown_calibration_state_is_incomplete():
    out = Y2.classify_attack_survival(
        _live_attack(calibration={"state": "NOT_MEASURED"}),
        distinct_reached=True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "ATTACK_CALIBRATION_UNAVAILABLE"


def test_a2_pass_without_calibration_counts_zero():
    out = Y2.classify_attack_survival(
        {"overall": "PASS", "attack_version":
         "a2_adversarial_gauntlet/2.1.0"},
        distinct_reached=True)
    assert out["reached"] is False
    assert out["count"] == 0
    assert out["typed_drop_reason"] in (
        "ATTACK_INDEPENDENCE_UNAVAILABLE",
        "ATTACK_CALIBRATION_UNAVAILABLE")


def test_separate_context_is_never_independent_validation():
    a = _live_attack(independence_mode="SEPARATE_CONTEXT",
                     attacker_provider="zai",
                     attacker_model="glm-4-plus")
    out = Y2.classify_attack_survival(a, distinct_reached=True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "ATTACK_INDEPENDENCE_UNAVAILABLE"
    assert out["extra"]["independence_state"] == "SEPARATE_CONTEXT_ONLY"


def test_missing_independence_is_unavailable():
    a = _live_attack()
    for k in ("independence_mode", "generator_provider",
              "attacker_provider"):
        a.pop(k)
    out = Y2.classify_attack_survival(a, distinct_reached=True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "ATTACK_INDEPENDENCE_UNAVAILABLE"
    assert out["extra"]["independence"]["state"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# 4. Distinctness — n_distinct >= 2, INDETERMINATE separate
# ---------------------------------------------------------------------------
def test_single_distinct_mechanism_is_insufficient():
    out = Y2.classify_distinctness(
        {"n_distinct": 1, "n_indeterminate": 0}, True)
    assert out["reached"] is False
    assert out["typed_drop_reason"] == "INSUFFICIENT_DISTINCT_MECHANISMS"
    assert out["count"] == 1


def test_two_distinct_mechanisms_reach():
    out = Y2.classify_distinctness(
        {"n_distinct": 2, "n_indeterminate": 1,
         "instrument_version": "mechanism_distinctness/2.0.0"}, True)
    assert out["reached"] is True
    assert out["count"] == 2
    assert out["extra"]["admission_classes"]["INDETERMINATE"] == 1
    assert out["extra"]["evidence_class"] == "LEXICAL_SCREENING_HEURISTIC"
    assert out["extra"]["discovery_credit"] == (
        "NOT_ESTABLISHED_AS_CAUSAL_DISTINCTNESS")


def test_indeterminate_never_counts_as_distinct():
    out = Y2.classify_distinctness(
        {"n_distinct": 0, "n_indeterminate": 2}, True)
    assert out["reached"] is False
    assert out["count"] == 0
    assert out["typed_drop_reason"] == "ALL_DISTINCTNESS_INDETERMINATE"
    assert out["extra"]["admission_classes"]["INDETERMINATE"] == 2


def test_calibrated_distinctness_record_earns_structural_class():
    out = Y2.classify_distinctness(
        {"n_distinct": 2,
         "benchmark": {"calibration_state": "CALIBRATED"}}, True)
    assert out["extra"]["evidence_class"] == (
        "CALIBRATED_MECHANISM_DISTINCTNESS")


def test_attack_cannot_reach_when_distinctness_failed(tmp_path):
    root = _durable_run(
        tmp_path,
        distinct={"n_distinct": 0, "n_indeterminate": 0},
        attack=_live_attack())
    src = Y2._base.ByteSource("fs", root=str(root))
    row = Y2.build_funnel_row(src, "case1")
    assert row["candidates_generated_distinct"]["reached"] is False
    att = row["attack_survivors"]
    assert att["reached"] is False
    assert att["typed_drop_reason"] == "PRIOR_DISTINCTNESS_NOT_REACHED"
    assert att["count"] == 0


# ---------------------------------------------------------------------------
# 5. Evidence custody on every transition
# ---------------------------------------------------------------------------
def test_every_transition_has_file_pointer_and_sha(tmp_path):
    root = _durable_run(tmp_path, attack=_live_attack())
    src = Y2._base.ByteSource("fs", root=str(root))
    row = Y2.build_funnel_row(src, "case1")
    assert row["attack_survivors"]["reached"] is True
    for name in Y2.ORDER:
        st = row.get(name) or {}
        assert st.get("evidence"), f"{name} missing evidence custody"
        if st["evidence"].get("file_state") == "STAGE_NOT_RUN_IN_RUN_BYTES":
            assert st["evidence"].get("sha256") is None
        else:
            assert st["evidence"].get("file"), f"{name} missing file"
            assert st["evidence"].get("pointer"), f"{name} missing pointer"
            assert (st["evidence"].get("sha256")
                    or st["evidence"].get("file_state")
                    == "ABSENT_IN_RUN_BYTES"), (
                f"{name} missing evidence hash custody")
        if not st.get("reached"):
            assert st.get("typed_drop_reason"), (
                f"{name} lost without a typed reason")
            assert st["typed_drop_reason"] in Y2.REASONS


def test_starvation_boundary_preserved(tmp_path):
    root = _durable_run(tmp_path, attack=_live_attack(),
                        final_status="MECHANISM_STARVED")
    src = Y2._base.ByteSource("fs", root=str(root))
    row = Y2.build_funnel_row(src, "case1")
    assert row["starvation_terminal"]["is_starved"] is True
    for name in ("attack_survivors", "contradiction_survivors",
                 "experimentally_discriminated", "mutated_survivors"):
        assert row[name]["reached"] is False
        assert row[name]["typed_drop_reason"] == "MECHANISM_STARVED"


# ---------------------------------------------------------------------------
# 6. The frozen lineage is untouched
# ---------------------------------------------------------------------------
def test_frozen_lineage_versions_unchanged():
    v1 = _load("yield_v1_check", V1_PATH)
    v11 = _load("yield_v11_check", V11_PATH)
    assert v1.INSTRUMENT_VERSION == "1.0.0"
    assert v11.INSTRUMENT_VERSION == "1.1.0"
    assert Y2.INSTRUMENT_VERSION == "2.0.0"
