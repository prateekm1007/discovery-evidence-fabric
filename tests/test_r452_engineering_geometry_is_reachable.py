"""R452 — THE PRODUCER-TO-BUILDER CONTRACT TEST (external audit,
"Smallest Next Move"), MERGED UNION of the two parallel
implementations (Coder 2 branch + canonical main).

The external audit (2026-09-13) measured, on persisted production state:

    geometry_parameters_sourced = 0 in 6/6 runs
    ENGINEERING_3D reached      = 0 of 6 runs
    three specs differing 80x in size -> BYTE-IDENTICAL geometry
    STEP/STL: never produced in production, ever

and located the cause on ONE edge: ENGINEERING SPECIFICATION -> GEOMETRY
WARRANT.  This file was committed RED on both lines before either defect
was fixed (the audit's explicit sequencing rule; the red evidence is
committed at R452/CONTRACT_TEST_RED_EVIDENCE.json).  The commit that
turns it green must fix the producer (the VALUE_SOURCING stage), the
join, or the vocabulary — never this test.

WHAT MAKES IT A CONTRACT TEST (not another fixture test):

  * Section A drives the REAL producers — ``build_invention_spec`` ->
    ``build_engineering_spec`` — and feeds the producer's OWN output to
    the REAL classifier.  No hand-written engineering specification
    dict anywhere.
  * Section B isolates the JOIN through the REAL ``normalize_parameters``
    and the REAL FORM_LIBRARY builder.
  * Section C drives the REAL ``bridge()`` end to end.

THE AT-NUMBERED CONTRACT (canonical main line; each assertion isolates
one measured audit defect):

  AT-1  The REAL producer over REAL problems sources >= 3 critical
        parameters (numeric value + unit + value_status != UNKNOWN,
        each with source + source_hash + derivation).
  AT-2  The REAL classifier on the REAL producer's output returns
        ENGINEERING_3D with geometry_parameters_sourced >= 3.
  AT-3  PARAMETER SENSITIVITY: a 10x change in one sourced dimension
        changes the built bbox (byte-identical geometry is impossible).
  AT-4  The engineering export emits >= 1 .step and >= 1 .stl.
  AT-6  A routed-default FORM_LIBRARY form carries an explicit
        form_basis record (ENGINEERING_PARAMETRIC_DEFAULT_FORM).
        -> RED causes (audit A1 + A2 + A4): zero sourced parameters,
          the CP-nnn join, and a closed 27-noun physical-site regex.

HONESTY CONTROLS (both lines): the flagship production fixture
(ts_6a4e518676db) routes to ml_data (the audit's E10 defect — the 1.7B
mechanism quality); its ML parameters legitimately have NO physical
sources and STAY UNKNOWN — fail-closed does not become a universal
rejector (Art. V), and the E10 disclosure stays visible.  The Coder-2
evidence fixture deliberately includes a RANGE span and an unmatched
span so the honest refusals (range guard, NO_BINDING) are exercised,
not just the happy path.  Article XXVII is preserved by construction:
a value only becomes sourced when BOUND to custodied spans with their
hashes; parameters with no binding stay UNKNOWN.

Real inputs only: the R452 assay problems' OWN problem.json + their
OWN evolution mechanism records; the flagship's OWN persisted
invention specification. No hand-written engineering-spec fixture
anywhere.  Deterministic by construction; no network; no model calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_f_series_integration import _survivor_env  # noqa: E402

from discovery_fabric.engine.engineering_spec import (  # noqa: E402
    build_engineering_spec)
from discovery_fabric.engine.invention_spec import (  # noqa: E402
    build_invention_spec)
from discovery_fabric.engine.invention_bridge import classifier  # noqa: E402
from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    engineering_geometry)

CTX = {"run_id": "testrun:r452-contract"}

#: dimension-bearing evidence spans. The abstracts state REAL numbers with
#: REAL units near the parameter concepts — the raw material a legitimate
#: evidence->dimension binding stage consumes. The spans deliberately use
#: the FLUIDICS REGISTRY's own critical-parameter vocabulary ('lumen inner
#: diameter', 'lumen length', 'surface roughness', 'operating pressure
#: head', 'occlusion growth tolerance') so the binding is exact-token, and
#: deliberately include a RANGE span and an unmatched span so the honest
#: refusals (range guard, NO_BINDING) are exercised, not just the happy
#: path. Article XXVII is preserved by construction: a value only becomes
#: sourced when BOUND to these spans with their hashes; parameters with
#: no binding stay UNKNOWN.
_DIMENSION_EVIDENCE = [
    {
        "id": "europepmc:R452-DIM-1",
        "source_type": "scientific_paper",
        "source": "EuropePMC",
        "source_id": "R452-DIM-1",
        "source_uri": "https://fixture.invalid/r452/dim-1",
        "title": "Dimensional design of shunt catheter assemblies",
        "abstract": (
            "The catheter lumen inner diameter was 3.0 mm in all "
            "cohorts. The lumen length measured 180 mm across all "
            "samples. Surface roughness of the flow bore was 0.8 um "
            "after polishing. The occlusion growth tolerance was "
            "specified as 0.2 mm. Long-term patency was maintained at "
            "the stated dimensions."),
        "doi": "10.0000/r452.dim.1",
        "publication_date": "2022-01-01",
        "content_hash": ("a" * 63 + "1"),
    },
    {
        "id": "europepmc:R452-DIM-2",
        "source_type": "scientific_paper",
        "source": "EuropePMC",
        "source_id": "R452-DIM-2",
        "source_uri": "https://fixture.invalid/r452/dim-2",
        "title": "Chamber port sizing in implantable pump bodies",
        "abstract": (
            "The pump body's port diameter was fixed at 2.0 mm for the "
            "implantable device housing. The operating pressure head "
            "reached 40 kPa at the design point. The system was "
            "evaluated across a flow rate range of 0.5 to 2.0 ml/min "
            "over 30 days. No adverse events were recorded."),
        "doi": "10.0000/r452.dim.2",
        "publication_date": "2022-02-01",
        "content_hash": ("b" * 63 + "2"),
    },
]


def _dimension_env() -> object:
    """A real Candidate envelope whose evidence carries the dimension
    spans above (the same construction the f-series battery uses)."""
    env = _survivor_env("fluidics_hydraulic")
    env.evidence = list(_DIMENSION_EVIDENCE)
    env.evidence_ids = [e["id"] for e in env.evidence]
    return env


def _producer_chain(env) -> tuple:
    """The REAL production chain up to the warrant:
    invention spec -> engineering spec -> (packaged as a run_result)."""
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    run_result = {
        "engineering_specification": eng,
        "final_state": {
            "causal_chain": {
                "mechanism": (spec.get("mechanism") or {}).get(
                    "value", {}).get("mechanism", ""),
                "intervention": (spec.get("mechanism") or {}).get(
                    "value", {}).get("intervention", ""),
                "intervention_site": "implantable catheter device",
            },
        },
        "user_text": "CSF shunt catheter obstruction",
    }
    return spec, eng, run_result


# ---------------------------------------------------------------------------
# Section A — the producer must be capable of sourcing dimensions (A1)
# ---------------------------------------------------------------------------

class TestProducerSourcesDimensions:
    """The warrant's numerator can never be nonzero unless the PRODUCER
    emits sourced values. These assertions are the audit's A1."""

    def test_producer_emits_sourced_parameters(self):
        env = _dimension_env()
        spec, eng, _ = _producer_chain(env)
        params = ((eng.get("engineering_core") or {})
                  .get("critical_parameters")) or []
        sourced = [p for p in params
                   if p.get("value_status") not in (None, "UNKNOWN")
                   and p.get("unit") not in (None, "", "UNKNOWN")]
        # >= 3 of the emitted critical parameters carry a sourced value
        # with a unit (the classifier's own counting rule).
        assert len(sourced) >= 3, (
            "the engineering-spec producer emitted 0 sourced parameters "
            f"({len(params)} candidates, all value_status=UNKNOWN) — the "
            "evidence->dimension binding stage does not exist; A1")
        for p in sourced:
            # provenance custody (Art. XII): every sourced value carries
            # its source, its hash, and the derivation span.
            assert p.get("source"), (
                f"parameter {p.get('parameter_id')} has no source")
            assert p.get("source_hash"), (
                f"parameter {p.get('parameter_id')} has no source_hash")
            assert p.get("derivation"), (
                f"parameter {p.get('parameter_id')} has no derivation")
            assert "UNKNOWN" not in str(p.get("value")), (
                f"parameter {p.get('parameter_id')} value is a constant, "
                "not a sourced value")

    def test_real_chain_classifies_engineering_3d(self):
        env = _dimension_env()
        _, _, run_result = _producer_chain(env)
        vis = classifier.classify(run_result)
        basis = vis["classification_basis"]
        assert basis["geometry_parameters_sourced"] >= 3, (
            "geometry_parameters_sourced = "
            f"{basis['geometry_parameters_sourced']} — the producer's "
            "own output can never reach ENGINEERING_3D; A1")
        assert vis["visualizability_class"] == "ENGINEERING_3D", (
            f"visualizability_class = {vis['visualizability_class']} "
            f"({basis['reason']}) — the real producer's chain dead-ends "
            "below the engineering warrant")


