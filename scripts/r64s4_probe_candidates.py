#!/usr/bin/env python3
"""r64s4_probe_candidates.py — pre-registration reachability probe
(the R36 lesson: register nothing without a reachable path).

Reads the OWNER-SUPPLIED keys from env (XKIRO_KEY_NEW / AGNES_KEY_NEW);
never prints or persists them. For each candidate id on xkiro: one
1-token chat capturing the EXACT served model string (the string the
registered constant must equal for served==registered), latency, and
a content head. Also verifies the agnes key via its roster.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")
from discovery_fabric.engine.route_adapter import BROWSER_UA  # noqa: E402

XKIRO_BASE = "https://api.xkiro.com/v1"
AGNES_BASE = "https://apihub.agnes-ai.com/v1"
CANDIDATES = ["anthropic/claude-haiku-4.5", "x-ai/grok-4.5",
              "openai/gpt-5.6-terra", "mistralai/mistral-large-4-0",
              "google/gemini-2.5-flash", "cohere/command-a-plus",
              "nvidia/nemotron-3-ultra",
              "sensenova/sensenova-6.8-flash-lite"]


def chat(base, key, model, max_tokens, ua, timeout=120.0):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, headers={
            "Authorization": f"Bearer {key}", "User-Agent": ua,
            "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    return {"served_model": d.get("model"),
            "finish_reason": ch.get("finish_reason"),
            "content_head": str((ch.get("message") or {})
                                .get("content") or "")[:20],
            "latency_s": round(time.time() - t0, 1)}


def roster(base, key, ua):
    req = urllib.request.Request(base.rstrip("/") + "/models", headers={
        "Authorization": f"Bearer {key}", "User-Agent": ua,
        "Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        d = json.loads(r.read())
    return sorted({str(m.get("id") if isinstance(m, dict) else m)
                   for m in (d.get("data") or d.get("models") or [])
                   if m})


if __name__ == "__main__":
    xkey = os.environ.get("XKIRO_KEY_NEW") or ""
    akey = os.environ.get("AGNES_KEY_NEW") or ""
    out = {"record": "R64S4_PREREGISTRATION_PROBE/1.0.0",
           "zero_zai_probes": True,
           "keys": "owner-supplied, env-passed, never printed",
           "candidates": []}
    try:
        ids = roster(XKIRO_BASE, xkey, BROWSER_UA)
        out["xkiro_roster_n"] = len(ids)
        out["xkiro_key_auth"] = "OK"
        for cand in CANDIDATES:
            if cand not in ids:
                out["candidates"].append({"requested": cand,
                                          "reachable": False,
                                          "typed_error":
                                          "id absent from roster"})
                continue
            try:
                r = chat(XKIRO_BASE, xkey, cand, 8, BROWSER_UA)
                r.update({"requested": cand, "reachable": True})
                out["candidates"].append(r)
            except urllib.error.HTTPError as e:
                out["candidates"].append({"requested": cand,
                                          "reachable": False,
                                          "typed_error": f"HTTP "
                                                         f"{e.code}"})
            except Exception as e:  # noqa: BLE001
                out["candidates"].append({"requested": cand,
                                          "reachable": False,
                                          "typed_error":
                                          f"{type(e).__name__}: "
                                          f"{str(e)[:80]}"})
    except Exception as e:  # noqa: BLE001
        out["xkiro_key_auth"] = f"FAILED {type(e).__name__}: " \
                                f"{str(e)[:80]}"
    try:
        out["agnes_key_auth"] = f"OK roster_n={len(roster(AGNES_BASE, akey, 'agnes-route-adapter/1.0'))}"
        a = chat(AGNES_BASE, akey, "agnes-2.5-flash", 8 + 512,
                 "agnes-route-adapter/1.0")
        out["agnes_probe"] = {"requested": "agnes-2.5-flash",
                              "reachable": True, **a}
    except Exception as e:  # noqa: BLE001
        out["agnes_key_auth"] = out.get("agnes_key_auth", "")
        out["agnes_probe"] = {"requested": "agnes-2.5-flash",
                              "reachable": False,
                              "typed_error": f"{type(e).__name__}: "
                                             f"{str(e)[:80]}"}
    with open("/home/z/my-project/discovery-evidence-fabric/"
              "eval/r64s4_preregistration_probe.json", "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("xkiro key:", out.get("xkiro_key_auth"),
          "| agnes key:", out.get("agnes_key_auth"))
    for c in out["candidates"]:
        if c.get("reachable"):
            print(f"  {c['requested']}: REACHABLE served="
                  f"{c['served_model']!r} latency={c['latency_s']}s "
                  f"head={c['content_head']!r} "
                  f"finish={c['finish_reason']}")
        else:
            print(f"  {c['requested']}: {c.get('typed_error')}")
