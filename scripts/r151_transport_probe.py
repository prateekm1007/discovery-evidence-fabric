#!/usr/bin/env python3
"""R151 transport probe: which judge lanes are alive THIS window.

Probes (1 chat call each, tiny): xkiro (vault key + directions key), cent-ai
(paid models + hy4-flash:free), glm-free via cent-ai. Typed output only;
no secrets printed. Exit 0 always (the record is the output)."""
import json, os, time, urllib.request, urllib.error

def chat(base, key, model, prompt="Reply with exactly: OK", max_tokens=8):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
            txt = (d.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return {"alive": True, "http": r.status, "latency_s": round(time.time()-t0, 1),
                    "reply": str(txt)[:60]}
    except urllib.error.HTTPError as e:
        return {"alive": False, "http": e.code, "err": e.read().decode()[:120]}
    except Exception as e:
        return {"alive": False, "http": None, "err": str(e)[:120]}

def models(base, key):
    req = urllib.request.Request(base.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return [m.get("id") for m in json.loads(r.read()).get("data", [])]
    except Exception as e:
        return [f"ERR {getattr(e,'code',e)}"]

env = {k: os.environ.get(k, "") for k in
       ("XKIRO_API_KEY", "CENT_AI_API_KEY", "AGNES_API_KEY", "AGNES_BASE_URL")}
# the directions' dead key is read from the env (DIRS_XKIRO_KEY), never
# embedded — Art. 17 (vault env-only; the F45 lesson). Digest f473944703d5.
DIRS_XKIRO = os.environ.get("DIRS_XKIRO_KEY", "")
XK = "https://api.xkiro.com/v1"
CA = os.environ.get("CENT_AI_BASE_URL", "https://api.cent-ai.dev/v1")

out = {"xkiro_vault_key": {}, "xkiro_directions_key": {}, "cent_ai": {}, "glm_free": {}}

xk_models = models(XK, env["XKIRO_API_KEY"])
print("xkiro models visible:", len(xk_models) if not (xk_models and str(xk_models[0]).startswith("ERR")) else xk_models[0])
# probe 2 representative families on xkiro with the VAULT key first
for m in ("google/gemini-2.5-flash", "anthropic/claude-sonnet-4", "openai/gpt-5-mini", "x-ai/grok-4"):
    if xk_models and not str(xk_models[0]).startswith("ERR") and m not in xk_models and xk_models[0] != "ERR":
        # fall back to the first visible model of that family
        fam = [x for x in xk_models if m.split("/")[0] in x]
        if fam: m = fam[0]
        else: continue
    r = chat(XK, env["XKIRO_API_KEY"], m)
    out["xkiro_vault_key"][m] = r
    print("xkiro VAULT", m, "->", r)

# the directions' dead key, one model, for the typed record (env-only;
# skipped typed if not supplied)
if DIRS_XKIRO:
    r = chat(XK, DIRS_XKIRO, "google/gemini-2.5-flash")
    out["xkiro_directions_key"]["google/gemini-2.5-flash"] = r
    print("xkiro DIRKEY google/gemini-2.5-flash ->", r)
else:
    out["xkiro_directions_key"] = {"skipped": "DIRS_XKIRO_KEY not in env "
                                    "(typed; the 401 is already recorded in "
                                    "eval/r151s1_transport_escalation.json)"}

# cent-ai: paid lane + the free lane
for m in ("deepseek-v4-flash", "qwen3.8-flash", "hy4-flash:free", "glm-5.3-flash:free", "glm-5.3-flash"):
    r = chat(CA, env["CENT_AI_API_KEY"], m)
    out["cent_ai"][m] = r
    print("cent-ai", m, "->", r)

json.dump(out, open("eval/r151_transport_probe.json", "w"), indent=1)
print("\nwrote eval/r151_transport_probe.json")
