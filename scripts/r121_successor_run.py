#!/usr/bin/env python3
"""r121_successor_run.py — the F31b successor-shape run (claim c-0181,
work id r121-successor-bind-value-run; the R121 direction 3).

The prereg (eval/r121_successor_bind_value_prereg.json) governs. The
successor arm on the 24 F31a items, re-using the committed bare bills
byte-identical (zero new authoring calls):

  (1) the bind CHECK layer over each committed bare bill — the
      stripped machine's own scans (zero LLM except the frozen
      direction-check leg, which is part of the check layer and runs
      through the direct transport with the registered model);
  (2) the findings SURFACED verbatim to a BARE REVIEWER — one
      agnes-3.0-flash call per item: the original problem + the
      authored bill + the surfaced findings, the F30 working-reviewer
      fix-directive; the reviewer's output is the DELIVERED bill.

Byte-skip resume: an existing succ_{pid}.json is NEVER re-requested
(one reviewer call per item, ever — Art. 29(c)).

Usage: python3 scripts/r121_successor_run.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

ITEMS = REPO / "eval" / "r118_authoring_set" / "items.jsonl"
BARE_DIR = REPO / "eval" / "r118_authoring_run"
OUT = REPO / "eval" / "r121_successor_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
import r40_machine_v77 as m77                  # noqa: E402
# R133 DIR-3: check_layer MOVED to discovery_fabric/engine/review_layer.py
# (the F63 rule); this name is now a thin re-export shim so the
# historical importers (r127_phaseA_gate et al.) stay importable.
from discovery_fabric.engine.review_layer import check_layer  # noqa: E402,F401

V = "agnes-3.0-flash"

FIX_DIRECTIVE = (
    "You are reviewing an engineering proposal. The automated check "
    "layer surfaced the findings listed below against the original "
    "problem. Fix the proposal so the findings no longer apply, "
    "changing as little else as possible. Return the complete "
    "corrected proposal.")


def reviewer_call(prob: dict, bill: str, findings: list) -> str:
    prompt = (
        FIX_DIRECTIVE
        + "\n\nORIGINAL PROBLEM:\n"
        + json.dumps({k: prob.get(k, "") for k in
                      ("problem_id", "device", "failure",
                       "constraint")}, ensure_ascii=False)
        + "\n\nPROPOSAL UNDER REVIEW:\n" + bill
        + "\n\nSURFACED FINDINGS (fix these):\n"
        + "\n".join(f"- {f}" for f in findings))
    for attempt in (1, 2, 3, 4):
        try:
            return ra.agnes_chat(
                [{"role": "user", "content": prompt}],
                model=V, visible_target=4000,
                timeout_s=300.0).get("content") or ""
        except Exception as e:  # noqa: BLE001
            print(f"    reviewer attempt {attempt} FAILED "
                  f"{type(e).__name__}: {str(e)[:90]}", flush=True)
            if attempt == 4:
                raise
            time.sleep(120)


def main() -> int:
    items = [json.loads(l) for l in
             ITEMS.read_text(encoding="utf-8").strip().split("\n")]
    items.sort(key=lambda p: p["problem_id"])
    print(f"F31b successor run: {len(items)} items "
          f"(committed bare bills re-used, zero authoring calls)",
          flush=True)
    for prob in items:
        pid = prob["problem_id"]
        outp = OUT / f"succ_{pid}.json"
        if outp.exists():
            print(f"  {pid}: SKIP (byte-resume)", flush=True)
            continue
        bill = (BARE_DIR / f"bare_{pid}.txt").read_text(
            encoding="utf-8")
        vio = check_layer(prob, bill, None)
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        try:
            delivered = reviewer_call(prob, bill, findings)
        except Exception as e:  # noqa: BLE001
            (OUT / f"succ_{pid}.TYPED_FAIL").write_text(
                f"reviewer leg: {type(e).__name__}: "
                f"{str(e)[:200]}\n", encoding="utf-8")
            print(f"  {pid}: TYPED_FAIL {type(e).__name__}",
                  flush=True)
            time.sleep(60)
            continue
        rescan = check_layer(prob, delivered, None)
        rec = {
            "problem_id": pid,
            "registered_model": V,
            "arm": "successor (bare author [committed bytes] + bind "
                   "check + bare reviewer fixes)",
            "authored_bill": bill,
            "surfaced_findings": findings,
            "surfaced_scan": {k: list(v) for k, v in vio.items()},
            "delivered_bill": delivered,
            "post_review_scan": {k: list(v) for k, v in rescan.items()},
        }
        outp.write_text(json.dumps(rec, indent=1,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
        still = sorted(k for k, v in rescan.items() if v)
        print(f"  {pid}: findings {len(findings)} -> residual "
              f"{len(still)} {still[:4]}", flush=True)
        time.sleep(8)
    n = len(list(OUT.glob("succ_*.json")))
    print(f"\nDONE: successor {n}/24 (typed fails: "
          f"{len(list(OUT.glob('*.TYPED_FAIL')))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
