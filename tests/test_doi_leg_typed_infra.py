#!/usr/bin/env python3
"""tests/test_doi_leg_typed_infra.py — the DOI leg's typed-infra
semantics (the R96 typed fix for the pre-existing CI flake: Crossref
rate-limiting the runner's shared IP (HTTP 429/403/5xx) was typed as
resolved=False -> KILL, false-killing CLEAN corpus rows on 2 of the
last 5 surface runs; Art. 15: infra failure is never scientific
rejection).

The typed split this battery pins:
  - HTTP 400/404  -> KILL UNVERIFIABLE_DOI  (the DOI as written does
    not resolve — the oracle keeps its teeth on every runner, any
    network state)
  - HTTP 429/403/5xx -> FLAG DOI_NETWORK_ABSENT (infra; the
    authoritative read stays the auditor's)
  - timeout/DNS (non-HTTP) -> FLAG DOI_NETWORK_ABSENT (unchanged)

Zero network in the tests (urlopen is monkeypatched — the leg's
dispatcher is exercised, never the real Crossref API).
"""
from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import plausibility_critic as pc  # noqa: E402


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.crossref.org/works/10.9999/x", code=code,
        msg="mocked", hdrs=None, fp=None)


class TestDoiLegTypedInfra(unittest.TestCase):
    def _run(self, exc: Exception) -> list:
        """The leg returns (kills, flags, records) — the tests assert
        on the RECORDS (the resolved classification surface)."""
        with mock.patch.object(pc.urllib.request, "urlopen",
                               side_effect=exc):
            return pc._check_doi_crossref(
                "the membrane study: 10.9999/mock.2024")[2]

    def test_rate_limit_429_is_infra_flag_not_kill(self):
        out = self._run(_http_error(429))
        self.assertEqual(len(out), 1)
        self.assertIsNone(out[0]["resolved"])

    def test_wall_403_and_5xx_are_infra_flags(self):
        for code in (403, 500, 502, 503, 504):
            out = self._run(_http_error(code))
            self.assertIsNone(out[0]["resolved"], f"code {code}")

    def test_definitive_404_keeps_the_kill(self):
        out = self._run(_http_error(404))
        self.assertEqual(len(out), 1)
        self.assertFalse(out[0]["resolved"])

    def test_malformed_400_keeps_the_kill(self):
        out = self._run(_http_error(400))
        self.assertEqual(len(out), 1)
        self.assertFalse(out[0]["resolved"])

    def test_timeout_class_stays_flag(self):
        out = self._run(TimeoutError("mocked timeout"))
        self.assertEqual(len(out), 1)
        self.assertIsNone(out[0]["resolved"])

    def test_verdict_mapping_end_to_end(self):
        """Through the public dispatcher: a 429 never yields a KILL
        verdict; a 404 does."""
        with mock.patch.object(pc.urllib.request, "urlopen",
                               side_effect=_http_error(429)):
            r = pc.check_answer_class_defects(
                "cited: doi.org/10.9999/mock.2024", {}, "")
            self.assertNotIn(
                "UNVERIFIABLE_DOI",
                [c["anchor"] for c in r.get("kills", [])])
        with mock.patch.object(pc.urllib.request, "urlopen",
                               side_effect=_http_error(404)):
            r = pc.check_answer_class_defects(
                "cited: doi.org/10.9999/mock.2024", {}, "")
            self.assertIn(
                "UNVERIFIABLE_DOI",
                [c["anchor"] for c in r.get("kills", [])])


if __name__ == "__main__":
    unittest.main()
