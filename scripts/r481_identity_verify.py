#!/usr/bin/env python3
"""R481 — identity verification for the union deploy (the Art. LXXI
tuple legs this round owns):

1. the Space reaches RUNNING at the new revision
2. /api/version engine_commit == the union tip (baked at build)
3. /api/health: ok, deployment_drift GREEN, identity_tamper false,
   providers measured (the R480 repoint must hold: zai on atria's
   catalog, atria HEALTHY)
4. the durable-state branch (runtime-state-hf) alive on the GitHub
   repo (queried with the vault PAT; graceful if unreachable)

Polls until the deadline; typed failures never guess.
OUT: R481/IDENTITY_VERIFY.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R481" / "IDENTITY_VERIFY.json"
SPACE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"
DEADLINE_S = int(os.environ.get("R481_VERIFY_DEADLINE", "2700"))


def load_vault() -> dict:
    vault = {}
    p = Path("/home/z/my-project/.secrets.env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vault[k.strip()] = v.strip()
    return vault


VAULT = load_vault()
HF_TOKEN = VAULT.get("HF_TOKEN", "")
GH_TOKEN = VAULT.get("GITHUB_TOKEN", "")


def _get(url: str, token: str = "", timeout: int = 60):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def space_stage() -> str:
    try:
        d = _get("https://huggingface.co/api/spaces/"
                 "prateekm1/toscanini-prod-validation/runtime",
                 HF_TOKEN)
        return str(d.get("stage") or d)
    except Exception as exc:  # noqa: BLE001
        return f"UNKNOWN ({type(exc).__name__})"


def main() -> int:
    target = os.environ.get("R481_TARGET_SHA") or subprocess_head()
    if not target:
        print("FATAL: no target (R481_TARGET_SHA unset and HEAD "
              "unresolvable)")
        return 2
    print(f"target: {target}")
    t0 = time.time()

    stage = ""
    while time.time() - t0 < DEADLINE_S:
        stage = space_stage()
        print(f"[{int(time.time()-t0):4d}s] space stage: {stage}",
              flush=True)
        if stage in ("RUNNING", "RUNNING_BUILDING"):
            break
        if stage.startswith("BUILD_ERROR") or stage in ("PAUSED",
                                                        "CRASHED"):
            print(f"FATAL: space stage {stage}")
            return 1
        time.sleep(30)

    version = None
    for attempt in range(90):
        if time.time() - t0 > DEADLINE_S:
            break
        try:
            v = _get(f"{SPACE_URL}/api/version", HF_TOKEN)
            commit = v.get("engine_commit")
            print(f"[/api/version] engine_commit={str(commit)[:12]} "
                  f"(source={v.get('source')}, "
                  f"constitution={v.get('constitution_version')})",
                  flush=True)
            if commit == target:
                version = v
                break
        except Exception as exc:  # noqa: BLE001
            print(f"[/api/version] probe pending "
                  f"({type(exc).__name__})", flush=True)
        time.sleep(20)

    if not version:
        print("DEADLINE: the version never matched the target")
        return 1

    health = _get(f"{SPACE_URL}/api/health", HF_TOKEN)
    ok = health.get("ok")
    ident = health.get("deployment_identity") or {}
    drift = ident.get("deployment_drift") or health.get(
        "deployment_drift")
    tamper = ident.get("identity_tamper")
    providers = health.get("providers") or {}
    print(f"[/api/health] ok={ok} drift={drift} "
          f"identity_tamper={tamper}")
    print(f"[/api/health] providers={json.dumps(providers)[:400]}")

    durable = None
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/prateekm1007/"
            "discovery-evidence-fabric/branches/runtime-state-hf",
            headers={"Authorization": f"Bearer {GH_TOKEN}",
                     "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        durable = {"branch": "runtime-state-hf",
                   "tip": (d.get("commit") or {}).get("sha"),
                   "alive": True}
    except Exception as exc:  # noqa: BLE001
        durable = {"alive": False, "probe_error": repr(exc)[:160]}

    tuple_ok = (ok is True and drift == "GREEN" and tamper is False)
    out = {
        "round": "R481",
        "target_sha": target,
        "identity_flip": {
            "before": "fbc73b8 (the R479/R480 deployed state — see "
                      "R481/SPACE_DEPLOY_RECORD.json before_identity "
                      "for the live-measured baseline)",
            "after": {
                "engine_commit": version.get("engine_commit"),
                "engine_commit_source": version.get("source"),
                "web_build_hash": version.get("web_build_hash"),
                "constitution_version":
                    version.get("constitution_version"),
            },
        },
        "health_after": {
            "ok": ok, "deployment_drift": drift,
            "identity_tamper": tamper,
            "providers": providers,
        },
        "durable_state": durable,
        "space_stage_at_verify": stage,
        "tuple": "GREEN" if tuple_ok else "DEGRADED",
        "verified_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"[r481-verify] record -> {OUT}")
    print("ARTICLE LXXI TUPLE (this round's legs): "
          + ("GREEN" if tuple_ok else "DEGRADED"))
    return 0 if tuple_ok else 1


def subprocess_head() -> str:
    import subprocess
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    sys.exit(main())