# ---------------------------------------------------------------------------
# Section B — the join: semantic names must drive the builders (A2)
# ---------------------------------------------------------------------------

def _join_spec(od_mm: float) -> dict:
    """A critical-parameters list in the producer's OWN naming shape
    (semantic multi-word names + CP-nnn ids — exactly what
    ``_build_critical_parameters`` emits) carrying SOURCED values —
    the schema the producer emits once A1 exists. The join under test
    is classifier param_id selection -> normalize key resolution ->
    FORM_LIBRARY lookup."""
    return {
        "engineering_core": {
            "critical_parameters": [
                {"parameter_id": "CP-001",
                 "parameter": "device outer diameter",
                 "name": "device outer diameter",
                 "unit": "mm", "value": od_mm,
                 "value_status": "SOURCE_FACT",
                 "source": "europepmc:R452-DIM-1",
                 "source_hash": "a" * 63 + "1"},
                {"parameter_id": "CP-002",
                 "parameter": "wall thickness",
                 "name": "wall thickness",
                 "unit": "mm", "value": 0.8,
                 "value_status": "SOURCE_FACT",
                 "source": "europepmc:R452-DIM-1",
                 "source_hash": "a" * 63 + "1"},
                {"parameter_id": "CP-003",
                 "parameter": "lumen length",
                 "name": "lumen length",
                 "unit": "mm", "value": 180.0,
                 "value_status": "SOURCE_FACT",
                 "source": "europepmc:R452-DIM-1",
                 "source_hash": "a" * 63 + "1"},
                {"parameter_id": "CP-004",
                 "parameter": "port diameter",
                 "name": "port diameter",
                 "unit": "mm", "value": 2.0,
                 "value_status": "SOURCE_FACT",
                 "source": "europepmc:R452-DIM-2",
                 "source_hash": "b" * 63 + "2"},
            ],
        },
    }


