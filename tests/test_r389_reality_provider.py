"""R389 PHASE 2 adversarial tests — the reality boundary IS the product.

Constitution anchors exercised:
- Art. XXXVIII  providers (AI systems) can never yield MEASURED evidence;
               generated reconstructions never become PHYSICAL_VALIDATION.
- Art. IV      no fallback: invalid measured events are refused, not
               downgraded to a weaker origin.
- Art. XXI.3   provider failure (AUTH_FAILED/TIMEOUT/PROVIDER_ERROR) is
               never absence.
- Art. XVII    every control here has an attempted bypass (the add() hole
               was found by self-attack and closed — pinned by test).
- Art. XXV     unresolved comparisons stay UNRESOLVED, never zero-delta.
- Art. IX      tests redirect the R370G ledger to a sandbox; canonical
               state is never touched.

Live network is NOT required: all tests run against a FakeProvider and a
sandbox ledger. The real World Labs round-trip is an explicitly-opt-in
smoke (test_live_worldlabs_roundtrip) guarded by env RUN_LIVE_WORLD_LABS=1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.reality_provider import (  # noqa: E402
    EvidenceOrigin, RealityAsset, RealityDatum, RealityModel,
    RealityProvider, RealityRequest, WorldLabsProvider,
    ProviderCallLedger, build_design_world, build_reality_world,
    compare_design_to_reality, harvest_reality_model,
    validate_measured_event, REALITY_MODEL_FIELDS)


# ---------------------------------------------------------------------------
# A fake provider (deterministic, offline)
# ---------------------------------------------------------------------------

class FakeProvider(RealityProvider):
    """Canned transport — never touches the network."""

    KIND = "SPATIAL_RECONSTRUCTION"

    def __init__(self, wire=None, ledger=None):
        super().__init__(evidence_origin=EvidenceOrigin.RECONSTRUCTED,
                         ledger=ledger)
        # wire: {"submit": {...}, "poll": {...}, "fetch": [assets...]}
        self.wire = wire or {}

    def submit(self, request):
        out = dict(self.wire.get("submit") or
                   {"status": "IN_PROGRESS", "operation_id": "op_fake_1"})
        out["provider"] = self.name()
        return out

    def poll(self, operation_id):
        return dict(self.wire.get("poll") or
                    {"status": "SUCCEEDED", "operation_id": operation_id,
                     "world_id": "world_fake", "response": {"mesh": "ref"}})

    def fetch(self, operation_id):
        poll = self.wire.get("poll", {"status": "SUCCEEDED"})
        if poll.get("status") != "SUCCEEDED":
            self.ledger.record({
                "provider": self.name(), "call": "fetch",
                "operation_id": operation_id,
                "status": poll.get("status"),
                "reason": poll.get("reason", "not done")})
            return []
        return [self._asset("WORLD_MESH", operation_id,
                            {"world_id": "world_fake",
                             "response": {"mesh": "ref"}})]


def _valid_r370g_event(event_id="EVT_TEST_1",
                       source_type="EXTERNAL_INSTRUMENT"):
    return {
        "event_id": event_id,
        "event_type": "PHYSICAL_OBSERVATION",
        "package_id": "P-TEST",
        "source_type": source_type,
        "organization": "Test Org",
        "operator": "Test Operator",
        "acquisition_timestamp": "2026-09-01T00:00:00Z",
        "raw_artifact_ref": "test://raw",
        "raw_data_sha256": "0" * 64,
        "attestation": {"attestation_text": "I measured this.",
                        "attestation_hash": "a" * 64},
        "custody_chain": [{"step": 1, "actor": "Test Operator",
                            "timestamp": "2026-09-01T00:00:00Z",
                            "action": "acquired"}],
        "provenance_validated": True,
        "experiment_id": "EXP-1",
        "instrument_ids": ["INST-1"],
        "instrument_serials": ["SN-1"],
        "calibration_record": "CAL-1",
        "protocol_revision": "rev-1",
        "hardware_revision": "hw-1",
        "software_revision": "sw-1",
        "observations": [{"name": "lumen_diameter_mm", "value": 1.2}],
    }


@pytest.fixture()
def sandbox_ledger(tmp_path):
    """R370G ledger redirected to a sandbox (Art. IX)."""
    from discovery_fabric.engine.reality_provider import _r370g_validator
    r370g = _r370g_validator()
    path = tmp_path / "REALITY_EVENT_LEDGER.jsonl"
    original = r370g.REALITY_EVENT_LEDGER_PATH
    r370g.REALITY_EVENT_LEDGER_PATH = str(path)
    try:
        yield path
    finally:
        r370g.REALITY_EVENT_LEDGER_PATH = original


def _record_event(event, ledger_path):
    from discovery_fabric.engine.reality_provider import _r370g_validator
    r370g = _r370g_validator()
    original = r370g.REALITY_EVENT_LEDGER_PATH
    r370g.REALITY_EVENT_LEDGER_PATH = str(ledger_path)
    try:
        return r370g.record_reality_event(event)
    finally:
        r370g.REALITY_EVENT_LEDGER_PATH = original


# ===========================================================================
# 1. The boundary itself
# ===========================================================================

def test_provider_cannot_declare_measured():
    """Art. XXXVIII: providers are AI systems — MEASURED is unreachable."""
    with pytest.raises(ValueError, match="REALITY BOUNDARY VIOLATION"):
        RealityProvider(evidence_origin=EvidenceOrigin.MEASURED)


def test_worldlabs_default_origin_is_reconstructed():
    p = WorldLabsProvider(api_key="k" * 40)
    assert p.evidence_origin is EvidenceOrigin.RECONSTRUCTED
    assert p.KIND == "SPATIAL_RECONSTRUCTION"


def test_add_rejects_direct_measured_datum():
    """PINNED ADVERSARIAL HOLE (Art. XVII): direct add() of a MEASURED
    datum without R370G attestation must raise — found by self-attack,
    closed in reality_provider.py, pinned here forever."""
    m = RealityModel(package_id="P-TEST")
    with pytest.raises(ValueError, match="REALITY BOUNDARY VIOLATION"):
        m.add("dimensions", RealityDatum(
            name="x", value=1.0, origin=EvidenceOrigin.MEASURED))


def test_measured_requires_real_event(sandbox_ledger):
    """Art. IV: unknown event id -> refused, NOT downgraded to a weaker
    origin and NOT silently accepted."""
    m = RealityModel(package_id="P-TEST")
    res = m.add_measured("dimensions", "lumen_diameter_mm", 1.2,
                         "EVT_DOES_NOT_EXIST", ledger_path=sandbox_ledger)
    assert res["admitted"] is False
    assert m.origin_counts()["MEASURED"] == 0


def test_measured_admitted_with_attested_event(sandbox_ledger):
    _record_event(_valid_r370g_event(), sandbox_ledger)
    m = RealityModel(package_id="P-TEST")
    res = m.add_measured("dimensions", "lumen_diameter_mm", 1.2,
                         "EVT_TEST_1", ledger_path=sandbox_ledger)
    assert res["admitted"] is True, res
    assert m.origin_counts()["MEASURED"] == 1
    d = m.fields["dimensions"][0]
    assert d.origin is EvidenceOrigin.MEASURED
    assert d.source == "EVT_TEST_1"


def test_controlled_rehearsal_cannot_supply_measured(sandbox_ledger):
    """Art. XXXVII: rehearsal events are synthetic — never MEASURED data."""
    _record_event(_valid_r370g_event(
        event_id="EVT_REH", source_type="CONTROLLED_REHEARSAL"),
        sandbox_ledger)
    m = RealityModel(package_id="P-TEST")
    res = m.add_measured("dimensions", "lumen_diameter_mm", 1.2,
                         "EVT_REH", ledger_path=sandbox_ledger)
    assert res["admitted"] is False
    assert any("SYNTHETIC" in e for e in res["errors"])


def test_invalid_r370g_event_cannot_supply_measured(sandbox_ledger):
    """A present-but-invalid event (bad attestation) is also refused."""
    bad = _valid_r370g_event(event_id="EVT_BAD")
    bad["attestation"] = {}
    # record_reality_event validates before recording — it must refuse
    from discovery_fabric.engine.reality_provider import _r370g_validator
    r370g = _r370g_validator()
    original = r370g.REALITY_EVENT_LEDGER_PATH
    r370g.REALITY_EVENT_LEDGER_PATH = str(sandbox_ledger)
    try:
        with pytest.raises(ValueError):
            r370g.record_reality_event(bad)
    finally:
        r370g.REALITY_EVENT_LEDGER_PATH = original
    check = validate_measured_event("EVT_BAD",
                                    ledger_path=sandbox_ledger)
    assert check["valid"] is False


# ===========================================================================
# 2. Provider failure honesty (Art. XXI.3)
# ===========================================================================

class _FailingWire:
    pass


def test_auth_failure_is_not_absence():
    p = WorldLabsProvider(api_key="k" * 40)
    p._request = lambda method, path, body=None: (401, {"detail": "unauthorized"})
    res = p.submit(RealityRequest(prompt="test scene"))
    assert res["status"] == "AUTH_FAILED"
    assert "reason" in res
    # the ledger recorded the failure — distinguishable from absence
    assert p.ledger.entries[-1]["status"] == "AUTH_FAILED"


def test_timeout_is_not_absence():
    p = WorldLabsProvider(api_key="k" * 40)
    p._request = lambda method, path, body=None: (0, {"transport_error": "timeout"})
    res = p.submit(RealityRequest(prompt="test scene"))
    assert res["status"] == "TIMEOUT"


def test_no_key_is_auth_failed_not_empty():
    p = WorldLabsProvider(api_key=None)
    p.api_key = None  # simulate unconfigured key AFTER construction
    res = p.submit(RealityRequest(prompt="test scene"))
    assert res["status"] == "AUTH_FAILED"
    assert "no WORLD_LABS_API_KEY" in res["reason"]


def test_fetch_before_done_is_empty_with_ledger_reason():
    p = FakeProvider(wire={"poll": {"status": "IN_PROGRESS",
                                    "operation_id": "op_x"}})
    assets = p.fetch("op_x")
    assert assets == []
    assert p.ledger.entries[-1]["status"] == "IN_PROGRESS"


# ===========================================================================
# 3. REALITY_MODEL + provider assets
# ===========================================================================

def test_asset_origin_preserved_on_ingest():
    m = RealityModel(package_id="P-TEST")
    asset = RealityAsset(
        asset_id="WorldLabsProvider:op1:WORLD_MESH", kind="WORLD_MESH",
        origin=EvidenceOrigin.RECONSTRUCTED, provider="WorldLabsProvider",
        operation_id="op1", payload={"world_id": "w1"})
    res = m.add_from_asset(asset)
    assert res["admitted"] is True
    counts = m.origin_counts()
    assert counts["RECONSTRUCTED"] == 2  # observation + geometry
    assert counts["MEASURED"] == 0
    for f in ("observations", "geometry"):
        for d in m.fields[f]:
            assert d.origin is EvidenceOrigin.RECONSTRUCTED
            assert "not" in (d.note or d.uncertainty or "").lower() or \
                "hypothesis" in (d.note or "").lower()


def test_reality_model_has_the_ten_ceo_fields():
    assert set(REALITY_MODEL_FIELDS) == {
        "geometry", "dimensions", "materials", "interfaces",
        "operating_conditions", "observations", "measurements",
        "uncertainties", "failure_modes", "provenance"}


def test_harvest_into_reality_model(tmp_path):
    ledger = ProviderCallLedger(tmp_path / "ledger.json")
    p = FakeProvider(ledger=ledger)
    model, status = harvest_reality_model(p, "op_fake_1", package_id="P-TEST")
    assert status["assets"] == 1
    assert status["origin"] == "RECONSTRUCTED"
    assert model.origin_counts()["RECONSTRUCTED"] == 2
    assert model.origin_counts()["MEASURED"] == 0
    # ledger provenance: the fetch is recorded with hashes (Art. VI)
    assert ledger.entries[-1]["asset_sha256"]


def test_unknown_field_rejected():
    m = RealityModel()
    with pytest.raises(KeyError):
        m.add("not_a_field", RealityDatum(
            name="x", value=1, origin=EvidenceOrigin.COMPUTATIONAL))


# ===========================================================================
# 4. DESIGN_WORLD / REALITY_WORLD / COMPARISON
# ===========================================================================

def _spec():
    return {
        "problem_id": "p_test",
        "engineering_specification": {
            "parameters": [
                {"name": "lumen_diameter_mm", "value": 1.0, "unit": "mm",
                 "epistemic_class": "MODEL_DERIVED"},
                {"name": "wall_thickness_mm", "value": 0.1, "unit": "mm",
                 "epistemic_class": "MODEL_DERIVED"},
            ],
            "materials": [{"name": "silicone", "spec": "medical grade",
                           "epistemic_class": "MODEL_DERIVED"}],
            "operating_conditions": {"pressure_mmhg": 10},
        },
    }


def test_design_world_is_authoritative_and_unpromoted():
    dw = build_design_world(_spec())
    assert dw["artifact"] == "DESIGN_WORLD"
    assert dw["authoritative"] is True
    names = {d["name"] for d in dw["dimensions"]}
    assert names == {"lumen_diameter_mm", "wall_thickness_mm"}
    for d in dw["dimensions"]:
        assert d["epistemic_class"] == "MODEL_DERIVED"  # never promoted


def test_reality_world_separates_origins(sandbox_ledger):
    _record_event(_valid_r370g_event(), sandbox_ledger)
    m = RealityModel(package_id="P-TEST")
    m.add_measured("dimensions", "lumen_diameter_mm", 1.2,
                   "EVT_TEST_1", ledger_path=sandbox_ledger)
    m.add_from_asset(RealityAsset(
        asset_id="p:op:WORLD_MESH", kind="WORLD_MESH",
        origin=EvidenceOrigin.RECONSTRUCTED, provider="p",
        operation_id="op", payload={}))
    rw = build_reality_world(m)
    assert rw["artifact"] == "REALITY_WORLD"
    assert rw["authoritative"] is False
    assert rw["measured_count"] == 1
    assert rw["reconstructed_count"] == 2


def test_comparison_reconstructed_is_hypothesis_grade():
    dw = build_design_world(_spec())
    m = RealityModel(package_id="P-TEST")
    m.add("dimensions", RealityDatum(
        name="lumen_diameter_mm", value=1.4,
        origin=EvidenceOrigin.RECONSTRUCTED,
        uncertainty="provider reconstruction"))
    cmp = compare_design_to_reality(dw, build_reality_world(m))
    rec = [r for r in cmp["records"] if r["name"] == "lumen_diameter_mm"][0]
    assert rec["status"] == "COMPARED"
    assert rec["grade"] == "HYPOTHESIS_GRADE"
    assert rec["origin"] == "RECONSTRUCTED"
    assert rec["technical_state_update"]["auto_applied"] is False
    assert rec["mutation"]["auto_applied"] is False
    # the discrepancy is flagged, not buried
    assert rec["within_uncertainty"] is False  # 1.0 vs 1.4 = 40% delta


def test_comparison_measured_is_evidence_grade_but_still_proposal(
        sandbox_ledger):
    dw = build_design_world(_spec())
    _record_event(_valid_r370g_event(), sandbox_ledger)
    m = RealityModel(package_id="P-TEST")
    m.add_measured("dimensions", "lumen_diameter_mm", 1.0,
                   "EVT_TEST_1", ledger_path=sandbox_ledger)
    cmp = compare_design_to_reality(dw, build_reality_world(m))
    rec = [r for r in cmp["records"] if r["name"] == "lumen_diameter_mm"][0]
    assert rec["grade"] == "EVIDENCE_GRADE"
    assert rec["within_uncertainty"] is True
    # measured evidence still routes through validators — never auto-applied
    assert rec["technical_state_update"]["auto_applied"] is False


def test_comparison_unresolved_stays_unknown():
    dw = build_design_world(_spec())
    cmp = compare_design_to_reality(dw, build_reality_world(
        RealityModel(package_id="P-TEST")))
    rec = [r for r in cmp["records"]
           if r["name"] == "wall_thickness_mm"][0]
    assert rec["status"] == "UNRESOLVED"
    assert rec["delta"] is None
    assert "NOT evidence" in rec["hypothesis"]  # Art. XXV wording pinned


def test_comparison_never_emits_physical_validation():
    """Art. XXXVIII structural absence: no record may carry a physical-
    validation state. (The top-level `emits` note explains the boundary in
    prose — records/summary/states are what downstream code would read.)"""
    dw = build_design_world(_spec())
    m = RealityModel(package_id="P-TEST")
    m.add("dimensions", RealityDatum(
        name="lumen_diameter_mm", value=1.0,
        origin=EvidenceOrigin.RECONSTRUCTED))
    m.add("measurements", RealityDatum(
        name="lumen_diameter_mm", value=1.0,
        origin=EvidenceOrigin.COMPUTATIONAL))
    cmp = compare_design_to_reality(dw, build_reality_world(m))
    for rec in cmp["records"]:
        blob = json.dumps(rec)
        assert "PHYSICAL_VALIDATION" not in blob
        assert "PHYSICALLY_VALIDATED" not in blob
        assert "validated" not in blob.lower().replace(
            "unvalidated", "")
        # a record either carries no mutation proposal (UNRESOLVED) or an
        # explicitly non-applied one
        assert rec.get("mutation", {}).get("auto_applied", False) is False
    assert cmp["loop_verification_state"] == "UNTOUCHED"
    assert cmp["summary"]["dimensions_compared"] >= 1


def test_comparison_summary_counts():
    dw = build_design_world(_spec())
    m = RealityModel(package_id="P-TEST")
    m.add("dimensions", RealityDatum(
        name="lumen_diameter_mm", value=1.05,
        origin=EvidenceOrigin.RECONSTRUCTED))
    cmp = compare_design_to_reality(dw, build_reality_world(m))
    assert cmp["summary"]["dimensions_compared"] == 1
    assert cmp["summary"]["dimensions_unresolved"] == 1
    assert cmp["summary"]["reconstructed_comparisons"] == 1


# ===========================================================================
# 5. Secret hygiene + live smoke (opt-in)
# ===========================================================================

def test_no_secret_material_in_payloads_or_ledger(tmp_path):
    SECRET = "SUPERSECRETKEYVALUE123"
    ledger = ProviderCallLedger(tmp_path / "ledger.json")
    p = WorldLabsProvider(api_key=SECRET, ledger=ledger)
    res = p.submit(RealityRequest(prompt="test"))
    model, _ = harvest_reality_model(p, res.get("operation_id", "op"))
    blob = json.dumps(model.to_dict()) + json.dumps(ledger.entries) + \
        json.dumps(res)
    assert SECRET not in blob


@pytest.mark.skipif(
    not (Path(REPO / ".env.keys").exists() or
         __import__("os").environ.get("WORLD_LABS_API_KEY")),
    reason="no World Labs key available")
def test_live_worldlabs_roundtrip():
    """EXPLICIT opt-in live smoke (RUN_LIVE_WORLD_LABS=1): one real
    text-to-world request, honest statuses, RECONSTRUCTED origin. This test
    NEVER asserts the world is physically real — only that the transport
    works and the boundary labels survive the real wire."""
    import os
    if os.environ.get("RUN_LIVE_WORLD_LABS") != "1":
        pytest.skip("set RUN_LIVE_WORLD_LABS=1 to run the live smoke")
    p = WorldLabsProvider()
    res = p.submit(RealityRequest(
        prompt="A mystical forest with glowing mushrooms",
        display_name="R389 API verification"))
    assert res["status"] in ("IN_PROGRESS", "SUCCEEDED"), res
    op = res["operation_id"]
    status = p.poll(op)
    assert status["status"] in ("IN_PROGRESS", "SUCCEEDED")
    # generation takes minutes: we do NOT block for completion here —
    # the operation id is recorded in the ledger for later harvest.
    assert p.ledger.for_operation(op)
