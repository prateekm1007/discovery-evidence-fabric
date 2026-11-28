#!/usr/bin/env python3
"""tests/test_r27_standard_bill_scan.py — regression pins for the AM26
D1 V7.1 STANDARD-BILL tuning scan (the four FORBIDDEN classes of the
STANDARD-BILL BIND).

POSITIVE pins use the REAL violating bytes (the r26 V7 generation rows
the AM26 auditor-judged pilot flagged or the same-shape rows the
committed scan found — Art. 22 real-bytes acceptance):
  bench-p01  BESPOKE_COMPONENT — capillary wick "calibrate ... to
             match" a custom target (pilot gap-1 row)
  bench-p04  CUSTOM_MACHINING — the auditor's named example ("no
             custom machining like the p04 vane reprofile"; CNC
             tapered-thickness reprofile) (pilot gap-1 row)
  bench-p08  CUSTOM_RECIPE — custom deposition recipe (100 W/60 s vs
             the standard practice's own 150 W/30 s) + the extra
             post-deposition anneal step (pilot gap-1 row)
  bench-p09  CUSTOM_MATERIAL — "co-extruded interlayer of PE
             containing 5 wt% montmorillonite nano-clay"
  bench-p11  CUSTOM_MACHINING — "Aluminum mounting bracket (machined
             from standard stock" (the preamble-mention boundary case:
             the bill's own first line mentions the standard practice's
             bill — the rows after it are still the mechanism under
             test)
  eval-new01 CUSTOM_MACHINING — end plates "modified with a 0.5 mm
             deep recess"
  eval-sofc-thermal-cycling
             CUSTOM_MATERIAL — "Graded glass-ceramic seal with 0.25
             intergranular glass phase ... 0.05 at interconnect"

NEGATIVE pins: the 11 scan-clean r26 intervention rows must NOT fire
(p02 duty-cycle resistor/relay, p03 valve+PLC schedule, p05 the
auditor-praised bilayer of standard elastomers, p06 timer-scheduled
flow reversal, p07 firmware anodic sweep, p10 inverter duty cycle,
p12 solenoid diverter, dev-fu-005 cyclic-loading procedure, eval-new03
standard MEMS transducer, eval-new05 NTC array, eval-sofc-redox
standard humidifier + flow-controller schedules); ALL 12 predictor
rows must be inert (no intervention bill); a conformant synthetic
bill (catalog parts + standard operations only) must not fire; the
quoted STANDARD-PRACTICE sections must never fire (the reference, not
the mechanism under test).

Art. 19-style determinism: same bytes -> same findings, twice.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r27_standard_bill_scan import (  # noqa: E402
    scan_standard_bill, bill_section, compare_recipe_params)

PAIRS = REPO / "eval" / "pairs" / "r26_v7_catalog"


def _load(pid):
    return json.loads((PAIRS / f"{pid}.json").read_text(encoding="utf-8"))


FLAGGED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-sofc-thermal-cycling",
]
CLEAN_INT = [
    "bench-p02-leadacid-grid-corrosion",
    "bench-p03-phe-biofouling",
    "bench-p05-bridge-bearing-aging",
    "bench-p06-water-biofilm",
    "bench-p07-cgm-biofouling",
    "bench-p10-pv-pid",
    "bench-p12-mbr-fouling",
    "dev-fu-005-bridge-bearing",
    "eval-new03-insulin-pump-occlusion",
    "eval-new05-liion-balance-drift",
    "eval-sofc-redox",
]
PREDICTORS = [
    "dev-fu-001-bearing-spalling",
    "dev-fu-003-motor-insulation",
    "dev-fu-004-fouling",
    "eval-new02-slipring-predictor",
    "eval-new04-chiller-fouling-predictor",
    "eval-new06-bearing-vibration-predictor",
    "eval-new07-transformer-dga-predictor",
    "eval-new08-pipeline-leak-predictor",
    "eval-new09-hvac-filter-predictor",
    "eval-new10-solar-inverter-predictor",
    "eval-new11-conveyor-belt-predictor",
    "eval-new12-axle-bearing-predictor",
]


def _classes(v):
    out = set()
    for f in v.get("STANDARD_BILL", []):
        out.add(f.split(":", 1)[0])
    return out


# --- positive pins: the REAL flagged bytes MUST fire -------------------

def test_p01_bespoke_wick_fires():
    v = scan_standard_bill(_load(FLAGGED[0])["a1_answer"],
                           "intervention-proposal")
    assert "BESPOKE_COMPONENT" in _classes(v), v


def test_p04_cnc_reprofile_fires():
    """THE AM26 named example: no custom machining like the p04 vane
    reprofile."""
    v = scan_standard_bill(_load(FLAGGED[1])["a1_answer"],
                           "intervention-proposal")
    assert "CUSTOM_MACHINING" in _classes(v), v


def test_p08_custom_recipe_fires_both_shapes():
    v = scan_standard_bill(_load(FLAGGED[2])["a1_answer"],
                           "intervention-proposal")
    cl = _classes(v)
    assert "CUSTOM_RECIPE" in cl, v
    # both shapes: the added post-deposition anneal step AND the
    # same-tool-different-parameters deposition recipe
    txt = " ".join(v["STANDARD_BILL"])
    assert "added post-process step" in txt, v
    assert "non-standard parameters" in txt, v


def test_p09_wt_pct_material_fires():
    v = scan_standard_bill(_load(FLAGGED[3])["a1_answer"],
                           "intervention-proposal")
    assert "CUSTOM_MATERIAL" in _classes(v), v


def test_p11_machined_bracket_fires():
    """The boundary case: the bill's preamble mentions 'the standard
    practice's own bill' — the boundary must NOT end the section there
    (the machined-bracket row comes after it)."""
    v = scan_standard_bill(_load(FLAGGED[4])["a1_answer"],
                           "intervention-proposal")
    assert "CUSTOM_MACHINING" in _classes(v), v


def test_eval_new01_recess_fires():
    v = scan_standard_bill(_load(FLAGGED[5])["a1_answer"],
                           "intervention-proposal")
    assert "CUSTOM_MACHINING" in _classes(v), v


def test_sofc_thermal_graded_seal_fires():
    v = scan_standard_bill(_load(FLAGGED[6])["a1_answer"],
                           "intervention-proposal")
    assert "CUSTOM_MATERIAL" in _classes(v), v


# --- negative pins: conformant rows must NOT fire ----------------------

def test_clean_interventions_do_not_fire():
    for pid in CLEAN_INT:
        rec = _load(pid)
        v = scan_standard_bill(rec["a1_answer"],
                               rec.get("question_type", ""))
        assert not v, (pid, v)


def test_predictors_inert():
    for pid in PREDICTORS:
        rec = _load(pid)
        v = scan_standard_bill(rec["a1_answer"],
                               rec.get("question_type", ""))
        assert not v, (pid, v)


def test_flagged_set_is_exactly_seven():
    """The pre-registered tuning set: the scan over the r26 generation
    flags EXACTLY these 7 rows (and nothing else)."""
    got = []
    for f in sorted(PAIRS.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if scan_standard_bill(rec["a1_answer"],
                              rec.get("question_type", "")):
            got.append(rec["problem_id"])
    assert sorted(got) == sorted(FLAGGED), got


def test_standard_practice_quote_does_not_fire():
    """The quoted standard-practice bill is the REFERENCE, not the
    mechanism under test: p04's own bill ends at 'The standard
    practice bill includes:' and the quoted 'CNC machining (constant
    profile)' row there must not be the firing evidence."""
    ans = _load("bench-p04-pump-cavitation")["a1_answer"]
    bill = bill_section(ans)
    assert "The standard practice bill includes" not in bill
    v = scan_standard_bill(ans, "intervention-proposal")
    for f in v["STANDARD_BILL"]:
        assert "constant profile" not in f, f


