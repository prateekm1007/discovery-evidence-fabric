"""R478 — the ONE survivor authority (external audit P1-12).

The server download gate and the bridge artifact gate consume the SAME
attestation: toscanini/bridge_gate.py::survivor_attested (pure). This
battery is authored by the CTO session, not the implementer (Art. III
— the verifier never trusts the claimant).

Under test:
  * survivor_attested legs (closed vocabulary, invention_id,
    spec-hash/selection evidence, status-None guard);
  * the server gate consumes exactly that authority (vocabulary
    identity, dead-end class deleted, legacy conservative branch);
  * _legacy_release_disclosure (Art. XV — surfaced, never gating);
  * the bridge regression: _survivor_recorded's outer contract is
    unchanged by the extraction (present/absent records).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toscanini.bridge_gate import (  # noqa: E402
    _NON_SURVIVOR_RELEASE_STATUSES, _survivor_recorded,
    survivor_attested)
from toscanini.server import (  # noqa: E402
    _legacy_release_disclosure, survivor_release_gate)


def _rel(status, inv="inv-1", spec="a" * 64):
    return {"status": status, "invention_id": inv,
            "invention_spec_hash": spec}


class TestSurvivorAttested:

    @pytest.mark.parametrize("status", [
        "DISCOVERY_INCOMPLETE", "NOT_A_SURVIVOR", "DISABLED_BY_CONFIG"])
    def test_closed_non_survivor_vocabulary_never_attests(self, status):
        attested, evidence = survivor_attested(_rel(status), None)
        assert attested is False
        assert evidence["non_survivor_statuses"] == list(
            _NON_SURVIVOR_RELEASE_STATUSES)

    def test_missing_status_never_attests(self):
        attested, _ = survivor_attested({"invention_id": "inv-1"}, None)
        assert attested is False

    def test_none_record_never_attests(self):
        attested, _ = survivor_attested(None, {"picked": True})
        assert attested is False

    def test_invention_id_required(self):
        attested, _ = survivor_attested(
            _rel("HELD_FOR_HUMAN_REVIEW", inv=None), None)
        assert attested is False

    def test_spec_hash_leg(self):
        attested, evidence = survivor_attested(
            _rel("HELD_FOR_HUMAN_REVIEW"), None)
        assert attested is True
        assert evidence["survivor_selection_passed"] is True
        assert evidence["survivor_selection_present"] is False

    def test_selection_leg_substitutes_for_spec_hash(self):
        attested, evidence = survivor_attested(
            _rel("HELD_FOR_HUMAN_REVIEW", spec=None), {"picked": True})
        assert attested is True
        assert evidence["invention_spec_hash_present"] is False
        assert evidence["survivor_selection_present"] is True

    def test_no_evidence_legs_fail(self):
        attested, evidence = survivor_attested(
            _rel("HELD_FOR_HUMAN_REVIEW", spec=None), None)
        assert attested is False
        assert evidence["survivor_selection_passed"] is False

    def test_authority_evidence_names_the_authority(self):
        _, evidence = survivor_attested(_rel("RELEASED"), None)
        assert evidence["authority"] == "DISCOVERY_RELEASE.json"


class TestServerGateConsumesTheAuthority:

    @pytest.mark.parametrize("status", [
        "DISCOVERY_INCOMPLETE", "NOT_A_SURVIVOR", "DISABLED_BY_CONFIG"])
    def test_authority_rejection_blocks(self, status):
        out = survivor_release_gate(None, _rel(status))
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        assert out["authority"] == "DISCOVERY_RELEASE.json"

    def test_attested_authority_serves(self):
        assert survivor_release_gate(None, _rel("RELEASED")) is None

    def test_dead_end_class_is_deleted(self):
        # the R452-era RELEASE_RECORDS_DISAGREE class must be gone
        out = survivor_release_gate({"status": "RELEASED"},
                                    _rel("HELD_FOR_HUMAN_REVIEW"))
        assert out is None


class TestLegacyDisclosure:

    def test_disagreeing_legacy_record_disclosed(self):
        headers = _legacy_release_disclosure(
            {"status": "NOT_A_SURVIVOR"}, _rel("HELD_FOR_HUMAN_REVIEW"))
        assert headers == [
            ("X-Release-Authority", "DISCOVERY_RELEASE"),
            ("X-Legacy-Release-Proof-Status", "NOT_A_SURVIVOR")]

    def test_agreeing_records_disclose_nothing(self):
        assert _legacy_release_disclosure(
            {"status": "RELEASED"}, _rel("RELEASED")) == []

    def test_absent_legacy_record_discloses_nothing(self):
        assert _legacy_release_disclosure(None, _rel("RELEASED")) == []


class TestBridgeRegression:

    def test_present_attested_record(self, tmp_path):
        (tmp_path / "DISCOVERY_RELEASE.json").write_text(json.dumps(
            _rel("HELD_FOR_HUMAN_REVIEW")))
        out = _survivor_recorded(tmp_path)
        assert out["recorded"] is True
        assert out["evidence"]["authority"] == "DISCOVERY_RELEASE.json"

    def test_present_rejected_record(self, tmp_path):
        (tmp_path / "DISCOVERY_RELEASE.json").write_text(json.dumps(
            _rel("NOT_A_SURVIVOR")))
        out = _survivor_recorded(tmp_path)
        assert out["recorded"] is False

    def test_absent_record_keeps_the_legacy_path(self, tmp_path):
        # the extraction MUST NOT change the absent-record contract:
        # recorded=True (the legacy invention-side check decides)
        out = _survivor_recorded(tmp_path)
        assert out["recorded"] is True
        assert out["evidence"]["authority"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
