"""
equation_status.py — CEO R374-2 + R374-3: equation-status language
correction and source-backed units.

R374-2 (status language):
  The R372 gate reported "66/66 equation validation (66 validated, 0
  inconsistent)". That sentence conflates three different claims. The
  dimensional state counts in the same shipped registries honestly say:
  0 equations dimensionally checked as consistent, 51 blocked by
  unrecorded units, 8 unparseable, 7 non-equalities. Reporting "validated"
  while the dimensional level is unproven is a silent semantic promotion
  (Constitution Art. XXVIII) — this module splits the claim into three
  SEPARATE, independently proven levels:

    STRUCTURAL_VALIDATION      the canonical math string parses into a
                               well-formed mathematical relation (both
                               sides of an equality parse, or the whole
                               string parses as a relation/inequality)
    APPLICABILITY_VALIDATION   the applicability envelope is fully
                               recorded: domain, operating regime
                               (boundary conditions), assumptions,
                               applicability, limitations (known failure
                               regimes), source — every field present,
                               non-empty or explicitly NOT_RECORDED
    DIMENSIONAL_VALIDATION     unit algebra was actually performed under
                               RECORDED units and LHS/RHS dimensions agree
                               (DIMENSIONALLY_CONSISTENT). NOT_EVALUABLE
                               states are NOT proof — they are reported
                               as not-proven with the recorded reason
                               (Art. XXV: unknown is not verified).

  An equation may be reported as "validated" ONLY at a level that is
  proven. The bare word "validated" for an equation whose dimensional
  level is unproven is a forbidden claim (checked mechanically in
  acceptance_r374.py).

R374-3 (units):
  Every FREE SYMBOL of every equation carries a unit status:

    SOURCE_BACKED   a unit is recorded in the canonical engineering
                    record (R370Q export critical_parameters) for a
                    critical parameter whose recorded name contains the
                    symbol; the recorded basis (e.g. DESIGN_CHOICE,
                    MODELLED) is disclosed. SOURCE_BACKED means
                    "recorded in the canonical source" — it does NOT
                    mean physically measured.
    UNKNOWN         no unit is recorded for that symbol anywhere in the
                    canonical record. A resolution path states exactly
                    what would resolve it. Units are never invented
                    (Constitution Art. VI) — standard-symbol guesses
                    (r = metres, eta = Pa*s) are not used.

No R371/R372/R373 gate is lowered by this module; it adds the honest
level split on top of the unchanged validation machinery.
"""

import re

import sympy

from ..r372.equation_validation import (
    _parse_side,
    _symbol_units,
    _symbols_in,
)

# ---------------------------------------------------------------------------
# R374-2: the three validation levels
# ---------------------------------------------------------------------------

_LEVEL_DEFINITIONS = {
    "STRUCTURAL_VALIDATION": (
        "The canonical math string parses into a well-formed mathematical "
        "relation (both sides of an equality parse with sympy, or the "
        "whole string parses as a relation). Proven independently of any "
        "unit information."
    ),
    "APPLICABILITY_VALIDATION": (
        "The applicability envelope is fully recorded in the canonical "
        "engineering record: domain, operating regime (boundary "
        "conditions), assumptions, applicability, limitations (known "
        "failure regimes) and source provenance — every field present, "
        "non-empty or explicitly NOT_RECORDED."
    ),
    "DIMENSIONAL_VALIDATION": (
        "Unit algebra was actually performed under RECORDED units and the "
        "LHS and RHS dimensions agree (state DIMENSIONALLY_CONSISTENT). "
        "NOT_EVALUABLE_* states are not proof and are reported as "
        "not-proven with the recorded reason — never as a pass (Art. XXV)."
    ),
}

_APPLICABILITY_FIELDS = ("domain", "operating_regime", "assumptions",
                         "applicability", "limitations", "source")


