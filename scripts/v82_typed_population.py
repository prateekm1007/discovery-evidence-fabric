#!/usr/bin/env python3
"""R47 D2c — typed-operator plan population on DEV (the F61 route).

Deterministic, zero-LLM PLAN layer: for each burned DEV problem,
enumerate K>=3 LEGAL candidate plans — each plan binds a mechanism_space
typed operator (six registered contracts), a self-encoded TRIZ
principle, a measure_class enum value, and signals_used enum values.

Legality = the operator's typed input_contract must be SATISFIED
(state dict, "satisfied" bool — semantics established by
scripts/r47_contract_probe.py, 14/14) against the problem-statement
anchor. Evidence-anchored operators bind only when the problem's own
vocabulary carries their contract terms — honest, deterministic,
reproducible (the anchor is the synthetic knowledge-first record built
from the problem statement itself; a real retrieval corpus would add
anchors, never fake them).

Schedule-family cap: at most ceil(K/6) duty_cycle-class plans per
problem (pre-registered adoption bar: aggregate schedule-share <=17%,
ALLOWED_ROW_OUTSIDE = 0). Diversity axes are computed from the plan
fields (QDAIF: deterministic axes, never LLM-judged).

This is the PLAN layer only; the LLM expansion of the chosen plan is
the machine's job — the matched-budget DEV ablation vs V7.7 consumes
these plans next. Zero LLM calls in this module.
"""
import json
import math
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
import triz_principles as tp  # noqa: E402

K = 3  # plans per problem (AM44 direction 2: K>=3)

MEASURE_CLASSES = {"duty_cycle", "chemistry", "geometry", "material",
                   "control", "configuration", "boundary"}
SCHEDULE_CLASS = "duty_cycle"          # the monoculture family (F54)
SIGNALS = {"conductivity", "ph", "temperature", "pressure", "vibration",
           "current", "visual_inspection", "ac_impedance", "flow_rate",
           "dewpoint", "none"}

# operator -> default measure_class affinity
OP_CLASS = {
    "GEOMETRIC_TRANSFORMATION": "geometry",
    "BOUNDARY_CONDITION_CHANGE": "boundary",
    "DIRECT_TRANSFER": "configuration",
    "CROSS_DOMAIN_ANALOGY": "chemistry",
    "FAILURE_PATH_INVERSION": "control",
}
# measure_class -> preferred TRIZ principles (from the self-encoded 40)
CLASS_PRINCIPLES = {
    "duty_cycle": ["P19", "P20", "P21"],
    "chemistry": ["P31", "P39", "P38"],
    "geometry": ["P1", "P7", "P14", "P30", "P4"],
    "material": ["P13", "P35", "P27"],
    "control": ["P22", "P23", "P24", "P25"],
    "configuration": ["P5", "P15", "P17", "P3"],
    "boundary": ["P35", "P39", "P3", "P6"],
}
# measure_class -> default signals_used (deterministic, enum only)
CLASS_SIGNALS = {
    "duty_cycle": ["temperature", "current"],
    "chemistry": ["ph", "conductivity"],
    "geometry": ["visual_inspection", "pressure"],
    "material": ["visual_inspection", "ac_impedance"],
    "control": ["vibration", "temperature"],
    "configuration": ["flow_rate", "pressure"],
    "boundary": ["pressure", "temperature"],
}


def anchor_item(problem: dict) -> dict:
    """The synthetic problem-statement anchor in the engine's nested
    field shape (the knowledge-first record)."""
    kf = ms.knowledge_first_item(problem)
    fields = {
        "system": str(problem.get("device") or ""),
        "mechanism": str(problem.get("failure") or ""),
        "intervention": str(problem.get("constraint") or ""),
        "observed_effect": str(problem.get("failure_mode") or ""),
        "boundary_conditions": str(problem.get("constraint") or ""),
        "failure_mode": str(problem.get("failure_mode") or ""),
    }
    kf.setdefault("fields", {})
    for k, v in fields.items():
        kf["fields"].setdefault(k, {"value": v})
    return kf


