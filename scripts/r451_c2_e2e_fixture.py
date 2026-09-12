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
                        if s.get("session_id") not in
                        (BLOCKED_ID, SUCCESS_ID)]
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
    print(f"seeded {BLOCKED_ID} (blocked) and {SUCCESS_ID} (success)")
    print(f"sessions: {SESSIONS}")
    print(f"success run dir: {run_dir}")


def clean() -> None:
    data = _load()
    data["sessions"] = [s for s in data.get("sessions", [])
                        if s.get("session_id") not in
                        (BLOCKED_ID, SUCCESS_ID)]
    _save(data)
    import shutil
    run_dir = RUNS / SUCCESS_ID
    if run_dir.exists():
        shutil.rmtree(run_dir)
    print("fixtures removed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()
    if args.clean:
        clean()
    else:
        seed()
