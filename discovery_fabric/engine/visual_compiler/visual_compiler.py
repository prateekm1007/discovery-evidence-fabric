"""visual_compiler.py — R441 the Visual Compiler orchestrator; R443
integrity hardening.

One entry point, one typed record — the same honest contract the
Blender path had (status / artifacts / source provenance / budget),
now over the deterministic Three.js pipeline, with two NEW hard
outputs the old pipeline never produced:

  * visual_gate.json  — the Visual Quality Gate verdict (R443
    vocabulary: COMPLETE_PASS / PARTIAL / NOT_RUN / FAIL); anything
    but COMPLETE_PASS suppresses the hero and blocks package release
    (Article LXXII);
  * scene_spec.json   — the deterministic scene the renderer executed
    (hash-recorded; the website and the PDF render from the SAME spec).

R443 (operator directive — Visual Integrity Hardening): EVERY return
record is finalized through render_record_schema — a skipped/failed
render carries the same typed shape as a successful one (out_dir null
when nothing was produced, visual_gate NOT_RUN, release blocked, a
non-empty reason) — and the artifact inventory is the FULL R443
required ladder (hero, poster, dimension, section, exploded when
multi-part, orthographic x4, turntable x12), so a missing view is a
typed PARTIAL, never silence.

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
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import camera_solver, material_mapper, render_worker, scene_builder
from . import visual_gate
from . import visual_set
from . import render_record_schema
from . import RENDER_PIPELINE

_META_ARTIFACTS = ("render_record.json", "scene_spec.json",
                   "visual_gate.json",
                   "VISUAL_COMPILER_INVOCATION.json")
DEFAULT_RESOLUTION = [1536, 1024]
DEFAULT_TURNTABLE_FRAMES = visual_set.DEFAULT_TURNTABLE_FRAMES

# R451-C2 (C2.9): the invocation receipt. "GLB exists" and "the GLB was
# passed to the renderer" are different facts (the BS-003/BS-030 class:
# built is not wired). The receipt is written at EVERY exit of the
# compiler — success, typed skip, failure — so the join is
# machine-distinguishable from the run directory alone:
#   receipt absent                          -> the boundary was never reached
#   receipt.status startswith RENDER_SKIPPED -> reached, did not render
#   receipt.status SUCCEEDED/PARTIAL        -> reached AND rendered
RECEIPT_FILENAME = "VISUAL_COMPILER_INVOCATION.json"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_invocation_receipt(work_dir: str, record: Dict[str, Any],
                              geometry_out: Optional[Dict[str, Any]],
                              ) -> Optional[str]:
    """R451-C2 (C2.9) / R451-C2.2 (§5): persist the invocation receipt
    for one boundary pass. Written on EVERY exit (the caller wraps the
    whole compile); every field is read from the record or the run's
    own files — never invented (Art. VI). Returns the receipt path, or
    None when the receipt could not be written (typed in the return
    value only; a receipt failure never alters the render record's
    epistemic content).

    Schema 1.1.0 (R451-C2.2 §5 — the directive's exact field contract;
    the 1.0.0 names are superseded IN THE SAME CHANGE — Art. LXIV):

        run_id, generation_id, geometry_spec_sha256, glb_sha256,
        visual_compiler_version, invocation_status, skip_reason,
        render_record_reference

    render_record_reference points at the persisted render record when
    one exists on disk (the success path wrote it before this receipt
    is written); it is None for every skip/failure exit — the receipt
    itself is then the boundary's only verdict (never an invented
    reference, Art. VI)."""
    try:
        run_id = Path(work_dir).name
        generation_id = (geometry_out or {}).get("generation_id")
        if not generation_id:
            # the run's own artifact identity doc is the recorded source
            aid = Path(work_dir) / "MODEL" / "ARTIFACT_IDENTITY.json"
            if aid.is_file():
                try:
                    generation_id = (json.loads(aid.read_text(encoding="utf-8"))
                                     or {}).get("generation_id")
                except Exception:  # noqa: BLE001 — absent stays absent
                    generation_id = None
        spec_path = Path(work_dir) / "MODEL" / "GEOMETRY_SPEC.json"
        geometry_spec_sha256 = (_sha256_file(str(spec_path))
                                if spec_path.is_file() else None)
        glb_sha = record.get("source_glb_sha256")
        if not glb_sha:
            # early typed skips (renderer/deps guards) exit before the
            # source is resolved — the receipt still names the GLB that
            # sat at the boundary, read from the same resolution order
            # the compiler itself uses (never invented, Art. VI)
            waiting = authoritative_glb(
                work_dir, (geometry_out or {}).get("generation_models"))
            if waiting and Path(waiting).is_file():
                glb_sha = _sha256_file(waiting)
        invocation_status = str(record.get("status") or "UNKNOWN")
        skip_reason = None
        if invocation_status.startswith("RENDER_SKIPPED") or \
                invocation_status in ("RENDER_FAILED", "RENDER_TIMEOUT"):
            skip_reason = (record.get("reason") or record.get("note")
                           or record.get("error"))
        # the boundary's output directory is canonical (always
        # MODEL/3D under the run dir) — recorded even on the
        # earliest skips, whose records may not carry out_dir
        out_dir = Path(work_dir) / "MODEL" / "3D"
        record_ref = out_dir / "render_record.json"
        receipt = {
            "kind": "VISUAL_COMPILER_INVOCATION",
            "schema_version": "1.1.0",
            "run_id": run_id,
            "generation_id": generation_id,
            "glb_sha256": glb_sha,
            "geometry_spec_sha256": geometry_spec_sha256,
            "visual_compiler_version": RENDER_PIPELINE,
            "invocation_status": invocation_status,
            "gate_version": visual_gate.GATE_VERSION,
            "invoked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
            "skip_reason": skip_reason,
            "render_record_reference":
                str(record_ref) if record_ref.is_file() else None,
            "output_directory": record.get("out_dir")
            or str(out_dir),
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / RECEIPT_FILENAME
        path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return str(path)
    except Exception as exc:  # noqa: BLE001 — typed, never fatal
        try:
            print(f"[visual_compiler] invocation receipt not written: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr,
                  flush=True)
        except Exception:  # noqa: BLE001
            pass
        return None


def _finish(record: Dict[str, Any]) -> Dict[str, Any]:
    """The ONE exit: finalize the record to its status's total typed
    shape, then validate. A validation failure is converted to a
    fail-closed RENDER_FAILED record (and re-validated) — a malformed
    record must never reach a consumer (R443 Workstream 4, Attack 4)."""
    render_record_schema.finalize_render_record(record)
    try:
        render_record_schema.validate_render_record(record)
    except render_record_schema.RenderRecordValidationError as exc:
        broken = dict(record)
        record.clear()
        record.update({
            "stage": "RENDER",
            "render_pipeline": RENDER_PIPELINE,
            "status": "RENDER_FAILED",
            "error": f"render record schema violation: {exc}",
            "reason": f"render record schema violation: {exc}",
            "note": ("the compiler refused to emit a record that is "
                     "not structurally valid for its status — fail "
                     "closed before any consumer sees it"),
            "broken_record_snapshot_keys": sorted(broken),
        })
        render_record_schema.finalize_render_record(record)
        render_record_schema.validate_render_record(record)
    return record


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

    R451-C2 (C2.9): EVERY exit also persists the invocation receipt
    (VISUAL_COMPILER_INVOCATION.json) — the mechanical, on-disk proof
    that the presentation boundary was reached, and whether the
    renderer actually ran (BS-003/BS-030: built is not wired).
    """
    record = _compile_visuals_inner(
        work_dir, geometry_out=geometry_out, is_conceptual=is_conceptual,
        resolution=resolution, turntable_frames=turntable_frames,
        timeout_s=timeout_s, memory_mode=memory_mode, views=views,
        context=context)
    _write_invocation_receipt(work_dir, record, geometry_out)
    return record


