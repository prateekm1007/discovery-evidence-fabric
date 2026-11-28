#!/usr/bin/env python3
"""r136s2_f31f_run.py — the F31e PROTOCOL replicated on a non-builder
set (R136 directions dir 6; prereg eval/r136s2_f31f_prereg.json governs;
claim c-0217). BYTE-FAITHFUL SCAFFOLD REUSE: the committed r125_f31e_run
driver is imported and only its SET/OUT path constants are re-pointed —
zero protocol bytes re-authored (same frozen authoring directive, same
improved-directive + M5 diff-min fold, same quota probe, same byte-
resume, same typed-fail discipline, same arms).

Set: eval/r136s2_f31f_set/items.jsonl (12 benchmark problems, non-
builder provenance, detector-fresh). Out: eval/r136s2_f31f_run/.

Usage: python3 scripts/r136s2_f31f_run.py [--draw1|--draw2|--review1|
       --review2|all]
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

import r125_f31e_run as base  # noqa: E402  (the committed scaffold)

base.SET = REPO / "eval" / "r136s2_f31f_set" / "items.jsonl"
base.OUT = REPO / "eval" / "r136s2_f31f_run"
base.OUT.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    raise SystemExit(base.main())
