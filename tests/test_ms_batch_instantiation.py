"""tests/test_ms_batch_instantiation.py — R6 item 1 (owner directive:
"Batch multi-operator generation into fewer calls").

The batch transport concatenates every applicable (operator, item) pair
prompt VERBATIM under typed section headers, makes ONE llm_generate call,
and serves each pair's first instantiation from its section. The
validation pipeline (parse -> span binding -> assemble -> operator
semantics -> recorded corrective retry) is UNCHANGED; the legacy per-pair
path remains the typed fallback when the batch call fails wholesale.

Falsifiable claims (each test attacks a bypass, Art. XXX):
  B1. With MS_BATCH_INSTANTIATION=1 and >=2 applicable pairs, the space
      makes exactly ONE operator-instantiation LLM call (plus zero
      corrective retries on valid fixtures) and every pair still yields
      its CANDIDATE with batch_served provenance riding the record.
  B2. A missing section in an otherwise-OK batch response is a TYPED
      OPERATOR_INSTANTIATION_FAILED for that one pair — never a hidden
      per-pair recovery call (the call count stays 1).
  B3. A failed batch CALL degrades to the legacy per-pair path — the
      same candidates the legacy path would produce, typed fallback,
      honest n_pairs_fallback.
  B4. With the env off, the legacy path is untouched (status quo) and
      the candidate states are IDENTICAL to the batch path (parity).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from tests.test_r401_operator_behavior import (  # noqa: E402
    PROBLEM, M1_MEDICAL, M1_FOREIGN, _m2_lines, SPAN_MED, SPAN_FOREIGN)

BATCH_PURPOSE = "operator_batch_instantiation"


def _body_med():
    """Valid DIRECT_TRANSFER body for M1_MEDICAL (the r401
    test_valid_transfer response: same-domain transfer, verbatim span,
    semantically valid)."""
    return _m2_lines(
        "heparin bonding inhibits clotting cascade activation at "
        "the luminal surface",
        "bond heparin to the tunneled hemodialysis catheter lumen "
        "wall",
        "thrombus area reduced by 50 percent under low flow",
        "luminal heparin surface density",
        "thrombus area at 50 mL/min reduced by 50 percent versus "
        "untreated catheters",
        "heparin leaching; bonding delamination",
        "flow above 20 mL/min", SPAN_MED)


def _body_foreign():
    """Valid CROSS_DOMAIN_ANALOGY body for M1_FOREIGN (the r401
    test_valid_analogy response: foreign-domain anchor admitted on the
    STATED shared mechanism, verbatim span)."""
    return _m2_lines(
        "the same electrostatic repulsion mechanism as in the "
        "source system: repulsion of like charges at the boundary "
        "prevents particle deposition in the catheter lumen",
        "charge the catheter lumen wall with an applied "
        "electrostatic field to repel charged thrombus precursors",
        "deposition and thrombus reduced by repulsion",
        "applied lumen wall voltage",
        "deposition mass decreases as voltage rises from 0 to 2 kV",
        "discharge; field distortion by conductive fluid",
        "applied voltage 0-2 kV in blood", SPAN_FOREIGN)


def _batch_response(pairs):
    """pairs: [(op_id, item_id, body)] in the preflight's plan order."""
    out = []
    for i, (op_id, item_id, body) in enumerate(pairs):
        out.append(ms._batch_pair_header(i, op_id, item_id))
        out.append(body)
    return "\n\n".join(out)


class _Spy:
    """Purpose-routed llm_generate spy: records (purpose, max_tokens)
    and returns scripted responses per purpose."""

    def __init__(self, route):
        self.route = route          # purpose -> callable(prompt) -> meta
        self.calls = []

    def __call__(self, prompt, system="", timeout=240, max_tokens=700,
                 purpose="mechanism_space", exclude_providers=None,
                 hard_pin_provider=None):
        self.calls.append({"purpose": purpose, "max_tokens": max_tokens})
        fn = self.route.get(purpose)
        if fn is None:
            return {"ok": False, "status": "UNROUTED_CALL",
                    "error": f"spy has no route for {purpose}"}
        return fn(prompt)

    def count(self, purpose=None):
        if purpose is None:
            return len(self.calls)
        return sum(1 for c in self.calls if c["purpose"] == purpose)


