"""zai gateway lifecycle — sandbox-local LLM transport for the engine.

Adapted from scripts/toscanini_6domain_benchmark.py (same mechanism, same
port). The gateway is a child process; the engine's llm_registry talks to
it. Keys stay server-side (loaded from .env.keys) and never appear in any
UI-facing payload.
"""
from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_PORT = 8787

_proc: subprocess.Popen | None = None


def _load_env_keys() -> dict:
    keys = {}
    kf = REPO_ROOT / ".env.keys"
    if kf.exists():
        for line in kf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()
    return keys


def gateway_up() -> bool:
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{GATEWAY_PORT}/healthz")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:  # noqa: BLE001
        return False


def ensure_gateway() -> dict:
    """Start the zai gateway if not already up. Idempotent."""
    global _proc
    if gateway_up():
        return {"started": False, "status": "ALREADY_UP"}
    keys = _load_env_keys()
    zai_key = keys.get("ZAI_API_KEY") or os.environ.get("ZAI_API_KEY")
    if not zai_key:
        return {"started": False, "status": "NO_ZAI_KEY"}
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = zai_key
    env["ZAI_GATEWAY_LOG"] = str(REPO_ROOT / "ENGINE_RUNS" / "zai_gateway_calls.jsonl")
    logf = open(REPO_ROOT / "ENGINE_RUNS" / "zai_gateway.stdout.log", "ab")
    _proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", str(GATEWAY_PORT)],
        cwd=str(REPO_ROOT), env=env, stdout=logf, stderr=logf,
        start_new_session=True)
    for _ in range(40):  # up to 20 s
        if gateway_up():
            return {"started": True, "status": "UP", "pid": _proc.pid}
        time.sleep(0.5)
    return {"started": False, "status": "GATEWAY_FAILED_TO_START",
            "pid": _proc.pid}


def preflight_probe() -> dict:
    """Small live LLM call to verify transport health before a run."""
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine import llm_registry as reg
    try:
        res = reg.generate(prompt="Reply with exactly: READY",
                           system="transport health probe",
                           timeout=90, max_retries=0)
        return {"status": res.status, "provider": res.provider_id,
                "latency_ms": res.latency_ms,
                "error": (res.error or "")[:160]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "CALL_FAILED", "error": f"{type(exc).__name__}: {exc}"[:200]}
