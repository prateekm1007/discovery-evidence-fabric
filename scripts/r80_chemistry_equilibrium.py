#!/usr/bin/env python3
"""R80 DEV prototype (AM80 direction 3, AM81 complement; claim c-0107):
generation-side COMPUTED-equilibrium direction check — Cantera (BSD-3-Clause,
see NOTICE.md) `equilibrate()` COMPUTES the equilibrium and a claimed
chemistry direction is verified against the COMPUTED sign, instead of the
LLM's guessed prose being trusted.

Relation to the committed registry scan (scripts/r70_stated_formula_scan.py,
the fifth bind): the scan covers the registry-known inversion legs (E1/E2/E3)
by text pattern — including the Ti-Cl class, whose species-level COMPUTED
check would need a Ti/Cl mechanism the repo does not custody (typed scope
note below; NO invented thermo data). This module is the computed
complement: it proves the mechanism (compute equilibrium -> compare the
claimed direction -> CONSISTENT/INVERTED/UNVERIFIABLE) on cantera-shipped
data (gri30), with a CONSERVATIVE prose extractor that fails open to
silence on ambiguity — the same contract as the registry scan
("anything ambiguous stays silent").

NON-FROZEN and adoption-gated (the c-0106 lane owns the frozen-machine
wiring): this module wires NOWHERE today; adoption follows the same gate
pattern as the convergence lane (LLM-stage DEV ablation -> wiring under the
CI-gated re-freeze discipline). Zero LLM, zero network.

Dilution discipline (verified in code, scripts/r80_chem_sanity.py): a mole
FRACTION comparison conflates dilution with equilibrium shift (excess O2
Lowers the CO2 mole fraction purely by dilution while conversion RISES) —
the engine compares the target species against its SOURCE species
(X[target]/X[source]), which is dilution-free.
"""
from __future__ import annotations

import re

FLAT_REL = 0.02  # |relative change| below this is typed flat/UNVERIFIABLE

TI_CLASS_SCOPE_NOTE = (
    "the Ti-Cl inversion class (the committed E1/E2 registry legs: excess "
    "oxidant claimed to favor a volatile chloride, T-up claimed to "
    "volatilize a refractory oxide) needs a Ti/Cl equilibrium mechanism "
    "under custody for a species-level COMPUTED check — none is shipped "
    "with cantera and none is invented here (no invented thermo data, "
    "Accuracy rule). The registry scan keeps covering those legs; this "
    "module proves the computed mechanism on gri30-verifiable legs and "
    "rides the same adoption gate.")


def _phase(mech: str):
    import cantera as ct
    return ct.Solution(mech)


def mole_fraction(mech: str, T: float, P: float, X: dict,
                  species: str) -> float:
    gas = _phase(mech)
    gas.TPX = T, P, X
    gas.equilibrate("TP")
    return float(gas.X[gas.species_index(species)])


def equilibrium_ratio(mech: str, T: float, P: float, X: dict,
                      target: str, source: str) -> float:
    """Dilution-free signal: X[target]/X[source] at equilibrium."""
    t = mole_fraction(mech, T, P, X, target)
    s = mole_fraction(mech, T, P, X, source)
    return t / max(s, 1e-30)


def _signed(rel_change: float) -> str:
    if abs(rel_change) < FLAT_REL:
        return "flat"
    return "up" if rel_change > 0 else "down"


def computed_T_direction(mech: str, X: dict, T_low: float, T_high: float,
                         P: float, target: str,
                         source: str | None = None) -> dict:
    """Computed direction of the target (vs its source, dilution-free)
    under a T step, at equilibrium. Returns the signal + the raw values."""
    if source is None:
        low = mole_fraction(mech, T_low, P, X, target)
        high = mole_fraction(mech, T_high, P, X, target)
    else:
        low = equilibrium_ratio(mech, T_low, P, X, target, source)
        high = equilibrium_ratio(mech, T_high, P, X, target, source)
    rel = (high - low) / low if low else float("inf")
    return {"computed_direction": _signed(rel), "rel_change": rel,
            "low": low, "high": high, "variable": "temperature",
            "T_low": T_low, "T_high": T_high}


def computed_oxidant_direction(mech: str, base_X: dict, oxidant: str,
                               stoich_frac: float, excess_frac: float,
                               T: float, P: float, target: str,
                               source: str) -> dict:
    """Computed direction of X[target]/X[source] when the oxidant share
    rises from stoich to excess (everything else held)."""
    xs = dict(base_X)
    xs[oxidant] = stoich_frac
    low = equilibrium_ratio(mech, T, P, xs, target, source)
    xs[oxidant] = excess_frac
    high = equilibrium_ratio(mech, T, P, xs, target, source)
    rel = (high - low) / low if low else float("inf")
    return {"computed_direction": _signed(rel), "rel_change": rel,
            "low": low, "high": high, "variable": "oxidant_excess",
            "oxidant": oxidant, "stoich_frac": stoich_frac,
            "excess_frac": excess_frac}


