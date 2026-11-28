#!/usr/bin/env python3
"""r126_dir4_run.py — the dir-4 re-test (claim c-0197; the prereg
eval/r126_dir4_duty_prereg.json governs).

The reviewer arm ONLY, over the COMMITTED F31e bare bytes (both
draws, 48 rows, zero authoring calls): the canonical check layer +
ONE reviewer call with the DIRECTIVE-V2 bytes (the frozen r122
567-byte improved directive VERBATIM + the 605-byte conditional
duty clause). A no-findings bare bill delivers itself (zero calls,
typed reviewer_skipped). Byte-skip resume. agnes-3.0-flash.

Usage: python3 scripts/r126_dir4_run.py [--review1|--review2|all]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r126_dir4_run"
OUT.mkdir(parents=True, exist_ok=True)
SRC = REPO / "eval" / "r125_f31e_run"  # the committed bare bytes
SET = REPO / "eval" / "r125_f31e_set" / "items.jsonl"

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from r121_successor_run import check_layer  # noqa: E402

V = "agnes-3.0-flash"

# the directive-v2: the frozen r122 bytes VERBATIM + the duty clause
_BASE = json.loads(
    (REPO / "eval" / "r122_lever_prereg.json")
    .read_text(encoding="utf-8"))["the_lever"]["improved_directive_bytes"]
_CLAUSE = (REPO / "eval" / "r126_duty_clause_bytes.txt")
DIRECTIVE_V2 = _BASE + _CLAUSE.read_text(encoding="utf-8")


def items():
    return [json.loads(l) for l in SET.read_text(
        encoding="utf-8").strip().split("\n") if l]


def quota_probe() -> bool:
    try:
        r = ra.agnes_chat(
            [{"role": "user",
              "content": "Reply with the single word: READY."}],
            model=V, visible_target=20, timeout_s=120.0)
        return bool((r.get("content") or "").strip())
    except Exception as e:  # noqa: BLE001
        print(f"quota probe FAILED: {type(e).__name__}: "
              f"{str(e)[:120]}", flush=True)
        return False


def reviewer_call(prob: dict, bill: str, findings: list) -> str:
    prompt = (DIRECTIVE_V2 + "\n\nORIGINAL PROBLEM:\n"
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


def run_review(draw: str) -> None:
    """The successor arm on the committed bare bytes."""
    for prob in items():
        pid = prob["problem_id"]
        outp = OUT / f"succ_{draw}_{pid}.json"
        if outp.exists():
            print(f"  succ {draw}/{pid}: SKIP (byte-resume)",
                  flush=True)
            continue
        bare = (SRC / f"bare_{draw}_{pid}.txt").read_text(
            encoding="utf-8")
        vio = check_layer(prob, bare, None)
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        if not findings:
            rec = {"draw": draw, "problem_id": pid,
                   "registered_model": V,
                   "arm": "successor-v3 (committed F31e bare bytes "
                          "+ canonical check + directive-v2 reviewer "
                          "[r122 verbatim + duty clause])",
                   "directive_v2_len": len(DIRECTIVE_V2),
                   "authored_bill": bare, "surfaced_findings": [],
                   "surfaced_scan": {},
                   "reviewer_skipped": True, "delivered_bill": bare,
                   "post_review_scan": {}}
            outp.write_text(json.dumps(rec, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
            print(f"  succ {draw}/{pid}: NO FINDINGS — delivered = "
                  "bare (zero calls)", flush=True)
            continue
        try:
            delivered = reviewer_call(prob, bare, findings)
        except Exception as e:  # noqa: BLE001
            (OUT / f"succ_{draw}_{pid}.TYPED_FAIL").write_text(
                f"reviewer leg: {type(e).__name__}: {str(e)[:200]}\n",
                encoding="utf-8")
            print(f"  succ {draw}/{pid}: TYPED_FAIL "
                  f"{type(e).__name__}", flush=True)
            time.sleep(60)
            continue
        rescan = check_layer(prob, delivered, None)
        rec = {"draw": draw, "problem_id": pid,
               "registered_model": V,
               "arm": "successor-v3 (committed F31e bare bytes + "
                      "canonical check + directive-v2 reviewer "
                      "[r122 verbatim + duty clause])",
               "directive_v2_len": len(DIRECTIVE_V2),
               "authored_bill": bare,
               "surfaced_findings": findings,
               "surfaced_scan": {k: list(v) for k, v in vio.items()},
               "delivered_bill": delivered,
               "post_review_scan": {k: list(v) for k, v
                                    in rescan.items()}}
        outp.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        still = sorted(k for k, v in rescan.items() if v)
        print(f"  succ {draw}/{pid}: findings {len(findings)} -> "
              f"residual {len(still)} {still[:4]}", flush=True)
        time.sleep(8)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    done = len(list(OUT.glob("succ_*.json")))
    print(f"dir-4 re-test: mode={mode} (directive-v2 bytes: "
          f"{len(DIRECTIVE_V2)}c = r122 {len(_BASE)}c verbatim + "
          f"clause {len(DIRECTIVE_V2) - len(_BASE)}c; 48 rows over "
          f"the committed F31e bare bytes; zero authoring)",
          flush=True)
    if done < 48:
        print("quota probe...", flush=True)
        if not quota_probe():
            (OUT / "INFRA_QUOTA_WALL").write_text(
                "the quota probe failed at run start; the claim stays "
                "OPEN typed INFRA_QUOTA_WALL\n", encoding="utf-8")
            print("REFUSED (typed INFRA_QUOTA_WALL)", flush=True)
            return 3
        print("quota probe OK", flush=True)
    if mode in ("all", "--review1"):
        run_review("d1")
    if mode in ("all", "--review2"):
        run_review("d2")
    print(f"\nDONE: succ {len(list(OUT.glob('succ_*.json')))} "
          f"(typed fails: {len(list(OUT.glob('*.TYPED_FAIL')))})",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
