#!/usr/bin/env python3
"""AM29 D1+D2 pins: the constraint-CLASS bind and the
DIRECTION-OF-EFFECT bind, against the auditor's own verdict bytes
(holdout v4 @ audit tip d9a6b2c06) plus synthetic unseen-vocabulary
and conformant cases.

The class bind must fire on HO4-04 and HO4-05 (the auditor's named
allowed-measures violations), fire LIMIT_DIRECTION_VIOLATION on
HO4-03 (cycling-to-heal under a ramp-rate LIMIT), and stay SILENT on
HO4-01/HO4-06 (dosing permitted by dose selection; the auditor
accepted those bills) and HO4-02 (gradation change IS the permitted
measure — its inversion is the direction bind's finding). The
direction bind must fire on HO4-02 and HO4-03 and stay clean on a
conformant synthetic carrying the structured statement.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r30_allowed_class_scan import (  # noqa: E402
    scan_allowed_measures_class)
from r30_physics_direction_scan import (  # noqa: E402
    scan_physics_direction)

AUDIT_BRANCH = "origin/audit/r11-auditor-verdict-20261114"
GEN = REPO / "eval" / "holdout_v4_generation"


def _probs():
    raw = subprocess.run(
        ["git", "show",
         f"{AUDIT_BRANCH}:audit/holdout_v4/holdout_v4_problems.json"],
        capture_output=True, text=True, cwd=REPO)
    assert raw.returncode == 0
    return {p["problem_id"]: p
            for p in json.loads(raw.stdout)["problems"]}


def _answer(pid):
    return json.loads((GEN / f"{pid}.json").read_text(
        encoding="utf-8"))["a1_answer"]


# --- the class bind (AM29 D1) ---------------------------------------

@pytest.mark.parametrize("pid,fires", [
    ("HO4-04-glass-furnace-crown-drip", True),
    ("HO4-05-blade-root-bolt-fatigue", True),
    ("HO4-02-geomembrane-stress-crack", False),
    ("HO4-01-esp-back-corona", False),
    ("HO4-06-ro-silica-scaling", False),
])
def test_class_bind_matches_auditor_verdict(pid, fires):
    r = scan_allowed_measures_class(_probs()[pid], _answer(pid))
    assert bool(r.get("ALLOWED_MEASURE_TYPE_OUTSIDE")) is fires, r


def test_limit_direction_fires_on_cycling_to_heal():
    r = scan_allowed_measures_class(
        _probs()["HO4-03-nas-battery-seal"],
        _answer("HO4-03-nas-battery-seal"))
    assert r.get("LIMIT_DIRECTION_VIOLATION"), r
    assert not r.get("ALLOWED_MEASURE_TYPE_OUTSIDE")


def test_class_bind_unseen_vocabulary():
    # a synthetic constraint whose vocabulary appears in NO dev list:
    # param-exhaustive set in unseen words -> a device row fires
    prob = {"constraint": "no rebuild this season; allowed measures: "
            "injection-pressure recipe retuning or cure-cycle dwell "
            "interval retuning only"}
    hardware_answer = (
        "IMPLEMENTATION BILL —\n"
        "- (b) platen-heat extractor assembly, bolted to the press "
        "frame\n"
        "- (c) press schedule unchanged")
    r = scan_allowed_measures_class(prob, hardware_answer)
    assert r.get("ALLOWED_MEASURE_TYPE_OUTSIDE"), r
    tuning_answer = (
        "IMPLEMENTATION BILL —\n"
        "- (a) existing press and platens, as-is\n"
        "- (c) procedure: retune injection-pressure recipe to the "
        "lower band; shorten cure-cycle dwell interval")
    assert scan_allowed_measures_class(prob, tuning_answer) == {}


def test_class_bind_physical_set_admits_actuation():
    # a physical permitted class admits its actuation equipment
    prob = {"constraint": "allowed measures: corrosive-inhibitor "
            "dose selection or bleed-stream valve trim change only"}
    answer = ("IMPLEMENTATION BILL —\n"
              "- (b) standard inhibitor dosing pump, as-sold")
    assert scan_allowed_measures_class(prob, answer) == {}


# --- the direction bind (AM29 D2, F43) ------------------------------

@pytest.mark.parametrize("pid", [
    "HO4-02-geomembrane-stress-crack",
    "HO4-03-nas-battery-seal",
])
def test_direction_bind_fires_on_inverted_rows(pid):
    r = scan_physics_direction(_probs()[pid], _answer(pid))
    assert r.get("PHYSICS_DIRECTION_UNSTATED"), r


def test_direction_bind_clean_on_structured_statement():
    prob = {"failure": "pump wear from abrasive particles",
            "constraint": "allowed measures: install a separator or "
                          "adjust flow only",
            "question_type": "intervention-proposal"}
    good = (
        "NOVELTY STATEMENT (INTERVENTION) — install a hydrocyclone "
        "separator upstream of the pump.\n"
        "PHYSICS CHECK — removes abrasive particles ahead of the "
        "pump; magnitude verification: 80% cut size reduction.\n"
        "DIRECTION-OF-EFFECT: driving variable = abrasive particle "
        "loading at the pump inlet; the separator reduces it by 80%, "
        "which lowers the wear rate that drives the failure.\n"
        "IMPLEMENTATION BILL — (a) existing pump; (b) hydrocyclone "
        "separator unit, as-sold.")
    assert scan_physics_direction(prob, good) == {}


def test_direction_bind_driver_as_remedy():
    # the failure text names the driver; the mechanism proposes it
    prob = {"failure": "thermal cycling cracks the glass seal",
            "constraint": "allowed measures: temperature-window "
                          "retuning only"}
    bad = ("NOVELTY STATEMENT (INTERVENTION) — a thermal cycling "
           "schedule that alternates setpoints to heal the seal.\n"
           "PHYSICS CHECK — crystallization heals microcracks.\n"
           "DIRECTION-OF-EFFECT: driving variable = thermal cycling; "
           "the mechanism adds more cycling.\n"
           "IMPLEMENTATION BILL — (a) existing heater; (c) schedule.")
    r = scan_physics_direction(prob, bad)
    assert r.get("DRIVER_AS_REMEDY"), r


# --- R35 pins (AM33 D2/D3) on committed holdout-v5 bytes -------------

V5_PACKET = REPO / "eval" / "holdout_v5_problems.json"
V5_ROWS = REPO / "eval" / "pairs" / "holdout_v5_generation"


def _v5_probs():
    d = json.loads(V5_PACKET.read_text(encoding="utf-8"))
    rows = d.get("rows") or d.get("problems") or []
    return {r["problem_id"]: (r.get("problem") or r) for r in rows}


def _v5_row(pid):
    return json.loads((V5_ROWS / f"{pid}.json").read_text(
        encoding="utf-8"))


def test_d2_actuation_device_pin_fires_on_HO5_05():
    # AM33 D2 accept: the pin fires on the committed solenoid-valve
    # bytes (the timer-controlled valve was laundered into a permitted
    # duty-cycle change in the v5 run)
    probs = _v5_probs()
    row = _v5_row("HO5-05-gearbox-oil-foaming")
    out = scan_allowed_measures_class(
        probs["HO5-05-gearbox-oil-foaming"], row["a1_answer"])
    assert out.get("ACTUATION_DEVICE_AS_MEASURE"), out
    assert "solenoid" in out["ACTUATION_DEVICE_AS_MEASURE"][0]


def test_d2_pin_preserves_dose_pump_precedent():
    # the documented precedent: dose selection admits the dosing pump
    prob = {"constraint": "allowed measures: dose selection, filter "
                          "setpoint retuning only",
            "failure": "particle breakthrough"}
    answer = (
        "NOVELTY STATEMENT (INTERVENTION) — retune the dose selection "
        "curve and install a dosing pump on the existing line.\n"
        "IMPLEMENTATION BILL — (b) dosing pump, as-sold.")
    out = scan_allowed_measures_class(prob, answer)
    assert not out.get("ACTUATION_DEVICE_AS_MEASURE"), out


def test_d3_direction_arithmetic_pin_fires_on_HO5_06():
    # AM33 D3 accept: added thermal holds vs a claimed creep-integral
    # reduction — the sign is arithmetic and the compensation is
    # unquantified, so the pin fires
    probs = _v5_probs()
    row = _v5_row("HO5-06-vacuum-furnace-hotzone-sag")
    out = scan_physics_direction(
        probs["HO5-06-vacuum-furnace-hotzone-sag"], row["a1_answer"])
    assert out.get("DIRECTION_INVERTED_ARITHMETIC"), out
    assert "600" in out["DIRECTION_INVERTED_ARITHMETIC"][0]
    assert "1000" in out["DIRECTION_INVERTED_ARITHMETIC"][0]


def test_d3_quantified_compensation_is_typed_not_fired():
    # when the answer quantifies the relief kinetics, the net sign is
    # not machine-decidable — typed for the auditor, never fired
    prob = {"constraint": "allowed measures: ramp schedule retuning "
                          "only", "failure": "hot-zone sag"}
    answer = (
        "NOVELTY STATEMENT (INTERVENTION) — add a 30-minute hold at "
        "900C during heating to allow stress relaxation and reduce "
        "cumulative creep strain.\n"
        "PHYSICS CHECK — DIRECTION-OF-EFFECT: driving variable = "
        "cumulative creep strain; the hold lowers stress from 60 MPa "
        "before to 25 MPa after (activation energy Q=380 kJ/mol "
        "assumed), so the creep integral decreases.\n"
        "DIRECTION-OF-EFFECT: the hold cuts cumulative creep strain.\n"
        "IMPLEMENTATION BILL — (a) schedule change only.")
    out = scan_physics_direction(prob, answer)
    assert out.get("DIRECTION_CONTESTABLE_TYPED"), out
    assert not out.get("DIRECTION_INVERTED_ARITHMETIC"), out


def test_r35_pins_zero_false_positives_on_other_v5_rows():
    probs = _v5_probs()
    fp = []
    for f in sorted(V5_ROWS.glob("HO5-*.json")):
        pid = f.stem
        if pid.startswith(("HO5-05", "HO5-06")):
            continue
        row = json.loads(f.read_text(encoding="utf-8"))
        c = scan_allowed_measures_class(probs[pid], row["a1_answer"])
        d = scan_physics_direction(probs[pid], row["a1_answer"])
        for fam in ("ACTUATION_DEVICE_AS_MEASURE",
                    "DIRECTION_INVERTED_ARITHMETIC"):
            if c.get(fam) or d.get(fam):
                fp.append((pid, fam))
    assert not fp, fp
