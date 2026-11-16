#!/usr/bin/env python3
"""r30_allowed_class_scan.py — the CONSTRAINT-CLASS bind (AM29 D1,
F36 recurring-closure). Deterministic, no LLM.

AM29 basis: the V7 family's constraint-bind learned the DEV
allowed-measures LISTS, not the CLASS "the measure must be drawn from
the permitted set" — on fresh problems it installed hardware where
only retuning/procedure was permitted (HO4-04 thermal shield+support+
exhaust cooling under "burner/profile retuning or batch/cullet
adjustment ONLY"; HO4-05 washer hardware under "retensioning
procedure or pitch-parameter retuning ONLY").

PRECISION-FIRST CLASS RULE (the class, not a memorized list — no dev
nouns are baked in): fire COMPONENT-measure rows OUT OF CLASS only
when the problem's constraint text states an EXHAUSTIVE permitted set
(the "only" marker) whose every listed item is parameter/procedure-
shaped (adjust/retune/schedule/protocol/profile/ratio/setpoint/limits/
selection/dose/control phrasing). In that state the permitted set
admits NO physical change: any bill row that installs, fits, or
provisions a device or bulk material is outside the class.
  - HO4-04 span: profile + retuning + adjustment, "only" -> fires on
    the shield/support/exhaust-cooler COMPONENT rows.
  - HO4-05 span: retensioning interval/procedure + parameter
    retuning, "only" -> fires on the washer COMPONENT row.
  - HO4-01 span: "flue-gas conditioning (SO3 or ammonia dosing),
    waveform/pulse control, or rapping-interval retuning only" — the
    conditioning/dosing item is NOT parameter-shaped (it admits a
    dosing system), so the set is not param-exhaustive and the scan
    stays silent on the conformant probe/PLC bill.
  - HO4-02 span: "cover-soil placement procedure ..., or
    drainage-layer gradation change only" — placement/change are
    material-class actions, not parameter-shaped -> silent (the
    gradation measure is permitted; its inversion is the DIRECTION
    bind's finding, not this scan's).

LIMIT-form permitted measures ("thermal-cycling ramp-rate limits")
permit only DECREASING the named variable: the scan fires
LIMIT_DIRECTION_VIOLATION when the mechanism AUGMENTS the limited
variable near its mention with no decrease-class verb in the same
window (the HO4-03 class: cycling-to-heal under "thermal-cycling
ramp-rate limits only").

If the constraint carries no parseable span (or is not param-
exhaustive), the scan is typed NOT-APPLICABLE (fail-open, disclosed)
— the strict allowed-row stem scan (r24_constraint_scan) still runs,
and the authoritative class read stays the auditor's.
"""
from __future__ import annotations

import re

from r26_catalog_scan import _bill_rows

ALLOWED_SPAN = re.compile(
    r"allowed measures?\s*[:\-]?\s*(.+?)(?:\.|;|$)", re.I)
PERMITTED_SPAN = re.compile(
    r"(?:permitted|allowed)\s+(?:measures?|changes?|actions?|"
    r"interventions?)\s*[:\-]?\s*(.+?)(?:\.|;|$)", re.I)
ONLY_MARKER = re.compile(r"\bonly\b", re.I)

# an item is PARAMETER-shaped when its action/noun is a setting,
# schedule, procedure, or selection — not a physical change
PARAM_SHAPE = re.compile(
    r"\b(retun\w*|tun\w*|adjust\w*|recalibrat\w*|reprogram\w*|"
    r"retension\w*|re-tension\w*|retorque\w*|optimi[sz]\w*|"
    r"procedure|protocol|schedul\w*|interval|parameter|setpoint|"
    r"set-point|profile|ratio|window|cutoff|cut-off|limits?|cap|"
    r"selection|dose|dosage|waveform|pulse control|control|"
    r"inspection|monitoring|sampling|recipe|sequence|regime|"
    r"strategy|timing|frequency|duty|placement procedure)\b", re.I)
# an item that names a physical action or a dosing/conditioning
# SYSTEM is NOT parameter-shaped (it admits hardware/material)
PHYS_SHAPE = re.compile(
    r"\b(dosing|conditioning|install\w*|instal\b|fitting|"
    r"mount\w*|retrofit\w*|replac\w*|place\w*|placement of|add\w*|"
    r"new\b|procur\w*|weld\w*|swap|substitut\w*|shield|panel|skid|"
    r"system|unit|device|component|cartridge|valve|sensor|probe|"
    r"actuator|pump|filter|membrane|liner|exchanger|cooler|heater|"
    r"coating|film|washer|shim|bracket|support|mesh|screen|aggregate|"
    r"gravel|sand|soil|bedding|ballast|grout)\b", re.I)

