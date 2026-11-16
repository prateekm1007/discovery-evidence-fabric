#!/usr/bin/env python3
"""r26_catalog_scan.py — the CATALOG scan (v2), deterministic, no LLM.

Byte-typed basis (Art. VI — each finding class names its measured
bytes):

  ALLOWED_ROW_OUTSIDE — the v1 constraint scan (r24_constraint_scan)
    checks whether the ANSWER TEXT mentions any allowed stem. HO3-05
    (holdout v3, auditor-scored violation) passed it: the draft
    "Install chelating resin cartridge IN PARALLEL WITH existing
    activated-alumina cartridge" mentions the allowed anchor while the
    ADDED measure (chelating resin) is outside the allowed list
    (eval/holdout_v3_generation/HO3-05 attempts ledger: v1 fired only
    BILL_UNTAGGED). The strict row-level check extracts the ADDED
    measure span from (i) add/install/replace-with/in-parallel rows
    and (ii) class-(b) bill rows (NEW procurement — HO2-03 zinc anode
    collar, HO2-04 humidity sensor/controller/valve are (b) rows) and
    fires when that span shares NO allowed-list stem after
    FORM-FACTOR nouns (cartridge, module, valve, ...) are stripped
    from both sides. This is the AM25 D2 strict enforcement: "the
    constraint-bind must reject any measure outside the stated list".

  APPARATUS_ROW — the AM25 "no audit apparatus that itself reads as
    burden" clause: bill rows that ADD monitoring/instrumentation to
    the DEPLOYED mechanism (HO3-05's bill carried a monthly ICP-MS/
    ASTM monitoring program). Scoped to the IMPLEMENTATION BILL
    section; the EXECUTABLE TEST's instruments are the falsifier, not
    the deployed mechanism, and are out of scope.

  NAMED_VARIANT — the V7 generic-class-only palette: brand/model
    markers and named custom variants in bill rows (the r24
    fictional-catalog failure class: "gradient-crosslink-density
    neoprene sheets (b)", "low-sodium borosilicate cover glass (b)").
    Lexical, high-precision markers only; disclosed as a typed net —
    the CONTRACT (r26_a1w_v7_contract.CATALOG_COMPOSITION_BIND) is
    the primary enforcement.

Findings feed the machine's NEUTRAL repair directive (quoted back,
never hidden); residuals are disclosed. The authoritative
constraint-fit read stays the auditor's (holdout v4, AM25 D2/D3).
"""
import re

from r24_constraint_scan import extract_constraint_terms  # noqa: F401

# --- section scoping (bill only) ------------------------------------------
BILL_SECTION = re.compile(
    r"IMPLEMENTATION BILL(.*?)(?=\n\s*[A-Z][A-Z ]{4,}\n|\Z)", re.S | re.I)
ROW_START = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M)

# --- added-measure span extraction ----------------------------------------
# verb rows: the span is the verb's OBJECT, cut at measure-boundary cues
# ("in parallel with X" -> the parallel anchor X is the EXISTING measure,
# not the added one — the HO3-05 byte).
_ADD_VERB = re.compile(
    r"\b(?:installs?|installed|installing|adds?|added|adding|uses?|used|"
    r"fits?|fitted|mounts?|mounted|introduces?|introducing)\s+"
    r"(?:a|an|the|one|two|three|\d+)?\s*"
    r"([a-z0-9][a-z0-9 \-/]{2,60}?)"
    r"\s*(?:,|;|\bin parallel with\b|\bwith existing\b|\balongside\b|"
    r"\bnext to\b|\bbeside\b|\bon the\b|\bto the\b|\bonto the\b|\bfor\b|"
    r"\busing\b|\bvia\b|\bat\b|$)",
    re.I)
_REPLACE_WITH = re.compile(
    r"\b(?:replaces?|replaced|replacing|swaps?|swapped|substitut\w+|"
    r"switch(?:es|ing)? to)\s+(?:a|an|the|one|two|three|\d+)?\s*"
    r"([a-z0-9][a-z0-9 \-/]{2,60}?)(?:\s+with\b|,|;|$)", re.I)
