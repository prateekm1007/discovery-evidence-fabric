"""opportunity.py — the Physics Gap Opportunity Score (R413, operator
directive V2 Phase 5, "the one major improvement I want beyond the
auditor").

For every missing solver domain (priced per CANDIDATE SOLVER — the
choice the operator makes is a tool, not a domain), six factors:

    dead candidates unlocked
    mechanism diversity
    expected information gain
    implementation cost
    validation maturity
    automation feasibility

SCORE (the operator's formula shape, all six factors):
    score = (U x G x D x V x A) / C
where U = weighted dead candidates unlocked, G = expected information
gain, D = mechanism diversity, V = validation maturity, A = automation
feasibility (higher = better), C = implementation cost (lower = 
better). The simple operator form (U x G / C) is also reported.

PRE-REGISTRATION DISCIPLINE (Art. XXVII/LIX): every factor scale,
its values per solver, and the formula are DECLARED in this module
BEFORE the score is computed from the coverage matrix. The
cost/maturity/automation tables are ENVIRONMENT and DOCUMENTATION
facts (measured probes, pip dry-run, official solver interfaces) —
not corpus-derived — so they cannot be tuned toward a desired
answer. The unlock/diversity/information-gain factors are computed
from the frozen matrix (PHYSICS_COVERAGE_MATRIX_V1.json).

The selection rule (pre-registered): the top-scoring solver is the
machine's recommendation and becomes the Phase 6 wiring target; the
operator's directive V2 already authorized installing and wiring
exactly ONE solver chosen this way.
"""
from __future__ import annotations

from typing import Any, Dict, List

from discovery_fabric.physics_stack.solver_registry import SOLVER_REGISTRY

#: simulation-decidable kill surfaces (the objections a solver can
#: actually decide): equation validity, boundary-condition/regime
#: validity, and predicted-effect magnitude. mechanism/evidence/
#: prior_art/experiment_design/buyer surfaces are NOT solver-decidable
#: (declared before computation).
SIMULATION_DECIDABLE_SURFACES = ("equations", "boundary_conditions",
                                 "predicted_effect")

#: ---------------------------------------------------------------------------
#: PRE-REGISTERED PER-SOLVER FACTORS (cost / validation maturity /
#: automation feasibility). Class: MODEL_DERIVED + MEASURED components,
#: each with justification (Art. XXVII). Scales: cost components sum
#: (lower = cheaper, 3..9); maturity and automation 1..3 (3 = best).
#: ---------------------------------------------------------------------------
#: install mechanism IN THIS ENVIRONMENT (measured: pip --dry-run
#: resolves pure-Python/wheel packages; system binaries are absent per
#: the availability probes): 1 = pure-Python pip; 2 = pip wheel with
#: native binaries; 3 = system binary / external package manager.
SOLVER_INSTALL_COST = {
    "sfepy": (1, "pure-Python pip package (numpy/scipy-based; "
                 "measured resolvable by pip --dry-run in this "
                 "environment)"),
    "openmdao": (1, "pure-Python pip package"),
    "mujoco": (2, "pip wheel shipping native binaries "
                  "(deepmind mujoco wheels)"),
    "project_chrono": (2, "pip wheel shipping native binaries "
                          "(pychrono)"),
    "fenicsx": (2, "dolfinx wheels/packages with native PETSc stack"),
    "openfoam": (3, "system package (apt/spack); no binary on PATH "
                    "(MEASURED by the availability probe)"),
    "elmer": (3, "system package; no binary on PATH (MEASURED)"),
    "openems": (3, "system package + (typically) Octave/MATLAB "
                   "driver; no binary on PATH (MEASURED)"),
    "sofa": (3, "system package / custom build; runSofa absent "
                "(MEASURED)"),
}

#: headless automation interface (official, documentation-declared):
#: 1 = native Python API; 2 = CLI case files (orchestrable but file-
#: bound); 3 = GUI-centric workflow.
SOLVER_AUTOMATION_COST = {
    "sfepy": (1, "native Python API + problem files; fully "
                 "scriptable headless"),
    "openmdao": (1, "native Python API"),
    "mujoco": (1, "native Python API (mujoco bindings)"),
    "project_chrono": (1, "pychrono Python API"),
    "fenicsx": (1, "native Python API"),
    "openfoam": (2, "case-directory CLI (blockMesh/simpleFoam "
                    "processes; file-bound orchestration)"),
    "elmer": (2, "sif case files + ElmerSolver CLI"),
    "openems": (3, "CSX XML + typically Octave/MATLAB driver — "
                   "GUI-adjacent workflow"),
    "sofa": (2, "runSofa CLI + scene files (Python plugin optional)"),
}

