"""discovery_fabric/engine/population_search.py — the typed-operator
plan population (R47 D2c, the F61 route), migrated from
scripts/v82_typed_population.py into the engine per the F63 remedy
(R52): the measured DEV path runs THROUGH the engine, not a script
harness.

Deterministic, zero-LLM PLAN layer: for each problem, enumerate
K>=3 LEGAL candidate plans — each plan binds a mechanism_space typed
operator (six registered contracts), a self-encoded TRIZ principle, a
measure_class enum value, and signals_used enum values.

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
these plans. Zero LLM calls in this module.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List

from . import mechanism_space as ms
from . import triz_principles as tp

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

# declared-measure phrase -> measure_class (deterministic keyword
# table, P1.4 domain clamp). A declared measure maps by the FIRST
# matching family; unmapped phrases contribute no class (an unknown
# measure never widens the domain — Art. XXV side: the clamp only
# ever NARROWS).
MEASURE_CLASS_KEYWORDS = [
    ("chemistry", ("additiv", "chemist", "dosing", "blanket", "inhibit",
                   "glue", "thiourea", "chloride", "accelerator",
                   "retarder", "grain-refiner", "biocide", "surfactant")),
    ("duty_cycle", ("schedul", "interval", "load-scheduling",
                    "duty", "periodic", "ramp-rate", "defrost-initiation")),
    ("control", ("monitor", "detect", "indicator", "alarm", "sensor")),
    ("geometry", ("redesign", "geometry", "shape", "retrofit",
                  "surface treatment", "coating")),
    ("material", ("material substitution", "alloy", "metallurg")),
    ("configuration", ("procedure", "ventilation", "cover", "valve",
                       "air-admission", "recirculation", "wastegate",
                       "door", "curtain", "loading", "bypass")),
    ("boundary", ("temperature", "setpoint", "pressure", "boost",
                  "operating-zone", "regime")),
]


def declared_domain_classes(problem: dict):
    """The problem's declared allowed-measures domain, mapped to
    measure classes. None = no declaration (Art. XXV: an unstated
    restriction is not manufactured and no clamp fires)."""
    txt = str(problem.get("constraint") or "")
    m = None
    for mm in re.finditer(r"allowed measures?:\s*(.+?)(?:\.|$)", txt,
                          re.IGNORECASE | re.DOTALL):
        m = mm
    if m is None:
        return None
    raw = m.group(1).lower()
    classes = []
    for cls, kws in MEASURE_CLASS_KEYWORDS:
        if any(k in raw for k in kws):
            classes.append(cls)
    return classes or None


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
    # 4.5 declared-domain clamp (P1.4): when the problem declares its
    #     allowed measures, every plan's measure_class must be in the
    #     mapped declared-domain class set; outside plans are demoted
    #     deterministically to the first declared class (flagged —
    #     never silently rewritten; the flags prove the clamp ran).
    #     No declaration -> no clamp (Art. XXV).
    domain = declared_domain_classes(problem)
    if domain:
        for p in plans:
            if p["measure_class"] not in domain:
                p["measure_class"] = domain[0]
                p["principle_id"] = CLASS_PRINCIPLES[domain[0]][0]
                p["signals_used"] = CLASS_SIGNALS[domain[0]]
                p["domain_clamped"] = True
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
