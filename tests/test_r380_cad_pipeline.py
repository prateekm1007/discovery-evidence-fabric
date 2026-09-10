"""R380 3D ENGINEERING DESIGN PIPELINE — adversarial hermetic tests.

Every test is an ATTACK on the implementation (Art. XVII): an
intelligent adversary tries to smuggle untrusted geometry, launder
invented measurements, forge provenance, escape the sandbox, or
promote a render into validation. The gates must hold.

Constitutional anchors under attack:
- Art. XVIII  sandbox escape attempts (imports, dunders, exec)
- Art. VI     forged hashes, invented measurements without logs
- Art. III    hardcoded values vs parameter map (claimant vs verifier)
- Art. XXVIII RENDER_IS_NOT_VALIDATION laundering
- Art. XXV    UNKNOWN/unverifiable must never silently pass
- Art. XXXVIII COMPUTATIONAL_RESULT never becomes physical evidence
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _archived_factory():
    """R440 (Art. LXIV): the package_factory is RETIRED from production
    (ARCHIVED_TO archive/r440_retired/). These R380 tests lock the FROZEN
    historical behavior of its 3D-section builder; they load the archive
    explicitly by path — the module name no longer resolves in the
    import system (structural retirement, asserted by
    tests/test_r440_canonical_package_compiler.py)."""
    import importlib.util
    name = "discovery_fabric.engine.package_factory_archived"
    if name in sys.modules:
        return sys.modules[name]
    src_path = Path(__file__).resolve().parents[1] / "archive" / \
        "r440_retired" / "package_factory.py"
    spec = importlib.util.spec_from_file_location(name, str(src_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

from discovery_fabric.engine import cad_pipeline as cp


def _dual_lumen_state(**overrides):
    """A realistic CereVasc-family technical state (hermetic fixture)."""
    params = [
        {"param_id": "outer_diameter_mm", "name": "outer diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 3.0,
         "value_class": "MODELLED", "range_min": 2.0, "range_max": 5.0,
         "range_class": "MODELLED", "role": "device envelope"},
        {"param_id": "lumen_diameter_mm", "name": "lumen diameter",
         "category": "GEOMETRY", "unit": "mm", "value": 1.0,
         "value_class": "MODELLED", "range_min": 0.5, "range_max": 2.0,
         "range_class": "MODELLED", "role": "drainage lumen"},
        {"param_id": "length_mm", "name": "tube length",
         "category": "GEOMETRY", "unit": "mm", "value": 30.0,
         "value_class": "MODELLED", "range_min": 10.0, "range_max": 60.0,
         "range_class": "MODELLED", "role": "implant length"},
        {"param_id": "septum_thickness_mm", "name": "septum thickness",
         "category": "GEOMETRY", "unit": "mm", "value": 0.2,
         "value_class": "MODELLED", "range_min": 0.05, "range_max": 0.5,
         "range_class": "MODELLED", "role": "wall between lumens"},
    ]
    for pid, newv in overrides.items():
        for p in params:
            if p["param_id"] == pid:
                p["value"] = newv
    return {
        "objects": [{"object_id": "dual_lumen_tube",
                     "role": "outer body with two through-lumens"}],
        "parameters": params,
        "constraints": [
            {"constraint_id": "c1", "target": "wall_thickness_mm",
             "bound": ">=", "limit": 0.15, "limit_class": "MODELLED",
             "justification": "thin-wall micro-extrusion"}],
        "dependencies": [], "materials": [],
        "operating_conditions": [], "measurable_outputs": [],
    }


def _spec_with_state(state):
    return {"candidate_id": "TEST-CAD",
            "technical_state": {"value": state}}


class TestWarrantsGate(unittest.TestCase):
    """The honest NOT_APPLICABLE path — never forced 3D."""

    def test_no_geometry_warrants_not_applicable(self):
        spec = {"candidate_id": "X", "technical_state": {"value": {
            "objects": [],
            "parameters": [
                {"param_id": "dose_mg", "category": "PARAMETERS",
                 "unit": "mg", "value": 5.0, "value_class": "MODELLED",
                 "range_min": 1.0, "range_max": 10.0,
                 "range_class": "MODELLED"}],
            "constraints": [], "dependencies": [], "materials": [],
            "operating_conditions": [], "measurable_outputs": []}}}
        w = cp.geometry_warrants_3d(spec)
        self.assertFalse(w["warranted"])
        self.assertEqual(w["verdict"], "NOT_APPLICABLE")
        self.assertTrue(w["reasons"])

    def test_unbounded_parameters_warrants_not_applicable(self):
        # ADR_R379 immutability rule: unbounded parameter cannot drive
        # a reproducible parametric model
        state = _dual_lumen_state()
        for p in state["parameters"]:
            p["range_min"] = p["range_max"] = None
        w = cp.geometry_warrants_3d(_spec_with_state(state))
        self.assertFalse(w["warranted"])

    def test_geometric_candidate_warrants(self):
        w = cp.geometry_warrants_3d(
            _spec_with_state(_dual_lumen_state()))
        self.assertTrue(w["warranted"])


class TestSandbox(unittest.TestCase):
    """Art. XVIII — untrusted build programs must be contained."""

    def _build_with_program(self, program):
        state = _dual_lumen_state()
        spec = _spec_with_state(state)
        model, problems = cp.template_model_from_state(
            state, candidate_id="TEST-CAD")
        self.assertIsNotNone(model)
        model["build_program"] = program
        shapes, errors = cp._execute_build_program(
            program, {"outer_diameter_mm": 3.0, "lumen_diameter_mm": 1.0,
                      "length_mm": 30.0, "septum_thickness_mm": 0.2})
        return shapes, errors

    def test_import_attempt_rejected(self):
        shapes, errors = self._build_with_program(
            "import os\n\ndef build(p):\n    return {}\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("FORBIDDEN_NODE" in e for e in errors))

    def test_dunder_access_rejected(self):
        shapes, errors = self._build_with_program(
            "def build(p):\n    x = p.__class__\n    return {}\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("DUnder" in e for e in errors))

    def test_open_attempt_rejected(self):
        shapes, errors = self._build_with_program(
            "def build(p):\n    open('/etc/passwd')\n    return {}\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("FORBIDDEN_PRIMITIVE" in e
                            for e in errors))

    def test_exec_attempt_rejected(self):
        shapes, errors = self._build_with_program(
            "def build(p):\n    exec('1')\n    return {}\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("FORBIDDEN_PRIMITIVE" in e
                            for e in errors))

    def test_syntax_error_rejected(self):
        shapes, errors = self._build_with_program("def broken(:\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("SYNTAX_ERROR" in e for e in errors))

    def test_no_build_function_rejected(self):
        shapes, errors = self._build_with_program("x = 1\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("NO_BUILD_FUNCTION" in e for e in errors))

    def test_globals_leak_rejected(self):
        shapes, errors = self._build_with_program(
            "def build(p):\n    global cq\n    return {}\n")
        self.assertIsNone(shapes)
        self.assertTrue(any("FORBIDDEN_NODE" in e for e in errors))


class TestGeometryGates(unittest.TestCase):
    """The G-gates must catch each CEO-listed failure mode."""

    def _build_model(self, **overrides):
        state = _dual_lumen_state(**overrides)
        model, problems = cp.template_model_from_state(
            state, candidate_id="TEST-CAD")
        self.assertIsNotNone(model)
        self.assertEqual(problems, [])
        with tempfile.TemporaryDirectory() as td:
            return cp.build_and_validate_model(model, out_dir=td)

    def test_baseline_valid(self):
        model, rec = self._build_model()
        gv = model["geometry_validation"]
        self.assertTrue(gv["valid"], gv.get("reasons"))
        self.assertEqual(rec["status"], "OK")
        # measured wall honored by the built solid
        wall = (model["measurements"]["objects"]
                ["dual_lumen_tube"]["min_wall_thickness_mm"])
        self.assertAlmostEqual(wall, 3.0 / 2 - 1.0 - 0.2 / 2, places=6)
        self.assertTrue(wall >= 0.15)

    def test_breach_detected_three_ways(self):
        # lumen 1.7 mm: wall = 1.5 - 1.7 - 0.1 < 0 — the lumen opens
        # through the outer wall
        model, rec = self._build_model(lumen_diameter_mm=1.7)
        gv = model["geometry_validation"]
        self.assertFalse(gv["valid"])
        checks = {g: c["status"] for g, c in gv["checks"].items()}
        self.assertEqual(checks["G1b_cylinder_containment"], "VIOLATED")
        self.assertEqual(checks["G4_violated_geometric_constraints"],
                         "VIOLATED")
        self.assertEqual(checks["G4b_measured_vs_claimed_dimensions"],
                         "VIOLATED")
        wall = (model["measurements"]["objects"]
                ["dual_lumen_tube"]["min_wall_thickness_mm"])
        self.assertLess(wall, 0.0)

    def test_envelope_violation_detected(self):
        model, rec = self._build_model(lumen_diameter_mm=9.0)
        gv = model["geometry_validation"]
        checks = {g: c["status"] for g, c in gv["checks"].items()}
        self.assertEqual(checks["G3_impossible_dimensions"], "VIOLATED")
        self.assertFalse(gv["valid"])

    def test_wall_constraint_violation_detected(self):
        # lumen 1.2: wall = 1.5-1.2-0.1 = 0.2 >= 0.15 OK
        # lumen 1.35: wall = 0.075 < 0.15 -> constraint violation while
        # geometry itself is still buildable (containment positive)
        model, rec = self._build_model(lumen_diameter_mm=1.35)
        gv = model["geometry_validation"]
        checks = {g: c["status"] for g, c in gv["checks"].items()}
        self.assertEqual(checks["G4_violated_geometric_constraints"],
                         "VIOLATED")
        # but NOT a containment breach
        self.assertEqual(checks["G1b_cylinder_containment"], "SATISFIED")
        self.assertFalse(gv["valid"])

    def test_hardcoded_value_detected(self):
        # adversary: program ignores the parameter map and hardcodes
        state = _dual_lumen_state()
        model, _ = cp.template_model_from_state(
            state, candidate_id="TEST-CAD")
        # adversary: hardcodes values EQUAL to today's map values —
        # the model looks right NOW but silently never responds to a
        # mutation (the source-of-truth violation G5b targets)
        model["build_program"] = (
            "def build(p):\n"
            "    od = 3.0\n"   # NOT from p — hardcoded
            "    ld = 1.0\n"
            "    L = 30.0\n"
            "    st = 0.2\n"
            "    r = ld / 2.0\n"
            "    c = r + st / 2.0\n"
            "    body = cq.Workplane('XY').circle(od / 2.0).extrude(L)\n"
            "    lumA = cq.Workplane('XY').center(-c, 0).circle(r).extrude(L)\n"
            "    lumB = cq.Workplane('XY').center(c, 0).circle(r).extrude(L)\n"
            "    return {'dual_lumen_tube': body.cut(lumA).cut(lumB)}\n")
        with tempfile.TemporaryDirectory() as td:
            built, rec = cp.build_and_validate_model(model, out_dir=td)
        gv = built["geometry_validation"]
        checks = {g: c["status"] for g, c in gv["checks"].items()}
        # G5 catches the map<->program mismatch (unused entries) and
        # G5b catches hardcoded literals; G4b catches the measured vs
        # claimed divergence
        self.assertEqual(checks["G5b_hardcoded_values"], "VIOLATED")
        self.assertFalse(gv["valid"])

    def test_missing_parameter_detected(self):
        state = _dual_lumen_state()
        state["parameters"] = [p for p in state["parameters"]
                               if p["param_id"] != "septum_thickness_mm"]
        model, problems = cp.template_model_from_state(
            state, candidate_id="TEST-CAD")
        self.assertIsNone(model)
        self.assertTrue(any("MISSING_PARAMETER" in x
                            for x in problems))

    def test_render_is_not_validation_structural(self):
        model, rec = self._build_model()
        gv = model["geometry_validation"]
        rinv = gv["render_is_not_validation"]
        self.assertFalse(rinv["technical_validity_derived_from_render"])
        # a render never sets validity
        self.assertNotEqual(gv["valid"], rinv["renders_successfully"])
        self.assertIn("NOT engineering validation", rinv["rule"])

    def test_stl_watertight_independent_check(self):
        model, rec = self._build_model()
        checks = {g: c["status"] for g, c in
                  model["geometry_validation"]["checks"].items()}
        # the secondary verifier (trimesh) actually ran and passed
        self.assertEqual(checks["G2_non_manifold_solids"], "SATISFIED")
        detail = model["geometry_validation"]["checks"][
            "G2_non_manifold_solids"]["detail"]
        self.assertTrue(any(r.get("watertight") for r in detail))

    def test_zero_volume_detected(self):
        # degenerate: zero length — OCCT raises on extrude(0) OR the
        # gates catch non-positive volume; either path is an honest
        # invalid model (BUILD_FAILED counts as detected)
        model, rec = self._build_model(length_mm=0.0)
        gv = model["geometry_validation"]
        self.assertFalse(gv["valid"])
        self.assertTrue(gv.get("reasons"))


class TestDerivedArtifacts(unittest.TestCase):
    """Art. VI — hashes are real; derivatives are labeled derivatives."""

    def _built(self):
        state = _dual_lumen_state()
        model, _ = cp.template_model_from_state(state,
                                                candidate_id="TEST-CAD")
        td = tempfile.mkdtemp()
        built, _rec = cp.build_and_validate_model(model, out_dir=td)
        return built, td

    def test_hashes_reverify_on_disk(self):
        model, td = self._built()
        arts = model["derived_artifacts"]
        self.assertTrue(arts)
        for key, art in arts.items():
            if not art.get("path"):
                continue
            h = cp._sha256_file(art["path"])
            self.assertEqual(h, art["sha256"],
                             f"hash mismatch on {key}")
            self.assertGreater(art["bytes"], 0)

    def test_derivative_of_references_real_model_id(self):
        model, td = self._built()
        for key, art in model["derived_artifacts"].items():
            self.assertTrue(art["derivative_of"].startswith(
                "parametric_model:"))
            self.assertNotIn("None", art["derivative_of"])

    def test_glb_is_presentation_labeled(self):
        model, td = self._built()
        glb = model["derived_artifacts"].get("GLB:presentation")
        self.assertIn("presentation", glb["role"].lower())
        self.assertIn("NOT engineering validation", glb["role"])

    def test_parametric_source_is_source_of_truth(self):
        # the build program hash re-verifies
        model, td = self._built()
        import hashlib
        h = hashlib.sha256(model["build_program"].encode(
            "utf-8")).hexdigest()
        self.assertEqual(h, model["program_source_sha256"])


class TestMutationRebuild(unittest.TestCase):
    """The CEO's exact loop: X=1.0 -> 1.2 KEEP region; -> 1.7 KILL."""

    def _model(self):
        state = _dual_lumen_state()
        model, _ = cp.template_model_from_state(state,
                                                candidate_id="TEST-CAD")
        td = tempfile.mkdtemp()
        built, _ = cp.build_and_validate_model(model, out_dir=td)
        return built

    def test_keep_mutation_rebuilds_valid_geometry(self):
        parent = self._model()
        child, rec = cp.rebuild_with_mutation(
            parent, "lumen_diameter_mm", 1.2, "tmut:t1", "r")
        self.assertEqual(rec["status"], "OK")
        self.assertTrue(child["geometry_validation"]["valid"])
        # provenance preserved
        self.assertEqual(child["parent_model_id"],
                         parent["model_id"])
        self.assertEqual(len(child["mutation_provenance"]), 1)
        mp = child["mutation_provenance"][0]
        self.assertEqual(mp["from_value"], 1.0)
        self.assertEqual(mp["to_value"], 1.2)
        # derivatives NOT inherited — rebuilt fresh
        self.assertNotEqual(child["model_id"], parent["model_id"])
        wall = (child["measurements"]["objects"]
                ["dual_lumen_tube"]["min_wall_thickness_mm"])
        self.assertAlmostEqual(wall, 0.2, places=6)

    def test_kill_mutation_detected_invalid(self):
        parent = self._model()
        child, rec = cp.rebuild_with_mutation(
            parent, "lumen_diameter_mm", 1.7, "tmut:t2", "r")
        self.assertEqual(rec["status"], "GEOMETRY_INVALID")
        self.assertFalse(child["geometry_validation"]["valid"])
        self.assertTrue(any("breaches" in r for r in
                            child["geometry_validation"]["reasons"]))

    def test_unbound_parameter_refused(self):
        parent = self._model()
        child, rec = cp.rebuild_with_mutation(
            parent, "not_a_bound_param", 1.0, "tmut:t3", "r")
        self.assertIsNone(child)
        self.assertEqual(rec["status"], "UNBOUND_PARAMETER")

    def test_provenance_chain_append_only(self):
        parent = self._model()
        child1, _ = cp.rebuild_with_mutation(
            parent, "lumen_diameter_mm", 1.2, "tmut:t4", "r1")
        child2, _ = cp.rebuild_with_mutation(
            child1, "length_mm", 40.0, "tmut:t5", "r2")
        self.assertEqual(len(child2["mutation_provenance"]), 2)
        self.assertEqual(child2["mutation_provenance"][0]["mutation_id"],
                         "tmut:t4")
        self.assertEqual(child2["mutation_provenance"][1]["mutation_id"],
                         "tmut:t5")