#: verification/validation material shipped with the solver that is
#: replayable headlessly IN THIS ENVIRONMENT once installed
#: (documentation-declared): 1 = shipped testsuite/examples with
#: analytical/reference solutions; 2 = tutorial/validation cases
#: requiring setup; 3 = none/unclear.
SOLVER_VERIFICATION_SETUP_COST = {
    "sfepy": (1, "ships a testsuite + examples with analytical "
                 "solutions (linear elasticity, Laplace/heat "
                 "verification problems) — replayable headless"),
    "openmdao": (1, "ships its own test suite; but an optimization "
                    "layer produces no physics evidence (not a "
                    "solver choice, kept for completeness)"),
    "mujoco": (1, "ships analytical/pendulum-style regression tests"),
    "project_chrono": (2, "ships unit/regression tests and demos "
                          "(C++/Python)"),
    "fenicsx": (2, "MMS conventions documented; verification problems "
                   "require authoring"),
    "openfoam": (2, "tutorial validation cases require per-case "
                    "setup (meshing, fields, schemes)"),
    "elmer": (2, "ships verification cases requiring sif setup"),
    "openems": (2, "ships validation examples (antennas/waveguides) "
                   "requiring setup"),
    "sofa": (2, "scene-level regression tests requiring scene setup"),
}

#: validation maturity (inverted to 1..3, higher = more mature):
#: 3 = shipped analytical/reference verification replayable headless
#: NOW in this environment class; 2 = strong shipped material but
#: setup-heavy or install-blocked; 1 = weak/unclear shipped material.
def _maturity(solver_id: str) -> int:
    m = {  # justification carried in the artifact
        "sfepy": 3, "mujoco": 3, "openmdao": 2, "project_chrono": 2,
        "fenicsx": 2, "openfoam": 2, "elmer": 2, "openems": 2,
        "sofa": 2,
    }
    return m[solver_id]


#: automation feasibility (inverted to 1..3, higher = better):
def _automation(solver_id: str) -> int:
    return 4 - SOLVER_AUTOMATION_COST[solver_id][0]


def solver_factor_table() -> List[Dict[str, Any]]:
    """The pre-registered per-solver factor table with every value and
    its justification (Art. XXVII — no invented numbers)."""
    out = []
    for sid in sorted(SOLVER_INSTALL_COST):
        install, install_why = SOLVER_INSTALL_COST[sid]
        autom, autom_why = SOLVER_AUTOMATION_COST[sid]
        verif, verif_why = SOLVER_VERIFICATION_SETUP_COST[sid]
        out.append({
            "solver_id": sid,
            "implementation_cost": {
                "value": install + autom + verif,
                "components": {
                    "install_mechanism": install,
                    "automation_interface": autom,
                    "verification_setup": verif,
                },
                "justification": {
                    "install_mechanism": install_why,
                    "automation_interface": autom_why,
                    "verification_setup": verif_why,
                },
                "class": "MODEL_DERIVED over MEASURED components "
                         "(availability probes, pip dry-run, official "
                         "interface documentation)",
                "scale": "lower = cheaper (3..9)",
            },
            "validation_maturity": {
                "value": _maturity(sid),
                "class": "MODEL_DERIVED / DOC_DECLARED — shipped "
                         "verification material replayable headless",
                "scale": "1..3, higher = more mature",
            },
            "automation_feasibility": {
                "value": _automation(sid),
                "class": "MODEL_DERIVED / DOC_DECLARED — official "
                         "headless interface",
                "scale": "1..3, higher = better",
            },
        })
    return out


def _coverage_weight(record: Dict[str, Any],
                     solver_phenomena: set) -> float:
    """Fraction of the mechanism's evidenced phenomena covered by the
    solver's registered phenomena (0 if no evidence)."""
    ev = record.get("phenomena_evidenced") or []
    if not ev:
        return 0.0
    covered = sum(1 for p in ev if p in solver_phenomena)
    return covered / len(ev)


