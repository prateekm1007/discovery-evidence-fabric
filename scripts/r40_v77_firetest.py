#!/usr/bin/env python3
"""r40_v77_firetest.py — the RETROSPECTIVE validation of the V7
checks over the COMMITTED v6 rows (claim c-0046; the rows are burned
and byte-frozen — NOTHING is regenerated; the v6 bills are read as
test fixtures).

Acceptance mapping (AM37 directions D1-D3):
  HO6-02 fires the direction checks (the inverted thermal-shock
        remedy — lexicon leg and/or the typed LLM sign/integral check),
  HO6-03 fires the duty-cycle pricing check (the unpriced circulation
        cut),
  HO6-04 and HO6-12 fire the input-availability check (online
        surface-charge sensing; ion-activity/water-chemistry analysis
        — not among the permitted signals).

The v76 direction scan (presence + the narrow driver-as-remedy net)
is run alongside for contrast: the AM37 gap was that it could not
judge correctness — the fire-test records what it caught and what
only the V7 checks catch.

Output: eval/r40_v77_firetest.json (per-row findings + the mapping
verdict). Exit code 0 always — the RESULTS are the deliverable; the
authoritative v7 acceptance read stays the auditor's on the v7
packet.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

from r30_physics_direction_scan import scan_physics_direction  # noqa
from r40_machine_v77 import (  # noqa: E402
    scan_input_availability, scan_duty_cycle_pricing,
    scan_mechanism_template, direction_lexicon_check,
    direction_check_llm, start_gateway)

PROBLEMS = REPO / "eval" / "holdout_v6_problems.json"
ROWS_DIR = REPO / "eval" / "pairs" / "holdout_v6_generation"
OUT = REPO / "eval" / "r40_v77_firetest.json"


def main() -> int:
    probs = json.loads(PROBLEMS.read_text(encoding="utf-8"))
    plist = (probs["problems"] if isinstance(probs, dict)
             and "problems" in probs else probs)
    interventions = [p for p in plist
                     if str(p.get("question_type", "")).startswith(
                         "intervention")]
    gw, gw_key = start_gateway()
    rows = []
    try:
        for p in interventions:
            pid = p["problem_id"]
            rf = ROWS_DIR / f"{pid}.json"
            if not rf.exists():
                rows.append({"problem_id": pid, "error": "row missing"})
                continue
            a = json.loads(rf.read_text(encoding="utf-8"))["a1_answer"]
            t0 = time.time()
            dc = direction_check_llm(p, a, gw_key)
            rec = {
                "problem_id": pid,
                "v76_direction_scan": sorted(scan_physics_direction(
                    p, a)),
                "v77_direction_lexicon": sorted(direction_lexicon_check(
                    p, a)),
                "v77_input_availability": sorted(scan_input_availability(
                    p, a)),
                "v77_duty_cycle_pricing": sorted(scan_duty_cycle_pricing(
                    a)),
                "v77_mechanism_template": sorted(scan_mechanism_template(
                    a, Counter())),
                "v77_direction_llm": {
                    "direction": dc.get("direction"),
                    "reason": str(dc.get("reason") or "")[:220]},
                "latency_s": round(time.time() - t0, 1),
            }
            rows.append(rec)
            print(f"  [firetest] {pid[:40]:<42} "
                  f"dir_llm={dc.get('direction'):<26} "
                  f"lex={bool(rec['v77_direction_lexicon'])} "
                  f"in={bool(rec['v77_input_availability'])} "
                  f"pr={bool(rec['v77_duty_cycle_pricing'])}",
                  flush=True)
    finally:
        try:
            gw.terminate()
        except Exception:
            pass

    def row(pid):
        return next((r for r in rows if r["problem_id"] == pid), {})

    def fired(r, key):
        return bool(r.get(key))

    mapping = {
        "HO6-02_direction_fires": (
            fired(row("HO6-02-caster-mould-taper"),
                  "v77_direction_lexicon")
            or row("HO6-02-caster-mould-taper", {}).get(
                "v77_direction_llm", {}).get("direction")
            in ("INVERTED", "UNCLEAR")),
        "HO6-03_pricing_fires": fired(
            row("HO6-03-fcc-cyclone-erosion"),
            "v77_duty_cycle_pricing"),
        "HO6-04_input_fires": fired(
            row("HO6-04-gis-spacer-charge"),
            "v77_input_availability"),
        "HO6-12_input_fires": fired(
            row("HO6-12-dhx-scaling"), "v77_input_availability"),
    }
    record = {
        "record": "R40_V77_FIRETEST/1.0.0",
        "claim": "c-0046 (pre-registered; the checks validated over "
                 "the COMMITTED v6 rows — zero regeneration; the v6 "
                 "rows stay burned)",
        "rows": rows,
        "acceptance_mapping": mapping,
        "note": "the mapping validates the CHECKERS against the "
                "auditor's cited failures; the authoritative v7 "
                "acceptance read is the auditor's on the v7 packet",
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"-> {OUT}")
    print("mapping:", json.dumps(mapping))
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)
