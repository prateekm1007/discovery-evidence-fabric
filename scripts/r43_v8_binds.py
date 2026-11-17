#!/usr/bin/env python3
"""r43_v8_binds.py — the V8 GENERATION binds (claim c-0060, the R42
verdict D1/D2/D5, pre-registered before any v8 problem is read).

MEASURED BASIS (the auditor's R42 verdict on the first v7 acceptance
score — mean 2.917/4 = 72.9%, ACCEPTANCE NOT GRANTED):
  F54/F58 intervention monoculture: the generator still defaults to
    duty-cycle templates (HO7-05 current-density cycling instead of
    deposition chemistry — the designed monoculture-break FAILED;
    HO7-02 thermal-cycling) and 3 of 6 interventions escaped the
    diversity cap by OMITTING the MECHANISM CLASS declaration
    (MECHANISM_CLASS_UNSTATED x3, the cap never bound on them);
    HO7-03's pricing positive control FAILED (unpriced duty cycle).
  F57 scan precision: the machine's 8 INPUT_UNAVAILABLE on v7 are ALL
    false positives (free-prose regex flags words/concepts/specs as
    "inputs": 'a metering pump', 'existing PLC control
    infrastructure', 'controlled bypass flow', 'mechanism', '30-day
    lead time', 'periodic visual splice inspection', 'energy
    efficiency decline', 'stated spec: mesophilic 38C'); 7
    ALLOWED_ROW_OUTSIDE are mostly wordform/apparatus false positives
    ('vs. standard practice uses no additional hardware', 'consumables
    or maintenance', 'and pressure transducer' fragments).
  D5 predictor framing: HO7-09/10/12 conflate detection with
    intervention (the direction line states an action the "mechanism"
    takes on the driver instead of the detected variable's direction).

THE V8 BINDS (generation-side, not checker-side — the contract makes
the generator produce the structure; the scans read the structure):

  INT BINDS (SYS_A1_INT_V8 = V7.2 + the four clauses below):
  1. CANDIDATE-CLASS ENUMERATION (D1a): the bill opens with a
     CANDIDATE CLASSES section enumerating >= 3 mechanistically
     DISTINCT candidate classes for the failure (one line each: class
     phrase + the physics reason), then SELECTED: <class> + one line
     why. At least ONE non-duty-cycle candidate must be enumerated
     (the generator must LOOK before defaulting); when the SELECTED
     class is a duty cycle / setpoint schedule, the rejection of the
     non-duty-cycle candidate(s) must be stated ON PHYSICS.
  2. MECHANISM-CLASS DECLARATION, HARD (D1b/F58): "MECHANISM CLASS:
     <one phrase>" in plain text (no markdown emphasis). A missing
     declaration is a typed defect AND the machine INFERs the class
     and counts it toward the set cap — an omitted declaration no
     longer escapes the diversity histogram.
  3. OPERATIONAL COST, QUANTIFIED (D1c): every schedule / duty-cycle
     / setpoint modulation carries an "OPERATIONAL COST:" line with a
     QUANTIFIED magnitude (a number with unit or percent, or an
     explicit "zero" with the off-production reason). The V7.7 escape
     (the phrase present, no number) is closed.
  4. SIGNALS USED (D2 structured side): the bill carries a
     "SIGNALS USED:" line listing EVERY online signal the mechanism
     requires to actuate or trigger, each with its source (existing
     sensor / permitted measure / derived from <permitted signals>),
     or the explicit word "none" (open-loop). The input-availability
     check reads THIS declaration, never free prose.

  PREDICTOR BINDS (SYS_A1F_V8 = SYS_A1F_V5 + two clauses):
  5. INPUT INVENTORY (D2): the bill carries an "INPUT INVENTORY:"
     section: every physical quantity the scheme's math consumes —
     including every quantity inside a derived index — one line each,
     "<quantity> — source: ALREADY-RECORDED(<problem wording>) |
     DERIVED(<from which permitted signals / stated physics>)". The
     closure check reads it against the PHYSICS CHECK's stated
     relation: a quantity the stated relation consumes that is
     neither in the inventory nor derivable from the permitted
     signals is an unavailable input (the HO6-12 class: LSI needs
     ion-activity products under temperature/flow-only meters).
  6. DIRECTION OF EFFECT, DETECTION-FRAMED (D5): the PHYSICS CHECK
     carries a "DIRECTION OF EFFECT:" line stating the DETECTED
     variable, the direction the FAILURE DRIVER moves as the detected
     variable moves (as X rises, driver Y rises/falls because
     <relation>), and the lead claim. The line must NOT state an
     intervention action ("the mechanism raises/lowers/maintains X")
     — a predictor OBSERVES the variable; it does not act on it.

THE SCANS (deterministic, zero-LLM; the free-prose input/measure
regex hunting of V7.7 — _MEASUREMENT/_QTY_COMPOUND/_QTY_OBJECT/
_DERIVED over the mechanism span and the r26 _added_spans free-prose
extraction — is RETIRED in V8 per the R42 delete list, superseded by
the structured extraction below; the V7.7 machine file stays
byte-frozen as the instrument of record for the v7 run):
  scan_candidate_classes_v8(a)      — D1a structure + preference
  scan_mechanism_class_v8(a, used)  — D1b: declaration (emphasis-
                                      stripped) + INFERRED class
                                      counted toward the cap (F58)
  scan_duty_pricing_v8(a)           — D1c: quantified cost or typed
                                      explicit zero
  scan_input_availability_v8(p, a)  — D2: reads SIGNALS USED /
                                      INPUT INVENTORY + the closure
                                      check, never free prose
  scan_allowed_rows_v8(p, a)        — D2: structured bill-row
                                      extraction (head object after
                                      the procurement tag; replaces-
                                      X is the OLD item; burden/
                                      comparative echoes excluded;
                                      control-apparatus implements
                                      the schedule class)
  scan_predictor_direction_v8(a)    — D5: detection framing

All findings feed the machine's NEUTRAL repair directive (quoted
back, never hidden); residuals are disclosed. The authoritative reads
stay the auditor's (Art. 3: the machine's self-checks fail-open
typed; the scoring gates stay the auditor's).
"""
from __future__ import annotations

