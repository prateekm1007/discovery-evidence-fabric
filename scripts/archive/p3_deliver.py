#!/usr/bin/env python3
"""CODER2-P3 driver — CEO Phase 3 directive B7-B12, in order.

  B7  freeze the independent baseline (once; hash-chained to B1)
  B8  decompose every rejection (PRIMARY + SECONDARY blockers)
  B9  blind semantic adjudication (two adjudicators, disagreements kept)
  B10 unseen-problem test (real mode + labeled rehearsal mode)
  B11 human spot-check queues + protocol (PENDING_HUMAN_REVIEW)
  B12 final audit report with the five-way failure taxonomy

Auditor-only: no engine file is modified, no rejected output is
repaired, the benchmark is never weakened, the frozen baselines are
never overwritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import (  # noqa: E402
    blind_adjudication, failure_taxonomy, human_spot_check,
    independent_freeze, rejection_decomposition, unseen_problem_test)


def step(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    # ---- B7 -------------------------------------------------------------
    step("B7 — FREEZE THE INDEPENDENT BASELINE (3/15, 12/15)")
    freeze = independent_freeze.freeze_independent_baseline()
    print(f"action: {freeze['action']}")
    integrity = independent_freeze.verify_independent_baseline()
    print(f"integrity: {integrity['verdict']} | "
          f"content={str(integrity.get('content_sha256'))[:16]}... | "
          f"file-bytes={str(integrity.get('file_sha256_bytes'))[:16]}... | "
          f"chained-to-B1={str(integrity.get('chain_to_b1'))[:16]}...")

    # ---- B8 -------------------------------------------------------------
    step("B8 — DECOMPOSE EVERY REJECTION")
    decomp = rejection_decomposition.decompose_all_rejections()
    print(f"decomposed: {decomp['rejections_decomposed']}/"
          f"{decomp['expected_rejections']}")
    print(f"primary blockers: {decomp['primary_blocker_counts']}")

    # ---- B9 -------------------------------------------------------------
    step("B9 — BLIND SEMANTIC ADJUDICATION")
    adjud = blind_adjudication.run_blind_adjudication()
    print(f"population: {adjud['population']}")
    print(f"sample (seed {adjud['sampling']['seed']}): "
          f"{adjud['sampling']['sampled']}")
    print(f"disagreements preserved: {adjud['disagreement_count']}")
    for axis, s in adjud["agreement_stats"].items():
        print(f"  {axis:36s} agreement {s['agreement_rate']:.0%}")

    # ---- B10 ------------------------------------------------------------
    step("B10 — UNSEEN-PROBLEM TEST (real + labeled rehearsal)")
    unseen = unseen_problem_test.run_unseen_test()
    r = unseen["UNSEEN_PROBLEM_RELEASE"]["real_mode"]
    rh = unseen["UNSEEN_PROBLEM_RELEASE"]["rehearsal_mode_labeled"]
    print(f"distinctness: "
          f"{unseen['distinctness_verification']['verdict']}")
    print(f"REAL mode:      {r['released']}/{r['runs']} released; "
          f"{r['evidence_failure_blocked']} EVIDENCE_FAILURE blocked")
    print(f"REHEARSAL mode: {rh['released']}/{rh['runs']} released")
    print(f"DEPTH failing dims: "
          f"{unseen['UNSEEN_PROBLEM_DEPTH']['failing_depth_dimension_counts']}")
    print(f"CORRECTNESS semantic fails: "
          f"{unseen['UNSEEN_PROBLEM_CORRECTNESS']['semantic_fail_count']}/"
          f"{unseen['UNSEEN_PROBLEM_CORRECTNESS']['released_rehearsal_dossiers']}")

    # ---- B11 ------------------------------------------------------------
    step("B11 — HUMAN SPOT-CHECK QUEUES + PROTOCOL")
    human_spot_check.write_protocol()
    queues = human_spot_check.build_review_queues()
    print(f"committed queue: "
          f"{len(queues['committed_queue']['items'])} items (repo)")
    print(f"blind queue:     {len(queues['blind_queue']['items'])} items "
          f"(custody only)")
    print("status: PENDING_HUMAN_REVIEW")

    # ---- B12 ------------------------------------------------------------
    step("B12 — FINAL AUDIT REPORT (five-way failure taxonomy)")
    report = failure_taxonomy.build_final_audit_report()
    for cat, ids in \
            report["failure_register_b12"]["category_ids"].items():
        print(f"  {cat:34s} {len(ids)}  {ids}")
    print(f"open by owner: "
          f"{report['failure_register_b12']['open_by_owner']}")

    print()
    print("PHASE 3 (B7-B12) COMPLETE — auditor-only; baseline untouched; "
          "benchmark not weakened.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
