#!/usr/bin/env python3
"""R521 BATTERY DRIVER — thin R521 wrapper over the R519 driver.

The R519 driver (scripts/r519_battery_driver.py, frozen R519 history —
never modified by R521) is fully env-parameterized, so R521 reuses it
as the execution engine: this wrapper maps R521_* env vars onto the
R519_* names and delegates the mode dispatch. One instrument, no fork
(Art. LXIV: no parallel implementation).

R521 arms (frozen):
  before = current production engine (post-R520 main)
  after  = before + EXACTLY ONE behavioral intervention targeting the
           single measured R521 cliff (named after attribution; the
           driver itself is cliff-agnostic)

The R519 engine requires its ARM in {baseline, optimized}; R521 maps
before->baseline and after->optimized at the engine boundary while all
R521 artifacts (sessions, harvests, records) carry before/after.

Env:
  R521_ARM            before | after      (REQUIRED — no default)
  R521_MANIFEST       default R521/BATTERY_PROBLEMS.json
  R521_SESSIONS       default R521/BATTERY_SESSIONS_<ARM>.json (LOCAL ONLY)
  R521_REDACTED       default R521/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R521_BATTERY_NAME   default R521-STAGE-ATTRIBUTION-<arm>
  R521_TAG            default R521-BATTERY
  R521_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)
  R521_ONLY           optional wave filter (selection_index list)
  R521_ANSWER_ONE     optional single-answer scheduling
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

ARM = os.environ.get("R521_ARM", "").strip().lower()
if ARM not in ("before", "after"):
    print("FATAL: R521_ARM must be 'before' or 'after' "
          "(explicit arm, never a default)")
    sys.exit(2)
ENGINE_ARM = {"before": "baseline", "after": "optimized"}[ARM]

os.environ["R519_ARM"] = ENGINE_ARM
os.environ.setdefault(
    "R519_MANIFEST",
    os.environ.get("R521_MANIFEST", "R521/BATTERY_PROBLEMS.json"))
os.environ.setdefault(
    "R519_SESSIONS",
    os.environ.get("R521_SESSIONS",
                   f"R521/BATTERY_SESSIONS_{ARM.upper()}.json"))
os.environ.setdefault(
    "R519_REDACTED",
    os.environ.get("R521_REDACTED",
                   f"R521/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json"))
os.environ.setdefault(
    "R519_BATTERY_NAME",
    os.environ.get("R521_BATTERY_NAME", f"R521-STAGE-ATTRIBUTION-{ARM}"))
os.environ.setdefault(
    "R519_TAG", os.environ.get("R521_TAG", "R521-BATTERY"))
if "R521_EXPECT_COMMIT" in os.environ:
    os.environ["R519_EXPECT_COMMIT"] = os.environ["R521_EXPECT_COMMIT"]
if "R521_ONLY" in os.environ:
    os.environ["R519_ONLY"] = os.environ["R521_ONLY"]
if "R521_ANSWER_ONE" in os.environ:
    os.environ["R519_ANSWER_ONE"] = os.environ["R521_ANSWER_ONE"]

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