_META_OK = {"ok": True, "status": "OK", "provider": "test-prov",
            "model": "test-model", "prompt_hash": "ph",
            "output_hash": "oh", "call_provenance": [],
            "task_degradation": None, "cost_provenance": {"basis": "TEST"}}


def _two_ops():
    ids = ("DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY")
    return [o for o in ms.TRANSFORMATION_OPERATORS if o["operator_id"] in ids]


def _two_items():
    # each item satisfies exactly one of the two operators' contracts:
    # DIRECT_TRANSFER -> M1_MEDICAL, CROSS_DOMAIN_ANALOGY -> M1_FOREIGN
    return [M1_MEDICAL, M1_FOREIGN]


def _run_both_ops(ops, items, problem):
    """Preflight (queue empty/filled by caller) + apply both operators;
    returns (states, first_candidates)."""
    states, firsts = [], []
    for op in ops:
        res = ms.apply_operator(op, items, problem, 2)
        cands = [c for c in res["candidates"] if isinstance(c, dict)]
        assert cands, f"{op['operator_id']} produced no candidate record"
        states.append(cands[0].get("candidate_state"))
        firsts.append(cands[0])
    return states, firsts


def test_b1_one_call_serves_every_pair(monkeypatch):
    monkeypatch.setenv(ms._MS_BATCH_ENV, "1")
    spy = _Spy({BATCH_PURPOSE: lambda p: {
        **_META_OK,
        "content": _batch_response([
            ("DIRECT_TRANSFER", M1_MEDICAL["item_id"], _body_med()),
            ("CROSS_DOMAIN_ANALOGY", M1_FOREIGN["item_id"],
             _body_foreign())])}})
    monkeypatch.setattr(ms, "llm_generate", spy)
    ops = _two_ops()
    rec = ms._preflight_operator_batch(ops, _two_items(), PROBLEM, 2)
    assert rec["n_pairs_planned"] == 2, rec
    assert rec["n_pairs_served"] == 2, rec
    assert rec["batch_call"]["ok"] is True
    states, firsts = _run_both_ops(ops, _two_items(), PROBLEM)
    # exactly ONE llm call (the batch), zero corrective retries
    assert spy.count() == 1, [c["purpose"] for c in spy.calls]
    assert spy.count(BATCH_PURPOSE) == 1
    assert all(s == "CANDIDATE" for s in states), states
    # the batch call's honest provenance rides every served candidate
    for c in firsts:
        bs = c.get("batch_served")
        if bs is None:
            dt = c.get("derivation_trace") or {}
            bs = dt.get("batch_served") if isinstance(dt, dict) else None
        assert isinstance(bs, dict) and "batched" in (bs.get("note") or "")
        assert bs.get("operator") in ("DIRECT_TRANSFER",
                                      "CROSS_DOMAIN_ANALOGY")


def test_b2_missing_section_is_typed_no_recovery(monkeypatch):
    monkeypatch.setenv(ms._MS_BATCH_ENV, "1")
    # only pair 0's section is present in the response
    spy = _Spy({BATCH_PURPOSE: lambda p: {
        **_META_OK,
        "content": _batch_response([
            ("DIRECT_TRANSFER", M1_MEDICAL["item_id"], _body_med())])}})
    monkeypatch.setattr(ms, "llm_generate", spy)
    ops = _two_ops()
    rec = ms._preflight_operator_batch(ops, _two_items(), PROBLEM, 2)
    assert rec["n_pairs_served"] == 1 and rec["n_sections_missing"] == 1
    failed = None
    ok_seen = False
    for op in ops:
        res = ms.apply_operator(op, [M1_MEDICAL, M1_FOREIGN], PROBLEM, 2)
        cands = [c for c in res["candidates"] if isinstance(c, dict)]
        assert cands
        r0 = cands[0]
        if r0.get("state") == "OPERATOR_INSTANTIATION_FAILED" or \
                r0.get("candidate_state") == \
                "OPERATOR_INSTANTIATION_FAILED":
            failed = r0
        elif r0.get("candidate_state") == "CANDIDATE":
            ok_seen = True
    # the served pair still produced its candidate
    assert ok_seen, "served pair lost its candidate"
    # the missing pair is TYPED failed with the batch basis, and the spy
    # saw NO recovery call (count stays exactly 1)
    assert failed is not None, "missing section was not recorded"
    assert failed.get("llm_status") == "BATCH_SECTION_MISSING", failed
    assert "no section" in (failed.get("llm_error") or "")
    assert spy.count() == 1, [c["purpose"] for c in spy.calls]


