"""r451_c2_e2e_fixture.py — seed the E2E proof sessions.

R451-C2 directive §14: the acceptance target is a FRESH USER PATH, not
unit tests. This script seeds a LOCAL sandbox store with labeled
PUBLIC fixture sessions (the store's established demo-content
mechanism, true origin recorded):

  1. ts-r451c2-blocked  — an infrastructure-blocked run
  2. ts-r451c2-success  — a COMPLETED run with a REAL trimesh-built
     engineering GLB and a COMPLETE_PASS gate record
  3. ts-r451c2statebfixture — State B (geometry not applicable)
  4. ts-r451c2statecfixture — State C (renderer unavailable)
  5. ts-r451c2statedfixture — State D (gate not passed)

R451-C2.2 additions (the new copy splits + the typed strip classes):

  6. tsr451c22notattemptedfixture — GLB present, NO invocation record,
     no pending job: the not_attempted ribbon copy + the strip's
     STOPPED JOIN_FAILURE visualization row (the no-silent-gap rule
     made visible)
  7. tsr451c22infraskipfixture — GLB + a 1.1.0 infrastructure-skip
     receipt: the DISTINCT infrastructure ribbon copy
  8. tsr451c22renderinprogressfixture — GLB + a RUNNING async render
     job: the render-in-progress ribbon copy
  9. tsr451c22pkgvisualgatefixture — a built package whose release the
     Visual Quality Gate blocked: the strip's Package row reads
     STOPPED with blocked_class VISUAL_GATE (never an infra pause)

Every fixture artifact is labeled (fixture=true in session records;
"FIXTURE" in origin). The script never touches existing sessions
beyond appending. `--clean` removes the fixtures again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


def _proc_starttime(pid: int) -> str:
    """The /proc starttime field — the same identity the artifact
    worker's liveness check reads (R392 pattern)."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as f:
            fields = f.read().rsplit(b")", 1)[1].split()
        return fields[19].decode()
    except Exception:  # noqa: BLE001 — fixture best effort
        return ""

REPO = Path(__file__).resolve().parents[1]
SESSIONS = REPO / "TOSCANINI_UI" / "sessions.json"
RUNS = REPO / "ENGINE_RUNS"

BLOCKED_ID = "tsr451c2blockedfixture"
SUCCESS_ID = "tsr451c2successfixture"
STATE_B_ID = "tsr451c2statebfixture"
STATE_C_ID = "tsr451c2statecfixture"
STATE_D_ID = "tsr451c2statedfixture"
C22_NOT_ATTEMPTED_ID = "tsr451c22notattemptedfixture"
C22_INFRA_SKIP_ID = "tsr451c22infraskipfixture"
C22_RENDER_IN_PROGRESS_ID = "tsr451c22renderinprogressfixture"
C22_PKG_VISUAL_GATE_ID = "tsr451c22pkgvisualgatefixture"
ALL_IDS = (BLOCKED_ID, SUCCESS_ID, STATE_B_ID, STATE_C_ID, STATE_D_ID,
           C22_NOT_ATTEMPTED_ID, C22_INFRA_SKIP_ID,
           C22_RENDER_IN_PROGRESS_ID, C22_PKG_VISUAL_GATE_ID)

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


def _full_invention_spec(arch_note: str) -> dict:
    """The canonical invention record shape the engine itself writes
    (R451-C2.3 §4: the strip's Invention milestone consumes the
    record's REQUIRED VALIDITY STATE — the fixtures carry the same
    core-field shape a real run produces)."""
    return {
        "invention_id": "INV-R451C2-FIXTURE",
        "problem": ("hydropower turbine blade erosion from "
                    "high-sediment water (FIXTURE problem context)"),
        "mechanism": ("sediment-bypassing runner inlet geometry that "
                      "keeps abrasive particles out of the blade "
                      f"boundary layer ({arch_note})"),
        "causal_chain": [
            "abrasive sediment entrains in the runner inlet flow",
            "the bypass passage routes the sediment-bearing layer "
            "away from the blade boundary layer",
            "blade surface erosion exposure drops accordingly",
        ],
        "novelty_hypothesis": (
            "FIXTURE: the bypass-passage placement relative to the "
            "inlet velocity field is the hypothesized novel causal "
            "arrangement (novelty SIGNAL only — never a legal "
            "determination)"),
        "intervention": "inlet sediment bypass + hardened blade coating",
        "evidence": [],
    }


