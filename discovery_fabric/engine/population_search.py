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
    # 1. evidence-anchored operators whose typed contract binds —
    #    principle pool matrix-sourced (D1, c-0128), tagged
    for op_id, cls in OP_CLASS.items():
        contract = ops[op_id]["input_contract"]
        state = contract(item, problem)
        if not state.get("satisfied"):
            continue
        ints = tuple(int(x[1:]) for x in CLASS_PRINCIPLES[cls])
        pool_res = tp.matrix_seeded_pool(ints)
        pr_list = ["P%d" % x for x in pool_res["principles"]] or \
            CLASS_PRINCIPLES[cls]
        pr = pr_list[0]
        plans.append({
            "operator_id": op_id,
            "measure_class": cls,
            "principle_id": pr,
            "signals_used": CLASS_SIGNALS[cls],
            "contract_satisfied": True,
            "contract_state": {k: v for k, v in state.items()
                               if k != "operator"},
            "principle_source": pool_res["source"],
            "matrix_cell": (pool_res["cell"] or {}).get(
                "improving") is not None and
                f"{pool_res['cell']['improving']}_" +
                f"{pool_res['cell']['worsening']}" or None,
        })
    # 2. knowledge-first (always legal per the probe) — D1 (auditor
    #    direction 1, claim c-0128): the principle pool comes from the
    #    classical TRIZ matrix cells via tp.matrix_seeded_pool (the
    #    keyword family stays the IDENTIFIER; the matrix owns the
    #    principle list). The pool provenance is tagged on every plan
    #    (principle_source) — the >=80% matrix-sourced bind is MEASURED
    #    on the tags, never assumed.
    seed_pr, seed_family = tp.seed_for(json.dumps(problem))
    kf_cls = "duty_cycle" if tp.DUTY_CYCLE_FAMILY_RX.search(
        json.dumps(problem)) else seed_class(seed_family)
    pool_res = tp.matrix_seeded_pool(seed_pr if seed_pr else ())
    kf_principles = ["P%d" % x for x in pool_res["principles"]]
    if not kf_principles:
        kf_principles = list(CLASS_PRINCIPLES.get(
            kf_cls, CLASS_PRINCIPLES["configuration"]))
        pool_res = {"source": "class_fallback", "cell": None,
                    "n_cells": 0}
    plans.append({
        "operator_id": "DOMAIN_KNOWLEDGE_FIRST",
        "measure_class": kf_cls,
        "principle_id": kf_principles[0],
        "signals_used": CLASS_SIGNALS.get(kf_cls, ["none"]),
        "contract_satisfied": True,
        "contract_state": {"basis": "problem-statement anchor"},
        "_kf_pool": kf_principles,
        "principle_source": pool_res["source"],
        "matrix_cell": (pool_res["cell"] or {}).get(
            "improving") is not None and
            f"{pool_res['cell']['improving']}_" +
            f"{pool_res['cell']['worsening']}" or None,
    })
    # 3. fill to K with knowledge-first principle variants
    pool = plans[-1].get("_kf_pool", [])
    fill_source = plans[-1].get("principle_source", "class_fallback")
    fill_cell = plans[-1].get("matrix_cell")
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
            "principle_source": fill_source,
            "matrix_cell": fill_cell,
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
    # 6. chemistry elicitation (AM63 directive 2): when the failure
    #    class admits chemical mechanisms and no plan carries the
    #    chemistry class, PROMOTE the last plan to it (flagged —
    #    never silent, Art. 4) and lead the population order with
    #    chemistry plans (stable): the pre-registered winner rule
    #    takes the first contract-satisfied non-duty_cycle plan in
    #    population order, so population order is the elicitation
    #    lever — the rule itself stays byte-identical.
    if (chemistry_admitted(problem)
            and not any(p["measure_class"] == "chemistry"
                        for p in plans)):
        p = plans[-1]
        taken = {q["principle_id"] for q in plans[:-1]}
        p["measure_class"] = "chemistry"
        p["principle_id"] = next(
            (c for c in CLASS_PRINCIPLES["chemistry"] if c not in taken),
            CLASS_PRINCIPLES["chemistry"][0])
        p["signals_used"] = CLASS_SIGNALS["chemistry"]
        p["chemistry_elicited"] = True
    plans.sort(key=lambda q: 0 if q["measure_class"] == "chemistry"
               else 1)
    # 7. R144 DIR-3 (R143-F7's remedy, claim c-0243): the failure-mode
    #    -> mechanism-class MAP reorders the population AFTER every
    #    legacy ordering rule — the stated failure physics decides
    #    which mechanism classes CAN act on it, and anti-class plans
    #    (a class whose mechanism cannot act on the stated failure
    #    mode — the measured off-target shapes: chemical CP for
    #    abrasion, flow-modulation for tramp metal, monitoring for
    #    nucleation) are demoted to the tail. The pre-registered
    #    winner rule (first contract-satisfied non-duty_cycle plan in
    #    population order) stays BYTE-IDENTICAL — the MAP is an
    #    ordering lever, the same shape as the AM63 elicitation.
    #    Every plan is TAGGED with its fit record (map_source) — the
    #    reorder is measured, never assumed; no detection = no
    #    reorder (Art. XXV).
    from .failure_mechanism_map import mechanism_class_fit
    for p in plans:
        p["mechanism_fit"] = mechanism_class_fit(
            problem, p.get("measure_class", ""))
    # 7b. admitted-class PROMOTION (the AM63 elicitation precedent,
    #     claim c-0243): when a failure family is detected and NO
    #     plan carries an admitted class, the plan space itself is
    #     blind to the failure physics — promote the LAST plan to the
    #     family's first admitted class (flagged map_promoted, never
    #     silent, Art. 4). The winner rule still picks by population
    #     order; the promotion guarantees an on-physics plan EXISTS.
    from .failure_mechanism_map import family_classes
    _fam = plans[0].get("mechanism_fit", {}).get("family") if plans else None
    if _fam and not any(p.get("mechanism_fit", {}).get("admitted")
                        for p in plans):
        _adm, _ = family_classes(_fam)
        if _adm:
            p = plans[-1]
            taken = {q["principle_id"] for q in plans[:-1]}
            p["measure_class"] = _adm[0]
            p["principle_id"] = next(
                (c for c in CLASS_PRINCIPLES[_adm[0]]
                 if c not in taken),
                CLASS_PRINCIPLES[_adm[0]][0])
            p["signals_used"] = CLASS_SIGNALS[_adm[0]]
            p["mechanism_fit"] = mechanism_class_fit(
                problem, p["measure_class"])
            p["map_promoted"] = True
    _pre = [tuple(p.items()) for p in plans]  # stability anchor
    plans.sort(key=lambda q: q.get("mechanism_fit", {}).get("rank", 0))
    if [tuple(p.items()) for p in plans] != _pre:
        for p in plans:
            p.setdefault("map_reordered", True)
    for p in plans:
        p.pop("_kf_pool", None)
    return plans[:K]


