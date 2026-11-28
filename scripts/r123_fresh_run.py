#!/usr/bin/env python3
"""r123_fresh_run.py — the F31c score-9 fresh held-out confirmation run
(claim c-0183, work id r123-fresh-confirmation-run; the R122 direction
2; the prereg eval/r123_fresh_confirmation_prereg.json governs).

Arms on eval/r123_fresh_set/items.jsonl (24 fresh items):
  BARE_ONLY   — the r118 AUTHORING_DIRECTIVE bytes, one agnes-3.0-flash
                call per item (imported from r118_authoring_run —
                never re-declared). Raw completion committed verbatim.
  SUCCESSOR   — the SAME authoring draw + the r121 check layer
                (imported, zero LLM) + the r121 FIX_DIRECTIVE reviewer
                call per item (imported, NOT improved). The reviewer's
                output is the DELIVERED bill.

Byte-skip resume per item per leg (one call per item per leg, ever —
Art. 29(c)). The quota probe gates execution (INFRA_QUOTA_WALL typed).

Usage: python3 scripts/r123_fresh_run.py [--bare-only|--successor-only]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

ITEMS = REPO / "eval" / "r123_fresh_set" / "items.jsonl"
OUT = REPO / "eval" / "r123_fresh_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from r118_authoring_run import bare_call  # noqa: E402  (the F31a bytes)
from r121_successor_run import check_layer, reviewer_call  # noqa: E402

V = "agnes-3.0-flash"


def quota_probe() -> bool:
    try:
        r = ra.agnes_chat(
            [{"role": "user", "content": "Reply with the single word: "
                                         "READY."}],
            model=V, visible_target=20, timeout_s=120.0)
        return bool((r.get("content") or "").strip())
    except Exception as e:  # noqa: BLE001
        print(f"quota probe FAILED: {type(e).__name__}: "
              f"{str(e)[:120]}", flush=True)
        return False


def run_bare(items: list) -> int:
    for prob in items:
        pid = prob["problem_id"]
        path = OUT / f"bare_{pid}.txt"
        if path.exists():
            print(f"  bare {pid}: SKIP (byte-resume)", flush=True)
            continue
        txt = bare_call(prob)
        path.write_text(txt, encoding="utf-8")
        print(f"  bare {pid}: {len(txt)}c", flush=True)
        time.sleep(8)
    return 0


def run_successor(items: list) -> int:
    for prob in items:
        pid = prob["problem_id"]
        outp = OUT / f"succ_{pid}.json"
        if outp.exists():
            print(f"  succ {pid}: SKIP (byte-resume)", flush=True)
            continue
        bill = (OUT / f"bare_{pid}.txt").read_text(encoding="utf-8")
        vio = check_layer(prob, bill, None)
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        try:
            delivered = reviewer_call(prob, bill, findings)
        except Exception as e:  # noqa: BLE001
            (OUT / f"succ_{pid}.TYPED_FAIL").write_text(
                f"reviewer leg: {type(e).__name__}: {str(e)[:200]}\n",
                encoding="utf-8")
            print(f"  succ {pid}: TYPED_FAIL {type(e).__name__}",
                  flush=True)
            time.sleep(60)
            continue
        rescan = check_layer(prob, delivered, None)
        rec = {
            "problem_id": pid,
            "registered_model": V,
            "arm": "successor (bare author [fresh set] + bind check + "
                   "bare reviewer fixes)",
            "authored_bill": bill,
            "surfaced_findings": findings,
            "surfaced_scan": {k: list(v) for k, v in vio.items()},
            "delivered_bill": delivered,
            "post_review_scan": {k: list(v) for k, v in rescan.items()},
        }
        outp.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        still = sorted(k for k, v in rescan.items() if v)
        print(f"  succ {pid}: findings {len(findings)} -> residual "
              f"{len(still)} {still[:4]}", flush=True)
        time.sleep(8)
    return 0


def main() -> int:
    items = [json.loads(l) for l in
             ITEMS.read_text(encoding="utf-8").strip().split("\n")]
    items.sort(key=lambda p: p["problem_id"])
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"
    print(f"F31c fresh confirmation: {len(items)} items (mode {mode})",
          flush=True)
    bare_done = len(list(OUT.glob("bare_*.txt")))
    succ_done = len(list(OUT.glob("succ_*.json")))
    if bare_done < len(items) or succ_done < len(items):
        print("quota probe...", flush=True)
        if not quota_probe():
            (OUT / "INFRA_QUOTA_WALL").write_text(
                "the quota probe failed at run start; the claim stays "
                "OPEN typed INFRA_QUOTA_WALL; byte-skip resume will "
                "continue the run when quota recovers\n",
                encoding="utf-8")
            print("REFUSED (typed INFRA_QUOTA_WALL)", flush=True)
            return 3
        print("quota probe OK", flush=True)
    if mode in ("--all", "--bare-only"):
        run_bare(items)
    if mode in ("--all", "--successor-only"):
        run_successor(items)
    print(f"\nDONE: bare {len(list(OUT.glob('bare_*.txt')))}/24, "
          f"successor {len(list(OUT.glob('succ_*.json')))}/24 "
          f"(typed fails: {len(list(OUT.glob('*.TYPED_FAIL')))})",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
