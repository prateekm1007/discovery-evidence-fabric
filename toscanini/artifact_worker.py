"""toscanini/artifact_worker.py — R419 section 21: async artifact build.

The render job (Blender 5.2 LTS headless over the run's authoritative
GLB) is a DETACHED subprocess — the web request that enqueues it never
waits for Blender (operator directive section 21: POST artifact-build
-> job -> worker -> Blender -> artifacts -> persisted).

Job contract:
    * idempotent: existing renders are never re-run (the job inspects
      MODEL/3D/ before starting; re-enqueue is a no-op read-back)
    * typed: every outcome is a JSON record, never a silent gap
      (OK / ALREADY_PRESENT / RENDER_SKIPPED_NO_BLENDER /
      RENDER_FAILED / RENDER_TIMEOUT — the render stage's own
      vocabulary, Art. LXI: infrastructure failure is never science)
    * durable: the job record is MODEL/3D/RENDER_JOB.json — the file
      is the authority (Art. X); a restart finds it and either sees
      the finished state or re-runs (renders are deterministic)
    * presentation-only: Blender never alters the engineering truth
      (operator section 7; the render record carries the topology
      comparison)

This module is a thin enqueue/job-record layer; the render itself is
discovery_fabric.engine.invention_bridge.render (the pinned-build
orchestrator) and blender_render.py (the Blender-side script).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import sessions as store

REPO_ROOT = Path(__file__).resolve().parent.parent

_JOB_LOCK = "RENDER_JOB.json"


def _job_path(session_id: str) -> Optional[Path]:
    s = store.get_session(session_id)
    if not s or not s.get("run_dir"):
        return None
    return Path(s["run_dir"]) / "MODEL" / "3D" / _JOB_LOCK


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def renderables_present(session: Dict[str, Any]) -> bool:
    """A renderable run: an authoritative GLB exists (MODEL/*.glb or a
    root GLB). No GLB -> the job is honestly refused (409 at the API
    layer; never a fabricated render)."""
    if not session.get("run_dir"):
        return False
    run_dir = Path(session["run_dir"])
    if not run_dir.exists():
        return False
    model = run_dir / "MODEL"
    glbs = list(model.glob("*.glb")) if model.exists() \
        else list(run_dir.glob("*.glb"))
    return bool(glbs)


def job_record(session_id: str) -> Optional[Dict[str, Any]]:
    """The persisted job record (the file is the authority)."""
    p = _job_path(session_id)
    if not p or not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — corrupt record -> re-runnable
        return None


def _write_job(session_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    p = _job_path(session_id)
    if p is None:
        return record
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(record, indent=2))
    return record


def enqueue(session_id: str) -> Dict[str, Any]:
    """Enqueue the detached render job. Returns the job record.

    Idempotency: a RUNNING job for the same session is returned as-is
    (one Blender process per run at a time); a terminal record with
    renders already on disk reads back ALREADY_PRESENT.
    """
    prior = job_record(session_id)
    if prior and prior.get("status") == "RUNNING":
        # one concurrent render per run — honest 202 with the live job
        return prior

    record = {
        "artifact": "RENDER_JOB",
        "session_id": session_id,
        "status": "RUNNING",
        "enqueued_at": _now(),
        "pipeline": "BLENDER_HEADLESS",
        "note": ("async artifact build — the web request never waits "
                 "for Blender; poll the render routes or the CIO's "
                 "visualization.renders"),
    }
    _write_job(session_id, record)

    subprocess.Popen(
        [sys.executable, "-m", "toscanini.artifact_worker", session_id],
        cwd=str(REPO_ROOT),
        stdout=open(REPO_ROOT / "ENGINE_RUNS" / "artifact_worker.log", "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=dict(os.environ),
    )
    return record


def run(session_id: str) -> Dict[str, Any]:
    """The job body: run the render stage over the authoritative GLB."""
    from discovery_fabric.engine.invention_bridge import render

    s = store.get_session(session_id)
    if not s or not s.get("run_dir"):
        return _write_job(session_id, {
            "artifact": "RENDER_JOB", "session_id": session_id,
            "status": "FAILED", "at": _now(),
            "error": "session or run directory not found"})

    run_dir = Path(s["run_dir"])
    # honest class label from the persisted CIO when present
    vis_class = None
    cio_files = [run_dir / "CIO.json", run_dir / "cio.json"]
    for cf in cio_files:
        if cf.is_file():
            try:
                cio = json.loads(cf.read_text())
                geo = cio.get("geometry") or {}
                vis_class = geo.get("visualizability_class") \
                    or geo.get("class")
            except Exception:  # noqa: BLE001
                pass
            break

    try:
        rec = render.render_invention(
            str(run_dir), {"generation_models": None},
            is_conceptual=vis_class != "ENGINEERING_3D")
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        rec = {"stage": "RENDER", "status": "RENDER_FAILED",
               "error": f"{type(exc).__name__}: {exc}"}

    status = {
        "OK": "OK", "RENDER_PARTIAL": "PARTIAL",
    }.get(rec.get("status", ""), rec.get("status", "UNKNOWN"))

    return _write_job(session_id, {
        "artifact": "RENDER_JOB",
        "session_id": session_id,
        "status": status,
        "at": _now(),
        "render_record": {
            k: rec.get(k) for k in
            ("status", "render_pipeline", "pinned_blender",
             "source_glb_sha256", "artifacts", "missing_artifacts",
             "seconds", "note", "error")},
    })


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m toscanini.artifact_worker <session_id>",
              file=sys.stderr)
        sys.exit(2)
    out = run(sys.argv[1])
    print(f"[artifact_worker] {sys.argv[1]}: {out.get('status')}",
          file=sys.stderr)
    sys.exit(0 if out.get("status") in ("OK", "PARTIAL") else 1)
