"""tests/test_r412_stage_cost.py — P1 stage-cost ledger seals.

Pins the ledger semantics:
  - append-only accumulation per (candidate, stage)
  - unlabeled/invalid cost labels are rejected (fail closed, Art. LXVI)
  - death_stage is immutable once set (Art. XI)
  - total_cost sums recorded seconds only; MEASURED_CALL_COUNT and
    NOT_RECORDED never fabricate seconds
  - aggregate_by_death_stage groups cost-before-death by where the
    death happened
  - the ledger round-trips through JSON (checkpoint/resume)
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.stage_cost import (  # noqa: E402
    STAGES, StageCostLedger)


def _ledger(tmp_path=None):
    return StageCostLedger(tmp_path / "ledger.json"
                           if tmp_path else None)


class TestRecording:
    def test_append_only_accumulates(self):
        led = _ledger()
        led.add_cost("C-1", "novelty", 10.0, "MEASURED")
        led.add_cost("C-1", "novelty", 5.0, "MEASURED", note="retry")
        s = led.candidate_summary("C-1")
        assert s["novelty_cost"] == 15.0
        assert len(s["cost_labels"]["novelty"]) == 1

    def test_unlabeled_cost_rejected(self):
        led = _ledger()
        with pytest.raises(Exception):
            led.add_cost("C-1", "novelty", 10.0, "TRUST_ME_BRO")

    def test_invalid_stage_rejected(self):
        led = _ledger()
        with pytest.raises(Exception):
            led.add_cost("C-1", "vibes", 10.0, "MEASURED")

    def test_call_counts_never_become_seconds(self):
        led = _ledger()
        led.add_llm_calls("C-1", "evidence", 3)
        led.add_cost("C-1", "evidence", 0.0, "MEASURED_CALL_COUNT")
        s = led.candidate_summary("C-1")
        assert s["evidence_cost"] == 0.0
        assert s["llm_calls"]["evidence"] == 3
        assert s["total_cost"] == 0.0

    def test_not_recorded_is_zero_with_label(self):
        led = _ledger()
        led.add_cost("C-1", "mechanism_generation", 0.0, "NOT_RECORDED")
        s = led.candidate_summary("C-1")
        assert s["mechanism_generation_cost"] == 0.0
        assert "NOT_RECORDED" in s["cost_labels"][
            "mechanism_generation"]


class TestDeathSemantics:
    def test_death_stage_immutable(self):
        led = _ledger()
        led.set_death("C-1", "attack (F7)", note="killed")
        with pytest.raises(Exception):
            led.set_death("C-1", "EARLY_COLLISION_SCREEN")

    def test_death_stage_idempotent_same_value(self):
        led = _ledger()
        led.set_death("C-1", "attack", note="a")
        led.set_death("C-1", "attack", note="b")
        assert led.candidate_summary("C-1")["death_stage"] == "attack"

    def test_unset_death_aggregates_as_alive(self):
        led = _ledger()
        led.add_cost("C-1", "retrieval", 5.0, "MEASURED")
        agg = led.aggregate_by_death_stage()
        assert agg[0]["death_stage"] == "ALIVE/UNSET"


class TestAggregation:
    def test_aggregate_by_death_stage(self):
        led = _ledger()
        # two collision deaths, one attack death
        for cid in ("C-a", "C-b"):
            led.add_cost(cid, "retrieval", 10.0, "AMORTIZED_MEASURED")
            led.add_cost(cid, "novelty", 133.0, "ENGINEERING_ESTIMATE")
            led.add_cost(cid, "attack", 30.0, "ENGINEERING_ESTIMATE")
            led.set_death(cid, "prior_art (F7 attack basis)")
        led.add_cost("C-c", "retrieval", 10.0, "AMORTIZED_MEASURED")
        led.set_death("C-c", "physics (F7 attack basis)")
        agg = led.aggregate_by_death_stage()
        top = agg[0]
        assert top["death_stage"] == "prior_art (F7 attack basis)"
        assert top["n_candidates"] == 2
        assert top["total_cost_before_death"] == 346.0
        assert top["cost_per_stage"]["novelty"] == 266.0
        assert agg[1]["n_candidates"] == 1

    def test_total_cost_sums_all_stages(self):
        led = _ledger()
        for s in STAGES:
            led.add_cost("C-1", s, 1.5, "MEASURED")
        assert led.candidate_summary("C-1")["total_cost"] == 9.0


class TestPersistence:
    def test_roundtrip_json(self, tmp_path):
        p = tmp_path / "ledger.json"
        led = StageCostLedger(p)
        led.add_cost("C-1", "attack", 30.0, "ENGINEERING_ESTIMATE",
                     note="est")
        led.set_death("C-1", "attack")
        led.save()
        led2 = StageCostLedger(p)
        s = led2.candidate_summary("C-1")
        assert s["attack_cost"] == 30.0
        assert s["death_stage"] == "attack"
        # append after reload accumulates, never rebases
        led2.add_cost("C-1", "attack", 5.0, "MEASURED")
        assert led2.candidate_summary("C-1")["attack_cost"] == 35.0
