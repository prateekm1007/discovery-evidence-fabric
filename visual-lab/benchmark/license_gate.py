"""R449 Step 9: the formal license gate. A beautiful render cannot bypass it.

Gate semantics (operator directive R449-C2 Step 9):

    registry license_gate.gate_status              ->  benchmark gate verdict
    EVALUATION_PERMITTED_COMMERCIAL_PRECHECK_PERMISSIVE -> COMMERCIAL_CLEAR (provisional*)
    COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS        -> COMMERCIAL_REVIEW_REQUIRED
    COMMERCIAL_BLOCKED_NON_COMMERCIAL_LICENSE           -> COMMERCIAL_BLOCKED
    LICENSE_UNSTATED_BLOCKED_UNTIL_REVIEWED             -> COMMERCIAL_BLOCKED

    COMMERCIAL_CLEAR              -> may enter the production candidate pool
    COMMERCIAL_REVIEW_REQUIRED    -> research only
    COMMERCIAL_BLOCKED            -> never production

* COMMERCIAL_CLEAR from a heuristic pre-classification is PROVISIONAL: it
  permits benchmark/lab evaluation and keeps the model OUT of any buyer-facing
  surface until the registry's final_legal_review (always
  REQUIRED_BEFORE_ANY_COMMERCIAL_SHIPMENT) is satisfied. The gate NEVER
  upgrades a status and never interprets a license (Art. VI/XXVII).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import json

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "registry" / "hf_visual_model_registry.json"

# input gate_status -> (benchmark verdict, may_enter_production_pool, research_only)
GATE_TABLE = {
    "EVALUATION_PERMITTED_COMMERCIAL_PRECHECK_PERMISSIVE": (
        "COMMERCIAL_CLEAR", True, False),
    "COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS": (
        "COMMERCIAL_REVIEW_REQUIRED", False, True),
    "COMMERCIAL_BLOCKED_NON_COMMERCIAL_LICENSE": (
        "COMMERCIAL_BLOCKED", False, False),
    "LICENSE_UNSTATED_BLOCKED_UNTIL_REVIEWED": (
        "COMMERCIAL_BLOCKED", False, False),
}


class LicenseGateError(RuntimeError):
    """Typed failure: an attempt to route a model around its license gate."""


def decide(gate_status: str) -> dict:
    if gate_status not in GATE_TABLE:
        # unknown / future registry states fail CLOSED (Art. IV)
        return {"gate_status_in": gate_status, "verdict": "COMMERCIAL_BLOCKED",
                "may_enter_production_pool": False, "research_only": True,
                "note": "unrecognized registry gate status -> fail closed"}
    verdict, pool, research = GATE_TABLE[gate_status]
    return {"gate_status_in": gate_status, "verdict": verdict,
            "may_enter_production_pool": pool, "research_only": research}


def enforce_pool_entry(model_id: str, gate_status: str) -> None:
    """Raises unless the model may enter the production candidate pool."""
    d = decide(gate_status)
    if not d["may_enter_production_pool"]:
        raise LicenseGateError(
            f"LICENSE_GATE_BLOCKED: {model_id} is {d['verdict']} - it may not "
            f"enter the production candidate pool (research_only={d['research_only']})")


def registry_results(registry_path=REGISTRY_PATH) -> list:
    reg = json.loads(Path(registry_path).read_text())
    models = reg.get("models", reg if isinstance(reg, list) else [])
    out = []
    for m in models:
        gate = m.get("license_gate", {})
        d = decide(gate.get("gate_status", ""))
        out.append({
            "model_id": m.get("model_id"),
            "hf_revision": m.get("hf_revision") or m.get("revision"),
            "license_tags_observed": gate.get("license_tags_observed", []),
            "registry_gate_status": gate.get("gate_status"),
            "verdict": d["verdict"],
            "may_enter_production_pool": d["may_enter_production_pool"],
            "research_only": d["research_only"],
            "final_legal_review": gate.get("final_legal_review"),
            "approved_for_canonical_geometry": m.get("approved_for_canonical_geometry", False),
            "note": gate.get("note"),
        })
    return out
