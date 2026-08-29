"""
equation_validation.py — R372-3: harden equation validation.

CEO R372-3: for every equation verify variables, units, domain, assumptions,
operating regime, applicability, limitations — then run a
dimensional-consistency check where possible. "Do not merely test whether
the string contains mathematical symbols."

Metadata (all canonical, no invention):
  variables          critical parameters whose recorded names match symbols
                     appearing in the expression (existing R371 rule)
  units              per-variable recorded units (None where unrecorded)
  domain             technology_domain + governing-model summary
  operating_regime   governing-model boundary_conditions (verbatim)
  assumptions        governing-model assumptions (verbatim)
  applicability      boundary conditions under which the equation is stated
  limitations        governing-model failure_regimes (verbatim) — the regimes
                     where the model is known not to hold
  source             provenance of the canonical string

Dimensional consistency (sympy):
  1. Parse the math expression (annotation/label already split off by
     equations.py). Unparseable / prose / corrupted strings -> state
     NOT_EVALUABLE_* with the reason (never a fake PASS — Art. XXV).
  2. Assign each symbol the unit recorded for a matching critical
     parameter. Symbols with NO recorded unit make the check
     NOT_EVALUABLE_UNITS_UNRECORDED — standard symbol guesses (r = metres,
     eta = Pa*s) are deliberately NOT used: units must come from the
     record (Constitution Art. VI).
  3. Where every symbol carries a recorded unit, evaluate
     dimension(LHS) == dimension(RHS) with sympy's SI unit system.

States:
  DIMENSIONALLY_CONSISTENT
  DIMENSIONALLY_INCONSISTENT       (a real finding -> release gate FAIL;
                                    surfaced, never hidden — Art. XV)
  NOT_EVALUABLE_SYNTAX
  NOT_EVALUABLE_UNITS_UNRECORDED
  NOT_EVALUABLE_NO_EQUALITY
  NOT_EVALUABLE_CORRUPTED_STRING
"""

import re

import sympy
from sympy.physics.units import Dimension
from sympy.physics.units.systems.si import SI

# unit strings recorded in critical_parameters -> sympy dimensions
_UNIT_MAP = {
    "mmhg": Dimension("pressure"), "kpa": Dimension("pressure"),
    "pa": Dimension("pressure"), "mm": Dimension("length"),
    "cm": Dimension("length"), "m": Dimension("length"),
    "µm": Dimension("length"), "um": Dimension("length"),
    "nm": Dimension("length"), "in": Dimension("length"),
    "ml/min": Dimension("volume") / Dimension("time"),
    "l/min": Dimension("volume") / Dimension("time"),
    "ml/h": Dimension("volume") / Dimension("time"),
    "ml": Dimension("volume"), "l": Dimension("volume"),
    "min": Dimension("time"), "h": Dimension("time"),
    "s": Dimension("time"), "s^-1": 1 / Dimension("time"),
    "1/s": 1 / Dimension("time"), "hz": 1 / Dimension("time"),
    "khz": 1 / Dimension("time"), "mhz": 1 / Dimension("time"),
    "ghz": 1 / Dimension("time"),
    "count": Dimension(1), "ratio": Dimension(1), "%": Dimension(1),
    "ng/l": Dimension("mass") / Dimension("volume"),
    "µm": Dimension("length"),
    "w": Dimension("power"), "mw": Dimension("power"),
    "µw": Dimension("power"), "uw": Dimension("power"),
    "v": Dimension("voltage"), "mv": Dimension("voltage"),
    "a": Dimension("current"), "ma": Dimension("current"),
    "n": Dimension("force"), "mn": Dimension("force"),
    "°c": Dimension("temperature"), "c": Dimension("temperature"),
    "k": Dimension("temperature"),
    "pc/n": Dimension("force") / Dimension("charge"),
    "v·m/n": Dimension("voltage") * Dimension("length") / Dimension("force"),
    "days": Dimension("time"), "weeks": Dimension("time"),
    "months": Dimension("time"),
    "mol/m^2": Dimension("amount_of_substance") / Dimension("length")**2,
    "kg": Dimension("mass"), "g": Dimension("mass"),
    "w/kg": Dimension("power") / Dimension("mass"),
    # compound units recorded in the canonical critical parameters
    "ml/min/mmhg": Dimension("volume") / Dimension("time") /
                   Dimension("pressure"),
    "mosm/kg": Dimension(1),  # osmolarity ratio (particle count per mass)
    "pc/n": Dimension("force") / Dimension("charge"),
    "v·m/n": Dimension("voltage") * Dimension("length") / Dimension("force"),
    "m/s^2": Dimension("length") / Dimension("time")**2,
    "ng/l": Dimension("mass") / Dimension("volume"),
    "µw/cm²": Dimension("power") / Dimension("length")**2,
    "uw/cm2": Dimension("power") / Dimension("length")**2,
    "µs": Dimension("time"),
}


