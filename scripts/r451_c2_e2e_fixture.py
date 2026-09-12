"""r451_c2_e2e_fixture.py — seed the two E2E proof sessions.

R451-C2 directive §14: the acceptance target is a FRESH USER PATH, not
unit tests. This script seeds a LOCAL sandbox store with two labeled
PUBLIC fixture sessions (the store's established demo-content
mechanism, true origin recorded):

  1. ts-r451c2-blocked  — an infrastructure-blocked run
     (status RUN_BLOCKED_TRANSPORT, no run dir): the fresh-browser DOM
     proof target for the blocked state.

  2. ts-r451c2-success — a COMPLETED run with a REAL trimesh-built
     engineering GLB, a persisted CIO-visible render set, and a
     COMPLETE_PASS gate record: the success-hero regression target.

Every fixture artifact is labeled (fixture=true in session records;
"FIXTURE" in origin). The script never touches existing sessions
beyond appending. `--clean` removes the two fixtures again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SESSIONS = REPO / "TOSCANINI_UI" / "sessions.json"
RUNS = REPO / "ENGINE_RUNS"

BLOCKED_ID = "tsr451c2blockedfixture"
SUCCESS_ID = "tsr451c2successfixture"
STATE_B_ID = "tsr451c2statebfixture"
STATE_C_ID = "tsr451c2statecfixture"
STATE_D_ID = "tsr451c2statedfixture"
ALL_IDS = (BLOCKED_ID, SUCCESS_ID, STATE_B_ID, STATE_C_ID, STATE_D_ID)

PROBLEM = ("How can hydropower turbine blade erosion from high-sediment "
           "water be reduced without sacrificing generating efficiency?")


def _load() -> dict:
    if SESSIONS.exists():
        return json.loads(SESSIONS.read_text())
    return {"sessions": []}


def _save(data: dict) -> None:
    SESSIONS.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def _tiny_png() -> bytes:
    from PIL import Image
    import io
    img = Image.new("RGB", (8, 8), (240, 240, 235))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_glb(path: Path) -> None:
    import trimesh
    s = trimesh.Scene({
        "runner_hub": trimesh.creation.cylinder(
            radius=20, height=24, sections=48),
        "blade_ring": trimesh.creation.icosahedron(radius=34),
        "draft_tube": trimesh.creation.cylinder(
            radius=12, height=60, sections=32),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    s.export(path, file_type="glb")


def seed() -> None:
    data = _load()
    data["sessions"] = [s for s in data.get("sessions", [])
                        if s.get("session_id") not in ALL_IDS]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ---- fixture 1: the infrastructure-blocked run ----------------------
    data["sessions"].append({
        "session_id": BLOCKED_ID,
        "title": PROBLEM,
        "user_text": PROBLEM,
        "status": "RUN_BLOCKED_TRANSPORT",
        "created_at": now,
        "problem_id": None,
        "final_status": None,
        "origin": "FIXTURE r451-c2 blocked-state E2E proof (local sandbox)",
        "public": True,
        "error": ("all model transport routes exhausted "
                  "(FIXTURE — recorded infrastructure failure class)"),
        "fixture": True,
    })

    # ---- fixture 2: the completed run with real geometry ----------------
    run_dir = RUNS / SUCCESS_ID
    if run_dir.exists():
        import shutil
        shutil.rmtree(run_dir)
    _make_glb(run_dir / "MODEL" / "engineering_model.glb")
    glb_sha = hashlib.sha256(
        (run_dir / "MODEL" / "engineering_model.glb").read_bytes()
    ).hexdigest()
    m3d = run_dir / "MODEL" / "3D"
    m3d.mkdir(parents=True, exist_ok=True)
    png = _tiny_png()
    sys.path.insert(0, str(REPO))
    from discovery_fabric.engine.visual_compiler import visual_set
    required = visual_set.required_artifacts(
        3, visual_set.DEFAULT_TURNTABLE_FRAMES)["required"]
    for name in required:
        p = m3d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(png if name.endswith("png") else
                      (run_dir / "MODEL"
                       / "engineering_model.glb").read_bytes())
    (m3d / "visual_gate.json").write_text(json.dumps(
        {"gate_version": "r451c2-fixture", "verdict": "COMPLETE_PASS",
         "hero_suppressed": False, "release_blocked": False}))
    (m3d / "render_record.json").write_text(json.dumps({
        "stage": "RENDER",
        "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        "status": "OK",
        "source_glb_sha256": glb_sha,
        "visual_gate": {"verdict": "COMPLETE_PASS"},
        "scene_spec": {"model": {"node_count": 3}},
        "out_dir": str(m3d)}))
    (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "run_id": SUCCESS_ID, "generation_id": "gen-1",
        "canonical_glb_sha256": glb_sha,
        "compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invoked_at": now, "status": "OK", "skip_reason": None,
        "output_directory": str(m3d)}))
    (run_dir / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "mechanism": ("sediment-bypassing runner inlet geometry that "
                      "keeps abrasive particles out of the blade "
                      "boundary layer (FIXTURE architecture for the "
                      "success-hero regression)"),
        "intervention": "inlet sediment bypass + hardened blade coating",
        "evidence": []}))
    (run_dir / "session.json").write_text(json.dumps(
        {"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": SUCCESS_ID,
        "title": PROBLEM,
        "user_text": PROBLEM,
        "status": "COMPLETE",
        "created_at": now,
        "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2 success-hero regression "
                   "(local sandbox)"),
        "public": True,
        "run_dir": str(run_dir),
        "fixture": True,
        "package": {"complete": False},
    })

    _save(data)

    # ---- fixture 3: State B — invention exists, geometry not applicable
    run_b = RUNS / STATE_B_ID
    if run_b.exists():
        import shutil
        shutil.rmtree(run_b)
    run_b.mkdir(parents=True)
    (run_b / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "mechanism": ("a software-only scheduling mechanism (FIXTURE: "
                      "an invention class with no physical geometry)"),
        "intervention": "scheduler parametrization", "evidence": []}))
    (run_b / "BRIDGE_REPORT.json").write_text(json.dumps({
        "outcome": "NOT_VISUALIZABLE",
        "visualizability_class": "NOT_VISUALIZABLE",
        "classification_basis": {"reason": (
            "FIXTURE: software/process invention — no physical "
            "geometry applies")}}))
    (run_b / "session.json").write_text(json.dumps(
        {"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": STATE_B_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE",
        "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.1 State B (geometry not "
                   "applicable) E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_b), "fixture": True,
        "package": {"complete": False},
    })

    # ---- fixture 4: State C — GLB exists, renderer unavailable ----------
    run_c = RUNS / STATE_C_ID
    if run_c.exists():
        import shutil
        shutil.rmtree(run_c)
    _make_glb(run_c / "MODEL" / "engineering_model.glb")
    m3d_c = run_c / "MODEL" / "3D"
    m3d_c.mkdir(parents=True)
    (m3d_c / "render_record.json").write_text(json.dumps({
        "stage": "RENDER",
        "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        "status": "RENDER_SKIPPED_LOW_MEMORY",
        "skip_reason": ("FIXTURE: free-plan memory floor — the typed "
                        "infrastructure skip"),
        "out_dir": str(m3d_c)}))
    (m3d_c / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "run_id": STATE_C_ID, "generation_id": "gen-1",
        "canonical_glb_sha256": hashlib.sha256(
            (run_c / "MODEL"
             / "engineering_model.glb").read_bytes()).hexdigest(),
        "compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invoked_at": now, "status": "RENDER_SKIPPED_LOW_MEMORY",
        "skip_reason": "LOW_MEMORY",
        "output_directory": str(m3d_c)}))
    (run_c / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "mechanism": "FIXTURE mechanism (state C renderer unavailable)",
        "intervention": "inlet bypass", "evidence": []}))
    (run_c / "session.json").write_text(json.dumps(
        {"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": STATE_C_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE",
        "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.1 State C (renderer unavailable) "
                   "E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_c), "fixture": True,
        "package": {"complete": False},
    })

    # ---- fixture 5: State D — GLB exists, render ran, gate FAILED -------
    run_d = RUNS / STATE_D_ID
    if run_d.exists():
        import shutil
        shutil.rmtree(run_d)
    _make_glb(run_d / "MODEL" / "engineering_model.glb")
    glb_sha_d = hashlib.sha256(
        (run_d / "MODEL" / "engineering_model.glb").read_bytes()
    ).hexdigest()
    m3d_d = run_d / "MODEL" / "3D"
    m3d_d.mkdir(parents=True)
    (m3d_d / "hero.png").write_bytes(_tiny_png())
    (m3d_d / "render_record.json").write_text(json.dumps({
        "stage": "RENDER",
        "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        "status": "OK",
        "source_glb_sha256": glb_sha_d,
        "visual_gate": {"verdict": "FAIL"},
        "out_dir": str(m3d_d)}))
    (m3d_d / "visual_gate.json").write_text(json.dumps({
        "gate_version": "r451c21-fixture", "verdict": "FAIL",
        "hero_suppressed": True, "release_blocked": True,
        "failed_rules": ["occupancy_band"]}))
    (m3d_d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "run_id": STATE_D_ID, "generation_id": "gen-1",
        "canonical_glb_sha256": glb_sha_d,
        "compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invoked_at": now, "status": "OK", "skip_reason": None,
        "output_directory": str(m3d_d)}))
    (run_d / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
        "mechanism": "FIXTURE mechanism (state D gate rejected)",
        "intervention": "inlet bypass", "evidence": []}))
    (run_d / "session.json").write_text(json.dumps(
        {"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": STATE_D_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE",
        "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.1 State D (gate not passed) "
                   "E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_d), "fixture": True,
        "package": {"complete": False},
    })

    _save(data)
    print(f"seeded {ALL_IDS}")
    print(f"sessions: {SESSIONS}")
    print(f"success run dir: {run_dir}")


def clean() -> None:
    data = _load()
    data["sessions"] = [s for s in data.get("sessions", [])
                        if s.get("session_id") not in ALL_IDS]
    _save(data)
    import shutil
    run_dir = RUNS / SUCCESS_ID
    if run_dir.exists():
        shutil.rmtree(run_dir)
    for sid in (STATE_B_ID, STATE_C_ID, STATE_D_ID):
        rd = RUNS / sid
        if rd.exists():
            shutil.rmtree(rd)
    print("fixtures removed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()
    if args.clean:
        clean()
    else:
        seed()
