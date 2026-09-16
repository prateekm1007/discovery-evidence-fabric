"""R452 — the survivor-release gate (external audit B4 / AT-10);
R478 — the single-authority contract change (external audit P1-12).

The R452 audit measured: 3 production runs carried downloadable
technology-transfer ZIPs against RELEASE_PROOF.status = NOT_A_SURVIVOR,
and on the same runs DISCOVERY_RELEASE said HELD_FOR_HUMAN_REVIEW — two
release artifacts disagreeing about the same run. Article XXXIX makes
the buyer-distribution repository the final authority; a NOT_A_SURVIVOR
package reaching a download route inverts that authority.

R478 (external audit P1-12) — DOCUMENTED CONTRACT CHANGE: the gate is
now ONE authority consumed by the server AND the bridge
(toscanini/bridge_gate.py::survivor_attested). DISCOVERY_RELEASE.json
attests (closed non-survivor vocabulary + invention_id + spec-hash/
selection evidence); a legacy RELEASE_PROOF no longer co-gates.
Disagreement WITHOUT rejection never blocks (disclosed on the served
bytes instead); the R452 corruption shape (legacy NOT_A_SURVIVOR
against an attesting authority record) blocks DECISIVELY with a named
conflict class and a re-adjudication path — never the old dead-end
"reconcile the records" state.

Under test:
  * the PURE gate function (toscanini/server.py::survivor_release_gate)
    across the authority matrix;
  * the WRITER half (package_compiler._update_discovery_release): the
    compiler binds hashes and never softens a survivor-gate verdict
    (the measured disagreement mechanism — unchanged by R478).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toscanini.server import survivor_release_gate  # noqa: E402


def _attested(status="HELD_FOR_HUMAN_REVIEW"):
    """A DISCOVERY_RELEASE record the authority attests (all three legs
    present: non-survivor-free status, invention_id, spec hash)."""
    return {"status": status, "invention_id": "inv-r478",
            "invention_spec_hash": "a" * 64}


class TestSurvivorReleaseGate:

    def test_not_a_survivor_blocks_every_route(self):
        out = survivor_release_gate(
            {"status": "NOT_A_SURVIVOR"},
            {"status": "NOT_A_SURVIVOR"})
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        assert out["authority"] == "DISCOVERY_RELEASE.json"
        assert out["records_agree"] is True

    def test_corruption_shape_blocks_decisively(self):
        # the R452 production shape: legacy PROOF says rejected while
        # the authority record attests — a NAMED conflict with a real
        # re-adjudication path, never the old dead-end block
        out = survivor_release_gate(
            {"status": "NOT_A_SURVIVOR"}, _attested())
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        assert out["conflict_class"] == (
            "LEGACY_PROOF_REJECTION_VS_ATTESTED_RELEASE")
        assert "re-adjudicate" in out["reconciliation"]
        assert out["records_agree"] is False
        assert out["release_proof_status"] == "NOT_A_SURVIVOR"
        assert out["discovery_release_status"] == "HELD_FOR_HUMAN_REVIEW"

    def test_softened_status_without_evidence_blocks(self):
        # a HELD wording with NO survivor evidence does not attest —
        # the softened-verdict guard (the R452 corruption mechanism
        # cannot smuggle a rejection back into a download)
        out = survivor_release_gate(
            {"status": "NOT_A_SURVIVOR"},
            {"status": "HELD_FOR_HUMAN_REVIEW"})
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        assert out["authority"] == "DISCOVERY_RELEASE.json"
        assert out["authority_evidence"]["invention_id"] is None

    def test_disagreement_without_rejection_never_blocks(self):
        # R478: the RELEASE_RECORDS_DISAGREE dead-end class is DELETED —
        # same-source artifacts on current runs; stale wording on old
        # ones is disclosed, never gating
        assert survivor_release_gate(
            {"status": "RELEASED"}, _attested()) is None

    def test_agreeing_non_terminal_records_do_not_block(self):
        assert survivor_release_gate(
            {"status": "HELD_FOR_HUMAN_REVIEW"}, _attested()) is None

    def test_absent_records_do_not_block(self):
        """No release records: the gate stays silent (never fabricated
        from absence, Art. XXV) — the visual-gate decision below still
        applies at the consumer."""
        assert survivor_release_gate(None, None) is None

    def test_legacy_rejection_with_no_authority_record_blocks(self):
        # pre-release-era shape: a recorded legacy rejection is never
        # silently served when no authority record exists to attest
        out = survivor_release_gate({"status": "NOT_A_SURVIVOR"}, None)
        assert out is not None
        assert out["package_state"] == "SURVIVOR_RELEASE_BLOCKED"
        assert "legacy" in out["authority"].lower()


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