def _structural_check(math_expr: str, rendering_note) -> dict:
    """Level 1 — does the canonical string parse as math?"""
    if rendering_note == "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM":
        return {"proven": False,
                "basis": "canonical string corrupted (annotation boundary "
                         "unrecoverable); preserved verbatim, never "
                         "repaired (Art. VI)"}
    if not (math_expr or "").strip():
        return {"proven": False,
                "basis": "empty expression"}
    from ..r372.equation_validation import _parse_side, split_relation, \
        _normalize_notation
    math_expr = _normalize_notation(math_expr)
    rel = split_relation(math_expr)
    if rel is not None:
        # any relation operator (=, ~, >=, <=): both sides must parse
        # ('~' proportionality and '>=' comparisons included — the R394
        # fix; the old split-on-'=' broke 'sigma_TOA >= c / …')
        _lhs, _op, rhs = rel
        e1, err1 = _parse_side(_lhs)
        e2, err2 = _parse_side(rhs)
        if err1 or err2:
            return {"proven": False,
                    "basis": f"parse failed: {(err1 or err2)[:100]} "
                             "(canonical string retained verbatim)"}
        return {"proven": True,
                "basis": f"both sides of the recorded {_op!r} relation "
                         "parse as sympy expressions under the canonical "
                         "symbols"}
    # no '=': a relation/inequality string — structural ONLY if the whole
    # string parses as a genuine sympy RELATIONAL (Re < 2300). A bare
    # expression parse is NOT accepted: sympy auto-symbols English words
    # into implicit multiplication ("flow proportional to ..." would
    # otherwise fake a pass — caught here, Art. XXX).
    try:
        func_names = set(re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\(",
                                    math_expr))
        local = {}
        for s in _symbols_in(math_expr):
            if s in func_names:
                local[s] = sympy.Function(s)
            else:
                local[s] = sympy.Symbol(s)
        expr = sympy.parse_expr(math_expr, local_dict=local,
                                transformations="all")
        is_rel = isinstance(expr, sympy.logic.boolalg.Boolean) or \
            expr.has(sympy.Eq, sympy.StrictLessThan, sympy.LessThan,
                     sympy.StrictGreaterThan, sympy.GreaterThan)
        if is_rel:
            return {"proven": True,
                    "basis": "string parses as a well-formed mathematical "
                             "relation (no equality to dimension-check — "
                             "recorded as-is)"}
        return {"proven": False,
                "basis": "parses as a bare expression, not a relation "
                         "(prose/auto-symbolized string preserved "
                         "verbatim — not claimed as canonical math)"}
    except Exception as e:
        return {"proven": False,
                "basis": f"parse failed: {str(e)[:100]} (canonical string "
                         "retained verbatim)"}


def _applicability_check(validation: dict) -> dict:
    """Level 2 — is the applicability envelope fully recorded?"""
    missing = []
    for f in _APPLICABILITY_FIELDS:
        v = validation.get(f)
        if v is None or v == "" or v == [] or v == {}:
            missing.append(f)
    if missing:
        return {"proven": False,
                "basis": f"field(s) absent from the canonical record: "
                         f"{', '.join(missing)}"}
    return {"proven": True,
            "basis": "domain, operating regime (boundary conditions), "
                     "assumptions, applicability, limitations (failure "
                     "regimes) and source all present in the canonical "
                     "engineering record"}


def _dimensional_check(validation: dict) -> dict:
    """Level 3 — was unit algebra actually performed and did it pass?"""
    dc = validation.get("dimensional_check", {}) or {}
    state = dc.get("state", "")
    if state == "DIMENSIONALLY_CONSISTENT":
        return {"proven": True, "state": state,
                "basis": dc.get("reason", "LHS/RHS dimensions agree under "
                                          "recorded units")}
    reason = dc.get("reason", "no dimensional check recorded")
    return {"proven": False, "state": state,
            "basis": f"{state}: {reason}" if state else reason}


