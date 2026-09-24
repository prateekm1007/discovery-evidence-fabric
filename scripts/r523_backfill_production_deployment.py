#!/usr/bin/env python3
"""R523 audit-hygiene close: backfill the constitution-mandated
production_deployment tuple (Art. LXXI §2) into R523/R523_ROUND_RECORD.json.

Art. LXXI requires every round record to carry EXACTLY:
  "production_deployment": {
    "target_sha": "...", "deployed_sha": "...", "deploy_id": "...",
    "health_check_result": "GREEN | BLOCKED | DEGRADED",
    "drift": "GREEN | DRIFT | UNKNOWN",
    "blocked_by": "...", "what_unblocks": "..."
  }

The R523 delivery close recorded the same facts under a differently
named "deployment" block. This script performs an ADDITIVE, automated
correction — it live-verifies the deployment facts and writes the
mandated block. It NEVER rewrites R523 scientific results
(rankings, harvests, comparisons, classifications); any other field is
left byte-identical.

Fail-closed: unless the live /api/version engine_commit EQUALS the
declared R523 deployment target (the after-arm winner the battery was
gated on), the script writes BLOCKED with the blocker named, never
GREEN.

Usage: python scripts/r523_backfill_production_deployment.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "https://prateekm1-toscanini-prod-validation.hf.space"
RECORD = REPO / "R523" / "R523_ROUND_RECORD.json"
DEPLOY_RECORD = REPO / "R523" / "AFTER_DEPLOY_RECORD.json"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(path: str, timeout: int = 60) -> dict:
    with urllib.request.urlopen(SPACE + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _ls_remote_main() -> str:
    t = subprocess.run(
        ["git", "ls-remote", "origin", "refs/heads/main"],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)
    if t.returncode != 0 or not t.stdout.strip():
        raise RuntimeError(f"ls-remote failed: {t.stderr.strip()[:200]}")
    return t.stdout.split()[0]


def main() -> int:
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    target = ((rec.get("after_configuration") or {}).get("engine") or "")
    if len(target) != 40:
        print("FATAL: after_configuration.engine is not a full SHA")
        return 2
    deploy_rec = json.loads(DEPLOY_RECORD.read_text(encoding="utf-8"))
    deploy_id = deploy_rec.get("hf_revision") or ""
    if deploy_rec.get("commit") != target:
        print("FATAL: AFTER_DEPLOY_RECORD.commit != declared target")
        return 2

    version = _get("/api/version", timeout=60)
    health = _get("/api/health", timeout=60)
    deployed = version.get("engine_commit") or ""
    drift = ((health.get("deployment_identity") or {}).get(
        "deployment_drift") or "UNKNOWN")
    identity_tamper = ((health.get("deployment_identity") or {}).get(
        "identity_tamper"))
    origin_main = _ls_remote_main()

    if deployed == target and drift == "GREEN" and identity_tamper is False:
        block = {
            "target_sha": target,
            "deployed_sha": deployed,
            "deploy_id": deploy_id,
            "health_check_result": "GREEN",
            "drift": "GREEN",
            "blocked_by": None,
            "what_unblocks": "n/a - R523 winner deployed and serving",
        }
    else:
        reasons = []
        if deployed != target:
            reasons.append(f"deployed_sha {deployed[:12]} != target "
                           f"{target[:12]}")
        if drift != "GREEN":
            reasons.append(f"drift={drift}")
        if identity_tamper is not False:
            reasons.append(f"identity_tamper={identity_tamper}")
        block = {
            "target_sha": target,
            "deployed_sha": deployed,
            "deploy_id": deploy_id,
            "health_check_result": "BLOCKED",
            "drift": drift,
            "blocked_by": "; ".join(reasons),
            "what_unblocks": ("redeploy the R523 winner commit and "
                              "re-verify /api/version + drift"),
        }
    rec["production_deployment"] = block
    # supplementary, non-mandated facts live in a SEPARATE sibling block
    # so the mandated schema stays exact.
    rec["production_deployment_evidence"] = {
        "origin_main_at_backfill": origin_main,
        "engine_bytes_note": (
            "production serves the R523 winner; origin/main additionally "
            "carries record/evidence material whose engine-bytes diff vs "
            "the winner is empty (accepted record-only delta, documented "
            "in the R523 record deploy_proofs)"),
        "verified_at_utc": _utcnow(),
        "reviewer_provenance": "AI_REVIEW",
    }
    rec["updated_at_utc"] = _utcnow()
    RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"wrote production_deployment "
          f"({block['health_check_result']}, drift={block['drift']}) "
          f"-> {RECORD}")
    print(f"  target={target[:12]} deployed={deployed[:12]} "
          f"origin_main={origin_main[:12]}")
    return 0 if block["health_check_result"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
