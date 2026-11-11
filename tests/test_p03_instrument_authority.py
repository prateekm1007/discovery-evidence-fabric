"""P0-3 (owner directive 2026-11-11, item 3; Art. LXXXI): per-instrument
attacker deployment authority.

The deterministic intervention-gate checks that a2/adversarial.py runs as
kill classes BEFORE the LLM gauntlet are SEPARATE attacker instruments:

    intervention_gate_function_removal/1.0.0
    intervention_gate_restates_constraint/1.0.0

Art. LXXXI: "the gate applies to every attacker instrument separately.
A new instrument version resets calibration status to UNCALIBRATED and
must earn deployment authority independently."

These two versions have NO committed calibration yet (the pinned
owner-held measurement + seal records are absent from the registry), so
both resolve UNKNOWN_NOT_CALIBRATED fail-closed: their kill classes may
issue the typed ESCALATED_OBJECTION (objection preserved verbatim, no
negative knowledge — Art. LXI/XXV), never a terminal KILL. Terminal
authority flips ONLY when the owner-held records land under the pinned
names and resolve_state derives CALIBRATED from their numbers against
the sealed bars — never asserted here, never threshold-tuned (Art.
XXVII). Synthetic fixtures below test the code paths; they do not
establish real calibration (the registry binding is monkeypatched, not
committed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest

from discovery_fabric.engine import attacker_calibration
from discovery_fabric.engine.attacker_calibration import (
    INSTRUMENT_MEASUREMENTS, resolve_state)

FR_INST = "intervention_gate_function_removal/1.0.0"
RC_INST = "intervention_gate_restates_constraint/1.0.0"

# P02 benchmark constraint (tests/test_intervention_gate.py pin): the
# "float at 2.27 V" mandate the 2.17 V intervention lowers
P02_C = ("15-year float service life at 2.27 V per cell without "
         "antimony above 2 percent")


# ---------------------------------------------------------------------------
# 1. registry + fail-closed states
# ---------------------------------------------------------------------------

def test_intervention_gate_instruments_registered_separately():
    # Art. LXXXI: the gate applies to every attacker instrument
    # separately — two kill classes, two instrument versions, each
    # earning authority independently
    assert FR_INST in INSTRUMENT_MEASUREMENTS
    assert RC_INST in INSTRUMENT_MEASUREMENTS
    assert FR_INST != RC_INST


@pytest.mark.parametrize("inst", [FR_INST, RC_INST])
def test_uncalibrated_intervention_gate_instruments_fail_closed(inst):
    # the pinned owner-held records are absent: UNKNOWN_NOT_CALIBRATED,
    # terminal_kill_admissible False (an unmeasured instrument has no
    # measured terminal authority, Art. L — fail-closed)
    st = resolve_state(instrument_version=inst)
    assert st["state"] == "UNKNOWN_NOT_CALIBRATED", st
    assert st["terminal_kill_admissible"] is False, st
    assert "absent" in st["reason"], st


# ---------------------------------------------------------------------------
# 2. behavior: uncalibrated kill class -> typed ESCALATED_OBJECTION
# ---------------------------------------------------------------------------

def _fr_kill_check(constraint, intervention):
    return {"killed": True, "state": "KILL",
            "kill_class": "LOWERS_MANDATED_FLOOR",
            "basis": ("constraint mandates float voltage at/above 2.27 V "
                      "per cell; intervention proposes 2.17 V per cell")}


def _rc_kill_check(constraint, intervention, mechanism):
    return {"killed": True, "state": "KILL",
            "kill_class": "RESTATES_CONSTRAINT",
            "jaccard": 0.91,
            "basis": "intervention is a token-level restatement of the "
                     "constraint (Jaccard 0.91) with no mechanism content"}


def _cand():
    return {"mechanism": "reducing the float voltage slows the corrosion "
                        "kinetics of the positive grid",
            "intervention": "Reduce the float charge voltage to 2.17 V "
                             "per cell.",
            "constraint_set": {"problem_constraint": P02_C}}


def test_uncalibrated_function_removal_is_escalated_not_terminal(
        monkeypatch):
    import discovery_fabric.engine.intervention_gate as ig
    monkeypatch.setattr(ig, "function_removal_check", _fr_kill_check)
    from discovery_fabric.a2.adversarial import adversarial_challenge
    import discovery_fabric.a2.adversarial as adv
    calls = {"n": 0}
    spy_orig = adv.llm_chat

    def spy(*a, **k):
        calls["n"] += 1
        return None
    adv.llm_chat = spy
    try:
        res = adversarial_challenge(_cand(), evidence_verified=True,
                                    prior_art_state="NO_MATCH_FOUND")
    finally:
        adv.llm_chat = spy_orig
    assert res["overall"] == "ESCALATED_OBJECTION", res
    assert res["adversarial_status"] == "ESCALATED_OBJECTION"
    assert res["killed_count"] == 0
    assert "KILLED" not in json.dumps(res.get("attacks"))
    obj = res["deterministic_objection"]
    assert obj["instrument"] == FR_INST
    assert obj["calibration_state"]["calibration_state"] == \
        "UNKNOWN_NOT_CALIBRATED"
    assert obj["calibration_state"]["terminal_kill_admissible"] is False
    assert obj["kill_class"] == "LOWERS_MANDATED_FLOOR"
    # the objection + deterministic basis preserved verbatim
    assert "2.17" in str(obj["basis"])
    assert res.get("kill_basis")
    assert calls["n"] == 0  # no LLM compute on the escalated path


def test_uncalibrated_restates_constraint_has_its_own_authority(
        monkeypatch):
    # the two instruments are gated SEPARATELY: function_removal NOT
    # killed -> restates_constraint fires its class on its OWN
    # instrument version
    import discovery_fabric.engine.intervention_gate as ig
    monkeypatch.setattr(ig, "function_removal_check",
                        lambda c, i: {"killed": False})
    monkeypatch.setattr(ig, "restates_constraint_check", _rc_kill_check)
    from discovery_fabric.a2.adversarial import adversarial_challenge
    cand = {"mechanism": "",
            "intervention": "Maintain float service at 2.27 V per cell "
                             "and antimony below 2 percent",
            "constraint_set": {"problem_constraint": P02_C}}
    res = adversarial_challenge(cand, evidence_verified=True,
                                prior_art_state="NO_MATCH_FOUND")
    assert res["overall"] == "ESCALATED_OBJECTION", res
    obj = res["deterministic_objection"]
    assert obj["instrument"] == RC_INST
    assert obj["calibration_state"]["terminal_kill_admissible"] is False
    assert obj["kill_class"] == "RESTATES_CONSTRAINT"
    assert obj["jaccard"] == 0.91
    assert res["killed_count"] == 0


# ---------------------------------------------------------------------------
# 3. behavior: calibrated (synthetic records, code test only) -> terminal
# ---------------------------------------------------------------------------

def _synthetic_calibrated_pair(tmp_path: Path):
    seal = tmp_path / "seal.json"
    seal.write_text(json.dumps({
        "pre_registered_thresholds": {
            "fpr_max": 0.30, "tpr_min": 0.75,
            "coverage_min": 0.95, "parse_completeness_min": 0.95}}),
        encoding="utf-8")
    measurement = tmp_path / "measurement.json"
    measurement.write_text(json.dumps({
        "metrics": {"false_kill_rate_on_known_good": 0.10,
                    "coverage": 1.0, "parse_completeness": 1.0},
        "scoped_tpr_diagnostic": {"tpr": 0.9},
        "n_cases_attacked": 40,
        "threshold_verdict": {"calibrated": True}}),
        encoding="utf-8")
    return measurement, seal


def test_calibrated_function_removal_earns_terminal_kill(monkeypatch,
                                                          tmp_path):
    # a SYNTHETIC measurement + seal pair proves the code path; it does
    # NOT establish real calibration (the binding is monkeypatched, not
    # committed — the owner-held records are what flip the real state)
    m, s = _synthetic_calibrated_pair(tmp_path)
    monkeypatch.setitem(INSTRUMENT_MEASUREMENTS, FR_INST,
                        {"measurement": m, "seal": s})
    import discovery_fabric.engine.intervention_gate as ig
    monkeypatch.setattr(ig, "function_removal_check", _fr_kill_check)
    from discovery_fabric.a2.adversarial import adversarial_challenge
    res = adversarial_challenge(_cand(), evidence_verified=True,
                                prior_art_state="NO_MATCH_FOUND")
    assert res["overall"] == "KILL", res
    assert res["adversarial_status"] == "KILLED_DETERMINISTIC"
    assert res["killed_count"] == 1
    kill = res["deterministic_kill"]
    assert kill["instrument"] == FR_INST
    assert kill["calibration_state"]["terminal_kill_admissible"] is True
    assert kill["calibration_state"]["calibration_state"] == "CALIBRATED"
    assert kill["llm_gauntlet_ran"] is False
    # the OTHER instrument stays uncalibrated — authority is per
    # instrument (Art. LXXXI), never shared
    assert resolve_state(instrument_version=RC_INST)[
        "terminal_kill_admissible"] is False


def test_fpr_above_sealed_bar_revokes_terminal_authority(monkeypatch,
                                                          tmp_path):
    # FPR 0.50 > sealed bar 0.30 (Art. LXXXI): the measured record
    # exists but the instrument is measured non-selective — terminal
    # kills remain inadmissible; the escalation path is the only one
    m, s = _synthetic_calibrated_pair(tmp_path)
    m.write_text(json.dumps({
        "metrics": {"false_kill_rate_on_known_good": 0.50,
                    "coverage": 1.0, "parse_completeness": 1.0},
        "scoped_tpr_diagnostic": {"tpr": 1.0},
        "n_cases_attacked": 40,
        "threshold_verdict": {"calibrated": False}}),
        encoding="utf-8")
    monkeypatch.setitem(INSTRUMENT_MEASUREMENTS, FR_INST,
                        {"measurement": m, "seal": s})
    st = resolve_state(instrument_version=FR_INST)
    assert st["state"] == "NOT_CALIBRATED", st
    assert st["terminal_kill_admissible"] is False, st
    assert "0.5" in str(st.get("reason"))
    import discovery_fabric.engine.intervention_gate as ig
    monkeypatch.setattr(ig, "function_removal_check", _fr_kill_check)
    from discovery_fabric.a2.adversarial import adversarial_challenge
    res = adversarial_challenge(_cand(), evidence_verified=True,
                                prior_art_state="NO_MATCH_FOUND")
    assert res["overall"] == "ESCALATED_OBJECTION", res


# ---------------------------------------------------------------------------
# 4. classify: the escalated overall maps to UNKNOWN / adjudication
#    blocked — no negative knowledge (Art. LXI/XXV)
# ---------------------------------------------------------------------------

def test_escalated_objection_maps_to_unknown_not_rejected(monkeypatch):
    import discovery_fabric.engine.intervention_gate as ig
    monkeypatch.setattr(ig, "function_removal_check", _fr_kill_check)
    from discovery_fabric.a2.adversarial import adversarial_challenge
    from discovery_fabric.a2.classify import classify
    rec = adversarial_challenge(_cand(), evidence_verified=True,
                                prior_art_state="NO_MATCH_FOUND")
    out = classify(candidate={},
                   evidence_verification={"verified": True},
                   prior_art={"prior_art_status": "NO_MATCH_FOUND"},
                   adversarial=rec)
    assert out["final_status"] == "UNKNOWN", out
    assert out.get("adjudication_blocked") is True
    assert out.get("promotion_blocked") is True
    # never negative knowledge: the uncalibrated instrument must not
    # manufacture a scientific rejection
    assert out["final_status"] != "REJECTED"
    assert out["epistemic_state"] == "CANDIDATE_CONNECTION"