_REPLACE_OBJ = re.compile(
    r"\breplace[sd]?\s+(?:a|an|the|one|two|three|\d+)?\s*"
    r"([a-z0-9][a-z0-9 \-/]{2,60}?)\s+with\s+"
    r"([a-z0-9][a-z0-9 \-/]{2,60})", re.I)
_PARALLEL_WITH = re.compile(
    r"\b([a-z0-9][a-z0-9 \-/]{2,60}?)\s+in parallel with\b", re.I)

# class-(b) tagged noun rows: the head phrase IS the added item.
# Two committed orders: tag-suffix (HO2-03 "Zinc anode collar (b): ...")
# and tag-first (the V7/r24 format "- (b) Two titanium anode modules").
_B_ROW_SUFFIX = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])?\s*([A-Za-z0-9][^(;:\n]{2,60}?)\s*"
    r"(?:\(|\[)b(?:\)|\])", re.M)
_B_ROW_FIRST = re.compile(
    r"(?:\(|\[)\s*b\s*(?:\)|\])\s*[-–—:.]?\s*"
    r"([A-Za-z0-9][^—–;:\n]{2,60}?)(?=\s*[—–:(,]|$)")

# spans that merely ride stated infrastructure are NOT added measures
_EXISTING_SPAN = re.compile(
    r"\b(?:existing|already|stated|repurpos\w+|present in)\b", re.I)

# form-factor nouns: mounting/procurement-form vocabulary that carries no
# measure class. Stripped from BOTH the added span and the allowed vocab
# before the stem comparison (the HO3-05 byte: the resin rode on
# "cartridge", which appears in the allowed list only as the FORM of the
# activated-alumina measure).
FORM_FACTORS = {
    "cartridge", "unit", "module", "system", "equipment", "component",
    "hardware", "assembly", "housing", "valve", "pump", "line", "loop",
    "tank", "vessel", "skid", "package", "kit", "device", "instrument",
    "sensor", "controller", "timer", "actuator", "fitting", "hose",
    "pipe", "piping", "tubing", "filter", "screen", "reservoir", "panel",
    "cabinet", "probe", "datalogger", "logger", "supply", "supplies",
    "schedule", "scheduled", "interval", "window", "procedure", "step",
    "cycle", "process", "operation", "operational", "replacement",
    "replacements", "source", "set", "stage", "station", "rack",
}
GENERIC_QUALIFIERS = {
    "standard", "catalog", "procurable", "existing", "stated", "present",
    "common", "commercial", "commercially", "available", "industry",
    "typical", "conventional", "rated", "grade", "class", "type", "size",
    "duty", "manual", "automatic", "online", "offline", "new", "same",
    "equal", "identical", "equivalent", "item", "items", "product",
    "products", "shelf", "shipping", "ships", "procurable",
}

STOP_SMALL = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "at",
    "on", "by", "from", "that", "this", "any", "all", "into", "onto",
    "when", "while", "during", "must", "shall", "will", "should", "can",
    "may", "it", "its", "their", "them", "these", "those", "there",
    "then", "than", "such", "same", "also", "only", "even", "ever",
    "per", "each", "every", "is", "are", "be", "as", "via", "using",
}

# standards citations are legitimate in bill rows, never product models
STANDARDS_TOKEN = re.compile(
    r"\b(?:ASTM|ISO|ASME|IEC|ANSI|API|NACE|DIN|JIS|SAE|UL|CSA|EN)\s*"
    r"[A-Z]?\s*\d+\b")

# F41 (AM28): size/pressure-class designations are ENGINEERING CLASSES,
# not brand markers — DN (nominal diameter), PN (nominal pressure), and
# thread/fitting classes. The auditor's false-positive set: a conformant
# bill row "3-way ball valve, DN80 PN16" flagged as a model marker.
SIZE_DESIGNATION = re.compile(
    r"\b(?:DN|PN|NPT|BSP|BSPT|G|M\d{2}|ANSI\s*class|class\s*\d{2,3})"
    r"\s*[\d.]+\b"
    # sensor physics classes, not brands: NTC/PTC thermistor resistance
    # ("NTC 10k"), IEC 60751 platinum RTD classes ("PT100", "PT1000")
    r"|\b(?:NTC|PTC|PT)\s*[- ]?\d{2,4}(?:k|K)?\b", re.I)


