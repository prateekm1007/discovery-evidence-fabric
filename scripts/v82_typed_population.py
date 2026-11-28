#!/usr/bin/env python3
"""R47 D2c CLI — scripts/ shim (F63 remedy R52): the plan-population
logic lives in discovery_fabric/engine/population_search.py now; this
CLI keeps the DEV-corpus loading and the artifact writing so the
committed eval/v82_dev_plan_population.json stays byte-reproducible.
Behavior-preservation is proven by re-running this CLI and
byte-diffing the artifact against the committed one."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import population_search as ps  # noqa: E402


def load_dev_problems() -> list:
    """The burned DEV corpus: v2 + v3 burned holdouts + dev12."""
    out = []
    for name, tag in [
        ("eval/dev_holdout_problems/holdout_v2_problems.burned_dev.json",
         "v2-burned"),
        ("eval/dev_holdout_problems/holdout_v3_problems.burned_dev.json",
         "v3-burned"),
        ("eval/problems_dev12.json", "dev12"),
    ]:
        d = json.loads((REPO / name).read_text(encoding="utf-8"))
        probs = d["problems"] if isinstance(d, dict) and "problems" in d \
            else (d if isinstance(d, list) else [])
        for p in probs:
            p["_dev_source"] = tag
            out.append(p)
    return out


def main():
    problems = load_dev_problems()
    records = []
    all_classes = set()
    op_counts = {}
    schedule_plans = 0
    total_plans = 0
    outside = 0
    for p in problems:
        plans = ps.enumerate_plans(p)
        assert len(plans) >= ps.K, (p.get("problem_id"), len(plans))
        pr_ids = {pl["principle_id"] for pl in plans}
        assert len(pr_ids) == len(plans), (
            p.get("problem_id"), "principles not distinct")
        for pl in plans:
            total_plans += 1
            all_classes.add(pl["measure_class"])
            op_counts[pl["operator_id"]] = \
                op_counts.get(pl["operator_id"], 0) + 1
            if pl["measure_class"] == ps.SCHEDULE_CLASS:
                schedule_plans += 1
            if pl["measure_class"] not in ps.MEASURE_CLASSES or \
                    not set(pl["signals_used"]) <= ps.SIGNALS:
                outside += 1
        records.append({
            "problem_id": p.get("problem_id"),
            "dev_source": p.get("_dev_source"),
            "device": p.get("device"),
            "plans": plans,
        })
    stats = {
        "problems": len(problems),
        "plans_total": total_plans,
        "plans_per_problem": total_plans / max(1, len(problems)),
        "schedule_share": schedule_plans / max(1, total_plans),
        "schedule_bar_max": 0.17,
        "schedule_bar_met": schedule_plans / max(1, total_plans) <= 0.17,
        "allowed_row_outside": outside,
        "plans_domain_clamped": sum(
            1 for r in records for pl in r["plans"]
            if pl.get("domain_clamped")),
        "measure_classes_used": sorted(all_classes),
        "operator_coverage": op_counts,
        "distinct_operators": len(op_counts),
        "llm_calls": 0,
    }
    out = {
        "record": "V82_TYPED_PLAN_POPULATION/1.1.0",
        "session": "builder-r52s1",
        "route": "F61 D2 (AM44 direction 2): typed-operator plan layer "
                 "on DEV, now generated THROUGH the engine "
                 "(discovery_fabric.engine.population_search — the F63 "
                 "remedy). 1.1.0 adds the P1.4 declared-domain clamp: "
                 "problems that declare allowed measures get their "
                 "plans clamped to the mapped declared-domain classes "
                 "(flagged domain_clamped; no declaration -> no clamp, "
                 "Art. XXV). The 1.0.0 artifact (pre-clamp, R47 "
                 "semantics) stays committed untouched.",
        "legality": "operator typed input_contract satisfied (state "
                    "dict convention, probe 14/14) against the "
                    "problem-statement anchor + declared allowed-"
                    "measures domain clamp",
        "stats": stats,
        "problems": records,
    }
    dest = REPO / "eval/r52_dev_plan_population.json"
    dest.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
