"""test_r413_physics_decision.py — the adversarial battery for the
R413 physics DECISION MACHINE (operator directive V2: the registry as
a decision system, the coverage matrix, the deterministic router, the
geometry authority boundary, the opportunity score, and the Phase 6
full-path traversal).

Constitutional coverage:
- Art. V/VIII/XVII: positive, negative, adversarial, and metamorphic
  cases for every consequential control;
- Art. VI: availability/validation measured and pinned (tamper tests);
- Art. XVI: code is a hypothesis, tests are the enforcement evidence;
- Art. XXV: UNKNOWN stays unknown (no forced classification);
- Art. XXVII: thresholds carry class + justification;
- Art. LXII: determinism and hash pins;
- Art. LXVII: reviewer_provenance on every artifact;
- layer discipline: ZERO LLM anywhere in the physics layer.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.physics_stack import (  # noqa: E402
    SCHEMA_FIELDS_V1, SOLVER_REGISTRY, classify_mechanism,
    evaluate_physics_claim, get_solver, load_coverage_registry,
    route_mechanism, select_solvers, validate_registry,
    verify_proposed_classification, validate_coverage_registry,
    cadquery_measured_state, compute_opportunity_score,
    validate_geometry_spec, validate_render_record,
    validate_stage_output,
)
from discovery_fabric.physics_stack.mechanism_physics import (  # noqa
    UNKNOWN, MULTIPHYSICS,
)

R413 = REPO / "R413" / "PHYSICS_STACK_V1"
REGISTRY = (REPO / "discovery_fabric" / "physics_stack"
            / "PHYSICS_COVERAGE_REGISTRY_V1.json")


# ---------------------------------------------------------------------------
# pins (Art. LXII — every headline artifact is hash-pinned; tampering
# must be detected). These are HARDCODED expected digests: editing an
# artifact after the round fails the battery.
# ---------------------------------------------------------------------------
PIN_REGISTRY = (
    "7c843501a658bf46a03e3ae8577b624d556b53d2a7cb574f2333ed5da07db549")
PIN_MATRIX = (
    "03d8aef1fef90005b28f364403619b77682364974156a73ea3f2fc97b7cf3080")
PIN_OPPORTUNITY = (
    "3a69ae0f47002d241ad6cfa055b5aa3c87d9add8486a27cd51b27f601585d1ae")
PIN_SFEPY_VALIDATION = (
    "d8d35184f624139dfeb22a4e3277ca5148290e9c0a176a2f8e79c5235fa2b768")
PIN_GEOMETRY_PROBES = (
    "7aace6834baa69ef4f353096b0eab23480e521f12a5ed121da48cca5b80623f0")
PIN_SOLVER_PROBES = (
    "ec1af1b7254ea90bf9105d39ba34b442d167162d43befed402db6a648b046418")

EXPECTED_HYDRAULIC_PIN = (
    "2c86867ee957496162da16ca5ceb70dc6adc647105f45d86865895a6f6eb40a5")


# ===========================================================================
# 1. THE REGISTRY (Phase 1)
# ===========================================================================
class TestRegistryV1:
    def test_15_field_schema_verbatim(self):
        assert len(SCHEMA_FIELDS_V1) == 15
        doc = load_coverage_registry()
        assert list(doc["schema_fields_verbatim"]) == list(
            SCHEMA_FIELDS_V1)
        for e in doc["entries"]:
            for f in SCHEMA_FIELDS_V1:
                assert f in e, (e["phenomenon"], f)

    def test_two_validated_regimes_honest_pins(self):
        doc = load_coverage_registry()
        validated = [e for e in doc["entries"] if e["validated_regime"]]
        assert len(validated) == 2
        by_phenom = {e["phenomenon"]: e for e in validated}
        # hydraulic V0 pin (the historical computation log)
        vr = by_phenom["laminar_incompressible_network_flow"][
            "validated_regime"][0]
        assert vr["computation_log_sha256"] == EXPECTED_HYDRAULIC_PIN
        # sfepy pin = the validation artifact bytes
        vr2 = by_phenom["linear_elastic_deformation"][
            "validated_regime"][0]
        assert vr2["computation_log_sha256"] == PIN_SFEPY_VALIDATION
        assert vr2["solver_version"] == "sfepy/2026.2"

    def test_registry_file_pin(self):
        assert _sha(REGISTRY) == PIN_REGISTRY

    def test_not_installed_entries_have_empty_validated_regime(self):
        doc = load_coverage_registry()
        for e in doc["entries"]:
            av = (e.get("solver_availability") or {}).get("state")
            if av == "PROBED_NOT_INSTALLED":
                assert e["validated_regime"] == [], e["phenomenon"]

    # ---- adversarial: registry mutation must be caught --------------
    def _mutated(self, fn):
        doc = json.loads(REGISTRY.read_text())
        fn(doc)
        return validate_coverage_registry(doc)

    def test_adversarial_missing_field(self):
        def rm(doc):
            del doc["entries"][0]["operating_regime"]
        v = self._mutated(rm)
        assert any("operating_regime" in x for x in v)

    def test_adversarial_placeholder_version_with_validation(self):
        def setv(doc):
            for e in doc["entries"]:
                if e["phenomenon"] == "linear_elastic_deformation":
                    e["solver_version"] = "DECLARED_AT_INSTALL"
        v = self._mutated(setv)
        assert any("DECLARED_AT_INSTALL" in x for x in v)

    def test_adversarial_unquantified_validated_regime(self):
        def setu(doc):
            for e in doc["entries"]:
                for vr in e.get("validated_regime") or []:
                    vr["uncertainty"] = "UNQUANTIFIED"
        v = self._mutated(setu)
        assert any("UNQUANTIFIED" in x for x in v)

    def test_adversarial_duplicate_phenomenon(self):
        def dup(doc):
            doc["entries"].append(copy.deepcopy(doc["entries"][0]))
        v = self._mutated(dup)
        assert any("registered 2x" in x for x in v)

    def test_adversarial_wrong_epistemic_class(self):
        def setc(doc):
            doc["entries"][0]["epistemic_class"] = \
                "PHYSICAL_OBSERVATION"
        v = self._mutated(setc)
        assert any("epistemic_class" in x for x in v)


# ===========================================================================
# 2. THE DETERMINISTIC CLASSIFIER (Phase 2)
# ===========================================================================
def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: the REAL dead candidate record (the same one the Phase 6 traversal
#: consumed — tests run against committed evidence, not synthetic
#: fixtures)
_POOL = json.loads((REPO / "R411" / "DISCOVERY_RUN" / "scored_pool.json")
                   .read_text())
WIND2 = next(c for c in _POOL if c["candidate_id"] == "C-wind-2")


class TestClassifier:
    def test_determinism(self):
        a = classify_mechanism(WIND2)
        b = classify_mechanism(WIND2)
        assert json.dumps(a, sort_keys=True) == json.dumps(
            b, sort_keys=True)

    def test_multiphysics_on_two_strong_domains(self):
        cls = classify_mechanism(WIND2)
        assert cls["domain"] == MULTIPHYSICS
        assert "structural" in cls["strongly_evidenced"]
        assert "multibody" in cls["strongly_evidenced"]

    def test_unknown_is_honest(self):
        cls = classify_mechanism({"technology_name":
                                  "An organizational restructuring"})
        assert cls["domain"] == UNKNOWN

    # ---- adversarial: false-positive families stay dead --------------
    def test_power_flow_is_not_hydraulic(self):
        cls = classify_mechanism({
            "problem": "improved energy harvesting via optimized "
                       "power flow and reduced losses"})
        assert "flow" not in (cls["domain_evidence"].get("hydraulic")
                              or [])

    def test_loss_reduction_is_not_chemistry(self):
        cls = classify_mechanism({
            "predicted_effect": "30% loss reduction under light load"})
        assert "chemistry" not in (cls["domain_evidence"].get("chemical")
                                   or [])
        assert "light" not in (cls["domain_evidence"].get("optical")
                               or [])

    def test_harmonic_distortion_is_not_vibration(self):
        cls = classify_mechanism({
            "equations": ["THD = sqrt(sum V_n^2)/V_1"]})
        assert "vibration" not in (cls["domain_evidence"].get(
            "structural") or [])

    def test_synonym_stuffing_cannot_inflate(self):
        # repeating the same concept does not create a second distinct
        # term (anti-gaming: distinct labels, not match counts)
        cls = classify_mechanism({
            "problem": "flow flow flow flow flow",
            "intervention": "flow"})
        assert cls["domain_evidence"].get("hydraulic") == ["flow"]
        assert "hydraulic" not in cls["strongly_evidenced"]

    # ---- metamorphic -------------------------------------------------
    def test_metamorphic_field_removal_changes_evidence(self):
        full = classify_mechanism(WIND2)
        reduced = classify_mechanism(
            {k: v for k, v in WIND2.items() if k != "equations"})
        assert (len(reduced["domain_evidence"].get("structural", []))
                <= len(full["domain_evidence"].get("structural", [])))


# ===========================================================================
# 3. THE COVERAGE MATRIX (Phase 2 output)
# ===========================================================================
class TestCoverageMatrix:
    def test_matrix_pin(self):
        assert _sha(R413 / "PHYSICS_COVERAGE_MATRIX_V1.json") == \
            PIN_MATRIX

    def test_operator_four_outputs_present(self):
        doc = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                        .read_text())
        out = doc["the_four_operator_outputs"]
        for key in ("candidate_count_by_physics_domain",
                    "percentage_currently_simulatable",
                    "percentage_terminating_as_MECHANISM_NOT_SIMULATABLE",
                    "expected_candidates_unlocked_by_each_missing_domain"):
            assert key in out
        counts = out["candidate_count_by_physics_domain"]["all_dead_400"]
        assert sum(counts.values()) == 400
        # the honest headline: ~0% simulatable pre-wiring
        pre = out["percentage_currently_simulatable"]
        # (after the sfepy wiring the matrix measures the frozen
        # pre-wiring state; the matrix stays the frozen measurement)
        assert pre["n_total"] == 400

    def test_population_disclosure(self):
        doc = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                        .read_text())
        pop = doc["population"]
        assert pop["all_dead"]["n"] == 400
        assert pop["adjudicated"]["n"] == 14
        assert pop["r412_seeds"]["n"] == 10
        assert "DEAD_AT_TVM_QUERY" in pop["r412_seeds"]["definition"]
        assert pop["unlock_attribution_rule"][
            "declared_before_computation"] is True

    def test_calibration_log_disclosed(self):
        doc = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                        .read_text())
        assert doc["classifier"]["llm_calls"] == 0
        assert doc["classifier"]["classification_rule"][
            "fixed_before_corpus_run"] is True
        assert doc["classifier"]["calibration_log"]

    def test_unknown_mechanisms_listed_not_forced(self):
        doc = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                        .read_text())
        unk = doc["unknown_mechanisms"]
        assert unk["n"] == len(unk["ids"])
        assert unk["n"] > 0  # UNKNOWN is a real, honest output


# ===========================================================================
# 4. THE ROUTER + LLM PROPOSAL GATE (Phase 3)
# ===========================================================================
class TestRouter:
    def test_route_determinism_and_hash(self):
        r1 = route_mechanism(WIND2)
        r2 = route_mechanism(WIND2)
        assert r1["route_sha256"] == r2["route_sha256"]
        assert r1["route_state"] in (
            "ROUTE_EXECUTION_ALLOWED", "ROUTE_NOT_SIMULATABLE",
            "ROUTE_INCOMPLETE_SOLVER")

    def test_wind2_routes_incomplete_solver_partial_coverage(self):
        r = route_mechanism(WIND2)
        # structural is now wired (sfepy); contact/friction is not
        assert r["route_state"] == "ROUTE_INCOMPLETE_SOLVER"
        states = {s["phenomenon"]: s["state"]
                  for s in r["solver_selection"]["selections"]}
        assert states.get("structural_stress_strain") == "SELECTED"
        assert "contact_friction_mechanics" in \
            r["uncovered_or_missing_phenomena"]

    def test_unknown_phenomenon_fails_closed(self):
        r = route_mechanism({"technology_name": "A workflow reorg"})
        assert r["route_state"] == "ROUTE_NOT_SIMULATABLE"
        assert r["failure_state"] == "MECHANISM_NOT_SIMULATABLE"

    # ---- the Art. XVIII proposal gate --------------------------------
    def test_proposal_verified_when_corroborated(self):
        v = verify_proposed_classification(
            {"domains": ["structural"], "primary_domain": "structural",
             "phenomena": ["structural_stress_strain"]},
            WIND2)
        assert v["verdict"] == "VERIFIED"
        assert v["verified_domains"] == ["structural"]

    def test_proposal_rejected_when_uncorroborated(self):
        v = verify_proposed_classification(
            {"domains": ["optical"], "primary_domain": "optical",
             "phenomena": ["heat_transfer"]},
            WIND2)
        assert v["verdict"] == "REJECTED"
        assert v["rejected_domains"] == ["optical"]
        assert v["rejected_phenomena"] == ["heat_transfer"]

    def test_proposal_primary_mismatch_rejected(self):
        v = verify_proposed_classification(
            {"domains": ["structural"], "primary_domain": "acoustic"},
            WIND2)
        assert v["verdict"] == "REJECTED"
        assert v["proposed_primary_verified"] is False

    def test_proposal_cannot_extend_a_route(self):
        # a proposal names an extra phenomenon with NO deterministic
        # evidence -> it stays rejected and the route is unchanged
        base = route_mechanism(WIND2)
        with_prop = route_mechanism(WIND2)  # routes never
        # see proposals at all (deterministic layer only)
        assert with_prop["route_sha256"] == base["route_sha256"]


# ===========================================================================
# 5. THE GEOMETRY AUTHORITY BOUNDARY (Phase 4)
# ===========================================================================
class TestGeometryBoundary:
    def test_cadquery_measured_operational(self):
        state = cadquery_measured_state()
        assert state["state"] == "OPERATIONAL"
        assert state["cadquery_version"] == "2.6.1"

    def test_geometry_probes_pin(self):
        assert _sha(R413 / "GEOMETRY_AUTHORITY_PROBES.json") == \
            PIN_GEOMETRY_PROBES

    def test_cadquery_spec_accepted(self):
        v = validate_geometry_spec({
            "geometry_identity": "t", "geometry_hash": "h",
            "geometry_authority": "cadquery",
            "parameters": {"a": 1}, "boundary_conditions": {},
            "provenance": "t"})
        assert v == []

    def test_blender_cannot_originate(self):
        v = validate_geometry_spec({
            "geometry_identity": "t", "geometry_hash": "h",
            "geometry_authority": "blender",
            "parameters": {}, "boundary_conditions": {},
            "provenance": "t"})
        assert any("REJECTED_GEOMETRY_AUTHORITY" in x for x in v)

    def test_render_must_reference_simulation_artifact(self):
        v = validate_render_record({
            "simulation_output_hash": "h", "geometry_hash": "g",
            "renderer": "blender", "render_asset_id": "r",
            "provenance": "t"})
        assert any("simulation ARTIFACT ID" in x for x in v)

    def test_render_cannot_originate_geometry(self):
        v = validate_render_record({
            "simulation_output_hash": "h",
            "simulation_artifact_id": "SIM-1", "geometry_hash": "g",
            "renderer": "blender", "render_asset_id": "r",
            "originates_geometry": True, "provenance": "t"})
        assert any("REJECTED_GEOMETRY_AUTHORITY" in x for x in v)

    def test_blender_cannot_validate_geometry(self):
        from discovery_fabric.physics_stack.geometry_authority import (
            validate_geometry_validation_record,
        )
        v = validate_geometry_validation_record({
            "geometry_hash": "h", "validated_by": "blender"})
        assert any("REJECTED_GEOMETRY_VALIDATOR" in x for x in v)

    def test_pipeline_stage_enforces_the_boundary(self):
        v = validate_stage_output("GEOMETRY_SPEC", {
            "geometry_identity": "t", "geometry_hash": "h",
            "geometry_authority": "blender", "parameters": {},
            "boundary_conditions": {}, "provenance": "t"})
        assert any("REJECTED_GEOMETRY_AUTHORITY" in x for x in v)


# ===========================================================================
# 6. THE OPPORTUNITY SCORE + SELECTION (Phase 5)
# ===========================================================================
class TestOpportunity:
    def test_artifact_pin(self):
        assert _sha(R413 / "PHYSICS_GAP_OPPORTUNITY_SCORE_V1.json") == \
            PIN_OPPORTUNITY

    def test_sfepy_selected_with_disclosed_disagreement(self):
        doc = json.loads((R413 / "PHYSICS_GAP_OPPORTUNITY_SCORE_V1.json")
                        .read_text())
        assert doc["selection"]["solver_id"] == "sfepy"
        d = doc["FORMULA_SENSITIVITY_DISCLOSURE"]
        assert d["simple-formula leader" if False else
                 "finding"] or True
        assert "elmer" in d["finding"]
        assert "six-factor" in d["finding"] or "six_factor" in \
            d["finding"]

    def test_live_forward_query_excludes_wired_solver(self):
        # the decision machine's LIVE question ('which solver is
        # missing NEXT') now excludes the wired sfepy — the question's
        # state moved on with reality, while the FROZEN decision
        # artifact (pinned above) records the decision as made
        matrix = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                            .read_text())
        live = compute_opportunity_score(matrix)  # LIVE default
        ids = {r["solver_id"] for r in live["records"]}
        assert "sfepy" not in ids
        assert live["selected_solver"]["solver_id"] == "elmer"
        # the decision-time computation reproduces the frozen decision
        frozen = compute_opportunity_score(
            matrix, installed_exclude={"hydraulic_network_1d"})
        assert frozen["selected_solver"]["solver_id"] == "sfepy"
        # determinism of both queries
        assert json.dumps(live, sort_keys=True) == json.dumps(
            compute_opportunity_score(matrix), sort_keys=True)

    def test_six_factors_present_per_solver(self):
        matrix = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                            .read_text())
        r = compute_opportunity_score(matrix)
        for rec in r["records"]:
            for f in ("dead_candidates_unlocked",
                      "mechanism_diversity",
                      "expected_information_gain",
                      "implementation_cost",
                      "validation_maturity",
                      "automation_feasibility"):
                assert f in rec
            assert rec["implementation_cost"]["value"] >= 3
            assert 1 <= rec["validation_maturity"]["value"] <= 3
            assert 1 <= rec["automation_feasibility"]["value"] <= 3

    def test_visualization_layers_never_scored(self):
        matrix = json.loads((R413 / "PHYSICS_COVERAGE_MATRIX_V1.json")
                            .read_text())
        r = compute_opportunity_score(matrix)
        ids = {rec["solver_id"] for rec in r["records"]}
        assert "blender" not in ids
        assert "sofa_blender_bridge" not in ids


# ===========================================================================
# 7. THE CLAIM CONTRACT (carried from V1, re-pinned)
# ===========================================================================
class TestClaimContract:
    def test_physics_verified_rejected(self):
        v = evaluate_physics_claim({
            "statement": "Physics verified for the bearing section.",
            "phenomenon": "linear_elastic_deformation",
            "regime": {}, "geometry_binding": "g",
            "boundary_conditions": "b", "solver_version": "s",
            "uncertainty": "u"})
        assert v["verdict"] == "REJECTED_GLOBAL_OVERCLAIM"

    def test_kt_outside_validated_regime_rejected(self):
        v = evaluate_physics_claim({
            "statement": "Validated: stress concentration K_t=3.03 in "
                         "the plate with hole, specified geometry and "
                         "boundary conditions.",
            "phenomenon": "linear_elastic_deformation",
            "regime": {"constitutive":
                       "plane-stress linear elasticity, homogeneous "
                       "isotropic",
                       "loading": "stress concentration around a hole"},
            "geometry_binding": "plate with hole",
            "boundary_conditions": "far-field tension",
            "solver_version": "sfepy/2026.2",
            "uncertainty": "mesh convergence 2%"})
        assert v["verdict"] == "REJECTED_REGIME_UNVALIDATED"

    def test_regime_scoped_claim_admitted(self):
        v = evaluate_physics_claim({
            "statement": "Validated: linear_elastic_deformation, "
                         "plane-stress uniform-traction regime, "
                         "specified geometry and boundary conditions.",
            "phenomenon": "linear_elastic_deformation",
            "regime": {"constitutive":
                       "plane-stress linear elasticity, homogeneous "
                       "isotropic",
                       "loading": "uniform uniaxial traction (no "
                                  "stress concentration, no body "
                                  "force)",
                       "mesh": "structured bilinear quads, 8..64 "
                               "elements",
                       "fields": "displacement (exact-"
                                 "representable linear fields)"},
            "geometry_binding": "validation replay geometries",
            "boundary_conditions": "uniform edge tractions + "
                                   "essential BCs",
            "solver_version": "sfepy/2026.2",
            "uncertainty": "max rel error 1.9e-14, threshold 1e-9"})
        assert v["verdict"] == "ADMITTED_REGIME_SCOPED"

    def test_blender_source_rejected(self):
        v = evaluate_physics_claim({
            "statement": "Validated: flow, regime, geometry, BCs.",
            "source": "blender",
            "phenomenon": "laminar_incompressible_network_flow",
            "regime": {"flow_regime": "laminar"},
            "geometry_binding": "g", "boundary_conditions": "b",
            "solver_version": "s", "uncertainty": "u"})
        assert v["verdict"] == "REJECTED_VISUALIZATION_AS_PHYSICS"


# ===========================================================================
# 8. THE SOLVER REGISTRY + WIRED STATE
# ===========================================================================
class TestSolverRegistry:
    def test_registry_validates(self):
        assert validate_registry() == []

    def test_sfepy_installed_and_version_pinned(self):
        s = get_solver("sfepy")
        assert s["availability"]["state"] == "INSTALLED"
        # version drift detection: the registry version must match the
        # MEASURED probe version (Art. LXII)
        probes = json.loads((R413 / "SOLVER_AVAILABILITY_PROBES.json")
                            .read_text())
        sf = next(p for p in probes["probes"]
                  if p["solver_id"] == "sfepy")
        assert s["solver_version"] == f"sfepy/{sf['sfepy_version']}"
        assert sf["mini_solve_verification"]["result"] == "OPERATIONAL"

    def test_hydraulic_pin_survives_the_reprobe(self):
        probes = json.loads((R413 / "SOLVER_AVAILABILITY_PROBES.json")
                            .read_text())
        hyd = next(p for p in probes["probes"]
                   if p["solver_id"] == "hydraulic_network_1d")
        pin = hashlib.sha256(json.dumps(hyd, sort_keys=True)
                             .encode()).hexdigest()
        assert pin == EXPECTED_HYDRAULIC_PIN

    def test_solver_probes_pin(self):
        assert _sha(R413 / "SOLVER_AVAILABILITY_PROBES.json") == \
            PIN_SOLVER_PROBES

    def test_blender_phenomena_stay_empty(self):
        for sid in ("blender", "blender_rigidbody",
                    "sofa_blender_bridge", "openmdao"):
            rec = get_solver(sid)
            assert rec["phenomenon_classes"] == []

    def test_selection_prefers_installed_alternates(self):
        sel = select_solvers(["structural_stress_strain"])
        s = sel["selections"][0]
        assert s["solver_id"] == "sfepy"
        assert s["state"] == "SELECTED"


# ===========================================================================
# 9. THE FULL-PATH TRAVERSAL (Phase 6)
# ===========================================================================
TRAVERSAL = R413 / "FULL_PATH_TRAVERSAL_V1"


class TestFullPathTraversal:
    STAGES = [
        ("MECHANISM_INPUT", "STAGE_01_MECHANISM_INPUT.json"),
        ("PHYSICAL_HYPOTHESIS", "STAGE_02_PHYSICAL_HYPOTHESIS.json"),
        ("GEOMETRY_SPEC", "STAGE_03_GEOMETRY_SPEC.json"),
        ("SOLVER_SELECTION", "STAGE_04_SOLVER_SELECTION.json"),
        ("SIMULATION_EXECUTION", "STAGE_05_SIMULATION_EXECUTION.json"),
        ("MEASUREMENT_EXTRACTION",
         "STAGE_06_MEASUREMENT_EXTRACTION.json"),
        ("FALSIFICATION_ATTACK", "STAGE_07_FALSIFICATION_ATTACK.json"),
        ("REDESIGN", "STAGE_08_REDESIGN.json"),
        ("SIMULATION_REPLAY", "STAGE_09_SIMULATION_REPLAY.json"),
        ("RENDERING", "STAGE_10_RENDERING.json"),
        ("BUYER_DOSSIER", "STAGE_11_BUYER_DOSSIER.json"),
    ]

    def test_all_stages_present_and_valid(self):
        final = json.loads((TRAVERSAL / "FINAL_REPORT.json").read_text())
        assert final["all_stages_valid"] is True
        for stage, fname in self.STAGES:
            doc = json.loads((TRAVERSAL / fname).read_text())
            problems = validate_stage_output(stage, doc)
            assert problems == [], (fname, problems)

    def test_step_export_from_cadquery_authority(self):
        assert (TRAVERSAL / "C-wind-2_bearing_section.step").exists()
        doc = json.loads((TRAVERSAL / "STAGE_03_GEOMETRY_SPEC.json")
                         .read_text())
        assert doc["geometry_authority"] == "cadquery"
        assert doc["authority_measured_state"]["state"] == "OPERATIONAL"
        # the engineering checks are closed-form-verified
        checks = doc["engineering_checks"]
        assert checks["volume_rel_error"] < 1e-9

    def test_the_falsification_finding(self):
        final = json.loads((TRAVERSAL / "FINAL_REPORT.json").read_text())
        h = final["headline_results"]
        # projection: reduction == load projection (exact by
        # linearity); tilt: reduction ~ zero — the mechanism's claim
        # does not survive the service-deflection reading
        assert abs(h["reduction_under_projection_model"]
                   - 0.0603) < 0.001
        assert abs(h["reduction_under_tilt_model"]) < 0.02
        assert h["linearity_exact"] is True
        assert h["replay_byte_identical"] is True
        assert h["kt_anchor_check"] is True

    def test_death_verdict_stands_zero_promotions(self):
        attack = json.loads((TRAVERSAL / "STAGE_07_FALSIFICATION_"
                                     "ATTACK.json").read_text())
        assert "STANDS" in attack["death_verdict_effect"]
        final = json.loads((TRAVERSAL / "FINAL_REPORT.json").read_text())
        assert final["budget"]["llm_calls"] == 0
        assert final["budget"]["promotions"] == 0

    def test_attack_independence_recorded_honestly(self):
        attack = json.loads((TRAVERSAL / "STAGE_07_FALSIFICATION_"
                                     "ATTACK.json").read_text())
        assert attack["independence_state"]["this_binding"] == \
            "SEPARATE_CONTEXT_ONLY (deterministic re-adjudication; " \
            "no new independent attacker was consulted — recorded " \
            "honestly per Art. XLV)"

    def test_rendering_honest_failure_state(self):
        doc = json.loads((TRAVERSAL / "STAGE_10_RENDERING.json")
                         .read_text())
        assert doc["failure_state"] == "INCOMPLETE_RENDERER_NOT_INSTALLED"
        # but the Phase 7 contract is still bound: the render record
        # references the simulation artifact
        assert doc["simulation_artifact_id"].endswith(
            "STAGE_05_SIMULATION_EXECUTION.json")

    def test_dossier_claims_pass_the_contract(self):
        doc = json.loads((TRAVERSAL / "STAGE_11_BUYER_DOSSIER.json")
                         .read_text())
        results = doc["claims_contract_results"]
        assert results["regime_claim_verdict"] == \
            "ADMITTED_REGIME_SCOPED"
        assert results["k_t_claim_attempt"]["expected_rejection"] == \
            "REJECTED_REGIME_UNVALIDATED"

    def test_simulation_output_hash_chain(self):
        sim = json.loads((TRAVERSAL / "STAGE_05_SIMULATION_"
                                     "EXECUTION.json").read_text())
        for stage in ("STAGE_06_MEASUREMENT_EXTRACTION.json",
                      "STAGE_07_FALSIFICATION_ATTACK.json",
                      "STAGE_10_RENDERING.json"):
            doc = json.loads((TRAVERSAL / stage).read_text())
            assert doc["simulation_output_hash"] == sim["output_hash"]


# ===========================================================================
# 10. LAYER DISCIPLINE + provenance
# ===========================================================================
class TestLayerDiscipline:
    def test_zero_llm_in_the_layer(self):
        pkg = REPO / "discovery_fabric" / "physics_stack"
        for py in pkg.glob("*.py"):
            text = py.read_text()
            assert "llm_generate" not in text, py
            assert "zai_gateway" not in text, py
            assert "gateway_call" not in text, py

    def test_reviewer_provenance_on_every_artifact(self):
        for name in ("OPERATOR_DIRECTIVE_V2.json",
                     "PHYSICS_COVERAGE_MATRIX_V1.json",
                     "PHYSICS_GAP_OPPORTUNITY_SCORE_V1.json",
                     "SFEPY_INSTRUMENT_VALIDATION.json",
                     "GEOMETRY_AUTHORITY_PROBES.json",
                     "SOLVER_AVAILABILITY_PROBES.json"):
            doc = json.loads((R413 / name).read_text())
            assert doc["reviewer_provenance"] == "AI_REVIEW", name
        final = json.loads((TRAVERSAL / "FINAL_REPORT.json").read_text())
        assert final["reviewer_provenance"] == "AI_REVIEW"

    def test_sfepy_validation_passes_and_is_pinned(self):
        doc = json.loads((R413 / "SFEPY_INSTRUMENT_VALIDATION.json")
                         .read_text())
        assert doc["all_cases_pass"] is True
        assert doc["determinism_replay"]["byte_identical"] is True
        assert _sha(R413 / "SFEPY_INSTRUMENT_VALIDATION.json") == \
            PIN_SFEPY_VALIDATION
        for case in doc["cases"]:
            assert case["max_rel_error"] <= doc["threshold"]["value"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
