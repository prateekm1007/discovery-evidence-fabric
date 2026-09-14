"""L8 campaign tests — hermetic, no network.

Covers the ENGINE's kill/survive decisions and the directive's cemetery
format (candidate_id, failure_reason, evidence, attacks, kill_condition,
date, reusable_constraints) — plus the query-ladder correction that
prevents too-narrow-query kills (Art. XV/XXXII memory).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceQueryResult, SourceRecord, utc_now,
)
from discovery_fabric.discovery_modes import device_failure as s5


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    from discovery_fabric.source_registry import retrieval_log
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "log.jsonl")
    yield


def _maude_result(records, status=STATUS_OK):
    return SourceQueryResult(source_id="fda_maude", status=status,
                             ok=status in (STATUS_OK, STATUS_EMPTY),
                             records=records, query="q", retrieved_at=utc_now())


class TestQueryLadder:
    """The L8 correction: kills only after BOTH retrieval levels answer
    zero — a brand-name-field zero is NOT problem-not-documented."""

    def _run_retrieve(self, monkeypatch, statuses):
        calls = []

        class _C:
            SOURCE_ID = "x"

            def search(self, q, timeout=25):
                calls.append(q)
                idx = len(calls) - 1
                st = statuses[idx] if idx < len(statuses) else STATUS_EMPTY
                return _maude_result([], status=st)

        import discovery_fabric.source_registry.connectors.openfda as of
        monkeypatch.setattr(of, "MaudeConnector", _C)
        monkeypatch.setattr(of, "FdaRecallConnector", _C)
        return s5.retrieve_failures("venous filter", timeout=5), calls

    def test_brand_empty_falls_back_to_full_text(self, monkeypatch):
        res, calls = self._run_retrieve(monkeypatch, [STATUS_EMPTY, STATUS_EMPTY])
        # two MAUDE queries: brand field then full-text
        assert len(calls) >= 2
        assert "device.brand_name" in calls[0]
        assert calls[1].startswith('"')
        assert res["retrieval_levels"]["maude"] == "FULL_TEXT_PHRASE"

    def test_brand_hit_does_not_broaden(self, monkeypatch):
        res, calls = self._run_retrieve(monkeypatch, [STATUS_OK])
        assert res["retrieval_levels"]["maude"] == "BRAND_NAME_FIELD"

    def test_ladder_disclosed_in_result(self, monkeypatch):
        res, _ = self._run_retrieve(monkeypatch, [STATUS_EMPTY, STATUS_EMPTY])
        assert "retrieval_levels" in res


class TestEngineDecisions:
    def _territory(self):
        return {"id": "01", "campaign_slot": "Orthopedics",
                "domain": "ORTHOPEDICS", "device_query": "hip prosthesis"}

    def _load_campaign_module(self, monkeypatch, result):
        import scripts.l8_campaign as camp
        monkeypatch.setattr(camp, "discover_opportunity",
                            lambda q, d, timeout=30: result)
        return camp

    def test_problem_not_documented_kills(self, monkeypatch):
        camp = self._load_campaign_module(monkeypatch, {
            "blocked": False,
            "chain_steps": [
                {"step": "real_world_failure", "status": "OK",
                 "maude_records": 0, "recall_records": 0},
                {"step": "failure_mechanism", "status": "EMPTY"},
                {"step": "problem_existence_gate",
                 "status": "PROBLEM_NOT_DOCUMENTED"},
            ],
            "candidates": [],
        })
        out = camp.run_territory(self._territory(), timeout=5)
        assert out["engine_decision"] == "KILLED"
        k = out["kills"][0]
        for field in ("candidate_id", "failure_reason", "evidence",
                      "attacks", "kill_condition",
                      "reusable_constraints"):
            assert field in k, field
        assert k["kill_condition_class"] == "PROBLEM_EXISTENCE_FAIL"

    def test_no_principles_kills_candidate(self, monkeypatch):
        camp = self._load_campaign_module(monkeypatch, {
            "blocked": False,
            "chain_steps": [
                {"step": "real_world_failure", "status": "OK",
                 "maude_records": 10, "recall_records": 5},
                {"step": "failure_mechanism", "status": "OK"},
            ],
            "candidates": [{
                "candidate_id": "opp:x:y:P",
                "problem": {"constraint": "c",
                            "epistemic_class": "OBSERVED"},
                "mechanism_hypothesis": {"physical_principle": "P"},
                "kill_conditions": [{"condition": "X", "test": "t",
                                     "kill_if": "k"}],
                "strongest_alternative_explanation": "retrieval narrowness",
                "cross_domain_evidence": {"transfer_domains": []},
                "chain_detail": {
                    "constraint": {"constraint_statement": "c"},
                    "attempted_solutions": {"literature": {"retrieved": 5,
                                                           "records": []}},
                    "why_they_fail": {},
                    "alternative_physical_principles": [],
                    "cross_domain_transfer": {
                        "per_domain": {"CARDIOVASCULAR":
                                       {"status": "TRANSFER_EVIDENCE"}},
                        "constraint_terms": ["c"]},
                },
            }],
        })
        out = camp.run_territory(self._territory(), timeout=5)
        assert out["engine_decision"] == "SURVIVORS" or out["kills"]
        assert len(out["kills"]) == 1
        assert "NO_MECHANISM_DIRECTION" in out["kills"][0]["failure_reason"]

    def test_no_transfer_kills_candidate(self, monkeypatch):
        camp = self._load_campaign_module(monkeypatch, {
            "blocked": False,
            "chain_steps": [
                {"step": "real_world_failure", "status": "OK",
                 "maude_records": 10, "recall_records": 5},
            ],
            "candidates": [{
                "candidate_id": "opp:x:y:P",
                "problem": {"constraint": "c"},
                "mechanism_hypothesis": {"physical_principle": "P"},
                "kill_conditions": [],
                "strongest_alternative_explanation": "x",
                "cross_domain_evidence": {"transfer_domains": []},
                "chain_detail": {
                    "constraint": {"constraint_statement": "c"},
                    "attempted_solutions": {"literature": {"retrieved": 5,
                                                           "records": []}},
                    "why_they_fail": {"root_causes": [], "narratives": []},
                    "alternative_physical_principles": [
                        {"principle": "P"}],
                    "cross_domain_transfer": {
                        "per_domain": {"CARDIOVASCULAR":
                                       {"status":
                                        "KILLED_NO_USABLE_TRANSFER"}},
                        "constraint_terms": ["c"]},
                },
            }],
        })
        out = camp.run_territory(self._territory(), timeout=5)
        assert len(out["kills"]) == 1
        assert "NO_TRANSFER_SUPPORT" in out["kills"][0]["failure_reason"]

    def test_survivor_ranked_with_score(self, monkeypatch):
        camp = self._load_campaign_module(monkeypatch, {
            "blocked": False,
            "chain_steps": [
                {"step": "real_world_failure", "status": "OK",
                 "maude_records": 10, "recall_records": 5},
            ],
            "candidates": [{
                "candidate_id": "opp:x:y:P",
                "problem": {"constraint": "c"},
                "mechanism_hypothesis": {"physical_principle": "P"},
                "kill_conditions": [],
                "strongest_alternative_explanation": "x",
                "cross_domain_evidence": {"transfer_domains": ["CARDIOVASCULAR"]},
                "chain_detail": {
                    "constraint": {"constraint_statement": "c"},
                    "attempted_solutions": {"literature": {"retrieved": 5,
                                                           "records": []}},
                    "why_they_fail": {"root_causes": [1], "narratives": [2]},
                    "alternative_physical_principles": [{"principle": "P"}],
                    "cross_domain_transfer": {
                        "per_domain": {"CARDIOVASCULAR":
                                       {"status": "TRANSFER_EVIDENCE"}},
                        "constraint_terms": ["c"]},
                },
            }],
        })
        out = camp.run_territory(self._territory(), timeout=5)
        assert out["engine_decision"] == "SURVIVORS"
        assert out["candidates"][0]["survivor_score"]["transfer_domains"] == 1
        assert out["candidates"][0]["survivor_score"]["root_cause_evidence"] == 1

    def test_blocked_territory_is_not_killed(self, monkeypatch):
        camp = self._load_campaign_module(monkeypatch, {
            "blocked": True, "chain_steps": [], "candidates": [],
        })
        out = camp.run_territory(self._territory(), timeout=5)
        assert out["engine_decision"] == "BLOCKED_PROVIDER_FAILURE"
        assert out["kills"] == []


class TestFifteenTerritories:
    def test_territory_slots_match_directive(self):
        import scripts.l8_campaign as camp
        slots = {}
        for t in camp.TERRITORIES:
            slots.setdefault(t["campaign_slot"], []).append(t["id"])
        assert slots["Orthopedics"] == ["01", "02", "03", "04", "05"]
        assert slots["Cardiovascular/Vascular"] == ["06", "07", "08", "09"]
        assert slots["Neurovascular"] == ["10", "11", "12"]
        assert slots["Limb/Osseointegration"] == ["13", "14"]
        assert slots["Ophthalmology"] == ["15"]
        assert len(camp.TERRITORIES) == 15

    def test_final_report_exists_with_directive_fields(self):
        p = (Path(__file__).resolve().parent.parent
             / "discovery_campaigns" / "CAMPAIGN_L8_2026-08-29"
             / "CAMPAIGN_REPORT.json")
        if not p.exists():
            pytest.skip("campaign report not generated in this checkout")
        r = json.loads(p.read_text())
        for k in r["cemetery_entries_directive_format"]:
            for field in ("candidate_id", "failure_reason", "evidence",
                          "attacks", "kill_condition", "date",
                          "reusable_constraints"):
                assert field in k, field
        assert r["summary"]["territories_run"] == 15
        assert "not-a-novelty" in json.dumps(
            r["dossier_candidates_ranked"]).lower() or all(
            s["not_a_novelty_determination"] for s in r["dossier_candidates_ranked"])