def _seed_engineering_identity(run_dir: Path, session_id: str) -> None:
    """R451-C2.3 §1: the recorded engineering identity chain the
    production bridge itself persists — MODEL/GEOMETRY_SPEC.json,
    MODEL/ARTIFACT_IDENTITY.json (geometry_hash == the GLB bytes on
    disk), and BRIDGE_REPORT.json with outcome COMPLETED and the
    ENGINEERING_3D class. The artifact contract's authority verdict
    reads THIS recorded chain (presence alone never claims
    engineering)."""
    model_dir = run_dir / "MODEL"
    glb = model_dir / "engineering_model.glb"
    glb_sha = hashlib.sha256(glb.read_bytes()).hexdigest()
    spec = {
        "artifact": "GEOMETRY_SPEC",
        "schema_version": "1.0.0",
        "technology_class": "hydropower_runner_fixture",
        "domain_family": "fluid",
        "parameters": [
            {"param_id": "runner_diameter_mm", "value": 240.0,
             "unit": "mm", "value_class": "MODELLED"},
            {"param_id": "bypass_fraction", "value": 0.18,
             "unit": "ratio", "value_class": "MODELLED"},
        ],
    }
    spec_sha = hashlib.sha256(
        json.dumps(spec, sort_keys=True).encode()).hexdigest()
    spec["spec_sha256"] = spec_sha
    (model_dir / "GEOMETRY_SPEC.json").write_text(json.dumps(spec))
    spec_file_sha = hashlib.sha256(
        (model_dir / "GEOMETRY_SPEC.json").read_bytes()).hexdigest()
    identity = {
        "artifact": "ARTIFACT_IDENTITY",
        "identity_version": "r451c2-fixture",
        "technology_id": "ts-fixture-runner",
        "run_id": session_id,
        "generation_id": "gen-1",
        "geometry_hash": glb_sha,
        "source_geometry_hash": spec_sha,
        "glb_path": str(glb),
        "glb_disk_sha256": glb_sha,
        "glb_matches_geometry_hash": True,
        "visualizability_class": "ENGINEERING_3D",
        "domain_family": "fluid",
    }
    (model_dir / "ARTIFACT_IDENTITY.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n")
    (run_dir / "BRIDGE_REPORT.json").write_text(json.dumps({
        "artifact": "BRIDGE_REPORT",
        "outcome": "COMPLETED",
        "visualizability_class": "ENGINEERING_3D",
        "geometry": {
            "generation_id": "gen-1",
            "visualizability_class": "ENGINEERING_3D",
            "artifact_identity": identity,
            "domain_family": "fluid",
        },
    }))
    return spec_file_sha


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
    # R451-C2.3: the recorded engineering identity chain (spec +
    # identity + bridge report) — the success fixture carries the SAME
    # recorded shape a real bridge completion produces
    spec_file_sha = _seed_engineering_identity(run_dir, SUCCESS_ID)
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
        # R451-C2.3 §5 rung 7: the real render record carries each
        # view's own hash — the exported hero.glb's provenance is part
        # of the release chain
        "views": {"hero.glb": {"sha256": glb_sha}},
        "out_dir": str(m3d)}))
    (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "schema_version": "1.1.0",
        "run_id": SUCCESS_ID, "generation_id": "gen-1",
        "glb_sha256": glb_sha,
        "geometry_spec_sha256": spec_file_sha,
        "visual_compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invoked_at": now, "invocation_status": "OK", "skip_reason": None,
        "render_record_reference": str(m3d / "render_record.json"),
        "output_directory": str(m3d)}))
    (run_dir / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec(
            "FIXTURE architecture for the success-hero regression")))
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
    (run_b / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        {**_full_invention_spec(
            "FIXTURE: a software-only scheduling invention class with "
            "no physical geometry"),
         "mechanism": (
             "a software-only scheduling mechanism (FIXTURE: an "
             "invention class with no physical geometry)")}))
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
    _seed_engineering_identity(run_c, STATE_C_ID)
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
    (run_c / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec("FIXTURE mechanism (state C renderer "
                             "unavailable)")))
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
    _seed_engineering_identity(run_d, STATE_D_ID)
    (m3d_d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "run_id": STATE_D_ID, "generation_id": "gen-1",
        "canonical_glb_sha256": glb_sha_d,
        "compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invoked_at": now, "status": "OK", "skip_reason": None,
        "output_directory": str(m3d_d)}))
    (run_d / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec("FIXTURE mechanism (state D gate "
                             "rejected)")))
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

    _seed_c22(data, now)
    _save(data)
    print(f"seeded {ALL_IDS}")
    print(f"sessions: {SESSIONS}")
    print(f"success run dir: {run_dir}")


