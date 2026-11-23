"""tests/test_alias_free_producer.py — R141 DELETE LIST: the producer
never emits a synthetic alias as an evidence_id.

The R138 defect class: the grid's structured items carried
item_id="lean_{record_id}" and NO "id", so a grid-sourced binding
named the alias ("lean_doi:...") — the admission resolver refused it
(fail closed, correct) but the PRODUCER was still emitting aliases.
Two layers landed this round:
  1. run.py's grid item now carries the REAL frozen record id ("id").
  2. mechanism_space._verbatim_eight_word_binding strips the known
     alias prefixes at the boundary (defense in depth).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.mechanism_space import (  # noqa: E402
    _verbatim_eight_word_binding)

SPAN = "moves measurement past the facility fence m1 to the lean "
REC_ID = "doi:10.5281/zenodo.22691356"


def _item(**over):
    base = {"title": f"chiller capacity record. {SPAN} the condenser",
            "abstract": "fouling raises kW/ton",
            "content_hash": "a" * 64}
    base.update(over)
    return base


def test_01_real_id_preferred() -> None:
    """A structured item with both "id" and an aliased item_id binds
    under the REAL id — never the alias."""
    mech = f"a mechanism that {SPAN} condenser approach"
    b = _verbatim_eight_word_binding(mech, [_item(id=REC_ID,
                                                  item_id=f"lean_{REC_ID}")])
    assert b["grounded"] is True
    assert b["evidence_id"] == REC_ID, (
        f"the binding must name the real record id, got {b['evidence_id']!r}")


def test_02_alias_item_id_stripped() -> None:
    """Defense in depth: an item carrying ONLY an aliased item_id (the
    legacy grid shape) still binds under the de-aliased id."""
    mech = f"a mechanism that {SPAN} condenser approach"
    b = _verbatim_eight_word_binding(mech, [_item(item_id=f"lean_{REC_ID}")])
    assert b["grounded"] is True
    assert b["evidence_id"] == REC_ID, (
        f"the alias prefix must be stripped at the producer boundary, "
        f"got {b['evidence_id']!r}")


def test_03_all_known_alias_prefixes() -> None:
    """Every ALIAS_PREFIXES-family prefix is stripped (lean_, doied_,
    ref_ — citation_identity's family)."""
    mech = f"a mechanism that {SPAN} condenser approach"
    for pfx in ("lean_", "doied_", "ref_"):
        b = _verbatim_eight_word_binding(
            mech, [_item(item_id=f"{pfx}{REC_ID}")])
        assert b["grounded"] and b["evidence_id"] == REC_ID, (
            f"prefix {pfx!r} not stripped: {b['evidence_id']!r}")


def test_04_no_grounding_without_span() -> None:
    """A mechanism without a verbatim 8-word span stays UNGROUNDED
    (the honest negative — never a sympathy pass)."""
    b = _verbatim_eight_word_binding(
        "a completely unrelated mechanism text with no span at all",
        [_item(id=REC_ID)])
    assert b["grounded"] is False
    assert b["evidence_id"] is None


def test_05_grid_items_carry_real_id() -> None:
    """Mechanics check on the run.py grid shape: the structured item
    dict has an "id" key (source-read pin; the run.py:1780 append)."""
    src = (REPO / "discovery_fabric" / "engine" / "run.py").read_text()
    assert '"id": str(_rec.get("id")),' in src, (
        "the grid structured item must carry the REAL frozen record id "
        "(the R141 DELETE LIST fix); run.py's grid append lost it")


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))  # noqa
