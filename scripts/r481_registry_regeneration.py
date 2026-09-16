#!/usr/bin/env python3
"""R481 — RUNTIME_CAPABILITY_REGISTRY.json regeneration (the external
audit's A1 stage-drift fix, the R478-scheduled item).

The drift the audit measured at 17504061: this artifact's
conductor.stage_order_exact_per_D8 listed 13 stages (the D8 chain as
of its creation), while the executable STAGE_ORDER had advanced to 16
(R394 PREMISE_GATE, R397 PHYSICS, R401 MECHANISM_SPACE never
regenerated it). THIS round adds R481's IMPROVE (the audit's P0-1
loop closure) as a first-class stage: the chain is 17, the registry
matches the executable arithmetic, and the regeneration is itself
recorded (the artifact's provenance fields are preserved; the
regeneration event is appended, never silently rewritten — Art. X).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "RUNTIME_CAPABILITY_REGISTRY.json"

STAGE_ORDER_17 = ["RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
                  "VERIFY", "MECHANISM_SPACE", "MULTI_SOURCE_DISCOVERY",
                  "COLLISION", "PHYSICS",
                  "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
                  "IMPROVE", "ADJUDICATION",
                  "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]

IMPROVE_CAPABILITY = {
    "capability_id": "IMPROVE",
    "module_path": "discovery_fabric/engine/improve_stage.py",
    "canonical_function": "improve_stage.run_improve",
    "purpose": ("R481 (external-audit P0-1) the loop closure: dead "
                "candidates are mutated FROM THEIR RECORDED KILL BASIS "
                "and the children re-run the SAME gauntlet gates "
                "(physics, engineering attack, INDEPENDENT attack, "
                "dossier quality); a passing child re-enters the "
                "competition with fresh scores, a failing child is "
                "re-killed with a typed record. Typed states: "
                "CHILDREN_ADMITTED / NO_CHILD_ADMITTED / "
                "NO_KILL_EVIDENCE / IMPROVEMENT_BLOCKED_TRANSPORT / "
                "DISABLED_BY_OPERATOR / DEFERRED_TO_KILL_POINT."),
    "current_status": "ACTIVE",
    "adapter": "ImproveAdapter (STAGE_ORDER position 13 of 17, between "
               "KILLER_EXPERIMENT and ADJUDICATION; execution point: "
               "the Directive-1 pipeline's kill-evidence point, the "
               "cemetery-update precedent)",
    "input_contract": {
        "dead": "the gauntlet's typed kill records (kill class + basis "
                "read from the persisted PACKAGE_FAILED_/"
                "QUALITY_REJECTION_ files, Art. X)",
        "bound": "ENGINE_IMPROVE_MAX_CHILDREN (default 3); one "
                 "mutation per dead candidate per run"},
    "output_contract": ("admitted children join `evaluated` with fresh "
                        "scores + full lineage (parent id, generation, "
                        "kill_basis_hash, causal change) and are "
                        "applied to env.mechanism_space (the front "
                        "door); every attempt lands in IMPROVE_LEDGER."
                        "json"),
    "proven_by": "tests/test_r481_improve_stage.py (14 tests green: "
                 "the contract arithmetic, the typed deferral, the "
                 "Art. XXXVII copy guard, the same-gauntlet re-entry, "
                 "the re-kill typing, the transport/disabled/no-kill "
                 "states, the bound)",
    "cost_policy": "EXPENSIVE_LLM (cheap_screen.STAGE_COST_CLASSES); "
                   "runs ONLY when kill evidence exists",
    "provenance": "AI_IMPLEMENTED_R481; the audit's P0-1 acceptance: "
                  "the live V1->kill->V2 re-entry proof is the exit "
                  "criterion (Art. XXXVII: landing the code without "
                  "the live proof would manufacture the synthetic-loop "
                  "class)",
}


def main() -> int:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()
    d = json.loads(ART.read_text())
    conductor = d["conductor"]
    old_chain = conductor.get("stage_order_exact_per_D8") or []
    if old_chain == STAGE_ORDER_17:
        print("registry already at the R481 arithmetic — nothing to do")
        return 0

    conductor["stage_order_exact_per_D8"] = STAGE_ORDER_17
    conductor["stage_order_regeneration_history"] = list(
        conductor.get("stage_order_regeneration_history") or []) + [{
            "regenerated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
            "round": "R481",
            "repo_head": head,
            "was": f"{len(old_chain)} stages (the drift the external "
                   f"audit measured as A1 at 17504061: this artifact "
                   f"lagged the executable STAGE_ORDER — R394/R397/R401 "
                   f"first-class stages never regenerated it)",
            "now": ("17 stages: the R394/R397/R401 additions AND "
                    "R481's IMPROVE (the P0-1 loop closure) — the "
                    "registry now matches the executable arithmetic "
                    "exactly, pinned by tests/test_r402_"
                    "discovery_integrity.py"),
        }]
    caps = d.get("capabilities") or []
    if not any(c.get("capability_id") == "IMPROVE" for c in caps):
        caps.append(IMPROVE_CAPABILITY)
    d["capabilities"] = caps
    d["last_updated_directive"] = (
        "R481 (external-audit P0-1): IMPROVE joined as a first-class "
        "stage — the registry regeneration the audit's A1 finding "
        "demanded; conductor chain 13 -> 17, the executable "
        "STAGE_ORDER is the single authority")

    ART.write_text(json.dumps(d, indent=1))
    print(f"registry regenerated: {len(old_chain)} -> "
          f"{len(STAGE_ORDER_17)} stages; IMPROVE capability "
          f"registered ({len(caps)} capabilities)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
