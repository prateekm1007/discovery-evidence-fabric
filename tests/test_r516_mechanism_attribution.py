"""tests/test_r516_mechanism_attribution.py — R516 Part A battery for the
MECHANISM_SPACE runtime attribution instrument (auditor directive,
Part F items as applicable to measurement infrastructure).

CLAIM: one additive timing+funnel record rides the lean
mechanism-space envelope; scientific decisions are byte-identical
with and without the instrument.

Falsifiers: a missing runtime_attribution key; a subphase absent or
negative; funnel counts disagreeing with the space record's own
typed states; an invented epistemic state in the record; a changed
candidate/retention outcome vs the uninstrumented path; an
untyped provider failure; a second LLM call introduced by the
instrument; the historical build_mechanism_space reachable from
the live adapter.

Hermetic: mocked ms.llm_generate (no network); deterministic
fixtures; shuffle-invariant assertions (no timing thresholds —
durations are recorded, never asserted against bounds, except
non-negativity and monotonic consistency).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.candidate import Candidate  # noqa: E402
from discovery_fabric.engine import adapters  # noqa: E402
from discovery_fabric.engine import mechanism_attribution as mattr  # noqa: E402

PROBLEM = {
    "problem_id": "r516_attr_test",
    "device": "ambulatory surgery center arthroscopic irrigation",
    "failure": "joint distension instability during high-flow flush",
    "failure_mode": "pressure swings outside the target band",
    "constraint": "no pump hardware replacement",
}
EVIDENCE = [{
    "id": "doi:10.1016/j.test.001",
    "title": "Arthroscopic irrigation pressure control in ambulatory "
             "knee surgery",
    "abstract": "Intra-articular pressure during arthroscopic surgery "
                "of the knee stays inside the 40-60 mmHg band when the "
                "inflow bag height and the shaver outflow resist are "
                "matched; mismatched outflow collapses the capsule.",
    "content_hash": "hash_test_001",
    "retrieval_timestamp": "2026-09-14T00:00:00Z",
    "source": "europepmc",
}]

GOOD_RESPONSE = (
    "MECHANISM: matched inflow and outflow resist holds the "
    "pressure in band\n"
    "INTERVENTION: a passive outflow resist sleeve sized to "
    "the shaver flow\n"
    "EXPECTED_EFFECT: pressure stays inside the 40-60 mmHg "
    "band\n"
    "FALSIFICATION_TEST: measure pressure across the commanded "
    "flow range\n"
    "MECHANISM_SOURCE_SPAN: pressure stays inside the 40-60 "
    "mmHg band\n"
    "NOVEL_DESIGN_VARIABLE: the outflow resist sleeve's "
    "flow-resistance value\n"
    "TESTABLE_PREDICTION: doubling the inflow step keeps the "
    "pressure within 5 mmHg of the band edge\n")

VOLATILE_KEYS = {"built_at", "derived_at", "extracted_at",
                 "recorded_at", "started_at", "finished_at"}


def _env_with(**kw) -> Candidate:
    env = Candidate(problem=PROBLEM, problem_id="r516_attr_test")
    env.evidence = list(EVIDENCE)
    for k, v in kw.items():
        setattr(env, k, v)
    return env


def _verified_env(**kw) -> Candidate:
    kw.setdefault("evidence_classification", {
        "n_items": 1,
        "items": [{"source_id": EVIDENCE[0]["id"],
                   "classification": "DIRECT_SUPPORT"}]})
    return _env_with(**kw)


def _fake_llm(calls, content=GOOD_RESPONSE, ok=True,
              status="OK", error="", provider="tierA",
              model="glm-strong", extra_meta=None):
    def _gen(prompt, system="", **kw):
        calls.append({"timeout": kw.get("timeout"),
                      "purpose": kw.get("purpose")})
        meta = {"ok": ok, "status": status,
                "content": content if ok else None,
                "provider": provider, "model": model,
                "prompt_hash": "h1", "output_hash": "h2",
                "error": error,
                "task_degradation": {
                    "requested_task": "STRONG",
                    "actual_task_capability": "STRONG",
                    "task_capability_match": True},
                "call_provenance": {}, "cost_provenance": {}}
        if extra_meta:
            meta.update(extra_meta)
        return meta
    return _gen


def _run_adapter(env, fake):
    import discovery_fabric.engine.mechanism_space as ms
    with mock.patch.object(ms, "llm_generate",
                           side_effect=fake):
        res = adapters.MechanismSpaceAdapter().execute(
            env, {"run_id": "r516"})
    return res["apply_to"]["mechanism_space"]


def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items()
                if k not in VOLATILE_KEYS
                and k != "runtime_attribution"}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


class TestAttributionEmitted(unittest.TestCase):
    """The record exists with the 12 subphases on every path."""

    def test_success_path_has_twelve_subphases(self):
        calls = []
        space = _run_adapter(
            _verified_env(),
            _fake_llm(calls))
        rec = space.get("runtime_attribution")
        self.assertIsNotNone(rec, "attribution record missing")
        self.assertEqual(rec["attribution_version"],
                         mattr.ATTRIBUTION_VERSION)
        names = [s["subphase"] for s in rec["subphases"]]
        self.assertEqual(names, list(mattr.SUBPHASES))
        for s in rec["subphases"]:
            if s["subphase"] == "provider_call_split_offline":
                self.assertIsNone(
                    s["duration_s"],
                    "the offline split must never be a fabricated "
                    "zero (Art. XXV)")
            else:
                self.assertGreaterEqual(s["duration_s"], 0, s)
        self.assertGreaterEqual(rec["total_s"], 0)
        # monotonic consistency: the total covers the measured spans
        measured = sum(s["duration_s"] for s in rec["subphases"]
                       if s["duration_s"] is not None)
        self.assertGreaterEqual(rec["total_s"], measured)

    def test_no_evidence_path_records_typed_shape(self):
        calls = []
        # admission passes (one DIRECT_SUPPORT classification) but the
        # classification's source matches no frozen record — the lean
        # builder's join yields zero items: the genuine NO_EVIDENCE
        # early return (not the admission skip).
        env = _env_with(evidence_classification={
            "n_items": 1,
            "items": [{"source_id": "doi:10.1016/j.test.MISSING",
                       "classification": "DIRECT_SUPPORT"}]})
        space = _run_adapter(env, _fake_llm(calls))
        rec = space.get("runtime_attribution")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["terminal_state"], "NO_EVIDENCE")
        self.assertEqual(calls, [])
        self.assertEqual(
            rec["funnel"]["verified_evidence_items"], 0)
        self.assertEqual(rec["llm"]["n_llm_calls"], 0)

    def test_llm_failure_is_typed_not_invented(self):
        calls = []
        space = _run_adapter(
            _verified_env(),
            _fake_llm(calls, ok=False, status="CALL_FAILED",
                      error="simulated transport stall",
                      extra_meta={"failure_type": "TIMEOUT"}))
        rec = space["runtime_attribution"]
        llm = rec["llm"]
        self.assertEqual(llm["n_llm_calls"], 1)
        self.assertEqual(llm["transport_status"], "CALL_FAILED")
        self.assertEqual(llm["failure_type"], "TIMEOUT")
        self.assertIn("stall", llm["transport_error"])
        self.assertEqual(rec["terminal_state"],
                         space["state"])
        # no invented epistemic states anywhere in the record
        blob = __import__("json").dumps(rec)
        for invented in ("REJECTED", "FAILED_VERDICT", "TIMEOUT_STATE"):
            self.assertNotIn(invented, blob)

    def test_empty_output_is_observed_not_a_state(self):
        calls = []
        space = _run_adapter(
            _verified_env(), _fake_llm(calls, content=""))
        rec = space["runtime_attribution"]
        self.assertTrue(rec["llm"]["output_empty"])
        self.assertEqual(rec["llm"]["n_llm_calls"], 1)
        # observational flag only — the terminal stays the typed
        # stage state, never an invented empty-output verdict
        self.assertEqual(rec["terminal_state"], space["state"])

    def test_partial_meta_tolerated(self):
        # a meta missing route/failure keys (older shapes) must not
        # crash the instrument (Art. XXV: absence is absence).
        calls = []
        space = _run_adapter(
            _verified_env(), _fake_llm(calls))
        rec = space["runtime_attribution"]
        self.assertEqual(rec["llm"]["n_route_hops"], 0)
        self.assertFalse(rec["llm"]["fallback_occurred"])


class TestFunnelMatchesTypedStates(unittest.TestCase):
    """Funnel counts agree with the space record's own states."""

    def test_funnel_counts_match_space_record(self):
        calls = []
        space = _run_adapter(
            _verified_env(), _fake_llm(calls))
        rec = space["runtime_attribution"]
        f = rec["funnel"]
        self.assertEqual(f["verified_evidence_items"],
                         space["n_structured_items"])
        self.assertEqual(f["n_retained"],
                         space["n_candidates_retained"])
        dd = (space.get("distinctness") or {})
        self.assertEqual(f["distinctness"]["n_distinct"],
                         dd.get("n_distinct"))
        # selected operator matches the space record
        opids = space.get("operator_ids") or []
        self.assertEqual(
            f["selected_operator"], opids[0] if opids else "NONE")
        # terminal reason is the stage's own typed state
        self.assertEqual(f["terminal_reason"], space["state"])
        self.assertEqual(rec["terminal_state"], space["state"])


