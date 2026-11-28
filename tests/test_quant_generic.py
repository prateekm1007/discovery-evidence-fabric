"""R145S1B — the class-generic quant layer tests (R144-F1)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation import quant_generic as qg  # noqa: E402


def test_every_failure_class_has_a_path():
    from discovery_fabric.generation import mechanism_map as mm
    covered = set(qg.CLASS_GENERIC_FORMULAS)
    specific_classes = set()
    for fc, entries in mm.MECHANISM_MAP.items():
        # a failure class is covered if ANY of its mechanism classes
        # has a specific formula
        from discovery_fabric.generation import quant_test as qt
        if any(m["mech"] in qt.FORMULAS for m in entries):
            specific_classes.add(fc)
    for fc in mm.FAILURE_CLASSES:
        assert fc in covered or fc in specific_classes, \
            f"{fc} has neither a specific nor a class-generic formula"


def test_fatigue_generic_computes():
    p = qg.fatigue_life_ratio("The design stress is 350 MPa at the "
                              "gauge corner; peening cuts the amplitude.")
    assert p["status"] == "computed" and "N ratio" in p["predicted_value"]
    p2 = qg.fatigue_life_ratio("no numbers here")
    assert p2["status"] == "insufficient_parameters"
    assert p2["measurement_plan"]


def test_vibration_generic_computes():
    p = qg.vibration_transmissibility("a tuned mass at 45 Hz away from "
                                      "the 63 Hz forcing")
    assert p["status"] == "computed" and "T =" in p["predicted_value"]


def test_dielectric_generic_computes():
    p = qg.dielectric_margin("12 kV across a 4 mm creepage gap")
    assert p["status"] == "computed"
    assert float(p["predicted_value"].split("=")[1].split()[0]) == 3.0


def test_dispatch_route_generic():
    p = qg.emit_prediction_generic("fatigue_crack",
                                   "350 MPa amplitude, peened")
    assert p["status"] == "computed"
    assert p["route"].startswith("class-generic") or \
        p["route"].startswith("specific")


def test_dispatch_route_specific():
    p = qg.emit_prediction_generic(
        "abrasion_erosion",
        "surface hardening from 200 HV to 400 HV by nitriding")
    assert p["status"] == "computed"
    assert p["route"].startswith("specific:surface_hardening")


def test_dispatch_typed_never_silent():
    p2 = qg.emit_prediction_generic("fatigue_crack", "no numbers")
    assert p2["status"] == "insufficient_parameters"
    assert p2["route"] == "typed-missing" or "measurement_plan" in p2
