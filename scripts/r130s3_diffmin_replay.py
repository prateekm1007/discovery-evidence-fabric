#!/usr/bin/env python3
"""r130s3_diffmin_replay.py — the dir-3 held-out no-regression re-test
(claim c-0209; the prereg eval/r130s3_diffmin_prereg.json governs).

Replays the REVIEWER stage over the 48 COMMITTED F31e pre-review bills
(authored_bill + surfaced_findings from succ_d{1,2}_*.json — disjoint
from the twin's GEPA compile corpus) with the PAIRED arms:
  v1 = IMPROVED_DIRECTIVE (the frozen incumbent bytes)
  v2 = v1 + M5  (the diff-minimization clause, byte-identical to the
       twin's m5_minimal composition)
The leg mechanics are BYTE-REUSED from the twin's committed harness
(review_leg + score_leg imported unmodified). Pool 3, byte-resume,
per-leg transport_attempts in the records. Zero engine lines.

Usage: python3 -I scripts/r130s3_diffmin_replay.py
Writes: eval/r130s3_diffmin_replay/{arm}_{draw}_{pid}.json (byte-resume)
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

OUT = REPO / "eval" / "r130s3_diffmin_replay"
OUT.mkdir(parents=True, exist_ok=True)

from r125_f31e_run import IMPROVED_DIRECTIVE  # noqa: E402
from r130_gepa_reviewer import M5, ITEMS, review_leg, score_leg  # noqa: E402

V1 = IMPROVED_DIRECTIVE
V2 = IMPROVED_DIRECTIVE + M5
WORKERS = 3  # the harness's own worker count
PRINT_LOCK = threading.Lock()


def heldout_inputs():
    """The 48 replayable pairs from the committed succ records."""
    out = []
    for f in sorted((REPO / "eval" / "r125_f31e_run")
                    .glob("succ_d*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        ab, sf = d.get("authored_bill"), d.get("surfaced_findings")
        if ab and sf:
            out.append({"pid": d["problem_id"], "draw": d["draw"],
                        "bill": ab, "findings": sf})
    return out


def quota_probe() -> bool:
    import discovery_fabric.engine.route_adapter as ra  # noqa: E402
    try:
        r = ra.agnes_chat(
            [{"role": "user", "content": "Reply with the single word: READY."}],
            model="agnes-3.0-flash", visible_target=20, timeout_s=120.0)
        return bool((r.get("content") or "").strip())
    except Exception as e:  # noqa: BLE001
        print(f"quota probe FAILED: {type(e).__name__}: {str(e)[:120]}",
              flush=True)
        return False


def main() -> int:
    print("DIFFMIN FOLD RE-TEST: v1 vs v2 (paired) over the 48 held-out "
          "committed F31e pre-review bills; leg mechanics byte-reused "
          "from r130_gepa_reviewer (the prereg governs)", flush=True)
    if not quota_probe():
        (OUT.parent / "r130s3_INFRA_QUOTA_WALL").write_text(
            "the quota probe failed at run start\n", encoding="utf-8")
        print("REFUSED (typed INFRA_QUOTA_WALL)", flush=True)
        return 3
    inputs = heldout_inputs()
    assert len(inputs) == 48, f"held-out corpus drift: {len(inputs)}"
    jobs = []
    for inp in inputs:
        for arm, directive in (("v1", V1), ("v2", V2)):
            path = OUT / f"{arm}_{inp['draw']}_{inp['pid']}.json"
            if path.exists():
                continue
            jobs.append((arm, directive, inp, path))
    print(f"byte-resume: {96 - len(jobs)} legs done, {len(jobs)} to go",
          flush=True)
    t0 = time.monotonic()
    done = 0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {}
        for arm, directive, inp, path in jobs:
            futs[ex.submit(review_leg, directive, inp["pid"],
                           inp["bill"], inp["findings"],
                           f"{arm}")] = (arm, inp, path)
        for fut in cf.as_completed(futs):
            arm, inp, path = futs[fut]
            rec = fut.result()
            rec["arm"] = arm
            rec["draw"] = inp["draw"]
            rec["work_id"] = "r130s3-diffmin-fold"
            if rec.get("ok"):
                rec["score"] = score_leg(inp["pid"], rec["delivered"])
            path.write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            with PRINT_LOCK:
                print(f"  [{done}/{len(jobs)}] {arm}/{inp['draw']}/"
                      f"{inp['pid']} "
                      f"{'ok' if rec.get('ok') else 'FAIL'} "
                      f"{rec.get('latency_s')}s "
                      f"att={rec.get('transport_attempts')}",
                      flush=True)
    print(f"ALL DONE in {round(time.monotonic() - t0, 1)}s wall "
          f"(pool of {WORKERS})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