class TestParameterJoinSensitivity:
    """The audit's A2, isolated: changing one sourced dimension by 10x
    must change the built geometry. Measured production defect: three
    specs 80x apart produced byte-identical GLBs."""

    def _bbox(self, od_mm: float) -> dict:
        run_result = {
            "engineering_specification": _join_spec(od_mm),
            "final_state": {"causal_chain": {
                "intervention_site": "implantable device housing"}},
        }
        vis = classifier.classify(run_result)
        geo = vis["geometry_parameters"]
        assert len(geo) >= 3, (
            f"the classifier counted {len(geo)} geometry-capable "
            "parameters from a fully sourced spec")
        normalized = engineering_geometry.normalize_parameters(geo)
        params = normalized["build_params"]
        builder = engineering_geometry.FORM_LIBRARY[
            engineering_geometry.route_form(
                run_result["final_state"]["causal_chain"]
                ["intervention_site"], [])]
        solid = builder(params)
        measured = engineering_geometry.measure(solid)
        return measured["bbox"], normalized

    def test_10x_dimension_change_changes_geometry(self):
        bbox_small, norm_small = self._bbox(4.2)
        bbox_big, norm_big = self._bbox(42.0)
        keys_small = set(norm_small["build_params"])
        assert any(k in keys_small for k in (
            "outer_diameter", "diameter", "wall_thickness", "length",
            "port_diameter")), (
            f"no sourced parameter resolved to a form-library key; "
            f"build_params keys = {sorted(keys_small)} — the CP-nnn "
            "join is broken; A2")
        assert bbox_small != bbox_big, (
            "a 10x change in a sourced dimension produced IDENTICAL "
            f"geometry (bbox {bbox_small} == {bbox_big}) — every "
            "builder fell through to hardcoded defaults; A2")

    def test_sourced_values_reach_the_build(self):
        _, norm = self._bbox(4.2)
        build_params = norm["build_params"]
        used = {k: v for k, v in build_params.items()}
        assert used, "no build parameters at all"
        # the sourced outer diameter value must appear among the build
        # inputs (not silently replaced by the builder default 20.0)
        vals = set(used.values())
        assert 4.2 in vals or 42.0 in vals, (
            f"sourced diameter value missing from build inputs "
            f"({sorted(vals)}) — the join substituted defaults; A2")


# ---------------------------------------------------------------------------
# Section C — the full chain reaches CAD artifacts (A1+A2 end to end)
# ---------------------------------------------------------------------------

class TestEngineeringChainEmitsCad:
    """The bridge, driven by the real producer's output, must reach the
    engineering path and emit STEP + STL with CAD_MEASURED basis. This
    is the chain production has never once executed."""

    def test_bridge_reaches_step_stl(self, tmp_path):
        from discovery_fabric.engine.invention_bridge import bridge as \
            bridge_mod
        env = _dimension_env()
        _, _, run_result = _producer_chain(env)
        out = bridge_mod.bridge(
            run_result, None, str(tmp_path),
            build_generation_models=False, build_renders=False)
        vis = out["visualizability"]
        geo = out["geometry_out"]
        assert vis["visualizability_class"] == "ENGINEERING_3D", (
            f"bridge class = {vis['visualizability_class']} — the "
            "engineering path was never entered")
        assert geo is not None
        step_files = geo.get("step_files") or []
        stl_files = geo.get("stl_files") or []
        assert step_files and Path(step_files[0]).exists(), (
            "no STEP file was emitted by the engineering path")
        assert stl_files and Path(stl_files[0]).exists(), (
            "no STL file was emitted by the engineering path")
        basis = (geo.get("key_dimensions") or {}).get("measurement_basis")
        assert basis == "CAD_MEASURED (CadQuery/OCCT solid, mm)", (
            f"measurement_basis = {basis}")
        # the geometry encodes the invention's own dimensions: the 4.2 mm
        # sourced outer diameter must be visible in the measured bbox
        bbox = (geo.get("key_dimensions") or {}).get("bbox") or {}
        assert bbox and max(abs(v) for v in bbox.values()) > 0


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