def equation_levels(entry: dict, validation: dict) -> dict:
    """Three-level validation status for one equation (R374-2)."""
    struct = _structural_check(entry.get("math_expression") or "",
                               entry.get("rendering_note"))
    applic = _applicability_check(validation)
    dim = _dimensional_check(validation)
    proven = [n for n, r in (("STRUCTURAL_VALIDATION", struct),
                             ("APPLICABILITY_VALIDATION", applic),
                             ("DIMENSIONAL_VALIDATION", dim)) if r["proven"]]
    summary = "+".join(proven) if proven else "NONE_PROVEN"
    return {
        "equation_id": entry.get("equation_id"),
        "structural_validation": struct,
        "applicability_validation": applic,
        "dimensional_validation": dim,
        "levels_proven": proven,
        "status_summary": (
            f"validated at: {summary}. 'Validated' never implies an "
            f"unproven level (CEO R374-2; Art. XXVIII)."),
    }


# ---------------------------------------------------------------------------
# R374-3: per-symbol unit status
# ---------------------------------------------------------------------------

def _resolution_path(symbol: str, pkg) -> str:
    """What would resolve an UNKNOWN unit — recorded, never invented."""
    name_hint = ""
    for cp in pkg.critical_parameters:
        if symbol in re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\b",
                                cp.get("name") or ""):
            name_hint = (f" for critical parameter "
                         f"'{cp.get('name')}' (recorded value: "
                         f"{str(cp.get('value'))[:60]})")
            break
    return (f"Record the unit for symbol '{symbol}'{name_hint} in the "
            f"canonical engineering record (critical_parameters), or "
            f"measure it on the package's bench prototype per its "
            f"engineering build plan; units are never guessed from "
            f"standard symbol conventions (Art. VI). With the unit "
            f"recorded, the dimensional-consistency check becomes "
            f"evaluable for this equation.")


def unit_status_table(entry: dict, pkg) -> list:
    """Per-symbol unit status for one equation (R374-3)."""
    math_expr = entry.get("math_expression") or ""
    if "=" not in math_expr:
        # non-equality strings still get their symbols reported
        syms = _symbols_in(math_expr)
        free = set(syms)
    else:
        lhs, rhs = math_expr.split("=", 1)
        free = set()
        for side in (lhs, rhs):
            ex, err = _parse_side(side)
            if ex is not None:
                try:
                    free |= {str(s) for s in ex.free_symbols}
                except Exception:
                    pass
        if not free:  # unparseable — report all identifiers honestly
            free = set(_symbols_in(math_expr))
    recorded = _symbol_units(math_expr, pkg.critical_parameters)
    table = []
    for sym in sorted(free):
        if sym in recorded:
            name, unit, _dim = recorded[sym]
            table.append({
                "symbol": sym,
                "unit": unit,
                "unit_status": "SOURCE_BACKED",
                "unit_source": {
                    "origin": "canonical engineering record "
                              "(critical_parameters)",
                    "recorded_parameter": name,
                    "recorded_unit": unit,
                    "recorded_basis": next(
                        (cp.get("basis") for cp in pkg.critical_parameters
                         if cp.get("name") == name), "NOT_RECORDED"),
                },
                "note": "SOURCE_BACKED = recorded in the canonical source; "
                        "not necessarily physically measured",
            })
        else:
            table.append({
                "symbol": sym,
                "unit": None,
                "unit_status": "UNKNOWN",
                "resolution_path": _resolution_path(sym, pkg),
            })
    return table


# ---------------------------------------------------------------------------
# registry augmentation (called by build_v5 right after r372_validation)
# ---------------------------------------------------------------------------

