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
