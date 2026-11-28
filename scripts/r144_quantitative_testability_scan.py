#!/usr/bin/env python3
"""r144_quantitative_testability_scan.py — the QUANTITATIVE
TESTABILITY bind (R144 DIR-2 lever (b), claim c-0243, the R143-F6
remedy). Deterministic, no LLM.

The measured defect (from the committed v16 bytes + the delegated
owner's scoring): 22/30 inventions were sound but NOT strong — the
rubric's 4 needs "novel+feasible+QUANTITATIVE-testable", and the
delivered EXECUTABLE TEST / PHYSICS CHECK sections asserted
qualitative effects ("the failure rate DROPS") without a running
unit-checked calculation and a falsifiable numeric prediction. The
V4 directive already mandates "a one-to-two-line magnitude
verification"; the 3.3-bar evidence is that the model does not
deliver it reliably under a directive alone — so this scan TYPESES
its absence at the check layer (the F42 convention: surfaced in
final_meta, fed to the neutral repair directive, never silent, never
a bar change).

Two deterministic legs (both typed findings, no LLM):

  QUANT_TEST_MISSING — the EXECUTABLE TEST section must contain a
    NUMERIC pass/fail threshold with UNITS (a quantity + a unit
    token + a comparison), not a bare qualitative verb. The scan
    fires when the threshold is absent.

  PHYSICS_MAGNITUDE_MISSING — the PHYSICS CHECK section must contain
    an explicit MAGNITUDE: a numeric value participating in a
    computation (value + operator + unit), e.g. "0.8 x 10^-6 m^2/s"
    or "dilution >= 45:1". A governing relation NAMED without a
    magnitude is the typed defect (the v16 pattern).

Findings feed the machine's NEUTRAL repair directive (quoted back,
never hidden); residuals are disclosed in final_meta — the same
contract as every other scan leg.
"""
from __future__ import annotations

import re

# the EXECUTABLE TEST / PHYSICS CHECK section extractors (the V4
# section headers; tolerant to markdown emphasis and casing)
_TEST_SECTION = re.compile(
    r"EXECUTABLE\s+TEST(.*?)(?=\n[A-Z][A-Z \-]{3,}\n|\Z)", re.I | re.S)
_PHYSICS_SECTION = re.compile(
    r"PHYSICS\s+CHECK(.*?)(?=\n[A-Z][A-Z \-]{3,}\n|\Z)", re.I | re.S)

# a unit token: SI/engineering units with optional exponents and
# prefixes (the structural vocabulary of a dimensioned quantity)
_UNIT = (
    r"(?:m(?:m|cm|km)?|kg|g|s|ms|hz|khz|mhz|n|kn|pa|kpa|mpa|bar|psi|"
    r"c|k|°c|°f|v|mv|kv|a|ma|w|mw|kw|j|kj|mj|wh|kwh|mol|mmol|ppm|"
    r"ph|l|ml|m3|cm3|m2|cm2|mm2|%|db|rpm|l/min|m/s|mm/s|mg/l|g/m3|"
    r"s-1|h-1|kg/m3|w/m2|w/mk|n/m|m/s2|rad|deg|cycles?|hours?|days?|"
    r"weeks?|months?|years?|runs?|parts?(?:\s+per\s+(?:million|thousand))"
    r"|(?:million|thousand)\s+cycles?)")

# a numeric value (with optional scientific notation / thousands)
_NUM = r"(?:\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?|(?:\d{1,3}(?:,\d{3})+))"

# leg 1: a numeric threshold in the EXECUTABLE TEST — value + unit +
# comparison operator, e.g. ">= 45:1", "< 0.2 mm", "at least 3 dB"
_THRESHOLD = re.compile(
    _NUM + r"\s*(?::1|:1\b|%\s|" + _UNIT + r")?\s*"
    r"(?:>=|<=|>|<|less\s+than|greater\s+than|at\s+(?:least|most)|"
    r"below|above|within|exceeds?|no\s+more\s+than|at\s+minimum|"
    r"at\s+maximum)"
    r"|" r"(?:>=|<=|>|<|less\s+than|greater\s+than|at\s+(?:least|most)"
    r"|below|above|exceeds?|no\s+more\s+than)\s*" + _NUM +
    r"\s*(?::1|:1\b|%\s|" + _UNIT + r")?", re.I)

# leg 2: a magnitude in the PHYSICS CHECK — a value WITH a unit
# participating in a relation (x >= y unit, y unit, "rate of Z"),
# not a bare dimensionless assertion
_MAGNITUDE = re.compile(
    _NUM + r"\s*(?:[eE][+-]?\d+\s*)?(?:x|×|\*|·)?\s*(?:" + _NUM +
    r"\s*)?" + _UNIT + r"|" + _NUM + r"\s*(?:to|–|-|—)\s*" + _NUM +
    r"\s*" + _UNIT, re.I)

# the ratio form (dilution 45:1, aspect 3:1) counts as a magnitude
_RATIO = re.compile(_NUM + r"\s*:\s*" + _NUM + r"(?!\d)", re.I)


def scan_quantitative_testability(prob: dict, a: str) -> dict:
    """The quantitative-testability typed findings for one answer.
    Structural, deterministic, quoted back to the repair directive —
    never a silent gate, never a bar change."""
    out: dict = {}
    qt = (prob.get("question_type") or "").lower()
    if qt.startswith("predictor"):
        # predictor rows are scored on calibration coverage, not the
        # invention rubric's quantitative-testability axis
        return out
    m = _TEST_SECTION.search(a)
    test_txt = m.group(1) if m else ""
    if test_txt and not (_THRESHOLD.search(test_txt)
                         or _RATIO.search(test_txt)):
        out["QUANT_TEST_MISSING"] = [
            "the EXECUTABLE TEST section has no NUMERIC pass/fail "
            "threshold with units — state the falsifiable quantity, "
            "its unit, and the comparison (e.g. '>= 45:1 dilution', "
            "'< 0.2 mm wear depth per 1000 h'); a qualitative "
            "'the failure rate drops' is not a falsifier"]
    m = _PHYSICS_SECTION.search(a)
    phys_txt = m.group(1) if m else ""
    if phys_txt and not (_MAGNITUDE.search(phys_txt)
                         or _RATIO.search(phys_txt)):
        out["PHYSICS_MAGNITUDE_MISSING"] = [
            "the PHYSICS CHECK section names no MAGNITUDE — show the "
            "running calculation with a unit-checked value (e.g. "
            "'the 2.1 m diffuser at 0.8 m depth yields 45:1 boundary "
            "dilution'); a governing relation named without a "
            "magnitude is a typed defect"]
    return out
