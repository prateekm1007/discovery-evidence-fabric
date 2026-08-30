#!/usr/bin/env python3
"""Live non-medical validation: run arbitrary non-medical problems through
the Toscanini problem builder so (a) the relevance-adjudication custody
path receives REAL pipeline-class entries (run_id=toscanini:ui), and
(b) directive #9 (test arbitrary non-medical problems, not just the
medical benchmark) gets real executions on record.

Discloses per-source status + relevant counts honestly. Never treats a
provider failure as absence (Art. XXI.3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from toscanini import problem_builder  # noqa: E402

PROBLEMS = [
    # (text, expected domain family)
    ("Why do wind turbine gearbox bearings develop micropitting failures "
     "within 5 years of operation?", "industrial"),
    ("How can hydrogen embrittlement be prevented in high-strength bolts "
     "used for bridge construction?", "general"),
    ("Why do lithium-ion battery packs in electric vehicles develop "
     "thermal runaway during fast charging?", "automotive"),
]


def main() -> int:
    for text, family in PROBLEMS:
        print(f"\n=== {text[:70]}...")
        out = problem_builder.build_problem(text)
        p = out["problem"]
        ep = out["evidence_pack"]
        print(f"domain={ep['extraction']['domain']} (expected {family})")
        print(f"problem_id={p['problem_id']}")
        for r in ep["retrieval"]:
            rel = r.get("relevant")
            print(f"  [{r['source']:18s}] {r['status']:12s} "
                  f"retrieved={r['count']:3d} relevant={rel}")
        note = r.get("custody_note") if isinstance(r, dict) else None
        if note:
            print(f"  custody note: {note}")
    print("\n--- usage log after runs ---")
    from discovery_fabric.source_registry import relevance_aggregation
    for sid, s in relevance_aggregation.aggregate_usage()["sources"].items():
        print(f"{sid:20s} n={s['records_total']:4d} "
              f"rate={s['pooled_relevant_rate']} band={s['usage_band']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