def test_conformant_synthetic_bill_clean():
    """A V7.1-conformant synthetic bill (bilayer of two standard
    catalog materials + duty-cycle schedule on a standard timer —
    the relocation-target shape) must not fire."""
    ans = (
        "NOVELTY STATEMENT (INTERVENTION) — The departure is the "
        "ARRANGEMENT: a bilayer of two standard commercial elastomers "
        "with a duty-cycled flush schedule.\n\n"
        "IMPLEMENTATION BILL — (a) Existing end plates, used as-is. "
        "(b) Commercial EPDM sheet, 60 Shore A, 3 mm, installed as the "
        "outer layer per the supplier's own bonding procedure. "
        "(b) Commercial natural rubber sheet, 60 Shore A, 5 mm, "
        "installed as the inner layer per the supplier's own bonding "
        "procedure. (b) Standard mechanical timer, 230 V AC, set to "
        "15 min on / 6 h off. (c) Operating procedure: run the "
        "existing pump at its rated flow during the on window.\n\n"
        "BURDEN LEDGER (STANDARD-PRACTICE PARITY) — Installation: one "
        "extra stock sheet vs standard's single pad. Commissioning: "
        "same bonding step, both layers. Operation: passive. "
        "Maintenance: same inspection cycle."
    )
    v = scan_standard_bill(ans, "intervention-proposal")
    assert not v, v


def test_flow_setpoint_is_not_material_recipe():
    """Operating setpoints ('5% H₂O vapor' at a flow controller) are
    standard operations, not material formulations — must not fire
    CUSTOM_MATERIAL (the eval-sofc-redox clean shape)."""
    ans = (
        "IMPLEMENTATION BILL — (a) Existing flow controller: set N2 "
        "at 0.5 L/min with 5% water vapor during the 30 s purge stage. "
        "(b) Standard commercial membrane dryer, rated 1 L/min."
    )
    v = scan_standard_bill(ans, "intervention-proposal")
    assert "CUSTOM_MATERIAL" not in _classes(v), v


def test_determinism():
    rec = _load("bench-p08-mems-stiction")
    a = scan_standard_bill(rec["a1_answer"], "intervention-proposal")
    b = scan_standard_bill(rec["a1_answer"], "intervention-proposal")
    assert a == b
    rec4 = _load("bench-p04-pump-cavitation")
    assert (scan_standard_bill(rec4["a1_answer"], "intervention-proposal")
            == scan_standard_bill(rec4["a1_answer"],
                                  "intervention-proposal"))


def test_recipe_param_compare_only_on_real_divergence():
    """compare_recipe_params fires only when the own bill runs the
    same process class at DIFFERENT explicit numeric parameters than
    the quoted standard practice (p08 real bytes), and never on the
    clean rows."""
    for pid in CLEAN_INT:
        rec = _load(pid)
        assert not compare_recipe_params(
            rec["a1_answer"], bill_section(rec["a1_answer"])), pid
    rec = _load("bench-p08-mems-stiction")
    assert compare_recipe_params(rec["a1_answer"],
                                 bill_section(rec["a1_answer"]))
