"""Phase 8 — equation integrity audit (Coder 2).

Audits every generated equation for:

    equation_id / equation / variables / units / domain / applicability /
    assumptions / source

Detects:
    WRONG_DOMAIN              — equation judged for a different domain than
                                 the package's technology domain
    MISSING_VARIABLE          — expression variables not declared
    MISSING_APPLICABILITY     — no applicability condition recorded
    MISSING_ASSUMPTIONS       — no assumptions recorded
    MISSING_SOURCE            — no source identity (naked equation)
    UNSUPPORTED_SUBSTITUTION  — numeric substitution into a symbolic-only
                                 equation without sourced inputs
    COPIED_WITHOUT_APPLICABILITY — equation reused while its applicability
                                 condition contradicts the invention

A mathematically valid formula is NOT assumed appropriate to the invention
(CEO mandate Phase 8).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# canonical variable registry: equation library variables carry units
# (Coder 1 discovery_fabric/engine/equations.py is the runtime source; the
#  audit re-derives from the rendered artifact and falls back to expression
#  parsing so it never trusts the library blindly).
_VAR_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_NUMBER_RE = re.compile(r"(?<![A-Za-z_])\d+(?:\.\d+)?")
_SUBSCRIPT_TOKENS = {"pi", "sin", "cos", "tan", "log", "ln", "exp", "sqrt",
                     "max", "min", "delta"}


def audit_equations(eng_spec: Optional[dict],
                    floor_equations: Optional[int] = None) -> Dict[str, Any]:
    if not eng_spec:
        return {"available": False, "equations": [], "verdict":
                "NOT_MEASURABLE", "reason": "no engineering specification"}

    domain = eng_spec.get("technology_domain")
    gm = (eng_spec.get("engineering_core") or {}).get("governing_model") or {}
    eqs = [e for e in (gm.get("equations", []) or []) if isinstance(e, dict)]

    results: List[Dict[str, Any]] = []
    for eq in eqs:
        eid = eq.get("equation_id") or "UNNAMED"
        expr = eq.get("expression") or ""
        applic = eq.get("applicability") or {}
        source = eq.get("source") or {}
        issues: List[str] = []

        if not eq.get("equation_id"):
            issues.append("MISSING_EQUATION_ID")
        if not expr:
            issues.append("MISSING_EXPRESSION")

        # domain check
        judged = applic.get("judged_for_domain")
        if judged and domain and judged != domain:
            issues.append("WRONG_DOMAIN")

        # applicability
        if not applic.get("condition"):
            issues.append("MISSING_APPLICABILITY")

        # assumptions
        if not eq.get("assumptions"):
            issues.append("MISSING_ASSUMPTIONS")

        # source identity
        if not source.get("text"):
            issues.append("MISSING_SOURCE")

        # variable declaration (variables referenced vs declared)
        declared = {v.get("symbol") for v in (eq.get("variables") or [])
                    if isinstance(v, dict)}
        if declared:
            referenced = _vars_in(expr)
            undeclared = [v for v in referenced if v not in declared]
            if undeclared:
                issues.append(f"MISSING_VARIABLE:{','.join(undeclared)}")

        # unsupported numeric substitution into a symbolic-only model
        if _NUMBER_RE.search(expr) and not _is_dimensional_constant(expr):
            # numbers inside an equation expression require sourced inputs;
            # the engine's contract is SYMBOLIC_ONLY until inputs are sourced
            inputs_sourced = _inputs_sourced(eng_spec)
            if not inputs_sourced:
                issues.append("UNSUPPORTED_SUBSTITUTION")

        # copied without applicability: source is external precedent but
        # applicability epistemic class missing
        if source.get("epistemic_class") == "EXTERNAL_PRECEDENT" and \
                not applic.get("epistemic_class"):
            issues.append("COPIED_WITHOUT_APPLICABILITY")

        results.append({
            "equation_id": eid,
            "expression": expr,
            "variables_declared": sorted(v for v in declared if v),
            "domain_judged": judged,
            "package_domain": domain,
            "units_recorded": bool(eq.get("units") or
                                   any(isinstance(v, dict) and v.get("unit")
                                       for v in (eq.get("variables") or []))),
            "issues": issues,
            "verdict": "PASS" if not issues else "FAIL",
        })

    n_bad = sum(1 for r in results if r["verdict"] == "FAIL")
    count_floor_issue = None
    if floor_equations is not None and len(results) < floor_equations:
        count_floor_issue = (f"EQUATION_COUNT_BELOW_FLOOR: {len(results)} "
                             f"< corpus floor {floor_equations}")
    verdict = "NOT_MEASURABLE"
    if results or count_floor_issue:
        verdict = "FAIL" if (n_bad or count_floor_issue) else "PASS"
    return {
        "available": True,
        "equations_total": len(results),
        "equations_with_issues": n_bad,
        "count_floor_issue": count_floor_issue,
        "equations": results,
        "verdict": verdict,
        "note": "a mathematically valid formula is not assumed appropriate; "
                "domain/applicability/assumption linkage is audited per "
                "equation",
    }


def _vars_in(expr: str) -> List[str]:
    out = []
    for tok in _VAR_RE.findall(expr or ""):
        if tok.lower() in _SUBSCRIPT_TOKENS:
            continue
        out.append(tok)
    return sorted(set(out))


def _is_dimensional_constant(expr: str) -> bool:
    """True if every number is an exact closed-form mathematical constant.

    Whitelist rationale (documented, not tuned): 2, 3, 4, 8 appear as exact
    algebraic constants in the corpus equation families (Hagen-Poiseuille
    8·µLQ/(πr⁴), orifice sqrt(2·dP/ρ), Reynolds, Friis (λ/4πd)²); 0.5/1.5
    are exact halves. Measurement-like numbers (decimals like 0.35, or
    arbitrary integers like 17) are NOT whitelisted — they require sourced
    inputs.
    """
    exact = {"2", "3", "4", "8", "0.5", "1.5"}
    nums = _NUMBER_RE.findall(expr or "")
    return bool(nums) and all(n in exact for n in nums)


def _inputs_sourced(eng_spec: dict) -> bool:
    """Are any equation inputs backed by sourced (non-UNKNOWN) values?"""
    cps = (eng_spec.get("engineering_core") or {}) \
        .get("critical_parameters", []) or []
    for cp in cps:
        if isinstance(cp, dict):
            v = str(cp.get("value", ""))
            if v and "UNKNOWN" not in v.upper():
                return True
    return False
