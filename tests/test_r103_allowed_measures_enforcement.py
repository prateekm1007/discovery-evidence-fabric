#!/usr/bin/env python3
"""tests/test_r103_allowed_measures_enforcement.py — the R103 (claim
c-0117, AM89 directive 1) CI fixtures: the per-problem permitted-
measure-set enforcement.

THE PERMANENT FIXTURE (the auditor's directive): HO14-12 recirculation
— the burned-v14 committed bytes MUST fire MEASURE_NOT_IN_PERMITTED_SET
(the auditor-verified sole v14 allowed-measures violation: the
recirculation-flow/VFD scour outside {pH/caustic, air-to-water,
water-temperature}).

THE FALSE-KILL PINS: the 14 conformant v14 intervention rows stay
silent (auditor-scored 0 violations on them), the v4 pinned bytes stay
in their pinned states (the AM29 battery covers the old legs; this
battery pins the NEW leg), and the corpus-verified catches (v3 HO3-05
auditor-verified; the two v7 pre-scan-era hardware installs) fire.

Read-only: the burned rows are calibration material (the c-0113
discipline); zero generation.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine.permitted_measures import (  # noqa: E402
    enforce_answer, parse_permitted_set, collect_measure_rows)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V14_ROWS = REPO / "eval" / "holdout_v14_generation" / "rows"


def _v14_problems():
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:audit/holdout_v14/"
         "holdout_v14_problems.json"],
        capture_output=True, text=True, cwd=REPO)
    assert raw.returncode == 0
    return {p["problem_id"]: p
            for p in json.loads(raw.stdout)["problems"]}


def _v14_answer(pid):
    return json.loads((V14_ROWS / f"{pid}.json").read_text(
        encoding="utf-8"))["a1_answer"]


# --- the permanent fixture (the AM89 defect byte) -----------------------

def test_ho14_12_recirculation_outside_permitted_set_fires():
    """HO14-12: the mechanism class 'High-Head Recirculation Scour' is
    out-of-set and the bill's recirculation-flow/VFD + scour-schedule
    rows are out-of-set measures — the typed KILL, from committed
    bytes (the R102 verdict's named defect)."""
    probs = _v14_problems()
    r = enforce_answer(probs["HO14-12-ammonia-strip"],
                       _v14_answer("HO14-12-ammonia-strip"))
    kills = r.get("MEASURE_NOT_IN_PERMITTED_SET")
    assert kills, r
    joined = " ".join(kills)
    assert "Recirculation" in joined or "Scouring" in joined, kills


def test_ho14_12_in_set_row_not_killed():
    """The A/W row (Row 2) is INSIDE the permitted set (air-to-water
    ratio is a permitted variable) — its inversion is the direction
    bind's finding (test_r103_stripping_direction_bind.py), never this
    scan's."""
    probs = _v14_problems()
    r = enforce_answer(probs["HO14-12-ammonia-strip"],
                       _v14_answer("HO14-12-ammonia-strip"))
    kills = " ".join(r.get("MEASURE_NOT_IN_PERMITTED_SET", []))
    assert "Air-to-Water Ratio" not in kills, kills


# --- the false-kill pins (the 14 conformant rows) -----------------------

@pytest.mark.parametrize("pid", [
    "HO14-01-coag-floc-jar", "HO14-02-daf-whitewater",
    "HO14-03-gac-exhaustion", "HO14-04-ix-resin-fouling",
    "HO14-05-uv-lamp-sleeve", "HO14-06-ozone-transfer",
    "HO14-07-chlorine-dbp", "HO14-08-cwetland-clog",
    "HO14-09-anammox-nitrite", "HO14-10-ebpr-gao",
    "HO14-11-struvite-scale", "HO14-13-thp-cambi",
    "HO14-14-trickling-filter", "HO14-15-sbr-settle",
])
def test_conformant_v14_rows_stay_silent(pid):
    """The auditor verified 0 allowed-measures violations on the other
    14 intervention rows — the new leg must stay silent on every one
    (the anaphora cases included: HO14-14's High-flow/Low-flow value
    rows ride their in-set recirculation class)."""
    probs = _v14_problems()
    r = enforce_answer(probs[pid], _v14_answer(pid))
    assert not r.get("MEASURE_NOT_IN_PERMITTED_SET"), (pid, r)


# --- the corpus-verified catches ---------------------------------------

def test_v3_ho3_05_chelating_resin_fires():
    """v3 HO3-05: the auditor-VERIFIED v3 violation (chelating resin
    outside the allowed list) — the new leg catches it from committed
    bytes."""
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:audit/holdout_v3/"
         "holdout_v3_problems.json"],
        capture_output=True, text=True, cwd=REPO)
    prob = {p["problem_id"]: p for p in
            json.loads(raw.stdout)["problems"]}[
        "HO3-05-immersion-fluid-degradation"]
    ans = json.loads((REPO / "eval" / "holdout_v3_generation" /
                      "HO3-05-immersion-fluid-degradation.json")
                     .read_text(encoding="utf-8"))["a1_answer"]
    assert enforce_answer(prob, ans).get(
        "MEASURE_NOT_IN_PERMITTED_SET")


