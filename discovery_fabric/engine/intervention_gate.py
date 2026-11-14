"""discovery_fabric/engine/intervention_gate.py — R6 deterministic
candidate/attack gates (owner directive 2026-11-11, item 4).

Three instruments, ONE module, all deterministic (zero LLM, Art. X:
one authority per rule — the LLM gauntlet and every consumer read
these same functions):

  1. not_an_intervention_check — a candidate whose "intervention" is
     not an actionable engineering intervention (monitor-only, gather-
     data-only, empty, or a pure restatement with no design content)
     is rejected at assembly with a typed state, BEFORE any attack
     compute is spent on it.

  2. function_removal_check — kill class: the intervention removes
     a function the user's constraint mandates (lowers a mandated
     floor, raises a mandated ceiling, narrows a mandated operating
     range, or explicitly eliminates a mandated element). P0-3
     (Art. LXXXI): the class is deterministic and always FIRES, but
     its TERMINAL authority is per-instrument — the check runs as
     instrument version intervention_gate_function_removal/1.0.0
     and issues a terminal KILL only when ITS OWN committed
     calibration meets the sealed bars (attacker_calibration
     registry); uncalibrated, it issues the typed
     ESCALATED_OBJECTION (objection preserved, no negative
     knowledge).

  3. restates_constraint_check — kill class: the intervention is a
     paraphrase of the constraint with no mechanism of its own
     (measured: token Jaccard against the constraint, no new
     mechanism content). "Survive 500 cycles" is the requirement,
     not the invention. P0-3 (Art. LXXXI): separate instrument
     version intervention_gate_restates_constraint/1.0.0 — it
     earns terminal authority independently (per-defect-class
     calibration on independently authored specimens); until
     then it issues the typed ESCALATED_OBJECTION, never a
     terminal KILL.

  4. anchor_domain_check — the anchor evidence record must share the
     failure's domain OR the candidate must state the shared
     mechanism (Art. XLII-adjacent: an unexplained cross-domain jump
     is not a mechanism). Neither -> the candidate is rejected at
     assembly as NOT_EVIDENCE_ANCHORED_DOMAIN.

Bases (committed DEV cases, tests are pinned to them):
  - eval-sofc-thermal-cycling: constraint mandates "survive 500
    thermal cycles from 25 C to 800 C ... holding open-circuit
    voltage above 1.0 V ... without increasing stack mass above 2
    percent". Function-removal specimen: "operate the stack
    continuously without start/stop cycling" / "hold OCV above 0.7 V".
  - bench-p02-leadacid-grid-corrosion: constraint mandates "15-year
    float service life at 2.27 V per cell ... without antimony above
    2 percent". Function-removal specimen: "reduce float voltage to
    2.17 V per cell" / "allow 4 percent antimony".
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

INTERVENTION_GATE_VERSION = "intervention_gate/1.0.0"

# ---------------------------------------------------------------------------
# 1. NOT_AN_INTERVENTION — typed rejection at candidate assembly
# ---------------------------------------------------------------------------
_MIN_INTERVENTION_CHARS = 25

#: monitor-only / study-only "interventions": not a design change
_NOT_INTERVENTION_RE = re.compile(
    r"\b(?:"
    r"no intervention|no design change|not feasible|"
    r"continue (?:to )?(?:monitor\w*|observ\w+|operat\w+)|"
    r"(?:monitor|observe|track|watch)\w* (?:the |this )?\w*"
    r"(?: (?:more|further|closely|continu\w+|over time))+|"
    r"collect (?:more )?data|gather (?:more )?data|"
    r"further (?:study|research|testing|investigation)\w*\s*"
    r"(?:is |are |would be )?(?:needed|required|warranted)|"
    r"future (?:work|study|research)|"
    r"more research is needed|"
    r"await(?:s|ing)? (?:further|more) (?:data|evidence|study)|"
    r"insufficient (?:data|evidence) to (?:determine|recommend)|"
    r"accept(?:s|ing)? the failure|"
    r"do nothing|take no action"
    r")\b", re.IGNORECASE)

#: negated-span strip: a design-verb match inside a negation phrase
#: ("no design change is proposed") is not a proposal
_NEGATED_SPAN_RE = re.compile(
    r"\bno [a-z-]+ (?:change|action|modification|intervention|design)\w*\b|"
    r"\bwithout (?:changing|modifying|altering)\b|"
    r"\bnot (?:propos|chang|modif)\w*\b", re.IGNORECASE)

#: a pure schedule/inspection proposal with no design content
_INSPECTION_ONLY_RE = re.compile(
    r"^\s*(?:schedule|inspect\w*|visual\w* check\w*|audit)\b"
    r"[^.]{0,80}$", re.IGNORECASE)


def not_an_intervention_check(intervention: Optional[str]) -> Dict[str, Any]:
    """Deterministic NOT_AN_INTERVENTION screen (owner directive item 4).
    Returns {rejected, reason, reason_class}. Empty/monitor-only/
    inspection-only "interventions" are rejected before attack compute.
    A monitor/study phrase only rejects when the text carries NO design-
    action verb (a proposal that coats AND monitors is a proposal)."""
    text = str(intervention or "").strip()
    if len(text) < _MIN_INTERVENTION_CHARS:
        return {"rejected": True, "reason_class": "EMPTY_OR_TRIVIAL",
                "reason": (f"intervention text is {len(text)} chars "
                           f"(< {_MIN_INTERVENTION_CHARS}); no actionable "
                           "design change is stated")}
    m = _NOT_INTERVENTION_RE.search(text)
    if m and not _DESIGN_VERB_RE.search(
            _NEGATED_SPAN_RE.sub(" ", text)):
        return {"rejected": True, "reason_class": "NOT_AN_INTERVENTION",
                "reason": (f"monitor/study-only statement ({m.group(0)!r}); "
                           "no design-action verb anywhere in the "
                           "intervention")}
    if _INSPECTION_ONLY_RE.match(text):
        return {"rejected": True, "reason_class": "NOT_AN_INTERVENTION",
                "reason": "inspection/schedule-only proposal; no design "
                          "change"}
    return {"rejected": False, "reason_class": None, "reason": None}


#: a design-action verb (any one of these makes the text a proposal:
#: the monitor-only screen never rejects a text carrying one). Words
#: with heavy noun overlap (seal, dry, heat, cool, treat, thin, set) are
#: excluded — a false positive here would pass a monitor-only
#: "intervention" because its OBJECT happens to be a design noun.
_DESIGN_VERB_RE = re.compile(
    r"\b(?:install|replace|coating|adding|plating|lining|"
    r"coat|bond|apply|switch|change|modify|"
    r"remove|reduce|increase|decrease|substitute|integrate|"
    r"plate|anneal|heat[- ]treat|precoat|pre-coat|dose|inject|retrofit|"
    r"redesign|re-?engineer|thicken|strengthen|filter|pre-?filter|"
    r"weld|braze|clamp|torque|derate|uprate|re-?rate|"
    r"combine|encapsulate|quench|temper|grind|polish|machin\w+|"
    r"pressuri[sz]e|insulate|"
    r"buffer|damp(?:en)?|stiffen|soften|reorient|reroute|redirect|"
    r"resize|recalibrat\w*|rebuild|refit|requalify)\b",
    re.IGNORECASE)


# ---------------------------------------------------------------------------
# 2. FUNCTION_REMOVAL — terminal kill (the intervention deletes a
#    function the constraint mandates)
# ---------------------------------------------------------------------------
_NUM = r"\d+(?:[.,]\d+)?"

#: mandated floors: hold/maintain/keep/survive/achieve X (at|above) N
#: unit — the metric class admits digits and acronyms ("15-year float
#: service life at 2.27 V", "OCV above 1.0 V")
_FLOOR_RE = re.compile(
    r"\b(?:hold|holding|maintain|maintaining|keep|keeping|survive|surviving|"
    r"achieve|achieving|at least|no less than|not (?:fall|drop)[^.;\n]{0,24}below|"
    r"above)\b[^.;\n]{0,60}?(?P<metric>[A-Za-z0-9][A-Za-z0-9 \-/%]{2,40}?)\s*"
    r"(?:at|above|of|>=|>|over)\s*(?P<num>" + _NUM + r")\s*"
    r"(?P<unit>[a-zA-Z°/%µ]{1,12})\b", re.IGNORECASE)

#: mandated ceilings: without (increasing|exceeding) X above N unit
_CEILING_RE = re.compile(
    r"\bwithout\b[^.;\n]{0,60}?(?P<metric>[A-Za-z0-9][A-Za-z0-9 \-/%]{2,40}?)\s*"
    r"(?:above|exceeding|over|beyond|>=|>|of)\s*(?P<num>" + _NUM + r")\s*"
    r"(?P<unit>[a-zA-Z°/%µ]{1,12})\b", re.IGNORECASE)

#: mandated operating ranges: from A unit to B unit (cycling windows etc.)
_RANGE_RE = re.compile(
    r"\bfrom\s*(?P<lo>" + _NUM + r")\s*(?P<lounit>[a-zA-Z°/%µ]{1,8})\s*"
    r"(?:to|–|—|-)\s*(?P<hi>" + _NUM + r")\s*(?P<hiunit>[a-zA-Z°/%µ]{1,8})"
    r"\b", re.IGNORECASE)

#: the intervention proposes a value for a metric
_PROPOSE_NUM_RE = re.compile(
    r"(?P<metric>[A-Za-z0-9][A-Za-z0-9 \-/%]{2,40}?)\s*(?:at|to|above|below|of|<=|>=|"
    r"<|>|=)\s*(?P<num>" + _NUM + r")\s*(?P<unit>[a-zA-Z°/%µ]{1,12})\b",
    re.IGNORECASE)

#: explicit removal phrases targeting something the constraint mandates.
#: The bare "without …" shapes were REMOVED: a candidate that preserves
#: the mandate but describes its internals can lex so ("operated without
#: start/stop cycling to avoid the transient") — without is not, by
#: itself, proof of deletion (Article LXXXI discipline). Unmatched
#: removals now surface as typed UNCERTAIN rather than invented kills.
_REMOVAL_RE = re.compile(
    r"\b(?:eliminate|remov\w+|delet\w+|omit\w*|skip|cancel|abandon|"
    r"get rid of)"
    r"\s*(?:the |any |its |our )?\s*(?P<obj>[a-z][a-z \-/]{3,50})",
    re.IGNORECASE)

#: no verb at all: bare "without" elimination only when the object is a
#: clear mandated element (carried by the mandate span itself)
_BARE_WITHOUT_RE = re.compile(
    r"\bwithout\s+(?:the |any |its |the need for )?(?P<obj>[a-z][a-z \-/]{3,50})",
    re.IGNORECASE)

#: envelope-narrowing verbs (a range may only be narrowed by removing
#: a mandated operating condition)
_NARROW_RE = re.compile(
    r"\b(?:reduc|lower|cut|limit|restrict|narrow|avoid|shrink)\w*\b",
    re.IGNORECASE)

_STOPW = set("""a an the of to in on for with and or is are at from by as
into within not no nor but if then than so such can could may might will
would shall should must have has had be been being it its this that these
those per while without above below during""".split())

#: words too generic to PROVE that two different physical quantities are
#: the same thing (the auditor's "stack" example); a match whose only
#: shared tokens are these never proves quantity identity
_LOW_INFO = {"stack", "content", "contents", "percentage", "value", "level",
             "rate", "unit", "number", "fraction", "amount", "total",
             "type", "kind", "case", "example", "system", "design", "analysis",
             "study", "data", "record", "based", "general", "overall"}

#: tokens that DO establish same-quantity identity unambiguously
_QUANTITY_REGISTRY = {"voltage", "current", "resistance", "power", "energy",
                      "charge", "capacitance", "inductance", "temperature",
                      "pressure", "leakage", "antimony", "calcium", "tin",
                      "corrosion", "viscosity", "conductivity", "cycle",
                      "cycles", "service", "antimony", "elastomer", "seal",
                      "hydrogen", "oxygen", "nitrogen", "sulfur", "alloy"}


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z]{3,}", str(text or "").lower())
            if t not in _STOPW}

#: metric aliasing so acronym proposals bind to spelled-out mandates
#: (OCV = open-circuit voltage; measured need: the sofc case's own
#: constraint spells it out, a proposer naturally writes "OCV")
_METRIC_ALIASES = [
    (re.compile(r"\bocv\b", re.IGNORECASE), "open circuit voltage"),
    (re.compile(r"\bopen[- ]circuit\b", re.IGNORECASE), "open circuit"),
]


def _norm_metric(s: str) -> str:
    out = str(s or "")
    for rx, repl in _METRIC_ALIASES:
        out = rx.sub(repl, out)
    return out


def _metric_match(metric_a: str, metric_b: str,
                  unit_a: str = "", unit_b: str = "") -> bool:
    """Same-quantity rule (never one shared generic word):
    (i)  at least two distinctive shared tokens of length >= 4 that are
         not low-information, OR
    (ii) one shared token from the quantity registry, OR
    (iii) one shared distinctive token (not low-information, len >= 4)
         WITH a unit alias match on both sides (same unit family — the
         same-unit constraint is what disambiguates a designator like
         "float charge" from an unrelated percentage).
    Anything weaker is ambiguous — the caller must return typed
    UNCERTAIN, never an invented kill (Art. LXXXI)."""
    ta = _tokens(_norm_metric(metric_a))
    tb = _tokens(_norm_metric(metric_b))
    if not ta or not tb:
        return False
    shared = ta & tb
    if not shared:
        return False
    if any(t in _QUANTITY_REGISTRY for t in shared):
        return True
    dist = {t for t in shared if len(t) >= 4 and t not in _LOW_INFO}
    if len(dist) >= 2:
        return True
    if unit_a and unit_b and _same_unit(unit_a, unit_b) and dist:
        return True
    return False


def _mandate_spans(c: str):
    """The constraint clauses that carry mandates (floor/ceiling/range)
    — the removal target must match a MANDATED span, never constraint
    vocabulary in the abstract."""
    spans = []
    for rx in (_FLOOR_RE, _CEILING_RE, _RANGE_RE):
        for m in rx.finditer(c):
            s = max(0, m.start() - 40)
            e = min(len(c), m.end() + 40)
            spans.append(c[s:e])
    if not spans:
        spans.append(c)
    return spans


def _removal_overlap(obj: str, c: str):
    """Strong/weak overlap of a proposed removal object against the
    mandated spans (never against the whole constraint)."""
    ot = _tokens(obj)
    if not ot:
        return 0, 0
    mandate_tokens = set()
    for s in _mandate_spans(c):
        mandate_tokens |= _tokens(s)
    ov = ot & mandate_tokens
    registry = sum(1 for t in ov if t in _QUANTITY_REGISTRY)
    dist = {t for t in ov if len(t) >= 4 and t not in _LOW_INFO}
    strong_count = max(registry, len(dist))
    weak = len({t for t in ov if t not in _LOW_INFO})
    return strong_count, weak


def function_removal_check(constraint: str,
                           intervention: str) -> Dict[str, Any]:
    """Terminal kill: the intervention removes a function the user's
    constraint mandates. Deterministic; every kill carries the
    offending span + the mandate clause it violates (Art. XXIV: the
    basis is citable, not asserted). Ambiguous correspondence between
    the intervention and a mandate produces a typed UNCERTAIN state —
    never an invented scientific rejection (Art. LXXXI)."""
    c = str(constraint or "")
    i = str(intervention or "")
    if not c or not i:
        return {"killed": False}
    # (a) explicit removal of a mandated element; bare "without" only
    # binds with two distinctive matches (weak single-token wording is
    # UNCERTAIN by design)
    for rx, min_strong in ((_REMOVAL_RE, 1), (_BARE_WITHOUT_RE, 2)):
        for m in rx.finditer(i):
            obj = m.group("obj")
            strong, weak = _removal_overlap(obj, c)
            if strong >= min_strong:
                return {"killed": True, "state": "KILL",
                        "kill_class": "REMOVES_MANDATED_ELEMENT",
                        "basis": (f"intervention states {m.group(0).strip()!r} "
                                  f"— the constraint mandates: "
                                  f"{_mandate_span(c, m.group(0))}")}
            if (min_strong == 1 and strong == 0 and weak >= 1) or \
                    (min_strong == 2 and strong == 1):
                return {"killed": False, "state": "UNCERTAIN",
                        "uncertain_reason": (
                            f"removal phrasing ({m.group(0).strip()!r}) "
                            "overlaps the constraint only weakly — "
                            "mandate correspondence not established")}
    # (b) mandated floor lowered / ceiling raised with an explicit number
    unit_mismatch: Optional[str] = None
    for fm in _FLOOR_RE.finditer(c):
        for pm in _PROPOSE_NUM_RE.finditer(i):
            if _metric_match(fm.group("metric"), pm.group("metric"), fm.group("unit"), pm.group("unit")):
                if not _same_unit(fm.group("unit"), pm.group("unit")):
                    unit_mismatch = (f"metric matches "
                                     f"({fm.group('metric').strip()!r}) but "
                                     f"units differ ({fm.group('unit')!r} vs "
                                     f"{pm.group('unit')!r})")
                    continue
                if _num(pm.group("num")) < _num(fm.group("num")):
                    return {"killed": True,
                            "kill_class": "LOWERS_MANDATED_FLOOR",
                            "basis": (f"constraint mandates "
                                      f"{fm.group('metric').strip()} at/above "
                                      f"{fm.group('num')} {fm.group('unit')}; "
                                      f"intervention proposes "
                                      f"{pm.group('metric').strip()} at "
                                      f"{pm.group('num')} {pm.group('unit')}")}
    for cm in _CEILING_RE.finditer(c):
        for pm in _PROPOSE_NUM_RE.finditer(i):
            if _metric_match(cm.group("metric"), pm.group("metric"), cm.group("unit"), pm.group("unit")):
                if not _same_unit(cm.group("unit"), pm.group("unit")):
                    unit_mismatch = (f"metric matches "
                                     f"({cm.group('metric').strip()!r}) but "
                                     f"units differ ({cm.group('unit')!r} vs "
                                     f"{pm.group('unit')!r})")
                    continue
                if _num(pm.group("num")) > _num(cm.group("num")):
                    return {"killed": True,
                            "kill_class": "RAISES_MANDATED_CEILING",
                            "basis": (f"constraint forbids "
                                      f"{cm.group('metric').strip()} above "
                                      f"{cm.group('num')} {cm.group('unit')}; "
                                      f"intervention proposes "
                                      f"{pm.group('metric').strip()} at "
                                      f"{pm.group('num')} {cm.group('unit')}")}
    # (c) mandated operating range narrowed — the intervention states
    # its own range ("limit thermal cycling from 25 C to 400 C") or a
    # single value with a narrowing verb ("reduce peak temperature to
    # 400 C")
    for rm in _RANGE_RE.finditer(c):
        lo, hi = _num(rm.group("lo")), _num(rm.group("hi"))
        if not _same_unit(rm.group("lounit"), rm.group("hiunit")):
            continue
        for im in _RANGE_RE.finditer(i):
            if not _same_unit(rm.group("hiunit"), im.group("hiunit")):
                continue
            ilo, ihi = _num(im.group("lo")), _num(im.group("hi"))
            # definitional rule (Art. XXVII): any exclusion of a
            # mandated endpoint is a narrowing — no tolerance constant
            # invented by this check
            narrowed_top = ihi < hi
            raised_bottom = ilo > lo
            if (narrowed_top or raised_bottom) and _NARROW_RE.search(i):
                return {"killed": True,
                        "kill_class": "NARROWS_MANDATED_RANGE",
                        "basis": (f"constraint mandates operating "
                                  f"from {rm.group('lo')} to {rm.group('hi')} "
                                  f"{rm.group('hiunit')}; intervention "
                                  f"proposes from {im.group('lo')} to "
                                  f"{im.group('hi')} {im.group('hiunit')} "
                                  "with a narrowing verb")}
        for pm in _PROPOSE_NUM_RE.finditer(i):
            if _same_unit(rm.group("hiunit"), pm.group("unit")) and \
                    _NARROW_RE.search(i[max(0, pm.start() - 90):
                                        pm.end() + 40]):
                pn = _num(pm.group("num"))
                # narrowing the top of a mandated range (e.g. cycles
                # 25-800 C proposed to 25-400 C) removes the mandated
                # function; definitional: the proposed value must fall
                # strictly below the mandated upper endpoint —
                # no tolerance constant
                if pn < hi and _metric_overlap_with_range(
                        pm.group("metric"), c, rm):
                    return {"killed": True,
                            "kill_class": "NARROWS_MANDATED_RANGE",
                            "basis": (f"constraint mandates operating "
                                      f"from {rm.group('lo')} to "
                                      f"{rm.group('hi')} "
                                      f"{rm.group('hiunit')}; intervention "
                                      f"proposes {pm.group('metric').strip()} "
                                      f"{pn} {pm.group('unit')} with a "
                                      "narrowing verb")}
    if unit_mismatch:
        return {"killed": False, "state": "UNCERTAIN",
                "uncertain_reason": (unit_mismatch + "; the metric "
                                      "correspondence is ambiguous "
                                      "(Art. LXXXI)")}
    return {"killed": False}


def _mandate_span(constraint: str, removal_text: str) -> str:
    """The constraint span naming what the removal deletes (best-effort
    citation; a miss returns the constraint head)."""
    obj_tokens = list(_tokens(removal_text))
    for sent in re.split(r"(?<=[.;])\s+", constraint):
        st = _tokens(sent)
        if obj_tokens and len(set(obj_tokens) & st) >= 1:
            return sent.strip()[:160]
    return constraint.strip()[:160]


def _metric_overlap_with_range(metric: str, constraint: str,
                               rm: "re.Match[str]") -> bool:
    """The proposed metric is plausibly the ranged quantity: shares a
    token with the constraint span around the range match, or with the
    range's own unit context."""
    s = max(0, rm.start() - 120)
    span = constraint[s:rm.end() + 60]
    return bool(_tokens(metric) & _tokens(span))


