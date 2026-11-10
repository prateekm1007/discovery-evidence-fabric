"""Regression guard for the cross-domain generic-term precision fix.

The cemetery's PROVEN_INVARIANT CE-003 (CSF turnover makes long-term
membrane retention impossible) used to hard-block any candidate whose
text contained "membrane" — including the pemfc dehydration candidate,
which shares no territory with CSF retention. The fix moved "membrane"
into _CROSS_DOMAIN_GENERIC_TERMS so it can no longer establish
territory on its own.

This test pins both sides of the fix:
  1. A known-killed membrane mechanism in the SAME territory (CSF
     retention) is still blocked — the fix did not disable the
     invariant.
  2. A pemfc (fuel-cell dehydration) candidate that merely mentions a
     membrane is NOT hard-blocked by CE-003 — the false positive is
     gone.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import orchestrator.mechanism_cemetery as mc


def test_ce003_still_blocks_same_territory_membrane_retention():
    result = mc.check_candidate_against_cemetery(
        "Use a 30kDa MWCO membrane to retain large therapeutics in CSF "
        "over 90 days despite CSF turnover",
        candidate_terms={"membrane", "mwco", "retention", "csf", "turnover"},
        problem_terms={"csf", "retention", "turnover", "membrane"},
    )
    blocked_ids = [b["cemetery_entry"] for b in result.get("hard_blocks", [])]
    assert "CE-003" in blocked_ids, (
        "CE-003 (CSF turnover invariant) must still hard-block a "
        "membrane-based CSF retention candidate in its own territory")


def test_pemfc_candidate_not_blocked_by_ce003_on_membrane_alone():
    result = mc.check_candidate_against_cemetery(
        "A pemfc membrane electrode assembly with hydrophilic additives "
        "to retain water under low humidity",
        candidate_terms={"membrane", "pemfc", "electrode", "humidity",
                         "water", "retention"},
        problem_terms={"pemfc", "dehydration", "membrane", "humidity"},
    )
    blocked_ids = [b["cemetery_entry"] for b in result.get("hard_blocks", [])]
    assert "CE-003" not in blocked_ids, (
        "CE-003 must not hard-block a pemfc candidate merely because "
        "both mention 'membrane'")