import re

from r29_a1w_v72_contract import SYS_A1_INT_V72, SYS_A1F_V5
from r40_v77_directive import V77_REPAIR_DIRECTIVE
from r30_allowed_class_scan import (
    ALLOWED_SPAN, PERMITTED_SPAN, parse_permitted_set, PARAM_SHAPE)
from r30_physics_direction_scan import _content_stems

# ---------------------------------------------------------------------------
# section parsing (markdown-tolerant: `**SECTION**`, `SECTION —`, tables)
# ---------------------------------------------------------------------------

def _strip_md(text: str) -> str:
    """Markdown emphasis removed (the delete-list item: a trailing
    '**' must not reach a class declaration — the HO7-05 artifact)."""
    return re.sub(r"\*+", "", str(text or ""))


def _section(answer: str, name: str, limit: int = 3000) -> str:
    """The named labeled section (markdown-bold tolerant), from its
    heading to the next ALL-CAPS heading line or the limit."""
    a = _strip_md(answer)
    m = re.search(rf"(?<![A-Z]){re.escape(name)}\s*[—:\-]?\s*\n?", a,
                  re.I)
    if not m:
        return ""
    body = a[m.end():m.end() + limit]
    cut = re.search(r"\n\s*[A-Z][A-Z0-9 (\-/&,_]{3,}[—:\-]?\s*\n", body)
    return body[:cut.start()] if cut else body


_BILL_SECTION = re.compile(r"IMPLEMENTATION BILL", re.I)
_HEADING_LINE = re.compile(r"^\s*[A-Z]{3,}[A-Z0-9 (\-/&,_]{2,}")


def _bill_rows(answer: str) -> list:
    """Structured rows of the IMPLEMENTATION BILL section only: tagged
    rows '(x) ...', bullet rows '- ...', digit rows, and TABLE rows
    '| ... | ... |' (the HO6-12 format). Burden/test sections are cut
    at the next heading."""
    a = _strip_md(answer)
    m = _BILL_SECTION.search(a)
    if not m:
        return []
    rows = []
    body = a[m.end():m.end() + 4000]
    for ln in body.splitlines():
        if _HEADING_LINE.match(ln.strip()):
            break
        s = ln.strip()
        if not s:
            continue
        if s.startswith("|"):
            if re.match(r"^\|[\s\-|:]+\|$", s):  # table ruler
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 3:
                rows.append(" | ".join(cells))
        elif re.match(r"^-\s", s) or re.match(r"^\d", s) or \
                re.match(r"^\([a-dA-D]\)", s):
            rows.append(s)
    return rows


# ---------------------------------------------------------------------------
# D1a — candidate-class enumeration
# ---------------------------------------------------------------------------

_DUTY_CLASS = re.compile(
    r"\b(duty[ -]?cycl\w*|setpoint|set[ -]?point|schedule|on[/-]off|"
    r"periodic\w*|cyclic\w*|timer|interval|dosing schedule|pulse[sd]?"
    r"\s+(dosing|operation)|derate|curtail\w*)\b", re.I)
_CAND_HEAD = re.compile(r"^\s*(?:[-*\d.)\s]*)"
                        r"([A-Z][^—:\n]{4,70}?)(?:\s*[—:]\s*|\s*-\s*)")

_CANDIDATE_SECTION = "CANDIDATE CLASSES"
_SELECTED = re.compile(
    r"SELECTED\s*[:\-]\s*([^\n]{3,80})", re.I)
_REJECT = re.compile(
    r"reject\w*|declin\w*|ruled?\s+out|not\s+selected|inferior|"
    r"loses?\s+to|dominat\w*|preferred\s+over|worse\s+than|"
    r"outperform\w*", re.I)


def _class_lines(sec: str) -> list:
    """Candidate lines: each names a class phrase before the physics
    justification separator."""
    out = []
    for ln in sec.splitlines():
        s = ln.strip()
        if not s or _SELECTED.search(s):
            continue
        if not re.match(r"^[-*\d.)\s]*[A-Za-z]", s):
            continue
        m = _CAND_HEAD.match(s)
        if m:
            out.append(m.group(1).strip())
        elif re.match(r"^[-*\d.)\s]*[A-Za-z].{4,}", s) and len(out) < 9:
            out.append(s.lstrip("-*0123456789.) ").strip()[:70])
    return out


def scan_candidate_classes_v8(a: str) -> dict:
    """D1a. Fires CANDIDATE_CLASSES_MISSING when the section is
    absent; CANDIDATE_CLASSES_UNDERSET when fewer than 3 DISTINCT
    classes are enumerated (distinct = pairwise stem-set none a
    subset of the other); NONDUTY_CANDIDATE_ABSENT when every
    candidate is duty-cycle-shaped (the generator must LOOK at
    non-duty-cycle physics before defaulting); DUTY_CYCLE_PREFERENCE_
    UNPROVEN when the SELECTED class is duty-cycle-shaped, a
    non-duty-cycle candidate exists, and no rejection-on-physics is
    stated for it."""
    sec = _section(a, _CANDIDATE_SECTION)
    findings = {}
    if not sec:
        return {"CANDIDATE_CLASSES_MISSING": [
            "the bill carries no CANDIDATE CLASSES section — enumerate "
            ">= 3 mechanistically distinct candidate classes (one line "
            "each: class + the physics reason), then SELECTED: <class> "
            "with the physics justification"]}
    cands = _class_lines(sec)
    stems = [_content_stems(c) for c in cands if c]
    distinct = []
    for i, si in enumerate(stems):
        if not si:
            continue
        if all(not (si <= sj or sj <= si)
               for j, sj in enumerate(stems) if j != i and sj):
            distinct.append(cands[i])
    if len(distinct) < 3:
        findings["CANDIDATE_CLASSES_UNDERSET"] = [
            f"the CANDIDATE CLASSES section enumerates only "
            f"{len(distinct)} distinct class(es) — the bind is >= 3 "
            "mechanistically distinct candidates before selection"]
    sel = _SELECTED.search(sec) or _SELECTED.search(_strip_md(a))
    nonduty = [c for c in distinct if not _DUTY_CLASS.search(c)]
    if not nonduty:
        findings["NONDUTY_CANDIDATE_ABSENT"] = [
            "every enumerated candidate class is duty-cycle/setpoint-"
            "schedule-shaped — enumerate at least one non-duty-cycle "
            "candidate (chemistry, material state, geometry/arrange-"
            "ment, flow path, force balance, energy removal) and "
            "select it unless the physics rejects it"]
    if sel and _DUTY_CLASS.search(sel.group(1)):
        if nonduty:
            rest = _strip_md(a)
            # the rejection must be stated (physics words near the
            # reject/reason verbs) — a duty-cycle selection over a
            # viable non-duty-cycle candidate needs the physics case
            if not _REJECT.search(sec):
                findings["DUTY_CYCLE_PREFERENCE_UNPROVEN"] = [
                    "the SELECTED class is duty-cycle-shaped while a "
                    "non-duty-cycle candidate is enumerated — state "
                    "the PHYSICS that rejects the non-duty-cycle "
                    "candidate (the preference bind); convenience is "
                    "not a physics reason"]
    if not sel and not findings:
        findings["CANDIDATE_CLASSES_MISSING"] = [
            "the CANDIDATE CLASSES section carries no SELECTED: line —"
            " name the selected class and the physics justification"]
    return findings


