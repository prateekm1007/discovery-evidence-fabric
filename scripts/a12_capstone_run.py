#!/usr/bin/env python3
"""scripts/a12_capstone_run.py — CEO A12 capstone runner.

E16-I TERMINOLOGY NOTE: this run is a LIVE AUTONOMOUS SOFTWARE
CAPSTONE (real literature, real LLM paths, real automatic pipeline).
The word REAL is reserved — per Article XXXVIII and CEO E16-I — for a
real buyer, a real engineer, a real experiment and real physical
observation. REAL_LOOP_VERIFIED remains FALSE for this run.

Execute ONE genuine problem through the ENTIRE system with no manual
intervention:

    REAL_EVIDENCE -> REAL_CANDIDATE -> SURVIVOR -> INVENTION_SPECIFICATION
    -> ENGINEERING_SPECIFICATION -> FULL_ENGINEERING_DOSSIER
    -> BUYER_PACKAGE -> ZIP

This is a REAL run (rehearsal=False): real EuropePMC retrieval, real LLM
synthesis (CEO-provisioned NVIDIA key), canonical package-id allocation,
and the full acceptance battery:

  - the A2 depth contract gate inside the package build
  - the A10 benchmark floor comparison (generated vs the frozen 15)
  - the A12 reader-readiness contract: a technical reader can answer,
    FROM THE PACKAGE ALONE: what the invention is / why the mechanism
    might work / what engineering must be done / what could fail / what
    must be measured / what would kill it / what the buyer receives /
    what the buyer must build / what the next experiment is.

Writes A_SERIES_ACCEPTANCE.json at repo root with the complete acceptance
table. Honesty rules (Art. XXXVIII): if the candidate does NOT survive, the
script reports REJECTED honestly — no package is fabricated. If the run
fails on infrastructure, the failure is recorded with its fix instruction.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.adapters import load_credentials  # noqa: E402
# R455-LEAN-1 reconciliation: this script's benchmark_corpus was
# retired to
# archive/r455-lean/ (ONE canonical archive; it carries a hyphen and is
# deliberately not on the import path). The archived bytes are loaded
# verbatim under their canonical module names so this kept surface
# stays importable (Art. LXIV: importable history; the r440_retired
# importlib precedent).
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[1]


def _load_archived(rel: str, name: str):
    if name in _sys.modules:
        return _sys.modules[name]
    _spec = _ilu.spec_from_file_location(name, _REPO_ROOT / rel)
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules[name] = _mod
    _spec.loader.exec_module(_mod)
    return _mod


_load_archived(
    "archive/r455-lean/discovery_fabric/engine/benchmark_corpus.py",
    "discovery_fabric.engine.benchmark_corpus")
from discovery_fabric.engine.benchmark_corpus import (  # noqa: E402
    meets_floors, measure_generated_package, load_contract)
from discovery_fabric.engine.run import EngineRun  # noqa: E402


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO),
            text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _reader_readiness(run_dir: Path, release: dict) -> dict:
    """The 9 CEO questions, each mapped to the artifact section that answers
    it, mechanically verified to be present, non-empty and invention-tied."""
    spec = json.loads((run_dir / "INVENTION_SPECIFICATION.json").read_text())
    eng = json.loads((run_dir / "ENGINEERING_SPECIFICATION.json").read_text())
    inv = (spec.get("invention_id") or {}).get("value")
    mech = (spec.get("mechanism") or {}).get("value") or {}
    gm = (eng.get("engineering_core") or {}).get("governing_model") or {}
    fas = eng.get("failure_analysis") or []
    vms = eng.get("verification_matrix") or []
    tb = eng.get("transfer_boundary") or {}
    wps = eng.get("engineering_build_plan") or []
    rc = eng.get("engineering_reasoning_chains") or {}
    ke_path = run_dir / "DECISIVE_EXPERIMENT.json"
    ke = json.loads(ke_path.read_text()) if ke_path.exists() else {}

    def _has_content(x):
        return bool(x)

    applicable_eqs = [e for e in gm.get("equations", [])
                      if (e.get("invention_tie") or {}).get("verdict")
                      in ("APPLICABLE", "CONDITIONAL")]
    checks = {
        "Q1_what_the_invention_is": {
            "section": "INVENTION_SPECIFICATION.mechanism+problem",
            "present": _has_content(mech.get("mechanism")),
            "answer_source": mech.get("intervention", "")},
        "Q2_why_the_mechanism_might_work": {
            "section": ("INVENTION_SPECIFICATION.causal_chain + "
                        "governing_model.equations (applicability-judged)"),
            "present": _has_content(mech.get("mechanism"))
            and len(applicable_eqs) >= 1,
            "answer_source": f"{len(applicable_eqs)} applicable equations; "
                             f"{rc.get('counts', {}).get('total_chains', 0)}"
                             " reasoning chains"},
        "Q3_what_engineering_must_be_done": {
            "section": "engineering_build_plan + design_outputs "
                       "(PROPOSED/UNKNOWN)",
            "present": len(wps) >= 4,
            "answer_source": f"{len(wps)} work packages"},
        "Q4_what_could_fail": {
            "section": "failure_analysis (invention-specific rows)",
            "present": len(fas) >= 3,
            "answer_source": f"{len(fas)} candidate failure modes"},
        "Q5_what_must_be_measured": {
            "section": "verification_matrix",
            "present": len(vms) >= 3,
            "answer_source": f"{len(vms)} planned verifications"},
        "Q6_what_would_kill_it": {
            "section": "kill_condition.statement",
            "present": bool((eng.get("kill_condition") or {})
                            .get("statement")),
            "answer_source": (eng.get("kill_condition") or {})
            .get("statement", "")},
        "Q7_what_the_buyer_receives": {
            "section": "transfer_boundary.buyer_receives",
            "present": len(tb.get("buyer_receives", [])) >= 5,
            "answer_source": f"{len(tb.get('buyer_receives', []))} items"},
        "Q8_what_the_buyer_must_build": {
            "section": "transfer_boundary.buyer_must_create",
            "present": len(tb.get("buyer_must_create", [])) >= 5,
            "answer_source": f"{len(tb.get('buyer_must_create', []))} items"},
        "Q9_what_the_next_experiment_is": {
            "section": "DECISIVE_EXPERIMENT.json",
            "present": bool(ke.get("selected")),
            "answer_source": str((ke.get("selected") or {})
                                 .get("name", ""))[:80]},
    }
    passed = all(c["present"] for c in checks.values())
    return {
        "invention_id": inv,
        "contract": "A12 READER-READINESS (the 9 questions a technical "
                    "reader must answer from the package alone)",
        "checks": checks,
        "passed": passed,
    }


def main() -> int:
    creds = load_credentials()
    print(f"[a12] credentials loaded: {sorted(creds.keys())}")

    import os as _os
    problem_id = _os.environ.get("A12_PROBLEM_ID", "p01")
    from discovery_fabric.a2.run import get_problem
    problem = get_problem(problem_id)
    assert problem, f"canonical problem {problem_id} missing"
    print(f"[a12] canonical problem: {problem_id} "
          f"({problem.get('device')} / {str(problem.get('failure'))[:60]})")

    # resume support: the real LLM endpoints take minutes per stage and the
    # sandbox may kill a long invocation — the F-series real run completed
    # across multiple resumed conductor invocations (completed stages are
    # NEVER re-run; EngineRun.from_run_dir restores the persisted envelope).
    import re as _re
    existing = sorted(REPO.glob("ENGINE_RUNS/A12_CAPSTONE_*"))
    resume_from = None
    for d in reversed(existing):
        if (d / "run_manifest.json").exists() and \
                not (d / "A12_COMPLETE.marker").exists():
            resume_from = d
            break

    if resume_from:
        out = resume_from
        run = EngineRun.from_run_dir(str(out), resume=True)
        print(f"[a12] RESUMING run dir: {out}")
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = REPO / "ENGINE_RUNS" / f"A12_CAPSTONE_{problem_id}_{ts}"
        run = EngineRun(problem, str(out), run_id=f"A12_CAPSTONE_{problem_id}_{ts}")
        print(f"[a12] NEW run dir: {out}")
    manifest = run.run()
    (out / "A12_COMPLETE.marker").write_text(
        datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z\n"
        + json.dumps({"final_status": manifest.get("final_status")}))

    final = json.loads((out / "final_state.json").read_text())
    release = json.loads((out / "DISCOVERY_RELEASE.json").read_text())
    print(f"[a12] final_status={final['final_status']} "
          f"release={release['status']}")

    acceptance = {
        "acceptance": "A_SERIES_ACCEPTANCE (CEO A1-A12)",
        "run_id": run.run_id,
        "run_dir": str(out),
        "final_status": final["final_status"],
        "release_status": release["status"],
        "code_commit": git_head(),
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds") + "Z",
    }

    if release["status"] == "RELEASED":
        spec = run._spec
        eng = run._eng
        rep = run.package_report
        # A10 benchmark floors on the REAL package
        measured = measure_generated_package(spec, eng, rep)
        floors = meets_floors(measured, load_contract())
        # A2 depth contract evaluation shipped in the package
        depth = json.loads(
            (Path(rep["folder"]) / "DEPTH_CONTRACT_EVALUATION.json")
            .read_text())
        # A12 reader-readiness
        readiness = _reader_readiness(out, release)
        acceptance.update({
            "AUTOMATIC_DISCOVERY_TO_INVENTION": "PASS",
            "AUTOMATIC_INVENTION_TO_ENGINEERING": "PASS",
            "AUTOMATIC_ENGINEERING_TO_DOSSIER": "PASS",
            "AUTOMATIC_DOSSIER_TO_BUYER_PACKAGE": "PASS",
            "AUTOMATIC_PACKAGE_TO_ZIP": "PASS",
            "REAL_AUTONOMOUS_RUN": ("DISCOVERY + INVENTION + ENGINEERING "
                                    "+ DOSSIER + BUYER_PACKAGE"),
            "A2_depth_contract_passed": depth["passed"],
            "A10_benchmark_floors_passed": floors["passed"],
            "A10_measured": measured,
            "A12_reader_readiness": readiness,
            "package": {"folder": rep["folder"], "zip": rep["zip"],
                        "maturity": rep["maturity"],
                        "posture": rep["posture"],
                        "reasoning_chains": eng.get(
                            "engineering_reasoning_chains", {})
                            .get("counts")},
        })
        print(f"[a12] PACKAGE RELEASED: {rep['folder']}")
        print(f"[a12] depth={depth['passed']} floors={floors['passed']} "
              f"readiness={readiness['passed']}")
    else:
        acceptance.update({
            "AUTOMATIC_DISCOVERY_TO_INVENTION": f"NOT_ACHIEVED "
                f"(final_status={final['final_status']}, "
                f"release={release['status']})",
            "failure_reason": release.get("failure_reason"),
            "honesty_note": "no package fabricated (Art. XXXVIII); see "
                            "run dir artifacts for the exact failure point",
        })
        print(f"[a12] RUN DID NOT REACH RELEASE: {release['failure_reason']}")

    (REPO / "A_SERIES_ACCEPTANCE.json").write_text(
        json.dumps(acceptance, indent=2, ensure_ascii=False))
    print(f"[a12] acceptance artifact: {REPO / 'A_SERIES_ACCEPTANCE.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