ROW_INSTALL = re.compile(
    r"\b(install|instal\w*|fit|fitting|mount\w*|retrofit\w*|weld\w*|"
    r"bolt\w*|fasten\w*|provisions?\b|procure\w*)\b", re.I)
ROW_PLACE = re.compile(
    r"\b(plac\w*|spread\w*|compact\w*|fill\w*|pour\w*|lay\w*|"
    r"backfill\w*)\b", re.I)
DEVICE_NOUN = re.compile(
    r"\b(shield|panel|support|bracket|valve|pump|sensor|probe|"
    r"actuator|damper|filter|cartridge|exchanger|heater|cooler|"
    r"chiller|fan|blower|washer|shim|gasket|mesh|screen|grate|"
    r"vessel|tank|pipe|piping|hose|fitting|gauge|controller|PLC|"
    r"transducer|reservoir|bellow\w*|catheter|skid|unit|enclosure|"
    r"heat exchanger)\b", re.I)
BULK_NOUN = re.compile(
    r"\b(aggregate|gravel|sand|soil|bedding|ballast|batch material|"
    r"cullet|grout|mortar|backfill|granular|crushed stone)\b", re.I)
BILL_ROW = re.compile(
    r"^\s*(?:\d+\.?\s*)?-\s*(?:\(([a-dA-D])\)\s*)?.*"
    r"(\([a-dA-D]\))?", re.X)

AUGMENT_VERB = re.compile(
    r"\b(alternat\w*|increas\w*|rais\w*|add\w*|more frequent|dwell\w*|"
    r"extend\w*|amplif\w*|cycl\w*)\b", re.I)
DECREASE_VERB = re.compile(
    r"\b(limit\w*|reduc\w*|lower\w*|restrict\w*|cap\w*|bound\w*|"
    r"decreas\w*|cut\b|narrow\w*|slow\w*)\b", re.I)
LIMIT_FORM = re.compile(
    r"\b((?:[\w\-]+/)?[\w\-]+(?:[\w\-/ ]{0,30})?)\s+limits?\b", re.I)


def parse_permitted_set(constraint: str) -> dict:
    """Parse the permitted-measure span and type its exhaustiveness.
    Returns {"span", "only", "param_exhaustive", "items", "limits"}.
    param_exhaustive is True iff the span carries the "only" marker
    and EVERY top-level item is parameter/procedure-shaped."""
    txt = str(constraint or "")
    m = ALLOWED_SPAN.search(txt) or PERMITTED_SPAN.search(txt)
    if not m:
        return {"span": None, "only": False, "param_exhaustive": False,
                "items": [], "limits": []}
    span = m.group(1)
    only = bool(ONLY_MARKER.search(span))
    items = [it.strip() for it in re.split(r",\s*(?:or\s+)?|\bor\b",
                                           span) if it.strip()]
    param_exhaustive = only and bool(items) and all(
        PARAM_SHAPE.search(it) and not PHYS_SHAPE.search(it)
        for it in items)
    limits = [lm.group(1).strip().lower()
              for lm in LIMIT_FORM.finditer(span)]
    return {"span": span, "only": only, "param_exhaustive":
            param_exhaustive, "items": items, "limits": limits}


def _is_physical_row(row: str) -> bool:
    """True when the bill row provisions a device or bulk material."""
    if ROW_INSTALL.search(row):
        # install-language over bulk material is still a physical
        # placement, but a burden-ledger echo ("same as standard
        # practice") is not a measure row
        if re.search(r"same as standard practice", row, re.I):
            return False
        return True
    if DEVICE_NOUN.search(row) and re.search(r"\(([bBdD])\)", row):
        return True
    if BULK_NOUN.search(row) and (ROW_PLACE.search(row) or
                                  re.search(r"\(([bB])\)", row)):
        return True
    if ROW_PLACE.search(row) and BULK_NOUN.search(row):
        return True
    return False


BILL_SECTION_START = re.compile(
    r"IMPLEMENTATION BILL", re.I)
