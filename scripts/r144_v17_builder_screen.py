#!/usr/bin/env python3
"""r144s1 v17 builder screen — the typed INPUT record for the auditor
(Art. 14: machine scores are inputs, never the verdict). Reads ONLY
the committed run bytes; computes the routing/winner/scan surface;
no scoring."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "holdout_v17_generation"

NUM_UNIT = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:[µμu]m|mm|cm|m\b|kPa|MPa|Pa\b|bar\b|°C|"
    r"\bK\b|W\b|kW\b|MW\b|J\b|kJ\b|Wh\b|kWh\b|N\b|kN\b|Hz\b|kHz\b|"
    r"rpm|A\b|mA\b|V\b|mV\b|kV\b|s\b|ms\b|min\b|h\b|mol|ppm|wt\s?%|"
    r"%|L(?:/min|/s|/h)?|g(?:/cm3|/L)?|kg(?:/h)?|m/s)\b", re.I)
FALSIFY = re.compile(
    r"falsif\w*|kill condition|refuted if|disconfirm\w*|"
    r"would (?:prove|show) .* (?:wrong|fails)", re.I)
CALC = re.compile(r"=\s*-?\d|\bcalculat\w*|\bsubstitut\w*|"
                  r"governing relation", re.I)

rows = []
for f in sorted(OUT.glob("v17-*.json")):
    d = json.loads(f.read_text())
    ans = d["a1_answer"]
    rows.append({
        "problem_id": d["problem_id"],
        "family": d["engine_trace"]["failure_physics"]["family"],
        "winner_class": d["engine_trace"]["failure_physics"]["winner_measure_class"],
        "winner_principle": d["engine_trace"]["failure_physics"]["winner_principle_id"],
        "chars": len(ans),
        "critic": d["final_meta"].get("critic_verdict"),
        "residual_keys": sorted((d["final_meta"].get("residual_findings") or {}).keys()),
        "has_numeric_unit": bool(NUM_UNIT.search(ans)),
        "has_worked_calc": bool(CALC.search(ans)),
        "has_kill_condition": bool(FALSIFY.search(ans)),
        "sha256_16": d["sha256_16"],
    })

n = len(rows)
fams = Counter(r["family"] or "NO_FAMILY" for r in rows)
winners = Counter(r["winner_class"] for r in rows)
quant_full = sum(1 for r in rows if r["has_numeric_unit"]
                 and r["has_worked_calc"] and r["has_kill_condition"])
quant_partial = sum(1 for r in rows if r["has_numeric_unit"]
                    and r["has_worked_calc"])
kills = sum(1 for r in rows if r["has_kill_condition"])
clean = sum(1 for r in rows if not r["residual_keys"])

record = {
    "record": "V17_BUILDER_SCREEN/1.0.0",
    "at": "2026-11-24",
    "executor": "builder-r144s1@holdout-v17-generation",
    "run": "holdout-v17-generation (one-shot, problem-only, the LANDED generation-strength engine)",
    "n": n,
    "wall_s": 355.7,
    "resumed": 0,
    "registered_model": "agnes-3.0-flash",
    "family_routing": dict(fams),
    "winner_classes": dict(winners),
    "quantitative_testability_surface": {
        "numeric_with_unit": sum(1 for r in rows if r["has_numeric_unit"]),
        "worked_calculation": quant_partial,
        "kill_condition": kills,
        "all_three": quant_full,
        "note": "the builder screen — INPUT for the auditor (Art. 14), never the scoring verdict",
    },
    "typed_findings_summary": {
        "rows_clean": clean,
        "rows_with_findings": n - clean,
        "finding_keys": dict(Counter(k for r in rows for k in r["residual_keys"])),
    },
    "per_row": rows,
    "honest_typing": {
        "scoring": "PENDING-AUDITOR-SCORE — the v17 set is the builder-authored CANDIDATE set; the seal + rubrics + scoring stay the AUDITOR's act (Art. 7/28-addendum)",
        "acceptance_gate": "mean>=3.3 AND CI lower>3.0 AND >=30% strong (4) — NOT computed here (Art. 10/14: the builder never scores itself)",
    },
}
out = REPO / "eval" / "holdout_v17_builder_screen.json"
out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print(json.dumps({k: record[k] for k in
                  ("n", "family_routing", "winner_classes",
                   "quantitative_testability_surface",
                   "typed_findings_summary")}, indent=1))