def attach_r374_status(registry: dict, pkg) -> dict:
    """Attach the R374 three-level status + unit table to a registry that
    already carries r372_validation (validations aligned by equation_id)."""
    val_by_id = {v["equation_id"]: v
                 for v in registry.get("r372_validation",
                                       {}).get("validations", [])}
    per_eq, units_rows = [], []
    struct_n = applic_n = dim_n = 0
    unit_states = {"SOURCE_BACKED": 0, "UNKNOWN": 0}
    for entry in registry.get("equations", []):
        v = val_by_id.get(entry["equation_id"], {})
        levels = equation_levels(entry, v)
        per_eq.append(levels)
        if levels["structural_validation"]["proven"]:
            struct_n += 1
        if levels["applicability_validation"]["proven"]:
            applic_n += 1
        if levels["dimensional_validation"]["proven"]:
            dim_n += 1
        utable = unit_status_table(entry, pkg)
        entry.setdefault("r374_unit_status", utable)  # per-equation copy
        for row in utable:
            unit_states[row["unit_status"]] = \
                unit_states.get(row["unit_status"], 0) + 1
        units_rows.append({"equation_id": entry["equation_id"],
                           "symbols": utable})
    n = len(registry.get("equations", []))
    inconsistent_n = sum(
        1 for e in per_eq
        if e["dimensional_validation"]["state"] == "DIMENSIONALLY_INCONSISTENT")
    not_evaluable_n = sum(
        1 for e in per_eq
        if not e["dimensional_validation"]["proven"]
        and e["dimensional_validation"]["state"] !=
        "DIMENSIONALLY_INCONSISTENT")
    registry["r374_validation_status"] = {
        "schema": "R374_EQUATION_VALIDATION_LEVELS",
        "package_id": pkg.pkg_id,
        "level_definitions": _LEVEL_DEFINITIONS,
        "language_rule": (
            "An equation is reported as validated ONLY at a level that is "
            "proven for that equation. The word 'validated' never implies "
            "an unproven level; DIMENSIONAL_VALIDATION is never implied by "
            "STRUCTURAL or APPLICABILITY validation (CEO R374-2; "
            "Constitution Art. XXVIII)."),
        "totals": {
            "equations": n,
            "structural_validated": struct_n,
            "applicability_validated": applic_n,
            "dimensionally_validated": dim_n,
            "dimensional_not_evaluable": not_evaluable_n,
            "dimensionally_inconsistent": inconsistent_n,
        },
        "honest_summary": (
            f"{n} canonical equations. Structural validation proven for "
            f"{struct_n}; applicability validation proven for {applic_n}; "
            f"DIMENSIONAL validation proven for {dim_n} — the dimensional "
            f"level is honestly NOT proven for the remainder (units "
            f"unrecorded in the canonical record for most symbols: "
            f"{unit_states.get('SOURCE_BACKED', 0)} of "
            f"{unit_states.get('SOURCE_BACKED', 0) + unit_states.get('UNKNOWN', 0)} "
            f"equation symbols carry recorded units). This is the honest "
            f"state of an ENGINEERING_DEFINITION package; populating the "
            f"unit fields is buyer-side engineering development recorded "
            f"in the unknown roadmaps."),
        "unit_coverage": unit_states,
        "equations": per_eq,
    }
    return registry


# ---------------------------------------------------------------------------
# forbidden-language rule (mechanical, applied to release artifacts)
# ---------------------------------------------------------------------------

# The exact defect R374-2 corrects: a numeric "validated" claim about
# equations whose sentence does not name WHICH level is proven.
_CLAIM_PATTERNS = [
    # "66 validated" / "0 validated"
    re.compile(r"\b\d+\s+validated\b", re.I),
    # "equations validated" / "all 66 equations are validated"
    re.compile(r"\b(?:all\s+)?\d*\s*equations?\s+(?:are\s+)?validated\b",
               re.I),
    # "66/66 equation validation" (a fraction-of-total validation claim)
    re.compile(r"\b\d+\s*/\s*\d+\s+equations?\s+validation\b", re.I),
]
_LEVEL_WORDS = re.compile(
    r"STRUCTURAL_VALIDATION|APPLICABILITY_VALIDATION|"
    r"DIMENSIONAL_VALIDATION|structural|applicability|dimensional", re.I)


def bare_validated_claims(text: str) -> list:
    """Every numeric/total 'equations validated' claim whose surrounding
    context does not name the validation level. A claim naming a level is
    legitimate; a bare claim is the R374-2 defect (semantic promotion)."""
    offenders = []
    for pat in _CLAIM_PATTERNS:
        for m in pat.finditer(text or ""):
            window = text[max(0, m.start() - 250):m.end() + 250]
            if not _LEVEL_WORDS.search(window):
                offenders.append(m.group(0))
    # de-duplicate, preserve order
    seen, out = set(), []
    for o in offenders:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out
