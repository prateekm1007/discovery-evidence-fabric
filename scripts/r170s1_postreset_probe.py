#!/usr/bin/env python3
"""r170s1_postreset_probe.py — typed post-reset infra census (ZERO corpus
burn; minimal non-corpus probes only, max_tokens<=8).

Probes (one run, one probe each):
  1. XKIRO  GET /v1/models       — catalog census (aya32b? mistral back?)
  2. XKIRO  1 completion probe   — free-pool state (live / rate_limited / auth)
  3. CTAI   GET /v1/models       — cantrustai catalog (judge-capable families?)
  4. CTAI   1 completion probe   — auth + liveness (owner's new judge transport)
  5. CENT   GET /v1/models       — G0-adjacent catalog + hy4-flash:free presence
  6. CENT   1 completion probe   — the J2 seat state (200 vs 503)
  7. TOKENR GET /v1/models       — the G0 generator seat (200 alive)

Output: typed JSON to stdout (statuses, counts, families; NEVER key bytes).
Exit 0 always (the caller interprets).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PROBE_PROMPT = "Reply with exactly: OK"


def load_env() -> None:
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read().decode("utf-8"))
            return {"status": r.status, "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "err": str(e.reason)[:60]}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "err": f"{type(e).__name__}: {str(e)[:80]}"}


def chat(url: str, key: str, model: str, max_tokens: int = 8) -> dict:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROBE_PROMPT}],
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))
            content = ""
            try:
                content = (body.get("choices") or [{}])[0].get(
                    "message", {}).get("content", "") or ""
            except Exception:  # noqa: BLE001
                pass
            return {"status": r.status, "content_head": content.strip()[:40]}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:120]
        except Exception:  # noqa: BLE001
            pass
        return {"status": e.code, "err": f"{e.reason} {detail}"[:120]}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "err": f"{type(e).__name__}: {str(e)[:80]}"}


def fams(models: list) -> dict:
    fam: dict[str, int] = {}
    for m in models:
        mid = m.get("id", "") if isinstance(m, dict) else str(m)
        head = mid.split("/")[0].split("-")[0].lower()
        fam[head] = fam.get(head, 0) + 1
    return dict(sorted(fam.items(), key=lambda kv: -kv[1])[:12])


def main() -> int:
    load_env()
    out: dict = {"probe": "r170s1_postreset_probe/1.0.0",
                 "at_utc": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip()}

    xk = os.environ.get("XKIRO_API_KEY", "")
    xb = os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1").rstrip("/")
    r = get(f"{xb}/models", xk)
    models = (r.get("body") or {}).get("data") or []
    mids = [m.get("id", "") for m in models if isinstance(m, dict)]
    out["xkiro_models"] = {"status": r.get("status"), "count": len(mids),
                           "families": fams(models),
                           "aya32b": [m for m in mids if "aya" in m.lower()][:5],
                           "mistral": [m for m in mids if "mistral" in m.lower()
                                       or "ministral" in m.lower()][:5],
                           "sensenova": [m for m in mids if
                                         "sensenova" in m.lower()][:3]}
    if mids:
        probe_model = ("sensenova/sensenova-6.8-flash-lite"
                       if any("6.8-flash-lite" in m for m in mids) else mids[0])
        out["xkiro_pool_probe"] = chat(f"{xb}/chat/completions", xk,
                                       probe_model, max_tokens=8)
        out["xkiro_pool_probe"]["model"] = probe_model

    cb = os.environ.get("CTAI_BASE_URL", "https://api.cantrustai.xyz/v1").rstrip("/")
    ck = os.environ.get("CTAI_API_KEY", "")
    r = get(f"{cb}/models", ck)
    models = (r.get("body") or {}).get("data") or []
    mids = [m.get("id", "") for m in models if isinstance(m, dict)]
    out["ctai_models"] = {"status": r.get("status"), "count": len(mids),
                          "families": fams(models), "ids_sample": mids[:40]}
    if mids:
        pick = next((m for m in mids if "flash" in m.lower() or "mini" in m.lower()
                     or "small" in m.lower()), mids[0])
        out["ctai_probe"] = chat(f"{cb}/chat/completions", ck, pick, max_tokens=8)
        out["ctai_probe"]["model"] = pick

    cb2 = os.environ.get("CENT_AI_BASE_URL",
                         "https://api.cent-ai.dev/v1").rstrip("/")
    ck2 = os.environ.get("CENT_AI_API_KEY", "")
    r = get(f"{cb2}/models", ck2)
    models = (r.get("body") or {}).get("data") or []
    mids = [m.get("id", "") for m in models if isinstance(m, dict)]
    out["cent_models"] = {"status": r.get("status"), "count": len(mids),
                          "hy4_free": [m for m in mids if "hy4" in m.lower()][:5]}
    hy4 = next((m for m in mids if "hy4" in m.lower()), None)
    if hy4:
        out["cent_j2_probe"] = chat(f"{cb2}/chat/completions", ck2, hy4,
                                    max_tokens=8)
        out["cent_j2_probe"]["model"] = hy4

    tb = os.environ.get("TOKENROUTER_BASE_URL",
                        "https://api.tokenrouter.ai/v1").rstrip("/")
    tk = os.environ.get("TOKENROUTER_API_KEY", "")
    r = get(f"{tb}/models", tk)
    models = (r.get("body") or {}).get("data") or []
    out["tokenrouter_g0"] = {"status": r.get("status"),
                             "count": len(models) if isinstance(models, list)
                             else None}

    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