def _unit_dimension(unit: str):
    """Map a recorded unit string to a sympy Dimension. Returns None when
    the unit string is unrecorded or unmapped (honest NOT_EVALUABLE)."""
    if not unit:
        return None
    u = str(unit).strip().lower()
    if u in ("unknown", "not_recorded", "n/a", ""):
        return None
    if u in _UNIT_MAP:
        return _UNIT_MAP[u]
    # "MODELLED (4 in V0 prototype)" etc. — units that aren't pure units
    return None


_IDENT_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def _symbols_in(math_expr: str) -> list:
    return sorted(set(_IDENT_RE.findall(math_expr or "")))


def _symbol_units(math_expr: str, critical_parameters: list) -> dict:
    """Assign recorded units to expression symbols. A symbol gets a unit
    only when a recorded critical-parameter name contains that symbol as a
    whole identifier token AND that parameter carries a unit. No guessing."""
    units = {}
    syms = _symbols_in(math_expr)
    for sym in syms:
        for cp in critical_parameters:
            name_tokens = _IDENT_RE.findall(cp.get("name") or "")
            if sym in name_tokens:
                dim = _unit_dimension(cp.get("unit"))
                if dim is not None:
                    units[sym] = (cp.get("name"), cp.get("unit"), dim)
                break
    return units


def _parse_side(expr: str):
    """Parse one side of an equation with sympy. Returns (expr, error)."""
    try:
        local = {s: sympy.Symbol(s) for s in _symbols_in(expr)}
        return sympy.parse_expr(expr, local_dict=local,
                                transformations="all"), None
    except Exception as e:  # syntax errors are expected for prose strings
        return None, f"SYMPY_PARSE_ERROR: {str(e)[:80]}"


def dimensional_check(math_expr: str, critical_parameters: list) -> dict:
    """Dimensional-consistency check for one equation (canonical ASCII math
    expression, annotation/label already removed)."""
    if not math_expr or not math_expr.strip():
        return {"state": "NOT_EVALUABLE_SYNTAX",
                "reason": "empty expression"}
    if "=" not in math_expr:
        return {"state": "NOT_EVALUABLE_NO_EQUALITY",
                "reason": "expression contains no '=' relation "
                          "(definition or inequality, not an equality "
                          "to check)"}
    lhs, rhs = math_expr.split("=", 1)
    lhs_expr, err1 = _parse_side(lhs)
    rhs_expr, err2 = _parse_side(rhs)
    if err1 or err2:
        return {"state": "NOT_EVALUABLE_SYNTAX",
                "reason": err1 or err2}

    syms = _symbols_in(math_expr)
    units = _symbol_units(math_expr, critical_parameters)
    # functions (exp, log, sqrt...) and dimensionless numerals are fine;
    # every FREE symbol needs a recorded unit
    free = set()
    for side in (lhs_expr, rhs_expr):
        try:
            free |= {str(s) for s in side.free_symbols}
        except Exception:
            pass
    missing = sorted(free - set(units))
    if missing:
        return {
            "state": "NOT_EVALUABLE_UNITS_UNRECORDED",
            "reason": (
                f"no recorded unit for symbol(s): {', '.join(missing[:8])}. "
                "Units are taken ONLY from recorded critical parameters "
                "(standard-symbol guesses are not used — Constitution "
                "Art. VI)."
            ),
            "symbols_with_recorded_units": sorted(units),
            "symbols_without_recorded_units": missing,
        }

    # substitute dimensions and compare dimensional dependencies
    from sympy.physics.units.systems.si import dimsys_SI
    subs = {sympy.Symbol(s): units[s][2] for s in units}
    try:
        dl = sympy.simplify(lhs_expr.subs(subs))
        dr = sympy.simplify(rhs_expr.subs(subs))
        dep_l = dimsys_SI.get_dimensional_dependencies(dl)
        dep_r = dimsys_SI.get_dimensional_dependencies(dr)
    except TypeError as e:
        # Dimension algebra error: incompatible dimensions combined by
        # + or - inside one side — that IS an inconsistency
        return {
            "state": "DIMENSIONALLY_INCONSISTENT",
            "reason": f"dimensionally incompatible operation between "
                      f"different dimensions: {str(e)[:80]}",
            "symbol_units": {s: units[s][1] for s in sorted(units)},
        }
    except Exception as e:
        return {"state": "NOT_EVALUABLE_SYNTAX",
                "reason": f"dimension substitution failed: {str(e)[:80]}"}
    if dict(dep_l) == dict(dep_r):
        return {"state": "DIMENSIONALLY_CONSISTENT",
                "reason": "LHS and RHS dimensions agree under recorded units",
                "symbol_units": {s: units[s][1] for s in sorted(units)}}
    return {
        "state": "DIMENSIONALLY_INCONSISTENT",
        "reason": "LHS and RHS dimensions DISAGREE under recorded units — "
                  "surfaced for engineering review (never hidden)",
        "lhs_dimension": str(dl),
        "rhs_dimension": str(dr),
        "symbol_units": {s: units[s][1] for s in sorted(units)},
    }


