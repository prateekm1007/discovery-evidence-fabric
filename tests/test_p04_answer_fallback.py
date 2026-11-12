"""P0-4 (owner directive 2026-11-11, item 4): the normal path must not
silently activate the superseded answer construction (Art. IV: no
fallback epistemology; Art. LXIV: retire-superseded).

The ANSWER COMPOSER's record (ANSWER_COMPOSED.json) is the ONLY answer
authority on the normal path. When the composer produced no answer
(NO_ADMISSIBLE_CANDIDATES, SKIPPED_NO_PACKET, COMPOSE_FAILED_
TRANSPORT, no record at all), the normal path returns a TYPED
incomplete/no-answer state — it never falls through to the old
field-concatenation paths (INVENTION_SPECIFICATION.json /
candidate_envelope.json), which would release an answer that did not
pass the current composition contract.

The superseded construction remains reachable ONLY from the
explicitly selected no_COMPOSE ablation arm, where it is clearly
labelled DIAGNOSTIC (legacy_diagnostic=True).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import eval.run as er


def _mk_run(tmp_path: Path, composed: dict | None,
             legacy: bool = True) -> Path:
    d = tmp_path / "run"
    d.mkdir(parents=True)
    if composed is not None:
        (d / "ANSWER_COMPOSED.json").write_text(
            json.dumps(composed), encoding="utf-8")
    if legacy:
        (d / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
            {"mechanism": "LEGACY MECHANISM LINE",
             "causal_chain": "LEGACY CHAIN LINE",
             "killer_experiment": "LEGACY KILLER LINE"}),
            encoding="utf-8")
        (d / "candidate_envelope.json").write_text(json.dumps(
            {"attack_results": {"overall": "KILLED"},
             "mechanism_map": {"mechanism": "LEGACY ENVELOPE MECHANISM",
                               "intervention": "LEGACY ENVELOPE INTERVENTION"}}),
            encoding="utf-8")
    return d


def test_composed_answer_is_the_normal_path_answer(tmp_path):
    d = _mk_run(tmp_path, {"state": "COMPOSED_CONTRACT_VALID",
                           "answer": "COMPOSED ANSWER",
                           "contract": {"valid": True}})
    ans = er._extract_pipeline_answer(d)
    assert ans == "COMPOSED ANSWER"
    assert er._answer_source(d) == "composer_llm_call:COMPOSED_CONTRACT_VALID"


def test_contract_invalid_composition_never_delivered(tmp_path):
    # OWNER AUDIT ROUND 2026-11-12, DIRECTIVE 1 (Art. LXIV retire-
    # superseded): the "CONTRACT-INVALID COMPOSITION (...)" banner the
    # auditor saw shipped in 4 of 9 pairs is RETIRED — a composition
    # that fails its own deterministic checker is NEVER delivered, not
    # with a banner and not bare; the typed state rides the record and
    # the delivered answer is the typed no-answer.
    d = _mk_run(tmp_path, {"state": "COMPOSED_CONTRACT_INVALID",
                           "answer": "COMPOSED ANSWER",
                           "contract": {"violations": ["v1", "v2"]}})
    ans = er._extract_pipeline_answer(d)
    assert ans is None
    src = er._answer_source(d)
    assert src.startswith("typed_no_answer:COMPOSED_CONTRACT_INVALID"), src


def test_no_admission_is_typed_no_answer_never_legacy(tmp_path):
    # P0-4 core: the composer's NO_ADMISSIBLE_CANDIDATES state must not
    # fall through to the superseded construction (legacy artifacts are
    # present on disk and must stay unreachable on the normal path)
    d = _mk_run(tmp_path, {"state": "NO_ADMISSIBLE_CANDIDATES",
                           "answer": None})
    assert er._extract_pipeline_answer(d) is None
    assert er._answer_source(d) == "typed_no_answer:NO_ADMISSIBLE_CANDIDATES"


def test_composer_transport_failure_is_typed_never_legacy(tmp_path):
    # the confirmed defect: a composer transport failure used to fall
    # through to the superseded construction — it must now be a typed
    # incomplete/no-answer state
    d = _mk_run(tmp_path, {"state": "COMPOSE_FAILED_TRANSPORT",
                           "answer": None,
                           "error": "PROVIDER_UNAVAILABLE"})
    assert er._extract_pipeline_answer(d) is None
    assert er._answer_source(d) == "typed_no_answer:COMPOSE_FAILED_TRANSPORT"


def test_no_composer_record_is_typed_never_legacy(tmp_path):
    d = _mk_run(tmp_path, None)  # no ANSWER_COMPOSED.json at all
    assert er._extract_pipeline_answer(d) is None
    assert er._answer_source(d) == "composer_record_absent"


def test_skipped_no_packet_is_typed_no_answer(tmp_path):
    d = _mk_run(tmp_path, {"state": "SKIPPED_NO_PACKET", "answer": None})
    assert er._extract_pipeline_answer(d) is None
    assert er._answer_source(d) == "typed_no_answer:SKIPPED_NO_PACKET"


def test_disabled_composer_on_normal_path_stays_typed(tmp_path):
    # a DISABLED_BY_CONFIG composer record (COMPOSE ablation) is NOT
    # the normal path: it stays typed, and the superseded construction
    # must not be consulted without the explicit diagnostic flag
    d = _mk_run(tmp_path, {"state": "DISABLED_BY_CONFIG", "answer": None})
    assert er._extract_pipeline_answer(d) is None
    assert er._answer_source(d) == "typed_no_answer:DISABLED_BY_CONFIG"


def test_diagnostic_no_compose_arm_uses_labelled_legacy(tmp_path):
    # the explicitly selected no_COMPOSE arm: the superseded
    # construction runs, clearly labelled DIAGNOSTIC
    d = _mk_run(tmp_path, {"state": "DISABLED_BY_CONFIG", "answer": None})
    ans = er._extract_pipeline_answer(d, legacy_diagnostic=True)
    assert ans and "LEGACY" in ans
    src = er._answer_source(d, legacy_diagnostic=True)
    assert src.startswith("diagnostic_"), src


def test_diagnostic_killed_delivers_flagged_hypothesis(tmp_path):
    d = _mk_run(tmp_path, {"state": "DISABLED_BY_CONFIG", "answer": None})
    ans = er._extract_pipeline_answer(d, legacy_diagnostic=True)
    assert ans and "UNVERIFIED" in ans.upper()
    assert er._answer_source(d, legacy_diagnostic=True) == \
        "diagnostic_unverified_hypothesis_fallback"


def test_diagnostic_invention_spec_label(tmp_path):
    # the spec concatenation path (no envelope on disk -> no KILLED
    # overall -> no flagged hypothesis): the source label names the
    # superseded construction it actually used
    d = tmp_path / "run"
    d.mkdir(parents=True)
    (d / "ANSWER_COMPOSED.json").write_text(
        json.dumps({"state": "DISABLED_BY_CONFIG", "answer": None}),
        encoding="utf-8")
    (d / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        {"mechanism": "LEGACY MECHANISM LINE"}), encoding="utf-8")
    ans = er._extract_pipeline_answer(d, legacy_diagnostic=True)
    assert ans == "LEGACY MECHANISM LINE"
    assert er._answer_source(d, legacy_diagnostic=True) == \
        "diagnostic_superseded_field_concatenation_invention_spec"


def test_diagnostic_flag_never_releases_on_normal_path(tmp_path):
    # the flag is a caller contract: a normal-path call passes no flag
    # and receives no legacy construction regardless of what legacy
    # artifacts exist on disk
    d = _mk_run(tmp_path, {"state": "COMPOSE_FAILED_TRANSPORT",
                           "answer": None})
    assert er._extract_pipeline_answer(d) is None