# ---------------------------------------------------------------------------
# D1b — mechanism-class declaration + INFERRED classes count (F58)
# ---------------------------------------------------------------------------

_MECH_DECL = re.compile(r"MECHANISM\s+CLASS\s*[:\-]\s*([^\n]{3,80})",
                        re.I)
# the inference taxonomy: coarse, deterministic, DISCLOSED as
# inference (the authoritative class read stays the auditor's)
_INFER_RULES = [
    ("duty-cycle modulation of a setpoint", re.compile(
        r"\b(duty[ -]?cycl\w*|on[/-]off cycl\w*|setpoint (?:modulat|"
        r"adjust|schedul)|schedul\w+ (?:the )?(?:dosing|operation|"
        r"cleaning|pulse)|timer[- ]set|pulsed? dosing|periodic "
        r"(?:dosing|purge|reversal|cleaning)|intermittent "
        r"(?:operation|dosing)|derate|curtail\w*)\b", re.I)),
    ("thermal-cycling", re.compile(
        r"\b(thermal (?:shock|cycl\w+)|quench\w*|heat[ -]?check\w*|"
        r"thermal transient\w*|thermal ramp\w*)\b", re.I)),
    ("wet-dry-cycling", re.compile(r"\b(wet[- ]?dry|wetting/drying)\b",
                                   re.I)),
    ("charge-discharge-cycling", re.compile(
        r"\b(charge[\s\-/]*(?:and|or)?\s*discharge|discharge[\s\-/]*"
        r"(?:and|or)?\s*charge)\b", re.I)),
    ("vibration", re.compile(r"\b(vibrat\w+|sonicat\w+|ultrasonic\w+)\b",
                             re.I)),
    ("process-chemistry additive", re.compile(
        r"\b(additive|surfactact\w*|surfactant|dos\w+ (?:of|rate)|"
        r"inhibitor|flocculant|antifoam|coagulant|reagent|catalyst)\b",
        re.I)),
    ("material-state conversion", re.compile(
        r"\b(conversion (?:coat|treatment|film)|phase[ -]?chang\w+|"
        r"passivat\w+|anodiz\w+|plating|oxide layer|conversion "
        r"layer)\b", re.I)),
    ("geometry/arrangement change", re.compile(
        r"\b(relocat\w+|reposition\w+|rerout\w+|baffle|redistribut\w+|"
        r"reorient\w+|spacing|clearance (?:increase|change)|"
        r"arrangement)\b", re.I)),
    ("procedure/inventory replacement", re.compile(
        r"\b(replac\w+ (?:the )?(?:part|component|consumable|element)"
        r"|swap\w*|substitut\w+|procedur\w+ chang\w*|inspection "
        r"interval)\b", re.I)),
    ("detection/monitoring software", re.compile(
        r"\b(software[- ]only|detection (?:scheme|algorithm)|monitor"
        r"ing (?:scheme|algorithm)|index calculator|trend analysis)\b",
        re.I)),
]


def infer_mechanism_class(a: str) -> str:
    """The coarse inferred class of an (undeclared) bill — F58: the
    inference COUNTS toward the set histogram so an omitted
    declaration cannot escape the diversity cap."""
    txt = _strip_md(a)
    mech = _section(txt, "NOVELTY STATEMENT") or txt[:2600]
    for name, rx in _INFER_RULES:
        if rx.search(mech):
            return name
    return "unclassified"


def scan_mechanism_class_v8(a: str, used: dict | None) -> dict:
    """D1b. MECHANISM_CLASS_UNSTATED fires on a missing/plain-less
    declaration (it is MANDATORY), but the histogram binds on the
    DECLARED class when present and the INFERRED class otherwise —
    an omitted declaration no longer escapes the cap (F58). The cap
    itself (MECHANISM_TEMPLATE_MONOCULTURE) fires when the counted
    class would become the third of its class in the set."""
    txt = _strip_md(a)
    m = _MECH_DECL.search(txt)
    findings = {}
    if not m:
        findings["MECHANISM_CLASS_UNSTATED"] = [
            "the bill does not declare 'MECHANISM CLASS: <one phrase>' "
            "in plain text — the declaration is mandatory; the machine "
            "additionally infers the class and counts it toward the "
            "set cap (an omitted declaration does not escape the "
            "diversity histogram)"]
        cls = infer_mechanism_class(txt)
    else:
        cls = m.group(1).strip().lower().rstrip(" .")
    if used and used.get(cls, 0) >= 2:
        findings["MECHANISM_TEMPLATE_MONOCULTURE"] = [
            f"mechanism class '{cls[:50]}' already appears in "
            f"{used.get(cls, 0)} rows of this set (declared or "
            "inferred) — the cap is 2 per 6 interventions; deliver a "
            "different mechanism class"]
    return findings


