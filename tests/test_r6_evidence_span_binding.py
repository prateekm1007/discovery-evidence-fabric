"""tests/test_r6_evidence_span_binding.py — owner audit round 2026-11-13
P0, Article LXXX: every mechanism must carry >= 8 CONTIGUOUS VERBATIM
words from its own frozen record, bound to the exact source/snapshot.

What is pinned:
  1. Deterministic word-count + verbatim check: 8 contiguous words pass,
     7 fail; a fabricated span fails; a quoted passage plus a bracketed
     annotation passes on its verbatim run.
  2. Missing/too-short/fabricated evidence is UNGROUNDED_SYNTHESIS — an
     epistemic UNKNOWN with `not_a_scientific_rejection=True`, never a
     scientific rejection and never a candidate.
  3. Exact source/snapshot binding is required when the item came from a
     frozen/expansion plane (missing snapshot ids => ungrounded).
  4. DOMAIN_KNOWLEDGE_FIRST is KNOWLEDGE_FIRST_EXPLORATORY: its anchor is
     the user problem statement, NOT a frozen record, and it is excluded
     from span_verbatim_rate (both numerator and denominator).
  5. span_summary / _metrics / stage_entry carry span_verbatim_rate,
     span_min_words, n_ungrounded_synthesis, n_exploratory.
  6. apply_operator emits the typed state and the retry path enforces the
     same rule (no second weaker gate).

Hermetic: the LLM call site is monkeypatched; zero network.
"""
from __future__ import annotations

import types
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.engine import stage_entry  # noqa: E402

PROBLEM = {
    "problem_id": "r6_span",
    "device": "tunneled hemodialysis catheter",
    "failure": "thrombotic occlusion of the catheter lumen under low flow",
    "failure_mode": "thrombosis",
    "constraint": "maintain drainage above 0.05 mL/min at venous pressure",
}

RECORD_TEXT = (
    "In a controlled bench study we demonstrate that heparin bonding "
    "of the catheter lumen reduces thrombus formation under low flow "
    "conditions. Heparin bonding inhibits clotting cascade activation "
    "at the luminal surface. We measured thrombus area at flow rate "
    "50 mL/min and venous pressure 20 mmHg: heparin-bonded lumens "
    "showed significantly reduced thrombus compared with untreated "
    "polyurethane controls.")

GOOD_SPAN = ("Heparin bonding inhibits clotting cascade activation "
             "at the luminal surface")
SHORT_SPAN = "Heparin bonding inhibits clotting"

ITEM = {
    "item_id": "evd-med-001",
    "structured_hash": "sh-med-001",
    "_record_text": RECORD_TEXT,
    "_evidence_plane": "FROZEN_PRIMARY",
    "_evidence_snapshot_id": "snap-001",
    "_evidence_hash": "evhash-001",
    "fields": {
        "claim": {"value": "heparin bonding reduces thrombus formation"},
        "system": {"value": "tunneled hemodialysis catheter lumen"},
        "mechanism": {"value": "heparin bonding inhibits clotting cascade "
                               "activation at the luminal surface"},
        "observed_effect": {"value": "significantly reduced thrombus area "
                                     "versus polyurethane controls"},
        "intervention": {"value": "heparin bonding of the luminal surface"},
        "boundary_conditions": {"value": "flow rate 50 mL/min and venous "
                                         "pressure 20 mmHg"},
        "constraints": {"value": "luminal surface treatment must not "
                                 "narrow the lumen"},
        "failure_mode": {"value": "thrombotic occlusion"},
        "confidence": {"value": "HIGH"},
    },
    "source": {"source": "europepmc", "id": "evd-med-001"},
    "confidence": "HIGH",
}

RESPONSE = (
    "MECHANISM: heparin bonding inhibits clotting cascade activation at "
    "the luminal surface\n"
    "INTERVENTION: bond heparin to the catheter luminal surface\n"
    "PREDICTED_EFFECT: thrombus area reduced by at least 50 percent "
    "under low flow\n"
    "NOVEL_DESIGN_VARIABLE: luminal heparin surface density\n"
    "TESTABLE_PREDICTION: at flow rate 50 mL/min, thrombus area is "
    "reduced by at least 50 percent versus untreated controls\n"
    "KNOWN_FAILURE_MODES: heparin leaching over weeks\n"
    "BOUNDARY_CONDITIONS: flow rate above 20 mL/min\n"
    "MECHANISM_SOURCE_SPAN: {span}\n"
)


