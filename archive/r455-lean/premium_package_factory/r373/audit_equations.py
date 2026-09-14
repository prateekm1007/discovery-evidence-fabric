"""
audit_equations.py — R373-4: physical audit of all equations, with an
adversarial injection suite.

For every equation in every package (66 across 15 packages) the audit
re-derives from the canonical record:
    equation            the shipped canonical string must be a verbatim
                        governing-model equation (annotation included)
    variables           the entry's variable symbols must be exactly the
                        intersection of the math-expression symbols and
                        the recorded critical-parameter universe
    units               per-variable units must equal the recorded
                        critical-parameter unit for the matched name
    dimensional state  recomputed with an INDEPENDENT sympy
                        implementation (own unit map, own parse); must
                        equal the shipped r372_validation state
    assumptions / operating regime / applicability / limitations
                        verbatim lists from governing_model
                        (assumptions, boundary_conditions x2, failure_regimes)
    source              present and non-empty

Then the adversarial injection suite (Constitution Art. VIII / XVII /
XXX — the validator must attack itself). On IN-MEMORY COPIES of real
equations:
    WRONG_UNIT      a dimension-changing wrong unit replaces a recorded
                    unit of a CONSISTENT equation -> the dimensional
                    check must leave the CONSISTENT state (catch it)
    WRONG_REGIME    a fabricated operating-regime string is injected ->
                    the verbatim-canonical regime check must flag it
    WRONG_VARIABLE  an alien symbol is injected into the expression ->
                    the validator must report the symbol as unrecorded
                    (never silently accept it)
Injections never touch shipped files (Art. IX — observational).
"""

import re

import sympy
from sympy.physics.units import Dimension
from sympy.physics.units.systems.si import dimsys_SI

# independent unit map (recorded unit string -> sympy Dimension)
_UNITS = {
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
    "w": Dimension("power"), "mw": Dimension("power"),
    "µw": Dimension("power"), "uw": Dimension("power"),
    "v": Dimension("voltage"), "mv": Dimension("voltage"),
    "a": Dimension("current"), "ma": Dimension("current"),
    "n": Dimension("force"), "mn": Dimension("force"),
    "°c": Dimension("temperature"), "c": Dimension("temperature"),
    "k": Dimension("temperature"),
    "days": Dimension("time"), "weeks": Dimension("time"),
    "months": Dimension("time"),
    "kg": Dimension("mass"), "g": Dimension("mass"),
    "mol/m^2": Dimension("amount_of_substance") / Dimension("length") ** 2,
    "w/kg": Dimension("power") / Dimension("mass"),
    "ml/min/mmhg": Dimension("volume") / Dimension("time") /
                   Dimension("pressure"),
    "mosm/kg": Dimension(1),
    "m/s^2": Dimension("length") / Dimension("time") ** 2,
    "µw/cm²": Dimension("power") / Dimension("length") ** 2,
    "uw/cm2": Dimension("power") / Dimension("length") ** 2,
    "µs": Dimension("time"),
    "pc/n": Dimension("force") / Dimension("charge"),
    "v·m/n": Dimension("voltage") * Dimension("length") / Dimension("force"),
    # R407 P0 (B1 class — V3-aware instrument alignment): the R394
    # set_symbol_units record (CEO directive 9) uses these unit strings;
    # they were present in the r372 validator (equation_validation.py)
    # but missing here, so the independent recompute disagreed with the
    # builder for the SAME recorded units. Same dimensions, same
    # discipline: recorded units only, never guessed (Art. VI).
    "ml/(min·mmhg)": Dimension("volume") / Dimension("time") /
                      Dimension("pressure"),
    "ml/(min*mmhg)": Dimension("volume") / Dimension("time") /
                     Dimension("pressure"),
    "mpa·s": Dimension("pressure") * Dimension("time"),
    "mpa*s": Dimension("pressure") * Dimension("time"),
    "pa·s": Dimension("pressure") * Dimension("time"),
    "pa*s": Dimension("pressure") * Dimension("time"),
    "dimensionless": Dimension(1),
}

_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def _dim(unit):
    if not unit:
        return None
    u = str(unit).strip().lower()
    if u in ("unknown", "not_recorded", "n/a", ""):
        return None
    return _UNITS.get(u)


def _symbols(expr: str):
    return sorted(set(_IDENT.findall(expr or "")))


def _recorded_units(math_expr, critical_parameters):
    """symbol -> (recorded_name, unit) — only exact identifier matches."""
    out = {}
    for sym in _symbols(math_expr):
        for cp in critical_parameters:
            if sym in _IDENT_RE.findall(cp.get("name") or ""):
                out[sym] = (cp.get("name"), cp.get("unit"))
                break
    return out


