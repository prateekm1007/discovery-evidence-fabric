#!/usr/bin/env python3
"""permitted_measures/1.0.0 — the per-problem permitted-measure-set
enforcement (R103, claim c-0117; AM89 directive 1, the HO14-12 defect
class).

THE DEFECT (typed in the R102 verdict, eval/holdout_v14_auditor_score
@ bbc89b7c2, AM89/V89): the generator delivered a bill whose measures
were OUTSIDE the problem's exhaustive permitted set — HO14-12 proposed
recirculation-flow/VFD scour (permitted set: pH/caustic dosing,
air-to-water ratio, water-temperature retuning ONLY). Both existing
deterministic scans missed it: r26's ALLOWED_ROW_OUTSIDE extracts
added-measure spans only from (b)-tagged/install-verb rows (a class-(c)
parameter row on a forbidden variable is never extracted), and
r30_allowed_class_scan's ALLOWED_MEASURE_TYPE_OUTSIDE fires only on
PHYSICAL rows (a parameter-shaped forbidden measure is invisible). The
auditor's full-read caught it (auditor Art. 2).

THE ENFORCEMENT (this module; the canonical taxonomy is the committed
engine JSON data/measure_class_taxonomy.json):

  parse_permitted_set(user_variables) -> the exhaustive "allowed
    measures: A, B, or C only" enumeration, each item mapped to its
    CANONICAL measure classes (chemistry_dosing, temperature,
    air_water_ratio, flow_rate, procedure_schedule, ...). A set is
    exhaustive only when it carries the "only" marker.

  enforce_answer(problem, answer) -> typed findings:
    MEASURE_NOT_IN_PERMITTED_SET  — the typed KILL (AM89 directive 1:
      "any measure outside the problem's allowed list = typed KILL").
      Fires under the two kill_rule conditions of the taxonomy: the
      whole-mechanism read (zero in-set substantive rows + an
      out-of-set mechanism class) or the out-of-set-rows read (an
      out-of-set mechanism class confirmed by >=1 out-of-set
      substantive row). Substantive = a real measure family; VEHICLE
      rows (control configuration over existing equipment, monitoring,
      documentation, burden annotations) ride the measure they
      implement and never kill — the precision that keeps the 14
      conformant v14 intervention rows silent (the anaphora cases:
      HO14-14's "High-flow setpoint value" rows ride their in-set
      recirculation class).
    MEASURE_CLASS_UNRESOLVED — a substantive row that classifies to no
      canonical class under an exhaustive set (a repair flag: restate
      the measure in the permitted vocabulary; never a kill).

  The PARAMETER_TUNING modifier (setpoint/retuning/adjust) never
  rescues an out-of-set substantive object: retuning a forbidden
  variable is still a forbidden measure (the HO14-12 Row-1 class —
  "Adjustment of Recirculation Pump Speed/VFD Setpoint" shares the
  word "setpoint" with the permitted items and is still outside).

Zero LLM, deterministic. The r30_allowed_class_scan wires this into
the machine's violation surface (the auditor-named seam); the logic
lives here in the engine (the F63 engine-line discipline). The
authoritative constraint-fit read stays the auditor's.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

RECORD = "PERMITTED_MEASURES/1.0.0"

_DATA_PATH = (Path(__file__).resolve().parent / "data" /
              "measure_class_taxonomy.json")
_TAXONOMY_CACHE: Optional[Dict[str, Any]] = None


def _taxonomy() -> Dict[str, Any]:
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is None:
        if not _DATA_PATH.exists():
            raise RuntimeError(
                f"measure-class taxonomy missing: {_DATA_PATH} (typed "
                "abort — the enforcement surface never runs without "
                "its taxonomy)")
        _TAXONOMY_CACHE = json.loads(
            _DATA_PATH.read_text(encoding="utf-8"))
    return _TAXONOMY_CACHE


# --- the permitted-set parse ------------------------------------------

ALLOWED_SPAN = re.compile(
    r"allowed measures?\s*[:\-]?\s*(.+?)(?:\.|;|$)", re.I)
PERMITTED_SPAN = re.compile(
    r"(?:permitted|allowed)\s+(?:measures?|changes?|actions?|"
    r"interventions?)\s*[:\-]?\s*(.+?)(?:\.|;|$)", re.I)
ONLY_MARKER = re.compile(r"\bonly\b", re.I)


def _constraint_text(value: Any) -> str:
    """The constraint text: a LIST constraint (the v7 convention:
    ['no ...; allowed measures: ... only', 'device of record: ...'])
    joins with '; ' — str() of a list would leak the Python repr
    and pollute the span parse (the R103 calibration catch)."""
    if isinstance(value, (list, tuple)):
        return " ; ".join(str(v) for v in value if v)
    return str(value or "")


def parse_permitted_set(constraint: Any) -> Dict[str, Any]:
    """The exhaustive permitted-measure enumeration with each item's
    canonical classes. Returns {"span", "only", "items", "classes",
    "substantive_classes", "has_set"}. has_set is True only when the
    span exists AND carries the 'only' marker (the exhaustive form the
    AM89 rule enforces; a non-exhaustive 'allowed' hint is advisory
    and this enforcement stays silent). Accepts str or list
    constraints."""
    txt = _constraint_text(constraint)
    m = ALLOWED_SPAN.search(txt) or PERMITTED_SPAN.search(txt)
    if not m:
        return {"span": None, "only": False, "items": [],
                "classes": set(), "substantive_classes": set(),
                "has_set": False}
    span = m.group(1)
    only = bool(ONLY_MARKER.search(span))
    items = [it.strip() for it in
             re.split(r",\s*(?:or\s+)?|\bor\b", span)
             if it.strip() and it.strip().lower() != "only"]
    tax = _taxonomy()
    classes: Set[str] = set()
    for it in items:
        classes |= classify_text_classes(it, tax)
    substantive = {c for c in classes
                   if c in tax["substantive_classes"]}
    return {"span": span, "only": only, "items": items,
            "classes": classes, "substantive_classes": substantive,
            "has_set": only and bool(items)}


# --- the canonical class extraction ------------------------------------

def _norm(text: str) -> str:
    """Hyphen/slash-insensitive normalization: 'air-to-water' and
    'air/water' and 'air to water' all match; markers keep their
    word boundaries at match time on the normalized text."""
    t = str(text or "").lower()
    t = re.sub(r"[\u2013\u2014]", "-", t)
    t = re.sub(r"([a-z])[-/]([a-z])", r"\1 \2", t)
    return t


def _marker_patterns(markers: List[str]) -> List[re.Pattern]:
    out = []
    for mk in markers:
        pat = r"(?<![a-z0-9])" + re.escape(_norm(mk)) \
            + r"(?![a-z0-9])"
        out.append(re.compile(pat))
    return out


_CLASS_PATTERNS: Optional[Dict[str, List[tuple]]] = None


def _class_patterns() -> Dict[str, List[tuple]]:
    """{kind: [(class_name, [compiled_patterns])]} sorted so
    multi-word markers match before their singles are consulted at
    classification time (patterns are independent per class; ordering
    only affects nothing here — matching is a union)."""
    global _CLASS_PATTERNS
    if _CLASS_PATTERNS is None:
        tax = _taxonomy()
        _CLASS_PATTERNS = {}
        for kind in ("substantive_classes", "vehicle_classes",
                     "modifier_classes"):
            entries = []
            for cls, spec in tax[kind].items():
                entries.append((cls, _marker_patterns(spec["markers"])))
            _CLASS_PATTERNS[kind] = entries
    return _CLASS_PATTERNS


def classify_text_classes(text: str,
                          tax: Optional[Dict[str, Any]] = None
                          ) -> Set[str]:
    """All canonical classes whose markers hit the text (any kind)."""
    tax = tax or _taxonomy()
    low = _norm(text)
    out: Set[str] = set()
    for kind in ("substantive_classes", "vehicle_classes",
                 "modifier_classes"):
        for cls, pats in _class_patterns()[kind]:
            for p in pats:
                if p.search(low):
                    out.add(cls)
                    break
    return out


def split_row_classes(classes: Set[str]) -> Dict[str, Set[str]]:
    """Split a class set by taxonomy kind."""
    tax = _taxonomy()
    return {
        "substantive": {c for c in classes
                        if c in tax["substantive_classes"]},
        "vehicle": {c for c in classes
                    if c in tax["vehicle_classes"]},
        "modifier": {c for c in classes
                     if c in tax["modifier_classes"]},
    }


# --- the answer's bill rows (the measure-row collector) ----------------

BILL_SECTION = re.compile(
    r"IMPLEMENTATION BILL(.*?)(?=\n[A-Z][A-Z ]{4,}\n|\Z)", re.S | re.I)
ROW_LINE = re.compile(
    r"^\s*(?:[-*\u2022]|\d+[.)]\s|\*\s+|Row\s+\d+\s*[:.]"
    r"|\([a-dA-D]\)\s)", re.I)
TABLE_ROW = re.compile(r"^\s*\|")
# any all-caps section heading (the frozen scanner's narrow stop-set
# misses markdown-bolded '*EXECUTABLE TEST**' and parenthesized
# '*BURDEN LEDGER (STANDARD-PRACTICE PARITY)**' — those sections'
# rows are NOT bill measures; this collector stops at ANY heading)
HEADING_LINE = re.compile(
    r"^\s*[#*\u2022\s]*[A-Z][A-Z0-9 ()&/\-,']{4,}[#*\s]*$")
TABLE_SEPARATOR = re.compile(r"^\s*\|([\s:|-]+\|)+\s*$")
_TABLE_HEADER_VOCAB = {
    "item", "description", "procurement tag", "justification", "class",
    "tag", "#", "no.", "no", "nr", "row", "measure", "action", "name",
    "source", "basis"}
MARKDOWN_ARTIFACT = re.compile(r"^[#*\u2022\s]+$")
BARE_HEADER = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])?\s*\**"
                         r"[^*\n]{1,60}:\s*\**\s*$")
ROW_NUM_LABEL = re.compile(r"^\s*Row\s+\d+\s*[:.]\s*", re.I)
BULLET_PREFIX = re.compile(
    r"^\s*(?:[-*\u2022]|\d+[.)]\s+|\*\s+)\s*")
LEADING_LABEL = re.compile(
    r"^\**\s*([A-Za-z][A-Za-z0-9 ()&/\-]{1,32}?)\s*\**\s*:")
CELL_SPLIT = re.compile(r"\|")


def collect_measure_rows(answer: str) -> List[str]:
    """The bill's MEASURE rows: bullet/numbered/Row-N/table lines in
    the IMPLEMENTATION BILL section, stopping at ANY section heading
    (the frozen scanner's narrow all-caps stop-set lets
    markdown-bolded headings leak their rows into scope; this
        collector is the precise scope). Sub-label continuation lines
    (Class:/Description:/Source:/...), burden/compliance-annotation
    labels, bare headers, markdown artifacts and table
    header/separator rows are skipped. Each returned row is the line
    text (head+body) for classification."""
    a = str(answer or "")
    m = BILL_SECTION.search(a)
    if not m:
        return []
    rows: List[str] = []
    for ln in m.group(1).splitlines():
        s = ln.strip()
        if not s:
            continue
        if MARKDOWN_ARTIFACT.match(s):
            continue
        if HEADING_LINE.match(s):
            break  # any section heading ends the bill's row scope
        if TABLE_SEPARATOR.match(s):
            continue
        is_row = bool(ROW_LINE.match(s)) or bool(TABLE_ROW.match(s))
        if not is_row:
            continue
        body = ROW_NUM_LABEL.sub("", s)
        body = BULLET_PREFIX.sub("", body)
        if BARE_HEADER.match(s):
            continue  # a label with no content is a header, not a row
        # the markdown table HEADER row (Item | Description | ...):
        # every cell short and a majority in the header vocabulary
        if TABLE_ROW.match(s):
            cells = [c.strip(" *") for c in s.strip("|").split("|")]
            nonempty = [c for c in cells if c]
            if nonempty and all(len(c) <= 22 for c in nonempty) and \
                    sum(1 for c in nonempty
                        if _norm(c) in _TABLE_HEADER_VOCAB) >= \
                    (len(nonempty) + 1) // 2:
                continue
        # continuation sub-rows + annotation labels: a leading label
        # from the substructure vocabulary is not a measure row
        lm = LEADING_LABEL.match(body)
        if lm and _label_in(lm.group(1)):
            continue
        rows.append(body)
    return rows


_CONTINUATION_WORDS: Optional[Set[str]] = None


def _label_in(label: str) -> bool:
    """The leading label names bill SUBSTRUCTURE (Class:/Source:/...)
    or an annotation/compliance echo (burden, pricing, parity, the
    machine's own finding-code echoes) — not a measure row."""
    global _CONTINUATION_WORDS
    if _CONTINUATION_WORDS is None:
        _CONTINUATION_WORDS = {
            # bill substructure
            "class", "description", "source", "basis", "tag",
            "justification", "note", "why", "procurement tag",
            "standard practice comparison", "duration", "instruments",
            # burden / pricing / parity annotations
            "burden", "cost", "cost pricing", "cost class",
            "cost impact", "rough cost class", "energy", "energy cost",
            "chemical cost", "throughput", "throughput loss",
            "conclusion", "parity conclusion", "operational loss",
            "operational loss pricing", "hardware", "hardware burden",
            "hardware cost", "installation", "installation burden",
            "installation commissioning", "commissioning",
            "commissioning burden", "procurement burden",
            "installation commissioning burden", "net burden",
            "net trade off", "net tradeoff", "operability",
            "installability", "maintainability", "maintenance",
            "parity", "labour", "labor", "standard practice",
            "standard practice burden", "mitigation",
            "alternative interpretation", "premise validity",
            "premise", "direction of effect", "trade off", "tradeoff",
            # compliance / disclosure echoes
            "permitted set", "permitted set adherence",
            "permitted set clause", "deployed part",
            "deployed part clause", "catalog composition",
            "apparatus row", "unpriced duty cycle", "mechanism class",
            "mechanism class unstated", "dev need",
            # test-protocol substructure
            "protocol", "measurement", "baseline", "verification",
            "pass fail", "pass/fail", "kill criterion",
            "falsification", "success criterion",
            # ('item'/'detail'/'input' are NOT skipped: they are
            # MEASURE-row labels in the industrial bill format
            # "- Item: X. (c)" — the content classifies them; the
            # predictor forms carry no allowed-measures span and this
            # enforcement stays silent there anyway)
            "derivation", "tagging"}
    lab = _norm(label).strip().rstrip(':').strip()
    return lab in _CONTINUATION_WORDS


MECHANISM_CLASS_LINE = re.compile(
    r"MECHANISM CLASS\s*[:\-]\s*\**\s*([^\n*]{3,90})", re.I)


def declared_mechanism_class(answer: str) -> Optional[str]:
    m = MECHANISM_CLASS_LINE.search(str(answer or ""))
    return m.group(1).strip() if m else None


# --- the enforcement ----------------------------------------------------

def enforce_answer(problem: Dict[str, Any], answer: str) -> Dict[
        str, List[str]]:
    """The per-problem permitted-measure-set enforcement. Returns
    typed findings ({} = clean/silent). Fires only on an EXHAUSTIVE
    permitted set ("only"); the auditor's full-read stays
    authoritative on every other form."""
    perm = parse_permitted_set(
        _constraint_text(problem.get("user_variables"))
        + " ; " + _constraint_text(problem.get("constraint")))
    if not perm["has_set"]:
        return {}
    a = str(answer or "")
    permitted_sub = perm["substantive_classes"]

    rows = collect_measure_rows(a)
    row_reads = []
    in_set_rows = 0
    out_rows: List[str] = []
    unresolved_rows: List[str] = []
    for row in rows:
        # an EXPLICIT (a) procurement tag is the model's own
        # rides-existing declaration (the r22 contract's class (a)) —
        # the row is an infrastructure echo, not a new measure; it
        # never needs resolution and never kills. Explicit (b)/(c)
        # tags do NOT override the substantive classification (the
        # HO14-12 rows were honestly tagged (c) and are still
        # out-of-set measures).
        if re.search(r"\(\s*a\s*\)|\[\s*a\s*\]", row):
            kinds = {"substantive": set(), "vehicle": {"tag_a"},
                     "modifier": set()}
        else:
            kinds = split_row_classes(classify_text_classes(row))
        if kinds["substantive"]:
            if kinds["substantive"] & permitted_sub:
                in_set_rows += 1
            else:
                out_rows.append(row)
        elif not kinds["vehicle"] and not kinds["modifier"] \
                and not kinds["substantive"]:
            # no class at all: an unclassifiable measure row
            unresolved_rows.append(row)
    # the mechanism-class read
    cls = declared_mechanism_class(a)
    cls_out = False
    if cls:
        cls_kinds = split_row_classes(classify_text_classes(cls))
        # the class rides an in-set family when it shares any
        # substantive class with the permitted set
        cls_out = bool(cls_kinds["substantive"]) and not (
            cls_kinds["substantive"] & permitted_sub)

    findings: Dict[str, List[str]] = {}
    kills: List[str] = []
    if cls_out and out_rows:
        for r in out_rows[:4]:
            kills.append(
                f"measure outside the permitted set (the mechanism "
                f"class '{cls[:44]}' is out-of-set and the row's "
                f"measure class shares nothing with the permitted "
                f"items {perm['items'][:3]}) | {r[:96]}")
    elif not in_set_rows and out_rows and (cls_out or cls is None):
        # no in-set substantive row at all: the whole bill is
        # out-of-set (or unclassifiable-headed)
        for r in out_rows[:4]:
            kills.append(
                f"measure outside the permitted set (no bill row "
                f"shares a measure class with the permitted items "
                f"{perm['items'][:3]}) | {r[:96]}")
    if kills:
        findings["MEASURE_NOT_IN_PERMITTED_SET"] = kills
    if unresolved_rows:
        findings["MEASURE_CLASS_UNRESOLVED"] = [
            "a bill measure row matches no canonical measure class "
            f"under the exhaustive permitted set — restate the measure "
            f"in the permitted vocabulary | {r[:96]}"
            for r in unresolved_rows[:3]]
    return findings
