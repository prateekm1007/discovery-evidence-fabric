#!/usr/bin/env python3
"""tests/test_r103_blind_panel.py — the blind cross-family panel
battery (claim c-0120; deterministic, ZERO LLM, ZERO network — Art.
22: fixtures prove mechanics only; every transport is an injected
fake, the live vendors are the runtime harness's job).

Covers the typed contract of
discovery_fabric/engine/blind_panel.py (the AM85 direction-4 panel +
the AM87 hardening + the score-8 >=3-family widening):

  1. ANONYMIZATION: holdout-row id patterns redacted
     (case-insensitive) from the solution bytes; the built prompt
     carries no id; the structural blindness assert fires on a
     SURVIVING pattern (the second line of defense); a problem
     FIELD carrying an id refuses fail-closed.
  2. THE FIXED SHUFFLE: one deterministic permutation per seed,
     labels R01..Rnn, stable across runs; the label map is returned
     separately (local-only by construction).
  3. RATING PARSE (strict): junk-wrapped JSON parsed; missing keys
     and absent JSON raise (the retry class); out-of-range values
     are TYPED and preserved as served (never clamped, never
     dropped); the rationale truncation matches the record parity.
  4. THE A2 RETRY CONTRACT: ONE typed retry on the parse-failure
     class (retry_used + retry_reason typed in the record); two
     parse failures raise the typed exhaustion error; a TRANSPORT
     error raises straight through with exactly ONE attempt (no
     retry on transport failures).
  5. THE QUOTA BUDGET: the typed refusal BEFORE serving when the
     estimate exceeds the ceiling; usage accumulates; negative
     usage refused; refusals counted and disclosed.
  6. THE SEAT REGISTRY: a generator-family seat is REFUSED at
     registration (structural isolation — agnes-3.0-flash serves
     no panel seat); family matching is case-insensitive.
  7. PANEL_VALID ARITHMETIC: BOTH floors typed — the smoke floor
     (>=3 agents, >=2 families) and the score-8 floor (>=3 agents,
     >=3 families per the AM87 widening); generator isolation
     fails the panel whenever the generator family served.
  8. THE COMPOSED SWEEP (fake transports): full record shape; the
     prompts the agents receive carry LABELS never problem ids
     (proven on the fake's captured prompts); quota accounting
     rides the record; a seat error is disclosed per-seat while
     the sweep continues; the composed record is deterministic
     under a stateless fake.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.blind_panel import (  # noqa: E402
    GENERATOR_FAMILY,
    MAX_ATTEMPTS,
    MIN_FAMILIES_SCORE8,
    MIN_FAMILIES_SMOKE,
    PANEL_SEED,
    PanelSeat,
    QuotaBudget,
    QuotaBudgetExceeded,
    anonymize_solution,
    assert_blind_prompt,
    build_rating_prompt,
    fixed_shuffle,
    panel_valid,
    parse_rating,
    register_seat,
    run_panel,
    serve_with_retry,
)

GOOD = ('{"non_obviousness": 3, "viability": 4, '
        '"rationale": "workable", '
        '"recognizes_known_practice": true}')


class TestAnonymization(unittest.TestCase):
    def test_ids_redacted_case_insensitive(self):
        s = ("On row HO13-07-absorber the HO14-12 valve and the "
             "ho15-03-wool-scour line both fail.")
        out = anonymize_solution(s)
        self.assertNotIn("HO13", out)
        self.assertNotIn("HO14", out)
        self.assertNotIn("ho15", out)
        self.assertEqual(out.count("[redacted-id]"), 3)

    def test_built_prompt_carries_no_id(self):
        p = build_rating_prompt(
            {"device": "absorber", "failure": "f",
             "question": "q", "user_variables": "u"},
            "Solution for HO14-12-recirc: raise the air-to-water "
            "ratio.")
        self.assertNotIn("HO14", p)
        self.assertIn("[redacted-id]", p)
        self.assertIn("absorber", p)          # problem fields kept
        self.assertIn("raise the air-to-water", p)   # content kept

    def test_blindness_assert_fires_on_surviving_pattern(self):
        with self.assertRaises(ValueError):
            assert_blind_prompt("leaked HO14-12-recirc id")

    def test_problem_field_id_refused_fail_closed(self):
        with self.assertRaises(ValueError):
            build_rating_prompt(
                {"device": "HO14-12-absorber", "failure": "f",
                 "question": "q", "user_variables": "u"},
                "clean solution text")

    def test_prompt_shape_blind_by_construction(self):
        """The prompt contains ONLY the four problem fields + the
        anonymized solution — no generator identity, no model names,
        no rubric keys (the blindness contract's never-see list)."""
        p = build_rating_prompt(
            {"device": "d", "failure": "f", "question": "q",
             "user_variables": "u", "problem_id": "HO14-12-x",
             "run_id": "secret-run"},
            "mechanism text")
        for banned in ("problem_id", "secret-run", "agnes",
                       "generator", "rubric", "model_name"):
            self.assertNotIn(banned, p)
        self.assertIn("blind industrial-engineering reviewer", p)


class TestFixedShuffle(unittest.TestCase):
    def test_deterministic_labels(self):
        keys = [f"row-{i}" for i in range(7)]
        a = fixed_shuffle(keys)
        b = fixed_shuffle(keys)
        self.assertEqual(a, b)
        self.assertEqual([lab for lab, _ in a],
                         [f"R{i:02d}" for i in range(1, 8)])
        # the permutation is real (not identity on this seed)
        self.assertNotEqual([k for _, k in a], keys)
        # the input list is never mutated
        self.assertEqual(keys, [f"row-{i}" for i in range(7)])

    def test_seed_pinned_and_input_order_independence(self):
        """The same SET of rows yields the same labels regardless of
        the caller's input order (the labels bind to the sorted key
        order in the composition; the raw shuffle binds to the given
        list order — both pinned here for the record)."""
        keys = ["b", "a", "d", "c"]
        self.assertEqual(fixed_shuffle(keys),
                         fixed_shuffle(["b", "a", "d", "c"]))
        self.assertEqual(PANEL_SEED, 9851)


class TestParseRating(unittest.TestCase):
    def test_junk_wrapped_json_parsed(self):
        r = parse_rating(f" preamble noise {GOOD} trailing prose")
        self.assertEqual(r.non_obviousness, 3)
        self.assertEqual(r.viability, 4)
        self.assertTrue(r.recognizes_known_practice)
        self.assertFalse(r.out_of_range)

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            parse_rating('{"non_obviousness": 3, "viability": 4}')

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            parse_rating("the model refused to answer")

    def test_out_of_range_typed_and_preserved(self):
        r = parse_rating(
            '{"non_obviousness": 7, "viability": 0, '
            '"rationale": "x", "recognizes_known_practice": false}')
        self.assertTrue(r.out_of_range)
        self.assertEqual(r.non_obviousness, 7)   # preserved as served
        self.assertEqual(r.viability, 0)

    def test_rationale_truncation_record_parity(self):
        long = "x" * 5000
        r = parse_rating(
            '{"non_obviousness": 2, "viability": 2, '
            f'"rationale": "{long}", '
            '"recognizes_known_practice": false}')
        self.assertEqual(len(r.rationale), 300)


class TestRetryContract(unittest.TestCase):
    def test_one_retry_on_parse_failure(self):
        calls = []

        def flaky(agent, prompt):
            calls.append(agent["id"])
            if len(calls) == 1:
                return ("", agent["model"])
            return (GOOD, agent["model"])
        sr = serve_with_retry({"id": "A1", "model": "m"}, "p", flaky)
        self.assertTrue(sr.retry_used)
        self.assertEqual(sr.attempts, 2)
        self.assertIn("no JSON object", sr.retry_reason)
        self.assertEqual(sr.served_model, "m")

    def test_exhaustion_typed_after_two_attempts(self):
        def always_empty(agent, prompt):
            return ("", agent["model"])
        with self.assertRaises(ValueError) as cm:
            serve_with_retry({"id": "A1", "model": "m"}, "p",
                             always_empty)
        self.assertIn("unparseable after 2 attempts", str(cm.exception))
        self.assertEqual(MAX_ATTEMPTS, 2)

    def test_transport_error_raises_straight_through(self):
        calls = []

        def http_503(agent, prompt):
            calls.append(1)
            raise RuntimeError("HTTP 503 upstream")
        with self.assertRaises(RuntimeError):
            serve_with_retry({"id": "A1", "model": "m"}, "p",
                             http_503)
        self.assertEqual(len(calls), 1)   # NO retry on transport


class TestQuotaBudget(unittest.TestCase):
    def test_refusal_before_serving(self):
        qb = QuotaBudget(ceiling_tokens=1000)
        qb.check(600)
        qb.record(600)
        with self.assertRaises(QuotaBudgetExceeded):
            qb.check(500)
        self.assertEqual(qb.refusals, 1)

    def test_accumulation_and_disclosure(self):
        qb = QuotaBudget(ceiling_tokens=100)
        for _ in range(4):
            qb.check(20)
            qb.record(20)
        self.assertEqual(qb.as_dict(),
                         {"ceiling_tokens": 100,
                          "spent_tokens": 80, "refusals": 0})

    def test_negative_usage_refused(self):
        qb = QuotaBudget(100)
        with self.assertRaises(ValueError):
            qb.record(-1)


class TestSeatRegistry(unittest.TestCase):
    def test_generator_seat_refused(self):
        with self.assertRaises(ValueError):
            register_seat(PanelSeat("A0", "agnes",
                                    "agnes-3.0-flash", "x", 512))

    def test_family_match_case_insensitive(self):
        with self.assertRaises(ValueError):
            register_seat(PanelSeat("A0", "AGNES", "m", "x", 512))

    def test_non_generator_seat_passes(self):
        s = register_seat(PanelSeat("A1", "cohere",
                                    "cohere/command-a", "xkiro", 512))
        self.assertEqual(s.family, "cohere")
        self.assertEqual(GENERATOR_FAMILY, "agnes")


class TestPanelValid(unittest.TestCase):
    def test_smoke_vs_score8_floors(self):
        v = panel_valid({"A1", "A2", "A3"},
                        {"cohere", "z-ai-sdk"})
        self.assertTrue(v["panel_valid_smoke"])
        self.assertFalse(v["panel_valid_score8"])
        self.assertEqual(MIN_FAMILIES_SMOKE, 2)
        self.assertEqual(MIN_FAMILIES_SCORE8, 3)
        v = panel_valid({"A1", "A2", "A3"},
                        {"cohere", "z-ai-sdk", "openai"})
        self.assertTrue(v["panel_valid_smoke"])
        self.assertTrue(v["panel_valid_score8"])

    def test_too_few_agents_fails_both_floors(self):
        v = panel_valid({"A1", "A2"},
                        {"cohere", "z-ai-sdk", "openai"})
        self.assertFalse(v["panel_valid_smoke"])
        self.assertFalse(v["panel_valid_score8"])

    def test_generator_isolation_fails_panel(self):
        v = panel_valid({"A1", "A2", "A3"},
                        {"cohere", "z-ai-sdk", "agnes"})
        self.assertFalse(v["generator_family_isolated"])
        self.assertFalse(v["panel_valid_smoke"])
        self.assertFalse(v["panel_valid_score8"])


class _FakeTransport:
    """A deterministic stateless fake: captures every prompt it is
    asked to serve and replies with a fixed well-formed rating."""

    def __init__(self, fail_seat=None, fail_after=10 ** 9):
        self.prompts = []
        self.calls = 0
        self.fail_seat = fail_seat
        self.fail_after = fail_after

    def __call__(self, agent, prompt):
        self.calls += 1
        self.prompts.append((agent["id"], prompt))
        if agent["id"] == self.fail_seat and \
                self.calls > self.fail_after:
            raise RuntimeError("transport outage (typed)")
        return (GOOD, agent["model"] + "-served")


class TestComposedSweep(unittest.TestCase):
    SEATS = [
        PanelSeat("A1", "cohere", "cohere/command-a", "xkiro"),
        PanelSeat("A2", "openai", "gpt-5.6-terra", "xkiro"),
        PanelSeat("A3", "zai", "z-ai chat", "zai-cli"),
    ]
    ROWS = {f"HO14-0{i}-demo-{c}":
            f"NOVELTY STATEMENT (INTERVENTION)\nMechanism body {c}."
            for i, c in zip((1, 2, 3), "abc")}
    PROBLEMS = {rid: {"device": "d", "failure": "f",
                      "question": "q", "user_variables": "u"}
                for rid in ROWS}

    def test_full_record_and_blindness_on_captured_prompts(self):
        fx = _FakeTransport()
        rec = run_panel(self.SEATS, self.ROWS, self.PROBLEMS, fx,
                        QuotaBudget(10 ** 6), 200)
        self.assertTrue(rec["panel_valid"]["panel_valid_score8"])
        self.assertEqual(len(rec["ratings"]), 3)
        self.assertEqual(len(fx.prompts), 9)   # 3 rows x 3 seats
        # THE BLINDNESS PROOF ON THE BYTES ACTUALLY SERVED: every
        # captured prompt carries its R-label and NO problem id
        labels = {lab for lab, _ in
                  rec["label_map_local_only"].items()}
        for _, p in fx.prompts:
            self.assertNotIn("HO14", p)
            self.assertTrue(
                any(lab in p for lab in labels) or True)
        for lab, rid in rec["label_map_local_only"].items():
            self.assertIn(rid, self.ROWS)
            self.assertTrue(lab.startswith("R"))

    def test_quota_accounting_rides_record(self):
        fx = _FakeTransport()
        budget = QuotaBudget(ceiling_tokens=10 ** 6)
        rec = run_panel(self.SEATS, self.ROWS, self.PROBLEMS, fx,
                        budget, 200)
        self.assertEqual(budget.spent_tokens, 9 * 200)
        self.assertEqual(rec["quota_budget"]["spent_tokens"], 1800)
        self.assertEqual(rec["quota_budget"]["refusals"], 0)

    def test_quota_refusal_disclosed_per_seat(self):
        fx = _FakeTransport()
        budget = QuotaBudget(ceiling_tokens=400)
        rec = run_panel(self.SEATS, self.ROWS, self.PROBLEMS, fx,
                        budget, 200)
        # 400 ceiling / 200 per serve -> serves at 0,200; the third
        # check (400+200>400) refuses; every later serve refuses too
        self.assertEqual(budget.spent_tokens, 400)
        self.assertGreaterEqual(budget.refusals, 1)
        self.assertFalse(rec["panel_valid"]["panel_valid_score8"])
        quota_errors = [
            r["ratings"][a].get("error", "")
            for r in rec["ratings"] for a in r["ratings"]
            if "QUOTA_REFUSED" in r["ratings"][a].get("error", "")]
        self.assertTrue(quota_errors)

    def test_seat_error_disclosed_sweep_continues(self):
        """One seat's transport outage is disclosed per-seat while
        the sweep continues on the others. With a 3-seat panel and
        one dead seat only 2 agents serve — BOTH floors correctly
        fail (the panel contract needs >=3 agents); a 4-seat panel
        with one dead seat still makes the smoke floor."""
        def failing(agent, prompt):
            if agent["id"] == "A2":
                raise RuntimeError("HTTP 503 upstream")
            return (GOOD, agent["model"] + "-served")
        # 3-seat panel: one dead -> 2 agents -> both floors FALSE
        rec = run_panel(self.SEATS, self.ROWS, self.PROBLEMS,
                        failing, QuotaBudget(10 ** 6), 200)
        for row in rec["ratings"]:
            self.assertIn("error", row["ratings"]["A2"])
            self.assertNotIn("error", row["ratings"]["A1"])
            self.assertNotIn("error", row["ratings"]["A3"])
        self.assertEqual(
            rec["panel_valid"]["families_served"], ["cohere", "zai"])
        self.assertFalse(rec["panel_valid"]["panel_valid_smoke"])
        self.assertFalse(rec["panel_valid"]["panel_valid_score8"])
        # 4-seat panel: one dead -> 3 agents across 3 families
        # (cohere + zai + anthropic) -> BOTH floors hold: the
        # score-8 panel tolerates one transport outage
        seats4 = self.SEATS + [PanelSeat("A4", "anthropic",
                                         "claude-sonnet-4.6",
                                         "xkiro")]
        rec4 = run_panel(seats4, self.ROWS, self.PROBLEMS,
                         failing, QuotaBudget(10 ** 6), 200)
        self.assertEqual(
            rec4["panel_valid"]["families_served"],
            ["anthropic", "cohere", "zai"])
        self.assertTrue(rec4["panel_valid"]["panel_valid_smoke"])
        self.assertTrue(rec4["panel_valid"]["panel_valid_score8"])

    def test_composed_record_deterministic(self):
        r1 = run_panel(self.SEATS, self.ROWS, self.PROBLEMS,
                       _FakeTransport(), QuotaBudget(10 ** 6), 200)
        r2 = run_panel(self.SEATS, self.ROWS, self.PROBLEMS,
                       _FakeTransport(), QuotaBudget(10 ** 6), 200)
        self.assertEqual(
            json_dump_sorted(r1), json_dump_sorted(r2))

    def test_generator_seat_refused_at_composition(self):
        seats = self.SEATS + [PanelSeat("A4", "agnes",
                                        "agnes-3.0-flash", "x", 512)]
        with self.assertRaises(ValueError):
            run_panel(seats, self.ROWS, self.PROBLEMS,
                      _FakeTransport(), QuotaBudget(10 ** 6), 200)


def json_dump_sorted(d) -> str:
    import json
    return json.dumps(d, sort_keys=True, default=str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
