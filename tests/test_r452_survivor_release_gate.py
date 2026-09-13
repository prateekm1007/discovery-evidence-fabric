"""R452 — the survivor-release gate (external audit B4 / AT-10).

The audit measured: 3 production runs carried downloadable
technology-transfer ZIPs against RELEASE_PROOF.status = NOT_A_SURVIVOR,
and on the same runs DISCOVERY_RELEASE said HELD_FOR_HUMAN_REVIEW — two
release artifacts disagreeing about the same run. Article XXXIX makes
the buyer-distribution repository the final authority; a NOT_A_SURVIVOR
package reaching a download route inverts that authority.

Under test:
  * the PURE gate function (toscanini/server.py::survivor_release_gate):
    a NOT_A_SURVIVOR verdict (from EITHER record) blocks every route,
    zero ZIPs reachable (no draft escape); disagreeing records block
    until reconciled, with the disagreement surfaced (Art. XV);
  * the WRITER half (package_compiler._update_discovery_release): the
    compiler binds hashes and never softens a survivor-gate verdict
    (the measured disagreement mechanism — the compiler overwrote
    NOT_A_SURVIVOR with HELD_FOR_HUMAN_REVIEW).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toscanini.server import survivor_release_gate  # noqa: E402


class TestSurvivorReleaseGate:

    def test_not_a_survivor_blocks_every_route(self):
        out = survivor_release_gate(
            {"status": "NOT_A_SURVIVOR"},
            {"status": "NOT_A_SURVIVOR"})
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        assert out["records_agree"] is True

    def test_survivor_verdict_from_either_record_blocks(self):
        # the audit's exact production shape: PROOF says rejected,
        # RELEASE says held — the conservative reading still blocks
        out = survivor_release_gate(
            {"status": "NOT_A_SURVIVOR"},
            {"status": "HELD_FOR_HUMAN_REVIEW"})
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        # the disagreement is surfaced, never hidden (Art. XV)
        assert out["records_agree"] is False
        assert out["release_proof_status"] == "NOT_A_SURVIVOR"
        assert out["discovery_release_status"] == "HELD_FOR_HUMAN_REVIEW"

    def test_disagreement_without_rejection_blocks_until_reconciled(self):
        out = survivor_release_gate(
            {"status": "RELEASED"},
            {"status": "HELD_FOR_HUMAN_REVIEW"})
        assert out is not None
        assert out["package_state"] == "RELEASE_RECORDS_DISAGREE"

    def test_agreeing_non_terminal_records_do_not_block(self):
        out = survivor_release_gate(
            {"status": "HELD_FOR_HUMAN_REVIEW"},
            {"status": "HELD_FOR_HUMAN_REVIEW"})
        assert out is None

    def test_absent_records_do_not_block(self):
        """No release records: the gate stays silent (never fabricated
        from absence, Art. XXV) — the visual-gate decision below still
        applies at the consumer."""
        assert survivor_release_gate(None, None) is None


class TestCompilerNeverSoftensSurvivorVerdict:

    def _compile_binding(self, tmp_path, initial_status):
        """Drive the REAL _update_discovery_release over a run dir whose
        DISCOVERY_RELEASE carries the survivor gate's verdict."""
        from discovery_fabric.engine.package_compiler import (
            _bind_release,
        )
        rel = tmp_path / "DISCOVERY_RELEASE.json"
        rel.write_text(json.dumps(
            {"status": initial_status, "release_id": "rel-x"}))
        binding = _bind_release(tmp_path, {
            "zip_path": "/tmp/does-not-matter.zip",
            "zip_sha256": "c" * 64,
            "final_invention_hash": "d" * 64,
            "quality_gate": {"package_quality": {"verdict": "PASS"}},
        }, {"release_id": "rel-x"})
        assert binding is not None
        return json.loads(rel.read_text())

    def test_not_a_survivor_survives_the_compiler(self, tmp_path):
        data = self._compile_binding(tmp_path, "NOT_A_SURVIVOR")
        assert data["status"] == "NOT_A_SURVIVOR", (
            "the compiler softened the survivor gate's verdict — the "
            "measured B4 disagreement mechanism is back")
        assert data["buyer_package_hash"] == "c" * 64

    def test_released_survives_the_compiler(self, tmp_path):
        data = self._compile_binding(tmp_path, "RELEASED")
        assert data["status"] == "RELEASED"

    def test_pre_release_state_is_held(self, tmp_path):
        data = self._compile_binding(tmp_path, "PENDING")
        assert data["status"] == "HELD_FOR_HUMAN_REVIEW"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
