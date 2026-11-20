#!/usr/bin/env python3
"""r109_d2_transport_probe.py — the R108 direction-2 probe: which
transport can serve a THIRD distinct model family for the score-8
blind panel (families already served: agnes + z-ai; the judge xkiro
serves ministral = a third family for JUDGING, but the panel needs
the family SERVED for panel membership per the R107/R108 read).

Probes (typed outcomes, no key values, digests nowhere):
  A. xkiro re-probe past the 2026-11-19T16:25Z maintenance window:
     openai/gpt-5.6-terra + anthropic/claude-sonnet-4.6 (the R106
     403 pair) + openai/gpt-5.2 + anthropic/claude-haiku-4.5 —
     ONE minimal call each (max_tokens 64, the preflight contract).
  B. agnes catalog read (GET /v1/models) — which families does the
     funded generator transport actually list?
  C. the direct transports (openai/anthropic/gemini/openrouter/
     nvidia/deepseek/mistral/qwen/inception/crowllm/unorouter):
     the vault key check — an absent key is a typed UNFUNDED without
     burning a call; a present key gets ONE 8-token call.
Zero generation bytes leave this script; the record carries statuses,
latencies, and error CLASSES only (never keys, never prompts).
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

import os  # noqa: E402
from discovery_fabric.engine import llm_registry as lr  # noqa: E402
from eval.run import _transport_call  # noqa: E402

OUT = REPO / "eval" / "r109_d2_transport_probe.json"
PREFLIGHT_PROMPT = ('Preflight probe. Reply with ONLY this exact JSON '
                    'object and nothing else: {"A1":0,"A2":0,"A3":0,'
                    '"A4":1,"B1":0,"B2":0,"B3":0,"B4":1,"A6":1,"B6":1,'
                    '"prefer":"TIE"}')


def fam(model_id: str) -> str:
    m = model_id.lower()
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "gpt" in m or "openai" in m or "o1" in m or "o3" in m:
        return "openai"
    if "gemini" in m:
        return "google"
    if "llama" in m:
        return "meta"
    if "qwen" in m:
        return "alibaba"
    if "deepseek" in m:
        return "deepseek"
    if "mistral" in m or "ministral" in m or "magistral" in m:
        return "mistral"
    if "grok" in m:
        return "xai"
    if "mercury" in m:
        return "inception"
    if "glm" in m or "zai" in m:
        return "zai"
    if "agnes" in m:
        return "agnes"
    return "other"


def probe_call(provider: str, model: str) -> dict:
    t0 = time.time()
    res = _transport_call(provider, model, PREFLIGHT_PROMPT,
                          "Reply with ONLY the JSON object.", 64)
    lat = round(time.time() - t0, 1)
    ok = res.get("status") == "OK" and str(res.get("content") or "").strip()
    err = str(res.get("error") or "")
    cls = "OK" if ok else ("HTTP_403" if "403" in err else
                           "HTTP_401" if "401" in err else
                           "HTTP_429" if "429" in err else
                           "HTTP_5XX" if any(f"50{x}" in err for x in
                                             range(9)) or "500" in err
                           else "TRANSPORT_FAIL" if err else
                           "EMPTY_OUTPUT")
    return {"provider": provider, "model": model, "family": fam(model),
            "status": cls, "latency_s": lat,
            "error_class": None if ok else err[:120],
            "served_chars": len(str(res.get("content") or ""))}


def catalog_read(provider: str) -> dict:
    spec = next(s for s in lr.PROVIDER_SPECS
                if s.provider_id == provider)
    url = spec.url.rsplit("/chat/completions", 1)[0] + "/models"
    key = os.environ.get(spec.env_var, "")
    import urllib.request
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}",
        "User-Agent": "r109s1-probe"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        ids = sorted(m.get("id") for m in data.get("data", []))
        return {"provider": provider, "status": "OK",
                "latency_s": round(time.time() - t0, 1),
                "n_models": len(ids),
                "families": sorted(set(fam(i) for i in ids if i)),
                "sample_ids": ids[:12]}
    except Exception as e:  # noqa: BLE001
        return {"provider": provider, "status": "FAIL",
                "latency_s": round(time.time() - t0, 1),
                "error_class": f"{type(e).__name__}: {str(e)[:100]}"}


rec = {
    "record": "R109_D2_TRANSPORT_PROBE/1.0.0",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "claim": "c-0135 (r109-lane-d2d3-score8; the R108 direction 2)",
    "basis": ("the R106 probe typed both third-family candidates 403 on "
              "xkiro; the R64s4 window note expired 2026-11-19T16:25Z — "
              "this probe re-measures AFTER expiry + reads the funded "
              "transports' catalogs"),
    "vault_keys_present": sorted(
        k for k in ("AGNES_API_KEY", "AGNES_API_KEY_2", "XKIRO_API_KEY",
                    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                    "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
                    "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "QWEN_API_KEY",
                    "INCEPTION_API_KEY", "CROWLLM_API_KEY",
                    "UNOROUTER_API_KEY")
        if os.environ.get(k)),
    "vault_keys_absent": sorted(
        k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                    "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
                    "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "QWEN_API_KEY",
                    "INCEPTION_API_KEY", "CROWLLM_API_KEY",
                    "UNOROUTER_API_KEY")
        if not os.environ.get(k)),
    "probes": [],
    "catalogs": [],
}

# A. the xkiro third-family re-probe (post-maintenance)
for model in ("openai/gpt-5.6-terra", "anthropic/claude-sonnet-4.6",
              "openai/gpt-5.2", "anthropic/claude-haiku-4.5"):
    p = probe_call("xkiro", model)
    rec["probes"].append(p)
    print("xkiro", model, "->", p["status"], p["latency_s"], "s")

# B. the funded transports' catalogs
for prov in ("agnes", "xkiro"):
    c = catalog_read(prov)
    rec["catalogs"].append(c)
    print("catalog", prov, "->", c.get("status"),
          "n_models:", c.get("n_models"),
          "families:", c.get("families"))

# C. direct transports: absent key = typed UNFUNDED (no call burned);
# the funded set is only agnes/xkiro per the vault record
rec["unfunded_direct_transports"] = {
    k: "UNFUNDED (vault key absent; the direct/azure path needs an "
       "owner-delivered credential — the ONE-reminder rule, not "
       "routine nagging)"
    for k in rec["vault_keys_absent"]}

served = set()
for p in rec["probes"]:
    if p["status"] == "OK":
        served.add(p["family"])
rec["families_served_this_probe"] = sorted(served)
rec["panel_valid_score8"] = {
    "families_total_available": sorted(
        {"agnes", "zai"} | served),
    "count": len({"agnes", "zai"} | served),
    "third_family_found": bool(served),
    "typed_note": ("panel_valid_score8=true requires >=3 DISTINCT "
                   "families SERVED under the identical blind "
                   "protocol; this probe only re-measures "
                   "availability — the panel rerun itself is the "
                   "acceptance act (separate claim/quota)"),
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("wrote", OUT)