def counted_class(a: str) -> str:
    """The class the driver's set histogram counts for this row: the
    declared class (emphasis-stripped) when present, the inferred
    class otherwise (F58)."""
    txt = _strip_md(a)
    m = _MECH_DECL.search(txt)
    return (m.group(1).strip().lower().rstrip(" .") if m
            else infer_mechanism_class(txt))


# ---------------------------------------------------------------------------
# D1c — quantified operational cost on every schedule/duty cycle
# ---------------------------------------------------------------------------

_DUTY = re.compile(
    r"\b(duty[ -]?cycle|periodic\w*|cyclic\w*|schedul\w+|interval\w*|"
    r"rest period|pause|on[- ]off|pulsed?|timer|setpoint (?:change|"
    r"modulation|reduction)|derate|curtail\w*)\b", re.I)
_TEST_CUT = re.compile(
    r"(?:FALSIFICATION|EXECUTABLE TEST|TEST PLAN|VERIFICATION|"
    r"VALIDATION)", re.I)
_COST_PHYSICS = re.compile(
    r"\b(kinetic energy|potential energy|energy of (?:the )?(?:"
    r"particle|impact|grain|jet)|surface energy)\b", re.I)
_QUANT = re.compile(
    r"\d+(?:\.\d+)?\s?(?:%|kWh|MW|kW|MWh|t/h|t/d|m3|scfm|kPa|bar|"
    r"g/L|kg|hours?/day|h/day|unit\w*/day)\b|\bzero\b", re.I)
_ZERO_REASON = re.compile(
    r"zero[^\n.]{0,120}(off[- ]production|non[- ]produc\w+|night|"
    r"shutdown|idle|no (?:throughput|energy|production|output)[^\n.]{0,"
    r"60})|(?:off[- ]production|non[- ]produc\w+|night window|"
    r"shutdown)[^\n.]{0,80}zero", re.I)
_COST_HEAD = re.compile(r"\b(operational cost|operational loss|"
                        r"burden)[^\n]{0,140}", re.I)
_COST_KW = re.compile(
    r"\b(throughput|energy|production (?:rate|loss)|availability|"
    r"yield|operational cost|cost|penalt\w+|trade[sd]? ?off)\b", re.I)


def scan_duty_pricing_v8(a: str) -> dict:
    """D1c. When the MECHANISM span modulates a duty cycle / schedule
    / setpoint, the bill must carry an OPERATIONAL COST line that is
    QUANTIFIED: a number with a unit/percent, or an explicit zero
    WITH the off-production reason. The V7.7 escapes — the phrase
    'OPERATIONAL COST' present without a number, or a cost keyword
    quantified somewhere unrelated — are closed: the quantity must
    sit ON the cost line (or its sentence)."""
    txt = _strip_md(a)
    mech = _section(txt, "NOVELTY STATEMENT") + "\n" + \
        "\n".join(_bill_rows(txt))
    cut = _TEST_CUT.search(mech)
    if cut:
        mech = mech[:cut.start()]
    if not _DUTY.search(mech):
        return {}
    # collect every OPERATIONAL COST / OPERATIONAL LOSS line
    lines = [ln for ln in txt.splitlines()
             if _COST_HEAD.search(ln)]
    quantified = []
    for ln in lines:
        seg = _COST_PHYSICS.sub(" ", ln)
        if _QUANT.search(seg):
            if re.search(r"\bzero\b", seg, re.I) and \
                    not _ZERO_REASON.search(seg) and \
                    not _QUANT.search(
                        re.sub(r"\bzero\b", " ", seg, flags=re.I)):
                continue  # a bare 'zero' without the reason is not
                # a quantified zero (the HO7-03 class: 'zero' asserted
                # on a producing window)
            quantified.append(ln.strip()[:100])
    if not quantified:
        # last resort: a cost keyword sentence with a quantity on it
        for ln in txt.splitlines():
            seg = _COST_PHYSICS.sub(" ", ln)
            if _COST_KW.search(seg) and _QUANT.search(seg) and \
                    not re.search(r"\bzero\b", seg, re.I):
                quantified.append(ln.strip()[:100])
                break
    if not quantified:
        return {"UNPRICED_DUTY_CYCLE": [
            "the bill modulates a duty cycle or schedule but carries "
            "no QUANTIFIED OPERATIONAL COST line — state the "
            "operational cost as a number with a unit (throughput, "
            "energy, availability lost per day or per cycle) or an "
            "explicit zero WITH the off-production reason; the "
            "unquantified phrase no longer prices a duty cycle"]}
    return {}


# ---------------------------------------------------------------------------
# D2 — structured input availability (SIGNALS USED / INPUT INVENTORY
# + the closure check; the free-prose regex hunting is RETIRED)
# ---------------------------------------------------------------------------

_SIGNALS_DECL = re.compile(
    r"SIGNALS\s+USED\s*[:\-]?\s*\n?((?:[^\n]|\n(?!\s*[A-Z]{3,})){0,600})",
    re.I)
_INVENTORY_DECL = re.compile(
    r"INPUT\s+INVENTORY\s*[:\-]?\s*\n?((?:[^\n]|\n(?!\s*[A-Z]{3,})){"
    r"0,1200})", re.I)
_INV_ROW = re.compile(
    r"[-*\d.)\s]*([A-Za-z][^\n—|]{2,60}?)\s*[—|]\s*"
    r"(?:source\s*[:\-]?\s*)?(ALREADY[- ]RECORDED|DERIVED|EXISTING|"
    r"PERMITTED|NEW)[\s(:\-]*([^\n]{0,90})", re.I)
_NONE_DECL = re.compile(r"\bnone\b[^\n]{0,60}(open[- ]loop|no online|"
                        r"no (?:sensing|signal|measurement))|"
                        r"\b(open[- ]loop|no online signal\w*|"
                        r"requires? no (?:online )?signal\w*)[^\n]{0,"
                        r"60}\bnone\b", re.I)