def verify_claim(claim: dict) -> dict:
    """The verdict engine: compute the direction, compare to the claim.
    claim = {mechanism, base_X, target, source, claimed_direction
             ('increase'|'decrease'), step: {'variable':'temperature',
             'T_low','T_high','P'} | {'variable':'oxidant_excess',
             'oxidant','stoich_frac','excess_frac','T','P'}}.
    Fail-open: any missing/unknown field -> UNVERIFIABLE (never a guess)."""
    required = {"mechanism", "base_X", "target", "source",
                "claimed_direction", "step"}
    if not required <= set(claim):
        return {"verdict": "UNVERIFIABLE",
                "note": "claim missing required fields (fail-open)"}
    if claim["claimed_direction"] not in ("increase", "decrease"):
        return {"verdict": "UNVERIFIABLE",
                "note": "claimed_direction must be increase|decrease"}
    step = claim["step"]
    try:
        if step.get("variable") == "temperature":
            comp = computed_T_direction(
                claim["mechanism"], claim["base_X"], step["T_low"],
                step["T_high"], step["P"], claim["target"],
                claim["source"])
        elif step.get("variable") == "oxidant_excess":
            comp = computed_oxidant_direction(
                claim["mechanism"], claim["base_X"], step["oxidant"],
                step["stoich_frac"], step["excess_frac"], step["T"],
                step["P"], claim["target"], claim["source"])
        else:
            return {"verdict": "UNVERIFIABLE",
                    "note": "unknown step variable (fail-open)"}
    except Exception as e:  # typed, fail-open — never a guessed verdict
        return {"verdict": "UNVERIFIABLE", "note": f"compute error: "
                f"{type(e).__name__}: {str(e)[:120]}"}
    comp["claimed_direction"] = claim["claimed_direction"]
    claimed_sign = {"increase": "up", "decrease": "down"}[
        claim["claimed_direction"]]
    if comp["computed_direction"] == "flat":
        comp["verdict"] = "UNVERIFIABLE"
        comp["note"] = "computed signal below the flat threshold"
    elif comp["computed_direction"] == claimed_sign:
        comp["verdict"] = "CONSISTENT"
    else:
        comp["verdict"] = "INVERTED"
    return comp


# --------------------------------------------- conservative prose extractor

_OX_RE = re.compile(r"excess\s+(oxygen|o2|air|oxidant|oxidizing\s+agent)",
                    re.IGNORECASE)
_DEC_RE = re.compile(
    r"(reduces|lowers|decreases|suppresses|less)\s+(the\s+)?(formation\s+"
    r"of\s+)?(co2|carbon\s+dioxide)", re.IGNORECASE)
_UP_RE = re.compile(
    r"(increases|drives|favors|favours|promotes|more)\s+(the\s+)?(formation"
    r"\s+of\s+)?(co2|carbon\s+dioxide)", re.IGNORECASE)

# The gri30-verifiable leg: CO -> CO2 under oxidant excess (the STRUCTURE
# of the volatile-chloride inversion leg — claiming the oxidant REDUCES
# the oxidized product). Species maps beyond this pair need custody-verified
# mechanisms (the typed scope note) — the extractor stays silent on them.
_CO_CO2_CLAIM = {
    "mechanism": "gri30.yaml",
    "base_X": {"CO": 0.02, "O2": 0.012, "N2": 1.0},
    "target": "CO2", "source": "CO",
    "step": {"variable": "oxidant_excess", "oxidant": "O2",
             "stoich_frac": 0.012, "excess_frac": 0.10,
             "T": 1200.0, "P": 101325.0},
}


def scan_computed_equilibrium_direction(answer: str) -> dict:
    """CONSERVATIVE prose scan: build a typed claim ONLY when the text has
    BOTH an explicit excess-oxidant phrase AND an explicit direction for a
    known-pair species; anything ambiguous stays silent ({}). The verdict
    is COMPUTED, not registry-matched."""
    if not answer:
        return {}
    if not _OX_RE.search(answer):
        return {}
    claimed = None
    if _DEC_RE.search(answer):
        claimed = "decrease"
    elif _UP_RE.search(answer):
        claimed = "increase"
    if claimed is None:
        return {}
    claim = dict(_CO_CO2_CLAIM)
    claim["claimed_direction"] = claimed
    verdict = verify_claim(claim)
    return {"claim_type": "oxidant_excess_vs_formation",
            "pair": ["CO", "CO2"], "claimed_direction": claimed,
            "computed_verdict": verdict["verdict"],
            "computed_direction": verdict.get("computed_direction"),
            "rel_change": verdict.get("rel_change"),
            "scope_note": TI_CLASS_SCOPE_NOTE}
