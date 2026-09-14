#!/usr/bin/env python3
"""scripts/r458_mutation_proof_problem.py — the §6 proof-fixture run.

WHY A SEPARATE PROBLEM (disclosed in full, Art. XV / XXXI):
The frozen R458 benchmark corpus was authored for domain breadth and
realism; its fluid problem (F1) declares only two of the five
canonical variables the R452 mechanistic chain binds (the corpus
authoring lesson, recorded in the round record: author at least one
problem per INSTRUMENT's binding domain). The §6 directive asks for
ONE REAL candidate taken through the full causal chain — and the
R452 round's own discipline (scripts/r452_causal_loop.py, verbatim)
was: "the driver selects the assay candidate whose problem +
candidate parameters satisfy the mechanistic chain (the hydraulic
family — case B by design)" — i.e. R452 AUTHORED its binding problem
deliberately. This script follows that exact precedent:

  1. ONE hydraulic proof problem is authored with the full Poiseuille
     variable set (diameter, length, viscosity, pressure, required
     flow — all in the extractor's canonical unit forms), under the
     SAME authoring discipline as the corpus (symptoms and
     constraints only, no solution class seeded);
  2. the ENGINE runs it for real (the same engine, the same transport
     as the benchmark arms) producing a REAL candidate;
  3. scripts/r458_reality_mutation_proof.py then takes that run's
     candidate through the causal loop.

The proof problem is NOT part of the frozen benchmark corpus, is
NEVER a model-comparison surface (the dev/holdout comparison is
untouched — BS-016 intact), and its authored-for-binding status is
recorded in the proof record verbatim (never presented as a
spontaneous benchmark outcome).

Usage: python scripts/r458_mutation_proof_problem.py [budget_s]
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import r458_model_capability_benchmark as mcb  # noqa: E402

OUT_ROOT = REPO_ROOT / "R458"
PROOF_RUN_DIR = OUT_ROOT / "MUTATION_PROOF_RUN"

#: THE §6 PROOF PROBLEM (authored 2026-09-15, the R452 case-B
#: discipline: the full canonical variable set, symptoms/constraints
#: only; the LAMINAR regime verified against the solver's own
#: validity flags BEFORE the run — the first draft's water-glycol
#: numbers measured Re ~ 42,000 and were honestly discarded, Art.
#: XXXI). Variables the mechanistic chain binds: 1.2-millimetre
#: gallery (diameter), 400 millimetres (length), 180 centipoise
#: (viscosity), 2.5 bar (pressure), 40 millilitres per minute
#: (required flow).
PROOF_PROBLEM = {
    "case_id": "r458-proof-p1-spindle-hydrostatic-feed-starvation",
    "purpose": ("the §6 causal-chain proof fixture — authored with the "
                "full Poiseuille variable set BY DESIGN (the R452 "
                "case-B precedent); NOT part of the frozen benchmark "
                "corpus and never a model-comparison surface"),
    "text": (
        "A precision grinding spindle in an aerospace shaft-finishing "
        "cell runs hydrostatic bearing pockets fed by a drilled "
        "gallery inside the spindle housing: a 1.2-millimetre "
        "passage, 400 millimetres long, from the pump manifold face "
        "to the bearing pocket. The lubricant is ISO VG 46 spindle "
        "oil, but the cell's first shift starts with the oil at "
        "15 degrees Celsius, where its viscosity is 180 centipoise, "
        "and the existing gear pump delivers 2.5 bar at the gallery "
        "inlet. On cold first-shift starts the spindle's hydrostatic "
        "film collapses intermittently: the pocket pressure trace "
        "shows the bearing metal-to-metal contact flag roughly once "
        "per cold start, spindle runout doubles for the first 3 "
        "minutes, and two spindles have needed bearing pocket "
        "rescraping within 18 months, at 14,000 euros each. The "
        "bearing pocket's own design analysis requires at least 40 "
        "millilitres per minute through the gallery to hold the film "
        "at full spindle speed with cold oil. The housing's drilled "
        "gallery wall thickness allows a maximum passage diameter of "
        "2.0 millimetres before breaking into the winding slot, the "
        "pump cannot be replaced with a higher-pressure unit (the "
        "manifold block is rated for 3.0 bar), the oil specification "
        "cannot change (the bearing material pair is qualified "
        "against VG 46 additives), and the gallery length is fixed "
        "by the spindle envelope. The cell needs the gallery to "
        "deliver the required 40 millilitres per minute with the "
        "existing pump, the existing oil, and the existing spindle "
        "housing."
    ),
}


def _log(msg: str) -> None:
    print(f"[r458proof {time.strftime('%H:%M:%S')}] {msg}",
          flush=True)


def main() -> int:
    budget_s = int(sys.argv[1]) if len(sys.argv) > 1 else 2400
    arm = "glm-4-plus"     # the §6 chain needs one real candidate;
    # the model is recorded on the run; the proof is machinery-level
    PROOF_RUN_DIR.mkdir(parents=True, exist_ok=True)
    env = mcb.arm_env(arm)
    problem_json = PROOF_RUN_DIR / "fresh_problem.json"
    if not problem_json.exists():
        code = (
            "import json, sys;\n"
            "sys.path.insert(0, '.');\n"
            "from toscanini.problem_builder import build_problem;\n"
            f"built = build_problem({PROOF_PROBLEM['text']!r});\n"
            "problem = built.get('problem') if isinstance("
            "built.get('problem'), dict) else built;\n"
            f"problem['problem_id'] = {PROOF_PROBLEM['case_id']!r};\n"
            "problem['r458_mutation_proof_fixture'] = {\n"
            "    'authored_for': 'the §6 causal-chain proof "
            "(the R452 case-B discipline: full variable set by design)',\n"
            "    'not_benchmark_corpus': True,\n"
            "    'never_a_model_comparison_surface': True,\n"
            "};\n"
            f"json.dump(problem, open({str(problem_json)!r}, 'w'), "
            "indent=1)\n"
        )
        r = subprocess.run([sys.executable, "-c", code],
                           cwd=str(REPO_ROOT), env=env,
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not problem_json.exists():
            (PROOF_RUN_DIR / "problem_build_error.txt").write_text(
                r.stdout[-3000:] + "\n" + r.stderr[-3000:])
            raise SystemExit("proof problem build failed")
        _log("proof problem built through the arm route")

    if (PROOF_RUN_DIR / "final_state.json").is_file():
        _log("proof run already complete — skipping")
        return 0

    assert mcb.ensure_transport(arm), "transport unavailable"
    cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
           "--problem-json", str(problem_json),
           "--out", str(PROOF_RUN_DIR), "--no-package",
           "--run-id", "r458proof-P1: coolant-channel flow "
                       "starvation (the §6 mutation proof fixture)",
           "--session-id", "r458proof-p1"]
    if (PROOF_RUN_DIR / "problem.json").exists():
        cmd.append("--resume")
    log_fh = open(PROOF_RUN_DIR / "engine.log", "ab")
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                            stdout=log_fh, stderr=subprocess.STDOUT,
                            start_new_session=True)
    (PROOF_RUN_DIR / "ENGINE_PID").write_text(str(proc.pid))
    _log(f"detached engine pid={proc.pid}")
    start = time.time()
    while True:
        try:
            os_pid = int((PROOF_RUN_DIR / "ENGINE_PID").read_text()
                         .strip())
            alive = True
            try:
                import os as _os
                _os.kill(os_pid, 0)
            except OSError:
                alive = False
        except Exception:   # noqa: BLE001
            alive = False
        if not alive:
            _log("proof engine exited")
            try:
                (PROOF_RUN_DIR / "ENGINE_PID").unlink()
            except FileNotFoundError:
                pass
            return 0
        if time.time() - start > budget_s:
            _log(f"budget {budget_s}s reached — re-invoke to continue")
            return 0
        time.sleep(10)


if __name__ == "__main__":
    raise SystemExit(main())
