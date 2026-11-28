#!/usr/bin/env python3
"""r130s2_bon_parity_run.py — the BoN round-2 PARITY replication (claim
c-0208; the prereg eval/r130s2_bon2_parity_prereg.json governs).

The arm is BYTE-IDENTICAL to round 1: this runner DELEGATES to the
committed round-1 module (scripts/r129_bon_run.py — the same
one_problem legs, the same transport policy, the same frozen bytes)
and writes replication-2 records to eval/r130s2_bon_parity_run/
rep2_{pid}.json (byte-resume: existing records are never re-run).
The only additions to each record are the replication tag and the
work id — the legs themselves are untouched (variable isolation).

Zero engine lines: scripts/ + eval/ only (Art. 27 disclosure).

Usage: python3 scripts/r130s2_bon_parity_run.py
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r130s2_bon_parity_run"
OUT.mkdir(parents=True, exist_ok=True)

from r129_bon_run import items, one_problem, quota_probe  # noqa: E402

PRINT_LOCK = threading.Lock()
WORKERS = 2  # byte-identical transport to round 1


def main() -> int:
    print("BON2-BINDSELECT ROUND-2 PARITY REPLICATION: 24 items x 2 "
          f"candidates, {WORKERS} workers (the prereg governs; arm "
          "legs byte-identical to round 1 via r129_bon_run "
          "delegation)", flush=True)
    if not quota_probe():
        (OUT.parent / "r130s2_bon_INFRA_QUOTA_WALL").write_text(
            "the quota probe failed at run start\n", encoding="utf-8")
        print("REFUSED (typed INFRA_QUOTA_WALL)", flush=True)
        return 3
    probs = items()
    todo = [p for p in probs
            if not (OUT / f"rep2_{p['problem_id']}.json").exists()]
    print(f"byte-resume: {len(probs) - len(todo)} already done, "
          f"{len(todo)} to go", flush=True)
    t0 = time.monotonic()
    done = 0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(one_problem, p): p["problem_id"]
                for p in todo}
        for fut in cf.as_completed(futs):
            rec = fut.result()
            rec["replication"] = 2
            rec["work_id"] = "r130s2-bon2-parity"
            (OUT / f"rep2_{rec['problem_id']}.json").write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            with PRINT_LOCK:
                print(f"  [{done}/{len(todo)}] {rec['problem_id']}: "
                      f"{rec['status']} sel={rec['selected_candidate']} "
                      f"scores={rec['selection_scores']} "
                      f"wall={rec['wall_clock_s']}s", flush=True)
    print(f"ALL DONE in {round(time.monotonic() - t0, 1)}s "
          f"wall (pool of {WORKERS})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
