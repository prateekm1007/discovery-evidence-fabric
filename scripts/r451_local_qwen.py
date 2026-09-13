#!/usr/bin/env python3
"""Probe + speed measurement for the local zero-paid Qwen transport.

Starts llama-server (if not up), runs two REAL completions through the
OpenAI-compatible endpoint (tiny + realistic FIELD-line prompt, thinking
DISABLED via chat_template_kwargs — Qwen3's default thinking mode would
inflate latency and leak meta-commentary into field lines), prints the
measured latencies, and leaves the server running (the sandbox reaps it
at the tool-call boundary; the wrapper restarts it per slice).

Usage: python3 scripts/r451_local_qwen.py probe
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BIN = Path("/home/z/my-project/local_llm/bin/llama-b10930")
GGUF = Path("/home/z/my-project/local_llm/models/Qwen3-1.7B-Q4_K_M.gguf")
PORT = int(os.environ.get("LOCAL_QWEN_PORT", "8790"))
BASE = f"http://127.0.0.1:{PORT}"
MODEL_ALIAS = "qwen3-1.7b"
# R451-C1.1 memory + context tuning (both measured live):
# * with -c 8192 and 4 slots the server's RSS grows to 3.5 GB (85
#   percent of this 4 GB host) under the engine's long prompts —
#   slowing generation (60-90 s per structured call vs 35-45 s fresh)
#   and triggering the sandbox's memory-pressure reaper mid-run;
# * with -c 4096 -np 2 each slot's context halves to 2048, which
#   TRUNCATED the technical-state JSON mid-string (measured: a 3364-
#   char completion cut at ~841 tokens, parse FAILED).
# ONE slot with the full 8192 context: the engine's LLM calls are
# strictly sequential (one registry call at a time), so a single slot
# serializes nothing that was parallel, gives every call the full
# window (largest measured need: ~1 k prompt + 3 k completion), and
# caps the KV cache at one slot's worth — the memory ceiling drops
# without reintroducing truncation.
CONTEXT_TOKENS = int(os.environ.get("LOCAL_QWEN_CTX", "8192"))
SLOTS = int(os.environ.get("LOCAL_QWEN_SLOTS", "1"))

#: the model card — recorded on every cost-provenance surface (R451 §1)
MODEL_CARD = {
    "model_id": "Qwen/Qwen3-1.7B",
    "quantization": "Q4_K_M (GGUF build bartowski/Qwen_Qwen3-1.7B-GGUF "
                    "repo sha dcb19155b962dbb6389f4691a982043a8e651022)",
    "gguf_sha256": "72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668"
                   "ad84057e3bd66e250b24fb",
    "model_revision": "dcb19155b962dbb6389f4691a982043a8e651022 "
                      "(GGUF build; base model Qwen/Qwen3-1.7B, "
                      "apache-2.0)",
    "transport": "llama.cpp llama-server b10930 (CPU, 2 threads, "
                 "context 8192)",
    "local_or_remote": "LOCAL",
    "license": "apache-2.0",
    "cost_basis": "ZERO_PAID_COST_SELF_HOSTED",
}


def _proc_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE}/health", timeout=3):
            return True
    except Exception:  # noqa: BLE001
        return False


def ensure_server() -> bool:
    """Start llama-server when not already up; wait for health."""
    if _proc_alive():
        return True
    if not GGUF.exists():
        print(f"FATAL: GGUF missing: {GGUF}", file=sys.stderr)
        return False
    log = open("/home/z/my-project/local_llm/server.log", "ab")
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(BIN)
    subprocess.Popen(
        [str(BIN / "llama-server"), "-m", str(GGUF),
         "--port", str(PORT), "--host", "127.0.0.1",
         "-c", str(CONTEXT_TOKENS), "-np", str(SLOTS),
         "-t", "2", "--alias", MODEL_ALIAS,
         "--no-webui"],
        env=env, stdout=log, stderr=log, start_new_session=True)
    for _ in range(120):  # up to 60 s (model load ~3 s measured)
        if _proc_alive():
            return True
        time.sleep(0.5)
    return False


def chat(prompt: str, system: str, max_tokens: int,
         thinking: bool = False) -> tuple:
    body = {
        "model": MODEL_ALIAS,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read().decode("utf-8"))
    dt = time.time() - t0
    content = (d.get("choices") or [{}])[0].get("message", {}).get(
        "content", "")
    usage = d.get("usage") or {}
    return content, dt, usage


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "probe")
    if cmd == "card":
        print(json.dumps(MODEL_CARD, indent=1))
        return 0
    if not ensure_server():
        print("FATAL: llama-server failed to start", file=sys.stderr)
        return 2
    if cmd == "probe":
        c1, t1, u1 = chat("Reply with exactly: READY",
                          "transport health probe", 8)
        print(f"[tiny] {t1:.1f}s -> {c1.strip()[:40]!r}")
        print(json.dumps({"model_card": MODEL_CARD,
                          "tiny_latency_s": round(t1, 2)}, indent=1))
    elif cmd == "speed":
        c1, t1, u1 = chat("Reply with exactly: READY",
                          "transport health probe", 8)
        pt = u1.get("prompt_tokens", 0)
        ct = u1.get("completion_tokens", 0)
        print(f"[tiny] {t1:.1f}s  prompt={pt} completion={ct} "
              f"(~{ct / max(t1, 0.01):.1f} tok/s) -> {c1.strip()[:40]!r}")
        # a realistic directional-hypothesis FIELD-line prompt (~350
        # prompt tokens, 300 completion tokens)
        prompt = """You are the causal-improvement analyst of an invention engine.

