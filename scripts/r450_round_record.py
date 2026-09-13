#!/usr/bin/env python3
"""R450 round record generator — the Directional Improvement Engine.

Writes R450/R450_C1_ROUND_RECORD.json with the Article LXXI
production_deployment tuple (filled after the deploy + health verify
by scripts/r447_deploy_verify.py's tuple output).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "R450" / "R450_C1_ROUND_RECORD.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(*args):
    r = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def main() -> int:
    head = _git("rev-parse", "HEAD")
    remote = _git("ls-remote", "origin", "refs/heads/main").split()[0] \
        if _git("ls-remote", "origin", "refs/heads/main") else ""
    bench = json.loads((REPO_ROOT / "R450" / "DIRECTIONAL_BENCHMARK.json")
                       .read_text())
    record = {
        "artifact_type": "R450_C1_ROUND_RECORD",
        "round": "R450",
        "created_at_utc": NOW,
        "reviewer_provenance": "AI_REVIEW",
        "directive": (
            "Build the Directional Improvement Engine: prove that a "
            "failed Toscanini candidate can produce a grounded, testable "
            "direction of improvement, execute a controlled intervention, "
            "evaluate the result, and update the causal model"),
        "constitution": {
            "version": "2.4.0",
            "sha256": ("b54a1be9bcbdd2465d0b034e1e1f472f80b87174209"
                       "c0d534b7d9e1223e649b2"),
            "read_in_full_at_round_start": True,
            "re_read_in_full_before_final_commit": True,
            "governance_files_read": [
                "GOVERNANCE/README.md",
                "GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md",
                "GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md",
                "GOVERNANCE/AUDITOR_REMEMBERED_STATE.md",
                "GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md",
                "ACTIVE_PATH.md",
            ],
            "acknowledgment": (
                "epistemic_integrity/approved_provenance/"
                "CONSTITUTION_ACKNOWLEDGMENT.json bound to v2.4.0 at "
                "b54a1be9 (this session)"),
        },
        "state_at_round_start": {
            "head": "d99e895c589964e4de3e92b994acd69ca9fbc942",
            "origin_main": "d99e895c589964e4de3e92b994acd69ca9fbc942",
            "r449_foundation_commit": "10c7483d (the Evidence Fabric "
                                      "foundation, committed at this "
                                      "round's start)",
        },
        "delivered": {
            "DirectionalHypothesis_canonical_schema": {
                "module": "discovery_fabric/directional/hypothesis.py",
                "fields": ["hypothesis_id", "candidate_id", "failure_id",
                           "causal_diagnosis_id", "target_variable",
                           "current_value", "proposed_value", "direction",
                           "mechanism_affected", "causal_rationale",
                           "predicted_effect",
                           "predicted_magnitude_or_range",
                           "competing_explanations",
                           "evidence_support", "evidence_gaps",
                           "falsifier", "measurement_required",
                           "intervention_type", "confidence",
                           "provenance", "status", "gate"],
                "ground_gate_checks": [
                    "G1_STRUCTURE (closed vocabularies)",
                    "G2_DIAGNOSIS_RESOLVES (recorded diagnosis only)",
                    "G3_MECHANISM_GROUNDED (term overlap with the "
                    "diagnosis/candidate)",
                    "G4_PREDICTION_FALSIFIABLE (measurable falsifier)",
                    "G5_EVIDENCE_HONEST (custody-resolved support or "
                    "declared gaps)"],
            },
            "canonical_state_integration": (
                "run.py::_evolution_generate_next — the directional step "
                "rides the ONE evolution pipeline (no second engine, no "
                "second invention graph; DIRECTIONAL_HYPOTHESES.json + "
                "IMPROVEMENT_TRAJECTORY.json are append-only records "
                "referencing canonical generation records)"),
            "loop_state_transitions": (
                "EVIDENCE -> MECHANISM -> CANDIDATE -> ATTACK -> FAILURE "
                "-> CAUSAL DIAGNOSIS -> DIRECTIONAL HYPOTHESIS (gate) -> "
                "CONTROLLED MUTATION -> EVALUATION (the same gauntlet) "
                "-> OBSERVATION -> CAUSAL UPDATE -> NEXT DIRECTION"),
            "grounded_vs_ungrounded_handling": (
                "the ground gate REJECTS ungrounded directions; the "
                "mutation never executes; the rejection is recorded; the "
                "stop reason is DIRECTION_REJECTED_BY_GROUND_GATE "
                "(distinct from transport failures — Art. LXI)"),
            "intervention_classes": [
                "PARAMETER_MUTATION", "TOPOLOGY_MUTATION",
                "MATERIAL_MUTATION", "OPERATING_CONDITION_MUTATION",
                "MECHANISM_COMBINATION", "EVIDENCE_UPDATE",
                "CONSTRAINT_RELAXATION", "CONSTRAINT_TIGHTENING"],
            "improvement_signals": (
                "observation.py — objective_delta / constraint_delta / "
                "distance_to_target / information_gain / sensitivity "
                "UNDER the epistemic gates; NO fabricated gradients "
                "(sensitivity only from real recorded evaluation pairs)"),
            "attacker_v2_upgrade": (
                "independent_attack/2.1.0 — INTERVENTION suggestion lines "
                "with the SAME grounding discipline (GROUNDED_INTERVENTION "
                "= directional-loop SEED, still gate-bound; UNGROUND_"
                "SUGGESTION never enters the hypothesis space); the "
                "calibration state carries forward NOT_CALIBRATED "
                "(inherited binding, negative knowledge preserved, "
                "discipline NOT weakened)"),
            "obvious_combination_protection": (
                "novelty.py gains NOVEL_BEHAVIOR — known A + known B -> "
                "evidenced interaction C -> mechanism prediction -> "
                "RECORDED reproduction by evaluation; "
                "novelty-by-description never upgrades without the "
                "recorded reproduction"),
            "improvement_trajectory_persistence": (
                "IMPROVEMENT_TRAJECTORY.json per run (append-only; "
                "V1 -> F1 -> D1 -> M1 -> R1 -> C1 -> V2 chain with "
                "provenance at every transition)"),
            "evidence_to_direction_linkage": (
                "the reverse path: DIRECTION -> declared gaps -> gap "
                "queries (deterministic) -> R449 evidence-fabric "
                "retrieval -> newly acquired support recorded ON the "
                "hypothesis (evidence_changed_direction)"),
            "fresh_directional_benchmark": {
                "artifact": "R450/DIRECTIONAL_BENCHMARK.json",
                "problems": [p["problem_id"] for p in
                             bench["problems"]],
                "arms": "DIRECTIONAL vs UNGUIDED (same engine, same "
                        "transport, same gauntlet, same budget)",
                "raw_metrics_only": True,
            },
            "tests": {
                "tests/test_r450_directional.py": "35 passed",
                "tests/test_r449_evidence_fabric.py": "41 passed",
                "regressions": "r419 english-only + r447 owner transport "
                               "25 passed; r446 cio/completion 49 "
                               "passed; r445 canonical domain passed "
                               "(in the combined run); r443 visual "
                               "integrity 6 failures BASELINE-IDENTICAL "
                               "on git-stash (the known sandbox Chromium "
                               "memory-contention class; no visual code "
                               "touched this round — disclosed)",
            },
        },
        "headline_result": bench["findings"]["headline_answer"],
        "honest_limitations": bench["findings"]["honest_limitations"],
        "known_unknowns": [
            "the benchmark is N=2 problems x 1 iteration per arm — a "
            "first live demonstration, NOT a statistically powered "
            "comparison",
            "the R449 two-arm evidence-power experiment measured "
            "mechanism_search_changed=true but "
            "evidence_fabric_sourced_mechanisms_present=false (the "
            "fabric's records entered the pool and did not win the "
            "synthesis rotation) — recorded honestly in "
            "R449/FRESH_EVIDENCE_POWERED_DISCOVERY.json",
            "the unguided arm's P1 survivor carries no falsifier and no "
            "causal contract — its 'success' is not re-testable; the "
            "benchmark records the difference in what each system KNOWS",
            "uspto_patents + s2orc remain PENDING_LICENSE_VERIFICATION "
            "(no license declaration on their cards — fail-closed, "
            "never production evidence until verified); "
            "openalex_mirror + cadgenbench remain PENDING_INDEX",
        ],
        "next_decisive_test": (
            "scale the benchmark (more problems, multi-iteration "
            "budgets) and connect the attacker's GROUNDED_INTERVENTION "
            "suggestions into the hypothesis proposal prompt as seeds "
            "(still gate-bound); the production fresh-run proof is in "
            "this round's delivery tuple below"),
        "production_deployment": {
            "target_sha": head,
            "deployed_sha": None,
            "deploy_id": None,
            "health_check_result": None,
            "drift": None,
            "blocked_by": None,
            "what_unblocks": None,
            "note": ("filled by the Article LXXI verification after the "
                     "canonical-Space deploy at the pushed SHA; a NULL "
                     "deployed_sha means DELIVERY_BLOCKED at record "
                     "time — the record is finalized after verification"),
        },
        "remote_main_at_record": remote,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False,
                              default=str))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
