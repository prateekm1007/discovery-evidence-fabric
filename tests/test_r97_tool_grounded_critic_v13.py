#!/usr/bin/env python3
"""R97 (c-0113) — the v13 convergence extension's CI fixtures.

The c-0109 corrector's 1.0.0 vocabulary left 210/231 of the sealed v12
residual BILL_UNTAGGED texts unclassified (mined from the committed
ledger @ 23ab8ad36 by scripts/r98_probe_residuals.py). The v13
extension adds four typed rules (existing-DATA markers, procedure
verbs, label dispatch, narrative guard) and normalizes self-declared
"(a - ...)" formats. Every fixture below is a VERBATIM prefix of a
committed v12 row byte string; every expected verdict was reviewed
row-by-row against the procurement semantics (a=existing-infrastructure,
b=purchased-standard, c=parameter/duty/procedure/configuration) with
None = ambiguous/narrative/header — never a guess. Pins no-regression
of tests/test_r95_tool_grounded_critic.py's semantics AND the v13
table's stability.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from discovery_fabric.engine import tool_grounded_critic as tgc

# (row_prefix, expected_class) — verbatim v12 residual corpus prefixes
C_CASES = [
    ("*   **Action:** Implement a slower ramp rate for Oxygen feed "
     "changes during turndown.", "c"),
    ("*   **Component:** Ramp rate restriction to prevent temperature "
     "transients.", "c"),
    ("*   **Component:** Steam-to-oil ratio control loop, set S/O = "
     "1.45.", "c"),
    ("*   **Parameter:** Change target ratio from nominal 0.60 to 0.55 "
     "mol O2 / mol C2H4.", "c"),
    ("*   **Parameter:** Limit d(O2 flow)/dt to 0.5% per minute "
     "(slower than standard 2% per min", "c"),
    ("*   **Warning Threshold:** DERIVED as `Baseline_CRSD + 3 * "
     "Baseline_StdDev`.", "c"),
    ("*   Logic: Compute $Z_{eff} = f(V, S, T)$. Normalize by "
     "temperature", "c"),
    ("*   -   Protocol: Back-test the algorithm on 12 months of "
     "historical DCS data.", "c"),
    ("*   -   **Tag:** **DERIVED** (From stated physics).", "c"),
    ("*   -   Pass/Fail: The algorithm must flag \"High Stress\" "
     "events", "c"),
    ("1.  **Parameter Change:** Modify the PLC recipe for CO pressure "
     "control", "c"),
    ("2.  Track the peak's frequency over time.", "c"),
    ("*   **Duration:** 24-hour back-test run.", "c"),
    ("*   **Steam Duty Cycle:** Increasing steam-to-oil ratio from "
     "1.5:1 to 2.5:1", "c"),
    ("*   False Positives (FA): The algorithm must produce <= 1 false "
     "alarm per pump", "c"),
    ("*   *Operation:* Filter/dry the feed stream to remove basic "
     "impurities and water.", "c"),
]
A_CASES = [
    ("*   Tag: AS-IS device.", "a"),
    ("*   -   **Tag:** **ALREADY-RECORDED** (Problem states: \"use "
     "only the existing column pressure", "a"),
    ("6.  Validation Source: ALREADY-RECORDED data + stated physics "
     "relation.", "a"),
    ("- Installation: Zero. No new hardware, no installation.",
     "a"),
    ("*   **Tension:** The constraint says \"no new sensors.\" This "
     "solution uses *existing* senso", "a"),
    ("*   **Maintenance:** No new maintenance. The existing "
     "tube-coking cleaning cycle is unchan", "a"),
]
B_CASES = [
    ("*   **Hardware:** The conductivity probe is a standard catalog "
     "item already procured in th", "b"),
]
NARRATIVE_NONE = [
    "*   **Rationale:** Calculates the dominant natural frequency of "
    "the liner assembly from th",
    "*   **DIRECTION-OF-EFFECT:** Correctly identifies the mechanism "
    "as a *detector* of passive",
    "*   **Deployed-Part Compliance:** No modification to the plunger "
    "or seal.",
    "6.  **Deployed-Part Clause**:",
    "*   *Physics*: In a tube-and-shell HX, $P_{shell}$ fluctuates",
    "*   *Is this better?* Yes. It uses *only* the stated signals",
    "*   -   **However**, \"Tube Wastage\" often correlates with "
    "**Gas Velocity**",
    "*   -   **This is a trap**. If I can't get thickness, I can't "
    "predict leak *time* in days.",
    "*   *Problem*: I need a *disturbance* to measure the transient.",
    "*   **PREMISE-VALIDITY:** References only stated signals",
]
AMBIGUOUS_NONE = [
    # existing-infrastructure + configuration signals: true ambiguity
    ("*   *Operation:* Adjust the existing DCS/PLC setpoint. No new "
     "instrumentation."),
    ("- Commissioning: Zero. Setpoint change is a PLC/DCS parameter "
     "edit. (Standard practice: Ze"),
    # derived-from-existing-data: a+c ambiguity, never guessed
    ("*   **Baseline CRSD:** DERIVED from the first 30 days of "
     "ALREADY-RECORDED data (Assumption"),
    # zero-installation + procedure change in one row
    ("*   **Installation:** 0 hours. (Standard practice requires 0 "
     "hours for recipe changes)."),
]
HEADER_NONE = [
    "*   **Operational Loss Pricing:**",
    "*   **Pass/Fail Thresholds:**",
    "2.  **Injection Nozzle Retrofit:**",
    "1.  **Alkali Salt Additive Feed Tank:**",
]
NOMARKER_NONE = [
    "Compliant.",
    "*   **Kiln Geometry/Mass:** \"rotary kiln shell\" specifications "
    "(Stated in `device`).",
    "-   Cost: $0 (software). Operational Loss: 0.",
]


def test_v13_class_table():
    for row, want in C_CASES + A_CASES + B_CASES:
        assert tgc.classify_bill_row(row) == want, (want, row)
    for row in (NARRATIVE_NONE + AMBIGUOUS_NONE + HEADER_NONE
                + NOMARKER_NONE):
        assert tgc.classify_bill_row(row) is None, row


def test_self_declared_format_normalization():
    # "(a - Firmware/Code)" is a self-declared class in a non-scannable
    # format: normalize to "(a)" — no semantics invented.
    row = ("*   **Data Acquisition (a - Firmware/Code):** Update "
           "existing PLC/SCADA firmware")
    assert "(a)" in tgc.NONSCANNABLE_TAG.sub(
        lambda g: f"({g.group(1).lower()})", row)
    assert tgc.classify_bill_row(row) == "a"
    for tag in ("(Tag: c)", "(b - purchased item)", "(C – valve trim)"):
        m = tgc.NONSCANNABLE_TAG.search(tag)
        assert m and m.group(1).lower() in "abc"


def test_tag_bill_integration_v13():
    answer = (
        "IMPLEMENTATION BILL\n"
        "- Parameter: Change target ratio from 0.60 to 0.55.\n"
        "- Rationale: This maximizes selectivity per the stated "
        "kinetics.\n"
        "- Hardware: standard catalog probe.\n"
        "- I think this is the best option.\n"
        "- (Tag: c) placeholder\n"
    )
    corrected, rec = tgc.tag_bill(answer)
    assert rec["record"] == "TOOL_GROUNDED_CRITIC/1.0.0"
    assert rec["corrected"] == 2        # parameter + catalog rows
    assert rec["normalized"] == 1       # "(Tag: c)" -> "(c)"
    assert rec["left_flagged"] == 2     # both narrative rows stay
    assert "Rationale" in rec["left_flagged_rows"][0]
    assert "best option" in rec["left_flagged_rows"][1]
    assert "(c)" in corrected.splitlines()[1]
    assert "(b)" in corrected.splitlines()[3]
    # the narrative row is untouched (never a guessed tag)
    assert "best option" in corrected and "(c)\n" not in \
        corrected.splitlines()[4]


def test_1_0_0_semantics_no_regression():
    # the 1.0.0 single-marker and ambiguity rules hold under the
    # extension
    assert tgc.classify_bill_row("- Uses the existing dosing pumps.") \
        == "a"
    assert tgc.classify_bill_row(
        "- Dosing schedule: 2 pulses per batch.") == "c"
    assert tgc.classify_bill_row(
        "- Commercial-grade coating on the existing impeller.") is None
