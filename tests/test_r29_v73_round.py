#!/usr/bin/env python3
"""tests/test_r29_v73_round.py — pins for the V7.3 residual-conversion
round (claim c-0027), pre-registered BEFORE any V7.3 LLM call.

  1. SET IDENTITY — the V7.3 set is EXACTLY the V7.2 rows whose final
     CONVERSION scan read is non-clean, recomputed from the committed
     eval/pairs/r29_v72_tuned/ bytes (the one-draw discipline: the 5
     clean-converted rows and the 20 frozen rows are never re-drawn).
  2. JUDGE-BLIND DIRECTIVE — the V73 relocation directive carries
     typed findings and class relocations only: no judged numbers, no
     novelty/feasibility values, no outcome feedback (the structural
     judge-blind property of the machine, Art. 19).
  3. BUDGET DELTA DISCLOSED — the V7.3 budget is 3 (pre-registered on
     the claim with the measured basis: 5/10 rows exhausted budget 2
     with the class intact); the V7.2 budget was 2 — the delta is a
     machine-effort increase, never a verification change.
  4. CONTRACT STABILITY — the V7.3 round rides the BYTE-UNCHANGED
     SYS_A1_INT_V72 contract (the arm is stable; only the directive
     and the budget differ, both pre-registered on c-0027).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_v73_relocation_directive import (  # noqa: E402
    V73_FLAGGED, V73_REPAIR_DIRECTIVE)
from r29_tune_battery_v73 import REPAIR_BUDGET as V73_BUDGET  # noqa: E402
from r29_tune_battery import REPAIR_BUDGET as V72_BUDGET  # noqa: E402
from r29_a1w_v72_contract import contract_for_v72  # noqa: E402
from r27_a1w_v71_contract import SYS_A1_INT_V71  # noqa: E402

V72_DIR = REPO / "eval" / "pairs" / "r29_v72_tuned"
V72_TUNED = [
    "bench-p01-pemfc-dehydration",
    "bench-p04-pump-cavitation",
    "bench-p06-water-biofilm",
    "bench-p08-mems-stiction",
    "bench-p09-packaging-barrier",
    "bench-p10-pv-pid",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
    "eval-sofc-thermal-cycling",
]


def _probs():
    probs = {}
    for f in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / f).read_text(encoding="utf-8"))[
                "problems"]:
            probs[p["problem_id"]] = p
    return probs


def test_v73_set_is_exactly_the_v72_conversion_residuals():
    probs = _probs()
    dirty = []
    for pid in V72_TUNED:
        rec = json.loads((V72_DIR / f"{pid}.json").read_text(
            encoding="utf-8"))
        v = scan_conversion(rec["a1_answer"], rec["question_type"],
                            probs.get(pid))
        if v:
            dirty.append(pid)
    assert sorted(dirty) == sorted(V73_FLAGGED), (
        f"the V7.3 set must be exactly the non-clean V7.2 rows: "
        f"recomputed {sorted(dirty)} vs declared {sorted(V73_FLAGGED)}")


def test_the_clean_converted_rows_stay_frozen():
    clean = [p for p in V72_TUNED if p not in V73_FLAGGED]
    assert sorted(clean) == [
        "bench-p01-pemfc-dehydration",
        "bench-p06-water-biofilm",
        "bench-p09-packaging-barrier",
        "bench-p10-pv-pid",
        "eval-sofc-thermal-cycling",
    ]


def test_directive_is_judge_blind():
    low = V73_REPAIR_DIRECTIVE.lower()
    for banned in ("novelty delta", "novelty_delta", "feasibility gap",
                   "feasibility_gap", "judged", "score", "auditor",
                   "am26", "am27", "gap 1", "gap 2"):
        assert banned not in low, f"judge-blind violation: {banned!r}"


def test_directive_names_the_relocation_not_a_relabel():
    assert "OUT OF SCOPE" in V73_REPAIR_DIRECTIVE
    assert "may not appear in your revision in any form" \
        in V73_REPAIR_DIRECTIVE


def test_budget_delta_is_the_pre_registered_disclosure():
    assert V72_BUDGET == 2 and V73_BUDGET == 3


def test_contract_is_the_unchanged_v72_arm():
    assert contract_for_v72("intervention-proposal").startswith(
        SYS_A1_INT_V71)
    assert "PREMISE VALIDITY" in contract_for_v72("intervention-proposal")
    assert "OPERATIONAL-LOSS PRICING" in contract_for_v72(
        "intervention-proposal")
