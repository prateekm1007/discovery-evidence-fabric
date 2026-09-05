"""tvm_v2.value_parser — the TVM v2 deterministic value parser/normalizer.

Operator directive (R412 gradient v2, Step 2): build the TVM as a
parser/verifier system. Keep the evidence contract. Expand the canonical
value representation to POINT / RANGE / INEQUALITY / ORDINAL_QUALITATIVE /
NOT_NUMERIC, with the numerical/range evidence carrying:
raw_source_span, normalized_value, normalized_min, normalized_max, unit,
year, year_min, year_max, normalization_method.

Constitutional contract (Articles II, IV, VI, VII, XVIII, XXV):
  - DETERMINISTIC: parse(span, context) is a pure function. The same input
    always yields byte-identical output. No LLM, no heuristic guessing, no
    randomness, no locale dependence.
  - LOSSLESS: every normalized value retains the exact raw source span
    (raw_source_span is the input span byte-for-byte). Normalization never
    manufactures precision: an approximation ("~50") is NOT converted to a
    range (that would invent a tolerance the source never stated); an
    inequality keeps its open bound open; significant digits are never
    extended.
  - FAIL-CLOSED: a span that does not match the frozen grammar is MALFORMED
    with an explicit reason. It is never silently coerced, never
    "close-enough" matched, and never converted to a weaker NOT_NUMERIC
    state when it looks numeric but is unparseable (that distinction is the
    difference between a serialization defect and missing evidence).
  - CONTEXT-TYPED: VALUE and YEAR are separate parse contexts supplied by
    the caller. The parser never guesses which is meant.

Arithmetic uses decimal.Decimal so that "0.42 ± 0.03" -> [0.39, 0.45]
EXACTLY (never 0.39000000000000001). Floats appear only at the JSON
serialization boundary.

Rule cascade order (frozen specification, NORMALIZATION_RULES.json):
  VALUE: empty -> qualitative -> no-digits -> sci-e -> sci-mult ->
         double-separator -> uncertainty -> inequality(symbol, word) ->
         approximation -> between-range -> word-range -> incomplete-range ->
         dash-range -> negative-point -> point(with unit) -> malformed.
  YEAR:  empty -> no-4-digits -> from-range -> dash-range -> qualifier ->
         preposition -> literal -> inverted-check -> malformed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Canonical representation vocabulary (frozen; operator directive Step 2)
# ---------------------------------------------------------------------------

REP_POINT = "POINT"
REP_RANGE = "RANGE"
REP_INEQUALITY = "INEQUALITY"
REP_ORDINAL_QUALITATIVE = "ORDINAL_QUALITATIVE"
REP_NOT_NUMERIC = "NOT_NUMERIC"
REP_MALFORMED = "MALFORMED"

CONTEXT_VALUE = "VALUE"
CONTEXT_YEAR = "YEAR"

# Frozen qualitative vocabulary (whole-span matches only, case-insensitive;
# the canonical term is recorded, the raw span is retained verbatim).
QUALITATIVE_TERMS: Dict[str, str] = {
    "state-of-the-art": "STATE_OF_THE_ART",
    "best-in-class": "BEST_IN_CLASS",
    "record-setting": "RECORD_SETTING",
    "leading": "LEADING",
    "order-of-magnitude improvement": "ORDER_OF_MAGNITUDE_IMPROVEMENT",
    "world-class": "WORLD_CLASS",
    "gold standard": "GOLD_STANDARD",
    "unprecedented": "UNPRECEDENTED",
}

# Unit alias map: canonical <- accepted surface forms (deterministic, frozen).
# The raw span always retains the surface form; "unit" records the canonical
# form, "unit_raw" the verbatim token.
UNIT_ALIASES: Dict[str, str] = {
    "nanometers": "nm", "nanometer": "nm", "nm": "nm",
    "micrometers": "µm", "micrometer": "µm", "microns": "µm",
    "micron": "µm", "um": "µm", "µm": "µm",
    "millimeters": "mm", "millimeter": "mm", "mm": "mm",
    "centimeters": "cm", "centimeter": "cm", "cm": "cm",
    "meters": "m", "meter": "m", "m": "m",
    "percent": "%", "%": "%", "wt%": "wt%",
    "watts": "W", "watt": "W", "W": "W",
    "milliwatts": "mW", "milliwatt": "mW", "mw": "mW",
    "kilowatts": "kW", "kilowatt": "kW",
    "volts": "V", "volt": "V", "V": "V",
    "millivolts": "mV", "millivolt": "mV", "mv": "mV",
    "hertz": "Hz", "Hz": "Hz", "khz": "kHz", "mhz": "MHz",
    "ghz": "GHz",
    "pascals": "Pa", "pascal": "Pa", "Pa": "Pa", "kpa": "kPa",
    "mpa": "MPa", "gpa": "GPa", "bar": "bar",
    "mmhg": "mmHg", "mmHg": "mmHg",
    "kelvin": "K", "K": "K", "°c": "°C", "°f": "°F",
    "grams": "g", "gram": "g", "g": "g", "kg": "kg", "mg": "mg",
    "µg": "µg", "ug": "µg",
    "milliliters": "mL", "milliliter": "mL", "ml": "mL", "L": "L",
    "liters": "L", "liter": "L",
    "minutes": "min", "minute": "min", "min": "min",
    "hours": "h", "hour": "h", "h": "h",
    "seconds": "s", "second": "s", "s": "s",
    "ms": "ms", "µs": "µs", "us": "µs", "ns": "ns",
    "cycles": "cycles",
    "×": "×", "x": "×",
    "newtons": "N", "newton": "N", "N": "N", "mn": "mN", "nn": "nN",
    "joules": "J", "joule": "J", "J": "J", "pj": "pJ", "nj": "nJ",
    "µj": "µJ", "uj": "µJ", "mj": "mJ",
    "db": "dB", "dbm": "dBm",
    "mw/cm²": "mW/cm²", "w/cm²": "W/cm²", "mw/cm2": "mW/cm²",
    "µm/min": "µm/min", "um/min": "µm/min",
}

# Inequality word forms -> canonical open_bound symbol (frozen mapping).
INEQUALITY_WORDS = {
    "greater than": ">",
    "less than": "<",
    "more than": ">",
    "at least": "≥",
    "at most": "≤",
    "no less than": "≥",
    "no more than": "≤",
    "over": ">",
    "under": "<",
    "above": ">",
    "below": "<",
}

APPROXIMATION_MARKERS = ["~", "≈", "approx.", "approx", "approximately",
                         "ca.", "ca", "circa", "about"]

INEQ_SYMBOLS = (">=", "<=", ">", "<", "≥", "≤")

# A number: optional sign, digits, optional single decimal part.
# Thousands separators (1,000) are deliberately NOT supported: a comma is a
# list separator in the TVM serialization contract, and accepting it would
# introduce list/value ambiguity. Leading-dot decimals (.5) are likewise
# rejected (must be written 0.5) to keep the grammar unambiguous.
_NUM = r"[+-]?\d+(?:\.\d+)?"
_NUM_RE = re.compile(rf"^{_NUM}$")

# Separators that may join the two endpoints of a stated range.
_DASH_CLASS = "[–—-]"

_YEAR_MIN, _YEAR_MAX = 1000, 3000


def _dec(text: str) -> Decimal:
    """Exact decimal parse; raises on non-numeric input."""
    return Decimal(text)


def _clean_ws(s: str) -> str:
    """Collapse internal runs of whitespace to single spaces and strip ends.

    Used ONLY for grammar matching. raw_source_span always keeps the input
    byte-for-byte (losslessness contract).
    """
    return re.sub(r"\s+", " ", s).strip()


def _canon_unit(token: str) -> str:
    """Canonical unit form via the frozen alias map (verbatim if unknown)."""
    return UNIT_ALIASES.get(token, UNIT_ALIASES.get(token.lower(), token))


@dataclass(frozen=True)
class CanonicalValue:
    """The canonical value representation (operator directive Step 2).

    Losslessness invariant: raw_source_span is the parse input EXACTLY as
    received; every normalized field is derived from that span by the
    frozen rule cascade and nothing else.
    """
    representation: str
    raw_source_span: str
    normalization_method: str
    normalized_value: Optional[float] = None
    normalized_min: Optional[float] = None
    normalized_max: Optional[float] = None
    unit: Optional[str] = None
    unit_raw: Optional[str] = None
    year: Optional[int] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    approximation_marker: bool = False
    open_bound: Optional[str] = None
    qualitative_term: Optional[str] = None
    malformed_reason: Optional[str] = None
    parse_context: str = CONTEXT_VALUE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "representation": self.representation,
            "raw_source_span": self.raw_source_span,
            "normalized_value": self.normalized_value,
            "normalized_min": self.normalized_min,
            "normalized_max": self.normalized_max,
            "unit": self.unit,
            "unit_raw": self.unit_raw,
            "year": self.year,
            "year_min": self.year_min,
            "year_max": self.year_max,
            "normalization_method": self.normalization_method,
            "approximation_marker": self.approximation_marker,
            "open_bound": self.open_bound,
            "qualitative_term": self.qualitative_term,
            "malformed_reason": self.malformed_reason,
            "parse_context": self.parse_context,
        }


def _malformed(span: str, reason: str, context: str) -> CanonicalValue:
    return CanonicalValue(
        representation=REP_MALFORMED,
        raw_source_span=span,
        normalization_method="MALFORMED_REJECTED",
        malformed_reason=reason,
        parse_context=context,
    )


def _not_numeric(span: str, context: str) -> CanonicalValue:
    return CanonicalValue(
        representation=REP_NOT_NUMERIC,
        raw_source_span=span,
        normalization_method="NO_NUMERIC_CONTENT",
        parse_context=context,
    )


# ---------------------------------------------------------------------------
# VALUE context rule cascade (order is part of the frozen specification)
# ---------------------------------------------------------------------------

def _parse_value(raw: str) -> CanonicalValue:
    if raw.strip() == "":
        return _malformed(raw, "MALFORMED_EMPTY", CONTEXT_VALUE)

    s = _clean_ws(raw)

    # R-QUAL: whole-span qualitative term (checked first so words like
    # "leading" are never partially consumed by numeric rules).
    qual = QUALITATIVE_TERMS.get(s.lower())
    if qual is not None and not re.search(r"\d", s):
        return CanonicalValue(
            representation=REP_ORDINAL_QUALITATIVE,
            raw_source_span=raw,
            normalization_method="STATED_QUALITATIVE_TERM",
            qualitative_term=qual,
            parse_context=CONTEXT_VALUE,
        )

    # No digits at all: either a legitimate non-numeric statement, or a
    # numeric marker whose value is missing (a serialization defect, which
    # must NOT be laundered into NOT_NUMERIC).
    if not re.search(r"\d", s):
        if s.startswith(INEQ_SYMBOLS) or any(
                s.lower().startswith(w) for w in INEQUALITY_WORDS):
            return _malformed(raw, "MALFORMED_NO_BOUND_VALUE", CONTEXT_VALUE)
        for marker in APPROXIMATION_MARKERS:
            if s.lower() == marker or s.lower().startswith(marker + " ") \
                    or s.startswith(("~", "≈")):
                return _malformed(raw, "MALFORMED_NO_VALUE", CONTEXT_VALUE)
        if s.startswith("±"):
            return _malformed(raw, "MALFORMED_NO_CENTER_VALUE", CONTEXT_VALUE)
        return _not_numeric(raw, CONTEXT_VALUE)

    # Leading uncertainty without a center value: "±0.03".
    if s.startswith(("±", "+/-")):
        return _malformed(raw, "MALFORMED_NO_CENTER_VALUE", CONTEXT_VALUE)

    # R-SCI-E: scientific notation with e/E exponent ("3.2e-2").
    m = re.match(rf"^({_NUM})\s*[eE]([+-]?\d+)$", s)
    if m:
        val = _dec(m.group(1)) * (Decimal(10) ** int(m.group(2)))
        return CanonicalValue(
            representation=REP_POINT,
            raw_source_span=raw,
            normalization_method="SCIENTIFIC_NOTATION_E",
            normalized_value=float(val),
            parse_context=CONTEXT_VALUE,
        )

    # R-SCI-MULT: "1.2 × 10^3" multiplier form (also "1.2 x 10^3").
    m = re.match(rf"^({_NUM})\s*[×x]\s*10\s*(?:\^)?\s*(\d+)$", s)
    if m:
        val = _dec(m.group(1)) * (Decimal(10) ** int(m.group(2)))
        return CanonicalValue(
            representation=REP_POINT,
            raw_source_span=raw,
            normalization_method="SCIENTIFIC_NOTATION_MULTIPLIER",
            normalized_value=float(val),
            parse_context=CONTEXT_VALUE,
        )

    # Double separators are malformed, never silently collapsed ("0.1--10").
    if re.search(rf"{_DASH_CLASS}\s*{_DASH_CLASS}", s):
        return _malformed(raw, "MALFORMED_SEPARATOR", CONTEXT_VALUE)

    # R-UNC: "A ± B" (also "+/-"). Uncertainty to range is lossless: the
    # stated ± bound IS the interval; decimal arithmetic is exact.
    m = re.match(rf"^({_NUM})\s*(?:±|\+/-)\s*({_NUM})\s*(\S.*)?$", s)
    if m:
        center = _dec(m.group(1))
        unc = _dec(m.group(2))
        if unc < 0:
            return _malformed(raw, "MALFORMED_NEGATIVE_UNCERTAINTY",
                              CONTEXT_VALUE)
        unit_raw = m.group(3)
        if unit_raw is not None and re.search(r"\d", unit_raw):
            return _malformed(raw, "MALFORMED_UNCERTAINTY_STRUCTURE",
                              CONTEXT_VALUE)
        lo = center - unc
        hi = center + unc
        return CanonicalValue(
            representation=REP_RANGE,
            raw_source_span=raw,
            normalization_method="UNCERTAINTY_TO_RANGE",
            normalized_min=float(lo),
            normalized_max=float(hi),
            unit=_canon_unit(unit_raw) if unit_raw else None,
            unit_raw=unit_raw,
            parse_context=CONTEXT_VALUE,
        )

    # R-INEQ (word form): "at least 12", "greater than 100".
    for word, sym in sorted(INEQUALITY_WORDS.items(),
                            key=lambda kv: -len(kv[0])):
        m = re.match(rf"^{re.escape(word)}\s+({_NUM})\s*(\S.*)?$", s,
                     flags=re.IGNORECASE)
        if m:
            return _ineq_result(raw, sym, m.group(1), m.group(2),
                                word_form=True)

    # R-INEQ (symbol form): ">100", "≤ 3.5", ">= 0.9".
    m = re.match(rf"^(>=|<=|>|<|≥|≤)\s*({_NUM})\s*(\S.*)?$", s)
    if m:
        sym = {"<=": "≤", ">=": "≥"}.get(m.group(1), m.group(1))
        return _ineq_result(raw, sym, m.group(2), m.group(3),
                            word_form=False)

    # R-INEQ (suffix form): "12 or more".
    m = re.match(rf"^({_NUM})\s*(?:or more|or greater|or higher)\s*$", s)
    if m:
        return CanonicalValue(
            representation=REP_INEQUALITY,
            raw_source_span=raw,
            normalization_method="STATED_INEQUALITY_WORD_FORM",
            normalized_min=float(_dec(m.group(1))),
            open_bound="≥",
            parse_context=CONTEXT_VALUE,
        )

    # R-APPROX: approximate point. The approximator is RETAINED as a flag;
    # the value is the stated number exactly. NO range is manufactured
    # (never manufacture precision).
    for marker in sorted(APPROXIMATION_MARKERS, key=len, reverse=True):
        if marker in ("~", "≈"):
            m = re.match(rf"^\{marker}\s*({_NUM})\s*(\S.*)?$", s)
        else:
            m = re.match(rf"^{re.escape(marker)}\s+({_NUM})\s*(\S.*)?$", s,
                         flags=re.IGNORECASE)
        if m:
            unit_raw = m.group(2)
            if unit_raw is not None and re.search(r"\d", unit_raw):
                continue
            return CanonicalValue(
                representation=REP_POINT,
                raw_source_span=raw,
                normalization_method="APPROXIMATION_RETAINED",
                normalized_value=float(_dec(m.group(1))),
                approximation_marker=True,
                unit=_canon_unit(unit_raw) if unit_raw else None,
                unit_raw=unit_raw,
                parse_context=CONTEXT_VALUE,
            )

    # R-BETWEEN: "between 10 and 20".
    m = re.match(rf"^between\s+({_NUM})\s+and\s+({_NUM})\s*(\S.*)?$", s,
                 flags=re.IGNORECASE)
    if m:
        return _range_result(raw, "STATED_RANGE_WORD_FORM", m, CONTEXT_VALUE)

    # Incomplete word range: "10 to" (checked BEFORE the point rule so the
    # dangling connector is never mistaken for a unit).
    m = re.match(rf"^({_NUM})\s*(?:to|through)$", s, flags=re.IGNORECASE)
    if m:
        return _malformed(raw, "MALFORMED_INCOMPLETE_RANGE", CONTEXT_VALUE)

    # R-RANGE-TO: "10 to 20", "10 nm to 20 nm", "-5 to 5" (the word form
    # makes signed endpoints unambiguous).
    m = re.match(rf"^({_NUM})\s*(\S+)?\s*(?:to|through)\s+({_NUM})\s*(\S.*)?$",
                 s, flags=re.IGNORECASE)
    if m:
        return _range_result_words(raw, m)

    # R-RANGE-DASH: "0.1–10", "0.05–0.3 mW/cm²", "10–100×".
    m = re.match(rf"^({_NUM})\s*{_DASH_CLASS}\s*({_NUM})\s*(\S.*)?$", s)
    if m:
        return _range_result(raw, "STATED_RANGE", m, CONTEXT_VALUE)

    # Negative single number: "-5" (leading sign, one numeric token).
    if _NUM_RE.match(s):
        return CanonicalValue(
            representation=REP_POINT,
            raw_source_span=raw,
            normalization_method="EXACT_NUMERIC_LITERAL",
            normalized_value=float(_dec(s)),
            parse_context=CONTEXT_VALUE,
        )

    # R-POINT with trailing unit: "0.42 mW/cm²".
    m = re.match(rf"^({_NUM})\s*(\S.*)?$", s)
    if m:
        unit_raw = m.group(2)
        if unit_raw is None:
            return CanonicalValue(
                representation=REP_POINT,
                raw_source_span=raw,
                normalization_method="EXACT_NUMERIC_LITERAL",
                normalized_value=float(_dec(m.group(1))),
                parse_context=CONTEXT_VALUE,
            )
        if re.search(r"\d", unit_raw) or re.match(r"^[+\-–—]", unit_raw):
            # Trailing numeric-looking junk: not a clean unit.
            return _malformed(raw, "MALFORMED_NOT_A_NUMBER", CONTEXT_VALUE)
        return CanonicalValue(
            representation=REP_POINT,
            raw_source_span=raw,
            normalization_method="EXACT_NUMERIC_LITERAL",
            normalized_value=float(_dec(m.group(1))),
            unit=_canon_unit(unit_raw),
            unit_raw=unit_raw,
            parse_context=CONTEXT_VALUE,
        )

    return _malformed(raw, "MALFORMED_NOT_A_NUMBER", CONTEXT_VALUE)


def _ineq_result(raw: str, sym: str, bound_text: Optional[str],
                 unit_raw: Optional[str],
                 word_form: bool) -> CanonicalValue:
    bound = float(_dec(bound_text))
    if unit_raw is not None and re.search(r"\d", unit_raw):
        return _malformed(raw, "MALFORMED_NOT_A_NUMBER", CONTEXT_VALUE)
    is_lower = sym in (">", "≥")
    return CanonicalValue(
        representation=REP_INEQUALITY,
        raw_source_span=raw,
        normalization_method=("STATED_INEQUALITY_WORD_FORM" if word_form
                              else "STATED_INEQUALITY"),
        normalized_min=bound if is_lower else None,
        normalized_max=None if is_lower else bound,
        unit=_canon_unit(unit_raw) if unit_raw else None,
        unit_raw=unit_raw,
        open_bound=sym,
        parse_context=CONTEXT_VALUE,
    )


def _range_result(raw: str, method: str, m: "re.Match",
                  context: str) -> CanonicalValue:
    lo = _dec(m.group(1))
    hi = _dec(m.group(2))
    unit_raw = m.group(3)
    if unit_raw is not None and re.search(r"\d", unit_raw):
        return _malformed(raw, "MALFORMED_NOT_A_NUMBER", context)
    if lo > hi:
        return _malformed(raw, "MALFORMED_INVERTED_RANGE", context)
    return CanonicalValue(
        representation=REP_RANGE,
        raw_source_span=raw,
        normalization_method=method,
        normalized_min=float(lo),
        normalized_max=float(hi),
        unit=_canon_unit(unit_raw) if unit_raw else None,
        unit_raw=unit_raw,
        parse_context=context,
    )


def _range_result_words(raw: str, m: "re.Match") -> CanonicalValue:
    lo = _dec(m.group(1))
    hi = _dec(m.group(3))
    unit_a = m.group(2)   # optional unit after the first endpoint
    unit_b = m.group(4)   # optional unit after the second endpoint
    if unit_a and re.search(r"\d", unit_a):
        return _malformed(raw, "MALFORMED_NOT_A_NUMBER", CONTEXT_VALUE)
    if unit_b and re.search(r"\d", unit_b):
        return _malformed(raw, "MALFORMED_NOT_A_NUMBER", CONTEXT_VALUE)
    # If both endpoints carry units they must agree (deterministic check).
    if unit_a and unit_b and unit_a.lower() != unit_b.lower():
        return _malformed(raw, "MALFORMED_UNIT_MISMATCH", CONTEXT_VALUE)
    unit_raw = unit_b or unit_a
    if lo > hi:
        return _malformed(raw, "MALFORMED_INVERTED_RANGE", CONTEXT_VALUE)
    return CanonicalValue(
        representation=REP_RANGE,
        raw_source_span=raw,
        normalization_method="STATED_RANGE_WORD_FORM",
        normalized_min=float(lo),
        normalized_max=float(hi),
        unit=_canon_unit(unit_raw) if unit_raw else None,
        unit_raw=unit_raw,
        parse_context=CONTEXT_VALUE,
    )


# ---------------------------------------------------------------------------
# YEAR context rule cascade
# ---------------------------------------------------------------------------

def _parse_year(raw: str) -> CanonicalValue:
    if raw.strip() == "":
        return _malformed(raw, "MALFORMED_EMPTY", CONTEXT_YEAR)

    s = _clean_ws(raw)

    if not re.search(r"\d{4}", s):
        if re.search(r"\d", s):
            return _malformed(raw, "MALFORMED_NOT_A_YEAR", CONTEXT_YEAR)
        return _not_numeric(raw, CONTEXT_YEAR)

    # R-YEAR-RANGE-FROM: "from 2019 to 2023".
    m = re.match(r"^from\s+(\d{4})\s+to\s+(\d{4})$", s, flags=re.IGNORECASE)
    if m:
        return _year_range_result(raw, int(m.group(1)), int(m.group(2)))

    # R-YEAR-RANGE: "2018–2024", "2023-2024" (dash or hyphen).
    m = re.match(r"^(\d{4})\s*[-–—]\s*(\d{4})$", s)
    if m:
        return _year_range_result(raw, int(m.group(1)), int(m.group(2)))

    # R-YEAR-QUAL: "2023 (study)", "2023 [cohort]".
    m = re.match(r"^(\d{4})\s*[\(\[]([^\]\)]*)[\)\]]$", s)
    if m:
        y = int(m.group(1))
        if _YEAR_MIN <= y <= _YEAR_MAX:
            return CanonicalValue(
                representation=REP_POINT,
                raw_source_span=raw,
                normalization_method="YEAR_WITH_QUALIFIER",
                year=y,
                parse_context=CONTEXT_YEAR,
            )
        return _malformed(raw, "MALFORMED_NOT_A_YEAR", CONTEXT_YEAR)

    # R-YEAR-PREP: "in 2021", "since 2019", "by 2020".
    m = re.match(r"^(in|since|by|before|after|from)\s+(\d{4})$", s,
                 flags=re.IGNORECASE)
    if m:
        y = int(m.group(2))
        if _YEAR_MIN <= y <= _YEAR_MAX:
            return CanonicalValue(
                representation=REP_POINT,
                raw_source_span=raw,
                normalization_method="YEAR_WITH_PREPOSITION",
                year=y,
                parse_context=CONTEXT_YEAR,
            )
        return _malformed(raw, "MALFORMED_NOT_A_YEAR", CONTEXT_YEAR)

    # R-YEAR-LIT: bare 4-digit year.
    m = re.match(r"^(\d{4})$", s)
    if m:
        y = int(m.group(1))
        if _YEAR_MIN <= y <= _YEAR_MAX:
            return CanonicalValue(
                representation=REP_POINT,
                raw_source_span=raw,
                normalization_method="YEAR_LITERAL",
                year=y,
                parse_context=CONTEXT_YEAR,
            )
        return _malformed(raw, "MALFORMED_NOT_A_YEAR", CONTEXT_YEAR)

    return _malformed(raw, "MALFORMED_NOT_A_YEAR", CONTEXT_YEAR)


def _year_range_result(raw: str, y1: int, y2: int) -> CanonicalValue:
    if y1 > y2:
        return _malformed(raw, "MALFORMED_INVERTED_YEAR_RANGE", CONTEXT_YEAR)
    return CanonicalValue(
        representation=REP_RANGE,
        raw_source_span=raw,
        normalization_method="STATED_YEAR_RANGE",
        year_min=y1,
        year_max=y2,
        parse_context=CONTEXT_YEAR,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_value_span(span: str, context: str = CONTEXT_VALUE) -> CanonicalValue:
    """Deterministically parse one raw source span into a CanonicalValue.

    Pure function: same (span, context) -> byte-identical CanonicalValue.
    No LLM, no network, no locale, no clock.
    """
    if context == CONTEXT_YEAR:
        return _parse_year(span)
    if context == CONTEXT_VALUE:
        return _parse_value(span)
    raise ValueError(f"Unknown parse context: {context!r}")


# Frozen method registry — NORMALIZATION_RULES.json must list exactly these.
METHOD_REGISTRY = [
    "EXACT_NUMERIC_LITERAL",
    "UNCERTAINTY_TO_RANGE",
    "STATED_RANGE",
    "STATED_RANGE_WORD_FORM",
    "STATED_INEQUALITY",
    "STATED_INEQUALITY_WORD_FORM",
    "APPROXIMATION_RETAINED",
    "SCIENTIFIC_NOTATION_E",
    "SCIENTIFIC_NOTATION_MULTIPLIER",
    "STATED_QUALITATIVE_TERM",
    "NO_NUMERIC_CONTENT",
    "YEAR_LITERAL",
    "YEAR_WITH_QUALIFIER",
    "YEAR_WITH_PREPOSITION",
    "STATED_YEAR_RANGE",
    "MALFORMED_REJECTED",
]
