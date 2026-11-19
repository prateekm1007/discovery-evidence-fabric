#!/usr/bin/env python3
"""stripping_direction/1.0.0 — the AMMONIA-STRIPPING direction and
premise bind (R103, claim c-0117; AM89 directive 2, the HO14-12
inverted-direction defect class).

THE DEFECT (typed in the R102 verdict, AM89/V89): the generator
(a) proposed LOWERING the air-to-water ratio ("effectively lowering
the instantaneous A/W ratio to maximize liquid film contact time")
— inverted: stripping efficiency IMPROVES with a RAISED A/W ratio
(more gas-side capacity per unit liquid, steeper NH3 partial-pressure
gradient); and (b) premised "ammonia stripping inhibition at high pH"
— backwards: RAISING pH shifts the NH4+ <=> NH3 + H+ equilibrium to
NH3, the strippable free species (pKa ~ 9.25 at 25 C: at pH 10.25,
~90% of TAN is free NH3; at pH 11.25, ~99%). High pH PROMOTES
stripping — the entire industrial-ammonia-strippers design basis.
The deterministic direction/equilibrium scans and the LLM sign check
all missed it (the auditor's full-read caught it, auditor Art. 2).

THE BIND (domain-gated, precision-first — the gate is the problem's
own device/failure text naming ammonia stripping; no generic
vocabulary is baked in):

  STRIPPING_DIRECTION_INVERTED — the mechanism states or implies
    LOWERING the air-to-water (A/W) ratio as a benefit for ammonia
    removal. Correct: RAISE A/W.

  STRIPPING_PREMISE_INVERTED — the answer carries the "high pH
    inhibits/hinders stripping" premise (or the equivalent "raise pH
    to reduce stripping" claim). Correct: raise pH (and temperature)
    to promote stripping.

Physics basis (typed, the classical ammonia-stripper design basis):
  - equilibrium: NH4+ <=> NH3(aq) + H+, pKa ~ 9.25 (25 C); fraction
    free NH3 = 1/(1 + 10^(pKa - pH)); the mechanism must RAISE pH to
    shift toward NH3.
  - gas side: Henry/van 't Hoff — NH3 solubility FALLS with
    temperature (exothermic dissolution), so RAISING water
    temperature raises the stripping driving force.
  - A/W: the stripping factor S = Kya * G/L; RAISING the gas rate G
    (air-to-water ratio) raises S toward the removal target.

The computed legs (van 't Hoff temperature dependence + the free-NH3
fraction) live in physics_checks.py (the Art. 3 CHECKS registry);
this module is the LEXICAL direction bind wired into
r30_physics_direction_scan. Zero LLM, deterministic. The
authoritative direction read stays the auditor's.
"""
from __future__ import annotations

import re
from typing import Any, Dict

RECORD = "STRIPPING_DIRECTION/1.0.0"

# the domain gate: the problem names ammonia stripping (device,
# failure, or question text; list- or string-typed user_variables)
_AMMONIA = re.compile(r"\b(?:ammonia|nh\s?3|nh4)\b", re.I)
_STRIPPING = re.compile(r"\bstripp(?:ing|er|ed|e)\b", re.I)


def _texts(problem: Dict[str, Any]) -> str:
    out = []
    for k in ("device", "failure", "failure_mode", "question",
              "user_variables", "constraint", "followup_finding"):
        v = problem.get(k)
        if isinstance(v, (list, tuple)):
            out.extend(str(x) for x in v)
        elif v:
            out.append(str(v))
    return " ".join(out)


def is_ammonia_stripping(problem: Dict[str, Any]) -> bool:
    """The domain gate: the problem's own text names ammonia AND
    stripping (the packed-tower degassing context)."""
    t = _texts(problem)
    return bool(_AMMONIA.search(t) and _STRIPPING.search(t))


# --- the inverted-direction nets ---------------------------------------

_AW = r"(?:air[- ]to[- ]water\s+ratio|air/?water\s+ratio|\bA/?W\s+ratio|\bA/W\b)"
_LOWER = (r"\b(?:lower\w*|reduc\w*|decreas\w*|minimi[sz]\w*|drop\w*|"
          r"cut(?:ting)?\s+down|shrink\w*)\b")
AW_LOWERED = re.compile(
    _LOWER + r"[^.]{0,120}?" + _AW + r"|" + _AW + r"[^.]{0,60}?" +
    _LOWER, re.I)
AW_LOWERED_BENEFIT = re.compile(
    _AW + r"[^.]{0,160}?\b(?:to\s+)?(?:maximi[sz]\w*|improv\w*|"
    r"enhanc\w*|optimi[sz]\w*|increas\w*|better\w*|greater\w*)\b", re.I)