def _stems(text, min_len=2):
    """Content stems, singular/plural tolerant, digits dropped. min_len
    2 for the ALLOWED vocab (technical short tokens: uv, ph) and for
    spans (the anchor 'UV' is a measure class — the HO3-01 byte)."""
    out = set()
    for w in re.split(r"[^a-z0-9]+", str(text).lower()):
        if w.isdigit() or len(w) < min_len or w in STOP_SMALL:
            continue
        out.add(w)
        out.add(w + "s") if not w.endswith("s") else out.add(w[:-1])
    return out


# form-factor and qualifier STRIPPING SETS: stem-normalized (both
# singular and plural variants stripped — the 'cartridge/cartridges'
# asymmetry that let the HO3-05 resin ride its own form factor).
def _strip_set(words):
    out = set(words)
    for w in words:
        out.add(w + "s")
        if w.endswith("s"):
            out.add(w[:-1])
    return out


_FF_STEMS = _strip_set(FORM_FACTORS)
_GQ_STEMS = _strip_set(GENERIC_QUALIFIERS)


def allowed_vocab(constraint):
    """(vocab_stems, has_list) from the problem's allowed-measures
    enumeration.

    Mirrors r24_constraint_scan.extract_constraint_terms' SEGMENT
    classification byte-for-byte (CUE_RE exclusions first, then the
    'only'-enumeration branch) but keeps the BODY TEXT and stems it at
    min_len=2 — v1's stemmer drops len<4 tokens ("uv", "ph"), which
    are real measure classes (the HO3-01 byte: the allowed class IS
    'in-duct UV irradiation'). The v1 function itself stays untouched
    for the exclusion path."""
    from r24_constraint_scan import CUE_RE, ALLOWED_START
    c = str(constraint or "").lower()
    bodies = []
    for seg in re.split(r"[;.]", c):
        seg = re.sub(r"^retrofit only\s*[:\-]?\s*", "", seg.strip())
        if not seg:
            continue
        cue_terms = {m.group(1) for m in CUE_RE.finditer(seg)}
        if cue_terms:
            continue  # exclusion segment — not part of the allowed body
        if "only" in seg and not re.search(r"\d", seg):
            body = re.sub(
                r"^(?:allowed measures?|permitted measures?)\s*[:\-]?\s*",
                "", seg)
            body = re.sub(r"\bonly\b\s*$", "", body).strip()
            if body:
                bodies.append(body)
    if not bodies:
        return set(), False
    return _stems(" ".join(bodies), min_len=2), True


def _added_spans(row):
    """Added-measure candidate spans from one bill row. Spans that ride
    stated infrastructure (existing/already/repurposed) are dropped."""
    spans = []
    m = _REPLACE_OBJ.search(row)
    if m:
        spans.append(m.group(2))  # the NEW item after "with"
    m = _ADD_VERB.search(row)
    if m:
        spans.append(m.group(1))
    m = _REPLACE_WITH.search(row)
    if m:
        spans.append(m.group(1))
    m = _PARALLEL_WITH.search(row)
    if m:
        # "X in parallel with Y" -> X is the ADDED measure
        spans.append(m.group(1))
    out = []
    for s in spans:
        s = s.strip(" -–—:,.")
        if len(s) < 3 or _EXISTING_SPAN.search(s):
            continue
        out.append(s)
    return out


def _span_fire(span, vocab):
    """True when the added span shares NO allowed stem after
    form-factor nouns are stripped from both sides (stem-normalized:
    singular and plural both stripped)."""
    span_stems = _stems(span, min_len=2) - _FF_STEMS - _GQ_STEMS
    if not span_stems:
        return False
    vocab_stems = set(vocab) - _FF_STEMS
    return not (span_stems & vocab_stems)


def _bill_rows(answer):
    m = BILL_SECTION.search(str(answer or ""))
    if not m:
        return []
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]