def _num(s: str) -> float:
    return float(str(s).replace(",", "."))


def _same_unit(a: str, b: str) -> bool:
    a, b = (a or "").strip().rstrip(".").lower(), (b or "").strip().rstrip(".").lower()
    if a == b:
        return True
    aliases = {
        "percent": {"percent", "%", "pct"},
        "v": {"v", "volt", "volts"},
        "c": {"c", "°c", "deg-c", "celsius"},
    }
    for k, vs in aliases.items():
        if a in vs and b in vs:
            return True
    return False


# ---------------------------------------------------------------------------
# 3. RESTATES_THE_CONSTRAINT — terminal kill
# ---------------------------------------------------------------------------
RESTATES_JACCARD_KILL = 0.62
RESTATES_CONTAINMENT_KILL = 0.8
RESTATES_MAX_NEW_TOKENS = 3


def restates_constraint_check(constraint: str, intervention: str,
                              mechanism: Optional[str] = None
                              ) -> Dict[str, Any]:
    """Terminal kill: the intervention is a paraphrase of the constraint
    with no mechanism of its own. Two deterministic paths:
      (a) token Jaccard >= 0.62 (the whole intervention is the
          constraint reworded), OR
      (b) containment >= 0.8 (>= 80 percent of the intervention's
          tokens come from the constraint) AND fewer than 4 new content
          tokens (no mechanism vocabulary of its own).
    A proposal with real mechanism content (new design nouns/verbs)
    never trips (b) regardless of topic overlap."""
    c, i = str(constraint or ""), str(intervention or "")
    if not c or not i:
        return {"killed": False}
    tc, ti = _tokens(c), _tokens(i)
    tm = _tokens(mechanism) if mechanism else set()
    if not tc or not ti:
        return {"killed": False}
    inter = tc & ti
    j = len(inter) / len(tc | ti)
    containment = len(inter) / len(ti)
    # mechanism vocabulary vetoes the kill on BOTH paths: a proposal that
    # carries real mechanism content (new design/causal vocabulary of its
    # own) is never a restatement, regardless of topical overlap
    new_tokens = (ti | tm) - tc
    has_mechanism_content = len(new_tokens) >= 4
    if j >= RESTATES_JACCARD_KILL and not has_mechanism_content:
        return {"killed": True, "kill_class": "RESTATES_THE_CONSTRAINT",
                "jaccard": round(j, 3),
                "mechanism_content_tokens": len(new_tokens),
                "basis": (f"intervention is a paraphrase of the constraint "
                          f"(token Jaccard {j:.2f}) — it restates the "
                          "requirement, not the design")}
    if containment >= RESTATES_CONTAINMENT_KILL and \
            not has_mechanism_content:
        return {"killed": True, "kill_class": "RESTATES_THE_CONSTRAINT",
                "jaccard": round(j, 3),
                "containment": round(containment, 3),
                "basis": (f"intervention re-uses the constraint's own "
                          f"vocabulary (containment {containment:.2f}) "
                          f"with {len(new_tokens)} new content token(s) — "
                          "no mechanism of its own; it restates the "
                          "requirement, not the design")}
    return {"killed": False, "jaccard": round(j, 3),
            "containment": round(containment, 3)}


