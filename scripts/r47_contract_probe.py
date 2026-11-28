#!/usr/bin/env python3
"""R47 D2a — proper typed-contract semantics probe.

The D1 smoke's accept/reject probe was weak (it counted any returned
dict as "accepted"). The real convention: each contract returns a
typed state dict whose "satisfied" bool is the bind. This probe builds
REAL positive and negative cases per contract and asserts the states
in both directions. Zero LLM calls.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

PROBLEM = {
    "problem_id": "DEV-probe-01",
    "device": "shell-and-tube condenser with tube bundle",
    "failure": "CaCO3 fouling deposits on tube walls reduce heat duty",
    "failure_mode": "scaling",
    "constraint": "no process shutdown; online mitigation only",
}

def _item(item_id, **fields):
    """Evidence items carry the engine's nested shape: each field is a
    dict with a "value" key (extract_structured_evidence_item output)."""
    return {"item_id": item_id,
            "fields": {k: {"value": v} for k, v in fields.items()}}


# A same-domain evidence item (system overlaps the problem domain)
ITEM_SAME_DOMAIN = _item(
    "ev-same-domain",
    system="shell-and-tube condenser cooling water side",
    mechanism="calcium carbonate scale layer on tube walls raises "
              "wall temperature and cuts effective U",
    intervention="online phosphonate threshold treatment",
    observed_effect="fouling resistance held below 2e-4 m2K/W",
    boundary_conditions="pressure 3 bar; temperature 55 degC; "
                        "pH 8.0; flow 1.2 m/s",
    failure_mode="CaCO3 scaling under elevated wall temperature")

# A foreign-system evidence item (zero system overlap; mechanism
# vocabulary still speaks to the failure)
ITEM_FOREIGN = _item(
    "ev-foreign",
    system="drip irrigation emitter lines in agricultural fields",
    mechanism="calcium carbonate scale clogs emitter channels; "
              "acid pulses dissolve the deposits",
    intervention="periodic acid dosing through the lines",
    observed_effect="emitter flow restored after scale dissolution",
    boundary_conditions="line pressure 1 bar; water hardness 300 "
                        "ppm CaCO3",
    failure_mode="mineral scale clogging")

ITEM_GEOMETRY = _item(
    "ev-geometry",
    system="plate heat exchanger",
    mechanism="porous coating on the plate surface nucleates "
              "scale away from the primary channel",
    intervention="helical groove insert changes wall shear",
    observed_effect="scale nucleates on the sacrificial layer",
    boundary_conditions="temperature 60 degC",
    failure_mode="scaling")

EV = []


def rec(name, expect, got):
    ok = expect == got
    EV.append({"case": name, "expect_satisfied": expect,
               "got_satisfied": got, "verdict": "OK" if ok else "MISMATCH"})
    print(f"{'OK  ' if ok else 'MISMATCH'} {name}: expect={expect} got={got}")


def sat(fn, item, problem):
    return bool(fn(item, problem)["satisfied"])


ops = {op["operator_id"]: op for op in ms.TRANSFORMATION_OPERATORS}
c_dt = ops["DIRECT_TRANSFER"]["input_contract"]
c_cd = ops["CROSS_DOMAIN_ANALOGY"]["input_contract"]
c_kf = ops["DOMAIN_KNOWLEDGE_FIRST"]["input_contract"]
c_gt = ops["GEOMETRIC_TRANSFORMATION"]["input_contract"]
c_bc = ops["BOUNDARY_CONDITION_CHANGE"]["input_contract"]
c_fp = ops["FAILURE_PATH_INVERSION"]["input_contract"]

# DIRECT_TRANSFER: same-domain binds; foreign system does not
rec("DT same-domain evidence", True, sat(c_dt, ITEM_SAME_DOMAIN, PROBLEM))
rec("DT foreign system", False, sat(c_dt, ITEM_FOREIGN, PROBLEM))

# CROSS_DOMAIN_ANALOGY: foreign system + failure-vocab overlap binds;
# same-domain evidence does NOT (it belongs to DIRECT_TRANSFER); and a
# foreign system with NO mechanism overlap does not
rec("CD foreign + mechanism overlap", True,
    sat(c_cd, ITEM_FOREIGN, PROBLEM))
rec("CD same-domain evidence", False,
    sat(c_cd, ITEM_SAME_DOMAIN, PROBLEM))
ITEM_FOREIGN_NOMECH = _item(
    "ev-foreign-nomech",
    system="drip irrigation emitter lines in agricultural fields",
    mechanism="root growth patterns shift with soil",
    observed_effect="emitter placement optimized",
    failure_mode="mineral scale clogging")
rec("CD foreign without mechanism overlap", False,
    sat(c_cd, ITEM_FOREIGN_NOMECH, PROBLEM))

# KNOWLEDGE_FIRST: anchored item binds; the tamper (flag stripped)
# must NOT bind — the D1 smoke's weak probe claimed accepted(!) here
kf = ms.knowledge_first_item(PROBLEM)
rec("KF anchored item", True, sat(c_kf, kf, PROBLEM))
kf_tampered = {k: v for k, v in kf.items() if k != "_knowledge_first"}
rec("KF tampered (flag stripped)", False, sat(c_kf, kf_tampered, PROBLEM))
rec("KF wrong problem (empty failure)", False,
    sat(c_kf, kf, {**PROBLEM, "failure": ""}))

# GEOMETRIC_TRANSFORMATION: geometry vocabulary binds; no geometry
# vocabulary does not
rec("GT geometry vocabulary", True, sat(c_gt, ITEM_GEOMETRY, PROBLEM))
ITEM_NOGEOM = _item(
    "ev-nogeom",
    system="plate heat exchanger",
    mechanism="chemical inhibitor adsorbs on nuclei",
    intervention="phosphonate dosing",
    observed_effect="nucleation blocked",
    boundary_conditions="temperature 60 degC",
    failure_mode="scaling")
rec("GT without geometry vocabulary", False,
    sat(c_gt, ITEM_NOGEOM, PROBLEM))

# BOUNDARY_CONDITION_CHANGE: explicit boundary conditions bind; an
# item without them does not
rec("BC explicit boundary conditions", True,
    sat(c_bc, ITEM_SAME_DOMAIN, PROBLEM))
ITEM_NOBC = _item(
    "ev-nobc",
    system=ITEM_SAME_DOMAIN["fields"]["system"]["value"],
    mechanism=ITEM_SAME_DOMAIN["fields"]["mechanism"]["value"],
    intervention=ITEM_SAME_DOMAIN["fields"]["intervention"]["value"],
    observed_effect=ITEM_SAME_DOMAIN["fields"]["observed_effect"]["value"],
    failure_mode=ITEM_SAME_DOMAIN["fields"]["failure_mode"]["value"])
rec("BC without boundary_conditions field", False,
    sat(c_bc, ITEM_NOBC, PROBLEM))

# FAILURE_PATH_INVERSION: documented failure mode binds; empty does not
rec("FP documented failure mode", True,
    sat(c_fp, ITEM_SAME_DOMAIN, PROBLEM))
ITEM_NOFM = _item(
    "ev-nofm",
    system=ITEM_SAME_DOMAIN["fields"]["system"]["value"],
    mechanism=ITEM_SAME_DOMAIN["fields"]["mechanism"]["value"],
    intervention=ITEM_SAME_DOMAIN["fields"]["intervention"]["value"],
    observed_effect=ITEM_SAME_DOMAIN["fields"]["observed_effect"]["value"],
    boundary_conditions=ITEM_SAME_DOMAIN["fields"]["boundary_conditions"]
    ["value"])
rec("FP without failure_mode", False, sat(c_fp, ITEM_NOFM, PROBLEM))

ok = sum(1 for e in EV if e["verdict"] == "OK")
print(f"\nPROBE VERDICT: {ok}/{len(EV)} cases match the typed state "
      f"convention (satisfied bool)")
with open("eval/r47_contract_probe_results.json", "w", encoding="utf-8") \
        as f:
    json.dump({"probe": "r47_d2a_contract_semantics/1.0.0",
               "convention": "state dict with satisfied bool",
               "llm_calls": 0, "cases": EV}, f, indent=1)
print("wrote eval/r47_contract_probe_results.json")