_PH_HIGH = r"(?:high|elevated|alkaline|excess\w*)\s+(?:\s*pH\b|ph\b)"
_INHIBIT = (r"\b(?:inhibit\w*|retard\w*|hindr\w+|imped\w*|suppress\w*|"
            r"reduc\w*|decreas\w*|limit\w*|impair\w*|degrad\w*|"
            r"diminish\w*|weaken\w*|slow\w*|hamper\w*)\b")
PREMISE_INHIBIT = re.compile(
    _PH_HIGH + r"[^.]{0,120}?" + _INHIBIT + r"|" + _INHIBIT +
    r"[^.]{0,120}?" + _PH_HIGH, re.I)
_STRIP_CTX = re.compile(
    r"\b(?:stripp\w+|mass[- ]transfer|remov\w+|liberat\w+|volatil\w+|"
    r"transfer\w*)\b", re.I)
PH_RAISE_HURTS = re.compile(
    r"\b(?:rais\w+|increas\w+|elevat\w+|boost\w*|push\w*)\b[^.]{0,40}?"
    r"\bpH\b[^.]{0,120}?" + _INHIBIT, re.I)

_MECHANISM_SPAN = re.compile(
    r"NOVELTY STATEMENT.{0,2600}?(?:\n[A-Z][A-Z ]{6,}\n|$)", re.S)
_PHYSICS_SPAN = re.compile(
    r"PHYSICS CHECK.{0,1800}?(?:\n[A-Z][A-Z ]{6,}\n|$)", re.S)


_BILL_SPAN = re.compile(
    r"IMPLEMENTATION BILL.{0,4000}?(?:\n[A-Z][A-Z ]{6,}\n|$)", re.S)


def _spans(answer: str, whole: bool = False):
    """The scanned spans: the NOVELTY STATEMENT, PHYSICS CHECK and
    IMPLEMENTATION BILL sections (direction claims live in bills too
    — the HO14-12 A/W-lowering byte sits in Row 2's description).
    whole=True returns the full answer (the direct A/W net)."""
    a = str(answer or "")
    if whole:
        return [a]
    out = []
    for rx in (_MECHANISM_SPAN, _PHYSICS_SPAN, _BILL_SPAN):
        m = rx.search(a)
        if m:
            out.append(m.group(0))
    if not out:
        out.append(a[:2600])
    return out


def scan_stripping_direction(problem: Dict[str, Any],
                             answer: str) -> Dict[str, list]:
    """The ammonia-stripping direction/premise bind. Fires only when
    the problem is domain-gated (is_ammonia_stripping) and the
    answer's mechanism/physics spans carry the inverted claims.
    Returns typed findings ({} = clean/silent)."""
    if not is_ammonia_stripping(problem):
        return {}
    a = str(answer or "")
    spans = _spans(a)
    out: Dict[str, list] = {}
    for span in _spans(a, whole=True):
        m = AW_LOWERED.search(span)
        if m:
            ctx = span[max(0, m.start() - 70):m.end() + 90]
            out.setdefault("STRIPPING_DIRECTION_INVERTED", []).append(
                "the mechanism LOWERS the air-to-water ratio — ammonia "
                "stripping IMPROVES with a RAISED A/W ratio (the "
                "stripping factor S = Kya*G/L rises with the gas "
                "rate) | ..." + ctx[:150] + "...")
            break
    if "STRIPPING_DIRECTION_INVERTED" not in out:
        for span in _spans(a, whole=True):
            m = AW_LOWERED_BENEFIT.search(span)
            if m:
                pre = span[max(0, m.start() - 90):m.start()]
                import re as _re
                if _re.compile(_LOWER, re.I).search(pre):
                    ctx = span[max(0, m.start() - 70):m.end() + 90]
                    out.setdefault(
                        "STRIPPING_DIRECTION_INVERTED", []).append(
                        "the mechanism claims a benefit from a lowered "
                        "air-to-water ratio — stripping improves with "
                        "a RAISED A/W | ..." + ctx[:150] + "...")
                    break
    for span in spans:
        m = PREMISE_INHIBIT.search(span)
        if m and _STRIP_CTX.search(span):
            ctx = span[max(0, m.start() - 90):m.end() + 110]
            out.setdefault("STRIPPING_PREMISE_INVERTED", []).append(
                "the premise reads HIGH pH as inhibiting stripping — "
                "backwards: raising pH shifts NH4+ <=> NH3 + H+ toward "
                "free NH3 (pKa ~ 9.25 at 25 C; pH 10.25 ~ 90% free "
                "NH3), the stripper design basis — high pH PROMOTES "
                "stripping | ..." + ctx[:160] + "...")
            break
        m2 = PH_RAISE_HURTS.search(span)
        if m2 and _STRIP_CTX.search(span):
            ctx = span[max(0, m2.start() - 90):m2.end() + 110]
            out.setdefault("STRIPPING_PREMISE_INVERTED", []).append(
                "the mechanism raises pH while claiming a stripping "
                "reduction — raising pH PROMOTES NH3 liberation (pKa "
                "~ 9.25) | ..." + ctx[:160] + "...")
            break
    return out
