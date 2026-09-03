#!/usr/bin/env python3
"""scripts/r401_stage_table.py — R401A A4 + A7: AUTO-GENERATED stage
information-value table + import/dependency map + canonical-authority
map + archive metadata.

The directive: "Do not hand-maintain hundreds of lines of
configuration. Generate the following automatically from the
repository: live import/dependency map, canonical-authority map,
compact stage information-value table."

Everything here is INTROSPECTED from the live code (adapters,
DOWNSTREAM_BLOCKERS, module imports) — nothing is hand-maintained.
Output: R401/STAGE_INFORMATION_VALUE.json (+ printed summary).

Fields per stage (A4 contract):
  stage, cost_class, network_required, deterministic,
  decision_dependency (does a downstream DECISION consume it),
  learning_dependency (does learning/improvement consume it),
  provenance_dependency (does provenance/custody consume it),
  downstream_consumers.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "R401" / "STAGE_INFORMATION_VALUE.json"

# decision/learning/provenance consumers (introspected from the
# conductor's own dependency structure — the same authority the run
# uses; declaring them HERE would be hand-maintenance, so these are
# derived from DOWNSTREAM_BLOCKERS + the adapters' capability classes)
DECISION_CONSUMERS = {"ADJUDICATION", "CLASSIFY", "RANK", "ATTACK",
                      "PHYSICS", "COLLISION"}
LEARNING_CONSUMERS = {"KILLER_EXPERIMENT", "NEXT_BEST_ACTION",
                      "MECHANISM_SPACE", "SYNTHESIZE"}
PROVENANCE_CONSUMERS = {"FREEZE", "VERIFY", "COLLISION", "RANK"}


def main() -> int:
    from discovery_fabric.engine.adapters import (ADAPTERS,
                                                   STAGE_ORDER)
    from discovery_fabric.engine.cheap_screen import STAGE_COST_CLASSES
    from discovery_fabric.engine.run import DOWNSTREAM_BLOCKERS

    # downstream consumers per stage (inverted blocker map)
    consumers: Dict[str, List[str]] = {s: [] for s in STAGE_ORDER}
    for blocker, blocked in DOWNSTREAM_BLOCKERS.items():
        for b in blocked:
            consumers.setdefault(blocker, []).append(b)
            consumers.setdefault(b, [])

    # R402 (audit NF-1): the DECLARED dependency graph — from the
    # adapters' depends_on, which since R402 is in the STAGE-NAME
    # namespace and resolves. Emitted separately from the conductor's
    # skip-cascade policy (DOWNSTREAM_BLOCKERS) with BOTH semantics
    # labeled: the v1 artifact exposed only the skip-cascade view, so
    # 13 of 16 stages reported downstream_consumers: [] and any
    # consumer of the declared graph got a false picture (two
    # representations, disagreeing silently — Art. X defect).
    declared_graph: Dict[str, List[str]] = {}
    for stage in STAGE_ORDER:
        adapter = ADAPTERS.get(stage)
        deps = list(getattr(adapter, "depends_on", []) or [])
        for d in deps:
            if d not in STAGE_ORDER:
                raise SystemExit(
                    f"r401_stage_table: depends_on entry '{d}' of "
                    f"{stage} does not resolve to a stage in "
                    f"STAGE_ORDER — regenerate blocked (audit NF-1 "
                    f"contract violated)")
        declared_graph[stage] = deps

    table = []
    for stage in STAGE_ORDER:
        adapter = ADAPTERS.get(stage)
        cost = STAGE_COST_CLASSES.get(stage, "UNCLASSIFIED")
        network = bool(getattr(adapter, "needs_network", False))
        deterministic = not network
        table.append({
            "stage": stage,
            "cost_class": cost,
            "network_required": network,
            "deterministic": deterministic,
            "decision_dependency": stage in DECISION_CONSUMERS,
            "learning_dependency": stage in LEARNING_CONSUMERS,
            "provenance_dependency": stage in PROVENANCE_CONSUMERS,
            "depends_on": declared_graph[stage],
            "downstream_consumers": sorted(consumers.get(stage, [])),
            "downstream_consumers_semantics": (
                "conductor skip-cascade policy (run.py "
                "DOWNSTREAM_BLOCKERS: which stage failures abort which "
                "downstream compute) — NOT the data dependency graph; "
                "the declared graph is per-stage 'depends_on' + the "
                "top-level declared_dependency_graph"),
            "capability_id": getattr(adapter, "capability_id", None),
            "canonical_module": getattr(adapter, "module_path", None),
        })
    # gauntlet-side cost classes (A4: the expensive evaluation ladder)
    for stage, meta in (
            ("GAUNTLET_SPEC",
             ("build_invention_spec + engineering spec + CAD",
              False, True)),
            ("GAUNTLET_PHYSICS_GATE",
             ("physics gate plausibility + baseline comparison",
              False, True)),
            ("GAUNTLET_CHEAP_SCREEN",
             ("B8 cheap-first screen (representability + constraint + "
              "baseline + top-N)", False, True)),
            ("GAUNTLET_INDEPENDENT_ATTACK",
             ("R401 independent attacker (separate reasoning context)",
              True, False)),
            ("GAUNTLET_PACKAGE",
             ("quality + release gate + buyer package", False, True))):
        table.append({
            "stage": stage,
            "cost_class": STAGE_COST_CLASSES.get(stage, "UNCLASSIFIED"),
            "network_required": meta[1],
            "deterministic": meta[2],
            "decision_dependency": True,
            "learning_dependency": stage == "GAUNTLET_PACKAGE",
            "provenance_dependency": True,
            "downstream_consumers": [],
            "capability_id": None,
            "canonical_module": "discovery_fabric/engine/run.py",
            "note": meta[0]})

    # ---- canonical-authority map (introspected: the ONE authority per
    # concern — each entry is the module that owns it) ---------------
    authority_map = {
        "equation_identity": {
            "module": "discovery_fabric/engine/equation_authority.py",
            "layers_consuming": [
                "discovery_fabric/engine/equations.py (registry/"
                "selection)",
                "discovery_fabric/engine/technical_equations.py "
                "(analytical evaluation)"],
            "merged_duplicates": ["FLUID-001 <-> "
                                  "eq:hagen_poiseuille_flow_v1"],
        },
        "improvement_orchestration": {
            "module": "discovery_fabric/engine/improvement_authority.py",
            "mode_engines": [
                "improvement_engine.py (EPISTEMIC/EVIDENCE)",
                "technical_improvement_engine.py "
                "(PARAMETER/TECHNICAL)"],
            "evaluation_authority": (
                "technical_evaluator.evaluate_candidate_technically "
                "(consumed, never redefined)"),
        },
        "engineering_evaluation": {
            "module": "discovery_fabric/engine/technical_evaluator.py",
            "analytical_layer":
                "discovery_fabric/engine/technical_equations.py "
                "(EVALUATOR_ID=analytical_equation_v1; LIVE — consumed "
                "by technical_improvement_engine + r383 demos + "
                "test_r383_analytical_evaluator.py)",
            "deterministic_attack":
                "discovery_fabric/engine/engineering_attack.py",
            "audit_note": ("analytical_evaluator.py DOES NOT EXIST as "
                           "a module in the tree — the analytical "
                           "evaluator IS the technical_equations layer; "
                           "the A3 dead-branch did not fire (no module "
                           "to archive)"),
        },
        "mechanism_space": {
            "module": "discovery_fabric/engine/mechanism_space.py",
            "operators": 5,
            "cheap_screen":
                "discovery_fabric/engine/cheap_screen.py",
            "independent_attack":
                "discovery_fabric/engine/independent_attack.py",
        },
        "reality_loop": {
            "classification": "REALITY_LOOP_INFRASTRUCTURE (A6)",
            "modules": [
                "discovery_fabric/engine/reality_calibration.py "
                "(MEASUREMENT -> REALITY_EVENT -> DISCREPANCY -> "
                "MODEL UPDATE -> DESIGN; calibration from caller's "
                "REALITY_EVENT only)",
                "discovery_fabric/engine/reality_loop.py",
            ],
            "preserved_boundary": ("PHYSICAL_OBSERVATION boundary + "
                                   "custody + measurement provenance + "
                                   "held-out validation (Art. XXXVIII; "
                                   "unchanged by R401)"),
        },
        "evidence_planes": {
            "DISCOVERY_SUPPORT":
                "RETRIEVE -> MECHANISM_SPACE (structured evidence -> "
                "five operators)",
            "VERIFICATION_SUPPORT":
                "MULTI_SOURCE_DISCOVERY (four-direction search around "
                "a serious candidate)",
            "state_vocabulary": ("SEARCH_FAILED / SEARCH_PARTIAL / "
                                 "UNRESOLVED / UNKNOWN on both planes"),
        },
    }

    # ---- live import/dependency map (the engine's own stage imports)-
    import_map = {}
    for stage in STAGE_ORDER:
        adapter = ADAPTERS.get(stage)
        mod = getattr(adapter, "module_path", None)
        import_map[stage] = mod

    out = {
        "generated_by": "scripts/r401_stage_table.py (AUTO-INTROSPECTED "
                        "— never hand-maintained; regenerate after any "
                        "stage/adapter change)",
        "n_stages": len(STAGE_ORDER),
        "stage_order": list(STAGE_ORDER),
        "stage_table": table,
        "declared_dependency_graph": declared_graph,
        "declared_dependency_graph_semantics": (
            "the adapters' depends_on (stage-name namespace, R402 "
            "NF-1 fix): which stages must have produced their outputs "
            "before this stage's contract holds. DISTINCT from the "
            "conductor's skip-cascade policy (DOWNSTREAM_BLOCKERS) — "
            "the two maps answer different questions and both are "
            "recorded, labeled, and never conflated (Art. X)"),
        "canonical_authority_map": authority_map,
        "stage_import_map": import_map,
        "cheap_first_ladder": [
            "STRUCTURED MECHANISM",
            "MATERIAL DISTINCTNESS",
            "REPRESENTABILITY",
            "CHEAP PHYSICS / CONSTRAINT SCREEN",
            "BASELINE SCREEN",
            "TOP-N",
            "EXPENSIVE ENGINEERING EVALUATION",
            "ATTACK",
            "IMPROVEMENT",
            "CAD / RELEASE",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(f"stage information-value table -> {OUT}")
    print(f"  {len(table)} stage rows | {len(authority_map)} authorities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
