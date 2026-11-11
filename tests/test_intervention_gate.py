"""R6 intervention-gate tests (owner directive 2026-11-11, item 4).

Deterministic gates, pinned to the COMMITTED DEV cases:
  - eval-sofc-thermal-cycling (constraint: survive 500 thermal cycles
    from 25 C to 800 C, OCV above 1.0 V, seal leakage below 1 percent,
    stack mass +2 percent max)
  - bench-p02-leadacid-grid-corrosion (constraint: 15-year float life
    at 2.27 V per cell, antimony <= 2 percent)

Covered:
  1. function-removal terminal kills (floor lowering, ceiling raising,
     mandated-element elimination, mandated-range narrowing);
  2. restates-the-constraint terminal kill;
  3. NOT_AN_INTERVENTION rejection (monitor-only, study-only, empty);
  4. anchor domain rule (shared domain OR stated shared mechanism);
  5. the adversarial_challenge integration: a function-removal
     candidate is terminally killed with NO LLM call;
  6. a LEGITIMATE candidate passes the gate (no false kill on the
     committed cases' real constraint texts).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.intervention_gate import (
    function_removal_check, restates_constraint_check,
    not_an_intervention_check, anchor_domain_check)

REPO = Path(__file__).resolve().parents[1]
_PROBS = {p["problem_id"]: p for p in json.loads(
    (REPO / "eval" / "problems.json").read_text(encoding="utf-8"))["problems"]}

SOFC = _PROBS["eval-sofc-thermal-cycling"]
P02 = _PROBS["bench-p02-leadacid-grid-corrosion"]
SOFC_C = SOFC["constraint"]
P02_C = P02["constraint"]


# ---------------------------------------------------------------------------
# 1. function-removal kills on the committed cases
# ---------------------------------------------------------------------------
def test_sofc_floor_lowering_killed():
    # constraint: OCV above 1.0 V; intervention proposes 0.7 V floor
    r = function_removal_check(
        SOFC_C, "Reduce the OCV requirement to 0.7 V and coat the seal.")
    assert r["killed"] is True and r["kill_class"] == "LOWERS_MANDATED_FLOOR", r
    assert "open-circuit voltage" in r["basis"].lower() or "ocv" in r["basis"].lower()


def test_sofc_mandated_range_narrowed_killed():
    # constraint: survive 500 cycles from 25 C to 800 C; intervention
    # proposes narrowing the cycling window to 400 C (the start/stop
    # function the user requires is deleted from the operating envelope)
    r = function_removal_check(
        SOFC_C,
        "Limit thermal cycling from 25 C to 400 C so the seal never "
        "sees the 800 C excursion; add a compliant seal coating.")
    assert r["killed"] is True, r
    assert r["kill_class"] == "NARROWS_MANDATED_RANGE", r


def test_p02_floor_lowering_killed():
    # constraint: 15-year float life AT 2.27 V/cell; intervention
    # proposes 2.17 V/cell float (removes the mandated charge regime)
    r = function_removal_check(
        P02_C, "Reduce the float charge voltage to 2.17 V per cell to "
               "slow grid corrosion.")
    assert r["killed"] is True and r["kill_class"] == "LOWERS_MANDATED_FLOOR", r


def test_p02_ceiling_raising_killed():
    # constraint: antimony NOT above 2 percent; intervention: 4 percent
    r = function_removal_check(
        P02_C, "Raise antimony content to 4 percent for creep strength.")
    assert r["killed"] is True and r["kill_class"] == "RAISES_MANDATED_CEILING", r


def test_sofc_explicit_elimination_killed():
    r = function_removal_check(
        SOFC_C, "Eliminate the glass-ceramic seal entirely and rely on "
                "compressive contact.")
    assert r["killed"] is True, r
    assert r["kill_class"] == "REMOVES_MANDATED_ELEMENT", r


def test_legitimate_sofc_candidate_not_killed():
    # a real design change that RESPECTS every mandate: no kill
    legit = ("Bond the glass-ceramic seal joint with a compliant "
             "buffer layer rated to 850 C and add fillet radius 1.5 mm "
             "at the seal-electrolyte interface.")
    r = function_removal_check(SOFC_C, legit)
    assert r["killed"] is False, r
    r2 = restates_constraint_check(SOFC_C, legit, "differential expansion buffer")
    assert r2["killed"] is False, r2


def test_legitimate_p02_candidate_not_killed():
    legit = ("Change the positive grid alloy to lead-calcium-tin with "
             "1.5 percent tin and 0.8 percent calcium, holding float at "
             "2.27 V per cell.")
    r = function_removal_check(P02_C, legit)
    assert r["killed"] is False, r


# ---------------------------------------------------------------------------
# 2. restates-the-constraint kill
# ---------------------------------------------------------------------------
def test_sofc_constraint_paraphrase_killed():
    r = restates_constraint_check(
        SOFC_C,
        "The stack must survive 500 thermal cycles from 25 C to 800 C "
        "while holding open-circuit voltage above 1.0 V.")
    assert r["killed"] is True and r["kill_class"] == "RESTATES_THE_CONSTRAINT", r
    # the kill rides ONE of the two deterministic paths: whole-text
    # Jaccard (>= 0.62) or containment (>= 0.8 with < 4 new tokens)
    assert (r.get("jaccard", 0) >= 0.62
            or r.get("containment", 0) >= 0.8), r


def test_paraphrase_with_mechanism_not_killed():
    r = restates_constraint_check(
        SOFC_C,
        "Survive the 500-cycle 25-800 C schedule by adding a compliant "
        "porous zirconia buffer that absorbs the differential expansion "
        "of the anode and the electrolyte.")
    assert r["killed"] is False, r


# ---------------------------------------------------------------------------
# 3. NOT_AN_INTERVENTION rejection
# ---------------------------------------------------------------------------
def test_monitor_only_rejected():
    r = not_an_intervention_check(
        "Continue monitoring the seal leakage rate more closely over "
        "time and log the results.")
    assert r["rejected"] is True and r["reason_class"] == "NOT_AN_INTERVENTION", r


def test_gather_data_rejected():
    r = not_an_intervention_check(
        "Collect more data on the corrosion rate before deciding.")
    assert r["rejected"] is True, r


def test_future_work_rejected():
    r = not_an_intervention_check(
        "Further research is needed to determine the right alloy; "
        "no design change is proposed now.")
    assert r["rejected"] is True, r


def test_empty_rejected():
    assert not_an_intervention_check("")["rejected"] is True
    assert not_an_intervention_check(None)["rejected"] is True


def test_real_intervention_not_rejected():
    r = not_an_intervention_check(
        "Switch the positive grid to a lead-calcium-tin alloy with 1.5 "
        "percent tin and refloat at 2.27 V per cell.")
    assert r["rejected"] is False, r


# ---------------------------------------------------------------------------
# 4. anchor domain rule
# ---------------------------------------------------------------------------
def test_anchor_shared_domain_ok():
    item = {"title": "Corrosion growth of lead-calcium battery grids "
                     "during float charging",
            "abstract": "Positive grid corrosion raises internal "
                        "resistance in valve-regulated lead-acid "
                        "batteries during extended float service."}
    fields = {"mechanism": "grid corrosion consumes cross-section",
              "intervention": "switch to a low-antimony alloy"}
    r = anchor_domain_check(P02, item, fields)
    assert r["ok"] is True and r["shared_domain"] is True, r


def test_anchor_cross_domain_with_stated_mechanism_ok():
    item = {"title": "Thermal barrier coatings on gas-turbine blades",
            "abstract": "Yttria-stabilized zirconia layers reduce heat "
                        "flux to the superalloy substrate under thermal "
                        "cycling of turbine hardware."}
    fields = {"mechanism": "the same differential-expansion mechanism "
                           "drives both the seal microcrack growth here "
                           "and the TBC spallation there",
              "intervention": "apply a compliant buffer"}
    r = anchor_domain_check(SOFC, item, fields)
    assert r["ok"] is True and r["shared_mechanism_stated"] is True, r


def test_anchor_unrelated_and_unstated_rejected():
    item = {"title": "Deep-sea sediment compaction records",
            "abstract": "Sediment porosity decreases with burial depth "
                        "in ocean-floor cores from the north Pacific."}
    fields = {"mechanism": "porosity reduction under load",
              "intervention": "compact the seal material"}
    r = anchor_domain_check(SOFC, item, fields)
    assert r["ok"] is False, r


# ---------------------------------------------------------------------------
# 5. assemble_candidate integration (typed states)
# ---------------------------------------------------------------------------
def test_assemble_candidate_rejects_not_an_intervention():
    from discovery_fabric.engine import mechanism_space as ms
    operator = {"operator_id": "DIRECT_TRANSFER", "version": "v1",
                "input_contract": lambda item, problem: {}}
    item = {"item_id": "x1", "title": "Grid corrosion in lead-acid "
            "batteries during float", "abstract": "Positive grid "
            "corrosion growth in valve-regulated lead-acid batteries "
            "under extended float charge raises internal resistance.",
            "fields": {}, "source": {}, "confidence": 0.9,
            "structured_hash": "h"}
    fields = {"mechanism": "corrosion layer growth", "intervention":
              "Continue to monitor the battery more closely over time.",
              "testable_prediction": "capacity falls below threshold in "
              "12 months", "mechanism_source_span": "grid corrosion "
              "growth"}
    cand = ms.assemble_candidate(operator, item, fields, P02, {})
    assert cand["candidate_state"].startswith("NOT_AN_INTERVENTION"), cand
    assert cand.get("not_an_intervention_reason")


def test_assemble_candidate_anchor_domain_typed_state():
    from discovery_fabric.engine import mechanism_space as ms
    operator = {"operator_id": "DIRECT_TRANSFER", "version": "v1",
                "input_contract": lambda item, problem: {}}
    item = {"item_id": "x2", "title": "Deep-sea sediment compaction",
            "abstract": "Ocean-floor sediment porosity decreases with "
            "burial depth in pacific cores.", "fields": {}, "source": {},
            "confidence": 0.9, "structured_hash": "h2"}
    fields = {"mechanism": "porosity reduction under load",
              "intervention": "Compact the seal glass phase to 0.10 "
              "mass fraction before firing.",
              "testable_prediction": "leakage falls below 1 percent in "
              "the 500-cycle rig",
              "mechanism_source_span": "porosity decreases with burial "
              "depth"}
    cand = ms.assemble_candidate(operator, item, fields, SOFC, {})
    assert cand["candidate_state"] == "NOT_EVIDENCE_ANCHORED_DOMAIN", cand


# ---------------------------------------------------------------------------
# 6. adversarial_challenge integration: deterministic terminal kill
#    with NO LLM call
# ---------------------------------------------------------------------------
def test_adversarial_challenge_function_removal_no_llm():
    from discovery_fabric.a2 import adversarial as adv
    calls = {"n": 0}
    orig = adv.llm_chat

    def spy(*a, **k):
        calls["n"] += 1
        return orig(*a, **k)
    adv.llm_chat = spy
    try:
        cand = {
            "mechanism": "reducing the float voltage slows the corrosion "
                         "kinetics of the positive grid",
            "intervention": "Reduce the float charge voltage to 2.17 V "
                            "per cell.",
            "predicted_effect": "corrosion growth falls 30 percent",
            "testable_prediction": "capacity loss after 15 years under "
                                   "2.17 V float",
            "constraint_set": {"problem_constraint": P02_C},
        }
        res = adv.adversarial_challenge(cand, evidence_verified=True,
                                        prior_art_state="NO_MATCH_FOUND")
        assert res.get("overall") == "KILL", res
        assert res.get("adversarial_status") == "KILLED_DETERMINISTIC"
        assert res["deterministic_kill"]["kill_class"] == \
            "LOWERS_MANDATED_FLOOR"
        assert res["deterministic_kill"]["llm_gauntlet_ran"] is False
        assert calls["n"] == 0, "no LLM compute may be spent on a " \
                                "function-removal candidate"
    finally:
        adv.llm_chat = orig


def test_adversarial_challenge_legitimate_runs_llm():
    # a legitimate candidate does NOT trip the deterministic gate (it
    # reaches the LLM gauntlet; the transport may fail in the sandbox —
    # the assertion is on the gate, never on the LLM verdict)
    from discovery_fabric.a2 import adversarial as adv
    reached_llm = {"flag": False}
    orig = adv.llm_chat

    def spy(*a, **k):
        reached_llm["flag"] = True
        return None  # transport refusal — never a KILL (typed path)
    adv.llm_chat = spy
    try:
        cand = {
            "mechanism": "tin additions improve the corrosion-layer "
                         "conductivity and cut early-life capacity loss",
            "intervention": "Change the positive grid alloy to "
                            "lead-calcium-tin with 1.5 percent tin, "
                            "holding float at 2.27 V per cell.",
            "predicted_effect": "15-year float service achieved",
            "testable_prediction": "capacity above service threshold "
                                   "after 15-year float",
            "constraint_set": {"problem_constraint": P02_C},
        }
        res = adv.adversarial_challenge(cand, evidence_verified=True,
                                        prior_art_state="NO_MATCH_FOUND")
        assert reached_llm["flag"] is True, res
        assert res.get("adversarial_status") != "KILLED_DETERMINISTIC"
        assert res.get("overall") == "EVALUATOR_CALL_FAILED"  # typed infra
    finally:
        adv.llm_chat = orig