# ---------------------------------------------------------------------------
# 4. ANCHOR DOMAIN RULE — the anchor record shares the failure's domain
#    OR the candidate states the shared mechanism
# ---------------------------------------------------------------------------
_SHARED_MECHANISM_RE = re.compile(
    r"\b(?:(?:same|shared|analogous|equivalent|identical|common)"
    r"\s+(?:[a-z-]+\s+){0,3}?"
    r"(?:mechanism|principle|physics|chemistry|effect|phenomenon|"
    r"process|pathway|reaction|transport|degradation|failure mode)|"
    r"transfers?\s+(?:because|via|through|since|as)|"
    r"shared mechanism|same underlying|"
    r"works (?:by|through|via) the same|"
    r"same (?:physical|electro|thermo|mech\w*)?\s?-?(?:chemical)?\s*"
    r"(?:mechanism|process|law))\b",
    re.IGNORECASE)

#: a bare generic phrase ("same mechanism", "works through the same
#: principle") is NOT evidence of causal transfer (the auditor's
#: finding). Stated-mechanism acceptance additionally requires at least
#: one distinctive PHYSICS_LEXEME in the candidate's mechanism text.
#: Lexeme class additions disclosed per Article 7 (the r401 fixture
#: states a resuspension mechanism explicitly; the lexicon must cover
#: the effect class, not only the deposition/fouling subset):
#: resuspension/erosion/wear/entrainment/abrasion join
#: deposition/fouling as transport-effect physics.
_PHYSICS_LEXEMES = {
    "corrosion", "oxidation", "reduction", "diffusion", "transport",
    "deposition", "spallation", "expansion", "contraction", "creep",
    "fatigue", "fracture", "buckling", "torque", "stress", "strain",
    "shear", "tension", "compression", "cavitation", "fouling",
    "scaling", "nucleation", "absorption", "adsorption", "desorption",
    "convection", "conduction", "radiation", "catalysis",
    "electrolyte", "interfacial", "differential", "kinetics",
    "thermal", "thermochemical",
    "resuspension", "erosion", "wear", "entrainment", "abrasion",
}

