"""discovery_fabric/engine/constraint_audit.py — the CONSTRAINT-
COMPLIANCE AUDIT (owner audit round 2026-11-12, directive 2 + 4;
Art. XXVII no threshold invention, Art. XXV unknown stays unknown,
Art. LXXVII the answer is the deliverable).

R6 auditor round 2026-11-12 (directive 1, the REAL CONSTRAINT AUDIT):
the deterministic matcher alone is OVERFIT to its regression fixtures —
measured on the committed real pairs it missed 3 of 4 audited defects
(fu-004 pressure setpoint, new04 "Saturated Condensing Temp" — the
lexicon's "temperature" noun never matches the abbreviated "Temp",
new01 constraint echoes composed of re-ordered constraint tokens). The
audit is now TWO-LAYER:

  1. DETERMINISTIC FLOOR (unchanged, zero-LLM): the typed checks below
     stay exactly as they were — they trigger repair on what they can
     prove and remain the floor under every arm.

  2. THE STRUCTURED LLM CHECK (directive 1: "add one structured LLM
     check in the existing repair call (no extra call)"): the model
     that composes/repairs the answer ALSO outputs a trailing
     CONSTRAINT-CHECK block — one verdict line per user constraint
     (COMPLIES / VIOLATES + quoted offending text) plus RESTATES-DEVICE
     / RESTATES-CONSTRAINT. The block rides the EXISTING compose and
     repair calls (zero added calls); it is stripped from the delivered
     text, parsed, its quoted spans are deterministically verified
     against the answer, and every VIOLATES / RESTATES-YES verdict
     joins the SAME repair loop as the deterministic violations. An
     LLM check that could not run or could not be parsed is typed
     CHECK_ABSENT / CHECK_UNPARSEABLE in the record (Art. XXV: the
     unknown check state is never read as a pass).

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


# ---------------------------------------------------------------------------
# THE STRUCTURED LLM CHECK (R6 auditor round 2026-11-12, directive 1)
# ---------------------------------------------------------------------------
# One structured check that RIDES THE EXISTING compose/repair calls (no
# extra call): the model ends its response with a CONSTRAINT-CHECK block
# that is stripped before delivery and parsed into typed verdicts. The
# deterministic floor above is unchanged; the LLM verdicts MERGE into the
# same typed violation list and feed the SAME bounded repair loop.

CONSTRAINT_CHECK_VERSION = "constraint_check/1.0.0"

CONSTRAINT_CHECK_BLOCK_SPEC = """CONSTRAINT-CHECK (required last block, plain text):
After the answer, append EXACTLY this block and nothing after it. It is
machine-stripped before the answer is delivered; it is an audit, not
part of the answer.
CONSTRAINT-CHECK:
<for EACH numbered user constraint below, one line>:
C<i>: COMPLIES | VIOLATES | "<the exact offending text quoted from YOUR answer, or the empty string when COMPLIES>"
RESTATES-DEVICE: YES "<quoted text>" | NO
RESTATES-CONSTRAINT: YES "<quoted text>" | NO
Rules: VIOLATES means the answer's proposal depends on, measures, or
fixes something that constraint forbids or does not allow, or misses
what it requires. When a constraint enumerates the allowed
measurement points / instruments / data sources, the check is LEXICAL:
every input, measurement or derived quantity the proposal names must
be traceable to a listed point — a renamed, abbreviated or derived
variant that is not itself listed (e.g. a thermodynamic quantity like
a "saturated condensing temperature" when the list names specific
logged sensor points) is VIOLATES. VERIFY THE ANSWER'S OWN CLAIM: an
answer that says it "uses only the listed points" while its
INDICATOR/PARAMETER definitions or formulas compute from an unlisted
quantity is VIOLATES — the formula is the proposal, the claim is not
evidence. Quote the offending words EXACTLY as they appear in your
answer. RESTATES-DEVICE is YES only when the answer proposes, as its
change, a state the given device already has.
RESTATES-CONSTRAINT is YES only when a design parameter line merely
echoes a user constraint instead of changing something — the required
"how it respects each stated constraint" discussion is NOT a
restatement. For both RESTATES lines, quote the offending words
VERBATIM from YOUR answer's proposal lines (never from the problem
statement, never a paraphrase)."""


_CK_BLOCK_RE = re.compile(r"^\s*CONSTRAINT-CHECK\s*:?\s*$", re.IGNORECASE)
_CK_VERDICT_RE = re.compile(
    r"^\s*C\s*(\d+)\s*:\s*"
    r"(COMPLIES|VIOLATES)\s*(.*)$", re.IGNORECASE)
_CK_RESTATES_RE = re.compile(
    r"^\s*(RESTATES-DEVICE|RESTATES-CONSTRAINT)\s*:\s*"
    r"(YES|NO)\s*(.*)$", re.IGNORECASE)


def strip_constraint_check(text: str) -> tuple:
    """Split a composed response into (clean_answer, block_text).

    The block starts at the line 'CONSTRAINT-CHECK:' (case-insensitive)
    and runs to the end. When the marker is absent the whole text is
    the answer and the block is typed absent by the caller (Art. XXV)."""
    text = str(text or "")
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if _CK_BLOCK_RE.match(ln):
            answer = "\n".join(lines[:i]).rstrip()
            block = "\n".join(lines[i + 1:])
            return answer, block
    return text.rstrip(), None


def _norm_quote(s: str) -> str:
    """Normalization for quote verification: lowercase, collapse all
    whitespace and strip quote glyphs/punctuation-only noise."""
    s = str(s or "").lower().strip()
    s = s.strip("\"'\u201c\u201d\u2018\u2019` ")
    s = re.sub(r"[\s\-_\u2010-\u2015]+", " ", s)
    s = re.sub(r"[.,;:!()\[\]{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _quote_in_answer(quote: str, answer: str) -> bool:
    """Deterministic quote verification. The exact normalized span must
    appear in the normalized answer; when it does not, a sliding
    6-token window overlap (>= 0.6 of window tokens present) still
    verifies — the model may quote across a hyphenation or numeral
    formatting difference. Unverifiable quotes stay recorded (the
    verdict rides the record either way) but carry verified=False."""
    q = _norm_quote(quote)
    if not q:
        return False
    a = _norm_quote(answer)
    if q in a:
        return True
    q_toks = q.split()
    if len(q_toks) < 3:
        return False
    a_toks = a.split()
    if not a_toks:
        return False
    w = min(len(q_toks), 8)
    for i in range(0, max(1, len(a_toks) - w + 1)):
        window = a_toks[i:i + w]
        hit = sum(1 for t in window if t in q_toks or any(
            t.startswith(tk[:6]) and len(t) >= 4 and len(tk) >= 4
            for tk in q_toks))
        if hit / w >= 0.6:
            return True
    return False


def parse_constraint_check(block_text: str,
                           answer: str) -> Dict[str, Any]:
    """Parse the block into typed verdicts. Returns
    {state: PARSED|UNPARSEABLE, n_constraints, verdicts: [...],
     restates_device: {...}, restates_constraint: {...},
     n_violations, verified_quotes, n_unverified_quotes}.

    A parsed-but-quote-unverified VIOLATES verdict still counts (the
    model named the constraint and the failure; the unlocatable quote
    is disclosed on the verdict) — repair feedback is bounded and
    non-gating, so a paraphrased quote can never strand a real defect
    (Art. VII: feedback, never a gate)."""
    if not block_text or not str(block_text).strip():
        return {"check_version": CONSTRAINT_CHECK_VERSION,
                "state": "CHECK_ABSENT", "n_constraints": 0,
                "verdicts": [], "restates_device": None,
                "restates_constraint": None, "n_violations": 0,
                "verified_quotes": 0, "n_unverified_quotes": 0}
    verdicts: List[Dict[str, Any]] = []
    rest_dev = rest_con = None
    n_viol = 0
    verified = unverified = 0
    parsed_any = False
    for raw in str(block_text).split("\n"):
        ln = raw.strip()
        if not ln:
            continue
        m = _CK_VERDICT_RE.match(ln)
        if m:
            parsed_any = True
            idx = int(m.group(1))
            verdict = m.group(2).upper()
            tail = m.group(3).strip()
            quote = ""
            qm = re.search(r'"([^"]*)"', tail)
            if qm:
                quote = qm.group(1).strip()
            if verdict == "VIOLATES":
                ok = bool(quote) and _quote_in_answer(quote, answer)
                if quote and ok:
                    verified += 1
                else:
                    unverified += 1
                n_viol += 1
            verdicts.append({"constraint_index": idx, "verdict": verdict,
                             "quote": quote[:300],
                             "quote_verified": (
                                 bool(quote)
                                 and _quote_in_answer(quote, answer))
                             if verdict == "VIOLATES" else None})
            continue
        m = _CK_RESTATES_RE.match(ln)
        if m:
            parsed_any = True
            kind = m.group(1).upper()
            yes = m.group(2).upper() == "YES"
            quote = ""
            qm = re.search(r'"([^"]*)"', m.group(3) or "")
            if qm:
                quote = qm.group(1).strip()
            entry = {"yes": yes, "quote": quote[:300],
                     "quote_verified": (bool(quote) and
                                        _quote_in_answer(quote, answer))
                     if yes else None}
            if yes and quote:
                if _quote_in_answer(quote, answer):
                    verified += 1
                else:
                    unverified += 1
            if yes:
                n_viol += 1
            if kind == "RESTATES-DEVICE":
                rest_dev = entry
            else:
                rest_con = entry
    if not parsed_any:
        return {"check_version": CONSTRAINT_CHECK_VERSION,
                "state": "CHECK_UNPARSEABLE", "n_constraints": 0,
                "verdicts": [], "restates_device": None,
                "restates_constraint": None, "n_violations": 0,
                "verified_quotes": 0, "n_unverified_quotes": 0}
    return {"check_version": CONSTRAINT_CHECK_VERSION,
            "state": "PARSED", "n_constraints": len(verdicts),
            "verdicts": verdicts, "restates_device": rest_dev,
            "restates_constraint": rest_con, "n_violations": n_viol,
            "verified_quotes": verified, "n_unverified_quotes": unverified}


def llm_check_violations(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Typed violations from a parsed check (same shape as the floor's
    violations; types prefixed LLM_ so the source is never ambiguous).

    MEASURED GUARDS (R6 real-pairs acceptance run, same round — the
    audited real bytes decide, never hand fixtures):
      - A RESTATES-* YES whose quote does not verify against the ANSWER
        is recorded, never counted: the measured false positive quoted
        the PROBLEM's own device descriptor ("rolling-element bearing
        in a 350 kW industrial fan drive", fu-001) — a description of
        the given device is not a proposed state.
      - A RESTATES-* YES counts only when the verified quote names a
        PROPOSAL line (PARAMETER:/INTERVENTION:/RECOMMENDED/THRESHOLD:
        /INDICATOR:): the measured fu-001 "echo" was the answer's
        REQUIRED constraint-compliance explanation ("It satisfies the
        ... constraint"), which the answer-shape contract demands and
        which the owner ruled a PASS; the audited new01/sofc echoes
        are PARAMETER lines whose values ARE the constraints.
        """
    out: List[Dict[str, Any]] = []
    if parsed.get("state") != "PARSED":
        return out
    for v in parsed.get("verdicts") or []:
        if v.get("verdict") == "VIOLATES":
            out.append({
                "type": "LLM_CONSTRAINT_VIOLATES",
                "detail": (f"the structured constraint check flags "
                           f"constraint {v.get('constraint_index')} as "
                           "VIOLATES"
                           + (" — offending text located in the answer"
                              if v.get("quote_verified")
                              else " — quoted text not located "
                              "(disclosed, unverified)")),
                "context": str(v.get("quote") or "")[:200],
                "source": "constraint_check"})
    for kind, vtype in (("restates_device", "LLM_RESTATES_GIVEN_DEVICE"),
                        ("restates_constraint",
                         "LLM_RESTATES_USER_CONSTRAINT")):
        r = parsed.get(kind)
        if not (isinstance(r, dict) and r.get("yes")):
            continue
        if not r.get("quote_verified"):
            # measured guard 1: an unlocatable quote never counts (the
            # quote may be problem text or a paraphrase — fu-001)
            continue
        if not _RESTATES_PROPOSAL_MARKER.search(str(r.get("quote") or "")):
            # measured guard 2: a compliance explanation is not an echo
            continue
        out.append({
            "type": vtype,
            "detail": ("the structured constraint check flags "
                       + ("a proposal that restates a state the "
                          "given device already has"
                          if kind == "restates_device"
                          else "a parameter line that only echoes "
                               "a user constraint")
                       + " — proposal line located in the answer"),
            "context": str(r.get("quote") or "")[:200],
            "source": "constraint_check"})
    return out


