#!/usr/bin/env python3
"""F40 pin (AM28 D4): the corrected bench-p10 bill must not name an
ionoplast structural interlayer as a sodium/ion barrier, and must
name its barrier exemplar as a stocked product class with a stated
property basis (the auditor's F40 diagnosis: SentryGlas is an
ionoplast structural interlayer, not an ion-barrier product — the
class exists, e.g. SiOx-coated PET; the c-0030 machine re-draw chose
a sulfonated-polyethylene separator film, likewise a stocked class).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROW = REPO / "eval" / "pairs" / "r30_v75_converted" / \
    "bench-p10-pv-pid.json"


def _answer():
    return json.loads(ROW.read_text(encoding="utf-8"))["a1_answer"]


def test_no_ionoplast_named_as_barrier():
    a = _answer().lower()
    assert "sentryglas" not in a, "F40: SentryGlas must not appear"
    assert "ionoplast" not in a, "F40: ionoplast must not appear"


def test_barrier_exemplar_is_a_stocked_class_with_basis():
    a = _answer()
    # a named barrier film class with a stated property/mechanism basis
    assert ("sulfonated polyethylene" in a.lower()
            or "siox" in a.lower()), \
        "the barrier exemplar must be a stocked film class"
    assert "as-sold" in a or "commercial" in a.lower() or \
        "battery-grade" in a.lower(), \
        "the exemplar must be stated as sold/stocked"