_ANCHOR_MIN_SHARED_TOKENS = 3


def anchor_domain_check(problem: Dict[str, Any],
                        anchor_item: Dict[str, Any],
                        fields: Dict[str, str]) -> Dict[str, Any]:
    """The anchor evidence record must share the failure's domain OR the
    candidate's mechanism text must state the shared mechanism (owner
    directive item 4). Deterministic lexical instrument: the anchor's
    recorded text vs the problem's device/failure/domain text. The
    anchor's text is read from every field the MECHANISM_SPACE
    structured item carries (flat keys AND the fields/relevance
    sub-dicts — the lean construction stores the abstract under
    fields.abstract, never flat)."""
    pt = " ".join(str(problem.get(k) or "") for k in
                  ("domain", "device", "failure", "failure_mode"))
    _flat = " ".join(str(anchor_item.get(k) or "") for k in
                     ("title", "abstract", "text", "content",
                      "record_text"))
    _sub = anchor_item.get("fields") or {}
    _rel = anchor_item.get("relevance") or {}
    _subtxt = " ".join(str(_sub.get(k) or "") for k in
                       ("system", "abstract", "mechanism",
                        "observed_effect", "intervention", "constraints"))
    _reltxt = " ".join(str(_rel.get(k) or "") for k in
                       ("domain", "failure_mode", "mechanism",
                        "expected_effect", "material", "operating_regime"))
    at = " ".join([_flat, _subtxt, _reltxt])
    pt_t, at_t = _tokens(pt), _tokens(at)
    shared = pt_t & at_t
    # distinctive tokens only: low-information vocabulary cannot prove an
    # anchor is in the problem's domain
    distinctive = {t for t in shared
                   if len(t) >= 4 and t not in _LOW_INFO}
    shared_domain = len(distinctive) >= _ANCHOR_MIN_SHARED_TOKENS
    mech_text = " ".join(str(fields.get(k) or "") for k in
                         ("mechanism", "intervention"))
    mech_tokens = _tokens(mech_text)
    stated = (bool(_SHARED_MECHANISM_RE.search(mech_text))
              and bool(mech_tokens & _PHYSICS_LEXEMES))
    return {
        "shared_domain": shared_domain,
        "n_shared_tokens": len(shared),
        "shared_tokens": sorted(shared)[:12],
        "shared_mechanism_stated": stated,
        "ok": bool(shared_domain or stated),
    }