def _op(op_id="DIRECT_TRANSFER"):
    return [o for o in ms.TRANSFORMATION_OPERATORS
            if o["operator_id"] == op_id][0]


def _fake_llm(responses):
    state = {"i": 0}

    def _gen(prompt, system="", timeout=240, max_tokens=700,
             purpose="mechanism_space", exclude_providers=None,
             hard_pin_provider=None, **kwargs):
        i = state["i"]
        state["i"] += 1
        if i >= len(responses) or responses[i] is None:
            return {"ok": False, "status": "CALL_FAILED",
                    "content": None, "provider": "fake",
                    "model": "fake", "error": "simulated failure"}
        return {"ok": True, "status": "OK", "content": responses[i],
                "provider": "fake", "model": "fake-model",
                "prompt_hash": f"ph{i}", "output_hash": f"oh{i}",
                "error": None}
    return _gen


# ---------------------------------------------------------------------------
# 1. Deterministic span binding
# ---------------------------------------------------------------------------
def test_eight_contiguous_verbatim_words_ground_the_mechanism():
    b = ms.span_binding_check(GOOD_SPAN, RECORD_TEXT, ITEM)
    assert b["longest_verbatim_word_run"] >= 8
    assert b["meets_min_verbatim_words"] is True
    assert b["grounded"] is True
    assert b["span_state"] == "GROUNDED"
    assert b["source_binding"]["record_sha256"]
    assert b["snapshot_required"] is True
    assert b["snapshot_bound"] is True


def test_seven_words_do_not_ground():
    span = "heparin bonding inhibits clotting cascade activation at"
    assert len(span.split()) == 7
    b = ms.span_binding_check(span, RECORD_TEXT, ITEM)
    assert b["longest_verbatim_word_run"] == 7
    assert b["meets_min_verbatim_words"] is False
    assert b["grounded"] is False
    assert b["span_state"] == "UNGROUNDED_SYNTHESIS"


def test_fabricated_span_cannot_ground():
    b = ms.span_binding_check(
        "an invented span that appears nowhere in the record",
        RECORD_TEXT, ITEM)
    assert b["longest_verbatim_word_run"] < 8
    assert b["grounded"] is False


def test_quoted_passage_plus_annotation_grounds_on_its_verbatim_run():
    b = ms.span_binding_check(
        GOOD_SPAN + " [emphasis added by the engineer]",
        RECORD_TEXT, ITEM)
    assert b["longest_verbatim_word_run"] >= 8
    assert b["grounded"] is True
    assert b["match_mode"] == "PARTIAL_WORD_RUN"


def test_missing_snapshot_binding_is_ungrounded():
    item = dict(ITEM)
    item.pop("_evidence_snapshot_id")
    item.pop("_evidence_hash")
    b = ms.span_binding_check(GOOD_SPAN, RECORD_TEXT, item)
    assert b["snapshot_required"] is True
    assert b["snapshot_bound"] is False
    assert b["record_bound"] is False
    assert b["grounded"] is False


def test_span_must_come_from_its_own_record():
    other = "A completely unrelated abstract about bearing lubrication."
    b = ms.span_binding_check(GOOD_SPAN, other, ITEM)
    assert b["grounded"] is False


def test_exploratory_knowledge_first_is_exempt_and_labelled():
    b = ms.span_binding_check(GOOD_SPAN, RECORD_TEXT, ITEM,
                              exploratory=True)
    assert b["grounded"] is False
    assert b["exploratory_exempt"] is True
    assert b["span_state"] == "KNOWLEDGE_FIRST_EXPLORATORY"


# ---------------------------------------------------------------------------
# 2. apply_operator integration
# ---------------------------------------------------------------------------
def test_operator_emits_ungrounded_synthesis_for_short_span(monkeypatch):
    short = RESPONSE.format(span=SHORT_SPAN)
    monkeypatch.setattr(ms, "llm_generate", _fake_llm([short, None]))
    res = ms.apply_operator(_op(), [ITEM], PROBLEM)
    cand = res["candidates"][0]
    assert cand["candidate_state"] == "UNGROUNDED_SYNTHESIS"
    assert cand["span_binding"]["meets_min_verbatim_words"] is False
    assert cand["epistemic_class"] == "UNKNOWN"
    assert cand["not_a_scientific_rejection"] is True
    assert cand["discovery_credit"] == "NONE_UNGROUNDED"