def scan_allowed_rows(problem, answer):
    """AM25 D2 STRICT row-level allowed-measures check. Fires only when
    the problem's constraint enumerates allowed measures."""
    c = str(problem.get("constraint") or "")
    vocab, has_list = allowed_vocab(c)
    if not has_list or not vocab:
        return {}
    hits = []
    for row in _bill_rows(answer):
        is_row = bool(ROW_START.match(row)) or "(b)" in row or "[b]" in row
        if not is_row:
            continue
        spans = []
        if "(b)" in row or "[b]" in row:
            bm = _B_ROW_SUFFIX.search(row) or _B_ROW_FIRST.search(row)
            if bm:
                spans.append(bm.group(1))
        spans.extend(_added_spans(row))
        for span in spans:
            if _span_fire(span, vocab):
                hits.append(
                    f"added measure '{span[:60]}' shares no allowed-list "
                    f"stem ({c[:80]}...)")
                break
        if len(hits) >= 4:
            break
    return {"ALLOWED_ROW_OUTSIDE": hits} if hits else {}


# --- apparatus scan (the deployed mechanism adds no monitoring) -----------
APPARATUS_NOUN = re.compile(
    r"\b(?:sensors?|monitors?|monitoring|instrumentation|telemetry|"
    r"data[- ]?log(?:ger|ging)?|logging|analysis program|inspection "
    r"program|sampling program|icp|spectrometry|chromatograph|"
    r" analyzer|interrogat)\w*", re.I)
APPARATUS_VERB = re.compile(
    r"\b(?:installs?|adds?|added|adding|fits?|mounts?|deploys?|"
    r"monitor|monitors|monitoring|measure|measures|measuring|sample|"
    r"sampling|log|logging|recording)\w*", re.I)


def scan_apparatus(answer):
    """APPARATUS_ROW: new monitoring/instrumentation rows in the
    DEPLOYED bill of an intervention answer (bill section only)."""
    hits = []
    for row in _bill_rows(answer):
        low = row.lower()
        if not (ROW_START.match(row) or "(a)" in row or "(b)" in row
                or "(c)" in row or "[b]" in row):
            continue
        if "existing" in low or "already" in low or "repurpos" in low:
            continue  # rides stated infrastructure — not NEW apparatus
        if APPARATUS_NOUN.search(row) and APPARATUS_VERB.search(row):
            hits.append(row[:110])
        if len(hits) >= 4:
            break
    return {"APPARATUS_ROW": hits} if hits else {}


# --- named-variant scan (V7 generic-class-only palette) -------------------
VARIANT_MARKER = re.compile(
    r"\b(?:custom[- ](?:variant|formulation|blend|compound|design|built)"
    r"|specialty |purpose[- ]built|bespoke|proprietary |prototype|"
    r"gradient[- ]crosslink|crosslink[- ]density (?:gradient|profile)|"
    r"low[- ]sodium |high[- ]purity custom)\w*", re.I)
MODEL_MARKER = re.compile(
    r"\b[A-Z]{2,}[A-Za-z]*[- ]?\d{2,}\b|\b(?:series|model) [A-Z0-9]"
    r"|®|™")


def scan_named_variant(answer):
    """NAMED_VARIANT: brand/model/custom-variant markers in bill rows —
    the V7 palette demands generic classes only (lexical, disclosed).
    Standards citations (ASTM D574) are whitelisted, never models."""
    hits = []
    for row in _bill_rows(answer):
        if not row:
            continue
        cleaned = STANDARDS_TOKEN.sub("", row)
        # F41: size/pressure classes are engineering designations,
        # stripped before the brand/model net (a class is not a brand)
        cleaned = SIZE_DESIGNATION.sub("", cleaned)
        vm = VARIANT_MARKER.search(cleaned)
        mm = MODEL_MARKER.search(cleaned)
        if vm or mm:
            hits.append(
                (f"variant-marker: {vm.group(0).strip()}" if vm else
                 f"model/brand-marker: {mm.group(0).strip()}")
                + f" | {row[:80]}")
        if len(hits) >= 4:
            break
    return {"NAMED_VARIANT": hits} if hits else {}


def scan_catalog(problem, answer):
    """The full catalog scan (deterministic, no LLM). Returns
    {kind: [details]} — empty dict is CLEAN. Findings are disclosed,
    never hidden; they feed the machine's NEUTRAL repair directive."""
    out = {}
    for partial in (scan_allowed_rows(problem, answer),
                    scan_apparatus(answer),
                    scan_named_variant(answer)):
        out.update(partial)
    return out
