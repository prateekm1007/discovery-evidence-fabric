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

# R526 S2 (operator-authorized 2026-09-24): the S1 freeze rule yielded
# 10 of the target 12 problems against the current NHTSA data (2 of the
# 6 vehicle pairs have no qualifying complaint under the frozen
# mechanical filters — INSUFFICIENT_QUANTIFIED_DETAIL /
# SUMMARY_TOO_SHORT / NO_QUALIFYING_COMPLAINT_FOR_CLASS). The operator
# authorized proceeding with the 10 mechanically-qualified problems as
# the R526 current arm, with the shortfall disclosed in the round
# record (measurement-only; the 10 are the qualified subset of the
# frozen vehicle set, NOT a retuned battery — the frozen rule file
# scripts/r526_freeze_battery_problems.py is unmodified). The
# manifest's selection_status is OUT_OF_RANGE by the frozen rule's own
# range check; the driver below relaxes that ONE gate (submit/preflight/
# answer/poll) to accept OUT_OF_RANGE when R526_SHORTFALL_DISCLOSED=1,
# by rewriting the on-disk manifest's selection_status to OK and
# recording the disclosure block before delegating to the R519 driver.
# All other gates (commit-identity, corpus disjointness, per-problem
# freshness) are unchanged.
if os.environ.get("R526_SHORTFALL_DISCLOSED", "").strip() == "1":
    import json as _json
    _MAN = REPO / os.environ.get(
        "R526_MANIFEST", "R526/BATTERY_PROBLEMS.json")
    _m = _json.loads(_MAN.read_text(encoding="utf-8"))
    if _m.get("selection_status") == "OUT_OF_RANGE":
        _m["selection_status"] = "OK"
        _m["r526_shortfall_disclosure"] = {
            "original_selection_status": "OUT_OF_RANGE",
            "n_problems": _m.get("n_problems"),
            "n_families": _m.get("n_families"),
            "declared_families": _m.get("declared_families"),
            "authorized_by": "operator directive 2026-09-24 "
                              "(R526 CODER NEXT DIRECTIVE)",
            "note": ("R526 S2: the S1-committed freeze rule "
                     "(scripts/r526_freeze_battery_problems.py, "
                     "committed at 91bf7832a) yielded 10 of the "
                     "target 12 problems against the current NHTSA "
                     "data; 2 of the 6 vehicle pairs have no "
                     "qualifying complaint under the frozen "
                     "mechanical filters (INSUFFICIENT_QUANTIFIED_"
                     "DETAIL / SUMMARY_TOO_SHORT / "
                     "NO_QUALIFYING_COMPLAINT_FOR_CLASS). The "
                     "operator authorized proceeding with the 10 "
                     "mechanically-qualified problems as the R526 "
                     "current arm with the shortfall disclosed. "
                     "The 10 are the qualified subset of the frozen "
                     "vehicle set, NOT a retuned battery: the "
                     "frozen rule file is unmodified, the per-vehicle "
                     "component-class pairs are unmodified, and no "
                     "prompt/gate/threshold/retrieval/model-selection "
                     "change occurred between scored problems "
                     "(Art. LXXIX). selection_status was relaxed from "
                     "OUT_OF_RANGE to OK for the driver gate only; "
                     "all other gates (commit identity, corpus "
                     "disjointness, per-problem freshness, verbatim "
                     "summary policy) are unchanged.")}
        _MAN.write_text(_json.dumps(_m, indent=1, ensure_ascii=False),
                        encoding="utf-8")
        print("[R526-driver] selection_status OUT_OF_RANGE -> OK "
              "(R526_SHORTFALL_DISCLOSED=1; frozen rule unmodified, "
              "shortfall disclosed in the manifest + round record)")

try:
    runpy.run_path(str(REPO / "scripts" / "r519_battery_driver.py"),
                   run_name="__main__")
except SystemExit as e:
    sys.exit(e.code if isinstance(e.code, int) else 0)
