"""discovery_fabric/engine/numeric_claims.py — the F80 on-row
numeric-claim extraction (R83, claim c-0099; AM72/V73 direction 3).

F80 (auditor, opened at audit 740814634): the generated answers' own
numbers were never typed — candidate_schema carries the enum fields
but no stated-magnitude/assumption/numeric_claim fields, so the P1
gate measured registry coverage on REFERENCE scenarios, not the
output's own physics (on_row_physics_runs was 0/36 on the labelled
set).

This module is the deterministic extraction leg: the answer's OWN
text fields (intervention / expected_effect / testable_prediction /
mechanism / falsification_test) are scanned for number+unit pairs and
each becomes a TYPED numeric-claim record:

  {claim_id, value, unit_raw, unit, quantity, dimension,
   source_field, source_span}

Unit discipline (the physics_checks convention): every claim is
parsed to a pint Quantity — a number whose unit cannot be parsed is a
TYPED unparseable record, never silently dropped and never coerced to
a bare float (a bare float for a dimensional input is UNVERIFIABLE,
Art. 3). The pint registry is physics_checks' own (_UREG) so claims
convert against registry inputs without cross-registry errors.

Unit aliases: the answers write units in prose forms ("kA/m2",
"degC", "C", "%"); the alias table normalizes them to pint-parseable
strings BEFORE parsing. Ambiguity policy (typed): bare "C" maps to
degC — the device-temperature convention of this problem domain; a
true coulomb claim would fail the C-dimension bind visibly rather
than false-bind (dimensional binding can only refuse, never
mis-convert: a degC quantity cannot .to("C")).

Zero LLM, zero network, zero prose semantics beyond the number+unit
pattern — the module never decides WHAT a number means, only that it
is a number with a parseable unit at a span. Binding semantics live
in onrow_physics (dimensional compatibility only).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import physics_checks as _pc

# number forms: 3.2 / 0.5 / 12 / 1,200 (comma thousands) — a leading
# word boundary keeps "P31" and ids out; the value must not be part of
# an identifier (no alnum immediately before the digits)
_NUM = r"(?<![0-9A-Za-z_])(\d+(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
# unit forms, longest-first so "kA/m2" wins over "A"; the trailing
# boundary keeps "W/m2x" from matching "W/m2" prefix-only
_UNIT = (r"\s?(kA/m2|kA/m\u00b2|A/m2|A/m\u00b2|MA/m2|degC|\u00b0C|"
         r"kPa|MPa|bar|mbar|kW|MW|W\b|mA\b|A\b|kV|V\b|"
         r"mg/L|g/mol|kg/m3|kg/m\u00b3|g/m2/day|"
         r"mS/cm|S/m|"
         r"mm|cm|km|mm2|mm\u00b2|"
         r"kJ/mol|MJ/kmol|"
         r"mN/m|N/m|"
         r"kHz|Hz|MHz|"
         r"kg/h|g/h|m3/h|L/min|m/s|mm/s|"
         r"\u00b5m|\u03bcm|"
         r"day|days|h\b|s\b|min\b|"
         r"%|C\b|K\b)")
NUMBER_UNIT_RE = re.compile(_NUM + _UNIT)

# prose unit -> pint-parseable string. Everything not in the table is
# passed through to pint unchanged (pint then accepts or the claim is
# typed unparseable).
UNIT_ALIASES = {
    "kA/m2": "kA/m**2", "kA/m\u00b2": "kA/m**2",
    "A/m2": "A/m**2", "A/m\u00b2": "A/m**2",
    "MA/m2": "MA/m**2",
    "degC": "degC", "\u00b0C": "degC", "C": "degC",
    "K": "kelvin",
    "%": "percent",
    "days": "day",
    "h": "hour", "min": "minute", "s": "second",
    "mm2": "mm**2", "mm\u00b2": "mm**2",
    "\u00b5m": "um", "\u03bcm": "um",
    "kg/m3": "kg/m**3", "kg/m\u00b3": "kg/m**3",
}

# the answer's own fields, in scan order (the extraction surface —
# the same fields the route composes and the measurement reads)
OWN_FIELDS = ("intervention", "expected_effect", "testable_prediction",
              "mechanism", "falsification_test")


def parse_quantity(value: float, unit_raw: str):
    """Value + raw unit string -> (pint Quantity, normalized unit) or
    (None, None) when the unit does not parse. NEVER raises: an
    unparseable unit is a typed outcome, not an exception path."""
    unit = UNIT_ALIASES.get(unit_raw, unit_raw)
    try:
        q = _pc._UREG.Quantity(float(value), unit)  # noqa: SLF001
        return q, unit
    except Exception:  # noqa: BLE001 — typed, never a crash path
        return None, None


def extract_numeric_claims(text: str,
                           source_field: str = "",
                           prefix: str = "nc"
                           ) -> Dict[str, Any]:
    """One text field -> the typed extraction record:

      {claims: [...], unparseable: [...], n_scanned: int}

    Each claim: {claim_id, value, unit_raw, unit, quantity, dimension,
    source_field, source_span}. Each unparseable: {value, unit_raw,
    source_field, source_span, typed: "UNPARSEABLE_UNIT"} — the number
    exists in the text but its unit is not a physical unit; it stays
    visible, never silently dropped (Art. 5)."""
    claims: List[Dict[str, Any]] = []
    unparseable: List[Dict[str, Any]] = []
    n = 0
    for m in NUMBER_UNIT_RE.finditer(text or ""):
        n += 1
        raw_value = m.group(1).replace(",", "")
        value = float(raw_value)
        unit_raw = m.group(2).strip()
        q, unit = parse_quantity(value, unit_raw)
        rec = {
            "claim_id": f"{prefix}-{n}",
            "value": value,
            "unit_raw": unit_raw,
            "source_field": source_field,
            "source_span": [m.start(1), m.end(2)],
        }
        if q is None:
            rec["typed"] = "UNPARSEABLE_UNIT"
            unparseable.append(rec)
            continue
        rec["unit"] = unit
        rec["quantity"] = f"{value} {unit}"
        rec["dimension"] = str(q.dimensionality)
        claims.append(rec)
    return {"claims": claims, "unparseable": unparseable,
            "n_scanned": n}


def extract_candidate_claims(candidate: Dict[str, Any]
                             ) -> Dict[str, Any]:
    """A route candidate -> the aggregated extraction record over its
    OWN fields. Claim ids are prefixed per field so ids stay unique
    across the candidate. Fields absent from the candidate are simply
    not scanned (absent fact is not manufactured)."""
    all_claims: List[Dict[str, Any]] = []
    all_unparseable: List[Dict[str, Any]] = []
    n = 0
    for field in OWN_FIELDS:
        text = str(candidate.get(field) or "")
        if not text:
            continue
        out = extract_numeric_claims(text, source_field=field,
                                     prefix=f"nc-{n}")
        n += out["n_scanned"]
        all_claims.extend(out["claims"])
        all_unparseable.extend(out["unparseable"])
    # re-key claim ids sequentially over the candidate
    for i, c in enumerate(all_claims, 1):
        c["claim_id"] = f"nc-{i}"
    for i, u in enumerate(all_unparseable, 1):
        u["claim_id"] = f"ncu-{i}"
    return {"claims": all_claims, "unparseable": all_unparseable,
            "n_scanned": n}


def claims_for_binding(extraction: Dict[str, Any]
                       ) -> List[Tuple[str, Any]]:
    """The bindable (claim_id, pint Quantity) pairs, in extraction
    order — the input surface for onrow_physics.bind_claims."""
    out = []
    for c in (extraction or {}).get("claims", []):
        q, _ = parse_quantity(c["value"], c["unit_raw"])
        if q is not None:
            out.append((c["claim_id"], q))
    return out
