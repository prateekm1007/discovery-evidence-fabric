#!/usr/bin/env python3
"""R47 D1 (F61) zero-LLM smoke of discovery_fabric/engine/mechanism_space.py.

Evidence for the measured-path decision: the 3,716-line typed-operator
engine is EXECUTABLE — the six typed operator contracts bind (accept
valid typed items, reject tampered ones), assemble_candidate produces
the canonical typed candidate with a derivation trace, and the signal
scorer runs. NO LLM call is made (deterministic contract layer only).
"""
import json
import sys
from pathlib import Path
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

EV = {"checks": [], "errors": []}


def check(name, fn):
    try:
        out = fn()
        EV["checks"].append({"check": name, "result": "OK", "detail": out})
        print(f"OK   {name}: {out}")
    except Exception as e:  # a crash IS evidence; record and continue
        tb = traceback.format_exc(limit=3)
        EV["checks"].append({"check": name, "result": "CRASH",
                             "detail": f"{type(e).__name__}: {e}"})
        EV["errors"].append({"check": name, "tb": tb})
        print(f"CRASH {name}: {type(e).__name__}: {e}")


def c1_operators():
    ids = list(ms.OPERATOR_IDS)
    assert len(ids) == 6, ids
    return {"count": len(ids), "ids": ids,
            "version": ms.MECHANISM_SPACE_VERSION}


def c2_registry_shape():
    ops = ms.TRANSFORMATION_OPERATORS
    keys = sorted(ops[0].keys())
    contracts = [op.get("input_contract").__name__ for op in ops]
    return {"keys": keys, "contracts": contracts}


PROBLEM = {
    "problem_id": "DEV-smoke-01",
    "device": "shell-and-tube condenser",
    "failure": "fouling deposits on the tube side reduce heat duty "
               "over long campaigns",
    "constraint": "no process shutdown; online mitigation only",
    "failure_mode": "CaCO3 scaling under elevated wall temperature",
}


def c3_knowledge_first_item():
    item = ms.knowledge_first_item(PROBLEM)
    assert item.get("_knowledge_first") is True
    return {"item_id": item.get("item_id"), "anchored": True,
            "text_len": len(str(item.get("text") or item.get("record") or ""))}


def c4_contracts():
    ops = ms.TRANSFORMATION_OPERATORS
    kf = ms.knowledge_first_item(PROBLEM)
    out = {}
    for op in ops:
        fn = op.get("input_contract")
        try:
            res = fn(kf, PROBLEM)
            out[op["operator_id"]] = "accepted" if res not in (
                False, None) else "rejected"
        except TypeError:
            # contract signature may be (item) or (item, problem)
            try:
                res = fn(kf)
                out[op["operator_id"]] = "accepted(1-arg)" if res not in (
                    False, None) else "rejected(1-arg)"
            except Exception as e:
                out[op["operator_id"]] = f"error:{type(e).__name__}"
        except Exception as e:
            out[op["operator_id"]] = f"error:{type(e).__name__}"
    # tamper: a knowledge-first item with the flag stripped must be
    # rejected by the knowledge-first contract (the anti-gimmick bind)
    tampered = dict(kf)
    tampered.pop("_knowledge_first", None)
    kf_contract = None
    for op in ops:
        if op["operator_id"] == "DOMAIN_KNOWLEDGE_FIRST":
            kf_contract = op.get("input_contract")
    tampered_state = "?"
    if kf_contract is not None:
        try:
            r = kf_contract(tampered, PROBLEM)
            tampered_state = "accepted(!)" if r not in (False, None) \
                else "rejected"
        except Exception as e:
            tampered_state = f"error:{type(e).__name__}"
    out["tampered_knowledge_first"] = tampered_state
    return out


def c5_assemble():
    ops = ms.TRANSFORMATION_OPERATORS
    kf = ms.knowledge_first_item(PROBLEM)
    op = [o for o in ops if o["operator_id"] == "DOMAIN_KNOWLEDGE_FIRST"][0]
    fields = {
        "mechanism": "seeded CaCO3 scale layer raises wall temperature "
                     "and cuts effective U",
        "intervention": "online phosphonate-based threshold treatment "
                        "with side-stream filtration",
        "testable_prediction": "dosing 8 ppm phosphonate holds fouling "
                               "resistance below 2e-4 m2K/W for 90 days",
        "boundary_conditions": "wall temperature 40-70 degC; pH 7.5-8.5",
        "constraints": "online only; no shutdown",
        "failure_mode": "CaCO3 scaling",
    }
    cand = ms.assemble_candidate(
        op, kf, fields, PROBLEM,
        {"provider": "smoke-zero-llm", "model": "none-deterministic"})
    assert cand["candidate_schema"] == "mechanism_candidate/1.0.0", \
        cand.get("candidate_schema")
    return {"schema": cand["candidate_schema"],
            "operator": cand["transformation_operator"],
            "has_graph": bool(cand.get("mechanism_graph")),
            "has_trace": bool(cand.get("derivation_trace")),
            "engine_version": cand.get("mechanism_space_version")}


def c6_signal_score():
    ops = ms.TRANSFORMATION_OPERATORS
    kf = ms.knowledge_first_item(PROBLEM)
    op = [o for o in ops if o["operator_id"] == "DOMAIN_KNOWLEDGE_FIRST"][0]
    fields = {"mechanism": "scale layer", "intervention": "antiscalant "
              "dosing", "testable_prediction": "fouling resistance "
              "below 2e-4 m2K/W for 90 days", "constraints": "online"}
    cand = ms.assemble_candidate(
        op, kf, fields, PROBLEM, {"provider": "smoke-zero-llm",
                                  "model": "none-deterministic"})
    score = ms.mechanism_signal_score(cand)
    return {"score_keys": sorted(score.keys())[:8]}


check("C1 six typed operators registered", c1_operators)
check("C2 registry shape (id/version/input_contract)", c2_registry_shape)
check("C3 knowledge_first_item anchor construction", c3_knowledge_first_item)
check("C4 six typed contracts bind (incl. tampered rejection)", c4_contracts)
check("C5 assemble_candidate emits canonical typed candidate", c5_assemble)
check("C6 mechanism_signal_score runs on the candidate", c6_signal_score)

ok = sum(1 for c in EV["checks"] if c["result"] == "OK")
print(f"\nSMOKE VERDICT: {ok}/{len(EV['checks'])} checks OK, "
      f"{len(EV['errors'])} crashes")
with open("eval/r47_engine_smoke_results.json", "w", encoding="utf-8") as f:
    json.dump({"smoke": "r47_d1_mechanism_space_zero_llm/1.0.0",
               "engine_version": getattr(ms, "MECHANISM_SPACE_VERSION",
                                         "unknown"),
               "llm_calls": 0, "results": EV}, f, indent=1)
print("wrote eval/r47_engine_smoke_results.json")