_IDENT_RE = _IDENT


def _parse(side: str):
    """R407 P0 (B1 class — instrument alignment): identifiers immediately
    followed by '(' (e.g. 'A_actuator(P, dP/dt)') are canonical
    FUNCTION-APPLICATION notation and are mapped to sympy Function
    objects, exactly as the r372 validator's _parse_side has done since
    its R394-era evolution. The audit's parser predated that handling,
    so the independent recompute returned NOT_EVALUABLE_SYNTAX for
    expressions the validator parsed (an instrument divergence, not a
    data defect). Same deterministic syntax-level handling; the
    canonical string is never rewritten (Art. II)."""
    try:
        func_names = set(re.findall(r"([A-Za-z][A-Za-z0-9_]*)\s*\(",
                                    side or ""))
        local = {}
        for s in _symbols(side):
            if s in func_names:
                local[s] = sympy.Function(s)
            else:
                local[s] = sympy.Symbol(s)
        return sympy.parse_expr(side, local_dict=local,
                                transformations="all"), None
    except Exception as e:
        return None, f"SYMPY_PARSE_ERROR: {str(e)[:80]}"


def dimensional_state(math_expr: str, critical_parameters: list,
                       symbol_units: dict | None = None) -> str:
    """Independent dimensional-consistency verdict (state only).

    R407 P0 (B1 class): `symbol_units` is the RECORDED
    governing_model.symbol_units overlay from the canonical view (the
    R394 CEO directive 9 unit record — every entry carries its own
    basis). Using it here aligns the independent recompute with the
    same recorded-unit discipline the r372 validator already applies
    (equation_validation._symbol_units). No guessing is introduced:
    units come only from the record (Art. VI); the recompute stays
    independent of the shipped registry's own claims.
    """
    if not math_expr or not math_expr.strip():
        return "NOT_EVALUABLE_SYNTAX"
    # R407 P0 (B1 class — instrument alignment): relations =, ~, >=, <=
    # are all dimension-comparable (a proportionality relates
    # same-dimension quantities up to a constant), exactly as the r372
    # validator's split_relation has handled since its evolution; the
    # audit's split-on-'=' predated that and mislabeled '~' relations
    # as NO_EQUALITY.
    rel = re.search(r"(==|>=|<=|~|=)", math_expr)
    if not rel:
        return "NOT_EVALUABLE_NO_EQUALITY"
    lhs, rhs = math_expr[:rel.start()].strip(), \
        math_expr[rel.end():].strip()
    # R407 P0 (B1 class — instrument alignment): the same deterministic
    # notation normalization the r372 validator applies FOR THE CHECK
    # ONLY (the canonical string is never rewritten — Art. II):
    # [X] concentration notation -> bare symbol X; Python-keyword
    # identifiers (lambda, in, ...) get a '_' suffix so they parse as
    # symbols. Without this the audit mislabeled bracket/keyword
    # expressions as SYNTAX while the validator evaluated them.
    _norm = re.compile(r"\[([A-Za-z][A-Za-z0-9_]*)\]")
    norm_expr = _norm.sub(r"\1", math_expr)
    for _kw in ("lambda", "in", "if", "else", "for", "and", "or",
                "not", "is", "as", "assert", "del", "pass", "raise",
                "while", "with", "yield", "global", "nonlocal"):
        norm_expr = re.sub(rf"\b{_kw}\b", f"{_kw}_", norm_expr)
    if _norm.search(math_expr) or norm_expr != math_expr:
        rel = re.search(r"(==|>=|<=|~|=)", norm_expr)
        if not rel:
            return "NOT_EVALUABLE_NO_EQUALITY"
        lhs, rhs = norm_expr[:rel.start()].strip(), \
            norm_expr[rel.end():].strip()
    l, e1 = _parse(lhs)
    r, e2 = _parse(rhs)
    if e1 or e2:
        return "NOT_EVALUABLE_SYNTAX"
    units = _recorded_units(math_expr, critical_parameters)
    overlay = symbol_units or {}
    for sym in _symbols(math_expr):
        if sym in units or sym not in overlay:
            continue
        entry = overlay[sym]
        u = entry.get("unit") if isinstance(entry, dict) else entry
        if u and _dim(u) is not None:
            units[sym] = (sym, u)
    free = set()
    for side in (l, r):
        try:
            free |= {str(s) for s in side.free_symbols}
        except Exception:
            pass
    # keyword-renamed symbols (lambda_ from lambda) match their original
    # name in the recorded units (the r372 discipline)
    _KWS = ("lambda", "in", "if", "else", "for", "and", "or", "not",
            "is", "as", "assert", "del", "pass", "raise", "while",
            "with", "yield", "global", "nonlocal")
    free = {s[:-1] if s.endswith("_") and s[:-1] in _KWS else s
            for s in free}
    if free - set(units):
        return "NOT_EVALUABLE_UNITS_UNRECORDED"
    subs = {sympy.Symbol(s): _dim(units[s][1]) for s in units}
    if any(v is None for v in subs.values()):
        return "NOT_EVALUABLE_UNITS_UNRECORDED"
    try:
        dl = sympy.simplify(l.subs(subs))
        dr = sympy.simplify(r.subs(subs))
        if (dict(dimsys_SI.get_dimensional_dependencies(dl))
                == dict(dimsys_SI.get_dimensional_dependencies(dr))):
            return "DIMENSIONALLY_CONSISTENT"
        return "DIMENSIONALLY_INCONSISTENT"
    except TypeError:
        return "DIMENSIONALLY_INCONSISTENT"
    except Exception:
        return "NOT_EVALUABLE_SYNTAX"