class TestRunCadPass(unittest.TestCase):
    """The top-level pass — outcome vocabulary honesty."""

    def test_baseline_pass_builds_validated_model(self):
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        self.assertEqual(ledger["outcome"],
                         "MODEL_BUILT_AND_VALIDATED")
        pm = new_spec.get("parametric_model")
        self.assertIsNotNone(pm)
        self.assertEqual(pm["epistemic_class"],
                         "COMPUTATIONAL_RESULT")
        model = pm["value"]
        self.assertEqual(model["evidence_class"],
                         "COMPUTATIONAL_RESULT")

    def test_not_applicable_pass_never_forces(self):
        spec = {"candidate_id": "X", "technical_state": {"value": {
            "objects": [], "parameters": [], "constraints": [],
            "dependencies": [], "materials": [],
            "operating_conditions": [], "measurable_outputs": []}}}
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=None,
                                           allow_llm=False)
        self.assertEqual(ledger["outcome"],
                         "NOT_APPLICABLE_NO_GEOMETRY")
        self.assertIsNone(new_spec.get("parametric_model"))

    def test_failed_geometry_never_enters_spec(self):
        # a valid state but a breach-producing value: the template
        # binds and builds, geometry FAILS -> nothing attached
        spec = _spec_with_state(_dual_lumen_state(
            lumen_diameter_mm=1.7))
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        self.assertIsNone(new_spec.get("parametric_model"),
                          "an invalid model must never enter the spec")
        # the template BOUND and built, geometry FAILED (recorded on
        # the attempt with geometry_invalid_reasons), the LLM path is
        # disabled -> honest no-model outcome; nothing entered the spec
        self.assertEqual(ledger["outcome"], "NO_MODEL_NO_LLM")
        attempts = ledger["attempts"]
        self.assertTrue(any(a.get("geometry_invalid_reasons")
                            for a in attempts
                            if a.get("path") == "ENGINE_TEMPLATE"),
                        attempts)

    def test_no_template_no_llm_honest(self):
        # bounded geometric params but a template that cannot bind
        state = _dual_lumen_state()
        for p in state["parameters"]:
            p["param_id"] = "other_" + p["param_id"]
        state["objects"] = [{"object_id": "other_object",
                             "role": "unknown form"}]
        spec = _spec_with_state(state)
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=None,
                                           allow_llm=False)
        self.assertEqual(ledger["outcome"], "NO_MODEL_NO_LLM")
        self.assertIsNone(new_spec.get("parametric_model"))

    def test_missing_template_params_not_bound(self):
        state = _dual_lumen_state()
        state["parameters"] = state["parameters"][:2]
        spec = _spec_with_state(state)
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=None,
                                           allow_llm=False)
        # template cannot bind (missing params) -> honest no-model
        self.assertIn(ledger["outcome"],
                      ("NO_MODEL_NO_LLM", "NOT_APPLICABLE_NO_GEOMETRY"))
        self.assertIsNone(new_spec.get("parametric_model"))


