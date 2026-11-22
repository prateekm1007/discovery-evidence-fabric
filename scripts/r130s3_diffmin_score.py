#!/usr/bin/env python3
"""r130s3_diffmin_score.py — the committed scorer for the dir-3 fold
re-test (claim c-0209; the prereg governs).

Recomputes BOTH arms' tallies from the committed replay bytes:
  per arm: introduced-defect rows (bill_defect_classes on the
  delivered bills, rows with >=1 class) + heal count (the twin's
  committed score_leg definition, already applied per-leg and
  re-verified here from the delivered bytes) + typed-fail legs.
GATE (preregistered dir-3 acceptance): FOLD iff v2 defect rows <= v1
AND v2 heal count >= v1 (paired, same 48 inputs) AND v2 typed-fail
legs <= 2. Writes eval/r130s3_diffmin_scoring.json (the gate object is
the defect_rows/rows dict the CI recompute pattern expects).
Fail-closed: corpus drift (<>48 replayable inputs per arm) or a
typed-fail breach -> exit 2, no scoring file. Zero LLM, zero network.

Usage: python3 scripts/r130s3_diffmin_score.py [--preview]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402
from r130_gepa_reviewer import ITEMS  # noqa: E402

CLASSES = ["input_availability", "duty_pricing", "constraint_violation",
           "physics_direction_inversion"]


def tally_arm(arm: str) -> dict:
    rows = 0
    fail_legs = []
    defects = []
    healed = 0
    per_class = {c: 0 for c in CLASSES}
    attempts = {"legs": 0, "backoff_legs": 0, "max_attempts": 1}
    parse_first_try = 0
    for f in sorted((REPO / "eval" / "r130s3_diffmin_replay")
                    .glob(f"{arm}_*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        attempts["legs"] += 1
        att = rec.get("transport_attempts") or 1
        if att > 1:
            attempts["backoff_legs"] += 1
        attempts["max_attempts"] = max(attempts["max_attempts"], att)
        if not rec.get("ok"):
            fail_legs.append(f"{arm}/{rec.get('draw')}/"
                             f"{rec.get('pid')}: "
                             f"{str(rec.get('typed_fail'))[:60]}")
            continue
        rows += 1
        if rec.get("parse_first_try"):
            parse_first_try += 1
        delivered = rec["delivered"]
        cls = bill_defect_classes(ITEMS[rec["pid"]], delivered)
        if cls:
            defects.append({"pid": rec["pid"], "draw": rec["draw"],
                            "classes": cls})
            for c in cls:
                if c in per_class:
                    per_class[c] += 1
        # re-verify the heal flag from bytes (the twin's definition)
        import r127_phaseA_gate as gate
        scan = gate.check_layer(ITEMS[rec["pid"]], delivered, None)
        vals = [v for v in (scan.values() if isinstance(scan, dict)
                            else []) if v]
        if not vals:
            healed += 1
    return {"rows": rows, "defects": defects, "per_class": per_class,
            "healed": healed, "fail_legs": fail_legs,
            "parse_first_try": parse_first_try, "attempts": attempts}


def main() -> int:
    preview = "--preview" in sys.argv
    v1 = tally_arm("v1")
    v2 = tally_arm("v2")
    print(f"v1: rows={v1['rows']} defect_rows={len(v1['defects'])} "
          f"healed={v1['healed']} per_class={v1['per_class']} "
          f"fail_legs={len(v1['fail_legs'])} "
          f"parse_first_try={v1['parse_first_try']}/"
          f"{v1['rows']} attempts={v1['attempts']}")
    for fl in v1["fail_legs"]:
        print("  v1 FAIL:", fl)
    print(f"v2: rows={v2['rows']} defect_rows={len(v2['defects'])} "
          f"healed={v2['healed']} per_class={v2['per_class']} "
          f"fail_legs={len(v2['fail_legs'])} "
          f"parse_first_try={v2['parse_first_try']}/"
          f"{v2['rows']} attempts={v2['attempts']}")
    for fl in v2["fail_legs"]:
        print("  v2 FAIL:", fl)

    # fail-closed coverage check BEFORE the gate (the prereg budget)
    # — skipped in preview (mid-run inspection is not a gate read)
    if not preview:
        if v1["rows"] != 48 or v2["rows"] != 48:
            print(f"FAIL-CLOSED: COVERAGE (v1 rows {v1['rows']}, "
                  f"v2 rows {v2['rows']} — both arms need 48 valid "
                  f"legs and the typed-fail budget is <=2 per arm) "
                  f"— exit 2")
            return 2
        if len(v2["fail_legs"]) > 2 or len(v1["fail_legs"]) > 2:
            print("FAIL-CLOSED: INVALID_COVERAGE (>2 typed-fail "
                  "legs) — exit 2")
            return 2

    no_reg_defects = len(v2["defects"]) <= len(v1["defects"])
    no_reg_heal = v2["healed"] >= v1["healed"]
    gate = "FOLD" if (no_reg_defects and no_reg_heal) else "NO-FOLD"
    print(f"GATE (dir 3, preregistered): v2 {len(v2['defects'])}/48 "
          f"defect rows vs v1 {len(v1['defects'])}/48 "
          f"({'<=' if no_reg_defects else '>'}); heal v2 {v2['healed']} "
          f"vs v1 {v1['healed']} ({'>=' if no_reg_heal else '<'}) "
          f"-> {gate}")

    if preview:
        print("PREVIEW ONLY — no scoring file written")
        return 0

    out = {
        "record": "R130S3_DIFFMIN_SCORING/1.0.0",
        "claim": "c-0209",
        "session": "builder-r130s3",
        "arm_pair": "v1 (frozen incumbent bytes) vs v2 (v1 + M5, "
                    "byte-identical to the twin's m5_minimal)",
        "corpus": "the 48 committed F31e pre-review bills "
                  "(succ_d{1,2} authored_bill + surfaced_findings), "
                  "disjoint from the GEPA compile corpus",
        "v1": {"rows": v1["rows"],
               "defect_rows": len(v1["defects"]),
               "defect_rows_detail": v1["defects"],
               "per_class": v1["per_class"],
               "healed": v1["healed"],
               "typed_fail_legs": v1["fail_legs"],
               "parse_first_try": v1["parse_first_try"],
               "transport": v1["attempts"]},
        "v2": {"rows": v2["rows"],
               "defect_rows": len(v2["defects"]),
               "defect_rows_detail": v2["defects"],
               "per_class": v2["per_class"],
               "healed": v2["healed"],
               "typed_fail_legs": v2["fail_legs"],
               "parse_first_try": v2["parse_first_try"],
               "transport": v2["attempts"]},
        "gate": {
            "defect_rows": len(v2["defects"]),
            "rows": v2["rows"],
            "verdict": gate,
            "no_regression_defects": no_reg_defects,
            "no_regression_heal": no_reg_heal,
            "v1_defect_rows": len(v1["defects"]),
            "note": "the preregistered dir-3 fold gate: FOLD iff v2 "
                    "defect rows <= v1 AND v2 heal >= v1 (paired, "
                    "same 48 held-out inputs); no score claims",
        },
    }
    path = REPO / "eval" / "r130s3_diffmin_scoring.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"scoring written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
