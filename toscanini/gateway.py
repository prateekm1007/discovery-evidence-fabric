"""zai gateway lifecycle — sandbox-local LLM transport for the engine.

Adapted from scripts/toscanini_6domain_benchmark.py (same mechanism, same
port). The gateway is a child process; the engine's llm_registry talks to
it. Keys stay server-side (loaded from .env.keys) and never appear in any
UI-facing payload.

R392 (public transport): the engine is in EXTERNAL transport mode when the
registry's own provider selection resolves to a PUBLIC (non-loopback)
endpoint with a usable credential — the hosted deployment shape. No local
gateway subprocess exists or is needed in that mode; the preflight probe
still demands a real live completion before any run (unchanged semantics).
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_PORT = 8787

_proc: subprocess.Popen | None = None

# ---------------------------------------------------------------------------
# R392: transport probe cache (directive 2 — honest readiness).
# The LAST REAL probe result (a genuine live LLM completion, from a worker
# preflight or an explicit health probe). Never fabricated; stale until a
# real call succeeds (Art. XXV).
# ---------------------------------------------------------------------------
_PROBE_LOCK = threading.Lock()
_LAST_PROBE: dict = {"status": "NEVER_PROBED", "at": None, "source": None}


def record_probe(probe: dict, source: str) -> None:
    with _PROBE_LOCK:
        _LAST_PROBE.clear()
        _LAST_PROBE.update(probe or {})
        _LAST_PROBE["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _LAST_PROBE["source"] = source


def last_probe() -> dict:
    with _PROBE_LOCK:
        return dict(_LAST_PROBE)


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


def external_base_url() -> str | None:
    """R391 (deployment): if ZAI_BASE_URL points at a non-loopback
    OpenAI-compatible endpoint, the registry talks to it DIRECTLY (the
    {PROVIDER}_BASE_URL override in llm_registry) — no local gateway
    subprocess exists or is needed on a hosted engine."""
    url = (os.environ.get("ZAI_BASE_URL") or "").strip()
    if not url:
        return None
    host = urllib.parse.urlparse(url).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1"):
        return None
    return url


def _loopback(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host in ("127.0.0.1", "localhost", "::1", "")


def registry_external_transport() -> dict | None:
    """R392: ask the EXISTING provider abstraction which provider the
    engine would actually call under the default selection policy
    (availability -> quality -> cost -> latency). If that provider has a
    usable credential and a public (non-loopback) endpoint, the engine is
    in EXTERNAL transport mode and the returned dict describes it.

    This adds NO new LLM architecture: it reuses select_provider() exactly
    as generate() does, so the transport the health endpoint reports is
    the transport the engine will actually use. Providers whose slot is
    re-pointed at a loopback URL (sandbox zai) are treated as local — the
    sandbox gateway path is unchanged.
    """
    try:
        from discovery_fabric.engine.adapters import load_credentials
        load_credentials()
        from discovery_fabric.engine import llm_registry as reg
        spec, ledger = reg.select_provider(reg.SelectionPolicy())
    except Exception:  # noqa: BLE001 — unavailable, not silent success
        return None
    if spec is None:
        return None
    url = spec.url_for_call()
    if not url or _loopback(url):
        return None
    return {
        "status": "EXTERNAL",
        "base_url": url,
        "provider": spec.provider_id,
        "model": spec.model_for_call(),
        "selection": "registry default policy (availability->quality->"
                     "cost->latency)",
    }


def transport_snapshot() -> dict:
    """R392: READ-ONLY transport assessment for the health endpoint —
    same resolution order as ensure_gateway() but NEVER spawns anything
    (a GET must not have process side effects). Status values:
    EXTERNAL / ALREADY_UP / LOCAL_CONFIGURED (zai key present, gateway
    not yet spawned) / NO_TRANSPORT."""
    ext = external_base_url()
    if ext:
        return {"status": "EXTERNAL", "base_url": ext, "provider": "zai",
                "selection": "ZAI_BASE_URL operator override"}
    if gateway_up():
        return {"status": "ALREADY_UP"}
    zai_key = _load_env_keys().get("ZAI_API_KEY") or \
        os.environ.get("ZAI_API_KEY")
    if zai_key:
        # R451: the historical hard-coded glm-4-plus label is REMOVED —
        # the model id is reported HONESTLY from the environment (the
        # ZAI_MODEL override) or the registry spec default, never a
        # stale paid id pretending to be the configured transport.
        try:
            from discovery_fabric.engine import llm_registry as _reg
            _zai_model = _reg._SPEC_BY_ID["zai"].model_for_call()
        except Exception:  # noqa: BLE001 — label only
            _zai_model = os.environ.get("ZAI_MODEL", "").strip() \
                or "(registry default)"
        return {"status": "LOCAL_CONFIGURED",
                "base_url": f"http://127.0.0.1:{GATEWAY_PORT}/v1/chat/"
                            "completions",
                "provider": "zai", "model": _zai_model,
                "selection": "sandbox local gateway (spawned on first run)"}
    reg_ext = registry_external_transport()
    if reg_ext:
        return reg_ext
    return {"status": "NO_TRANSPORT",
            "reason": "no LLM provider credential available in the "
                      "environment (see availability matrix)"}


def ensure_gateway() -> dict:
    """Start the zai gateway if not already up. Idempotent.

    Transport resolution order (explicit at every step, never silent):
      1. ZAI_BASE_URL external re-point (R391 operator override) -> EXTERNAL
      2. local gateway already up -> ALREADY_UP
      3. zai credential present -> spawn the sandbox gateway -> UP
         (unavailable: NO_ZAI_KEY / GATEWAY_FAILED_TO_START)
      4. R392: registry-resolved public provider -> EXTERNAL
         (the hosted shape; the preflight probe still runs a REAL live
         completion before any run)
      5. otherwise -> NO_TRANSPORT (honest: nothing is configured)
    """
    global _proc
    ext = external_base_url()
    if ext:
        return {"started": False, "status": "EXTERNAL", "base_url": ext,
                "provider": "zai",
                "selection": "ZAI_BASE_URL operator override"}
    if gateway_up():
        return {"started": False, "status": "ALREADY_UP"}
    keys = _load_env_keys()
    zai_key = keys.get("ZAI_API_KEY") or os.environ.get("ZAI_API_KEY")
    if not zai_key:
        reg_ext = registry_external_transport()
        if reg_ext:
            return reg_ext
        return {"started": False, "status": "NO_TRANSPORT",
                "reason": ("no LLM provider credential available in the "
                           "environment (see availability matrix)")}
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
    """Small live LLM call to verify transport health before a run.

    R392: the result is cached for the health endpoint (directive 2) —
    LLM_TRANSPORT_READY is only ever TRUE when this real completion
    succeeded. A missing credential, timeout, or HTTP failure stays
    exactly what it is (Art. XXV).

    R415: the probe is a REAL completion through the routing ladder —
    generate() cascades across (provider, model) rungs, so the probe
    fails only when every rung failed, and the typed route (provider /
    model / attempt / failure_class per hop) travels with the result so
    the worker's blocked-transport record carries it (directive §1)."""
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine import llm_registry as reg
    try:
        res = reg.generate(prompt="Reply with exactly: READY",
                           system="transport health probe",
                           timeout=90, max_retries=0)
        out = {"status": res.status, "provider": res.provider_id,
               "model": res.model,
               "latency_ms": res.latency_ms,
               "error": (res.error or "")[:160],
               "route": [
                   {"provider_attempted": h.get("provider_attempted"),
                    "model": h.get("model"),
                    "attempts": h.get("attempts"),
                    "failure_type": h.get("failure_type"),
                    "timestamp": h.get("timestamp")}
                   for h in (res.route or [])]}
    except Exception as exc:  # noqa: BLE001
        out = {"status": "CALL_FAILED",
               "error": f"{type(exc).__name__}: {exc}"[:200]}
    record_probe(out, "preflight")
    return out
