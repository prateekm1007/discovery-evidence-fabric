"""Engine bridge to the R376 collision core.

Thin adapter so run.py's grid/ensemble candidate path and the COLLISION
stage share ONE collision authority (Art. X) without the engine package
importing prior_art_v2 internals inline. Returns the (collision, prior_art)
pair in the same shapes the COLLISION adapter applies to the envelope.
"""
from __future__ import annotations

from typing import Any, Dict


def candidate_collision(mechanism_map: Dict[str, Any],
                        problem: Dict[str, Any]) -> Dict[str, Any]:
    """Run the mechanism-centered collision for ONE candidate's mechanism
    map. Used for grid/ensemble candidates so each is differentiated
    against art searched for ITS OWN mechanism (R376 defect class E).
    Raises on infrastructure failure — the caller records the honest
    UNRESOLVED state (never inherited art, never fabricated absence)."""
    from discovery_fabric.prior_art_v2.collision_resolution import (
        run_collision)
    collision = run_collision(mechanism_map, problem)
    resolution = collision["differentiation_resolution"]
    prior_art = {
        "prior_art_status": resolution["state"],
        "differentiation_resolution": resolution,
        "state_vocabulary": "collision_resolution R376 + classify/v4",
        "note": ("per-candidate collision re-run (grid/ensemble path); "
                 "the naive candidate's collision results are NOT "
                 "inherited"),
    }
    return {"collision": collision, "prior_art": prior_art}