def compute_opportunity_score(matrix: Dict[str, Any],
                              installed_exclude: Any = "LIVE"
                              ) -> Dict[str, Any]:
    """Compute the six-factor score per not-installed candidate
    solver from the FROZEN coverage matrix. Deterministic.

    installed_exclude: which solvers to EXCLUDE from the candidate
    table (they are not 'missing'):
      - "LIVE" (default): read the registry's CURRENT measured
        state — the forward-looking 'which solver is missing NEXT'
        query (post-wiring this excludes sfepy: correct behavior,
        the machine's question moves on);
      - an explicit set: the DECISION-TIME state. The Phase 5
        decision artifact is built with the pre-installation set
        (only hydraulic_network_1d) so the frozen artifact records
        the decision AS MADE (sfepy was then the missing top
        scorer) — a live re-run must never silently rewrite a
        frozen decision (Art. XI).
    """
    if installed_exclude == "LIVE":
        exclude = {r["solver_id"] for r in SOLVER_REGISTRY
                   if r["availability"]["state"] == "INSTALLED"}
    else:
        exclude = set(installed_exclude)
    per_candidate = matrix["per_candidate"]
    records = []
    for rec in SOLVER_REGISTRY:
        sid = rec["solver_id"]
        if sid not in SOLVER_INSTALL_COST:
            continue  # installed (hydraulic V0) or non-solver layers
        if sid in exclude:
            continue  # not missing (decision-time or live state)
        phenomena = set(rec["phenomenon_classes"])
        if not phenomena:
            continue  # visualization/orchestration layers are not
            # solver choices (Blender is Phase 7, not Phase 5)

        # U: weighted dead candidates unlocked
        u_all = 0.0
        u_adj = 0.0
        full_all = 0
        full_adj = 0
        # D: mechanism diversity (distinct pain classes among
        # unlockable mechanisms)
        pain_classes = set()
        domain_ids = set()
        # G: expected information gain (adjudicated physics-relevant
        # deaths only — the only place kill surfaces are recorded)
        g_total = 0.0
        g_detail = []
        for c in per_candidate:
            w = _coverage_weight(c, phenomena)
            if w <= 0.0:
                continue
            u_all += w
            pain_classes.add(c.get("pain_class"))
            domain_ids.add(c.get("domain_id"))
            if w == 1.0:
                full_all += 1
            death = c.get("death")
            if death and c.get("unlock_attribution") == \
                    "PHYSICS_RELEVANT":
                u_adj += w
                if w == 1.0:
                    full_adj += 1
                decidable = [s for s in
                             (death.get("kill_surfaces") or [])
                             if s in SIMULATION_DECIDABLE_SURFACES]
                if decidable:
                    g_total += len(decidable) * w
                    g_detail.append({
                        "candidate_id": c["candidate_id"],
                        "decidable_surfaces": decidable,
                        "coverage_weight": round(w, 4),
                    })

        # factor lookups (pre-registered tables)
        factors = next(f for f in solver_factor_table()
                       if f["solver_id"] == sid)
        cost = factors["implementation_cost"]["value"]
        maturity = factors["validation_maturity"]["value"]
        automation = factors["automation_feasibility"]["value"]
        diversity = len(pain_classes)

        score = (u_all * g_total * diversity * maturity * automation
                 ) / cost
        operator_simple = (u_all * g_total) / cost

        records.append({
            "solver_id": sid,
            "registered_phenomena": sorted(phenomena),
            "dead_candidates_unlocked": {
                "weighted_all_dead": round(u_all, 2),
                "full_unlock_all_dead": full_all,
                "weighted_adjudicated_physics_relevant": round(u_adj, 2),
                "full_unlock_adjudicated": full_adj,
                "basis": "weighted = fraction of each mechanism's "
                         "evidenced phenomena covered by this "
                         "solver's registered phenomena (partial "
                         "credit: multiphysics mechanisms need "
                         "combinations); full = 100% coverage",
            },
            "mechanism_diversity": {
                "distinct_pain_classes": diversity,
                "distinct_industry_domains": len(domain_ids),
                "class": "MODEL_DERIVED — Art. XLVIII discipline: "
                         "families (pain classes), not candidate "
                         "counts",
            },
            "expected_information_gain": {
                "value": round(g_total, 2),
                "basis": "adjudicated physics-relevant deaths only "
                         "(the only population with recorded kill "
                         "surfaces): simulation-DECIDABLE surfaces "
                         "(equations, boundary_conditions, "
                         "predicted_effect) x coverage weight; "
                         "mechanisms without kill-surface records "
                         "contribute 0 — unknown stays unknown "
                         "(Art. XXV)",
                "detail": g_detail,
            },
            "implementation_cost": factors["implementation_cost"],
            "validation_maturity": factors["validation_maturity"],
            "automation_feasibility":
                factors["automation_feasibility"],
            "score": round(score, 2),
            "operator_simple_score_UxG_div_C": round(
                operator_simple, 2),
        })

    records.sort(key=lambda r: (-r["score"], r["solver_id"]))
    top = records[0] if records else None
    return {
        "records": records,
        "selected_solver": None if top is None else {
            "solver_id": top["solver_id"],
            "score": top["score"],
            "selection_rule": "top score under the pre-registered "
                              "formula (U x G x D x V x A) / C; the "
                              "operator's directive V2 pre-authorized "
                              "installing and wiring exactly ONE "
                              "solver chosen this way (Phase 6 target)",
            "runner_up": None if len(records) < 2 else {
                "solver_id": records[1]["solver_id"],
                "score": records[1]["score"],
            },
        },
        "formula": {
            "score": "(U x G x D x V x A) / C",
            "operator_simple": "(U x G) / C  (the directive's own "
                               "shape: candidate unlock x expected "
                               "information gain / integration cost)",
            "factors": {
                "U": "weighted dead candidates unlocked (all-dead "
                     "population; adjudicated subset reported "
                     "alongside)",
                "G": "expected information gain (adjudicated "
                     "physics-relevant, simulation-decidable kill "
                     "surfaces x coverage)",
                "D": "mechanism diversity (distinct pain classes)",
                "V": "validation maturity (1..3)",
                "A": "automation feasibility (1..3)",
                "C": "implementation cost (3..9, lower = cheaper)",
            },
        },
        "pre_registration_note": "factor tables (cost/maturity/"
                                 "automation) are environment- and "
                                 "documentation-derived, declared in "
                                 "opportunity.py BEFORE the matrix "
                                 "numbers were read; the formula is "
                                 "the operator's directive shape; no "
                                 "factor was revised after any score "
                                 "was computed (Art. XXVII/LIX)",
    }
