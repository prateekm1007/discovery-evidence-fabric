#!/usr/bin/env python3
"""tests/test_r30_permitted_measures.py — the per-problem
permitted-measure enforcement CI (AM91 lane claim c-0116; SUPERSEDED
surface R103 claim c-0118 after the verifier recompute typed the
original measure_guard's defects — eval/r103_verifier_record.json +
the Art. 16 retirement ledger).

The superseding guard (discovery_fabric/engine/permitted_measures.py +
data/measure_class_taxonomy.json):
  1. KILLS the HO14-12-shape synthetic (out-of-set measure, nested);
  2. handles EVERY bill format (the original's row walk found ZERO
     rows on 22/30 burned answers — the '*'-bullet/'|'-table formats
     unmatched; this battery pins the format coverage);
  3. stays silent when every measure is inside the permitted set
     (incl. the anaphora cases and the burden/annotation rows);
  4. fails closed on an unclassifiable measure row (a typed finding,
     never a silent pass-through — the strictest read; a self-declared
     (c) tag does NOT resolve the measure variable, it declares the
     procurement class);
  5. reproduces the REAL post-burn regression from committed bytes:
     fires on EXACTLY HO14-12 across the 30 burned v14 rows WITH rows
     checked on every row (the auditor full-read is the labelled
     truth) — the original's 'exactly HO14-12 KILLED' claim was
     technically true but 22/30 rows were never checked (NOT_APPLICABLE,
     zero rows found);
  6. the sensor form ("use only the existing ...; no new sensors") is
     NOT this scan's jurisdiction (no allowed-measures span): the
     new-instrumentation class is the r26 APPARATUS_ROW +
     scan_input_availability binds — pinned here as the coverage
     hand-off.
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

from discovery_fabric.engine import permitted_measures as pm  # noqa
from discovery_fabric.engine.permitted_measures import (  # noqa
    enforce_answer, collect_measure_rows)
from r30_allowed_class_scan import scan_allowed_measures_class  # noqa
from r26_catalog_scan import scan_apparatus  # noqa

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V14_PATH = "audit/holdout_v14/holdout_v14_problems.json"
ROWS_DIR = REPO / "eval" / "holdout_v14_generation" / "rows"

AMMONIA_SET = ("no tower redesign; allowed measures: pH/caustic "
               "chemistry dosing retuning, air-to-water ratio "
               "setpoint retuning, or water-temperature setpoint "
               "retuning only")


def _prob(uv: str) -> dict:
    return {"user_variables": uv}


def test_ho14_12_shape_synthetic_kills_outside_measure() -> None:
    ans = ("IMPLEMENTATION BILL\n"
           "- Item: Recirculation pump speed increase to scour the "
           "packing. (c)\n"
           "  Tag: (c) parameter change\n")
    r = enforce_answer(_prob(AMMONIA_SET), ans)
    assert r.get("MEASURE_NOT_IN_PERMITTED_SET"), r


def test_every_bill_format_found() -> None:
    """The R103 format-coverage pin: the water-domain formats the
    original walk missed (asterisk bullets, markdown tables, Row-N
    labels) all yield measure rows."""
    ans = ("IMPLEMENTATION BILL\n"
           "*   Row 1: **Adjustment of Recirculation Pump Speed/VFD "
           "Setpoint.** (c)\n"
           "| **1** | **Rapid-Mix Paddle Speed Setpoint:** Change the "
           "drive frequency. | **(c)** | Parameter. |\n"
           "2. **Retuning of Air-to-Water Ratio Setpoint.** (c)\n")
    rows = collect_measure_rows(ans)
    assert len(rows) == 3, rows
    joined = " | ".join(rows)
    assert "Recirculation" in joined and "Rapid-Mix" in joined \
        and "Air-to-Water" in joined


def test_all_measures_inside_stays_silent() -> None:
    ans = ("IMPLEMENTATION BILL\n"
           "- Item: pH setpoint retuning to 10.5. (c)\n"
           "  Tag: (c) parameter change\n"
           "- Item: Raise the air-to-water ratio to 3000:1. (c)\n"
           "*   **Operational Loss:** Zero throughput loss.\n"
           "*   *Source:* Existing air blower control loop.\n")
    assert enforce_answer(_prob(AMMONIA_SET), ans) == {}


def test_unresolvable_measure_row_fails_closed() -> None:
    """A measure row matching NO canonical class is a typed finding
    (never a silent pass-through); a self-declared (c) tag declares
    the PROCUREMENT class, not the measure variable — the row still
    needs restatement (the strictest fail-closed read, diverging from
    the original guard's (c)-resolves-to-generic semantics — typed in
    the verifier record)."""
    p = _prob(AMMONIA_SET)
    ans = ("IMPLEMENTATION BILL\n"
           "- Item: Qublorg the framistat assembly to nine grades.\n")
    r = enforce_answer(p, ans)
    assert (r.get("MEASURE_CLASS_UNRESOLVED")
            or r.get("MEASURE_NOT_IN_PERMITTED_SET")), r
    # the (c)-tagged variant: still not a silent pass-through
    ans2 = ("IMPLEMENTATION BILL\n"
            "- Item: Qublorg the framistat assembly to nine grades. "
            "(c)\n")
    r2 = enforce_answer(p, ans2)
    assert (r2.get("MEASURE_CLASS_UNRESOLVED")
            or r2.get("MEASURE_NOT_IN_PERMITTED_SET")), r2


def test_sensor_form_is_apparatus_jurisdiction() -> None:
    """The predictor sensor form carries NO allowed-measures span —
    this scan stays silent; the new-instrumentation class is the r26
    APPARATUS_ROW bind (the coverage hand-off, pinned)."""
    p = _prob("use only the existing feed temperature, distillate "
              "temperature and flow; no new sensors")
    bad = ("IMPLEMENTATION BILL\n"
           "- Item: Install a new conductivity sensor on the permeate "
           "line. (c)\n")
    assert enforce_answer(p, bad) == {}   # not this scan's span
    hits = scan_apparatus(bad.replace("IMPLEMENTATION BILL\n", ""))
    # scan_apparatus scopes to the bill section via its own regex
    assert scan_apparatus(bad).get("APPARATUS_ROW"), hits


def test_post_burn_regression_exact_and_checked() -> None:
    """The post-burn regression (read-only): across the 30 burned v14
    rows the guard fires on EXACTLY HO14-12 — WITH rows collected on
    every intervention row (the original's NOT_APPLICABLE-on-22 gap
    closed; the auditor full-read is the labelled truth)."""
    out = subprocess.run(["git", "show", f"{AUDIT_REF}:{V14_PATH}"],
                         capture_output=True, cwd=REPO)
    assert out.returncode == 0
    probs = {p["problem_id"]: p for p in
             json.loads(out.stdout)["problems"]}
    assert len(probs) == 30
    fired, rows_found = [], 0
    for pid, p in sorted(probs.items()):
        f = ROWS_DIR / f"{pid}.json"
        row = json.loads(f.read_text(encoding="utf-8"))
        ans = row["a1_answer"]
        n = len(collect_measure_rows(ans))
        if (p.get("question_type") or "").startswith("intervention"):
            assert n > 0, f"no measure rows found on {pid} — the " \
                "format coverage regressed"
            rows_found += n
        if enforce_answer(p, ans).get("MEASURE_NOT_IN_PERMITTED_SET"):
            fired.append(pid)
    assert rows_found >= 30, rows_found
    assert fired == ["HO14-12-ammonia-strip"], fired


def test_taxonomy_committed_and_deterministic() -> None:
    t1 = pm._taxonomy()
    t2 = pm._taxonomy()
    assert t1 is t2                      # cached single load
    assert t1["record"].startswith("MEASURE_CLASS_TAXONOMY")
    assert set(t1["substantive_classes"]) and \
        set(t1["vehicle_classes"]) and set(t1["modifier_classes"])
    # determinism: classify is pure over the taxonomy
    a = pm.classify_text_classes("Retuning of Air-to-Water Ratio")
    b = pm.classify_text_classes("Retuning of Air-to-Water Ratio")
    assert a == b and "air_water_ratio" in a


def test_wired_scan_fires_through_r30() -> None:
    """The r30 wiring carries the engine findings into the machine's
    violation surface (the fail-closed crash path typed)."""
    ans = ("IMPLEMENTATION BILL\n"
           "*   Row 1: **Adjustment of Recirculation Pump Speed/VFD "
           "Setpoint.** (c)\n")
    r = scan_allowed_measures_class(_prob(AMMONIA_SET), ans)
    assert r.get("MEASURE_NOT_IN_PERMITTED_SET"), r
    assert r.get("PERMITTED_MEASURE_GUARD_ERROR") is None
