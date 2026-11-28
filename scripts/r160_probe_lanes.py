#!/usr/bin/env python3
"""r160: post-reset lane probes (Art. 3 probe-before-legs; ONE cheap call per lane).
Typed outcomes only — no key values ever printed."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")

PROBE_MESSAGES = [{"role": "user", "content": "Reply with the single word OK"}]


def _post_json(url: str, key: str, payload: dict, ua: str,
               timeout: float = 90.0) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}",
                 "User-Agent": ua}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
            content = ""
            try:
                content = (body["choices"][0]["message"].get("content")
                           or "")[:60]
            except (KeyError, IndexError, TypeError):
                content = "<unparsed-shape>"
            return {"http": resp.status, "ok": True, "content": content}
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:160]
        except Exception:  # noqa: BLE001
            detail = "<no-body>"
        return {"http": e.code, "ok": False, "error": detail}
    except Exception as e:  # noqa: BLE001 — typed degradation
        return {"http": None, "ok": False,
                "error": f"{type(e).__name__}: {str(e)[:160]}"}


def probe_xkiro() -> dict:
    from discovery_fabric.engine.route_adapter import xkiro_chat
    key_present = True
    r = xkiro_chat(PROBE_MESSAGES, model="sensenova/sensenova-6.8-flash-lite",
                   max_tokens=16, timeout_s=120.0)
    out = {"lane": "xkiro/snlite (panel judge transport)",
           "vault_key": "present" if key_present else "absent"}
    if r.get("content"):
        out["outcome"] = "VALID"
        out["served"] = r.get("served_model") or r.get("served") or "n/a"
        out["preview"] = (r.get("content") or "")[:40]
    else:
        err = str(r.get("error") or "")
        out["outcome"] = ("RATE_LIMITED" if ("429" in err or "quota" in err.lower())
                          else "AUTH_DEAD" if ("401" in err or "403" in err)
                          else "TRANSPORT_FAILED")
        out["error_head"] = err[:160]
    return out


def probe_cent() -> dict:
    from discovery_fabric.engine.route_adapter import cent_ai_chat
    r = cent_ai_chat(PROBE_MESSAGES, model="hy4-flash:free", max_tokens=16,
                     timeout_s=120.0)
    out = {"lane": "cent-ai/hy4-flash:free (hy4f judge transport)"}
    if r.get("content"):
        out["outcome"] = "VALID"
        out["preview"] = (r.get("content") or "")[:40]
    else:
        err = str(r.get("error") or "")
        out["outcome"] = ("RATE_LIMITED" if "429" in err
                          else "AUTH_DEAD" if ("401" in err or "402" in err or "403" in err)
                          else "TRANSPORT_FAILED")
        out["error_head"] = err[:160]
    return out


def probe_tokenrouter() -> dict:
    key = os.environ.get("TOKENROUTER_API_KEY", "")
    out = {"lane": "tokenrouter/deepseek-v4.1-flash (P5 G0/T2 lane)",
           "key": "env-present" if key else "MISSING"}
    if not key:
        out["outcome"] = "KEY_MISSING"
        return out
    r = _post_json(
        "https://api.tokenrouter.com/v1/chat/completions", key,
        {"model": "deepseek/deepseek-v4.1-flash-1017-free",
         "messages": PROBE_MESSAGES, "max_tokens": 8},
        ua="r160-probe/1.0")
    if r.get("ok"):
        out["outcome"] = "VALID"
        out["preview"] = r.get("content", "")
    else:
        out["outcome"] = ("RATE_LIMITED" if r.get("http") == 429
                          else "AUTH_DEAD" if r.get("http") in (401, 403)
                          else "TRANSPORT_FAILED")
        out["http"] = r.get("http")
        out["error_head"] = str(r.get("error"))[:160]
    return out


def probe_hf() -> dict:
    key = os.environ.get("HF_TOKEN", "")
    out = {"lane": "huggingface whoami-v2 (master token)", }
    if not key:
        out["outcome"] = "KEY_MISSING"
        return out
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "r160-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
            out["outcome"] = "VALID"
            out["login"] = body.get("name", "?")
    except urllib.error.HTTPError as e:
        out["outcome"] = "AUTH_DEAD" if e.code in (401, 403) else f"HTTP_{e.code}"
    except Exception as e:  # noqa: BLE001
        out["outcome"] = f"TRANSPORT_FAILED: {type(e).__name__}"
    return out


def main() -> int:
    results = {}
    for name, fn in (("xkiro", probe_xkiro), ("cent", probe_cent),
                     ("tokenrouter", probe_tokenrouter), ("hf", probe_hf)):
        try:
            results[name] = fn()
        except Exception as e:  # noqa: BLE001 — typed degradation
            results[name] = {"outcome": f"PROBE_CRASHED: {type(e).__name__}: {str(e)[:120]}"}
        print(json.dumps(results[name], ensure_ascii=False))
    verdict = {k: v.get("outcome") for k, v in results.items()}
    print("VERDICT:", json.dumps(verdict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