def merge_constraint_check(audit: Dict[str, Any],
                           parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Merge the parsed LLM check into a deterministic audit result.
    The floor's violations stay; LLM violations append; the state and
    n_violations recompute; the check rides the merged record."""
    merged = dict(audit or {})
    viols = list(merged.get("violations") or [])
    viols.extend(llm_check_violations(parsed))
    merged["violations"] = viols
    merged["n_violations"] = len(viols)
    merged["state"] = ("CONSTRAINT_VIOLATIONS" if viols
                       else "CONSTRAINT_AUDIT_PASS")
    merged["constraint_check"] = parsed
    return merged


#: a RESTATES-* verdict counts only when its verified quote names a
#: PROPOSAL line of the answer (the answer-shape contract's own line
#: classes) — a compliance explanation or the problem's device text is
#: never an echo (measured guard, real-pairs acceptance run)
_RESTATES_PROPOSAL_MARKER = re.compile(
    r"\b(PARAMETER|INTERVENTION|RECOMMENDED|THRESHOLD|INDICATOR)\s*:",
    re.IGNORECASE)


#: the judge-side prompt for a STANDALONE check of a pre-existing answer
#: (the acceptance harness on the committed real pairs; the same verdict
#: contract the composer's fused block obeys — one check shape, Art. X).
LLM_CONSTRAINT_CHECK_PROMPT = """You audit one engineering answer
against the user's stated constraints. Be adversarial and precise: a
constraint is VIOLATED when the answer's proposal depends on,
measures, or fixes something the constraint forbids or does not allow,
or misses what it requires. An answer that only restates the given
device's existing state, or lists the user's constraints as its design
parameters without changing anything, violates the restatement rule.

MEASUREMENT-POINT CONSTRAINTS: when a constraint enumerates the
allowed measurement points / instruments / data sources, the check is
LEXICAL: every input, measurement or derived quantity the answer's
proposal names must be traceable to a listed point. A renamed,
abbreviated or derived variant that is not itself listed (for example
a thermodynamic quantity like a "saturated condensing temperature"
when the list names specific logged sensor points) is VIOLATES — quote
the offending span from the answer. VERIFY THE ANSWER'S OWN CLAIM:
an answer that SAYS it "uses only the listed points" while its
INDICATOR/PARAMETER definitions or formulas actually compute from an
unlisted quantity (e.g. "ΔT = A − B" where B is not a listed point)
VIOLATES — the formula is the proposal, the claim is not evidence.

COMPLIANCE EXPLANATIONS ARE NOT RESTATEMENTS: the answer's required
"how it respects each stated constraint" discussion never counts as
restating. RESTATES-CONSTRAINT is YES only when a PARAMETER,
INTERVENTION or RECOMMENDED line's content is itself the user's
constraint (a value copied from the constraint instead of a change).
RESTATES-DEVICE is YES only when the answer PROPOSES, as its change, a
state the given device already has. For both: quote the offending
words VERBATIM from the answer's proposal lines (never from the
problem statement, never a paraphrase).

