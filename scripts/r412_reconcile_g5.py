#!/usr/bin/env python3
"""scripts/r412_reconcile_g5.py — R412 Phase 1: G5 canonical-state reconciliation.

THE MEASURED DIVERGENCE (PCEF-2026-08-20-001, re-measured live in R412):

  CV-T06: PORTFOLIO.json frozen_at_version=V22.6 (the R6 benchtop
          protocol-hardening cycle V6->V22.6, artifact work committed at
          2506e9b5) while the ledger's terminal event is a STALE
          re-bootstrap (seq 20, V6, commit dcd8d452) that was appended
          AFTER the evidence-backed chain (V9/V14.1/V15.2/V16.1) by the
          f1f3f97 portfolio consolidation and never superseded.
  CV-T07: PORTFOLIO.json frozen_at_version=V5 (the evidence-backed
          negative-ceiling freeze, ledger seq 13, EVIDENCE_BACKED,
          anchored to CEREVASC_TERRITORY_7_V5_M5_ATTACK/
          V5_FINAL_ADJUDICATION.json) while the ledger's terminal event is
          the STALE re-bootstrap (seq 29, V4, commit dcd8d452).

THE CANONICAL AUTHORITY DETERMINATION (Art. X):

  The append-only state transition ledger IS the canonical authority; the
  PORTFOLIO.json is its projection. Neither side is overwritten: the
  correction is APPENDED through the ledger's own authoritative mechanism
  (record_transition), with each correction transition re-anchoring the
  REAL artifact evidence for the true version. The stale bootstrap events
  stay in the ledger verbatim (Art. XI: history is evidence) — they are
  superseded by sequence position, never rewritten.

CORRECTION EVENTS APPENDED:

  CV-T06: V6 -> V22.6, PHYSICAL_VALIDATION_PENDING, EVIDENCE_BACKED,
          anchored to the R6 V22.6 final-control-hierarchy artifact
          (scripts/r6_final_control_hierarchy.py @ 2506e9b5, sha256
          beeb1d97...).
  CV-T07: V4 -> V5, FROZEN_NEGATIVE_CEILING, EVIDENCE_BACKED,
          re-anchoring the seq-13 artifact (V5_FINAL_ADJUDICATION.json @
          6720fada, sha256 980e2cce...).

Idempotent: appends only if the terminal projection still disagrees.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from epistemic_integrity.state_transition_ledger import (  # noqa: E402
    StateTransitionLedger,
)

LEDGER_DIR = REPO / "epistemic_integrity" / "approved_provenance"
PORTFOLIO = REPO / "CANONICAL_STATE" / "PORTFOLIO.json"

# Resolved (never hand-typed) anchors:
R6_V226_COMMIT = subprocess.run(
    ["git", "rev-parse", "2506e9b5"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout.strip()  # commit that introduced the R6 V22.6 control hierarchy
T07_V5_COMMIT = subprocess.run(
    ["git", "rev-parse", "6720fada"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout.strip()  # commit that anchored the T07 V5 negative ceiling
T07_V5_ARTIFACT_HASH = (
    "980e2cce3d5b7ed6d04bb57a842dfc3edc27c512ab9479a884131d75cc7ad589")
R6_V226_ARTIFACT = "scripts/r6_final_control_hierarchy.py"


def _artifact_hash_at(commit: str, path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=str(REPO), capture_output=True,
    ).stdout
    import hashlib
    return hashlib.sha256(out).hexdigest()


def main() -> int:
    stl = StateTransitionLedger(LEDGER_DIR)
    chain = stl.verify_chain_integrity()
    if not chain["chain_valid"]:
        print("FAIL: ledger chain integrity invalid BEFORE correction:",
              chain["failures"][:3])
        return 1

    portfolio = json.loads(PORTFOLIO.read_text())
    committed = {t["id"]: t for t in portfolio.get("territories", [])}

    def current(tid: str):
        t = stl.get_current_transition(tid)
        return (t.artifact_version, t.to_state) if t else (None, None)

    changes = []

    # ---------------- CV-T06 ----------------
    v, s = current("CV-T06")
    want_v = committed["CV-T06"].get("frozen_at_version")
    want_s = committed["CV-T06"].get("current_state")
    if (v, s) != (want_v, want_s):
        artifact_hash = _artifact_hash_at(R6_V226_COMMIT, R6_V226_ARTIFACT)
        ev = stl.record_transition(
            territory_id="CV-T06",
            to_state=want_s,
            artifact_id="CV-T06-V22.6",
            artifact_version=want_v,
            commit_sha=R6_V226_COMMIT,
            reason=(
                "R412 G5 reconciliation (PCEF-2026-08-20-001): the R6 "
                "benchtop protocol-hardening cycle advanced the frozen "
                "version V6->V22.6 (final control hierarchy committed at "
                f"{R6_V226_COMMIT[:12]}) without ledger appends, and the "
                "consolidation-era re-bootstrap (V6) masked the advance. "
                "Canonical authority is this ledger (Art. X); the "
                "correction is appended, never overwritten. Anchored "
                "artifact: scripts/r6_final_control_hierarchy.py at the "
                f"cited commit (sha256 {artifact_hash[:16]}...)."
            ),
            artifact_hash=artifact_hash,
            transition_type="EVIDENCE_BACKED",
        )
        changes.append(("CV-T06", ev))

    # ---------------- CV-T07 ----------------
    v, s = current("CV-T07")
    want_v = committed["CV-T07"].get("frozen_at_version")
    want_s = committed["CV-T07"].get("current_state")
    if (v, s) != (want_v, want_s):
        ev = stl.record_transition(
            territory_id="CV-T07",
            to_state=want_s,
            artifact_id="CV-T07-V5",
            artifact_version=want_v,
            commit_sha=T07_V5_COMMIT,
            reason=(
                "R412 G5 reconciliation (PCEF-2026-08-20-001): the "
                "evidence-backed V5 negative-ceiling freeze (ST-CV-T07-0002, "
                f"seq 13, anchored to CEREVASC_TERRITORY_7_V5_M5_ATTACK/"
                "V5_FINAL_ADJUDICATION.json) was masked by the stale "
                "consolidation-era re-bootstrap (V4) appended after it. "
                "Canonical authority is this ledger (Art. X); the "
                "correction re-anchors the original V5 artifact evidence "
                "(same commit, same artifact sha256) and supersedes the "
                "stale bootstrap by sequence position — history is "
                "preserved verbatim (Art. XI)."
            ),
            artifact_hash=T07_V5_ARTIFACT_HASH,
            transition_type="EVIDENCE_BACKED",
        )
        changes.append(("CV-T07", ev))

    # ---------------- verify ----------------
    chain = stl.verify_chain_integrity()
    if not chain["chain_valid"]:
        print("FAIL: ledger chain integrity invalid AFTER correction:",
              chain["failures"][:3])
        return 1

    mismatches = []
    by_tid = {}
    for t in stl._events:
        by_tid.setdefault(t.territory_id, []).append(t)
    for tid, evs in sorted(by_tid.items()):
        term = sorted(evs, key=lambda e: e.global_sequence)[-1]
        if term.to_state == "NOT_IN_CERTIFICATION_SCOPE":
            continue
        ct = committed.get(tid)
        if ct is None:
            mismatches.append(f"{tid}: in ledger but not in PORTFOLIO.json")
            continue
        if ct.get("current_state") != term.to_state:
            mismatches.append(
                f"{tid}: state portfolio={ct.get('current_state')} "
                f"ledger={term.to_state}")
        cv = ct.get("frozen_at_version") or ""
        if cv and term.artifact_version and cv != term.artifact_version:
            mismatches.append(
                f"{tid}: version portfolio={cv} "
                f"ledger={term.artifact_version}")

    print(f"corrections appended: {len(changes)}")
    for tid, ev in changes:
        print(f"  {tid}: seq={ev.global_sequence} {ev.transition_id} "
              f"{ev.from_state} -> {ev.to_state} @ {ev.artifact_version} "
              f"(type={ev.transition_type}, artifact_hash="
              f"{(ev.artifact_hash or '')[:16]}...)")
    print(f"post-correction projection mismatches: {len(mismatches)}")
    for m in mismatches:
        print("  MISMATCH:", m)
    print(f"ledger root: {stl.get_root_hash()[:16]}...")
    return 0 if (not mismatches) else 2


if __name__ == "__main__":
    sys.exit(main())
