"""SOURCE COVERAGE MATURITY MODEL tests — hermetic, adversarial (Art. VIII/XVII/XXX).

The maturity model is the CEO's instrument for distinguishing role COVERAGE
from DEPTH. These tests attack it:
- completeness: every registered source graded on all 11 dimensions
- Art. XXV pin: UNMEASURED never numeric, never averaged as zero
- no-fabrication: absent measurement can never produce a 3
- monotonicity: LIVE > DEGRADED > UNAVAILABLE on LIVE_AVAILABILITY
- chain tamper detection (the grader's own custody re-verification)
- role-depth honesty: a role with live sources zeroed out must flip to GAP
- QUERY_RELEVANCE canary: UNMEASURED engine-wide until the per-source
  aggregation machinery actually exists (Art. XXXI — updating this test is
  a deliberate act, not a drift)
- determinism: same inputs -> identical grades
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import maturity
from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
from discovery_fabric.source_registry.roles import COVERAGE_MATRIX_ROLES


@pytest.fixture(scope="module")
def grades():
    return maturity.build_grades()


def test_all_eleven_dimensions_per_source(grades):
    assert maturity.DIMENSIONS and len(maturity.DIMENSIONS) == 11
    for sid, g in grades["sources"].items():
        for dim in maturity.DIMENSIONS:
            assert dim in g["dimensions"], f"{sid} missing {dim}"
        for dim, d in g["dimensions"].items():
            assert d["grade"] in (0, 1, 2, 3, "UNMEASURED"), (sid, dim, d)
            assert d["basis"] in ("MEASURED", "DECLARED", "MEASURED+DECLARED", "UNMEASURED")
            assert d.get("evidence") and d.get("rationale"), (sid, dim)


def test_every_registered_source_graded(grades):
    assert set(grades["sources"]) == set(SOURCE_REGISTRY)


def test_art_xxv_unmeasured_never_numeric_or_averaged():
    """A source with no measurement basis must never acquire numeric grades
    for the measured dimensions — the explicit unknown survives."""
    src = dict(SOURCE_REGISTRY["fda_maude"])
    graded = maturity.grade_source(src, health=None, log_stats={})
    d = graded["dimensions"]
    assert d["LIVE_AVAILABILITY"]["grade"] == "UNMEASURED"
    assert d["RECORD_VOLUME"]["grade"] == "UNMEASURED"
    assert d["ROLE_COVERAGE"]["grade"] == "UNMEASURED"
    # declared dimensions may still grade — they don't depend on measurement
    assert d["PRIMARY_SOURCE_AUTHORITY"]["grade"] == 3


def test_no_fabrication_without_measurement():
    """Absence of health + log can NEVER yield STRONG on a measured dim."""
    graded = maturity.grade_source(
        dict(SOURCE_REGISTRY["openalex"]), health=None, log_stats={})
    for dim in ("ROLE_COVERAGE", "LIVE_AVAILABILITY", "RECORD_VOLUME",
                "PROVENANCE_COMPLETENESS"):
        assert graded["dimensions"][dim]["grade"] != 3


def test_live_availability_monotonic():
    base = dict(SOURCE_REGISTRY["fda_510k"])
    def with_status(st):
        return maturity.grade_source(
            dict(base), health={"status": st, "chain": {}}, log_stats={})
    live = with_status("LIVE")["dimensions"]["LIVE_AVAILABILITY"]["grade"]
    deg = with_status("DEGRADED")["dimensions"]["LIVE_AVAILABILITY"]["grade"]
    una = with_status("UNAVAILABLE")["dimensions"]["LIVE_AVAILABILITY"]["grade"]
    nii = with_status("NOT_INTEGRATED")["dimensions"]["LIVE_AVAILABILITY"]["grade"]
    assert live > deg > una == nii == 0


def test_record_volume_bands_and_metered_note():
    src = dict(SOURCE_REGISTRY["fda_maude"])
    stats = {"fda_maude": {"entries": 10, "ok_entries": 10, "ok_records": 250,
                           "prov_fields": 10, "provenance_field_fraction": 1.0,
                           "last_success": "2026-08-29T00:00:00+00:00"}}
    graded = maturity.grade_source(
        src, health={"status": "LIVE", "chain": {"provenance_stores": True,
                                                 "retrieval_log_stores": True}},
        log_stats=stats)
    assert graded["dimensions"]["RECORD_VOLUME"]["grade"] == 3
    assert graded["dimensions"]["PROVENANCE_COMPLETENESS"]["grade"] == 3
    # metered source carries the policy-cap disclosure, volume stays numeric
    pb = dict(SOURCE_REGISTRY["patentbear"])
    pb_stats = {"patentbear": {"entries": 1, "ok_entries": 1, "ok_records": 5,
                               "prov_fields": 1, "provenance_field_fraction": 1.0,
                               "last_success": "2026-08-29T00:00:00+00:00",
                               "metered_note": "metered source"}}
    graded_pb = maturity.grade_source(
        pb, health={"status": "LIVE", "chain": {}}, log_stats=pb_stats)
    assert graded_pb["dimensions"]["RECORD_VOLUME"]["grade"] == 1
    assert graded_pb["dimensions"]["RECORD_VOLUME"]["note"] == "metered source"


def test_chain_tamper_detected():
    entries = maturity.load_retrieval_log()
    tampered = copy.deepcopy(entries)
    if tampered:
        tampered[0]["query"] = tampered[0].get("query", "") + " TAMPERED"
    audit = maturity.verify_log_chain(tampered)
    assert audit["chain_intact"] is False
    # and the real log verifies clean
    assert maturity.verify_log_chain(entries)["chain_intact"] is True


def test_role_depth_flips_to_gap_when_live_sources_removed(grades):
    """Attack the rollup: zero out a role's live sources; covered_binary and
    the label must both degrade — binary coverage must never stand on
    non-live sources."""
    g2 = copy.deepcopy(grades)
    role = "ADVERSE_EVENT"
    for sid in g2["role_depth"][role]["live_sources"]:
        g2["sources"][sid]["health_status"] = "UNAVAILABLE"
    rolled = maturity.rollup_roles(g2["sources"])
    assert rolled[role]["covered_binary"] is False
    assert rolled[role]["depth_label"] == "GAP_NO_LIVE_SOURCE"


def test_query_relevance_canary_unmeasured_engine_wide(grades):
    """Art. XXXI canary: QUERY_RELEVANCE is UNMEASURED for every source until
    per-source relevance aggregation is built AND this test is deliberately
    updated. Changing this test requires a machinery reference."""
    for sid, g in grades["sources"].items():
        assert g["dimensions"]["QUERY_RELEVANCE"]["grade"] == "UNMEASURED", sid
    assert grades["engine_level"]["QUERY_RELEVANCE"]["status"] == "UNMEASURED engine-wide"


def test_engine_findings_state_inconvenient_results(grades):
    """Art. XV: the engine-level findings must contain the negative
    statements — which failure domains ARE covered and which have ZERO
    live coverage (the list must never shrink to empty while gaps exist)."""
    finding = grades["engine_level"]["FAILURE_NEGATIVE_EVIDENCE"]["finding"]
    domains = grades["engine_level"]["FAILURE_NEGATIVE_EVIDENCE"]["failure_domains"]
    for d in domains:
        assert d in finding
    assert "ZERO live failure coverage" in finding
    # while any CEO-named domain is missing, it must be named as a gap
    for d in ("industrial", "energy", "aerospace", "electronics"):
        if d not in domains:
            assert d in finding
    dist = grades["engine_level"]["GEOGRAPHIC"]["live_source_distribution"]
    assert dist.get("SINGLE_JURISDICTION", 0) > 0
    assert "no live source" in grades["engine_level"]["GEOGRAPHIC"]["finding"]


def test_depth_mean_excludes_unmeasured(grades):
    for g in grades["sources"].values():
        numeric = [d["grade"] for d in g["dimensions"].values()
                   if isinstance(d.get("grade"), int)]
        if numeric:
            expected = round(sum(numeric) / len(numeric), 2)
            assert g["depth_mean"] == expected
        else:
            assert g["depth_mean"] == "UNMEASURED"


def test_grades_deterministic():
    a = maturity.build_grades()
    b = maturity.build_grades()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_all_thirteen_roles_rolled_up(grades):
    assert set(grades["role_depth"]) == set(COVERAGE_MATRIX_ROLES)
    for role, r in grades["role_depth"].items():
        if r["covered_binary"]:
            assert r["live_count"] >= 1
            assert isinstance(r["live_depth_mean"], (int, float)) or r["live_depth_mean"] == "UNMEASURED"
