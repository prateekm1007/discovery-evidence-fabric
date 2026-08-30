#!/usr/bin/env python3
"""One-time cemetery chain restoration (2026-08-30).

DEFECT MEMORY (Art. XXXI): the engine kill path (run.py::_cemetery_update)
round-tripped the whole cemetery through save_cemetery() during the MVP UI
runs, DESTROYING the internal hash chain the R374 cycle installed at
50d1664a (52 chained entries -> 57 unchained). Deletions were verified
absent against git (all 52 committed ids present in the 57-entry working
file) — append-only HELD, only the chain broke. This script restores the
chain from the CURRENT 57-entry state using the same laundering-safe
extend logic now embedded in append_entries_to_cemetery_file, then
verifies with the R374 canonical verifier (premium_package_factory/r374/
pathway._chain_verify).

The chain re-baselines TODAY: history before today is protected by git
commits (46/52/57 entry states), history after by the internal chain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from orchestrator import mechanism_cemetery as mc  # noqa: E402

PATH = REPO / "MECHANISM_CEMETERY" / "CEMETERY.json"


def main() -> int:
    before = json.loads(PATH.read_text())
    n_before = len(before.get("entries", []))
    chained_before = sum(1 for e in before.get("entries", [])
                         if "prev_entry_sha256" in e)
    mc._chain_extend(before)   # laundering-safe: only unchained entries
    PATH.write_text(json.dumps(before, indent=2, ensure_ascii=False))

    after = json.loads(PATH.read_text())
    chained_after = sum(1 for e in after.get("entries", [])
                        if "prev_entry_sha256" in e)

    # verify with the R374 canonical verifier
    from premium_package_factory.r374 import pathway
    v = pathway._chain_verify(after)

    print(f"entries: {n_before} (unchanged: {len(after['entries']) == n_before})")
    print(f"chained: {chained_before} -> {chained_after}")
    print(f"r374 canonical verify: {v}")
    assert v.get("valid") is True, "chain verify failed after backfill"
    assert len(after["entries"]) == n_before, "entry count changed!"
    print("CHAIN RESTORED — deletion detection active again")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