# --- the parse + collector mechanics -----------------------------------

def test_permitted_set_parse_exhaustive_only():
    p = parse_permitted_set(
        "no redesign; allowed measures: pH dosing retuning or "
        "temperature setpoint retuning only")
    assert p["has_set"] and p["only"]
    assert {"chemistry_dosing", "ph_alkalinity", "temperature"} <= \
        p["substantive_classes"]
    # a non-exhaustive 'allowed' hint is advisory — silent
    q = parse_permitted_set("no redesign; allowed measures include "
                            "dosing changes")
    assert not q["has_set"]


def test_list_typed_constraint_parse():
    """The v7 convention: user_variables as a LIST — the repr must
    never leak into the parse (the R103 calibration catch)."""
    p = parse_permitted_set(
        ["no redesign; allowed measures: defrost-intiation logic and "
         "interval retuning, evaporator fan-speed setpoint retuning, "
         "or door/curtain and loading procedure only",
         "device of record: industrial spiral freezer"])
    assert p["has_set"]
    assert all("device of record" not in it for it in p["items"]), \
        p["items"]
    assert {"procedure_schedule", "speed_agitation"} <= \
        p["substantive_classes"]


def test_measure_row_collector_skips_substructure():
    ans = ("IMPLEMENTATION BILL\n"
           "MECHANISM CLASS: pH Setpoint Retuning\n"
           "| Item | Description | Procurement Tag |\n"
           "| :--- | :--- | :--- |\n"
           "| **1** | **pH Setpoint Retuning:** Shift the band. | "
           "**(c)** | Parameter. |\n"
           "*   *Description:* Shift the band using existing pumps.\n"
           "*   Row 2: **Scheduling the Scouring Phase.**\n"
           "\n*EXECUTABLE TEST**\n"
           "1. Baseline: run 48 hours.\n")
    rows = collect_measure_rows(ans)
    joined = " | ".join(rows)
    assert "pH Setpoint Retuning" in joined        # the measure row
    assert "Scheduling the Scouring" in joined     # the measure row
    assert "Description:" not in joined            # sub-row skipped
    assert "Item | Description" not in joined      # table header
    assert ":---" not in joined                    # separator skipped
    assert "Baseline" not in joined                # post-heading scope


def test_modifier_never_rescues_out_of_set_object():
    """The PARAMETER_TUNING modifier (setpoint/retuning) never rescues
    an out-of-set substantive object: 'Adjustment of Recirculation
    Pump Speed/VFD Setpoint' shares the word setpoint with the
    permitted items and is still outside (the HO14-12 Row-1 class)."""
    prob = {"user_variables": "no tower redesign; allowed measures: "
             "pH/caustic chemistry dosing retuning, air-to-water "
             "ratio setpoint retuning, or water-temperature setpoint "
             "retuning only"}
    ans = ("IMPLEMENTATION BILL\n"
           "MECHANISM CLASS: High-Head Recirculation Scour\n"
           "- Row 1: **Adjustment of Recirculation Pump Speed/VFD "
           "Setpoint.** (c)\n")
    r = enforce_answer(prob, ans)
    assert r.get("MEASURE_NOT_IN_PERMITTED_SET"), r


def test_no_bill_section_is_silent():
    assert enforce_answer(
        {"user_variables": "allowed measures: dosing only"},
        "no bill here") == {}
