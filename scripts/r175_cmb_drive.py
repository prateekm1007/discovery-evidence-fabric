#!/usr/bin/env python3
"""r175_cmb_drive.py — the full DIR-2 measurement driver wrapper
(claim c-0276): walks every DEV-12 item through pipeline -> baseline ->
dominance with PER-ITEM typed-error isolation (one item's transport
death never kills the others; byte-resume per item), then abmap ->
judge -> packets -> tally. The wiring smoke (scripts/
r175_cmb_smoke.py, verdict WIRING_OK) must pass BEFORE this runs.

Usage: python3 scripts/r175_cmb_drive.py [--stop-after-dominance]
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r175_cmb_run as R  # noqa: E402

LOG = R.OUT / "drive.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def guarded(name: str, fn, *a):
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001 — typed, never silent
        err = f"{name} TYPED_DRIVER_ERROR {type(e).__name__}: " \
              f"{str(e)[:200]}"
        log(err)
        traceback.print_exc()
        with open(R.OUT / "driver_errors.jsonl", "a",
                  encoding="utf-8") as f:
            f.write(json.dumps({"at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "phase": name, "error": err}) + "\n")
        return None


def main() -> int:
    stop_after_dominance = "--stop-after-dominance" in sys.argv
    t0 = time.monotonic()
    smoke = REPO / "eval" / "r175_cmb_smoke" / "smoke.json"
    if not smoke.exists() or json.loads(
            smoke.read_text(encoding="utf-8")).get("verdict") \
            != "WIRING_OK":
        raise SystemExit("wiring smoke not WIRING_OK — run "
                         "scripts/r175_cmb_smoke.py first (fail closed)")
    log("wiring smoke WIRING_OK — full DEV-12 run begins")

    for prob in R.problems():
        pid = prob["problem_id"]
        pipe = guarded(f"pipeline:{pid}", R.phase_pipeline, prob)
        if pipe is None or pipe.get("state") != "OK":
            log(f"{pid}: pipeline not OK — baseline/dominance skip "
                f"(typed; resumable)")
            continue
        base = guarded(f"baseline:{pid}", R.phase_baseline, prob, pipe)
        if base is None or base.get("state") != "OK":
            log(f"{pid}: baseline not OK — dominance skips (typed)")
            continue
        guarded(f"dominance:{pid}", R.phase_dominance, prob, pipe, base)
        log(f"{pid}: item complete "
            f"({round(time.monotonic()-t0)/60:.1f} min elapsed)")

    if stop_after_dominance:
        log("stop-after-dominance reached")
        return 0

    guarded("abmap", R.phase_abmap)
    guarded("judge", R.phase_judge, None)
    guarded("packets", R.phase_packets)
    log(f"full run wall: {round((time.monotonic()-t0)/60, 1)} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
