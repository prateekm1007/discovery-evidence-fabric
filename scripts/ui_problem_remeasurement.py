"""Live re-measurement of the three failing UI problems — CEO directive
2026-08-31 (doe_osti 0.175 relevance failure).

Replays the EXACT three problems from the 2026-08-30 toscanini:ui run
(nonmedical_validation_run.py) through the FIXED plumbing:
  - keyword-form queries (what a correct extraction now emits, and what
    keyword_form() enforces on any question-form input)
  - the dual-format OSTI connector (XML + JSON)
  - grammar-aware routing (NHTSA asked vehicle questions only)

The extraction fields are supplied as literals here (DISCLOSED: the live
LLM registry is PROVIDER_UNAVAILABLE this session — these field values
are builder-authored stand-ins for MODEL_DERIVED extraction output, and
each is exactly what the extraction prompt now requests; the deterministic
query-form enforcement (keyword_form) is applied to the QUESTION forms too
so both query shapes are measured against the same live sources).

Adjudication uses the UNCHANGED engine rule (term overlap >= 2).
Reproduction: PYTHONPATH=. python3 scripts/ui_problem_remeasurement.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from toscanini import problem_builder as pb  # noqa: E402
from discovery_fabric.source_registry import query_relevance as qr  # noqa: E402
from discovery_fabric.source_registry import relevance_aggregation as ra  # noqa: E402


PROBLEMS = [
    {
        "text": ("Why do wind turbine gearbox bearings develop micropitting "
                 "failures within 5 years of operation?"),
        "extraction": {
            "domain": "industrial", "device": "wind turbine gearbox bearing",
            "failure_mode": "micropitting",
            "constraint": "bearings must resist micropitting beyond 5 years",
            "failure_query": "wind turbine gearbox bearing micropitting",
            "science_query": "wind turbine gearbox bearing micropitting",
            "_llm": {"status": "BUILDER_STANDIN", "provider": "none",
                     "latency_ms": 0},
        },
    },
    {
        "text": ("How can hydrogen embrittlement be prevented in "
                 "high-strength bolts used for bridge construction?"),
        "extraction": {
            "domain": "general", "device": "high-strength bridge bolts",
            "failure_mode": "hydrogen embrittlement",
            "constraint": "bolts must retain strength without embrittlement",
            "failure_query": "hydrogen embrittlement bridge bolts",
            "science_query": "hydrogen embrittlement prevention high-strength steel bolts",
            "_llm": {"status": "BUILDER_STANDIN", "provider": "none",
                     "latency_ms": 0},
        },
    },
    {
        "text": ("Why do lithium-ion battery packs in electric vehicles "
                 "develop thermal runaway during fast charging?"),
        "extraction": {
            "domain": "automotive", "device": "electric vehicle battery pack",
            "failure_mode": "thermal runaway",
            "constraint": "packs must not enter thermal runaway while fast charging",
            "failure_query": "lithium battery thermal runaway fast charging",
            "science_query": "lithium-ion battery thermal runaway fast charging",
            "_llm": {"status": "BUILDER_STANDIN", "provider": "none",
                     "latency_ms": 0},
        },
    },
]


def main() -> int:
    report = {
        "artifact": "UI_PROBLEM_REMEASUREMENT",
        "directive": "CEO 2026-08-31 — investigate the measured DOE OSTI "
                     "relevance failure end-to-end",
        "disclosure": "extraction fields are builder-authored stand-ins "
                      "(live LLM PROVIDER_UNAVAILABLE this session); "
                      "retrieval, connectors and adjudication are fully "
                      "LIVE; adjudication rule unchanged (overlap >= 2)",
        "baseline_reference": "TOSCANINI/QUERY_RELEVANCE_USAGE.json "
                              "2026-08-30: doe_osti pooled 0.175 "
                              "(7/40, UI questions 0/20)",
        "problems": [],
    }
    for p in PROBLEMS:
        print(f"\n=== {p['text'][:70]}")
        # measure BOTH query forms through the live plumbing: the raw
        # question (old defect condition) and the keyword form (fixed)
        entry = {"text": p["text"], "runs": []}
        for label, extract in (
                ("question_form (old defect condition)",
                 {**p["extraction"],
                  "failure_query": p["text"],
                  "science_query": p["text"]}),
                ("keyword_form (fixed)", p["extraction"])):
            orig = pb.extract_problem_fields
            pb.extract_problem_fields = lambda text, _e=extract: dict(_e)
            try:
                out = pb.build_problem(p["text"])
            finally:
                pb.extract_problem_fields = orig
            run = {
                "query_form": label,
                "retrieval": [
                    {"source": r["source"], "status": r["status"],
                     "count": r["count"], "relevant": r.get("relevant"),
                     "error": (r.get("error") or "")[:120]}
                    for r in out["evidence_pack"]["retrieval"]],
                "routing_notes": out["evidence_pack"]["extraction"]
                                         .get("routing_notes", []),
            }
            entry["runs"].append(run)
            print(f"  --- {label}")
            for r in run["retrieval"]:
                print(f"    [{r['source']:18s}] {r['status']:19s} "
                      f"retrieved={r['count']:3d} relevant={r['relevant']}")
            for note in run["routing_notes"]:
                print(f"    ROUTING: {note[:90]}")
            time.sleep(1)
        report["problems"].append(entry)

    out_path = REPO / "TOSCANINI" / "UI_PROBLEM_REMEASUREMENT.json"
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(f"\n[remeasurement] wrote {out_path}")

    # pooled usage aggregation AFTER these runs — the same instrument that
    # measured 0.175 now sees the new adjudications
    usage = ra.aggregate_usage()
    print("\n--- pooled usage aggregation (post-fix entries) ---")
    for sid, s in usage["sources"].items():
        if sid == "doe_osti":
            print(f"{sid:20s} n={s['records_total']:4d} "
                  f"relevant={s['relevant_total']:3d} "
                  f"rate={s['pooled_relevant_rate']} "
                  f"band={s['usage_band']}")
    usage_path = REPO / "TOSCANINI" / "QUERY_RELEVANCE_USAGE.json"
    usage_path.write_text(json.dumps(usage, indent=1, ensure_ascii=False))
    print(f"[remeasurement] wrote {usage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