def enumerate_plans(problem: dict) -> list:
    """Legal plan set for one problem: contract-satisfied operators
    first (one plan per binding operator), then knowledge-first
    variants under distinct principles until K plans."""
    item = anchor_item(problem)
    ops = {op["operator_id"]: op for op in ms.TRANSFORMATION_OPERATORS}
    plans = []
    # 1. evidence-anchored operators whose typed contract binds
    for op_id, cls in OP_CLASS.items():
        contract = ops[op_id]["input_contract"]
        state = contract(item, problem)
        if not state.get("satisfied"):
            continue
        pr = CLASS_PRINCIPLES[cls][0]
        plans.append({
            "operator_id": op_id,
            "measure_class": cls,
            "principle_id": pr,
            "signals_used": CLASS_SIGNALS[cls],
            "contract_satisfied": True,
            "contract_state": {k: v for k, v in state.items()
                               if k != "operator"},
        })
    # 2. knowledge-first (always legal per the probe)
    seed_pr, seed_family = tp.seed_for(json.dumps(problem))
    kf_cls = "duty_cycle" if tp.DUTY_CYCLE_FAMILY_RX.search(
        json.dumps(problem)) else seed_class(seed_family)
    kf_principles = [seed_pr] + [p for p in CLASS_PRINCIPLES.get(
        kf_cls, CLASS_PRINCIPLES["configuration"]) if p != seed_pr]
    plans.append({
        "operator_id": "DOMAIN_KNOWLEDGE_FIRST",
        "measure_class": kf_cls,
        "principle_id": kf_principles[0],
        "signals_used": CLASS_SIGNALS.get(kf_cls, ["none"]),
        "contract_satisfied": True,
        "contract_state": {"basis": "problem-statement anchor"},
        "_kf_pool": kf_principles,
    })
    # 3. fill to K with knowledge-first principle variants
    pool = plans[-1].get("_kf_pool", [])
    used_pr = {p["principle_id"] for p in plans}
    for pr in pool:
        if len(plans) >= K:
            break
        if pr in used_pr:
            continue
        plans.append({
            "operator_id": "DOMAIN_KNOWLEDGE_FIRST",
            "measure_class": plans[-1]["measure_class"],
            "principle_id": pr,
            "signals_used": plans[-1]["signals_used"],
            "contract_satisfied": True,
            "contract_state": {"basis": "problem-statement anchor"},
        })
        used_pr.add(pr)
    # 4. schedule cap: at most ceil(K/6) duty_cycle plans; demote the
    #    excess deterministically to the configuration class
    cap = max(1, math.ceil(K / 6))
    dc_idx = [i for i, p in enumerate(plans)
              if p["measure_class"] == SCHEDULE_CLASS]
    for i in dc_idx[cap:]:
        plans[i]["measure_class"] = "configuration"
        plans[i]["principle_id"] = CLASS_PRINCIPLES["configuration"][0]
        plans[i]["signals_used"] = CLASS_SIGNALS["configuration"]
        plans[i]["schedule_demoted"] = True
    # 5. distinct principles across the set (the F54 monoculture kill)
    seen = set()
    for p in plans:
        if p["principle_id"] in seen:
            alts = [c for c in CLASS_PRINCIPLES[p["measure_class"]]
                    if c not in seen]
            if alts:
                p["principle_id"] = alts[0]
        seen.add(p["principle_id"])
    for p in plans:
        p.pop("_kf_pool", None)
    return plans[:K]


def seed_class(family) -> str:
    """Family (from the self-encoded contradiction map) -> measure
    class."""
    fam = str(family or "").lower()
    if any(w in fam for w in ("temp", "thermal", "heat")):
        return "boundary"
    if any(w in fam for w in ("chem", "corros", "scal", "deposit")):
        return "chemistry"
    if any(w in fam for w in ("geom", "shape", "struct", "surface")):
        return "geometry"
    if any(w in fam for w in ("wear", "fatigue", "material")):
        return "material"
    if any(w in fam for w in ("monitor", "measure", "detect")):
        return "control"
    return "configuration"


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
        plans = enumerate_plans(p)
        assert len(plans) >= K, (p.get("problem_id"), len(plans))
        pr_ids = {pl["principle_id"] for pl in plans}
        assert len(pr_ids) == len(plans), (
            p.get("problem_id"), "principles not distinct")
        for pl in plans:
            total_plans += 1
            all_classes.add(pl["measure_class"])
            op_counts[pl["operator_id"]] = \
                op_counts.get(pl["operator_id"], 0) + 1
            if pl["measure_class"] == SCHEDULE_CLASS:
                schedule_plans += 1
            if pl["measure_class"] not in MEASURE_CLASSES or \
                    not set(pl["signals_used"]) <= SIGNALS:
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
        "measure_classes_used": sorted(all_classes),
        "operator_coverage": op_counts,
        "distinct_operators": len(op_counts),
        "llm_calls": 0,
    }
    out = {
        "record": "V82_TYPED_PLAN_POPULATION/1.0.0",
        "session": "builder-r47s2",
        "route": "F61 D2 (AM44 direction 2): typed-operator plan layer "
                 "on DEV; LLM expansion + matched-budget ablation vs "
                 "V7.7 are the next step",
        "legality": "operator typed input_contract satisfied (state "
                    "dict convention, probe 14/14) against the "
                    "problem-statement anchor",
        "stats": stats,
        "problems": records,
    }
    dest = REPO / "eval/v82_dev_plan_population.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