# the physics-quantity lexicon for the CLOSURE check (a measurable
# physical quantity named in the stated relation must be in the
# inventory with a permitted source — a concept word like 'energy
# efficiency decline' or hardware like 'a metering pump' is NOT a
# closure quantity; 'ion activity product' IS)
_PHYS_QTY = re.compile(
    r"\b((?:[a-z]+[ -]){0,2}(?:temperature\w*|pressur\w+|flow(?: rate)?"
    r"|viscosity|density|concentration\w*|pHs?\b|ion activity|"
    r"activity product|solubility product|saturation (?:ratio|index)|"
    r"supersaturation|conductivity|current(?: density)?|voltage|"
    r"alkalinity|calcium|magnesium|hardness|TDS|dissolved solids|"
    r"power|torque|speed|rpm|frequency|vibration|acoustic emission|"
    r"humidity|moisture|turbidity|opacity|particle (?:count|size)|"
    r"mass (?:flow|rate)|level|load|strain|displacement|"
    r"wall thickness|corrosion (?:rate|potential)|"
    r"coating thickness|surface roughness|hardness|"
    r"oil (?:quality|acidity|particle count)|water content|"
    r"foam (?:height|density)|bubble\w*|dew ?point|"
    r"approach temperature|delta[T]?_?\w*|differential pressure|"
    r"concentration cell|redox potential|dissolved \w+|"
    r"heat ?transfer(?: rate)?|coefficient of performance)\b)", re.I)

_PERMITTED_SOURCE = re.compile(
    r"ALREADY[- ]RECORDED|EXISTING|PERMITTED|STATED (?:DATA|SPEC|"
    r"PHYSICS)|PROBLEM", re.I)
_DERIVED_FROM = re.compile(
    r"(?:from|via)\s+([^\n.;]{5,90})", re.I)
# short-token word check (a 'pH' must not be stem-dropped — the
# HO6-12 lesson: the closure quantity list needs word-boundary
# matching against the permitted/declared TEXT, not just stems)


def _word_in(token: str, text: str) -> bool:
    return bool(re.search(r"\b" + re.escape(token.strip()) + r"\b",
                          text, re.I))


def _permitted_span_text(prob: dict) -> str | None:
    """The permitted-signals span TEXT (allowed-measures /
    permitted-measures / use-only-existing phrasing). None when no
    span parses (typed fail-open)."""
    cons = _strip_md(str(prob.get("constraint") or ""))
    m = (PERMITTED_SPAN.search(cons) or ALLOWED_SPAN.search(cons)
         or re.search(
             r"(?:use only|using only|only the existing|no new "
             r"sensors?)[^.;]{0,160}", cons, re.I))
    return m.group(0) if m else None


def _permitted_stems_of(prob: dict) -> set | None:
    """Permitted signal stems from the permitted span. None when no
    span parses (typed fail-open)."""
    t = _permitted_span_text(prob)
    if not t:
        return None
    stems = _content_stems(t)
    return stems or None


def scan_input_availability_v8(prob: dict, a: str) -> dict:
    """D2. STRUCTURED: reads the SIGNALS USED declaration (inter-
    ventions) or the INPUT INVENTORY (predictors) and the PHYSICS
    CHECK's stated relation. Fires:
      SIGNALS_USED_UNDECLARED / INPUT_INVENTORY_UNDECLARED — the
        mandatory declaration is missing (a typed defect; the V7.7
        free-prose hunt is retired — prose is no longer scanned);
      INPUT_UNAVAILABLE — a declared input whose source is not
        permitted/existing/derived-from-permitted under a parseable
        permitted span, or a CLOSURE violation: a physics quantity the
        stated relation consumes that is neither declared nor
        permitted (the HO6-12 class)."""
    qt = str(prob.get("question_type") or "").lower()
    txt = _strip_md(a)
    perm = _permitted_stems_of(prob)
    findings = {}

    if qt.startswith("predictor"):
        m = _INVENTORY_DECL.search(txt)
        if not m:
            # the V5-era bills tag inputs inside the bill rows — a
            # table/row-level ALREADY-RECORDED structure ALSO parses
            # (the HO6-12 format); missing both is the typed defect
            rows = [r for r in _bill_rows(txt)
                    if re.search(r"ALREADY[- ]RECORDED", r, re.I)]
            if not rows:
                findings["INPUT_INVENTORY_UNDECLARED"] = [
                    "the bill carries no INPUT INVENTORY section and "
                    "no ALREADY-RECORDED-tagged bill rows — every "
                    "physical quantity the scheme consumes must be "
                    "declared with its source (ALREADY-RECORDED / "
                    "DERIVED)"]
                return findings
            inv_rows = rows
            declared_txt = "\n".join(rows)
        else:
            declared_txt = m.group(1)
            inv_rows = [ln for ln in declared_txt.splitlines()
                        if _INV_ROW.search(ln)]
        # leg 1: every declared quantity permitted or derived-from-
        # permitted (only under a parseable permitted span)
        if perm:
            for ln in inv_rows:
                rm = _INV_ROW.search(ln)
                if not rm:
                    continue
                qty, tag, src = rm.group(1).strip(), \
                    rm.group(2).upper(), rm.group(3) or ""
                if "ALREADY" in tag or "EXISTING" in tag or \
                        "PERMITTED" in tag:
                    # the problem's own wording — stems must meet the
                    # permitted span OR the problem's stated-existing
                    # text (the inventory cites it; trust the tag when
                    # the cited wording is the problem's)
                    continue
                if "NEW" in tag:
                    qty_stems = _content_stems(qty)
                    if qty_stems and not (qty_stems & perm):
                        findings.setdefault("INPUT_UNAVAILABLE", [])\
                            .append(
                                f"declared input '{qty.strip()[:50]}' "
                                "is tagged NEW and is not among the "
                                "permitted signals")
                    continue
                # DERIVED: its source quantities must be permitted
                dm = _DERIVED_FROM.search(src)
                src_txt = (dm.group(1) if dm else src).strip()
                src_stems = _content_stems(src_txt)
                if src_stems and not (src_stems & perm) and \
                        not re.search(r"stated (?:physics|spec|data)",
                                      src, re.I):
                    findings.setdefault("INPUT_UNAVAILABLE", [])\
                        .append(
                            "derived input '%s' derives from '%s' "
                            "which is not among the permitted signals"
                            % (qty.strip()[:40], src_txt[:40]))
        # leg 2 — CLOSURE: quantities named in the PHYSICS CHECK's
        # stated relation must be declared (in the inventory/bill
        # tags) or permitted. Short tokens (pH) compare by
        # word-boundary against the permitted/declared TEXT — the
        # stem filter would drop them (the HO6-12 lesson)
        phys = _section(txt, "PHYSICS CHECK")
        perm_text = _permitted_span_text(prob) or ""
        if phys and perm is not None:
            declared_stems = _content_stems(
                declared_txt + "\n" + str(prob.get("constraint") or ""))
            for qm in _PHYS_QTY.finditer(phys):
                q = qm.group(1).strip()
                qs = _content_stems(q)
                toks = [t for t in re.split(r"[^A-Za-z0-9]+", q)
                        if len(t) >= 2]
                head_tok = toks[-1] if toks else ""
                if qs and (qs & perm):
                    continue
                if qs and (qs & declared_stems):
                    continue
                if head_tok and (_word_in(head_tok, perm_text)
                                 or _word_in(head_tok, declared_txt)):
                    continue
                findings.setdefault("INPUT_UNAVAILABLE", [])\
                    .append(
                        "the stated governing relation consumes "
                        "'%s' which is neither a declared input nor "
                        "among the permitted signals" % q[:50])
        return findings

    # interventions
    m = _SIGNALS_DECL.search(txt)
    if not m:
        findings["SIGNALS_USED_UNDECLARED"] = [
            "the bill carries no SIGNALS USED: line — list every "
            "online signal the mechanism requires to actuate or "
            "trigger (each with its source: existing sensor / "
            "permitted measure / derived from permitted signals) or "
            "the explicit 'none (open-loop)'"]
        return findings
    decl = m.group(1)
    if _NONE_DECL.search(decl) and not re.search(
            r"sensor|meter|probe|signat|signal is|signals:", decl,
            re.I):
        return findings
    if perm:
        for ln in decl.splitlines():
            s = ln.strip().lstrip("-*0123456789.) ")
            if not s or re.match(r"^(source|note)\b", s, re.I):
                continue
            sm = re.match(r"([A-Za-z][^\n—:]{2,60})", s)
            if not sm:
                continue
            qty = sm.group(1).strip()
            if re.search(r"\bexisting\b|\bpermitted\b|already[- ]"
                         r"recorded|derived from (?:the )?permitted",
                         s, re.I):
                continue
            qty_stems = _content_stems(qty)
            if qty_stems and not (qty_stems & perm):
                findings.setdefault("INPUT_UNAVAILABLE", [])\
                    .append(
                        f"required online signal '{qty[:50]}' is not "
                        "among the permitted measures/signals and "
                        "carries no existing/permitted source")
    return findings


