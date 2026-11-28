#!/usr/bin/env python3
"""tests/test_r29_v74_round.py — pins for the V7.4 deployed-part
micro-round (claim c-0028), pre-registered BEFORE any V7.4 LLM call.

  1. SET IDENTITY — the V7.4 set is EXACTLY [bench-p04] — the only
     V7.3 row whose STANDARD_BILL residual evidence is a modification
     of the stated device (the circumferential-groove machining row),
     recomputed from the committed eval/pairs/r29_v73_tuned/ bytes.
  2. JUDGE-BLIND DIRECTIVE — the V74 directive carries structural
     class relocations only: no judged numbers, no novelty/feasibility
     values, no outcome feedback.
  3. THE DEPLOYED-PART CLAUSE — the directive forbids modification of
     the stated device's parts in any form (the AM26 named defect:
     "no custom machining like the p04 vane reprofile") and relocates
     the mechanism to the surrounding system + schedules.
  4. BUDGET + CONTRACT STABILITY — budget 3 (the pre-registered
     c-0027 basis) and the BYTE-UNCHANGED SYS_A1_INT_V72 contract.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r29_v74_directive import V74_FLAGGED, V74_REPAIR_DIRECTIVE  # noqa: E402
from r29_tune_battery_v74 import REPAIR_BUDGET as V74_BUDGET  # noqa: E402
from r29_tune_battery import REPAIR_BUDGET as V72_BUDGET  # noqa: E402
from r29_tune_battery_v73 import REPAIR_BUDGET as V73_BUDGET  # noqa: E402
from r29_a1w_v72_contract import contract_for_v72  # noqa: E402
from r27_a1w_v71_contract import SYS_A1_INT_V71  # noqa: E402

V73_DIR = REPO / "eval" / "pairs" / "r29_v73_tuned"
V73_TUNED = [
    "bench-p04-pump-cavitation",
    "bench-p08-mems-stiction",
    "bench-p11-spindle-thermal-drift",
    "eval-new01-supercap-dryout",
    "eval-new03-insulin-pump-occlusion",
]


def test_v74_set_is_exactly_the_device_modification_row():
    """The only V7.3 row with a STANDARD_BILL residual whose evidence
    row is a physical MODIFICATION of the stated device (a
    geometry/material-removal instruction carrying a dimension spec —
    the impeller groove '0.3 mm depth, 1 mm width') is bench-p04; the
    other V7.3 residuals are lexical (p11's 'programmed into existing
    CNC controller' false positive — an operating schedule, no
    geometry; p08's comparator brand) or format classes."""
    import re
    dirty = []
    for pid in V73_TUNED:
        rec = json.loads((V73_DIR / f"{pid}.json").read_text(
            encoding="utf-8"))
        sb = scan_standard_bill(rec["a1_answer"], rec["question_type"])
        for f in (sb.get("STANDARD_BILL") or []):
            low = f.lower()
            is_device_mod = (
                f.startswith("CUSTOM_MACHINING")
                and bool(re.search(r"\d+(?:\.\d+)?\s*mm\b", low))
                and any(w in low for w in
                        ("groove", "machin", "cut", "grind", "drill",
                         "texture", "coat", "reprofil")))
            if is_device_mod:
                dirty.append(pid)
                break
    assert sorted(set(dirty)) == sorted(V74_FLAGGED), (
        f"the V7.4 set must be exactly {V74_FLAGGED}: {sorted(set(dirty))}")


def test_directive_is_judge_blind():
    low = V74_REPAIR_DIRECTIVE.lower()
    for banned in ("novelty delta", "novelty_delta", "feasibility gap",
                   "feasibility_gap", "judged", "score", "auditor",
                   "am26", "am27", "gap 1", "gap 2"):
        assert banned not in low, f"judge-blind violation: {banned!r}"


def test_directive_carries_the_deployed_part_clause():
    assert "may not be MODIFIED in any form" in V74_REPAIR_DIRECTIVE
    assert "used AS-IS" in V74_REPAIR_DIRECTIVE
    assert "SURROUNDING system" in V74_REPAIR_DIRECTIVE


def test_budget_and_contract_stability():
    assert V72_BUDGET == 2 and V73_BUDGET == 3 and V74_BUDGET == 3
    assert contract_for_v72("intervention-proposal").startswith(
        SYS_A1_INT_V71)
