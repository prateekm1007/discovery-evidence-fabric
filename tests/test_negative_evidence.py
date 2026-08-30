"""Negative-evidence architecture tests (hermetic).

Class discipline: deterministic from structured fields; NONE when fields
absent; every class carries its epistemic caps; COMPLETED_NO_RESULTS is
explicitly inference-from-absence and never failure-proof.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.negative_evidence import (
    NEGATIVE_EVIDENCE_CLASSES, build_negative_evidence_view,
    classify_negative_evidence,
)


def _rec(**kw):
    base = {"source_id": "test", "record_id": "test:1",
            "raw_payload_sha256": "sha", "normalized": {}}
    base.update(kw)
    return base


def test_maude_record_is_adverse_signal_with_caps():
    rec = _rec(source_id="fda_maude", role="ADVERSE_EVENT",
               limitations=["REPORT_COUNT_NOT_INCIDENCE"])
    cls = classify_negative_evidence(rec)
    assert cls["evidence_class"] == "ADVERSE_EVENT_SIGNAL"
    assert cls["failure_domain"] == "medical"
    assert "SIGNAL_NOT_INCIDENCE" in cls["limitations"]
    assert "CAUSALITY_UNVERIFIED" in cls["limitations"]


def test_nhtsa_recall_is_transport_domain():
    rec = _rec(source_id="nhtsa_recalls", role="RECALL",
               normalized={"nhtsa_campaign_number": "20V682000"})
    cls = classify_negative_evidence(rec)
    assert cls["evidence_class"] == "RECALL_EVENT"
    assert cls["failure_domain"] == "transport"
    assert any("ACKNOWLEDGED_DEFECT" in l for l in cls["limitations"])


def test_terminated_trial_carries_stop_reason():
    rec = _rec(source_id="clinicaltrials_gov",
               normalized={"overall_status": "TERMINATED",
                           "why_stopped": "Interim futility"})
    cls = classify_negative_evidence(rec)
    assert cls["evidence_class"] == "TERMINATED_TRIAL"
    assert cls["stop_reason"] == "Interim futility"
    assert any("NOT_PROOF" in l for l in cls["limitations"])


def test_withdrawn_and_suspended_are_negative():
    for status in ("WITHDRAWN", "SUSPENDED"):
        rec = _rec(source_id="clinicaltrials_gov",
                   normalized={"overall_status": status})
        assert classify_negative_evidence(rec)["evidence_class"] == \
            "TERMINATED_TRIAL"


def test_completed_no_results_requires_explicit_flag():
    # without the structured flag -> NONE (no guessing from absence)
    rec = _rec(source_id="clinicaltrials_gov",
               normalized={"overall_status": "COMPLETED"})
    assert classify_negative_evidence(rec)["evidence_class"] == "NONE"
    # with the explicit connector-provided flag -> SOFT class
    rec2 = _rec(source_id="clinicaltrials_gov",
                normalized={"overall_status": "COMPLETED",
                            "results_posted": False})
    cls = classify_negative_evidence(rec2)
    assert cls["evidence_class"] == "COMPLETED_NO_RESULTS"
    assert any("INFERENCE_FROM_ABSENCE" in l for l in cls["limitations"])


def test_plain_literature_is_not_negative_evidence():
    rec = _rec(source_id="pubmed", normalized={"doi": "10.1/x"})
    assert classify_negative_evidence(rec)["evidence_class"] == "NONE"


def test_view_aggregates_by_class_and_domain():
    view = build_negative_evidence_view([
        _rec(source_id="fda_maude", role="ADVERSE_EVENT"),
        _rec(source_id="fda_recall", role="RECALL",
             normalized={"recall_event_id": "R-1"}),
        _rec(source_id="nhtsa_recalls", role="RECALL",
             normalized={"nhtsa_campaign_number": "20V1"}),
        _rec(source_id="clinicaltrials_gov",
             normalized={"overall_status": "TERMINATED"}),
        _rec(source_id="pubmed", normalized={"doi": "10.1/x"}),
    ])
    assert view["negative_records"] == 4
    assert view["non_negative_records"] == 1
    assert view["by_class"] == {"ADVERSE_EVENT_SIGNAL": 1,
                                "RECALL_EVENT": 2,
                                "TERMINATED_TRIAL": 1}
    assert view["by_domain"] == {"medical": 3, "transport": 1}
    assert "never converted into incidence" in view["policy"]