# ---------------------------------------------------------------------------
# D2 — structured allowed-rows extraction (the r26 _added_spans
# free-prose hunt is RETIRED; head objects only, class-aware)
# ---------------------------------------------------------------------------

_TAG_ROW = re.compile(r"^\s*(?:[-\d.)\s]*)\(([a-dA-D])\)\s*(.+)")
# head nouns are PLURAL-TOLERANT (the HO4-04 lesson: 'refractory
# panels' / 'support brackets' must parse)
_ROW_HEAD = re.compile(
    r"^\s*(?:[-\d.)\s]+)?(?:[A-Z][\w-]*(?:\s+[A-Z][\w-]*)?\s+)?"
    r"((?:[A-Za-z][\w-]*\s+){0,4}(?:sensors?|probes?|meters?|"
    r"transducers?|valves?|pumps?|controllers?|PLCs?|timers?|"
    r"relays?|drives?|coatings?|membranes?|filters?|cartridges?|"
    r"nozzles?|injectors?|skids?|units?|panels?|shields?|"
    r"brackets?|supports?|coolers?|heaters?|exchangers?|washers?|"
    r"shims?|gaskets?|mesh(?:es)?|screens?|additives?|surfactants?|"
    r"chemicals?|reagents?|inhibitors?|modules?|systems?|devices?|"
    r"cameras?|spectrometers?|analyzers?|wipers?)\b)", re.I)
_REPLACES_OLD = re.compile(
    r"\b(?:replace[sd]?|instead of|substitut\w+ (?:for)|over "
    r"(?:the )?existing)\b", re.I)
_BURDEN_ECHO = re.compile(
    r"same as standard practice|vs\.? standard practice|additional "
    r"burden|burden class|burden ledger|zero additional|no additional "
    r"hardware|consumables? or maintenance|operational loss|"
    r"cost class", re.I)
_CONTROL_APPARATUS = re.compile(
    r"\b(timer|PLC|controller|relay|VFD|drive|contactor|logic "
    r"timer|programmable)\b", re.I)


