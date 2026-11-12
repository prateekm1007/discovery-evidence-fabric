"""discovery_fabric/engine/constraint_audit.py — the CONSTRAINT-
COMPLIANCE AUDIT (owner audit round 2026-11-12, directive 2 + 4;
deterministic, zero-LLM; Art. XXVII no threshold invention, Art.
XXV unknown stays unknown, Art. LXXVII the answer is the deliverable).

The R6 auditor found shipped answers that violate the user's own
constraints and restate the problem as the answer:
  - fu-004 used a turbine exhaust PRESSURE setpoint as the predictor
    input while the constraint allows "existing temperature and flow
    measurements only";
  - new04 used "saturated condensing temperature", which is not a
    listed BMS point, while the constraint enumerates the allowed
    logged points;
  - new01 listed the user's constraints as the design parameters
    (restating);
  - sofc "recommended" an anode-supported cell — which the device
    already is — and never used the stated 0.15 intergranular glass
    phase fraction in the design itself.

The audit runs IN THE REPAIR STEP of the answer composer: its typed
violations ride the repair prompt (deterministic feedback, no gate
widening, Art. VII) and, when they survive every bounded repair, ride
the record's constraint_audit metadata plus ONE plain-language caveat
line. It is never a second evaluator of mechanism quality (Art. IV):
it checks COMPLIANCE and RESTATING only.

Violation types (typed):
  DISALLOWED_MEASUREMENT   — the proposal relies on a measurement
      outside the allowed set derived from the constraint text
      (enumerated logged points OR measurement-type allowlist).
  RESTATES_USER_CONSTRAINT — a PARAMETER line is a near-verbatim echo
      of a user variable (the constraint listed as the design).
  RESTATES_GIVEN_DEVICE    — the recommendation proposes as its change
      a state the given device already has.
  STATED_VARIABLE_UNUSED   — a user-stated numeric design variable
      (dict clarification_answer value, e.g. sofc's 0.15 glass phase
      fraction) never appears in the design outside constraint-echo
      lines.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

CONSTRAINT_AUDIT_VERSION = "constraint_audit/1.0.0"

# ---------------------------------------------------------------------------
# allowed-measurement extraction from the constraint text
# ---------------------------------------------------------------------------

_MEASUREMENT_LEXICON = (
    "temperature", "pressure", "flow", "vibration", "current", "voltage",
    "power", "speed", "humidity", "level", "acoustic", "emission",
    "strain", "displacement", "conductivity", "torque", "force",
    "position", "weight", "mass", "volume", "frequency", "impedance",
    "wet-bulb", "wet bulb",
)

_INSTRUMENT_MARKERS = (
    "transmitter", "sensor", "sensors", "setpoint", "set point", "gauge",
    "thermocouple", "transducer", "probe", "meter", "measurement",
    "measure", "measured", "measuring", "reading", "instrument",
    "instrumentation",
)

_ENUM_POINTS_RE = re.compile(
    r"(?:only\s+BMS\s+points\s+already\s+logged|BMS\s+points\s+already\s+"
    r"logged|already\s+logged)\s*\(([^)]+)\)", re.IGNORECASE)
_TYPE_ALLOWLIST_RES = [
    # "existing temperature and flow measurements only"
    re.compile(
        r"(?:existing|use\s+existing|using\s+existing)?\s*"
        r"((?:[a-z\-]+(?:\s+and\s+|\s*,\s*)?)+?)\s+measurements?\s+only",
        re.IGNORECASE),
    # "must use only X, Y, and Z points/signals"
    re.compile(
        r"use\s+only\s+((?:[a-z\-]+\s*(?:,\s*)?(?:and\s+)?)+)"
        r"\s*(?:points|signals|measurements?)", re.IGNORECASE),
]


def allowed_measurements(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the allowed measurement set from the constraint text.

    Returns {mode: 'enumerated_points'|'type_allowlist'|'none',
             allowed: [...], constraint: str} — 'none' means the
    constraint names no measurement restriction (the audit then skips
    DISALLOWED_MEASUREMENT; unknown stays unknown, Art. XXV)."""
    constraint = str(problem.get("constraint") or "")
    m = _ENUM_POINTS_RE.search(constraint)
    if m:
        raw = m.group(1)
        parts = [p.strip(" ,;/") for p in re.split(r",\s*|\s+/\s*", raw)
                 if p.strip(" ,;/")]
        # split "chilled water supply/return temperature" style entries
        allowed: List[str] = []
        for p in parts:
            if "/" in p:
                head, tail = p.rsplit("/", 1)
                # "supply/return" splits into two point phrases sharing
                # the trailing noun
                allowed.append(p)
                allowed.append(head.strip() + " " + tail.strip())
            else:
                allowed.append(p)
        return {"mode": "enumerated_points", "allowed": allowed,
                "constraint": constraint}
    for rx in _TYPE_ALLOWLIST_RES:
        m = rx.search(constraint)
        if m:
            seg = m.group(1).lower()
            toks = re.split(r"\s+and\s+|\s*,\s*|\s+or\s+", seg)
            types = [t.strip() for t in toks
                     if t.strip() in _MEASUREMENT_LEXICON]
            if types:
                return {"mode": "type_allowlist", "allowed": types,
                        "constraint": constraint}
    return {"mode": "none", "allowed": [], "constraint": constraint}