A candidate FAILED its evaluation gauntlet. A typed causal diagnosis was recorded.
Propose ONE directional improvement hypothesis.

FAILED CANDIDATE:
- Mechanism: chromium-molybdenum white-iron impeller relying on hard chromium carbides for hydro-abrasive erosion resistance
- Intervention: as-cast impeller with 28 percent chromium carbide fraction
- Failure: engineering attack KILLED: impeller service life 1100 hours versus required 6000 hours; erosion-corrosion at pH 2.5 removes the hardened skin

TYPED CAUSAL DIAGNOSIS (recorded):
- Cause: ADVERSARIAL_KILL
- Basis: carbide fraction too low against 40-percent-weight solids; acidic chloride slurry couples erosion with corrosion

RETRIEVED EVIDENCE (exact spans, with ids):
- [ev:aaa111] Slurry erosion of white irons: Erosion rate falls with carbide volume fraction above 35 percent in quartz slurry.
- [ev:bbb222] Rubber linings: Natural rubber outlasts white iron by 3x below 60 C in abrasive acid slurry.

Respond in EXACTLY this format (each field on ONE line):
TARGET_VARIABLE: <the design variable to change>
CURRENT_VALUE: <current value>
PROPOSED_VALUE: <proposed value>
DIRECTION: <INCREASE | DECREASE | ADD | REMOVE | REPLACE | CHANGE_MECHANISM | TIGHTEN | RELAX | REVERSE>
MECHANISM_AFFECTED: <causal mechanism acted on>
CAUSAL_RATIONALE: <why, referencing the diagnosed cause>
PREDICTED_EFFECT: <observable effect>
EVIDENCE_IDS: <ids or none>
EVIDENCE_GAPS: <missing evidence or none>
FALSIFIER: <measurable outcome that would kill this>
MEASUREMENT_REQUIRED: <the measurement>
INTERVENTION_TYPE: <PARAMETER_MUTATION | TOPOLOGY_MUTATION | MATERIAL_MUTATION | OPERATING_CONDITION_MUTATION | MECHANISM_COMBINATION | EVIDENCE_UPDATE | CONSTRAINT_RELAXATION | CONSTRAINT_TIGHTENING>
CONFIDENCE: <LOW | MODERATE | HIGH>"""
        c2, t2, u2 = chat(prompt, "You propose machine-evaluable causal "
                          "improvement hypotheses. English only.", 400)
        pt2 = u2.get("prompt_tokens", 0)
        ct2 = u2.get("completion_tokens", 0)
        print(f"[realistic] {t2:.1f}s prompt={pt2} completion={ct2} "
              f"(~{ct2 / max(t2, 0.01):.1f} tok/s)")
        print("--- completion (first 600 chars) ---")
        print(c2[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
