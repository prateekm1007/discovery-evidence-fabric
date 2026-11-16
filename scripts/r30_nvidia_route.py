#!/usr/bin/env python3
"""r30_nvidia_route.py — the typed NVIDIA NIM route (the R31
credential round).

The operator supplied an NVIDIA API key (vault: NVIDIA_API_KEY,
gitignored, loaded by r7_queue_runner._load_key_vault — names only
ever echoed). Verified servable on 2026-11-16 with tiny calls
(catalog 39 models; chat 200 + real content):
  z-ai/glm-5.3-flash                              3.6-5.0s  content ok
  nvidia/nemotron-3-ultra-550b-a55b               1.1-2.0s  content ok
  nvidia/nemotron-3-nano-omni-30b-a3b-reasoning   1.1s      content ok
  nvidia/nemotron-3.5-bolt-e4b                    0.5s      content ok
  (NO qwen family in the catalog — the pre-registered judge route
  crowllm/qwen-3.8-max:free is NOT servable from this key; Art. 26
  judge options are flagged, never silently swapped.)

ROLE: a typed TRANSPORT fallback for the generator leg when the
primary local z.ai gateway returns an auth error. The contract, the
directive, the scans, the budget and the claim discipline are
untouched — only the HTTP endpoint serving the same GLM-5.3-flash
model family changes, and EVERY call records which route served it.
The model difference (z.ai GLM-5.3 vs NVIDIA-hosted z-ai/
glm-5.3-flash serving) is disclosed per call and in the round
record; the acceptance read stays the auditor's.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

BASE_URL = "https://integrate.api.nvidia.com/v1"
GENERATOR_MODEL = "z-ai/glm-5.3-flash"
# Art. 26 note: a DIFFERENT model family from the generator
# (glm-5.3-flash) — the only catalog model usable as a judge-family
# alternative; NOT the pre-registered judge route.
JUDGE_CAPABLE_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"


def _key() -> str:
    k = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not k:
        try:  # load the vault if the caller has not
            import sys
            from pathlib import Path
            repo = Path(__file__).resolve().parents[1]
            sys.path.insert(0, str(repo))
            from r7_queue_runner import _load_key_vault
            _load_key_vault()
            k = os.environ.get("NVIDIA_API_KEY", "").strip()
        except Exception:
            k = ""
    if not k:
        raise RuntimeError(
            "NVIDIA_API_KEY not set (vault NVIDIA_API_KEY missing)")
    return k


def nvidia_chat(messages, model: str = GENERATOR_MODEL,
                max_tokens: int = 2600, temperature: float = 0.0,
                timeout: int = 300):
    """One OpenAI-compatible call. Returns
    (content, {"route": "nvidia", "model", "latency_s", "usage"})."""
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens,
                       "temperature": temperature}).encode()
    req = urllib.request.Request(
        BASE_URL + "/chat/completions", data=body,
        headers={"Authorization": "Bearer " + _key(),
                 "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    content = str(msg.get("content") or "")
    if not content.strip() and msg.get("reasoning_content"):
        # reasoning models answer in content after the reasoning
        # span; an empty content with a reasoning span means the
        # budget was consumed thinking — surface the tail as typed
        # context, never as the answer
        content = ""
    return content, {"route": "nvidia", "model": model,
                     "latency_s": round(time.time() - t0, 1),
                     "usage": d.get("usage", {})}


def gen_with_fallback(prompt: str, contract: str, gw_key: str,
                      primary_gen):
    """Primary generator first (the local z.ai gateway); on an auth
    error (401/403) or a connection refusal, fall back typed to the
    NVIDIA route. Returns (content, route_meta) where route_meta
    names the route that actually served the call."""
    try:
        content, lat = primary_gen(prompt, contract, gw_key)
        return content, {"route": "zai_gateway", "latency_s": lat}
    except urllib.error.HTTPError as e:
        if e.code not in (401, 403):
            raise
        why = f"primary HTTP {e.code} (typed: credential dead)"
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        why = f"primary unreachable ({type(e).__name__})"
    content, meta = nvidia_chat(
        [{"role": "system", "content": contract},
         {"role": "user", "content": prompt}])
    meta["fallback_reason"] = why
    return content, meta
