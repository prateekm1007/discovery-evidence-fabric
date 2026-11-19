"""tests/test_r30_permitted_measures.py — the per-problem
permitted-measure enforcement CI (AM91 capability-fix lane, claim
c-0116; the auditor-approved design contract §2.1 + refinement).

The HO14-12 defect class: the v14 ammonia-strip answer proposed
recirculation-flow/VFD scour OUTSIDE the problem's permitted measure
set, and the deterministic scan missed it (the permitted sets live in
user_variables; the offender row was procedure-shaped; a nested
sub-plan row). The engine guard (measure_guard.py + the committed
taxonomy) must:
  1. KILL the HO14-12-shape synthetic (out-of-set measure, nested);
  2. KILL on a violation that appears ONLY in a nested sub-plan row
     (the flat-walk structural miss);
  3. stay CLEAN when every measure is inside the permitted set;
  4. KILL MEASURE_CLASS_UNRESOLVED (fail-closed) on an unclassifiable
     measure row;
  5. reproduce the REAL post-burn regression from committed bytes:
     exactly HO14-12 KILLED across the 30 burned v14 rows (the
     auditor full-read is the labelled truth: 29 sound rows).
The burned rows are read READ-ONLY (the set is BURNED; no generation,
no quota, no sealed contact).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import measure_guard  # noqa: E402
from r30_allowed_class_scan import scan_allowed_measures_class  # noqa

AUDIT_REF = "36f9559ef"  # the re-sealed v14 (AM88/CORR-7) tip
V14_PATH = "audit/holdout_v14/holdout_v14_problems.json"
ROWS_DIR = REPO / "eval" / "holdout_v14_generation" / "rows"


def _prob(uv: str) -> dict:
    return {"user_variables": uv}


BILL = """IMPLEMENTATION BILL
- Item: {measure}. (c)
  Tag: (c) {tag}
