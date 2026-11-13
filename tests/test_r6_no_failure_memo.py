"""tests/test_r6_no_failure_memo.py — OWNER DIRECTIVE 2026-11-12:
NEVER CACHE OR MEMOIZE FAILURES.

Measured defect (owner audit facts fe44d79e0): the cache/stage memo
replayed a frozen EVALUATOR_CALL_FAILED verbatim, so a pair could never
form — an infrastructure failure is not a result. Pins:
  1. the call cache stores ONLY finish_reason=stop (a "length" cut is
     infrastructure truncation, never replayed);
  2. a stage whose payload carries a typed infrastructure state is
     never memoized (memo_skipped rides the stage_log entry);
  3. content outcomes (typed kills) stay memoizable (a typed loss is
     data — owner, same round).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_economy as econ  # noqa: E402


@pytest.fixture()
def econ_store(tmp_path, monkeypatch):
    monkeypatch.setenv("FABRIC_LLM_ECONOMY_DIR", str(tmp_path / "econ"))
    monkeypatch.setenv("FABRIC_LLM_CACHE", "rw")
    econ._counters.update({"cache_writes": 0, "cache_hits": 0,
                           "cache_misses": 0})
    yield tmp_path


def test_call_cache_rejects_non_stop_finish(econ_store):
    key = "a" * 32
    econ.cache_put(key, {"content": "cut draft", "finish_reason": "length",
                         "model": "m", "provider_id": "zai"})
    # the "length" entry must NOT be readable back (an infrastructure
    # truncation is never a result) — cache_put itself refuses to write
    # it when the caller passes the typed finish (registry gate), and a
    # poisoned legacy entry reads back with its typed finish so the
    # reader can refuse it
    assert econ.cache_get(key) is None or \
        econ.cache_get(key).get("finish_reason") != "length"


def test_stage_memo_skips_infrastructure_failure(tmp_path, monkeypatch):
    # a recorded failed-evaluator envelope: the ATTACK stage's payload
    # carries EVALUATOR_CALL_FAILED — the memo must refuse to store it
    monkeypatch.setenv("FABRIC_LLM_CACHE", "rw")
    from discovery_fabric.engine import candidate as cand
    from discovery_fabric.engine.candidate import Candidate
    monkeypatch.setenv("FABRIC_LLM_ECONOMY_DIR", str(tmp_path / "econ"))

    class _Adapter:
        capability_id = "ATTACK_ENGINE"
        module_path = "discovery_fabric/a2/adversarial.py"
        canonical_fn = "adversarial_challenge"

        def execute(self, env, run_ctx):
            return {"_engine_result": True,
                    "apply_to": {"attack_results": {
                        "overall": "EVALUATOR_CALL_FAILED"}},
                    "status": "OK"}

    c = Candidate(problem={"problem_id": "p1"}, problem_id="p1")
    entry = c.run_stage("ATTACK", _Adapter.capability_id,
                    _Adapter.module_path, _Adapter.canonical_fn,
                    _Adapter().execute, c, {})
    # the payload's typed infrastructure state blocked the memo put
    assert entry.get("memo_skipped", "").startswith(
        "INFRASTRUCTURE_STATE:")
    stored = list((tmp_path / "econ" / "stages").glob("*.json")) \
        if (tmp_path / "econ" / "stages").exists() else []
    assert not stored, \
        f"an infrastructure-failure stage was memoized: {stored}"


def test_stage_memo_still_stores_content_outcomes(tmp_path, monkeypatch):
    # a typed KILL is data (owner, same round): the memo stores it
    monkeypatch.setenv("FABRIC_LLM_CACHE", "rw")
    from discovery_fabric.engine import candidate as cand
    from discovery_fabric.engine.candidate import Candidate
    monkeypatch.setenv("FABRIC_LLM_ECONOMY_DIR", str(tmp_path / "econ"))

    class _Adapter:
        capability_id = "ATTACK_ENGINE"
        module_path = "discovery_fabric/a2/adversarial.py"
        canonical_fn = "adversarial_challenge"

        def execute(self, env, run_ctx):
            return {"_engine_result": True,
                    "apply_to": {"attack_results": {
                        "overall": "KILLED", "killed_count": 1}},
                    "status": "OK"}

    c = Candidate(problem={"problem_id": "p1"}, problem_id="p1")
    entry = c.run_stage("ATTACK", _Adapter.capability_id,
                    _Adapter.module_path, _Adapter.canonical_fn,
                    _Adapter().execute, c, {})
    assert not entry.get("memo_skipped")
    stored = list((tmp_path / "econ" / "stages").glob("*.json"))
    assert stored, "a typed-kill content outcome must stay memoizable"
    hit = json.loads(stored[0].read_text(encoding="utf-8"))
    assert (hit.get("apply_to") or {}).get("attack_results", {}) \
        .get("overall") == "KILLED"
