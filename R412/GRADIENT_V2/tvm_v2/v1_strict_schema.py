"""tvm_v2.v1_strict_schema — the reconstructed v1 admission predicate.

Operator directive (R412 gradient v2, Step 4): measure how many of the
v1 proposals would become admissible after lossless deterministic
normalization. The v1 failure class was reported by the operator as
VALUE_OR_YEAR_NOT_NUMERIC (31 of 34 proposals).

PROVENANCE DISCLOSURE (Constitution Articles VI, XXV):
  The actual v1 admission code was NOT recoverable from this workspace
  (see V1_OUTPUT_REPARSE_MEASUREMENT.json and
  R412_GRADIENT_V1_INSTRUMENT_FINDING.json). This predicate is a
  RECONSTRUCTION from the operator-reported failure-class name:
  a schema that rejects a proposal with VALUE_OR_YEAR_NOT_NUMERIC is one
  whose value field must be a plain decimal number and whose year field
  must be a plain 4-digit integer. The reconstruction is labeled
  RECONSTRUCTED_FROM_REPORTED_FAILURE_CLASS everywhere it is used, and
  it is used ONLY for the corpus-level instrument comparison — never as
  a claim about the actual v1 code.
"""
from __future__ import annotations

import re
from typing import Optional

V1_PREDICATE_LABEL = "RECONSTRUCTED_FROM_REPORTED_FAILURE_CLASS"

_V1_VALUE_RE = re.compile(r"^-?\d+(\.\d+)?$")
_V1_YEAR_RE = re.compile(r"^\d{4}$")


def v1_value_admissible(span: str) -> bool:
    """v1 strict value admission: plain decimal number only.

    Everything else — ranges ("0.1-10", "10 to 20"), uncertainties
    ("0.42 ± 0.03"), approximations ("~50"), inequalities (">100"),
    scientific notation ("3.2e-2"), values with units attached to the
    number token in a non-flat form — is NOT a plain decimal and would be
    rejected by a strict POINT-only schema as VALUE_OR_YEAR_NOT_NUMERIC.
    """
    return bool(_V1_VALUE_RE.match(span.strip()))


def v1_year_admissible(span: str) -> bool:
    """v1 strict year admission: plain 4-digit integer only.

    "2023 (study)", "2018-2024", "in 2021", "from 2019 to 2023" are not
    plain integers and would be rejected as VALUE_OR_YEAR_NOT_NUMERIC.
    """
    return bool(_V1_YEAR_RE.match(span.strip()))


def v1_flat_admission(value_span: str, year_span: Optional[str]) -> bool:
    """The full reconstructed v1 admission predicate for one proposal."""
    if year_span is not None and not v1_year_admissible(year_span):
        return False
    return v1_value_admissible(value_span)
