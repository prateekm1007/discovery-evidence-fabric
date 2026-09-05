"""tvm_v2.signal_policy — the trajectory-signal hierarchy (Step 6).

Operator directive (R412 gradient v2, Step 6): preserve investment as
secondary. Do NOT turn the TVM into an "industries with the most money"
ranking. Use performance / cost / efficiency / reliability /
manufacturing / deployment trajectories as PRIMARY technical signals.
Investment / talent / experimental concentration may explain where to
look, but cannot establish technological capability.

Constitutional basis: Articles XXVII (threshold/evidence class
provenance), XXVIII (no silent semantic promotion — an investment
signal must never be promoted into capability evidence), XLIII
(search-space neutrality: money concentration is not a problem fact).

Machine enforcement: classify_signal() maps every signal name to exactly
one class; validate_tvm_entry() (evidence_contract) rejects any entry
whose capability evidence is not a PRIMARY technical signal.
"""
from __future__ import annotations

from typing import Dict, List

SIGNAL_PRIMARY_TECHNICAL = "PRIMARY_TECHNICAL"
SIGNAL_EXPLANATORY_ONLY = "EXPLANATORY_ONLY"
SIGNAL_UNKNOWN = "UNKNOWN_SIGNAL"

# Frozen primary signal vocabulary (operator directive Step 6). These —
# and only these — can establish a measured technological trajectory.
PRIMARY_TECHNICAL_SIGNALS: List[str] = [
    "performance",
    "cost",
    "efficiency",
    "reliability",
    "manufacturing",
    "deployment",
]

# Frozen explanatory-only vocabulary. These may appear in the
# explanatory_signals array of a TVM entry (class EXPLANATORY_ONLY) and
# may guide WHERE to search, but NEVER as capability evidence.
EXPLANATORY_ONLY_SIGNALS: List[str] = [
    "investment",
    "talent",
    "experimental_concentration",
]

_ALIASES: Dict[str, str] = {
    # performance-family surface forms
    "accuracy": "performance", "precision": "performance",
    "speed": "performance", "throughput": "performance",
    "bandwidth": "performance", "sensitivity": "performance",
    "resolution": "performance", "power_density": "performance",
    "energy_density": "performance", "range": "performance",
    # cost-family
    "price": "cost", "unit_cost": "cost", "capex": "cost",
    "cost_per_unit": "cost",
    # efficiency-family
    "conversion_efficiency": "efficiency", "yield": "efficiency",
    "specific_energy": "efficiency", "figure_of_merit": "efficiency",
    # reliability-family
    "lifetime": "reliability", "durability": "reliability",
    "mtbf": "reliability", "failure_rate": "reliability",
    "drift": "reliability",
    # manufacturing-family
    "process_capability": "manufacturing", "tolerance": "manufacturing",
    "scalability": "manufacturing", "wafer_yield": "manufacturing",
    # deployment-family
    "installed_base": "deployment", "field_units": "deployment",
    "adoption": "deployment", "cumulative_production": "deployment",
    # explanatory-family surface forms
    "vc_funding": "investment", "funding": "investment",
    "r_and_d_spend": "investment", "capital_flow": "investment",
    "researcher_headcount": "talent", "phd_output": "talent",
    "publication_rate": "experimental_concentration",
    "patent_filing_rate": "experimental_concentration",
    "active_labs": "experimental_concentration",
}


def classify_signal(name: str) -> str:
    """Deterministically classify one signal name.

    Primary technical signals establish measured capability; explanatory
    signals never do. Unknown names are UNKNOWN_SIGNAL (recorded, never
    guessed — Article XXV), and validate_tvm_entry rejects them as
    capability evidence.
    """
    if name in PRIMARY_TECHNICAL_SIGNALS:
        return SIGNAL_PRIMARY_TECHNICAL
    if name in EXPLANATORY_ONLY_SIGNALS:
        return SIGNAL_EXPLANATORY_ONLY
    canonical = _ALIASES.get(name)
    if canonical is None:
        return SIGNAL_UNKNOWN
    if canonical in PRIMARY_TECHNICAL_SIGNALS:
        return SIGNAL_PRIMARY_TECHNICAL
    if canonical in EXPLANATORY_ONLY_SIGNALS:
        return SIGNAL_EXPLANATORY_ONLY
    return SIGNAL_UNKNOWN


def validate_signal_usage(entry: Dict[str, object]) -> List[str]:
    """Return the list of signal-policy violations for one TVM entry.

    Rules:
      - trajectory_dimension (the capability-evidence signal) must
        classify as PRIMARY_TECHNICAL.
      - explanatory_signals (if present) must all classify as
        EXPLANATORY_ONLY and are flagged if they appear instead in
        trajectory_dimension.
    """
    issues: List[str] = []
    traj = entry.get("trajectory_dimension")
    if traj is None:
        issues.append("missing_trajectory_dimension")
    else:
        cls = classify_signal(str(traj))
        if cls != SIGNAL_PRIMARY_TECHNICAL:
            issues.append(
                f"non_primary_signal_as_capability:{traj}={cls}")
    for sig in entry.get("explanatory_signals", []) or []:
        cls = classify_signal(str(sig))
        if cls not in (SIGNAL_EXPLANATORY_ONLY, SIGNAL_UNKNOWN):
            issues.append(f"primary_signal_misfiled_as_explanatory:{sig}")
    return issues


def signal_vocabulary_report() -> Dict[str, List[str]]:
    """The frozen signal vocabulary (for preregistration and tests)."""
    return {
        "primary_technical": list(PRIMARY_TECHNICAL_SIGNALS),
        "explanatory_only": list(EXPLANATORY_ONLY_SIGNALS),
        "alias_count": len(_ALIASES),
    }
