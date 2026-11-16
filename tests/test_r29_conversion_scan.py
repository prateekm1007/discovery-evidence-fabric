#!/usr/bin/env python3
"""tests/test_r29_conversion_scan.py — regression pins for the AM27 D2
V7.2 CONVERSION scan (the six classes that convert the
auditor-adjudicated gap>=1 rows to pure catalog-part / procedure
changes).

POSITIVE pins use the REAL violating bytes of the CURRENT battery
(Art. 22 real-bytes acceptance; the r27-tuned rows + the r26 frozen
rows the auditor re-judged at d7540c6fe):
  bench-p01  (r27) MATERIAL_FUNCTION_CLAIM — "selectively permeates
             water vapor" / "selectively recirculates only water
             vapor" (an off-spec selective-function claim for a
             catalog membrane)
  bench-p04  (r27) SURFACE_TREATMENT_DEV — micro-blasting at a target
             "Ra = 8 +/- 2 um" (surface-treatment development on the
             deployed impeller)
  bench-p06  (r26) PREMISE_TOPOLOGY_INVALID — "unidirectional flow
             reversal in dead-end mains" (the auditor self-correction:
             a dead-end main has no second supply path and cannot
             reverse flow)
  bench-p08  (r27) SURFACE_TREATMENT_DEV + ADDED_PROCESS_STEP —
             "etch dimples with 0.5 um radius" (MEMS comb process
             development)
  bench-p09  (r27) ADDED_PROCESS_STEP — the gravure-coater silica
             coating + cure rows (a coating process added to the
             packaging line)
  bench-p11  (r27) BONDED_INTERFACE_DEV — the aluminum sleeve
             epoxy-bonded to the steel shaft (a dissimilar-metal
             bonded interface the standard practice's bill does not
             perform)
  eval-new01 (r27) MATERIAL_FUNCTION_CLAIM — "passively reabsorbed
             evaporated solvent" (a catalog desiccant claimed to
             perform solvent reabsorption, an off-spec function)
  eval-new03 (r26) ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE — "Add
             downstream pressure sensor at catheter midpoint (b)"
             on an insulin pump (medical device hardware+regulatory
             development)

NEGATIVE pins — the auditor-scored gap-0 rows must stay clean:
  bench-p02 (charging-profile duty cycle, catalog relay/resistor),
  bench-p03 (3-way valve + PLC; the reversal is on a LOOPED heat
             exchanger, and its pressure taps row is (a) existing),
  bench-p05 (the auditor-praised bilayer of standard elastomers:
             every bond row rides existing infrastructure — the
             exemption that keeps arrangement-class bonding clean),
  bench-p07 (firmware anodic sweep on EXISTING electrodes),
  bench-p10 (inverter + timer relay; its F38 defect is the
             operational-loss scan's class, not this scan's),
  bench-p12 (solenoid diverter on existing pumps),
  dev-fu-005 (install-time cyclic loading procedure),
  eval-new05 (BMS firmware + commodity NTC array — the added-sensor
             shape on a NON-regulated device: the auditor's gap-0
             read),
  eval-sofc-redox (gas sequencing on existing manifold; the
             industrial humidity probe is not a regulated-device
             channel),
  eval-sofc-thermal-cycling (r27 tuned: clean on THIS scan — its
             graded-composition defect is the r27 CUSTOM_MATERIAL
             class, pinned in tests/test_r27_standard_bill_scan.py;
             not duplicated here),
plus ALL 12 predictor rows (inert by construction) and SYNTHETIC
shape pins for each class (fire) and each exemption (stay clean).

Art. 19-style determinism: same bytes -> same findings, twice.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r29_conversion_scan import scan_conversion  # noqa: E402

R26 = REPO / "eval" / "pairs" / "r26_v7_catalog"
R27 = REPO / "eval" / "pairs" / "r27_v71_tuned"


def _load(pairs_dir, pid):
    return json.loads((pairs_dir / f"{pid}.json").read_text(encoding="utf-8"))


def _probs():
    probs = {}
    for f in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / f).read_text(encoding="utf-8"))[
                "problems"]:
            probs[p["problem_id"]] = p
    return probs


PROBS = _probs()

# (pairs_dir, pid, expected class substring)
POSITIVE = [
    (R27, "bench-p01-pemfc-dehydration", "MATERIAL_FUNCTION_CLAIM"),
    (R27, "bench-p04-pump-cavitation", "SURFACE_TREATMENT_DEV"),
    (R26, "bench-p06-water-biofilm", "PREMISE_TOPOLOGY_INVALID"),
    (R27, "bench-p08-mems-stiction", "SURFACE_TREATMENT_DEV"),
    (R27, "bench-p08-mems-stiction", "ADDED_PROCESS_STEP"),
    (R27, "bench-p09-packaging-barrier", "ADDED_PROCESS_STEP"),
    (R27, "bench-p11-spindle-thermal-drift", "BONDED_INTERFACE_DEV"),
    (R27, "eval-new01-supercap-dryout", "MATERIAL_FUNCTION_CLAIM"),
    (R26, "eval-new03-insulin-pump-occlusion",
     "ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE"),
]

NEGATIVE = [
    (R26, "bench-p02-leadacid-grid-corrosion"),
    (R26, "bench-p03-phe-biofouling"),
    (R26, "bench-p05-bridge-bearing-aging"),
    (R26, "bench-p07-cgm-biofouling"),
    (R26, "bench-p10-pv-pid"),
    (R26, "bench-p12-mbr-fouling"),
    (R26, "dev-fu-005-bridge-bearing"),
    (R26, "eval-new05-liion-balance-drift"),
    (R26, "eval-sofc-redox"),
    (R27, "eval-sofc-thermal-cycling"),
]


def test_positive_pins_on_real_bytes():
    for pairs_dir, pid, cls in POSITIVE:
        rec = _load(pairs_dir, pid)
        v = scan_conversion(rec["a1_answer"], rec["question_type"],
                            PROBS.get(pid))
        assert v and any(f.startswith(cls + ":")
                         for f in v["CONVERSION"]), (
            f"{pid} must fire {cls}: {v}")


def test_the_premise_flaw_fires_from_the_problem_too():
    """The dead-end topology is stated in the PROBLEM itself — the scan
    must catch a reversal claim even if the answer never says
    'dead-end' (answer-only variant of the same defect)."""
    ans = ("NOVELTY STATEMENT (INTERVENTION) — The intervention is a "
           "periodic flow reversal in the distribution main to shear "
           "biofilm. IMPLEMENTATION BILL — (a) Existing DN50 gate "
           "valve, operated to reverse the flow direction. BURDEN "
           "LEDGER — same class. EXECUTABLE TEST — hydrant sampling.")
    v = scan_conversion(ans, "intervention-proposal",
                        PROBS["bench-p06-water-biofilm"])
    assert v and any(f.startswith("PREMISE_TOPOLOGY_INVALID:")
                     for f in v["CONVERSION"]), v


def test_negative_pins_on_real_bytes():
    for pairs_dir, pid in NEGATIVE:
        rec = _load(pairs_dir, pid)
        v = scan_conversion(rec["a1_answer"], rec["question_type"],
                            PROBS.get(pid))
        assert not v, f"{pid} must stay clean: {v}"


def test_the_loop_topology_reversal_stays_clean():
    """bench-p03's class: reversing flow on a LOOPED system (a plate
    heat exchanger circuit) is topology-valid — no dead-end anywhere."""
    ans = ("NOVELTY STATEMENT — periodic reverse flow through the heat "
           "exchanger loop. IMPLEMENTATION BILL — (b) 3-way ball "
           "valve, (c) PLC program: reverse flow every 6 hours for 5 "
           "minutes. BURDEN LEDGER — same class. EXECUTABLE TEST — "
           "pressure-drop measurement.")
    assert not scan_conversion(ans, "intervention-proposal")


def test_arrangement_class_bonding_stays_clean():
    """bench-p05's class: a bilayer of standard sheets bonded ON the
    EXISTING jig with the EXISTING cement applicator — every process
    row rides existing infrastructure, so it must stay clean."""
    ans = ("IMPLEMENTATION BILL — (a) Inner layer: standard commercial "
           "natural rubber sheet bonded to steel plates (uses existing "
           "steel plates and bonding jig). (b) Outer layer: standard "
           "commercial EPDM sheet bonded to the NR layer (uses "
           "existing cement applicator and roller). (c) Bonding "
           "procedure: modify existing bonding protocol (no new "
           "equipment). BURDEN LEDGER — same class.")
    assert not scan_conversion(ans, "intervention-proposal")


def test_dissimilar_metal_bond_fires():
    ans = ("IMPLEMENTATION BILL — (b) Commercial aluminum sleeve, "
           "6061-T6, press-fit over existing steel shaft (stock "
           "catalog item). (c) Standard epoxy adhesive applied per "
           "manufacturer's spec, cured at 25C for 24 hr. BURDEN "
           "LEDGER — same class.")
    v = scan_conversion(ans, "intervention-proposal")
    assert v and any(f.startswith("BONDED_INTERFACE_DEV:")
                     for f in v["CONVERSION"]), v


def test_regulated_device_added_channel_fires_non_regulated_does_not():
    medical = ("IMPLEMENTATION BILL — (b) Add downstream pressure "
               "sensor at catheter midpoint (commercially available "
               "MEMS pressure transducer, same class as existing pump "
               "sensor). BURDEN LEDGER — same class.")
    v = scan_conversion(medical, "intervention-proposal",
                        PROBS["eval-new03-insulin-pump-occlusion"])
    assert v and any(
        f.startswith("ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE:")
        for f in v["CONVERSION"]), v
    industrial = ("IMPLEMENTATION BILL — (b) Install 13 NTC "
                  "thermocouples (one per cell), commercially "
                  "available temperature sensors. BURDEN LEDGER — "
                  "commodity items.")
    assert not scan_conversion(
        industrial, "intervention-proposal",
        PROBS["eval-new05-liion-balance-drift"])


def test_existing_equipment_rows_do_not_fire_sensing():
    """bench-p03/p07's class: rows that USE existing sensors are the
    existing-equipment class — clean even on a regulated device."""
    ans = ("IMPLEMENTATION BILL — (a) Existing pressure taps, use "
           "existing differential pressure indicators. (a) Existing "
           "working electrode, no hardware change. BURDEN LEDGER — "
           "same.")
    assert not scan_conversion(ans, "intervention-proposal",
                               PROBS["eval-new03-insulin-pump-occlusion"])


def test_surface_treatment_fires_but_standard_operation_does_not():
    treated = ("IMPLEMENTATION BILL — (c) Micro-blast leading edges "
               "at 10 cm/s, 2 passes, achieving Ra = 8 um. BURDEN "
               "LEDGER — same class.")
    v = scan_conversion(treated, "intervention-proposal")
    assert v and any(f.startswith("SURFACE_TREATMENT_DEV:")
                     for f in v["CONVERSION"]), v
    standard = ("IMPLEMENTATION BILL — (b) Commercial suction strainer, "
                "DN80, installed on the existing inlet flange. "
                "(c) Set the existing pump to its rated duty point. "
                "BURDEN LEDGER — same class.")
    assert not scan_conversion(standard, "intervention-proposal")


def test_predictor_rows_inert():
    n = 0
    for f in sorted(R26.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if str(rec.get("question_type", "")).startswith("predictor"):
            v = scan_conversion(rec["a1_answer"],
                                rec.get("question_type", ""),
                                PROBS.get(rec.get("problem_id")))
            assert not v, f"predictor {f.name} must be inert: {v}"
            n += 1
    assert n == 12, f"expected 12 predictor rows, saw {n}"


def test_determinism():
    rec = _load(R26, "bench-p06-water-biofilm")
    a = scan_conversion(rec["a1_answer"], rec["question_type"],
                        PROBS["bench-p06-water-biofilm"])
    b = scan_conversion(rec["a1_answer"], rec["question_type"],
                        PROBS["bench-p06-water-biofilm"])
    assert a == b