"""


def test_ho14_12_shape_synthetic_kills_outside_measure() -> None:
    """Fixture 1 (the contract): a recirculation/VFD scour measure
    under the ammonia-strip permitted set must be a typed KILL naming
    the offending class."""
    p = _prob("no tower redesign; allowed measures: pH/caustic "
              "chemistry dosing retuning, air-to-water ratio setpoint "
              "retuning, or water-temperature setpoint retuning only")
    ans = BILL.format(measure="Switch to recirculation-flow/VFD "
                      "scouring during the stripping cycle",
                      tag="Operating mode change on the existing loop")
    g = measure_guard.permitted_measures_check(p, ans)
    assert g["verdict"] == "KILL", g
    assert any(r.startswith("MEASURE_NOT_IN_PERMITTED_SET")
               for r in g["kill_reasons"]), g["kill_reasons"]
    assert any("flow_recirculation_hardware" in r
               for r in g["kill_reasons"])
    # the r30 harness wiring surfaces the same finding
    s = scan_allowed_measures_class(p, ans)
    assert "PERMITTED_MEASURE_SET_VIOLATION" in s


def test_nested_only_violation_kills() -> None:
    """Fixture 2: the violation hides in a NESTED sub-plan row (the
    flat-walk structural miss that let the real HO14-12 through)."""
    p = _prob("no tower redesign; allowed measures: pH/caustic "
              "chemistry dosing retuning, air-to-water ratio setpoint "
              "retuning, or water-temperature setpoint retuning only")
    ans = ("IMPLEMENTATION BILL\n"
           "- Item: Retune the water-temperature setpoint to 35 C. (c)\n"
           "  - Sub-step: install a VFD-driven recirculation scour "
           "loop. (c)\n"
           "  - Sub-step: log the outlet ammonia. (c)\n")
    g = measure_guard.permitted_measures_check(p, ans)
    assert g["verdict"] == "KILL", g
    assert any("hardware_installation" in r or
               "flow_recirculation_hardware" in r
               for r in g["kill_reasons"]), g["kill_reasons"]


def test_all_measures_inside_stays_clean() -> None:
    """Fixture 3: every measure inside the permitted set stays CLEAN
    (the false-kill control; incidental 'adjust' verbs must not
    kill)."""
    p = _prob("no tower redesign; allowed measures: pH/caustic "
              "chemistry dosing retuning, air-to-water ratio setpoint "
              "retuning, or water-temperature setpoint retuning only")
    ans = ("IMPLEMENTATION BILL\n"
           "- Item: Raise the water-temperature setpoint from 25 C to "
           "35 C. (c)\n"
           "- Item: Adjust the air-to-water ratio setpoint to 3.5. "
           "(c)\n"
           "- Item: Increase the caustic dose setpoint for pH hold at "
           "10.8. (c)\n")
    g = measure_guard.permitted_measures_check(p, ans)
    assert g["verdict"] == "CLEAN", g["kill_reasons"]


def test_unresolvable_measure_row_fails_closed() -> None:
    """Fixture 4 (fail-closed): a measure row matching NO taxonomy
    rule and carrying NO self-declared procurement tag is
    MEASURE_CLASS_UNRESOLVED — a typed KILL, never a pass-through.
    (A row with an explicit (c) self-declaration IS classifiable by
    the machine's own procurement contract — (c) is the parameter/
    procedure class — so it falls to the generic class, not the
    unresolved kill.)"""
    p = _prob("no tower redesign; allowed measures: pH/caustic "
              "chemistry dosing retuning, air-to-water ratio setpoint "
              "retuning, or water-temperature setpoint retuning only")
    ans = ("IMPLEMENTATION BILL\n"
           "- Item: Qublorg the framistat assembly to nine grades.\n")
    g = measure_guard.permitted_measures_check(p, ans)
    assert g["verdict"] == "KILL", g
    assert any(r.startswith("MEASURE_CLASS_UNRESOLVED")
               for r in g["kill_reasons"])
    # and the self-declared (c) row resolves to the generic class
    ans2 = ("IMPLEMENTATION BILL\n"
            "- Item: Qublorg the framistat assembly to nine grades. "
            "(c)\n")
    g2 = measure_guard.permitted_measures_check(p, ans2)
    assert g2["verdict"] == "CLEAN", g2["kill_reasons"]


def test_sensor_form_addition_kills_usage_passes() -> None:
    """The predictor-row sensor form: adding a NEW sensor is the
    violation; using the existing instrumentation is not."""
    p = _prob("use only the existing feed temperature, distillate "
              "temperature and flow; no new sensors")
    bad = ("IMPLEMENTATION BILL\n"
           "- Item: Install a conductivity probe on the permeate "
           "line. (c)\n")
    g = measure_guard.permitted_measures_check(p, bad)
    assert g["verdict"] == "KILL", g
    good = ("IMPLEMENTATION BILL\n"
            "- Item: Source: EXISTING flow meter (stated in "
            "problem). (a)\n"
            "- Tag: (a) No new hardware. Uses existing telemetry "
            "export.\n")
    g2 = measure_guard.permitted_measures_check(p, good)
    assert g2["verdict"] == "CLEAN", g2["kill_reasons"]


def _burned_rows_and_problems():
    out = subprocess.run(["git", "show", f"{AUDIT_REF}:{V14_PATH}"],
                         capture_output=True, cwd=REPO)
    assert out.returncode == 0, "the burned v14 problems must be "
    "readable at the audit ref (committed bytes)"
    doc = json.loads(out.stdout)
    return doc["problems"]


def test_post_burn_regression_ho14_12_killed_only() -> None:
    """The post-burn regression (read-only over the BURNED artifacts;
    no generation, no quota): across the 30 v14 rows the guard KILLS
    EXACTLY HO14-12 — the auditor full-read is the labelled truth
    (29 sound rows; HO14-12 out-of-set)."""
    probs = {p["problem_id"]: p for p in _burned_rows_and_problems()}
    assert len(probs) == 30
    killed = []
    for pid, p in sorted(probs.items()):
        f = ROWS_DIR / f"{pid}.json"
        assert f.exists(), f"burned row missing: {pid}"
        row = json.loads(f.read_text(encoding="utf-8"))
        g = measure_guard.permitted_measures_check(p,
                                                   row["a1_answer"])
        if g["verdict"] == "KILL":
            killed.append(pid)
    assert killed == ["HO14-12-ammonia-strip"], (
        f"the post-burn regression must kill exactly HO14-12 "
        f"(the auditor's labelled truth); got {killed}")


def test_r70_ammonia_leg_post_burn_single_hit() -> None:
    """The ammonia-strip direction legs (A1 inverted + A2 false
    premise) fire on EXACTLY the HO14-12 burned answer — the
    auditor's labelled truth — and stay silent on the other 29."""
    from r70_stated_formula_scan import scan_ammonia_strip_direction
    probs = _burned_rows_and_problems()
    hits = {}
    for p in probs:
        pid = p["problem_id"]
        row = json.loads((ROWS_DIR / f"{pid}.json")
                         .read_text(encoding="utf-8"))
        d = scan_ammonia_strip_direction(row["a1_answer"])
        if d:
            hits[pid] = sorted(d.keys())
    assert hits == {"HO14-12-ammonia-strip":
                    ["AMMONIA_STRIP_DIRECTION_INVERTED",
                     "AMMONIA_STRIP_PREMISE_FALSE"]}, hits


def test_taxonomy_committed_and_deterministic() -> None:
    """The taxonomy is committed engine data with the fail-closed
    policy and a stable load (byte-identical across loads)."""
    t1 = measure_guard.load_taxonomy()
    t2 = measure_guard.load_taxonomy()
    assert t1 == t2
    assert t1["unclassified_policy"] == \
        "MEASURE_CLASS_UNRESOLVED_KILL"
    assert len(t1["row_rules"]) >= 20 and len(t1["item_rules"]) >= 10
