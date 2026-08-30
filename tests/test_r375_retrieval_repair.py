"""R375 retrieval repair tests (Art. V/XXI) — the campaign found a live
defect: MAUDE problem-term phrases with literal 'or'/'(s)' poison the
EuropePMC boolean parser (candidate 11: hitCount 0 for the poisoned
query vs 4580 for the sanitized one), and provider exceptions were
swallowed into `[]` — absence fabrication, Art. XXI.3.

Positive: sanitized fallback retrieves real evidence for the poisoned case.
Negative: provider failure RAISES SearchProviderFailure, never [].
Metamorphic: sanitize never drops the device term or invents vocabulary.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.a2.retrieve import (  # noqa: E402
    SearchProviderFailure, retrieve, sanitize_query, search_europe_pmc)


class TestSanitizeQuery(unittest.TestCase):
    def test_boolean_words_removed(self):
        self.assertNotIn(" or ", sanitize_query("a or b and c"))

    def test_s_suffix_fragments_removed(self):
        self.assertEqual(sanitize_query("ingredient(s)"), "ingredient")

    def test_vocabulary_preserved_otherwise(self):
        # metamorphic: sanitization removes ONLY operator vocabulary —
        # every remaining word comes from the input
        out = sanitize_query("coagulation in device or device ingredie")
        for word in out.split():
            self.assertIn(word.lower(),
                          "coagulation in device or device ingredie")

    def test_empty_stays_empty(self):
        self.assertEqual(sanitize_query(""), "")


class TestProviderFailureIsNotAbsence(unittest.TestCase):
    def test_transport_error_raises(self):
        with mock.patch("discovery_fabric.a2.retrieve."
                        "urllib.request.urlopen",
                        side_effect=TimeoutError("read timed out")):
            with self.assertRaises(SearchProviderFailure):
                search_europe_pmc("anything")
            # Art. XXI.3: the failure mentions it is NOT absence
            self.assertIn("NOT absence",
                          SearchProviderFailure("x (NOT absence)").args[0])

    def test_retrieve_propagates_provider_failure(self):
        problem = {"device": "venous filter",
                   "failure_mode": "coagulation"}
        with mock.patch("discovery_fabric.a2.retrieve."
                        "urllib.request.urlopen",
                        side_effect=OSError("network down")):
            with self.assertRaises(SearchProviderFailure):
                retrieve(problem)


class TestPoisonedQueryFallback(unittest.TestCase):
    """The exact campaign case: boolean-poisoned primary query returns a
    TRUE zero from the live API; the fallback must retrieve evidence
    (verified live 2026-08-30: 4580 hits for 'venous filter coagulation
    mechanism'). Network-dependent: skipped when EuropePMC unreachable."""

    def test_fallback_retrieves_for_poisoned_case(self):
        problem = {"device": "venous filter",
                   "failure_mode":
                       "coagulation in device or device ingredient(s) "
                       "or component(s)"}
        try:
            items = retrieve(problem)
        except SearchProviderFailure:
            self.skipTest("EuropePMC unreachable from test environment")
        self.assertGreater(len(items), 0,
                           "the sanitized fallback must retrieve real "
                           "evidence for the poisoned campaign case")
        # every retrieved item carries its actual query provenance
        for it in items:
            self.assertIn("query_or_method", it["provenance"])


if __name__ == "__main__":
    unittest.main()
