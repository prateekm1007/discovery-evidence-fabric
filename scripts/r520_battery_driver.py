#!/usr/bin/env python3
"""R520 BATTERY DRIVER — thin R520 wrapper over the R519 driver.

The R519 driver (scripts/r519_battery_driver.py, frozen R519 history —
never modified by R520) is fully env-parameterized, so R520 reuses it
as the execution engine: this wrapper maps R520_* env vars onto the
R519_* names and delegates the mode dispatch. One instrument, no fork
(Art. LXIV: no parallel implementation).

R520 arms (frozen):
  baseline  = post-R519 production engine (pre-R520-change tree)
  optimized = baseline + EXACTLY ONE change: zai retired from the MS
              operator-instantiation purpose scope (R520 MS route)

Env:
  R520_ARM            baseline | optimized   (REQUIRED — no default)
  R520_MANIFEST       default R520/BATTERY_PROBLEMS.json
  R520_SESSIONS       default R520/BATTERY_SESSIONS_<ARM>.json (LOCAL ONLY)
  R520_REDACTED       default R520/BATTERY_SESSIONS_<ARM>_REDACTED.json
  R520_BATTERY_NAME   default R520-MS-AB-<ARM>
  R520_TAG            default R520-BATTERY
  R520_EXPECT_COMMIT  REQUIRED (arm build SHA prefix accepted)
  R520_ONLY           optional wave filter (selection_index list)
  R520_ANSWER_ONE     optional single-answer scheduling
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

ARM = os.environ.get("R520_ARM", "").strip().lower()
if ARM not in ("baseline", "optimized"):
    print("FATAL: R520_ARM must be 'baseline' or 'optimized' "
          "(explicit arm, never a default)")
    sys.exit(2)

os.environ["R519_ARM"] = ARM
os.environ.setdefault(
    "R519_MANIFEST",
    os.environ.get("R520_MANIFEST", "R520/BATTERY_PROBLEMS.json"))
os.environ.setdefault(
    "R519_SESSIONS",
    os.environ.get("R520_SESSIONS",
                   f"R520/BATTERY_SESSIONS_{ARM.upper()}.json"))
os.environ.setdefault(
    "R519_REDACTED",
    os.environ.get("R520_REDACTED",
                   f"R520/BATTERY_SESSIONS_{ARM.upper()}_REDACTED.json"))
os.environ.setdefault(
    "R519_BATTERY_NAME",
    os.environ.get("R520_BATTERY_NAME", f"R520-MS-AB-{ARM}"))
os.environ.setdefault(
    "R519_TAG", os.environ.get("R520_TAG", "R520-BATTERY"))
if "R520_EXPECT_COMMIT" in os.environ:
    os.environ["R519_EXPECT_COMMIT"] = os.environ["R520_EXPECT_COMMIT"]
if "R520_ONLY" in os.environ:
    os.environ["R519_ONLY"] = os.environ["R520_ONLY"]
if "R520_ANSWER_ONE" in os.environ:
    os.environ["R519_ANSWER_ONE"] = os.environ["R520_ANSWER_ONE"]

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
