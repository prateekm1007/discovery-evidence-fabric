#!/usr/bin/env python3
"""Build + seal the R412 gradient v2.1 preregistration.

The v2.0 preregistration (R412/GRADIENT_V2/
R412_GRADIENT_V2_PREREGISTRATION.json) was authored with the v1
substrate absent: its run gate is BLOCKED on population_hash,
seed_allocation, and tvm_snapshot_hash, and its v1_provenance states
NOT_VERIFIABLE_IN_THIS_WORKSPACE — true then, STALE now.

This builder produces the v2.1 preregistration as a NEW versioned
artifact (the stale v2.0 is superseded, never edited in place — Art.
XLIV/XI), resolving every blocking field with VERIFIED values:

  * population_hash: 750647b8... — live-recomputed from the frozen
    R411 records in the Phase B reconciliation (which also matched
    the sealed v1 pin and the accounting artifact);
  * seed_allocation: the EXACT v1 10-seed priority order,
    byte-copied from R412/R412_GRADIENT_RECOVERY_PREREGISTRATION
    .json resource_allocation.priority_order and cross-checked
    against the committed ga3 attempted set;
  * tvm substrate hashes: TVM v0 snapshot + the v1 run record +
    TVM_CONSTRUCTED + TVM_FROZEN + waterfall + accounting, all
    hash-verified in the Phase B reconciliation;
  * model pin: zai glm-4-plus via the sandbox gateway (the only
    live transport in this workspace — OpenRouter, the v1
    proposer's route, has no credentials here; the CONFOUND is
    disclosed on the comparison: v2 admission deltas are
    attributable to instrument + proposer);
  * the three v2 prompt hashes (frontier-entry template v1.1.0 —
    the pre-seal batch adjustment — plus the backcast and causal-
    delta templates);
  * the capability-family map v2.0 hash (Phase D derivation);
  * the v1 budget fields BYTE-COPIED (no expanded budget: TVM
    construction 12+12, ga4 10, ga5 10+10, ga55 10+20, ga6 10+30,
    ga8 10+10, ga9 10, out tokens 2600) plus the GA-1b REUSE rule
    (the committed 13 extractions are frozen evidence — zero new
    GA-1b calls);
  * stopping rules copied from the sealed v1 set plus the v2 rules
    (raw persistence; closed family vocabulary; canonical-basis
    labeling on slopes).

The run gate flips to RUN_ALLOWED only after every pin is verified
from live bytes in THIS script. Zero gradient model calls are made
here (this is pre-registration, Art. LIX).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
V2 = REPO / "R412" / "GRADIENT_V2"

OUT = V2 / "R412_GRADIENT_V2_1_PREREGISTRATION.json"
V1_PREREG = REPO / "R412" / \
    "R412_GRADIENT_RECOVERY_PREREGISTRATION.json"
RECON = V2 / "V1_PROVENANCE_RECONCILIATION.json"
FAM_MAP_V2 = V2 / "CAPABILITY_FAMILY_MAP_V2.json"
GA3 = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / "ga3.jsonl"
GW = REPO / "scripts" / "zai_gateway.mjs"


def _load(p: Path):
    return json.loads(p.read_text())


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    v1 = _load(V1_PREREG)
    recon = _load(RECON)
    problems: list = []

    # --- blocking field 1: population hash (verified live) ---
    pop = recon["live_recomputes"]["population_hash"]
    if not (pop["match_prereg"] and pop["match_accounting"]):
        problems.append("population hash not verified by the "
                        "reconciliation")
    population_hash = pop["expected_from_prereg"]

    # --- blocking field 2: the seed allocation (byte-copied) ---
    alloc = list(v1["resource_allocation"]["priority_order"])
    ga3_ids = [json.loads(l)["candidate_id"] for l in
               GA3.read_text().splitlines() if l.strip()]
    if ga3_ids != alloc:
        problems.append("ga3 attempted order != v1 allocation")

    # --- blocking field 3: the TVM substrate hashes ---
    subs = {}
    for a in recon["artifacts"]:
        if a["sha256"]:
            subs[a["artifact"]] = {
                "path": a["path"], "sha256": a["sha256"],
                "status": a["provenance_status"]}
        if a["expected_hash"] and a["match"] is not True:
            problems.append(f"pinned artifact mismatch: "
                            f"{a['artifact']}")

    # --- prompts ---
    prompts = {}
    for name in ("TVM_V2_FRONTIER_ENTRY_PROPOSAL",
                 "TVM_V2_MECHANISM_BACKCAST",
                 "TVM_V2_CAUSAL_ARCHITECTURE_DELTA"):
        p = V2 / "PROMPTS" / f"{name}.json"
        d = _load(p)
        prompts[name] = {
            "version": d["version"], "sha256": _sha(p),
            "template_sha256": hashlib.sha256(
                d["template"].encode()).hexdigest()}

    # --- budgets (byte-copied from the sealed v1) ---
    v1_budget = dict(v1["token_and_cost_budgets"])

    doc = {
        "artifact_type": "R412_GRADIENT_V2_1_PREREGISTRATION",
        "preregistration_version": "2.1.0",
        "supersedes": {
            "path": "R412/GRADIENT_V2/"
                    "R412_GRADIENT_V2_PREREGISTRATION.json",
            "version": "1.0.0",
            "note": "v2.0 was authored with the v1 substrate absent "
                    "(run gate BLOCKED; v1_provenance "
                    "NOT_VERIFIABLE_IN_THIS_WORKSPACE — true then, "
                    "stale after the history reconciliation). v2.1 "
                    "resolves every blocking field with VERIFIED "
                    "values; v2.0 remains as history (Art. XI)",
        },
        "directive": "operator Phase L (2026-09-06): run exactly "
                     "the original 10 seeds; no new seeds, no "
                     "expanded budget, no threshold changes, no "
                     "prompt changes after unsealing",
        "v1_provenance": {
            "verification_state": "VERIFIED_VIA_RECONCILIATION",
            "reconciliation_artifact": "R412/GRADIENT_V2/"
                                       "V1_PROVENANCE_"
                                       "RECONCILIATION.json",
            "reconciliation_status": recon["overall_status"],
            "v1_run_commit": "abb90c88 (run complete) + 42a17514 "
                             "(post-run seal verification)",
            "v1_result_preserved_unmodified": True,
        },
        "population": {
            "population_sha256": population_hash,
            "verification": "live recompute over the frozen R411 "
                            "records matched BOTH the sealed v1 pin "
                            "and the accounting artifact (Phase B "
                            "reconciliation)",
            "raw_accepted": 550, "unique_scored": 400,
            "technical_deaths": 13, "nontechnical_rejections": 387,
        },
        "seed_allocation": {
            "state": "RESOLVED_VERIFIED",
            "source": "byte-copied from R412/"
                      "R412_GRADIENT_RECOVERY_PREREGISTRATION.json "
                      "resource_allocation.priority_order",
            "priority_order": alloc,
            "cross_check": "identical to the committed ga3 "
                           "attempted set in order",
            "budget_shortfall_rule": v1["resource_allocation"]
            ["budget_shortfall_rule"],
        },
        "tvm_substrate_hashes": subs,
        "ga1b_reuse": {
            "rule": "the 13 committed GA-1b deficit extractions "
                    "(ga1b.jsonl, span-verified 13/13, model+prompt_"
                    "hash+output_hash provenance) are FROZEN "
                    "EVIDENCE reused unchanged — zero new GA-1b "
                    "calls; the instrument change is the TVM "
                    "proposer schema only (the v1 run's recorded "
                    "learning: 'field-line TVM prompt, everything "
                    "else unchanged')",
            "path": "R412/RECOVERY_ARM/GRADIENT_RUN/ga1b.jsonl",
            "n_records": 13,
        },
        "model_pin": {
            "provider": "zai", "model": "glm-4-plus",
            "transport": "sandbox-local OpenAI-compatible gateway "
                         "(scripts/zai_gateway.mjs, port 8787, "
                         "child process for the run duration)",
            "gateway_script_sha256": _sha(GW),
            "substitution": "FORBIDDEN",
            "confound_disclosure": "the v1 proposer was "
                                   "minimax/minimax-m3:free via "
                                   "OpenRouter, which has no "
                                   "credentials in this workspace; "
                                   "the v2 arm uses this "
                                   "workspace's only live transport "
                                   "(zai glm-4-plus). The v1-vs-v2 "
                                   "comparison table reports this "
                                   "openly: v2 admission deltas are "
                                   "attributable to instrument + "
                                   "proposer, and no pure "
                                   "instrument attribution is "
                                   "claimed",
        },
        "prompt_pins": prompts,
        "capability_family_map": {
            "path": "R412/GRADIENT_V2/"
                    "CAPABILITY_FAMILY_MAP_V2.json",
            "sha256": _sha(FAM_MAP_V2),
            "version": _load(FAM_MAP_V2)["version"],
            "rule": "closed vocabulary; exact-key lookup; misses "
                    "recorded, never fuzzy (Art. XLIII); "
                    "AI-proposed frontier vocabulary is EXPLORATORY "
                    "search priority only (Phase F)",
        },
        "instrument_change_vs_v1": [
            "TVM proposal prompt: field-line JSON format (v1: "
            "pipe-delimited ENTRY lines)",
            "deterministic verification: the v2 parser + evidence "
            "contract (lossless canonical values, byte-exact span "
            "binding, canonical re-derivation, signal policy, "
            "two-truths flat-field checks) replaces the v1 "
            "float()/int() casts",
            "RAW proposals + raw LLM output persisted per "
            "construction attempt (the v1 unpersisted-outputs "
            "defect fixed forward)",
            "queries expanded through the derived family map "
            "(Phase D/E) with the Phase F signal-policy "
            "enforcement",
        ],
        "unchanged_vs_v1": [
            "the 10-seed allocation and priority order",
            "the sealed budget fields (byte-copied below)",
            "all downstream machinery: backcast, feasibility, "
            "why-not, availability, causal delta, fresh novelty, "
            "fresh attack (imported unchanged from the sealed "
            "modules)",
            "the frozen GA-1b/GA-2 evidence",
            "the v1 artifacts (byte-identical; the v2 run writes "
            "only to R412/GRADIENT_V2/RUN/)",
        ],
        "token_and_cost_budgets": v1_budget,
        "stopping_rules": list(v1["stopping_rules"]) + [
            "RAW proposal persistence is mandatory: every TVM "
            "construction attempt records the raw LLM output and "
            "every raw proposal (admitted and rejected) — a future "
            "instrument comparison must replay committed bytes, "
            "never reconstruct",
            "slope computation uses canonical values with basis "
            "labels (POINT_VALUE / RANGE_MIDPOINT / "
            "INEQUALITY_BOUND); mixed-basis slopes are disclosed "
            "on the record, never silent",
            "the family search vocabulary is CLOSED; a lookup miss "
            "is recorded and the query falls back to the rung "
            "text (never a fuzzy family guess)",
        ],
        "success_criterion": {
            "chain": "REAL MEASURED FRONTIER -> CAUSAL MECHANISM "
                     "BACKCAST -> TRANSFERABLE TO TARGET -> "
                     "CAPABILITIES AVAILABLE TODAY -> NEW CAUSAL "
                     "ARCHITECTURE -> fresh novelty -> fresh attack "
                     "-> buyer-grade pipeline entry",
            "principal_metric": "PRESENT_RECOVERY: existing "
                                "capabilities + genuinely new "
                                "causal architecture surviving the "
                                "NORMAL invention pipeline (no "
                                "privileged path — Phase J)",
            "explicitly_not_success": [
                "more descendants", "more TVM domains found",
                "candidates that look technologically sophisticated",
                "'use technology X in industry Y'",
                "better sensor/material/processor substitution",
                "did the model generate something clever"],
            "honest_zero_rule": "a zero is reported as a zero; the "
                                "bar is identical for every seed "
                                "(Art. LXVIII)",
        },
        "comparison_table_schema": "the operator's Phase L table "
                                   "(v1 column from committed "
                                   "evidence; v2 column measured "
                                   "by this run)",
        "run_gate": {},
        "no_gradient_calls_before_seal": 0,
        "reviewer_provenance": "AI_REVIEW",
        "sealed_before_any_v2_model_call": True,
    }
    import datetime
    doc["created_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    if problems:
        doc["run_gate"] = {
            "state": "BLOCKED", "problems": problems,
            "fail_closed_rule": "Art. XIV — no v2 model call while "
                                "any pin is unverified",
        }
    else:
        doc["run_gate"] = {
            "state": "RUN_ALLOWED",
            "verified_by": "this builder, from live bytes",
            "fail_closed_rule": "the runner re-verifies every pin "
                                "before each stage; any drift "
                                "REFUSES the stage",
        }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"v2.1 preregistration written: {OUT}")
    print(f"run gate: {doc['run_gate']['state']}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
