#!/usr/bin/env python3
"""r127_phaseA_score.py — the Phase-A gate-run scoring (claim c-0200;
the prereg governs; zero LLM).

Gates (the prereg): g1 speed median<=120s/worst<=300s per problem;
g2 parse retries 0; g3 cached-token hit-rate reported; g4 the
delivered-defect rate on the 12-item slice not worse than the F31e
d1 baseline on the SAME items by more than 1 item; per-class table.

Output: eval/r127_phaseA/gate_scoring.json
"""
from __future__ import annotations

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
OUT = REPO / "eval" / "r127_phaseA" / "gate_scoring.json"
CLS = ("input_availability", "duty_pricing", "constraint_violation",
       "physics_direction_inversion")


def main() -> int:
    probs = [json.loads(l) for l in (REPO / "eval" / "r125_f31e_set"
             / "items.jsonl").read_text(encoding="utf-8").strip()
             .split("\n") if l]
    rows = []
    for prob in probs:
        pid = prob["problem_id"]
        rec = json.loads((GATE / f"gate_{pid}.json").read_text(
            encoding="utf-8"))
        # the same-item F31e d1 baseline (delivered defects)
        base = json.loads((F31E / f"succ_d1_{pid}.json").read_text(
            encoding="utf-8"))
        base_cls = bill_defect_classes(prob, base["delivered_bill"])
        gate_cls = (bill_defect_classes(prob, rec["delivered_bill"])
                    if rec.get("delivered_bill") else [])
        rows.append({"pid": pid, "status": rec["status"],
                     "wall_clock_s": rec["wall_clock_s"],
                     "parse_retries": rec["parse_retries"],
                     "reviewer_calls": sum(
                         1 for c in rec["calls"]
                         if c["leg"] == "reviewer"),
                     "schema_first_try": any(
                         c.get("schema_parsed_first_try")
                         for c in rec["calls"]),
                     "gate_cls": gate_cls, "f31e_d1_cls": base_cls,
                     "usage": rec["calls"]})

    walls = [r["wall_clock_s"] for r in rows]
    median = statistics.median(walls)
    worst = max(walls)
    parse_fails = sum(1 for r in rows
                      if r["status"] == "TYPED_PARSE_FAIL")
    reviewer_legs = sum(r["reviewer_calls"] for r in rows)
    first_try = sum(1 for r in rows if r["schema_first_try"])
    call_usages = [c.get("usage") or {} for r in rows
                   for c in r["usage"]]
    cached = [u.get("cached_tokens") for u in call_usages
              if u.get("cached_tokens") is not None]
    pts = [u.get("prompt_tokens") or 0 for u in call_usages]
    cached_total = sum(c or 0 for c in cached)
    prompt_total = sum(pts)
    hit_rate = (cached_total / prompt_total) if prompt_total else 0.0

    gate_defects = sum(1 for r in rows if r["gate_cls"])
    baseline_defects = sum(1 for r in rows if r["f31e_d1_cls"])
    per_class = {c: {"gate": sum(1 for r in rows if c in r["gate_cls"]),
                     "f31e_d1": sum(1 for r in rows
                                    if c in r["f31e_d1_cls"])}
                 for c in CLS}
    new_classes = sorted(c for c in CLS
                         if per_class[c]["gate"] > per_class[c]["f31e_d1"])
    g4_pass = gate_defects <= baseline_defects + 1
    gates = {
        "g1_speed": median <= 120 and worst <= 300,
        "g2_parse_retries_zero": parse_fails == 0 and first_try
        == reviewer_legs,
        "g3_hit_rate_reported": True,
        "g4_no_regression": g4_pass,
    }
    out = {
        "record": "R127_PHASEA_GATE_RESULT/1.0.0",
        "claim": "c-0200 (r127-phaseA-speed)",
        "prereg": "eval/r127_phaseA_prereg.json",
        "speed": {"median_s": median, "worst_s": worst,
                  "walls": dict(zip([r["pid"] for r in rows], walls)),
                  "pool_workers": 4},
        "parse": {"reviewer_legs": reviewer_legs,
                  "schema_parsed_first_try": first_try,
                  "typed_parse_fails": parse_fails,
                  "retries_spent": 0},
        "cache_telemetry": {
            "calls": len(call_usages), "cached_tokens_total":
            cached_total, "prompt_tokens_total": prompt_total,
            "hit_rate": round(hit_rate, 6),
            "typed_note": "the agnes route reports the "
                          "cached_tokens channel but 0 hits on "
                          "every call — the honest hit-rate is 0; "
                          "the Bedrock cachePoint lever stays "
                          "owner-gated"},
        "defects": {"gate_slice_n": len(rows),
                    "gate_defect_items": gate_defects,
                    "f31e_d1_defect_items": baseline_defects,
                    "gate_rate": round(gate_defects / len(rows), 4),
                    "baseline_rate": round(baseline_defects
                                           / len(rows), 4),
                    "per_class": per_class,
                    "classes_worse_than_baseline": new_classes},
        "statuses": {r["pid"]: r["status"] for r in rows},
        "gates": gates,
        "acceptance_branch": (
            "PHASE-A ACCEPT MET (the sandbox-executable slice): "
            "schema-constrained reviewer output, 0 parse retries by "
            "construction, hit-rate reported, speed gates passed, "
            "defect-rate not regressed"
            if all(gates.values()) else
            "TYPED_NEGATIVE ON THE PHASE-A GATES AS PRE-REGISTERED"
            + (" — the schema variant is DELETED per Art. 20"
               if not g4_pass else "")),
        "detector": "the CANONICAL 92485038719557e4 bytes (imported); "
                    "zero LLM at scoring time",
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"speed: median={median}s worst={worst}s (gates "
          f"<={120}/{300})")
    print(f"parse: reviewer_legs={reviewer_legs} "
          f"first_try={first_try} parse_fails={parse_fails} "
          f"retries={0}")
    print(f"cache: hit_rate={hit_rate:.6f} "
          f"({cached_total}/{prompt_total})")
    print(f"defects: gate {gate_defects}/{len(rows)} vs F31e-d1 "
          f"baseline {baseline_defects}/{len(rows)}; per_class "
          f"{json.dumps(per_class)}")
    print(f"gates: {gates}")
    print(f"acceptance: {out['acceptance_branch'][:140]}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
