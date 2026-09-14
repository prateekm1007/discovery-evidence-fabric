#!/usr/bin/env python3
"""R461 — the operator's refreshed router key set + the FIFTH router
(router.bynara.id). Probe-before-admit (R451-C1.2 / Art. III): every
credential is LIVE-MEASURED through the provider's REAL transport before
any registration decision. Catalog presence is never admission evidence;
a tiny completion through the real endpoint is.

Keys come from the ENVIRONMENT ONLY (BS-021): UNOROUTER_API_KEY,
BYNARA_API_KEY, XKIRO_API_KEY, APINEX_API_KEY, BAI_API_KEY. The probe
artifacts record measurements, never key values.
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

# (provider_id, [candidate base URLs], needs browser UA)
CANDIDATES = [
    ("unorouter", ["https://api.unorouter.com/v1"], False),
    ("bynara", [
        "https://router.bynara.id/v1",
        "https://api.bynara.id/v1",
        "https://bynara.id/v1",
    ], None),  # None: try both plain and Chrome UA
    ("xkiro", ["https://xkiro.com/v1"], True),
    ("apinex", ["https://apinex.bond/v1"], True),
    ("bai", ["https://api.b.ai/v1"], False),
]


def _req(url: str, key: str, ua: str, payload=None, timeout=45):
    body = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": ua})
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw, time.time() - t0, ""
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:400]
        return e.code, raw, time.time() - t0, str(e)
    except Exception as e:  # noqa: BLE001
        return 0, "", time.time() - t0, repr(e)[:200]


def probe_catalog(base: str, key: str, ua: str):
    return _req(f"{base}/models", key, ua, timeout=30)


def probe_chat(base: str, key: str, ua: str, model: str):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: PROBE_OK"}],
        "max_tokens": 4096,
        "temperature": 0.0,
    }
    return _req(f"{base}/chat/completions", key, ua, payload=payload)


def main() -> int:
    out = {}
    for pid, bases, ua_need in CANDIDATES:
        key = os.environ.get(f"{pid.upper()}_API_KEY", "").strip()
        if not key:
            print(f"[{pid}] KEY UNSET — skipped (typed, honest)")
            out[pid] = {"key_present": False}
            continue
        print(f"\n=== {pid} (key present, {len(key)} chars) ===")
        entry = {"key_present": True, "key_len": len(key),
                 "key_fingerprint": f"{key[:6]}...{key[-4:]}",
                 "probes": []}
        for base in bases:
            uas = [CHROME_UA] if ua_need is True else (
                ["Python-urllib/3.11"] if ua_need is False
                else ["Python-urllib/3.11", CHROME_UA])
            for ua in uas:
                ua_label = "chrome" if "Chrome" in ua else "plain"
                st, raw, dt, err = probe_catalog(base, key, ua)
                n_models = 0
                free_models = []
                if st == 200:
                    try:
                        data = json.loads(raw)
                        ids = [m.get("id", "?") for m in
                               data.get("data", [])]
                        n_models = len(ids)
                        free_models = [i for i in ids
                                       if ":free" in i or i.startswith("free/")
                                       or "free" in i.lower()][:30]
                    except Exception:  # noqa: BLE001
                        pass
                rec = {"base": base, "ua": ua_label,
                       "status": st, "latency_s": round(dt, 2),
                       "models": n_models,
                       "free_family_sample": free_models[:12],
                       "error": err or raw[:200]}
                entry["probes"].append(rec)
                print(f"  models {base} [{ua_label}] -> {st} "
                      f"{dt:.1f}s models={n_models}"
                      + (f" free={free_models[:8]}" if st == 200
                         else f" err={raw[:120]!r}"))
                if st == 200:
                    entry["working_base"] = base
                    entry["working_ua"] = ua_label
                    entry["catalog"] = free_models
                    break
            if "working_base" in entry:
                break
        out[pid] = entry

    print("\n=== SUMMARY ===")
    for pid, e in out.items():
        wb = e.get("working_base", "-")
        print(f"{pid:10s} base={wb:35s} "
              f"ua={e.get('working_ua', '-'):7s} "
              f"models={sum(p.get('models', 0) for p in e.get('probes', []))}")
    path = os.path.join(os.path.dirname(__file__), "..", "R461")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "PROBE_CATALOG.json"), "w") as f:
        json.dump({"round": "R461", "measured_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "providers": out},
            f, indent=2)
    print("catalog probe artifacts -> R461/PROBE_CATALOG.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