class TestEvidenceClassLaundering(unittest.TestCase):
    """Art. XXXVIII — computed geometry is never physical evidence."""

    def test_model_sections_never_claim_physical(self):
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        model = new_spec["parametric_model"]["value"]
        self.assertEqual(model["evidence_class"],
                         "COMPUTATIONAL_RESULT")
        gv = model["geometry_validation"]
        self.assertEqual(gv["evidence_class"],
                         "COMPUTATIONAL_RESULT")
        for key, art in model["derived_artifacts"].items():
            self.assertEqual(art["evidence_class"],
                             "COMPUTATIONAL_RESULT")
        # the computation log exists for measurements
        self.assertTrue(model["measurements"]["computation_log"])
        for entry in model["measurements"]["computation_log"]:
            self.assertIn("kernel", entry)
            self.assertIn("computed_at", entry)

    def test_measurement_without_log_is_naked(self):
        # adversary: inject an invented measurement with no log —
        # the numerical provenance audit must flag it (the audit is
        # re-derived, so we simulate the attack on the SPEC section)
        from discovery_fabric.benchmark import numerical_provenance as np
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        # ATTACK: strip the computation log, keep the measurements
        attacked = copy.deepcopy(new_spec)
        attacked["parametric_model"]["value"]["measurements"][
            "computation_log"] = []
        audit = np.audit_numerical_provenance(
            run_dir=None, package_dir=None, eng_spec=None,
            inv_spec=attacked)
        naked = [f for f in audit["findings"]
                 if f["status"] == "NAKED_NUMBER" and
                 f["number_id"].startswith("PM:meas:")]
        self.assertTrue(naked, "invented measurement not caught")

    def test_forged_artifact_hash_caught(self):
        from discovery_fabric.benchmark import numerical_provenance as np
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        # ATTACK: forge one artifact hash
        attacked = copy.deepcopy(new_spec)
        arts = attacked["parametric_model"]["value"][
            "derived_artifacts"]
        key = next(iter(arts))
        arts[key]["sha256"] = "0" * 64
        audit = np.audit_numerical_provenance(
            run_dir=Path(td), package_dir=None, eng_spec=None,
            inv_spec=attacked)
        mismatches = [f for f in audit["findings"]
                      if f["status"] == "SOURCE_MISMATCH" and
                      f["number_id"].startswith("PM:art:")]
        self.assertTrue(mismatches, "forged artifact hash not caught")

    def test_unclassed_parametric_number_caught(self):
        from discovery_fabric.benchmark import numerical_provenance as np
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        # ATTACK: drop the value_class on one parameter
        attacked = copy.deepcopy(new_spec)
        pmap = attacked["parametric_model"]["value"]["parameter_map"]
        pmap["outer_diameter_mm"]["value_class"] = None
        audit = np.audit_numerical_provenance(
            run_dir=None, package_dir=None, eng_spec=None,
            inv_spec=attacked)
        naked = [f for f in audit["findings"]
                 if f["status"] == "NAKED_NUMBER" and
                 f["number_id"] == "PM:outer_diameter_mm:value"]
        self.assertTrue(naked, "unclassed parametric number not caught")

    def test_physical_class_claim_rejected(self):
        from discovery_fabric.benchmark import numerical_provenance as np
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, ledger = cp.run_cad_pass(spec, out_dir=td,
                                           allow_llm=False)
        # ATTACK: relabel the section as physical observation
        attacked = copy.deepcopy(new_spec)
        attacked["parametric_model"]["epistemic_class"] = \
            "PHYSICAL_OBSERVATION"
        audit = np.audit_numerical_provenance(
            run_dir=None, package_dir=None, eng_spec=None,
            inv_spec=attacked)
        bad = [f for f in audit["findings"]
               if f["number_id"] == "PM:epistemic_class"]
        self.assertTrue(bad, "physical-evidence laundering not caught")


