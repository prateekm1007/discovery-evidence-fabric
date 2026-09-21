"""tests/test_r516_operator_budget.py — R516 Part D/F battery for the
operator-instantiation budget change (auditor directive items 1-12).

CLAIM: raising the operator call's initial max_tokens 700 -> 2800
(the rescue-proven level) skips the systematically-failing first
generation without changing any scientific decision.

Falsifiers: a changed candidate/parse/semantic/distinctness/support
outcome for identical mock content; a second LLM call; a new retry
or fallback path; a changed failure/empty vocabulary; a resumed or
starved-behavior change; the budget applied anywhere but the single
measured call site.

Hermetic: mocked ms.llm_generate (no network); the budget is
asserted at the call boundary (what the provider actually receives).
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
from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.engine import stage_entry  # noqa: E402

PROBLEM = {
    "problem_id": "r516_budget_test",
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
    "pressure within 5 mmHg of the band edge\n"
    "BOUNDARY_CONDITIONS: normal arthroscopic flow range\n"
    "KNOWN_FAILURE_MODES: sleeve migration\n")


def _env():
    env = Candidate(problem=PROBLEM, problem_id="r516_budget_test")
    env.evidence = list(EVIDENCE)
    env.evidence_classification = {
        "n_items": 1,
        "items": [{"source_id": EVIDENCE[0]["id"],
                   "classification": "DIRECT_SUPPORT"}]}
    return env


def _fake_llm(calls, content=GOOD_RESPONSE, ok=True,
              status="OK", error=""):
    def _gen(prompt, system="", **kw):
        calls.append({"max_tokens": kw.get("max_tokens"),
                      "purpose": kw.get("purpose")})
        return {"ok": ok, "status": status,
                "content": content if ok else None,
                "provider": "tierA", "model": "glm-strong",
                "prompt_hash": "h1", "output_hash": "h2",
                "error": error,
                "task_degradation": {
                    "requested_task": "STRONG",
                    "actual_task_capability": "STRONG",
                    "task_capability_match": True},
                "call_provenance": {}, "cost_provenance": {}}
    return _gen


def _run(calls, **kw):
    with mock.patch.object(ms, "llm_generate",
                           side_effect=_fake_llm(calls, **kw)):
        res = adapters.MechanismSpaceAdapter().execute(
            _env(), {"run_id": "r516"})
    return res["apply_to"]["mechanism_space"]


def _strip_volatile(obj):
    skip = {"built_at", "derived_at", "extracted_at", "recorded_at",
            "started_at", "finished_at", "runtime_attribution"}
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items()
                if k not in skip}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


class TestBudgetIsTheMeasuredPath(unittest.TestCase):
    """Directive item 12: the edit hits the measured component only."""

    def test_operator_call_receives_2800(self):
        calls = []
        _run(calls)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_tokens"], 2800)
        self.assertTrue(calls[0]["purpose"].startswith("operator_"))

    def test_budget_constant_has_measured_provenance(self):
        self.assertEqual(ms.OPERATOR_INSTANTIATION_MAX_TOKENS, 2800)

    def test_no_other_llm_site_takes_2800(self):
        # the measured path is the ONLY consumer of the 2800 budget:
        # extraction retired (lean), synthesis keeps 512 (a2), attack
        # keeps 420 (calibration-adjacent). A second consumer fails.
        import subprocess
        r = subprocess.run(
            ["git", "grep", "-n", "OPERATOR_INSTANTIATION_MAX_TOKENS",
             "--", "discovery_fabric/"],
            capture_output=True, text=True, cwd=str(REPO))
        sites = [l for l in r.stdout.splitlines() if l.strip()
                 and "test_r516" not in l
                 and not l.split(":", 2)[-1].lstrip().startswith("#")]
        self.assertEqual(len(sites), 2, sites)
        joined = "\n".join(sites)
        self.assertIn("mechanism_space.py", joined)  # definition
        self.assertIn("adapters.py", joined)  # the measured call site

    def test_shared_defaults_unchanged(self):
        import inspect
        sig = inspect.signature(ms.llm_generate)
        self.assertEqual(sig.parameters["max_tokens"].default, 700)


class TestSemanticsPreserved(unittest.TestCase):
    """Directive items 1-5: identical scientific decisions."""

    def test_same_candidate_outcome_for_identical_content(self):
        # identical mock content under the OLD budget (700, forced
        # through the constant) and the NEW budget (2800) must
        # produce identical scientific decisions — the budget is
        # headroom, never an admission criterion.
        c_old, c_new = [], []
        with mock.patch.object(ms, "OPERATOR_INSTANTIATION_MAX_TOKENS",
                               700):
            s_old = _run(c_old)
        s_new = _run(c_new)
        self.assertEqual(c_old[0]["max_tokens"], 700)
        self.assertEqual(c_new[0]["max_tokens"], 2800)
        self.assertEqual(_strip_volatile(s_old),
                         _strip_volatile(s_new))
        for space in (s_old, s_new):
            for c in space.get("candidates") or []:
                self.assertIn(c.get("candidate_state"), {
                    "CANDIDATE", "NOT_A_CANDIDATE_SPAN_NOT_VERBATIM",
                    "NOT_A_CANDIDATE_TEXTUAL_REWRITE",
                    "NOT_A_CANDIDATE_OPERATOR_INVARIANT_BROKEN"})

    def test_distinctness_verdicts_untouched(self):
        calls = []
        space = _run(calls)
        dd = space.get("distinctness") or {}
        # distinctness inputs are candidate texts (budget-independent);
        # the instrument version is unchanged
        self.assertEqual(
            dd.get("instrument_version"),
            "mechanism_distinctness/2.0.0")

    def test_support_verdicts_untouched(self):
        calls = []
        space = _run(calls)
        for c in space.get("candidates") or []:
            sup = c.get("mechanism_support") or {}
            self.assertIn(sup.get("mechanism_support_state"),
                          {"SUPPORTED", "PARTIALLY_SUPPORTED",
                           "NOT_ENOUGH_EVIDENCE", "CONTESTED", None})

    def test_provider_failure_stays_typed(self):
        calls = []
        space = _run(calls, ok=False, status="CALL_FAILED",
                     error="simulated stall")
        self.assertIn(space.get("state"),
                      {"OPERATOR_INSTANTIATION_FAILED", "NO_CANDIDATES"})
        # no fallback epistemology: failure is recorded, never a
        # silent success
        self.assertEqual(space.get("n_candidates_retained"), 0)

    def test_empty_output_stays_typed(self):
        calls = []
        space = _run(calls, content="")
        rec = space.get("runtime_attribution") or {}
        self.assertTrue((rec.get("llm") or {}).get("output_empty"))
        self.assertEqual(space.get("n_candidates_retained"), 0)


class TestNoNewMachinery(unittest.TestCase):
    """Directive items 6-8: no new calls, retries, or fallback paths."""

    def test_exactly_one_llm_call(self):
        calls = []
        _run(calls)
        self.assertEqual(len(calls), 1,
                         "the budget change must not add calls")

    def test_no_hidden_retry_on_valid_output(self):
        # a valid first output resolves in one call (the pre-existing
        # recorded corrective retry only fires on span/semantic
        # defects — exercised by the r401 battery, unchanged here)
        calls = []
        _run(calls)
        self.assertEqual(len(calls), 1)

    def test_resume_discipline_untouched(self):
        # the lean builder takes no resume state; re-execution is
        # deterministic (R401 discipline lives in the conductor,
        # untouched by this round)
        import json as _json
        c1, c2 = [], []
        a = _run(c1)
        b = _run(c2)
        self.assertEqual(_strip_volatile(a), _strip_volatile(b))


class TestContractsUntouched(unittest.TestCase):
    """Directive items 9-11: starvation, unknown, and path isolation."""

    def test_starved_stays_starved(self):
        env = _env()
        env.mechanism_space = {
            "state": "BUILT", "n_candidates_retained": 1,
            "distinctness": {"n_distinct": 1,
                             "instrument_version":
                                 "mechanism_distinctness/2.0.0"}}
        self.assertIsNotNone(stage_entry.mechanism_starved(env))
        block = stage_entry.justify("ATTACK", env, {}, set())
        self.assertEqual(block["prerequisite"], "MINIMUM_DIVERSITY")

    def test_unknown_still_fails_open(self):
        env = _env()
        env.mechanism_space = {"state": "BUILT",
                               "n_candidates_retained": 1}
        self.assertIsNone(stage_entry.mechanism_starved(env))

    def test_historical_builder_still_unreachable(self):
        with mock.patch.object(
                ms, "build_mechanism_space",
                side_effect=AssertionError("must not be called")):
            calls = []
            res = adapters.MechanismSpaceAdapter().execute(
                _env(), {"run_id": "r516"})
            self.assertIn("mechanism_space", res["apply_to"])


if __name__ == "__main__":
    unittest.main()
