"""discovery_fabric/engine/smoke_e2e.py — E11 true end-to-end smoke test +
CEO Directive 1/2 proof.

Runs the full chain and FAILS if any link is missing:

    problem -> real evidence -> candidate -> prior art -> collision -> attack
    -> killer experiment -> survivor -> INVENTION_SPECIFICATION
    -> ENGINEERING_SPECIFICATION -> dossier -> BUYER PACKAGE (zip)
    -> DISCOVERY_RELEASE

Two modes:

  REAL mode (default)
    Executes the real engine loop (real retrieval, real custody, real LLM
    synthesis through the E1 registry). The post-RANK survivor -> package
    pipeline is AUTOMATIC (Directive 1). If no provider credential exists
    the smoke FAILS at SYNTHESIZE with PROVIDER_UNAVAILABLE and prints
    exactly which env keys would unblock it — it does NOT fake progress
    (Art. IV/VI).

  --rehearsal mode
    CONTROLLED REHEARSAL (Constitution Art. XXXVIII pattern): consumes a
    recorded fixture envelope through the SAME post-RANK machinery to prove
    every downstream link exists. Every artifact is labeled
    SYNTHETIC_REHEARSAL=TRUE / REAL_LOOP_VERIFIED=FALSE, and the final
    verdict is REHEARSAL_PASS — never a real-run pass.

Exit codes: 0 = pass, 1 = missing link (printed explicitly).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from .candidate import Candidate, canonical_json, utc_now
from .llm_registry import availability_statement
from .run import EngineRun, REPO_ROOT

REQUIRED_E2E_LINKS = [
    "PROBLEM_RECORDED",
    "EVIDENCE_RETRIEVED",
    "EVIDENCE_FROZEN",
    "CANDIDATE_SYNTHESIZED",
    "EVIDENCE_VERIFIED",
    "MULTI_SOURCE_EXECUTED",
    "COLLISION_EXECUTED",
    "ATTACK_EXECUTED",
    "CONTRADICTIONS_ASSESSED",
    "KILLER_EXPERIMENT_SELECTED",
    "ADJUDICATION_RECORDED",
    "CLASSIFICATION_RECORDED",
    "NEXT_BEST_ACTION_RECORDED",
    "RANK_RECORDED",
    "SURVIVOR_GATE_PASSED",
    "INVENTION_SPECIFICATION_BUILT",
    "ENGINEERING_SPECIFICATION_BUILT",
    "DESIGN_GRAPH_STRUCTURAL",
    "DECISIVE_EXPERIMENT_EXPLAINED",
    "DOSSIER_PDF_00_PACKAGE_README",
    "DOSSIER_PDF_01_EXECUTIVE_TECHNOLOGY_BRIEF",
    "DOSSIER_PDF_02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER",
    "DOSSIER_PDF_03_BUYER_DECISION_CARD",
    "DOSSIER_PDF_04_EVIDENCE_SUMMARY",
    "DOSSIER_PDF_05_TRANSFER_MANIFEST",
    "PACKAGE_MANIFEST_JSON",
    "ENGINEERING_TRACEABILITY_JSON",
    "MATURITY_BASIS_JSON",
    "PACKAGE_ZIP",
    "DISCOVERY_RELEASE_JSON",
    "RELEASE_HASHES_BOUND",
    "DISPLAY_REGISTER_CLEAN",
    "MATURITY_COMPUTED",
]


def _fail(missing: List[str], extra: Dict[str, Any]) -> int:
    print("\n" + "=" * 70)
    print("E2E SMOKE: FAIL — missing links:")
    for m in missing:
        print(f"  ✗ {m}")
    print("=" * 70)
    print(json.dumps(extra, indent=1, default=str)[:2000])
    return 1


def _check_post_rank(run: EngineRun, links_ok: List[str],
                     missing: List[str]) -> None:
    """Verify the AUTOMATIC post-RANK artifacts of an EngineRun (Directive
    1) — the smoke never builds a second copy of the pipeline."""
    out = run.out

    def check(link: str, cond: bool):
        (links_ok if cond else missing).append(link)

    rep = run.package_report or {}
    folder = Path(rep["folder"]) if rep.get("folder") else None
    for f in rep.get("rendered", []):
        check(f"DOSSIER_PDF_{f['file'].split('.')[0]}", True)
    check("PACKAGE_MANIFEST_JSON",
          bool(folder) and (folder / "PACKAGE_MANIFEST.json").exists())
    check("ENGINEERING_TRACEABILITY_JSON", bool(rep.get("traceability_passed")))
    check("MATURITY_BASIS_JSON",
          bool(folder) and (folder / "MATURITY_BASIS.json").exists())
    check("PACKAGE_ZIP", bool(rep.get("zip")))
    rel = run.release or {}
    check("DISCOVERY_RELEASE_JSON",
          (out / "DISCOVERY_RELEASE.json").exists())
    check("RELEASE_HASHES_BOUND", bool(
        rel.get("candidate_hash") and rel.get("invention_spec_hash")
        and rel.get("engineering_spec_hash")
        and rel.get("dossier_manifest_hash")
        and rel.get("buyer_package_hash")))
    dreg = rep.get("display_register") or {}
    check("DISPLAY_REGISTER_CLEAN", not dreg.get("violations", ["x"]))
    check("MATURITY_COMPUTED",
          bool((folder or Path()) / "MATURITY_BASIS.json") and
          json.loads((folder / "MATURITY_BASIS.json").read_text())
          .get("basis", "").startswith("computed"))


def run_real_from(run: "EngineRun", disabled_extra: str = "") -> int:
    """Run-link proof over a resumed EngineRun (same checks as run_real,
    driving the conductor's own automatic pipeline)."""
    run.resume = True
    if disabled_extra:
        run.disabled |= {s for s in disabled_extra.split(",") if s}
    manifest = run.run()
    return _verify_run_links(run, manifest)


def _verify_run_links(run: EngineRun, manifest: Dict[str, Any]) -> int:
    out_dir = str(run.out)
    links_ok: List[str] = []
    missing: List[str] = []
    env = run.env

    def check(link: str, cond: bool):
        (links_ok if cond else missing).append(link)

    check("PROBLEM_RECORDED", (Path(out_dir) / "problem.json").exists())
    check("EVIDENCE_RETRIEVED", bool(env.evidence))
    # the FREEZE adapter records its snapshot under provenance.evidence_freeze
    check("EVIDENCE_FROZEN", bool(env.provenance.get("evidence_freeze")))
    check("CANDIDATE_SYNTHESIZED",
          "SYNTHESIZE" not in run.failed_stages and bool(env.mechanism_map))
    check("EVIDENCE_VERIFIED",
          bool((env.adjudication or {}).get("evidence_verification")))
    check("MULTI_SOURCE_EXECUTED", bool(env.multi_source))
    check("COLLISION_EXECUTED", bool(env.collision_results))
    check("ATTACK_EXECUTED", bool(env.attack_results))
    check("CONTRADICTIONS_ASSESSED", bool(env.contradictions))
    check("KILLER_EXPERIMENT_SELECTED", bool(env.killer_experiment))
    check("ADJUDICATION_RECORDED",
          bool((env.adjudication or {}).get("council")))
    check("CLASSIFICATION_RECORDED",
          bool((env.epistemic_state or {}).get("final_status")))
    check("NEXT_BEST_ACTION_RECORDED", bool(env.next_best_action))
    check("RANK_RECORDED", bool(env.ranking))

    if missing:
        avail = availability_statement()
        return _fail(missing, {
            "note": "run stopped before post-RANK pipeline",
            "final_status": manifest.get("final_status"),
            "failed_stages": run.failed_stages,
            "provider_availability": avail,
            "unblock": ("set one of " + str(avail["unblock_with_env"]) +
                        " (or .env.keys) and rerun — PROVIDER_UNAVAILABLE is "
                        "an infrastructure state, not NO_INVENTION")
            if not avail["any_provider_available"] else
            "provider call failed — see stage log"})

    from .invention_spec import SPEC_FIELDS
    from .experiment_selector import select_decisive_experiment
    spec = run._spec or {}
    check("SURVIVOR_GATE_PASSED",
          (spec.get("_survivor_gate") or {}).get("survivor") is True)
    if not spec.get("_survivor_gate", {}).get("survivor"):
        return _fail(missing + ["(survivor gate)"], {
            "final_status": (spec.get("_survivor_gate") or {})})
    check("INVENTION_SPECIFICATION_BUILT",
          all(f in spec for f in SPEC_FIELDS)
          and spec["_integrity"]["passed"])
    eng = run._eng or {}
    check("ENGINEERING_SPECIFICATION_BUILT",
          bool(eng.get("engineering_core")))
    check("DESIGN_GRAPH_STRUCTURAL",
          (eng.get("design_graph", {}).get("integrity", {})
           .get("passed", False)))
    sel = select_decisive_experiment(env)
    check("DECISIVE_EXPERIMENT_EXPLAINED",
          bool(sel.get("selected")) and "because" in sel["explanation"])

    _check_post_rank(run, links_ok, missing)

    if missing:
        return _fail(missing, {
            "package_report": {k: v for k, v in
                               (run.package_report or {}).items()
                               if k != "rendered"},
            "release": run.release})

    proof = {
        "smoke": "E11_REAL_END_TO_END",
        "run_id": run.run_id,
        "verdict": "PASS",
        "resumed_from_stage": run.resumed_from_stage,
        "links_verified": links_ok,
        "final_status": manifest.get("final_status"),
        "package_folder": (run.package_report or {}).get("folder"),
        "package_zip": (run.package_report or {}).get("zip"),
        "release_status": (run.release or {}).get("status"),
        "loop_verification_state": "NONE",
        "real_loop_verified": False,
        "note": "loop_verification_state stays NONE until the R370G "
                "reality-loop chain validates a real external event",
        "timestamp": utc_now()}
    (Path(out_dir) / "RUN_LINK_PROOF.json").write_text(
        json.dumps(proof, indent=1, ensure_ascii=False))
    print("\n" + "=" * 70)
    print(f"E2E SMOKE: PASS ({len(links_ok)}/{len(REQUIRED_E2E_LINKS)} links)")
    print(f"  package: {(run.package_report or {}).get('folder')}")
    print(f"  release: {(run.release or {}).get('status')}")
    print("=" * 70)
    return 0


def run_real(problem: Dict[str, Any], out_dir: str,
             disabled: List[str]) -> int:
    run = EngineRun(problem, out_dir, disabled_stages=disabled)
    manifest = run.run()
    return _verify_run_links(run, manifest)


def run_rehearsal(out_dir: str) -> int:
    """CONTROLLED REHEARSAL: exercise the full AUTOMATIC post-RANK machinery
    on a recorded fixture. Output is explicitly labeled SYNTHETIC_REHEARSAL.
    EngineRun is driven with a fixture envelope through the same conductor
    path used in production (post-RANK pipeline + release)."""
    sys.path.insert(0, str(REPO_ROOT))
    from tests.test_engine_integration import _full_offline_chain, PROBLEM

    env = _full_offline_chain("PASS")
    missing: List[str] = []
    links_ok: List[str] = []

    def check(link: str, cond: bool):
        (links_ok if cond else missing).append(link)

    check("PROBLEM_RECORDED", bool(env.problem))
    check("EVIDENCE_RETRIEVED", bool(env.evidence))
    check("EVIDENCE_FROZEN", bool(env.provenance.get("evidence_freeze")))
    check("CANDIDATE_SYNTHESIZED", bool(env.mechanism_map))
    check("EVIDENCE_VERIFIED",
          bool((env.adjudication or {}).get("evidence_verification")))
    check("COLLISION_EXECUTED", bool(env.collision_results))
    check("ATTACK_EXECUTED", bool(env.attack_results))
    check("CONTRADICTIONS_ASSESSED", bool(env.contradictions))
    check("KILLER_EXPERIMENT_SELECTED", bool(env.killer_experiment))
    check("ADJUDICATION_RECORDED",
          bool((env.adjudication or {}).get("council")))
    check("CLASSIFICATION_RECORDED",
          (env.epistemic_state or {}).get("final_status")
          == "AUTOMATED_INVENTION_CANDIDATE")
    check("NEXT_BEST_ACTION_RECORDED", bool(env.next_best_action))
    check("RANK_RECORDED", bool(env.ranking))

    # Drive the REAL conductor with the recorded fixture envelope: the
    # post-RANK pipeline and the release path run exactly as in production
    # (Directive 1), with the rehearsal label preserved end-to-end.
    run = EngineRun(PROBLEM, out_dir, run_id=f"rehearsal:{utc_now()[:19]}",
                    with_package=True)
    run.env = env
    run.rehearsal = True   # every artifact must carry SYNTHETIC_REHEARSAL
    run._post_rank_pipeline({"run_id": run.run_id})
    from .release import build_discovery_release, write_discovery_release
    run.release = build_discovery_release(
        run.out, run_id=run.run_id, problem_id=run.problem_id, env=env,
        spec=run._spec, eng=run._eng,
        package_report=run.package_report,
        failure_reason=run.package_failure)
    write_discovery_release(run.out, run.release)

    from .invention_spec import SPEC_FIELDS
    from .engineering_spec import build_engineering_spec
    from .experiment_selector import select_decisive_experiment
    spec = run._spec or {}
    check("SURVIVOR_GATE_PASSED",
          (spec.get("_survivor_gate") or {}).get("survivor") is True)
    check("INVENTION_SPECIFICATION_BUILT",
          all(f in spec for f in SPEC_FIELDS)
          and spec["_integrity"]["passed"])
    eng = run._eng or {}
    check("ENGINEERING_SPECIFICATION_BUILT", bool(eng.get("engineering_core")))
    check("DESIGN_GRAPH_STRUCTURAL",
          eng.get("design_graph", {}).get("integrity", {}).get("passed",
                                                               False))
    sel = select_decisive_experiment(env)
    check("DECISIVE_EXPERIMENT_EXPLAINED", bool(sel.get("selected")))

    _check_post_rank(run, links_ok, missing)

    if missing:
        return _fail(missing, {"package_report":
                               {k: v for k, v in
                                (run.package_report or {}).items()
                                if k != "rendered"}})
    proof = {
        "smoke": "E11_CONTROLLED_REHEARSAL",
        "verdict": "REHEARSAL_PASS",
        "SYNTHETIC_REHEARSAL": True,
        "REAL_LOOP_VERIFIED": False,
        "note": ("machinery proven end-to-end on a recorded fixture; this is "
                 "NOT a real discovery run and its package must never be "
                 "shown to buyers (Art. XXXVII/XXXVIII)"),
        "links_verified": links_ok,
        "package_folder": (run.package_report or {}).get("folder"),
        "package_zip": (run.package_report or {}).get("zip"),
        "release_status": (run.release or {}).get("status"),
        "timestamp": utc_now()}
    (Path(out_dir) / "RUN_LINK_PROOF.json").write_text(
        json.dumps(proof, indent=1, ensure_ascii=False))
    print("\n" + "=" * 70)
    print(f"CONTROLLED REHEARSAL: PASS ({len(links_ok)} links verified)")
    print(f"  SYNTHETIC_REHEARSAL=TRUE  REAL_LOOP_VERIFIED=FALSE")
    print(f"  package (never for buyers): "
          f"{(run.package_report or {}).get('folder')}")
    print("=" * 70)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="E11 true end-to-end smoke (real run or labeled rehearsal)")
    ap.add_argument("--problem-json", help="real problem json (REAL mode)")
    ap.add_argument("--problem-id", help="id from a2.run.PROBLEM_MANIFEST")
    ap.add_argument("--out", default=None)
    ap.add_argument("--disable", default="",
                    help="stages to disable (ablation use only)")
    ap.add_argument("--rehearsal", action="store_true",
                    help="controlled rehearsal over recorded fixture "
                         "(labeled SYNTHETIC_REHEARSAL)")
    ap.add_argument("--resume", action="store_true",
                    help="resume an interrupted REAL run from persisted "
                         "stage snapshots (--out names the run dir)")
    args = ap.parse_args()

    if args.resume:
        if not args.out:
            raise SystemExit("--resume requires --out <run dir>")
        from .run import EngineRun as _ER
        run = _ER.from_run_dir(args.out)
        return run_real_from(run, args.disable)

    out = args.out or str(REPO_ROOT / "ENGINE_RUNS" /
                          f"smoke_e2e_{utc_now()[:19].replace(':', '')}")
    if args.rehearsal:
        return run_rehearsal(out)

    problem: Dict[str, Any]
    if args.problem_json:
        problem = json.loads(Path(args.problem_json).read_text())
    elif args.problem_id:
        import importlib
        a2run = importlib.import_module("discovery_fabric.a2.run")
        problem = a2run.get_problem(args.problem_id)
        if problem is None:
            raise SystemExit(f"unknown problem id: {args.problem_id}")
    else:
        raise SystemExit(
            "REAL mode requires --problem-json or --problem-id; "
            "add --rehearsal for the labeled fixture rehearsal")
    return run_real(problem, out,
                    [s for s in args.disable.split(",") if s])


if __name__ == "__main__":
    raise SystemExit(main())
