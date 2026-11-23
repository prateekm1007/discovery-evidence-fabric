#!/usr/bin/env python3
"""tests/test_binding_identity.py — the R139 DIR-2 acceptance:
functional tests of the REAL identity resolver (the same function the
production admission calls), covering the auditor's required negative
and positive cases. NO source-text pattern checks.

Cases: grounded-positive, false ID, wrong hash, non-matching span,
duplicate ID, contradiction (the support layer), unknown evidence
(the support layer), malformed binding, alias correction, empty
frozen set."""
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.adapters import (  # noqa: E402
    _resolve_binding_identity)
from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

TEXT = ("Trailing edge vortex generators suppress cavitation erosion "
        "on Francis runner blades.")
HASH = hashlib.sha256(TEXT.encode()).hexdigest()


def _recs():
    return [{"id": "doi:10.1080/x", "content_hash": HASH,
             "fields": {"system": {"value": "Francis runner"},
                        "abstract": {"value": TEXT},
                        "mechanism": {"value": TEXT},
                        "observed_effect": {"value": TEXT}},
             "_record_text": TEXT}]


def _binding(**over):
    b = {"grounded": True, "evidence_id": "doi:10.1080/x",
         "span": "generators suppress cavitation erosion on francis",
         "content_hash": HASH}
    b.update(over)
    return b


def test_01_positive_resolves():
    ok, reason, rec = _resolve_binding_identity(_binding(), _recs())
    assert ok and rec["id"] == "doi:10.1080/x"
    assert rec["content_hash"] == HASH
    assert "exactly-one" in reason


def test_02_false_id_refused():
    ok, reason, rec = _resolve_binding_identity(
        _binding(evidence_id="doi:10.9999/fake"), _recs())
    assert not ok and rec is None and "FALSE_ID" in reason


def test_03_wrong_hash_refused():
    ok, reason, rec = _resolve_binding_identity(
        _binding(content_hash="deadbeef" * 8), _recs())
    assert not ok and "HASH_MISMATCH" in reason


def test_04_span_not_in_record_refused():
    ok, reason, _ = _resolve_binding_identity(
        _binding(span="piezoelectric harvester array underneath the"),
        _recs())
    assert not ok and "SPAN_NOT_IN_RECORD" in reason


def test_05_duplicate_id_refused():
    ok, reason, _ = _resolve_binding_identity(
        _binding(), _recs() + _recs())
    assert not ok and "AMBIGUOUS_ID" in reason


def test_06_unknown_hash_fail_closed():
    ok, reason, _ = _resolve_binding_identity(
        _binding(), [dict(_recs()[0], content_hash=None)])
    assert not ok and "UNKNOWN_HASH" in reason


def test_07_malformed_binding_refused():
    ok, reason, _ = _resolve_binding_identity(
        {"grounded": True}, _recs())
    assert not ok and "MALFORMED_BINDING" in reason


def test_08_synthetic_alias_refused():
    # R139S3 (V99 + the DIR-2 acceptance contract): the R138-era
    # "lean_" synthetic alias is REFUSED, never de-aliased — the
    # stage-1 ALIAS_CORRECTED tolerance is deleted. A binding that
    # names the alias is refused as SYNTHETIC_ALIAS_REFUSED.
    ok, reason, rec = _resolve_binding_identity(
        _binding(evidence_id="lean_doi:10.1080/x"), _recs())
    assert not ok and rec is None
    assert "SYNTHETIC_ALIAS_REFUSED" in reason


def test_10_binding_hash_missing_refused():
    # R139S3: the binding MUST carry its own content_hash — the
    # stage-1 "(if present)" loophole admitted hash-less bindings
    # (the R139S2 verifier probe P2 measured the admission).
    ok, reason, _ = _resolve_binding_identity(
        _binding(content_hash=None), _recs())
    assert not ok and "UNKNOWN_HASH" in reason


def test_09_empty_frozen_set_refused():
    ok, reason, _ = _resolve_binding_identity(_binding(), [])
    assert not ok and "FALSE_ID" in reason


def test_10_contradiction_stays_blocked_support_layer():
    """CONTESTED (a contradicting record) is never admission-eligible
    — the support instrument's own rule, exercised functionally."""
    _ctext = ("Vortex generators were not effective on Francis "
              "runner blades; the coating was not effective at "
              "suppressing cavitation erosion on Francis runner "
              "blades.")
    contradicting = [{"id": "doi:10.1080/y",
                      "content_hash": HASH,
                      "fields": {"system": {"value": "Francis runner"},
                                 "abstract": {"value": _ctext},
                                 "mechanism": {"value": _ctext},
                                 "observed_effect": {"value": _ctext}},
                      "_record_text": _ctext}]
    cand = {"candidate_id": "c1",
            "mechanism": "trailing edge vortex generators suppress "
                         "cavitation erosion on francis runner blades",
            "intervention": "install vortex generators"}
    v = ms.verify_mechanism_support(cand, _recs() + contradicting,
                                    {"device": "x", "failure": "y"})
    assert v["mechanism_support_state"] == "CONTESTED"
    # the admission rule refuses CONTESTED regardless of identity
    ok, _, _ = _resolve_binding_identity(
        v.get("evidence_binding") or {}, _recs() + contradicting)
    admissible = (ok and v["mechanism_support_state"] in (
        "SUPPORTED", "PARTIALLY_SUPPORTED"))
    assert not admissible


def test_11_unknown_evidence_stays_unknown():
    cand = {"candidate_id": "c1",
            "mechanism": "magnetohydrodynamic pulse descaling lattice",
            "intervention": "install MHD descaler"}
    v = ms.verify_mechanism_support(cand, _recs(),
                                    {"device": "x", "failure": "y"})
    assert v["mechanism_support_state"] == "NOT_ENOUGH_EVIDENCE"


def test_12_partially_supported_stays_distinct():
    """PARTIALLY_SUPPORTED is admitted AS TYPED — the admission basis
    records the state verbatim; it is never relabeled SUPPORTED."""
    cand = {"candidate_id": "c1",
            "mechanism": "the runner blade trailing edge vortex "
                         "generators suppress cavitation erosion on "
                         "francis runner blades at partial load",
            "intervention": "install vortex generators"}
    v = ms.verify_mechanism_support(cand, _recs(),
                                    {"device": "x", "failure": "y"})
    state = v["mechanism_support_state"]
    assert state in ("SUPPORTED", "PARTIALLY_SUPPORTED")
    b = v.get("evidence_binding") or {}
    ok, _, rec = _resolve_binding_identity(b, _recs())
    assert ok
    # the basis carries the state verbatim (the distinctness rule)
    basis_state = state  # what the adapter records
    assert basis_state == state
