#!/usr/bin/env python3
"""F41 regression pins (AM28 D4): size/pressure-class and sensor
physics designations are ENGINEERING CLASSES, not brand markers —
the auditor's false-positive set (a conformant bill "3-way ball
valve, DN80 PN16" flagged by the model-marker net). Real brand/model
markers and named custom variants still flag.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r26_catalog_scan import scan_named_variant  # noqa: E402


def test_size_and_pressure_classes_are_clean():
    bill = ("Implementation bill — (a) 3-way ball valve, DN80 PN16; "
            "(b) commercial NTC 10k probe; (c) standard DIN flange, "
            "DN15; (d) PT100 RTD, class B.")
    assert scan_named_variant(bill) == {}, scan_named_variant(bill)


def test_real_brand_model_still_flags():
    bill = ("IMPLEMENTATION BILL — (a) Acme Pumps model XYZ-123, "
            "installed inline")
    assert "NAMED_VARIANT" in scan_named_variant(bill)


def test_custom_variant_still_flags():
    bill = ("IMPLEMENTATION BILL — (a) custom-blend epoxy gasket, cut "
            "to flange")
    assert "NAMED_VARIANT" in scan_named_variant(bill)


def test_specialty_variant_still_flags():
    bill = ("IMPLEMENTATION BILL — (a) specialty high-temp variant of "
            "the standard gasket")
    assert "NAMED_VARIANT" in scan_named_variant(bill)