# AM63 directive 2 (F75-adjacent, the HO9-01/05/08 monoculture-break
# class): chemistry elicitation fires on the problem's OWN vocabulary
# admitting chemical mechanisms — scale/deposit/corrosion/froth/
# dosing/lubricant classes — while the declared domain does not
# exclude chemistry. The elicitation only adds/plans-orders at the
# PLAN layer; the pre-registered winner rule stays byte-identical.
CHEMISTRY_ADMITS_RX = re.compile(
    r"scal(?:e|ing)|deposit|corros|fouling|froth|flotat|collect(?:or|ion)"
    r"|floccul|coagul|dissolut|precipitat|oxid|reduc(?:tion|ing) agent"
    r"|acids?|alkali|caustic|chloride|sulfide|sulphide|lime|soda|ash"
    r"|inhibit\w*|passivat|chelat|sequest|antiscalant|lubric\w*|grease"
    r"|oil\s+film|emuls|biocid|contaminant|leach|ph\b|dosage|dosing",
    re.IGNORECASE)


def chemistry_admitted(problem: dict) -> bool:
    """True when the problem's own text admits chemical mechanisms and
    the declared domain (P1.4 clamp) does not exclude them."""
    txt = " ".join(str(problem.get(k) or "") for k in
                   ("device", "failure", "failure_mode", "constraint"))
    if not CHEMISTRY_ADMITS_RX.search(txt):
        return False
    domain = declared_domain_classes(problem)
    return domain is None or "chemistry" in domain


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