def test_operator_admits_eight_word_span(monkeypatch):
    monkeypatch.setattr(ms, "llm_generate",
                        _fake_llm([RESPONSE.format(span=GOOD_SPAN)]))
    res = ms.apply_operator(_op(), [ITEM], PROBLEM)
    cand = res["candidates"][0]
    assert cand["candidate_state"] == "CANDIDATE"
    assert cand["evidence_class"] == "FROZEN_RECORD_GROUNDED"
    assert cand["span_binding"]["grounded"] is True


def test_knowledge_first_stays_exploratory(monkeypatch):
    kf_item = ms.knowledge_first_item(PROBLEM)
    response = (
        "MECHANISM: heparin bonding passivates the luminal surface and "
        "inhibits clotting cascade activation\n"
        "INTERVENTION: apply a heparin-bonded coating to the catheter "
        "lumen\n"
        "PREDICTED_EFFECT: thrombus area reduced by at least 50 percent "
        "under low flow\n"
        "NOVEL_DESIGN_VARIABLE: luminal heparin surface density\n"
        "TESTABLE_PREDICTION: at flow rate 50 mL/min, thrombus area is "
        "reduced by at least 50 percent versus untreated controls\n"
        "KNOWN_FAILURE_MODES: heparin leaching over weeks\n"
        "BOUNDARY_CONDITIONS: flow rate above 20 mL/min\n"
        "MECHANISM_SOURCE_SPAN: thrombotic occlusion of the catheter "
        "lumen under low flow\n")
    monkeypatch.setattr(ms, "llm_generate", _fake_llm([response]))
    res = ms.apply_operator(_op("DOMAIN_KNOWLEDGE_FIRST"), [kf_item],
                            PROBLEM)
    cand = res["candidates"][0]
    assert cand["candidate_state"] == "CANDIDATE"
    assert cand["evidence_class"] == "KNOWLEDGE_FIRST_EXPLORATORY"
    assert cand["discovery_credit"] == "EXPLORATORY_NOT_EVIDENCE_GROUNDED"
    assert cand["span_binding"]["exploratory_exempt"] is True


# ---------------------------------------------------------------------------
# 3. Summaries carry the span facts and exclude DKF
# ---------------------------------------------------------------------------
def test_span_summary_rate_excludes_exploratory():
    grounded = {"span_binding": {"grounded": True,
                                 "longest_verbatim_word_run": 12}}
    ungrounded = {"span_binding": {"grounded": False,
                                   "longest_verbatim_word_run": 3}}
    exploratory = {"span_binding": {"exploratory_exempt": True}}
    s = ms.span_summary([grounded, ungrounded, exploratory])
    assert s["n_spans_checked"] == 2
    assert s["n_grounded"] == 1
    assert s["n_ungrounded_synthesis"] == 1
    assert s["n_exploratory_knowledge_first"] == 1
    assert s["span_verbatim_rate"] == 0.5
    assert s["span_min_words"] == 8


def test_stage_entry_divergence_facts_carry_span_rate():
    env = types.SimpleNamespace(
        mechanism_space={
            "state": "BUILT",
            "n_candidates_retained": 2,
            "distinctness": {
                "n_distinct": 2,
                "instrument_version": "mechanism_distinctness/2.0.0"},
            "span_binding_summary": ms.span_summary([]),
        },
        adjudication={})
    facts = stage_entry.mechanism_diversity_facts(env)
    assert facts["span_verbatim_rate"] is None
    assert facts["evidence_class"] == "LEXICAL_SCREENING_HEURISTIC"
    assert facts["discovery_credit"] == (
        "NOT_ESTABLISHED_AS_CAUSAL_DISTINCTNESS")
    ret = stage_entry.retained_candidate_facts(env)
    assert "span_verbatim_rate" in ret
    assert ret["span_min_words"] == 8
