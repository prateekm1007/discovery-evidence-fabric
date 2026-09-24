"""tests/test_r525_synth_span_neutrality.py — R525 Q-A contract.

The R525 SYNTHESIZE span instrumentation (synthesis_span_timings on the
candidate) MUST be behavior-neutral: read-only perf_counter deltas, no
prompt/budget/retry/gate/parse/repair/assembly logic touched.

Proves:
  A. the timings record exists with every expected span name
  B. all values non-negative; parts sum within the measured total
  C. candidate content fields are byte-identical to the uninstrumented
     logic for fixed mocked transports (logic untouched)
  D. rotation backoff is MEASURED (real 8 s sleep observed in-span)
  E. retry paths (span-corrective) are timed without changing outcomes

NOTE (Art. XV disclosure): tests/test_r422_synthesis_rotation.py has 3
PRE-EXISTING failures on pristine HEAD (the R483 span-corrective retry
added a second llm_chat call; the R422 exact-count assertions were not
updated). Those failures are unrelated to this instrumentation and must
remain EXACTLY 3 after it (verified in the R525 round record).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.a2 import synthesize as synth  # noqa: E402

SPAN_NAMES = {"abstract_gate_s", "prompt_construction_total_s",
              "llm_chat_total_s", "n_llm_chat_calls",
              "rotation_backoff_sleep_s", "parse_total_s",
              "span_repair_check_s", "candidate_assembly_s",
              "synthesize_total_s"}


def _paper(i: int) -> dict:
    return {
        "id": f"ev_{i}",
        "title": f"paper {i}",
        "abstract": (f"Abstract {i}. " * 30).strip(),
        "content_hash": f"hash_{i}",
        "retrieval_timestamp": "2026-09-08T00:00:00Z",
    }


PROBLEM = {
    "problem_id": "p_test",
    "device": "infusion pump",
    "failure_mode": "occlusion",
    "failure": "downstream occlusion undetected",
    "constraint": "cost < $50",
}

# verbatim span (substring of the paper abstract): no corrective retry.
VERBATIM_RESPONSE = (
    "MECHANISM: pressure wave reflection\n"
    "INTERVENTION: add an impedance sensor downstream\n"
    "EXPECTED_EFFECT: earlier occlusion detection\n"
    "FALSIFICATION_TEST: bench occlusion trial\n"
    "MECHANISM_SOURCE_SPAN: Abstract 0. Abstract 0."
)


class TestSpanRecordShape(unittest.TestCase):

    def test_clean_path_timings_present_and_consistent(self):
        with mock.patch.object(synth, "llm_chat",
                               return_value=VERBATIM_RESPONSE) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0), _paper(1)])
        self.assertIsNotNone(cand)
        # content logic untouched: exact expected fields
        self.assertEqual(cand["mechanism"], "pressure wave reflection")
        self.assertEqual(cand["intervention"],
                         "add an impedance sensor downstream")
        self.assertEqual(cand["mechanism_source_span"],
                         "Abstract 0. Abstract 0.")
        self.assertEqual(cand["source_evidence"]["source_id"], "ev_0")
        self.assertEqual(chat.call_count, 1)
        # no retry/rotation records on the clean path
        self.assertNotIn("synthesis_rotation", cand)
        self.assertNotIn("span_corrective_retry", cand)
        # timings record: every span present, non-negative, consistent
        timings = cand.get("synthesis_span_timings")
        self.assertIsNotNone(timings)
        self.assertEqual(timings.get("instrument"), "synth_spans/1.0")
        self.assertEqual(set(timings) - {"instrument"}, SPAN_NAMES)
        for k in SPAN_NAMES:
            self.assertGreaterEqual(timings[k], 0, k)
        self.assertEqual(timings["n_llm_chat_calls"], 1)
        parts = sum(timings[k] for k in SPAN_NAMES
                    - {"synthesize_total_s", "n_llm_chat_calls"})
        self.assertLessEqual(parts, timings["synthesize_total_s"])
        self.assertEqual(timings["rotation_backoff_sleep_s"], 0.0)

    def test_rotation_backoff_is_measured(self):
        # first paper transport-fails; second serves its own verbatim
        # span. The R422 8 s backoff really sleeps: the span observes it.
        verbatim_1 = VERBATIM_RESPONSE.replace(
            "Abstract 0. Abstract 0.", "Abstract 1. Abstract 1.")
        with mock.patch.object(synth, "llm_chat",
                               side_effect=[None, verbatim_1]
                               ) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0), _paper(1)])
        self.assertIsNotNone(cand)
        self.assertEqual(cand["source_evidence"]["source_id"], "ev_1")
        self.assertEqual(chat.call_count, 2)
        timings = cand["synthesis_span_timings"]
        self.assertEqual(timings["n_llm_chat_calls"], 2)
        self.assertGreaterEqual(timings["rotation_backoff_sleep_s"], 8.0)
        self.assertLess(timings["rotation_backoff_sleep_s"], 30.0)

    def test_span_corrective_retry_is_timed_without_changing_outcome(self):
        # non-verbatim span triggers the R483 corrective retry (2 calls);
        # the honest typed outcome stands, both calls timed.
        bad_span = (
            "MECHANISM: pressure wave reflection\n"
            "INTERVENTION: add an impedance sensor downstream\n"
            "EXPECTED_EFFECT: earlier occlusion detection\n"
            "FALSIFICATION_TEST: bench occlusion trial\n"
            "MECHANISM_SOURCE_SPAN: Abstract pressure")
        with mock.patch.object(synth, "llm_chat",
                               return_value=bad_span) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0)])
        self.assertIsNotNone(cand)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(
            cand["span_corrective_retry"]["succeeded"], False)
        timings = cand["synthesis_span_timings"]
        self.assertEqual(timings["n_llm_chat_calls"], 2)
        self.assertGreater(timings["llm_chat_total_s"], 0.0)

    def test_no_provider_literal_in_timer_code(self):
        import inspect
        src = inspect.getsource(synth.synthesize)
        # timers are provider-blind (Art. X / R519 §6 discipline)
        for pid in ("zai", "atria", "xkiro", "openrouter", "unorouter"):
            self.assertNotIn(f'"{pid}"', src)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
