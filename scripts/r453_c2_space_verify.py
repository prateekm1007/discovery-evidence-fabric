#!/usr/bin/env python3
"""r453_c2_space_verify.py — the R453-C2 Art. LXXI identity verification
against the canonical Space (prateekm1/toscanini-prod-validation).

The three conditions (EPISTEMIC_CONSTITUTION.md Article LXXI §1):

  1. push confirmed          — ls-remote origin refs/heads/main == the
                               deployed target SHA
  2. deployed identity       — /api/version engine_commit == the target
                               SHA (engine_commit_source, web_build_hash,
                               constitution_version captured)
  3. health check            — /api/health ok == true,
                               deployment_identity.deployment_drift ==
                               GREEN, identity_tamper == false

Record -> REPO/R453/HF_DEPLOYMENT_RECORD.json (the Art. LXXI §2
deployment tuple; the round's closure commit carries it into main).

Idempotent: safe to re-invoke while the build is still running (prints
the stage only, exit 1). --wait N polls the stage for up to N minutes
within THIS invocation (the sandbox kills spawned processes at the
tool-call boundary — the R447 measurement — so waiting happens inside
one live call), then probes.

Credentials (env-injection only, fail-closed): HF_TOKEN (the Space API
+ the Bearer probes), GITHUB_TOKEN (the ls-remote push confirmation).

Usage:
  HF_TOKEN=... GITHUB_TOKEN=... python3 r453_c2_space_verify.py
  HF_TOKEN=... GITHUB_TOKEN=... python3 r453_c2_space_verify.py --wait 7
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path("/home/z/my-project/hf_space")
SCRIPTS = Path(__file__).resolve().parent
STATE = SCRIPTS / "r453_c2_deploy_state.json"
OUT = REPO / "R453" / "HF_DEPLOYMENT_RECORD.json"

GITHUB_URL = "https://github.com/prateekm1007/discovery-evidence-fabric.git"
SPACE = "prateekm1/toscanini-prod-validation"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"


def _log(msg: str) -> None:
    print(f"[r453c2-verify] {msg}", flush=True)


def _creds() -> tuple[str, str]:
    hf = os.environ.get("HF_TOKEN", "")
    gh = os.environ.get("GITHUB_TOKEN", "")
    if not hf or not gh:
        _log("FATAL: HF_TOKEN / GITHUB_TOKEN missing — env injection "
             "only (R451-C2 scrub)")
        raise SystemExit(2)
    return hf, gh


def space_stage(hf_token: str) -> str:
    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/runtime",
        headers={"Authorization": f"Bearer {hf_token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("stage", "UNKNOWN")


def probe(path: str, hf_token: str, timeout: int = 90):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {hf_token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def ls_remote_main(github_token: str) -> str:
    pat_b64 = base64.b64encode(
        f"x-access-token:{github_token}".encode()).decode()
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(
        ["git", "-c", f"http.extraheader=Authorization: Basic {pat_b64}",
         "ls-remote", GITHUB_URL, "refs/heads/main"],
        capture_output=True, text=True, timeout=60,
        cwd=str(REPO), env=env)
    if r.returncode != 0:
        raise RuntimeError(f"ls-remote failed: {r.stderr[:200]}")
    out = r.stdout.split()
    return out[0] if out else ""


def wait_running(hf_token: str, minutes: int) -> str:
    deadline = time.time() + minutes * 60
    stage = "UNKNOWN"
    while time.time() < deadline:
        stage = space_stage(hf_token)
        if stage in ("RUNNING", "BUILD_ERROR", "RUNTIME_ERROR"):
            return stage
        _log(f"space stage: {stage} (polling, {minutes} min budget)")
        time.sleep(40)
    return stage


def main() -> int:
    hf_token, github_token = _creds()

    if not STATE.exists():
        _log(f"FATAL: no deploy state at {STATE} — run "
             f"r453_c2_space_deploy.py first")
        return 2
    state = json.loads(STATE.read_text())
    target = state["github_sha"]
    hf_revision = state.get("hf_space_revision", "UNKNOWN")
    _log(f"target (from deploy state): {target[:12]} | Space revision: "
         f"{str(hf_revision)[:12]}")

    # ---- Article LXXI condition 1: push confirmed ----------------------
    remote_main = ls_remote_main(github_token)
    push_ok = remote_main == target
    _log(f"origin/main {remote_main[:12]} | target {target[:12]} | "
         f"condition_1_push_confirmed={push_ok}")

    # ---- build state ----------------------------------------------------
    wait_min = 0
    for i, a in enumerate(sys.argv):
        if a == "--wait" and i + 1 < len(sys.argv):
            wait_min = int(sys.argv[i + 1])
    stage = (wait_running(hf_token, wait_min) if wait_min
             else space_stage(hf_token))
    _log(f"space stage: {stage}")
    if stage != "RUNNING":
        _log("build not finished (or errored) — re-invoke later")
        return 1

    # ---- condition 2: deployed identity --------------------------------
    v_status, version = probe("/api/version", hf_token)
    if v_status != 200:
        _log(f"/api/version not ready: {version}")
        return 1
    deployed = version.get("engine_commit")
    identity_ok = deployed == target
    _log(f"/api/version engine_commit={deployed and deployed[:12]} "
         f"source={version.get('engine_commit_source')} "
         f"constitution={version.get('constitution_version')} "
         f"identity={'== target (VERIFIED)' if identity_ok else '!= TARGET (DRIFT!)'}")

    # ---- condition 3: health check --------------------------------------
    h_status, health = probe("/api/health", hf_token)
    if h_status != 200:
        _log(f"/api/health not ready: {health}")
        return 1
    di = health.get("deployment_identity") or {}
    drift = di.get("deployment_drift")
    tamper = di.get("identity_tamper")
    health_ok = health.get("ok") is True and drift == "GREEN" \
        and tamper is False
    _log(f"/api/health ok={health.get('ok')} drift={drift} "
         f"tamper={tamper} discovery_ready={health.get('discovery_ready')}")

    complete = push_ok and identity_ok and health_ok
    record = {
        "artifact_type": "R453-C2 HF deployment record (the Claude-class "
                         "UI reconstruction at the merged SHA)",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "github_repo": GITHUB_URL,
        "github_sha": target,
        "hf_space": SPACE,
        "hf_revision": hf_revision,
        "space_stage": stage,
        "zai_model": "zai-org/GLM-5.3",
        "adapter": state.get("adapter"),
        "api_version": version,
        "api_health": health,
        "identity_verified": identity_ok,
        "article_lxxi_delivery_tuple": {
            "condition_1_push_confirmed": push_ok,
            "condition_2_deployed_sha_matches_target": identity_ok,
            "condition_3_health_check": health_ok,
            "target_sha": target,
            "deployed_sha": deployed,
            "health_check_result": "GREEN" if health_ok else "BLOCKED",
            "drift": drift,
            "delivery_complete": bool(complete),
        },
        "deployment_notes": [
            "the R451-C1.3 phase-split recipe verbatim (ONE adapter "
            "implementation, Art. X): git archive at the ls-remote-pinned "
            "origin/main tip, driver._r451_c13_adapter_dockerfile "
            "(RENDER_GIT_COMMIT pinned, llama.cpp b10930 + sha-pinned "
            "Qwen3-1.7B local route), README frontmatter upfront, ONE "
            "upload_folder, the full R451-C1.3 env contract",
            "the deploy carries the R453-C2 Claude-class UI "
            "reconstruction: the composer-first home, the chat-first run "
            "narrative, the right-hand workspace, honest "
            "BLOCKED/UNKNOWN/PENDING states with stale-positive "
            "suppression (Test B), the Art. LXIV deletions",
            "engine bytes unchanged since 7e4ed47d (the prior verified "
            "deploy): the commits between are the UI reconstruction + "
            "records-only worklog closures",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1))
    _log(f"record -> {OUT}")
    _log(f"ARTICLE LXXI DELIVERY {'COMPLETE' if complete else 'INCOMPLETE/BLOCKED'}")
    return 0 if complete else 4


if __name__ == "__main__":
    raise SystemExit(main())
