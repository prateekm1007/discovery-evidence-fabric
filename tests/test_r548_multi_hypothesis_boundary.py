"""tests/test_r548_multi_hypothesis_boundary.py — the R548 audit
Round A battery (Constitution v2.10.1, audit problems 3/4 + the
dead-branch duplication).

Covers, in order:

  A. the multi-hypothesis parser (mechanism_space): three-block
     parse with field isolation, the _N_HYPOTHESES ceiling, the
     truncation-honesty rules (a cut response keeps ONLY the fields
     the model actually emitted — never invented, never guessed
     field names), and the legacy no-marker fallback (one block,
     backward compatible);
  B. the generation boundary itself: the prompt suffix requests N
     independently-parseable hypotheses, and the instantiation
     budget is pinned at the rescue-proven level (the truncation
     measurement against this budget happens on the live Round C
     responses — the constant is pinned HERE so a silent change
     cannot hide);
  C. the lean adapter end-to-end (mocked llm_generate): ONE call
     parses ALL blocks, the typed attempt record attributes EVERY
     parsed hypothesis (the audit item: pre-R548 it recorded block
     1 only), the Art. LXXXIV minimum is recorded as 2, the
     cemetery + distinctness tail covers every CANDIDATE-state
     block, the legacy block-1 top-level attempt fields stay
     byte-stable against attribution[0], and the LLM-failure path
     writes the typed OPERATOR_INSTANTIATION_FAILED record without
     crashing (the field_blocks UnboundLocalError regression —
     this test crashed the honest failure path before the fix);
  D. the Art. LXXXIV minimum-diversity gate (stage_entry): the
     minimum is 2 and is never lower, starvation fires at
     n_distinct=1, does not fire at 2, and never fires on unknown
     (Art. XXV);
  E. the R548 finished-flag ruling (user_state_view): a COMPLETE
     terminal with NO recorded completion answer is NOT finished
     (the BS-042 measured shape), a recorded positive final status
     keeps the legacy True, a recorded FINISHED_DISCOVERY answer
     overrides the residual, and the COMPLETED_UNKNOWN branch exists
     exactly once in source (the dead duplicate stays dead).

No live claims: every fixture below is synthetic; the live Round C
runs carry the truncation measurement.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters  # noqa: E402
from discovery_fabric.engine import stage_entry  # noqa: E402
from discovery_fabric.engine.candidate import Candidate  # noqa: E402
import discovery_fabric.engine.mechanism_space as ms  # noqa: E402

# ---------------------------------------------------------------------------
# the shared fixture (the r453 lean shape: one structured evidence item,
# a satisfied DIRECT_SUPPORT admission contract)
# ---------------------------------------------------------------------------
PROBLEM = {
    "problem_id": "r548_multi_hyp_test",
    "device": "ambulatory surgery center arthroscopic irrigation",
    "failure": "joint distension instability during high-flow flush",
    "failure_mode": "pressure swings outside the target band",
    "constraint": "no pump hardware replacement",
}
_EVIDENCE_ABSTRACT = (
    "Intra-articular pressure during arthroscopic surgery of the knee "
    "stays inside the 40-60 mmHg band when the inflow bag height and "
    "the shaver outflow resist are matched; mismatched outflow "
    "collapses the capsule.")
EVIDENCE = [{
    "id": "doi:10.1016/j.test.r548",
    "title": "Arthroscopic irrigation pressure control in ambulatory "
             "knee surgery",
    "abstract": _EVIDENCE_ABSTRACT,
    "content_hash": "hash_r548_001",
    "retrieval_timestamp": "2026-09-29T00:00:00Z",
    "source": "europepmc",
}]

# Three causally distinct hypothesis blocks (distinct mechanism graph,
# intervention site, and boundary regime — the prompt's own rule 2).
# Each block: the full 8-field schema; TESTABLE_PREDICTION carries a
# digit + >= 4 terms so _testable_prediction_check passes; every
# MECHANISM_SOURCE_SPAN is a VERBATIM substring of the evidence
# abstract (the span gate never sees an invented span).
_BLOCK_1 = (
    "MECHANISM: matched inflow and outflow resistance holds "
    "intra-articular pressure inside the operating band\n"
    "INTERVENTION: a passive outflow resist sleeve sized to the "
    "shaver flow\n"
    "PREDICTED_EFFECT: pressure stays inside the 40-60 mmHg band "
    "across commanded flow steps\n"
    "NOVEL_DESIGN_VARIABLE: the outflow resist sleeve flow-resistance "
    "value\n"
    "TESTABLE_PREDICTION: doubling the inflow step keeps pressure "
    "within 5 mmHg of the band edge across 10 trials\n"
    "KNOWN_FAILURE_MODES: sleeve fouling by debris reduces outflow "
    "resistance over time\n"
    "BOUNDARY_CONDITIONS: flow rates between 20 and 80 milliliters "
    "per minute\n"
    "MECHANISM_SOURCE_SPAN: stays inside the 40-60 mmHg band")
_BLOCK_2 = (
    "MECHANISM: pulsed outflow venting equalizes transient pressure "
    "spikes during shaver startups\n"
    "INTERVENTION: a pressure-triggered vent valve opened by a 10 ms "
    "pulse\n"
    "PREDICTED_EFFECT: spike amplitude drops by at least 15 mmHg "
    "during startup transients\n"
    "NOVEL_DESIGN_VARIABLE: the vent pulse width and trigger "
    "threshold\n"
    "TESTABLE_PREDICTION: a 10 ms vent pulse reduces startup spikes "
    "below 8 mmHg in 9 of 10 cycles\n"
    "KNOWN_FAILURE_MODES: valve latency delays the vent pulse beyond "
    "the spike window\n"
    "BOUNDARY_CONDITIONS: startup transients under 100 ms at flows "
    "up to 100 milliliters per minute\n"
    "MECHANISM_SOURCE_SPAN: mismatched outflow collapses the capsule")
_BLOCK_3 = (
    "MECHANISM: a cascaded proportional controller adjusts inflow "
    "against measured outflow in real time\n"
    "INTERVENTION: a closed-loop controller commanding the pump from "
    "a downstream pressure sensor\n"
    "PREDICTED_EFFECT: band excursions fall below 2 mmHg across "
    "variable flow loads\n"
    "NOVEL_DESIGN_VARIABLE: the controller proportional gain "
    "schedule\n"
    "TESTABLE_PREDICTION: closed-loop gain control holds pressure "
    "within 3 mmHg for flow loads up to 120 milliliters per minute\n"
    "KNOWN_FAILURE_MODES: sensor noise amplifies gain oscillations "
    "at low flow\n"
    "BOUNDARY_CONDITIONS: continuous operation at flows between 10 "
    "and 120 milliliters per minute\n"
    "MECHANISM_SOURCE_SPAN: the inflow bag height and the shaver "
    "outflow resist are matched")
THREE_BLOCKS = (
    "HYPOTHESIS 1:\n" + _BLOCK_1 +
    "\nHYPOTHESIS 2:\n" + _BLOCK_2 +
    "\nHYPOTHESIS 3:\n" + _BLOCK_3)

_EIGHT_FIELDS = ("mechanism", "intervention", "predicted_effect",
                 "novel_design_variable", "testable_prediction",
                 "known_failure_modes", "boundary_conditions",
                 "mechanism_source_span")


def _env() -> Candidate:
    env = Candidate(problem=PROBLEM, problem_id="r548_multi_hyp_test")
    env.evidence = list(EVIDENCE)
    env.evidence_classification = {
        "n_items": 1,
        "items": [{"source_id": EVIDENCE[0]["id"],
                   "classification": "DIRECT_SUPPORT"}]}
    return env


class _FakeLLM:
    """Records every llm_generate call; serves one canned response."""

    def __init__(self, content: str | None, ok: bool = True,
                 status: str = "OK"):
        self.content = content
        self.ok = ok
        self.status = status
        self.prompts: list[str] = []
        self.kwargs: list[dict] = []

    def __call__(self, prompt, system="", **kw):
        self.prompts.append(prompt)
        self.kwargs.append(kw)
        if not self.ok:
            return {"ok": False, "status": self.status, "error": "boom"}
        return {"ok": True, "status": "OK",
                "content": self.content,
                "provider": "tierA", "model": "glm-strong",
                "prompt_hash": "h1", "output_hash": "h2",
                "latency_ms": 100,
                "task_degradation": {
                    "requested_task": "STRONG",
                    "actual_task_capability": "STRONG",
                    "task_capability_match": True},
                "call_provenance": {}, "cost_provenance": {}}


def _run(fake: _FakeLLM):
    with mock.patch.object(ms, "llm_generate", side_effect=fake):
        res = adapters.MechanismSpaceAdapter().execute(
            _env(), {"run_id": "r548"})
    return res["apply_to"]["mechanism_space"]


# ---------------------------------------------------------------------------
# A. the parser
# ---------------------------------------------------------------------------
class TestMultiHypothesisParser(unittest.TestCase):

    def test_three_blocks_parse_with_isolated_fields(self):
        blocks = ms._parse_multi_candidate_fields(THREE_BLOCKS)
        self.assertEqual(len(blocks), 3)
        for blk, expected in zip(blocks, (_BLOCK_1, _BLOCK_2, _BLOCK_3)):
            self.assertEqual(
                sorted(k for k, v in blk.items() if str(v)),
                sorted(_EIGHT_FIELDS),
                "every block parses exactly the 8-field schema")
            # field isolation: no content leaks across blocks
            self.assertNotIn(blk["mechanism"], expected.replace(
                blk["mechanism"], ""))
        self.assertIn("matched inflow", blocks[0]["mechanism"])
        self.assertIn("pulsed outflow venting", blocks[1]["mechanism"])
        self.assertIn("cascaded proportional controller",
                      blocks[2]["mechanism"])
        self.assertEqual(blocks[0]["mechanism_source_span"],
                         "stays inside the 40-60 mmHg band")

    def test_default_ceiling_is_three_blocks(self):
        four = THREE_BLOCKS + (
            "\nHYPOTHESIS 4:\nMECHANISM: a fourth mechanism\n"
            "TESTABLE_PREDICTION: drops by 4 mmHg across 4 trials\n")
        blocks = ms._parse_multi_candidate_fields(four)
        self.assertEqual(len(blocks), 3,
                         "the _N_HYPOTHESES ceiling caps at 3")
        self.assertNotIn("a fourth mechanism",
                         blocks[-1]["mechanism"])

    def test_custom_ceiling_respected(self):
        blocks = ms._parse_multi_candidate_fields(
            THREE_BLOCKS, n_hypotheses=2)
        self.assertEqual(len(blocks), 2)

    def test_marker_only_truncation_drops_empty_block(self):
        cut = THREE_BLOCKS + "\nHYPOTHESIS 4:"
        blocks = ms._parse_multi_candidate_fields(cut)
        self.assertEqual(len(blocks), 3,
                         "a marker with zero emitted fields is dropped, "
                         "never an invented empty block")

    def test_mid_value_truncation_keeps_only_emitted_fields(self):
        # cut mid-value on block 2 (the token budget died)
        cut = ("HYPOTHESIS 1:\n" + _BLOCK_1 +
               "\nHYPOTHESIS 2:\n"
               "MECHANISM: partial mechanism emitted before the token "
               "budget ex")
        blocks = ms._parse_multi_candidate_fields(cut)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(
            blocks[1]["mechanism"],
            "partial mechanism emitted before the token budget ex")
        for f in _EIGHT_FIELDS:
            if f == "mechanism":
                continue
            self.assertEqual(
                blocks[1][f], "",
                f"truncation may never invent {f}")

    def test_cut_field_name_is_never_guessed(self):
        # cut mid-FIELD-NAME: "TESTABLE_PRED" has no colon and no
        # complete field token — the parser must not guess it
        cut = ("HYPOTHESIS 1:\n" + _BLOCK_1 +
               "\nHYPOTHESIS 2:\n"
               "MECHANISM: a second mechanism\nTESTABLE_PRED")
        blocks = ms._parse_multi_candidate_fields(cut)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[1]["testable_prediction"], "")
        self.assertEqual(blocks[1]["mechanism"], "a second mechanism")

    def test_no_marker_response_parses_as_single_legacy_block(self):
        blocks = ms._parse_multi_candidate_fields(_BLOCK_1)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(sorted(k for k, v in blocks[0].items() if str(v)),
                         sorted(_EIGHT_FIELDS))

    def test_empty_and_none_return_no_blocks(self):
        self.assertEqual(ms._parse_multi_candidate_fields(""), [])
        self.assertEqual(ms._parse_multi_candidate_fields(
            "HYPOTHESIS 1:\nMECHANISM:").__len__(), 0)
        # a marker line whose only content is a field NAME (no colon
        # value) still yields nothing nonempty
        self.assertEqual(ms._parse_multi_candidate_fields(None), [])


# ---------------------------------------------------------------------------
# B. the generation boundary (prompt + budget)
# ---------------------------------------------------------------------------
class TestPromptBoundary(unittest.TestCase):

    def test_prompt_requests_three_independent_hypotheses(self):
        suffix = ms._multi_hypothesis_prompt_suffix()
        self.assertIn("3 INDEPENDENTLY PARSEABLE", suffix)
        self.assertIn("HYPOTHESIS 3:", suffix)
        self.assertIn("8-field schema", suffix)
        self.assertIn("CAUSALLY DISTINCT", suffix)
        self.assertIn("never pad with rewordings", suffix)

    def test_budget_constant_pinned_at_rescue_level(self):
        """The instantiation budget that Round C measures truncation
        against (usage.completion_tokens vs this cap). If this
        constant changes, the R548 truncation measurement must be
        re-run — a silent raise would fake a clean measurement."""
        self.assertEqual(ms.OPERATOR_INSTANTIATION_MAX_TOKENS, 2800)
        self.assertEqual(ms._N_HYPOTHESES, 3)


# ---------------------------------------------------------------------------
# C. the lean adapter end-to-end
# ---------------------------------------------------------------------------
class TestLeanPathMultiHypothesis(unittest.TestCase):

    def test_one_call_parses_three_blocks_and_attributes_each(self):
        fake = _FakeLLM(THREE_BLOCKS)
        space = _run(fake)
        self.assertEqual(len(fake.prompts), 1,
                         "R453/R548: ONE instantiation call — N "
                         "hypotheses never cost a second call")
        self.assertIn("HYPOTHESIS 3:", fake.prompts[0])
        self.assertEqual(fake.kwargs[0].get("max_tokens"),
                         ms.OPERATOR_INSTANTIATION_MAX_TOKENS)

        att = space["instantiation_attempts"][0]
        self.assertEqual(att["hypothesis_blocks_parsed"], 3)
        self.assertEqual(len(att["hypothesis_attribution"]), 3)
        for i, entry in enumerate(att["hypothesis_attribution"], 1):
            self.assertEqual(entry["hypothesis_index"], i)
            self.assertEqual(entry["n_fields_nonempty"], 8)
            self.assertTrue(entry["mechanism"])
            self.assertIn(entry["candidate_state"],
                          ("CANDIDATE",
                           "NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION",
                           "NOT_A_CANDIDATE_TEXTUAL_REWRITE",
                           "NOT_A_CANDIDATE_SEMANTIC_INVARIANT_BROKEN"))
        self.assertEqual(
            [e["mechanism"] for e in att["hypothesis_attribution"]],
            [blocks["mechanism"] for blocks in
             ms._parse_multi_candidate_fields(THREE_BLOCKS)])

        # every assembled candidate carries its own index
        cands = space["operator_candidates_full"][0]["candidates"]
        self.assertEqual([c["hypothesis_index"] for c in cands],
                         [1, 2, 3])
        self.assertEqual(
            space["operator_results"][0]["n_hypotheses_parsed"], 3)

        # the Art. LXXXIV minimum is recorded as the constitution's
        # bar (2), never the old "at least 1" structural floor
        self.assertEqual(space["min_candidates_required"],
                         stage_entry.MINIMUM_DISTINCT_MECHANISMS)
        self.assertEqual(space["min_candidates_required"], 2)

        # legacy block-1 top-level attempt fields stay byte-stable
        # against attribution[0] (existing readers unaffected)
        for key in ("semantic_verdict", "candidate_state",
                    "candidate_id", "distinctness_verdict",
                    "support_state", "cemetery_blocked"):
            self.assertEqual(att[key], att["hypothesis_attribution"][0][key],
                             f"legacy {key} must equal block 1's "
                             f"attribution value")

    def test_cemetery_and_distinctness_cover_every_block(self):
        space = _run(_FakeLLM(THREE_BLOCKS))
        generated = space["n_candidates_generated"]
        self.assertEqual(generated, 3,
                         "all three blocks must assemble as CANDIDATE "
                         "state (fixture content is fully testable)")
        cem = space["cemetery_consumption"] or {}
        self.assertEqual(cem.get("n_candidates_consulted"), generated,
                         "the cemetery consults EVERY CANDIDATE-state "
                         "block, not only block 1")
        dd = space["distinctness"] or {}
        self.assertGreaterEqual(dd.get("n_distinct"), 1)
        self.assertGreaterEqual(space["n_candidates_retained"], 1)
        self.assertEqual(space["state"], "BUILT")
        # per-block attribution carries the tail's own verdicts
        for entry in space["instantiation_attempts"][0][
                "hypothesis_attribution"]:
            self.assertIsInstance(entry["cemetery_blocked"], bool)
            self.assertIn("distinctness_verdict", entry)
            self.assertIn("retained", entry)

    def test_llm_failure_writes_typed_attempt_without_crash(self):
        """The R548 round-A regression pin: field_blocks was read
        before initialization on this path — UnboundLocalError
        CRASHED the honest OPERATOR_INSTANTIATION_FAILED record."""
        fake = _FakeLLM(None, ok=False, status="UPSTREAM_503")
        space = _run(fake)  # must not raise
        att = space["instantiation_attempts"][0]
        self.assertTrue(att["attempted"])
        self.assertEqual(att["typed_outcome"],
                         "OPERATOR_INSTANTIATION_FAILED")
        self.assertEqual(att["hypothesis_blocks_parsed"], 0)
        self.assertEqual(att["hypothesis_attribution"], [])
        self.assertIsNone(att["candidate_id"])

    def test_legacy_single_block_response_still_builds(self):
        space = _run(_FakeLLM(_BLOCK_1))
        att = space["instantiation_attempts"][0]
        self.assertEqual(att["hypothesis_blocks_parsed"], 1)
        self.assertEqual(len(att["hypothesis_attribution"]), 1)
        self.assertEqual(
            space["operator_results"][0]["n_hypotheses_parsed"], 1)
        self.assertEqual(space["state"], "BUILT")
        self.assertEqual(len(space["operator_candidates_full"][0]
                             ["candidates"]), 1)


# ---------------------------------------------------------------------------
# D. the Art. LXXXIV minimum-diversity gate
# ---------------------------------------------------------------------------
class TestMinimumDiversityGate(unittest.TestCase):

    @staticmethod
    def _env_with_ms(ms_env: dict) -> Candidate:
        env = Candidate(problem=PROBLEM,
                        problem_id="r548_multi_hyp_test")
        env.mechanism_space = ms_env
        return env

    def test_minimum_is_two_and_never_lower(self):
        """Art. XXVII: MINIMUM_DISTINCT_MECHANISMS is 2 — this pin
        fails if anyone lowers it to make runs pass."""
        self.assertEqual(stage_entry.MINIMUM_DISTINCT_MECHANISMS, 2)

    def test_starvation_at_one_distinct(self):
        env = self._env_with_ms({"state": "BUILT", "distinctness": {
            "n_distinct": 1, "instrument_version": "r402-v2"}})
        facts = stage_entry.mechanism_diversity_facts(env)
        self.assertTrue(facts["present"])
        self.assertEqual(facts["n_distinct"], 1)
        self.assertEqual(facts["minimum_required"], 2)
        starved = stage_entry.mechanism_starved(env)
        self.assertIsNotNone(starved)
        self.assertEqual(starved["n_distinct"], 1)

    def test_not_starved_at_two_distinct(self):
        env = self._env_with_ms({"state": "BUILT", "distinctness": {
            "n_distinct": 2, "instrument_version": "r402-v2"}})
        self.assertIsNotNone(stage_entry.mechanism_diversity_facts(env))
        self.assertIsNone(stage_entry.mechanism_starved(env))

    def test_gate_silent_on_unknown_distinctness(self):
        # absent adjudication (legacy/empty envelope)
        for ms_env in ({"state": "BUILT"},
                       {"state": "BUILT",
                        "distinctness": {"n_distinct": None}},
                       # non-countable value (Art. XXV: never fires
                       # on unknown)
                       {"state": "BUILT",
                        "distinctness": {"n_distinct": "INDETERMINATE"}}):
            env = self._env_with_ms(ms_env)
            facts = stage_entry.mechanism_diversity_facts(env)
            self.assertFalse(facts["present"], ms_env)
            self.assertIsNone(stage_entry.mechanism_starved(env), ms_env)


# ---------------------------------------------------------------------------
# E. the R548 finished-flag ruling
# ---------------------------------------------------------------------------
class TestFinishedFlagR548(unittest.TestCase):

    @staticmethod
    def _bare(**extra) -> dict:
        rec = {"session_id": "ts_r548", "status": "COMPLETE",
               "run_dir": None}
        rec.update(extra)
        return rec

    def test_bare_complete_without_answer_is_not_finished(self):
        """The R548 ruling (BS-042's third occurrence): a COMPLETE
        terminal with NO recorded completion answer anywhere answers
        finished=False — the pre-R548 key-prefix path served True on
        exactly this shape. (Note: r545's
        test_bare_terminal_without_final_status_stays_unresolved
        documents the legacy True in prose but never asserts it — the
        asserted contract is THIS test's False.)"""
        from toscanini import user_state as us
        rec = self._bare()
        self.assertEqual(us.user_state(rec), "COMPLETED_UNKNOWN")
        self.assertIsNone(us._contract_finished_flag(rec))
        view = us.user_state_view(rec)
        self.assertEqual(view["user_state"], "COMPLETED_UNKNOWN")
        self.assertIs(view["finished"], False)

    def test_positive_candidate_terminal_keeps_legacy_true(self):
        """A recorded positive final status is the record's own
        honest terminal — the key-prefix True is untouched by the
        R548 residual branch."""
        from toscanini import user_state as us
        rec = self._bare(final_status="AUTOMATED_INVENTION_CANDIDATE")
        self.assertEqual(us.user_state(rec), "COMPLETED_CANDIDATE")
        self.assertIs(us.user_state_view(rec)["finished"], True)

    def test_recorded_finished_answer_overrides_the_residual(self):
        """When a recorded completion answer exists, the contract
        chain answers — the R548 residual branch only ever runs when
        _contract_finished_flag is None."""
        from toscanini import user_state as us
        fin = {"PIPELINE_COMPLETED": True, "DISCOVERY_COMPLETED": True,
               "TECHNOLOGY_PACKAGE_COMPLETED": True,
               "FINISHED_DISCOVERY": True}
        rec = self._bare(completion_states=dict(fin))
        self.assertIs(us._contract_finished_flag(rec), True)
        self.assertIs(us.user_state_view(rec)["finished"], True)

    def test_recorded_unfinished_answer_forces_false(self):
        from toscanini import user_state as us
        unf = {"PIPELINE_COMPLETED": True, "DISCOVERY_COMPLETED": False,
               "TECHNOLOGY_PACKAGE_COMPLETED": False,
               "FINISHED_DISCOVERY": False}
        rec = self._bare(completion_states=dict(unf))
        self.assertIs(us._contract_finished_flag(rec), False)
        self.assertIs(us.user_state_view(rec)["finished"], False)

    def test_completed_unknown_branch_exists_exactly_once(self):
        """The R548 deduplication guard: the dead duplicate
        COMPLETED_UNKNOWN FINISHED-FLAG branch must never come back
        (one branch, one ruling). The pattern targets the compound
        finished-flag condition (`elif key == "COMPLETED_UNKNOWN"
        and ...`); the plain `elif key == "COMPLETED_UNKNOWN":` at
        the decision-line chain is a different, legitimate branch
        (the "outcome not established" wording)."""
        src = (REPO / "toscanini" / "user_state.py").read_text(
            encoding="utf-8")
        self.assertEqual(
            src.count('elif key == "COMPLETED_UNKNOWN" and'), 1,
            "exactly one COMPLETED_UNKNOWN finished-flag branch may "
            "exist in user_state_view")


# ---------------------------------------------------------------------------
# E2. R548 Round B (audit problem 2, Art. VII): the reality-loop gate
# must claim what is measured — the loop is NOT ready while the
# loop_chain module is absent, even though the interface modules are
# ---------------------------------------------------------------------------
class TestRealityLoopGateR548B(unittest.TestCase):

    def test_flag_is_false_while_chain_module_absent(self):
        from toscanini import server
        p = server._health_payload()
        # the typed module map rides the readiness view
        self.assertFalse(
            p["readiness"]["reality_loop_modules"]["loop_chain"])
        self.assertIs(p["reality_loop_ready"], False,
                      "the closed loop is not ready while loop_chain "
                      "is absent — the flag claims the loop, not the "
                      "interface")
        self.assertIs(p["reality_loop_interface_ready"], True,
                      "the interface modules (ingestion + "
                      "calibration) ARE present — recorded as a "
                      "separate typed fact, never hidden")
        self.assertIn("loop_chain", p["reality_loop_reason"])
        # one source: the readiness view carries the same answer
        self.assertIs(p["readiness"]["reality_loop_ready"], False)

    def test_gate_flips_when_chain_module_present(self):
        """Metamorphic: with all three measured modules present the
        gate must flip True — the flag is a measurement, not a
        hardcoded constant that could never be updated."""
        import tempfile
        from pathlib import Path
        from toscanini import server as srv
        tmp = Path(tempfile.mkdtemp(prefix="r548b_repo_"))
        eng = tmp / "discovery_fabric" / "engine"
        eng.mkdir(parents=True)
        for name in ("reality_ingestion.py", "reality_calibration.py",
                     "loop_chain.py"):
            (eng / name).write_text("x = 1\n", encoding="utf-8")
        with mock.patch.object(srv, "REPO_ROOT", tmp):
            p = srv._health_payload()
        self.assertTrue(
            p["readiness"]["reality_loop_modules"]["loop_chain"])
        self.assertIs(p["reality_loop_ready"], True)
        self.assertIs(p["reality_loop_interface_ready"], True)
        self.assertIn("all loop modules present",
                      p["reality_loop_reason"])


if __name__ == "__main__":
    unittest.main()
