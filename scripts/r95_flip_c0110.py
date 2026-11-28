#!/usr/bin/env python3
"""R95: flip c-0110 OPEN->DONE on completion."""
import json
import datetime

NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
c = next(x for x in claims if str(x.get("claim_id")) == "c-0110")
assert str(c.get("status")).upper() == "OPEN", "c-0110 not OPEN"
c["status"] = "DONE"
c["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
c["completion_note"] = (
    "DONE: the AIDE tree-search controller is landed and green — "
    "discovery_fabric/engine/aide_tree_search.py (engine-native, F63-"
    "clean; pattern copy only: WecoAI/aideml MIT, zero upstream code "
    "bytes, NOTICE rows updated — the library row now names the landed "
    "module and the pattern-copies section carries the c-0110 entry). "
    "The single-chain repair loop becomes a best-first POPULATION "
    "search: the metric is the machine's OWN finding surface (residual "
    "finding count, critic verdict, type-gate verdict — lexicographic, "
    "canonical sorted-key digests); each repair slot refines the live "
    "node with the LOWEST metric (ties break to the LATEST — the AIDE "
    "journal ordering); the frontier is metric-pruned to top-K (K=2: "
    "best + latest) with every pruned node typed pruned_reason="
    "metric_pruned in the trajectory; each slot carries a DISTINCT "
    "process-only structural angle from the roster (no angle repeats "
    "within a row while unused angles remain; the rotation is seeded "
    "from the problem key's CONTENT via sha256 — never Python hash()). "
    "Budget-MATCHED: the controller adds ZERO LLM calls — the slots are "
    "exactly the incumbent's (draft + REPAIR_BUDGET=3); next_slot() "
    "returns None once the budget is used. INCUMBENT PARITY: "
    "population=False reduces EXACTLY to the frozen single chain "
    "(parent always latest, no angle text, chain n0->n1->n2->n3) — the "
    "c-0106 invariant-7 pattern. CI battery tests/test_r95_aide_tree_"
    "search.py: 14 deterministic tests, zero LLM, zero network (budget "
    "cap never exceeded; best-first selection proven — the parent is "
    "the best node, not the latest; metric-pruning recorded; "
    ">=3 distinct candidates on a full-budget row — the AM82 roadmap "
    "acceptance surface, CI-encoded; parity proof; degenerate inputs "
    "typed (budget 0 -> draft is the final selection; None scan -> "
    "empty surface); determinism across PYTHONHASHSEED 1/2 in fresh "
    "subprocesses (the Art. 15 pattern); signature digests order-"
    "independent; angle rotation content-seeded; and the composition "
    "proof — TOOLS FIRST, TREE SECOND: the c-0109 corrector mechanically "
    "corrects a candidate BEFORE it is scored and the best-first "
    "selection carries the corrected node). CI wiring additive-forward-"
    "only: tests/test_r95_aide_tree_search.py joins the queue-surface "
    "invocation list (r11_queue_surface.yml, next to the c-0109 suite). "
    "NO frozen bytes touched; the c-0109 lane referenced READ-ONLY (the "
    "corrector module is imported in the composition test, never "
    "edited); the c-0106 peer lane untouched. Art. 29(e) stand-down on "
    "this window's duplicate local c-0109 claim rows typed in "
    "scripts/r95_claim_c0110.py (the remote canonical c-0109 stands). "
    "NO live LLM calls: the live matched-budget measurement is the v12 "
    "sealed one-shot (the auditor's path-to-6: CRITIC tool-grounding + "
    "AIDE tree search + all five binds on agnes-3.0-flash; mean >=3.25, "
    "0 inverted, CI > 3.0 -> score 6); quota is not spent on a parallel "
    "DEV arm before the sealed run (typed sequencing decision). Art. "
    "27: the engine behavior change is the controller surface itself "
    "(engine lines >=30% of this round's diff, F63-clean); no "
    "diagnostic-only commits.")
c["result"] = {
    "module": "discovery_fabric/engine/aide_tree_search.py",
    "tests": "tests/test_r95_aide_tree_search.py (14 deterministic, "
             "zero LLM, zero network)",
    "ci_wiring": ".github/workflows/r11_queue_surface.yml (additive)",
    "notice": "WecoAI/aideml MIT — library row + pattern-copies row",
    "acceptance_surface": {
        "budget_matched": "slots == incumbent slots; controller adds 0 "
                          "calls (CI-proven)",
        "best_first": "parent = lowest-metric live node, ties -> latest "
                      "(CI-proven on a mock where best != latest)",
        "distinct_candidates": ">=3 per full-budget row (CI-encoded, "
                               "the AM82 roadmap acceptance)",
        "schedule_family_cap": "untouched — the winner-rule histogram "
                               "logic is the machine's own, not the "
                               "controller's",
        "parity_mode": "population=False -> the frozen single chain "
                       "byte-identically (CI-proven)",
    },
    "next_steps_typed": [
        "the v12 sealed one-shot runs BOTH controllers (c-0109 corrector "
        "+ c-0110 tree) with all five binds on agnes-3.0-flash — the "
        "auditor's path-to-6 gate (mean >=3.25, 0 inverted, CI > 3.0)",
        "the machine-side wiring of the c-0109 corrector rides the "
        "CI-gated re-freeze discipline in the v12 driver composition",
    ],
}
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("c-0110 flipped DONE")
