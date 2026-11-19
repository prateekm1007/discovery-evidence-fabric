#!/usr/bin/env python3
"""tests/test_r103_stripping_direction_bind.py — the R103 (claim
c-0117, AM89 directive 2) CI fixtures: the ammonia-stripping
direction/premise bind.

Physics basis (the classical stripper design basis, typed in the
engine module): RAISE pH (NH4+ <=> NH3 + H+, pKa ~ 9.25 at 25 C),
RAISE air-to-water ratio (stripping factor S = Kya*G/L), RAISE
temperature (van 't Hoff: exothermic dissolution -> solubility falls)
all IMPROVE stripping. LOWERING A/W or premising 'high pH inhibits
stripping' are typed INVERTED — the R102 verdict's HO14-12 defect
class.

Fixtures: the burned-v14 committed byte fires BOTH codes; the 29 other
v14 rows stay silent; conformant synthetics stay silent; the domain
gate keeps non-ammonia problems silent.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.stripping_direction import (  # noqa: E402
    scan_stripping_direction, is_ammonia_stripping)
from discovery_fabric.engine import physics_checks as pc  # noqa: E402

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


def test_ho14_12_committed_byte_fires_both_codes():
    probs = _v14_problems()
    p = probs["HO14-12-ammonia-strip"]
    ans = json.loads((V14_ROWS / "HO14-12-ammonia-strip.json")
                     .read_text(encoding="utf-8"))["a1_answer"]
    assert is_ammonia_stripping(p)
    r = scan_stripping_direction(p, ans)
    assert r.get("STRIPPING_DIRECTION_INVERTED"), r   # lowered A/W
    assert r.get("STRIPPING_PREMISE_INVERTED"), r     # high-pH-inhibits


def test_all_other_v14_rows_silent():
    probs = _v14_problems()
    for fp in sorted(V14_ROWS.glob("*.json")):
        pid = fp.stem
        if pid == "HO14-12-ammonia-strip":
            continue
        ans = json.loads(fp.read_text(encoding="utf-8"))["a1_answer"]
        assert scan_stripping_direction(probs[pid], ans) == {}, pid


CONFORMANT = (
    "NOVELTY STATEMENT (INTERVENTION)\n"
    "MECHANISM CLASS: Caustic-Boost Countercurrent Stripping\n"
    "The intervention RAISES the packed tower feed pH from 8.5 to 11.0 "
    "via the existing caustic dosing pumps, shifting the NH4+ <=> NH3 "
    "equilibrium toward free NH3, and RAISES the air-to-water ratio "
    "from 2000:1 to 3000:1 by increasing blower flow, steepening the "
    "partial-pressure gradient.\n\n"
    "PHYSICS CHECK\n"
    "At pH 11.0 the free NH3 fraction is ~98% (pKa 9.25 at 25 C); the "
    "stripping factor S = Kya*G/L rises linearly with the gas rate; "
    "warming the feed to 35 C further cuts NH3 solubility (van 't "
    "Hoff).\n\n"
    "IMPLEMENTATION BILL\n"
    "1. **Caustic dose setpoint retuning:** raise the pH band to "
    "10.8-11.2. (c)\n"
    "2. **Blower flow setpoint retuning:** raise A/W to 3000:1. (c)\n")


def test_conformant_raise_all_stays_silent():
    p = _v14_problems()["HO14-12-ammonia-strip"]
    assert scan_stripping_direction(p, CONFORMANT) == {}


def test_domain_gate_non_ammonia_silent():
    p = {"device": "cooling tower scale control",
         "failure": "calcium carbonate scaling",
         "question": "Propose mitigation."}
    assert scan_stripping_direction(
        p, CONFORMANT.replace("NH3", "CO2")) == {}
    assert not is_ammonia_stripping(p)


def test_lowered_aw_synthetic_fires():
    p = _v14_problems()["HO14-12-ammonia-strip"]
    ans = CONFORMANT.replace(
        "RAISES the air-to-water ratio from 2000:1 to 3000:1 by "
        "increasing blower flow, steepening the partial-pressure "
        "gradient.",
        "LOWERS the air-to-water ratio to maximize liquid film "
        "contact time and carry-over capacity.")
    r = scan_stripping_direction(p, ans)
    assert r.get("STRIPPING_DIRECTION_INVERTED"), r


def test_high_ph_inhibits_premise_synthetic_fires():
    p = _v14_problems()["HO14-12-ammonia-strip"]
    ans = CONFORMANT.replace(
        "shifting the NH4+ <=> NH3 equilibrium toward free NH3,",
        "exploiting the ammonia stripping inhibition at high pH,")
    r = scan_stripping_direction(p, ans)
    assert r.get("STRIPPING_PREMISE_INVERTED"), r


# --- the computed ride-along legs (physics_checks registry) -------------

def test_ammonia_free_fraction_raises_with_ph():
    r = pc.ammonia_free_fraction(ph=11.0, ph_ref=8.5)
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "improves"
    assert r["value"] > 0.9  # pH 11: ~98% free NH3


def test_vant_hoff_solubility_falls_with_temperature():
    r = pc.nh3_henry_ratio(t1_degC=25.0, t2_degC=60.0)
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "improves"   # less soluble
    assert r["value"] < 0.9


def test_naoh_guard_catches_impossible_concentration():
    """The 50-M class (the HO14-04 committed byte '50 M NaOH' — >1.4x
    the ~20.6 M saturation at 25 C; the 50%-w/w vs 50-M confusion)."""
    r = pc.naoh_solubility_guard(concentration_mol_l=50.0)
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "worsens"
    assert r["value"] > 1.0
    assert "SATURATION_EXCEEDED" in r["detail"]


def test_naoh_guard_feasible_concentration_neutral():
    r = pc.naoh_solubility_guard(concentration_mol_l=19.0)
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "neutral"
    assert r["value"] <= 1.0


def test_degenerate_inputs_refused():
    assert pc.ammonia_free_fraction(ph=15.0)["verdict"] == "REFUSED"
    assert pc.nh3_henry_ratio(25.0, -300.0)["verdict"] == "REFUSED"
    assert pc.naoh_solubility_guard()["verdict"] == "REFUSED"


def test_failure_class_router_knows_the_new_classes():
    assert pc.classify_failure(
        "poor ammonia removal efficiency in the stripping tower") \
        == "ammonia_stripping"
    assert pc.classify_failure("caustic dosing pump degradation") \
        == "caustic_dosing"
    assert "ammonia_free_fraction" in pc.CHECKS_BY_FAILURE_CLASS[
        "ammonia_stripping"]
