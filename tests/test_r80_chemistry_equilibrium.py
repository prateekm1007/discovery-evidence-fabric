#!/usr/bin/env python3
"""R80 CI-wired acceptance tests for the COMPUTED-equilibrium direction
check (scripts/r80_chemistry_equilibrium.py — Cantera BSD-3, patterns per
AM81 ChemMCP/CACTUS). Deterministic, zero-LLM, zero-network; every expected
sign was COMPUTED FIRST (scripts/r80_chem_sanity.py) and only then baked
into these tests (never assumed). Fixtures use ONLY cantera-shipped
mechanisms (gri30.yaml) — no invented thermo data. Art. 22: fixtures prove
MECHANICS; the generation-side wiring is adoption-gated (the c-0106 lane
owns the frozen-machine work)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "r80chem", REPO / "scripts" / "r80_chemistry_equilibrium.py")
r80chem = importlib.util.module_from_spec(spec)
sys.modules["r80chem"] = r80chem
spec.loader.exec_module(r80chem)

ATM = 101325.0
SMR_X = {"CH4": 0.10, "H2O": 0.10, "N2": 1.0}
DIS_X = {"CO": 0.01, "O2": 0.006, "N2": 1.0}


# ------------------------------------------------ L1 oxidant excess (CO->CO2)
def _l1_claim(direction):
    c = dict(r80chem._CO_CO2_CLAIM)
    c["claimed_direction"] = direction
    return c


def test_oxidant_excess_reduction_claim_is_inverted():
    # COMPUTED FIRST: CO2/CO ratio RISES (2.53e6 -> 1.63e7) with excess O2.
    v = r80chem.verify_claim(_l1_claim("decrease"))
    assert v["verdict"] == "INVERTED", v
    assert v["computed_direction"] == "up"


def test_oxidant_excess_increase_claim_is_consistent():
    v = r80chem.verify_claim(_l1_claim("increase"))
    assert v["verdict"] == "CONSISTENT", v


# --------------------------------------------------- L2 SMR T-up (CO)
def test_T_up_endothermic_forward_is_computed_up():
    # COMPUTED FIRST: CO +45.8% from 900K -> 1600K (rich SMR mix).
    v = r80chem.verify_claim({
        "mechanism": "gri30.yaml", "base_X": SMR_X,
        "target": "CO", "source": None, "claimed_direction": "increase",
        "step": {"variable": "temperature", "T_low": 900.0,
                 "T_high": 1600.0, "P": ATM}})
    assert v["verdict"] == "CONSISTENT", v
    assert v["computed_direction"] == "up"
    v2 = r80chem.verify_claim({
        "mechanism": "gri30.yaml", "base_X": SMR_X,
        "target": "CO", "source": None, "claimed_direction": "decrease",
        "step": {"variable": "temperature", "T_low": 900.0,
                 "T_high": 1600.0, "P": ATM}})
    assert v2["verdict"] == "INVERTED", v2


# ------------------------------------- L3 dissociation T-up (CO and CO2)
def test_T_up_exothermic_dissociation_legs():
    # COMPUTED FIRST: CO up ~1500x, CO2 down ~24% from 1500K -> 2300K.
    co = r80chem.verify_claim({
        "mechanism": "gri30.yaml", "base_X": DIS_X,
        "target": "CO", "source": None, "claimed_direction": "increase",
        "step": {"variable": "temperature", "T_low": 1500.0,
                 "T_high": 2300.0, "P": ATM}})
    assert co["verdict"] == "CONSISTENT", co
    co2 = r80chem.verify_claim({
        "mechanism": "gri30.yaml", "base_X": DIS_X,
        "target": "CO2", "source": None, "claimed_direction": "increase",
        "step": {"variable": "temperature", "T_low": 1500.0,
                 "T_high": 2300.0, "P": ATM}})
    assert co2["verdict"] == "INVERTED", co2


# ------------------------------------------------------------ flat typing
def test_flat_signal_is_typed_unverifiable():
    # COMPUTED FIRST: H2O 1200 -> 1201K rel change -0.00006% (well below 2%).
    v = r80chem.verify_claim({
        "mechanism": "gri30.yaml", "base_X": {"H2": 0.01, "O2": 0.005,
                                              "N2": 1.0},
        "target": "H2O", "source": None, "claimed_direction": "increase",
        "step": {"variable": "temperature", "T_low": 1200.0,
                 "T_high": 1201.0, "P": ATM}})
    assert v["verdict"] == "UNVERIFIABLE", v


def test_fail_open_on_bad_claim():
    assert r80chem.verify_claim({"mechanism": "gri30.yaml"})["verdict"] \
        == "UNVERIFIABLE"
    bad = _l1_claim("increase")
    bad["step"] = {"variable": "pressure"}
    assert r80chem.verify_claim(bad)["verdict"] == "UNVERIFIABLE"


# ---------------------------------------------- conservative prose extractor
def test_prose_inversion_claim_is_computed_inverted():
    text = ("Excess oxygen reduces the formation of CO2 in the flue gas, "
            "so lowering the oxidant share is attractive.")
    out = r80chem.scan_computed_equilibrium_direction(text)
    assert out and out["computed_verdict"] == "INVERTED", out
    assert out["pair"] == ["CO", "CO2"]


def test_prose_consistent_claim_is_computed_consistent():
    text = "Excess oxidant favors the formation of CO2 at this temperature."
    out = r80chem.scan_computed_equilibrium_direction(text)
    assert out and out["computed_verdict"] == "CONSISTENT", out


def test_ambiguous_prose_stays_silent():
    # the registry-scan contract: anything ambiguous stays silent
    assert r80chem.scan_computed_equilibrium_direction(
        "The furnace operates at elevated temperature with several "
        "reactions in competition.") == {}
    assert r80chem.scan_computed_equilibrium_direction(
        "Excess oxygen is fed through the secondary register.") == {}
    assert r80chem.scan_computed_equilibrium_direction(
        "CO2 decreases were observed; the oxidant share was raised.") == {}
    assert r80chem.scan_computed_equilibrium_direction("") == {}


# ------------------------------------------------------ determinism + guards
def test_determinism():
    a = r80chem.verify_claim(_l1_claim("increase"))
    b = r80chem.verify_claim(_l1_claim("increase"))
    assert a["low"] == b["low"] and a["high"] == b["high"]


def test_frozen_baselines_untouched():
    rec = json.loads((REPO / "eval" / "r64_v9_preflight.json").read_text())
    fb = rec["checks"]["freeze_baselines_sha16"]
    for f, expected in fb.items():
        got = hashlib.sha256((REPO / f).read_bytes()).hexdigest()[:16]
        assert got == expected, f"the frozen file {f} MOVED (typed abort)"


def test_module_is_zero_network():
    src = (REPO / "scripts" / "r80_chemistry_equilibrium.py").read_text()
    for banned in ("import socket", "import requests", "import urllib",
                   "import http", "urlopen", "subprocess"):
        assert banned not in src, f"zero-network violation: {banned}"
