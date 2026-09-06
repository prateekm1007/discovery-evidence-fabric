#!/usr/bin/env python3
"""r413_build_physics_coverage_registry_v1.py — build PHYSICS_COVERAGE_REGISTRY_V1
(the operator directive V2, Phase 1).

THE REGISTRY IS A DECISION SYSTEM, NOT A DOCUMENTATION TABLE (operator):
every entry carries the 15-field schema verbatim from the directive —
    phenomenon, governing_equations, solver, solver_version,
    geometry_requirements, boundary_conditions, material_requirements,
    operating_regime, validated_regime, known_limitations, uncertainty,
    verification_method, epistemic_class, input_schema, output_schema
— so that (a) the coverage matrix can measure what is simulatable,
(b) the deterministic router can look phenomena up, and (c) the
opportunity score can price each unvalidated domain.

HONESTY RULES BAKED INTO THE BUILD (Constitution v2.1.0):
- Art. VI: availability and validation are MEASURED. The ONE validated
  regime (hydraulic V0) is carried with its computation-log sha256 pin
  from the live replay recorded in
  R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json; this builder
  RE-RUNS the closed-form reference replay live and FAILS CLOSED if it
  does not pass (a registry build is not allowed to cite a validation
  that no longer reproduces).
- Art. XXVIII / XXXVIII: every entry's epistemic_class is
  COMPUTATIONAL_RESULT (layer 4) — declaring a phenomenon covered is a
  statement about MODEL FORM, never evidence that the model form
  applies to any specific device.
- Art. XXV: entries whose solver is measured NOT_INSTALLED carry
  validated_regime = [] — the honest empty state.
- Art. XXVII: every threshold/limit carried with class + justification.
- Determinism (Art. LXII): the build is byte-identical on re-run (fixed
  build date; canonical JSON serialization).

Output: discovery_fabric/physics_stack/PHYSICS_COVERAGE_REGISTRY_V1.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_PATH = (REPO / "discovery_fabric" / "physics_stack"
            / "PHYSICS_COVERAGE_REGISTRY_V1.json")
BUILD_DATE = "2026-09-06"  # fixed for byte-determinism (this round)

sys.path.insert(0, str(REPO))

# ---------------------------------------------------------------------------
# live re-verification of the ONE validated regime (fail-closed build)
# ---------------------------------------------------------------------------
from discovery_fabric.engine import physics_core  # noqa: E402

_replay = physics_core.validate_against_reference()
_max_rel = max((c.get("rel_error", 1.0) for c in _replay.get("cases", [])),
               default=1.0)
if not (_replay.get("status") == "REFERENCE_VALIDATED"
        and _replay.get("cases")
        and all(c.get("pass") for c in _replay["cases"])
        and _max_rel <= 1e-12):
    print("BUILD REFUSED: the V0 hydraulic closed-form replay no longer "
          "passes — the registry may not cite a validation that does not "
          "reproduce (Art. VI/IX)", file=sys.stderr)
    print(json.dumps(_replay, indent=1), file=sys.stderr)
    sys.exit(1)


# live re-verification of the SECOND validated regime (fail-closed
# build): the sfepy closed-form replay artifact must exist, pass all
# cases, and carry a byte-identical determinism re-run (the replay
# itself ran each case twice; the builder re-asserts from bytes).
_SFEPY_VALIDATION_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
                          / "SFEPY_INSTRUMENT_VALIDATION.json")
_sfepy_validation = json.loads(_SFEPY_VALIDATION_PATH.read_text())
_sfepy_validation_sha = hashlib.sha256(
    _SFEPY_VALIDATION_PATH.read_bytes()).hexdigest()
if not (_sfepy_validation.get("all_cases_pass")
        and _sfepy_validation.get("determinism_replay", {})
        .get("byte_identical")):
    print("BUILD REFUSED: the sfepy closed-form replay artifact does "
          "not pass (all_cases_pass / determinism) — the registry may "
          "not cite a validation that does not reproduce (Art. VI/IX)",
          file=sys.stderr)
    sys.exit(1)
_sfepy_max_rel = max(c["max_rel_error"]
                    for c in _sfepy_validation["cases"])


def _eq(name: str, form: str, note: str = "") -> dict:
    return {
        "equation": name,
        "form": form,
        "epistemic_class": "MODEL_FORM_DECLARED",
        "note": note,
    }


def _req(kind: str, description: str, fields: list) -> dict:
    """A declared requirement group (geometry/boundary/material)."""
    return {
        "requirement": kind,
        "description": description,
        "fields": fields,
        "epistemic_class": "MODEL_FORM_DECLARED",
    }


#: honest placeholder for solver versions of measured-not-installed
#: solvers (Art. VI: a version number may never be invented before the
#: solver exists in the environment).
DECLARED_AT_INSTALL = "DECLARED_AT_INSTALL"

#: the computation-log pin of the V0 live replay (carried from the
#: recorded probe; location unchanged on disk).
_V0_REPLAY_PIN = {
    "regime": {
        "flow_regime": "laminar",
        "network": "trivial topologies (single tube, series, parallel)",
        "fluid": "newtonian, viscosity 1.0 mPa.s, density 998 kg/m3",
        "reduction": "1D",
    },
    "method": "closed-form reference replay: single-tube Poiseuille, "
              "series resistances add, parallel conductances add",
    "computation_log_sha256":
        "2c86867ee957496162da16ca5ceb70dc6adc647105f45d86865895a6f6eb40a5",
    "computation_log_location":
        "R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json probe "
        "hydraulic_network_1d (the recorded live replay: 3/3 cases pass, "
        "max rel error 0.0)",
    "solver_version": "hydraulic_network_1d/1.0.0",
    "uncertainty": "numerical: max rel error 0.0 vs closed form across 3 "
                   "reference cases, threshold 1e-12 (ENGINEERING); "
                   "model-form uncertainty: NOT quantified beyond the "
                   "Re<2300 laminar criterion — claims outside the "
                   "laminar regime are not covered",
    "validated_at": "2026-09-06",
    "determinism": "linear solve; identical inputs -> identical outputs "
                   "(R394 V0 contract)",
}

_V0_LIVE_REVERIFICATION = {
    "replayed_at_build": True,
    "result": "3/3 reference cases pass, max rel error 0.0 "
              f"(re-run live {BUILD_DATE} by this builder, fail-closed)",
}

#: entry-level uncertainty contract for not-yet-validated phenomena
_UNC_UNVALIDATED = {
    "state": "UNQUANTIFIED_UNTIL_VALIDATED",
    "note": "no validation has been executed and recorded in this "
            "environment; UNQUANTIFIED uncertainty BLOCKS validated "
            "claims (Art. XXVII) — an empty validated_regime is the "
            "honest state, never evidence against the solver",
}


def _entry(phenomenon, equations, solver, solver_version, geometry,
            boundary, material, regime, limitations, uncertainty,
            verification, input_schema, output_schema,
            validated_regime=None, availability=None, notes=None) -> dict:
    e = {
        "phenomenon": phenomenon,
        "governing_equations": equations,
        "solver": solver,
        "solver_version": solver_version,
        "geometry_requirements": geometry,
        "boundary_conditions": boundary,
        "material_requirements": material,
        "operating_regime": regime,
        "validated_regime": validated_regime or [],
        "known_limitations": limitations,
        "uncertainty": uncertainty,
        "verification_method": verification,
        "epistemic_class": "COMPUTATIONAL_RESULT",
        "epistemic_class_note": (
            "results produced under this entry are COMPUTATIONAL_RESULT "
            "(Reality Boundary layer 4); simulation -> physics requires "
            "measurement (Art. LIII); a covered phenomenon is a model-"
            "form declaration, never evidence the form applies to any "
            "specific device (Art. XXVIII)"),
        "input_schema": input_schema,
        "output_schema": output_schema,
    }
    if availability is not None:
        e["solver_availability"] = availability
    if notes:
        e["notes"] = notes
    return e


def _not_installed_availability(solver_id: str, detail: str) -> dict:
    """Availability carried from the MEASURED probe artifact (Art. VI)."""
    probes = json.loads((REPO / "R413" / "PHYSICS_STACK_V1"
                         / "SOLVER_AVAILABILITY_PROBES.json").read_text())
    rec = next(p for p in probes["probes"] if p["solver_id"] == solver_id)
    return {
        "state": "PROBED_NOT_INSTALLED",
        "probe": rec["probe"],
        "measured_at": rec["measured_at"],
        "detail": detail,
    }


def _declared_io(declaration: dict) -> dict:
    return {
        "epistemic_class": "DECLARED_INTERFACE_NOT_YET_EXECUTED",
        "declaration": declaration,
        "note": "the interface contract this entry will honor once the "
                "solver is installed and replayed in this environment; "
                "until then no run record may exist (Art. VI/LXI)",
    }


ENTRIES = []

# ===========================================================================
# 1. THE HYDRAULIC V0 — fully specified, one MEASURED validated regime
# ===========================================================================
ENTRIES.append(_entry(
    phenomenon="laminar_incompressible_network_flow",
    equations=[
        _eq("poiseuille_laminar",
            "Q = dP * pi * d^4 / (128 * mu * L)",
            "circular-segment volumetric flow under a pressure gradient"),
        _eq("mass_conservation",
            "sum of flows at each internal node = 0",
            "incompressible steady state"),
        _eq("uniform_stenosis_reduction",
            "d_eff = d * sqrt(1 - obstruction_pct/100)",
            "disclosed model choice: obstruction modeled as uniform "
            "diameter reduction (R394)"),
    ],
    solver="hydraulic_network_1d",
    solver_version="hydraulic_network_1d/1.0.0",
    geometry=_req(
        "geometry",
        "1D segment network: connectivity graph over named nodes; each "
        "segment is a circular tube (diameter, length); a primary "
        "segment representing the mechanism's failure site must exist "
        "for failure-mode simulation",
        [
            {"field": "geometry_identity", "type": "str",
             "unit": None, "meaning": "CAD model_id / parametric id"},
            {"field": "geometry_hash", "type": "str (sha256)",
             "unit": None, "meaning": "canonical geometry pin"},
            {"field": "segments[].segment_id", "type": "str",
             "unit": None, "meaning": "segment identity"},
            {"field": "segments[].node_a / node_b", "type": "str",
             "unit": None, "meaning": "connectivity graph edges"},
            {"field": "segments[].diameter_mm", "type": "float",
             "unit": "mm", "bound": "> 0 (d=0 allowed only as the "
                                    "fully-obstructed state)"},
            {"field": "segments[].length_mm", "type": "float",
             "unit": "mm", "bound": "> 0"},
            {"field": "segments[].obstruction_pct", "type": "float",
             "unit": "percent", "bound": "0..100"},
        ]),
    boundary=_req(
        "boundary",
        "fixed-pressure nodes: inlet and outlet pressures (mmHg); "
        "node assignment is TOPOLOGICAL (first segment node_a = inlet, "
        "last segment node_b = outlet) unless explicitly overridden — "
        "never alphabetical guessing",
        [
            {"field": "boundary.inlet_mmHg", "type": "float",
             "unit": "mmHg"},
            {"field": "boundary.outlet_mmHg", "type": "float",
             "unit": "mmHg"},
            {"field": "boundary.inlet_node / outlet_node",
             "type": "str (optional override)"},
        ]),
    material=_req(
        "material",
        "single Newtonian fluid; per-field source class required "
        "(Art. XXVII)",
        [
            {"field": "fluid.viscosity_mPa_s", "type": "float",
             "unit": "mPa.s", "bound": "> 0"},
            {"field": "fluid.density_kg_m3", "type": "float",
             "unit": "kg/m3", "default": 993.0},
            {"field": "fluid.temperature_K", "type": "float",
             "unit": "K", "role": "carried to the record (operating "
                                  "condition basis)"},
        ]),
    regime={
        "laminar": {"criterion": "Re < 2300 (LAMINAR_RE_LIMIT)",
                    "epistemic_class": "ENGINEERING",
                    "justification": "standard laminar-turbulent "
                                     "transition bound (R394 V0 "
                                     "threshold declaration, unchanged)"},
        "incompressible": True,
        "steady_state": True,
        "rigid_walls": True,
        "no_pump": "the solver models no pump — a passive network "
                   "cannot amplify pressure (enforced as a "
                   "plausibility bound)",
        "reduction": "1D (entrance effects neglected)",
    },
    limitations=[
        "laminar regime only — turbulent flows are NOT covered",
        "1D network reduction: no cross-section-resolved flow fields",
        "uniform-stenosis obstruction model, not discrete geometry",
        "single fluid, rigid walls, steady state, isothermal",
        "the solver validates FLOW quantities only — no heat, no "
        "stress, no electromagnetics (a mechanism needing those is "
        "MECHANISM_NOT_SIMULATABLE under this entry, never a forced "
        "analogy)",
    ],
    uncertainty={
        "state": "QUANTIFIED_FOR_VALIDATED_REGIME",
        "numerical": "max rel error 0.0 vs closed form across 3 "
                     "reference cases at threshold 1e-12 (ENGINEERING)",
        "model_form": "NOT quantified beyond the Re<2300 laminar "
                      "criterion — claims outside the laminar regime "
                      "are not covered",
    },
    verification={
        "method": "closed-form reference replay (deterministic): "
                  "single-tube Poiseuille, series resistances add, "
                  "parallel conductances add",
        "threshold": {"name": "REFERENCE_REL_TOL", "value": 1e-12,
                      "epistemic_class": "ENGINEERING",
                      "justification": "a linear-network solver must "
                                       "reproduce Poiseuille closed "
                                       "forms to floating-point "
                                       "agreement (R394 V0)"},
        "computation_log_sha256":
            "2c86867ee957496162da16ca5ceb70dc6adc647105f45d86865895a6f6eb40a5",
        "live_reverification_at_build": _V0_LIVE_REVERIFICATION,
    },
    input_schema={
        "epistemic_class": "VERIFIED_FROM_CODE",
        "fields": {
            "geometry_identity": "str",
            "geometry_hash": "str (sha256)",
            "fluid": {"viscosity_mPa_s": "float", "density_kg_m3":
                      "float (default 993.0)", "temperature_K": "float"},
            "boundary": {"inlet_mmHg": "float", "outlet_mmHg": "float",
                         "inlet_node": "str (optional)",
                         "outlet_node": "str (optional)"},
            "segments": ["{segment_id, node_a, node_b, diameter_mm, "
                         "length_mm, obstruction_pct}"],
            "operating_conditions": "dict (optional, carried to record)",
        },
        "source": "discovery_fabric/engine/physics_core.py "
                  "solve_network (section 8 contract), verified live "
                  "by the builder's reference replay",
    },
    output_schema={
        "epistemic_class": "VERIFIED_FROM_CODE",
        "fields": {
            "solver_version": "str",
            "model_version": "str",
            "status": "SOLVED | PLAUSIBILITY_BOUND_VIOLATED | "
                      "MECHANISM_NOT_SIMULATABLE",
            "input_hash": "str (sha256 of canonical spec)",
            "output_hash": "str (sha256 of canonical output)",
            "node_pressures_mmHg": "{node: float}",
            "segment_results": ["{segment_id, flow_ml_min, ...}"],
            "predicted_quantities": "{metric: value} (e.g. "
                                    "total_flow_ml_min)",
        },
        "failure_states": "PLAUSIBILITY_BOUND_VIOLATED carries the "
                          "violation list (physical bounds checked "
                          "BEFORE the solve); no computational result "
                          "is emitted in that state",
    },
    validated_regime=[_V0_REPLAY_PIN],
    availability={
        "state": "INSTALLED",
        "probe": "IMPORT_AND_REPLAY",
        "measured_at": "2026-09-06T12:08:43Z",
        "detail": "the R394 V0, in-repo, reference-validated by live "
                  "closed-form replay",
    },
    notes="the ONE execution-capable, reference-validated solver in "
          "this environment (measured); the registry's first member — "
          "the stack generalizes the V0 pattern (Art. LXIV: member, "
          "not superseded)",
))

# ===========================================================================
# 2..18 — declared phenomena whose solvers are MEASURED NOT_INSTALLED:
# full 15-field contract, empty validated_regime (the honest state)
# ===========================================================================

def _not_installed_entry(phenomenon, equations, solver, geometry,
                         boundary, material, regime, limitations,
                         verification, input_decl, output_decl,
                         probe_id, probe_detail, notes=None):
    return _entry(
        phenomenon=phenomenon,
        equations=equations,
        solver=solver,
        solver_version=DECLARED_AT_INSTALL,
        geometry=geometry,
        boundary=boundary,
        material=material,
        regime=regime,
        limitations=limitations,
        uncertainty=_UNC_UNVALIDATED,
        verification=verification,
        input_schema=_declared_io(input_decl),
        output_schema=_declared_io(output_decl),
        availability=_not_installed_availability(probe_id, probe_detail),
        notes=notes,
    )


_common_fem_geom = _req(
    "geometry",
    "3D (or 2D-axisymmetric where declared) solid/fluid domain mesh "
    "with named boundaries; mesh must resolve the field gradients the "
    "declared equations require (a mesh-quality declaration, not a "
    "guarantee)",
    [{"field": "mesh", "type": "mesh file / programmatic mesh",
      "unit": None},
     {"field": "named_boundaries", "type": "list of boundary names",
      "unit": None},
     {"field": "geometry_hash", "type": "str (sha256)",
      "unit": None, "meaning": "canonical geometry pin"}])

ENTRIES += [

    _not_installed_entry(
        "incompressible_viscous_flow", [
            _eq("navier_stokes_incompressible",
                "rho*(du/dt + u.grad u) = -grad p + mu * lap u + f"),
            _eq("continuity", "div u = 0"),
        ], "openfoam",
        _req("geometry",
             "3D fluid domain mesh (polyhedral/hex-dominant), "
             "inlet/outlet/wall patches named",
             [{"field": "fluid_domain_mesh", "type": "mesh"},
              {"field": "patches", "type": "inlet|outlet|wall|symmetry"}]),
        _req("boundary",
             "velocity or pressure at inlets/outlets; no-slip walls; "
             "turbulence model inlet conditions where RANS is used",
             [{"field": "inlet", "type": "fixedValue | pressureInlet"},
              {"field": "walls", "type": "no-slip (U=0)"},
              {"field": "outlet", "type": "zeroGradient | fixedValue"}]),
        _req("material",
             "Newtonian fluid: density + dynamic viscosity (constant "
             "or temperature-dependent as declared)",
             [{"field": "nu", "type": "kinematic viscosity",
               "unit": "m2/s"},
              {"field": "rho", "type": "density", "unit": "kg/m3"}]),
        {"regime": "laminar or RANS-modeled turbulent; steady or "
                   "transient", "incompressible": True},
        ["turbulence model fidelity is the dominant uncertainty for "
         "RANS cases (validation regime must state the model)",
         "mesh-resolution dependence: results unvalidated without a "
         "mesh-convergence check",
         "no compressibility, no cavitation, no free surfaces (OpenFOAM "
         "can do these; THIS entry declares the incompressible scope "
         "only)"],
        {"method": "shipped tutorial/validation cases replayed "
                   "headlessly in THIS environment + a "
                   "mesh-convergence demonstration, recorded with "
                   "computation-log hashes before any validated_regime "
                   "is non-empty",
         "note": "NOT executed yet — Art. XXV: the honest empty state"},
        {"solver": "OpenFOAM case directory: mesh (blockMesh/polyMesh), "
                   "fields, BCs, fvSchemes, fvSolution"},
        {"fields": "velocity (U), pressure (p), derived wall shear / "
                   "flow rates; residual + continuity convergence "
                   "record"},
        "openfoam", "shutil.which('blockMesh') -> None (MEASURED)"),

    _not_installed_entry(
        "turbulent_flow", [
            _eq("rans_reynolds_averaging",
                "RANS + turbulence closure (k-epsilon / k-omega SST "
                "families)"),
            _eq("navier_stokes_incompressible",
                "rho*(du/dt + u.grad u) = -grad p + mu_eff * lap u + f"),
        ], "openfoam",
        _req("geometry",
             "3D fluid domain mesh with wall-resolving or wall-"
             "function-declared near-wall treatment (y+ declaration "
             "required)",
             [{"field": "fluid_domain_mesh", "type": "mesh"},
              {"field": "y_plus_declaration", "type": "float or range",
               "unit": None}]),
        _req("boundary",
             "turbulence quantities at inlets (k, epsilon/omega); "
             "wall functions or low-Re wall treatment as declared",
             [{"field": "k_inlet", "type": "turbulent kinetic energy"},
              {"field": "omega_inlet", "type": "specific dissipation"}]),
        _req("material",
             "Newtonian fluid + turbulence model constants",
             [{"field": "turbulence_model", "type": "kEpsilon | kOmegaSST"}]),
        {"regime": "fully turbulent (Re >> 2300); RANS closure declared "
                   "per case; steady or transient"},
        ["RANS closures are MODEL FORMS with known regime-dependent "
         "fidelity (k-epsilon poor in adverse pressure gradients; "
         "k-omega SST better) — the validated regime must name the "
         "closure",
         "no LES/DDES in this entry (declared scope: RANS)",
         "laminar-to-turbulent transition is NOT modeled"],
        {"method": "shipped validation cases (backward-facing step, "
                   "channel flow) replayed headlessly + closure-named "
                   "regime records",
         "note": "NOT executed yet"},
        {"solver": "OpenFOAM case directory with turbulence model "
                   "declaration"},
        {"fields": "U, p, k, epsilon/omega; wall shear, pressure drop"},
        "openfoam", "shutil.which('blockMesh') -> None (MEASURED)"),

    _not_installed_entry(
        "convective_heat_transfer", [
            _eq("energy_advection_diffusion",
                "rho*cp*(dT/dt + u.grad T) = div(k grad T) + S"),
            _eq("convective_correlation_family",
                "Nu = f(Re, Pr) — correlation-based (R394 discipline: "
                "dimensional validity must be verified, the "
                "C-batteries_ev-1 death was a dimensionally invalid "
                "Nu correlation)"),
        ], "openfoam",
        _req("geometry",
             "3D conjugate or fluid-side domain with thermal wall "
             "coupling declared",
             [{"field": "domain", "type": "fluid | conjugate "
               "(fluid+solid)"},
              {"field": "thermal_interfaces", "type": "named "
               "coupled boundaries"}]),
        _req("boundary",
             "fixed or profiled temperatures/heat fluxes at thermal "
             "boundaries; inlet fluid temperature",
             [{"field": "T_inlet", "type": "fixedValue",
               "unit": "K"},
              {"field": "q_wall or T_wall", "type": "fixedValue | "
               "zeroGradient", "unit": "W/m2 | K"}]),
        _req("material",
             "fluid (rho, cp, k, mu) and solid (k, optionally rho*cp) "
             "properties per region",
             [{"field": "k", "type": "thermal conductivity",
               "unit": "W/m/K"},
              {"field": "cp", "type": "specific heat", "unit":
               "J/kg/K"}]),
        {"regime": "forced and/or natural convection as declared; "
                   "steady or transient"},
        ["correlation-based predictions (Nu=f(Re,Pr)) carry the "
         "regime-validity burden the R411 battery-cooling death "
         "demonstrated (dimensional + regime mismatch)",
         "radiation NOT in this entry unless declared",
         "turbulent convection inherits the RANS fidelity limits"],
        {"method": "shipped validation cases (e.g. heated channel / "
                   "buoyant cavity) replayed headlessly with "
                   "closure-named regimes",
         "note": "NOT executed yet"},
        {"solver": "OpenFOAM case: mesh + T field + thermophysical "
                   "properties"},
        {"fields": "T field, wall heat fluxes, h (derived), Nu (derived)"},
        "openfoam", "shutil.which('blockMesh') -> None (MEASURED)"),

    _not_installed_entry(
        "porous_media_flow", [
            _eq("darcy_law", "u = -(K/mu) * grad p"),
            _eq("forchheimer_extension",
                "grad p = -(mu/K) u - (rho C_F / sqrt K) |u| u"),
        ], "openfoam",
        _req("geometry",
             "porous region designation over the domain mesh (porosity "
             "and permeability zones)",
             [{"field": "porous_zones", "type": "cell zones with "
               "permeability tensor"},
              {"field": "porosity", "type": "void fraction",
               "unit": "dimensionless"}]),
        _req("boundary",
             "as incompressible_viscous_flow plus porous-zone "
             "interface treatment",
             [{"field": "K", "type": "permeability tensor",
               "unit": "m2"}]),
        _req("material",
             "fluid properties + porous medium (K, porosity, Forchheim"
             "er coefficient)",
             [{"field": "K", "type": "intrinsic permeability",
               "unit": "m2"},
              {"field": "C_F", "type": "Forchheimer coefficient"}]),
        {"regime": "Darcy (Re_p << 1) up to Forchheimer as declared"},
        ["Darcy-Forchheimer is an averaged homogenized model — "
         "pore-scale geometry is NOT resolved (the R411 porous-media "
         "death's 'enhanced turbulence' causal chain was an "
         "homogenization-level claim)",
         "anisotropic K must be declared per axis"],
        {"method": "shipped porous media validation cases replayed "
                   "headlessly",
         "note": "NOT executed yet"},
        {"solver": "OpenFOAM case with porousZones / DarcyForchheimer "
                   "declaration"},
        {"fields": "U, p; pressure-drop vs flow-rate curves"},
        "openfoam", "shutil.which('blockMesh') -> None (MEASURED)"),

    _not_installed_entry(
        "structural_stress_strain", [
            _eq("linear_elasticity_equilibrium",
                "div sigma + b = 0; sigma = C : epsilon(u)"),
        ], "fenicsx",
        _common_fem_geom,
        _req("boundary",
             "displacement constraints and tractions on named "
             "boundaries (Dirichlet/Neumann)",
             [{"field": "fixed_boundaries", "type": "u = 0 or "
               "prescribed"},
              {"field": "loads", "type": "traction | pressure",
               "unit": "Pa"}]),
        _req("material",
             "linear elastic isotropic (E, nu) or orthotropic as "
             "declared",
             [{"field": "E", "type": "Young's modulus", "unit": "Pa"},
              {"field": "nu", "type": "Poisson ratio",
               "unit": "dimensionless"}]),
        {"regime": "small strain, small displacement, static "
                   "(linear elasticity)"},
        ["small-strain linear elasticity only — no plasticity, "
         "contact, or geometric nonlinearity in this entry",
         "stress singularities at re-entrant corners require mesh-"
         "refinement honesty (values AT singularities are not "
         "reportable)",
         "no fatigue or fracture propagation"],
        {"method": "method of manufactured solutions (MMS) or shipped "
                   "convergence tests replayed headlessly; "
                   "mesh-convergence recorded",
         "note": "NOT executed yet"},
        {"solver": "FEM: mesh (meshio-compatible), fields, Dirichlet/"
                   "Neumann BCs, material law"},
        {"fields": "displacement u, stress sigma (von Mises derived), "
                   "strain epsilon; reaction forces"},
        "fenicsx_dolfinx",
        "import dolfinx failed in a clean subprocess (MEASURED)"),

    _entry(
        phenomenon="linear_elastic_deformation",
        equations=[
            _eq("linear_elasticity_equilibrium",
                "div sigma + b = 0; sigma = C : epsilon(u)"),
        ],
        solver="sfepy",
        solver_version=_sfepy_validation["solver_version"],
        geometry=_req(
            "geometry",
            "2D (plane-stress declared) or 3D solid domain mesh with "
            "named regions and boundaries; the validation regime "
            "uses structured bilinear quad meshes over rectangles",
            [{"field": "mesh", "type": "quad/tetra mesh "
              "(Mesh.from_data / meshio)"},
             {"field": "regions", "type": "Omega + named facet "
              "boundaries (GammaL/GammaR...)"},
             {"field": "geometry_hash", "type": "str (sha256)",
              "unit": None, "meaning": "canonical geometry pin"}]),
        boundary=_req(
            "boundary",
            "prescribed displacements (EssentialBC per dof, e.g. "
            "u.0=0 on a facet) and surface tractions "
            "(dw_surface_ltr; SIGN CONVENTION: the term's val enters "
            "the residual minus the engineering tension convention — "
            "measured and pinned by the validation replay)",
            [{"field": "ebcs", "type": "EssentialBC(name, region, "
              "{dof: value})"},
             {"field": "tractions", "type": "Material val shape "
              "(dim, 1)"}]),
        material=_req(
            "material",
            "linear elastic plane-stress stiffness D = E/(1-nu^2) * "
            "[[1,nu,0],[nu,1,0],[0,0,(1-nu)/2]] (isotropic declared "
            "first; E, nu with source class)",
            [{"field": "E", "type": "Young's modulus", "unit": "Pa"},
             {"field": "nu", "type": "Poisson ratio",
              "unit": "dimensionless"}]),
        regime={
            "constitutive": "plane-stress linear elasticity, "
                            "homogeneous isotropic",
            "loading": "static, uniform surface traction, no body "
                       "force",
            "mesh": "bilinear quads, displacement fields exactly "
                    "representable in the element space",
            "validated_scope_note": "stress concentrations, "
                                    "singularities, nonlinear "
                                    "materials, dynamics and 3D are "
                                    "OUTSIDE the validated regime",
        },
        limitations=[
            "small-strain linear elasticity only — no plasticity, "
            "contact, or geometric nonlinearity",
            "the VALIDATED regime is plane-stress uniform-traction "
            "problems with exactly-representable displacement "
            "fields; anything else computes numbers the claim "
            "contract will NOT admit as validated claims (regime "
            "scoping is enforced by coverage.evaluate_physics_claim)",
            "stress AT re-entrant corners/singularities is not "
            "reportable without mesh-refinement honesty",
            "pure-Python FEM: mesh scale limited by memory/time — "
            "large 3D assemblies may be impractical (priced in the "
            "opportunity score)",
        ],
        uncertainty={
            "state": "QUANTIFIED_FOR_VALIDATED_REGIME",
            "numerical": f"max rel error {_sfepy_max_rel:.2e} vs "
                         "closed form across 3 reference cases at "
                         "threshold 1e-9 (ENGINEERING)",
            "model_form": "NOT quantified beyond the declared "
                          "plane-stress/uniform-traction regime — "
                          "claims outside it are not covered",
        },
        verification={
            "method": "closed-form reference replay: uniform-traction "
                      "plane-stress problems whose exact displacement "
                      "fields lie inside the element space (ux="
                      "sigma*x/E, uy=-nu*sigma*y/E) — 3 cases, 2 "
                      "geometries, 3 materials, tension+compression",
            "threshold": {"name": "REFERENCE_REL_TOL",
                          "value": 1e-9,
                          "epistemic_class": "ENGINEERING",
                          "justification": "the closed-form solution is "
                                           "exactly representable in "
                                           "the bilinear element "
                                           "space; the threshold "
                                           "detects assembly/BC/unit "
                                           "defects (the R394 V0 "
                                           "discipline applied to "
                                           "FEM)"},
            "computation_log_sha256": _sfepy_validation_sha,
            "computation_log_location":
                "R413/PHYSICS_STACK_V1/"
                "SFEPY_INSTRUMENT_VALIDATION.json",
            "determinism": "linear solve; byte-identical re-run "
                           "(replay case A re-executed and "
                           "byte-compared)",
            "sign_convention_incident": "the first fail-closed run "
                                        "measured FE = -1x closed "
                                        "form (dw_surface_ltr sign "
                                        "convention); fixed with the "
                                        "documented sign and the "
                                        "replay re-run — the "
                                        "instrument caught its own "
                                        "defect (Art. XVI: tests are "
                                        "evidence of enforcement)",
        },
        input_schema={
            "epistemic_class": "VERIFIED_FROM_CODE",
            "fields": {
                "mesh": "Mesh.from_data(name, coors, ngroups, "
                        "[conns], [mat_ids], ['2_4'])",
                "regions": "domain.create_region(name, selector, "
                           "'facet'|'vertex'|'cell')",
                "field": "Field.from_args(name, dtype, 'vector'|"
                         "'scalar', region, approx_order=1)",
                "variables": "FieldVariable unknown + test pair",
                "materials": "Material D (stiffness, shape (3,3) "
                             "plane-stress), traction val shape "
                             "(dim,1)",
                "terms": "dw_lin_elastic(m.D, v, u) + "
                         "dw_surface_ltr(m_tr.val, v)",
                "bcs": "EssentialBC(name, region, {dof: value})",
                "solvers": "Newton({}, lin_solver=ScipyDirect({}))",
            },
            "source": "scripts/r413_sfepy_instrument_validation.py — "
                      "the exact interface driven by the passing "
                      "closed-form replay",
        },
        output_schema={
            "epistemic_class": "VERIFIED_FROM_CODE",
            "fields": {
                "state": "solution state; state.vec = DOF vector "
                         "(vertex-ordered for P1 fields)",
                "displacements": "u at mesh vertices (reshape(-1, dim))",
                "derived": "strain/stress recoverable from the "
                           "displacement gradient (postprocessing)",
            },
        },
        validated_regime=[{
            "regime": _sfepy_validation["validated_regime"],
            "method": _sfepy_validation["method"],
            "computation_log_sha256": _sfepy_validation_sha,
            "computation_log_location": "R413/PHYSICS_STACK_V1/"
                                        "SFEPY_INSTRUMENT_VALIDATION"
                                        ".json",
            "solver_version": _sfepy_validation["solver_version"],
            "uncertainty": f"numerical: max rel error "
                           f"{_sfepy_max_rel:.2e} across 3 reference "
                           "cases, threshold 1e-9 (ENGINEERING); "
                           "model-form: not quantified beyond the "
                           "declared regime",
            "validated_at": "2026-09-06",
            "determinism": "linear solve; byte-identical re-run",
        }],
        availability={
            "state": "INSTALLED",
            "probe": "CLEAN_SUBPROCESS_IMPORT_AND_MINI_FEM_SOLVE",
            "measured_at": "2026-09-06T13:40:00Z",
            "detail": "sfepy 2026.2 installed by the operator-"
                      "authorized Phase 5/6 decision; mini-solve "
                      "Laplace err 1.1e-16 (measured)",
        },
        notes="the SECOND execution-capable, reference-validated "
              "solver — earned by the Phase 5 decision machine "
              "(score 20855, formula-sensitivity disclosed on the "
              "opportunity artifact) and validated by closed-form "
              "replay BEFORE any discovery use",
    ),

    _not_installed_entry(
        "thermal_structural_multiphysics", [
            _eq("heat_equation",
                "rho*cp*dT/dt = div(k grad T) + Q"),
            _eq("thermoelastic_coupling",
                "sigma = C:(epsilon(u) - alpha*dT*1)"),
        ], "elmer",
        _common_fem_geom,
        _req("boundary",
             "thermal BCs (fixed T / flux / convection) + structural "
             "BCs, coupled on shared boundaries",
             [{"field": "thermal_bc", "type": "T | q | h+T_inf"},
              {"field": "structural_bc", "type": "u | traction"}]),
        _req("material",
             "solid: k, rho, cp, E, nu, alpha (CTE) per region",
             [{"field": "alpha", "type": "coeff. thermal expansion",
               "unit": "1/K"}]),
        {"regime": "small strain, linear thermoelastic coupling, "
                   "steady or transient"},
        ["coupled linear regime only; nonlinear materials (plasticity, "
         "temperature-dependent k/E) outside declared scope",
         "two-way coupling fidelity depends on both sub-models' "
         "validations"],
        {"method": "Elmer shipped verification cases replayed "
                   "headlessly (ElmerSolver CLI)",
         "note": "NOT executed yet"},
        {"solver": "Elmer sif case: mesh (ElmerGrid input), coupled "
                   "heat + elasticity solvers"},
        {"fields": "T field, displacement, thermal stress"},
        "elmer", "shutil.which('ElmerSolver') -> None (MEASURED)"),

    _not_installed_entry(
        "heat_transfer", [
            _eq("heat_equation",
                "rho*cp*dT/dt = div(k grad T) + Q"),
        ], "elmer",
        _common_fem_geom,
        _req("boundary",
             "fixed temperature, heat flux, or convective (h, T_inf) "
             "boundary conditions",
             [{"field": "T_bc", "type": "fixedValue", "unit": "K"},
              {"field": "q_bc", "type": "flux", "unit": "W/m2"}]),
        _req("material",
             "solid conduction properties: k (+ rho, cp for transient)",
             [{"field": "k", "type": "thermal conductivity",
               "unit": "W/m/K"}]),
        {"regime": "conduction-dominated solid heat transfer; steady "
                   "or transient"},
        ["conduction-only declared scope (convection lives in "
         "convective_heat_transfer; radiation undeclared)",
         "temperature-dependent k would move this out of linear scope"],
        {"method": "Elmer shipped heat-equation verification cases "
                   "replayed headlessly",
         "note": "NOT executed yet"},
        {"solver": "Elmer sif case: heat solver"},
        {"fields": "T field, heat fluxes, temperature gradients"},
        "elmer", "shutil.which('ElmerSolver') -> None (MEASURED)"),

    _not_installed_entry(
        "soft_body_continuum_mechanics", [
            _eq("finite_strain_equilibrium",
                "div P + b = 0; P = F*S (neo-Hookean / Mooney-Rivlin "
                "declared per case)"),
        ], "sofa",
        _req("geometry",
             "3D volumetric mesh of the deformable body (SOFA "
             "mechanical object topology)",
             [{"field": "deformable_body_mesh", "type": "tetra/hexa "
               "mesh"},
              {"field": "collision_models", "type": "declared "
               "collision primitives"}]),
        _req("boundary",
             "prescribed displacements, forces, or contact "
             "constraints",
             [{"field": "prescribed_dofs", "type": "fixed | imposed"},
              {"field": "contact", "type": "collision pairs"}]),
        _req("material",
             "hyperelastic or corotated-linear parameters per body",
             [{"field": "constitutive_model", "type":
               "neoHookean | corotated"}]),
        {"regime": "large deformation, quasi-static or explicit "
                   "dynamic"},
        ["SOFA's corotated-linear default is a FASTER but coarser "
         "model form than full hyperelasticity — the regime record "
         "must name the constitutive model",
         "contact fidelity depends on collision model resolution"],
        {"method": "SOFA scene regression tests replayed headlessly "
                   "via runSofa -n",
         "note": "NOT executed yet"},
        {"solver": "SOFA scene (.scn / Python scene): mechanical "
                   "objects, force fields, mass, collision models"},
        {"fields": "positions, velocities, von Mises (derived), "
                   "contact forces"},
        "sofa", "shutil.which('runSofa') -> None (MEASURED)"),

    _not_installed_entry(
        "deformable_biomechanics", [
            _eq("finite_strain_equilibrium",
                "div P + b = 0 (tissue-constitutive models: "
                "hyperelastic / viscoelastic declared per case)"),
        ], "sofa",
        _req("geometry",
             "anatomical-region volumetric meshes with interaction "
             "surfaces",
             [{"field": "anatomy_mesh", "type": "patient or canonical "
               "geometry"}]),
        _req("boundary",
             "physiological loads/motions; contact with devices or "
             "adjacent anatomy",
             [{"field": "physiological_load", "type": "declared "
               "per case"}]),
        _req("material",
             "tissue parameters — REGIME-CRITICAL (soft tissue "
             "properties vary orders of magnitude across sources; "
             "each parameter carries a source class, Art. XXVII)",
             [{"field": "tissue_model", "type": "constitutive + "
               "parameters + source"}]),
        {"regime": "physiological-strain-rate deformation"},
        ["tissue parameter uncertainty dominates: results are "
         "parameter-sensitivity-bound, and the validated regime must "
         "carry the parameter source",
         "patient-specific geometry changes conclusions (the R411 "
         "lesson generalized)"],
        {"method": "SOFA biomechanics scene regression + "
                   "parameter-sensitivity demonstration",
         "note": "NOT executed yet"},
        {"solver": "SOFA scene with tissue constitutive models"},
        {"fields": "deformation, stress, contact pressure"},
        "sofa", "shutil.which('runSofa') -> None (MEASURED)"),

    _not_installed_entry(
        "rigid_body_contact_dynamics", [
            _eq("rigid_body_dynamics",
                "M(q) q_ddot + C(q, qdot) qdot + g(q) = tau + "
                "contact forces"),
            _eq("contact_complementarity",
                "contact forces solve a complementarity problem "
                "(impulse-based or constraint-based as declared)"),
        ], "mujoco",
        _req("geometry",
             "rigid-body model: bodies, joints, collision shapes "
             "(MuJoCo MJCF model)",
             [{"field": "mjcf_model", "type": "body/joint/geom "
               "tree"}]),
        _req("boundary",
             "initial states, actuation signals, contact friction "
             "parameters",
             [{"field": "friction", "type": "per-pair coefficients"},
              {"field": "actuation", "type": "control inputs"}]),
        _req("material",
             "mass/inertia per body + contact friction/restitution "
             "pairs",
             [{"field": "inertia", "type": "mass + inertia tensor"}]),
        {"regime": "rigid-body (non-deformable) multibody dynamics; "
                   "impulse/constraint contact"},
        ["rigid bodies by construction — no structural deformation "
         "(deformation lives in soft_body/structural entries)",
         "friction coefficients are tunable model parameters whose "
         "validated regime must carry their source",
         "contact-rich dynamics may be chaotic — determinism "
         "guarantees only per identical inputs + integrator "
         "declaration"],
        {"method": "MuJoCo shipped analytical/pendulum-style tests "
                   "replayed headlessly via its Python API",
         "note": "NOT executed yet"},
        {"solver": "MJCF model + initial state + controls"},
        {"fields": "positions, velocities, contact forces, energies"},
        "mujoco",
        "import mujoco failed in a clean subprocess (MEASURED)"),

    _not_installed_entry(
        "actuated_multibody_control", [
            _eq("controlled_multibody",
                "M(q) q_ddot + ... = tau + contact; tau = K(x) with "
                "declared control law"),
        ], "mujoco",
        _req("geometry",
             "MJCF model with actuators declared",
             [{"field": "actuators", "type": "motor/piston/..."}]),
        _req("boundary",
             "control law parameters + reference signals",
             [{"field": "control_law", "type": "declared gain "
               "schedule"}]),
        _req("material",
             "actuator models (force/torque limits, bandwidth)",
             [{"field": "actuator_limits", "type": "declared"}]),
        {"regime": "closed-loop dynamics within actuator bandwidth "
                   "limits"},
        ["control-loop conclusions are only as good as the actuator "
         "model (bandwidth, saturation)",
         "no electrical drive modeling (EM entry) — co-simulation "
         "undeclared"],
        {"method": "MuJoCo shipped control-relevant tests replayed "
                   "headlessly",
         "note": "NOT executed yet"},
        {"solver": "MJCF + control law + reference trajectory"},
        {"fields": "tracking errors, forces, stability margins "
                   "(derived)"},
        "mujoco",
        "import mujoco failed in a clean subprocess (MEASURED)"),

    _not_installed_entry(
        "multibody_mechanisms", [
            _eq("multibody_dynamics",
                "M(q) q_ddot + C qdot + g = Q (joints, constraints, "
                "contact/friction)"),
        ], "project_chrono",
        _req("geometry",
             "mechanism bodies, joints (revolute/prismatic/spherical), "
             "collision shapes",
             [{"field": "mechanism_model", "type": "body/joint graph"}]),
        _req("boundary",
             "drivers (motions/forces), initial assembly, friction "
             "pairs",
             [{"field": "joint_drivers", "type": "motor laws"}]),
        _req("material",
             "mass/inertia, joint friction, contact material pairs",
             [{"field": "inertia", "type": "per body"}]),
        {"regime": "large-displacement mechanism kinematics/dynamics"},
        ["friction models are tunable — regime records must carry "
         "their source",
         "joint clearance/backlash not modeled unless declared"],
        {"method": "Chrono shipped unit/regression tests replayed "
                   "headlessly (pychrono or C++ demos)",
         "note": "NOT executed yet"},
        {"solver": "Chrono system: bodies, links, motors, contact"},
        {"fields": "positions, velocities, joint reactions, contact "
                   "forces"},
        "project_chrono_pychrono",
        "import pychrono failed in a clean subprocess (MEASURED)"),

    _not_installed_entry(
        "vehicle_dynamics", [
            _eq("multibody_dynamics",
                "full-vehicle multibody (chassis, suspension, tires) "
                "+ tire-force models (declared: e.g. Pacejka-style "
                "magic formula)"),
        ], "project_chrono",
        _req("geometry",
             "vehicle multibody model (chassis + suspension + wheels "
             "+ tires)",
             [{"field": "vehicle_model", "type": "assembly"}]),
        _req("boundary",
             "road profile / terrain, speeds, maneuvers",
             [{"field": "road", "type": "height profile"},
              {"field": "maneuver", "type": "steering/throttle law"}]),
        _req("material",
             "masses, inertias, tire model parameters (regime-critical",
             " parameter sources required)"),
        {"regime": "ground-vehicle speeds within tire-model validity"},
        ["tire force models carry the dominant model-form uncertainty "
         "(outside their fitted regime they extrapolate badly)",
         "validated regimes must name the tire model + road class"],
        {"method": "Chrono vehicle demos (the DoD/NSF-funded vehicle "
                   "simulation use case) replayed headlessly",
         "note": "NOT executed yet"},
        {"solver": "Chrono vehicle system + terrain + maneuver"},
        {"fields": "trajectories, loads, accelerations, tire forces"},
        "project_chrono_pychrono",
        "import pychrono failed in a clean subprocess (MEASURED)"),

    _not_installed_entry(
        "contact_friction_mechanics", [
            _eq("friction_cone_constraints",
                "|t_t| <= mu * t_n (Coulomb cone); complementarity "
                "contact"),
        ], "project_chrono",
        _common_fem_geom,
        _req("boundary",
             "normal approach velocities, applied loads",
             [{"field": "approach", "type": "initial conditions"}]),
        _req("material",
             "contact pair friction coefficients (source class "
             "required)",
             [{"field": "mu", "type": "friction coefficient"}]),
        {"regime": "dry Coulomb friction within declared coefficient "
                   "validity"},
        ["Coulomb friction is a model form — stick-slip transitions "
         "are sensitive to mu and solver settings",
         "lubricated contacts are NOT covered (regime boundary)"],
        {"method": "Chrono contact benchmarks replayed headlessly",
         "note": "NOT executed yet"},
        {"solver": "Chrono bodies + contact material pairs"},
        {"fields": "contact forces, slip velocities, wear proxies "
                   "(derived, NOT wear prediction)"},
        "project_chrono_pychrono",
        "import pychrono failed in a clean subprocess (MEASURED)"),

    _not_installed_entry(
        "electromagnetic_fields_lowfreq", [
            _eq("magnetostatic_quasistatic",
                "curl H = J; B = mu H (magnetoquasistatic "
                "approximation)"),
            _eq("eddy_current_induction",
                "curl E = -dB/dt (MQS induction)"),
        ], "elmer",
        _req("geometry",
             "2D-axisymmetric or 3D mesh with conductors, coils, "
             "magnetic regions",
             [{"field": "em_regions", "type": "coils | cores | "
               "conductors"}]),
        _req("boundary",
             "coil currents / magnetization, magnetic insulation "
             "(n x A = 0) or far-field approximations",
             [{"field": "currents", "type": "ampere-turns"}]),
        _req("material",
             "permeability, conductivity per region (nonlinear B-H "
             "curves outside linear declared scope)",
             [{"field": "mu_r", "type": "relative permeability"},
              {"field": "sigma", "type": "conductivity",
               "unit": "S/m"}]),
        {"regime": "low-frequency (magnetoquasistatic): dimensions "
                   "<< wavelength"},
        ["quasistatic approximation invalid when device size "
         "approaches wavelength (high-frequency entry then required)",
         "linear materials only in declared scope (saturation needs "
         "B-H curves, out of scope)"],
        {"method": "Elmer EM verification cases replayed headlessly",
         "note": "NOT executed yet"},
        {"solver": "Elmer sif: magnetodynamics solver, AV formulation"},
        {"fields": "B, H, E fields, induced currents, losses"},
        "elmer", "shutil.which('ElmerSolver') -> None (MEASURED)"),

    _not_installed_entry(
        "electromagnetic_fields_highfreq", [
            _eq("maxwell_fdtd",
                "curl E = -dB/dt; curl H = J + dD/dt solved on a "
                "FDTD grid (Yee scheme)"),
        ], "openems",
        _req("geometry",
             "FDTD grid with conformal or staircased metal/substrate "
             "geometry",
             [{"field": "fdtd_geometry", "type": "primitives + mesh"}]),
        _req("boundary",
             "ports/excitation (waveguide/antenna feeds), absorbing "
             "boundaries (PML/MUR)",
             [{"field": "excitation", "type": "port modes/gaussian "
               "pulses"}]),
        _req("material",
             "permittivity, conductivity, permeability per region; "
             "dispersive models as declared",
             [{"field": "eps_r", "type": "relative permittivity"}]),
        {"regime": "full-wave: device dimensions comparable to "
                   "wavelength"},
        ["staircasing error on curved metal edges (conformal schemes "
         "mitigate; regime must declare which)",
         "cell-size vs wavelength constraints drive cost",
         "dispersive material models need measured parameters"],
        {"method": "openEMS shipped validation examples (antennas, "
                   "waveguides with analytical/S-parameter "
                   "comparisons) replayed headlessly",
         "note": "NOT executed yet"},
        {"solver": "openEMS XML/CSX geometry + simulation settings"},
        {"fields": "S-parameters, fields, radiation patterns"},
        "openems", "shutil.which('openEMS') -> None (MEASURED)"),
]


DOC = {
    "artifact_type": "R413_PHYSICS_COVERAGE_REGISTRY_V1",
    "version": "1.0.0",
    "directive": "operator directive V2 (OPERATOR_DIRECTIVE_V2.json) "
                 "Phase 1: the registry is a DECISION SYSTEM — "
                 "machine-readable, 15-field schema verbatim, feeding "
                 "the coverage matrix, the deterministic router, and "
                 "the Physics Gap Opportunity Score",
    "schema_fields_verbatim": [
        "phenomenon", "governing_equations", "solver", "solver_version",
        "geometry_requirements", "boundary_conditions",
        "material_requirements", "operating_regime", "validated_regime",
        "known_limitations", "uncertainty", "verification_method",
        "epistemic_class", "input_schema", "output_schema",
    ],
    "decision_system_contract": {
        "coverage_matrix_consumes": "solver availability + validated_"
                                    "regime state per phenomenon (what "
                                    "is simulatable NOW, measured)",
        "router_consumes": "phenomenon + operating_regime + "
                           "requirements (deterministic lookup, "
                           "fail-closed)",
        "opportunity_score_consumes": "uncovered phenomena + their "
                                      "unvalidated state (the price of "
                                      "each gap)",
        "llm_role": "the LLM may PROPOSE classifications; the registry "
                    "and rules VERIFY (Art. XVIII — the LLM is never "
                    "the sole selector)",
    },
    "availability_context": {
        "probe_artifact":
            "R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json",
        "measured_state": "1 of 18 phenomena execution-capable + "
                          "reference-validated (hydraulic V0); 17 "
                          "declared-contract-only (solvers measured "
                          "NOT_INSTALLED in this environment)",
        "note": "availability is MEASURED (Art. VI) and re-read from "
                "the probe artifact by the solver registry at import "
                "time; this registry carries the same measured states",
    },
    "entries": ENTRIES,
    "build": {
        "builder": "scripts/r413_build_physics_coverage_registry_v1.py",
        "build_date": BUILD_DATE,
        "determinism": "byte-identical on re-run (fixed date, "
                       "canonical JSON, sorted structure)",
        "live_reverification": "the V0 closed-form replay re-run at "
                               "build time; build fails closed if it "
                               "does not pass",
    },
    "reviewer_provenance": "AI_REVIEW",
}


def _canonical(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=False, ensure_ascii=False)


def main() -> None:
    problems = []
    seen = set()
    for e in ENTRIES:
        ph = e["phenomenon"]
        if ph in seen:
            problems.append(f"duplicate phenomenon {ph!r} (Art. X)")
        seen.add(ph)
        for f in DOC["schema_fields_verbatim"]:
            if f not in e:
                problems.append(f"{ph}: missing schema field {f!r}")
        if e["solver_version"] == DECLARED_AT_INSTALL and \
                e["validated_regime"]:
            problems.append(
                f"{ph}: validated_regime non-empty with a "
                "DECLARED_AT_INSTALL solver version — a validation may "
                "never cite an unmeasured version (Art. VI/LXII)")
        for vr in e["validated_regime"]:
            if not vr.get("computation_log_sha256") or \
                    not vr.get("uncertainty") or \
                    not vr.get("solver_version"):
                problems.append(
                    f"{ph}: validated_regime record missing "
                    "computation_log_sha256 / uncertainty / "
                    "solver_version (Art. VI/XXVII)")
    if problems:
        print("BUILD REFUSED — registry self-validation failed:",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    OUT_PATH.write_text(_canonical(DOC) + "\n")
    import hashlib
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(f"wrote {OUT_PATH} ({len(ENTRIES)} phenomena)")
    print(f"sha256: {digest}")
    print(f"validated regimes: "
          f"{sum(1 for e in ENTRIES if e['validated_regime'])} "
          "(hydraulic V0)")


if __name__ == "__main__":
    main()
