#!/usr/bin/env python3
"""r11_pool30.py — D6 battery-pool repair (found 2026-11-14, pre-run).

The battery's own acceptance criterion is `30_complete` but the pool
composes to 29 pairs (17 fresh + 12 dev12): the docstring's "13 DEV12"
was aspirational — problems_dev12.json has carried 12 problems since
its creation (af7e2a03f). The defect was invisible because every R4
window died before the battery reached phase 1 (typed OUT, Art. LXI).

The fix is a NEW FRESH PROBLEM (30th pair), authored to the exact
new_r1 conventions — NOT a threshold change (Art. XXVII: no threshold
invention; Art. XXX: never optimize the evaluator). eval-new12 is a
predictor-design problem in a domain no existing pool problem covers
(railway axle-bearing condition monitoring), disjoint from every
engine test fixture and existing problem id.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POOL = REPO / "eval" / "problems.json"

NEW12 = {
 "problem_id": "eval-new12-axle-bearing-predictor",
 "device": "tier-1 freight-wagon axle-box rolling-element bearing "
           "monitored by a wayside acoustic trackside station",
 "failure": "Bearing raceway spalling initiates as a subsurface fatigue "
            "crack and propagates until rolling-contact spalls shed "
            "debris, heating the axle box until seizure risks a "
            "derailment; detection today relies on periodic manual "
            "inspection at depot intervals of up to 4 years.",
 "failure_mode": "raceway-spalling",
 "constraint": "predict at least 60 days before critical temperature "
               "rise using only the wayside acoustic station's existing "
               "microphone array and wheel-impact-load-detector data, "
               "with no onboard hardware installed on any wagon",
 "domain": "railways",
 "source": "new_r1",
 "question_type": "predictor-design",
 "question": ("Propose the most cost-effective measurable leading "
              "indicator (predictor) for the stated failure, its "
              "operating threshold, and the concrete test that would "
              "validate or kill the predictor."),
 "user_variables": [
  "60 days minimum warning before critical temperature rise",
  "existing wayside acoustic microphone array only",
  "existing wheel-impact-load-detector data only",
  "no onboard hardware on any wagon",
  "depot inspection interval up to 4 years today",
 ],
 "clarification_answer": None,
 "contamination_tag": None,
 "split": "DEV",
}


def main() -> int:
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    plist = pool if isinstance(pool, list) else pool.get("problems", [])
    ids = {p["problem_id"] for p in plist}
    assert NEW12["problem_id"] not in ids, "id collision"
    # disjointness: no other problem covers railway axles / wayside acoustics
    for p in plist:
        blob = json.dumps(p, ensure_ascii=False).lower()
        assert "axle" not in blob and "wayside" not in blob, \
            f"overlap with {p['problem_id']}"
    plist.append(NEW12)
    if isinstance(pool, list):
        POOL.write_text(json.dumps(plist, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
    else:
        pool["problems"] = plist
        POOL.write_text(json.dumps(pool, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
    print(f"[pool30] added {NEW12['problem_id']} -> "
          f"{len(plist)} problems (pool now 18 fresh + 12 dev12 = 30)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
