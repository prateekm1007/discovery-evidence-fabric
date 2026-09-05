"""tvm_v2 — the TVM v2 parser/verifier system (R412 gradient v2).

Deterministic value parsing, evidence-contract span binding, typed
capability-family abstraction, and trajectory-signal policy. No LLM
participates in any verification decision (operator directive Steps 2-6;
Constitution Articles II/III/IV/XVIII).
"""
from .value_parser import (
    CanonicalValue,
    CONTEXT_VALUE,
    CONTEXT_YEAR,
    parse_value_span,
    METHOD_REGISTRY,
    REP_POINT,
    REP_RANGE,
    REP_INEQUALITY,
    REP_ORDINAL_QUALITATIVE,
    REP_NOT_NUMERIC,
    REP_MALFORMED,
)
from .evidence_contract import (
    SpanVerification,
    verify_span_binding,
    verify_tvm_entry,
    SPAN_VERIFIED,
    SPAN_NOT_FOUND,
    SPAN_INDEX_OUT_OF_RANGE,
    SPAN_AMBIGUOUS_REQUIRES_INDEX,
    TVM_V1_FIELDS,
)
from .signal_policy import (
    classify_signal,
    validate_signal_usage,
    signal_vocabulary_report,
    SIGNAL_PRIMARY_TECHNICAL,
    SIGNAL_EXPLANATORY_ONLY,
    SIGNAL_UNKNOWN,
)
from .capability_family import (
    load_family_map,
    validate_family_entry,
    validate_family_map,
    validate_family_reference,
    expand_search_vocabulary,
)
from .v1_strict_schema import (
    v1_value_admissible,
    v1_year_admissible,
    v1_flat_admission,
    V1_PREDICATE_LABEL,
)

__all__ = [
    "CanonicalValue", "CONTEXT_VALUE", "CONTEXT_YEAR", "parse_value_span",
    "METHOD_REGISTRY", "REP_POINT", "REP_RANGE", "REP_INEQUALITY",
    "REP_ORDINAL_QUALITATIVE", "REP_NOT_NUMERIC", "REP_MALFORMED",
    "SpanVerification", "verify_span_binding", "verify_tvm_entry",
    "SPAN_VERIFIED", "SPAN_NOT_FOUND", "SPAN_INDEX_OUT_OF_RANGE",
    "SPAN_AMBIGUOUS_REQUIRES_INDEX", "TVM_V1_FIELDS",
    "classify_signal", "validate_signal_usage", "signal_vocabulary_report",
    "SIGNAL_PRIMARY_TECHNICAL", "SIGNAL_EXPLANATORY_ONLY",
    "SIGNAL_UNKNOWN",
    "load_family_map", "validate_family_entry", "validate_family_map",
    "validate_family_reference", "expand_search_vocabulary",
    "v1_value_admissible", "v1_year_admissible", "v1_flat_admission",
    "V1_PREDICATE_LABEL",
]
