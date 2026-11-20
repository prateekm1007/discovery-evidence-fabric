"""tests/test_physics_library_checks.py — D2 (auditor direction 2,
claim c-0128): the heavier physics libraries run as ENGINE-NATIVE
checks with the sign-of-computed-result contract, typed
UNAVAILABLE/REFUSED verdicts, and the unit/claim discipline.
Every engine-imported NOTICE library (cantera, fluids, CoolProp, ht)
has >=1 test here (the auditor's direction-2 acceptance test)."""
from __future__ import annotations

from discovery_fabric.engine import physics_library_checks as plc


# --- cantera: the computed equilibrium direction -------------------
def test_equilibrium_T_direction_consistent():
    r = plc.check_equilibrium_direction({
        "kind": "T_direction", "mechanism": "gri30.yaml",
        "X": {"CO2": 0.2, "H2": 0.2, "CO": 0.1, "H2O": 0.5},
        "target": "CO", "source": "CO2",
        "T_low": 800.0, "T_high": 1200.0, "P": 101325.0,
        "claimed": "increases"})
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "improves"
    assert r["detail"]["computed"] == "increases"


def test_equilibrium_T_direction_inverted():
    """The claimed direction INVERTED vs the computed sign must come
    out 'worsens' — the check can fail a claim, not just pass it."""
    r = plc.check_equilibrium_direction({
        "kind": "T_direction", "mechanism": "gri30.yaml",
        "X": {"CO2": 0.2, "H2": 0.2, "CO": 0.1, "H2O": 0.5},
        "target": "CO", "source": "CO2",
        "T_low": 800.0, "T_high": 1200.0, "P": 101325.0,
        "claimed": "decreases"})
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "worsens"


# --- fluids: the computed pipe pressure-drop direction --------------
def test_pipe_drop_diameter_reduction():
    r = plc.check_pipe_pressure_drop({
        "rho": 998.0, "mu": 1e-3, "L": 100.0, "D": 0.05, "v": 2.0,
        "D_new": 0.04, "eps": 1e-5, "claimed": "increases"})
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "improves"
    assert r["detail"]["dp_new"] > r["detail"]["dp_base"]


def test_pipe_drop_refused_on_bad_claim():
    r = plc.check_pipe_pressure_drop({
        "rho": 998.0, "mu": 1e-3, "L": 100.0, "D": 0.05, "v": 2.0,
        "claimed": "maybe"})
    assert r["verdict"] == "REFUSED"


# --- CoolProp: the computed property direction ----------------------
def test_coolprop_density_direction():
    r = plc.check_fluid_property_direction({
        "fluid": "Water", "prop": "D", "P": 101325.0,
        "T_a": 300.0, "T_b": 350.0, "claimed": "decreases"})
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "improves"


def test_coolprop_refused_on_unknown_fluid():
    r = plc.check_fluid_property_direction({
        "fluid": "Unobtainium404", "prop": "D", "P": 101325.0,
        "T_a": 300.0, "T_b": 350.0, "claimed": "decreases"})
    assert r["verdict"] == "REFUSED"


# --- ht: the computed convective-htc direction ----------------------
def test_htc_velocity_direction():
    r = plc.check_convective_htc_direction({
        "v": 1.0, "v_new": 3.0, "D": 0.02, "k": 0.6, "mu": 1e-3,
        "rho": 998.0, "cp": 4180.0, "claimed": "increases"})
    assert r["verdict"] == "RUN"
    assert r["direction_of_effect"] == "improves"
    assert r["detail"]["htc_new"] > r["detail"]["htc_base"]


# --- the typed-UNAVAILABLE path (a missing library never
#     degrades into a fabricated number — the physics_checks
#     contract, enforced here) ----------------------------------------
def test_unavailable_when_library_absent(monkeypatch):
    monkeypatch.setattr(plc, "_lib", lambda name: None)
    r = plc.check_pipe_pressure_drop({
        "rho": 998.0, "mu": 1e-3, "L": 100.0, "D": 0.05, "v": 2.0,
        "claimed": "increases"})
    assert r["verdict"] == "UNAVAILABLE"
    assert r["direction_of_effect"] == "unavailable"
    r2 = plc.check_equilibrium_direction({"claimed": "increases"})
    assert r2["verdict"] == "UNAVAILABLE"
