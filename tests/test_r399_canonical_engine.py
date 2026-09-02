"""tests/test_r399_canonical_engine.py — R399 W6: ONE canonical engine.

The top-level legacy `engine/` package (invention_synthesis v1/v2 + old
loop machinery) was archived in R399 (removed from the working tree at
commit <R399>; full history preserved — recoverable from any parent
commit, e.g. `git show <parent>:engine/invention_synthesis.py`).

This guard prevents accidental future production imports of a top-level
`engine` namespace: the ONE authoritative production engine is
`discovery_fabric/engine/`. A fix that lands in the wrong package is
the exact failure mode the archive removes (R399 audit W6).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The production namespaces (live packages). scripts/ may reference
# ARCHIVED campaigns — the guard covers production code only.
LIVE_PACKAGES = ("discovery_fabric", "toscanini",
                 "premium_package_factory", "orchestrator")

_TOP_LEVEL_ENGINE_IMPORT = re.compile(
    r"^\s*(?:from\s+engine(?:\.|$)|import\s+engine(?:\.|$))")


def test_legacy_top_level_engine_is_archived():
    assert not (REPO_ROOT / "engine").exists(), (
        "the legacy top-level engine/ package must stay archived "
        "(R399 W6): discovery_fabric/engine/ is the one canonical "
        "production engine")


def test_no_production_imports_top_level_engine():
    offenders = []
    for pkg in LIVE_PACKAGES:
        for py in (REPO_ROOT / pkg).rglob("*.py"):
            try:
                text = py.read_text(errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if _TOP_LEVEL_ENGINE_IMPORT.match(line):
                    offenders.append(f"{py.relative_to(REPO_ROOT)}:{i}:"
                                     f" {line.strip()}")
    assert not offenders, (
        "production code must import the canonical engine "
        "(discovery_fabric.engine), never a top-level `engine` package "
        f"(R399 W6 guard). Offenders:\n" + "\n".join(offenders[:10]))