def _seed_c22(data: dict, now: str) -> None:
    """R451-C2.2 fixtures: the new copy splits + the typed strip
    classes. Every artifact is written from the recorded shape the
    production path itself produces (no invented fields)."""
    # ---- fixture 6: not_attempted — GLB, NO receipt, NO job -----------
    # a TERMINAL seeded job record keeps the boot recovery sweep out
    # (its rule 4: a terminal job verdict stands) so the seeded
    # no-invocation state stays authoritative for the capture — the
    # live join's auto-heal is separately proven in this round's log
    run_na = RUNS / C22_NOT_ATTEMPTED_ID
    if run_na.exists():
        import shutil
        shutil.rmtree(run_na)
    _make_glb(run_na / "MODEL" / "engineering_model.glb")
    m3d_na = run_na / "MODEL" / "3D"
    m3d_na.mkdir(parents=True)
    _seed_engineering_identity(run_na, C22_NOT_ATTEMPTED_ID)
    (m3d_na / "RENDER_JOB.json").write_text(json.dumps({
        "artifact": "RENDER_JOB",
        "session_id": C22_NOT_ATTEMPTED_ID,
        "status": "FAILED",
        "enqueued_by": "fixture-seed",
        "at": now,
        "error": ("FIXTURE: seeded terminal job record — the recovery "
                  "sweep must not heal this no-invocation capture"),
    }))
    (run_na / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec("FIXTURE mechanism (not_attempted join "
                             "state)")))
    (run_na / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": C22_NOT_ATTEMPTED_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE", "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.2 not_attempted (no invocation "
                   "record) E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_na), "fixture": True,
        "package": {"complete": False},
    })

    # ---- fixture 7: infrastructure skip receipt (1.1.0) ---------------
    run_is = RUNS / C22_INFRA_SKIP_ID
    if run_is.exists():
        import shutil
        shutil.rmtree(run_is)
    _make_glb(run_is / "MODEL" / "engineering_model.glb")
    m3d_is = run_is / "MODEL" / "3D"
    m3d_is.mkdir(parents=True)
    _seed_engineering_identity(run_is, C22_INFRA_SKIP_ID)
    (m3d_is / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
        "kind": "VISUAL_COMPILER_INVOCATION",
        "schema_version": "1.1.0",
        "run_id": C22_INFRA_SKIP_ID, "generation_id": "gen-1",
        "glb_sha256": hashlib.sha256(
            (run_is / "MODEL"
             / "engineering_model.glb").read_bytes()).hexdigest(),
        "geometry_spec_sha256": None,
        "visual_compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
        "invocation_status": "RENDER_SKIPPED_LOW_MEMORY",
        "gate_version": "fixture", "invoked_at": now,
        "skip_reason": ("FIXTURE: free-plan memory floor — the typed "
                        "infrastructure skip"),
        "render_record_reference": None,
        "output_directory": str(m3d_is)}))
    (m3d_is / "RENDER_JOB.json").write_text(json.dumps({
        "artifact": "RENDER_JOB",
        "session_id": C22_INFRA_SKIP_ID,
        "status": "FAILED",
        "enqueued_by": "fixture-seed",
        "at": now,
        "error": ("FIXTURE: seeded terminal job record — the recovery "
                  "sweep must not heal this infrastructure-skip capture"),
    }))
    (run_is / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec("FIXTURE mechanism (infrastructure skip)")))
    (run_is / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": C22_INFRA_SKIP_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE", "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.2 infrastructure-skip ribbon copy "
                   "E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_is), "fixture": True,
        "package": {"complete": False},
    })

    # ---- fixture 8: render job RUNNING (explicit pending) --------------
    run_rp = RUNS / C22_RENDER_IN_PROGRESS_ID
    if run_rp.exists():
        import shutil
        shutil.rmtree(run_rp)
    _make_glb(run_rp / "MODEL" / "engineering_model.glb")
    m3d_rp = run_rp / "MODEL" / "3D"
    m3d_rp.mkdir(parents=True)
    _seed_engineering_identity(run_rp, C22_RENDER_IN_PROGRESS_ID)
    (m3d_rp / "RENDER_JOB.json").write_text(json.dumps({
        "artifact": "RENDER_JOB", "session_id": C22_RENDER_IN_PROGRESS_ID,
        "status": "RUNNING", "enqueued_by": "bridge_gate",
        "worker_pid": os.getpid(),
        "worker_starttime": _proc_starttime(os.getpid()),
        "pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        "note": ("FIXTURE: the async artifact build is running — the "
                 "live pid keeps the recovery sweep out of this "
                 "explicit-pending capture")}))
    (run_rp / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec("FIXTURE mechanism (render in progress)")))
    (run_rp / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": C22_RENDER_IN_PROGRESS_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE", "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.2 render-in-progress ribbon copy "
                   "E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_rp), "fixture": True,
        "package": {"complete": False},
    })

    # ---- fixture 9: package release blocked by the VISUAL GATE ---------
    run_pv = RUNS / C22_PKG_VISUAL_GATE_ID
    if run_pv.exists():
        import shutil
        shutil.rmtree(run_pv)
    _make_glb(run_pv / "MODEL" / "engineering_model.glb")
    m3d_pv = run_pv / "MODEL" / "3D"
    m3d_pv.mkdir(parents=True)
    _seed_engineering_identity(run_pv, C22_PKG_VISUAL_GATE_ID)
    # the recorded Art. LXXII release block (the gate never passed)
    (m3d_pv / "HERO_RELEASE_STATE.json").write_text(json.dumps({
        "verdict": "FAIL", "release_blocked": True,
        "gate_verdict": "NOT_RUN",
        "note": ("FIXTURE: the Visual Quality Gate did not pass/run — "
                 "the package contains zero visual artifacts by design")}))
    (run_pv / "PACKAGE_BUILD_BLOCKED.json").write_text(json.dumps({
        "stage": "QUALITY_GATE_BLOCKED",
        "detail": ("FIXTURE: the buyer release stays blocked until the "
                   "visual gate passes (Article LXXII)")}))
    m3d_pv_job = m3d_pv / "RENDER_JOB.json"
    m3d_pv_job.write_text(json.dumps({
        "artifact": "RENDER_JOB",
        "session_id": C22_PKG_VISUAL_GATE_ID,
        "status": "FAILED",
        "enqueued_by": "fixture-seed",
        "at": now,
        "error": ("FIXTURE: seeded terminal job record — the recovery "
                  "sweep must not heal this visual-gate-block capture"),
    }))
    (run_pv / "INVENTION_SPECIFICATION.json").write_text(json.dumps(
        _full_invention_spec("FIXTURE mechanism (package visual-gate "
                             "block)")))
    (run_pv / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
    data["sessions"].append({
        "session_id": C22_PKG_VISUAL_GATE_ID,
        "title": PROBLEM, "user_text": PROBLEM,
        "status": "COMPLETE", "created_at": now, "problem_id": None,
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "origin": ("FIXTURE r451-c2.2 package visual-gate blocked strip "
                   "class E2E proof (local sandbox)"),
        "public": True, "run_dir": str(run_pv), "fixture": True,
        "package": {"complete": False},
    })


def clean() -> None:
    data = _load()
    data["sessions"] = [s for s in data.get("sessions", [])
                        if s.get("session_id") not in ALL_IDS]
    _save(data)
    import shutil
    run_dir = RUNS / SUCCESS_ID
    if run_dir.exists():
        shutil.rmtree(run_dir)
    for sid in (STATE_B_ID, STATE_C_ID, STATE_D_ID,
                C22_NOT_ATTEMPTED_ID, C22_INFRA_SKIP_ID,
                C22_RENDER_IN_PROGRESS_ID, C22_PKG_VISUAL_GATE_ID):
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
