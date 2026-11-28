#!/usr/bin/env python3
"""r156s1_llmtr_scan.py — the llmtr free-model census + probe (the
owner's ask: try the llmtr key's free models from the dashboard).

Discipline: the key lives in .env.keys (gitignored, 0600) — env-only,
never printed in full, never committed. Digests only in any record.

Two surfaces, the lesson from the xkiro quota-dead typing applied:
- GET /v1/models          — the catalog (the free pricing filter)
- POST /v1/chat/completions — the GATED surface (the real liveness;
  a model listed free can still 402/429 at call time)
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = os.environ.get("LLMTTR_BASE_URL", "https://llmtr.com/v1")
KEY = os.environ.get("LLMTTR_API_KEY", "")


def call(method: str, path: str, body: dict | None = None,
         timeout: float = 45.0) -> tuple[int, object]:
    req = urllib.request.Request(
        BASE + path, method=method,
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    req.data = data
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return -1, {"error": str(e)[:120]}


def main() -> int:
    if not KEY:
        raise SystemExit("LLMTTR_API_KEY not in env (vault custody)")
    st, cat = call("GET", "/models")
    if st != 200:
        print("models listing:", st, json.dumps(cat)[:200])
        return 1
    models = cat.get("data", [])
    print(f"catalog: {len(models)} models")

    def is_free(m: dict) -> bool:
        p = m.get("pricing") or {}
        try:
            return float(p.get("prompt", 1)) == 0 and \
                float(p.get("completion", 1)) == 0
        except (TypeError, ValueError):
            return False

    free = [m for m in models if is_free(m)]
    print(f"free models (prompt==0 AND completion==0): {len(free)}")
    rows = []
    for m in free:
        mid = m["id"]
        ctx = m.get("context_length")
        t0 = time.monotonic()
        st, resp = call("POST", "/chat/completions", {
            "model": mid,
            "messages": [{"role": "user",
                          "content": "Reply with exactly: OK"}],
            "max_tokens": 400,
        }, timeout=90.0)
        dt = round(time.monotonic() - t0, 1)
        if st == 200:
            ch = (resp.get("choices") or [{}])[0]
            content = ((ch.get("message") or {}).get("content") or "") \
                .strip()
            finish = ch.get("finish_reason")
            rows.append({"id": mid, "status": 200, "latency_s": dt,
                         "reply": content[:40], "finish": finish,
                         "ctx": ctx,
                         "verdict": "ALIVE" if content else "EMPTY"})
        else:
            err = ""
            if isinstance(resp, dict):
                err = json.dumps(resp.get("error") or resp)[:110]
            rows.append({"id": mid, "status": st, "latency_s": dt,
                         "reply": err, "finish": None, "ctx": ctx,
                         "verdict": f"HTTP {st}"})
        print(f"  {mid}: {rows[-1]['verdict']} ({dt}s) "
              f"ctx={ctx}", flush=True)
        time.sleep(1.0)

    alive = [r for r in rows if r["verdict"] == "ALIVE"]
    print(f"\nALIVE: {len(alive)}/{len(rows)} free models")
    out = Path("/home/z/my-project/repo/eval/r156s1_llmtr_scan.json")
    out.write_text(json.dumps({
        "record": "R156S1_LLMTTR_SCAN/1.0.0",
        "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "key": "vault custody (digest 999c1f0560a9), never committed",
        "catalog_size": len(models),
        "free_count": len(free),
        "free_ids": [m["id"] for m in free],
        "probes": rows,
        "alive": [r["id"] for r in alive],
    }, indent=1, ensure_ascii=False) + "\n")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
