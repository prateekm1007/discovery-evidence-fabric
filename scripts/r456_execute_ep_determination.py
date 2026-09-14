#!/usr/bin/env python3
"""R456 — execute the §N.1 epistemic_integrity determination (Art. LXIV.3
step 1: move-to-archive, history preserved by git mv; the round record
carries the deletion accounting). The determination itself is produced by
scripts/r456_module_inventory.py --determination (consumer-evidenced).

Operator authorization: this round's directive lists 'the
epistemic_integrity/ determination (§N.1)' explicitly.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DET = REPO / "R456" / "EPISTEMIC_INTEGRITY_DETERMINATION.json"
DEST = REPO / "archive" / "r456-lean" / "epistemic_integrity"

# data/orphaned-output moves (owners archived; no kept-module readers —
# verified by the consumer scan in the determination instrument)
EXTRA_MOVES = [
    ("epistemic_integrity/invention_loop_engine/live_replay",
     "archive/r456-lean/epistemic_integrity/invention_loop_engine/live_replay"),
    ("epistemic_integrity/commit_provenance_report.json",
     "archive/r456-lean/epistemic_integrity/commit_provenance_report.json"),
    ("epistemic_integrity/hash_verification_report.json",
     "archive/r456-lean/epistemic_integrity/hash_verification_report.json"),
    ("epistemic_integrity/production_claims_summary.json",
     "archive/r456-lean/epistemic_integrity/production_claims_summary.json"),
]

REASONS = {
    "epistemic_integrity.invention_loop_engine": (
        "the R339-R370 reality-loop instrument family; bayesian_eig is "
        "the ONLY production member (KILLER_EXPERIMENT adapter, "
        "path-loaded) — the other 22 modules have no importer in "
        "production, CI, tests, or scripts (audit §B.1 row 63 / §C.9)"),
    "epistemic_integrity.populate_ledger": (
        "pre-R396 scrub machinery; zero importers"),
    "epistemic_integrity.populate_production_claims": (
        "pre-R396 populate machinery; zero importers"),
    "epistemic_integrity.state_reconciliation": (
        "pre-R396 state reconciliation; the gate's G4 uses "
        "state_transition_ledger (KEPT), not this module"),
    "epistemic_integrity.hash_verifier": (
        "pre-R396 hash audit; zero importers; report archived with it"),
    "epistemic_integrity.commit_provenance_verifier": (
        "pre-R396 provenance audit; zero importers"),
    "epistemic_integrity.append_only_binding_registry": (
        "pre-R396 binding registry; zero importers"),
    "epistemic_integrity.patent_coverage_contract": (
        "pre-R396 coverage contract; zero importers"),
    "epistemic_integrity.independent_certification_corpus": (
        "corpus generator; the JSON data file STAYS (historical_artifact_"
        "audit reads it) — only the module archives"),
    "epistemic_integrity.real_production_certification_corpus": (
        "corpus generator; the JSON data file STAYS (the gate, "
        "attestation_binding, the capsule, historical_artifact_audit all "
        "read it) — only the module archives"),
}


def _git_mv(src: str, dst: str) -> bool:
    if not (REPO / src).exists():
        return False
    (REPO / dst).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "mv", src, dst], cwd=str(REPO),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  git mv FAILED {src}: {r.stderr.strip()}")
        return False
    return True


def main() -> int:
    det = json.loads(DET.read_text())
    archive = det["archive_candidates"]
    manifest_path = REPO / "archive" / "r456-lean" / "MANIFEST.json"

    entries = []
    moved, missed = [], []
    for mod in archive:
        rel = mod.replace(".", "/") + ".py"
        dst = f"archive/r456-lean/{rel}"
        if _git_mv(rel, dst):
            moved.append(mod)
            entries.append({
                "module": mod,
                "original_path": rel,
                "disposition": "ARCHIVED_TO archive/r456-lean/" + rel,
                "reason": REASONS.get(mod, (
                    "superseded/pre-R396 machinery; zero importers in "
                    "production, CI, tests, or scripts (consumer "
                    "evidence in R456/EPISTEMIC_INTEGRITY_DETERMINATION"
                    ".json)")),
            })
        else:
            # package __init__ handling: module name maps to pkg/__init__
            rel2 = mod.replace(".", "/") + "/__init__.py"
            dst2 = f"archive/r456-lean/{rel2}"
            if _git_mv(rel2, dst2):
                moved.append(mod)
                entries.append({
                    "module": mod,
                    "original_path": rel2,
                    "disposition": "ARCHIVED_TO archive/r456-lean/" + rel2,
                    "reason": REASONS.get(mod, (
                        "package __init__ of an archived family; every "
                        "member with an importer was kept")),
                })
            else:
                missed.append(mod)

    for src, dst in EXTRA_MOVES:
        if _git_mv(src, dst):
            entries.append({
                "module": "(data)",
                "original_path": src,
                "disposition": f"ARCHIVED_TO {dst}",
                "reason": "data/output of archived modules; no kept-module "
                          "reader (consumer-verified)",
            })

    # merge with any existing manifest (r456-lean already exists from R455)
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        if isinstance(existing, dict) and "entries" in existing:
            existing["entries"].extend(entries)
            existing["rounds"] = sorted(set(
                existing.get("rounds", []) + ["R456"]))
            manifest = existing
        else:
            manifest = {"rounds": ["R455", "R456"], "entries": entries}
    else:
        manifest = {"rounds": ["R456"], "entries": entries}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"archived {len(moved)} modules + {len(EXTRA_MOVES)} data moves; "
          f"missed={missed}")
    # prune now-empty dirs (git doesn't track dirs)
    for d in sorted((REPO / "epistemic_integrity").rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    if missed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
