#!/usr/bin/env python3
"""r123_v2_run.py — the F31d successor-v2 fresh-confirmation run (claim
c-0186, work id r123-successor-v2-fresh-run; the R123 verdict dirs 3+5;
the prereg eval/r123_successor_v2_prereg.json governs).

Arms over BOTH committed fresh draws (the frozen set's two independent
authoring draws — zero new authoring calls):
  BARE_ONLY    — the committed bare bytes (eval/r123_fresh_run/
                 bare_*.txt + the claiming lane's row_*.json
                 authored_bill), byte-identical.
  SUCCESSOR_V2 — the imported check layer (the F97-fixed detector) +
                 ONE agnes-3.0-flash reviewer call per item with the
                 TWIN'S FROZEN improved-directive bytes (imported from
                 eval/r122_lever_prereg.json, never re-typed).

Byte-skip resume per item per lane; quota probe gates (INFRA_QUOTA_WALL).

Usage: python3 scripts/r123_v2_run.py [--replication-only|--claiming-only]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r123_v2_run"
OUT.mkdir(parents=True, exist_ok=True)

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from r121_successor_run import check_layer  # noqa: E402

V = "agnes-3.0-flash"
# the dir-3 lever: the twin's FROZEN improved-directive bytes,
# imported byte-exact from the committed c-0185 prereg — never re-typed
IMPROVED_DIRECTIVE = json.loads(
    (REPO / "eval" / "r122_lever_prereg.json")
    .read_text(encoding="utf-8"))["the_lever"]["improved_directive_bytes"]


def items_by_lane():
    """[(lane, pid, prob, bare_bill)] for both committed draws."""
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in (REPO / "eval" / "r123_fresh_set" / "items.jsonl")
             .read_text(encoding="utf-8").strip().split("\n") if l}
    rows = []
    for pid in sorted(items):
        bpath = REPO / "eval" / "r123_fresh_run" / f"bare_{pid}.txt"
        rpath = (REPO / "eval" / "r123_fresh_confirmation_run"
                 / f"row_{pid}.json")
        if bpath.exists():
            rows.append(("replication", pid, items[pid],
                         bpath.read_text(encoding="utf-8")))
        if rpath.exists():
            rec = json.loads(rpath.read_text(encoding="utf-8"))
            rows.append(("claiming", pid, items[pid],
                         rec["authored_bill"]))
    return rows


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


def reviewer_call_v2(prob: dict, bill: str, findings: list) -> str:
    prompt = (
        IMPROVED_DIRECTIVE
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
    rows = items_by_lane()
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"
    lanes = ("replication",) if mode == "--replication-only" else (
        ("claiming",) if mode == "--claiming-only" else
        ("replication", "claiming"))
    rows = [r for r in rows if r[0] in lanes]
    print(f"F31d successor-v2: {len(rows)} items over lanes {lanes} "
          f"(improved-directive bytes: {len(IMPROVED_DIRECTIVE)}c, "
          "imported from the c-0185 prereg)", flush=True)
    if len(list(OUT.glob("v2_*.json"))) < len(rows):
        print("quota probe...", flush=True)
        if not quota_probe():
            (OUT / "INFRA_QUOTA_WALL").write_text(
                "the quota probe failed at run start; the claim stays "
                "OPEN typed INFRA_QUOTA_WALL\n", encoding="utf-8")
            print("REFUSED (typed INFRA_QUOTA_WALL)", flush=True)
            return 3
        print("quota probe OK", flush=True)
    for lane, pid, prob, bare in rows:
        outp = OUT / f"v2_{lane}_{pid}.json"
        if outp.exists():
            print(f"  v2 {lane}/{pid}: SKIP (byte-resume)", flush=True)
            continue
        vio = check_layer(prob, bare, None)
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        if not findings:
            rec = {"lane": lane, "problem_id": pid,
                   "registered_model": V,
                   "arm": "successor-v2 (bare author [committed bytes] "
                          "+ F97-fixed check + improved-directive "
                          "reviewer)",
                   "improved_directive_len": len(IMPROVED_DIRECTIVE),
                   "authored_bill": bare, "surfaced_findings": [],
                   "surfaced_scan": {},
                   "reviewer_skipped": True, "delivered_bill": bare,
                   "post_review_scan": {}}
            outp.write_text(json.dumps(rec, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
            print(f"  v2 {lane}/{pid}: NO FINDINGS — delivered = bare "
                  "(no reviewer call needed; zero bytes spent)",
                  flush=True)
            continue
        try:
            delivered = reviewer_call_v2(prob, bare, findings)
        except Exception as e:  # noqa: BLE001
            (OUT / f"v2_{lane}_{pid}.TYPED_FAIL").write_text(
                f"reviewer leg: {type(e).__name__}: {str(e)[:200]}\n",
                encoding="utf-8")
            print(f"  v2 {lane}/{pid}: TYPED_FAIL "
                  f"{type(e).__name__}", flush=True)
            time.sleep(60)
            continue
        rescan = check_layer(prob, delivered, None)
        rec = {"lane": lane, "problem_id": pid,
               "registered_model": V,
               "arm": "successor-v2 (bare author [committed bytes] + "
                      "F97-fixed check + improved-directive reviewer)",
               "improved_directive_len": len(IMPROVED_DIRECTIVE),
               "authored_bill": bare,
               "surfaced_findings": findings,
               "surfaced_scan": {k: list(v) for k, v in vio.items()},
               "delivered_bill": delivered,
               "post_review_scan": {k: list(v) for k, v
                                    in rescan.items()}}
        outp.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        still = sorted(k for k, v in rescan.items() if v)
        print(f"  v2 {lane}/{pid}: findings {len(findings)} -> "
              f"residual {len(still)} {still[:4]}", flush=True)
        time.sleep(8)
    print(f"\nDONE: v2 {len(list(OUT.glob('v2_*.json')))}/{len(rows)} "
          f"(typed fails: {len(list(OUT.glob('*.TYPED_FAIL')))})",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
