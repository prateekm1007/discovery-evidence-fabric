#!/usr/bin/env python3
"""r170s1_judge_census.py — the judge-model census on the NEW owner transport
(cantrustai) + the two seat probes (xkiro aya32b callable? cent-ai J2 hy4?).

Minimal burn: one 8-token probe per model, non-corpus prompt ("Reply with
exactly: OK"). Typed outcomes only; no key bytes printed.
"""
from __future__ import annotations
import json, os, urllib.request, urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
PROMPT = "Reply with exactly: OK"

for line in (REPO / ".env.keys").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

def chat(url, key, model, mt=8):
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": mt}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))
            head = ""
            try: head = (body.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
            except Exception: head = json.dumps(body)[:80]
            return {"status": r.status, "head": head.strip()[:40]}
    except urllib.error.HTTPError as e:
        det = ""
        try: det = e.read().decode("utf-8")[:160]
        except Exception: pass
        return {"status": e.code, "err": f"{e.reason} {det}"[:160]}
    except Exception as e:
        return {"status": None, "err": f"{type(e).__name__}: {str(e)[:100]}"}

out = {}

cb = os.environ.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1").rstrip("/")
ck = os.environ.get("CTAI_API_KEY", "")
JUDGES = [
    "cohere/aya-expanse-32b",          # aya32b — the AM51 substitute
    "aya-expanse-32b",                  # bare-name variant
    "mistralai/ministral-14b",          # mst14b — the ORIGINAL delisted judge
    "mistralai/mistral-small-2603",     # msm2603 — kept-aside 4th judge / fallback
    "sensenova/sensenova-6.8-flash-lite",  # snlite — serving panel anchor
    "hy4-flash:free",                   # hy4f — the cent-ai judge id form
]
out["ctai_judge_census"] = {}
for m in JUDGES:
    r = chat(f"{cb}/chat/completions", ck, m)
    out["ctai_judge_census"][m] = r
    if r.get("status") == 200:
        break  # one hit is enough to type the transport; stop burning

xb = os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
xk = os.environ.get("XKIRO_API_KEY", "")
out["xkiro_aya32b_probe"] = chat(f"{xb}/chat/completions", xk, "cohere/aya-expanse-32b")

cb2 = os.environ.get("CENT_AI_BASE_URL", "https://api.cent-ai.dev/v1").rstrip("/")
ck2 = os.environ.get("CENT_AI_API_KEY", "")
out["cent_j2_hy4_probe"] = chat(f"{cb2}/chat/completions", ck2, "hy4-flash:free")

print(json.dumps(out, indent=1, ensure_ascii=False))
