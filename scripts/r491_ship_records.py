#!/usr/bin/env python3
"""R491 — ship the ring-pinned v3 attacker-calibration records inside
the engine tree (the R486 prune-proof pattern; the r487_ship pattern).

THE SHIPMENT: after the ring-pinned measurement exists
(R491/RING_PINNED_MEASUREMENT/MEASUREMENT.json + SEAL.json — the
sealed-bar run on the deployed instrument, on ONE declared provider
ring), this script copies both records into
discovery_fabric/engine/calibration_records/ as byte-identical
duplicates under the registry's bound names for
independent_attack/3.0.0 (r487_attacker_v3_measurement.json /
r487_attacker_v3_seal.json — REPLACING the R488 unpinned-ring
measurement as the instrument's operative record), and re-pins their
sha256 digests in DIGESTS.json.

The registry entry's semantics: an instrument version's calibration
state derives from its LATEST committed measurement. The R488 record
(unpinned ring, FPR 1.0) remains the canonical round-dir record and
the git history — nothing is erased; the operative derivation input
moves to the newest measurement, and the record itself carries the
ring block so the gate can bind the authority to the measured ring.

This script changes NO threshold, NO metric, NO verdict — it makes
the derivation input survive round-dir pruning (the R486 lesson) so
the DEPLOYED gate reads the MEASURED state, whatever it is.

Reviewer provenance: AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "discovery_fabric" / "engine" / "calibration_records"
DIGESTS = DEST / "DIGESTS.json"

NEW_COPIES = {
    "r487_attacker_v3_measurement.json":
        REPO / "R491" / "RING_PINNED_MEASUREMENT" / "MEASUREMENT.json",
    "r487_attacker_v3_seal.json":
        REPO / "R491" / "RING_PINNED_MEASUREMENT" / "SEAL.json",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    import shutil
    DEST.mkdir(parents=True, exist_ok=True)
    pins = json.loads(DIGESTS.read_text())
    for name, src in NEW_COPIES.items():
        if not src.exists():
            print(f"FATAL: {src} does not exist — run the ring-pinned "
                  f"measurement first (scripts/"
                  f"r491_ring_pinned_measurement.py --run)")
            return 2
        shutil.copyfile(src, DEST / name)
        pins["sha256"][name] = _sha(src)
        pins["canonical_sources"][name] = str(
            src.relative_to(REPO)).replace("\\", "/")
        print(f"shipped {name} (sha256 {_sha(src)[:12]}...)")
    pins["artifact_type"] = "R486_CALIBRATION_RECORDS_SHIPMENT"
    pins["r491_extension"] = (
        "the ring-pinned v3.0.0 records REPLACE the R488 unpinned-"
        "ring measurement as the instrument's operative derivation "
        "input (the newest committed measurement is the operative "
        "record; the R488 record remains canonical in R487/"
        "ATTACKER_V3_CALIBRATION + git history); the record carries "
        "the attacker_ring block — the gate binds terminal kill "
        "authority to the measured ring (rules x ring, the R488 "
        "lesson)")
    pins["reviewer_provenance"] = "AI_REVIEW"
    DIGESTS.write_text(json.dumps(pins, indent=1))

    # the gate's own derivation — the authority, stated live
    import sys
    sys.path.insert(0, str(REPO))
    from discovery_fabric.engine import attacker_calibration as gate
    st = gate.resolve_state(
        instrument_version="independent_attack/3.0.0")
    print(f"GATE STATE for independent_attack/3.0.0: {st.get('state')} "
          f"(terminal_kill_admissible="
          f"{st.get('terminal_kill_admissible')}; ring_binding="
          f"{st.get('ring_binding')})")
    if st.get("measured"):
        print(f"measured: {json.dumps(st['measured'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