def _point_tokens(phrase: str) -> set:
    stop = {"the", "and", "or", "of", "for", "already", "logged",
            "points", "point", "existing", "only", "at", "to", "in"}
    toks = set(re.findall(r"[a-z0-9][a-z\-0-9]*",
                          str(phrase or "").lower()))
    return {t for t in toks if t not in stop}


def _find_disallowed_measurements(
        answer: str, allowed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag measurement-usage phrases whose measurement noun is outside
    the allowed set. Only instrument-marked phrases count (a mention of
    the failure consequence — 'back-pressure hits the derating limit' —
    is not a measured input)."""
    out: List[Dict[str, Any]] = []
    if allowed.get("mode") == "none":
        return out
    text = str(answer or "")
    low = text.lower()
    for noun in _MEASUREMENT_LEXICON:
        for m in re.finditer(re.escape(noun), low):
            s = max(0, m.start() - 45)
            e = min(len(low), m.end() + 45)
            window = low[s:e]
            if not any(mk in window for mk in _INSTRUMENT_MARKERS):
                continue
            if allowed.get("mode") == "type_allowlist":
                types = allowed.get("allowed") or []
                base = noun.replace("-", " ").replace("wet bulb",
                                                      "wet-bulb")
                hits = any(base == t or base in t or t in base
                           for t in types)
                if not hits:
                    # a wet-bulb allowlist entry admits the phrase
                    if ("wet" in window and "bulb" in window
                            and "wet-bulb" in types):
                        hits = True
                if not hits:
                    out.append({
                        "type": "DISALLOWED_MEASUREMENT",
                        "detail": ("measurement type "
                                   f"'{noun}' is outside the "
                                   "constraint's allowed set "
                                   f"({', '.join(types)})"),
                        "context": text[s:e].strip()})
            else:  # enumerated_points
                pts = allowed.get("allowed") or []
                w_toks = _point_tokens(window)
                covered = False
                for p in pts:
                    ptoks = _point_tokens(p)
                    if not ptoks:
                        continue
                    # the window must not add a DIFFERENT discriminative
                    # modifier outside the point phrase (exact-lexeme,
                    # never stem-matched: 'condensing' is not
                    # 'condenser' — the audited new04 violation)
                    core = ptoks & w_toks
                    if not core:
                        continue
                    extra = {
                        t for t in (w_toks - ptoks)
                        if t in _MEASUREMENT_LEXICON
                        or t in ("saturated", "superheated", "subcooled",
                                 "discharge", "suction", "liquid",
                                 "vapor", "vapour", "condensing")}
                    if not extra:
                        covered = True
                        break
                if not covered:
                    out.append({
                        "type": "DISALLOWED_MEASUREMENT",
                        "detail": ("measurement phrase around "
                                   f"'{noun}' is not one of the "
                                   "constraint's enumerated logged "
                                   f"points ({'; '.join(pts[:6])}...)"),
                        "context": text[s:e].strip()})
    # de-duplicate identical details (one violation per distinct phrase)
    seen = set()
    uniq = []
    for v in out:
        k = v["detail"]
        if k not in seen:
            seen.add(k)
            uniq.append(v)
    return uniq[:8]


# ---------------------------------------------------------------------------
# restating checks
# ---------------------------------------------------------------------------

def _line_param_segments(text: str) -> List[str]:
    """PARAMETER-labelled segments (one per line, the composer's
    contract shape)."""
    starts = [m.start() for m in re.finditer(r"\bPARAMETER\b",
                                             text, re.IGNORECASE)]
    segs = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        seg = text[s:e]
        nl = seg.find("\n")
        segs.append(seg[: nl if nl != -1 else len(seg)])
    return segs


#: structural scaffolding on a PARAMETER line — never counts as design
#: content in the overlap check
_PARAM_SCAFFOLD = frozenset({
    "parameter", "parameters", "fixed", "assumption", "evidence-backed",
    "user", "stated", "constraint", "target", "design", "value", "set",
    "at", "up", "of", "the", "a", "an", "than", "more", "less", "no",
    "over", "below", "above", "percent", "maximum", "minimum", "max",
    "min", "keep", "hold", "maintain",
})


def _restates_user_constraint(segment: str,
                              user_variables: List[str]) -> Optional[str]:
    """A PARAMETER segment that is a near-verbatim echo of ONE user
    variable (the constraint listed as a design parameter). Overlap is
    computed on the segment's content after stripping the label
    scaffolding."""
    seg_toks = _point_tokens(segment) - _PARAM_SCAFFOLD
    if not seg_toks:
        return None
    for uv in user_variables or []:
        uv_toks = _point_tokens(uv) - _PARAM_SCAFFOLD
        if not uv_toks:
            continue
        cover = len(seg_toks & uv_toks) / max(1, len(seg_toks))
        if cover >= 0.8:
            return str(uv)
    return None


_DEVICE_PROPOSAL_MARKERS = (
    "transition to", "convert to", "switch to", "adopt",
    "recommends?", "propose[sd]?", "move to", "change to",
    "should be", "replace with",
)

#: a STATE noun right after the echoed device phrase — the proposal
#: offers the device's own state as the change ("transition ... to an
#: anode-supported configuration", "recommends an anode-supported
#: cell"). A predictor proposed FOR the device ("recommend a
#: vibration-based predictor for the fan-drive bearing") is NOT a
#: restatement — no state noun follows the device phrase.
_DEVICE_STATE_NOUNS = (
    "configuration", "design", "architecture", "geometry", "layout",
    "arrangement", "structure", "cell", "setup", "variant", "option",
    "format", "type", "version",
)


def _restates_given_device(answer: str,
                           problem: Dict[str, Any]) -> Optional[str]:
    """The recommendation proposes as its central change a state the
    device text already states (sofc: 'anode-supported' IS the given
    device). Fires only on device n-grams (2-3 words) echoed in a
    sentence that carries a change verb AND a state noun right after
    the echoed phrase."""
    device = str(problem.get("device") or "").lower()
    if not device:
        return None
    text = str(answer or "")
    low = text.lower()
    dtoks = [t for t in re.findall(r"[a-z][a-z\-0-9]*", device)]
    grams = {" ".join(dtoks[i:i + n])
             for n in (2, 3)
             for i in range(max(0, len(dtoks) - n + 1))
             if not all(t.isdigit() for t in dtoks[i:i + n])}
    # compound device descriptors are the defining-state phrases the
    # audited answer echoed ("anode-supported", "yttria-stabilized"):
    # a single HYPHENATED token carries the state
    grams |= {t for t in dtoks if "-" in t and len(t) >= 8}
    for snt in re.split(r"(?<=[.!?])\s+|\n+", text):
        sl = snt.lower()
        if not any(re.search(p, sl) for p in _DEVICE_PROPOSAL_MARKERS):
            continue
        for g in grams:
            gpat = re.escape(g).replace(r"\ ", r"[\s\-]+")
            for m in re.finditer(gpat, sl):
                tail = sl[m.end(): m.end() + 40]
                if any(re.search(r"\b" + re.escape(sn) + r"\b", tail)
                       for sn in _DEVICE_STATE_NOUNS):
                    return g
    return None


# ---------------------------------------------------------------------------
# stated-variable usage (directive 4)
# ---------------------------------------------------------------------------

def _clarification_numbers(problem: Dict[str, Any]) -> List[Dict[str, Any]]:
    """User-stated numeric design variables from a dict-valued
    clarification_answer ({'intergranular glass phase fraction': 0.15,
    ...})."""
    out: List[Dict[str, Any]] = []
    ca = problem.get("clarification_answer")
    if isinstance(ca, dict):
        for k, v in ca.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append({"name": str(k), "value": v})
    return out


def _line_restates(segment_or_line: str,
                   user_variables: List[str]) -> bool:
    return _restates_user_constraint(segment_or_line,
                                     user_variables) is not None


def stated_variable_usage(
        answer: str, problem: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Each user-stated numeric variable must appear in the DESIGN
    (any line that is not a constraint echo)."""
    out: List[Dict[str, Any]] = []
    uvs = list(problem.get("user_variables") or [])
    for var in _clarification_numbers(problem):
        val = var["value"]
        val_str = ("%g" % val)
        lines = [ln for ln in str(answer or "").split("\n")
                 if val_str in ln]
        used = [ln for ln in lines
                if not _line_restates(ln, uvs)
                and "USER-STATED" not in ln.upper()
                and "user constraint" not in ln.lower()
                and "user-stated" not in ln.lower()]
        if not used:
            out.append({
                "type": "STATED_VARIABLE_UNUSED",
                "detail": (f"user-stated design variable "
                           f"'{var['name']}' = {val_str} never appears "
                           "in the design outside constraint-echo "
                           "lines"),
                "context": (lines[0].strip()[:160] if lines else "")})
    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def audit_constraints(problem: Dict[str, Any],
                      answer: str) -> Dict[str, Any]:
    """The constraint-compliance audit (deterministic, zero-LLM).

    Returns {state: CONSTRAINT_AUDIT_PASS|CONSTRAINT_VIOLATIONS,
             violations: [...], n_violations,
             allowed_measurements: {...}}."""
    violations: List[Dict[str, Any]] = []
    uvs = list(problem.get("user_variables") or [])
    allowed = allowed_measurements(problem)
    violations.extend(_find_disallowed_measurements(answer, allowed))
    for seg in _line_param_segments(answer):
        uv = _restates_user_constraint(seg, uvs)
        if uv:
            violations.append({
                "type": "RESTATES_USER_CONSTRAINT",
                "detail": ("a PARAMETER line is a near-verbatim echo "
                           f"of the user variable '{uv[:80]}' — the "
                           "constraint listed, not a design change"),
                "context": seg.strip()[:160]})
    rgd = _restates_given_device(answer, problem)
    if rgd:
        violations.append({
            "type": "RESTATES_GIVEN_DEVICE",
            "detail": ("the recommendation proposes as its change a "
                       f"state the given device already has ('{rgd}' "
                       "is in the device description)"),
            "context": rgd})
    violations.extend(stated_variable_usage(answer, problem))
    # cap the report (repair prompt carries the first N, all ride the
    # record)
    return {"audit_version": CONSTRAINT_AUDIT_VERSION,
            "state": ("CONSTRAINT_VIOLATIONS" if violations
                      else "CONSTRAINT_AUDIT_PASS"),
            "violations": violations,
            "n_violations": len(violations),
            "allowed_measurements": allowed}