def validate_equation(entry: dict, pkg) -> dict:
    """Full R372-3 validation record for one registry entry."""
    math_expr = entry.get("math_expression") or ""
    gm = pkg.gm
    if entry.get("rendering_note") == "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM":
        dim = {"state": "NOT_EVALUABLE_CORRUPTED_STRING",
               "reason": "canonical string is corrupted (annotation "
                         "boundary unrecoverable); preserved verbatim, "
                         "never repaired (Art. VI)"}
    else:
        dim = dimensional_check(math_expr, pkg.critical_parameters)

    variables = entry.get("variables", [])
    return {
        "equation_id": entry["equation_id"],
        "variables": variables,
        "variable_units": [
            {"symbol": v.get("symbol"), "unit": v.get("unit"),
             "recorded_name": v.get("recorded_name")}
            for v in variables
        ],
        "domain": pkg.dossier.get("engineering_content", {}).get(
            "technology_domain", "NOT_RECORDED"),
        "operating_regime": gm.get("boundary_conditions", []),
        "assumptions": gm.get("assumptions", []),
        "applicability": gm.get("boundary_conditions", []),
        "limitations": gm.get("failure_regimes", []),
        "dimensional_check": dim,
    }


def validate_registry(registry: dict, pkg) -> dict:
    """Attach R372 validation to an EQUATION_REGISTRY (returns a NEW dict;
    the registry itself is not mutated here)."""
    validations = [validate_equation(e, pkg) for e in registry["equations"]]
    counts = {}
    for v in validations:
        counts[v["dimensional_check"]["state"]] = \
            counts.get(v["dimensional_check"]["state"], 0) + 1
    return {
        "schema": "R372_EQUATION_VALIDATION",
        "package_id": pkg.pkg_id,
        "equation_count": len(validations),
        "dimensional_state_counts": counts,
        "inconsistent_equations": [
            v["equation_id"] for v in validations
            if v["dimensional_check"]["state"] == "DIMENSIONALLY_INCONSISTENT"],
        "validations": validations,
    }


def validation_complete(v: dict) -> bool:
    """An equation validation is COMPLETE when every required metadata
    field is present (non-empty or explicit NOT_RECORDED) and the
    dimensional check state is an allowed explicit state."""
    required = ["variables", "variable_units", "domain", "operating_regime",
                "assumptions", "applicability", "limitations",
                "dimensional_check"]
    if any(k not in v for k in required):
        return False
    allowed = {
        "DIMENSIONALLY_CONSISTENT", "DIMENSIONALLY_INCONSISTENT",
        "NOT_EVALUABLE_SYNTAX", "NOT_EVALUABLE_UNITS_UNRECORDED",
        "NOT_EVALUABLE_NO_EQUALITY", "NOT_EVALUABLE_CORRUPTED_STRING",
    }
    return v["dimensional_check"].get("state") in allowed