# ---------------------------------------------------------------------------
# R11 owner item 6 (2026-11-14): QUESTION-TYPE ROUTING. The audited live
# regression: fu-004, a PREDICTOR question ("propose the most
# cost-effective measurable leading indicator...") was answered with a
# tanh-PID CONTROLLER (Kp/Ki/Kd gain factors modulating a valve). The
# routing decision happens BEFORE any LLM call: a predictor question's
# candidate must be an INDICATOR (a monitored quantity + threshold),
# never a controller (a closed-loop actuator). Deterministic, zero-LLM,
# recorded on the candidate either way (never a silent drop, Art.
# XXI.3). Serves: Art. XIX (the measured regression decides the
# instrument), Art. X (labels describe the actual delivery).
# ---------------------------------------------------------------------------

#: the controller signatures (the CORE actuation vocabulary — two or
#: more co-occurring is a controller, not a monitored indicator)
_CONTROLLER_CORE_SIGNS = (
    r"\bPID\b", r"\bKp\b", r"\bKi\b", r"\bKd\b",
    r"proportional\s+gain", r"integral\s+gain", r"derivative\s+gain",
    r"gain\s+schedule", r"\bcontroller\b", r"control\s+loop",
    r"control\s+valve", r"\bmodulat", r"\bactuator\b", r"closed[- ]loop",
    r"\bsetpoint\b", r"control\s+algorithm", r"\bactu(at|ing)\b",
)


