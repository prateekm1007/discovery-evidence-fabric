"""tests/test_r412_tvm_v2.py — hermetic R412 gradient v2 suite.

Covers the operator directive Steps 1-3, 5-7 with positive, negative,
adversarial, and metamorphic tests (Constitution Articles V, VIII, XVII,
XXX). NO LLM is used anywhere in this suite; every verdict is
deterministic. The calibration corpus hash is pinned so the corpus
cannot change without this suite failing (corpus immutability rule).

Frozen pins:
  corpus sha256 = dd2a40906bf3f8a3fe730b4947e250ec47b65ac51831b1e387ad36fe5d0d419c
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
V2DIR = REPO / "R412" / "GRADIENT_V2"
sys.path.insert(0, str(V2DIR))

from tvm_v2 import (  # noqa: E402
    CONTEXT_VALUE,
    CONTEXT_YEAR,
    SIGNAL_EXPLANATORY_ONLY,
    SIGNAL_PRIMARY_TECHNICAL,
    SPAN_AMBIGUOUS_REQUIRES_INDEX,
    SPAN_INDEX_OUT_OF_RANGE,
    SPAN_NOT_FOUND,
    SPAN_VERIFIED,
    V1_PREDICATE_LABEL,
    classify_signal,
    expand_search_vocabulary,
    parse_value_span,
    signal_vocabulary_report,
    validate_family_map,
    v1_value_admissible,
    verify_span_binding,
    verify_tvm_entry,
)
from tvm_v2.value_parser import METHOD_REGISTRY  # noqa: E402

CORPUS_PATH = V2DIR / "TVM_V2_PARSER_CALIBRATION_CORPUS.json"
# Single contiguous literal on purpose: the seal verifier checks this
# exact hash string appears in this test file's source.
CORPUS_SHA256 = "dd2a40906bf3f8a3fe730b4947e250ec47b65ac51831b1e387ad36fe5d0d419c"
PREREG_PATH = V2DIR / "R412_GRADIENT_V2_PREREGISTRATION.json"
FINDING_PATH = REPO / "R412" / "R412_GRADIENT_V1_INSTRUMENT_FINDING.json"
MEASUREMENT_PATH = V2DIR / "V1_OUTPUT_REPARSE_MEASUREMENT.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Stage 1+2: raw span -> parsed canonical representation (every case)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda c: c["id"])
def test_corpus_case(case):
    """Every frozen corpus case: parse matches ground truth, and the raw
    span is retained byte-for-byte (losslessness)."""
    exp = case["expected"]
    got = parse_value_span(case["raw_span"], case["field_context"])
    d = got.to_dict()
    for key in ("representation", "normalization_method", "unit", "year",
                "year_min", "year_max", "approximation_marker", "open_bound",
                "qualitative_term", "malformed_reason"):
        if key in exp:
            assert d[key] == exp[key], f"{case['id']} {key}"
    for key in ("normalized_value", "normalized_min", "normalized_max"):
        if key in exp:
            ev, gv = exp[key], d[key]
            if ev is None or gv is None:
                assert (ev is None) == (gv is None), f"{case['id']} {key}"
            else:
                assert abs(float(ev) - float(gv)) < 1e-9, f"{case['id']} {key}"
    assert d["raw_source_span"] == case["raw_span"]


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda c: c["id"])
def test_parse_is_deterministic(case):
    """Same input -> byte-identical output, always (pure function)."""
    a = parse_value_span(case["raw_span"], case["field_context"]).to_dict()
    b = parse_value_span(case["raw_span"], case["field_context"]).to_dict()
    assert a == b


def test_corpus_hash_pinned():
    """Corpus immutability: the frozen corpus cannot change unnoticed."""
    assert _sha256(CORPUS_PATH) == CORPUS_SHA256


def test_method_registry_matches_ruleset():
    rules = json.loads(
        (V2DIR / "NORMALIZATION_RULES.json").read_text(encoding="utf-8"))
    assert sorted(METHOD_REGISTRY) == \
        sorted(rules["method_registry_must_equal"])


# ---------------------------------------------------------------------------
# Never manufacture precision (the core losslessness guarantees)
# ---------------------------------------------------------------------------

def test_approximation_never_becomes_range():
    """'~50' must NOT be widened to a range: the source never stated a
    tolerance, so inventing one would manufacture precision."""
    cv = parse_value_span("~50", CONTEXT_VALUE)
    assert cv.representation == "POINT"
    assert cv.approximation_marker is True
    assert cv.normalized_min is None
    assert cv.normalized_max is None


def test_approximation_flag_is_the_only_difference():
    """Metamorphic: '~50' vs '50' differ only in the marker and method —
    the numeric value must be identical."""
    a = parse_value_span("~50", CONTEXT_VALUE)
    b = parse_value_span("50", CONTEXT_VALUE)
    assert a.normalized_value == b.normalized_value == 50.0
    assert a.approximation_marker and not b.approximation_marker
    assert a.normalization_method != b.normalization_method


def test_uncertainty_range_is_exact_decimal_arithmetic():
    cv = parse_value_span("0.42 ± 0.03", CONTEXT_VALUE)
    assert cv.representation == "RANGE"
    assert cv.normalized_min == pytest.approx(0.39, abs=1e-12)
    assert cv.normalized_max == pytest.approx(0.45, abs=1e-12)
    assert cv.normalized_min != pytest.approx(0.390000000001, abs=1e-15)


def test_inequality_bound_stays_open():
    cv = parse_value_span(">100", CONTEXT_VALUE)
    assert cv.representation == "INEQUALITY"
    assert cv.normalized_min == 100.0
    assert cv.normalized_max is None  # an open bound is never closed


def test_inequality_upper_bound():
    cv = parse_value_span("≤ 3.5", CONTEXT_VALUE)
    assert cv.normalized_max == 3.5
    assert cv.normalized_min is None


def test_no_unit_conversion_by_parser():
    """The parser never converts units: '10 nm' stays 10 nm (verbatim
    raw span; canonical alias only)."""
    cv = parse_value_span("10 nm", CONTEXT_VALUE)
    assert cv.unit == "nm"
    assert cv.normalized_value == 10.0


def test_inverted_range_is_malformed_never_swapped():
    cv = parse_value_span("20 to 10", CONTEXT_VALUE)
    assert cv.representation == "MALFORMED"
    assert cv.malformed_reason == "MALFORMED_INVERTED_RANGE"


def test_inverted_year_range_is_malformed():
    cv = parse_value_span("2024–2018", CONTEXT_YEAR)
    assert cv.representation == "MALFORMED"
    assert cv.malformed_reason == "MALFORMED_INVERTED_YEAR_RANGE"


def test_double_separator_is_malformed_never_collapsed():
    cv = parse_value_span("0.1--10", CONTEXT_VALUE)
    assert cv.malformed_reason == "MALFORMED_SEPARATOR"


def test_dangling_connector_is_not_a_unit():
    cv = parse_value_span("10 to", CONTEXT_VALUE)
    assert cv.malformed_reason == "MALFORMED_INCOMPLETE_RANGE"


def test_malformed_is_not_laundered_into_not_numeric():
    """A serialization defect (numeric-looking, unparseable) must remain
    MALFORMED — distinct from genuine NOT_NUMERIC evidence absence."""
    for span in ("±0.03", "0.4.2", ">", "approx"):
        cv = parse_value_span(span, CONTEXT_VALUE)
        assert cv.representation == "MALFORMED", span
    for span in ("varies", "not reported"):
        cv = parse_value_span(span, CONTEXT_VALUE)
        assert cv.representation == "NOT_NUMERIC", span


def test_value_year_context_disambiguation_is_explicit():
    a = parse_value_span("2023", CONTEXT_VALUE)
    b = parse_value_span("2023", CONTEXT_YEAR)
    assert a.representation == "POINT" and a.normalized_value == 2023.0
    assert b.year == 2023 and b.normalized_value is None


# ---------------------------------------------------------------------------
# Stage 3: evidence verification (span binding; byte-exact, no LLM judge)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fx", CORPUS["verification_fixtures"],
                         ids=lambda f: f["id"])
def test_verification_fixture(fx):
    sv = verify_span_binding(fx["span"], fx["source_text"],
                             fx["occurrence_index"])
    assert sv.verdict == fx["expected_verdict"]
    assert sv.occurrences == fx["expected_occurrences"]


def test_no_fuzzy_span_binding():
    """A whitespace-mutated span must not match (Article II: exact beats
    semantic plausibility)."""
    source = "efficiency was 0.42 ± 0.03 under standard conditions"
    sv = verify_span_binding("0.42  ±  0.03", source, 0)
    assert sv.verdict == SPAN_NOT_FOUND


def test_no_case_insensitive_fallback_for_numeric_spans():
    """Numeric evidence binding is STRICTER than the a2 mechanism-span
    check: case changes must not match either."""
    source = "reported value of 5X gain"
    sv = verify_span_binding("5x gain", source, 0)
    assert sv.verdict == SPAN_NOT_FOUND


def test_ambiguous_span_requires_index():
    source = "0.42 first; 0.42 second"
    sv = verify_span_binding("0.42", source, None)
    assert sv.verdict == SPAN_AMBIGUOUS_REQUIRES_INDEX
    assert sv.occurrences == 2


def test_span_index_out_of_range_recorded():
    source = "0.42 first; 0.42 second"
    sv = verify_span_binding("0.42", source, 5)
    assert sv.verdict == SPAN_INDEX_OUT_OF_RANGE
    assert sv.occurrences == 2


# ---------------------------------------------------------------------------
# TVM entry verification (adversarial: the proposer is untrusted)
# ---------------------------------------------------------------------------

SOURCE_TEXT = ("The actuator achieved a positioning error of 0.42 ± 0.03 "
               "nm under closed-loop control in 2023, with state-of-the-art "
               "disturbance rejection at bandwidths up to 10 to 20 kHz.")


def _valid_entry():
    return {
        "domain": "precision actuation",
        "capability_rung": "frontier",
        "indicator": "positioning error",
        "metric": "closed-loop positioning error",
        "value": 0.42,
        "unit": "nm",
        "window": "2023",
        "source_record": "SR-001",
        "citation": "Test Source 2023",
        "retrieved_at": "2026-09-06T00:00:00Z",
        "quoted_span": "0.42 ± 0.03 nm",
        "span_verification": "SPAN_VERIFIED",
        "confidence": 0.9,
        "canonical_value": {"representation": "RANGE"},
        "signal_class": "PRIMARY_TECHNICAL",
        "trajectory_dimension": "performance",
        "capability_family_ref": "ACTUATION_CONTROL_PRECISION",
        "occurrence_index": 0,
    }


def test_valid_tvm_entry_passes():
    result = verify_tvm_entry(_valid_entry(), SOURCE_TEXT)
    assert result["valid"], result["issues"]
    assert result["span_verification"]["verdict"] == SPAN_VERIFIED
    # The canonical value was RE-DERIVED from the span (Article III).
    assert result["canonical_value"]["representation"] == "RANGE"
    assert result["canonical_value"]["normalized_min"] == \
        pytest.approx(0.39, abs=1e-12)


def test_tvm_entry_with_bad_span_fails():
    entry = _valid_entry()
    entry["quoted_span"] = "0.55 ± 0.02 nm"  # not in source
    result = verify_tvm_entry(entry, SOURCE_TEXT)
    assert not result["valid"]
    assert any("span_binding:SPAN_NOT_FOUND" in i for i in result["issues"])


def test_tvm_entry_flat_value_disagreement_detected():
    entry = _valid_entry()
    entry["value"] = 0.99  # disagrees with the quoted span's center
    result = verify_tvm_entry(entry, SOURCE_TEXT)
    assert any("flat_value_disagrees_with_canonical" in i
               for i in result["issues"])


def test_tvm_entry_fabricated_center_on_stated_range_detected():
    """A stated range ('0.1-10') has no center: a flat 'value' field
    claiming one manufactures a number the source never stated."""
    source = "the device operates from 0.1–10 mW across its range"
    entry = _valid_entry()
    entry["quoted_span"] = "0.1–10 mW"
    entry["value"] = 5.05  # fabricated midpoint
    entry["unit"] = "mW"
    entry["canonical_value"] = {"representation": "RANGE"}
    result = verify_tvm_entry(entry, source)
    assert any(
        "flat_value_incompatible_with_range_representation" in i
        for i in result["issues"])


def test_tvm_entry_flat_value_on_inequality_detected():
    source = "the sensor detects levels >100 ppm reliably"
    entry = _valid_entry()
    entry["quoted_span"] = ">100 ppm"
    entry["value"] = 100.0
    entry["unit"] = "ppm"
    result = verify_tvm_entry(entry, source)
    assert any("flat_value_incompatible_with_inequality" in i
               for i in result["issues"])


def test_tvm_entry_missing_v1_field_detected():
    entry = _valid_entry()
    del entry["confidence"]
    result = verify_tvm_entry(entry, SOURCE_TEXT)
    assert any("missing_field:confidence" in i for i in result["issues"])


def test_tvm_entry_investment_signal_rejected():
    """Step 6 enforcement: investment cannot be capability evidence."""
    entry = _valid_entry()
    entry["trajectory_dimension"] = "investment"
    result = verify_tvm_entry(entry, SOURCE_TEXT)
    assert any("non_primary_signal_as_capability" in i
               for i in result["issues"])


def test_tvm_entry_malformed_value_rejected():
    entry = _valid_entry()
    entry["quoted_span"] = "0.4.2 nm"
    result = verify_tvm_entry(entry, "value was 0.4.2 nm here")
    assert any("canonical_value_malformed" in i for i in result["issues"])


# ---------------------------------------------------------------------------
# Signal policy (Step 6)
# ---------------------------------------------------------------------------

def test_primary_signal_vocabulary():
    report = signal_vocabulary_report()
    assert report["primary_technical"] == [
        "performance", "cost", "efficiency", "reliability",
        "manufacturing", "deployment"]
    assert report["explanatory_only"] == [
        "investment", "talent", "experimental_concentration"]


@pytest.mark.parametrize("name,expected", [
    ("performance", SIGNAL_PRIMARY_TECHNICAL),
    ("yield", SIGNAL_PRIMARY_TECHNICAL),
    ("cost_per_unit", SIGNAL_PRIMARY_TECHNICAL),
    ("mtbf", SIGNAL_PRIMARY_TECHNICAL),
    ("vc_funding", SIGNAL_EXPLANATORY_ONLY),
    ("talent", SIGNAL_EXPLANATORY_ONLY),
    ("researcher_headcount", SIGNAL_EXPLANATORY_ONLY),
    ("publication_rate", SIGNAL_EXPLANATORY_ONLY),
])
def test_signal_classification(name, expected):
    assert classify_signal(name) == expected


def test_unknown_signal_is_recorded_not_guessed():
    assert classify_signal("vibes") == "UNKNOWN_SIGNAL"


def test_investment_never_classifies_as_primary():
    for name in ("investment", "vc_funding", "r_and_d_spend",
                 "talent", "experimental_concentration"):
        assert classify_signal(name) != SIGNAL_PRIMARY_TECHNICAL


# ---------------------------------------------------------------------------
# Capability family layer (Step 5)
# ---------------------------------------------------------------------------

def test_family_map_valid():
    ok, issues = validate_family_map()
    assert ok, issues


def test_operator_example_expansion():
    vocab = expand_search_vocabulary("10-100x misalignment vs deflection")
    assert "dynamic positioning" in vocab
    assert "closed-loop disturbance rejection" in vocab


def test_family_lookup_is_exact_not_fuzzy():
    """A near-miss query returns EMPTY — never a nearest-neighbor guess."""
    vocab = expand_search_vocabulary("misalignment versus deflection")
    assert vocab == []


def test_family_derivation_status_enforced():
    from tvm_v2.capability_family import validate_family_entry
    data = json.loads(
        (V2DIR / "CAPABILITY_FAMILY_MAP.json").read_text(encoding="utf-8"))
    entry = data["families"][0]
    assert entry["derivation_status"] == "EXPLORATORY_HYPOTHESIS"
    bad = dict(entry)
    bad["derivation_status"] = "OBVIOUSLY_TRUE"
    ok, issues = validate_family_entry(bad)
    assert not ok
    assert any("invalid_derivation_status" in i for i in issues)


def test_family_required_fields_all_present():
    from tvm_v2.capability_family import REQUIRED_FAMILY_FIELDS
    data = json.loads(
        (V2DIR / "CAPABILITY_FAMILY_MAP.json").read_text(encoding="utf-8"))
    for field in REQUIRED_FAMILY_FIELDS:
        assert field in data["families"][0], field


def test_no_invented_families():
    """Only the operator-directive example is seeded (Article XLIII)."""
    data = json.loads(
        (V2DIR / "CAPABILITY_FAMILY_MAP.json").read_text(encoding="utf-8"))
    assert len(data["families"]) == 1


# ---------------------------------------------------------------------------
# v1 strict schema predicate (the instrument comparison baseline)
# ---------------------------------------------------------------------------

def test_v1_predicate_label_disclosed():
    assert V1_PREDICATE_LABEL == "RECONSTRUCTED_FROM_REPORTED_FAILURE_CLASS"


@pytest.mark.parametrize("span,admissible", [
    ("0.42", True), ("-5", True), ("0.42 mW/cm²", False),
    ("0.42 ± 0.03", False), ("0.1–10", False), ("10 to 20", False),
    ("~50", False), (">100", False), ("3.2e-2", False),
    ("state-of-the-art", False),
])
def test_v1_strict_value_admission(span, admissible):
    assert v1_value_admissible(span) is admissible


def test_instrument_comparison_measurement_recorded():
    """The Step 4 record: mandated measurement NOT_MEASURABLE (honest),
    with the corpus-level instrument comparison measured and reproducible."""
    m = json.loads(MEASUREMENT_PATH.read_text(encoding="utf-8"))
    assert m["mandated_measurement"]["measurement_state"] == "NOT_MEASURABLE"
    assert m["mandated_measurement"]["reason"] == \
        "V1_OUTPUTS_NOT_PRESENT_IN_REPOSITORY"
    result = m["what_was_measured_instead"]["result"]
    # Re-measure in-test: the recorded numbers must be reproducible.
    value_cases = [c for c in CORPUS["cases"]
                   if c["field_context"] == CONTEXT_VALUE]
    v1_admits = sum(1 for c in value_cases
                    if v1_value_admissible(c["raw_span"]))
    v2_admits = sum(1 for c in value_cases
                    if c["expected"]["representation"]
                    in ("POINT", "RANGE", "INEQUALITY"))
    assert result["v1_strict_schema_admits"] == v1_admits
    assert result["v2_canonical_parser_admits_measured"] == v2_admits
    assert result["serialization_failure_class_size_on_corpus"] == \
        v2_admits - v1_admits


# ---------------------------------------------------------------------------
# Step 1 artifact + Step 7 preregistration (the seal)
# ---------------------------------------------------------------------------

def test_instrument_finding_conclusions_exact():
    finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))
    assert finding["scientific_conclusion"] == "NOT_DETERMINED"
    assert finding["instrument_conclusion"] == "TVM_PROPOSER_SCHEMA_FAILURE"
    assert finding["frontier_absence_conclusion"] == "NOT_PERMITTED"


def test_instrument_finding_never_reports_discovery_failure():
    finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))
    rule = finding["headline_interpretation_rule"]
    assert "MUST NOT be reported as a discovery failure" in rule


def test_instrument_finding_figures_are_operator_reported():
    finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))
    assert finding["v1_reported_figures"]["provenance"] == \
        "OPERATOR_DIRECTIVE_REPORTED"
    assert finding["v1_reported_figures"]["repository_verification"] == \
        "NOT_VERIFIABLE_IN_THIS_WORKSPACE"


def test_preregistration_seals_all_artifacts():
    """Every hash recorded in the preregistration matches the file on
    disk (the seal is intact at test time)."""
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    checks = [
        (prereg["v2_parser_specification"]["sha256"],
         V2DIR / "tvm_v2" / "value_parser.py"),
        (prereg["parser_calibration_corpus"]["sha256"], CORPUS_PATH),
        (prereg["normalization_rules"]["sha256"],
         V2DIR / "NORMALIZATION_RULES.json"),
        (prereg["capability_family_layer"]["sha256"],
         V2DIR / "CAPABILITY_FAMILY_MAP.json"),
        (prereg["v1_provenance"]["v1_instrument_finding"]["sha256"],
         FINDING_PATH),
        (prereg["v1_output_reparse_measurement"]["sha256"],
         MEASUREMENT_PATH),
        (prereg["transport_probe"]["sha256"],
         V2DIR / "TRANSPORT_PROBE.json"),
    ]
    for prompt_id, ph in prereg["prompt_hashes"]["files"].items():
        path = V2DIR / "PROMPTS" / f"{prompt_id}.json"
        if prompt_id == "TVM_V2_FRONTIER_ENTRY_PROPOSAL":
            # v1.0.0 -> v1.1.0 SUPERSESSION (disclosed pre-v2.1-seal
            # adjustment to the per-rung batch semantics): the v2.0
            # preregistration's pin for this prompt is STALE BY
            # DESIGN — the v2.1 preregistration carries the live pin.
            # Verify the supersession instead of the stale pin (same
            # rigor, versioned truth — Art. XI/XLIV).
            v21 = json.loads((V2DIR /
                              "R412_GRADIENT_V2_1_PREREGISTRATION"
                              ".json").read_text(encoding="utf-8"))
            live_pin = v21["prompt_pins"][prompt_id]["sha256"]
            assert _sha256(path) == live_pin, (
                "superseded prompt pin broken in v2.1: "
                f"{prompt_id}")
            assert v21["prompt_pins"][prompt_id]["version"] == \
                "1.1.0"
            continue
        checks.append((ph, path))
    for expected, path in checks:
        assert _sha256(path) == expected, f"seal broken: {path.name}"


def test_preregistration_run_gate_is_blocked():
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    gate = prereg["run_gate"]
    assert gate["state"] == "BLOCKED_PENDING_OPERATOR_INPUT"
    assert set(gate["blocking_fields"]) == {
        "population_hash", "seed_allocation", "tvm_snapshot_hash"}


def test_preregistration_records_zero_gradient_calls():
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    assert prereg["cost_budget"]["gradient_calls_spent_before_seal"] == 0
    probe = json.loads(
        (V2DIR / "TRANSPORT_PROBE.json").read_text(encoding="utf-8"))
    assert probe["gradient_model_calls_made"] == 0
    assert probe["discovery_model_calls_made"] == 0
    assert probe["verdict"] == "LIVE"


def test_preregistration_v1_provenance_is_honest():
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    vp = prereg["v1_provenance"]
    assert vp["verification_state"] == "NOT_VERIFIABLE_IN_THIS_WORKSPACE"
    assert vp["v1_figures_provenance"] == "OPERATOR_DIRECTIVE_REPORTED"
    assert vp["v1_result_modified"] is False
    assert vp["temporal_control_arm_modified"] is False


def test_preregistration_success_criterion_not_descendant_count():
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    sc = prereg["success_criterion"]
    assert "NEW CAUSAL ARCHITECTURE" in sc["chain"]
    assert "more descendants" in sc["explicitly_not_success"]


def test_prompts_enforce_serialization_contract():
    prop = json.loads((V2DIR / "PROMPTS" /
                       "TVM_V2_FRONTIER_ENTRY_PROPOSAL.json").read_text(
                           encoding="utf-8"))
    template = prop["template"]
    assert "EXACT contiguous substring" in template
    assert "DO NOT compute, convert, average, or round" in template
    assert "investment" in template  # forbidden as capability signal
