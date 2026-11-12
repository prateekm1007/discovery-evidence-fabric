#!/usr/bin/env python3
"""R6 B-protocol provider-key probe (owner round 2026-11-12).

Probes the three .env.keys provider keys with a TINY live completion
(64-token cap — the registry's probe_max_tokens class, not a
generation): AGNES (apihub.agnes-ai.com, agnes-3.0-flash), INCEPTION
(api.inceptionlabs.ai, mercury-3), OPENROUTER (openrouter.ai, the
frozen synthesis model class deepseek/deepseek-v4-flash-0731 —
measured 401 last round, re-probed per the owner directive "must be
re-probed").

Output: JSON on stdout with per-provider {status, latency_ms,
content_chars, typed} — NO key material, NO prompt content (Art. VI:
real values only; the keys never leave .env.keys / the process
environment). Exit code 0 always (the probe itself cannot fail
hard); the JSON is the deliverable.

Usage: python scripts/r6_probe_provider_keys.py
       (optionally --out <path> to also write the JSON to a file)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TARGETS = [
    ("agnes", "AGNES_API_KEY",
     "https://apihub.agnes-ai.com/v1/chat/completions",
     "agnes-3.0-flash"),
    ("inception", "INCEPTION_API_KEY",
     "https://api.inceptionlabs.ai/v1/chat/completions",
     "mercury-3"),
    ("openrouter", "OPENROUTER_API_KEY",
     "https://openrouter.ai/api/v1/chat/completions",
     "deepseek/deepseek-v4-flash-0731"),
]

PROMPT = ("Reply with exactly one line: R6-PROBE-OK <three digits "
          "chosen by you>. No other text.")


def _load_keys() -> dict:
    keys = {}
    env = REPO / ".env.keys"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip().strip('"').strip("'")
    for k in (k for k in keys):
        os.environ.setdefault(k, keys[k])
    return {name: (os.environ.get(envvar, "").strip()
                   or keys.get(envvar, ""))
            for name, envvar, _, _ in TARGETS}


def _classify(status: int, body: str) -> str:
    if status == 200:
        return "ALIVE"
    if status in (401, 403):
        return "AUTH_OR_GATE_" + ("EXHAUSTED" if (
            "quota" in body.lower() or "credit" in body.lower()
            or "insufficient" in body.lower()) else "FAILURE")
    if status == 402:
        return "CREDIT_EXHAUSTED"
    if status == 429:
        return "RATE_LIMITED"
    if status == 404:
        return "MODEL_OR_ROUTE_404"
    return f"HTTP_{status}"


def _probe(name: str, key: str, url: str, model: str,
           extra_headers: dict) -> dict:
    row = {"provider": name, "model": model, "url": url}
    if not key:
        row.update(status=None, typed="KEY_ABSENT", latency_ms=None,
                   content_chars=0)
        return row
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 64, "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    for hk, hv in extra_headers.items():
        req.add_header(hk, hv)
    t0 = time.perf_counter()
    status = None
    text = ""
    err = ""
    try:
        with urllib.request.urlopen(req, timeout=60,
                                    context=ssl.create_default_context()
                                    ) as r:
            status = r.status
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            text = e.read().decode("utf-8", "replace")[:400]
        except Exception:  # noqa: BLE001
            text = ""
    except Exception as e:  # noqa: BLE001 — typed, not silent
        err = f"{type(e).__name__}: {e}"
    latency_ms = int((time.perf_counter() - t0) * 1000)
    content_chars = 0
    finish = ""
    if status == 200 and text:
        try:
            d = json.loads(text)
            c = (d.get("choices") or [{}])[0].get("message", {})
            content_chars = len(c.get("content") or "")
            finish = c.get("finish_reason") or ""
        except Exception:  # noqa: BLE001
            err = "unparseable-200"
    row.update(status=status, latency_ms=latency_ms,
               content_chars=content_chars,
               finish_reason=finish or None,
               error=(err or text[:200]) if err or (
                   status not in (None, 200)) else None,
               typed=_classify(status, text) if status is not None
               else "NETWORK_" + (err.split(":")[0]
                                  if err else "UNKNOWN"))
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    keys = _load_keys()
    rows = []
    for name, envvar, url, model in TARGETS:
        headers = {}
        if name == "openrouter":
            # the registry's recorded openrouter transport requires the
            # attribution headers on some routes (transport plumbing)
            headers["HTTP-Referer"] = "discovery-evidence-fabric"
            headers["X-Title"] = "discovery-evidence-fabric"
        rows.append(_probe(name, keys.get(name, ""), url, model,
                           headers))
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    out = {
        "instrument": "provider_key_probe/1.0 (R6 B-protocol, owner "
                      "2026-11-12)",
        "note": ("tiny 64-token completion per key; NO key material "
                 "recorded; openrouter re-probe (measured 401 last "
                 "round; the owner's fresh key may be a replacement)"),
        "results": rows,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1,
                                              ensure_ascii=False),
                                  encoding="utf-8")
        print("wrote", args.out)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
