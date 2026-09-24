#!/usr/bin/env python3
"""R525 BATTERY DRIVER — thin R525 wrapper over the R519 driver.

The R519 driver (scripts/r519_battery_driver.py, frozen R519 history —
never modified by R525) is fully env-parameterized, so R525 reuses it
as the execution engine: this wrapper maps R525_* env vars onto the
R519_* names and delegates the mode dispatch. One instrument, no fork
(Art. LXIV: no parallel implementation).

R525 arms (frozen):
  current = the exactly deployed production build (openalex excluded,
            evidence fabric off) — the mandatory attribution sweep
  after   = ONLY if and when the completed ranking names one measured
            cliff: identical engine bytes or the single named
            intervention, per the round record's decision

The R519 engine requires its ARM in {baseline, optimized}; R525 maps
current->baseline and after->optimized at the engine boundary while all
R525 artifacts (sessions, harvests, records) carry current/after.

Env:
  R525_ARM            current | after       (REQUIRED — no default)
  R525_MANIFEST       default R525/BATTERY_PROBLEMS.json
  R525_SESSIONS       default R525/BATTERY_SESSIONS_<ARM>.json (LOCAL ONLY)
  R525_REDACTED       default R525/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R525_BATTERY_NAME   default R525-CURRENT-PRODUCTION-ATTRIBUTION-<arm>
  R525_TAG            default R525-BATTERY
  R525_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)
  R525_ONLY           optional wave filter (selection_index list)
  R525_ANSWER_ONE     optional single-answer scheduling
  HF_TOKEN            REQUIRED for all Space modes (Art. LXXIII lookup)

Modes: preflight | submit | answer | poll [budget] | redact
Session files are LOCAL ONLY (BS-021); only the redacted mirror commits.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

ARM = os.environ.get("R525_ARM", "").strip().lower()
if ARM not in ("current", "after"):
    print("FATAL: R525_ARM must be 'current' or 'after' "
          "(explicit arm, never a default)")
    sys.exit(2)
ENGINE_ARM = {"current": "baseline", "after": "optimized"}[ARM]

os.environ["R519_ARM"] = ENGINE_ARM
os.environ.setdefault(
    "R519_MANIFEST",
    os.environ.get("R525_MANIFEST", "R525/BATTERY_PROBLEMS.json"))
os.environ.setdefault(
    "R519_SESSIONS",
    os.environ.get("R525_SESSIONS",
                   f"R525/BATTERY_SESSIONS_{ARM.upper()}.json"))
os.environ.setdefault(
    "R519_REDACTED",
    os.environ.get("R525_REDACTED",
                   f"R525/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json"))
os.environ.setdefault(
    "R519_BATTERY_NAME",
    os.environ.get("R525_BATTERY_NAME",
                   f"R525-CURRENT-PRODUCTION-ATTRIBUTION-{ARM}"))
os.environ.setdefault(
    "R519_TAG", os.environ.get("R525_TAG", "R525-BATTERY"))
if "R525_EXPECT_COMMIT" in os.environ:
    os.environ["R519_EXPECT_COMMIT"] = os.environ["R525_EXPECT_COMMIT"]
if "R525_ONLY" in os.environ:
    os.environ["R519_ONLY"] = os.environ["R525_ONLY"]
if "R525_ANSWER_ONE" in os.environ:
    os.environ["R519_ANSWER_ONE"] = os.environ["R525_ANSWER_ONE"]

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
