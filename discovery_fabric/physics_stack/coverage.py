"""coverage.py — the Physics Coverage Registry V1 and the claim-language
contract (R413, operator directive V2 Phase 1).

THE REGISTRY IS A DECISION SYSTEM (operator, directive V2):
    machine-readable, 15-field schema, feeding (a) the coverage matrix,
    (b) the deterministic router, (c) the Physics Gap Opportunity Score.

THE 15-FIELD SCHEMA (operator, verbatim):
    phenomenon, governing_equations, solver, solver_version,
    geometry_requirements, boundary_conditions, material_requirements,
    operating_regime, validated_regime, known_limitations, uncertainty,
    verification_method, epistemic_class, input_schema, output_schema

THE CRUCIAL RULE, MECHANICAL (carried from directive v1, restated by
directive V2):
    the machine may say
        "Validated: incompressible turbulent flow, Re=18,400, specified
         geometry and boundary conditions."
    and may NEVER say
        "Physics verified."
    A coverage entry's validated_regime is a LIST of measured,
    regime-scoped validation records (each with a computation-log
    hash), and the claim evaluator enforces regime scoping
    deterministically.

EVIDENCE HONESTY (Art. XXV/XXVIII/XXXVIII):
- An EMPTY validated_regime is the honest default: "declared solver,
  no validation executed and recorded in this environment" — never
  "the solver is invalid", and never license for a validated claim.
- UNQUANTIFIED uncertainty BLOCKS validated claims (Art. XXVII).
- Every entry's epistemic_class is COMPUTATIONAL_RESULT (layer 4):
  a covered phenomenon is a model-form declaration, never evidence
  the model form applies to any specific device.

SUPERSSESSION (Art. LXIV): PHYSICS_COVERAGE_REGISTRY_V1.json supersedes
the uncommitted draft PHYSICS_COVERAGE_REGISTRY.json (7-field chain) in
the same change that ships this module update. The draft never entered
git history; the worklog records the replacement.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (REPO / "discovery_fabric" / "physics_stack"
                 / "PHYSICS_COVERAGE_REGISTRY_V1.json")

#: The operator's directive-V2 schema, verbatim, in order — every
#: registry entry carries exactly these fields.
SCHEMA_FIELDS_V1 = (
    "phenomenon", "governing_equations", "solver", "solver_version",
    "geometry_requirements", "boundary_conditions",
    "material_requirements", "operating_regime", "validated_regime",
    "known_limitations", "uncertainty", "verification_method",
    "epistemic_class", "input_schema", "output_schema",
)

#: honest placeholder for not-installed solver versions (Art. VI).
DECLARED_AT_INSTALL = "DECLARED_AT_INSTALL"

#: entry-level epistemic class is pinned to the Reality Boundary layer
#: 4 — every result the registry can admit is computational.
ENTRY_EPISTEMIC_CLASS = "COMPUTATIONAL_RESULT"

#: Deterministic overclaim markers — a claim containing any of these
#: patterns (case-insensitive) is REJECTED as a global overclaim. This
#: is the "never say 'Physics verified'" rule as code.
_OVERCLAIM_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"physics\s+verified",
    r"physically\s+verified",
    r"all\s+laws\s+of\s+physics",
    r"proven\s+physically",
    r"fully\s+validates?\s+physics",
    r"laws\s+of\s+physics\s+(are\s+)?(satisfied|obeyed|verified)",
    r"physically\s+plausible",  # UNQUALIFIED — see _needs_qualification
))

#: A "physically plausible" claim is admissible ONLY with an explicit
#: scope qualifier (regime/geometry/BC binding); the bare phrase is the
#: operator's forbidden anti-pattern ("AI -> Blender picture -> 'looks
#: physically plausible'").
_PLAUSIBLE_QUALIFIER = re.compile(
    r"(regime|Re\s*=|geometry|boundary|conditions|solver|within|"
    r"specified|under\s+assumption)", re.IGNORECASE)

#: Required bindings on any VALIDATED claim (the operator's canonical
#: sentence names them: phenomenon, regime, geometry AND boundary
#: conditions — plus solver version and uncertainty per Art. XXVII/
#: LXII).
_VALIDATED_REQUIRED_BINDINGS = (
    "phenomenon", "regime", "geometry_binding", "boundary_conditions",
    "solver_version", "uncertainty",
)

VERDICT_ADMITTED = "ADMITTED_REGIME_SCOPED"
VERDICT_REJECTED_OVERCLAIM = "REJECTED_GLOBAL_OVERCLAIM"
VERDICT_REJECTED_UNREGISTERED = "REJECTED_UNREGISTERED_PHENOMENON"
VERDICT_REJECTED_UNVALIDATED = "REJECTED_REGIME_UNVALIDATED"
VERDICT_REJECTED_BINDINGS = "REJECTED_MISSING_BINDINGS"
VERDICT_REJECTED_UNCERTAINTY = "REJECTED_UNQUANTIFIED_UNCERTAINTY"
VERDICT_REJECTED_VIZ = "REJECTED_VISUALIZATION_AS_PHYSICS"

#: Visualization-layer solver ids that can never support a physics
#: claim (directive V2 geometry boundary: a render is presentation,
#: never computation and never engineering-geometry validation).
VISUALIZATION_SOURCE_IDS = frozenset({
    "blender", "blender_rigidbody", "sofa_blender_bridge",
})


def load_coverage_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or REGISTRY_PATH
    if not p.exists():
        raise FileNotFoundError(f"coverage registry missing: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    problems = validate_coverage_registry(doc)
    if problems:
        raise ValueError("coverage registry invalid: " + "; ".join(problems))
    return doc


def validate_coverage_registry(doc: Optional[Dict[str, Any]] = None
                               ) -> List[str]:
    """Structural + adversarial validation of the V1 registry document.
    EMPTY result = valid.

    Checks the 15-field schema verbatim (operator directive V2 Phase 1),
    the validated-regime evidence contract (computation-log hash +
    quantified uncertainty + real solver version), the one-identity
    rule, and the pinned entry epistemic class."""
    if doc is None:
        doc = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    v: List[str] = []
    entries = doc.get("entries", [])
    if not entries:
        v.append("coverage registry has no entries")
    schema = doc.get("schema_fields_verbatim") or SCHEMA_FIELDS_V1
    if list(schema) != list(SCHEMA_FIELDS_V1):
        v.append("schema_fields_verbatim must be the operator's "
                 "directive-V2 15-field schema, in order")
    seen: Dict[str, int] = {}
    for e in entries:
        ph = e.get("phenomenon")
        if not ph:
            v.append("entry without phenomenon")
            continue
        seen[ph] = seen.get(ph, 0) + 1
        for field in schema:
            if field not in e:
                v.append(f"{ph}: missing schema field {field!r} "
                         "(the operator's 15-field schema is required "
                         "verbatim)")
        if e.get("epistemic_class") != ENTRY_EPISTEMIC_CLASS:
            v.append(f"{ph}: epistemic_class must be pinned to "
                     f"{ENTRY_EPISTEMIC_CLASS!r} (Art. XXXVIII layer 4)")
        solver = e.get("solver")
        if not solver:
            v.append(f"{ph}: missing solver binding")
        if not e.get("solver_version"):
            v.append(f"{ph}: solver_version required (Art. LXII)")
        for vr in e.get("validated_regime") or []:
            for req in ("regime", "computation_log_sha256",
                        "solver_version", "uncertainty",
                        "validated_at", "method"):
                if req not in vr:
                    v.append(f"{ph}: validated_regime record missing "
                             f"{req!r} — a validation without a "
                             "computation-log hash is an assertion "
                             "(Art. VI/XXVII)")
            unc = vr.get("uncertainty")
            if unc in (None, "", "UNQUANTIFIED"):
                v.append(f"{ph}: validated regime with UNQUANTIFIED "
                         "uncertainty — a validation without uncertainty "
                         "is an assertion, not a measurement (Art. XXVII)")
            if vr.get("solver_version") in (None, DECLARED_AT_INSTALL):
                v.append(f"{ph}: validated regime citing a placeholder "
                         "solver version — a validation may never cite "
                         "an unmeasured version (Art. VI/LXII)")
        # requirements fields must be declared (structure is checked
        # loosely; content honesty is enforced by the builder + tests)
        for reqf in ("geometry_requirements", "boundary_conditions",
                     "material_requirements"):
            r = e.get(reqf)
            if not isinstance(r, dict) or not r:
                v.append(f"{ph}: {reqf} must be a declared requirement "
                         "record (operator 15-field schema)")
        if not e.get("operating_regime"):
            v.append(f"{ph}: operating_regime required (the decision "
                     "system routes on it)")
        if not e.get("known_limitations"):
            v.append(f"{ph}: known_limitations required — an entry "
                     "without declared limitations overclaims by "
                     "omission (Art. XV)")
        if not e.get("verification_method"):
            v.append(f"{ph}: verification_method required (how this "
                     "entry would earn a validated regime)")
        for eq in e.get("governing_equations") or []:
            if not isinstance(eq, dict) or not eq.get("equation") \
                    or not eq.get("epistemic_class"):
                v.append(f"{ph}: governing equation declarations need "
                         "name + epistemic_class (Art. XXVII)")
        # solver_version placeholder rule: only allowed when the
        # solver is measured NOT_INSTALLED (validated_regime empty)
        if e.get("solver_version") == DECLARED_AT_INSTALL and \
                e.get("validated_regime"):
            v.append(f"{ph}: DECLARED_AT_INSTALL version with a "
                     "non-empty validated_regime (Art. VI)")
    for ph, n in seen.items():
        if n > 1:
            v.append(f"phenomenon {ph!r} registered {n}x — one identity "
                     "per phenomenon (Art. X)")
    return v


def _claim_text(claim: Dict[str, Any]) -> str:
    return str(claim.get("statement", claim.get("text", "")))


def _is_visualization_source(claim: Dict[str, Any]) -> bool:
    src = (claim.get("source") or "")
    return src in VISUALIZATION_SOURCE_IDS


def evaluate_physics_claim(claim: Dict[str, Any],
                           registry: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
    """THE CLAIM-LANGUAGE CONTRACT.

    Admissible output (the operator's canonical form):
        {verdict: ADMITTED_REGIME_SCOPED, ...}
    only when ALL of:
      - the statement carries no overclaim marker (or every
        "physically plausible" carries an explicit scope qualifier);
      - phenomenon is a registered phenomenon class;
      - a validated_regime record EXISTS for the phenomenon (with
        computation-log hash + quantified uncertainty);
      - the claim binds geometry AND boundary conditions AND solver
        version AND uncertainty.

    Everything else is REJECTED with a machine-readable reason. A
    visualization-layer source (blender / bridge) is rejected outright
    for physics claims: a render is not computation (Art. XXXVIII) and
    cannot validate engineering geometry (directive V2 Phase 4).
    """
    reg = registry or load_coverage_registry()
    text = _claim_text(claim)
    reasons: List[str] = []
    verdict: Optional[str] = None

    # 1. global overclaim scan (the crucial rule)
    for pat in _OVERCLAIM_PATTERNS:
        m = pat.search(text)
        if m:
            if pat.pattern.startswith(r"physically\s+plausible") and \
                    _PLAUSIBLE_QUALIFIER.search(text):
                continue  # scoped plausibility is admissible language
            reasons.append(
                f"overclaim marker {m.group(0)!r} — no software stack "
                "can guarantee all laws of physics (operator crucial "
                "rule; Art. XXVIII no silent semantic promotion)")
            verdict = VERDICT_REJECTED_OVERCLAIM
            break

    # 2. visualization as physics (also: geometry authority boundary)
    if verdict is None and _is_visualization_source(claim):
        verdict = VERDICT_REJECTED_VIZ
        reasons.append(
            "the source is a visualization-layer tool — a render is "
            "transport, not computation, may never support a physics "
            "claim (Art. XXXVIII) and may never originate or validate "
            "engineering geometry (operator directive V2 Phase 4)")

    # 3. registered phenomenon?
    phenomenon = claim.get("phenomenon")
    entry = None
    if verdict is None:
        if not phenomenon:
            verdict = VERDICT_REJECTED_BINDINGS
            reasons.append("claim does not name a phenomenon")
        else:
            entry = next((e for e in reg["entries"]
                          if e["phenomenon"] == phenomenon), None)
            if entry is None:
                verdict = VERDICT_REJECTED_UNREGISTERED
                reasons.append(
                    f"phenomenon {phenomenon!r} is not registered — an "
                    "unregistered phenomenon can never support a "
                    "validated claim (Art. IV: no fallback epistemology)")

    # 4. validated regime exists for the (claim's) regime?
    if verdict is None and entry is not None:
        want_regime = claim.get("regime")
        vr_list = entry.get("validated_regime") or []
        if not vr_list:
            verdict = VERDICT_REJECTED_UNVALIDATED
            reasons.append(
                f"phenomenon {phenomenon!r} has NO validated regime on "
                "record (empty is honest — no validation has been "
                "executed and recorded here); a validated claim would "
                "manufacture provenance (Art. VI)")
        elif want_regime:
            match = any(
                _regime_covers(vr.get("regime"), want_regime)
                for vr in vr_list)
            if not match:
                verdict = VERDICT_REJECTED_UNVALIDATED
                reasons.append(
                    f"the claimed regime {want_regime!r} is not within "
                    "any recorded validated regime for "
                    f"{phenomenon!r} — validation is regime-scoped, "
                    "never global")

    # 5. required bindings
    if verdict is None:
        missing = [b for b in _VALIDATED_REQUIRED_BINDINGS
                   if not claim.get(b)]
        if missing:
            verdict = VERDICT_REJECTED_BINDINGS
            reasons.append(
                f"missing required bindings: {missing} — the canonical "
                "form is 'Validated: <phenomenon>, <regime>, specified "
                "geometry and boundary conditions' + solver version + "
                "uncertainty (operator canonical sentence; Art. XXVII/"
                "LXII)")
        elif claim.get("uncertainty") in ("UNQUANTIFIED", "none", "NONE"):
            verdict = VERDICT_REJECTED_UNCERTAINTY
            reasons.append(
                "uncertainty is UNQUANTIFIED — an unquantified "
                "validation is an assertion, not a measurement "
                "(Art. XXVII)")

    if verdict is None:
        verdict = VERDICT_ADMITTED
        reasons.append(
            "regime-scoped validated claim: admissible language — "
            "'Validated: <phenomenon>, <regime>, specified geometry "
            "and boundary conditions' (operator canonical form)")

    out = {
        "verdict": verdict,
        "reasons": reasons,
        "claim_statement": text[:300],
        "evidence_class_if_admitted": "COMPUTATIONAL_RESULT",
        "art_xxxviii_note": ("even an ADMITTED claim is computational "
                             "evidence (layer 4) — it may never be "
                             "cited as physical observation (Art. LIII: "
                             "simulation -> physics requires "
                             "measurement)"),
    }
    if entry is not None:
        out["registry_solver"] = entry.get("solver")
    return out


def _regime_covers(recorded: Any, claimed: Any) -> bool:
    """Regime matching: a recorded regime covers a claimed regime iff
    every claimed key is present and equal in the recorded regime
    (exact match per Art. II — no approximate regime equality, no
    'close enough' Reynolds numbers)."""
    if recorded is None:
        return False
    if isinstance(recorded, str) and isinstance(claimed, str):
        return recorded == claimed
    if isinstance(recorded, dict) and isinstance(claimed, dict):
        return all(k in recorded and recorded[k] == v
                   for k, v in claimed.items())
    return recorded == claimed


def format_validated_sentence(entry: Dict[str, Any],
                              regime: Dict[str, Any]) -> str:
    """The ONLY sentence template through which the machine may state
    a validation (the operator's canonical form)."""
    return (f"Validated: {entry['phenomenon']}, "
            f"regime {json.dumps(regime, sort_keys=True)}, "
            f"solver {entry.get('solver')}, "
            "specified geometry and boundary conditions; "
            "computational result, not physical observation.")


def simulatable_phenomena(doc: Optional[Dict[str, Any]] = None
                          ) -> Dict[str, Any]:
    """DECISION-SYSTEM QUERY: which phenomena are simulatable NOW?

    A phenomenon is simulatable iff its solver is measured-INSTALLED
    AND it has at least one validated regime (a solver without a
    recorded validation computes numbers the machine may not use as
    validated evidence — the R394 discipline)."""
    reg = doc or load_coverage_registry()
    out = {"simulatable": [], "declared_not_validated": [],
           "solver_not_installed": []}
    for e in reg["entries"]:
        if e["validated_regime"]:
            out["simulatable"].append(e["phenomenon"])
        elif (e.get("solver_availability") or {}).get("state") == \
                "INSTALLED":
            out["declared_not_validated"].append(e["phenomenon"])
        else:
            out["solver_not_installed"].append(e["phenomenon"])
    return out
