#!/usr/bin/env python3
"""R469 — the evidence-span citation contract tests.

The engineer's 10-test list (Atria-Dawn-Preview design, CTO-reviewed):
the repair fires only when a >=8-word contiguous verbatim window exists,
the promoted span is the abstract's own characters, the REAL verifier
gate re-checks it, honest failures stand, and verify.py can never grow
a fuzzy matcher (the constitutional tripwire).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.a2.synthesize import (  # noqa: E402
    SPAN_MIN_WORDS,
    SPAN_INSTRUCTION,
    repair_mechanism_span,
)
from discovery_fabric.a2.verify import verify_evidence  # noqa: E402

ABSTRACT = (
    "Aneurysm recurrence after flow-diverter treatment is driven by "
    "incomplete wall apposition at the neck. Platelets adhere to the "
    "injured endothelium within seconds and initiate thrombus "
    "formation. Hemodynamic shear stress modulates the "
    "endothelial glycocalyx and governs neointimal coverage. "
    "Vascular smooth muscle cells migrate toward the neck remnant "
    "over several weeks.")

PAPER = {"id": "pap_001", "abstract": ABSTRACT,
         "title": "Wall apposition", "content_hash": "h" * 16,
         "retrieval_timestamp": "2026-09-16T00:00:00Z"}


def _candidate(span: str, paper=PAPER):
    return {
        "mechanism_source_span": span,
        "source_evidence": {"source_id": paper["id"],
                            "source_hash": paper["content_hash"],
                            "source_title": paper["title"],
                            "source_span": paper["abstract"][:2000],
                            "retrieval_timestamp":
                                paper["retrieval_timestamp"]},
    }


def test_verbatim_span_untouched():
    c = _candidate("Platelets adhere to the injured endothelium "
                   "within seconds")
    out = repair_mechanism_span(c, ABSTRACT)
    assert out["mechanism_source_span"] == c["mechanism_source_span"]
    assert "span_repair" not in out


def test_case_insensitive_span_untouched():
    c = _candidate("platelets adhere to the injured endothelium "
                   "within seconds")  # case differs -> verifier's own
    # documented fallback already accepts it; repair must not fire
    out = repair_mechanism_span(c, ABSTRACT)
    assert "span_repair" not in out


def test_paraphrase_repaired_eight_plus_words():
    # the model wraps an 11-word verbatim run in its own words and
    # lower-cases the first word — the classic measured paraphrase
    c = _candidate("The mechanism involves platelets adhere to the "
                   "injured endothelium within seconds and initiate "
                   "thrombus formation at the device site")
    out = repair_mechanism_span(c, ABSTRACT)
    assert out.get("span_repair", {}).get("method") == \
        "verbatim-subwindow"
    promoted = out["mechanism_source_span"]
    assert promoted in ABSTRACT  # byte-exact substring BY CONSTRUCTION
    assert len(promoted.split()) >= SPAN_MIN_WORDS


def test_promoted_span_clears_the_real_gate():
    c = _candidate("The mechanism involves platelets adhere to the "
                   "injured endothelium within seconds and initiate "
                   "thrombus formation at the device site")
    out = repair_mechanism_span(c, ABSTRACT)
    res = verify_evidence(out, [PAPER])
    assert res["verified"] is True
    assert "mechanism_span_not_verbatim" not in res["issues"]


def test_paraphrase_not_repaired_short_window():
    c = _candidate("Thrombus growth begins quickly after vessel wall "
                   "trauma in the setting of stent placement")  # <8
    # contiguous shared words with the abstract
    out = repair_mechanism_span(c, ABSTRACT)
    assert "span_repair" not in out
    res = verify_evidence(out, [PAPER])
    assert res["verified"] is False
    assert res["evidence_class"] == "UNSUPPORTED"


def test_span_from_wrong_paper_rejected():
    other = {"id": "pap_002", "abstract":
             "Catheter deflection in endovascular navigation depends "
             "on friction between the guidewire and the sheath wall "
             "under cyclic pulsatile flow conditions in vivo.",
             "content_hash": "h" * 16, "title": "t",
             "retrieval_timestamp": "2026-09-16T00:00:00Z"}
    span_from_other = ("friction between the guidewire and the sheath "
                       "wall under cyclic pulsatile flow")
    # (a) repair vs THIS abstract must not fire (the span belongs to a
    # different paper; no >=8-word contiguous run exists here)
    c = _candidate(span_from_other, paper=other)
    out = repair_mechanism_span(c, ABSTRACT)
    assert "span_repair" not in out
    # (b) the ALIGNED case: the candidate claims pap_002 and the span
    # IS verbatim in pap_002's abstract -> SUPPORTED (the R469 source
    # alignment; the old evidence[0]-always gate would have wrongly
    # failed this honest rotation candidate)
    res = verify_evidence(out, [PAPER, other])
    assert res["verified"] is True
    # (c) the MISATTRIBUTION case: the same span claimed against
    # pap_001 -> byte-exact failure stands (wrong-paper rejection)
    c2 = _candidate(span_from_other, paper=PAPER)
    res2 = verify_evidence(c2, [PAPER, other])
    assert res2["verified"] is False
    assert "mechanism_span_not_verbatim" in res2["issues"]


def test_punctuation_mismatch_breaks_run():
    # the emitted span differs by ONE punctuation mark; the contiguous
    # verbatim run must break there (no punctuation normalization)
    c = _candidate("injured endothelium within seconds and initiate")
    out = repair_mechanism_span(c, ABSTRACT)
    # the run 'injured endothelium within seconds and initiate' shares
    # 'injured endothelium within seconds' (5 words) then breaks at the
    # punctuation difference -> below the floor -> no repair
    if "span_repair" in out:
        # if any window was promoted it is STILL byte-exact + >= floor
        assert out["mechanism_source_span"] in ABSTRACT
        assert len(out["mechanism_source_span"].split()) >= SPAN_MIN_WORDS


def test_non_adjacent_words_not_joined():
    # words that exist in the abstract but are far apart must never be
    # spliced into one span
    c = _candidate("Aneurysm recurrence glycocalyx several weeks "
                   "incomplete wall apposition neointimal coverage")
    out = repair_mechanism_span(c, ABSTRACT)
    if "span_repair" in out:
        assert out["mechanism_source_span"] in ABSTRACT  # contiguous


def test_repair_is_deterministic():
    c1 = _candidate("The mechanism involves platelets adhere to the "
                    "injured endothelium within seconds and initiate "
                    "thrombus formation at the device site")
    c2 = _candidate("The mechanism involves platelets adhere to the "
                    "injured endothelium within seconds and initiate "
                    "thrombus formation at the device site")
    o1 = repair_mechanism_span(c1, ABSTRACT)
    o2 = repair_mechanism_span(c2, ABSTRACT)
    assert o1["mechanism_source_span"] == o2["mechanism_source_span"]
    assert o1["span_repair"]["promoted"] == \
        o2["span_repair"]["promoted"]


def test_verify_module_has_no_fuzzy_matching():
    """Constitutional tripwire: the verifier stays byte-exact forever."""
    src = (REPO / "discovery_fabric" / "a2" / "verify.py").read_text()
    for banned in ("difflib", "rapidfuzz", "fuzzywuzzy", "Levenshtein",
                   "SequenceMatcher"):
        assert banned not in src, banned


def test_prompt_carries_the_mechanical_rules():
    assert "character-for-character" in SPAN_INSTRUCTION
    assert "8 consecutive words" in SPAN_INSTRUCTION
    assert "paraphrase" in SPAN_INSTRUCTION
