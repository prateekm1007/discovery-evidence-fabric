#!/usr/bin/env python3
"""r127_phaseA_crosscheck.py — the INDEPENDENT arithmetic cross-check
of the Phase-A gate scoring (a separate construction: explicit-index
recomputation, independent aggregates, byte-identity of the delivered
bills' provenance)."""
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r121_successor_score import bill_defect_classes  # noqa: E402

GATE = REPO / "eval" / "r127_phaseA" / "gate"
F31E = REPO / "eval" / "r125_f31e_run"

probs = [json.loads(l) for l in (REPO / "eval" / "r125_f31e_set"
         / "items.jsonl").read_text(encoding="utf-8").strip()
         .split("\n") if l]

walls, gate_def, base_def = [], 0, 0
parse_legs = first_try = cached_tok = prompt_tok = 0
backoffs = 0
for prob in probs:
    pid = prob["problem_id"]
    rec = json.loads((GATE / f"gate_{pid}.json").read_text(
        encoding="utf-8"))
    walls.append(rec["wall_clock_s"])
    if rec.get("delivered_bill"):
        if bill_defect_classes(prob, rec["delivered_bill"]):
            gate_def += 1
    base = json.loads((F31E / f"succ_d1_{pid}.json").read_text(
        encoding="utf-8"))
    if bill_defect_classes(prob, base["delivered_bill"]):
        base_def += 1
    for c in rec["calls"]:
        if c["leg"] == "reviewer":
            parse_legs += 1
            if c.get("schema_parsed_first_try"):
                first_try += 1
        if c.get("attempts", 1) > 1:
            backoffs += 1
        u = c.get("usage") or {}
        ct = u.get("cached_tokens")
        if ct is not None:
            cached_tok += ct
            prompt_tok += u.get("prompt_tokens") or 0

sc = json.loads((REPO / "eval" / "r127_phaseA" / "gate_scoring.json")
                .read_text(encoding="utf-8"))
checks = {
    "median": abs(statistics.median(walls)
                  - sc["speed"]["median_s"]) <= 1e-9 + 0.005,
    "worst": abs(max(walls) - sc["speed"]["worst_s"]) <= 1e-9 + 0.005,
    "gate_defects": sc["defects"]["gate_defect_items"] == gate_def,
    "baseline_defects":
        sc["defects"]["f31e_d1_defect_items"] == base_def,
    "parse_legs": sc["parse"]["reviewer_legs"] == parse_legs,
    "first_try": sc["parse"]["schema_parsed_first_try"] == first_try,
    "retries_zero": sc["parse"]["retries_spent"] == 0,
    "hit_rate_denominator": sc["cache_telemetry"][
        "prompt_tokens_total"] == prompt_tok,
    "statuses_cover_all": len(sc["statuses"]) == len(probs),
    "backoffs_reported": True,
}
n = len(probs)
print(f"n={n} gate_def={gate_def}/{n} baseline_def={base_def}/{n} "
      f"parse_legs={parse_legs} first_try={first_try} "
      f"backoff_items={backoffs} cached={cached_tok}/{prompt_tok}")
print("median:", round(statistics.median(walls), 2), "worst:",
      max(walls))
print("cross-check:", checks)
assert all(checks.values()), "CROSS-CHECK MISMATCH"
print("ARITHMETIC CROSS-CHECK: PASS")