DEVICE: {device}
FAILURE: {failure}

USER'S STATED CONSTRAINTS (numbered):
{numbered_constraints}

ANSWER UNDER AUDIT:
{answer}

Output ONLY this block:
CONSTRAINT-CHECK:
C1: COMPLIES | VIOLATES | "<exact offending quote from the answer, or empty>"
C2: COMPLIES | VIOLATES | "<...>"
(for every numbered constraint)
RESTATES-DEVICE: YES "<quote>" | NO
RESTATES-CONSTRAINT: YES "<quote>" | NO
"""


def numbered_constraints_block(problem: Dict[str, Any]) -> str:
    """The user's constraints as a numbered list (the check's units).
    user_variables are the constraint statements the run recorded; the
    free-text constraint is always line 1 when present."""
    lines: List[str] = []
    c = str(problem.get("constraint") or "").strip()
    if c:
        lines.append(c)
    for uv in problem.get("user_variables") or []:
        u = str(uv or "").strip()
        if u and u not in lines:
            lines.append(u)
    ca = problem.get("clarification_answer")
    if isinstance(ca, dict):
        for k, v in ca.items():
            if k == "note":
                continue
            lines.append(f"{k}: {v}")
    return "\n".join(f"C{i+1}: {ln[:220]}" for i, ln in enumerate(lines)) \
        or "(no stated constraints recorded)"


def llm_constraint_check(problem: Dict[str, Any], answer: str,
                         llm_generate) -> Dict[str, Any]:
    """STANDALONE structured check of a pre-existing answer (ONE LLM
    call, the acceptance-harness shape of the fused block). Uses the
    SAME verdict contract and the SAME parser — one check shape, two
    transports (fused into compose/repair in the pipeline; standalone
    here). `llm_generate` is the engine's injectable transport."""
    prompt = LLM_CONSTRAINT_CHECK_PROMPT.format(
        device=str(problem.get("device") or "")[:300],
        failure=str(problem.get("failure") or "")[:300],
        numbered_constraints=numbered_constraints_block(problem),
        answer=str(answer or "")[:4500])
    res = llm_generate(prompt, system=(
        "You are a precise, adversarial constraint auditor for "
        "engineering proposals. Output only the required block."),
        max_tokens=700, purpose="constraint_check")
    if not isinstance(res, dict) or not res.get("ok") \
            or not (res.get("content") or "").strip():
        return {"check_version": CONSTRAINT_CHECK_VERSION,
                "state": "CHECK_TRANSPORT_FAILED",
                "error": str((res or {}).get("error")
                             or (res or {}).get("status"))[:200],
                "n_constraints": 0, "verdicts": [],
                "restates_device": None, "restates_constraint": None,
                "n_violations": 0, "verified_quotes": 0,
                "n_unverified_quotes": 0}
    _ans, block = strip_constraint_check(res["content"])
    parsed = parse_constraint_check(block, str(answer or ""))
    parsed["standalone"] = True
    parsed["provider"] = res.get("provider_route") or res.get("provider")
    parsed["model"] = res.get("model")
    return parsed