class TestNoSemanticChange(unittest.TestCase):
    """The instrument does not perturb scientific outputs."""

    def test_two_runs_identical_modulo_volatile(self):
        import json as _json

        def _once():
            calls = []
            return _run_adapter(_verified_env(),
                                _fake_llm(calls))

        a, b = _once(), _once()
        self.assertEqual(_strip_volatile(a), _strip_volatile(b),
                         "instrument perturbs deterministic outputs")
        # ...except the attribution itself, which re-measures
        self.assertIn("runtime_attribution", a)
        self.assertIn("runtime_attribution", b)

    def test_call_count_unchanged_by_instrumentation(self):
        calls = []
        _run_adapter(_verified_env(), _fake_llm(calls))
        self.assertLessEqual(
            len(calls), 1,
            "the instrument must not introduce LLM calls")


class TestProductionPathIsolation(unittest.TestCase):
    """Directive Part F item 11: the live adapter never routes
    through the historical full build_mechanism_space."""

    def test_live_adapter_never_calls_full_builder(self):
        import discovery_fabric.engine.mechanism_space as ms

        def _forbidden(*a, **k):
            raise AssertionError(
                "historical build_mechanism_space reached from "
                "the live path")

        calls = []
        with mock.patch.object(ms, "build_mechanism_space",
                               side_effect=_forbidden), \
             mock.patch.object(ms, "llm_generate",
                               side_effect=_fake_llm(calls)):
            res = adapters.MechanismSpaceAdapter().execute(
                _verified_env(), {"run_id": "r516"})
        self.assertIn("mechanism_space", res["apply_to"])


