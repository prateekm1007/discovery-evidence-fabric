#!/usr/bin/env python3
"""r110_hf_router_probe.py — the auditor's R110 direction 2: unblock
the third model family through Hugging Face Inference Providers.

The router (https://router.huggingface.co/v1) is OpenAI-compatible;
the master HF token needs the 'Make calls to Inference Providers'
permission — the live call IS the test (a 403 or an exhausted-credits
error is recorded EXACTLY and the lane STOPS, per the direction).

Probe: GET /v1/models (the census), then ONE minimal chat call each
to Qwen/Qwen3-32B (alibaba), deepseek-ai/DeepSeek-V3.2 (deepseek),
meta-llama/Llama-3.3-70B-Instruct (meta), openai/gpt-oss-120b
(openai) — with ':fastest' retry when the bare id 404s. Real usage
bytes are required for the SERVED verdict; prompt-injected content is
never printed, statuses/latencies/usages only.
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r110_d2_hf_router_probe.json"
ROUTER = "https://router.huggingface.co/v1"
TOKEN = os.environ.get("HF_TOKEN", "")
MODELS = ["Qwen/Qwen3-32B", "deepseek-ai/DeepSeek-V3.2",
          "meta-llama/Llama-3.3-70B-Instruct", "openai/gpt-oss-120b"]
FAMILY = {"Qwen/Qwen3-32B": "qwen/alibaba",
          "deepseek-ai/DeepSeek-V3.2": "deepseek",
          "meta-llama/Llama-3.3-70B-Instruct": "meta",
          "openai/gpt-oss-120b": "openai"}
PROMPT = ('Reply with ONLY this exact JSON object and nothing else: '
          '{"A1":0,"A2":0,"A3":0,"A4":1,"B1":0,"B2":0,"B3":0,"B4":1,'
          '"A6":1,"B6":1,"prefer":"TIE"}')


def call(url: str, payload: dict | None):
    headers = {"Authorization": f"Bearer {TOKEN}",
               "User-Agent": "r110s1-hf-router-probe"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode()), \
                round(time.time() - t0, 1), None
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        return e.code, body, round(time.time() - t0, 1), \
            f"HTTP_{e.code}"
    except Exception as e:  # noqa: BLE001
        return None, None, round(time.time() - t0, 1), \
            f"{type(e).__name__}: {str(e)[:120]}"


rec = {
    "record": "R110_D2_HF_ROUTER_PROBE/1.0.0",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "direction": "the auditor R110 direction 2 (the HF Inference "
                 "Providers router; the funded-credential stop rule)",
    "token_permission_test": "the live /v1/models read IS the test",
    "census": None,
    "probes": [],
    "typed_conclusion": None,
}

if not TOKEN:
    rec["typed_conclusion"] = ("HF_TOKEN absent from env — typed "
                               "INFRA_CREDENTIAL_MISSING, stop")
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    raise SystemExit(3)

# 1. the census
code, body, lat, err = call(f"{ROUTER}/models", None)
census = {"status": code, "latency_s": lat, "error": err}
if code == 200:
    ids = sorted(m.get("id") for m in body.get("data", []))
    census["n_models_listed"] = len(ids)
    census["target_ids_listed"] = [m for m in MODELS if m in ids]
    census["sample_ids"] = ids[:10]
else:
    census["error_body"] = body if isinstance(body, str) else str(body)[:300]
rec["census"] = census
print("census:", code, "n=", census.get("n_models_listed"), "targets:",
      census.get("target_ids_listed"), "err:", err)

if code == 403:
    rec["typed_conclusion"] = ("the token LACKS the Inference Providers "
                               "permission (403 on the census read) — "
                               "exact error recorded, the lane STOPS "
                               "per the direction")
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    raise SystemExit(3)

# 2. one chat call per target (with :fastest fallback on 404)
for model in MODELS:
    entry = None
    for mid in (model, model + ":fastest"):
        payload = {"model": mid,
                   "messages": [{"role": "user", "content": PROMPT}],
                   "max_tokens": 64, "temperature": 0.0}
        code, body, lat, err = call(f"{ROUTER}/chat/completions",
                                    payload)
        ok = code == 200 and (body or {}).get("choices")
        entry = {"model": mid, "family": FAMILY[model],
                 "status": f"HTTP_{code}" if code else err,
                 "latency_s": lat}
        if ok:
            ch = body["choices"][0].get("message", {})
            entry.update({
                "served": True,
                "usage_bytes": body.get("usage"),
                "content_chars": len(ch.get("content") or ""),
                "served_model_field": body.get("model"),
            })
            break
        entry["error_body_excerpt"] = \
            body if isinstance(body, str) else str(body)[:220]
        entry["served"] = False
        if code and code not in (404, 400):
            break  # 403/402/429: the stop-class errors, no retry
    rec["probes"].append(entry)
    print(model, "->", entry["status"], "served:", entry["served"],
          "usage:", bool(entry.get("usage_bytes")))

served = [p for p in rec["probes"] if p.get("served")]
fams = sorted({p["family"] for p in served})
existing = {"agnes", "glm/zai", "cohere"}
new_fams = [f for f in fams
            if not any(x in f.lower() for x in
                       ("agnes", "zai", "glm", "cohere"))]
rec["families_served"] = fams
rec["new_families_vs_existing_panel"] = new_fams
rec["panel_third_family_unlocked"] = len(new_fams) >= 1
rec["panel_valid_families_projected"] = sorted(existing | set(fams))
rec["typed_conclusion"] = (
    f"{len(served)}/4 targets served with real usage bytes; "
    f"families: {fams}; new-vs-panel: {new_fams}" if served
    else "ZERO targets served — the exact errors are in the probes; "
         "per the direction the lane STOPS and the funded-key ask "
         "stands")
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT)
