#!/usr/bin/env python3
"""scripts/r412_fix_correction_event_format.py — repair the reason format
of the two R412 correction transitions (ST-CV-T06-0007, ST-CV-T07-0004).

DEFECT (measured by the clean-clone certification, G10): the R412
correction transitions were appended with reasons that G10's artifact
verifier cannot parse — `_parse_artifact_path_from_reason` requires the
repository's established anchor format
    "EVIDENCE_BACKED — artifact anchored: <path> blob=<sha> hash=<sha> | ..."
while the first correction attempt wrote free-form prose. G10 therefore
reported both transitions as failed artifacts ('could not parse
artifact_path from reason'), turning the certification RED.

REPAIR SEMANTICS (why this is NOT a history rewrite):
  - The transition_hash of every event hashes: global_sequence,
    transition_id, territory_id, from_state, to_state, artifact_id,
    artifact_version, commit_sha, created_at, transition_type,
    previous_transition_hash, artifact_hash, state_hash — the REASON
    field is NOT hash material.
  - The ledger root = the last transition's hash (chain tip).
  => Editing ONLY the reason leaves every hash, every chain link, and
     the root hash BIT-IDENTICAL. The repair is a metadata format fix on
     two events appended EARLIER IN THIS SAME SESSION, disclosed here and
     in the commit message (Art. XI: what can/cannot be proven after the
     edit — the chain proves itself; nothing cryptographic changes).
  - The verifier is NOT weakened: the parser and G10 are untouched; the
    events are brought INTO the established format (Art. VII: fix the
    claim, never the verifier).
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "epistemic_integrity" / "approved_provenance" / \
    "state_transition_ledger.ndjson"
ROOT = REPO / "epistemic_integrity" / "approved_provenance" / \
    "state_transition_ledger_root.json"

# Verified anchors (measured earlier this session):
T06_PATH = "scripts/r6_final_control_hierarchy.py"
T06_BLOB = subprocess_blob = None  # resolved below
T07_PATH = "CEREVASC_TERRITORY_7_V5_M5_ATTACK/V5_FINAL_ADJUDICATION.json"


def _git(*args):
    import subprocess
    return subprocess.run(["git", *args], cwd=str(REPO),
                          capture_output=True, text=True, timeout=30)


def main() -> int:
    events = [json.loads(l) for l in LEDGER.read_text().splitlines()
              if l.strip()]

    # Resolve blob shas the way the historical format records them
    # (12-char blob prefix, resolved via git, never typed).
    t06_commit = "2506e9b5e6c1789d70df734c05263f751cda224e"
    t07_commit = "6720fada69ee11ff0b7d772956ee6d887a96179f"
    t06_blob = _git("rev-parse",
                    f"{t06_commit}:{T06_PATH}").stdout.strip()
    t07_blob = _git("rev-parse",
                    f"{t07_commit}:{T07_PATH}").stdout.strip()
    if not (t06_blob and t07_blob):
        print("FAIL: could not resolve artifact blob shas")
        return 1

    t06_hash12 = events[29]["artifact_hash"][:12]
    t07_hash12 = events[30]["artifact_hash"][:12]

    # --- capture the pre-repair hash chain state (must be unchanged) ---
    pre_root = json.loads(ROOT.read_text())

    new_reasons = {
        "ST-CV-T06-0007": (
            "EVIDENCE_BACKED — artifact anchored: "
            f"{T06_PATH} blob={t06_blob[:12]} hash={t06_hash12} | "
            "R412 G5 reconciliation (PCEF-2026-08-20-001): the R6 benchtop "
            "protocol-hardening cycle advanced the frozen version "
            "V6->V22.6 (final control hierarchy) without ledger appends, "
            "and the consolidation-era re-bootstrap (V6) masked the "
            "advance. Canonical authority is this ledger (Art. X); the "
            "correction is appended, never overwritten. Reason-format "
            "repaired same-session (hash-neutral: reason is not hash "
            "material; the chain and root are bit-identical)."
        ),
        "ST-CV-T07-0004": (
            "EVIDENCE_BACKED — artifact anchored: "
            f"{T07_PATH} blob={t07_blob[:12]} hash={t07_hash12} | "
            "R412 G5 reconciliation (PCEF-2026-08-20-001): the "
            "evidence-backed V5 negative-ceiling freeze (ST-CV-T07-0002, "
            "seq 13) was masked by the stale consolidation-era "
            "re-bootstrap (V4) appended after it. Canonical authority is "
            "this ledger (Art. X); the correction re-anchors the original "
            "V5 artifact evidence (same commit, same artifact sha256) "
            "and supersedes the stale bootstrap by sequence position. "
            "Reason-format repaired same-session (hash-neutral)."
        ),
    }

    changed = 0
    for e in events:
        if e["transition_id"] in new_reasons:
            e["reason"] = new_reasons[e["transition_id"]]
            changed += 1
    if changed != 2:
        print(f"FAIL: expected to repair 2 events, repaired {changed}")
        return 1

    LEDGER.write_text("\n".join(json.dumps(e, default=str)
                                for e in events) + "\n")

    # --- verify the hash chain is UNCHANGED by the repair ---
    sys.path.insert(0, str(REPO))
    from epistemic_integrity.post_scrub_evidence_revalidation import (
        _replay_ledger, verify_single_artifact,
    )
    computed_root, chain_valid, failures = _replay_ledger(events)
    post_root = json.loads(ROOT.read_text())
    if not chain_valid:
        print("FAIL: chain invalid after repair:", failures[:3])
        return 1
    if post_root["ledger_root_hash"] != pre_root["ledger_root_hash"]:
        print("FAIL: root hash changed by the reason repair — abort")
        return 1
    if computed_root != post_root["ledger_root_hash"]:
        print("FAIL: recomputed root != stored root after repair")
        return 1

    # --- verify G10 now resolves both correction events ---
    bad = []
    for e in events:
        av = verify_single_artifact(e)
        ok = av.content_hash_matches or av.error == (
            "artifact_hash is null (scope-excluded or unanchored)")
        if not ok:
            bad.append((e["transition_id"], av.error))
    print(f"repaired reasons: {changed}; root hash UNCHANGED "
          f"({post_root['ledger_root_hash'][:16]}...)")
    print(f"artifact verifications failing after repair: {len(bad)}")
    for tid, err in bad:
        print("  STILL FAILING:", tid, err)
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
