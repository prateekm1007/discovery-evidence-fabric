#!/usr/bin/env python3
"""
Slot-Territory Derivation & Invariant Enforcement

Per CEO directive (2026-08-20) — eliminate dual-state entropy:
  slots = SOLE canonical active portfolio authority
  territories = DERIVED compatibility projection (read-only)

Invariant:
  derived_territories == projection(slots + immutable_history)

If the actual `territories` key in PORTFOLIO.json diverges from the
derived projection → certification RED.

This module is imported by the certification pipeline. It MUST pass
for the consolidation to be considered valid.

Constitution articles enforced:
  Article VII  — never weaken the verifier to rescue a claim
  Article X    — canonical state has one authority
  Article XXIII — never infer repository state from local state
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PORTFOLIO = REPO_ROOT / "CANONICAL_STATE" / "PORTFOLIO.json"


def _load_portfolio() -> dict[str, Any]:
    with open(CANONICAL_PORTFOLIO) as f:
        return json.load(f)


def _slot_to_territory_mapping() -> dict[int, str]:
    """Map slot_id → list of territory IDs absorbed by that slot.

    This mapping is IMMUTABLE — it is the consolidation contract.
    Changing it requires a new consolidation event with explicit CEO authority.
    """
    return {
        1: ["CV-T06"],           # R6 Passive Rescue / Obstruction Bypass
        2: ["CV-T08"],           # Adaptive / Sensing eShunt
        3: ["CV-T03"],           # Controlled CNS Therapeutic Platform
        4: ["CV-T09", "CV-T10"], # CNS / Lifecycle Intelligence (merged)
        # Slot 5 = EMPTY, no territories absorbed
    }


def _absorbed_territory_record(slot: dict, territory_id: str) -> dict:
    """Derive the backward-compatible territory record from its owning slot.

    The granular territory state comes from slot.consolidation_mapping.territory_state_mapping.
    This is the SOLE legitimate source of the territory current_state for absorbed territories.
    """
    state_mapping = slot.get("consolidation_mapping", {}).get("territory_state_mapping", {})
    granular_state = state_mapping.get(territory_id, slot["current_state"])
    return {
        "id": territory_id,
        "name": _territory_name(territory_id),
        "branch": slot.get("consolidation_mapping", {}).get("absorbs_branches", {}).get(territory_id, "unknown"),
        "current_state": granular_state,
        "mapped_to_slot": slot["slot_id"],
        "portfolio_role": "ABSORBED_ACTIVE",
        "_derived_from": f"slots[{slot['slot_id']}].consolidation_mapping.territory_state_mapping[{territory_id}]",
    }


def _territory_name(territory_id: str) -> str:
    names = {
        "CV-T01": "Hydraulic state estimation",
        "CV-T02": "Selective therapeutic retention",
        "CV-T02L": "Large-therapeutic size-selective retention",
        "CV-T03": "Controlled therapeutic retention / CNS delivery",
        "CV-T04": "Venous-aware regulation",
        "CV-T05": "Fouling / obstruction",
        "CV-T06": "Retrieval / rescue (R6)",
        "CV-T07": "Venous-interface protection",
        "CV-T08": "Patient-specific / adaptive eShunt",
        "CV-T09": "CNS therapy platform",
        "CV-T10": "Lifecycle / platform intelligence",
    }
    return names.get(territory_id, "UNKNOWN")


def _historical_territory_record(territory_id: str, portfolio: dict) -> dict:
    """Build a historical-frozen territory record from the immutable ledger.

    The LEDGER is the immutable record of state transitions. The historical
    file (PORTFOLIO_10TERRITORY_HISTORICAL_2026-08-18.json) is a SNAPSHOT that
    may be stale. The ledger is always current because it is append-only.

    Per Article X (canonical state has one authority), the ledger projection
    is the SOLE legitimate source of historical territory current_state.
    """
    # Read the ledger to find the latest state for this territory
    ledger_path = REPO_ROOT / "epistemic_integrity" / "approved_provenance" / "state_transition_ledger.ndjson"
    latest_state = "UNKNOWN"
    if ledger_path.exists():
        with open(ledger_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get("territory_id") == territory_id:
                    latest_state = event.get("to_state", "UNKNOWN")
    return {
        "id": territory_id,
        "name": _territory_name(territory_id),
        "current_state": latest_state,
        "mapped_to_slot": None,
        "portfolio_role": "HISTORICAL_FROZEN",
        "_derived_from": "state_transition_ledger.ndjson (immutable ledger projection)",
    }


def derive_territories(portfolio: dict) -> list[dict]:
    """Project slots + immutable_history → territories list.

    This is the SOLE legitimate way to produce the `territories` list.
    Any manual edit to `territories` that does not match this derivation
    is an invariant violation.
    """
    slot_to_territories = _slot_to_territory_mapping()
    derived = []

    # 1. Absorbed active territories (from slots)
    for slot in portfolio.get("slots", []):
        territory_ids = slot_to_territories.get(slot["slot_id"], [])
        for tid in territory_ids:
            derived.append(_absorbed_territory_record(slot, tid))

    # 2. Historical frozen territories (from immutable history)
    historical_ids = ["CV-T01", "CV-T02", "CV-T02L", "CV-T04", "CV-T05", "CV-T07"]
    for tid in historical_ids:
        derived.append(_historical_territory_record(tid, portfolio))

    return derived


def verify_invariant() -> dict:
    """Verify that the `territories` key matches the derived projection.

    Returns a report dict with:
      invariant_holds: bool
      actual_territories: list
      derived_territories: list
      discrepancies: list of (territory_id, field, actual, derived)
    """
    portfolio = _load_portfolio()
    actual = portfolio.get("territories", [])
    derived = derive_territories(portfolio)

    discrepancies = []

    # Build lookup by territory ID
    actual_by_id = {t["id"]: t for t in actual if isinstance(t, dict) and "id" in t}
    derived_by_id = {t["id"]: t for t in derived}

    # Check all derived territories are present in actual with matching current_state
    for tid, derived_rec in derived_by_id.items():
        if tid not in actual_by_id:
            discrepancies.append({
                "territory_id": tid,
                "issue": "MISSING_IN_ACTUAL",
                "derived_current_state": derived_rec["current_state"],
                "actual_current_state": None,
            })
            continue
        actual_rec = actual_by_id[tid]
        if actual_rec.get("current_state") != derived_rec["current_state"]:
            discrepancies.append({
                "territory_id": tid,
                "issue": "CURRENT_STATE_MISMATCH",
                "derived_current_state": derived_rec["current_state"],
                "actual_current_state": actual_rec.get("current_state"),
            })
        if actual_rec.get("portfolio_role") != derived_rec.get("portfolio_role"):
            discrepancies.append({
                "territory_id": tid,
                "issue": "PORTFOLIO_ROLE_MISMATCH",
                "derived_role": derived_rec.get("portfolio_role"),
                "actual_role": actual_rec.get("portfolio_role"),
            })

    # Check no extra territories in actual that aren't in derived
    for tid in actual_by_id:
        if tid not in derived_by_id:
            discrepancies.append({
                "territory_id": tid,
                "issue": "EXTRA_IN_ACTUAL_NOT_DERIVED",
                "actual_current_state": actual_by_id[tid].get("current_state"),
            })

    return {
        "invariant_holds": len(discrepancies) == 0,
        "actual_territories_count": len(actual),
        "derived_territories_count": len(derived),
        "discrepancies": discrepancies,
    }


def main() -> int:
    """CLI entry: verify invariant, exit 0 if holds, 1 if violated."""
    report = verify_invariant()
    print(f"Invariant holds: {report['invariant_holds']}")
    print(f"Actual territories: {report['actual_territories_count']}")
    print(f"Derived territories: {report['derived_territories_count']}")
    if report["discrepancies"]:
        print(f"Discrepancies: {len(report['discrepancies'])}")
        for d in report["discrepancies"]:
            print(f"  ❌ {d['territory_id']}: {d['issue']}")
            if "derived_current_state" in d:
                print(f"     derived: {d['derived_current_state']}")
            if "actual_current_state" in d and d.get("actual_current_state") is not None:
                print(f"     actual:  {d['actual_current_state']}")
        return 1
    print("✅ territories == projection(slots + immutable_history)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
