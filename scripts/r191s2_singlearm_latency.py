#!/usr/bin/env python3
"""r191s2 single-arm delivery latency (owner DIR-7).

Measures the SERVED recipe only — the r184 pipeline arm:
4 plain draws -> best-of-4 -> critique -> revise -> deterministic verifier.
NO baseline arm, NO judge legs (those are measurement instrumentation,
not delivery). One item at a time, fresh wall clock per item.

Writes eval/r191s2_singlearm_latency/item_{pid}.json (byte-resume) and
prints the median/p95/calls summary at n=24.

Usage: python3 scripts/r191s2_singlearm_latency.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r186s1_ablation_run import (  # noqa: E402  (byte-faithful reuse)
    agnes, env_keys, verify,
)

OUT = REPO / "eval" / "r191s2_singlearm_latency"
OUT.mkdir(exist_ok=True)
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"

# The r184 pipeline-arm recipe (best-of-4 plain + critique + revise),
# exactly as shipped. Critique/revise prompts reused byte-faithfully
# from the ablation runner so the measured arm IS the shipped arm.
from r186s1_ablation_run import plain_prompt  # noqa: E402

N_DRAWS = 4


def critique_prompt(prob: dict, text: str) -> str:
    return (
        "You are a hostile engineering reviewer. Audit the PROPOSAL "
        "against the PROBLEM PACKET. List every serious, defensible "
        "error (wrong physics direction, violated constraint, inverted "
        "causality, missing falsification test). No style comments.\n\n"
        "PROBLEM PACKET:\n" + json.dumps(
            {k: prob.get(k, "") for k in
             ("device", "failure", "constraint")},
            ensure_ascii=False) + "\n\nPROPOSAL:\n" + text + "\n\n"
        "Answer with ONLY the numbered findings (or 'NO FINDINGS')."
    )


def revise_prompt(prob: dict, text: str, findings: str) -> str:
    return (
        "Revise the PROPOSAL to fix every valid finding. Keep the "
        "mechanism, the constraints and the falsification test "
        "structure; change only what a finding requires.\n\n"
        "PROBLEM PACKET:\n" + json.dumps(
            {k: prob.get(k, "") for k in
             ("device", "failure", "constraint")},
            ensure_ascii=False) + "\n\nPROPOSAL:\n" + text +
        "\n\nFINDINGS:\n" + findings + "\n\nOutput ONLY the revised "
        "proposal text."
    )


def serve_one(prob: dict, keys: dict) -> dict:
    """The shipped single-arm delivery. Returns timing + call count."""
    t0 = time.time()
    calls = 0
    draws = []
    for i in range(N_DRAWS):
        draws.append(agnes(
            plain_prompt(prob) +
            f"\n\n(DRAW {i + 1} of {N_DRAWS}; propose the single best "
            "mechanism.)", keys, what="draw"))
        calls += 1
    best = max(draws, key=len)  # the r184 selector: longest draw
    crit = agnes(critique_prompt(prob, best), keys, what="critique")
    calls += 1
    rev = agnes(revise_prompt(prob, best, crit), keys, what="revise")
    calls += 1
    v = verify(rev)
    wall = time.time() - t0
    return {"wall_s": round(wall, 1), "calls": calls,
            "structural_gate_ok": v.get("ok"),
            "fabricated_citations": len(v.get("citation_patterns") or []),
            "has_falsification_span": v.get("has_falsification_span"),
            "text_chars": len(rev)}


def main() -> None:
    keys = env_keys()
    rows = [json.loads(l) for l in
            CORPUS.read_text().splitlines() if l.strip()]
    done = 0
    for prob in rows:
        pid = prob["problem_id"]
        f = OUT / f"item_{pid}.json"
        if f.exists():
            done += 1
            continue
        r = serve_one(prob, keys)
        f.write_text(json.dumps(
            {"problem_id": pid, **r}, indent=1, ensure_ascii=False),
            encoding="utf-8")
        done += 1
        print(f"  {pid}: {r['wall_s']}s {r['calls']} calls "
              f"ok={r['structural_gate_ok']}", flush=True)
    walls = sorted(json.loads(
        (OUT / f"item_{r['problem_id']}.json").read_text())["wall_s"]
        for r in rows)
    calls = [json.loads(
        (OUT / f"item_{r['problem_id']}.json").read_text())["calls"]
        for r in rows]
    n = len(walls)
    med = statistics.median(walls)
    p95 = walls[min(n - 1, int(round(0.95 * n)) - 1)]
    summary = {
        "record": "R191S2_SINGLEARM_LATENCY/1.0.0",
        "n": n,
        "median_s": round(med, 1),
        "p95_s": round(p95, 1),
        "max_s": max(walls),
        "calls_per_item": sorted(set(calls)),
        "gates": {
            "median_le_120": med <= 120,
            "p95_le_300": p95 <= 300,
            "calls_le_12": max(calls) <= 12,
        },
        "recipe": "4 plain draws + critique + revise + deterministic "
                  "verifier (the r184 pipeline arm, served alone; no "
                  "baseline, no judge legs)",
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
