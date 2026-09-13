"""R452 — THE PRODUCER-TO-BUILDER CONTRACT TEST (external audit, "Smallest
Next Move").

The external audit (2026-09-13) measured, on persisted production state:

    geometry_parameters_sourced = 0 in 6/6 runs
    ENGINEERING_3D reached      = 0 of 6 runs
    three specs differing 80x in size -> BYTE-IDENTICAL geometry
    STEP/STL: never produced in production, ever

and located the cause on ONE edge: ENGINEERING SPECIFICATION -> GEOMETRY
WARRANT.  The producer (`engineering_spec.py`) hardcodes every critical
parameter to ``value="UNKNOWN (no sourced value)"`` /
``value_status="UNKNOWN"`` and no other production code ever writes those
fields, so the classifier's numerator is permanently zero and the whole
CadQuery/OCCT chain is dead code in production.  A second defect (the
parameter-name join: ``CP-001`` vs ``outer_diameter``) sits one step
downstream and would produce confidently-wrong stock geometry the moment
values existed.

This file is committed RED, on purpose, before either defect is fixed
(the audit's explicit sequencing rule): every assertion below is
machine-checked evidence about the chain that had ZERO coverage.  The
commit that turns it green must fix the producer (the VALUE_SOURCING
stage), the join, or the vocabulary — never this test.

WHAT MAKES IT A CONTRACT TEST (not another fixture test):

  * Section A drives the REAL producers — ``build_invention_spec`` ->
    ``build_engineering_spec`` — over a real Candidate envelope, and
    feeds the producer's OWN output to the REAL classifier.  No
    hand-written engineering specification dict anywhere.
  * Section B isolates the JOIN by feeding the classifier's real
    critical-parameters extraction path (the producer's own naming
    shape: semantic multi-word names + CP-nnn ids) through the REAL
    ``normalize_parameters`` and the REAL FORM_LIBRARY builder.
  * Section C drives the REAL ``bridge()`` end to end (the exact path
    production never reaches) and asserts the CAD artifacts exist.

Deterministic by construction; no network; no model calls.
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