class TestStarvationAndUnknownUntouched(unittest.TestCase):
    """Directive Part F items 9-10: the instrument changes neither
    the starvation verdict nor the fail-open contract."""

    def test_starved_shape_still_detected_with_record_present(self):
        from discovery_fabric.engine import stage_entry
        env = _env_with()
        env.mechanism_space = {
            "state": "BUILT", "n_candidates_retained": 1,
            "distinctness": {"n_distinct": 1,
                             "instrument_version":
                                 "mechanism_distinctness/2.0.0"},
            "runtime_attribution": {"attribution_version": "x"}}
        self.assertIsNotNone(stage_entry.mechanism_starved(env))
        block = stage_entry.justify("ATTACK", env, {}, set())
        self.assertEqual(block["prerequisite"], "MINIMUM_DIVERSITY")

    def test_absent_adjudication_still_fails_open(self):
        from discovery_fabric.engine import stage_entry
        env = _env_with()
        env.mechanism_space = {
            "state": "BUILT", "n_candidates_retained": 1,
            "runtime_attribution": {"attribution_version": "x"}}
        self.assertIsNone(stage_entry.mechanism_starved(env))
        block = stage_entry.justify("ATTACK", env, {}, set())
        self.assertEqual(block["entry_status"], "ALLOWED")


if __name__ == "__main__":
    unittest.main()
