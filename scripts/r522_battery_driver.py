#!/usr/bin/env python3
"""R522 BATTERY DRIVER — thin R522 wrapper over the R519 driver.

The R519 driver (scripts/r519_battery_driver.py, frozen R519 history —
never modified by R522) is fully env-parameterized, so R522 reuses it
as the execution engine: this wrapper maps R522_* env vars onto the
R519_* names and delegates the mode dispatch. One instrument, no fork
(Art. LXIV: no parallel implementation).

R522 arms (frozen):
  baseline = winner engine SHA with the centralized source-exclusion
             authority DORMANT (ENGINE_RETRIEVE_EXCLUDE_SOURCES unset):
             the exact current production retrieval path, openalex
             enabled
  after    = identical engine bytes + the single Space variable delta
             ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex through the one
             centralized authority

The R519 engine requires its ARM in {baseline, optimized}; R522 maps
baseline->baseline and after->optimized at the engine boundary while
all R522 artifacts (sessions, harvests, records) carry baseline/after.

Env:
  R522_ARM            baseline | after      (REQUIRED — no default)
  R522_MANIFEST       default R522/BATTERY_PROBLEMS.json
  R522_SESSIONS       default R522/BATTERY_SESSIONS_<ARM>.json (LOCAL ONLY)
  R522_REDACTED       default R522/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R522_BATTERY_NAME   default R522-OPENALEX-EXCLUSION-<arm>
  R522_TAG            default R522-BATTERY
  R522_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)
  R522_ONLY           optional wave filter (selection_index list)
  R522_ANSWER_ONE     optional single-answer scheduling
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

ARM = os.environ.get("R522_ARM", "").strip().lower()
if ARM not in ("baseline", "after"):
    print("FATAL: R522_ARM must be 'baseline' or 'after' "
          "(explicit arm, never a default)")
    sys.exit(2)
ENGINE_ARM = {"baseline": "baseline", "after": "optimized"}[ARM]

os.environ["R519_ARM"] = ENGINE_ARM
os.environ.setdefault(
    "R519_MANIFEST",
    os.environ.get("R522_MANIFEST", "R522/BATTERY_PROBLEMS.json"))
os.environ.setdefault(
    "R519_SESSIONS",
    os.environ.get("R522_SESSIONS",
                   f"R522/BATTERY_SESSIONS_{ARM.upper()}.json"))
os.environ.setdefault(
    "R519_REDACTED",
    os.environ.get("R522_REDACTED",
                   f"R522/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json"))
os.environ.setdefault(
    "R519_BATTERY_NAME",
    os.environ.get("R522_BATTERY_NAME",
                   f"R522-OPENALEX-EXCLUSION-{ARM}"))
os.environ.setdefault(
    "R519_TAG", os.environ.get("R522_TAG", "R522-BATTERY"))
if "R522_EXPECT_COMMIT" in os.environ:
    os.environ["R519_EXPECT_COMMIT"] = os.environ["R522_EXPECT_COMMIT"]
if "R522_ONLY" in os.environ:
    os.environ["R519_ONLY"] = os.environ["R522_ONLY"]
if "R522_ANSWER_ONE" in os.environ:
    os.environ["R519_ANSWER_ONE"] = os.environ["R522_ANSWER_ONE"]

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
