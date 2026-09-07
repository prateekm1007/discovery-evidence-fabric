"""Engine-side render orchestrator — invokes the pinned Blender build.

R419 fixed 3D stack (operator directive):

    INVENTION -> ENGINEERING SPEC -> CadQuery/OCCT -> MEASURE -> GLB
        -> Blender 5.2 LTS (headless) -> hero/section/exploded renders
        -> Three.js / React Three Fiber -> WEB

This module is the engine half of that pipeline. It NEVER runs Blender
interactively, never keeps it resident, and runs it as a subprocess of
the run WORKER (the run is already a background job — the web request
never waits for Blender; operator directive section 21).

Failure semantics: a render failure is a TYPED record
(RENDER_FAILED / RENDER_SKIPPED_NO_BLENDER / RENDER_TIMEOUT) written to
the bridge report. The GLB contract is unaffected — the interactive 3D
artifact is served from the CadQuery-authored geometry regardless; the
PNG renders and materialized GLBs are enhancements produced when the
pinned build is available. Nothing is fabricated (Art. VI/XXV/LXI:
infrastructure failure is never scientific rejection).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

RENDER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "blender_render.py")

# Pinned build (operator directive: Blender 5.2 LTS). The tarball sha256
# is recorded so the Docker image and every local verification run use
# byte-identical builds.
PINNED_BLENDER_VERSION = "5.2.1 LTS"
PINNED_TARBALL_SHA256 = (
    "a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9")

_BLENDER_TIMEOUT_S = 900  # whole hero+section+exploded bundle
_ARTIFACTS = ("hero.png", "section.png", "exploded.png",
              "hero.glb", "section.glb", "exploded.glb")


def find_blender() -> Optional[str]:
    """Locate the pinned Blender build. Resolution order:

    1. $BLENDER_PATH (explicit operator/environment override — also
       how local verification runs point at their own build)
    2. /opt/blender — the Docker image install location (the pinned
       tarball, sha256-verified at build time)
    3. shutil.which("blender") — a system install (operator-managed)

    No machine-specific fallbacks: a render that cannot find the pinned
    build is a TYPED honest skip (RENDER_SKIPPED_NO_BLENDER), never a
    guessed binary (Art. VI: no fabricated provenance).
    """
    candidates = [
        os.environ.get("BLENDER_PATH") or "",
        "/opt/blender/blender",
        shutil.which("blender") or "",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def authoritative_glb(work_dir: str,
                      generation_models: Optional[List[Dict]] = None
                      ) -> Optional[str]:
    """The CURRENT generation's GLB — the geometry authority to render.

    Order: the current generation model (MODEL/model-00N.glb where N is
    the current generation), then engineering_model.glb, then any GLB.
    """
    model_dir = os.path.join(work_dir, "MODEL")
    current: Optional[int] = None
    for m in generation_models or []:
        if m.get("current"):
            current = int(m.get("generation") or 0)
    if current:
        p = os.path.join(model_dir, f"model-{current:03d}.glb")
        if os.path.isfile(p):
            return p
    eng = os.path.join(model_dir, "engineering_model.glb")
    if os.path.isfile(eng):
        return eng
    if os.path.isdir(model_dir):
        glbs = sorted(Path(model_dir).glob("model-*.glb"))
        if glbs:
            return str(glbs[-1])
    roots = sorted(Path(work_dir).glob("*.glb"))
    return str(roots[0]) if roots else None


def render_invention(work_dir: str,
                     geometry_out: Optional[Dict[str, Any]],
                     is_conceptual: bool,
                     renders: Optional[List[str]] = None,
                     resolution: Optional[List[int]] = None,
                     samples: Optional[int] = None) -> Dict[str, Any]:
    """Run the pinned Blender build over the authoritative GLB.

    Returns a typed render record — always honest, never raising into
    the caller (the run's epistemic state is never altered by a
    presentation-layer failure; Art. LXI).
    """
    record: Dict[str, Any] = {
        "stage": "RENDER",
        "render_pipeline": "BLENDER_HEADLESS",
        "pinned_blender": PINNED_BLENDER_VERSION,
        "pinned_tarball_sha256": PINNED_TARBALL_SHA256,
        "is_conceptual": bool(is_conceptual),
        "status": "OK",
    }
    t0 = time.time()

    blender = find_blender()
    if not blender:
        record["status"] = "RENDER_SKIPPED_NO_BLENDER"
        record["note"] = (
            "no Blender build found (set BLENDER_PATH or install the "
            "pinned 5.2.1 LTS build) — the interactive GLB is served "
            "unchanged; PNG renders are enhancements, not the contract")
        return record

    source = authoritative_glb(
        work_dir, (geometry_out or {}).get("generation_models"))
    if not source:
        record["status"] = "RENDER_SKIPPED_NO_SOURCE_GLB"
        record["note"] = "no authoritative GLB found in the run directory"
        return record
    record["source_glb"] = source
    record["source_glb_sha256"] = _sha256_file(source)

    out_dir = os.path.join(work_dir, "MODEL", "3D")
    os.makedirs(out_dir, exist_ok=True)
    spec = {
        "source_glb": source,
        "output_dir": out_dir,
        "is_conceptual": is_conceptual,
        "renders": renders or ["hero", "section", "exploded"],
        "export_glbs": True,
        "resolution": resolution or [1152, 768],
        "samples": samples or 48,
    }
    spec_path = os.path.join(out_dir, "render_spec.json")
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)

    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "2")
    try:
        proc = subprocess.run(
            [blender, "--background", "--factory-startup",
             "--python", RENDER_SCRIPT, "--", spec_path],
            capture_output=True, text=True, timeout=_BLENDER_TIMEOUT_S,
            cwd=out_dir, env=env)
    except subprocess.TimeoutExpired:
        record["status"] = "RENDER_TIMEOUT"
        record["timeout_seconds"] = _BLENDER_TIMEOUT_S
        record["note"] = (
            "Blender exceeded the render budget — typed failure; the GLB "
            "contract is unaffected (interactive 3D served from the "
            "authoritative geometry)")
        return record
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        record["status"] = "RENDER_FAILED"
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    record["blender_exit_code"] = proc.returncode
    # pull the blender-side record (authoritative detail)
    side_path = os.path.join(out_dir, "render_record.json")
    if os.path.isfile(side_path):
        try:
            side = json.loads(Path(side_path).read_text())
            record["blender"] = side
        except Exception:  # noqa: BLE001
            record["blender_record_unreadable"] = True
    if proc.returncode != 0:
        record["status"] = "RENDER_FAILED"
        record["stderr_tail"] = (proc.stderr or "")[-2000:]
        return record

    # verify every artifact class exists (operator §4: EVERY invention
    # gets the six artifacts when the stack is available)
    produced = {}
    missing = []
    for name in _ARTIFACTS:
        p = os.path.join(out_dir, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            produced[name] = {"bytes": os.path.getsize(p),
                              "sha256": _sha256_file(p)}
        else:
            missing.append(name)
    record["artifacts"] = produced
    record["missing_artifacts"] = missing
    if missing:
        record["status"] = "RENDER_PARTIAL"
        record["note"] = (
            f"Blender completed but {len(missing)} artifact(s) missing: "
            f"{missing} — disclosed; GLB contract unaffected")
    record["seconds"] = round(time.time() - t0, 2)
    record["out_dir"] = out_dir
    return record
