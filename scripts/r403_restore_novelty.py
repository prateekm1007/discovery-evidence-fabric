#!/usr/bin/env python3
"""R403 — restore the Patent-Bear / PatSnap novelty-search artifacts for the
LEAD PORTFOLIO 4 hardening from the immutable archive branch.

Source of truth: git branch `origin/archive/rounds-R309-R383` (tip c7f7d692,
the pre-R388 tree). The files were deleted from main at R388 (8cb6ff3b,
2026-09-01, "distill the active tree") — no history rewrite occurred, so the
blobs are byte-recoverable. This script copies them OUT of git history into
NOVELTY_EVIDENCE/restored/ and records per-file provenance:

  - source branch + source commit + source blob sha (git's own identity)
  - sha256 of the source blob (computed from `git show`)
  - sha256 of the restored copy (must equal the source-blob sha256)

Art. XI (history is evidence) + Art. VI (never manufacture provenance):
restoration-from-history with hash custody, not fabrication. The archive
branch itself is never modified.

Run from the engine repo root: python3 scripts/r403_restore_novelty.py
"""
import hashlib
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE_REF = "origin/archive/rounds-R309-R383"
OUT_DIR = REPO / "NOVELTY_EVIDENCE" / "restored"
PROVENANCE_PATH = REPO / "NOVELTY_EVIDENCE" / "RESTORATION_PROVENANCE.json"

# The minimal sufficient evidence set for the four lead packages' novelty
# records + the PatSnap attempted-never-executed record + the P-28 (P14)
# never-searched record. Original relative paths preserved.
FILES = [
    # R359 — real PatentBear broad searches (15-package roster, 2026-08-26)
    "R359/patentbear_full/P-07_patentbear.json",
    "R359/patentbear_full/P-16_patentbear.json",
    "R359/patentbear_full/P-24_patentbear.json",
    "R359/patentbear_full/ALL_PATENTBEAR_RESULTS.json",
    # R359 — per-package §102/§103/FTO evidence graphs (NOT-a-legal-opinion stamped)
    "R359/canonical_evidence_v2/P-07/evidence_graph_v2.json",
    "R359/canonical_evidence_v2/P-16/evidence_graph_v2.json",
    "R359/canonical_evidence_v2/P-24/evidence_graph_v2.json",
    # R361 — specific-mechanism queries + novelty verdicts (the precise queries)
    "R361/full_portfolio_assessment/FULL_PORTFOLIO_PATENT_ASSESSMENT.json",
    # R365 — passage-level claim analysis (P-16 closest-art element mapping)
    "R365/passage_analysis/PASSAGE_LEVEL_ANALYSIS.json",
    # R368 — final acceptance gate + the P-28/P-29 "earned" record
    "R368/audit/ROUND_368_AUDIT.json",
    "R368/p28_p29_earned/P28_P29_EARNED.json",
    # R354 — the documented PatSnap ATTEMPT that never executed (balance exhausted)
    "R354/patsnap_pipeline/PATSNAP_API_STATUS.json",
    "R354/patsnap_pipeline/patsnap_search.py",
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def blob_bytes(ref: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), "show", f"{ref}:{path}"],
        check=True, capture_output=True,
    ).stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    # Verify the archive ref exists and record its tip commit.
    ref_hash = git("rev-parse", ARCHIVE_REF)
    tip_commit = git("rev-parse", f"{ARCHIVE_REF}^{{commit}}")
    print(f"archive ref {ARCHIVE_REF} -> {ref_hash[:12]} (commit {tip_commit[:12]})")

    records = []
    failures = []
    for rel in FILES:
        try:
            raw = blob_bytes(ARCHIVE_REF, rel)
        except subprocess.CalledProcessError:
            failures.append(rel)
            continue
        blob_sha = git("rev-parse", f"{ARCHIVE_REF}:{rel}")
        dst = OUT_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)
        restored_sha = sha256(dst.read_bytes())
        source_sha = sha256(raw)
        if restored_sha != source_sha:
            failures.append(f"{rel} (hash mismatch after copy)")
            continue
        records.append({
            "path": rel,
            "restored_to": f"NOVELTY_EVIDENCE/restored/{rel}",
            "source_branch": "archive/rounds-R309-R383",
            "source_commit": tip_commit,
            "source_blob_sha1": blob_sha,
            "sha256": source_sha,
            "bytes": len(raw),
        })
        print(f"  restored {rel} ({len(raw)} B, sha256 {source_sha[:16]}...)")

    if failures:
        print("FAILURES:", failures)
        return 1

    provenance = {
        "artifact_type": "NOVELTY_EVIDENCE_RESTORATION_PROVENANCE",
        "purpose": (
            "Custody record for the Patent-Bear / PatSnap novelty-search "
            "artifacts restored from git history for the LEAD PORTFOLIO 4 "
            "hardening (CEO R403 directive, sections 5-8). The originals "
            "were deleted from main at R388 (commit 8cb6ff3b, 2026-09-01, "
            "tree distillation) and are recoverable byte-identically from "
            "the archive branch. No history was rewritten (Art. XI); these "
            "copies cite their source blobs (Art. XII); nothing here is "
            "manufactured (Art. VI)."
        ),
        "source_branch": "archive/rounds-R309-R383",
        "source_branch_tip_commit": tip_commit,
        "deleted_from_main_at": {
            "commit": "8cb6ff3b",
            "date": "2026-09-01",
            "round": "R388",
        },
        "restoration_session": "R403 (2026-09-04)",
        "verification_rule": (
            "sha256(restored file) == sha256(source blob). The cross-artifact "
            "consistency test (tests/test_r403_lead_portfolio_integrity.py) "
            "recomputes every sha256 against this manifest; any drift fails."
        ),
        "files": records,
        "honest_scope": (
            "These are SEARCH ACTIVITY records, not novelty determinations "
            "(Constitution Art. XXI/XXVIII): a PatentBear hit count is not a "
            "legal opinion; the evidence graphs carry their own NOT-a-legal-"
            "opinion stamps; PatSnap rows record ATTEMPTED searches that "
            "never executed (balance exhausted / key rejected)."
        ),
    }
    PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROVENANCE_PATH.write_text(json.dumps(provenance, indent=1) + "\n")
    print(f"\nprovenance manifest: {PROVENANCE_PATH}")
    print(f"restored {len(records)} artifacts, 0 failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
