#!/usr/bin/env python3
"""r186s1_ablation_repair.py — the item-2 hy4 judge-leg repair (typed infra
failure, the r159 checkpoint precedent).

WHY: the ablation run's hy4 seat ran with max_tokens 2000; on the item-2
real pair (~15K-char prompt) hy4 burned the whole budget on
reasoning_content and returned 200-with-EMPTY content 8 consecutive
times (4 XY + 4 YX attempts, all `unparseable: ''`). The runner recorded
TYPED_JUDGE_FAILURE TIE votes for BOTH hy4 legs — a transport artifact,
not a judge verdict. Measured this session: the SAME prompt with
max_tokens 4000 parses cleanly (VERDICT: X, finish=stop).

SCOPE (one-shot integrity):
  - item-1 verdicts STAND (real parsed bytes; its single failed attempt
    succeeded on retry with real content — no failure markers).
  - item-2 GENERATION bytes STAND (the 4 shared draws + both texts are
    recorded; the generator legs were never affected).
  - ONLY item-2's two hy4 judge legs re-fire (XY and YX, one attempt
    ladder each, budget 4000); qwen legs stand (real verdicts).
  - the item-2 outcome is RECOMPUTED from {repaired hy4, standing qwen}
    with the same panel-majority rule; the repair is disclosed in the
    pair file and in the run record.

Usage: python3 scripts/r186s1_ablation_repair.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from r186s1_ablation_run import blind_prompt, packet  # noqa: E402  byte-identical

PAIR = REPO / "eval/r186s1_ablation/pair_r176i-02-thermoelectric-zt.json"
BASE = "https://api.cent-ai.dev/v1"
MODEL = "hy4-flash:free"
MAX_TOKENS = 4000


def judge_leg(prompt, key, what):
    body = {"model": MODEL, "max_tokens": MAX_TOKENS, "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        req = urllib.request.Request(
            BASE + "/chat/completions", data=json.dumps(body).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                rsp = json.loads(r.read().decode())
            txt = (rsp.get("choices") or [{}])[0].get(
                "message", {}).get("content") or ""
            up = txt.upper()
            v = ("X" if "VERDICT: X" in up else
                 "Y" if "VERDICT: Y" in up else
                 "TIE" if "VERDICT: TIE" in up else None)
            if v:
                return v, txt
            last = RuntimeError(f"unparseable: {txt[:60]!r}")
        except urllib.error.HTTPError as e:
            last = RuntimeError(f"HTTP{e.code}")
            if e.code in (401, 403):
                break
        except Exception as e:  # noqa: BLE001
            last = RuntimeError(f"{type(e).__name__}: {str(e)[:80]}")
        print(f"  {what} attempt {attempt}: {last}; backoff 120s", flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last


def main():
    keys = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            keys[k] = v
    key = keys["CENT_AI_API_KEY"]

    d = json.loads(PAIR.read_text())
    # reconstruct the problem text the same way the runner does
    item = None
    for ln in (REPO / "eval/r176_invention_corpus/items.jsonl").read_text().splitlines():
        it = json.loads(ln)
        if it["problem_id"] == d["problem_id"]:
            item = it
            break
    # the runner passes packet(prob) — the device/failure/constraint JSON
    problem = packet(item)

    full_text = d["full_text"]
    nc_text = d["no_critique_revise_text"]

    # verify the recorded hy4 legs really were typed failures
    raw = json.dumps(d)
    assert "TYPED_JUDGE_FAILURE" in raw or d["votes"]["hy4-flash-centai"] == "TIE", \
        "item-2 hy4 votes do not show the typed-failure state — refusing"

    print("re-firing item-2 hy4 judge legs (budget 4000)...", flush=True)
    legs = {}
    for order in ("XY", "YX"):
        a, b = ((full_text, nc_text) if order == "XY"
                else (nc_text, full_text))
        v, txt = judge_leg(
            blind_prompt(problem, a, b), key, f"item2 hy4 {order}")
        legs[order] = {"raw_verdict": v, "text_head": txt[:120]}
        print(f"  {order}: {v}", flush=True)

    # same two-pass aggregation as the runner: pipeline-in-X for XY,
    # pipeline-in-Y for YX
    vals = []
    for order in ("XY", "YX"):
        v = legs[order]["raw_verdict"]
        pip = (v if order == "XY" else
               "X" if v == "Y" else
               "Y" if v == "X" else "TIE")
        vals.append(pip)
    if all(x in ("X", "TIE") for x in vals) and "X" in vals:
        hy4_vote = "WIN"
    elif all(x in ("Y", "TIE") for x in vals) and "Y" in vals:
        hy4_vote = "LOSS"
    else:
        hy4_vote = "TIE"

    qwen_vote = d["votes"]["qwen3.8-max-xkiro"]  # stands (real bytes)
    outcome = hy4_vote if hy4_vote == qwen_vote else "TIE"

    d["votes"]["hy4-flash-centai"] = hy4_vote
    for jm in d["judges"]:
        if jm["seat"] == "hy4-flash-centai":
            jm["vote"] = hy4_vote
    d["outcome"] = outcome
    d["win_plus_tie"] = outcome in ("WIN", "TIE")
    d["hy4_repair"] = {
        "record": "R186S1_HY4_LEG_REPAIR/1.0.0",
        "cause": ("hy4 seat ran max_tokens 2000; item-2's ~15K-char pair "
                  "prompt burned the budget on reasoning_content — 8 "
                  "consecutive 200-with-EMPTY legs (finish=length), typed "
                  "TYPED_JUDGE_FAILURE TIE votes; measured: budget 4000 "
                  "parses the SAME prompt cleanly"),
        "what_was_refired": ("the two hy4 judge legs ONLY (XY+YX, budget "
                             "4000); generation bytes and qwen legs stand "
                             "unre-fired; item-1 stands entirely"),
        "legs": legs,
        "aggregation": "same two-pass rule; panel majority with standing qwen",
        "repaired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    PAIR.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print(f"item-2 repaired: hy4={hy4_vote} qwen={qwen_vote} -> {outcome}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