HEADING_LINE = re.compile(
    r"^\s*[A-Z]{3,}[A-Z0-9 (\-/&,_]{2,}")
BURDEN_ECHO = re.compile(
    r"same as standard practice|additional burden|burden class|"
    r"burden ledger|zero additional", re.I)
LOCATION_SPLIT = re.compile(
    r"\b(?:on|upon|above|below|beside|near|at|in|with|for|along)\b",
    re.I)
_SUFFIXES = ("ing", "ed", "er", "es", "s", "e")


def _stem(w: str) -> str:
    w = w.lower()
    for suf in _SUFFIXES:
        if len(w) > 3 and w.endswith(suf):
            w = w[:-len(suf)]
            break
    return w[:6]


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z]{4,}", text)}


def _object_stems(row: str) -> set:
    """Stems of the row's PROCURED OBJECT: the first six content words
    after the procurement tag/label — the device or material being
    added, not the location or the tooling tail ('mounted on the
    crown', 'torque re-verified with an existing wrench' must not
    inherit the permitted set's stems)."""
    m = re.search(r"\(([b-dB-D])\)\s*(.*)", row)
    body = m.group(2) if m else re.sub(
        r"^-\s*[A-Za-z]+:\s*", "", row)
    words = [w for w in _content_words(body)][:6]
    return {_stem(w) for w in words}


def _permitted_stems(items) -> set:
    out = set()
    for it in items:
        out |= {_stem(w) for w in _content_words(it)}
    return out


def _bill_rows_scoped(answer: str) -> list:
    """Rows of the IMPLEMENTATION BILL section only (the r26 section
    regex can swallow the burden/test sections when their headings
    carry parenthesized qualifiers)."""
    a = str(answer or "")
    m = BILL_SECTION_START.search(a)
    if not m:
        return []
    body = a[m.end():]
    rows = []
    for ln in body.splitlines():
        if HEADING_LINE.match(ln):
            break
        ln = ln.strip()
        # a measure row is tagged, bullet-, or digit-led; parenthetical
        # intros and prose lines are not bill rows
        if ln and (re.match(r"^-\s", ln) or re.match(r"^\d", ln) or
                   re.match(r"^\([a-dA-D]\)", ln)):
            rows.append(ln)
    return rows


def scan_allowed_measures_class(problem: dict, answer: str) -> dict:
    """The CONSTRAINT-CLASS bind (precision-first)."""
    perm = parse_permitted_set(problem.get("constraint") or "")
    out: dict = {}
    if not perm["param_exhaustive"]:
        return out  # typed not-applicable; stem scan still runs
    perm_stems = _permitted_stems(perm["items"])
    hits = []
    for row in _bill_rows_scoped(answer):
        if not row:
            continue
        if BURDEN_ECHO.search(row):
            continue  # a burden-ledger echo is not a measure row
        if _is_physical_row(row):
            # actuation-equipment escape: the row's OBJECT implements a
            # permitted measure when their stems meet (dose selection
            # admits the dosing pump); a location mention does not
            obj = _object_stems(row)
            if obj & perm_stems:
                continue
            hits.append("physical measure outside the param-exhaustive "
                        f"permitted set | {row[:80]}")
            if len(hits) >= 4:
                break
    if hits:
        out["ALLOWED_MEASURE_TYPE_OUTSIDE"] = hits
    # LIMIT-form permitted measures are decrease-only near the variable
    lim_hits = []
    mech = re.search(r"NOVELTY STATEMENT.{0,900}", answer, re.S)
    mech_txt = mech.group(0) if mech else answer[:900]
    for var in perm["limits"]:
        var = re.sub(r"^(?:or|and)\s+", "", var)
        head_m = re.search(r"[a-z]{4,}", var)
        if not head_m:
            continue
        head = head_m.group(0)
        for wm in re.finditer(re.escape(head), mech_txt, re.I):
            win = mech_txt[max(0, wm.start() - 70):wm.end() + 70]
            if AUGMENT_VERB.search(win) and \
                    not DECREASE_VERB.search(win):
                lim_hits.append(
                    f"permitted LIMIT on '{var[:44]}' but the mechanism "
                    f"augments it near the variable | {win[:80]}")
                break
        if lim_hits:
            break
    if lim_hits:
        out["LIMIT_DIRECTION_VIOLATION"] = lim_hits
    return out
