#!/usr/bin/env python3
"""R80 matched-budget DEV ablation harness for the repair-loop convergence
layer (AM79 roadmap integration discipline: every copy gets a matched-budget
DEV ablation BEFORE adoption). This run is the DETERMINISTIC FIXTURE stage
(zero LLM, Art. 22 mechanics-proof): the same fixture battery through the
baseline loop (no memory, fixed budget) and the convergence loop (Reflexion
memory + Self-Refine stop), matched budget 3. The REAL pre-adoption ablation
(same DEV rows, matched budget, live generation both arms) is the next stage
and runs only when the frozen-side wiring plan + quota are authorized —
typed, not silent (Art. 5). Emits eval/r80_convergence_ablation.json."""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location(
    "r80c", REPO / "scripts" / "r80_repair_convergence.py")
r80c = importlib.util.module_from_spec(spec)
sys.modules["r80c"] = r80c
spec.loader.exec_module(r80c)

from tests.test_r80_repair_convergence import FIXTURES  # noqa: E402

rows = {}
for name, model in FIXTURES.items():
    base = r80c.run_loop(model, budget=3, convergence=False)
    conv = r80c.run_loop(model, budget=3, convergence=True)
    rows[name] = {"baseline": base, "convergence": conv,
                  "delta_repairs": base["repairs_used"] - conv["repairs_used"],
                  "regressed": conv["converged"] < base["converged"]
                  or conv["repairs_used"] > base["repairs_used"]}
    assert not rows[name]["regressed"], name

burn_base = sum(1 for r in rows.values() if r["baseline"]["budget_burned_full"])
burn_conv = sum(1 for r in rows.values()
                if r["convergence"]["budget_burned_full"])
rep_base = sum(r["baseline"]["repairs_used"] for r in rows.values())
rep_conv = sum(r["convergence"]["repairs_used"] for r in rows.values())

record = {
    "record": "R80_CONVERGENCE_ABLATION_FIXTURES/1.0.0",
    "session": "builder-r80s1",
    "stage": "DETERMINISTIC_FIXTURES (zero LLM, Art. 22 mechanics proof)",
    "arms": ["baseline (fixed budget 3, no memory, no stop)",
             "convergence (Reflexion memory + Self-Refine structured stop, "
             "budget 3)"],
    "matched_budget": True,
    "rows": rows,
    "aggregate": {
        "baseline_burned_full": burn_base,
        "convergence_burned_full": burn_conv,
        "baseline_repairs_total": rep_base,
        "convergence_repairs_total": rep_conv,
        "repairs_saved": rep_base - rep_conv,
        "rows_regressed": sum(1 for r in rows.values() if r["regressed"]),
    },
    "typed_notes": [
        "The stop criterion is the CONSERVATIVE rule: stop only on an EXACT "
        "failure-signature repeat (same problem set as the immediately "
        "prior attempt); an improving or churning sequence always keeps its "
        "full budget. The saved budget on the repeat class is provably safe "
        "on fixtures; the LLM-stage ablation must confirm it on live rows.",
        "The early stop is typed as BUDGET-SAVED, not as convergence: the "
        "row stays unresolved with its findings disclosed (never hidden, "
        "Art. 5) — the auditor sees the identical residual picture.",
        "The REAL pre-adoption gate (roadmap integration discipline) is the "
        "matched-budget LIVE ablation on DEV rows both arms; adoption "
        "requires: no mean drop, ALLOWED_ROW_OUTSIDE=0, and the convergence "
        "gate (>=50% of rows zero-findings within budget) measured on the "
        "NEXT sealed set with the layer wired at the frozen call site under "
        "the CI-gated re-freeze discipline.",
    ],
    "next_steps": [
        "1. LLM-stage matched-budget DEV ablation (both arms, live rows).",
        "2. Frozen-side wiring: enrich the frozen machine's repair directive "
        "with the reflection note + wire the structured stop, via the "
        "non-frozen seam or a typed frozen edit under CI-gated re-freeze.",
        "3. Re-freeze with the freeze guard; CI-wired immutability test for "
        "the frozen bytes.",
    ],
}
dest = REPO / "eval" / "r80_convergence_ablation.json"
dest.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
print(json.dumps(record["aggregate"], indent=1))
print("written:", dest)
