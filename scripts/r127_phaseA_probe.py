#!/usr/bin/env python3
"""r127_phaseA_probe.py — the Phase-A capability probe (claim
c-0200 recon; digests-only, zero key output).

Answers three typed questions about the agnes route:
  Q1 structured outputs — does /chat/completions accept a
     response_format json_schema body (HTTP 200 + schema-conformant
     content), or refuse it?
  Q2 cached-token telemetry — does usage carry cache fields
     (prompt_tokens_details.cached_tokens / prompt_cache_hit_tokens)?
  Q3 frozen-prefix caching behavior — do repeated calls sharing a
     long identical prefix show any cache evidence in usage?

Also collects the baseline per-call latency for the tiny calls.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine.route_adapter import (  # noqa: E402
    resolve_vault_key)

BASE = "https://apihub.agnes-ai.com/v1"
MODEL = "agnes-3.0-flash"
OUT = REPO / "eval" / "r127_phaseA" / "probe.json"
OUT.parent.mkdir(parents=True, exist_ok=True)


def post(body: dict, timeout_s: float = 90.0):
    key = resolve_vault_key("AGNES_API_KEY")
    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": "r127-phaseA-probe/1.0"},
        method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            d = json.loads(r.read())
        return {"ok": True, "latency_s": round(time.monotonic() - t0, 2),
                "resp": d}
    except urllib.error.HTTPError as e:
        return {"ok": False, "latency_s": round(time.monotonic() - t0, 2),
                "http": e.code, "detail": e.read()[:220].decode(
                    "utf-8", "replace")}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "latency_s": round(time.monotonic() - t0, 2),
                "err": f"{type(e).__name__}: {str(e)[:160]}"}


def usage_of(resp):
    u = (resp or {}).get("usage") or {}
    return {k: u.get(k) for k in
            ("prompt_tokens", "completion_tokens", "total_tokens",
             "prompt_tokens_details", "completion_tokens_details",
             "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
            if u.get(k) is not None}


FROZEN_PREFIX = (
    "You are reviewing an engineering proposal. The automated check "
    "layer surfaced the findings listed below against the original "
    "problem. Fix the proposal so the findings no longer apply, "
    "changing as little else as possible. Return the complete "
    "corrected proposal. INPUT RULE: for every input, measurement, "
    "or logic signal your corrected proposal relies on, state "
    "explicitly which permitted sensor or measurement it comes from, "
    "or how it is derived from the permitted measurements with the "
    "formula; remove any input that cannot be derived from the "
    "permitted measurements. DUTY-PRICING RULE: if your corrected "
    "proposal modulates any duty cycle, schedule, or intermittent "
    "operation, it must price the operational cost of that "
    "modulation (state the basis: throughput, energy, or margin, "
    "derived from the permitted measurements) - never introduce or "
    "leave an unpriced duty modulation. SCOPE RULE: introduce no "
    "mechanism the surfaced findings do not require, and preserve "
    "every duty and cost already priced in the original proposal. "
    "This standard block is repeated verbatim on every call so the "
    "route's prefix cache can key on it. " * 3)

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "review_fix",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "corrected_proposal": {"type": "string"},
                "cost_basis_note": {"type": "string"},
            },
            "required": ["corrected_proposal", "cost_basis_note"],
            "additionalProperties": False,
        },
    },
}

results = {}

# Q1: structured outputs
r_schema = post({
    "model": MODEL, "max_tokens": 900, "temperature": 0.0,
    "response_format": SCHEMA,
    "messages": [{"role": "user", "content":
                  "Review note: the proposal has no bill section. "
                  "Return the fix object for a water-pump duty "
                  "modulation proposal."}]})
r_schema["usage_fields"] = usage_of(r_schema.get("resp"))
content = ""
if r_schema["ok"]:
    content = str(((r_schema["resp"].get("choices") or [{}])[0]
                   .get("message") or {}).get("content") or "")
r_schema["content_is_json_object"] = content.strip().startswith("{")
try:
    json.loads(content)
    r_schema["content_parses_as_json"] = True
except Exception:  # noqa: BLE001
    r_schema["content_parses_as_json"] = False
results["Q1_structured"] = {k: v for k, v in r_schema.items()
                            if k != "resp"}
results["Q1_structured"]["content_head"] = content[:120]

# Q2+Q3: baseline call, then two calls sharing the SAME frozen prefix
# with different variable suffixes (cache-hit evidence = identical
# prompt_tokens + a cache field, or identical usage with lower
# latency)
suffices = [
    "\n\nPROBLEM VARIANT A: an irrigation pump modulates its duty "
    "cycle seasonally; state the annual energy cost basis.",
    "\n\nPROBLEM VARIANT B: a kiln fan modulates its duty cycle "
    "hourly; state the annual energy cost basis.",
]
base_call = post({"model": MODEL, "max_tokens": 60, "temperature": 0.0,
                  "messages": [{"role": "user",
                                "content": "Reply READY only."}]})
results["Q2_baseline"] = {
    "ok": base_call["ok"], "latency_s": base_call["latency_s"],
    "usage_fields": usage_of(base_call.get("resp"))}

prefix_calls = []
for i, sfx in enumerate(suffices):
    c = post({"model": MODEL, "max_tokens": 220, "temperature": 0.0,
              "messages": [{"role": "user",
                            "content": FROZEN_PREFIX + sfx}]})
    prefix_calls.append({
        "variant": i, "ok": c["ok"], "latency_s": c["latency_s"],
        "usage_fields": usage_of(c.get("resp"))})
    time.sleep(2)
results["Q3_frozen_prefix"] = prefix_calls

# the retry-free JSON control: does the model emit parseable JSON
# when asked in-band WITHOUT response_format (the fallback contract)?
r_inband = post({"model": MODEL, "max_tokens": 400, "temperature": 0.0,
                 "messages": [{"role": "user", "content":
                     "Return ONLY a JSON object with exactly these "
                     "keys: {\"corrected_proposal\": string, "
                     "\"cost_basis_note\": string}. The proposal: a "
                     "pump runs 60% duty; price its energy cost. No "
                     "other text."}]})
c2 = ""
if r_inband["ok"]:
    c2 = str(((r_inband["resp"].get("choices") or [{}])[0]
              .get("message") or {}).get("content") or "")
try:
    json.loads(c2[c2.find("{"):c2.rfind("}") + 1])
    r_inband["parses"] = True
except Exception:  # noqa: BLE001
    r_inband["parses"] = False
results["Q1b_inband_json"] = {"ok": r_inband["ok"],
                              "latency_s": r_inband["latency_s"],
                              "parses": r_inband["parses"],
                              "content_head": c2[:120]}

OUT.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
print(json.dumps(results, indent=1)[:2600])
print(f"\nwritten: {OUT}")
