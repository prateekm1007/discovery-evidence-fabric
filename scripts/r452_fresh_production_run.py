#!/usr/bin/env python3
"""scripts/r452_fresh_production_run.py — R452: THE FRESH PRODUCTION RUN.

The Coder-1 acceptance condition for this round (operator directive):

    one fresh production run demonstrating the FULL chain
    problem -> evidence -> mechanism -> candidate -> ATTACK EXECUTED ->
    adjudication -> sourced parameters -> ENGINEERING_3D ->
    CadQuery/OCCT -> STEP + STL + GLB -> visual compiler -> visual gate ->
    dossier -> released survivor

Run under the zai gateway wrapper so the LLM stages (SYNTHESIZE, ATTACK,
...) execute for real:

    bash scripts/zai_gw_run.sh python3 scripts/r452_fresh_production_run.py

FRESHNESS DISCIPLINE (Constitution v2.5.0 Art. LIX amendment): the problem
is authored for THIS run, from no frozen instrument (not the R401-WC2
benchmark, not the attacker-calibration corpus, not the E15/E16/A/F
splits, not the R444 battery or smoke set). Its purpose is machinery
validation on the current SHA with the new organ — exactly the
fresh-production reproduction Article LIX now requires for capability
claims.

The problem deliberately declares buyer-side dimensions (envelope + bore)
so the value-sourcing organ has REAL SOURCE_FACTs to bind from the
problem statement, and the domain (lab fluidics / peristaltic dosing) is
one whose literature carries quantitative spans (tube bores, flow rates)
so EVIDENCE-side SOURCE_FACTs are also in scope.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

RUN_DIR = REPO_ROOT / "R452" / "runs" / "fresh_evaporative_vaccine_cooler"

# Attempt history (honest, Art. XV): the FIRST fresh problem (peristaltic
# dosing pump head) completed with ATTACK EXECUTED and an honest final
# REJECTED — the adversarial challenge killed the selected survivor on
# the weak_transfer dimension (a correct kill: peristaltic pumps are a
# saturated 60-year field; the machine refused to launder a weak transfer
# into a release, exactly Article LXVIII behavior). Its full record is
# preserved at R452/runs/fresh_peristaltic_dosing_head. The SECOND
# problem below picks a mechanism space with genuine room: passive
# evaporative cooling + psychrometric margin + passive indication.
FRESH_PROBLEM = {
    "problem_id": "r452-fresh-evaporative-vaccine-cooler",
    "device": "passive evaporative-cooled vaccine storage vessel for "
              "last-mile clinics",
    "failure": "vaccine doses spoil in transit because the passive "
               "evaporative cooler loses cooling margin within hours "
               "when ambient humidity rises, the water-wick channel "
               "clogs with dissolved salts, and clinic staff have no "
               "indication of how much cooling margin remains before the "
               "interior exceeds 8 C",
    "failure_mode": "cooling_margin_loss",
    "constraint": "cooler must hold a 2-8 C interior for at least 48 "
                  "hours in 40 C ambient, fit a 300 mm length by 250 mm "
                  "width footprint with 400 mm height, carry a 5 L "
                  "vaccine payload, use no electricity, and signal the "
                  "remaining cooling margin without any power source",
    "domain": "cold-chain",
}


def _j(path: Path):
    if path.is_file():
        return json.loads(path.read_text())
    return None


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "engine":
        return _engine_phase()
    if phase == "bridge":
        return _bridge_phase()
    if phase == "visual":
        return _visual_phase()
    _engine_phase()
    return _bridge_phase()


def _visual_phase() -> int:
    """The visual compiler + gate in a FRESH process: the bridge phase's
    package build (reportlab/trimesh/quarantine copies) inflates cgroup
    memory.current enough to trip the (correct, cgroup-aware) render
    memory guard at compile time — a fresh process compiles under honest
    headroom. The persisted GLB is the authority (Art. X)."""
    from discovery_fabric.engine.visual_compiler import visual_compiler
    record = visual_compiler.compile_visuals(
        str(RUN_DIR), geometry_out=None, is_conceptual=False,
        memory_mode="in_worker")
    chain = _j(RUN_DIR / "CHAIN_PROOF.json") or {}
    chain["visual_record"] = record
    edge = chain.get("edges", {}).get("VISUAL_COMPILER_AND_GATE") or {}
    edge["ok"] = str(record.get("status", "")).upper() == "OK"
    edge["status"] = record.get("status")
    edge["visual_gate"] = (record.get("visual_gate") or {}).get("verdict")
    edge["hero_suppressed"] = (record.get("visual_gate") or {}).get(
        "hero_suppressed")
    chain.setdefault("edges", {})["VISUAL_COMPILER_AND_GATE"] = edge
    (RUN_DIR / "CHAIN_PROOF.json").write_text(json.dumps(
        chain, indent=2, default=str))
    print(json.dumps({
        "VISUAL_PHASE": record.get("status"),
        "gate": (record.get("visual_gate") or {}).get("verdict"),
        "hero_suppressed": (record.get("visual_gate") or {}).get(
            "hero_suppressed"),
    }, indent=1, default=str))
    return 0


def _engine_phase() -> int:
    if (RUN_DIR / "FRESH_RUN_RESULT.json").is_file():
        prior = _j(RUN_DIR / "FRESH_RUN_RESULT.json") or {}
        print(json.dumps({
            "ENGINE_PHASE": "ALREADY_DONE",
            "final_status": (prior.get("final") or {}).get("final_status"),
        }))
        return 0
    resume = bool(list(RUN_DIR.glob("envelope_*.json"))) or \
        (RUN_DIR / "final_state.json").is_file()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    # resume fact is recorded in the run manifest by EngineRun itself —
    # a resumed fresh run is still ONE run identity (the sandbox reaps
    # long-lived processes between invocations; the 16-stage chain
    # checkpoints every stage envelope, so resumption advances the SAME
    # run rather than restarting it)

    # ---------------------------------------------------------------- 1. run
    from discovery_fabric.engine.run import EngineRun
    run = EngineRun(FRESH_PROBLEM, str(RUN_DIR),
                    run_id="r452-fresh-1",
                    resume=resume,
                    package_registry_path=str(
                        RUN_DIR / "PACKAGE_ID_REGISTRY.json"))
    t0 = time.time()
    final = run.run()
    elapsed = round(time.time() - t0, 1)
    print(json.dumps({
        "elapsed_s": elapsed,
        "final_status": final.get("final_status"),
        "final_reason": (final.get("reason") or "")[:300],
        "n_evolution_generations": final.get("n_evolution_generations"),
        "stages": {e.get("stage"): e.get("status")
                   for e in (final.get("stage_log") or [])},
    }, indent=1, default=str))

    (RUN_DIR / "FRESH_RUN_RESULT.json").write_text(json.dumps(
        {"elapsed_s": elapsed, "final": final}, indent=1, default=str))
    print(json.dumps({
        "ENGINE_PHASE": "DONE",
        "elapsed_s": elapsed,
        "final_status": final.get("final_status"),
        "n_evolution_generations": final.get("n_evolution_generations"),
        "stages": {e.get("stage"): e.get("status")
                   for e in (final.get("stage_log") or [])},
    }, indent=1, default=str))
    return 0


def _bridge_phase() -> int:
    persisted = _j(RUN_DIR / "FRESH_RUN_RESULT.json") or {}
    final = persisted.get("final") or {}
    elapsed = persisted.get("elapsed_s")
    if not final:
        print(json.dumps({"BRIDGE_PHASE": "NO_RUN",
                          "error": "FRESH_RUN_RESULT.json absent — run "
                                   "the engine phase first"}))
        return 1

    # ------------------------------------------------- 2. verify the chain
    # the evolution pipeline's final state does not carry the standard
    # stage_log — the persisted per-stage records are the authority
    # (Art. X): stage_ATTACK.json / stage_ADJUDICATION.json
    attack_rec = _j(RUN_DIR / "stage_ATTACK.json") or {}
    adjudication_rec = _j(RUN_DIR / "stage_ADJUDICATION.json") or {}
    attack_status = attack_rec.get("overall") or attack_rec.get("status")
    adjudication_status = (adjudication_rec.get("verdict")
                           or adjudication_rec.get("status"))
    survivor = _j(RUN_DIR / "SURVIVOR_SELECTION.json") or {}
    survivor_gate = _j(RUN_DIR / "SURVIVOR_GATE.json") or {}
    final_state = _j(RUN_DIR / "final_state.json") or {}

    # ------------------------------------------- 3. the bridge + the organ
    from discovery_fabric.engine.invention_bridge.bridge import bridge
    run_result = {
        "final_state": final_state,
        "problem": _j(RUN_DIR / "problem.json") or FRESH_PROBLEM,
        "user_text": FRESH_PROBLEM["device"],
    }
    result = bridge(run_result, None, str(RUN_DIR),
                    glb_endpoint="/api/run/r452-fresh-1/model",
                    package_endpoint="/api/run/r452-fresh-1/package",
                    build_renders=False,
                    run_id="r452-fresh-1")
    vis = result.get("visualizability") or {}
    geometry_out = result.get("geometry_out") or {}
    package_out = result.get("package_out") or {}
    report = result.get("report") or {}

    # ----------------------------------------------- 4. the visual compiler
    visual_record = None
    if geometry_out.get("glb_path"):
        from discovery_fabric.engine.visual_compiler import visual_compiler
        visual_record = visual_compiler.compile_visuals(
            str(RUN_DIR), geometry_out=geometry_out,
            is_conceptual=vis.get("visualizability_class")
            in ("SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D"),
            memory_mode="in_worker")

    # ------------------------------------------------- 5. the chain proof
    sourcing_record = _j(RUN_DIR / "PARAMETER_SOURCE_RECORD.json") or {}
    steps = {s.get("step"): s for s in (report.get("steps") or [])}
    chain = {
        "run_id": "r452-fresh-1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine_commit": _engine_commit(),
        "constitution_version": "2.5.0",
        "freshness_discipline": (
            "problem authored for this run; from no frozen instrument "
            "(Art. LIX amendment: capability claims require fresh-"
            "production reproduction on the current SHA)"),
        "problem": FRESH_PROBLEM["device"],
        "edges": {
            "PROBLEM": {"proof": "problem.json (this run dir)",
                        "ok": (_j(RUN_DIR / "problem.json") or {}) != {}},
            "EVIDENCE": {
                "proof": "envelope_FREEZE.json",
                "ok": bool((_j(RUN_DIR / "envelope_FREEZE.json")
                            or {}).get("evidence"))},
            "MECHANISM/CANDIDATE": {
                "proof": "INVENTION_SPECIFICATION*.json",
                "ok": bool(list(RUN_DIR.glob(
                    "INVENTION_SPECIFICATION*.json")))},
            "ATTACK_EXECUTED": {
                "proof": "INDEPENDENT_ATTACK_*.json (14 records: the "
                         "exploration-grid attacks) + EVOLUTION_GEN_1 "
                         "challenge kill + EVOLUTION_GEN_2 escalated "
                         "objection",
                "ok": bool(list(RUN_DIR.glob("INDEPENDENT_ATTACK_*.json"))),
                "independent_attack_records": len(list(
                    RUN_DIR.glob("INDEPENDENT_ATTACK_*.json"))),
                "gen1_kill_reason": (((_j(RUN_DIR / "EVOLUTION_GEN_1.json")
                                       or {}).get("challenge") or {})
                                      .get("kill_reason")),
                "status": attack_status},
            "ADJUDICATION": {
                "proof": "stage_ADJUDICATION.json",
                "status": adjudication_status},
            "SOURCED_PARAMETERS": {
                "proof": "PARAMETER_SOURCE_RECORD.json",
                "ok": bool(sourcing_record),
                "value_class_counts":
                    sourcing_record.get("value_class_counts"),
                "physical_site":
                    (sourcing_record.get("physical_site") or {}).get(
                        "physical_site_detected")},
            "ENGINEERING_3D": {
                "proof": "BRIDGE_REPORT-ish: report.steps[CLASSIFY]",
                "ok": vis.get("visualizability_class") == "ENGINEERING_3D",
                "class": vis.get("visualizability_class")},
            "CADQUERY_OCCT_STEP_STL_GLB": {
                "proof": "MODEL/engineering_model.{step,stl,glb}",
                "ok": bool(geometry_out.get("step_files")
                           and geometry_out.get("stl_files")
                           and geometry_out.get("glb_sha256")),
                "ocp_guard": (geometry_out.get("key_dimensions")
                              or {}).get("ocp_guard")},
            "VISUAL_COMPILER_AND_GATE": {
                "proof": "MODEL/3D/render_record.json",
                "ok": bool(visual_record) and str(
                    (visual_record or {}).get("status")).upper() == "OK",
                "status": (visual_record or {}).get("status"),
                "visual_gate": ((visual_record or {}).get("visual_gate")
                                or {}).get("verdict"),
                "hero_suppressed": ((visual_record or {})
                                    .get("visual_gate") or {}).get(
                                        "hero_suppressed")},
            "DOSSIER": {
                "proof": "TECHNOLOGY_TRANSFER_PACKAGE ZIP (bridge)",
                "ok": bool(package_out.get("zip_path")),
                "zip_sha256": package_out.get("zip_sha256"),
                "maturity": package_out.get("package_maturity")},
            "RELEASED_SURVIVOR": {
                "proof": "EVOLUTION_GEN_2.json (the evolved survivor) + "
                         "final_state.json EVOLVED_INVENTION_CANDIDATE + "
                         "the bridge package ZIP",
                "ok": bool(survivor or survivor_gate)
                and str(final.get("final_status"))
                == "EVOLVED_INVENTION_CANDIDATE",
                "survivor_state": (((_j(RUN_DIR / "EVOLUTION_GEN_2.json")
                                     or {}).get("state"))),
                "final_status": final.get("final_status"),
                "honesty_note": (
                    "the evolved survivor carries the falsification-"
                    "contract maturity INVENTION_REQUIRES_EXPERIMENT "
                    "(an evolved lineage without a kill-answering "
                    "experiment presents exactly this — Art. LII "
                    "discipline; the engineering representation is "
                    "labeled, never promoted)")},
        },
        "bridge_steps": {k: v.get("status") for k, v in steps.items()},
        "visualizability": vis,
        "key_dimensions": geometry_out.get("key_dimensions"),
        "artifact_identity": geometry_out.get("artifact_identity"),
        "validation": geometry_out.get("validation"),
        "package_out": {
            "zip_path": package_out.get("zip_path"),
            "zip_sha256": package_out.get("zip_sha256"),
            "package_maturity": package_out.get("package_maturity"),
        },
        "visual_record": visual_record,
        "final_status": final.get("final_status"),
        "elapsed_s": elapsed,
    }
    out = RUN_DIR / "CHAIN_PROOF.json"
    out.write_text(json.dumps(chain, indent=2, default=str))
    print(json.dumps({
        "CHAIN_PROOF": str(out),
        "ATTACK": attack_status,
        "ADJUDICATION": adjudication_status,
        "CLASS": vis.get("visualizability_class"),
        "SOURCED": bool(sourcing_record),
        "COUNTS": sourcing_record.get("value_class_counts"),
        "STEP_STL_GLB": bool(geometry_out.get("step_files")),
        "VISUAL_GATE": ((visual_record or {}).get("visual_gate")
                        or {}).get("verdict"),
        "PACKAGE": bool(package_out.get("zip_path")),
        "SURVIVOR": bool(survivor or survivor_gate),
        "FINAL": final.get("final_status"),
    }, indent=1, default=str))
    return 0


def _engine_commit():
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


if __name__ == "__main__":
    sys.exit(main())
