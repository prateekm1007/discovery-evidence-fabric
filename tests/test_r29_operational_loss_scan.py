#!/usr/bin/env python3
"""tests/test_r29_operational_loss_scan.py — regression pins for the
AM27 D1 / F38 OPERATIONAL-LOSS scan (the unpriced-curtailment defect
class).

POSITIVE pin uses the REAL violating bytes (Art. 22 real-bytes
acceptance): bench-p10 r26 V7 — the AM27-named F38 violation. The
answer duty-cycles the PRIMARY OUTPUT stage ("duty cycle: 8h on /
4h off" on the string inverter; "periodically interrupts the
high-voltage bias with zero-voltage intervals"; "1000 V for 8
hours, 0 V for 4 hours daily") while its burden ledger counts only
PLC wiring hours and asserts "Operation unchanged" — the ~33% daily
energy curtailment is entirely unpriced. The scan MUST fire.

THE FALSE-PRICING TRAP (byte-pinned): bench-p10's own PHYSICS CHECK
says "0.5% annual power loss constraint" — that is the problem's
pass criterion (the degradation idiom), NOT a curtailment price. A
scan that reads it as pricing would let the violation through; the
pin holds that it does not.

NEGATIVE pins — the auxiliary-process duty cycles the auditor scored
gap 0 with NO F38 finding must stay inert (the output-gating
discriminator):
  bench-p02  duty-cycle CHARGING-PROFILE modulation (charge
             controller firmware; float/discharge pulses — the
             battery's serviced function is not gated)
  bench-p07  duty-cycle electrochemical RESET (10 ms every 30 min on
             a sensor electrode; monitoring continues)
  bench-p12  periodic reverse-flow cleaning PULSE (auxiliary
             backpulse; the ledger also prices the valve's <5 W)
  dev-fu-005 one-time INSTALL cyclic loading (a procedure, not an
             operating regime)
  bench-p05  "cyclic loading" only as physics description + the
             test section (out of class)
plus every other intervention row of the r26 generation (p01, p03,
p04, p06, p08, p09, p11, eval-new01, eval-new03, eval-new05,
eval-sofc-redox, eval-sofc-thermal-cycling) and the 7 r27 V7.1
tuned rows (none duty-cycles a primary output stage), ALL 12
predictor rows (inert by construction), and three SYNTHETIC shape
pins:
  - a PRICED duty cycle (states "energy loss of 33% of daily
    production, counted against parity") must NOT fire;
  - a ZERO-LOSS night schedule ("bias-reset windows run only during
    non-producing hours; zero energy loss") must NOT fire;
  - an unpriced synthetic inverter on/off regime MUST fire.

Art. 19-style determinism: same bytes -> same findings, twice.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r29_operational_loss_scan import scan_operational_loss  # noqa: E402

R26 = REPO / "eval" / "pairs" / "r26_v7_catalog"
R27 = REPO / "eval" / "pairs" / "r27_v71_tuned"

CLEAN_R26 = [
    "bench-p01-pemfc-dehydration",
    "bench-p02-leadacid-grid-corrosion",
    "bench-p03-phe-biofouling",
    "bench-p04-pump-cavitation",
    "bench-p05-bridge-bearing-aging",
    "bench-p06-water-biofilm",
    "bench-p07-cgm-biofouling",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "bench-p12-mbr-fouling",
    "dev-fu-005-bridge-bearing",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
    "eval-new05-liion-balance-drift",
    "eval-sofc-redox",
    "eval-sofc-thermal-cycling",
]
CLEAN_R27 = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-sofc-thermal-cycling",
]


def _load(pairs_dir, pid):
    return json.loads((pairs_dir / f"{pid}.json").read_text(
        encoding="utf-8"))


def test_the_real_violation_fires():
    """The AM27/F38 named violation: bench-p10's 8h-on/4h-off inverter
    duty cycle with an unpriced ~33% daily energy curtailment."""
    rec = _load(R26, "bench-p10-pv-pid")
    v = scan_operational_loss(rec["a1_answer"], rec["question_type"])
    assert v, "the real F38 violation bytes must fire"
    findings = v["UNPRICED_OPERATIONAL_LOSS"]
    assert any("duty cycle" in f for f in findings)
    assert any("inverter" in f or "voltage bias" in f for f in findings)


def test_the_degradation_idiom_is_not_a_price():
    """The false-pricing trap: "0.5% annual power loss constraint" is
    the problem's pass criterion, not a curtailment pricing — the
    violation must still fire on the full bench-p10 bytes."""
    rec = _load(R26, "bench-p10-pv-pid")
    assert "power loss constraint" in rec["a1_answer"]
    v = scan_operational_loss(rec["a1_answer"], rec["question_type"])
    assert v, ("a degradation-threshold mention must not be read as "
               "operational-loss pricing")


def test_auxiliary_duty_cycles_stay_inert():
    """The auditor-scored-gap-0 auxiliary duty cycles: charging-profile
    modulation (p02), sensor-electrode reset (p07), cleaning pulses
    (p12), install-time cyclic loading (dev-fu-005), physics/test
    "cyclic loading" (p05) — none gates the primary output stage."""
    for pid in ("bench-p02-leadacid-grid-corrosion",
                "bench-p05-bridge-bearing-aging",
                "bench-p07-cgm-biofouling",
                "bench-p12-mbr-fouling",
                "dev-fu-005-bridge-bearing"):
        rec = _load(R26, pid)
        v = scan_operational_loss(rec["a1_answer"], rec["question_type"])
        assert not v, f"{pid} (auxiliary/none) must stay inert: {v}"


def test_all_other_intervention_rows_clean():
    for pid in CLEAN_R26:
        rec = _load(R26, pid)
        v = scan_operational_loss(rec["a1_answer"], rec["question_type"])
        assert not v, f"{pid} must not fire: {v}"


def test_r27_tuned_rows_clean():
    for pid in CLEAN_R27:
        rec = _load(R27, pid)
        v = scan_operational_loss(rec["a1_answer"], rec["question_type"])
        assert not v, f"{pid} must not fire: {v}"


def test_predictor_rows_inert():
    """Predictor answers are inert by construction (no intervention
    regime)."""
    n = 0
    for f in sorted(R26.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if str(rec.get("question_type", "")).startswith("predictor"):
            v = scan_operational_loss(rec["a1_answer"],
                                      rec.get("question_type", ""))
            assert not v, f"predictor {f.name} must be inert: {v}"
            n += 1
    assert n == 12, f"expected 12 predictor rows, saw {n}"


def test_synthetic_priced_duty_cycle_does_not_fire():
    """A duty cycle that STATES its loss and counts it against parity
    is priced — the scan's purpose is the unpriced shape."""
    ans = (
        "NOVELTY STATEMENT (INTERVENTION) — A duty cycle modification "
        "to the system voltage bias. IMPLEMENTATION BILL — (a) String "
        "inverter (duty cycle: 8 h on / 4 h off daily), (b) PLC timer "
        "relay. BURDEN LEDGER — Operational loss: the cycle curtails "
        "daily energy production by 33% (4 h of the 12 h cycle at 0 V "
        "export), counted against parity in this ledger. EXECUTABLE "
        "TEST — 5000 h aging run.")
    assert not scan_operational_loss(ans, "intervention-proposal")