class TestPackageThreeDSection(unittest.TestCase):
    """The buyer package carries the 3D design only when real."""

    def _spec(self):
        spec = _spec_with_state(_dual_lumen_state())
        td = tempfile.mkdtemp()
        new_spec, _ = cp.run_cad_pass(spec, out_dir=td,
                                      allow_llm=False)
        return new_spec

    def test_section_present_with_all_ten_items(self):
        build_three_d_section = _archived_factory().build_three_d_section
        spec = self._spec()
        with tempfile.TemporaryDirectory() as td:
            section = build_three_d_section(spec, Path(td))
        self.assertTrue(section["present"])
        self.assertEqual(section["verdict"],
                         "PRESENT_AND_VALIDATED")
        names = {f["file"].split("/")[-1]
                 for f in section["files"]}
        # CEO items 1..10
        for item in ("PARAMETRIC_MODEL_SOURCE.py",
                     "KEY_DIMENSIONS.json",
                     "GEOMETRY_VALIDATION_REPORT.json",
                     "PARAMETER_MANIFEST.json",
                     "DESIGN_LINEAGE.json",
                     "TECHNICAL_EVALUATION_RESULT.json",
                     "README.json"):
            self.assertIn(item, names)
        # STEP/STL/GLB/SVG derivatives copied
        exts = {n.rsplit(".", 1)[-1] for n in names}
        self.assertIn("step", exts)
        self.assertIn("stl", exts)
        self.assertIn("glb", exts)

    def test_section_absent_without_model(self):
        build_three_d_section = _archived_factory().build_three_d_section
        spec = {"candidate_id": "X"}
        with tempfile.TemporaryDirectory() as td:
            section = build_three_d_section(spec, Path(td))
        self.assertFalse(section["present"])
        self.assertEqual(section["verdict"], "NOT_PRESENT")
        self.assertIn("never forced", section["reason"])

    def test_section_absent_when_geometry_rejected(self):
        build_three_d_section = _archived_factory().build_three_d_section
        spec = _spec_with_state(_dual_lumen_state(
            lumen_diameter_mm=1.7))
        with tempfile.TemporaryDirectory() as td:
            section = build_three_d_section(spec, Path(td))
        # no valid model -> not present (the pass rejected it)
        self.assertIn(section["verdict"],
                      ("NOT_PRESENT", "REJECTED_BY_GEOMETRY_GATES"))

    def test_no_physical_evidence_claim_in_section(self):
        build_three_d_section = _archived_factory().build_three_d_section
        spec = self._spec()
        with tempfile.TemporaryDirectory() as td:
            section = build_three_d_section(spec, Path(td))
            readme = json.loads(
                (Path(td) / "THREE_D_DESIGN" / "README.json")
                .read_text())
        self.assertEqual(
            readme["evidence_classes"]["physical_evidence"],
            "NONE — no physical observation exists in this section; "
            "manufacture and measurement are the buyer's next step "
            "(Art. XXXVIII)")