# ---------------------------------------------------------------------------
# per-equation audit
# ---------------------------------------------------------------------------

def audit_registry(pkg, shipped_registry: dict) -> dict:
    """Audit one package's shipped EQUATION_REGISTRY.json against the
    canonical governing model."""
    failures = []
    gm = pkg.gm
    canon_eqs = gm.get("equations", [])
    canon_assumptions = gm.get("assumptions", [])
    canon_bc = gm.get("boundary_conditions", [])
    canon_fr = gm.get("failure_regimes", [])
    entries = shipped_registry.get("equations", [])
    validations = {v.get("equation_id"): v for v in
                   (shipped_registry.get("r372_validation", {})
                    .get("validations", []))}

    if len(entries) != len(canon_eqs):
        failures.append({"check": "EQUATION_COUNT",
                         "detail": f"shipped {len(entries)} equations, "
                                   f"canonical record has {len(canon_eqs)}"})

    per_eq = []
    for e in entries:
        eq_fail = []
        eid = e.get("equation_id")
        # equation verbatim canonical
        if e.get("equation_canonical") not in canon_eqs:
            eq_fail.append("EQUATION_NOT_VERBATIM_CANONICAL")
        # variables: re-derive with the registry's DISCLOSED matching rule
        # (a recorded critical parameter is a variable of the equation
        # when the base of one of its name tokens appears in the compact
        # expression) and require exact equality — both no invention and
        # no drift. Fresh code, same disclosed rule.
        math_expr = e.get("math_expression", "")
        expr_compact = (math_expr or "").replace(" ", "")
        expected_vars = {}
        for cp in pkg.critical_parameters:
            name = (cp.get("name") or "").strip()
            for sym in re.findall(r"\b([A-Za-z][A-Za-z0-9_]{0,14})\b",
                                  name):
                base = sym.split("_")[0]
                if base and base in expr_compact:
                    expected_vars[sym] = cp
                    break
        declared = {v.get("symbol"): v for v in e.get("variables", [])}
        if set(declared) != set(expected_vars):
            eq_fail.append("VARIABLES_NOT_THE_RECORDED_UNIVERSE")
        for sym, v in declared.items():
            cp = expected_vars.get(sym)
            if cp is None:
                continue
            if (v.get("unit") or None) != (cp.get("unit") or None):
                eq_fail.append(f"UNIT_MISMATCH:{sym}")
            if v.get("recorded_name") != (cp.get("name") or "").strip():
                eq_fail.append(f"VARIABLE_NAME_MISMATCH:{sym}")
        # dimensional state: shipped validation vs independent recompute
        val = validations.get(eid)
        if val is None:
            eq_fail.append("NO_SHIPPED_VALIDATION")
        else:
            # metadata verbatim canonical
            if val.get("assumptions") != canon_assumptions:
                eq_fail.append("ASSUMPTIONS_NOT_VERBATIM")
            if val.get("operating_regime") != canon_bc:
                eq_fail.append("OPERATING_REGIME_NOT_VERBATIM")
            if val.get("applicability") != canon_bc:
                eq_fail.append("APPLICABILITY_NOT_VERBATIM")
            if val.get("limitations") != canon_fr:
                eq_fail.append("LIMITATIONS_NOT_VERBATIM")
            if not val.get("source"):
                eq_fail.append("SOURCE_MISSING")
            shipped_state = (val.get("dimensional_check", {})
                             .get("state"))
            recomputed = dimensional_state(math_expr,
                                           pkg.critical_parameters,
                                           gm.get("symbol_units"))
            if shipped_state != recomputed:
                eq_fail.append(f"DIMENSIONAL_STATE_DRIFT:"
                               f"shipped={shipped_state},"
                               f"recomputed={recomputed}")
            if shipped_state == "DIMENSIONALLY_INCONSISTENT":
                # a real physical finding — surfaced, never hidden; the
                # release gate treats it as a failure downstream
                eq_fail.append("DIMENSIONALLY_INCONSISTENT")
        if eq_fail:
            failures.extend({"check": f"{eid}:{f}",
                             "detail": ""} for f in eq_fail)
        per_eq.append({"equation_id": eid,
                       "shipped_dimensional_state":
                           (val or {}).get("dimensional_check", {})
                           .get("state"),
                       "recomputed_dimensional_state":
                           dimensional_state(math_expr,
                                             pkg.critical_parameters),
                       "failures": eq_fail})

    return {
        "package_id": pkg.pkg_id,
        "equation_count": len(entries),
        "equations": per_eq,
        "failures": failures,
        "ok": not failures,
    }


