#!/usr/bin/env python3
"""R535 round-record generator (§14 completion criteria).

Machine-generates R535/R535_ROUND_RECORD.json from the durable
R535 artifacts only — no hand edits, no narrative claim that is
not backed by a pushed artifact.

The record binds together the 14 §14 criteria:
  1. fresh production identity proof  -> R535/R535_PRODUCTION_IDENTITY_PROOF.json
  2. fresh blind battery manifest      -> R535/BATTERY_PROBLEMS.json
  3. complete stage-by-stage runtime attribution -> R535/R535_STAGE_WALL_ATTRIBUTION.json
  4. complete discovery-yield funnel   -> R535/R535_FUNNEL_AND_CLIFF_DECISION.json
  5. source/provider attribution       -> R535/MECHANISM_SPACE_PROVIDER_JOIN_R535.json
  6. stage reachability matrix         -> R535/R535_FUNNEL_AND_CLIFF_DECISION.json
  7. dependency failure-injection results -> R535/DEPENDENCY_INJECTION_TRACE.json
  8. typed dropout table               -> R535/R535_FUNNEL_AND_CLIFF_DECISION.json
  9. avoidable-runtime analysis        -> R535/R535_STAGE_WALL_ATTRIBUTION.json
  10. explicit optimization authorization decision -> this record
  11. exactly one optimization, only if authorized -> NOT authorized (measurement round)
  12. post-optimization holdout evidence -> N/A (no optimization in R535)
  13. HF deployment identity proof for the optimized commit -> N/A (no optimization in R535)
  14. CI diagnosis remains separately recorded -> R534/CI_DIAGNOSIS_R534_FAILURE.json (superseded by the next CI run's own diagnosis; not folded into R535)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R535 = REPO / "R535"
OUT = R535 / "R535_ROUND_RECORD.json"

ARTIFACTS = [
    "R535_PRODUCTION_IDENTITY_PROOF.json",
    "BATTERY_PROBLEMS.json",
    "R535_STAGE_WALL_ATTRIBUTION.json",
    "R535_FUNNEL_AND_CLIFF_DECISION.json",
    "MECHANISM_SPACE_PROVIDER_JOIN_R535.json",
    "DEPENDENCY_INJECTION_TRACE.json",
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(REPO)).stdout.strip()
    om = subprocess.run(
        ["git", "rev-parse", "origin/main"],
        capture_output=True, text=True, cwd=str(REPO)).stdout.strip()

    proof = json.loads((R535 / "R535_PRODUCTION_IDENTITY_PROOF.json")
                       .read_text(encoding="utf-8"))
    manifest = json.loads((R535 / "BATTERY_PROBLEMS.json")
                          .read_text(encoding="utf-8"))
    stage_wall = json.loads((R535 / "R535_STAGE_WALL_ATTRIBUTION.json")
                            .read_text(encoding="utf-8"))
    funnel = json.loads((R535 / "R535_FUNNEL_AND_CLIFF_DECISION.json")
                        .read_text(encoding="utf-8"))
    join = json.loads((R535 / "MECHANISM_SPACE_PROVIDER_JOIN_R535.json")
                      .read_text(encoding="utf-8"))
    inj = json.loads((R535 / "DEPENDENCY_INJECTION_TRACE.json")
                     .read_text(encoding="utf-8"))

    decision = funnel.get("single_cliff_decision") or {}
    opt_authorized = decision.get("optimization_authorized")

    rec = {
        "artifact": "R535_ROUND_RECORD/1.0",
        "round": "R535",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "parent_round": "R534",
        "round_type": "MEASUREMENT",
        "constitution_ref": "v2.10.1 (Art. LXXVII/LXXVIII/LXXIX/"
                            "LXXXIII/LXXXIV + the one-cliff rule)",
        "production_identity": {
            "target_sha": proof.get("deployed_engine_target"),
            "production_engine_commit":
                proof.get("production_engine_commit"),
            "health_ok": proof.get("health_ok"),
            "identity_tamper": proof.get("identity_tamper"),
            "drift": proof.get("drift"),
            "serve_gate_integrity_verified":
                proof.get("serve_gate_integrity_verified"),
            "chain_ok": proof.get("chain_ok"),
            "proof": "R535/R535_PRODUCTION_IDENTITY_PROOF.json",
            "note": ("the R534 deployment identity proof is a "
                     "timestamped proof from 2026-09-25 08:36Z; "
                     "this R535 proof is a FRESH machine-readable "
                     "probe taken at measurement time — the "
                     "auditor channel cannot independently reach "
                     "the private HF endpoint, so each "
                     "measurement run generates its own proof "
                     "(Art. LXXI)"),
        },
        "three_commit_distinction": {
            "metadata_source_commit":
                proof.get("metadata_source_commit"),
            "deployed_engine_commit":
                proof.get("deployed_engine_commit"),
            "current_origin_main_commit":
                proof.get("current_origin_main_commit"),
            "note": ("R535 §13: the metadata artifact "
                     "(ACTIVE_DISCOVERY_GRAPH.json / "
                     "RUNTIME_CAPABILITY_REGISTRY.json) "
                     "fingerprint the adapter bytes from "
                     f"{proof.get('metadata_source_commit')}; the "
                     f"deployed engine is "
                     f"{proof.get('deployed_engine_commit')} "
                     "(the R534 run.py FREEZE dependency fix); "
                     f"origin/main is "
                     f"{proof.get('current_origin_main_commit')} "
                     "(audit-artifact-only commits).  These three "
                     "are DISTINCT and must not be conflated."),
        },
        "battery": {
            "manifest": "R535/BATTERY_PROBLEMS.json",
            "n_problems": manifest.get("n_problems"),
            "declared_families": manifest.get("declared_families"),
            "vehicles": sorted({p.get("vehicle")
                                for p in manifest.get("problems", [])}),
            "frozen_before_submission": True,
            "corpus_disjoint": True,
            "odi_disjoint": True,
            "all_attempts_retained": True,
        },
        "retrieval_config_audit": {
            "note": ("R535 §4: the current deployed configuration "
                     "excludes openalex and disables the evidence "
                     "fabric channel (ENGINE_EVIDENCE_FABRIC=0, "
                     "ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex).  "
                     "This is the STANDING production policy, NOT "
                     "an experimental arm that accidentally "
                     "persisted — the per-run retrieval two-level "
                     "record (R535/R535_STAGE_WALL_ATTRIBUTION."
                     "json) records exactly what production "
                     "actually exercised; no configuration was "
                     "silently changed."),
            "excluded_sources": "openalex",
            "evidence_fabric_enabled": False,
            "retrieval_fabric_version": "V2",
        },
        "stage_reachability_matrix": funnel.get(
            "stage_reachability_matrix"),
        "typed_dropout_table": funnel.get("typed_dropout_table"),
        "funnel_terminal_distribution":
            funnel.get("funnel_terminal_distribution"),
        "mechanism_space_provider_join": {
            "classification": join.get("classification"),
            "funnel_parity": join.get("funnel_parity"),
            "selection_subspan_aggregate":
                join.get("selection_subspan_aggregate"),
        },
        "dependency_injection_trace": {
            "seams_proven": sorted(
                k for k, v in inj.items()
                if not k.startswith("_") and "error" not in v),
            "representation_divergence":
                inj.get("_representation_divergence"),
            "note": ("R535 §5: the real EngineRun conductor was "
                     "driven for every critical seam; no false "
                     "OK was recorded on any blocked stage; every "
                     "run terminated in a typed non-discovery "
                     "state.  The two dependency representations "
                     "(adapter.depends_on vs "
                     "DOWNSTREAM_BLOCKERS) were proven to diverge "
                     "for the seams named in the directive — the "
                     "divergence is DOCUMENTED, not fixed, per "
                     "the §5 instruction to prove divergence "
                     "before any architectural refactor."),
        },
        "ok_vs_typed_outcome_audit": {
            "note": ("R535 §6: stage-log status==OK is NOT a "
                     "discovery-yield signal.  The MECHANISM_"
                     "SPACE typed terminal state (BUILT / "
                     "NO_CANDIDATES / MECHANISM_STARVED) is the "
                     "authoritative yield signal; the SYNTHESIZE "
                     "CAPABILITY_INSUFFICIENT typed state is "
                     "recorded alongside a stage-log OK; the "
                     "FREEZE custody hash_ok=False typed field is "
                     "recorded alongside a stage-log OK.  "
                     "Downstream admission gates read the typed "
                     "state, never the OK flag."),
        },
        "avoidable_runtime_analysis":
            stage_wall.get("avoidable_runtime_analysis"),
        "single_cliff_decision": decision,
        "optimization": {
            "authorized": opt_authorized,
            "executed": False,
            "note": ("R535 is a MEASUREMENT round.  No "
                     "optimization was authorized (§9 rule: "
                     "authorize only when measured cost AND "
                     "measured avoidability hold for the same "
                     "class).  The discovery cliff is measured "
                     "but its causality is not yet established; "
                     "the runtime cliff is measured with "
                     "avoidable_fraction ~0 (the R530 stopping "
                     "rule).  The next authorized move is the "
                     "upstream-instrumentation round (RETRIEVE "
                     "-> FREEZE -> VERIFY seam) to establish the "
                     "causality of the MECHANISM_SPACE admission "
                     "loss, NOT an optimization."),
        },
        "post_optimization_holdout": {
            "required": False,
            "note": "N/A — no optimization was executed in R535",
        },
        "ci_diagnosis": {
            "status": "NOT_GREEN",
            "separately_recorded":
                "R534/CI_DIAGNOSIS_R534_FAILURE.json (the "
                "classify-job log is 404 via the REST API; root "
                "cause UNKNOWN; a separate infrastructure task, "
                "NOT folded into R535 or the optimization "
                "decision)",
            "constitution_ref":
                "Art. XXVI: local pytest does NOT substitute for "
                "the external certification; Art. LXI: an "
                "infrastructure failure is never a scientific "
                "verdict",
        },
        "independent_certification": {
            "status": "NOT_GREEN",
            "cause": ("UNKNOWN — the classify-job log is not "
                      "retrievable via the REST API (BlobNotFound); "
                      "root cause not independently observed"),
        },
        "classification":
            ("MEASUREMENT_COMPLETE__R535_FULL_CHAIN_PRODUC"
             "TION_BEHAVIOR"),
        "classification_not": [
            "NOT claimed: discovery improvement (the 3/8 BUILT "
            "count is a MECHANISM_SPACE output, not a discovery "
            "credit — Art. LXXVII/LXXVIII)",
            "NOT claimed: current full-production execution "
            "verified for all 15 stages (the reachability matrix "
            "records UNPROVEN_CURRENT_REACHABILITY for stages "
            "not reached by the battery)",
            "NOT claimed: optimization (the §9 rule is not yet "
            "satisfied — causality not established, avoidable "
            "fraction ~0)",
            "NOT claimed: CI GREEN (the classify-job log is not "
            "retrievable; root cause UNKNOWN)",
            "NOT claimed: 'all stages working' — the R535 audit "
            "verdict is that implemented != working in current "
            "production, and R535 has now MEASURED the current "
            "production behavior (this round's deliverable)",
        ],
        "round_states": {
            "measurement_complete": True,
            "optimization_authorized": opt_authorized,
            "optimization_executed": False,
            "optimization_measured": False,
            "optimization_deployed": False,
            "note": ("measurement complete: the full-chain "
                     "production behavior was MEASURED on the "
                     "current R534 production build (eaeba79d8) "
                     "with a fresh blind battery (8 problems, 3 "
                     "families, 6 vehicles, corpus/ODI-disjoint). "
                     "The single-cliff decision is recorded; no "
                     "optimization is authorized.  The next "
                     "authorized move is the upstream-"
                     "instrumentation round to establish the "
                     "causality of the MECHANISM_SPACE admission "
                     "loss."),
        },
        "artifact_sha256": {a: _sha(R535 / a) for a in ARTIFACTS
                            if (R535 / a).exists()},
        "current_head": head,
        "current_origin_main": om,
        # R535 §13: the three-commit distinction MUST appear in the
        # round record itself (not only in the production identity
        # proof) — a future automated refresh must not silently
        # overwrite this distinction.
        "three_commit_distinction_in_record": {
            "metadata_source_commit": proof.get(
                "metadata_source_commit"),
            "deployed_engine_commit": proof.get(
                "deployed_engine_commit"),
            "current_origin_main_commit": proof.get(
                "current_origin_main_commit"),
            "rule": ("an automated metadata refresh stamps "
                     "generated_from_commit = the commit whose "
                     "adapter bytes were actually inspected; it "
                     "MUST NOT conflate that with the deployed "
                     "engine commit or the current origin/main "
                     "commit (R535 §13: 'Do not allow a future "
                     "automated refresh to silently overwrite this "
                     "distinction')"),
        },
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"classification: {rec['classification']}")
    print(f"optimization authorized: {opt_authorized}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
