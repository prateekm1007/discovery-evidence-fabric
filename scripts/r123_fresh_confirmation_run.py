#!/usr/bin/env python3
"""r123_fresh_confirmation_run.py — the F31c score-9 FRESH held-out
confirmation run (claim c-0183, work id r123-fresh-confirmation-run;
the R122 direction 2, the enacted axis's acceptance).

The prereg (eval/r123_fresh_confirmation_prereg.json, committed at
528368856 BEFORE any run byte) governs; this runner IMPORTS the
committed instrument bytes and never re-declares them:

  - the fresh set: eval/r123_fresh_set/items.jsonl (24 items, frozen)
  - the bare-authoring prompt: r118's AUTHORING_DIRECTIVE bytes
  - the bind CHECK layer: r121's check_layer (deterministic, zero LLM)
  - the reviewer FIX_DIRECTIVE: r121's bytes (NOT improved — the
    dir-3 lever must not confound the confirmation)

Arms per item (one authoring draw shared by both arms, the F31b
construction): bare_only = the raw authored bill; successor = the
authored bill + the check layer's findings + ONE bare-reviewer call;
the reviewer's output is the DELIVERED bill.

Byte-skip resume: an existing row file is NEVER re-requested (one
call per item per leg, ever — Art. 29(c)).

Usage: python3 scripts/r123_fresh_confirmation_run.py
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
OUT = REPO / "eval" / "r123_fresh_confirmation_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from r118_authoring_run import authoring_prompt  # noqa: E402
from r121_successor_run import check_layer, FIX_DIRECTIVE  # noqa: E402

V = "agnes-3.0-flash"


def _call(prompt: str, target: int, label: str) -> str:
    for attempt in (1, 2, 3, 4):
        try:
            return ra.agnes_chat(
                [{"role": "user", "content": prompt}],
                model=V, visible_target=target,
                timeout_s=300.0).get("content") or ""
        except Exception as e:  # noqa: BLE001
            print(f"    {label} attempt {attempt} FAILED "
                  f"{type(e).__name__}: {str(e)[:90]}", flush=True)
            if attempt == 4:
                raise
            time.sleep(120)


def reviewer_prompt(prob: dict, bill: str,
                    findings: list) -> str:
    return (
        FIX_DIRECTIVE
        + "\n\nORIGINAL PROBLEM:\n"
        + json.dumps({k: prob.get(k, "") for k in
                      ("problem_id", "device", "failure",
                       "constraint")}, ensure_ascii=False)
        + "\n\nPROPOSAL UNDER REVIEW:\n" + bill
        + "\n\nSURFACED FINDINGS (fix these):\n"
        + "\n".join(f"- {f}" for f in findings))


def main() -> int:
    items = [json.loads(l) for l in
             ITEMS.read_text(encoding="utf-8").strip().split("\n")]
    items.sort(key=lambda p: p["problem_id"])
    print(f"F31c fresh confirmation: {len(items)} items, "
          f"48 calls worst case (24 authoring + 24 reviewer)",
          flush=True)
    for prob in items:
        pid = prob["problem_id"]
        outp = OUT / f"row_{pid}.json"
        if outp.exists():
            print(f"  {pid}: SKIP (byte-resume)", flush=True)
            continue
        # (1) the bare authoring draw (shared by both arms)
        bill = _call(authoring_prompt(prob), 4000, "author")
        # (2) the bind CHECK layer (deterministic, zero LLM)
        vio = check_layer(prob, bill, None)
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        # (3) the bare reviewer (only when findings exist; a clean
        #     bare bill delivers as-is — the F31b form)
        if findings:
            try:
                delivered = _call(
                    reviewer_prompt(prob, bill, findings),
                    4000, "reviewer")
            except Exception as e:  # noqa: BLE001
                (OUT / f"row_{pid}.TYPED_FAIL").write_text(
                    f"reviewer leg: {type(e).__name__}: "
                    f"{str(e)[:200]}\n", encoding="utf-8")
                print(f"  {pid}: TYPED_FAIL {type(e).__name__}",
                      flush=True)
                time.sleep(60)
                continue
        else:
            delivered = bill
        rescan = check_layer(prob, delivered, None)
        rec = {
            "problem_id": pid,
            "registered_model": V,
            "arm_construction": "shared authoring draw (F31b form)",
            "authored_bill": bill,
            "surfaced_findings": findings,
            "surfaced_scan": {k: list(v) for k, v in vio.items()},
            "delivered_bill": delivered,
            "post_review_scan": {k: list(v) for k, v in
                                 rescan.items()},
        }
        outp.write_text(json.dumps(rec, indent=1,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
        still = sorted(k for k, v in rescan.items() if v)
        print(f"  {pid}: findings {len(findings)} -> residual "
              f"{len(still)} {still[:4]}", flush=True)
        time.sleep(8)
    n = len(list(OUT.glob("row_*.json")))
    print(f"\nDONE: {n}/24 rows (typed fails: "
          f"{len(list(OUT.glob('*.TYPED_FAIL')))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