def scan_allowed_rows_v8(prob: dict, a: str) -> dict:
    """D2. The strict row-level allowed-measures check over the
    STRUCTURED bill rows only: the added measure is the row's HEAD
    object (the noun phrase at the row start after the procurement
    tag) — never a mid-sentence fragment, never the replaced OLD item
    ('replaces standard surfactant'), never a burden/comparative
    echo. A control/scheduling apparatus row (timer/PLC/relay/VFD)
    implements the SCHEDULE class: it is exempt when the permitted
    set admits any parameter/dosing/schedule-shaped item and the bill
    shows the apparatus modulates that permitted object; the
    actuation-device laundering pin (R35 D2) still fires on powered
    actuation hardware whose family the permitted set does not name.
    Fires only when the constraint enumerates allowed measures."""
    cons = _strip_md(str(prob.get("constraint") or ""))
    perm = parse_permitted_set(cons)
    vocab, has_list = _allowed_vocab(cons)
    if not has_list or not vocab:
        return {}
    perm_stems = _permitted_stems(perm["items"])
    param_shaped = any(PARAM_SHAPE.search(it) for it in perm["items"])
    findings = {}
    rows = _bill_rows(a)
    apparat_rows = []
    for row in rows:
        if _BURDEN_ECHO.search(row):
            continue
        # (a)-tagged rows are the problem's OWN existing equipment
        # used as-is — never an added measure; (c)/untagged rows are
        # checked only when they provision a physical object (the
        # r30 _is_physical_row semantics)
        tm = _TAG_ROW.match(row)
        tag = tm.group(1).lower() if tm else None
        body = tm.group(2) if tm else row
        if tag == "a":
            continue
        if tag in ("c", None):
            from r30_allowed_class_scan import _is_physical_row
            if not _is_physical_row(body):
                continue
        # a leading 'Label:' prefix (Installation:/Operation:/
        # Maintenance: — the HO4-05 format) is structure, not the
        # object; strip it (bullet/digit lead included) before head
        # matching
        body = re.sub(r"^\s*[-*\d.)\s]*[A-Za-z]{3,18}:\s*", "", body)
        # a 'replaces X' tail is the OLD item — the added object is
        # the head only
        body = _REPLACES_OLD.split(body)[0] if _REPLACES_OLD.search(
            body) else body
        hm = _ROW_HEAD.match(body)
        if not hm:
            continue
        head = hm.group(1).strip()
        head_stems = _content_stems(head)
        if not head_stems:
            continue
        if head_stems & perm_stems:
            continue  # the class word meets the permitted set
        if _CONTROL_APPARATUS.search(head):
            # schedule-class apparatus: exempt when the permitted set
            # admits a parameter/dosing/schedule item AND the row (or
            # its bill context) modulates a permitted object — the
            # row is the IMPLEMENTATION of a permitted schedule, not
            # an added measure class of its own
            if param_shaped:
                continue
            if any(((_content_stems(r) & perm_stems))
                   for r in rows if r is not row):
                continue
            apparat_rows.append(head)
            continue
        apparat_rows.append(head)
    # emission: (1) powered actuation hardware (the R35 pin) fires;
    # (2) control/scheduling apparatus fires when not exempt; (3) a
    # PLAIN physical head fires only under a PARAM-EXHAUSTIVE
    # permitted set (the r30 class rule: the set admits no physical
    # change — HO4-04's panels/brackets, HO4-05's washer) — under a
    # mixed permitted set a non-matching physical row is NOT
    # necessarily outside (the set may admit hardware/material
    # measures; fail-open, the auditor's call)
    for head in apparat_rows:
        if re.search(r"\b(solenoid|motorized|motorised|power[- ]?"
                     r"actuated|electrically[- ]?actuated|servo[- ]?"
                     r"(?:driven|operated))\b", head, re.I):
            findings.setdefault("ACTUATION_DEVICE_AS_MEASURE", [])\
                .append(
                    "actuation device proposed as the measure while "
                    f"the bounded permitted set names no such "
                    f"hardware | {head[:80]}")
        elif _CONTROL_APPARATUS.search(head):
            findings.setdefault("ALLOWED_ROW_OUTSIDE", [])\
                .append(
                    f"added measure '{head[:60]}' shares no "
                    "allowed-list stem and the permitted set admits "
                    "no schedule/parameter class for it")
        elif perm["param_exhaustive"]:
            findings.setdefault("ALLOWED_ROW_OUTSIDE", [])\
                .append(
                    f"added measure '{head[:60]}' is a physical "
                    "object under a parameter/procedure-exhaustive "
                    "permitted set (the set admits no physical "
                    "change)")
    if findings:
        return {k: v[:3] for k, v in findings.items()}
    return {}


def _allowed_vocab(constraint: str):
    """The allowed-measures vocab (reuses the r26 semantics: the
    allowed-list segment body's stems, min_len 2)."""
    from r26_catalog_scan import allowed_vocab
    return allowed_vocab(constraint)


def _permitted_stems(items) -> set:
    out = set()
    for it in items:
        out |= _content_stems(it)
    return out


# ---------------------------------------------------------------------------
# D5 — predictor direction-of-effect framing
# ---------------------------------------------------------------------------

_DOE = re.compile(r"DIRECTION[ -]OF[ -]EFFECT\s*[:\-]?\s*([^\n]{10,"
                  r"400})", re.I)
_INTERV_ACTION = re.compile(
    r"\b(?:the )?mechanism (raises|lowers|reduces|increases|"
    r"maintains|restores|imposes|moves|shifts|modulates)\b|"
    r"\bwe (?:raise|lower|reduce|increase|maintain|impose)\b", re.I)
_DIRECTION_STATED = re.compile(
    r"\bas\b[^\n.]{0,80}\b(rises|falls|increases|decreases|drops|"
    r"grows|declines)\b[^\n.]{0,120}\b(driver|failure|fouling|"
    r"degradation|scaling|erosion|fatigue|wear|crack\w*|corrosion|"
    r"varnish|foam\w*|mist|surge|cavitation|scorch|nodulation|"
    r"blockage|blinding|fouling rate)\b", re.I)


def scan_predictor_direction_v8(a: str) -> dict:
    """D5. On predictor rows: the DIRECTION OF EFFECT line must
    exist, state the DETECTED VARIABLE + the direction the FAILURE
    DRIVER moves as it moves (the 'as X rises, the driver Y ...'
    form), and carry NO intervention action ('the mechanism raises/
    lowers/maintains ...' — the predictor observes; it does not
    act)."""
    txt = _strip_md(a)
    m = _DOE.search(txt)
    if not m:
        return {"PREDICTOR_DIRECTION_UNSTATED": [
            "the PHYSICS CHECK carries no DIRECTION OF EFFECT line — "
            "state the detected variable and the direction the "
            "failure driver moves as the detected variable moves "
            "(as X rises, the driver Y rises/falls because "
            "<governing relation>)"]}
    line = m.group(1)
    if _INTERV_ACTION.search(line):
        return {"PREDICTOR_DIRECTION_FRAMING": [
            f"the DIRECTION OF EFFECT line states an intervention "
            f"action ('{_INTERV_ACTION.search(line).group(0)[:40]} "
            "...') — a predictor OBSERVES the detected variable; "
            "restate as: as <detected variable> rises/falls, the "
            "failure driver <rises/falls> because <relation>"]}
    if not _DIRECTION_STATED.search(line):
        return {"PREDICTOR_DIRECTION_UNSTATED": [
            "the DIRECTION OF EFFECT line does not state the "
            "detected-variable -> failure-driver direction (the 'as "
            "<variable> rises, the driver <rises/falls>' form)"]}
    return {}