class TestTechnicalEngineIntegration(unittest.TestCase):
    """T10/K7 gates in the R379 mutation loop (hermetic, no LLM)."""

    def _ctx_with_model(self, lumen_value=1.0):
        from discovery_fabric.engine.evaluator_contract import \
            CandidateContext
        spec = _spec_with_state(_dual_lumen_state(
            lumen_diameter_mm=lumen_value))
        td = tempfile.mkdtemp()
        new_spec, _ = cp.run_cad_pass(spec, out_dir=td,
                                      allow_llm=False)
        return CandidateContext(spec=new_spec), new_spec

    def test_t10_rejects_breaching_mutation(self):
        from discovery_fabric.engine.technical_improvement_engine \
            import validate_technical_mutation
        ctx, spec = self._ctx_with_model()
        proposal = {
            "status": "OK",
            "fields": {
                "MUTATION_KIND": "GEOMETRY_CHANGE",
                "TARGET_PARAM": "lumen_diameter_mm",
                "DIRECTION": "INCREASE",
                "NEW_VALUE": "1.7",
                "VALUE_CLASS": "MODELLED",
                "MECHANISM_DELTA": "enlarging the lumen diameter "
                                    "increases drainage capacity",
                "INTERVENTION_DELTA": "the lumen diameter is enlarged "
                                      "within the extrusion envelope",
                "RATIONALE": "flow follows Poiseuille scaling"}}
        # a minimal evaluation dict naming the limiting variable
        evaluation = {"limiting_variable": {
            "param_id": "lumen_diameter_mm",
            "improving_move": "INCREASE"}}
        validation = validate_technical_mutation(
            ctx, proposal, evaluation)
        self.assertIn("t10_geometry_gate", validation["checks"])
        self.assertFalse(validation["checks"]["t10_geometry_gate"])
        self.assertFalse(validation["valid"])

    def test_t10_passes_valid_mutation(self):
        from discovery_fabric.engine.technical_improvement_engine \
            import validate_technical_mutation
        ctx, spec = self._ctx_with_model()
        proposal = {
            "status": "OK",
            "fields": {
                "MUTATION_KIND": "GEOMETRY_CHANGE",
                "TARGET_PARAM": "lumen_diameter_mm",
                "DIRECTION": "INCREASE",
                "NEW_VALUE": "1.2",
                "VALUE_CLASS": "MODELLED",
                "MECHANISM_DELTA": "enlarging the lumen diameter "
                                    "increases drainage capacity",
                "INTERVENTION_DELTA": "the lumen diameter is enlarged "
                                      "within the extrusion envelope",
                "RATIONALE": "flow follows Poiseuille scaling"}}
        evaluation = {"limiting_variable": {
            "param_id": "lumen_diameter_mm",
            "improving_move": "INCREASE"}}
        validation = validate_technical_mutation(
            ctx, proposal, evaluation)
        t10 = validation["checks"].get("t10_geometry_gate")
        self.assertTrue(t10, validation.get("reasons"))

    def test_t10_no_model_bounded_is_pass(self):
        from discovery_fabric.engine.technical_improvement_engine \
            import validate_technical_mutation
        from discovery_fabric.engine.evaluator_contract import \
            CandidateContext
        spec = _spec_with_state(_dual_lumen_state())
        ctx = CandidateContext(spec=spec)
        proposal = {
            "status": "OK",
            "fields": {
                "MUTATION_KIND": "GEOMETRY_CHANGE",
                "TARGET_PARAM": "lumen_diameter_mm",
                "DIRECTION": "INCREASE",
                "NEW_VALUE": "1.2",
                "VALUE_CLASS": "MODELLED",
                "MECHANISM_DELTA": "enlarging the lumen diameter "
                                    "increases drainage capacity",
                "INTERVENTION_DELTA": "the lumen diameter is enlarged "
                                      "within the extrusion envelope",
                "RATIONALE": "flow"}}
        evaluation = {"limiting_variable": {
            "param_id": "lumen_diameter_mm",
            "improving_move": "INCREASE"}}
        validation = validate_technical_mutation(
            ctx, proposal, evaluation)
        # state-level gates decisive, no model bound
        self.assertIn("t10_geometry_gate", validation["checks"])


