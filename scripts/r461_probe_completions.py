#!/usr/bin/env python3
"""R461 phase 2 — admission-grade probes: a tiny completion through each
provider's REAL transport (the R451-C1.2 discipline: catalog presence is
never admission evidence). Records the bynara telegram_required 403
failure specimen AND its post-owner-action resolution (the key valid,
telegram joined — the Art. LXV escalation answered), plus the newly
measured free rungs on the standing quartet.

Keys from ENV ONLY (BS-021). Artifacts record measurements, never keys.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/131.0.0.0 Safari/537.36")

# (provider, base, ua, models to probe)
ARMS = [
    ("unorouter", "https://api.unorouter.com/v1", "plain",
     ["glm-5.3:free", "glm-5.3-thinking:free", "qwen3.8-27b:free"]),
    ("xkiro", "https://xkiro.com/v1", "chrome",
     ["qwen/qwen3.8-max:free", "minimax/minimax-m3:free",
      "qwen/qwen3.5-plus:free"]),
    ("apinex", "https://apinex.bond/v1", "chrome",
     ["free/deepseek-v4.1-flash", "free/deepseek-v4-pro-0813",
      "free/glm-5.3-flash"]),
    ("bai", "https://api.b.ai/v1", "plain",
     ["qwen3.8-flash", "mimo-v2.5"]),
    # R461: bynara's REAL -free family (the catalog measured 2026-09-15,
    # post-telegram-join; the prior session's deepseek-v4.1-flash:free
    # guess was not in the served catalog)
    ("bynara", "https://router.bynara.id/v1", "plain",
     ["glm-5.3-free", "qwen3.8-flash-free", "mimo-v2.5-free",
      "muse-spark-1.3-contributor-free", "tencent-hy3-free"]),
]


def _chat(base, key, ua, model, timeout=60):
    payload = {
        "model": model,
        "messages": [{"role": "user",
                      "content": "Reply with exactly: PROBE_OK"}],
        "max_tokens": 4096,
        "temperature": 0.0,
    }
    r = urllib.request.Request(
        f"{base}/chat/completions", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": ua})
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8", "replace"))
            dt = time.time() - t0
            ch = (raw.get("choices") or [{}])[0]
            msg = ch.get("message") or {}
            content = msg.get("content")
            reasoning = msg.get("reasoning_content")
            usage = raw.get("usage") or {}
            return {"status": resp.status, "latency_s": round(dt, 2),
                    "finish_reason": ch.get("finish_reason"),
                    "content_preview": (content or "")[:80],
                    "content_null": content is None,
                    "reasoning_tokens": (usage.get("completion_tokens_details")
                                         or {}).get("reasoning_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "verdict": "PROBE_OK" if content and "PROBE_OK" in content
                    else ("EMPTY_CONTENT" if content is None else "CONTENT")}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        return {"status": e.code, "latency_s": round(time.time() - t0, 2),
                "error_body": body, "verdict": f"HTTP_{e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "latency_s": round(time.time() - t0, 2),
                "error": repr(e)[:200], "verdict": "TRANSPORT_ERROR"}


def main() -> int:
    results = {}
    for pid, base, ua_kind, models in ARMS:
        key = os.environ.get(f"{pid.upper()}_API_KEY", "").strip()
        ua = CHROME_UA if ua_kind == "chrome" else "Python-urllib/3.11"
        print(f"\n=== {pid} @ {base} [{ua_kind} UA] ===")
        results[pid] = {}
        if not key:
            print("  KEY UNSET — skipped")
            results[pid]["_key_present"] = False
            continue
        results[pid]["_key_present"] = True
        for model in models:
            rec = _chat(base, key, ua, model)
            results[pid][model] = rec
            print(f"  {model:38s} -> {rec.get('verdict'):14s} "
                  f"{rec.get('latency_s')}s "
                  f"status={rec.get('status')} "
                  + (f"tokens={rec.get('completion_tokens')} "
                     f"reasoning={rec.get('reasoning_tokens')}"
                     if rec.get("verdict") in ("PROBE_OK", "CONTENT",
                                               "EMPTY_CONTENT")
                     else f"body={str(rec.get('error_body'))[:150]!r}"))
    path = os.path.join(os.path.dirname(__file__), "..", "R461")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "PROBE_COMPLETIONS.json"), "w") as f:
        json.dump({"round": "R461", "measured_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arms": results},
            f, indent=2)
    print("\ncompletion probe artifacts -> R461/PROBE_COMPLETIONS.json")
    n_ok = sum(1 for p in results.values()
               for m, r in p.items()
               if isinstance(r, dict) and r.get("verdict") == "PROBE_OK")
    print(f"measured PROBE_OK completions: {n_ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
