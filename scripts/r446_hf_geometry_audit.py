#!/usr/bin/env python3
"""scripts/r446_hf_geometry_audit.py — R446-HF Phase 10: the Coder 1
geometry differentiation audit across the three fresh cases.

The directive's requirement (Phase 10), on the HF deployment's OWN runs:

    different mechanism
        -> different engineering parameterization
        -> different geometry spec
        -> different canonical GLB

Do NOT accept 'different text, same geometry'.

Method (all from the runs' OWN recorded artifacts — Art. X; the GLB
analysis is loader-free over the raw glTF JSON chunk, the R443-C2 gate
discipline):

  per case:
    - technology_class + canonical domain (the CIO/geometry records)
    - mechanism identity (the CIO's identity.mechanism)
    - component roles (the CIO geometry.components names/types)
    - GLB node identity set (raw glTF JSON chunk node names)
    - bounding boxes (POSITION accessor min/max per mesh, loader-free)
    - byte size + sha256 of the canonical GLB

  across cases (pairwise):
    - mechanism distinctness (text-level, honestly labeled)
    - component-set overlap (Jaccard)
    - node-set overlap (Jaccard)
    - bounding-box shape comparison (normalized extents)
    - GLB byte-identity (MUST differ; identical bytes = the R442
      'byte-identical generic shells' defect class)

The audit READS the captured artifacts in R446/HF_PRODUCTION_RUNS/ (the
bytes the server served — sha-verified in the production record) and the
CIO bodies. Nothing is re-derived from local state.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "R446" / "HF_PRODUCTION_RUNS"
RUNS_JSON = REPO_ROOT / "R446" / "HF_PRODUCTION_RUNS.json"
OUT = REPO_ROOT / "R446" / "HF_GEOMETRY_AUDIT.json"


def _glb_nodes_and_boxes(glb: bytes) -> Dict[str, Any]:
    """Loader-free GLB analysis: node names + per-node bounding boxes
    from the raw glTF JSON chunk + POSITION accessor min/max."""
    if glb[:4] != b"glTF":
        return {"error": "not a GLB"}
    version, total_len = struct.unpack_from("<II", glb, 4)
    # first chunk: JSON
    chunk_len, chunk_type = struct.unpack_from("<II", glb, 12)
    if chunk_type != 0x4E4F534A:
        return {"error": "first chunk is not JSON"}
    doc = json.loads(glb[20:20 + chunk_len])
    nodes = doc.get("nodes") or []
    meshes = doc.get("meshes") or []
    accessors = doc.get("accessors") or []
    out_nodes: List[Dict[str, Any]] = []
    for n in nodes:
        entry: Dict[str, Any] = {"name": n.get("name")}
        mesh_idx = n.get("mesh")
        if mesh_idx is not None and mesh_idx < len(meshes):
            prims = (meshes[mesh_idx].get("primitives") or [])
            boxes = []
            for p in prims:
                pos_acc = p.get("attributes", {}).get("POSITION")
                if pos_acc is not None and pos_acc < len(accessors):
                    acc = accessors[pos_acc]
                    mn, mx = acc.get("min"), acc.get("max")
                    if mn and mx:
                        boxes.append({"min": mn, "max": mx})
            entry["n_prims"] = len(prims)
            if boxes:
                entry["bbox_min"] = [min(b["min"][i] for b in boxes)
                                     for i in range(3)]
                entry["bbox_max"] = [max(b["max"][i] for b in boxes)
                                     for i in range(3)]
        out_nodes.append(entry)
    return {
        "glb_version": version,
        "n_nodes": len(nodes),
        "n_meshes": len(meshes),
        "nodes": out_nodes,
    }


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def _norm_extent(box: Dict[str, Any]) -> Optional[List[float]]:
    mn, mx = box.get("bbox_min"), box.get("bbox_max")
    if not mn or not mx:
        return None
    ext = [mx[i] - mn[i] for i in range(3)]
    s = sum(ext) or 1.0
    return [round(e / s, 4) for e in ext]


def main() -> None:
    runs = json.loads(RUNS_JSON.read_text())
    cases = [c for c in runs.get("cases", [])
             if (c.get("problem") or {}).get("case_id")]
    per_case: List[Dict[str, Any]] = []
    for c in cases:
        rid = c["run_id"]
        glb_path = RUNS_DIR / f"{rid}_canonical.glb"
        cio_path = RUNS_DIR / f"{rid}_cio.json"
        if not glb_path.exists() or not cio_path.exists():
            continue
        glb = glb_path.read_bytes()
        cio = json.loads(cio_path.read_text())
        geo = cio.get("geometry") or {}
        ident = cio.get("identity") or {}
        analysis = _glb_nodes_and_boxes(glb)
        node_names = [n.get("name") for n in analysis.get("nodes", [])
                      if n.get("name")]
        comp_names = [x.get("name") for x in (geo.get("components") or [])
                      if isinstance(x, dict)]
        # overall scene bbox from all node boxes
        all_min, all_max = None, None
        for n in analysis.get("nodes", []):
            if "bbox_min" in n:
                if all_min is None:
                    all_min, all_max = list(n["bbox_min"]), list(
                        n["bbox_max"])
                else:
                    for i in range(3):
                        all_min[i] = min(all_min[i], n["bbox_min"][i])
                        all_max[i] = max(all_max[i], n["bbox_max"][i])
        per_case.append({
            "case_id": (c.get("problem") or {}).get("case_id"),
            "run_id": rid,
            "directive_class": (c.get("problem") or {}).get(
                "directive_class"),
            "canonical_domain": (c.get("technical_state") or {}).get(
                "canonical_domain"),
            "mechanism": (ident.get("mechanism") or {}).get("mechanism")
            if isinstance(ident.get("mechanism"), dict)
            else ident.get("mechanism"),
            "intervention": (ident.get("mechanism") or {}).get(
                "intervention") if isinstance(ident.get("mechanism"),
                                              dict) else None,
            "geometry_class": geo.get("class"),
            "domain_family": geo.get("domain_family"),
            "technology_class": (geo.get("artifact_identity") or {}).get(
                "technology_class") or geo.get("technology_class"),
            "n_components_declared": len(comp_names),
            "components_declared": comp_names,
            "glb": {
                "bytes": len(glb),
                "sha256": c.get("geometry", {}).get("glb_sha256"),
                "n_nodes": analysis.get("n_nodes"),
                "n_meshes": analysis.get("n_meshes"),
                "node_names": node_names,
                "scene_bbox_min": [round(v, 3) for v in all_min]
                if all_min else None,
                "scene_bbox_max": [round(v, 3) for v in all_max]
                if all_max else None,
                "normalized_extent": _norm_extent({
                    "bbox_min": all_min, "bbox_max": all_max})
                if all_min else None,
            },
        })

    pairwise: List[Dict[str, Any]] = []
    for i in range(len(per_case)):
        for j in range(i + 1, len(per_case)):
            a, b = per_case[i], per_case[j]
            ga, gb = a["glb"], b["glb"]
            pairwise.append({
                "pair": f'{a["case_id"]} vs {b["case_id"]}',
                "mechanism_distinct": (
                    a.get("mechanism") != b.get("mechanism")),
                "domain_distinct": (
                    a.get("canonical_domain") != b.get("canonical_domain")),
                "component_set_jaccard": round(_jaccard(
                    a["components_declared"], b["components_declared"]), 4),
                "node_set_jaccard": round(_jaccard(
                    ga.get("node_names") or [],
                    gb.get("node_names") or []), 4),
                "glb_byte_identical": ga.get("sha256") == gb.get("sha256"),
                "glb_size_ratio": round(
                    max(ga.get("bytes", 1), gb.get("bytes", 1)) /
                    max(1, min(ga.get("bytes", 1), gb.get("bytes", 1))), 2),
                "normalized_extent_a": ga.get("normalized_extent"),
                "normalized_extent_b": gb.get("normalized_extent"),
                "extent_shape_distinct": (
                    ga.get("normalized_extent")
                    != gb.get("normalized_extent")),
            })

    failures = [p for p in pairwise
                if p["glb_byte_identical"]
                or p["node_set_jaccard"] >= 0.999
                or (p["component_set_jaccard"] >= 0.999
                    and p["glb_size_ratio"] == 1.0)]
    audit = {
        "artifact_type": "R446-HF Phase 10 geometry differentiation audit",
        "method": ("the deployment's OWN served artifacts: canonical GLB "
                   "bytes (sha-verified) analyzed loader-free over the raw "
                   "glTF JSON chunk + POSITION accessor min/max; the CIO's "
                   "own geometry/identity records for the semantic fields"),
        "per_case": per_case,
        "pairwise": pairwise,
        "differentiation_verdict": "DIFFERENTIATED" if (
            per_case and len(pairwise) >= 3 and not failures
        ) else ("CHECK" if per_case else "NO_DATA"),
        "byte_identical_generic_shell": [p["pair"] for p in pairwise
                                         if p["glb_byte_identical"]],
        "reviewer_provenance": "AI_REVIEW",
        "note": ("the R442 defect class under test: different inventions "
                 "receiving identical chassis geometry (byte-identical "
                 "heroes). The R443+ causal-geometry chain was verified "
                 "live then; this audit re-verifies on the HF deployment's "
                 "fresh runs. A mechanism-distinct pair with identical "
                 "GLB bytes or identical node sets = FAILURE."),
    }
    OUT.write_text(json.dumps(audit, indent=2))
    print(json.dumps({
        "cases": len(per_case),
        "verdict": audit["differentiation_verdict"],
        "pairs": [(p["pair"], "byte_identical=" + str(
            p["glb_byte_identical"]), "node_jaccard=" + str(
            p["node_set_jaccard"])) for p in pairwise],
    }, indent=2))


if __name__ == "__main__":
    main()
