"""tests/test_r10_experiment_contract.py — R10 P0 item 5 (owner round
2026-11-13): the experiment contract + the composer's honesty floor.

The audit's measured loose shapes, each pinned as a NEGATIVE:
  * new02's `n = 12 months` — a DURATION is not a count of
    independent experimental units;
  * new07's `n = 2,880 measurements` — repeated measurements are not
    independent units (the device/failure-case count is n);
  * new04's `n = 1 full season` — a single-unit run is a PILOT;
  * a bare temperature with no scale ('at 60 for 3000 h');
  * an ASSUMPTION value with no selection rationale and no
    calibration/sensitivity path (the p02 70 C / 5000 h / 15% audit
    case).
And the owner's PRESERVED positive cases:
  * the nickel-parameter fabrication case STAYS a violation (the
    unsupported EVIDENCE-BACKED value is never admitted);
  * the real unit-count protocol (n = 20 cells) and a rationale-carrying
    ASSUMPTION line PASS — no over-firing.
Hermetic: pure functions on string fixtures (Art. IX).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import (  # noqa: E402
    validate_answer, _experiment_contract_violations,
    _assumption_rationale_violations)


class TestExperimentContractNDistinctUnits:
    def test_n_stated_in_time_units_is_rejected(self):
        seg = ("VALIDATION PROTOCOL: n = 12 months of field data; "
               "alarm when slipring resistance exceeds mean + 3 sigma")
        out = _experiment_contract_violations(seg, False)
        assert out and "TIME units" in out[0], out

    def test_n_time_units_passes_on_real_unit_counts(self):
        seg = ("VALIDATION PROTOCOL: fleet of n = 120 machines "
               "monitored for 12 months; detection lead >= 30 days")
        assert _experiment_contract_violations(seg, False) == []

    def test_repeated_measurements_are_not_independent_units(self):
        seg = ("VALIDATION PROTOCOL: 30-day online monitoring; "
               "n = 2,880 measurements at 15-minute resolution; "
               "detection when d[H2]/dt exceeds the threshold")
        out = _experiment_contract_violations(seg, False)
        assert out and "repeated measurements" in out[0], out

    def test_n_one_full_season_is_a_single_unit_pilot(self):
        seg = ("VALIDATION PROTOCOL: n = 1 full season pilot on the "
               "chiller rig; fouling factor trend exceeds 15%")
        out = _experiment_contract_violations(seg, False)
        assert out and "SINGLE-UNIT pilot" in out[0], out

    def test_cycles_stay_a_valid_fatigue_unit(self):
        seg = ("FALSIFICATION TEST: at 60 C for 10^7 cycles on "
               "n = 12 bearings; fail when crack length exceeds "
               "0.5 mm")
        assert _experiment_contract_violations(seg, True) == []

    def test_bare_temperature_without_scale_is_flagged(self):
        seg = ("FALSIFICATION TEST: run at 60 for 3000 hours with "
               "n = 20 cells; fail when fade exceeds 15%")
        out = _experiment_contract_violations(seg, True)
        assert any("temperature stated without a unit" in v
                   for v in out), out


class TestAssumptionRationale:
    def test_assumption_without_rationale_or_sensitivity_fails(self):
        ans = ("ASSUMPTION PARAMETER: charge temperature = 70 C\n"
               "ASSUMPTION PARAMETER: target float life = 5000 hours")
        out = _assumption_rationale_violations(ans)
        assert len(out) == 2, out
        assert "selection rationale" in out[0]

    def test_assumption_with_rationale_passes(self):
        ans = ("ASSUMPTION PARAMETER: charge temperature = 70 C\n"
               "  chosen from the typical VRLA float-charge band in "
               "the manufacturer guideline")
        assert _assumption_rationale_violations(ans) == []

    def test_assumption_with_sensitivity_path_passes(self):
        ans = ("ASSUMPTION PARAMETER: float voltage = 2.27 V/cell\n"
               "A sensitivity sweep over 2.20-2.35 V/cell brackets "
               "the float-life claim.")
        assert _assumption_rationale_violations(ans) == []


class TestFullValidateAnswerIntegration:
    def test_p02_nickel_fabrication_case_still_violates(self):
        """保留 unsupported nickel 参数的造假案例 (owner R10): the
        fabricated EVIDENCE-BACKED nickel value against a packet that
        never states it REMAINS a violation — the experiment contract
        never widens the honesty floor."""
        packet = [{"id": "doi:10.1016/j.powsour.2019.01.001",
                   "title": "Lead-acid battery grid corrosion review",
                   "abstract": ("Grid corrosion growth of positive "
                                "plates progresses with float charge "
                                "voltage and temperature; anode grid "
                                "alloys with calcium and tin show "
                                "reduced corrosion rates.")}]
        ans = (
            "PROPOSAL: revise the float-charge regime.\n\n"
            "EVIDENCE-BACKED PARAMETER: nickel coating thickness = "
            "15 um [doi:10.1016/j.powsour.2019.01.001]\n"
            "ASSUMPTION PARAMETER: float voltage = 2.27 V/cell ("
            "typical VRLA float band)\n"
            "ASSUMPTION PARAMETER: test duration = 5000 hours "
            "(conservative industry standard)\n\n"
            "FALSIFICATION TEST: at 60 C for 5000 hours with "
            "n = 20 cells; fail when capacity fade exceeds 15%")
        res = validate_answer(ans, "intervention-proposal",
                              packet=packet)
        assert res.get("valid") is not True, res
        joined = " ".join(res.get("violations") or [])
        assert ("nickel" in joined or "unrelated_source" in joined
                or "value_not_in_source" in joined
                or "does not jointly support" in joined), joined

    def test_clean_honest_answer_validates(self):
        packet = [{"id": "doi:10.1016/j.powsour.2019.01.001",
                   "title": "Lead-acid battery grid corrosion review",
                   "abstract": ("Grid corrosion growth of positive "
                                "plates progresses with float charge "
                                "voltage and temperature; anode grid "
                                "alloys with calcium and tin show "
                                "reduced corrosion rates at 60 C.")}]
        ans = (
            "PROPOSAL: revise the float-charge regime.\n\n"
            "EVIDENCE-BACKED PARAMETER: float charge voltage = 2.27 "
            "V/cell [doi:10.1016/j.powsour.2019.01.001]\n"
            "ASSUMPTION PARAMETER: test duration = 5000 hours "
            "(conservative industry standard)\n\n"
            "FALSIFICATION TEST: at 60 C for 5000 hours with "
            "n = 20 cells; fail when capacity fade exceeds 15%")
        res = validate_answer(ans, "intervention-proposal",
                              packet=packet)
        assert res.get("valid") is True, res.get("violations")

    def test_predictor_protocol_with_time_n_violates(self):
        ans = (
            "INDICATOR: slipring contact resistance drift in "
            "mOhm/1000h\n"
            "THRESHOLD: mean + 3 sigma computed from 30 days of "
            "healthy-fleet telemetry\n"
            "VALIDATION PROTOCOL: n = 12 months of field data; "
            "detection lead >= 30 days")
        res = validate_answer(ans, "predictor-design")
        assert res.get("valid") is not True
        joined = " ".join(res.get("violations") or [])
        assert "TIME units" in joined, joined