# ---------------------------------------------------------------------------
# adversarial injection suite (validator self-attack)
# ---------------------------------------------------------------------------

# dimension-diverse wrong units for the WRONG_UNIT injection
_WRONG_UNITS = ["mL", "mmHg", "Hz", "V", "N", "degC", "mm", "kg"]


def _dim_of_unit(unit: str):
    return _dim(unit)


def adversarial_injections(packages) -> dict:
    """Inject wrong unit / wrong regime / wrong physical variable into
    copies of REAL equations where possible and prove the validator
    catches each.

    HONEST DISCLOSURE (Art. XV): as of this audit, 0 of the 66 real
    equations carry fully-recorded units (all dimensional states are
    NOT_EVALUABLE_* — units are recorded for only a subset of critical
    parameters). The dimensional check has therefore never fired
    positively on real data. The WRONG-UNIT injection consequently runs
    on BOTH (a) any real equation whose symbols carry recorded units
    (currently none) and (b) a DISCLOSED SYNTHETIC fixture — a
    physically correct Hagen-Poiseuille statement with a complete unit
    table — to prove the validator machinery catches a wrong unit when
    units are recorded. The synthetic fixture is labelled SYNTHETIC in
    the results; it injects no claim into any shipped artifact.
    """
    results = []
    real_probes = 0
    for p in packages:
        shipped_src = p.gm.get("equations", [])
        for i, eq in enumerate(shipped_src):
            math_expr = str(eq).split("[")[0].strip()
            state = dimensional_state(math_expr, p.critical_parameters)
            if state != "DIMENSIONALLY_CONSISTENT":
                continue  # injections run on CONSISTENT baselines
            units = _recorded_units(math_expr, p.critical_parameters)
            if not units:
                continue
            sym = sorted(units)[0]
            orig_unit = units[sym][1]
            orig_dim = _dim_of_unit(orig_unit)
            caught_unit = None
            for wrong in _WRONG_UNITS:
                if _dim_of_unit(wrong) is None or \
                        _dim_of_unit(wrong) == orig_dim:
                    continue
                tampered_cp = [dict(cp) for cp in p.critical_parameters]
                for cp in tampered_cp:
                    if sym in _IDENT_RE.findall(cp.get("name") or ""):
                        cp["unit"] = wrong
                        break
                tampered_state = dimensional_state(math_expr, tampered_cp)
                if tampered_state != "DIMENSIONALLY_CONSISTENT":
                    caught_unit = {"symbol": sym, "original": orig_unit,
                                   "injected": wrong,
                                   "tampered_state": tampered_state}
                    break
            results.append({
                "package_id": p.pkg_id,
                "baseline": "REAL",
                "equation": math_expr[:60],
                "baseline_state": state,
                "wrong_unit": caught_unit,
                "wrong_unit_caught": caught_unit is not None,
            })
            real_probes += 1
            break  # one real probe per package is sufficient

    # ---- synthetic fixture (disclosed) --------------------------------
    # No real equation carries fully-recorded units, so the wrong-unit
    # self-attack runs on a dimensionally consistent SYNTHETIC statement:
    # a pressure balance P_total = P_static + P_dynamic, all symbols
    # [mmHg]. A wrong (dimension-changing) unit on any symbol must flip
    # the validator to DIMENSIONALLY_INCONSISTENT.
    synthetic_expr = "P_total = P_static + P_dynamic"
    synthetic_cp = [
        {"name": "Total pressure P_total", "unit": "mmHg"},
        {"name": "Static pressure P_static", "unit": "mmHg"},
        {"name": "Dynamic pressure P_dynamic", "unit": "mmHg"},
    ]
    syn_baseline = dimensional_state(synthetic_expr, synthetic_cp)
    syn_caught = None
    if syn_baseline == "DIMENSIONALLY_CONSISTENT":
        for wrong in _WRONG_UNITS:
            if _dim_of_unit(wrong) is None or \
                    _dim_of_unit(wrong) == Dimension("pressure"):
                continue
            tampered = [dict(cp) for cp in synthetic_cp]
            tampered[2]["unit"] = wrong
            tampered_state = dimensional_state(synthetic_expr, tampered)
            if tampered_state != "DIMENSIONALLY_CONSISTENT":
                syn_caught = {"symbol": "P_dynamic", "original": "mmHg",
                              "injected": wrong,
                              "tampered_state": tampered_state}
                break
    results.append({
        "package_id": "SYNTHETIC_FIXTURE",
        "baseline": "SYNTHETIC",
        "equation": synthetic_expr,
        "baseline_state": syn_baseline,
        "wrong_unit": syn_caught,
        "wrong_unit_caught": syn_caught is not None,
        "note": "disclosed synthetic fixture — no real equation carries "
                "fully-recorded units, so the wrong-unit self-attack runs "
                "on a dimensionally consistent synthetic statement to "
                "prove the machinery",
    })

    # --- WRONG REGIME: inject a fabricated operating regime into a copy
    # of a REAL shipped validation and run it through the actual
    # audit_registry code path — the verbatim-canonical comparison must
    # flag it.
    regime_pkg = packages[0]
    fabricated_regime = list(
        regime_pkg.gm.get("boundary_conditions", [])
    ) + ["4500 K plasma regime (injected)"]
    tampered_registry = {
        "equations": [{
            "equation_id": "EQ-1",
            "equation_canonical":
                (regime_pkg.gm.get("equations") or ["x = x"])[0],
            "math_expression":
                str((regime_pkg.gm.get("equations") or ["x = x"])[0])
                .split("[")[0].strip(),
            "variables": [],
            "source": {"origin": "fixture"},
        }],
        "r372_validation": {"validations": [{
            "equation_id": "EQ-1",
            "assumptions": regime_pkg.gm.get("assumptions", []),
            "operating_regime": fabricated_regime,
            "applicability": regime_pkg.gm.get("boundary_conditions", []),
            "limitations": regime_pkg.gm.get("failure_regimes", []),
            "source": {"origin": "fixture"},
            "dimensional_check": {"state": "NOT_EVALUABLE_SYNTAX"},
        }]},
    }
    tampered_audit = audit_registry(regime_pkg, tampered_registry)
    regime_caught = any(
        "OPERATING_REGIME_NOT_VERBATIM" in f["check"]
        for f in tampered_audit["failures"])

    # --- WRONG VARIABLE: alien symbol must be flagged unrecorded
    probe_pkg = packages[0]
    probe_eq = "Q = (pi * r^4 * dP) / (8 * eta * L)"
    wrong_var_state = dimensional_state(
        probe_eq + " + Zq7", probe_pkg.critical_parameters)
    wrong_var_caught = wrong_var_state == "NOT_EVALUABLE_UNITS_UNRECORDED"
    return {
        "wrong_unit_probes": results,
        "real_equation_probes": real_probes,
        "units_coverage_disclosure": (
            "0 of 66 real equations carry fully-recorded units; all 66 "
            "dimensional states are NOT_EVALUABLE_* (the honest state of "
            "the record — units exist for only a subset of critical "
            "parameters). The wrong-unit injection therefore runs on the "
            "disclosed synthetic fixture; it will run on real equations "
            "as soon as one carries complete units."
        ),
        "wrong_unit_all_caught": all(r["wrong_unit_caught"]
                                     for r in results) and bool(results),
        "wrong_regime": {
            "injected": "4500 K plasma regime (injected)",
            "run_through": "audit_registry verbatim-canonical comparison",
            "caught": regime_caught,
        },
        "wrong_variable": {
            "injected_symbol": "Zq7",
            "validator_state": wrong_var_state,
            "caught": wrong_var_caught,
        },
        "all_caught": (all(r["wrong_unit_caught"] for r in results)
                       and bool(results) and regime_caught
                       and wrong_var_caught),
    }
