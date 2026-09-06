#!/usr/bin/env python3
"""r413_reprobe_sfepy.py — re-probe ONLY the sfepy solver after the
Phase 5 decision + operator-authorized installation (R413 Phase 6).

PIN-PRESERVING (Art. XI): the hydraulic_network_1d probe record is the
computation log pinned by the registry's validated regime (sha256
2c86867e... over its canonical serialization). This re-probe touches
ONLY the sfepy record; every other probe stays byte-identical, and the
script ASSERTS the hydraulic pin still verifies before writing.

The new sfepy probe is stronger than IMPORT: it runs a minimal FEM
solve in a clean subprocess (proving the solver OPERATIONAL, not
merely importable) and records the runtime version (Art. LXII).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROBES = (REPO / "R413" / "PHYSICS_STACK_V1"
          / "SOLVER_AVAILABILITY_PROBES.json")

EXPECTED_HYDRAULIC_PIN = (
    "2c86867ee957496162da16ca5ceb70dc6adc647105f45d86865895a6f6eb40a5")

_MINI_SOLVE = r"""
import warnings; warnings.filterwarnings('ignore')
import json
try:
    import numpy as np
    import sfepy
    from sfepy.discrete.fem import Mesh, FEDomain, Field
    from sfepy.discrete import (FieldVariable, Material, Integral,
                                Equation, Equations, Problem)
    from sfepy.terms import Term
    from sfepy.discrete.conditions import Conditions, EssentialBC
    from sfepy.solvers.ls import ScipyDirect
    from sfepy.solvers.nls import Newton
    # minimal Laplace solve on a 2x2 quad mesh, u=0 on x=0, u=1 on x=1
    # -> the exact solution is u = x (linear gradient) which bilinear
    #    quad elements reproduce EXACTLY -> max error ~ machine eps
    #    (a real FEM solve, not an import)
    conns = [[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]]
    mesh = Mesh.from_data(
        'quad2x2',
        np.array([[0., 0.], [0.5, 0.], [1., 0.],
                  [0., 0.5], [0.5, 0.5], [1., 0.5],
                  [0., 1.], [0.5, 1.], [1., 1.]]),
        None, [conns], [[0, 0, 0, 0]], ['2_4'])
    domain = FEDomain('domain', mesh)
    omega = domain.create_region('Omega', 'all')
    gamma_l = domain.create_region('GammaL', 'vertices in x < 0.001',
                                   'facet')
    gamma_r = domain.create_region('GammaR',
                                   'vertices in x > 0.999', 'facet')
    field = Field.from_args('u', np.float64, 'scalar', omega,
                            approx_order=1)
    u = FieldVariable('u', 'unknown', field)
    v = FieldVariable('v', 'test', field, primary_var_name='u')
    m = Material('m', val=1.0)
    integral = Integral('i', order=2)
    t1 = Term.new('dw_laplace(m.val, v, u)', integral, omega, m=m,
                  v=v, u=u)
    eqs = Equations([Equation('balance', t1)])
    pb = Problem('laplace', equations=eqs)
    pb.set_bcs(ebcs=Conditions([
        EssentialBC('u_left', gamma_l, {'u.0': 0.0}),
        EssentialBC('u_right', gamma_r, {'u.0': 1.0})]))
    pb.set_solver(Newton({}, lin_solver=ScipyDirect({})))
    state = pb.solve(verbose=False)
    dofs = np.asarray(state.vec).reshape(-1)
    err = float(np.max(np.abs(dofs - mesh.coors[:, 0])))
    print(json.dumps({
        "result": "OPERATIONAL" if err < 1e-9 else "SOLVE_MISMATCH",
        "sfepy_version": sfepy.__version__,
        "mini_solve": "2D Laplace, u=0/1 Dirichlet, exact solution u=x",
        "max_abs_error": err,
    }))
except Exception as e:
    import traceback
    print(json.dumps({"result": "PROBE_CRASH",
                      "detail": repr(e)[:400],
                      "traceback_tail": traceback.format_exc()[-300:]}))
"""


def main() -> None:
    doc = json.loads(PROBES.read_text())
    hydraulic = next(p for p in doc["probes"]
                     if p["solver_id"] == "hydraulic_network_1d")
    pin = hashlib.sha256(
        json.dumps(hydraulic, sort_keys=True).encode()).hexdigest()
    assert pin == EXPECTED_HYDRAULIC_PIN, (
        f"hydraulic pin drift: {pin} != {EXPECTED_HYDRAULIC_PIN} "
        "(Art. XI — aborting, the pinned computation log must not "
        "change)")

    proc = subprocess.run([sys.executable, "-c", _MINI_SOLVE],
                          capture_output=True, text=True, timeout=300)
    out = proc.stdout.strip().splitlines()
    try:
        res = json.loads(out[-1] if out else "{}")
    except Exception:
        res = {"result": "PROBE_CRASH",
               "detail": (proc.stderr or proc.stdout)[:400]}

    new_rec = {
        "solver_id": "sfepy",
        "probe": "CLEAN_SUBPROCESS_IMPORT_AND_MINI_FEM_SOLVE",
        "target": "sfepy (minimal Laplace FEM solve with exact "
                  "solution u=x)",
        "measured_at": "2026-09-06T13:40:00Z",
        "result": ("INSTALLED" if res.get("result") == "OPERATIONAL"
                   else str(res.get("result", "PROBE_CRASH"))),
        "detail": res.get("detail", ""),
        "sfepy_version": res.get("sfepy_version"),
        "mini_solve_verification": res,
        "supersedes_probe_measured_at": "2026-09-06T12:08:42Z "
                                        "(the pre-install IMPORT probe: "
                                        "NOT_INSTALLED — preserved in "
                                        "git history if committed; this "
                                        "record replaces it in place "
                                        "with the post-install "
                                        "measurement, Art. XI: the "
                                        "change is this artifact's own "
                                        "versioned update)",
    }

    replaced = False
    for i, p in enumerate(doc["probes"]):
        if p["solver_id"] == "sfepy":
            doc["probes"][i] = new_rec
            replaced = True
    assert replaced, "sfepy probe record not found"

    # update the summary honestly
    n_installed = sum(1 for p in doc["probes"]
                      if p.get("result") == "INSTALLED")
    doc["summary"] = {
        "n_probes": len(doc["probes"]),
        "n_installed": n_installed,
        "note": "re-probed after the Phase 5 selection + operator-"
                "authorized installation of sfepy (the ONE solver); "
                "the hydraulic V0 record is byte-preserved (pin "
                f"verified: {EXPECTED_HYDRAULIC_PIN[:16]}...)",
    }

    PROBES.write_text(json.dumps(doc, indent=1) + "\n")

    # post-write assertion: the pin still verifies from the file
    doc2 = json.loads(PROBES.read_text())
    hydraulic2 = next(p for p in doc2["probes"]
                      if p["solver_id"] == "hydraulic_network_1d")
    pin2 = hashlib.sha256(
        json.dumps(hydraulic2, sort_keys=True).encode()).hexdigest()
    assert pin2 == EXPECTED_HYDRAULIC_PIN, "pin drifted after write"

    print(f"sfepy probe updated: {new_rec['result']} "
          f"(version {new_rec.get('sfepy_version')}, "
          f"mini-solve err {res.get('max_abs_error')})")
    print(f"hydraulic pin preserved: {pin2[:16]}...")
    print(f"probe results now: "
          f"{ {p['solver_id']: p['result'] for p in doc2['probes']} }"
          .replace("'", '"')[:400])


if __name__ == "__main__":
    main()
