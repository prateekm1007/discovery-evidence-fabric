#!/usr/bin/env python3
"""r95_claim_c0110.py — Art. 29(b) claim for round R95, work item
r95-aide-tree-search (claim c-0110), staked BEFORE any c-0110 work
byte.

ART. 29(e) STAND-DOWN RECORD (typed, never silent): this window
independently staked c-0109 + c-0110 at 05:46Z (local commit
ad801a110, NOT pushed — push failed non-fast-forward). The remote
already carried c-0109 (work_id critic-tool-grounding-dev, claimed
05:34:29Z, DONE at c252de328 with the full corrector + 13-test suite)
from the same session identity (builder-r95s1, the recycled sibling
context window). Per Art. 29(e): same-work_id => stand down, never
rebase a duplicate. The duplicate local claim rows (my c-0109 row and
my duplicate session note) are DISCARDED here — the remote's
canonical c-0109 row and session registration stand untouched. Only
the DISJOINT work (c-0110, r95-aide-tree-search — no remote commits
touch an AIDE/tree-search surface) is re-staked by this script and
pushed.

Lane division (typed): c-0110 composes with the canonical c-0109
corrector (discovery_fabric/engine/tool_grounded_critic.py) as a
READ-ONLY import surface — no bytes of the c-0109 lane are edited.
The c-0106 peer lane (builder-r93s1, OPEN) is untouched. Collision
check at stake time: no competing claim on r95-aide-tree-search; the
claim_id c-0110 is free.
"""
import json
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
BASE = "edbac00bb480214a829c312c15448c847c02e9a3"

registry_path = REPO / "eval" / "work_claims.json"
reg = json.loads(registry_path.read_text(encoding="utf-8"))

existing_ids = {c.get("claim_id") for c in reg.get("claims", [])}
assert "c-0110" not in existing_ids, "c-0110 already staked (abort)"
wid_claims = [c for c in reg.get("claims", [])
              if c.get("work_id") == "r95-aide-tree-search"]
assert not wid_claims, "work_id r95-aide-tree-search already claimed"

reg["claims"].append({
    "claim_id": "c-0110",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "r95-aide-tree-search",
    "title": (
        "R95 (AM82 direction 2, builder-r95s1): the AIDE tree-search "
        "controller, engine-native — "
        "discovery_fabric/engine/aide_tree_search.py (pattern copy "
        "only: WecoAI/aideml MIT, zero upstream code bytes, NOTICE "
        "row). The single-chain repair loop becomes a best-first "
        "POPULATION search: the machine's own finding surface is the "
        "metric; each repair slot refines a parent chosen best-first "
        "(lowest residual finding count, deterministic tie-break) "
        "across a DIVERSE angle roster (structural repair strategies "
        "— process-only instructions, no outcome/rubric information); "
        "the population is metric-pruned between slots; the "
        "trajectory records every node (>=3 distinct candidates per "
        "intervention row when the budget is used), the parent "
        "choice, the angle, and the per-node metric. Budget-MATCHED: "
        "the same call slots as the incumbent (draft + "
        "REPAIR_BUDGET=3); the controller adds ZERO LLM calls. "
        "Incumbent-parity mode: population=False reduces EXACTLY to "
        "the frozen single chain (byte-identical prompts, "
        "latest-node parenting, no angle text) — the c-0106 "
        "invariant-7 pattern. CI-wired deterministic battery "
        "tests/test_r95_aide_tree_search.py with a mock generator "
        "(zero LLM, zero network): budget cap never exceeded, "
        "best-first selection on recorded metrics, >=3 distinct "
        "candidate nodes, metric-pruning recorded, parity proof, "
        "degenerate inputs typed, determinism (the slot rotation is "
        "seeded from problem_id CONTENT, never Python hash()). NO "
        "frozen bytes touched; NO live LLM calls (the live "
        "matched-budget measurement is the v12 sealed one-shot — the "
        "auditor's path-to-6; quota is not spent on a parallel DEV "
        "arm before the sealed run). Composition with the canonical "
        "c-0109 corrector (tool_grounded_critic.py) is READ-ONLY on "
        "that lane."),
    "status": "OPEN",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": BASE,
    "lease_expiry": "2026-11-20T23:59:00Z",
    "takes_over": None,
    "artifact_paths": [
        "discovery_fabric/engine/aide_tree_search.py",
        "tests/test_r95_aide_tree_search.py",
        "scripts/r95_claim_c0110.py",
        "NOTICE.md",
        "eval/work_claims.json",
    ],
    "notes": (
        "Art. 29(e) stand-down on the c-0109 duplicate typed in the "
        "script docstring (the sibling context window's canonical "
        "row stands; never rebased). c-0110 is the disjoint item "
        "this window executes."),
    "no_problem_read_before_claim": True,
})

registry_path.write_text(
    json.dumps(reg, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("staked c-0110 (r95-aide-tree-search) for builder-r95s1 @",
      BASE[:9])
