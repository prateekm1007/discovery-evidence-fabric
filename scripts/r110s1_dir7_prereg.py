#!/usr/bin/env python3
"""r110s1_dir7_prereg.py — the R110 direction-7 pre-registration: the
D8 bias probe EXTENDED to a stratified 10 of the 25 PARTIAL items,
executing only after the direction-3 instrument lands (the auditor's
gating)."""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path("eval/work_claims.json")
PRE = Path("eval/r110_d7_stratified_probe_prereg.json")
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
assert "c-0146" not in {c["claim_id"] for c in d["claims"]}
d["claims"].append({
    "claim_id": "c-0146",
    "claimed_at": NOW,
    "registered_at": NOW + " (push = the lock, Art. 29(b))",
    "work_id": "r110-lane-d7d8-stratified-probe",
    "session_id": "builder-r109s1",
    "role": "EXECUTOR",
    "status": "OPEN",
    "kind": "measurement",
    "base_sha": "8e6cffa95",
    "lease_expiry": "2026-11-23T23:59:00Z",
    "title": ("the R110 direction 7: the D8 family-swap bias probe "
              "EXTENDED to a stratified 10 of the 25 PARTIAL items "
              "(the execution gate: only after the direction-3 "
              "instrument lands — its judge-free graded recall is the "
              "third reference panel). Design: the stratification is "
              "the D5 label-matrix shapes (deterministic seed 110): "
              "2 from J1-NR|J2-P (5 available), 5 from J1-P|J2-P (15 "
              "available), 1 from J1-P|J2-R (3), 1 from J1-R|J2-P "
              "(2), 1 from J1-R|J2-R (2) = 10; per item ONE agnes "
              "regeneration (temp 0.0, the SAME generator prompt) + "
              "the dual-panel judge swap (zai-J1/xkiro-J2 vs "
              "xkiro-J1/zai-J2, 4 judge calls each) + the judge-free "
              "graded key-element recall on the NEW corpus's "
              "instruments where the item maps; raw bytes committed "
              "verbatim."),
    "notes": ("the 3-class judge labels are the PROBE's read (the "
              "family-swap effect needs a labeled verdict to flip); "
              "the judge-free recall runs alongside as the "
              "reference — the R110 delete list removes the 3-class "
              "count as the SCORE-9 metric, not as a probe "
              "instrument"),
    "artifact_paths": ["eval/r110_d7d8_stratified_probe.json",
                       "eval/r110_d7d8_probe_raw/"],
})
REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")

pre = {
    "record": "R110_D7D8_STRATIFIED_PROBE_PREREG/1.0.0 "
              "(PRE-REGISTRATION)",
    "at": NOW,
    "executor": "builder-r109s1",
    "claim": "c-0146 (r110-lane-d7d8-stratified-probe; the R110 "
             "direction 7)",
    "gate": ("EXECUTES ONLY AFTER the direction-3 instrument result "
             "(c-0145) lands DONE with its committed record — the "
             "auditor's own sequencing"),
    "stratification": {
        "basis": "the D5 label matrix (the committed rerun's J1xJ2 "
                 "shapes over the 25 PARTIAL items)",
        "cells": {"J1-NR|J2-P": (5, 2), "J1-P|J2-P": (15, 5),
                  "J1-P|J2-R": (3, 1), "J1-R|J2-P": (2, 1),
                  "J1-R|J2-R": (2, 1)},
        "rule": "seed-110 fixed shuffle within each cell, the first k "
                "taken — deterministic, no hand-picking",
    },
    "per_item": ["ONE agnes regeneration (temp 0.0, the same "
                 "generator_prompt; raw bytes committed)",
                 "std panel: zai-J1 + xkiro-J2",
                 "swapped panel: xkiro-J1' + zai-J2'",
                 "the judge-free graded recall (the direction-3 "
                 "matcher, tau fixed by the c-0145 calibration) as "
                 "the third reference where the item maps to the new "
                 "instrument"],
    "readings": ("the family effect on the PARTIAL body: do verdicts "
                 "flip under the seat swap; does either family "
                 "systematically rate higher; the judge-free recall "
                 "vs both panels' labels as the calibration "
                 "reference"),
    "quota_estimate": "10 agnes regenerations + 40 judge calls",
    "anti_tuning": "committed BEFORE the probe runs; amendments are "
                   "typed findings",
}
PRE.write_text(json.dumps(pre, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("c-0146 registered; prereg written:", PRE)
