#!/usr/bin/env python3
"""r59_seed_hash_probe.py — the cross-seed determinism probe substrate
(Art. 15 v3.2.0 CI addition for F64; ratification claim c-0080).

Runs the INTEGRATED ENGINE ROUTE (engine_route.run_row — the same
measured path the P1 regression uses, zero LLM, zero network) over ONE
fixed committed DEV problem, then prints the content hashes the
constitution names: candidate_id, candidate_hash (per plan result),
and a canonical envelope digest per result.

The TEST (tests/test_article15_determinism.py) invokes this probe
under PYTHONHASHSEED 1/2/3/random and asserts byte-identical stdout —
the F64 failure mode (hashes rotating per process under hash-seed
luck) is structurally absent only if the whole measured path is
seed-stable, which is what this probe measures.

Fixed substrate (committed bytes, not fixtures): the first DEV12
problem by id from eval/problems_dev12.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import engine_route as er          # noqa: E402
from discovery_fabric.engine.candidate import sha256_obj       # noqa: E402


def main() -> int:
    probs = json.loads((REPO / "eval" / "problems_dev12.json")
                       .read_text(encoding="utf-8"))
    if isinstance(probs, dict):
        probs = probs.get("problems", [])
    prob = sorted(probs, key=lambda p: p["problem_id"])[0]
    row = er.run_row(prob)
    out = {"problem_id": prob["problem_id"], "results": []}
    for r in row["results"]:
        c = r["candidate"]
        out["results"].append({
            "candidate_id": c.get("candidate_id"),
            "candidate_hash": c.get("candidate_hash"),
            "content_digest": sha256_obj(
                {k: c[k] for k in sorted(c) if k != "derivation_trace"}),
            "trace_digest": sha256_obj(
                {k: v for k, v in
                 (c.get("derivation_trace") or {}).items()
                 if k != "derived_at"}),
            "novelty_verdicts": row["novelty_gate"]["verdicts"].get(
                c.get("candidate_id")),
        })
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