def test_synthetic_zero_loss_night_schedule_does_not_fire():
    """A schedule that moves the gated windows off production hours and
    SAYS the loss is zero is priced."""
    ans = (
        "NOVELTY STATEMENT (INTERVENTION) — A duty cycle modification "
        "to the system voltage bias: the bias-reset windows run only "
        "during non-producing hours (night), so the schedule causes "
        "zero energy loss. IMPLEMENTATION BILL — (a) String inverter "
        "(duty cycle: reset windows at night only). BURDEN LEDGER — "
        "Operation: zero curtailment; all windows fall in "
        "non-generating hours.")
    assert not scan_operational_loss(ans, "intervention-proposal")


def test_synthetic_unpriced_inverter_regime_fires():
    ans = (
        "NOVELTY STATEMENT (INTERVENTION) — The intervention "
        "periodically interrupts the inverter output with "
        "zero-voltage intervals. IMPLEMENTATION BILL — (a) String "
        "inverter (modified duty cycle: 1000 V for 8 hours, 0 V for 4 "
        "hours daily), (b) PLC. BURDEN LEDGER — Installation: 1 h "
        "wiring. Operation unchanged.")
    v = scan_operational_loss(ans, "intervention-proposal")
    assert v and v["UNPRICED_OPERATIONAL_LOSS"]


def test_determinism():
    rec = _load(R26, "bench-p10-pv-pid")
    a = scan_operational_loss(rec["a1_answer"], rec["question_type"])
    b = scan_operational_loss(rec["a1_answer"], rec["question_type"])
    assert a == b
