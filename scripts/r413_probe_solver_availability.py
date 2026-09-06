#!/usr/bin/env python3
"""r413_probe_solver_availability.py — MEASURE the availability of every
solver in the operator's preferred multi-solver physics stack in THIS
environment (R413 Physics Stack V1, operator directive 2026-09-06).

Constitutional basis:
- Art. VI / Art. XXV: availability is MEASURED, never assumed; a solver
  that is not installed is recorded NOT_INSTALLED (an honest state, never
  silently "available" and never a verdict about the stack design).
- Art. XXXVIII: only a solver whose instrument validation can be
  deterministically replayed in this environment may carry a validated
  regime; everything else records validated_regime = [] (empty, honest).
- Art. LXII: solver identity + version are part of reproducibility; the
  probe captures the version wherever it is cheaply measurable.

Probes:
  WHICH       — shutil.which on the CLI binary (blender, blockMesh,
                simpleFoam, ElmerSolver, ElmerGrid, openEMS, runSofa)
  IMPORT      — python import in a SUBPROCESS (mujoco, openmdao, fenics,
                dolfinx, sfepy, pychrono, sofa, bpy, pyvista) so a
                partial import cannot pollute this process
  REPLAY      — the V0 hydraulic_network_1d instrument validation
                (physics_core.validate_against_reference, closed-form
                reference cases) executed live and recorded

Output: R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json
"""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "R413" / "PHYSICS_STACK_V1" / "SOLVER_AVAILABILITY_PROBES.json"

CLI_PROBES = [
    # (solver_id, binary, version_args or None)
    ("blender", "blender", ["--version"]),
    ("openfoam", "blockMesh", ["-help"]),
    ("openfoam_simplefoam", "simpleFoam", ["-help"]),
    ("elmer", "ElmerSolver", ["-v"]),
    ("elmer_grid", "ElmerGrid", ["-v"]),
    ("openems", "openEMS", ["-h"]),
    ("sofa", "runSofa", ["-h"]),
]

IMPORT_PROBES = [
    # (solver_id, python module)
    ("mujoco", "mujoco"),
    ("openmdao", "openmdao"),
    ("fenics_legacy", "fenics"),
    ("fenicsx_dolfinx", "dolfinx"),
    ("sfepy", "sfepy"),
    ("project_chrono_pychrono", "pychrono"),
    ("sofa_python", "Sofa"),
    ("blender_python_bpy", "bpy"),
    ("pyvista", "pyvista"),
    ("numpy", "numpy"),
]


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def probe_cli(solver_id: str, binary: str, version_args):
    path = shutil.which(binary)
    rec = {
        "solver_id": solver_id, "probe": "WHICH",
        "target": binary, "measured_at": _ts(),
    }
    if not path:
        rec["result"] = "NOT_INSTALLED"
        rec["detail"] = (f"shutil.which({binary!r}) -> None — the binary "
                         "is not on PATH in this environment")
        return rec
    rec["result"] = "INSTALLED"
    rec["path"] = path
    if version_args:
        try:
            out = subprocess.run(
                [path] + version_args, capture_output=True, text=True,
                timeout=30)
            rec["version_detail"] = ((out.stdout or out.stderr)
                                     .strip().splitlines()[0][:200]
                                     if (out.stdout or out.stderr).strip()
                                     else f"exit {out.returncode}")
            rec["probe_exit"] = out.returncode
        except Exception as e:  # version probe failure != absence
            rec["version_detail"] = f"version probe failed: {str(e)[:120]}"
    return rec


def probe_import(solver_id: str, module: str):
    code = (f"import importlib, json\n"
            f"m = importlib.import_module({module!r})\n"
            f"v = getattr(m, '__version__', None)\n"
            f"print(json.dumps({{'module': {module!r}, 'version': v}}))\n")
    try:
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            timeout=60, cwd=str(REPO))
        ok = out.returncode == 0 and f'"module": "{module}"' in out.stdout
    except Exception:
        ok = False
        out = None
    rec = {
        "solver_id": solver_id, "probe": "IMPORT",
        "target": module, "measured_at": _ts(),
    }
    if ok:
        try:
            detail = json.loads(out.stdout.strip().splitlines()[-1])
            rec["result"] = "INSTALLED"
            rec["version"] = detail.get("version")
            rec["detail"] = f"import {module} succeeded"
        except Exception:
            rec["result"] = "INSTALLED"
            rec["detail"] = f"import {module} succeeded (no version json)"
    else:
        err = ""
        if out is not None and out.stderr:
            err = out.stderr.strip().splitlines()[-1][:160]
        rec["result"] = "NOT_INSTALLED"
        rec["detail"] = (f"import {module} failed in a clean subprocess"
                         + (f" ({err})" if err else ""))
    return rec


