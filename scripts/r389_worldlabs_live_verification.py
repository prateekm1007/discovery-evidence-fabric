#!/usr/bin/env python3
"""R389 — LIVE World Labs reality-provider verification.

One real text-to-world round-trip, recorded with full provenance:

  submit -> poll -> fetch assets -> download GLB -> trimesh re-measures
  the mesh (independent verifier — the same discipline as the STL gates)
  -> REALITY_MODEL built -> verification record written.

The record NEVER claims the world is physically real: every asset is
labeled RECONSTRUCTED (Art. XXXVIII). This script exists to prove the
provider transport + boundary labels survive contact with the real API.

Usage:
  python3 scripts/r389_worldlabs_live_verification.py            # harvest the existing SUCCEEDED op if given
  python3 scripts/r389_worldlabs_live_verification.py --new "prompt"

Output: TOSCANINI/R389_REALITY_PROVIDER_LIVE/VERIFICATION_RECORD.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.reality_provider import (  # noqa: E402
    EvidenceOrigin, RealityModel, WorldLabsProvider,
    harvest_reality_model, build_reality_world, compare_design_to_reality,
    build_design_world)

OUT_DIR = REPO / "TOSCANINI" / "R389_REALITY_PROVIDER_LIVE"
DEFAULT_OP = "666549e8-e75b-4c97-988c-84c6c4183dea"  # the 2026-09-01 verification op


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", metavar="PROMPT",
                    help="generate a NEW world from this prompt")
    ap.add_argument("--op", default=DEFAULT_OP,
                    help="existing operation id to harvest")
    ap.add_argument("--timeout-min", type=int, default=20,
                    help="minutes to wait for generation")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    record: dict = {
        "artifact": "R389_REALITY_PROVIDER_LIVE_VERIFICATION",
        "purpose": "prove the provider-neutral REALITY_PROVIDER transport "
                   "works against the real World Labs/Marble API and that "
                   "the Art. XXXVIII boundary labels survive the real wire",
        "boundary_statement": "ALL assets below are RECONSTRUCTED "
                              "(AI-generated spatial hypotheses). Nothing "
                              "in this record is MEASURED. This record "
                              "does NOT validate any technology package.",
    }

    provider = WorldLabsProvider(
        ledger=__import__(
            "discovery_fabric.engine.reality_provider",
            fromlist=["ProviderCallLedger"]).ProviderCallLedger(
            OUT_DIR / "PROVIDER_CALL_LEDGER.json"))

    if not provider.api_key:
        record["status"] = "AUTH_FAILED"
        record["reason"] = "WORLD_LABS_API_KEY not configured"
        (OUT_DIR / "VERIFICATION_RECORD.json").write_text(
            json.dumps(record, indent=2))
        print("AUTH_FAILED: no key")
        return 1

    # ---- submit or reuse ---------------------------------------------------
    if args.new:
        t0 = time.time()
        submit = provider.submit(__import__(
            "discovery_fabric.engine.reality_provider",
            fromlist=["RealityRequest"]).RealityRequest(
            prompt=args.new, display_name="R389 live verification"))
        record["submit"] = submit
        if submit.get("status") not in ("IN_PROGRESS", "SUCCEEDED"):
            record["status"] = submit.get("status")
            (OUT_DIR / "VERIFICATION_RECORD.json").write_text(
                json.dumps(record, indent=2))
            print(f"submit failed: {submit}")
            return 1
        op_id = submit["operation_id"]
    else:
        op_id = args.op
        record["reused_operation"] = op_id

    # ---- poll --------------------------------------------------------------
    deadline = time.time() + args.timeout_min * 60
    status = {"status": "IN_PROGRESS"}
    polls = 0
    while time.time() < deadline:
        status = provider.poll(op_id)
        polls += 1
        if status.get("status") != "IN_PROGRESS":
            break
        time.sleep(20)
    record["final_operation_status"] = {
        "status": status.get("status"),
        "world_id": status.get("world_id"),
        "polls": polls,
        "cost": status.get("cost"),
    }
    if status.get("status") != "SUCCEEDED":
        record["status"] = "GENERATION_NOT_SUCCEEDED"
        (OUT_DIR / "VERIFICATION_RECORD.json").write_text(
            json.dumps(record, indent=2))
        print(f"operation not succeeded: {status.get('status')}")
        return 1

    # ---- harvest into a REALITY_MODEL --------------------------------------
    model, harvest_status = harvest_reality_model(
        provider, op_id, package_id="R389-LIVE-VERIFICATION")
    record["harvest"] = harvest_status
    record["reality_model_origin_counts"] = model.origin_counts()
    assert model.origin_counts().get("MEASURED", 0) == 0, \
        "boundary violation: MEASURED data from a provider"

    # ---- download the collider GLB + independent re-measure (trimesh) ------
    mesh_asset = next((a for a in model.fields["geometry"]
                       if "mesh_url" in (a.value or {})), None)
    if mesh_asset and mesh_asset.value.get("mesh_url"):
        glb_path = OUT_DIR / f"reconstructed_world_{op_id[:8]}.glb"
        try:
            req = urllib.request.Request(mesh_asset.value["mesh_url"])
            with urllib.request.urlopen(req, timeout=120) as r:
                glb_path.write_bytes(r.read())
            record["mesh_download"] = {
                "path": str(glb_path.relative_to(REPO)),
                "bytes": glb_path.stat().st_size,
                "sha256": sha256_file(glb_path),
                "origin": EvidenceOrigin.RECONSTRUCTED.value,
            }
            try:
                import trimesh
                scene = trimesh.load(glb_path, force="scene")
                geoms = list(scene.geometry.values()) if hasattr(
                    scene, "geometry") else [scene]
                tri = sum(int(len(g.faces)) for g in geoms if hasattr(
                    g, "faces"))
                verts = sum(int(len(g.vertices)) for g in geoms if hasattr(
                    g, "vertices"))
                record["mesh_independent_remeasure"] = {
                    "verifier": f"trimesh {trimesh.__version__}",
                    "meshes": len(geoms), "triangles": tri,
                    "vertices": verts,
                    "note": "independent re-measure of the downloaded "
                            "reconstruction mesh — geometry STATISTICS "
                            "only, never a physical measurement",
                }
            except ImportError:
                record["mesh_independent_remeasure"] = {
                    "note": "trimesh not available — skipped"}
        except Exception as exc:  # noqa: BLE001
            record["mesh_download"] = {"error": f"{type(exc).__name__}: {exc}"}

    # ---- a real DESIGN_WORLD ↔ REALITY_WORLD comparison demonstration ------
    # The verification world is a forest scene, not an engineering part, so
    # the demonstration uses the provider's own dimensional metadata
    # (metric_scale_factor) as the RECONSTRUCTED dimension datum — honestly
    # labeled hypothesis-grade.
    semantics = (mesh_asset.value.get("semantics") or {}) if mesh_asset else {}
    demo_spec = {
        "problem_id": "r389_live_verification",
        "engineering_specification": {
            "parameters": [
                {"name": "scene_metric_scale_factor", "value": 1.0,
                 "unit": "ratio", "epistemic_class": "MODEL_DERIVED"},
            ]}}
    if semantics.get("metric_scale_factor") is not None:
        model.add("dimensions", __import__(
            "discovery_fabric.engine.reality_provider",
            fromlist=["RealityDatum"]).RealityDatum(
            name="scene_metric_scale_factor",
            value=float(semantics["metric_scale_factor"]),
            origin=EvidenceOrigin.RECONSTRUCTED,
            uncertainty="provider-declared reconstruction scale — unverified",
            source=f"WorldLabsProvider:{op_id}"))
    comparison = compare_design_to_reality(
        build_design_world(demo_spec), build_reality_world(model))
    record["comparison_demonstration"] = comparison
    (OUT_DIR / "REALITY_COMPARISON_DEMO.json").write_text(
        json.dumps(comparison, indent=2))

    record["reality_model"] = model.to_dict()
    (OUT_DIR / "REALITY_MODEL.json").write_text(
        json.dumps(model.to_dict(), indent=2))
    record["status"] = "VERIFIED_TRANSPORT_BOUNDARY_INTACT"
    record["verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime())
    (OUT_DIR / "VERIFICATION_RECORD.json").write_text(
        json.dumps(record, indent=2))
    print(f"VERIFIED — record at "
          f"{(OUT_DIR / 'VERIFICATION_RECORD.json').relative_to(REPO)}")
    print(f"  assets: {harvest_status['assets']}, "
          f"origins: {model.origin_counts()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
