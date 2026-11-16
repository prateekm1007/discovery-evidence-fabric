#!/usr/bin/env python3
"""tests/test_v77_bind_controls.py — NEGATIVE CONTROLS for the V7
binds (claim c-0055, the auditor's R40b D3: "a guard fire-tested only
on rows that all violate is untested for false positives").

Pricing bind (scan_duty_cycle_pricing):
  negatives (MUST stay silent, >=3):
    N1 a duty-cycling bill with an OPERATIONAL COST line,
    N2 a duty-cycling bill with a quantified in-prose cost,
    N3 a bill whose duty-cycle mention lives ONLY in the
       falsification-test span (a verification protocol is not the
       intervention),
  positives (MUST fire):
    P1 the committed HO6-03 bill (the auditor's cited unpriced
       circulation cut),
    P2 a synthetic unpriced duty-cycling bill.

Diversity cap (scan_mechanism_template):
  negatives (MUST stay silent, >=3):
    N4 six distinct classes in the histogram,
    N5 a 2-shared set with a DISTINCT third row,
    N6 a same-class second row (count 1 -> 2 is under the cap),
  positives (MUST fire):
    P3 a third row of one class (count 2 -> 3),
    P4 a missing MECHANISM CLASS declaration.

Driver-class lexicon (direction_lexicon_check, D4 semantics):
  negatives (wordform traps MUST stay silent):
    N7 'cyclone' in the failure AND the remedy (a device noun, not
       cycling),
    N8 'charge-sensing' in the remedy with a static-charge failure
       (a measurement, not a charge/discharge cycle),
  positives (MUST fire):
    P5 a thermal-shock remedy against a fatigue/heat-check driver
       (the HO6-02 class, different wordforms, same class),
    P6 the committed HO6-02 bill via the LLM leg is pinned in the
       fire-test (an LLM call — not in this zero-LLM suite); here the
       D5 derivation function is pinned instead.

D5 derivation (_derive_direction):
    P7 SAME -> INVERTED, OPPOSITE -> CORRECT, UNSTATED -> UNCLEAR,
    P8 the reason is assembled from the fields (verdict/reason
       cannot diverge),
    P9 a label/derivation disagreement types DIVERGENT (fail-open,
       disclosed, the derived verdict stays authoritative).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r40_machine_v77 import (  # noqa: E402
    scan_duty_cycle_pricing, scan_mechanism_template,
    direction_lexicon_check, _derive_direction)


def _bill(novelty: str, tail: str = "") -> str:
    return ("NOVELTY STATEMENT (INTERVENTION) — " + novelty
            + ("\n" + tail if tail else ""))


# ---------- pricing bind ----------

N1_PRICED_SECTION = _bill(
    "The remedy duty-cycles the coolant flow between two setpoints "
    "on a fixed schedule.",
    "OPERATIONAL COST: approximately 2.3% conversion throughput per "
    "campaign; the trade nets positive because the fouling rate "
    "falls.")
N2_PRICED_PROSE = _bill(
    "A periodic backflush schedule modulates the feed pump duty "
    "cycle. The schedule costs about 1.5% of hourly throughput, "
    "which the filter life more than repays.")
N3_DUTY_IN_TEST_ONLY = _bill(
    "The remedy converts the deposited surface state in place; the "
    "flow regime is unchanged.",
    "EXECUTABLE TEST — Protocol: duty-cycle the rig at 10 min "
    "intervals to verify the converted state survives cycling.")
P1_COMMITTED_HO6_03 = (REPO / "eval" / "pairs" / "holdout_v6_generation"
                       / "HO6-03-fcc-cyclone-erosion.json")
P2_SYNTHETIC_UNPRICED = _bill(
    "Duty-cycle modulation of the feed rate; periodic rest intervals "
    "let the bed de-fluidize.")

def test_pricing_negatives_stay_silent():
    for name, bill in (("N1", N1_PRICED_SECTION), ("N2", N2_PRICED_PROSE),
                       ("N3", N3_DUTY_IN_TEST_ONLY)):
        got = scan_duty_cycle_pricing(bill)
        assert not got, f"pricing negative control {name} FIRED: {got}"


def test_pricing_positives_still_fire():
    assert scan_duty_cycle_pricing(P2_SYNTHETIC_UNPRICED), (
        "P2 synthetic unpriced duty cycle did not fire")
    assert P1_COMMITTED_HO6_03.exists(), "committed HO6-03 row missing"
    a = json.loads(P1_COMMITTED_HO6_03.read_text(
        encoding="utf-8"))["a1_answer"]
    got = scan_duty_cycle_pricing(a)
    assert got and "UNPRICED_DUTY_CYCLE" in got, (
        "P1 the committed HO6-03 bill (the auditor's cited unpriced "
        "circulation cut) no longer fires")


# ---------- diversity cap ----------

def test_diversity_negatives_stay_silent():
    cls = "MECHANISM CLASS: %s\n"
    six_distinct = _bill(cls % "duty-cycle modulation of a transport "
                         "flow")
    assert not scan_mechanism_template(
        six_distinct, Counter({"surface state conversion": 1,
                               "inventory replacement": 1,
                               "procedure retiming": 1,
                               "flow routing change": 1,
                               "dosing schedule shift": 1,
                               "seal selection": 1}))
    distinct_third = _bill(cls % "surface state conversion")
    assert not scan_mechanism_template(
        distinct_third, Counter({"duty-cycle modulation": 2}))
    second_row = _bill(cls % "inventory replacement procedure")
    assert not scan_mechanism_template(
        second_row, Counter({"inventory replacement procedure": 1})), (
        "N6 the SECOND row of a class must stay under the cap")


def test_diversity_positives_still_fire():
    third_row = _bill("MECHANISM CLASS: duty-cycle modulation\nbody")
    got = scan_mechanism_template(
        third_row, Counter({"duty-cycle modulation": 2}))
    assert got and "MECHANISM_TEMPLATE_MONOCULTURE" in got, (
        "P3 a third row of one class must fire the cap")
    no_decl = _bill("some remedy with no declaration")
    got = scan_mechanism_template(no_decl, Counter())
    assert got and "MECHANISM_CLASS_UNSTATED" in got, (
        "P4 a missing declaration must fire")


# ---------- driver-class lexicon (D4 semantics) ----------

def test_lexicon_wordform_traps_stay_silent():
    # N7: 'cyclone' is the DEVICE in the FCC failure — a remedy that
    # schedules cyclone inspection must not read as cycling-to-heal-
    # cycling
    prob_n7 = {"failure": "cyclone wall erosion from catalyst "
                          "impingement", "failure_mode": "cyclone-erosion"}
    bill_n7 = _bill("A scheduled cyclone inspection and tip-casting "
                    "rotation retimes the wear; periodic intervals.")
    assert not direction_lexicon_check(prob_n7, bill_n7), (
        "N7 'cyclone' fired the thermal-cycling class (a device noun "
        "is not cycling)")
    # N8: 'charge-sensing' is a measurement, and a static-charge
    # failure is not a charge/discharge cycle
    prob_n8 = {"failure": "static charge accumulation on the spacer",
               "failure_mode": "charge-buildup"}
    bill_n8 = _bill("Set the charge-sensing threshold to trigger the "
                    "polarity-reversal procedure.")
    assert not direction_lexicon_check(prob_n8, bill_n8), (
        "N8 'charge-sensing' fired the charge-discharge class (a "
        "measurement is not a charge/discharge cycle)")


def test_lexicon_class_pins_still_fire():
    # P5: the HO6-02 class with DIFFERENT wordforms — shock vs
    # fatigue/heat-check — must fire on the class, not the word
    prob_p5 = {"failure": "heat-checking and fatigue of the coated "
                          "face", "failure_mode": "fatigue-cracking"}
    bill_p5 = _bill("Creates periodic thermal shocks to induce "
                    "compressive residual stresses that inhibit "
                    "cracking.")
    got = direction_lexicon_check(prob_p5, bill_p5)
    assert got and "DRIVER_CLASS_AS_REMEDY" in got, (
        "P5 the HO6-02 class (shock remedy vs fatigue driver, "
        "different wordforms) must fire")


# ---------- D5 derivation ----------

def test_derive_direction_pins():
    f = lambda s: {"sign_of_ingredient_vs_driver": s,
                   "established_driver": "cyclic thermal shock drives "
                   "heat-checking", "ingredient_action": "periodic "
                   "thermal shocks through the coating"}
    got = _derive_direction(f("SAME"))
    assert got["direction"] == "INVERTED" and not got.get("divergence")
    got = _derive_direction(f("OPPOSITE"))
    assert got["direction"] == "CORRECT" and not got.get("divergence")
    got = _derive_direction(f("UNSTATED"))
    assert got["direction"] == "UNCLEAR" and not got.get("divergence")
    # the reason is assembled from the fields — verdict and reason
    # cannot diverge structurally
    assert got["reason"].endswith("-> UNCLEAR")
    assert got["ingredient_action"][:20] in got["reason"], (
        "the reason must carry the ingredient field verbatim")


def test_derive_direction_divergence_is_typed_fail_open():
    fields = {"sign_of_ingredient_vs_driver": "SAME",
              "direction": "CORRECT",
              "established_driver": "cyclic shock drives cracking",
              "ingredient_action": "periodic shocks"}
    got = _derive_direction(fields)
    assert got["direction"] == "INVERTED", (
        "the DERIVED verdict stays authoritative under divergence")
    assert got.get("divergence") and "DIVERGENT" in got["divergence"], (
        "a label/derivation disagreement must be typed DIVERGENT "
        "(fail-open, disclosed)")
