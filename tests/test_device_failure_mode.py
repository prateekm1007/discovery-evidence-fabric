"""DEVICE_FAILURE -> UNMET_CONSTRAINT operator tests — hermetic.

Pins the constitutional gates:
- Art. XX: no documented failure -> PROBLEM_NOT_DOCUMENTED, zero candidates.
- Art. XXI.3: provider failure -> BLOCKED_PROVIDER_FAILURE, never 'no failures'.
- Art. XXI.5: MAUDE counts carry FDA limitations; sample disclosed vs population.
- Art. XXI.2: unexplored directions carry the not-a-novelty caveat.
- Art. XXVII: recurrence threshold is declared MODEL_DERIVED with justification.
- Art. XXVIII: epistemic classes per stage, no silent promotion.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceQueryResult, SourceRecord,
)
from discovery_fabric.discovery_modes import device_failure as df


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "log.jsonl")
    yield


def _maude_result(records, total=0):
    return SourceQueryResult(source_id="fda_maude", status=STATUS_OK, ok=True,
                             http_status=200, records=records, total_hits=total)


def _rec(i: int, problems=None, event_type="Malfunction", brand="PACER X"):
    return SourceRecord(
        source_id="fda_maude", role="ADVERSE_EVENT", record_id=f"maude:{i}",
        title="t", uri="u", retrieved_at="2026-01-01T00:00:00Z",
        query="q", raw_payload_sha256=f"{i:064d}",
        normalized={
            "mdr_report_key": str(i), "report_number": f"R{i}",
            "event_type": event_type, "product_problems": problems or [],
            "device_brand_name": brand, "date_received": "2024-06-01",
            "pma_pmn_number": "K100",
        },
        provenance={"provider": "fda_maude"},
        limitations=list(df.MAUDE_LIMITATIONS) if hasattr(df, "MAUDE_LIMITATIONS") else
        ["REPORT_COUNT_SEMANTICS: counts are raw report counts, NOT incidence or event rates"],
    )


class TestProblemExistenceGate:
    def test_no_documented_failure_no_candidates(self, monkeypatch):
        # Art. XX: both providers answer definitively-empty -> no candidates
        def _empty_result(q, timeout=40):
            from discovery_fabric.source_registry.connectors.openfda import MaudeConnector
            c = MaudeConnector()
            monkeypatch.setattr(c, "search", lambda q2, timeout=40: SourceQueryResult(
                source_id=c.SOURCE_ID, status=STATUS_EMPTY, ok=True, http_status=404))
            return c.search(q)
        monkeypatch.setattr(df, "retrieve_failures", lambda *a, **k: {
            "device_query": "ghost device", "maude": SourceQueryResult(
                source_id="fda_maude", status=STATUS_EMPTY, ok=True, http_status=404),
            "recall": SourceQueryResult(
                source_id="fda_recall", status=STATUS_EMPTY, ok=True, http_status=404),
            "provider_failures": [], "blocked": False,
        })
        out = df.discover_from_failure("ghost device")
        gate = [s for s in out["chain_steps"]
                if s["step"] == "problem_existence_gate"]
        assert gate and gate[0]["status"] == "PROBLEM_NOT_DOCUMENTED"
        assert out["candidates"] == []

    def test_provider_failure_blocks_chain(self, monkeypatch):
        # Art. XXI.3: transport failure is NOT 'no failures'
        monkeypatch.setattr(df, "retrieve_failures", lambda *a, **k: {
            "device_query": "x", "maude": SourceQueryResult(
                source_id="fda_maude", status="TIMEOUT", ok=False),
            "recall": SourceQueryResult(
                source_id="fda_recall", status="SEARCH_FAILED", ok=False),
            "provider_failures": [
                {"source_id": "fda_maude", "status": "TIMEOUT"},
                {"source_id": "fda_recall", "status": "SEARCH_FAILED"},
            ],
            "blocked": True,
        })
        out = df.discover_from_failure("anything")
        assert out["blocked"] is True
        assert out["candidates"] == []
        step = out["chain_steps"][0]
        assert step["status"] == "BLOCKED_PROVIDER_FAILURE"
        assert len(step["provider_failures"]) == 2


class TestClustering:
    def test_clusters_carry_fda_limitations(self):
        records = [_rec(i, problems=["Battery Depletion"]) for i in range(7)]
        clusters = df.cluster_mechanisms(_maude_result(records))
        assert len(clusters) == 1
        assert clusters[0].report_count == 7
        assert any("NOT incidence" in lim for lim in clusters[0].limitations)

    def test_below_threshold_cluster_not_recurring(self):
        records = [_rec(i, problems=["Odd Noise"]) for i in range(3)]
        clusters = df.cluster_mechanisms(_maude_result(records))
        assert clusters[0].report_count == 3
        assert clusters[0].report_count < df.RECURRENCE_MIN_REPORTS

    def test_threshold_is_declared_model_derived(self):
        # Art. XXVII: no threshold invention
        basis = df.RECURRENCE_THRESHOLD_BASIS
        assert basis["class"] == "MODEL_DERIVED"
        assert len(basis["justification"]) > 50
        assert "NOT a clinical incidence" in basis["justification"]


class TestConstraintDerivation:
    def test_constraint_is_ai_inference_with_trace(self):
        records = [_rec(i, problems=["Lead Fracture"]) for i in range(6)]
        clusters = df.cluster_mechanisms(_maude_result(records))
        constraint = df.derive_constraint(clusters[0], "pacemaker lead")
        assert constraint["epistemic_class"] == "AI_INFERENCE"
        assert constraint["derivation_trace"]
        assert constraint["problem_existence_gate"]["incidence_unknown"] is True
        assert constraint["problem_existence_gate"]["causality_unverified"] is True


class TestUnexploredSpace:
    def _attempted(self, titles):
        recs = []
        for i, t in enumerate(titles):
            recs.append({
                "record_id": f"europepmc:{i}", "title": t, "uri": "u",
                "raw_payload_sha256": f"{i:064d}",
                "relevance": "RELEVANT",
                "relevance_basis": {"overlapping_terms": ["fracture", "lead"]},
            })
        return {
            "query": "q",
            "literature": {"source_status": "OK", "retrieved": len(recs),
                           "relevant": len(recs), "records": recs},
            "patents": {"status": "UNAVAILABLE", "error": "503",
                        "record_count": 0, "note": ""},
        }

    def test_matching_axis_without_attempts_is_direction(self):
        records = [_rec(i, problems=["Lead Fracture"]) for i in range(6)]
        cluster = df.cluster_mechanisms(_maude_result(records))[0]
        # attempts address OTHER axes (infection) — fracture axes unexplored
        attempted = self._attempted(["infection prevention coating study"])
        space = df.unexplored_mechanism_space(cluster, attempted)
        axes = [d["direction"] for d in space]
        assert "LOAD_PATH_REDISTRIBUTION" in axes
        assert "MATERIAL_SUBSTITUTION" in axes

    def test_attempted_axis_excluded(self):
        records = [_rec(i, problems=["Lead Fracture"]) for i in range(6)]
        cluster = df.cluster_mechanisms(_maude_result(records))[0]
        # attempts address fracture via material toughness
        attempted = self._attempted(["material toughness fracture resistance lead"])
        space = df.unexplored_mechanism_space(cluster, attempted)
        axes = [d["direction"] for d in space]
        assert "MATERIAL_SUBSTITUTION" not in axes

    def test_every_direction_carries_not_novelty_caveat(self):
        records = [_rec(i, problems=["Battery Depletion"]) for i in range(6)]
        cluster = df.cluster_mechanisms(_maude_result(records))[0]
        attempted = self._attempted(["infection prevention coating study"])
        space = df.unexplored_mechanism_space(cluster, attempted)
        assert space
        for d in space:
            assert "NOT_NOVELTY" in d["caveat"] or "NOT a novelty determination" in d["caveat"]
            assert d["epistemic_class"] == "HYPOTHESIS"


class TestRemainingLimitation:
    def test_limitation_bounded_by_retrieved_set(self):
        attempted = self = None  # noqa: F841 — constructed inline below
        attempted = {
            "query": "q",
            "literature": {"source_status": "OK", "retrieved": 8, "relevant": 3,
                           "records": []},
            "patents": {"status": "UNAVAILABLE", "error": "503", "record_count": 0},
        }
        constraint = {
            "constraint_statement": "Devices must maintain function despite lead fracture",
            "derivation_basis": {"mechanism": "lead fracture"},
        }
        lim = df.remaining_limitation(attempted, constraint)
        assert lim["epistemic_class"] == "AI_INFERENCE"
        assert lim["basis"]["exhaustive_survey"] is False
        assert "non-exhaustive" in lim["limitation_statement"]
