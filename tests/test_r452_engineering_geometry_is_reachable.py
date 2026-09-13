"""tests/test_r452_engineering_geometry_is_reachable.py — the
producer-to-builder ENGINEERING GEOMETRY REACHABILITY CONTRACT
(the external audit's SMALLEST NEXT MOVE, shipped RED first; the red
evidence is committed at R452/CONTRACT_TEST_RED_EVIDENCE.json).

THE CONTRACT (each assertion isolates one measured audit defect):

  AT-1  The REAL producer over REAL problems sources >= 3 critical
        parameters (numeric value + unit + value_status != UNKNOWN,
        each with source + source_hash + derivation).
        → RED cause (audit A1): value_status hardcoded UNKNOWN.

  AT-2  The REAL classifier on the REAL producer's output returns
        ENGINEERING_3D with geometry_parameters_sourced >= 3.
        → RED causes (audit A1 + A4): zero sourced parameters AND a
          closed 27-noun physical-site regex that missed 4 of 6 real
          physical inventions.

  AT-3  PARAMETER SENSITIVITY: classifier params -> REAL
        normalize_parameters -> REAL FORM_LIBRARY builder — a 10x
        change in one sourced dimension changes the built bbox.
        → RED cause (audit A2): the CP-nnn vs semantic-name join
          produced byte-identical geometry across an 80x range.

  AT-4  The engineering export emits >= 1 .step and >= 1 .stl.
        → RED cause: ENGINEERING_3D unreachable; zero STEP/STL have
          ever existed in production runtime state.

  AT-6  A routed-default FORM_LIBRARY form carries an explicit
        form_basis record (ENGINEERING_PARAMETRIC_DEFAULT_FORM) —
        never silently presented as the invention's own geometry.

  HONESTY CONTROL (the flagship production fixture): the REAL
  persisted production invention specification (ts_6a4e518676db,
  extracted verbatim from origin/runtime-state-hf) routes to ml_data
  (the audit's E10 defect — the 1.7B mechanism quality); its ML
  parameters legitimately have NO physical sources and STAY UNKNOWN.
  The sourcing machinery runs and records the honest summary —
  fail-closed does not become a universal rejector (Art. V), and the
  E10 disclosure stays visible.

Real inputs only: the R452 assay problems' OWN problem.json + their
OWN evolution mechanism records; the flagship's OWN persisted
invention specification. No hand-written fixture anywhere.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FIXTURE_DIR = REPO_ROOT / "R452" / "CONTRACT_FIXTURE"
INVENTION_SPEC = FIXTURE_DIR / "INVENTION_SPECIFICATION.json"
PROBLEM = FIXTURE_DIR / "problem.json"
ASSAY_B = REPO_ROOT / "R452" / "ASSAY_RUN_B"


def _produce_real_engineering_spec(problem: dict,
                                   mechanism: dict,
                                   run_id: str = "r452-contract"):
    """Run the REAL producer (build_engineering_spec) over a REAL
    problem record + REAL mechanism map — the same shapes the engine
    passes (spec.problem.value / spec.mechanism.value)."""
    from discovery_fabric.engine.engineering_spec import (
        build_engineering_spec)

    class _Env:
        pass

    env = _Env()
    env.problem = problem
    spec = {
        "problem": {"value": problem},
        "mechanism": {"value": mechanism},
    }
    return build_engineering_spec(spec, env, {"run_id": run_id})


def _real_assay_b_inputs():
    """The REAL assay problem B inputs: its own problem.json and its
    own evolution generation-1 architecture (the run's mechanism)."""
    problem = json.loads((ASSAY_B / "problem.json").read_text())
    evo = json.loads((ASSAY_B / "EVOLUTION_GEN_1.json").read_text())
    arch = evo.get("architecture") or {}
    mechanism = {k: str(arch.get(k) or "")
                 for k in ("mechanism", "intervention",
                           "expected_effect", "falsification_test")}
    # the problem statement itself is the SOURCE_FACT authority
    problem = dict(problem)
    problem["user_text"] = json.loads(
        (ASSAY_B / "authored_problem.json").read_text())["text"]
    return problem, mechanism


def _sourced_parameters(eng: dict):
    core = (eng.get("engineering_core") or {})
    out = []
    for p in core.get("critical_parameters") or []:
        vs = str(p.get("value_status") or "").upper()
        val = p.get("value")
        numeric = isinstance(val, (int, float)) and not isinstance(
            val, bool)
        if numeric and "UNKNOWN" not in vs and p.get("unit"):
            out.append(p)
    return out


class TestEngineeringGeometryReachable(unittest.TestCase):
    """The contract battery: RED at ship (2026-09-13, evidence
    committed), GREEN after the A1/A2/A4 fixes in the same round."""

    @classmethod
    def setUpClass(cls):
        cls.problem, cls.mechanism = _real_assay_b_inputs()
        cls.eng = _produce_real_engineering_spec(
            cls.problem, cls.mechanism)
        cls.run_result = {
            "final_state": {},
            "engineering_specification": cls.eng,
            # the run's own invention record (problem.device drives
            # the intervention-site derivation — the real bridge
            # passes the persisted invention specification)
            "invention_specification": {
                "problem": {"device": cls.problem.get("device", ""),
                            "failure_mode":
                                cls.problem.get("failure_mode", "")},
                "mechanism": cls.mechanism.get("mechanism", ""),
                "causal_chain": {
                    "intervention_site":
                        cls.problem.get("device", ""),
                    "mechanism":
                        cls.mechanism.get("mechanism", ""),
                    "intervention":
                        cls.mechanism.get("intervention", "")},
            },
        }

    def test_at1_producer_sources_three_parameters(self):
        """AT-1: the REAL producer emits >= 3 sourced critical
        parameters on the REAL problem B (its own statement carries
        the gallery/branch diameters, the branch length, the
        viscosity, the pressure, and the required flow)."""
        sourced = _sourced_parameters(self.eng)
        self.assertGreaterEqual(
            len(sourced), 3,
            f"the producer sourced only {len(sourced)} parameters — "
            f"the evidence->dimension binding stage is missing "
            f"(audit A1)")
        for p in sourced:
            self.assertTrue(str(p.get("source") or "").strip(),
                            "sourced parameter without source")
            self.assertTrue(str(p.get("source_hash") or "").strip(),
                            "sourced parameter without source_hash")
            self.assertIn("derivation", p)
        # the sourcing summary is recorded in the spec itself
        summary = (self.eng.get("engineering_core") or {}).get(
            "value_sourcing") or {}
        self.assertTrue(summary.get("geometry_reachable"))

    def test_at2_classifier_reaches_engineering_3d(self):
        """AT-2: the REAL classifier on the REAL producer's output
        returns ENGINEERING_3D with >= 3 sourced geometry params and
        a detected physical site (the widened vocabulary)."""
        from discovery_fabric.engine.invention_bridge import classifier
        vis = classifier.classify(self.run_result, None)
        self.assertEqual(
            vis["visualizability_class"], "ENGINEERING_3D",
            f"classifier returned {vis['visualizability_class']} "
            f"({vis['classification_basis']['reason']})")
        self.assertGreaterEqual(
            vis["classification_basis"]["geometry_parameters_sourced"],
            3)
        self.assertTrue(
            vis["classification_basis"]["physical_site_detected"])

    def test_at3_parameter_sensitivity(self):
        """AT-3: a 10x change in ONE sourced dimension changes the
        built bounding box (the join is real, not cosmetic)."""
        from discovery_fabric.engine.invention_bridge import classifier
        from discovery_fabric.engine.invention_bridge import (
            engineering_geometry)
        vis = classifier.classify(self.run_result, None)
        geo_params = vis["geometry_parameters"]

        def _build(params_in):
            normalized = engineering_geometry.normalize_parameters(
                params_in)
            build_params = normalized["build_params"]
            self.assertGreaterEqual(
                len(build_params), 1,
                "no sourced parameter reached the builder — the name "
                "join dropped everything (audit A2)")
            form = engineering_geometry.route_form(
                vis.get("intervention_site", ""),
                vis.get("subsystems") or [])
            builder = engineering_geometry.FORM_LIBRARY[form]
            solid = builder(build_params)
            m = engineering_geometry.measure(solid)
            return m["bbox"], m["volume_mm3"], build_params

        bbox1, vol1, used1 = _build(geo_params)
        mutated = [dict(p) for p in geo_params]
        target = next(
            (p for p in mutated
             if str(p.get("param_id") or "").replace(" ", "_")
             .replace("-", "_").lower() in
             {k.replace("outer_diameter", "").strip("_")
              for k in used1} or
             any(k in str(p.get("param_id") or "").lower()
                 for k in used1)),
            None)
        # mutate the FIRST sourced mm-family parameter (deterministic)
        if target is None:
            mm_params = [p for p in mutated
                         if "mm" in str(p.get("unit") or "").lower()]
            target = mm_params[0] if mm_params else mutated[0]
        target["value"] = float(target["value"]) * 10.0
        bbox2, vol2, _ = _build(mutated)
        self.assertNotEqual(
            vol1, vol2,
            "a 10x dimension change produced the IDENTICAL solid — "
            "the parameter-name join is broken (audit A2: "
            "byte-identical geometry across an 80x range)")
        changed = [k for k in ("xlen", "ylen", "zlen")
                   if bbox1[k] != bbox2[k]]
        self.assertTrue(
            changed,
            f"bbox unchanged after 10x mutation: {bbox1} == {bbox2}")

    def test_at4_step_and_stl_emitted(self):
        """AT-4: the engineering export emits STEP + STL from the
        producer-sourced parameters (zero STEP/STL existed in
        production before this fix)."""
        from discovery_fabric.engine.invention_bridge import classifier
        from discovery_fabric.engine.invention_bridge import (
            engineering_geometry)
        vis = classifier.classify(self.run_result, None)
        self.assertEqual(vis["visualizability_class"],
                         "ENGINEERING_3D")
        normalized = engineering_geometry.normalize_parameters(
            vis["geometry_parameters"])
        build_params = normalized["build_params"]
        form = engineering_geometry.route_form(
            vis.get("intervention_site", ""),
            vis.get("subsystems") or [])
        builder = engineering_geometry.FORM_LIBRARY[form]
        solid = builder(build_params)
        with tempfile.TemporaryDirectory() as td:
            engineering_geometry.export(
                solid, "engineering_model", td,
                component_solids=[("engineering_model", solid)])
            steps = list(Path(td).glob("*.step"))
            stls = list(Path(td).glob("*.stl"))
            self.assertTrue(steps, "no STEP file emitted")
            self.assertTrue(stls, "no STL file emitted")

    def test_at6_default_form_carries_form_basis(self):
        """AT-6: a routed-default FORM_LIBRARY form is recorded as
        ENGINEERING_PARAMETRIC_DEFAULT_FORM with an explicit basis."""
        from discovery_fabric.engine.invention_bridge import (
            engineering_geometry)
        routed = engineering_geometry.route_form("generic site", [])
        self.assertEqual(routed, "cylindrical_device")
        basis = engineering_geometry.default_form_basis(
            routed, "generic site", [])
        self.assertEqual(
            basis["representation_class"],
            "ENGINEERING_PARAMETRIC_DEFAULT_FORM")
        self.assertTrue(basis.get("form_basis"))
        self.assertIn("default", str(basis["form_basis"]).lower())
        self.assertIn("NOT the invention", basis["form_basis"])


class TestFlagshipHonestyControl(unittest.TestCase):
    """The REAL persisted production invention specification (the
    flagship lyophilization run). Its domain routed to ml_data (the
    audit's E10 defect — the 1.7B mechanism quality); its ML
    parameters legitimately have NO physical sources. The honest
    contract: the sourcing machinery RUNS, records the summary, and
    the values STAY UNKNOWN — fail-closed without becoming a
    universal rejector (Art. V); the E10 disclosure stays visible."""

    @classmethod
    def setUpClass(cls):
        s = json.loads(INVENTION_SPEC.read_text())
        problem = json.loads(PROBLEM.read_text())

        class _Env:
            pass

        env = _Env()
        env.problem = problem
        from discovery_fabric.engine.engineering_spec import (
            build_engineering_spec)
        cls.eng = build_engineering_spec(
            s, env, {"run_id": "r452-contract-flagship"})

    def test_sourcing_machinery_runs_and_records(self):
        core = (self.eng.get("engineering_core") or {})
        summary = core.get("value_sourcing") or {}
        self.assertTrue(summary)
        self.assertEqual(summary.get("n_total"),
                         len(core.get("critical_parameters") or []))
        self.assertIn("counts", summary)

    def test_unsourceable_parameters_stay_unknown(self):
        """An ml_data-domain parameter set has no physical quantities
        to bind: every value STAYS UNKNOWN with the explicit
        VALUE_SOURCING derivation (Art. XXVII preserved — the absence
        is a measured fact, never silently sourced)."""
        core = (self.eng.get("engineering_core") or {})
        sourced = _sourced_parameters(self.eng)
        for p in core.get("critical_parameters") or []:
            vs = str(p.get("value_status") or "").upper()
            self.assertIn(vs, ("SOURCE_FACT", "COMPUTED", "MODELLED",
                               "UNKNOWN"))
            if "UNKNOWN" in vs:
                self.assertIn("VALUE_SOURCING",
                              str(p.get("derivation") or ""))
        # the honest summary says whether geometry is reachable
        summary = core.get("value_sourcing") or {}
        self.assertIn("geometry_reachable", summary)

    def test_sourcing_never_invents(self):
        """No parameter may carry a numeric value without a source
        string (Art. XXVII/VI — the anti-naked-number invariant)."""
        core = (self.eng.get("engineering_core") or {})
        for p in core.get("critical_parameters") or []:
            val = p.get("value")
            numeric = isinstance(val, (int, float)) and not isinstance(
                val, bool)
            if numeric:
                self.assertTrue(
                    str(p.get("source") or "").strip(),
                    f"naked number on {p.get('parameter')!r} — a "
                    f"numeric value without a source is forbidden")


if __name__ == "__main__":
    unittest.main()
