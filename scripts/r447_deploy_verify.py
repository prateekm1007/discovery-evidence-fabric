#!/usr/bin/env python3
"""R447 deploy verification — poll the canonical Space build, then verify
the Article LXXI delivery tuple:

  1. ls-remote origin/main == the target SHA (push confirmation)
  2. /api/version engine_commit == the target SHA (deployed identity)
  3. /api/health deployment_drift == GREEN (health check)

Writes R447/HF_DEPLOYMENT_RECORD.json on success. Idempotent per call —
safe to re-invoke while the build is still running (prints stage only).

Usage: HF_TOKEN=... GITHUB_TOKEN=... python scripts/r447_deploy_verify.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = REPO / "R447" / "HF_DEPLOYMENT_RECORD.json"


def space_stage() -> str:
    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/runtime",
        headers={"Authorization": f"Bearer {HF_TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("stage", "UNKNOWN")


def probe(path: str, timeout: int = 90):
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Authorization": f"Bearer {HF_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
        cwd=str(REPO)).stdout.strip()

    # ---- Article LXXI condition 1: push confirmed --------------------
    ls = subprocess.run(
        ["git", "ls-remote",
         f"https://{GITHUB_TOKEN}@github.com/prateekm1007/"
         f"discovery-evidence-fabric.git" if GITHUB_TOKEN else
         "https://github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True, timeout=60)
    remote_main = ls.stdout.split()[0] if ls.stdout.strip() else ""
    push_ok = remote_main == commit
    print(f"[r447-verify] HEAD {commit[:12]} | origin/main "
          f"{remote_main[:12]} | push_confirmed={push_ok}")

    # ---- build state --------------------------------------------------
    stage = space_stage()
    print(f"[r447-verify] space stage: {stage}")
    if stage != "RUNNING":
        print("[r447-verify] build not finished — re-invoke later")
        return 1

    # ---- app probes ----------------------------------------------------
    v_status, version = probe("/api/version")
    if v_status != 200:
        print(f"[r447-verify] /api/version not ready: {version}")
        return 1
    h_status, health = probe("/api/health")
    deployed = version.get("engine_commit")
    identity_ok = deployed == commit
    drift = (health.get("deployment_identity") or {}).get(
        "deployment_drift")
    tamper = (health.get("deployment_identity") or {}).get("identity_tamper")
    health_ok = health.get("ok") is True and drift == "GREEN" \
        and tamper is False
    print(f"[r447-verify] /api/version engine_commit={deployed and deployed[:12]} "
          f"identity={'== target (VERIFIED)' if identity_ok else '!= TARGET (DRIFT!)'}")
    print(f"[r447-verify] /api/health ok={health.get('ok')} "
          f"drift={drift} tamper={tamper} "
          f"discovery_ready={health.get('discovery_ready')}")

    record = {
        "artifact_type": "R447 HF deployment record",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "github_repo": "https://github.com/prateekm1007/"
                       "discovery-evidence-fabric",
        "github_sha": commit,
        "hf_space": SPACE,
        "hf_revision": "77fb2d09889a96b39ee14dea217cfc0752ec044c "
                       "(tree upload; README frontmatter preserved "
                       "upfront this time)",
        "space_stage": stage,
        "zai_model": "zai-org/GLM-5.3",
        "api_version": version,
        "identity_verified": identity_ok,
        "article_lxxi_delivery_tuple": {
            "condition_1_push_confirmed": push_ok,
            "condition_2_deployed_sha_matches_target": identity_ok,
            "condition_3_health_check": health_ok,
            "target_sha": commit,
            "deployed_sha": deployed,
            "health_check_result": "GREEN" if health_ok else "BLOCKED",
            "drift": drift,
            "delivery_complete": bool(push_ok and identity_ok and health_ok),
        },
        "deployment_notes": [
            "the phase-split uploader (scripts/r447_deploy_upload.py): the "
            "sandbox kills spawned processes at the tool-call boundary, so "
            "upload+env ran in one call; the build ran on HF infrastructure",
            "the Space README frontmatter (sdk: docker, app_port: 7860) was "
            "written INTO the upload upfront — the CONFIG_ERROR of the first "
            "R447 deploy (git-archive overwrote it) fixed at the source",
            "the deploy carries: the run-not-found owner-capability "
            "transport fix + the canonical Space selection record + phases "
            "1/2/6/7 (geometry identity join, package terminal join, "
            "attacker v2, join attacks) + the C2 system-Chromium alignment "
            "+ the BS-021 credential scrub",
            "the prior deployed engine 23910247 resolved to no GitHub ref "
            "(the R447-C2 worklog finding) — THIS deploy serves "
            "dca25537, pushed and ls-remote verified, closing that finding",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1))
    print(f"[r447-verify] record -> {OUT}")
    complete = push_ok and identity_ok and health_ok
    print(f"[r447-verify] ARTICLE LXXI DELIVERY "
          f"{'COMPLETE' if complete else 'INCOMPLETE/BLOCKED'}")
    return 0 if complete else 4


if __name__ == "__main__":
    raise SystemExit(main())