def test_b3_failed_batch_call_falls_back_legacy(monkeypatch):
    monkeypatch.setenv(ms._MS_BATCH_ENV, "1")
    bodies = {"DIRECT_TRANSFER": _body_med(),
              "CROSS_DOMAIN_ANALOGY": _body_foreign()}
    spy = _Spy({
        BATCH_PURPOSE: lambda p: {
            "ok": False, "status": "CALL_FAILED", "error": "429 storm"},
        "operator_DIRECT_TRANSFER": lambda p: {
            **_META_OK, "content": bodies["DIRECT_TRANSFER"]},
        "operator_CROSS_DOMAIN_ANALOGY": lambda p: {
            **_META_OK, "content": bodies["CROSS_DOMAIN_ANALOGY"]}})
    monkeypatch.setattr(ms, "llm_generate", spy)
    ops = _two_ops()
    rec = ms._preflight_operator_batch(ops, _two_items(), PROBLEM, 2)
    assert rec["batch_call"]["ok"] is False
    assert rec["n_pairs_fallback"] == 2, rec
    states, _ = _run_both_ops(ops, _two_items(), PROBLEM)
    # 1 failed batch + 2 legacy per-pair calls, both candidates valid
    assert spy.count() == 3, [c["purpose"] for c in spy.calls]
    assert all(s == "CANDIDATE" for s in states), states


def test_b4_env_off_legacy_parity(monkeypatch):
    ops = _two_ops()
    bodies = {"DIRECT_TRANSFER": _body_med(),
              "CROSS_DOMAIN_ANALOGY": _body_foreign()}
    # legacy path (env off): two per-pair calls, no batch plumbing
    monkeypatch.delenv(ms._MS_BATCH_ENV, raising=False)
    spy_legacy = _Spy({
        "operator_DIRECT_TRANSFER": lambda p: {
            **_META_OK, "content": bodies["DIRECT_TRANSFER"]},
        "operator_CROSS_DOMAIN_ANALOGY": lambda p: {
            **_META_OK, "content": bodies["CROSS_DOMAIN_ANALOGY"]}})
    monkeypatch.setattr(ms, "llm_generate", spy_legacy)
    legacy_states, _ = _run_both_ops(ops, _two_items(), PROBLEM)
    assert spy_legacy.count() == 2, [c["purpose"] for c in spy_legacy.calls]
    assert all(s == "CANDIDATE" for s in legacy_states)
    # batch path: SAME states from ONE call
    monkeypatch.setenv(ms._MS_BATCH_ENV, "1")
    spy_batch = _Spy({BATCH_PURPOSE: lambda p: {
        **_META_OK,
        "content": _batch_response([
            ("DIRECT_TRANSFER", M1_MEDICAL["item_id"], _body_med()),
            ("CROSS_DOMAIN_ANALOGY", M1_FOREIGN["item_id"],
             _body_foreign())])}})
    monkeypatch.setattr(ms, "llm_generate", spy_batch)
    rec = ms._preflight_operator_batch(ops, _two_items(), PROBLEM, 2)
    assert rec["n_pairs_served"] == 2
    batch_states, _ = _run_both_ops(ops, _two_items(), PROBLEM)
    assert spy_batch.count() == 1
    assert batch_states == legacy_states, (batch_states, legacy_states)


def test_batch_reset_hygiene(monkeypatch):
    monkeypatch.setenv(ms._MS_BATCH_ENV, "1")
    ms._BATCH_QUEUES["operator_X"] = [{"ok": True}]
    ms._batch_reset()
    assert ms._BATCH_QUEUES == {}
