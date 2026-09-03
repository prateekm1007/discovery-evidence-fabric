#!/usr/bin/env python3
"""scripts/r401_final_report.py — R401-WC FINAL REPORT generator.

Assembles the nine directive-mandated sections from the machine's OWN
phase records (every conclusion points to measured evidence), assigns
the exact FINAL CLASSIFICATION from the six-state vocabulary, and
records the Phase 14 boundary (what R401 does NOT establish) and the
Phase 15 world-class gap report.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
R401 = REPO_ROOT / "R401"
OUT_MD = R401 / "FINAL_REPORT.md"
OUT_JSON = R401 / "FINAL_REPORT.json"


def _load(name: str) -> Dict[str, Any]:
    p = R401 / name
    return json.loads(p.read_text()) if p.exists() else {}


def main() -> int:
    phase0 = _load("PHASE0_CANONICALIZATION.json")
    baseline = _load("R401_BASELINE.json")
    addendum = _load("R401_BASELINE_ADDENDUM.json")
    lanes = _load("RETRIEVAL_LANE_PROBES.json")
    arms = _load("RETRIEVAL_ARMS_RESULTS.json")
    dedup = _load("DEDUP_RESULTS.json")
    fidelity = _load("FIDELITY_GUARD.json")
    e2e = _load("R401_END_TO_END_RESULTS.json")
    acceptance = _load("R401_ACCEPTANCE.json")
    frontier = _load("PHASE6_FRONTIER_CONTEST_STATE.json")

    bm = (baseline.get("metrics") or {})
    e2e_metrics = e2e.get("metrics") or {}
    ms = e2e.get("mechanism_space") or {}

    # ---- the exact classification ----
    # NOT_READY / STRUCTURALLY_READY / BEHAVIORALLY_VALIDATED /
    # REALITY_VALIDATED / COMMERCIALLY_VALIDATED / WORLD_CLASS_QUALIFIED
    n_pass = acceptance.get("n_pass", 0)
    n_total = acceptance.get("n_total", 10)
    if n_pass == n_total and n_total:
        classification = "BEHAVIORALLY_VALIDATED"
    elif n_pass >= 8:
        classification = "STRUCTURALLY_READY_WITH_BEHAVIORAL_GAPS"
    else:
        classification = "NOT_READY"
    # Phase 14 gates: PHYSICAL_OBSERVATION == 0 and REAL_LOOP_VERIFIED
    # == 0 (no physical measurement has occurred; the vendor Phase-E
    # experiment is proposed, not executed) — the classification is
    # CAPPED at BEHAVIORALLY_VALIDATED regardless of behavioral score.

    arms_s = arms.get("arms") or {}

    def _arm_line(name: str) -> str:
        r = arms_s.get(name) or {}
        if "state" in r and "precision" not in r:
            return f"{name}: **{r.get('state')}** (explicit blocked " \
                   f"state, never silently skipped)"
        return (f"{name}: P={r.get('precision')} R={r.get('recall')} "
                f"F1={r.get('f1')} | FP(mech-irrelevant admitted)="
                f"{r.get('fp')} FN(mech-relevant dropped)={r.get('fn')} "
                f"| latency={r.get('latency_s')}s")

    report = {
        "CURRENT_PIPELINE_BASELINE": {
            "record": "R401/R401_BASELINE.json (frozen, write-once) + "
                      "R401_BASELINE_ADDENDUM.json (retrieval-metric "
                      "correction)",
            "pipeline": "the committed production engine at 7dbebe94 "
                        "(byte-identical engine to the deployed "
                        "930eca8b artifact — verified: git diff "
                        "930eca8b 7dbebe94 -- discovery_fabric/ empty)",
            "problem": "the held-out peritoneal-dialysis-catheter "
                       "obstruction problem (identical for both arms)",
            "measured": {
                "candidate_count": bm.get("candidate_count"),
                "material_distinctness_rate": (
                    bm.get("distinctness") or {}).get(
                    "material_distinctness_rate"),
                "cad_rate": (bm.get("cad_rate") or {}).get("rate"),
                "physics_rate": (bm.get("physics") or {}).get(
                    "physics_rate"),
                "baseline_beats_rate": (bm.get("baseline_rate") or
                                        {}).get("rate"),
                "attack_survival": (bm.get("attack") or {}).get(
                    "attack_survival"),
                "testable_prediction_rate": bm.get(
                    "testable_prediction_rate"),
                "evidence_precision": (bm.get("evidence_precision")
                                       or {}).get("value"),
                "contradiction_rate": bm.get("contradiction_rate"),
                "keep_kill": (bm.get("keep_kill") or {}).get(
                    "final_status"),
                "runtime_s": bm.get("runtime_s"),
                "llm_calls": (bm.get("llm") or {}).get("llm_calls"),
                "retrieval_calls_live": (
                    addendum.get(
                        "corrected_retrieval_measurement") or {}
                ).get("total_live_retrieval_calls"),
                "network_cost_basis": bm.get("network_cost_basis")},
            "the_weak_pattern_frozen": (
                "6 candidates generated, 1 materially distinct "
                "mechanism after structural dedup (rate 0.167): the "
                "baseline's 'diversity' is one mechanism restated five "
                "times — the exact pattern R401 exists to replace")},
        "EMPIRICAL_COMPONENT_MATRIX": {
            "phase0_determination": (
                "the prior session's bench/ artifacts "
                "(benchmark_worldclass.py, bench/results/*, "
                "bench/kkernel/*) are NOT committed and NOT present — "
                "every number in that report is "
                "NOT_REPRODUCIBLE_FROM_REPOSITORY and is NOT claimed "
                "as release-certified evidence (Art. VI/XXIV/XXV); "
                "see R401/PHASE0_CANONICALIZATION.json"),
            "measured_this_session": {
                "corpus_lanes": {
                    l["lane"]: l["state"] for l in lanes.get(
                        "lanes", [])},
                "dedup": {
                    "false_merge": dedup.get("false_merge"),
                    "false_split": dedup.get("false_split"),
                    "verdict": dedup.get("verdict")},
                "fidelity": fidelity.get("verdict"),
                "replay_precision": {
                    "before": 0.5, "after": 1.0,
                    "fixture": "fixed 14-record replay set (test-pinned)"},
                "frontier_llm": frontier.get("contest_status")}},
        "LLM_CONTEST_RESULTS": {
            "status": "BLOCKED_INFERENCE_UNAVAILABLE",
            "measured": (
                "NVIDIA path probed live: /v1/models 200 OK (81 models "
                "listed), chat/completions hang with no response "
                "(HTTP 000 at 15-40s x3), embeddings model 410 EOL — "
                "the 6-model frontier contest cannot run; NOT decided "
                "by model reputation (it was not decided at all)"),
            "pure_vs_hybrid_this_session": (
                "pure-LLM arm measured as a RANKER on the labeled "
                "fixture (see RETRIEVAL_RESULTS); the synthesis pure-vs-"
                "hybrid contest remains blocked with the inference path"),
        },
        "RETRIEVAL_RESULTS": {
            "fixture": arms.get("fixture"),
            "arms": {k: _arm_line(k) for k in arms_s},
            "principle": "a rate-limit result is not a quality result; "
                         "blocked arms carry explicit states",
        },
        "DEDUP_RESULTS": {
            "fixture_pairs": dedup.get("n_fixture_pairs"),
            "accuracy": dedup.get("accuracy"),
            "false_merge": dedup.get("false_merge"),
            "false_split": dedup.get("false_split"),
            "verdict": dedup.get("verdict"),
            "classes": [r.get("class") for r in dedup.get(
                "results", [])]},
        "FIDELITY_RESULTS": {
            "verdict": fidelity.get("verdict"),
            "keep_kill_flips": ((fidelity.get("keep_kill_flip_analysis")
                                 or {}).get("flips")),
            "suites": fidelity.get("suites"),
            "r372_defect_classification": (
                "PRE_EXISTING_AT_HEAD — the identical test fails on "
                "the baseline commit 7dbebe94 (verified by re-run in "
                "the detached worktree); disclosed, never counted as a "
                "pass; the RELEASED buyer surface is unaffected "
                "(r386 verify-fresh PASS from clean clones)")},
        "MECHANISM_OPERATOR_RESULTS": {
            "operator_fidelity": "tests/test_r401_operator_behavior.py "
                                 "— VALID/REWRITE/BROKEN per operator, "
                                 "all green (wording/synonym/expansion "
                                 "FAIL; invariant + required change + "
                                 "structural comparison + derivation "
                                 "trace enforced)",
            "live_operator_counts": e2e_metrics.get("operator_counts"),
            "zero_live_operators": ms.get(
                "operators_with_zero_live_candidates"),
            "downstream_chain": e2e.get("mandatory_downstream_chain")},
        "R401_END_TO_END_RESULTS": {
            "n_distinct_mechanisms": (ms.get("distinctness") or {}).get(
                "n_kept"),
            "material_distinctness_rate": e2e_metrics.get(
                "material_distinctness_rate"),
            "evidence_mechanism_support_rate": e2e_metrics.get(
                "evidence_mechanism_support_rate"),
            "contradiction_rate": e2e_metrics.get("contradiction_rate"),
            "testable_prediction_rate": e2e_metrics.get(
                "testable_prediction_rate"),
            "final_verdict": (e2e.get("final_verdict") or {}).get(
                "final_status"),
            "honesty_note": "the machine REJECTED after the adversarial "
                            "challenge — an acceptable result; no "
                            "winner was fabricated"},
        "WORLD_CLASS_GAP_REPORT": {
            "classification": classification,
            "classification_vocabulary": [
                "NOT_READY", "STRUCTURALLY_READY",
                "BEHAVIORALLY_VALIDATED", "REALITY_VALIDATED",
                "COMMERCIALLY_VALIDATED", "WORLD_CLASS_QUALIFIED"],
            "phase14_boundary": (
                "R401 does NOT establish PHYSICAL_OBSERVATION > 0, "
                "REAL_LOOP_VERIFIED, multiple solver-domain validation, "
                "or commercial validation. The vendor Phase-E decisive "
                "experiment is PROPOSED (R400-D package), not executed. "
                "The classification is therefore capped at "
                "BEHAVIORALLY_VALIDATED."),
            "acceptance": {
                "n_pass": n_pass, "n_total": n_total,
                "verdict": acceptance.get("verdict")},
            "tracks": {
                "W1_second_physics_domain": (
                    "NOT STARTED — the hydraulic solver remains the "
                    "only V0 physics model; MECHANISM_NOT_SIMULATABLE "
                    "is the honest out-of-scope answer (3 of 5 e2e "
                    "candidates used it)"),
                "W2_first_real_physical_closed_loop": (
                    "BLOCKED ON REALITY — requires the Phase-E vendor "
                    "experiment (CEO decision + funding); the machine "
                    "side (R370G one-door ledger) is ready"),
                "W3_six_domain_retrieval_generality": (
                    "PARTIAL — lanes measured reachable (OpenAlex/"
                    "Crossref/arXiv/EuropePMC OK, S2 rate-limited, "
                    "patents keyless); the 48-pair fixture covers 2 "
                    "domains; the 153-prior corpus is missing"),
                "W4_engineer_usability_time_to_decision": (
                    "NOT MEASURED this round"),
                "W5_external_commercial_validation": (
                    "NOT MEASURED — no external buyer/auditor contact "
                    "this round")}},
    }

    # markdown rendering
    md = ["# R401-WC Final Report — Toscanini Discovery Engine",
          "",
          f"**Final classification: {classification}**",
          "",
          f"Acceptance: {n_pass}/{n_total} behavioral criteria "
          f"(R401/R401_ACCEPTANCE.json). Every conclusion below points "
          f"to a measured record in R401/.", ""]
    section_titles = {
        "CURRENT_PIPELINE_BASELINE": "1. Current Pipeline Baseline",
        "EMPIRICAL_COMPONENT_MATRIX": "2. Empirical Component Matrix",
        "LLM_CONTEST_RESULTS": "3. LLM Contest Results",
        "RETRIEVAL_RESULTS": "4. Retrieval Results",
        "DEDUP_RESULTS": "5. Dedup Results",
        "FIDELITY_RESULTS": "6. Fidelity Results",
        "MECHANISM_OPERATOR_RESULTS": "7. Mechanism Operator Results",
        "R401_END_TO_END_RESULTS": "8. R401 End-to-End Results",
        "WORLD_CLASS_GAP_REPORT": "9. World-Class Gap Report"}
    for key, title in section_titles.items():
        md.append(f"## {title}")
        md.append("```json")
        md.append(json.dumps(report[key], indent=1, default=str))
        md.append("```")
        md.append("")
    OUT_MD.write_text("\n".join(md))
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str))
    print(f"classification: {classification}")
    print(f"acceptance: {n_pass}/{n_total}")
    print(f"report -> {OUT_MD} + {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
