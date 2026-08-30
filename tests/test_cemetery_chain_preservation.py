"""Regression tests — the engine kill path must PRESERVE the cemetery's
internal hash chain (Art. XXXI defect memory, 2026-08-30).

DEFECT: run.py::_cemetery_update round-tripped the whole cemetery through
save_cemetery() during the MVP UI runs, silently destroying the chain
installed at 50d1664a (52 chained -> 57 unchained). Deletion detection was
OFF until the R374 append-only test caught it. These tests pin the fixed
architecture: the kill path appends via
append_entries_to_cemetery_file(), which is byte-preserving AND
chain-maintaining.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator import mechanism_cemetery as mc


@pytest.fixture()
def cemetery_file(tmp_path, monkeypatch):
    path = tmp_path / "CEMETERY.json"
    # seed with two chained entries
    seed = {"description": "test cemetery", "entries": [
        {"entry_id": "CE-1", "kill_reason": "r1"},
        {"entry_id": "CE-2", "kill_reason": "r2"},
    ]}
    mc._chain_extend(seed)
    path.write_text(json.dumps(seed, indent=2))
    monkeypatch.setattr(mc, "CEMETERY_PATH", path)
    return path


def _new_entry(eid):
    return mc.CemeteryEntry(
        entry_id=eid, territory_id="T", mechanism_name="m",
        proposed_version="v1", killed_at_version="v1",
        kill_reason="killed", what_was_proposed="x", why_it_failed="y",
        reusable_lesson="z", what_to_avoid="w",
        evidence_sources=["e1"], epistemic_class="FAILURE_LESSON")


class TestKillPathChainPreservation:
    def test_append_maintains_chain(self, cemetery_file):
        mc.append_entries_to_cemetery_file([_new_entry("CE-3")])
        d = json.loads(cemetery_file.read_text())
        assert len(d["entries"]) == 3
        assert all("prev_entry_sha256" in e for e in d["entries"])
        # canonical R374 verifier agrees
        from premium_package_factory.r374 import pathway
        assert pathway._chain_verify(d)["valid"] is True

    def test_append_preserves_existing_bytes(self, cemetery_file):
        before = json.loads(cemetery_file.read_text())
        mc.append_entries_to_cemetery_file([_new_entry("CE-3")])
        after = json.loads(cemetery_file.read_text())
        # existing entries identical (incl. chain fields)
        assert after["entries"][:2] == before["entries"]

    def test_save_cemetery_still_exists_but_is_not_the_append_path(self):
        """save_cemetery remains for INITIALIZATION (main()); the engine
        kill path must never CALL it — pinned by source inspection of
        call syntax (docstring mentions don't count)."""
        import inspect
        import re
        from discovery_fabric.engine import run as engine_run
        src = inspect.getsource(engine_run.EngineRun._cemetery_update)
        assert not re.search(r"\bsave_cemetery\s*\(", src), \
            "kill path must not CALL save_cemetery (chain destroyer)"
        assert re.search(r"\bappend_entries_to_cemetery_file\s*\(", src)

    def test_deletion_detectable_after_appends(self, cemetery_file):
        """The property that broke live: after ANY number of appends, a
        deletion must still be detected by the canonical verifier."""
        mc.append_entries_to_cemetery_file([_new_entry("CE-3")])
        mc.append_entries_to_cemetery_file([_new_entry("CE-4")])
        d = json.loads(cemetery_file.read_text())
        d["entries"] = d["entries"][1:]  # simulate deletion of entry 0
        from premium_package_factory.r374 import pathway
        v = pathway._chain_verify(d)
        assert v["valid"] is False
