"""R6 per-job wall budget in the retrieval fan-out (owner directive:
FAST and LEAN). Measured basis (R6 fresh-run 1): fanout_wall_s ==
max_job_wall_s (48.6 s sofc / 30.1 s new02) — ONE straggler gated the
whole phase while productive jobs finished in <= 10-20 s. The budget
caps the phase: finished jobs keep their records; a cut job is a TYPED
timeout in the fabric's existing lane vocabulary (never a silent drop,
Art. XXI.3 / XXV), and the cut list rides the attribution record.
"""
import os
import time
from types import SimpleNamespace

import pytest

from discovery_fabric.retrieval_fabric.pipeline import (
    _drive_fanout, _job_budget_s, _timeout_result,
)
from discovery_fabric.retrieval_fabric.canonical import Canonicalizer


def _conn(status="SUCCESS", records=None, sleep_s=0.0, error=None):
    def search(query, retrieval_role="DISCOVERY"):
        if sleep_s:
            time.sleep(sleep_s)
        return SimpleNamespace(status=status, records=records or [],
                               error=error)
    return SimpleNamespace(search=search)


def _plan(jobs_spec):
    """Build a minimal fan-out plan (job units only)."""
    plan = []
    for i, (source_id, conn) in enumerate(jobs_spec):
        plan.append({"kind": "job", "job": {
            "index": i, "lane": "SCHOLARLY", "source_id": source_id,
            "scoped": False,
            "variants": [{"query": "q1", "derivation_class": "PRIMARY"}],
            "connector": conn}})
    return plan


def test_job_budget_default_and_env(monkeypatch):
    monkeypatch.delenv("RETRIEVE_JOB_BUDGET_S", raising=False)
    assert _job_budget_s() == 20.0
    monkeypatch.setenv("RETRIEVE_JOB_BUDGET_S", "7.5")
    assert _job_budget_s() == 7.5
    monkeypatch.setenv("RETRIEVE_JOB_BUDGET_S", "0")
    assert _job_budget_s() == 0.0  # 0 disables the budget


def test_slow_job_cut_typed_fast_jobs_keep(monkeypatch):
    monkeypatch.setenv("RETRIEVE_JOB_BUDGET_S", "0.5")
    plan = _plan([
        ("slow_source", _conn(sleep_s=3.0)),
        ("fast_source", _conn()),
    ])
    canon = Canonicalizer()
    lane_states = []
    t0 = time.perf_counter()
    attr = _drive_fanout(plan, canon, lane_states,
                         {"mode": "parallel", "max_workers_configured": 2})
    wall = time.perf_counter() - t0
    # the phase is capped near the budget, NOT at the straggler's sleep
    assert wall < 2.5, wall
    assert attr["fanout_wall_s"] < 2.5
    # the cut is typed and recorded
    assert attr["job_budget_cut"] == ["slow_source"]
    slow = [r for r in attr["jobs"] if r["source_id"] == "slow_source"]
    fast = [r for r in attr["jobs"] if r["source_id"] == "fast_source"]
    assert slow and fast
    slow_row = slow[0]
    # the placeholder outcome carries the typed timeout status
    statuses = [vd["transport_status"]
                for vd in slow_row["variant_details"]]
    assert statuses == ["timeout"], slow_row["variant_details"]
    # the lane state for the cut source is the typed timeout (the
    # fabric's existing vocabulary), never a silent drop
    slow_lane = [s for s in lane_states
                 if getattr(s, "source_id", "") == "slow_source"]
    assert slow_lane and slow_lane[-1].status == "timeout"
    assert "RETRIEVE_JOB_BUDGET_EXCEEDED" in (slow_lane[-1].error or "")
    # the fast job is untouched
    fast_statuses = [vd["transport_status"]
                     for vd in fast[0]["variant_details"]]
    assert fast_statuses == ["SUCCESS"]


def test_budget_disabled_keeps_serial_parity(monkeypatch):
    monkeypatch.setenv("RETRIEVE_JOB_BUDGET_S", "0")
    plan = _plan([("slow_source", _conn(sleep_s=0.6))])
    canon = Canonicalizer()
    lane_states = []
    t0 = time.perf_counter()
    attr = _drive_fanout(plan, canon, lane_states,
                         {"mode": "parallel", "max_workers_configured": 1})
    wall = time.perf_counter() - t0
    # no budget: the straggler completes (this is the parity reference)
    assert wall >= 0.6, wall
    assert attr["job_budget_cut"] == []
    row = attr["jobs"][0]
    assert [vd["transport_status"]
            for vd in row["variant_details"]] == ["SUCCESS"]


def test_timeout_result_shape():
    job = {"variants": [{"query": "a", "derivation_class": "PRIMARY"},
                        {"query": "b", "derivation_class": "EXPANSION"}]}
    res = _timeout_result(job, 3, 20.0)
    assert res["index"] == 3
    assert len(res["variant_outcomes"]) == 2
    for vo in res["variant_outcomes"]:
        assert vo["raised"] is None
        assert vo["status"] == "timeout"
        assert vo["records"] == []
        assert "RETRIEVE_JOB_BUDGET_EXCEEDED" in (vo["error"] or "")
