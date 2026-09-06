"""routing.py — the deterministic solver router (R413, operator
directive V2 Phase 3).

THE OPERATOR'S CHAIN, VERBATIM:
    mechanism terminology
    -> physical phenomena
    -> required equations
    -> eligible solver domains
    -> registry lookup

"Do not allow an LLM to be the sole solver selector." — this module
contains ZERO LLM. It routes on the mechanism's own recorded fields
through the deterministic classifier (mechanism_physics) into the
coverage registry (phenomena -> equations -> solvers) and the
deterministic selection layer (selection.select_solvers).

FAIL-CLOSED OUTCOMES (typed, never prose):
    ROUTE_EXECUTION_ALLOWED     every evidenced phenomenon has a
                                measured-INSTALLED, validated solver
    ROUTE_NOT_SIMULATABLE       the mechanism's physics cannot be
                                simulated under the current registry
                                (untyped physics, uncovered phenomenon,
                                or an unregistered-domain request) —
                                MECHANISM_NOT_SIMULATABLE with the
                                domain and phenomena NAMED
    ROUTE_INCOMPLETE_SOLVER     every evidenced phenomenon has a
                                registered solver but >=1 is measured
                                NOT_INSTALLED in this environment —
                                an infrastructure fact, never a
                                scientific verdict (Art. LXI)

PROPOSAL GATE (Art. XVIII): an LLM may propose a classification via
verify_proposed_classification (mechanism_physics) — proposals are
verified against the deterministic evidence and can NEVER extend the
route: the router routes on deterministic evidence only. If the
deterministic layer cannot read the mechanism's physics, the route is
NOT_SIMULATABLE regardless of what any model proposes (fail-closed,
Art. IV).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from discovery_fabric.physics_stack.mechanism_physics import (
    classify_mechanism, verify_proposed_classification, UNKNOWN,
    MULTIPHYSICS,
)
from discovery_fabric.physics_stack.coverage import (
    load_coverage_registry,
)
from discovery_fabric.physics_stack.selection import select_solvers

ROUTE_EXECUTION_ALLOWED = "ROUTE_EXECUTION_ALLOWED"
ROUTE_NOT_SIMULATABLE = "ROUTE_NOT_SIMULATABLE"
ROUTE_INCOMPLETE_SOLVER = "ROUTE_INCOMPLETE_SOLVER"

#: the pipeline's typed failure states this router can emit (kept in
#: sync with pipeline.STAGE_FAILURE_STATES.SIMULATION_EXECUTION)
FAILURE_STATE_NOT_SIMULATABLE = "MECHANISM_NOT_SIMULATABLE"
FAILURE_STATE_NOT_INSTALLED = "INCOMPLETE_SOLVER_NOT_INSTALLED"


def route_mechanism(fields: Dict[str, Any]) -> Dict[str, Any]:
    """The deterministic route for one mechanism record.

    Returns the operator's chain as a machine-readable record with a
    sha256 (determinism: identical input -> byte-identical record,
    Art. LXII)."""
    cls = classify_mechanism(fields)
    registry = load_coverage_registry()
    entries = {e["phenomenon"]: e for e in registry["entries"]}

    phenomena: List[str] = sorted(cls["phenomenon_evidence"])
    domains = cls["strongly_evidenced"] or cls["weakly_evidenced"]
    domain = cls["domain"]

    # step 3: required equations (from the registry entries for the
    # evidenced phenomena — the DECLARED governing relations)
    required_equations: Dict[str, List[str]] = {}
    for ph in phenomena:
        e = entries.get(ph)
        if e is not None:
            required_equations[ph] = [
                eq.get("equation") for eq in
                (e.get("governing_equations") or [])
                if eq.get("equation")]

    # step 4: eligible solver domains (from the solver registry via
    # the selection layer's candidate scan)
    selection = select_solvers(phenomena)
    eligible_solver_domains = sorted({
        s["solver_id"] for s in selection["selections"]
    } | {
        a for s in selection["selections"] for a in s["alternates"]
    })

    # ---- the route verdict -------------------------------------------
    if domain == UNKNOWN or not domains:
        state = ROUTE_NOT_SIMULATABLE
        failure_state = FAILURE_STATE_NOT_SIMULATABLE
        reason = ("the mechanism's physics is unreadable by the "
                  "deterministic rules (no domain evidence in its own "
                  "recorded fields) — UNKNOWN physics is never forced "
                  "onto a neighboring domain (Art. IV/XXV)")
        missing = phenomena
    elif not phenomena:
        state = ROUTE_NOT_SIMULATABLE
        failure_state = FAILURE_STATE_NOT_SIMULATABLE
        reason = (f"domain evidence exists ({', '.join(domains)}) but "
                  "no phenomenon binds to a registry entry — the "
                  "physics is domain-typed but phenomenon-UNCOVERED "
                  "(the registry has no acoustic/chemical/optical/"
                  "soft-body phenomenon in this version; the coverage "
                  "matrix prices these gaps)")
        missing = []
    else:
        n_installed = sum(
            1 for s in selection["selections"]
            if s["state"] == "SELECTED")
        n_refused = sum(
            1 for s in selection["selections"]
            if s["state"] == "REFUSED_SOLVER_NOT_INSTALLED")
        if selection["execution_allowed"]:
            state = ROUTE_EXECUTION_ALLOWED
            failure_state = None
            reason = ("every evidenced phenomenon has a measured-"
                      "INSTALLED, validated solver")
        elif n_refused:
            state = ROUTE_INCOMPLETE_SOLVER
            failure_state = FAILURE_STATE_NOT_INSTALLED
            reason = (f"{n_refused} of {len(selection['selections'])} "
                      "evidenced phenomena have registered solvers "
                      "measured NOT_INSTALLED in this environment — "
                      "an infrastructure fact, never a scientific "
                      "verdict (Art. LXI)")
        else:
            state = ROUTE_NOT_SIMULATABLE
            failure_state = FAILURE_STATE_NOT_SIMULATABLE
            reason = ("one or more evidenced phenomena have NO "
                      "registered solver — MECHANISM_NOT_SIMULATABLE, "
                      "fail-closed")
        missing = [
            p for p in phenomena
            if any(r["phenomenon"] == p
                   and r["state"] in (
                       "REFUSED_PHENOMENON_NOT_COVERED",
                       "REFUSED_NO_SOLVER_REGISTERED",
                       "REFUSED_SOLVER_NOT_INSTALLED")
                   for r in selection["refusals"] + selection[
                       "selections"])]

    doc = {
        "route_state": state,
        "failure_state": failure_state,
        "reason": reason,
        "mechanism_physics_domain": domain,
        # step 1: mechanism terminology (the deterministic evidence)
        "terminology_evidence": {
            "strongly_evidenced": cls["strongly_evidenced"],
            "weakly_evidenced": cls["weakly_evidenced"],
            "domain_evidence": cls["domain_evidence"],
        },
        # step 2: physical phenomena (registry-bound)
        "phenomena": phenomena,
        "uncovered_or_missing_phenomena": missing,
        # step 3: required equations (declared, from the registry)
        "required_equations": required_equations,
        # step 4: eligible solver domains
        "eligible_solver_domains": eligible_solver_domains,
        # step 5: registry lookup (the deterministic selection record)
        "solver_selection": selection,
        "role_separation": {
            "proposer_role": "an LLM may PROPOSE classifications "
                             "(verified by mechanism_physics."
                             "verify_proposed_classification against "
                             "the deterministic evidence; proposals "
                             "can never EXTEND a route)",
            "router_role": "deterministic code (this module; zero LLM)",
            "llm_in_routing": False,
        },
    }
    doc["route_sha256"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return doc


def route_with_verified_proposal(fields: Dict[str, Any],
                                 proposal: Dict[str, Any]
                                 ) -> Dict[str, Any]:
    """Route a mechanism while RECORDING an LLM proposal's
    verification outcome (Art. XVIII gate).

    The route itself is ALWAYS the deterministic route — a verified
    proposal cannot extend it, and a rejected proposal cannot narrow
    it. The verification record travels alongside for audit.
    """
    route = route_mechanism(fields)
    route["proposal_verification"] = verify_proposed_classification(
        proposal, fields)
    return route