class TestSourceOfTruth(unittest.TestCase):
    """The parametric definition — never the mesh — is authoritative."""

    def test_model_id_changes_with_parameters_not_with_exports(self):
        state = _dual_lumen_state()
        model, _ = cp.template_model_from_state(state,
                                                candidate_id="TEST")
        td1 = tempfile.mkdtemp()
        m1, _ = cp.build_and_validate_model(model, out_dir=td1)
        # rebuild with SAME parameters in a NEW directory: same id
        td2 = tempfile.mkdtemp()
        m2, _ = cp.build_and_validate_model(model, out_dir=td2)
        self.assertEqual(m1["model_id"], m2["model_id"])
        # mutate one parameter: different id
        m3, _ = cp.build_and_validate_model(
            cp.template_model_from_state(
                _dual_lumen_state(lumen_diameter_mm=1.2),
                candidate_id="TEST")[0], out_dir=td2)
        self.assertNotEqual(m1["model_id"], m3["model_id"])

    def test_spec_hash_invalidated_by_model_attachment(self):
        from discovery_fabric.engine.candidate import sha256_obj
        spec = _spec_with_state(_dual_lumen_state())
        h0 = sha256_obj({k: v for k, v in spec.items()
                         if not k.startswith("_")})
        spec["_spec_hash"] = h0
        td = tempfile.mkdtemp()
        new_spec, _ = cp.run_cad_pass(spec, out_dir=td,
                                      allow_llm=False)
        # the cached hash is dropped; sections may not ride stale hashes
        self.assertNotIn("_spec_hash", new_spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
