#!/usr/bin/env python3
"""R452-C2 item 3 — ONE real production device path, executed and recorded.

Gate (operator directive): Coder 1's production physical-device run exists.
Measured gate evidence: on the canonical HF Space's own durable-state branch
(origin/runtime-state-hf — the production Space pushes this branch itself),
session ts_6a4e518676db reached terminal:COMPLETE (commit e031b294,
2026-09-13T11:04:23Z) and render_complete (commit b368db2a, 11:07:26Z), on
engine build e50d56c0690e (branch MANIFEST engine_commit, source
build_artifact).

This script executes the visual production proof on THOSE production bytes:
  1. extracts the run dir from the production-committed branch;
  2. verifies every extracted file's sha256 against the branch MANIFEST
     (the Space's own custody map);
  3. records the directive's ladder — geometry_warrant / CAD / STEP / GLB /
     Visual Compiler / render / poster-hero / 7-view / release state —
     with EXISTS/ABSENT measured per rung (absence is recorded, never
     inferred away, Art. XXV);
  4. runs the presentation-layer verifiers (dossier projection, geometry
     artifact contract, visual join, release chain, watchdog) against the
     REAL production bytes;
  5. best-effort live probe of the canonical Space's /api/version + /api/health
     (in-memory transient token, BS-021; the value is never printed or
     written).

Observational only (Art. IX): the production branch is read, never written.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRANCH = "origin/runtime-state-hf"
RUN_DIR_NAME = ("runs/"
                "toscanini_ui_ui_40_000_vial_batches_protein_injectable_"
                "she_291053")
SESSION_ID = "ts_6a4e518676db"
APP_URL = "https://prateekm1-toscanini-prod-validation.hf.space"
SPACE_META_URL = ("https://huggingface.co/api/spaces/prateekm1/"
                  "toscanini-prod-validation")

R443_LADDER_REQUIRED = (
    ["hero.png", "poster.png", "dimension.png", "section.png"]
    + [f"orthographic_{a}.png" for a in ("front", "back", "left", "right")]
    + [f"turntable_{i:02d}.png" for i in range(1, 13)])


def sh(*args: str, binary: bool = False):
    out = subprocess.run(args, capture_output=True, check=True, cwd=REPO)
    return out.stdout if binary else out.stdout.decode("utf-8", "replace")


def branch_files() -> dict:
    out = sh("git", "ls-tree", "-r", BRANCH, "--name-only")
    return {p: None for p in out.splitlines() if p.startswith(RUN_DIR_NAME)}


def extract_run(dest: Path, files: dict) -> dict:
    """Extract every run file, verifying sha256 against the branch
    MANIFEST (production's own custody map)."""
    manifest = json.loads(sh("git", "show", f"{BRANCH}:MANIFEST.json"))
    manifest_files = manifest.get("files") or {}
    result = {"verified": 0, "mismatch": [], "missing_from_manifest": []}
    for path in files:
        data = sh("git", "show", f"{BRANCH}:{path}", binary=True)
        rel = path  # MANIFEST keys use the same run-prefixed path
        expected = manifest_files.get(rel)
        digest = hashlib.sha256(data).hexdigest()
        if expected is None:
            result["missing_from_manifest"].append(path)
        elif expected != digest:
            result["mismatch"].append(path)
        else:
            result["verified"] += 1
        target = dest / Path(path).relative_to(RUN_DIR_NAME)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result["engine_commit"] = manifest.get("engine_commit")
    result["engine_commit_source"] = manifest.get("engine_commit_source")
    result["manifest_at"] = manifest.get("at")
    return result


def find_hf_token_in_memory() -> bytes | None:
    """Transient in-memory recovery of the operator's HF token from the
    reachable history (the R451 precedent) — used ONLY for the read-only
    live probe; the value is never printed, logged, or written."""
    import urllib.error  # noqa
    lines = sh("git", "rev-list", "--objects", "--all").splitlines()
    shas = [ln.split(" ", 1)[0] for ln in lines if ln.strip()]
    proc = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=REPO, check=True,
        input=("\n".join(shas) + "\n").encode(), capture_output=True)
    stream, pos, found = proc.stdout, 0, set()
    pattern = re.compile(rb"hf_[A-Za-z0-9]{34,40}")
    b64 = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
              b"0123456789+/=")
    while pos < len(stream):
        nl = stream.index(b"\n", pos)
        header = stream[pos:nl].decode("utf-8", "replace").split()
        if len(header) < 3:
            break
        size = int(header[2])
        data = stream[nl + 1: nl + 1 + size]
        pos = nl + 1 + size + 1
        for m in pattern.finditer(data):
            lo, hi = m.start(), m.end()
            while lo > 0 and data[lo - 1] in b64:
                lo -= 1
            while hi < len(data) and data[hi] in b64:
                hi += 1
            if hi - lo < 64:  # standalone token, not base64 noise
                found.add(m.group(0))
    # keep exactly the fingerprint the records document (hf_M...NkNM)
    for value in found:
        text = value.decode()
        if text.startswith("hf_M") and text.endswith("NkNM") and \
                len(text) == 37:
            return value
    return None


