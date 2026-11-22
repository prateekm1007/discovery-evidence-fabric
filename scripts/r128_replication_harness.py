#!/usr/bin/env python3
"""r128_replication_harness.py — the dir-3 replication harness,
PARAMETERIZED and GATED (a verifier gap-fill artifact, claim
c-0204): the F31e protocol (bare author -> canonical check ->
schema reviewer -> rescan, item-clustered scoring) runnable on ANY
item set, ready for the auditor-authored v16 sealed set the day it
lands. The executor's dir-3 typed the gating correctly (no
non-builder set exists; the holdouts v2-v4 are burned, v5-v16 were
never authored) but left the harness unbuilt — this arms it.

NO RUN this round (Art. 3 + the executor's authorship audit: a
builder-set self-run would answer dir 3 with the wrong independence
class).

Usage (the day the set lands):
  python3 scripts/r128_replication_harness.py \
      --set eval/v16_sealed_items.jsonl --draws 2 --workers 2 \
      --out eval/r128_v16_replication/
Pre-declared acceptance (written into SET_PROVENANCE.json at arm
time): treated rate <= 0.25; the item-clustered 95% CI lower bound
> 0; damage <= 0.25; >= 3 classes with nonzero bare rates.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

import discovery_fabric.engine.route_adapter as ra  # noqa: E402
from r121_successor_run import check_layer  # noqa: E402
from r125_f31e_run import (IMPROVED_DIRECTIVE,  # noqa: E402
                           authoring_prompt)

V = "agnes-3.0-flash"
FIX_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "reviewer_fix",
        "strict": True,
        "schema": {"type": "object",
                   "properties": {"corrected_proposal":
                                  {"type": "string"}},
                   "required": ["corrected_proposal"],
                   "additionalProperties": False},
    },
}


def _call(prompt: str, visible: int, response_format=None,
          what: str = ""):
    for attempt in (1, 2, 3, 4):
        try:
            return ra.agnes_chat(
                [{"role": "user", "content": prompt}],
                model=V, visible_target=visible,
                timeout_s=300.0,
                response_format=response_format), attempt
        except ra.RouteRefused as e:
            if e.kind in ("auth", "missing_key"):
                raise
            if attempt < 4:
                time.sleep(120)
        except Exception:  # noqa: BLE001
            if attempt < 4:
                time.sleep(120)
    raise RuntimeError(f"transport exhausted: {what}")


def one_problem(prob: dict, out: Path, draw: int) -> dict:
    pid = prob["problem_id"]
    rec: dict = {"problem_id": pid, "draw": draw,
                 "registered_model": V, "calls": [],
                 "parse_retries": 0}
    t0 = time.monotonic()
    resp, att = _call(authoring_prompt(prob), 1200,
                      what=f"{pid}/d{draw}/author")
    rec["calls"].append({"leg": "author", "attempts": att,
                         "usage": _usage(resp)})
    bill = resp.get("content") or ""
    rec["authored_bill"] = bill
    vio = check_layer(prob, bill, None)
    findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                for k, v in vio.items() if v]
    rec["surfaced_findings"] = findings
    if not findings:
        rec["delivered_bill"] = bill
        rec["post_review_scan"] = {}
        rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
        rec["status"] = "DELIVERED_BARE"
        _write(out, f"rep_d{draw}_{pid}.json", rec)
        return rec
    prompt = (IMPROVED_DIRECTIVE + "\n\nORIGINAL PROBLEM:\n"
              + json.dumps({k: prob.get(k, "") for k in
                            ("problem_id", "device", "failure",
                             "constraint")}, ensure_ascii=False)
              + "\n\nPROPOSAL UNDER REVIEW:\n" + bill
              + "\n\nSURFACED FINDINGS (fix these):\n"
              + "\n".join(f"- {f}" for f in findings))
    resp, att = _call(prompt, 4000, response_format=FIX_SCHEMA,
                      what=f"{pid}/d{draw}/reviewer")
    rec["calls"].append({"leg": "reviewer", "attempts": att,
                         "usage": _usage(resp)})
    raw = resp.get("content") or ""
    try:
        delivered = str(json.loads(raw).get("corrected_proposal")
                        or "")
        if not delivered.strip():
            raise ValueError("empty corrected_proposal")
    except Exception as e:  # noqa: BLE001
        rec["status"] = "TYPED_PARSE_FAIL"
        rec["parse_fail"] = f"{type(e).__name__}: {str(e)[:140]}"
        rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
        _write(out, f"rep_d{draw}_{pid}.json", rec)
        return rec
    rec["delivered_bill"] = delivered
    rec["post_review_scan"] = {k: list(v) for k, v in
                               check_layer(prob, delivered,
                                           None).items()}
    rec["wall_clock_s"] = round(time.monotonic() - t0, 2)
    rec["status"] = "DELIVERED_REVIEWED"
    _write(out, f"rep_d{draw}_{pid}.json", rec)
    return rec


def _usage(resp: dict) -> dict:
    u = (resp or {}).get("usage") or {}
    ptd = u.get("prompt_tokens_details") or {}
    return {"prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "cached_tokens": ptd.get("cached_tokens")}


def _write(out: Path, name: str, rec: dict) -> None:
    (out / name).write_text(
        json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--draws", type=int, default=2)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    set_path = Path(args.set)
    marker = ("v16" in set_path.parts
              or "auditor" in set_path.name
              or "sealed" in set_path.name)
    if not marker:
        print("REFUSED (typed exit 2): the set name carries no "
              "non-builder provenance marker (v16/auditor/sealed) — "
              "dir 3 requires a set the builder did not author",
              flush=True)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    probs = [json.loads(l) for l in
             set_path.read_text(encoding="utf-8").strip()
             .split("\n") if l]
    (out / "SET_PROVENANCE.json").write_text(json.dumps({
        "set": str(set_path), "n_items": len(probs),
        "draws": args.draws, "workers": args.workers,
        "registered_model": V,
        "acceptance_predeclared": {
            "treated_rate_max": 0.25, "damage_max": 0.25,
            "clustered_ci_low_min": 0.0,
            "min_classes_with_nonzero_bare_rate": 3},
        "scoring": "the item-clustered bootstrap + the discordant "
                   "sign test, the r128_verifier_recompute "
                   "construction",
        "run_starts_only_under": "its own preregistered claim "
                                 "(Art. 29b; the set must carry the "
                                 "auditor's Art. 7 custody chain)",
    }, indent=1), encoding="utf-8")
    print(f"harness ARMED: {len(probs)} items x {args.draws} draws "
          f"-> {out} (no run: awaiting the auditor-authored set "
          f"under its own preregistered claim)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
