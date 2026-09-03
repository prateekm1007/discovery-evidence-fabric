"""R401 Phase 12 — held-out end-to-end proof (sandbox-executable slice).

Held-out problem: EV high-voltage connector contact fretting corrosion —
NOT one of the 8 benchmark fixture domains (wind/rails/inverter/hemo/
cgm/pouch/syrup/glass), so nothing here was tuned on it.

Pipeline: live multi-source retrieval (a2.retrieve, R401 step 1) ->
structured evidence records -> seed mechanism (auditor-authored V0,
provenance-stamped) -> ALL FIVE operators -> operator fidelity gate ->
material distinctness -> mechanism-level evidence verification ->
downstream routing decision.

HONESTY RULES (Constitution): engine CAD/physics solvers are NOT wired
to arbitrary new domains in this sandbox; the routing decision states
CAD_ELIGIBLE / MECHANISM_NOT_SIMULATABLE / REJECTED_* as a ROUTING
record only — actual CAD/physics execution is INCOMPLETE until the
deployed engine runs it. Nothing in this module claims a scientific
result; it produces a decision-ready dossier with full provenance.
"""
from __future__ import annotations
import json
from typing import Any, Dict, List

from .schema import mechanism_candidate, evidence_record, now_utc
from .operators import apply_operator, operator_fidelity, OperatorError
from .distinctness import structural_dedup
from .verification import verify_mechanism_evidence

HELDOUT_PROBLEM = {
    "device": "EV high-voltage charging connector",
    "failure_mode": "CONTACT_RESISTANCE_RISE_FROM_FRETTING",
    "statement": ("Why do EV high-voltage charging connector contacts develop "
                  "fretting corrosion and rising contact resistance after "
                  "thousands of plug cycles with vehicle vibration?"),
}

SEED_GRAPH = {
    "nodes": [
        {"id": "n1", "type": "COMPONENT", "label": "electrical contact interface"},
        {"id": "n2", "type": "PROCESS", "label": "micro-slip at contact spots under vibration"},
        {"id": "n3", "type": "PHENOMENON", "label": "oxide film disruption"},
        {"id": "n4", "type": "PROCESS", "label": "metal-to-metal adhesion and transfer"},
        {"id": "n5", "type": "PHENOMENON", "label": "third-body wear debris accumulation"},
        {"id": "n6", "type": "PHENOMENON", "label": "contact resistance rise"},
        {"id": "n7", "type": "GEOMETRY", "label": "flat cylindrical pad contact"},
    ],
    "edges": [
        {"src": "n1", "dst": "n2", "rel": "ENABLES"},
        {"src": "n7", "dst": "n2", "rel": "ENABLES"},
        {"src": "n2", "dst": "n3", "rel": "CAUSES"},
        {"src": "n3", "dst": "n4", "rel": "CAUSES"},
        {"src": "n4", "dst": "n5", "rel": "CAUSES"},
        {"src": "n5", "dst": "n6", "rel": "CAUSES"},
    ],
}


def seed_candidate() -> Dict[str, Any]:
    return mechanism_candidate(
        id="M1_seed", problem=HELDOUT_PROBLEM["statement"],
        system=HELDOUT_PROBLEM["device"],
        failure_mode=HELDOUT_PROBLEM["failure_mode"],
        mechanism_graph=json.loads(json.dumps(SEED_GRAPH)),
        evidence_bundle=[],
        constraint_set={"environment": "in-vehicle vibration + charging duty cycles"},
        boundary_conditions={"vibration": "5-20 um relative micro-slip",
                             "current": "high DC fast-charge current"},
        predicted_effect="contact resistance rises monotonically with plug cycles and vibration exposure",
        known_failure_modes=["fretting corrosion", "hot spots at debris-rich spots"],
        novel_design_variable=None,
        testable_prediction="Contact resistance increase correlates with debris accumulation depth measured by cross-sectioning after cyclic vibration tests",
        transformation_operator=None,
        derivation_trace={"operator": "SEED", "at": now_utc(),
                          "provenance_note": "auditor-authored V0 seed mechanism; standard fretting-chain textbook account"},
        provenance={"author": "auditor_seed_v0", "created": now_utc()},
        status=None,
    )


