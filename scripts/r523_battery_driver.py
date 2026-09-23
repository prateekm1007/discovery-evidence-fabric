#!/usr/bin/env python3
"""R523 BATTERY DRIVER — thin R523 wrapper over the R519 driver.

The R519 driver (scripts/r519_battery_driver.py, frozen R519 history —
never modified by R523) is fully env-parameterized, so R523 reuses it
as the execution engine: this wrapper maps R523_* env vars onto the
R519_* names and delegates the mode dispatch. One instrument, no fork
(Art. LXIV: no parallel implementation).

R523 arms (frozen):
  current = the exactly deployed production build (openalex excluded,
            evidence fabric off) — the mandatory attribution sweep
  after   = ONLY if and when the completed ranking names one measured
            cliff: identical engine bytes or the single named
            intervention, per the round record's decision

The R519 engine requires its ARM in {baseline, optimized}; R523 maps
current->baseline and after->optimized at the engine boundary while all
R523 artifacts (sessions, harvests, records) carry current/after.

Env:
  R523_ARM            current | after       (REQUIRED — no default)
  R523_MANIFEST       default R523/BATTERY_PROBLEMS.json
  R523_SESSIONS       default R523/BATTERY_SESSIONS_<ARM>.json (LOCAL ONLY)
  R523_REDACTED       default R523/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R523_BATTERY_NAME   default R523-CURRENT-PRODUCTION-ATTRIBUTION-<arm>
  R523_TAG            default R523-BATTERY
  R523_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)
  R523_ONLY           optional wave filter (selection_index list)
  R523_ANSWER_ONE     optional single-answer scheduling
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

ARM = os.environ.get("R523_ARM", "").strip().lower()
if ARM not in ("current", "after"):
    print("FATAL: R523_ARM must be 'current' or 'after' "
          "(explicit arm, never a default)")
    sys.exit(2)
ENGINE_ARM = {"current": "baseline", "after": "optimized"}[ARM]

os.environ["R519_ARM"] = ENGINE_ARM
os.environ.setdefault(
    "R519_MANIFEST",
    os.environ.get("R523_MANIFEST", "R523/BATTERY_PROBLEMS.json"))
os.environ.setdefault(
    "R519_SESSIONS",
    os.environ.get("R523_SESSIONS",
                   f"R523/BATTERY_SESSIONS_{ARM.upper()}.json"))
os.environ.setdefault(
    "R519_REDACTED",
    os.environ.get("R523_REDACTED",
                   f"R523/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json"))
os.environ.setdefault(
    "R519_BATTERY_NAME",
    os.environ.get("R523_BATTERY_NAME",
                   f"R523-CURRENT-PRODUCTION-ATTRIBUTION-{ARM}"))
os.environ.setdefault(
    "R519_TAG", os.environ.get("R523_TAG", "R523-BATTERY"))
if "R523_EXPECT_COMMIT" in os.environ:
    os.environ["R519_EXPECT_COMMIT"] = os.environ["R523_EXPECT_COMMIT"]
if "R523_ONLY" in os.environ:
    os.environ["R519_ONLY"] = os.environ["R523_ONLY"]
if "R523_ANSWER_ONE" in os.environ:
    os.environ["R519_ANSWER_ONE"] = os.environ["R523_ANSWER_ONE"]

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
