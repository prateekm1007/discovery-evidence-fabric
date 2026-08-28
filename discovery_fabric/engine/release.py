"""discovery_fabric/engine/release.py — CEO Directive 2: the canonical
DISCOVERY_RELEASE.json.

Every completed engine run emits ONE release record binding the discovery
side (run, candidate, evidence) to the transfer side (invention spec,
engineering spec, dossier manifest, buyer package). This is the binding
between discovery and the transfer artifact:

    run_id, candidate_id, invention_id, problem_id,
    evidence_hash, candidate_hash,
    invention_spec_hash, engineering_spec_hash,
    dossier_manifest_hash, buyer_package_hash,
    status

All hashes are real SHA-256 over the actual artifacts (Art. VI: never
manufacture provenance). A run that did not reach a released package still
gets an honest release record with status != RELEASED and the missing
fields explicitly null (Art. XXV: unknown stays unknown) — the release is
the single place a downstream system looks to discover what exists.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .candidate import sha256_obj, utc_now

# Explicit status vocabulary (Art. X: one authority; no free-text states)
ST_RELEASED = "RELEASED"
ST_HELD_FOR_HUMAN_REVIEW = "HELD_FOR_HUMAN_REVIEW"
ST_NOT_A_SURVIVOR = "NOT_A_SURVIVOR"
ST_PIPELINE_FAILED = "PIPELINE_FAILED"
ST_PACKAGE_INCOMPLETE = "PACKAGE_INCOMPLETE"
ST_DISCOVERY_INCOMPLETE = "DISCOVERY_INCOMPLETE"
ST_DISABLED_BY_CONFIG = "DISABLED_BY_CONFIG"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_discovery_release(
        run_dir: Path, run_id: str, problem_id: str,
        env: Any = None,
        spec: Optional[Dict[str, Any]] = None,
        eng: Optional[Dict[str, Any]] = None,
        package_report: Optional[Dict[str, Any]] = None,
        failure_reason: Optional[str] = None,
        disabled_by_config: bool = False) -> Dict[str, Any]:
    """Compute the release record from artifacts ON DISK (not from memory)
    wherever the artifact exists as a file — hashes must be reproducible by
    a third party from the run directory alone (Art. XXVI)."""
    run_dir = Path(run_dir)
    evidence = (getattr(env, "evidence", None) or []) if env else []
    evidence_hash = sha256_obj([
        {"id": e.get("id"), "content_hash": e.get("content_hash"),
         "frozen": bool(e.get("frozen", e.get("custody")))}
        for e in evidence]) if evidence else None
    candidate_hash = env.envelope_hash() if env is not None else None
    candidate_id = (getattr(env, "candidate_id", "") or
                    ((env.mechanism_map or {}).get("raw_candidate", {})
                     .get("candidate_id") if env else "") or
                    (f"cand:{candidate_hash[:12]}" if candidate_hash else None))
    invention_id = ((spec or {}).get("invention_id") or {}).get("value")
    spec_hash = (spec or {}).get("_spec_hash")
    eng_hash = sha256_obj(
        {k: v for k, v in (eng or {}).items()
         if not k.startswith("_")}) if eng else None

    dossier_manifest_hash = None
    buyer_package_hash = None
    package_folder = None
    package_zip = None
    if package_report and package_report.get("complete"):
        package_folder = Path(package_report["folder"]).resolve()
        pm = package_folder / "PACKAGE_MANIFEST.json"
        zp = Path(package_report["zip"]).resolve() \
            if package_report.get("zip") else None
        if pm.exists():
            dossier_manifest_hash = sha256_file(pm)
        if zp and zp.exists():
            buyer_package_hash = sha256_file(zp)
            package_zip = str(zp)

    if disabled_by_config:
        status = ST_DISABLED_BY_CONFIG
    elif spec is None and eng is None:
        status = ST_DISCOVERY_INCOMPLETE
    elif spec is not None and not ((spec.get("_survivor_gate") or {})
                                   .get("survivor")):
        # CEO E16-F: an EXPLORATION-GRID candidate advances through the
        # engineering gauntlet after the discovery loop rejected the naive
        # candidate. The package exists and passed the E16-H gate (capped
        # at HELD — discovery-level verification was not re-run for the
        # grid candidate). Only a NON-exploration non-survivor is
        # NOT_A_SURVIVOR.
        if spec.get("_exploration_candidate"):
            status = ST_HELD_FOR_HUMAN_REVIEW
        else:
            status = ST_NOT_A_SURVIVOR
    elif package_report is None or failure_reason:
        status = ST_PIPELINE_FAILED
    elif not package_report.get("complete") or not buyer_package_hash:
        status = ST_PACKAGE_INCOMPLETE
    else:
        # CEO E16-H: the terminal status comes from the persisted holdout
        # release gate (read from DISK, Art. XXVI). RELEASED requires all
        # six gates PASS; a CONDITIONAL gate is HELD_FOR_HUMAN_REVIEW and
        # is NEVER counted as an automatic PASS.
        gate_path = run_dir / "RELEASE_GATE_EVALUATION.json"
        if gate_path.exists():
            try:
                gate = json.loads(gate_path.read_text())
                status = (ST_RELEASED
                          if gate.get("decision") == "RELEASED"
                          else ST_HELD_FOR_HUMAN_REVIEW)
            except Exception:  # noqa: BLE001 — corrupt gate = held
                status = ST_HELD_FOR_HUMAN_REVIEW
        else:
            status = ST_HELD_FOR_HUMAN_REVIEW

    return {
        "release_id": f"rel:{run_id}:{(invention_id or 'nosurvivor')}",
        "run_id": run_id,
        "candidate_id": candidate_id,
        "invention_id": invention_id,
        "problem_id": problem_id,
        "evidence_hash": evidence_hash,
        "candidate_hash": candidate_hash,
        "invention_spec_hash": spec_hash,
        "engineering_spec_hash": eng_hash,
        "dossier_manifest_hash": dossier_manifest_hash,
        "buyer_package_hash": buyer_package_hash,
        "package_folder": str(package_folder) if package_folder else None,
        "package_zip": package_zip,
        "status": status,
        "failure_reason": failure_reason,
        "loop_verification_state": "NONE",
        "real_loop_verified": False,
        "code_commit": _git_head(),
        "generated_at": utc_now(),
    }


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def write_discovery_release(run_dir: Path, release: Dict[str, Any]) -> Path:
    p = Path(run_dir) / "DISCOVERY_RELEASE.json"
    p.write_text(json.dumps(release, indent=2, ensure_ascii=False))
    return p
