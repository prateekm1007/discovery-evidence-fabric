#!/usr/bin/env python3
"""tests/test_r103_tool_grounded_critic_v14.py — the R103 (claim
c-0117, AM89 directive 3) CI fixtures: the c-0109 corrector's v1.2
water-domain extension.

Fixtures (verbatim prefixes of the burned-v14 committed residual
population — eval/r103_corrector_v12_water_mining.json): the burden-
label dispatch, the compliance-echo dispatch, the test/predictor
label dispatch, the equation rows, and the W5 sub-row inheritance.
Every expected verdict reviewed against the procurement semantics
(a=existing-infrastructure, b=purchased-standard, c=parameter/duty/
procedure/configuration); None = ambiguous/narrative — never a guess.

The measured calibration (committed bytes, zero generation): the
delivered-answer residual BILL_UNTAGGED population 127 -> 45 lines;
zero-residual rows 10/30 -> 17/30; the conservative delivered-node
convergence projection 15/30 = 50% (the AM89 >=50% water-domain
target); the v12/v13 regression: 0 forbidden flips (a->*, b->*),
10 reviewed c->a burden reclassifications, 66 new tags on v1.1-left-
flagged rows.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import tool_grounded_critic as tgc  # noqa: E402
import r22_a1w_v5_repair as r22  # noqa: E402


# --- the v1.2 typed rules (verbatim burned-v14 prefixes) ---------------

def test_w1_burden_label_zero_body_is_a():
    assert tgc.classify_bill_row(
        "*   **Commissioning Burden:** Zero. No new hardware, no new "
        "installation. (Standard practice: Zero for a setpoint "
        "change).") == "a"
    assert tgc.classify_bill_row(
        "*   **Operability:** No new user interface complexity; adds "
        "one alarm point. (Same class).") == "a"
    assert tgc.classify_bill_row(
        "*   **Installability:** Zero physical installation. Uses "
        "existing I/O channels.") == "a"
    assert tgc.classify_bill_row(
        "- Hardware: 0 new items. (Standard practice: 0 new items). "
        "Parity: Same.") == "a"


def test_w1_bare_burden_header_is_a():
    assert tgc.classify_bill_row("*   **Operational Loss Pricing:**") \
        == "a"
    assert tgc.classify_bill_row("*   **Operational Loss:**") == "a"


def test_w2_compliance_echoes_are_a():
    assert tgc.classify_bill_row(
        "*   **DEPLOYED-PART CLAUSE:** No modification to MBBR "
        "carriers, baffles, or vessel. Only c") == "a"
    assert tgc.classify_bill_row(
        "*   **UNPRICED_DUTY_CYCLE:** Operational loss (energy) is "
        "priced in the Burden Ledger.") == "a"
    assert tgc.classify_bill_row(
        "*   **MECHANISM_CLASS_UNSTATED:** Declared as \"High-Head "
        "Recirculation Scour\".") == "a"


def test_w3_test_predictor_labels_are_c():
    assert tgc.classify_bill_row(
        "4.  Measurement: Record outlet ammonia concentration at the "
        "same intervals.") == "c"
    assert tgc.classify_bill_row(
        "*   **Kill Criterion:** If anammox activity declines >10% "
        "(increased NH4 breakthrough).") == "c"
    assert tgc.classify_bill_row(
        "*   **Pass/Fail Thresholds:**") == "c"
    assert tgc.classify_bill_row(
        "*   *Source:* SCADA/DCS historian tags for Feed_Pressure") \
        == "c"


def test_w4_equation_and_schedule_rows_are_c():
    assert tgc.classify_bill_row(
        "-   $Re = \\frac{4 \\dot{m}_f}{\\pi D_h \\mu(T_f)}$") == "c"
    assert tgc.classify_bill_row(
        "*   Row 3: **Scheduling the Scouring Phase.**") == "c"


def test_w5_subrows_inherit_parent_tag():
    ans = ("IMPLEMENTATION BILL\n"
           "MECHANISM CLASS: A/W Setpoint Retuning\n"
           "- Row 1: **Retuning of Air-to-Water Ratio Setpoint.** (c)\n"
           "*   *Description:* Maintain the air flow at its existing "
           "setpoint.\n"
           "*   *Source:* Existing air blower control loop.\n")
    corrected, rec = tgc.tag_bill(ans)
    assert rec["inherited"] == 2, rec
    assert r22.scan(corrected).get("BILL_UNTAGGED") is None


def test_w5_never_overrides_own_class():
    """'Tag: AS-IS device.' carries its OWN (a) semantics — the parent
    never overrides it (the v13-table pin)."""
    assert tgc.classify_bill_row("*   Tag: AS-IS device.") == "a"


def test_b_marker_beats_burden_label():
    """A 'Hardware:' row naming a catalog item IS a (b) procurement
    row (the v13 pin — the label family never launders procurement)."""
    assert tgc.classify_bill_row(
        "*   **Hardware:** The conductivity probe is a standard "
        "catalog item already procured in th") == "b"


def test_a_marker_beats_test_predictor_label():
    """An input/source row citing ALREADY-RECORDED data is (a) — the
    v13-table-pinned read (the v1.2 a->c flip class, fixed)."""
    assert tgc.classify_bill_row(
        "*   *Input 2:* Liquid Flow Rate ($Q_{liq}$) — "
        "**ALREADY-RECORDED** (Stated: \"liquid flow\"). (a)") == "a"


def test_indicator_rows_are_predictor_structure_c():
    assert tgc.classify_bill_row(
        "*   **Secondary Indicators:** **Temperature** and **Pump "
        "Current**.") == "c"


def test_feed_tank_hardware_stays_none():
    """'Alkali Salt Additive Feed Tank:' is a HARDWARE header (the
    'feed' collision class, fixed) — never a test/predictor row."""
    assert tgc.classify_bill_row(
        "1.  **Alkali Salt Additive Feed Tank:**") is None


# --- the measured calibration (committed bytes, read-only) -------------

def test_v14_delivered_answer_clearance():
    """The burned-v14 measured calibration: >=17/30 delivered answers
    clean of residual BILL_UNTAGGED under v1.2 (v1.1: 10/30), and the
    population <= 50 lines (v1.1: 127)."""
    import json
    rows_dir = REPO / "eval" / "holdout_v14_generation" / "rows"
    zero = 0
    total = 0
    for fp in sorted(rows_dir.glob("*.json")):
        ans = json.loads(fp.read_text(encoding="utf-8"))["a1_answer"]
        corrected, _ = tgc.tag_bill(ans)
        total += len(r22.scan(corrected).get("BILL_UNTAGGED", []))
        if not r22.scan(corrected).get("BILL_UNTAGGED"):
            zero += 1
    assert zero >= 17, (zero, total)
    assert total <= 50, total


def test_record_version_bumped():
    assert tgc.RECORD == "TOOL_GROUNDED_CRITIC/1.2.0"