def _compile_visuals_inner(work_dir: str,
                           geometry_out: Optional[Dict[str, Any]] = None,
                           is_conceptual: bool = False,
                           resolution: Optional[List[int]] = None,
                           turntable_frames: Optional[int] = None,
                           timeout_s: Optional[int] = None,
                           memory_mode: str = "async",
                           views: Optional[Dict[str, bool]] = None,
                           context: str = "visual_compiler",
                           ) -> Dict[str, Any]:
    """The compile body (single entry, single typed record) — the
    receipt wrapper above owns the boundary bookkeeping."""
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

    # memory guard BEFORE any subprocess (the R420d discipline). The
    # guard record is merged and then finalized like every other exit:
    # the R442-disclosed defect (skip records without out_dir /
    # visual_gate) is structurally impossible after _finish.
    guard = render_worker.memory_guard(context, mode=memory_mode)
    if guard:
        return _finish({**record,
                        **{k: v for k, v in guard.items() if k != "stage"}})

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
        return _finish(record)
    deps = _rw.renderer_deps_present()
    if deps:
        record["status"] = deps
        record["note"] = (f"the renderer dependency contract is not met "
                          f"({deps}) — typed skip")
        return _finish(record)

    source = authoritative_glb(
        work_dir, (geometry_out or {}).get("generation_models"))
    if not source:
        record["status"] = "RENDER_SKIPPED_NO_SOURCE_GLB"
        record["note"] = ("no authoritative GLB found in the run "
                          "directory — typed skip; the interactive GLB "
                          "is served unchanged")
        return _finish(record)
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
        record["out_dir"] = out_dir
        return _finish(record)
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
        return _finish(rec)
    record.update({k: v for k, v in rec.items() if k != "stage"})

    # ---- verify artifacts on disk (the record's hashes re-computed) ----
    # the FULL R443 required ladder — a missing view is a typed PARTIAL,
    # never silence (the gate re-derives the same classification)
    mandatory = visual_set.required_artifacts(
        int(spec["model"]["node_count"]), turntable_frames)["required"]
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
            f"missing: {missing[:8]} — disclosed, never silent")

    # ---- the Visual Quality Gate (Article LXXII) ----------------------------
    gate = visual_gate.evaluate(out_dir, spec, record, record["status"])
    gate_path = visual_gate.write_gate(out_dir, gate)
    record["visual_gate"] = gate
    record["visual_gate_path"] = str(gate_path)
    record["hero_suppressed"] = gate.get("hero_suppressed", True)
    record["release_blocked"] = gate.get("release_blocked", True)
    record["out_dir"] = out_dir
    record = _finish(record)
    # R444-C2: the BUYER SURFACE carries the finalized typed record.
    # The node-side side-record written by render.js is the renderer's
    # contemporaneous claim; its full content was merged into this
    # record, which is then finalized + validated for its status (R443
    # Workstream 4). Persisting the validated record in place means the
    # shipped bytes satisfy the same schema the in-memory record does —
    # a package copy of render_record.json can therefore be schema-
    # checked and lineage-checked AS SHIPPED, not merely as returned.
    # (Art. LXIV disposition: the side-record shape is superseded by
    # this merge-and-persist; no second record shape survives on disk.)
    (Path(out_dir) / "render_record.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    return record


def _with_chrome(rspec_path: str) -> str:
    """The renderer spec MUST carry the chrome binary the worker itself
    verified — the placeholder file is rewritten here, inside the
    process boundary, so the page never runs against an unverified
    binary (fail-closed provenance, Art. VI)."""
    chrome = render_worker._LAST_RESOLUTION.get("accepted_chrome") \
        or render_worker.find_chrome()
    spec = json.loads(Path(rspec_path).read_text(encoding="utf-8"))
    spec["chrome_path"] = chrome
    Path(rspec_path).write_text(json.dumps(spec), encoding="utf-8")
    return rspec_path
