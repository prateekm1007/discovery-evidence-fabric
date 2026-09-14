"""tests/test_r452_discovery_engineering_organ.py — R452: the discovery→engineering organ.

Constitution v2.5.0 Article XVI (as amended): tests must exercise CANONICAL
PRODUCERS and REAL CONSUMERS. This battery is the producer-to-consumer
CONTRACT TEST for the chain the external audit found uncovered:

    producer (engineering_spec.py — real committed output of the real
              production run R444/SMOKE, NOT a hand-written fixture)
      -> VALUE SOURCING  (evidence/problem -> typed parameter values)
      -> PARAMETER JOIN  (typed values -> engineering_spec.parameters[])
      -> classifier.classify (the production consumer of the spec)
      -> engineering_geometry.normalize_parameters (the normalizer)
      -> FORM_LIBRARY builder (the builder, under the OCP memory guard)

The red state this battery pins first: the REAL producer output, as
committed, classifies BELOW ENGINEERING_3D (zero numeric geometry
parameters — the audit's finding). The green state: after the organ runs,
the SAME real producer output classifies ENGINEERING_3D with every value
typed per Article LXXIV (no naked numbers).

Negative/metamorphic controls (Art. XVII):
  - a naked number (no class/provenance) is BLOCKED, not admitted
  - a MODELLED value tampered to claim SOURCE_FACT is rejected (class
    masquerade detection — Art. XXVIII)
  - UNKNOWN residuals carry the Article LXXV next-action record
  - SOURCE_FACT custody re-verifies against the evidence corpus itself
    (Art. III: the verifier never trusts the claimant)
  - unit conversion is explicit and recorded (Art. XXVII)
  - the OCP memory guard returns a TYPED failure under a starvation limit
    (Art. LXI: infrastructure failure is never a silent success)
  - capability tier claims above the measured tier are blocked (Art. LXXI)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SMOKE_DIR = REPO_ROOT / "R444" / "SMOKE"
SPEC_PATH = SMOKE_DIR / "ENGINEERING_SPECIFICATION.json"
FREEZE_PATH = SMOKE_DIR / "envelope_FREEZE.json"
PROBLEM_PATH = SMOKE_DIR / "problem.json"


# ---------------------------------------------------------------------------
# Fixtures: the REAL producer output (committed production-run artifacts)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


@pytest.fixture(scope="module")
def real_evidence() -> list:
    freeze = json.loads(FREEZE_PATH.read_text())
    return freeze.get("evidence") or []


@pytest.fixture(scope="module")
def real_problem() -> dict:
    return json.loads(PROBLEM_PATH.read_text())


# ---------------------------------------------------------------------------
# 1. The RED state: the real producer output, as committed, cannot reach
#    ENGINEERING_3D. This is the audit finding, pinned as a contract.
# ---------------------------------------------------------------------------

class TestRedStatePinned:
    def test_real_producer_output_has_no_numeric_geometry_parameters(
            self, real_spec):
        from discovery_fabric.engine.invention_bridge import classifier
        geo = classifier._geometry_parameters(real_spec)
        assert geo == [], (
            "if the real producer already emits numeric geometry "
            "parameters, this battery's premise is stale — update the "
            "fixture run, do not delete the test (Art. XI)")

    def test_red_classification_is_below_engineering(self, real_spec,
                                                     real_problem):
        from discovery_fabric.engine.invention_bridge import classifier
        run_result = {"engineering_specification": real_spec,
                      "final_state": {"device": real_problem.get("device"),
                                      "causal_chain": {}},
                      "problem": real_problem}
        vis = classifier.classify(run_result, {})
        assert vis["visualizability_class"] != "ENGINEERING_3D"


# ---------------------------------------------------------------------------
# 2. VALUE SOURCING (Art. LXXIV): evidence + problem -> typed values
# ---------------------------------------------------------------------------

class TestValueSourcing:
    def test_extracts_typed_facts_with_custody(self, real_evidence):
        from discovery_fabric.engine import value_sourcing as vs
        facts = vs.extract_quantitative_facts(real_evidence)
        assert isinstance(facts, list)
        for f in facts:
            # every fact carries full custody (Art. XII chain)
            assert f["value"] > 0 or f["value"] == 0
            assert f["unit"]
            assert f["unit_family"] in vs.UNIT_FAMILIES
            assert f["span"]
            assert f["source_id"]
            assert f["content_hash"]
            assert f["source_kind"] == "EVIDENCE"

    def test_problem_statement_is_a_sourced_record(self, real_problem):
        from discovery_fabric.engine import value_sourcing as vs
        facts = vs.extract_quantitative_facts(
            [vs.problem_as_record(real_problem)])
        assert facts, "the problem's own declared constraints must be " \
                      "extractable as sourced facts (buyer-declared " \
                      "requirements are legitimate provenance)"
        assert all(f["source_kind"] == "PROBLEM_STATEMENT" for f in facts)

    def test_sourcing_record_shape(self, real_spec, real_evidence,
                                   real_problem):
        from discovery_fabric.engine import value_sourcing as vs
        rec = vs.source_parameters(real_spec, real_evidence,
                                   problem=real_problem)
        assert rec["organ"] == "VALUE_SOURCING"
        assert rec["value_class_counts"].keys() >= {"SOURCE_FACT",
                                                     "MODELLED", "UNKNOWN"}
        params = rec["parameters"]
        assert params, "the organ must produce parameter records"
        for p in params:
            cls = p["value_class"]
            assert cls in ("SOURCE_FACT", "COMPUTED", "MODELLED", "UNKNOWN")
            if cls in ("SOURCE_FACT", "COMPUTED", "MODELLED"):
                # no naked numbers (Art. LXXIV): class + provenance + unit
                assert isinstance(p["value"], (int, float))
                assert p["unit"]
                assert p["provenance"], (
                    f"parameter {p.get('param_id')} carries a value with "
                    "empty provenance — that is a naked number")
                if cls == "SOURCE_FACT":
                    assert p["provenance"]["source_id"]
                    assert p["provenance"]["span"]
                    assert p["provenance"]["content_hash"]
                if cls == "MODELLED":
                    env = p["envelope"]
                    assert env and len(env) == 2
                    assert env[0] <= p["value"] <= env[1]
                    assert p["provenance"]["envelope_basis"]
            if cls == "UNKNOWN":
                # Art. LXXV: unknown must be actionable
                na = p["next_action"]
                assert na and na.get("candidate_action") \
                    and na.get("what_would_resolve_it")

    def test_source_fact_custody_reverifies(self, real_spec, real_evidence,
                                            real_problem):
        """Art. III: independently re-verify each SOURCE_FACT span against
        the evidence corpus — the claimant's binding is not trusted.

        Part 1 (real corpus): every SOURCE_FACT the organ emitted from the
        REAL producer corpus re-verifies against that corpus (count may be
        honestly zero for a corpus with no relevant quantitative spans —
        the smoke corpus is such a case; MODELLED envelopes then carry the
        geometry, honestly labeled).

        Part 2 (controlled custody mechanics, Art. VIII adversarial
        input): a corpus record that DOES carry relevant dimensions must
        produce SOURCE_FACT bindings whose spans re-verify — and a
        tampered span must NOT be verifiable."""
        from discovery_fabric.engine import value_sourcing as vs
        rec = vs.source_parameters(real_spec, real_evidence,
                                   problem=real_problem)
        problem_text = json.dumps(real_problem)
        evidence_text = [((e.get("title") or "") + " " +
                          (e.get("abstract") or ""))
                         for e in real_evidence]
        for p in rec["parameters"]:
            if p["value_class"] != "SOURCE_FACT":
                continue
            span = p["provenance"]["span"]
            found = (span in problem_text
                     or any(span in t for t in evidence_text))
            assert found, (
                f"SOURCE_FACT span {span!r} not present in any corpus "
                "record — the binding is fabricated (Art. VI)")

        # Part 2: controlled record with buyer-declared dimensions
        problem_with_dims = {
            "problem_id": "custody-probe",
            "device": "compact wearable dialysis pump",
            "failure": "occlusion alarms fail because the pump head is "
                       "too bulky for the wearable chassis",
            "failure_mode": "occlusion",
            "constraint": "pump head must fit within 120 mm length and "
                          "60 mm width with a 15 mm thick base plate",
        }
        rec2 = vs.source_parameters(real_spec, [], problem=problem_with_dims)
        ptext = json.dumps(problem_with_dims)
        # geometry dims bind (the evidence→dimension organ): length /
        # width / thickness slots from the buyer-declared constraints
        geo = rec2["geometry_bindings"]
        assert geo, ("buyer-declared length dimensions must bind onto "
                     "geometry slots (the evidence→dimension organ)")
        for slot, b in geo.items():
            span = b["provenance"]["span"]
            assert span in ptext, (
                f"controlled custody: slot {slot} span {span!r} must "
                "re-verify verbatim against the problem text")
            # a tampered span must NOT verify (metamorphic control)
            tampered = span + "0"
            assert tampered not in ptext

    def test_unit_conversion_is_recorded(self):
        from discovery_fabric.engine import value_sourcing as vs
        facts = vs.extract_quantitative_facts([{
            "id": "test:cm-record", "source_id": "test:cm-record",
            "source_type": "scientific_paper", "title":
                "A 2.5 cm thick cold plate with 30 mm channels",
            "abstract": "", "content_hash": "0" * 64,
        }])
        conv = [f for f in facts if f["canonical_unit"] == "mm"]
        assert conv, "cm spans must normalize to the mm canonical unit"
        cm_fact = next(f for f in facts if f["unit"] == "cm")
        assert cm_fact["conversion"] is not None
        assert cm_fact["conversion"]["factor"] == 10.0
        assert cm_fact["canonical_value"] == pytest.approx(25.0)

    def test_naked_number_is_blocked(self):
        from discovery_fabric.engine import parameter_join as pj
        naked = {"param_id": "X-001", "unit": "mm", "value": 42.0,
                 "value_class": None, "provenance": None}
        with pytest.raises(Exception):
            pj.validate_typed_parameter(naked)

    def test_modelled_masquerading_as_source_fact_is_rejected(self):
        from discovery_fabric.engine import parameter_join as pj
        masquerade = {
            "param_id": "X-002", "unit": "mm", "value": 12.0,
            "value_class": "SOURCE_FACT",
            "provenance": {"envelope_basis": "form-library default"},
            "envelope": [10.0, 20.0],
        }
        with pytest.raises(Exception):
            pj.validate_typed_parameter(masquerade)


# ---------------------------------------------------------------------------
# 3. PARAMETER JOIN: typed values -> the spec the classifier consumes
# ---------------------------------------------------------------------------

class TestParameterJoin:
    def test_join_produces_classifier_readable_parameters(
            self, real_spec, real_evidence, real_problem):
        from discovery_fabric.engine import value_sourcing as vs
        from discovery_fabric.engine import parameter_join as pj
        rec = vs.source_parameters(real_spec, real_evidence,
                                   problem=real_problem)
        joined = pj.join_parameters(real_spec, rec, run_result={
            "final_state": {"device": real_problem.get("device")},
            "problem": real_problem})
        spec = joined["spec"]
        # the classifier's contract: engineering_spec.parameters[]
        params = spec.get("parameters") or []
        assert len(params) >= 3, (
            "the join must fill at least ENGINEERING_MIN_PARAMS "
            "parameters for the parametric build")
        mm = [p for p in params
              if pj.is_length_unit(p.get("unit") or "")]
        assert len(mm) >= 3, (
            "at least 3 mm-family (geometry-driving) parameters are "
            "required for ENGINEERING_3D")
        # join report honesty
        jr = joined["join_report"]
        assert jr["value_class_counts"]["MODELLED"] >= 0
        assert jr["joined_parameter_count"] == len(params)
        # physical site validation (the R452 PHYSICAL SITE step)
        ps = joined["physical_site"]
        assert ps["intervention_site"] is not None
        assert isinstance(ps["physical_site_detected"], bool)
        assert isinstance(ps["length_family_parameters"], int)
        assert ps["form"] in (
            "layered_panel", "dual_lumen_catheter", "cylindrical_device")

    def test_green_classification_is_engineering_3d(
            self, real_spec, real_evidence, real_problem):
        from discovery_fabric.engine import value_sourcing as vs
        from discovery_fabric.engine import parameter_join as pj
        from discovery_fabric.engine.invention_bridge import classifier
        rec = vs.source_parameters(real_spec, real_evidence,
                                   problem=real_problem)
        joined = pj.join_parameters(real_spec, rec, run_result={
            "final_state": {"device": real_problem.get("device")},
            "problem": real_problem})
        run_result = {"engineering_specification": joined["spec"],
                      "final_state": {
                          "device": real_problem.get("device"),
                          "causal_chain": {}},
                      "problem": real_problem}
        vis = classifier.classify(run_result, {})
        assert vis["visualizability_class"] == "ENGINEERING_3D", (
            f"joined spec classified {vis['visualizability_class']} — "
            "the organ failed to open the engineering path")

    def test_join_does_not_mutate_the_producer_spec(self, real_spec,
                                                    real_evidence,
                                                    real_problem):
        from discovery_fabric.engine import value_sourcing as vs
        from discovery_fabric.engine import parameter_join as pj
        before = json.dumps(real_spec, sort_keys=True)
        rec = vs.source_parameters(real_spec, real_evidence,
                                   problem=real_problem)
        pj.join_parameters(real_spec, rec, run_result={})
        assert json.dumps(real_spec, sort_keys=True) == before, (
            "the producer's committed artifact must not be mutated in "
            "place (Art. IX: observational)")


# ---------------------------------------------------------------------------
# 4. NORMALIZER -> BUILDER (under the OCP memory guard)
# ---------------------------------------------------------------------------

class TestBuilderUnderGuard:
    def test_normalize_and_build_through_the_real_chain(
            self, real_spec, real_evidence, real_problem, tmp_path):
        from discovery_fabric.engine import value_sourcing as vs
        from discovery_fabric.engine import parameter_join as pj
        from discovery_fabric.engine.invention_bridge import (
            classifier, engineering_geometry, ocp_guard)
        rec = vs.source_parameters(real_spec, real_evidence,
                                   problem=real_problem)
        joined = pj.join_parameters(real_spec, rec, run_result={
            "final_state": {"device": real_problem.get("device")},
            "problem": real_problem})
        run_result = {"engineering_specification": joined["spec"],
                      "final_state": {
                          "device": real_problem.get("device"),
                          "causal_chain": {}},
                      "problem": real_problem}
        vis = classifier.classify(run_result, {})
        normalized = engineering_geometry.normalize_parameters(
            vis["geometry_parameters"])
        assert len(normalized["build_params"]) >= 3
        form = engineering_geometry.route_form(
            vis.get("intervention_site", ""),
            vis.get("subsystems") or [])
        assert form in engineering_geometry.FORM_LIBRARY

        out_dir = tmp_path / "MODEL"
        out_dir.mkdir()

        # the PRODUCTION guarded path (spawned subprocess — fork was
        # measured unsafe after parent OCCT builds; see ocp_guard)
        guard = ocp_guard.run_guarded_build(
            form, normalized["build_params"], str(out_dir))
        assert guard["status"] == "OK", guard
        exported = guard["result"]["exported"]
        assert Path(exported["step_path"]).is_file()
        assert Path(exported["stl_path"]).is_file()
        assert Path(exported["glb_path"]).stat().st_size > 0
        assert guard["result"]["key_dimensions"]["volume_mm3"] > 0

    def test_guard_returns_typed_failure_under_starvation(self, tmp_path):
        from discovery_fabric.engine.invention_bridge import ocp_guard

        def explosive():
            _ = bytearray(1024 * 1024 * 1024)  # 1 GB allocation
            return {"made": True}

        guard = ocp_guard.run_guarded(explosive, memory_limit_mb=64,
                                      timeout_s=30)
        assert guard["status"] in ("OOM_KILLED", "ERROR", "TIMEOUT")
        assert guard["status"] != "OK"
        assert guard.get("memory_limit_mb") == 64
        assert guard.get("guard_basis"), \
            "the typed failure must record its basis (Art. LXI)"


# ---------------------------------------------------------------------------
# 5. CAPABILITY / SCIENCE SEPARATION (Art. LXXI)
# ---------------------------------------------------------------------------

class TestCapabilityTier:
    def test_tier_order_and_measurement(self):
        from discovery_fabric.engine import capability_tier as ct
        assert ct.TIER_ORDER[0] == "TIER_1_TRANSPORT_ONLY"
        assert ct.TIER_ORDER[-1] == "TIER_6_EXPERIMENT_REALITY_LOOP"
        rec = ct.measure_capability_tier(
            model_id="test-model", provider="test-provider",
            probe_results={"evidence_citation": True,
                           "causal_chain_completion": True,
                           "attack_execution": False,
                           "parameterized_engineering_synthesis": False,
                           "closed_loop_learning": False})
        assert rec["tier"] == "TIER_3_REASONING_CAPABLE"
        assert rec["basis"]["probes_run"] == 5
        assert rec["model_provenance"]["model_id"] == "test-model"

    def test_claim_above_measured_tier_is_blocked(self):
        from discovery_fabric.engine import capability_tier as ct
        verdict = ct.evaluate_capability_claim(
            measured_tier="TIER_2_EVIDENCE_CAPABLE",
            claim="adversarial attack execution")
        assert verdict["allowed"] is False
        assert verdict["violation"] == "CAPABILITY_EXCEEDS_MEASURED_TIER"
        verdict2 = ct.evaluate_capability_claim(
            measured_tier="TIER_4_ADVERSARIAL_SCIENTIFIC",
            claim="adversarial attack execution")
        assert verdict2["allowed"] is True

    def test_capability_identity_tuple_carries_model_provenance(self):
        from discovery_fabric.engine import capability_tier as ct
        tup = ct.capability_identity(
            model_id="Qwen/Qwen3-14B", model_revision="abc123",
            provider="hf-inference", constitution_version="2.5.0")
        assert tup["model_id"] == "Qwen/Qwen3-14B"
        assert tup["model_revision"] == "abc123"
        assert tup["constitution_version"] == "2.5.0"
        assert tup["capability_tier"] in ct.TIER_ORDER


# ---------------------------------------------------------------------------
# 6. The bridge hook: ensure_sourced_parameters wires the organ into the
#    production bridge path (idempotent, persists the record, no-ops when
#    the released chain already provides parameters).
# ---------------------------------------------------------------------------

class TestBridgeHook:
    def test_hook_persists_record_and_enriches_run_result(
            self, real_spec, real_evidence, real_problem, tmp_path):
        from discovery_fabric.engine import value_sourcing as vs
        run_result = {"engineering_specification": json.loads(
            SPEC_PATH.read_text()),
            "evidence": real_evidence,
            "final_state": {"device": real_problem.get("device"),
                            "causal_chain": {}},
            "problem": real_problem}
        enriched, record = vs.ensure_sourced_parameters(
            run_result, work_dir=str(tmp_path))
        assert record is not None
        assert record["status"] == "SOURCED"
        persisted = tmp_path / "PARAMETER_SOURCE_RECORD.json"
        assert persisted.is_file()
        loaded = json.loads(persisted.read_text())
        assert loaded["organ"] == "VALUE_SOURCING"
        # the enriched spec now carries parameters the classifier reads
        params = (enriched.get("engineering_specification")
                  or {}).get("parameters") or []
        assert len(params) >= 3

    def test_hook_noops_when_parameters_already_present(self, tmp_path):
        from discovery_fabric.engine import value_sourcing as vs
        spec = {"parameters": [
            {"param_id": "P-1", "unit": "mm", "value": 10.0,
             "value_class": "MODELLED",
             "provenance": {"envelope_basis": "released chain"}},
            {"param_id": "P-2", "unit": "mm", "value": 20.0,
             "value_class": "MODELLED",
             "provenance": {"envelope_basis": "released chain"}},
            {"param_id": "P-3", "unit": "mm", "value": 30.0,
             "value_class": "MODELLED",
             "provenance": {"envelope_basis": "released chain"}},
        ]}
        run_result = {"engineering_specification": spec}
        enriched, record = vs.ensure_sourced_parameters(
            run_result, work_dir=str(tmp_path))
        assert record is None, (
            "the organ must not overwrite released-chain parameters "
            "(Art. IV: no fallback, no double-write)")

    def test_hook_noops_without_an_engineering_spec(self, tmp_path):
        from discovery_fabric.engine import value_sourcing as vs
        enriched, record = vs.ensure_sourced_parameters(
            {"final_state": {}}, work_dir=str(tmp_path))
        assert record is None
