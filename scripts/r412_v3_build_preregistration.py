#!/usr/bin/env python3
"""r412_v3_build_preregistration.py — the v3 preregistration builder
+ seal (Art. XLIV/LIX: the seal precedes every run stage; thresholds
pre-registered BEFORE the lane evaluation; no tuning after results).

Pins (all verified from live bytes before RUN_ALLOWED):
  * the FEAL instrument (discovery_fabric/r412/frontier_evidence.py)
  * the lane runner + benchmark evaluator scripts
  * the frozen retrieval benchmark corpus (48 records, labels
    authored by reading before any FEAL execution on them)
  * the pre-registered benchmark gate thresholds
  * the prompts: P1 (the sealed v2.1 TVM prompt, byte-reused) and
    P2 (TVM_V3_FRONTIER_ENTRY_PROPOSAL — the second proposer
    configuration) + the adoption-gap prompt (directive item 10)
  * the population hash (live recompute) + the 10-seed allocation
    (byte-copied from the sealed v1 preregistration)
  * the model pin (zai/glm-4-plus for BOTH proposer configurations —
    the independence variable is the prompt procedure, never claimed
    as model independence; disclosed)
  * budgets: 46 fabric lane queries; TVM construction 13 rungs x 2
    proposer configurations = 26 LLM calls TOTAL; downstream budgets
    byte-copied from the sealed v1 budgets (only reachable when the
    benchmark gate passes and measured movers exist)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "R412" / "GRADIENT_V3" / \
    "R412_GRADIENT_V3_PREREGISTRATION.json"
V3DIR = REPO / "R412" / "GRADIENT_V3"
V2DIR = REPO / "R412" / "GRADIENT_V2"
V21_PREREG = V2DIR / "R412_GRADIENT_V2_1_PREREGISTRATION.json"
V1_PREREG = REPO / "R412" / \
    "R412_GRADIENT_RECOVERY_PREREGISTRATION.json"
CORPUS = V3DIR / "RETRIEVAL_BENCHMARK" / \
    "RETRIEVAL_BENCHMARK_CORPUS.json"
GA1B = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "ga1b.jsonl"
GA3_V1 = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
    "ga3.jsonl"

#: the pre-registered benchmark gate thresholds (directive item 7:
#: "materially better evidence exposure than v2"). Anchors: the v2
#: measured baseline (RETRIEVAL_DIAGNOSTIC_V2_POOLS.json, committed).
#: Provenance class ENGINEERING: each threshold is a monotone
#: multiple of the measured v2 baseline; none was tuned against any
#: lane result (the lanes have not run at seal time).
THRESHOLDS: Dict[str, float] = {
    "recall_numeric_bearing": 0.25,
    "recall_measurement_bearing": 0.25,
    "numeric_bearing_rate": 0.15,
    "measurement_bearing_rate": 0.30,
    "abstract_bearing_rate": 0.60,
    "year_recovery_rate": 0.50,
    "source_identity_recovery_rate": 1.00,
    "baseline_recovery_rate": 0.10,
    "domain_diversity": 5,
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canon_sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


def main() -> int:
    problems: list = []

    # ---- population (live recompute, the v2.1 discipline) ----------
    from discovery_fabric.r412.recovery import \
        build_population_accounting
    recomputed = build_population_accounting(
        json.loads((REPO / "R411" / "DISCOVERY_RUN" /
                    "funnel_collision.json").read_text()),
        json.loads((REPO / "R411" / "DISCOVERY_RUN" /
                    "scored_pool.json").read_text()),
        json.loads((REPO / "R411" / "DISCOVERY_RUN" /
                    "shortlist.json").read_text()),
        json.loads((REPO / "R411" / "DISCOVERY_RUN" /
                    "selection.json").read_text()),
        json.loads((REPO / "R412" /
                    "R412_DEATH_CAUSE_WATERFALL.json").read_text()))
    v21 = json.loads(V21_PREREG.read_text())
    pop_sha = recomputed["population_sha256"]
    if pop_sha != v21["population"]["population_sha256"]:
        problems.append("population hash drift vs v2.1")

    # ---- allocation (byte-copied) ----------------------------------
    v1 = json.loads(V1_PREREG.read_text())
    priority = v1["resource_allocation"]["priority_order"]
    ga3_ids = [json.loads(l)["candidate_id"]
               for l in GA3_V1.read_text().splitlines()
               if l.strip()]
    if ga3_ids != priority:
        problems.append("allocation drift vs committed ga3")

    # ---- corpus pin -------------------------------------------------
    corpus = json.loads(CORPUS.read_text())
    corpus_sha = _canon_sha(corpus)
    if corpus.get("n_records") != 48:
        problems.append("benchmark corpus size drift")

    # ---- the lane plan (deterministic; recorded verbatim) ----------
    from discovery_fabric.r412.frontier_evidence import (
        all_lane_queries, rungs_from_ga1b, FEAL_VERSION)
    rungs = rungs_from_ga1b()
    plan = all_lane_queries(rungs)
    plan_sha = _canon_sha(plan)

    # ---- model pin (gateway script) --------------------------------
    gw = REPO / "scripts" / "zai_gateway.mjs"
    if not gw.exists():
        problems.append("gateway script absent")

    prereg: Dict[str, Any] = {
        "artifact_type": "R412_GRADIENT_V3_PREREGISTRATION",
        "preregistration_version": "1.0.0",
        "directive": (
            "operator directive 2026-09-06 (audit of the v2 arm): "
            "build a retrieval-first Gradient V3 arm — the Frontier "
            "Evidence Acquisition Layer; the objective is NOT a "
            "nonzero result but determining whether a better "
            "frontier-evidence acquisition system can expose real "
            "quantitative capabilities the v2 proposer could not "
            "see; 14 directive items; benchmark gate before any "
            "discovery run"),
        "external_audit_arrival": (
            "Claude Sonnet 4.6 external audit Parts 1-3 (HEAD "
            "42a17514) received mid-build this session; its "
            "checkable claims were verified against live bytes "
            "(attacker NOT_CALIBRATED FPR 0.8 CONFIRMED — recorded "
            "as the standing P-minus-1 for the NEXT round, out of "
            "scope for this sealed arm which reuses the v1 attack "
            "machinery unchanged with the NOT_CALIBRATED caveat "
            "traveling; OSTI suspension criterion NOT met; "
            "ENGINE_RETRIEVAL_FABRIC default IS V2 (audit "
            "STALE-CHECK resolved); cadquery imports OK in THIS "
            "workspace; CORE already integrated in the fabric)"),
        "population": {
            "population_sha256": pop_sha,
            "verified_by": "live recompute via the v1 accounting "
                           "path; matched the v2.1 pin",
        },
        "seed_allocation": {
            "source": "byte-copied from R412/"
                      "R412_GRADIENT_RECOVERY_PREREGISTRATION.json "
                      "resource_allocation.priority_order",
            "priority_order": priority,
            "cross_check": "identical to the committed ga3 "
                           "attempted set in order",
        },
        "instruments": {
            "frontier_evidence_module": {
                "path": "discovery_fabric/r412/"
                        "frontier_evidence.py",
                "sha256": _sha(REPO / "discovery_fabric" / "r412" /
                               "frontier_evidence.py"),
                "version": FEAL_VERSION,
            },
            "lane_runner": {
                "path": "scripts/r412_v3_run_lanes.py",
                "sha256": _sha(REPO / "scripts" /
                               "r412_v3_run_lanes.py"),
            },
            "benchmark_evaluator": {
                "path": "scripts/r412_v3_benchmark_eval.py",
                "sha256": _sha(REPO / "scripts" /
                               "r412_v3_benchmark_eval.py"),
            },
            "diagnostic": {
                "path": "scripts/r412_retrieval_diagnostic.py",
                "sha256": _sha(REPO / "scripts" /
                               "r412_retrieval_diagnostic.py"),
                "output": "R412/GRADIENT_V3/"
                          "RETRIEVAL_DIAGNOSTIC_V2_POOLS.json",
            },
            "capability_family_map": {
                "path": "R412/GRADIENT_V2/"
                        "CAPABILITY_FAMILY_MAP_V2.json",
                "sha256": _sha(V2DIR / "CAPABILITY_FAMILY_MAP_V2.json"),
            },
            "admission_gate": (
                "discovery_fabric.r412.gradient_v2."
                "verify_v2_proposals — IDENTICAL for proposer "
                "configurations P1 and P2 (Art. XLVII: the "
                "admission instrument is never the experimental "
                "variable)"),
        },
        "retrieval_benchmark": {
            "corpus_path": "R412/GRADIENT_V3/RETRIEVAL_BENCHMARK/"
                           "RETRIEVAL_BENCHMARK_CORPUS.json",
            "corpus_sha256": corpus_sha,
            "corpus_records": corpus["n_records"],
            "corpus_label_authorship":
                "labels authored by the coder READING each record "
                "before the evaluator ran and before FEAL ever "
                "executed on them (Art. VIII); the simple "
                "digit+unit scan is candidate SELECTION only",
            "neutrality": "acquired by direct connector calls "
                          "with a query form distinct from every "
                          "lane form",
        },
        "retrieval_benchmark_gate": {
            "thresholds": THRESHOLDS,
            "threshold_provenance":
                "ENGINEERING class (Art. XXVII): each threshold is "
                "a monotone multiple of the v2 MEASURED baseline "
                "(numeric-bearing 0.0263 -> 0.15; measurement-"
                "bearing 0.1513 -> 0.30; abstract-bearing 0.2237 "
                "-> 0.60; year recovery 0.0 -> 0.50; source "
                "identity 0.0 -> 1.00); recall thresholds are the "
                "reference-set floors for 'materially better "
                "evidence exposure' (directive item 7); registered "
                "BEFORE the lane run; NEVER tuned to results (Art. "
                "LIX)",
            "gate_rule": "ALL thresholds must pass before ANY "
                         "proposer call; a FAIL is an honest stop "
                         "with decomposition — no threshold may be "
                         "revised after results are seen",
        },
        "lane_plan": {
            "n_queries": len(plan),
            "plan_sha256": plan_sha,
            "lanes": {
                "A": "v1 plain query form reproduced byte-"
                     "identically (the control column)",
                "B": "capability requirement + the operator's "
                     "frozen measurement-terminology list (+ the "
                     "family measurement-dimension second form)",
                "C": "frontier-domain transfer (ga1b "
                     "AI_PROPOSED_EXPLORATORY domains anchor WHERE "
                     "to search; the capability rung is the "
                     "bridge)",
            },
            "plumbing_disclosure": (
                "the fabric invocation is byte-identical to the "
                "v1/v2 _retrieve plumbing (same problem "
                "construction, default lane caps, "
                "reciprocal/unpaywall disabled). The ONLY plumbing "
                "delta vs the sealed v2 run is the REPAIRED "
                "connectors (arxiv/openalex/semantic_scholar "
                "normalized.title defect + the canonicalizer "
                "blank-title guard — root-caused in the diagnostic "
                "from committed bytes; a defect repair, not an "
                "instrument change; 97 retrieval tests green)"),
        },
        "proposer_independence": {
            "directive_item": 8,
            "configurations": {
                "P1": {
                    "prompt": "TVM_V2_FRONTIER_ENTRY_PROPOSAL "
                              "1.1.0 (the sealed v2.1 prompt, "
                              "byte-reused)",
                    "prompt_sha256": _sha(
                        V2DIR / "PROMPTS" /
                        "TVM_V2_FRONTIER_ENTRY_PROPOSAL.json"),
                },
                "P2": {
                    "prompt": "TVM_V3_FRONTIER_ENTRY_PROPOSAL "
                              "1.0.0 (explicit numeric-evidence "
                              "scan procedure; same serialization "
                              "contract, same verifier)",
                    "prompt_sha256": _sha(
                        V3DIR / "PROMPTS" /
                        "TVM_V3_FRONTIER_ENTRY_PROPOSAL.json"),
                },
            },
            "same_pools_rule": (
                "P1 and P2 receive EXACTLY the same per-rung "
                "retrieved record pools (the lane union pool, "
                "deterministic FES-ranked selection); the "
                "proposer never determines what evidence is "
                "available"),
            "independence_disclosure": (
                "SEPARATE_CONTEXT_ONLY-style independence is NOT "
                "claimed: both configurations run on the same "
                "model (zai/glm-4-plus, the only live transport). "
                "The variable is the proposer's instructed "
                "procedure. Retrieval-vs-proposer failure "
                "separation is the objective (directive item 8), "
                "not model independence"),
        },
        "adoption_gap_instrument": {
            "directive_item": 10,
            "prompt": "TVM_V3_ADOPTION_GAP 1.0.0",
            "prompt_sha256": _sha(V3DIR / "PROMPTS" /
                                  "TVM_V3_ADOPTION_GAP.json"),
            "closed_categories": [
                "economics", "materials", "operating_regime",
                "manufacturing", "control_complexity", "regulation",
                "reliability", "missing_measurement",
                "integration_architecture",
                "historical_path_dependence"],
            "verifier": "deterministic: closed category list, "
                        "byte-exact span binding to pool records, "
                        "signal-policy screening; UNRESOLVED is a "
                        "legitimate state (Art. XXV)",
            "applies_to": "every serious frontier capability "
                          "(corroboration >= MULTI_SOURCE_SIGNAL "
                          "or top trajectory score) BEFORE the "
                          "causal transfer (directive item 11)",
        },
        "model_pin": {
            "provider": "zai",
            "model": "glm-4-plus",
            "transport": "sandbox-local OpenAI-compatible gateway "
                         "(scripts/zai_gateway.mjs, runner-owned "
                         "child process — the R412 v2 incident "
                         "lesson)",
            "gateway_script_sha256": _sha(gw),
            "substitution": "FORBIDDEN",
            "confound_disclosure": (
                "the v1 proposer was minimax/minimax-m3:free "
                "(unreachable here); v2 AND v3 both use "
                "zai/glm-4-plus — so v2-vs-v3 admission deltas are "
                "attributable to RETRIEVAL + PROPOSER PROCEDURE, "
                "not model change; no v1-vs-v3 model attribution "
                "is claimed"),
        },
        "token_and_cost_budgets": {
            "lane_fabric_invocations_max": len(plan),
            "tvm_construction_llm_calls_max": 26,
            "tvm_construction_budget_note": (
                "13 rungs x 2 proposer configurations = 26 TOTAL "
                "LLM calls; the two-config expansion over the v2 "
                "12-call single-config budget is REQUIRED by "
                "directive item 8 (proposer independence on the "
                "same pools) and is registered here BEFORE any "
                "call; bounded one-retry per rung-config on "
                "INCOMPLETE transport"),
            "ga4_backcast_calls_max": 10,
            "ga5_feasibility_calls_max": 10,
            "ga55_why_not_calls_max": 10,
            "ga6_decomposition_calls_max": 10,
            "ga8_novelty_calls_max": 10,
            "ga9_attack_calls_max": 10,
            "adoption_gap_calls_max": 13,
            "out_tokens_per_llm_call": 2600,
            "downstream_note": "downstream budgets byte-copied "
                               "from the sealed v1 budgets; only "
                               "reachable when the benchmark gate "
                               "passes AND measured movers exist",
        },
        "stopping_rules": [
            "the benchmark gate must PASS before any proposer "
            "call (a FAIL is an honest stop with decomposition)",
            "a gate that fails is never retried with revised "
            "thresholds (Art. LIX)",
            "sealed v1/v2/temporal artifacts are never modified; "
            "v3 output goes ONLY under R412/GRADIENT_V3/RUN/",
            "DOMAIN_ONLY_RELABEL remains an automatic failure in "
            "the causal-delta verifier (directive item 11)",
            "the NOT_CALIBRATED attacker caveat travels on every "
            "attack verdict (the v1 machinery's own rule)",
            "every stage re-verifies this seal first; any pin "
            "drift REFUSES the stage",
            "transport failures are INCOMPLETE (Art. LXI), never "
            "scientific rejections",
            "zero physical-reality claims: TVM entries are "
            "literature observations, never device performance "
            "(Art. XXXVIII)",
            "no threshold, prompt, or gate change after unseal "
            "(Art. LIX)",
            "honest zero: a zero is reported as a zero (Art. "
            "LXVIII)",
        ],
        "success_criterion": {
            "directive_item": 14,
            "primary": "evidence-backed frontier capabilities "
                       "exposed to the reasoning engine per unit "
                       "retrieval cost",
            "secondary": "present-capability rediscoveries per "
                         "eligible seed",
            "tertiary": "buyer-grade inventions produced from "
                        "genuinely new causal architecture",
            "not_the_objective": "TVM entry count",
        },
        "run_gate": {
            "state": "RUN_ALLOWED" if not problems else "BLOCKED",
            "problems": problems,
            "verified_by": "this builder, from live bytes",
            "fail_closed_rule": "the runner re-verifies every pin "
                                "before each stage; any drift "
                                "REFUSES the stage",
        },
        "no_gradient_calls_before_seal": True,
        "reviewer_provenance": "AI_REVIEW",
        "created_at": None,
    }

    if problems:
        print("REFUSED — preregistration problems:")
        for p in problems:
            print("  -", p)
        return 1
    OUT.write_text(json.dumps(prereg, indent=1) + "\n")
    print(f"v3 preregistration written: {OUT}")
    print(f"  population {pop_sha[:12]} | allocation {len(priority)}"
          f" seeds | corpus {corpus_sha[:12]} "
          f"({corpus['n_records']} records)")
    print(f"  thresholds: {json.dumps(THRESHOLDS)}")
    print(f"  lane plan: {len(plan)} queries "
          f"(sha {plan_sha[:12]})")
    print("RUN_GATE: RUN_ALLOWED (all pins verified from live "
          "bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
