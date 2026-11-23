"""tests/test_quote_anchored_enrichment.py — R142 DIR-3: the
quote-anchored re-generation (the typed v3 next-capability).

The measured cause the twin typed in c-0226: the enrichment
re-verified the SAME paraphrase text against fresh retrieval — the
8-word verbatim binding instrument cannot fire on paraphrase-only
hypotheses. The fix: extract VERBATIM topical anchor spans from the
retrieved records (the same normalization as the binding gram
search, sliced from the RAW text), regenerate the mechanism FROM the
quote (one bounded LLM call, the revise-pass precedent), and admit
ONLY through the unchanged identity-true bar. Fail-closed: a
regeneration that does not reproduce the quote verbatim is typed
STILL_UNGROUNDED — never admitted."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.run import (  # noqa: E402
    _verbatim_quote_anchors, _quote_present)

QUOTE = ("scale on condenser tubes raises the condensing "
         "temperature")
ITEMS = [
    {"id": "doi:10.1/anchor", "title": "condenser fouling study",
     "abstract": ("Calcium carbonate " + QUOTE + " and drops plant "
                  "capacity measurably under peak load.")},
    {"id": "doi:10.1/other", "title": "unrelated metallurgy",
     "abstract": "Grain boundary segregation in welded steel joints."},
]


def test_01_anchor_is_verbatim_and_topical() -> None:
    """The extracted span is a genuine verbatim substring of the raw
    record text and shares content words with the hypothesis."""
    q = _verbatim_quote_anchors(ITEMS, "condenser tube scale fouling "
                                "raises condensing temperature")
    assert q, "no anchor extracted"
    assert q[0]["record_id"] == "doi:10.1/anchor"
    raw = (ITEMS[0]["title"] + ". " + ITEMS[0]["abstract"])
    assert q[0]["quote"] in raw, (
        "the anchor must be a verbatim substring of the raw record text")
    assert q[0]["overlap"] >= 2


def test_02_unrelated_record_yields_no_anchor() -> None:
    """A record with no topical overlap yields NO anchor (never a
    random span)."""
    q = _verbatim_quote_anchors(
        [ITEMS[1]], "condenser tube scale fouling rises temperature")
    assert q == [], "an unrelated record must not anchor"


def test_03_quote_present_compliance() -> None:
    """The compliance check: the regenerated text must contain the
    quote's normalized 8-gram VERBATIM; a paraphrase fails."""
    assert _quote_present("the mechanism: " + QUOTE + " — mitigated "
                          "by treatment", QUOTE)
    assert not _quote_present(
        "condenser tube scaling raises the condenser temperature",
        QUOTE), "a paraphrase must NOT pass the verbatim check"


def test_04_short_or_stopped_hypothesis_yields_nothing() -> None:
    """A hypothesis with <3 content tokens or only stop-words yields
    no anchor (the topical-overlap precondition)."""
    assert _verbatim_quote_anchors(ITEMS, "the of and to") == []
    assert _verbatim_quote_anchors(ITEMS, "") == []


def test_05_enrichment_wiring_present() -> None:
    """Source pin: the enrichment loop carries the regeneration step
    between retrieval and verify (the R142 fix), with the fail-closed
    typing."""
    src = (REPO / "discovery_fabric" / "engine" / "run.py").read_text()
    assert "_verbatim_quote_anchors(new_items, mech)" in src, (
        "the enrichment must extract quote anchors before verify")
    assert "purpose=\"enrichment_regenerate\"" in src, (
        "the regeneration rides the engine transport (one bounded "
        "call, the revise-pass precedent)")
    assert "quote_present" in src and "fail closed" in src, (
        "a non-verbatim regeneration is typed fail-closed")
    assert "mechanism_pre_enrichment" in src, (
        "the original paraphrase stays for provenance")


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))  # noqa
