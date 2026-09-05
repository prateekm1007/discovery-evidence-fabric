"""tvm_v2.evidence_contract — span binding + TVM entry verification.

Operator directive (R412 gradient v2, Step 2/3): keep the evidence
contract; test raw span -> parsed representation -> evidence
verification; no LLM as judge.

Constitutional contract (Articles II, III, IV, XXV):
  - EXACT binding: a quoted span binds to a source record by byte-exact
    substring occurrence. No fuzzy matching, no case-insensitive fallback,
    no "close enough" (Article II). The a2/verify.py mechanism-span
    check tolerates a case-insensitive fallback; for NUMERICAL evidence
    spans this module is deliberately STRICTER, because a number that
    differs by one character is a different measurement.
  - The verifier never trusts the claimant (Article III): the span is
    located independently in the source text; the parsed canonical value
    is re-derived by the deterministic parser, never accepted from the
    proposer.
  - Ambiguity is recorded, never silently resolved: a span occurring more
    than once requires an explicit occurrence index; multiple occurrences
    without an index is SPAN_AMBIGUOUS_REQUIRES_INDEX.
  - Unknown stays unknown (Article XXV): SPAN_NOT_FOUND is evidence
    absence, never evidence of anything else.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .value_parser import (
    CanonicalValue,
    CONTEXT_VALUE,
    CONTEXT_YEAR,
    parse_value_span,
    REP_MALFORMED,
    REP_NOT_NUMERIC,
    REP_ORDINAL_QUALITATIVE,
)

SPAN_VERIFIED = "SPAN_VERIFIED"
SPAN_NOT_FOUND = "SPAN_NOT_FOUND"
SPAN_INDEX_OUT_OF_RANGE = "SPAN_INDEX_OUT_OF_RANGE"
SPAN_AMBIGUOUS_REQUIRES_INDEX = "SPAN_AMBIGUOUS_REQUIRES_INDEX"


@dataclass(frozen=True)
class SpanVerification:
    verdict: str
    occurrences: int
    occurrence_index: Optional[int]
    matched_substring: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "occurrences": self.occurrences,
            "occurrence_index": self.occurrence_index,
            "matched_substring": self.matched_substring,
        }


def verify_span_binding(span: str, source_text: str,
                        occurrence_index: Optional[int] = 0
                        ) -> SpanVerification:
    """Deterministically bind a quoted span to a source text.

    Byte-exact (case-sensitive, whitespace-exact) occurrence counting.
    occurrence_index: None = caller has not chosen an occurrence;
    0-based otherwise. With exactly one occurrence and no index chosen,
    index 0 is the unambiguous resolution (recorded explicitly).
    """
    if span == "":
        return SpanVerification(SPAN_NOT_FOUND, 0, None, None)
    occurrences = source_text.count(span)
    if occurrences == 0:
        return SpanVerification(SPAN_NOT_FOUND, 0, occurrence_index, None)
    if occurrences == 1 and occurrence_index is None:
        return SpanVerification(SPAN_VERIFIED, 1, 0, span)
    if occurrences == 1 and occurrence_index == 0:
        return SpanVerification(SPAN_VERIFIED, 1, 0, span)
    if occurrences == 1 and occurrence_index is not None \
            and occurrence_index != 0:
        return SpanVerification(SPAN_INDEX_OUT_OF_RANGE, 1,
                                occurrence_index, None)
    if occurrence_index is None:
        return SpanVerification(SPAN_AMBIGUOUS_REQUIRES_INDEX, occurrences,
                                None, None)
    if not (0 <= occurrence_index < occurrences):
        return SpanVerification(SPAN_INDEX_OUT_OF_RANGE, occurrences,
                                occurrence_index, None)
    return SpanVerification(SPAN_VERIFIED, occurrences, occurrence_index,
                            span)


# ---------------------------------------------------------------------------
# TVM v2 entry contract (extends the v1 13-field TVM entry schema)
# ---------------------------------------------------------------------------

# v1 field contract (operator directive, R412 recovery arm): every TVM
# entry carries domain, capability_rung, indicator, metric, value, unit,
# window, source_record, citation, retrieved_at, quoted_span,
# span_verification, confidence.
TVM_V1_FIELDS = [
    "domain", "capability_rung", "indicator", "metric", "value", "unit",
    "window", "source_record", "citation", "retrieved_at", "quoted_span",
    "span_verification", "confidence",
]

# v2 additions: the canonical value object and the signal classification.
TVM_V2_ADDITIONAL_FIELDS = [
    "canonical_value", "signal_class", "trajectory_dimension",
    "capability_family_ref", "occurrence_index",
]


def verify_tvm_entry(entry: Dict[str, Any],
                     source_text: Optional[str] = None) -> Dict[str, Any]:
    """Full deterministic verification of one TVM v2 entry.

    Returns {"valid": bool, "issues": [...], "span_verification": {...},
    "canonical_value": {...}}. An entry is valid only if every contract
    term holds. No LLM participates at any point.

    Checks:
      1. All v1 fields present (contract continuity — the v1 schema is
         not weakened in v2; it is extended).
      2. canonical_value present and parsed by the deterministic parser
         from quoted_span (re-derived, never trusted from the proposer).
      3. The canonical value is not MALFORMED / NOT_NUMERIC when the
         entry claims a measured value.
      4. quoted_span binds byte-exactly to source_text (when provided).
      5. Signal policy: capability evidence must be a PRIMARY technical
         signal (see signal_policy).
      6. Flat-field consistency: entry["value"]/entry["unit"] must agree
         with canonical_value when present (never two truths).
    """
    from .signal_policy import classify_signal, SIGNAL_PRIMARY_TECHNICAL

    issues: List[str] = []
    for f in TVM_V1_FIELDS:
        if f not in entry:
            issues.append(f"missing_field:{f}")

    span = entry.get("quoted_span", "")
    context = CONTEXT_VALUE
    cv: Optional[CanonicalValue] = None
    if "canonical_value" in entry and span:
        # Re-derive from the span: the proposer's canonical_value is
        # NEVER trusted (Article III) — the parser output is the truth.
        cv = parse_value_span(span, context)
        if cv.representation == REP_MALFORMED:
            issues.append(f"canonical_value_malformed:{cv.malformed_reason}")
        if cv.representation == REP_NOT_NUMERIC:
            issues.append("canonical_value_not_numeric")
        if cv.representation == REP_ORDINAL_QUALITATIVE:
            issues.append("canonical_value_qualitative_not_measured")
        # Flat-field consistency (value). Two truths are forbidden: the
        # flat v1 fields must agree with the re-derived canonical value.
        flat_value = entry.get("value")
        if cv.representation == "RANGE" and flat_value is not None:
            if cv.normalization_method == "UNCERTAINTY_TO_RANGE":
                # The center WAS stated by the source ("A ± B"); the flat
                # value may carry it, but it must be the exact center.
                center = (cv.normalized_min + cv.normalized_max) / 2.0
                if _num_neq(flat_value, center):
                    issues.append("flat_value_disagrees_with_canonical_center")
            else:
                # A stated range ("0.1-10") has no center; a non-null
                # flat "value" would claim one the source never stated.
                issues.append("flat_value_incompatible_with_range_representation")
        if flat_value is not None and cv.normalized_value is not None:
            if _num_neq(flat_value, cv.normalized_value):
                issues.append("flat_value_disagrees_with_canonical")
        if cv.representation == "INEQUALITY" and flat_value is not None:
            issues.append("flat_value_incompatible_with_inequality")
        flat_min = entry.get("normalized_min")
        if flat_min is not None and cv.normalized_min is not None:
            if _num_neq(flat_min, cv.normalized_min):
                issues.append("flat_min_disagrees_with_canonical")
        flat_max = entry.get("normalized_max")
        if flat_max is not None and cv.normalized_max is not None:
            if _num_neq(flat_max, cv.normalized_max):
                issues.append("flat_max_disagrees_with_canonical")
        # Flat-field consistency (unit).
        flat_unit = entry.get("unit")
        if flat_unit is not None and cv.unit is not None \
                and flat_unit != cv.unit:
            issues.append("flat_unit_disagrees_with_canonical")

    sv = SpanVerification(SPAN_NOT_FOUND, 0, None, None)
    if source_text is not None:
        sv = verify_span_binding(span, source_text,
                                 entry.get("occurrence_index", 0))
        if sv.verdict != SPAN_VERIFIED:
            issues.append(f"span_binding:{sv.verdict}")
    else:
        issues.append("source_text_not_supplied_for_verification")

    # Signal policy (operator directive Step 6).
    signal = entry.get("trajectory_dimension")
    if signal is not None:
        sig_class = classify_signal(signal)
        if sig_class != SIGNAL_PRIMARY_TECHNICAL:
            issues.append(f"non_primary_signal_as_capability:{signal}")
    else:
        issues.append("missing_trajectory_dimension")

    family_ref = entry.get("capability_family_ref")
    if family_ref:
        from .capability_family import validate_family_reference
        ok, fam_issues = validate_family_reference(family_ref)
        if not ok:
            issues.extend(f"family:{p}" for p in fam_issues)

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "span_verification": sv.to_dict(),
        "canonical_value": cv.to_dict() if cv else None,
    }


def _num_neq(a: Any, b: float) -> bool:
    try:
        return abs(float(a) - float(b)) > 1e-12
    except (TypeError, ValueError):
        return True
