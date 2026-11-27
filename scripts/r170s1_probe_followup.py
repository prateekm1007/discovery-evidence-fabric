#!/usr/bin/env python3
"""r170s1_probe_followup.py — the blocked-probe followup (zero xkiro burn):
cantrustai chat probe (its /models 404s — try the chat path + root base),
cent-ai models err detail, tokenrouter models err detail."""
from __future__ import annotations
import json, os, urllib.request, urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

for line in (REPO / ".env.keys").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

def show(tag, r):
    body = r.get("body")
    s = json.dumps(body)[:500] if body is not None else ""
    print(tag, json.dumps({k: r[k] for k in r if k != "body"}))
    if s: print(tag, "body:", s)

def get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            try: body = json.loads(r.read().decode("utf-8"))
            except Exception: body = r.read().decode("utf-8", "replace")[:200]
            return {"status": r.status, "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "err": str(e.reason)[:60]}
    except Exception as e:
        return {"status": None, "err": f"{type(e).__name__}: {str(e)[:100]}"}

def chat(url, key, model, mt=8):
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": mt}).encode()
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
        try: det = e.read().decode("utf-8")[:150]
        except Exception: pass
        return {"status": e.code, "err": f"{e.reason} {det}"[:150]}
    except Exception as e:
        return {"status": None, "err": f"{type(e).__name__}: {str(e)[:100]}"}

ck = os.environ.get("CTAI_API_KEY", "")
cb = os.environ.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1").rstrip("/")
root = cb[:-3] if cb.endswith("/v1") else cb
show("CTAI /v1/models:", get(f"{cb}/models", ck))
show("CTAI root/models:", get(f"{root}/models", ck))
# try the chat path on a guessed small model; then try common names
for m in ["gpt-4o-mini", "claude-3-5-haiku-20241022", "deepseek-chat", "glm-4-flash"]:
    r = chat(f"{cb}/chat/completions", ck, m)
    print("CTAI chat", m, json.dumps(r))
    if r.get("status") == 200: break

cb2 = os.environ.get("CENT_AI_BASE_URL", "https://api.cent-ai.dev/v1").rstrip("/")
ck2 = os.environ.get("CENT_AI_API_KEY", "")
show("CENT /models:", get(f"{cb2}/models", ck2))

tb = os.environ.get("TOKENROUTER_BASE_URL", "")
print("TOKENROUTER_BASE_URL set:", bool(tb))
tk = os.environ.get("TOKENROUTER_API_KEY", "")
if tb:
    show("TOKENR /models:", get(f"{tb.rstrip('/')}/models", tk))
