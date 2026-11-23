#!/usr/bin/env python3
"""tests/_panel_engine_check.py — the subprocess program for
test_article22_measured_path.test_panel_measured_path_runs_through_
the_engine (R133 DIR-2/R132-F1). Run with python -I from the repo
root; exit 0 = the panel path resolves through the engine."""
import sys

sys.path.insert(0, ".")

from discovery_fabric.engine.blind_panel import (  # noqa: E402
    build_pair_prompt, parse_pair_rating)
from discovery_fabric.engine.panel_agreement import (  # noqa: E402
    rcal_qualification, swap_robust_panel)  # noqa: F401

p = build_pair_prompt(
    {"device": "d", "failure": "f", "question": "q",
     "user_variables": ["v"]}, "answer A text", "answer B text")
assert "=== ANSWER A ===" in p and "=== ANSWER B ===" in p
assert "a tie is NOT available" in p

good = ('{"N_A": 3, "F_A": 3, "T_A": 3, "C_A": 3, '
        '"N_B": 2, "F_B": 3, "T_B": 3, "C_B": 3, '
        '"prefer": "A"}')
r = parse_pair_rating(good)
assert r["prefer"] == "A" and r["axes"]["N_A"] == 3

tie = good[:-2] + 'TIE"}'
try:
    parse_pair_rating(tie)
    raise SystemExit("TIE must be a parse failure")
except ValueError:
    pass

print("panel-path engine-routed")
