#!/usr/bin/env python3
"""r123_build_f97_fixture.py — build the F97 precision-regression
fixture (tests/fixtures/f97_input_availability_cases.json) from the
REAL committed run bytes (the R123 fresh draws — both lanes' records).

Each case pins: the problem dict, the bill (the authored or delivered
bytes verbatim), the CURRENT (pre-F97) INPUT_UNAVAILABLE finding
strings, and the TYPED EXPECTATION after the adjudicated F97 fix:
  "silent"  — a prose mis-parse must NOT fire (the auditor's four
              named shapes + the same-family paren/clause garbage);
  "fires"   — a genuine signal/feature finding must KEEP firing
              (recall preserved), with the expected qty span.
Zero LLM, zero network; the fixture bytes freeze at this commit.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# (source record, arm-file pattern, expectation)
# expectation: ("silent", None) | ("fires", "qty-substring-expected")
CASES = [
    # --- leg-1 prose mis-parses (the auditor's four named shapes) ---
    ("eval/r123_fresh_run/succ_r123-02-s2.json", "delivered_bill",
     "silent", None, "F97-1 'Continuously' as compound qty"),
    ("eval/r123_fresh_run/succ_r123-05-s2.json", "delivered_bill",
     "silent", None, "F97-1 'Continuously'"),
    ("eval/r123_fresh_run/succ_r123-05-s2.json", "delivered_bill",
     "silent", None, "F97-2 'critical'"),
    ("eval/r123_fresh_run/succ_r123-05-s2.json", "delivered_bill",
     "silent", None, "F97-3 'loop for'"),
    ("eval/r123_fresh_confirmation_run/row_r123-07-s2.json",
     "delivered_bill", "silent", None, "F97-1 'continuous'"),
    ("eval/r123_fresh_confirmation_run/row_r123-03-s2.json",
     "delivered_bill", "silent", None, "F97-1 'directly'"),
    ("eval/r123_fresh_confirmation_run/row_r123-03-s2.json",
     "delivered_bill", "silent", None, "F97 'and alarming strategy'"),
    ("eval/r123_fresh_confirmation_run/row_r123-04-s2.json",
     "delivered_bill", "silent", None, "F97 'system'"),
    ("eval/r123_fresh_confirmation_run/row_r123-11-s1.json",
     "delivered_bill", "silent", None, "F97 'Standard'"),
    ("eval/r123_fresh_confirmation_run/row_r123-08-s2.json",
     "delivered_bill", "silent", None, "F97 'and adaptive setpoint'"),
    # --- leg-2 paren/clause garbage (the same mis-parse family) ---
    ("eval/r123_fresh_run/succ_r123-05-s1.json", "delivered_bill",
     "silent", None, "F97-4 leg2 'O2 concentration)' unbalanced tail"),
    ("eval/r123_fresh_run/succ_r123-01-s1.json", "delivered_bill",
     "silent", None, "leg2 'speed) proactively' unbalanced tail"),
    ("eval/r123_fresh_confirmation_run/row_r123-08-s1.json",
     "delivered_bill", "silent", None,
     "leg2 'valve position or pump speed)' paren aside"),
    ("eval/r123_fresh_confirmation_run/row_r123-03-s1.json",
     "delivered_bill", "silent", None,
     "leg2 'setpoint reduction) or terminate operation...' clause "
     "garbage"),
    ("eval/r123_fresh_run/succ_r123-06-s1.json", "delivered_bill",
     "silent", None,
     "leg2 '...adjustment , assuming a VS' clause garbage"),
    # --- hyphenated permitted-signal matching (M3) ---
    ("eval/r123_fresh_run/succ_r123-09-s2.json", "delivered_bill",
     "silent", None,
     "leg1 'belt speed' — the permitted list names the belt-speed "
     "encoder (hyphenation must not hide the match)"),
    # --- genuine detections that MUST KEEP FIRING (recall guard) ---
    ("eval/r123_fresh_confirmation_run/row_r123-01-s2.json",
     "delivered_bill", "fires", "Wet-Bulb Deviation Logic",
     "GENUINE leg2 derived feature (the documented residual class)"),
    ("eval/r123_fresh_confirmation_run/row_r123-07-s1.json",
     "delivered_bill", "fires", "DP-Opacity Correlation",
     "GENUINE leg2 derived feature"),
    ("eval/r123_fresh_run/succ_r123-09-s1.json", "delivered_bill",
     "fires", "Amperometric Drift Correction",
     "GENUINE leg2 derived feature"),
    ("eval/r123_fresh_run/succ_r123-06-s1.json", "authored_bill",
     "fires", "Ampere-Flow Head Mapping",
     "GENUINE leg2 derived feature"),
    ("eval/r123_fresh_run/succ_r123-02-s1.json", "delivered_bill",
     "fires", "Performance Index Restoration",
     "GENUINE leg2 derived feature"),
    ("eval/r123_fresh_run/succ_r123-11-s1.json", "authored_bill",
     "fires", "varying torque demands and oil flow dynamics",
     "GENUINE leg2 derived feature"),
    ("eval/r123_fresh_run/succ_r123-06-s2.json", "delivered_bill",
     "fires", "current",
     "GENUINE leg1 unpermitted online signal (electrical current)"),
    ("eval/r123_fresh_run/succ_r123-07-s1.json", "authored_bill",
     "fires", "rate of DP",
     "GENUINE leg1 unpermitted online signal (DP rate)"),
    ("eval/r123_fresh_run/succ_r123-07-s1.json", "delivered_bill",
     "fires", "post-pulse state",
     "GENUINE leg1 unpermitted online signal"),
]


def load_prob(pid: str) -> dict:
    """The problem bytes: from the frozen set items.jsonl."""
    items = (REPO / "eval" / "r123_fresh_set" / "items.jsonl")
    for line in items.read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        d = json.loads(line)
        if d["problem_id"] == pid:
            return d
    raise SystemExit(f"problem {pid} not found in {items}")


def main() -> int:
    out = []
    seen = set()
    for path, bill_key, expect, qty, why in CASES:
        rec = json.loads((REPO / path).read_text(encoding="utf-8"))
        pid = rec["problem_id"]
        prob = load_prob(pid)
        bill = rec[bill_key]
        cur = (rec.get("post_review_scan") or {}).get(
            "INPUT_UNAVAILABLE") or (rec.get("surfaced_scan") or {}).get(
            "INPUT_UNAVAILABLE") or []
        key = (pid, why)
        assert key not in seen, key
        seen.add(key)
        out.append({
            "case_id": f"f97-{len(out) + 1:02d}",
            "source_record": path,
            "problem_id": pid,
            "why": why,
            "expectation": expect,
            "expected_qty_substring": qty,
            "problem": prob,
            "bill": bill,
            "pre_f97_findings": cur,
        })
    dst = REPO / "tests" / "fixtures" / "f97_input_availability_cases.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps({
        "record": "F97_INPUT_AVAILABILITY_PRECISION_FIXTURE/1.0.0",
        "note": "REAL committed run bytes (the R123 fresh draws); "
                "expectations typed per the R123 adjudication F97: "
                "prose/paren/clause mis-parses go silent; genuine "
                "signal/feature findings keep firing; hyphenated "
                "permitted-signal names match. The fixture bytes "
                "freeze at the F97 commit.",
        "cases": out}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    n_silent = sum(1 for c in out if c["expectation"] == "silent")
    print(f"written: {dst} ({len(out)} cases: {n_silent} silent, "
          f"{len(out) - n_silent} fires)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
