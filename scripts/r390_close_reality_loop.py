#!/usr/bin/env python3
"""R390 — CLOSE THE ACTUAL REALITY LOOP (CEO directive #6).

Two modes:
  --rehearsal : hermetic run — redirected ledgers, fixture observation,
                canonical state untouched (Art. IX). Proves machinery.
  --live      : REAL observation — live NIST WebBook fetch, canonical
                R370G ledger, full causal chain, derived loop state.

The proof the CEO demanded: an observation changes a technical decision
(P-07 drainage floor: measured water viscosity at 310.15 K refutes the
design's declared 'essentially water at 37 C' basis; EQ-1 compensation
changes floor_lumen_diameter_mm; the rebuilt model is re-evaluated).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import reality_loop  # noqa: E402

OUT_ROOT = REPO / "TOSCANINI" / "R390_REALITY_LOOP"
SLOT = "04"                       # P-07 drainage floor (medical demo)
PACKAGE_ID = "P-07"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rehearsal", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if not (args.rehearsal or args.live):
        ap.error("choose --rehearsal or --live")

    if args.live:
        out_dir = OUT_ROOT / "live"
        print("[R390] LIVE acquisition: NIST WebBook water viscosity "
              "at 310.15 K ...")
        observation = reality_loop.acquire_nist_water_viscosity(
            out_dir / "observation", package_id=PACKAGE_ID)
        ledger_path = None            # canonical ledger
        out_root = OUT_ROOT
        mode = "LIVE"
    else:
        out_dir = OUT_ROOT / "rehearsal"
        out_dir.mkdir(parents=True, exist_ok=True)
        ledger = out_dir / "REALITY_EVENT_LEDGER.jsonl"
        observation = reality_loop.acquire_nist_water_viscosity(
            out_dir / "observation", package_id=PACKAGE_ID,
            ledger_path=ledger, rehearsal=True,
            http_get=lambda url: (
                b"Temperature (K)\tPressure (kPa)\tDensity (mol/l)\t"
                b"Volume (l/mol)\tInternal Energy (J/mol)\tEnthalpy "
                b"(J/mol)\tEntropy (J/mol*K)\tCv (J/mol*K)\tCp (J/mol*K)"
                b"\tSound Spd. (m/s)\tJoule-Thomson (K/MPa)\tViscosity "
                b"(uPa*s)\tTherm. Cond. (W/m*K)\tPhase\n"
                b"310.1500\t101.3250\t55.13822\t0.01813624\t2791.940\t"
                b"2793.778\t9.586539\t73.62747\t75.29020\t1523.658\t"
                b"-0.2138357\t691.3036\t0.6244750\tliquid\n"))
        ledger_path = ledger
        out_root = out_dir
        mode = "REHEARSAL"

    print(f"[R390] {mode} observation: eta = "
          f"{observation['value_mPa_s']} mPa*s, ledger_appended="
          f"{observation.get('ledger_appended')}")

    record = reality_loop.close_reality_loop(
        SLOT, observation,
        out_root=out_root,
        ledger_path=ledger_path)

    summary = {
        "mode": mode,
        "status": record.get("status"),
        "closure_id": record.get("closure_id"),
        "observation_event": record.get("observation_event_id"),
        "observation_origin": record.get("observation_origin"),
        "comparison": record.get("comparison"),
        "decision_change_proof": (record.get("re_evaluation") or {}).get(
            "decision_change_proof"),
        "mutation": {k: (record.get("mutation") or {}).get(k) for k in (
            "target_parameter", "from_value", "to_value", "envelope",
            "rebuild_status", "applied_to_canonical_package")},
        "loop_state": record.get("loop_verification_state"),
        "real_loop_derivation": (record.get("causal_chain") or {}).get(
            "real_loop_derivation", {}).get("real_loop_verified"),
        "record_path": str(Path(record.get("record_path", "")) or
                           (out_root / str(record.get("closure_id", "")) /
                            "LOOP_CLOSURE_RECORD.json")),
    }
    (out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2)[:2400])
    return 0 if record.get("status") == "LOOP_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
