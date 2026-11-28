#!/usr/bin/env python3
"""r122_lever_run.py — the dir-3 residual-class lever run (claim
c-0185, work id r122-residual-class-lever; the R122 direction 3).

The prereg (eval/r122_lever_prereg.json, committed BEFORE any
lever-run byte) governs. A SECOND reviewer pass with the IMPROVED
directive (the frozen INPUT RULE clause) over the F31c DELIVERED
bills:

  - retest set: the 9 F31c items whose successor delivery was still
    defective (8 input_availability + 1 physics_direction)
  - guard set: the 15 F31c items whose successor delivery was clean

The bind CHECK layer + the detectors stay byte-identical (imported
from the r121 instrument). Byte-skip resume.

Usage: python3 scripts/r122_lever_run.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

F31C = REPO / "eval" / "r123_fresh_confirmation_run"
ITEMS = REPO / "eval" / "r123_fresh_set" / "items.jsonl"
OUT = REPO / "eval" / "r122_lever_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from r121_successor_run import check_layer  # noqa: E402

V = "agnes-3.0-flash"

# the FROZEN improved directive (eval/r122_lever_prereg.json
# improved_directive_bytes — copied verbatim, never re-worded)
IMPROVED_DIRECTIVE = (
    "You are reviewing an engineering proposal. The automated check "
    "layer surfaced the findings listed below against the original "
    "problem. Fix the proposal so the findings no longer apply, "
    "changing as little else as possible. Return the complete "
    "corrected proposal. INPUT RULE: for every input, measurement, "
    "or logic signal your corrected proposal relies on, state "
    "explicitly which permitted sensor or measurement it comes from, "
    "or how it is derived from the permitted measurements with the "
    "formula; remove any input that cannot be derived from the "
    "permitted measurements.")

RETEST = ["r123-01-s2", "r123-02-s2", "r123-03-s1", "r123-03-s2",
          "r123-04-s2", "r123-06-s1", "r123-07-s1", "r123-07-s2",
          "r123-08-s1"]
GUARD = ["r123-01-s1", "r123-02-s1", "r123-04-s1", "r123-05-s1",
         "r123-05-s2", "r123-06-s2", "r123-08-s2", "r123-09-s1",
         "r123-09-s2", "r123-10-s1", "r123-10-s2", "r123-11-s1",
         "r123-11-s2", "r123-12-s1", "r123-12-s2"]


def _call(prompt: str, label: str) -> str:
    for attempt in (1, 2, 3, 4):
        try:
            return ra.agnes_chat(
                [{"role": "user", "content": prompt}],
                model=V, visible_target=4000,
                timeout_s=300.0).get("content") or ""
        except Exception as e:  # noqa: BLE001
            print(f"    {label} attempt {attempt} FAILED "
                  f"{type(e).__name__}: {str(e)[:90]}", flush=True)
            if attempt == 4:
                raise
            time.sleep(120)


def main() -> int:
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in ITEMS.read_text(encoding="utf-8")
             .strip().split("\n")}
    plan = [(pid, "retest") for pid in RETEST] + \
           [(pid, "guard") for pid in GUARD]
    print(f"lever run: {len(RETEST)} retest + {len(GUARD)} guard = "
          f"{len(plan)} second-pass calls", flush=True)
    for pid, group in plan:
        outp = OUT / f"lever_{pid}.json"
        if outp.exists():
            print(f"  {pid}: SKIP (byte-resume)", flush=True)
            continue
        prob = items[pid]
        f31c = json.loads((F31C / f"row_{pid}.json").read_text(
            encoding="utf-8"))
        base_bill = f31c["delivered_bill"]
        # the STILL-STANDING findings (the F31c post-review scan)
        vio = f31c["post_review_scan"]
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        prompt = (IMPROVED_DIRECTIVE
                  + "\n\nORIGINAL PROBLEM:\n"
                  + json.dumps({k: prob.get(k, "") for k in
                                ("problem_id", "device", "failure",
                                 "constraint")}, ensure_ascii=False)
                  + "\n\nPROPOSAL UNDER REVIEW:\n" + base_bill
                  + "\n\nSURFACED FINDINGS (fix these):\n"
                  + "\n".join(f"- {f}" for f in findings))
        try:
            delivered = _call(prompt, f"lever-{pid}")
        except Exception as e:  # noqa: BLE001
            (OUT / f"lever_{pid}.TYPED_FAIL").write_text(
                f"lever leg: {type(e).__name__}: "
                f"{str(e)[:200]}\n", encoding="utf-8")
            print(f"  {pid}: TYPED_FAIL {type(e).__name__}",
                  flush=True)
            time.sleep(60)
            continue
        rescan = check_layer(prob, delivered, None)
        rec = {
            "problem_id": pid, "group": group,
            "registered_model": V,
            "pass": "second reviewer pass with the improved "
                    "directive (the frozen INPUT RULE clause)",
            "input_bill": base_bill,
            "still_standing_findings": findings,
            "still_standing_scan": {k: list(v) for k, v in
                                    vio.items()},
            "delivered_bill": delivered,
            "post_lever_scan": {k: list(v) for k, v in
                                rescan.items()},
        }
        outp.write_text(json.dumps(rec, indent=1,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
        still = sorted(k for k, v in rescan.items() if v)
        print(f"  {pid} [{group}]: standing {len(findings)} -> "
              f"residual {len(still)} {still[:4]}", flush=True)
        time.sleep(8)
    n = len(list(OUT.glob("lever_*.json")))
    print(f"\nDONE: {n}/{len(plan)} rows (typed fails: "
          f"{len(list(OUT.glob('*.TYPED_FAIL')))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
