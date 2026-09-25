#!/usr/bin/env python3
"""R533 audit §7: R532 deploy-record round-identity correction.

Art. XI: the original R532 deploy record (with round=R526) is
PRESERVED byte-for-byte — its SHA is recorded here. The correction
record does NOT silently overwrite it.

This machine-generated correction:
  - records the metadata defect (round field said R526);
  - states exactly which evidence remains valid (engine diff,
    build identity, deployment tuple, engine_commit, etc.);
  - generates the corrected R532 deployment tuple from the
    original record's authoritative bytes;
  - references itself as the correction of record.

The deploy generator (scripts/r526_deploy_arm.py) has been
round-parameterized (--round required) so the next round cannot
inherit R526 identity.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R532 = REPO / "R532"
OUT = R532 / "R532_DEPLOY_RECORD_CORRECTION.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    orig_path = R532 / "R532_DEPLOY_RECORD.json"
    orig = json.loads(orig_path.read_text(encoding="utf-8"))
    orig_sha = _sha(orig_path)

    defect_fields = []
    for k, v in orig.items():
        if k == "round" and v != "R532":
            defect_fields.append({"field": k, "recorded": v, "correct": "R532"})

    valid_evidence = [
        "engine_diff_guard (discovery_fabric/engine/adapters.py only)",
        "commit = 62c560989556b126d00c7156bc199852ca1664e2",
        "counterpart_commit = 96e2d03652d330156da7e0818bc386447c2ad8df",
        "hf_revision",
        "arm_identity_proof",
        "variable_readback",
        "standing_configuration",
        "constitution_served",
        "image_slimming",
        "secrets_fingerprints",
        "intervention (R532 §3 typed-outcome instrumentation)",
        "all engine-bytes evidence (staged tree, marker, no scattered branch)",
    ]

    corrected = {k: v for k, v in orig.items() if k != "round"}
    corrected["round"] = "R532"
    corrected["correction_of"] = orig_sha
    corrected["correction_note"] = (
        "round field corrected from 'R526' to 'R532'. "
        "All other fields are byte-identical to the original record. "
        "The original record is preserved at R532/R532_DEPLOY_RECORD.json "
        "(SHA256 recorded in this correction).")

    rec = {
        "artifact": "R532_DEPLOY_RECORD_CORRECTION/1.0",
        "round": "R532",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "correction_of_original_record": "R532/R532_DEPLOY_RECORD.json",
        "correction_of_original_sha256": orig_sha,
        "defect": {
            "type": "ROUND_IDENTITY",
            "cause": ("R532 deploy reused scripts/r526_deploy_arm.py "
                      "which hardcoded round='R526' in the record; "
                      "the driving round was R532"),
            "fields": defect_fields,
        },
        "valid_evidence": valid_evidence,
        "corrected_round": "R532",
        "corrected_record": corrected,
        "deploy_generator_repaired": {
            "file": "scripts/r526_deploy_arm.py",
            "change": "--round required arg added; record's round field "
                      "now uses args.round instead of hardcoded R526",
            "next_round_cannot_inherit_r526_identity": True,
        },
        "constitution_ref": "Art. XI: original record preserved "
                             "byte-for-byte, not silently overwritten",
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} (corrects {orig_sha[:12]})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(main())
