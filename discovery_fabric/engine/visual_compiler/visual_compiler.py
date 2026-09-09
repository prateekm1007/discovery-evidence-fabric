"""visual_compiler.py — R441 the Visual Compiler orchestrator.

One entry point, one typed record — the same honest contract the
Blender path had (status / artifacts / source provenance / budget),
now over the deterministic Three.js pipeline, with two NEW hard
outputs the old pipeline never produced:

  * visual_gate.json  — the Visual Quality Gate verdict; a FAIL
    suppresses the hero and blocks package release (Article LXXII);
  * scene_spec.json   — the deterministic scene the renderer executed
    (hash-recorded; the website and the PDF render from the SAME spec).

Pipeline (operator directive R441):

    CadQuery/OCCT GLB
      -> scene_builder   (bbox, centering, grounding — no floating parts)
      -> material_mapper (semantic materials from component type)
      -> camera_solver   (hero 70-85% / ortho / section / exploded)
      -> render_worker   (headless Chromium + Three.js, SwiftShader)
      -> visual_gate     (independent pixel verification, NO HERO on fail)
      -> website + PDF   (the exact same approved render)
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import camera_solver, material_mapper, render_worker, scene_builder
from . import visual_gate
from . import RENDER_PIPELINE

# the mandatory visual set (R441: every package must generate these
# AUTOMATICALLY — a missing class is a typed PARTIAL, never silence).
# The exploded pair is conditional: a single-part architecture has
# nothing to separate — its typed skip is disclosed in the render
# record, never faked (Art. XXV).
BASE_ARTIFACTS = (
    "hero.png", "hero.glb",
    "poster.png", "dimension.png",
    "section.png",
    "orthographic/front.png", "orthographic/side.png",
    "orthographic/top.png", "orthographic/iso.png",
)
EXPLODED_ARTIFACTS = ("exploded.png", "exploded.glb")
_META_ARTIFACTS = ("render_record.json", "scene_spec.json",
                   "visual_gate.json")
DEFAULT_RESOLUTION = [1536, 1024]
DEFAULT_TURNTABLE_FRAMES = 12


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def authoritative_glb(work_dir: str,
                      generation_models: Optional[List[Dict]] = None
                      ) -> Optional[str]:
    """The CURRENT generation's GLB — the geometry authority to render
    (the same resolution order the R419 path defined; now owned here
    so the visual compiler is self-contained)."""
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


def compile_visuals(work_dir: str,
                    geometry_out: Optional[Dict[str, Any]] = None,
                    is_conceptual: bool = False,
                    resolution: Optional[List[int]] = None,
                    turntable_frames: Optional[int] = None,
                    timeout_s: Optional[int] = None,
                    memory_mode: str = "async",
                    views: Optional[Dict[str, bool]] = None,
                    context: str = "visual_compiler",
                    ) -> Dict[str, Any]:
    """Run the full visual compiler over the authoritative GLB.

    Returns a typed render record — always honest, never raising into
    the caller (a presentation-layer failure never alters the run's
    epistemic state; Art. LXI). The record's `visual_gate` carries the
    release decision: `hero_suppressed` / `release_blocked`.
    """
    if timeout_s is None:
        try:
            timeout_s = max(120, int(os.environ.get(
                "ENGINE_VC_TIMEOUT_S", "480")))
        except (TypeError, ValueError):
            timeout_s = 480
    resolution = resolution or DEFAULT_RESOLUTION
    turntable_frames = turntable_frames or DEFAULT_TURNTABLE_FRAMES

    record: Dict[str, Any] = {
        "stage": "RENDER",
        "render_pipeline": RENDER_PIPELINE,
        "is_conceptual": bool(is_conceptual),
        "memory_mode": memory_mode,
        "budget_seconds": timeout_s,
        "status": "OK",
    }

    # memory guard BEFORE any subprocess (the R420d discipline)
    guard = render_worker.memory_guard(context, mode=memory_mode)
    if guard:
        return {**record, **{k: v for k, v in guard.items()
                             if k != "stage"}}

    # the renderer availability check is the CHEAPEST typed skip — run
    # it before any scene work (a renderer-less environment fails in
    # milliseconds, not after a scene solve)
    from . import render_worker as _rw
    if not _rw.find_node() or not _rw.find_chrome():
        record["status"] = "RENDER_SKIPPED_NO_RENDERER"
        record["binary_resolution"] = _rw.last_resolution()
        record["note"] = ("no verified Chromium/Node pair in this "
                          "environment — typed skip; the interactive "
                          "GLB is served unchanged")
        return record
    deps = _rw.renderer_deps_present()
    if deps:
        record["status"] = deps
        record["note"] = (f"the renderer dependency contract is not met "
                          f"({deps}) — typed skip")
        return record

    source = authoritative_glb(
        work_dir, (geometry_out or {}).get("generation_models"))
    if not source:
        record["status"] = "RENDER_SKIPPED_NO_SOURCE_GLB"
        record["note"] = ("no authoritative GLB found in the run "
                          "directory — typed skip; the interactive GLB "
                          "is served unchanged")
        return record
    record["source_glb"] = source
    record["source_glb_sha256"] = _sha256_file(source)

    out_dir = os.path.join(work_dir, "MODEL", "3D")
    os.makedirs(out_dir, exist_ok=True)

    # ---- the deterministic scene solve ------------------------------------
    # a scene the compiler cannot solve (corrupt/partial GLB) is a TYPED
    # failure at the source — never a raised exception into the worker
    # (Art. LXI discipline, applied to the compiler itself)
    try:
        gspec = material_mapper.load_geometry_spec(work_dir, geometry_out)
        inventory = scene_builder.inspect_glb(source)
        mapping = material_mapper.build_mapping(
            [n["name"] for n in inventory["nodes"]], gspec)
        spec = scene_builder.build_scene_spec(source, gspec, mapping)
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        record["status"] = "RENDER_FAILED"
        record["error"] = (f"scene solve failed on the canonical GLB: "
                           f"{type(exc).__name__}: {exc}")
        record["note"] = ("the GLB the geometry authority produced could "
                          "not be solved for presentation — typed "
                          "failure; the interactive GLB contract is "
                          "unaffected and the geometry stage owns the "
                          "defect")
        record["visual_gate"] = {
            "gate_version": visual_gate.GATE_VERSION,
            "verdict": "NOT_RUN", "hero_suppressed": True,
            "release_blocked": True,
            "reasons": [record["error"]], "checks": {}}
        record["hero_suppressed"] = True
        record["release_blocked"] = True
        return record
    spec["solve"] = camera_solver.solve(spec)
    spec["domain_family"] = (geometry_out or {}).get("domain_family")
    spec_bytes = scene_builder.scene_spec_bytes(spec)
    spec_path = os.path.join(out_dir, "scene_spec.json")
    with open(spec_path, "wb") as f:
        f.write(json.dumps(spec, indent=2, sort_keys=True).encode("utf-8"))
    record["scene_spec_sha256"] = hashlib.sha256(spec_bytes).hexdigest()

    # ---- renderer payload --------------------------------------------------
    payload = {
        "glb_sha256": record["source_glb_sha256"],
        "scene_spec": spec,
        "resolution": resolution,
        "draft_scale": 0.35,
        "turntable_frames": turntable_frames,
        "explode_factor": spec["solve"]["camera"]["exploded"]["factor"],
        "views": views or {},
        "poster": {
            "title": (geometry_out or {}).get("invention_label")
            or "Technology artifact",
            "subtitle": ("engineering model · Visual Compiler R441"
                         if not is_conceptual
                         else "conceptual design · Visual Compiler R441"),
        },
    }
    rspec_path = os.path.join(out_dir, "render_payload.json")
    with open(rspec_path, "w") as f:
        json.dump({"chrome_path": None, "output_dir": out_dir,
                   "source_glb": source,
                   "timeout_ms": int(timeout_s * 1000 * 0.9),
                   "payload": payload}, f)
    # chrome_path is injected by the worker from its own verified
    # resolution — never trusted from a pre-written file (Art. III);
    # render.js reads chrome_path at the top level of the spec, so the
    # payload file carries a placeholder the worker replaces.
    # (run_renderer re-writes the file with the verified binary path.)

    # ---- run the renderer ---------------------------------------------------
    rec = render_worker.run_renderer(
        _with_chrome(rspec_path), timeout_s, context=context)
    status = rec.get("status") or ""
    if status.startswith("RENDER_SKIPPED") or status in (
            "RENDER_FAILED", "RENDER_TIMEOUT"):
        rec["source_glb"] = record["source_glb"]
        rec["source_glb_sha256"] = record["source_glb_sha256"]
        rec["scene_spec_sha256"] = record["scene_spec_sha256"]
        # a skipped/failed render CANNOT pass the gate (fail closed,
        # Art. V/XXV) — the hero is suppressed, the release is blocked
        rec["visual_gate"] = {
            "gate_version": visual_gate.GATE_VERSION,
            "verdict": "NOT_RUN",
            "hero_suppressed": True,
            "release_blocked": True,
            "reasons": [f"renderer status {status}: the gate refuses to "
                        "pass what it cannot measure"],
            "checks": {},
        }
        rec["hero_suppressed"] = True
        rec["release_blocked"] = True
        rec["out_dir"] = out_dir
        return rec
    record.update({k: v for k, v in rec.items() if k != "stage"})

    # ---- verify artifacts on disk (the record's hashes re-computed) ----
    mandatory = list(BASE_ARTIFACTS)
    if spec["model"]["node_count"] >= 2:
        mandatory += list(EXPLODED_ARTIFACTS)
    produced: Dict[str, Any] = {}
    missing: List[str] = []
    for name in mandatory:
        p = Path(out_dir) / name
        if p.is_file() and p.stat().st_size > 0:
            produced[name] = {"bytes": p.stat().st_size,
                              "sha256": _sha256_file(str(p))}
        else:
            missing.append(name)
    record["artifacts"] = produced
    record["missing_artifacts"] = missing
    if missing:
        record["status"] = "PARTIAL"
        record["note"] = (
            f"the visual set completed with {len(missing)} artifact(s) "
            f"missing: {missing} — disclosed, never silent")

    # ---- the Visual Quality Gate (Article LXXII) ----------------------------
    gate = visual_gate.evaluate(out_dir, spec, record, record["status"])
    gate_path = visual_gate.write_gate(out_dir, gate)
    record["visual_gate"] = gate
    record["visual_gate_path"] = str(gate_path)
    record["hero_suppressed"] = gate.get("hero_suppressed", True)
    record["release_blocked"] = gate.get("release_blocked", True)
    record["out_dir"] = out_dir
    return record


def _with_chrome(rspec_path: str) -> str:
    """The renderer spec MUST carry the chrome binary the worker itself
    verified — the placeholder file is rewritten here, inside the
    process boundary, so the page never runs against an unverified
    binary (fail-closed provenance, Art. VI)."""
    chrome = render_worker._LAST_RESOLUTION.get("accepted_chrome") \
        or render_worker.find_chrome()
    spec = json.loads(Path(rspec_path).read_text())
    spec["chrome_path"] = chrome
    Path(rspec_path).write_text(json.dumps(spec))
    return rspec_path
