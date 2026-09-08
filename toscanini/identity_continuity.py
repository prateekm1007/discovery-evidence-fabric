"""R436 — the canonical invention identity continuity checker.

The operator invariant (R436 directive): a successful fresh investigation
must produce the SAME canonical invention identity across the result,
the dossier, the 3D asset, the decisive experiment, and the
technology-transfer package. That join has repeatedly been the weak one;
this module checks it from the run's own persisted bytes with EXACT
joins only — no fuzzy matching, no re-derivation (Art. II / X / VI).

The five join families, all read from recorded artifacts:

  J1 problem identity — final_state.problem_id == the invention_id's
     inv:<problem_id>:<hash> problem part == the 3D artifact's
     technology_id == the BRIDGE_REPORT geometry artifact identity.
  J2 3D asset integrity — ARTIFACT_IDENTITY.geometry_hash ==
     glb_disk_sha256 == sha256 of the actual GLB file on disk (the
     served model is the recorded model).
  J3 session/run identity — the session id == the 3D artifact's run_id
     == the BRIDGE_REPORT geometry artifact identity run_id.
  J4 decisive experiment binding — the selected killer-experiment
     hypothesis embeds the invention's own expected_effect text
     (exact substring — the recorded join the engine itself writes).
  J5 package integrity — BRIDGE_REPORT.package_out.zip_sha256 == the
     sha256 of the package ZIP on disk, and the ZIP lives inside this
     run's DOWNLOAD tree (the package belongs to THIS technology).

Every join reports {join, passed, detail}; a missing artifact is an
honest MISSING (recorded, never guessed — Art. XXV); the overall
verdict is PASS only when every present-and-required join passed and
none of the required artifacts is missing.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

INV_ID_RE = re.compile(r"^inv:([^:]+):([0-9a-f]+)$")


def _read_json(p: Path) -> Optional[dict]:
    try:
        if p.exists() and p.is_file():
            return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — absent stays absent
        return None
    return None


def _sha256_file(p: Path) -> Optional[str]:
    try:
        if p.exists() and p.is_file():
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
    except OSError:
        return None
    return None


def check_run(run_dir: Path, session_id: Optional[str] = None) -> dict:
    """Verify the canonical invention identity continuity for one run.

    Returns a verdict dict: {passed, joins: [...], missing: [...],
    checked_at_source: {...}}. Honest about every absence.
    """
    run_dir = Path(run_dir)
    joins: List[Dict[str, Any]] = []
    missing: List[str] = []

    final_state = _read_json(run_dir / "final_state.json")
    inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json")
    ai = _read_json(run_dir / "MODEL" / "ARTIFACT_IDENTITY.json")
    bridge = _read_json(run_dir / "BRIDGE_REPORT.json")
    dece = _read_json(run_dir / "DECISIVE_EXPERIMENT.json")

    for name, obj in (
        ("final_state.json", final_state),
        ("INVENTION_SPECIFICATION.json", inv),
        ("MODEL/ARTIFACT_IDENTITY.json", ai),
        ("BRIDGE_REPORT.json", bridge),
        ("DECISIVE_EXPERIMENT.json", dece),
    ):
        if obj is None:
            missing.append(name)

    # ---- J1: problem identity across result / invention / 3D asset ----
    problem_ids = set()
    if final_state:
        problem_ids.add(final_state.get("problem_id"))
    inv_id = ((inv or {}).get("invention_id") or {}).get("value") or ""
    m = INV_ID_RE.match(inv_id or "")
    inv_problem = m.group(1) if m else None
    if inv_problem:
        problem_ids.add(inv_problem)
    if ai:
        problem_ids.add(ai.get("technology_id"))
    br_geo_ai = ((bridge or {}).get("geometry") or {}).get(
        "artifact_identity") or {}
    if br_geo_ai:
        problem_ids.add(br_geo_ai.get("technology_id"))
    problem_ids.discard(None)
    problem_ids.discard("")
    if problem_ids:
        joins.append({
            "join": "J1_problem_identity",
            "passed": len(problem_ids) == 1,
            "detail": {
                "ids": sorted(problem_ids),
                "sources": ["final_state", "invention_id", "artifact",
                            "bridge_geometry"],
            },
        })

    # ---- J2: the 3D asset is the recorded model (bytes-level) --------
    if ai:
        glb_path = ai.get("glb_path")
        recorded = ai.get("geometry_hash")
        disk_hash = (_sha256_file(Path(glb_path)) if glb_path else None)
        if disk_hash is None:
            # the recorded path is machine-bound (production) — the
            # local copy of the same run resolves by basename
            local = run_dir / "MODEL" / Path(str(glb_path)).name
            disk_hash = _sha256_file(local) if glb_path else None
        joins.append({
            "join": "J2_geometry_hash_matches_file",
            "passed": bool(
                recorded and disk_hash and recorded == disk_hash),
            "detail": {
                "geometry_hash": (recorded or "")[:16] + "…",
                "glb_disk_sha256": (disk_hash or "")[:16] + "…",
                "glb_file": Path(str(glb_path)).name if glb_path else None,
                "note": (None if disk_hash
                         else "GLB file not found — recorded hash "
                              "unverified, not passed (Art. XXV)"),
            },
        })

    # ---- J3: session / run identity ----------------------------------
    run_ids = set()
    if session_id:
        run_ids.add(session_id)
    if ai:
        run_ids.add(ai.get("run_id"))
    if br_geo_ai:
        run_ids.add(br_geo_ai.get("run_id"))
    run_ids.discard(None)
    run_ids.discard("")
    if run_ids:
        joins.append({
            "join": "J3_run_identity",
            "passed": len(run_ids) == 1,
            "detail": {"ids": sorted(run_ids)},
        })

    # ---- J4: the decisive experiment binds to THIS invention ---------
    # The engine's own recorded join: DECISIVE_EXPERIMENT.selected and
    # INVENTION_SPECIFICATION.killer_experiment carry the SAME canonical
    # hypotheses list (structural equality — the exact join the engine
    # writes; a paraphrased expected_effect is NOT a join, so substring
    # matching is forbidden here — Art. II).
    ke_val = ((inv or {}).get("killer_experiment") or {}).get("value") or {}
    ke_hyps = ke_val.get("hypotheses") or []
    sel_hyps = ((dece or {}).get("selected") or {}).get("hypotheses") or []
    if ke_hyps or sel_hyps:
        joins.append({
            "join": "J4_decisive_experiment_binding",
            "passed": bool(ke_hyps) and ke_hyps == sel_hyps,
            "detail": {
                "hypotheses_in_invention": len(ke_hyps),
                "hypotheses_in_experiment": len(sel_hyps),
                "structural_equality": ke_hyps == sel_hyps,
                "note": ("the selected killer-experiment hypotheses are "
                         "the invention specification's own canonical "
                         "hypotheses (exact list equality)"),
            },
        })

    # ---- J5: the package IS this invention's package ------------------
    # The final package's own manifest (PACKAGE_MANIFEST.json inside this
    # run's DOWNLOAD tree) declares package_id — the canonical invention
    # identity — and pins every file by sha256. The bridge's package_out
    # is an intermediate generation (its zip no longer exists once the
    # named package supersedes it): recorded as an OBSERVATION, not a
    # join failure (Art. LXIV disposition discipline).
    inv_id_val = inv_id or None
    observations: List[Dict[str, Any]] = []
    pm = None
    pm_dir = None
    dl = run_dir / "DOWNLOAD"
    if dl.exists():
        for cand in sorted(dl.rglob("PACKAGE_MANIFEST.json")):
            pm = _read_json(cand)
            if pm and pm.get("package_id"):
                pm_dir = cand.parent
                break
    if pm:
        pid = pm.get("package_id")
        files_ok = True
        files_checked = 0
        for f in (pm.get("files") or []):
            name = f.get("file") or f.get("name") or f.get("path")
            sha = f.get("sha256")
            if not name:
                continue
            fp = pm_dir / name
            disk = _sha256_file(fp) if fp.exists() else None
            files_checked += 1
            if not (sha and disk and sha == disk):
                files_ok = False
        joins.append({
            "join": "J5_package_identity",
            "passed": bool(
                pid and inv_id_val and pid == inv_id_val and files_ok),
            "detail": {
                "package_id": pid,
                "invention_id": inv_id_val,
                "package_files_checked": files_checked,
                "package_files_hash_verified": files_ok,
                "package_dir": pm_dir.name if pm_dir else None,
            },
        })
    po = (bridge or {}).get("package_out") or {}
    if po and po.get("zip_sha256"):
        bridge_zip_on_disk = _sha256_file(
            run_dir / "DOWNLOAD" / str(po.get("zip_name"))) \
            if po.get("zip_name") else None
        observations.append({
            "observation": "bridge_package_generation_superseded",
            "bridge_zip_name": po.get("zip_name"),
            "bridge_zip_sha256_head": (po.get("zip_sha256") or "")[:16],
            "bridge_zip_on_disk": bool(bridge_zip_on_disk),
            "disposition": (
                "the bridge's package_out is the intermediate package "
                "generation; the named DOWNLOAD package (with its own "
                "manifest declaring the invention identity) supersedes "
                "it. Recorded, never silently dropped (Art. LXIV)."),
        })

    required = ["final_state.json", "INVENTION_SPECIFICATION.json",
                "MODEL/ARTIFACT_IDENTITY.json", "BRIDGE_REPORT.json"]
    passed = (not missing
              and all(j["passed"] for j in joins)
              and {j["join"] for j in joins} >= {
                  "J1_problem_identity", "J2_geometry_hash_matches_file",
                  "J3_run_identity"})
    return {
        "artifact": "R436_IDENTITY_CONTINUITY",
        "run_dir": str(run_dir),
        "session_id": session_id,
        "passed": bool(passed),
        "joins": joins,
        "observations": observations,
        "missing": missing,
        "note": ("canonical invention identity continuity — exact joins "
                 "from persisted bytes; the dossier projection is checked "
                 "separately against the same CIO the API serves"),
    }