# ---------------------------------------------------------------------------
# the V8 contracts
# ---------------------------------------------------------------------------

V8_INT_BINDS = """

GENERATION BINDS (V8 — bind the GENERATOR, not just the checkers;
OUTRANK mechanism preference):

M. CANDIDATE-CLASS ENUMERATION BEFORE SELECTION: the bill opens with
   a CANDIDATE CLASSES section: at least THREE mechanistically
   DISTINCT candidate classes for this failure, one line each
   ("<class phrase> — <the physics reason it attacks the failure
   driver>"), then a line "SELECTED: <class phrase>" and one line of
   physics justification for the selection. At least ONE enumerated
   candidate must be NON-duty-cycle (chemistry, material state,
   geometry/arrangement, flow path, force balance, energy removal).
   If the SELECTED class is a duty cycle or setpoint schedule, the
   rejection of the non-duty-cycle candidate(s) must be stated ON
   PHYSICS (why that class cannot attack this failure driver) —
   convenience is not a physics reason.
N. MECHANISM CLASS DECLARATION (HARD): the bill opens with
   "MECHANISM CLASS: <one phrase>" in plain text (no markdown
   emphasis). The declaration is mandatory; the machine additionally
   infers the class of an undeclared bill and counts it toward the
   set cap — an omitted declaration no longer escapes the diversity
   histogram (at most 2 rows per class per 6-intervention set).
O. OPERATIONAL COST (QUANTIFIED): every schedule, duty-cycle, or
   setpoint modulation the bill makes carries an "OPERATIONAL COST:"
   line with a QUANTIFIED magnitude — a number with its unit or
   percent (throughput, energy, availability lost per day or per
   cycle), or an explicit "zero" WITH the off-production reason
   (night window, non-producing interval). The phrase without a
   number is an unpriced duty cycle.
P. SIGNALS USED DECLARATION: the bill carries a "SIGNALS USED:" line
   listing EVERY online signal the mechanism requires to actuate or
   trigger, each with its source — existing sensor / permitted
   measure / derived from <permitted signals> — or the explicit
   "none (open-loop)" when the mechanism needs no online signal.
   The input-availability check reads this declaration, never free
   prose; an undeclared signal the plant does not permit is an
   unavailable input.
"""

V8_PREDICTOR_BINDS = """

GENERATION BINDS (V8, predictors — bind the GENERATOR, not just the
checkers):

Q. INPUT INVENTORY: the bill carries an "INPUT INVENTORY:" section:
   every physical quantity the scheme's math consumes — including
   every quantity inside a derived index — one line each, "<quantity>
   — source: ALREADY-RECORDED(<the problem's own wording>)" or
   "<quantity> — source: DERIVED(<from which permitted signals /
   stated physics>)". A quantity the stated governing relation
   consumes that is neither declared nor among the permitted signals
   is an unavailable input (an index that secretly needs water
   chemistry under temperature/flow-only meters fails here).
R. DIRECTION OF EFFECT (DETECTION-FRAMED): the PHYSICS CHECK carries
   a "DIRECTION OF EFFECT:" line stating the DETECTED VARIABLE, the
   direction the FAILURE DRIVER moves as the detected variable moves
   ("as <detected variable> rises, the <failure driver> rises/falls
   because <governing relation>"), and the lead/precedence claim. The
   line describes DETECTION physics — it must NOT state an
   intervention action ("the mechanism raises/lowers/maintains X"):
   a predictor OBSERVES the variable; it does not act on it.
"""

SYS_A1_INT_V8 = SYS_A1_INT_V72 + V8_INT_BINDS
SYS_A1F_V8 = SYS_A1F_V5 + V8_PREDICTOR_BINDS

V8_REPAIR_DIRECTIVE = V77_REPAIR_DIRECTIVE + """

V8 BIND REPAIRS: for CANDIDATE_CLASSES_MISSING / _UNDERSET /
NONDUTY_CANDIDATE_ABSENT / DUTY_CYCLE_PREFERENCE_UNPROVEN: add or
widen the CANDIDATE CLASSES section (>= 3 distinct classes, >= 1
non-duty-cycle, SELECTED with the physics justification; a duty-cycle
selection needs the physics rejection of the non-duty-cycle
candidate). For MECHANISM_CLASS_UNSTATED / MECHANISM_TEMPLATE_
MONOCULTURE: declare the MECHANISM CLASS in plain text; if the class
is capped in this set, deliver a different mechanism class (the cap
counts inferred classes). For UNPRICED_DUTY_CYCLE: add the QUANTIFIED
OPERATIONAL COST line (a number with unit, or an explicit zero with
the off-production reason). For SIGNALS_USED_UNDECLARED /
INPUT_INVENTORY_UNDECLARED / INPUT_UNAVAILABLE: declare every online
signal / input quantity with its permitted source, or re-choose the
mechanism to live on the permitted signals — never invent the
instrumentation. For PREDICTOR_DIRECTION_UNSTATED / _FRAMING: state
the detection-framed direction of effect (as the detected variable
moves, the failure driver moves ...); remove intervention actions
from the line.
"""


def contract_for_v8(question_type):
    """V8 arm map: interventions carry the generation binds on top of
    the V7.2 conversion bind; predictors carry the V5 contract + the
    input-inventory and direction-of-effect binds."""
    qt = (question_type or "").lower()
    return SYS_A1_INT_V8 if qt.startswith("intervention") \
        else SYS_A1F_V8


__all__ = [
    "SYS_A1_INT_V8", "SYS_A1F_V8", "V8_INT_BINDS",
    "V8_PREDICTOR_BINDS", "V8_REPAIR_DIRECTIVE", "contract_for_v8",
    "scan_candidate_classes_v8", "scan_mechanism_class_v8",
    "scan_duty_pricing_v8", "scan_input_availability_v8",
    "scan_allowed_rows_v8", "scan_predictor_direction_v8",
    "infer_mechanism_class", "counted_class", "_section",
    "_strip_md", "_bill_rows",
]
