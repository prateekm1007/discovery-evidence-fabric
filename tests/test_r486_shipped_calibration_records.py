"""R486 — the shipped calibration records battery.

The measured defect: the R484/R485 closure runs executed in production
images whose round-tree pruning had removed R447/ — the v2 attacker
measurement — so the R417 escalation gate recorded
UNKNOWN_NOT_CALIBRATED / measured:null ("no committed measurement")
while the repository held a committed NOT_CALIBRATED measurement
(FPR 1.0 vs sealed bar 0.3). The fail-closed direction was correct;
the recorded reason was infrastructure-degraded (Art. LXI class).

The fix under test: the four calibration records ship inside the
engine tree (discovery_fabric/engine/calibration_records/, which no
round-dir pruning touches), tamper-evident via DIGESTS.json. The gate
verifies the pinned digests before reading; a mismatch fails closed
WITHOUT falling back to another instrument's record.

What may NEVER change (the assertions are constitutional, not
convenience): the derived state for every measured instrument version
is NOT_CALIBRATED with measured FPR 1.0 — the gate still refuses
terminal kills; no threshold, metric, or verdict moved (Art. VII).
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import attacker_calibration as ac  # noqa: E402

SHIPPED = REPO / "discovery_fabric" / "engine" / "calibration_records"

MEASURED_VERSIONS = (
    "independent_attack/1.0.0",
    "independent_attack/2.0.0",
    "independent_attack/2.1.0",
)


def test_shipped_digests_match_canonical_records():
    """Every shipped copy is byte-identical to its canonical round-dir
    record (Art. X: the round dirs remain the repository authority; the
    shipment is a provable duplicate, not a fork)."""
    pins = json.loads((SHIPPED / "DIGESTS.json").read_text())
    for name, rel in pins["canonical_sources"].items():
        canonical = REPO / rel
        assert canonical.exists(), f"canonical record missing: {rel}"
        shipped = SHIPPED / name
        assert shipped.exists(), f"shipped copy missing: {name}"
        assert pins["sha256"][name] == ac._sha(shipped)
        assert pins["sha256"][name] == ac._sha(canonical)


def test_shipped_dir_is_inside_the_engine_tree():
    """The shipment lives under discovery_fabric/engine/ — the code tree
    every deploy ships — not under a prunable round dir."""
    assert SHIPPED.is_dir()
    assert "calibration_records" in str(SHIPPED)
    parts = SHIPPED.relative_to(REPO).parts
    assert parts[0] == "discovery_fabric" and parts[1] == "engine"
    for pins in (json.loads((SHIPPED / "DIGESTS.json").read_text()),):
        for rel in pins["canonical_sources"].values():
            assert rel.split("/")[0].startswith("R"), (
                "canonical source must stay in its round dir")


@pytest.mark.parametrize("version", MEASURED_VERSIONS)
def test_every_measured_version_resolves_the_true_measured_state(version):
    """The R484/R485 defect class is closed: each registered version
    derives NOT_CALIBRATED from ITS OWN committed measurement with the
    measured numbers attached — never the degraded
    UNKNOWN_NOT_CALIBRATED / measured:null shape the deployed runs
    recorded after pruning."""
    st = ac.resolve_state(instrument_version=version)
    assert st["state"] == "NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    measured = st["measured"]
    assert measured["fpr_known_good"] == 1.0
    assert measured["tpr_scoped"] == 1.0
    assert measured["coverage"] == 1.0
    assert measured["parse_completeness"] == 1.0
    assert st["measurement_path"] and "calibration_records" in st["measurement_path"]
    assert "measured FPR 1.0" in st["reason"]


def test_tampered_shipment_fails_closed_at_read_time(tmp_path):
    """A mutated shipped record is refused AT READ TIME (the import-time
    pin alone would miss mid-process mutation): the digest
    re-verification fails and the gate fails closed — never reading the
    mutated bytes, never substituting another instrument's measurement
    (Art. IV/IX/XXVIII)."""
    victim = SHIPPED / "r447_attacker_v2_measurement.json"
    original = victim.read_bytes()
    try:
        victim.write_bytes(original + b" ")
        st = ac.resolve_state(instrument_version="independent_attack/2.1.0")
        assert st["state"] == "UNREADABLE_NOT_CALIBRATED"
        assert st["terminal_kill_admissible"] is False
        assert st.get("measured") is None
        assert "pinned-digest" in st["reason"]
    finally:
        victim.write_bytes(original)
    # the honest restore is itself verified: the state is measurable again
    st = ac.resolve_state(instrument_version="independent_attack/2.1.0")
    assert st["state"] == "NOT_CALIBRATED"
    assert st["measured"]["fpr_known_good"] == 1.0


def test_registry_entry_without_shipped_record_fails_closed(tmp_path,
                                                            monkeypatch):
    """Simulated deploy pruning of the shipment itself: a registry entry
    whose pinned record is absent fails closed — never a fallback to the
    R412 record for a v2 instrument (Art. IV/XXVIII)."""
    monkeypatch.setitem(
        ac.INSTRUMENT_MEASUREMENTS, "independent_attack/2.0.0",
        {"measurement": None, "seal": None})
    st = ac.resolve_state(instrument_version="independent_attack/2.0.0")
    assert st["state"] == "UNKNOWN_NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    assert st.get("measured") is None
    assert "pinned-digest" in st["reason"]

    monkeypatch.setitem(
        ac.INSTRUMENT_MEASUREMENTS, "independent_attack/2.0.0",
        {"measurement": tmp_path / "absent.json",
         "seal": tmp_path / "absent_seal.json"})
    st = ac.resolve_state(instrument_version="independent_attack/2.0.0")
    assert st["state"] == "UNKNOWN_NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False


def test_gate_composition_carries_the_measured_numbers_at_consumption():
    """A v2.1.0 KILLED record at consumption becomes ESCALATED_OBJECTION
    whose escalation block carries the true measured FPR — the exact
    record shape the R484 closure run emitted, with the degraded
    measured:null repaired to the measured truth."""
    record = {
        "attack_version": "independent_attack/2.1.0",
        "overall": "KILLED",
        "kill_basis": [{"attack_class": "MECHANISM_FAILURE",
                        "basis": "sealed-corpus fixture basis"}],
        "items": [],
    }
    out = ac.gate_attack_record(record)
    assert out["overall"] == "ESCALATED_OBJECTION"
    assert out["raw_overall"] == "KILLED"
    esc = out["escalation"]
    assert esc["calibration_state"] == "NOT_CALIBRATED"
    assert esc["measured"]["fpr_known_good"] == 1.0
    assert esc["sealed_thresholds"]["fpr_max"] == 0.3
    assert esc["terminal_kill_admissible"] is False
    assert out["preserved_objections"] == record["kill_basis"]
    assert esc["reviewer_provenance"].startswith("AI_REVIEW")


def test_surviving_records_pass_through_untouched():
    """The gate touches only KILLED records (R417 semantics unchanged):
    SURVIVED/UNCERTAIN shapes return byte-identical."""
    rec = {"attack_version": "independent_attack/2.1.0",
           "overall": "SURVIVED_WITH_UNCERTAINTIES", "items": []}
    assert ac.gate_attack_record(rec) is rec


def test_explicit_override_paths_still_work():
    """The operator's verification entry point (explicit measurement +
    seal paths) is unchanged by the shipment."""
    st = ac.resolve_state(
        measurement_path=REPO / "R412" / "CALIBRATION" /
        "engine_independent_attack_measurement.json",
        seal_path=REPO / "R412" / "CALIBRATION" / "r412_calibration_seal.json",
        instrument_version="independent_attack/1.0.0")
    assert st["state"] == "NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    assert "R412" in st["measurement_path"]


def test_module_reimport_repins_clean():
    """The registry resolves at import time from pinned digests; a fresh
    import repins cleanly and every version still resolves measured."""
    mod = importlib.reload(ac)
    for version in MEASURED_VERSIONS:
        entry = mod.INSTRUMENT_MEASUREMENTS[version]
        assert entry["measurement"] is not None
        assert entry["seal"] is not None
    importlib.reload(ac)
