#!/usr/bin/env python3
"""r13_question_type_gate.py — AM14 D3: the QUESTION-TYPE GATE.

AM14 F31 (critical): a novel predictor answering an intervention
question scored a HIGH novelty delta in the dev batteries while being
the WRONG ANSWER TYPE — the gate never penalized it, so wrong-type
novelty was rewarded. This module adds the missing axis:

  gate_question_type(answer, problem) -> {"verdict": "MATCH"|"MISMATCH",
                                          "reason": str}

Rules (typed, deterministic, fail-closed):
- INTERVENTION-PROPOSAL question: the answer must PROPOSE A MITIGATION
  (an explicit design/operational change: intervention verbs or the
  mandated "NOVELTY STATEMENT (INTERVENTION)" section). An answer
  whose proposal is a monitoring observable / leading indicator is a
  MISMATCH — it watches the failure instead of preventing it.
- PREDICTOR-DESIGN question: the answer must be an observable/leading
  indicator design; a pure mitigation with no detection content is a
  MISMATCH (reverse direction, recorded too).
- Unverifiable (no sections, no verbs) -> MISMATCH (fail-closed).

The gate instrument (battery driver) folds this in: a MISMATCH pair's
judge scores are still recorded (zeros are data) but the pair is
EXCLUDED from the novelty/feasibility acceptance estimate with
excluded_reason QUESTION_TYPE_MISMATCH — wrong-type novelty no longer
counts toward any clause.
"""
import re

INTERVENTION_VERBS = re.compile(
    r"\b(install|replace|coat|add|derate|reconfigure|retrofit|swap|"
    r"upgrade|switch|introduce|apply|redesign|insert|machine|anneal|"
    r"plate|anodize|galvanize|balance|align|tighten|preheat|bake-?out|"
    r"flush|filter|clamp|shroud|shield| stiffen|stiffen|broaden|widen|"
    r"reduce the fit|increase the fit|torque|gasket|seal ring|"
    r"bellows|sacrificial anode|inhibitor|coating|liner|alloy|"
    r"temper|treat)\b", re.I)
OBSERVABLE_ONLY = re.compile(
    r"\b(leading indicator|invent the observable|monitoring observable|"
    r"the observable|predictor|predict the failure|detect)\b", re.I)
INTERVENTION_SECTION = "NOVELTY STATEMENT (INTERVENTION)"
PREDICTOR_SECTION = "NOVELTY STATEMENT"


def gate_question_type(ans: str, prob: dict) -> dict:
    qt = (prob.get("question_type") or "").lower()
    a = ans or ""
    if qt.startswith("intervention"):
        has_section = INTERVENTION_SECTION in a
        verbs = bool(INTERVENTION_VERBS.search(a))
        obs = bool(OBSERVABLE_ONLY.search(a[:1200]))
        if has_section or (verbs and not obs):
            return {"verdict": "MATCH",
                    "reason": "proposes a mitigation (section=%s, "
                              "verbs=True)" % has_section}
        if obs and not verbs:
            return {"verdict": "MISMATCH",
                    "reason": "predictor/observable proposal on an "
                              "intervention question (F31 class): it "
                              "watches the failure instead of "
                              "preventing it"}
        return {"verdict": "MISMATCH",
                "reason": "no explicit mitigation proposal found "
                          "(fail-closed: section=%s verbs=%s)"
                          % (has_section, verbs)}
    if qt.startswith("predictor"):
        has_pred = bool(OBSERVABLE_ONLY.search(a))
        if has_pred or PREDICTOR_SECTION in a:
            return {"verdict": "MATCH",
                    "reason": "observable/indicator design present"}
        return {"verdict": "MISMATCH",
                "reason": "no observable/indicator content found "
                          "(fail-closed)"}
    # unknown type: record, don't exclude
    return {"verdict": "MATCH", "reason": "unknown question_type — "
                                          "not gated"}


def pair_excluded(prob: dict, ans: str) -> dict | None:
    """Return the exclusion record for the gate instrument, or None."""
    g = gate_question_type(ans, prob)
    if g["verdict"] == "MISMATCH":
        return {"excluded": True, "excluded_reason": "QUESTION_TYPE_"
                "MISMATCH", "question_type": prob.get("question_type"),
                "gate_reason": g["reason"]}
    return None
