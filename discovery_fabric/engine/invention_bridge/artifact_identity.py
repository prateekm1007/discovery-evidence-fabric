"""Canonical visual-artifact identity (R432 section 20).

Every generated visual artifact carries the identity chain the browser
(and the package, and the dossier) can use to establish:

    THIS MODEL  =  THIS INVENTION GENERATION  =  THIS CANONICAL GEOMETRY

    technology_id        the stable technology identity (problem_id /
                         invention family the run belongs to)
    run_id               the session that produced it
    generation_id        which invention generation the model renders
    geometry_hash        sha256 of the GLB bytes (the model itself)
    source_geometry_hash sha256 of the canonical geometry spec (the
                         deterministic source the model was built from)
    blender_scene_hash   sha256 of the Blender render record (the
                         presentation layer identity; null until the
                         render stage has actually executed — never a
                         guess, Art. VI)
    cad_source           engineering path only: the canonical builder
                         identity (module + builder hashes)

The identity doc is PERSISTED at MODEL/ARTIFACT_IDENTITY.json and
projected through the CIO into the dossier's Design tab. It is derived
— never hand-authored — and every field comes from a real artifact on
disk at build time.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

IDENTITY_VERSION = "1.0.0"


def _sha_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def build_artifact_identity(
    run_dir: str,
    technology_id: str,
    run_id: str,
    generation_id: str,
    geometry_hash: str,
    source_geometry_hash: Optional[str],
    glb_path: Optional[str] = None,
    cad_source: Optional[Dict[str, Any]] = None,
    visualizability_class: Optional[str] = None,
    domain_family: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble + persist the identity doc. The blender_scene_hash is
    filled only when a render record exists on disk (the render stage
    may run later — async — and refreshes the identity then)."""
    d = Path(run_dir)
    model_dir = d / "MODEL"

    blender_hash = None
    render_record = model_dir / "3D" / "render_record.json"
    if render_record.is_file():
        blender_hash = _sha_file(render_record)

    # the GLB on disk must be the bytes the hash claims (drift check
    # basis; None when the file is absent — honest, never guessed)
    disk_glb = _sha_file(Path(glb_path)) if glb_path else None

    doc = {
        "artifact": "ARTIFACT_IDENTITY",
        "identity_version": IDENTITY_VERSION,
        "technology_id": str(technology_id) or None,
        "run_id": str(run_id) or None,
        "generation_id": str(generation_id) or None,
        "geometry_hash": str(geometry_hash) or None,
        "source_geometry_hash": source_geometry_hash,
        "blender_scene_hash": blender_hash,
        "glb_path": str(glb_path) if glb_path else None,
        "glb_disk_sha256": disk_glb,
        "glb_matches_geometry_hash": (
            disk_glb is not None and disk_glb == geometry_hash),
        "cad_source": cad_source,
        "visualizability_class": visualizability_class,
        "domain_family": domain_family,
        "derived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "derivation": ("assembled from persisted run artifacts only — "
                       "every hash from a real file at build time "
                       "(Art. VI); blender_scene_hash fills when the "
                       "render stage records its scene"),
    }
    return doc


def persist(run_dir: str, doc: Dict[str, Any]) -> Optional[str]:
    """Write MODEL/ARTIFACT_IDENTITY.json (+ its own sha) and return
    the path."""
    try:
        model_dir = Path(run_dir) / "MODEL"
        model_dir.mkdir(parents=True, exist_ok=True)
        path = model_dir / "ARTIFACT_IDENTITY.json"
        raw = json.dumps(doc, indent=2, sort_keys=True).encode() + b"\n"
        path.write_bytes(raw)
        (model_dir / "ARTIFACT_IDENTITY.sha256").write_text(
            f"{hashlib.sha256(raw).hexdigest()}  ARTIFACT_IDENTITY.json\n")
        return str(path)
    except OSError:
        return None


def load(run_dir: str) -> Optional[Dict[str, Any]]:
    path = Path(run_dir) / "MODEL" / "ARTIFACT_IDENTITY.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def refresh_blender_hash(run_dir: str) -> Optional[str]:
    """The render stage completed: re-derive blender_scene_hash from
    the render record and rewrite the identity doc (append-only in
    spirit — the doc records the latest presentation layer identity;
    the render record itself carries the full history)."""
    d = Path(run_dir)
    doc = load(run_dir)
    if doc is None:
        return None
    rr = d / "MODEL" / "3D" / "render_record.json"
    h = _sha_file(rr) if rr.is_file() else None
    if h is None:
        return None
    doc["blender_scene_hash"] = h
    doc["blender_scene_refreshed_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    persist(run_dir, doc)
    return h
