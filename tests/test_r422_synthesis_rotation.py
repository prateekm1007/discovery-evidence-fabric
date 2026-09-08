"""R422 — synthesis paper-rotation retry (the LLM chokepoint directive).

Measured live (2026-09-08, ts_12ad5b143371): the probe completes while
the real synthesis call fails on free-tier rungs; the frozen A2 path
tried exactly ONE paper (evidence[0]) and the whole run died at
SYNTHESIZE/FAILED_EXPLICIT with 16 evidence records unused. The fix
rotates through up to 3 papers with backoff. These tests verify the
rotation semantics with a mocked transport (no network, no keys).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.a2 import synthesize as synth  # noqa: E402


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

GOOD_RESPONSE = (
    "MECHANISM: pressure wave reflection\n"
    "INTERVENTION: add an impedance sensor downstream\n"
    "EXPECTED_EFFECT: earlier occlusion detection\n"
    "FALSIFICATION_TEST: bench occlusion trial\n"
    "MECHANISM_SOURCE_SPAN: Abstract pressure"
)


class TestRotation(unittest.TestCase):

    def test_first_paper_success_no_rotation_record(self):
        with mock.patch.object(synth, "llm_chat",
                               return_value=GOOD_RESPONSE) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0), _paper(1)])
        self.assertIsNotNone(cand)
        self.assertEqual(cand["source_evidence"]["source_id"], "ev_0")
        self.assertNotIn("synthesis_rotation", cand)
        self.assertEqual(chat.call_count, 1)

    def test_transport_failure_rotates_to_second_paper(self):
        responses = [None, GOOD_RESPONSE]
        with mock.patch.object(synth, "llm_chat",
                               side_effect=responses) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0), _paper(1),
                                              _paper(2)])
        self.assertIsNotNone(cand)
        self.assertEqual(cand["source_evidence"]["source_id"], "ev_1")
        self.assertEqual(chat.call_count, 2)
        rot = cand.get("synthesis_rotation")
        self.assertIsNotNone(rot)
        self.assertEqual(rot["attempt_index"], 1)
        self.assertEqual(rot["papers_tried"], ["ev_0", "ev_1"])
        self.assertEqual(rot["evidence_available"], 3)

    def test_format_failure_rotates_to_third_paper(self):
        # paper 0: transport OK but format-hostile (no INTERVENTION line)
        # paper 1: transport failure
        # paper 2: good
        responses = ["I cannot follow your format.",
                     None,
                     GOOD_RESPONSE]
        with mock.patch.object(synth, "llm_chat",
                               side_effect=responses) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0), _paper(1),
                                              _paper(2)])
        self.assertIsNotNone(cand)
        self.assertEqual(cand["source_evidence"]["source_id"], "ev_2")
        self.assertEqual(chat.call_count, 3)
        rot = cand.get("synthesis_rotation")
        self.assertEqual(rot["attempt_index"], 2)
        self.assertEqual(rot["papers_tried"], ["ev_0", "ev_1", "ev_2"])

    def test_all_failures_return_none_honestly(self):
        with mock.patch.object(synth, "llm_chat", return_value=None):
            cand = synth.synthesize(PROBLEM, [_paper(0), _paper(1),
                                              _paper(2)])
        self.assertIsNone(cand)

    def test_rotation_is_bounded_at_three_papers(self):
        evidence = [_paper(i) for i in range(6)]
        with mock.patch.object(synth, "llm_chat", return_value=None) as chat:
            synth.synthesize(PROBLEM, evidence)
        self.assertEqual(chat.call_count, 3)

    def test_single_evidence_paper_still_retries_none(self):
        # degenerate case: one paper, one real attempt (no rotation
        # possible) — the honest pre-R422 semantics preserved
        with mock.patch.object(synth, "llm_chat", return_value=None) as chat:
            cand = synth.synthesize(PROBLEM, [_paper(0)])
        self.assertIsNone(cand)
        self.assertEqual(chat.call_count, 1)

    def test_backoff_is_applied_between_attempts(self):
        with mock.patch.object(synth, "llm_chat", return_value=None), \
                mock.patch.object(synth.time, "sleep") as tsleep:
            synth.synthesize(PROBLEM, [_paper(0), _paper(1), _paper(2)])
        sleeps = [c.args[0] for c in tsleep.call_args_list]
        self.assertEqual(sleeps, [8, 20])

    def test_candidate_provenance_fields_unchanged(self):
        with mock.patch.object(synth, "llm_chat",
                               return_value=GOOD_RESPONSE):
            cand = synth.synthesize(PROBLEM, [_paper(0)])
        for key in ("candidate_id", "problem_id", "device", "failure",
                    "constraint", "mechanism", "intervention",
                    "expected_effect", "falsification_test",
                    "mechanism_source_span", "source_evidence", "model",
                    "provider", "transport_status", "prompt_hash",
                    "input_hash", "output_hash", "synthesis_timestamp"):
            self.assertIn(key, cand)


if __name__ == "__main__":
    unittest.main()
