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

  2. function_removal_check — TERMINAL kill: the intervention removes
     a function the user's constraint mandates (lowers a mandated
     floor, raises a mandated ceiling, narrows a mandated operating
     range, or explicitly eliminates a mandated element). The owner's
     directive: these kills are terminal — a candidate that solves the
     failure by deleting a requirement the user fixed has not solved
     the problem the user has.

  3. restates_constraint_check — TERMINAL kill: the intervention is a
     paraphrase of the constraint with no mechanism of its own
     (measured: token Jaccard against the constraint, no new
     mechanism content). "Survive 500 cycles" is the requirement, not
     the invention.

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

#: explicit removal phrases targeting something the constraint mandates
_REMOVAL_RE = re.compile(
    r"\b(?:eliminate|remov\w+|delet\w+|omit\w*|skip|cancel|abandon|"
    r"operat\w+ without|run(?:ning)? without|without (?:the |any |its )?)"
    r"\s*(?P<obj>[a-z][a-z \-/]{3,50})", re.IGNORECASE)

#: envelope-narrowing verbs (a range may only be narrowed by removing
#: a mandated operating condition)
_NARROW_RE = re.compile(
    r"\b(?:reduc|lower|cut|limit|restrict|narrow|avoid|shrink)\w*\b",
    re.IGNORECASE)

_STOPW = set("""a an the of to in on for with and or is are at from by as
into within not no nor but if then than so such can could may might will
would shall should must have has had be been being it its this that these
those per while without above below during""".split())


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


def _metric_match(metric_a: str, metric_b: str) -> bool:
    """Two metric phrases name the same quantity when they share a
    distinctive content token (e.g. 'open-circuit voltage' vs 'OCV
    voltage' share 'voltage' after aliasing; 'stack mass' vs 'mass')."""
    ta, tb = _tokens(_norm_metric(metric_a)), _tokens(_norm_metric(metric_b))
    if not ta or not tb:
        return False
    shared = ta & tb
    return bool(shared) and any(len(t) >= 4 for t in shared)


def function_removal_check(constraint: str,
                           intervention: str) -> Dict[str, Any]:
    """Terminal kill: the intervention removes a function the user's
    constraint mandates. Deterministic; every kill carries the
    offending span + the mandate clause it violates (Art. XXIV: the
    basis is citable, not asserted)."""
    c = str(constraint or "")
    i = str(intervention or "")
    if not c or not i:
        return {"killed": False}
    # (a) explicit removal of a mandated element
    c_tokens = _tokens(c)
    for m in _REMOVAL_RE.finditer(i):
        obj = m.group("obj")
        ot = _tokens(obj)
        if ot and len(ot & c_tokens) >= 1:
            # only a kill when the removed object is part of the
            # mandated function (a token the constraint itself names)
            return {"killed": True, "kill_class": "REMOVES_MANDATED_ELEMENT",
                    "basis": (f"intervention states {m.group(0).strip()!r} "
                              f"— the constraint mandates: "
                              f"{_mandate_span(c, m.group(0))}")}
    # (b) mandated floor lowered / ceiling raised with an explicit number
    for fm in _FLOOR_RE.finditer(c):
        for pm in _PROPOSE_NUM_RE.finditer(i):
            if _metric_match(fm.group("metric"), pm.group("metric")) and \
                    _same_unit(fm.group("unit"), pm.group("unit")):
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
            if _metric_match(cm.group("metric"), pm.group("metric")) and \
                    _same_unit(cm.group("unit"), pm.group("unit")):
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
            narrowed_top = ihi < hi * 0.98
            raised_bottom = ilo > lo * 1.02
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
                # function; the proposed metric must plausibly BE the
                # ranged quantity (token overlap with the range span)
                if pn < hi * 0.98 and _metric_overlap_with_range(
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
    if not tc or not ti:
        return {"killed": False}
    inter = tc & ti
    j = len(inter) / len(tc | ti)
    containment = len(inter) / len(ti)
    new_tokens = ti - tc
    has_mechanism_content = len(new_tokens) >= 4
    if j >= RESTATES_JACCARD_KILL:
        return {"killed": True, "kill_class": "RESTATES_THE_CONSTRAINT",
                "jaccard": round(j, 3),
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

_ANCHOR_MIN_SHARED_TOKENS = 2


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
    shared_domain = len(shared) >= _ANCHOR_MIN_SHARED_TOKENS
    mech_text = " ".join(str(fields.get(k) or "") for k in
                         ("mechanism", "intervention"))
    stated = bool(_SHARED_MECHANISM_RE.search(mech_text))
    return {
        "shared_domain": shared_domain,
        "n_shared_tokens": len(shared),
        "shared_tokens": sorted(shared)[:12],
        "shared_mechanism_stated": stated,
        "ok": bool(shared_domain or stated),
    }
