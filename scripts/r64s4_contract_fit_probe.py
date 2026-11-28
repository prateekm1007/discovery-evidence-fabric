#!/usr/bin/env python3
"""r64s4: real-contract measurement of the three serving candidates."""
import json
import sys
import time
import urllib.error
import urllib.request

REPO = "/home/z/my-project/discovery-evidence-fabric"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/scripts")
from discovery_fabric.engine.route_adapter import (  # noqa: E402
    BROWSER_UA, resolve_vault_key)
from r40_machine_v77 import contract_for_v72  # noqa: E402

contract = contract_for_v72("intervention-proposal")
prompt = json.dumps({
    "problem_id": "X", "device": "rooftop HVAC unit",
    "failure": "compressor overheating at high ambient",
    "question": "propose a passive fix and the falsification test",
    "question_type": "intervention-proposal",
    "user_variables": {}})


def raw(base, key, model, mt, ua):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": contract},
                     {"role": "user", "content": prompt}],
        "max_tokens": mt, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, headers={
            "Authorization": f"Bearer {key}", "User-Agent": ua,
            "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=200) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    txt = str((ch.get("message") or {}).get("content") or "")
    return {"served": d.get("model"), "finish": ch.get("finish_reason"),
            "vis_chars": len(txt),
            "completion_tokens": (d.get("usage") or {})
            .get("completion_tokens"),
            "lat": round(time.time() - t0, 1),
            "head": txt[:150].replace("\n", " ")}


xk = resolve_vault_key("XKIRO_API_KEY")
ag = resolve_vault_key("AGNES_API_KEY")
cases = [
    ("command-a-plus @4648", ("https://api.xkiro.com/v1", xk,
                              "cohere/command-a-plus", 4648,
                              BROWSER_UA)),
    ("sensenova-lite @2600", ("https://api.xkiro.com/v1", xk,
                              "sensenova/sensenova-6.8-flash-lite",
                              2600, BROWSER_UA)),
    ("agnes-3.0-flash @3112", ("https://apihub.agnes-ai.com/v1", ag,
                               "agnes-3.0-flash", 2600 + 512,
                               "agnes-route-adapter/1.0")),
]
only = sys.argv[1] if len(sys.argv) > 1 else None
for label, args in cases:
    if only and only not in label:
        continue
    print(label, "starting...", flush=True)
    try:
        r = raw(*args)
        print(label, "->", json.dumps(r)[:340], flush=True)
    except urllib.error.HTTPError as e:
        print(label, "-> HTTP", e.code, e.read().decode()[:120],
              flush=True)
    except Exception as e:  # noqa: BLE001
        print(label, "->", type(e).__name__, str(e)[:120], flush=True)