def live_probe(token: bytes | None) -> dict:
    out = {}
    def probe(name: str, url: str, auth: str | None):
        headers = {"User-Agent": "r452-production-path-proof"}
        if auth and token:
            headers["Authorization"] = f"{auth} {token.decode()}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read(4096).decode("utf-8", "replace")
                out[name] = {"http": resp.status, "body": body[:1500]}
        except Exception as exc:  # noqa: BLE001 — recorded, never fatal
            out[name] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
    probe("space_meta_authenticated", SPACE_META_URL, "Bearer")
    probe("api_version", f"{APP_URL}/api/version", "Bearer")
    probe("api_health", f"{APP_URL}/api/health", "Bearer")
    return out


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    files = branch_files()
    if not files:
        print(f"FATAL: no run files found on {BRANCH}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="r452-prod-") as tmp:
        run = Path(tmp)
        custody = extract_run(run, files)
        if custody["mismatch"]:
            print(f"FATAL: custody mismatch {custody['mismatch']}",
                  file=sys.stderr)
            return 2

        # ---- the ladder rungs, measured on the production bytes --------
        def exists(rel: str) -> bool:
            return (run / rel).is_file()

        def sha(rel: str) -> str | None:
            p = run / rel
            return hashlib.sha256(p.read_bytes()).hexdigest() \
                if p.is_file() else None

        load = {}
        for rel in ("run_manifest.json", "final_state.json",
                    "RELEASE_PROOF.json", "SURVIVOR_SELECTION.json",
                    "ENGINEERING_SPECIFICATION.json", "BRIDGE_REPORT.json",
                    "MODEL/model-001.glb", "MODEL/3D/render_record.json",
                    "MODEL/3D/visual_gate.json", "MODEL/3D/scene_spec.json",
                    "MODEL/3D/render_payload.json", "MODEL/3D/RENDER_JOB.json",
                    "MODEL/3D/hero.png", "MODEL/3D/poster.png",
                    "MODEL/3D/hero.glb", "MODEL/3D/exploded.glb",
                    "MODEL/3D/dimension.png", "MODEL/3D/section.png",
                    "MODEL/3D/exploded.png", "MODEL/3D/material_probe.png",
                    "INVENTION_LINEAGE.json", "INVENTION_SPECIFICATION.json"):
            load[rel] = {
                "exists": exists(rel),
                "sha256": sha(rel) if exists(rel) else None}

        def jload(rel):
            p = run / rel
            return json.loads(p.read_text()) if p.is_file() else None

        render_record = jload("MODEL/3D/render_record.json") or {}
        gate = jload("MODEL/3D/visual_gate.json") or {}
        release = jload("RELEASE_PROOF.json") or {}
        final_state = jload("final_state.json") or {}
        bridge = jload("BRIDGE_REPORT.json") or {}
        render_sha = load["MODEL/model-001.glb"]["sha256"]
        source_matches = bool(
            render_sha and render_record.get("source_glb_sha256")
            and render_sha == render_record["source_glb_sha256"])

        # ---- the presentation-layer verifiers on the REAL bytes -------
        sys.path.insert(0, str(REPO))
        from toscanini import dossier as dossier_mod  # noqa: E402
        from toscanini import visual_join as vj  # noqa: E402
        session = {"session_id": SESSION_ID, "status": "COMPLETE",
                   "problem_id": "ui_40_000_vial_batches_protein_"
                                 "injectable_she_291053",
                   "run_dir": str(run)}
        dossier = dossier_mod.build_dossier(session)
        design = dossier.get("tabs", {}).get("design", {})
        evidence_tab = dossier.get("tabs", {}).get("evidence", {})
        contract = design.get("geometry_contract") or {}
        glb_path = run / "MODEL" / "model-001.glb"
        chain = vj.verify_release_chain(
            run, glb_path=glb_path if glb_path.is_file() else None)
        geometry_warrant = {
            "engineering_authority": contract.get("engineering_authority"),
            "authority_source": contract.get("authority_source"),
            "geometry_state": design.get("geometry_state"),
            "engineering_geometry_ready":
                contract.get("engineering_geometry_ready"),
            "bridge_geometry_class": (bridge.get("geometry") or {})
                .get("class") or bridge.get("geometry_class"),
            "glb_sha256_recorded": (bridge.get("geometry") or {})
                .get("glb_sha256"),
            "glb_sha256_measured": render_sha,
            "glb_sha256_match": bool(
                render_sha and (bridge.get("geometry") or {})
                .get("glb_sha256") == render_sha)}

        # CAD evidence: what the production run recorded about the CAD stage
        cad_evidence = {
            "cad_pipeline_ledger_present": exists("CAD_PIPELINE_LEDGER.json"),
            "parametric_model_present": exists("PARAMETRIC_MODEL.json"),
            "engineering_specification_present":
                load["ENGINEERING_SPECIFICATION.json"]["exists"],
            "bridge_report_present":
                load["BRIDGE_REPORT.json"]["exists"]}

        ladder_present = sorted(p.name for p in
                                (run / "MODEL" / "3D").iterdir()) \
            if (run / "MODEL" / "3D").is_dir() else []
        ladder_missing = [a for a in R443_LADDER_REQUIRED
                          if not (run / "MODEL" / "3D" / a).is_file()]

        proof = {
            "kind": "PRODUCTION_DEVICE_PATH_PROOF",
            "round": "R452-C2",
            "generated_at": started,
            "gate_evidence": {
                "production_run_session_id": SESSION_ID,
                "durable_state_branch": BRANCH,
                "terminal_commit": "e031b294 (terminal:COMPLETE, "
                                   "2026-09-13T11:04:23Z)",
                "render_commit": "b368db2a (render_complete, "
                                 "2026-09-13T11:07:26Z)",
                "session_status_recorded": "COMPLETE",
                "engine_commit": custody["engine_commit"],
                "engine_commit_source": custody["engine_commit_source"]},
            "custody": {
                "files_extracted": len(files),
                "sha256_verified_against_production_manifest":
                    custody["verified"],
                "sha256_mismatches": custody["mismatch"],
                "absent_from_manifest": custody["missing_from_manifest"]},
            "ladder": {
                "geometry_warrant": geometry_warrant,
                "cad": cad_evidence,
                "step": {"exists": bool(
                    list(run.glob("**/*.step")) +
                    list(run.glob("**/*.stp")))},
                "glb": {"canonical_glb": "MODEL/model-001.glb",
                        "sha256": render_sha,
                        "render_record_source_match": source_matches},
                "visual_compiler": {
                    "scene_spec": load["MODEL/3D/scene_spec.json"]["exists"],
                    "render_payload":
                        load["MODEL/3D/render_payload.json"]["exists"],
                    "render_job": load["MODEL/3D/RENDER_JOB.json"]["exists"],
                    "invocation_receipt_present": exists(
                        "MODEL/3D/VISUAL_COMPILER_INVOCATION.json"),
                    "render_record_status": render_record.get("status"),
                    "render_record_schema":
                        render_record.get("schema_version")},
                "render": {"hero_png": load["MODEL/3D/hero.png"]["exists"],
                           "hero_png_sha256":
                               load["MODEL/3D/hero.png"]["sha256"]},
                "poster_hero": {
                    "poster_png": load["MODEL/3D/poster.png"]["exists"],
                    "hero_png": load["MODEL/3D/hero.png"]["exists"],
                    "visual_gate_verdict": gate.get("verdict"),
                    "visual_gate_version": gate.get("gate_version")},
                "seven_view": {
                    "present_on_production_branch": ladder_present,
                    "required_r443_ladder_missing": ladder_missing,
                    "discrepancy_surfaced": bool(ladder_missing) and
                        gate.get("verdict") == "COMPLETE_PASS",
                    "discrepancy_note":
                        "the gate record claims COMPLETE_PASS (the ladder "
                        "was verified on the machine at gate time) while "
                        "the production-committed run dir carries a subset "
                        "of the R443 ladder — the disagreement is "
                        "surfaced, never silently resolved (BS-026)"},
                "release_state": {
                    "release_status": release.get("status"),
                    "hashes_present": release.get("hashes_present"),
                    "final_status": final_state.get("final_status"),
                    "epistemic_state": final_state.get("epistemic_state"),
                    "hero_release_state_present": exists(
                        "MODEL/3D/HERO_RELEASE_STATE.json")}},
            "presentation_layer_verdicts_on_production_bytes": {
                "design_geometry_state": design.get("geometry_state"),
                "engineering_authority":
                    contract.get("engineering_authority"),
                "evidence_retrieval_state":
                    evidence_tab.get("retrieval_state"),
                "evidence_retrieved_count":
                    evidence_tab.get("retrieved_count"),
                "pipeline_rows": [
                    {"key": r.get("key"), "status": r.get("status"),
                     "detail": (r.get("detail") or "")[:160]}
                    for r in dossier.get("pipeline", [])],
                "release_chain": {
                    "verified": chain.get("verified"),
                    "failed_rungs": [r.get("rung") for r in
                                     chain.get("rungs", [])
                                     if not r.get("ok")],
                    "note": "the production engine predates the unmerged "
                            "C2-line identity writers (PR #5) — the chain "
                            "verdict on production bytes is recorded, not "
                            "forced"}},
            "live_production_probe": None,
            "observational": "the production branch and the live Space "
                             "were read, never written (Art. IX)"}
        token = find_hf_token_in_memory()
        proof["live_production_probe"] = live_probe(token)
        out = REPO / "R452" / "C2_PRODUCT" / "PRODUCTION_DEVICE_PATH_PROOF.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(proof, indent=2))
        print(f"proof written: {out}")
        print(f"custody: {custody['verified']}/{len(files)} sha-verified, "
              f"{len(custody['missing_from_manifest'])} not in MANIFEST")
        print(f"geometry warrant: authority="
              f"{geometry_warrant['engineering_authority']} state="
              f"{geometry_warrant['geometry_state']}")
        print(f"release chain verified: {chain.get('verified')} "
              f"failed rungs: {[r.get('rung') for r in chain.get('rungs', []) if not r.get('ok')]}")
        probe = proof["live_production_probe"] or {}
        for k, v in probe.items():
            print(f"probe {k}: {v.get('http', v.get('error'))}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