def question_type_match_check(
        problem: Optional[Dict[str, Any]],
        fields: Dict[str, Any]) -> Dict[str, Any]:
    """A predictor-design question's candidate must propose an
    INDICATOR (a monitored quantity, a threshold), never a CONTROLLER
    (a closed-loop actuator with gains). Returns {checked,
    rejected, reason_class, reason, n_controller_signatures,
    matched_signatures} — the typed verdict rides the candidate or
    the admission record either way."""
    qtype = str((problem or {}).get("question_type") or "")
    text = " ".join(str(fields.get(k) or "") for k in
                    ("intervention", "mechanism", "expected_effect",
                     "predicted_effect", "falsification_test"))
    out: Dict[str, Any] = {
        "instrument_version": INTERVENTION_GATE_VERSION,
        "instrument": "question_type_match_check/1.0.0",
        "question_type": qtype,
        "checked": True,
        "rejected": False,
        "reason_class": None,
        "reason": None,
        "n_controller_signatures": 0,
        "matched_signatures": []}
    if qtype != "predictor-design":
        out["checked"] = False
        return out
    matched = [p for p in _CONTROLLER_CORE_SIGNS
               if re.search(p, text or "", re.IGNORECASE)]
    out["n_controller_signatures"] = len(matched)
    out["matched_signatures"] = matched[:6]
    if len(matched) >= 2:
        out.update({
            "rejected": True,
            "reason_class": "ROUTING_PREDICTOR_QUESTION_PROPOSED_CONTROLLER",
            "reason": (
                "a predictor question asks for a measurable leading "
                "INDICATOR and its threshold; this candidate proposes "
                "a CONTROLLER (actuation/gain signatures: "
                f"{', '.join(m.strip('\\\\b') for m in matched[:4])}) — "
                "the audited fu-004 regression class (owner R11 item "
                "6); route to an indicator, never a controller")})
    return out
