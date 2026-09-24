#!/usr/bin/env python3
"""R526 BATTERY DRIVER — thin R526 wrapper over the R519 driver.

The R519 driver (scripts/r519_battery_driver.py, frozen R519 history —
never modified by R526) is fully env-parameterized, so R526 reuses it
as the execution engine: this wrapper maps R526_* env vars onto the
R519_* names and delegates the mode dispatch. One instrument, no fork
(Art. LXIV: no parallel implementation).

R526 arms (frozen):
  current = the exactly deployed production build (openalex excluded,
            evidence fabric off) — the mandatory attribution sweep
  after   = ONLY if and when the completed ranking names one measured
            cliff: identical engine bytes or the single named
            intervention, per the round record's decision

The R519 engine requires its ARM in {baseline, optimized}; R526 maps
current->baseline and after->optimized at the engine boundary while all
R526 artifacts (sessions, harvests, records) carry current/after.

Env:
  R526_ARM            current | after       (REQUIRED — no default)
  R526_MANIFEST       default R526/BATTERY_PROBLEMS.json
  R526_SESSIONS       default R526/BATTERY_SESSIONS_<ARM>.json (LOCAL ONLY)
  R526_REDACTED       default R526/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R526_BATTERY_NAME   default R526-CURRENT-PRODUCTION-ATTRIBUTION-<arm>
  R526_TAG            default R526-BATTERY
  R526_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)
  R526_ONLY           optional wave filter (selection_index list)
  R526_ANSWER_ONE     optional single-answer scheduling
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

ARM = os.environ.get("R526_ARM", "").strip().lower()
if ARM not in ("current", "after"):
    print("FATAL: R526_ARM must be 'current' or 'after' "
          "(explicit arm, never a default)")
    sys.exit(2)
ENGINE_ARM = {"current": "baseline", "after": "optimized"}[ARM]

os.environ["R519_ARM"] = ENGINE_ARM
os.environ.setdefault(
    "R519_MANIFEST",
    os.environ.get("R526_MANIFEST", "R526/BATTERY_PROBLEMS.json"))
os.environ.setdefault(
    "R519_SESSIONS",
    os.environ.get("R526_SESSIONS",
                   f"R526/BATTERY_SESSIONS_{ARM.upper()}.json"))
os.environ.setdefault(
    "R519_REDACTED",
    os.environ.get("R526_REDACTED",
                   f"R526/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json"))
os.environ.setdefault(
    "R519_BATTERY_NAME",
    os.environ.get("R526_BATTERY_NAME",
                   f"R526-CURRENT-PRODUCTION-ATTRIBUTION-{ARM}"))
os.environ.setdefault(
    "R519_TAG", os.environ.get("R526_TAG", "R526-BATTERY"))
if "R526_EXPECT_COMMIT" in os.environ:
    os.environ["R519_EXPECT_COMMIT"] = os.environ["R526_EXPECT_COMMIT"]
if "R526_ONLY" in os.environ:
    os.environ["R519_ONLY"] = os.environ["R526_ONLY"]
if "R526_ANSWER_ONE" in os.environ:
    os.environ["R519_ANSWER_ONE"] = os.environ["R526_ANSWER_ONE"]

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
