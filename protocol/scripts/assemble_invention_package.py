#!/usr/bin/env python3
"""
assemble_invention_package.py — Generic version

Regenerates SHA256SUMS, MANIFEST.json, EVIDENCE_LEDGER.json, REVISED_SCORE.json
for an invention package. This is the canonical assembler; per-invention
overrides (e.g., CereVasc #2 specific fields) live in the invention folder
itself and are read at runtime.

USAGE:
    python3 protocol/scripts/assemble_invention_package.py \
        /path/to/<COMPANY>_INVENTION_<NNN>_V<M>

CONVENTION (chicken-egg rule):
    - SHA256SUMS lists every artifact in the folder EXCEPT itself.
    - 00_MANIFEST.json lists every artifact in its 'artifacts' array
      EXCEPT itself.
    - Both SHA256SUMS and 00_MANIFEST.json ARE included in the other's
      hash computation via this script: the script first walks all files
      (excluding 00_MANIFEST.json and SHA256SUMS), writes 00_MANIFEST.json,
      then computes 00_MANIFEST.json's hash and adds it to SHA256SUMS.

Per INVENTION_PROTOCOL_V1 §6 (mandatory artifacts) and §9.10 (hash integrity).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main(invention_dir: Path) -> int:
    if not invention_dir.is_dir():
        print(f"FATAL: {invention_dir} is not a directory", file=sys.stderr)
        return 2

    os.chdir(invention_dir)

    # ---- 1. Walk artifacts (excluding SHA256SUMS and 00_MANIFEST.json) ----
    artifacts = []
    for root, dirs, files in os.walk(invention_dir):
        for name in sorted(files):
            full = Path(root) / name
            rel = full.relative_to(invention_dir)
            if name == "SHA256SUMS" or rel.name == "00_MANIFEST.json":
                continue
            artifacts.append((str(rel), sha256_of_file(full)))
    artifacts.sort(key=lambda x: x[0])

    # ---- 2. Write 00_MANIFEST.json ----
    # Try to read existing manifest to preserve metadata; if not present, use defaults
    existing_manifest_path = invention_dir / "00_MANIFEST.json"
    existing = {}
    if existing_manifest_path.is_file():
        try:
            with open(existing_manifest_path) as f:
                existing = json.load(f)
        except Exception:
            pass

    manifest = {
        "protocol": "INVENTION_PROTOCOL_V1",
        "invention_id": existing.get("invention_id", invention_dir.name),
        "portfolio_position": existing.get("portfolio_position", "TBD"),
        "buyer": existing.get("buyer", "TBD"),
        "version": existing.get("version", "V1"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": [{"file": rel, "sha256": digest} for rel, digest in artifacts],
        "mandatory_artifact_check": {
            "00_MANIFEST.json": True,
            "08_LIMITATION_FREEZE.json": (invention_dir / "08_LIMITATION_FREEZE.json").is_file(),
            "11_102_ATTACK": (invention_dir / "11_102_ATTACK").is_dir(),
            "12_103_ATTACK": (invention_dir / "12_103_ATTACK").is_dir(),
            "14_DESIGN_AROUND": (invention_dir / "14_DESIGN_AROUND").is_dir(),
            "15_ENGINEERING_BLUEPRINT": (invention_dir / "15_ENGINEERING_BLUEPRINT").is_dir(),
            "16_SIMULATION": (invention_dir / "16_SIMULATION").is_dir(),
            "17_MANUFACTURING": (invention_dir / "17_MANUFACTURING").is_dir(),
            "18_REGULATORY": (invention_dir / "18_REGULATORY").is_dir(),
            "19_BUILD_BUY": (invention_dir / "19_BUILD_BUY").is_dir(),
            "20_BUYER_MEMO": (invention_dir / "20_BUYER_MEMO").is_dir(),
            "21_EVIDENCE_LEDGER.json": (invention_dir / "21_EVIDENCE_LEDGER.json").is_file(),
            "22_FINAL_ADJUDICATION.json": (invention_dir / "22_FINAL_ADJUDICATION.json").is_file(),
            "23_LESSONS_LEARNED.json": (invention_dir / "23_LESSONS_LEARNED.json").is_file(),
            "SHA256SUMS": True,  # will be written below
        },
        "missing_artifacts": [],
        "all_mandatory_artifacts_present": True,
        "_self_hash_note": (
            "00_MANIFEST.json is included in SHA256SUMS but NOT in its own "
            "artifacts array (chicken-and-egg rule, per §6)."
        ),
    }

    # Check for missing mandatory artifacts
    for k, v in manifest["mandatory_artifact_check"].items():
        if not v:
            manifest["missing_artifacts"].append(k)
    manifest["all_mandatory_artifacts_present"] = (len(manifest["missing_artifacts"]) == 0)

    with open(invention_dir / "00_MANIFEST.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # ---- 3. Add 00_MANIFEST.json to artifacts, write SHA256SUMS ----
    manifest_rel = "00_MANIFEST.json"
    manifest_hash = sha256_of_file(invention_dir / "00_MANIFEST.json")
    artifacts.append((manifest_rel, manifest_hash))
    artifacts.sort(key=lambda x: x[0])

    with open(invention_dir / "SHA256SUMS", "w") as f:
        for rel, digest in artifacts:
            f.write(f"{digest}  {rel}\n")

    # ---- 4. Print summary ----
    print("=" * 60)
    print(f"{invention_dir.name} — package assembly complete")
    print("=" * 60)
    print(f"Artifacts: {len(artifacts)}")
    for rel, digest in artifacts[:10]:
        print(f"  {digest[:16]}  {rel}")
    if len(artifacts) > 10:
        print(f"  ... ({len(artifacts) - 10} more)")
    print()
    if manifest["all_mandatory_artifacts_present"]:
        print("All mandatory artifacts present: PASS")
    else:
        print(f"Missing mandatory artifacts: {manifest['missing_artifacts']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 assemble_invention_package.py <invention_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1]).resolve()))
