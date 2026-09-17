"""R486 — ship the attacker-calibration records inside the engine tree.

MEASURED DEFECT (R484/R485 closure runs, the auditor's sharpest open
question): the R417 escalation gate (attacker_calibration/1.1.0) derives
its state from committed measurement records stored under round dirs
(R412/CALIBRATION/, R447/ATTACKER_V2_RECALIBRATION/). The production
Space image prunes round dirs for size (R485 deploy removed 64 round
dirs, R447 among them). At runtime in the deployed container the
v2.1.0 registry path did not exist, so resolve_state() failed closed to
UNKNOWN_NOT_CALIBRATED with reason "no committed measurement" — while
the repository in fact holds a committed measurement saying
NOT_CALIBRATED (measured FPR 1.0 vs sealed bar 0.3). The fail-closed
DIRECTION was correct both times; the recorded REASON was degraded by
infrastructure (Art. LXI class: an infrastructure state entered the
record as if it were an epistemic one).

THE FIX (this script): copy the four calibration files (measurement +
seal for v1.0.0 and v2.0.0/2.1.0) into
discovery_fabric/engine/calibration_records/ — inside the code tree,
which every deploy ships (round-dir pruning cannot touch it) — and pin
their sha256 digests in DIGESTS.json. The gate module then binds the
registry to the in-tree copies and verifies the pinned digests before
reading them; a digest mismatch fails closed. The canonical round-dir
records remain exactly where they are (Art. X: they stay the repository
authority); the in-tree copies are byte-identical shipment duplicates
whose digests prove identity. This changes NO threshold, NO metric, NO
verdict — the derived state (NOT_CALIBRATED, FPR 1.0) is identical; the
recorded reason becomes the true measured one.

Reviewer provenance: AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "discovery_fabric" / "engine" / "calibration_records"

COPIES = {
    "r412_engine_independent_attack_measurement.json":
        REPO / "R412" / "CALIBRATION" / "engine_independent_attack_measurement.json",
    "r412_calibration_seal.json":
        REPO / "R412" / "CALIBRATION" / "r412_calibration_seal.json",
    "r447_attacker_v2_measurement.json":
        REPO / "R447" / "ATTACKER_V2_RECALIBRATION" / "MEASUREMENT.json",
    "r447_attacker_v2_seal.json":
        REPO / "R447" / "ATTACKER_V2_RECALIBRATION" / "SEAL.json",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    for name, src in COPIES.items():
        if not src.exists():
            raise SystemExit(f"FATAL: canonical record missing: {src}")
        dst = DEST / name
        shutil.copyfile(src, dst)
        d = _sha(dst)
        if d != _sha(src):
            raise SystemExit(f"FATAL: copy not byte-identical: {name}")
        digests[name] = d
        print(f"OK {name} sha256={d[:16]}…")
    manifest = DEST / "DIGESTS.json"
    payload = {
        "artifact_type": "R486_CALIBRATION_RECORDS_SHIPMENT",
        "purpose": ("prune-proof in-tree shipment duplicates of the "
                    "committed calibration measurements + seals; the "
                    "gate verifies these digests before reading; the "
                    "canonical round-dir records remain the repository "
                    "authority (Art. X); digests make the duplicates "
                    "tamper-evident, not authoritative-by-copy"),
        "canonical_sources": {
            name: str(src.relative_to(REPO)) for name, src in COPIES.items()
        },
        "sha256": digests,
        "reviewer_provenance": "AI_REVIEW",
    }
    manifest.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"OK DIGESTS.json ({len(digests)} pinned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
