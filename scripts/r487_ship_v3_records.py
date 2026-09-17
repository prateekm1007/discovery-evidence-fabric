#!/usr/bin/env python3
"""R487 — ship the v3 attacker-calibration records inside the engine
tree (the R486 prune-proof pattern, extended to the v3.0.0 instrument).

THE SHIPMENT: after the fresh v3 measurement exists
(R487/ATTACKER_V3_CALIBRATION/MEASUREMENT.json + SEAL.json — the
sealed-bar run on the deployed instrument), this script copies both
records into discovery_fabric/engine/calibration_records/ as
byte-identical duplicates, pins their sha256 digests in DIGESTS.json
(the gate verifies digests at import AND at every read), and records
the canonical sources. The attacker_calibration registry entry for
independent_attack/3.0.0 already points at these shipped names
(r487_attacker_v3_measurement.json / r487_attacker_v3_seal.json) —
until the shipment exists the entry fails closed
(UNKNOWN_NOT_CALIBRATED); after it, resolve_state derives the state
from the record's numbers against the seal.

The canonical round-dir records remain the repository authority
(Art. X). This script changes NO threshold, NO metric, NO verdict —
it makes the derivation input survive round-dir pruning (the R486
lesson) so the DEPLOYED gate reads the MEASURED state, whatever it is.

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
        REPO / "R487" / "ATTACKER_V3_CALIBRATION" / "MEASUREMENT.json",
    "r487_attacker_v3_seal.json":
        REPO / "R487" / "ATTACKER_V3_CALIBRATION" / "SEAL.json",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    import shutil
    DEST.mkdir(parents=True, exist_ok=True)
    pins = json.loads(DIGESTS.read_text())
    for name, src in NEW_COPIES.items():
        if not src.exists():
            print(f"FATAL: {src} does not exist — run the v3 "
                  f"measurement first (scripts/"
                  f"r487_attacker_v3_measurement.py)")
            return 2
        shutil.copyfile(src, DEST / name)
        pins["sha256"][name] = _sha(src)
        pins["canonical_sources"][name] = str(
            src.relative_to(REPO)).replace("\\", "/")
        print(f"shipped {name} (sha256 {_sha(src)[:12]}...)")
    pins["artifact_type"] = "R486_CALIBRATION_RECORDS_SHIPMENT"
    pins["r487_extension"] = (
        "the v3.0.0 records joined the prune-proof shipment after the "
        "fresh sealed-bar measurement; the registry entry for "
        "independent_attack/3.0.0 binds to these names")
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
          f"{st.get('terminal_kill_admissible')})")
    if st.get("measured"):
        print(f"measured: {json.dumps(st['measured'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
