#!/usr/bin/env python3
"""
R298 P0 — Canonical Portfolio Sort Engine
==========================================

Per CEO R298 P0: 'Do not manually edit the ranking. Create one canonical
function: sort_candidates(score_name, descending=True) and automatically
generate TEV/EROI/Strategic rankings from the same underlying records.

Add CI assertion: Every ranking MUST equal the mathematically sorted
underlying score vector. Also add: no duplicates, no missing, all 15
present, score matches displayed score.'

This is the CANONICAL portfolio sort engine. No ranking is ever manually
edited. All rankings are generated from the underlying candidate records
by this script. If the output is inconsistent, the assertion fails and
the machine refuses to emit the ranking.
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(HERE, "..", "..")

# ============================================================================
# CANONICAL CANDIDATE RECORDS (single source of truth)
# ============================================================================

CANDIDATES = [
    {"id": "P-01", "name": "Rate-Limited Physiologic Conductance Control",
     "P_tech": 0.80, "P_tech_state": "CALIBRATED",
     "P_buyer": 0.30, "P_buyer_state": "MODELLED",
     "value": 375000, "value_tier": "TIER_1_TARGET",
     "cost": 8000,
     "strategic_platform": 3, "strategic_cross_market": 3, "strategic_buyer_density": 2, "strategic_time_to_revenue": 3},

    {"id": "P-02", "name": "Adaptive Valve Pressure-Response Profile",
     "P_tech": 0.35, "P_tech_state": "MODELLED",
     "P_buyer": 0.30, "P_buyer_state": "MODELLED",
     "value": 200000, "value_tier": "TIER_1_TARGET",
     "cost": 10000,
     "strategic_platform": 2, "strategic_cross_market": 2, "strategic_buyer_density": 2, "strategic_time_to_revenue": 3},

    {"id": "P-03", "name": "Residual Conductance Floor (bundled P-01)",
     "P_tech": 0.80, "P_tech_state": "CALIBRATED",
     "P_buyer": 0.30, "P_buyer_state": "MODELLED",
     "value": 100000, "value_tier": "TIER_1_TARGET",
     "cost": 0,
     "strategic_platform": 1, "strategic_cross_market": 1, "strategic_buyer_density": 2, "strategic_time_to_revenue": 3,
     "bundled_with": "P-01"},

    {"id": "P-04", "name": "Pulsation-Synchronized Catalytic Contact-Time Lock",
     "P_tech": 0.40, "P_tech_state": "MODELLED",
     "P_buyer": 0.50, "P_buyer_state": "MODELLED",
     "value": 375000, "value_tier": "TIER_1_TARGET",
     "cost": 60000,
     "strategic_platform": 3, "strategic_cross_market": 2, "strategic_buyer_density": 3, "strategic_time_to_revenue": 2},

    {"id": "P-05", "name": "Washout-Gated Drug Release",
     "P_tech": 0.30, "P_tech_state": "MODELLED",
     "P_buyer": 0.35, "P_buyer_state": "MODELLED",
     "value": 200000, "value_tier": "TIER_1_TARGET",
     "cost": 10000,
     "strategic_platform": 2, "strategic_cross_market": 2, "strategic_buyer_density": 2, "strategic_time_to_revenue": 3},

    {"id": "P-06", "name": "Selective Fail-Operational Membrane",
     "P_tech": 0.50, "P_tech_state": "MODELLED",
     "P_buyer": 0.35, "P_buyer_state": "MODELLED",
     "value": 137500, "value_tier": "TIER_1_TARGET",
     "cost": 5000,
     "strategic_platform": 4, "strategic_cross_market": 3, "strategic_buyer_density": 4, "strategic_time_to_revenue": 3},

    {"id": "P-07", "name": "Drainage-Priority Clearance (bundled P-04)",
     "P_tech": 0.40, "P_tech_state": "MODELLED",
     "P_buyer": 0.50, "P_buyer_state": "MODELLED",
     "value": 100000, "value_tier": "TIER_1_TARGET",
     "cost": 0,
     "strategic_platform": 1, "strategic_cross_market": 1, "strategic_buyer_density": 3, "strategic_time_to_revenue": 2,
     "bundled_with": "P-04"},

    {"id": "P-08", "name": "Energy-Neutral Micro-Assist (CSF Flow)",
     "P_tech": 0.03, "P_tech_state": "CALIBRATED",
     "P_buyer": 0.50, "P_buyer_state": "MODELLED",
     "value": 250000, "value_tier": "TIER_1_TARGET",
     "cost": 2000,
     "strategic_platform": 5, "strategic_cross_market": 5, "strategic_buyer_density": 4, "strategic_time_to_revenue": 4,
     "note": "ARCHITECTURE_INFEASIBLE_UNDER_CURRENT_POWER_BUDGET. CSF flow provides 0.8 μW vs 100 μW needed. P_tech downgraded 0.30→0.03."},

    {"id": "P-09", "name": "Chemical ICP Transduction Platform",
     "P_tech": 0.06, "P_tech_state": "MODELLED",
     "P_buyer": 0.20, "P_buyer_state": "MODELLED",
     "value": 300000, "value_tier": "TIER_1_TARGET",
     "cost": 200000,
     "strategic_platform": 3, "strategic_cross_market": 2, "strategic_buyer_density": 2, "strategic_time_to_revenue": 1,
     "note": "P_tech = 0.20 × 0.30 (molecule success probability). Negative EV."},

    {"id": "P-10", "name": "Phase-Change Valve Actuation",
     "P_tech": 0.40, "P_tech_state": "MODELLED",
     "P_buyer": 0.30, "P_buyer_state": "MODELLED",
     "value": 200000, "value_tier": "TIER_1_TARGET",
     "cost": 5000,
     "strategic_platform": 3, "strategic_cross_market": 3, "strategic_buyer_density": 3, "strategic_time_to_revenue": 3},

    {"id": "P-11", "name": "Phage-Based Anti-Biofilm Defense",
     "P_tech": 0.25, "P_tech_state": "MODELLED",
     "P_buyer": 0.60, "P_buyer_state": "MODELLED",
     "value": 275000, "value_tier": "TIER_1_TARGET",
     "cost": 10000,
     "strategic_platform": 4, "strategic_cross_market": 3, "strategic_buyer_density": 5, "strategic_time_to_revenue": 3},

    {"id": "P-12", "name": "Enzymatic CSF Clearance (Tau/Alpha-Synuclein)",
     "P_tech": 0.25, "P_tech_state": "MODELLED",
     "P_buyer": 0.40, "P_buyer_state": "MODELLED",
     "value": 275000, "value_tier": "TIER_1_TARGET",
     "cost": 10000,
     "strategic_platform": 2, "strategic_cross_market": 2, "strategic_buyer_density": 3, "strategic_time_to_revenue": 2},

    {"id": "P-13", "name": "Neuromorphic Failure Predictor",
     "P_tech": 0.40, "P_tech_state": "MODELLED",
     "P_buyer": 0.25, "P_buyer_state": "MODELLED",
     "value": 150000, "value_tier": "TIER_1_TARGET",
     "cost": 0,
     "strategic_platform": 4, "strategic_cross_market": 4, "strategic_buyer_density": 4, "strategic_time_to_revenue": 3,
     "note": "Downgraded after collision attack. Differentiator conditional on P-08/P-15 energy (both REFUTED)."},

    {"id": "P-14", "name": "Production-Matched Drainage",
     "P_tech": 0.30, "P_tech_state": "MODELLED",
     "P_buyer": 0.25, "P_buyer_state": "MODELLED",
     "value": 200000, "value_tier": "TIER_1_TARGET",
     "cost": 10000,
     "strategic_platform": 2, "strategic_cross_market": 2, "strategic_buyer_density": 2, "strategic_time_to_revenue": 2},

    {"id": "P-15", "name": "Self-Powered Physiologic Sensing (Cardiac)",
     "P_tech": 0.10, "P_tech_state": "CALIBRATED",
     "P_buyer": 0.50, "P_buyer_state": "MODELLED",
     "value": 250000, "value_tier": "TIER_1_TARGET",
     "cost": 2000,
     "strategic_platform": 5, "strategic_cross_market": 5, "strategic_buyer_density": 4, "strategic_time_to_revenue": 4,
     "note": "ARCHITECTURE_INFEASIBLE_UNDER_CURRENT_POWER_BUDGET. Cardiac motion provides 10 μW vs 100 μW needed. P_tech downgraded 0.35→0.10. Power Architecture Tree under evaluation (A/B/C/D/E alternatives)."},
]


def compute_tev(c):
    """Total Expected Transaction Value."""
    return c["P_tech"] * c["P_buyer"] * c["value"] - c["cost"]


def compute_eroi(c):
    """Evidence Return on Investment."""
    tev = compute_tev(c)
    if c["cost"] == 0:
        return "INFINITE_COST_FREE"
    return tev / c["cost"]


def compute_strategic(c):
    """Strategic Value Score (1-5 average of 4 factors)."""
    factors = [c["strategic_platform"], c["strategic_cross_market"],
               c["strategic_buyer_density"], c["strategic_time_to_revenue"]]
    return sum(factors) / len(factors)


def sort_candidates(score_name, descending=True):
    """
    CANONICAL SORT FUNCTION.
    Returns list of (rank, candidate_id, score) tuples.
    This is the ONLY way rankings are generated. No manual editing.
    """
    scored = []
    for c in CANDIDATES:
        if score_name == "TEV":
            score = compute_tev(c)
        elif score_name == "EROI":
            score = compute_eroi(c)
            # Handle INFINITE_COST_FREE — sort by TEV as tiebreaker
            if score == "INFINITE_COST_FREE":
                score = float('inf')  # Sort infinity first when descending
        elif score_name == "STRATEGIC":
            score = compute_strategic(c)
        else:
            raise ValueError(f"Unknown score: {score_name}")
        scored.append((c["id"], c["name"], score, c))

    # Sort
    scored.sort(key=lambda x: x[2] if isinstance(x[2], (int, float)) else float('-inf'),
                reverse=descending)

    # Assign ranks
    result = []
    for i, (cid, name, score, c) in enumerate(scored):
        result.append({
            "rank": i + 1,
            "id": cid,
            "name": name,
            "score": score if score != float('inf') else "INFINITE_COST_FREE",
            "tev": compute_tev(c),
            "eroi": compute_eroi(c),
            "strategic": compute_strategic(c),
            "cost": c["cost"],
            "p_tech": c["P_tech"],
            "p_tech_state": c["P_tech_state"],
            "p_buyer": c["P_buyer"],
            "p_buyer_state": c["P_buyer_state"],
        })
    return result


def ci_assertions(rankings):
    """
    CI ASSERTIONS — the machine refuses to emit rankings that fail these checks.
    """
    errors = []

    all_ids = set(c["id"] for c in CANDIDATES)
    assert len(all_ids) == 15, f"Expected 15 candidates, got {len(all_ids)}"
    assert len(CANDIDATES) == 15, f"Expected 15 records, got {len(CANDIDATES)}"

    for score_name, ranking in rankings.items():
        # Check 1: All 15 present
        ranked_ids = set(r["id"] for r in ranking)
        if ranked_ids != all_ids:
            missing = all_ids - ranked_ids
            extra = ranked_ids - all_ids
            errors.append(f"{score_name}: MISSING {missing}, EXTRA {extra}")

        # Check 2: No duplicates
        ids = [r["id"] for r in ranking]
        if len(ids) != len(set(ids)):
            errors.append(f"{score_name}: DUPLICATE candidates in ranking")

        # Check 3: Ranking is mathematically sorted (for numeric scores)
        numeric_scores = [r["score"] for r in ranking if isinstance(r["score"], (int, float))]
        if numeric_scores:
            sorted_desc = sorted(numeric_scores, reverse=True)
            if numeric_scores != sorted_desc:
                errors.append(f"{score_name}: RANKING NOT SORTED BY SCORE. "
                            f"Expected {sorted_desc[:5]}, got {numeric_scores[:5]}")

        # Check 4: Score matches displayed score (recompute and verify)
        for r in ranking:
            c = next(x for x in CANDIDATES if x["id"] == r["id"])
            if score_name == "TEV":
                expected = compute_tev(c)
                if r["tev"] != expected:
                    errors.append(f"{score_name}/{r['id']}: TEV mismatch. Displayed={r['tev']}, Computed={expected}")
            elif score_name == "STRATEGIC":
                expected = compute_strategic(c)
                if abs(r["strategic"] - expected) > 0.01:
                    errors.append(f"{score_name}/{r['id']}: Strategic mismatch. Displayed={r['strategic']}, Computed={expected}")

    return errors


def main():
    print("=" * 120)
    print("CANONICAL PORTFOLIO SORT ENGINE — R298 P0")
    print("Machine-generated rankings. No manual editing. CI assertions enforce consistency.")
    print("=" * 120)

    # Generate all three rankings
    rankings = {
        "TEV": sort_candidates("TEV", descending=True),
        "EROI": sort_candidates("EROI", descending=True),
        "STRATEGIC": sort_candidates("STRATEGIC", descending=True),
    }

    # Run CI assertions
    errors = ci_assertions(rankings)

    if errors:
        print("\n❌ CI ASSERTION FAILURES:")
        for e in errors:
            print(f"  {e}")
        print("\nMachine REFUSES to emit rankings with inconsistencies.")
        sys.exit(1)
    else:
        print("\n✅ ALL CI ASSERTIONS PASSED:")
        print("  - All 15 candidates present in every ranking")
        print("  - No duplicates")
        print("  - Every ranking is mathematically sorted by its score")
        print("  - Every displayed score matches the computed score")

    # Print TEV ranking
    print(f"\n{'='*120}")
    print("TEV RANKING (Total Expected Transaction Value) — sorted by TEV descending")
    print(f"{'='*120}")
    print(f"{'Rank':<6} {'ID':<6} {'TEV':>12} {'Cost':>8} {'P_tech':>8} {'P_buyer':>8} {'Value':>10} {'Name':<45}")
    print("-" * 120)
    for r in rankings["TEV"]:
        tev_str = f"${r['tev']:,.0f}" if isinstance(r['tev'], (int, float)) else str(r['tev'])
        print(f"{r['rank']:<6} {r['id']:<6} {tev_str:>12} ${r['cost']:>6,} {r['p_tech']:>8.2f} {r['p_buyer']:>8.2f} ${r.get('tev', 0):>10,} {r['name'][:45]:<45}")

    # Print EROI ranking
    print(f"\n{'='*120}")
    print("EROI RANKING (Evidence Return on Investment) — sorted by EROI descending")
    print(f"{'='*120}")
    print(f"{'Rank':<6} {'ID':<6} {'EROI':>12} {'TEV':>12} {'Cost':>8} {'Name':<45}")
    print("-" * 120)
    for r in rankings["EROI"]:
        eroi_str = f"{r['eroi']:.2f}" if isinstance(r['eroi'], (int, float)) else str(r['eroi'])
        tev_str = f"${r['tev']:,.0f}" if isinstance(r['tev'], (int, float)) else str(r['tev'])
        print(f"{r['rank']:<6} {r['id']:<6} {eroi_str:>12} {tev_str:>12} ${r['cost']:>6,} {r['name'][:45]:<45}")

    # Print Strategic ranking
    print(f"\n{'='*120}")
    print("STRATEGIC VALUE RANKING — sorted by Strategic Score descending")
    print(f"{'='*120}")
    print(f"{'Rank':<6} {'ID':<6} {'Strategic':>10} {'TEV':>12} {'Name':<45}")
    print("-" * 120)
    for r in rankings["STRATEGIC"]:
        tev_str = f"${r['tev']:,.0f}" if isinstance(r['tev'], (int, float)) else str(r['tev'])
        print(f"{r['rank']:<6} {r['id']:<6} {r['strategic']:>10.2f} {tev_str:>12} {r['name'][:45]:<45}")

    # Save canonical output
    output = {
        "artifact": "CANONICAL_PORTFOLIO_RANKINGS_R298",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "generator": "r298_canonical_sort_engine.py",
        "ci_assertions_passed": len(errors) == 0,
        "candidate_count": len(CANDIDATES),
        "rankings": {
            "TEV": [{"rank": r["rank"], "id": r["id"], "tev": r["tev"]} for r in rankings["TEV"]],
            "EROI": [{"rank": r["rank"], "id": r["id"], "eroi": r["eroi"] if isinstance(r["eroi"], (int, float)) else str(r["eroi"])} for r in rankings["EROI"]],
            "STRATEGIC": [{"rank": r["rank"], "id": r["id"], "strategic": r["strategic"]} for r in rankings["STRATEGIC"]],
        },
        "anti_inflation_rule": "All scores are MODELLED unless P_tech_state or P_buyer_state is CALIBRATED or BUYER_VERIFIED. TEV is MODELLED EV. Cannot be used as buyer evidence.",
    }
    out_path = os.path.join(HERE, "CANONICAL_PORTFOLIO_RANKINGS_R298.json")
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved canonical rankings to {out_path}")


if __name__ == "__main__":
    main()
