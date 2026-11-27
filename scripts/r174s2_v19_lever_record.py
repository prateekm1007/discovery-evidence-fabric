#!/usr/bin/env python3
"""r174s2_v19_lever_record.py — the honest DIR-3 delivery record: the
v19 non-obviousness lever is ENGINE-WIRED and structurally enforced;
the 5/5 smoke bar is NOT MET (4 rounds: 3/5, 4/5, 2/5, 2/5 on the
non-obvious axis under the single-judge strict proxy)."""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

rounds = []
for tag, note in [
    ("r1", "lever v1 (7-part contract) — 3/5 NO; lexicon gaps found"),
    ("r2", "lexicon fix (cavitat/hydrate/frost) + DIRECTION clause — "
           "4/5 NO; failure-sign confusion found"),
    ("r3", "failure-sign filtering (suppress/promote) — 2/5 NO; "
           "expert-level counters found"),
    ("r4", "STEELMAN clause — 2/5 NO; mechanism-phrasing errors found"),
]:
    rounds.append({"round": tag, "finding": note})

record = {
    "record": "R174S2_V19_LEVER_DELIVERY/1.0.0",
    "session": "builder-r174s1",
    "dir": "DIR 3 — build the v19 non-obviousness lever",
    "delivered": {
        "module": "discovery_fabric/generation/nonobvious_departure.py",
        "wiring": "engine package + tests/test_nonobvious_departure.py "
                  "(7/7) + scripts/r174_v19_departure_smoke.py; the "
                  "generation tests battery GREEN (26 tests)",
        "contract": "CROSS-DOMAIN INSPIRATION (cited precedent + "
                    "physical principle) -> NEAREST PRIOR ART -> THE "
                    "DEPARTURE (different physical coupling) -> "
                    "NOT-A-SUBSTITUTION -> DIRECTION CHECK (anti-"
                    "inversion) -> ENABLING CONDITIONS (incl. the "
                    "continuous-regime survival condition) -> ENVELOPE "
                    "CHECK -> STEELMAN (strongest expert counter, "
                    "answered)",
        "typed_exclusions": "failure-sign filtering: promote-mechanisms "
                            "are never offered to suppress-problems "
                            "(and vice versa); same-family precedents "
                            "excluded; conventional first response "
                            "named as the thing to depart from",
        "lexicon_fixes": "mechanism_map: cavitat*/hydrate/clathrate/"
                         "frost/defrost stems (the s2 mis-route to "
                         "corrosion_chemical on bare 'pitting'); "
                         "classifications verified on all 5 smoke "
                         "problems + regressions",
    },
    "smoke_acceptance": {
        "bar": "5/5 non-obvious departures (panel proxy gpt-6-luna)",
        "verdict": "NOT MET",
        "rounds": [
            {"round": 1, "non_obvious": 3, "viable": 0,
             "finding": "lexicon: 'cavitates'/'hydrate' hit nothing"},
            {"round": 2, "non_obvious": 4, "viable": 1,
             "finding": "sign confusion: nucleation sites offered to "
                        "deposition problems"},
            {"round": 3, "non_obvious": 2, "viable": 0,
             "finding": "expert counters: N2 forms hydrates; "
                        "circulating elements lodge"},
            {"round": 4, "non_obvious": 2, "viable": 0,
             "finding": "mechanism-phrasing: 'raises the energy "
                        "threshold' is wrong cavitation physics"},
        ],
        "what_does_hold": "structure 5/5 every round (the contract is "
                          "emitted + enforced); physics_truth 5/5 "
                          "every round (DIR 6 intact); the NO axis "
                          "moves 2-4/5 with strict single-judge "
                          "adjudication — the failures are now "
                          "mechanism-level physics subtleties on hard "
                          "problems (cavitation, clathrate "
                          "thermodynamics), not structural gaps",
        "honest_reading": "the lever changes the generation shape "
                          "(mechanism classes outside the obvious set, "
                          "sign-checked, self-defended) but the "
                          "generator still phrases mechanism physics "
                          "wrongly at the margin; the panel-proxy "
                          "verdict is the honest floor, not a tuning "
                          "target (never screen-gaming). The v19 "
                          "one-shot (DIR 4) would face the same "
                          "single-judge strictness at 2/3-majority — "
                          "the smoke does NOT license predicting the "
                          "panel outcome either way.",
    },
    "artifacts": [
        "discovery_fabric/generation/nonobvious_departure.py",
        "discovery_fabric/generation/mechanism_map.py (additive stems)",
        "tests/test_nonobvious_departure.py",
        "scripts/r174_v19_departure_smoke.py",
        "eval/r174_v19_smoke/ (the round-4 rows + SUMMARY)",
        "eval/r174_dir2_divergence_diagnosis.json (the DIR-2 input)",
    ],
}
out = REPO / "eval" / "r174s2_v19_lever_delivery.json"
out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
print("DIR 3: lever DELIVERED (engine-wired); smoke 5/5 NOT MET — "
      "recorded honestly")