def operator_calls(m1: Dict[str, Any]) -> List[tuple]:
    return [
        ("DIRECT_TRANSFER", m1,
         {"target_system": "industrial slip-ring power joint",
          "binding": {"electrical contact interface": "slip-ring brush interface",
                      "flat cylindrical pad contact": "brush pad geometry"}}),
        ("CROSS_DOMAIN_ANALOGY", m1,
         {"mapping": {"metal-to-metal adhesion and transfer": "rock asperity adhesion and gouge formation",
                      "third-body wear debris accumulation": "glacial till accumulation",
                      "electrical contact interface": "glacier bed interface"},
          "target_domain": "glacial geology"}),
        ("GEOMETRIC_TRANSFORMATION", m1,
         {"geometry_node": "n7",
          "new_label": "micro-dimpled patterned contact pad",
          "new_geometry_field": "laser-textured dimple array, 50 um depth, 20% area fraction"}),
        ("BOUNDARY_CONDITION_CHANGE", m1,
         {"new_bc": {"vibration": "preloaded contact, <1 um relative slip (full-stick regime)",
                     "current": "high DC fast-charge current"},
          "new_predicted_effect": "contact resistance stays stable: fretting chain never initiates in the full-stick regime"}),
        ("FAILURE_PATH_INVERSION", m1,
         {"edge_to_invert": ("n5", "n6"),
          "design_variable": "engineered solid-lubricant tribofilm (intentional third-body layer)",
          "new_predicted_effect": "designed tribofilm traps debris and lubricates the interface, keeping contact resistance low",
          "new_purpose": "debris accumulation repurposed from failure driver to maintained protective layer"}),
    ]


def to_evidence_records(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert live-retrieved a2 evidence items into structured records.
    V0: claim/mechanism filled from title+abstract head — every record
    carries the full retrieval provenance and content hash."""
    out = []
    for it in items[:8]:
        mech_head = (it.get("abstract") or "")[:300]
        out.append(evidence_record(
            source=it["source_id"],
            claim=it.get("title", ""),
            observed_effect=it.get("title", ""),
            system=HELDOUT_PROBLEM["device"],
            intervention=None,
            mechanism=mech_head,
            boundary_conditions=None,
            constraints=None,
            failure_mode=HELDOUT_PROBLEM["failure_mode"],
            confidence=None,
            provenance={"provider": it.get("source"),
                        "retrieval_method": it.get("retrieval_method"),
                        "content_hash": it.get("content_hash"),
                        "retrieved_at": it.get("retrieval_timestamp")}))
    return out


def route(cand: Dict[str, Any], verification: Dict[str, Any]) -> Dict[str, Any]:
    """Downstream routing decision — a ROUTING record, not a science claim."""
    if verification["bundle_verdict"] == "CONTRADICTED":
        return {"route": "REJECTED_EVIDENCE_CONTRADICTION",
                "cad": "NOT_ATTEMPTED", "physics": "NOT_ATTEMPTED"}
    if verification["bundle_verdict"] in ("SUPPORTED", "PARTIALLY_SUPPORTED"):
        return {"route": "CAD_ELIGIBLE",
                "cad": "INCOMPLETE (engine CAD not runnable on arbitrary "
                       "domains in this sandbox — requires deployed engine)",
                "physics": "MECHANISM_NOT_SIMULATABLE (no fretting/wear solver "
                           "domain in the engine; honest terminal per Phase 9)"}
    return {"route": "PENDING_EVIDENCE (phenomenon-level only)",
            "cad": "NOT_ATTEMPTED", "physics": "NOT_ATTEMPTED"}


def run(live_evidence_items: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    m1 = seed_candidate()
    evidence = to_evidence_records(live_evidence_items or [])
    results = {"heldout_problem": HELDOUT_PROBLEM, "evidence_n": len(evidence),
               "operators": {}, "distinctness": None,
               "verification": {}, "routing": {}, "class_state": None}
    candidates = [m1]
    for op, base, params in operator_calls(m1):
        try:
            m2 = apply_operator(op, base, **params)
            results["operators"][op] = {
                "produced": m2["id"], "fidelity": "PASS",
                "proofs": m2["operator_fidelity"]["proofs"],
                "changed_fields": m2["derivation_trace"]["changed_fields"]}
            candidates.append(m2)
        except OperatorError as e:
            results["operators"][op] = {"produced": None, "fidelity": "FAIL",
                                        "reason": str(e)}
    dedup = structural_dedup(candidates)
    results["distinctness"] = {"stats": dedup["stats"],
                               "ledger": dedup["ledger"]}
    for c in dedup["kept"]:
        v = verify_mechanism_evidence(evidence, c)
        results["verification"][c["id"]] = v["bundle_verdict"] + (
            f" (counts={v['counts']})")
        results["routing"][c["id"]] = route(c, v)
    n_ops_pass = sum(1 for r in results["operators"].values()
                     if r.get("fidelity") == "PASS")
    n_distinct = dedup["stats"]["kept"]
    results["class_state"] = {
        "operators_passing_behavior_test": f"{n_ops_pass}/5",
        "materially_distinct_mechanisms": n_distinct,
        "phase9_downstream": "INCOMPLETE in sandbox (CAD/physics execution "
                             "requires the deployed engine; routing recorded honestly)",
        "classification": "STRUCTURALLY_READY" if (n_ops_pass == 5 and
                                                   n_distinct >= 5) else "NOT_READY"}
    return results
