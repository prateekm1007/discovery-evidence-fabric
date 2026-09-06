#!/usr/bin/env python3
"""r413_sfepy_instrument_validation.py — the instrument validation
replay for the newly wired solver (R413 Phase 6, the SfePy arm).

THE STANDARD (operator Phase 6): "The standard is not: 'Solver
installed.'" A solver earns a validated regime in the coverage
registry only by a deterministic closed-form replay recorded with a
computation-log pin — exactly the discipline the R394 V0 hydraulic
solver established.

THE CLOSED-FORM CASES (plane-stress linear elasticity, exactly
representable by bilinear quad elements):
    domain [0, L] x [0, H], material E, nu
    BCs:   u_x = 0 on x = 0 (the whole left edge)
           u_y = 0 at ONE vertex (0, 0)  [rigid-body removal only]
           uniform traction sigma on x = L (right edge)
    closed form:
           u_x(x, y) = sigma * x / E
           u_y(x, y) = -nu * sigma * y / E
           sigma_xx  = sigma (uniform; no stress concentration)
    A linear-in-x / constant-in-y displacement field lies inside the
    bilinear quad element space, so the FE solution must reproduce
    the closed form to near machine precision. Anything larger is an
    assembly/BC/instrument error -> the replay FAILS CLOSED.

THRESHOLD (Art. XXVII): max relative displacement error <= 1e-9,
class ENGINEERING, justification: the closed-form solution is exactly
representable in the element space; the threshold detects any
assembly, BC, or unit-conversion defect while allowing floating-point
roundoff.

Determinism (Art. LXII): linear solve; identical inputs -> identical
outputs. The replay is re-run twice here and byte-compared.

Output: R413/PHYSICS_STACK_V1/SFEPY_INSTRUMENT_VALIDATION.json
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
OUT_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
            / "SFEPY_INSTRUMENT_VALIDATION.json")

import numpy as np  # noqa: E402
import sfepy  # noqa: E402
from sfepy.discrete.fem import Mesh, FEDomain, Field  # noqa: E402
from sfepy.discrete import (FieldVariable, Material, Integral,  # noqa: E402
                            Equation, Equations, Problem)
from sfepy.terms import Term  # noqa: E402
from sfepy.discrete.conditions import Conditions, EssentialBC  # noqa
from sfepy.solvers.ls import ScipyDirect  # noqa: E402
from sfepy.solvers.nls import Newton  # noqa: E402

THRESHOLD = 1e-9

#: three cases: (name, L, H, nx, ny, E, nu, sigma)
CASES = [
    ("uniaxial-tension-A", 1.0, 0.5, 4, 2, 200e9, 0.3, 1.0e6),
    ("uniaxial-tension-B", 2.0, 1.0, 8, 4, 70e9, 0.33, -2.5e6),
    ("uniaxial-tension-C", 0.5, 2.0, 4, 8, 3.0e9, 0.4, 7.5e5),
]


def _structured_quads(L: float, H: float, nx: int, ny: int):
    """A structured bilinear quad mesh over [0,L]x[0,H]."""
    xs = np.linspace(0.0, L, nx + 1)
    ys = np.linspace(0.0, H, ny + 1)
    coors = []
    for y in ys:
        for x in xs:
            coors.append([x, y])
    coors = np.array(coors)
    conns = []
    for j in range(ny):
        for i in range(nx):
            n00 = j * (nx + 1) + i
            n10 = n00 + 1
            n01 = n00 + (nx + 1)
            n11 = n01 + 1
            conns.append([n00, n10, n11, n01])
    return coors, [conns]


def plane_stress_D(E: float, nu: float) -> np.ndarray:
    return (E / (1.0 - nu ** 2)) * np.array([
        [1.0, nu, 0.0],
        [nu, 1.0, 0.0],
        [0.0, 0.0, 0.5 * (1.0 - nu)],
    ])


def run_case(name: str, L: float, H: float, nx: int, ny: int,
             E: float, nu: float, sigma: float) -> dict:
    coors, conn_groups = _structured_quads(L, H, nx, ny)
    mesh = Mesh.from_data(name, coors, None, conn_groups,
                          [[0] * len(conn_groups[0])], ["2_4"])
    domain = FEDomain(f"domain-{name}", mesh)
    omega = domain.create_region("Omega", "all")
    eps = min(L, H) * 1e-3
    gamma_l = domain.create_region(
        "GammaL", f"vertices in x < {eps}", "facet")
    gamma_r = domain.create_region(
        "GammaR", f"vertices in x > {L - eps}", "facet")
    # the single (0,0) vertex, for u_y rigid-body removal only
    vertex00 = domain.create_region(
        "V00", f"vertices in (x < {eps}) & (y < {eps})", "vertex")

    field = Field.from_args("u", np.float64, "vector", omega,
                            approx_order=1)
    u = FieldVariable("u", "unknown", field)
    v = FieldVariable("v", "test", field, primary_var_name="u")

    m = Material("m", D=plane_stress_D(E, nu))
    # SIGN CONVENTION (measured by this replay's first fail-closed run:
    # with +sigma the FE solution came out as exactly -1x the closed
    # form): sfepy's dw_surface_ltr val enters the residual with a
    # minus sign relative to the engineering tension convention, so a
    # TENSILE traction sigma is applied as -sigma. The closed-form
    # comparison is the arbiter, not the API's sign convention.
    m_tr = Material("m_tr", val=np.array([[-sigma], [0.0]]))
    integral = Integral("i", order=2)

    t_el = Term.new("dw_lin_elastic(m.D, v, u)", integral, omega,
                    m=m, v=v, u=u)
    t_tr = Term.new("dw_surface_ltr(m_tr.val, v)", integral, gamma_r,
                    m_tr=m_tr, v=v)
    eqs = Equations([
        Equation("balance", t_el + t_tr),
    ])

    pb = Problem(name, equations=eqs)
    pb.set_bcs(ebcs=Conditions([
        EssentialBC("fix_ux", gamma_l, {"u.0": 0.0}),
        EssentialBC("fix_uy_point", vertex00, {"u.1": 0.0}),
    ]))
    pb.set_solver(Newton({}, lin_solver=ScipyDirect({})))
    state = pb.solve(verbose=False)

    dofs = np.asarray(state.vec).reshape(-1, 2)
    ux_exact = sigma * coors[:, 0] / E
    uy_exact = -nu * sigma * coors[:, 1] / E
    scale = max(np.max(np.abs(ux_exact)), np.max(np.abs(uy_exact)),
                1e-30)
    err_x = float(np.max(np.abs(dofs[:, 0] - ux_exact)))
    err_y = float(np.max(np.abs(dofs[:, 1] - uy_exact)))
    rel = float(max(err_x, err_y) / scale)
    return {
        "case": name,
        "geometry": {"L": L, "H": H, "n_elements": nx * ny,
                     "element": "bilinear quad (2_4)"},
        "load": {"sigma": sigma, "E": E, "nu": nu},
        "closed_form": {"ux": "sigma*x/E", "uy": "-nu*sigma*y/E",
                        "sigma_xx": "sigma (uniform)"},
        "max_abs_err_ux": err_x,
        "max_abs_err_uy": err_y,
        "max_rel_error": rel,
        "threshold": THRESHOLD,
        "pass": rel <= THRESHOLD,
    }


def main() -> None:
    results = [run_case(*c) for c in CASES]
    # determinism: re-run case A and compare byte-level
    rerun = run_case(*CASES[0])
    deterministic = (
        json.dumps(rerun, sort_keys=True)
        == json.dumps(results[0], sort_keys=True))
    all_pass = all(r["pass"] for r in results) and deterministic

    doc = {
        "artifact_type": "R413_SFEPY_INSTRUMENT_VALIDATION",
        "solver": "sfepy",
        "solver_version": f"sfepy/{sfepy.__version__}",
        "validated_phenomenon": "linear_elastic_deformation",
        "validated_regime": {
            "constitutive": "plane-stress linear elasticity, "
                            "homogeneous isotropic",
            "loading": "uniform uniaxial traction (no stress "
                       "concentration, no body force)",
            "mesh": "structured bilinear quads, 8..64 elements",
            "fields": "displacement (exact-representable linear "
                      "fields)",
        },
        "method": "closed-form reference replay: uniform-traction "
                  "plane-stress problems whose exact displacement "
                  "fields lie inside the element space — the FE "
                  "solution must reproduce them to floating-point "
                  "agreement",
        "threshold": {
            "name": "REFERENCE_REL_TOL",
            "value": THRESHOLD,
            "epistemic_class": "ENGINEERING",
            "justification": "the closed-form solution is exactly "
                             "representable in the bilinear element "
                             "space; the threshold detects assembly, "
                             "BC, or unit defects while allowing "
                             "roundoff (the R394 V0 discipline "
                             "applied to FEM)",
        },
        "cases": results,
        "all_cases_pass": all_pass,
        "determinism_replay": {
            "case_rerun": CASES[0][0],
            "byte_identical": deterministic,
        },
        "notes": "this replay validates the instrument for the "
                 "DECLARED REGIME ONLY (uniform traction, plane "
                 "stress, exactly-representable fields). Stress "
                 "concentrations, singularities, nonlinear materials, "
                 "and 3D remain OUTSIDE the validated regime — the "
                 "claim contract enforces this scoping "
                 "(coverage.evaluate_physics_claim).",
        "measured_at": "2026-09-06",
        "reviewer_provenance": "AI_REVIEW",
    }
    if not all_pass:
        print("VALIDATION FAILED (fail-closed — no validated regime "
              "may be registered)", file=sys.stderr)
        print(json.dumps(doc, indent=1), file=sys.stderr)
        sys.exit(1)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, indent=1) + "\n")
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(f"wrote {OUT_PATH}")
    print(f"sha256: {digest}")
    for r in results:
        print(f"  {r['case']:24s} rel_err={r['max_rel_error']:.3e} "
              f"pass={r['pass']}")
    print(f"determinism replay byte-identical: {deterministic}")


if __name__ == "__main__":
    main()