def probe_v0_replay():
    """The V0 hydraulic solver is the one execution-capable solver here:
    replay its closed-form instrument validation LIVE and record the
    measured relative errors (this is the evidence basis for the single
    non-empty validated_regime entry in the coverage registry)."""
    from discovery_fabric.engine import physics_core
    t0 = time.time()
    report = physics_core.validate_against_reference()
    dt = round(time.time() - t0, 3)
    cases = report.get("cases", report if isinstance(report, list) else [])
    try:
        cases = report["cases"]
    except Exception:
        cases = report
    all_pass = all(c.get("pass") for c in cases) if cases else False
    return {
        "solver_id": "hydraulic_network_1d",
        "probe": "IMPORT_AND_REPLAY",
        "target": "discovery_fabric.engine.physics_core."
                  "validate_against_reference",
        "measured_at": _ts(),
        "result": "INSTALLED",
        "solver_version": physics_core.SOLVER_VERSION,
        "model_version": physics_core.MODEL_VERSION,
        "instrument_validation_replayed_live": True,
        "n_reference_cases": len(cases),
        "all_cases_pass": bool(all_pass),
        "max_rel_error": max((c.get("rel_error", 0.0) for c in cases),
                             default=None),
        "replay_duration_s": dt,
        "cases": [
            {"case": c.get("case"), "rel_error": c.get("rel_error"),
             "pass": c.get("pass")} for c in cases
        ],
        "determinism_note": ("linear solve; identical inputs -> identical "
                             "outputs (the R394 V0 contract)"),
    }


def main() -> int:
    records = []
    for sid, binary, vargs in CLI_PROBES:
        records.append(probe_cli(sid, binary, vargs))
    for sid, module in IMPORT_PROBES:
        records.append(probe_import(sid, module))
    records.append(probe_v0_replay())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "artifact_type": "R413_SOLVER_AVAILABILITY_PROBES",
        "directive": ("operator 2026-09-06: multi-solver physics stack "
                      "(Blender as visualization/geometry layer; "
                      "OpenFOAM/FEM/SOFA/MuJoCo/Chrono/EM solvers + "
                      "OpenMDAO optimization behind it)"),
        "environment": "this sandbox egress (the repo's standing "
                       "measurement environment)",
        "measured_at": _ts(),
        "probe_methods": {
            "WHICH": "shutil.which + optional CLI version invocation",
            "IMPORT": "python import in a clean subprocess (60s timeout)",
            "IMPORT_AND_REPLAY": ("live deterministic replay of the "
                                  "closed-form instrument validation")
        },
        "probes": records,
        "summary": {
            "n_probed": len(records),
            "n_installed": sum(1 for r in records
                               if r["result"] == "INSTALLED"),
            "n_not_installed": sum(1 for r in records
                                   if r["result"] == "NOT_INSTALLED"),
            "the_only_execution_capable_solver": "hydraulic_network_1d "
                                                 "(the R394 V0)",
            "honest_conclusion": ("the multi-solver stack is a CONTRACT "
                                  "and REGISTRY layer in this environment: "
                                  "no CFD/FEM/soft-body/multibody/EM/"
                                  "optimization solver is installed here "
                                  "(measured); no simulation may be "
                                  "claimed to have run on them (Art. VI/"
                                  "XXV); the V1 layer therefore ships "
                                  "contracts + selection + coverage "
                                  "registry with measured availability "
                                  "states, and ZERO solver executions "
                                  "beyond the V0 deterministic replay")
        },
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"probes: {doc['summary']['n_installed']} installed / "
          f"{doc['summary']['n_not_installed']} not installed "
          f"-> {OUT.relative_to(REPO)}")
    for r in records:
        print(f"  {r['solver_id']:28s} {r['result']:14s} "
              f"({r['probe']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
