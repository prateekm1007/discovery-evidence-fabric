"""tests/test_r6_a2_calibration_registry.py — owner audit round 2026-11-13.

A2 `a2_adversarial_gauntlet/2.1.0` (the v4.2 ATTACKER-COMPUTES DEV
iteration) must EARN its calibration from its OWN sealed measurement:
it changed verdict logic (rule 4.5), so it cannot inherit the 2.0.0
record. The R505 strong-ring campaign measured it on four rings and
every run failed the pre-registered bars; those are
MEASUREMENT_RESULTS records, not a sealed MEASUREMENT.json + SEAL.json
pair. Until such a pair ships under the pinned names, the state is
fail-closed UNKNOWN_NOT_CALIBRATED with no terminal kill authority.

Pins:
  1. the registry entry exists and is NOT an inheritance alias;
  2. its pinned record names are distinct from 2.0.0's;
  3. resolve_state on the live tree is UNKNOWN_NOT_CALIBRATED;
  4. the entry CAN earn CALIBRATED / NOT_CALIBRATED from synthetic
     sealed records patched into the registry — the derivation is by
     numbers, never asserted;
  5. the engine's A2_GAUNTLET_VERSION matches the registered id.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import attacker_calibration as gate  # noqa: E402
from discovery_fabric.a2 import adversarial as a2  # noqa: E402

V20 = "a2_adversarial_gauntlet/2.0.0"
V42 = "a2_adversarial_gauntlet/2.1.0"


def _sealed(tmp: Path, *, tpr: float, fpr: float,
            coverage: float = 1.0, parse: float = 1.0):
    meas = {
        "metrics": {"false_kill_rate_on_known_good": fpr,
                    "coverage": coverage,
                    "parse_completeness": parse},
        "scoped_tpr_diagnostic": {"tpr": tpr},
        "threshold_verdict": {"calibrated": True},
        "n_cases_attacked": 21,
        "attacker_ring": {"provider": "xkiro", "model": "pinned"},
    }
    seal = {"pre_registered_thresholds": {
        "tpr_min": 0.75, "fpr_max": 0.30,
        "coverage_min": 0.875, "parse_completeness_min": 0.875}}
    m = tmp / "m.json"
    s = tmp / "s.json"
    m.write_text(json.dumps(meas), encoding="utf-8")
    s.write_text(json.dumps(seal), encoding="utf-8")
    return {"measurement": m, "seal": s}


def test_engine_version_is_registered():
    assert a2.A2_GAUNTLET_VERSION == V42
    assert V42 in gate.INSTRUMENT_MEASUREMENTS


def test_v42_is_not_an_inheritance_alias():
    entry = gate.INSTRUMENT_MEASUREMENTS[V42]
    assert "inherited_from" not in entry
    assert "inheritance_basis" not in entry
    v20 = gate.INSTRUMENT_MEASUREMENTS[V20]
    # distinct pinned record names even while both are absent: a future
    # 2.1.0 seal can never silently bind to the 2.0.0 measurement
    assert entry["measurement"] != v20["measurement"]
    assert entry["seal"] != v20["seal"]


def test_live_state_is_fail_closed_uncalibrated():
    st = gate.resolve_state(instrument_version=V42)
    assert st["state"] == "UNKNOWN_NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    assert st["instrument"] == V42
    assert "absent" in st["reason"] or "pinned-digest" in st["reason"]


def test_entry_earns_state_from_its_own_numbers(tmp_path):
    with mock.patch.dict(gate.INSTRUMENT_MEASUREMENTS,
                         {V42: _sealed(tmp_path, tpr=1.0, fpr=0.0)}):
        st = gate.resolve_state(instrument_version=V42)
    assert st["state"] == "CALIBRATED"
    assert st["terminal_kill_admissible"] is True
    assert st["measured"]["tpr_scoped"] == 1.0


def test_failing_numbers_stay_not_calibrated(tmp_path):
    # the R505 measured shape: TPR below the sealed bar
    with mock.patch.dict(gate.INSTRUMENT_MEASUREMENTS,
                         {V42: _sealed(tmp_path, tpr=0.3636, fpr=0.0)}):
        st = gate.resolve_state(instrument_version=V42)
    assert st["state"] == "NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    assert st["measured"]["tpr_scoped"] == 0.3636


def test_incomplete_metrics_stay_unknown_not_calibrated(tmp_path):
    # the coverage/parse-incomplete R505 runs must never be rounded up
    with mock.patch.dict(gate.INSTRUMENT_MEASUREMENTS,
                         {V42: _sealed(tmp_path, tpr=0.9, fpr=0.0,
                                       coverage=None, parse=1.0)}):
        st = gate.resolve_state(instrument_version=V42)
    assert st["state"] == "UNKNOWN_NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
