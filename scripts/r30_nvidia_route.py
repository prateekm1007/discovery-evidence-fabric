#!/usr/bin/env python3
"""r30_nvidia_route.py — the typed NVIDIA NIM route (the R31/R32
transport lane).

HISTORY (all typed, all forward-committed):
- R31: operator-supplied NVIDIA key verified servable (catalog 39;
  tiny-call 200s with real content on glm-5.3-flash, nemotron-3-ultra,
  nano-omni-30b, bolt-e4b; NO qwen family in the catalog — the
  pre-registered judge route crowllm/qwen-3.8-max:free is NOT servable
  from this key; Art. 26 held, never silently swapped). Fallback wired
  as generator-leg-only, route recorded per call.
- R31 run defect (caught by the row ledger: chars=0 rows, quarantined
  in eval/pairs/r30_v76_tuned_defective_transport/): glm-5.3-flash on
  the machine's LONG contract prompt burns the ENTIRE token budget on
  reasoning_content — content=0, finish=length at 8192 tokens in 416s;
  non-streamed long calls additionally 504 at the free endpoint.
- R32 typed probe (scripts/r30_transport_probe.py -> eval/
  r30_transport_probe.json): glm-5.3-flash STILL_REASONING (9277
  reasoning chars in a 100s sample, content=0 — unservable latency,
  NOT a loop: the deliberation text advances); nemotron-3-ultra-550b
  CONTENT_FLOWING (6230 content chars in 77s); bolt-e4b
  CONTENT_FLOWING (3115 chars, zero reasoning, 8.8s).

AMENDED FALLBACK CHAIN (typed amendment filed in the claim BEFORE any
round run): primary local z.ai gateway -> nvidia/nemotron-3-ultra-550b
-> nvidia/nemotron-3.5-bolt-e4b. glm-5.3-flash is retained as
DOCUMENTED-UNSERVABLE (the probe record is the evidence).
NOTE THE MODEL-FAMILY CHANGE: the fallback generator is no longer the
GLM-5.3-flash family — it is a DIFFERENT family (nemotron). This is
disclosed per call (route/route_model in every ledger row) and in the
claim amendment; the machine's contract, directive, scans, repair
budget and K_GEN=1 are untouched; the acceptance read stays the
auditor's on a fresh auditor-authored set. Streaming is used for every
fallback call (the non-streamed long call 504s at the endpoint).

ROLE DISCIPLINE (unchanged): generator-leg fallback ONLY. The judge
route is never served from this module; nemotron-ultra is flagged
judge-CAPABLE in the catalog but is NOT the pre-registered judge and
is not wired as one here.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request

BASE_URL = "https://integrate.api.nvidia.com/v1"
# Typed probe verdict 2026-11-16: unservable latency on machine-path
# prompts (reasoning span exceeds any workable budget; see module doc).
UNSERVABLE_MODELS = {"z-ai/glm-5.3-flash"}
# The amended fallback chain, in try order.
FALLBACK_CHAIN = [
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-bolt-e4b",
]
MAX_TOKENS = 8192
# Art. 26 note: a DIFFERENT family from the GLM generator — flagged
# judge-capable in the catalog, but NOT the pre-registered judge route.
JUDGE_CAPABLE_BUT_NOT_WIRED = "nvidia/nemotron-3-ultra-550b-a55b"


def _key() -> str:
    k = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not k:
        try:
            repo = os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))
            k = subprocess.run(
                ["bash", "-c",
                 f"grep '^NVIDIA_API_KEY=' {repo}/.env.keys | cut -d= -f2"],
                capture_output=True, text=True).stdout.strip()
        except Exception:
            k = ""
    if not k:
        raise RuntimeError(
            "NVIDIA_API_KEY not set (vault NVIDIA_API_KEY missing)")
    return k


class NVIDIAEmptyContent(RuntimeError):
    """Typed: the model produced no final content (reasoning consumed
    the budget). The caller advances to the next chain member."""


def nvidia_chat_stream(messages, model: str, max_tokens: int = MAX_TOKENS,
                       temperature: float = 0.0):
    """One STREAMED OpenAI-compatible call (streaming is required: the
    non-streamed long call 504s at the free endpoint). Raises
    NVIDIAEmptyContent (typed) when the stream ends with no content."""
    body = json.dumps({"model": model, "messages": messages,
                       "max_tokens": max_tokens,
                       "temperature": temperature,
                       "stream": True}).encode()
    req = urllib.request.Request(
        BASE_URL + "/chat/completions", data=body,
        headers={"Authorization": "Bearer " + _key(),
                 "Content-Type": "application/json",
                 "Accept": "text/event-stream"}, method="POST")
    t0 = time.time()
    content, finish = [], None
    with urllib.request.urlopen(req, timeout=560) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            if line == "data: [DONE]":
                break
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            ch = (d.get("choices") or [{}])[0]
            delta = ch.get("delta") or {}
            if delta.get("content"):
                content.append(delta["content"])
            if ch.get("finish_reason"):
                finish = ch["finish_reason"]
    text = "".join(content)
    if not text.strip():
        raise NVIDIAEmptyContent(
            f"{model}: stream ended content=0 finish={finish}")
    return text, {"route": "nvidia", "model": model,
                  "latency_s": round(time.time() - t0, 1),
                  "finish_reason": finish}


def nvidia_chat(messages, model: str = FALLBACK_CHAIN[0],
                max_tokens: int = MAX_TOKENS, temperature: float = 0.0):
    """Compat wrapper: single-model call with the typed empty-content
    error (no chain walk — the chain lives in gen_with_fallback)."""
    return nvidia_chat_stream(messages, model, max_tokens, temperature)


# Sustained-outage clause (R32 amendment #3, filed BEFORE any row used
# it): after this many consecutive PRIMARY infra failures (500-class,
# NOT auth — auth always falls through immediately), the amended chain
# serves and the row's route record discloses
# "sustained_primary_outage". A single transient 500 still retries on
# the primary (the R24 behavior is preserved for blips).
SUSTAINED_OUTAGE_THRESHOLD = 2
_infra_fail_streak = {"n": 0}


def gen_with_fallback(prompt: str, contract: str, gw_key: str,
                      primary_gen):
    """Primary generator first (the local z.ai gateway); on an auth
    error (401/403), a connection failure, or an empty-content result,
    walk the amended NVIDIA chain; on a SUSTAINED primary infra outage
    (>= SUSTAINED_OUTAGE_THRESHOLD consecutive 500-class failures),
    the chain serves with a typed sustained_primary_outage disclosure.
    Returns (content, route_meta) naming the route that served."""
    global_streak = _infra_fail_streak
    try:
        content, lat = primary_gen(prompt, contract, gw_key)
        if content and content.strip():
            global_streak["n"] = 0
            return content, {"route": "zai_gateway", "latency_s": lat}
        why = "primary returned empty content"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            why = f"primary HTTP {e.code} (typed: credential dead)"
        elif e.code >= 500:
            global_streak["n"] += 1
            if global_streak["n"] < SUSTAINED_OUTAGE_THRESHOLD:
                raise  # typed infra retry: the ladder handles blips
            why = (f"sustained_primary_outage "
                   f"(HTTP 500 x{global_streak['n']}, typed)")
        else:
            raise  # 4xx client errors are not transport-fallback scope
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        global_streak["n"] += 1
        why = f"primary unreachable ({type(e).__name__})"
    last_err = why
    for model in FALLBACK_CHAIN:
        if model in UNSERVABLE_MODELS:
            continue
        try:
            content, meta = nvidia_chat_stream(
                [{"role": "system", "content": contract},
                 {"role": "user", "content": prompt}], model=model)
            meta["fallback_reason"] = last_err
            _infra_fail_streak["n"] = 0  # served; probe primary next row
            return content, meta
        except NVIDIAEmptyContent as e:
            last_err = f"{model} empty content (typed)"
            continue
        except (urllib.error.HTTPError, urllib.error.URLError,
                ConnectionError, OSError) as e:
            last_err = f"{model} {type(e).__name__}: {str(e)[:80]}"
            continue
    raise RuntimeError(
        "TYPED: every fallback route failed — " + last_err)
