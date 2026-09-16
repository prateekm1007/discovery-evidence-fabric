#!/usr/bin/env python3
"""R479 — the P0-5 transport probe, PRODUCTION leg (the HF router).

The committed r478 probe (scripts/r478_hf_transport_probe.py) measures
the atria ring; its CREDENTIAL_ABSENT record stands as the historical
R478 measurement. The audit's actual acceptance class, though, is the
HF-router 402: "HF inference dead (402): no strong-model provenance
chain live until top-up." This probe measures that leg NOW with the
operator-supplied credential, against the exact transport production
uses (ZAI_BASE_URL -> router.huggingface.co, ZAI_MODEL
zai-org/GLM-5.3).

Measured facts, each typed (Art. VI: real transport metadata only):
  1. CREDENTIAL  — the HF token from the env or the LXXIII vault;
     only the FINGERPRINT is recorded, never the value (BS-021).
  2. INFERENCE   — one tiny real completion through the router; the
     measured latency, the served model id, and usage are recorded.
  3. ARTIFACT    — the response bound into a probe record whose
     sha256 is computed here (credential -> inference -> artifact,
     hash checkable afterwards).

Exit codes / typed outcomes (Art. LXI — infrastructure states are
never scientific rejections):
  LEDGER_LINE_GREEN   — all three links measured and hash-bound.
  CREDENTIAL_ABSENT   — no token in env or vault (what_unblocks
                        printed; the operator decision is NOT made
                        for them, Art. LXV).
  TRANSPORT_DEGRADED  — a credential exists but the call failed
                        (HTTP status typed: 402 credits / 401 auth /
                        429 rate / other), detail recorded.

Usage: python3 scripts/r479_hf_router_probe.py [--out R479/PATH.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "zai-org/GLM-5.3"
ENDPOINT = "https://router.huggingface.co/v1/chat/completions"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def fingerprint(value: str) -> str:
    """BS-021: the token's fingerprint, never its value."""
    return ("fp_" + hashlib.sha256(value.encode()).hexdigest()[:12]
            + f"_len{len(value)}")


def find_token() -> tuple[str | None, str]:
    """Article LXXIII order, in-session steps only: env -> vault."""
    for name in ("HF_TOKEN", "ZAI_API_KEY", "HUGGINGFACE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    p = Path("/home/z/my-project/.secrets.env")
    if p.exists():
        vault = {}
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vault[k.strip()] = v.strip()
        for name in ("HF_TOKEN", "ZAI_API_KEY"):
            value = vault.get(name, "").strip()
            if value:
                return f"vault:{name}", value
    return None, ""


def infer(token: str, model: str) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "PROBE_OK"}],
        "max_tokens": 16,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
            latency = round(time.monotonic() - t0, 2)
            content = ((payload.get("choices") or [{}])[0].get("message")
                       or {}).get("content", "")
            return {"status": "OK", "latency_s": latency,
                    "served_model": payload.get("model", ""),
                    "content_preview": str(content)[:80],
                    "usage": payload.get("usage", {})}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode()[:300]
        except Exception:  # noqa: BLE001 — typed, never silent
            pass
        return {"status": f"HTTP_{exc.code}",
                "detail": f"{exc.reason}" + (f" | {detail}" if detail
                                             else ""),
                "latency_s": round(time.monotonic() - t0, 2)}
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        return {"status": "CALL_FAILED",
                "detail": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "R479"
                                         / "HF_ROUTER_PROBE.json"))
    ap.add_argument("--model", default=os.environ.get(
        "ZAI_MODEL", DEFAULT_MODEL))
    args = ap.parse_args()

    record: dict = {
        "probe": ("R479 P0-5 production-leg fresh ledger line "
                  "(credential -> inference -> artifact; the audit's "
                  "402 class measured NOW)"),
        "endpoint": ENDPOINT,
        "model_requested": args.model,
        "measured_at_utc": utc_now(),
        "audit_baseline": ("the audit's measured 402 class "
                           "(HF_ACCOUNT_CREDITS depleted); NOT "
                           "re-asserted — measured fresh here"),
    }
    name, token = find_token()
    if name is None:
        record.update({
            "outcome": "CREDENTIAL_ABSENT",
            "lookup_order": ("Article LXXIII: env (measured: none of "
                             "HF_TOKEN/ZAI_API_KEY/"
                             "HUGGINGFACE_API_KEY present) -> vault "
                             "(.secrets.env absent) -> operator (LAST,"
                             " escalated)"),
            "what_unblocks": ("one env injection (HF_TOKEN=...) or the "
                              "vault restored at the workspace root, "
                              "then re-run: python3 "
                              "scripts/r479_hf_router_probe.py"),
            "infrastructure_note": ("Art. LXI: an "
                                    "INCOMPLETE_INFRASTRUCTURE state, "
                                    "never a scientific verdict"),
        })
        print(json.dumps(record, indent=1))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(record, indent=1))
        return 2

    record["credential"] = {"source": name,
                            "fingerprint": fingerprint(token)}
    res = infer(token, args.model)
    record["inference"] = res
    if res.get("status") != "OK":
        record["outcome"] = "TRANSPORT_DEGRADED"
        record["what_unblocks"] = ("inspect inference.status/detail "
                                   "(402 = credits still depleted; "
                                   "401 = token lacks the inference "
                                   "scope; 429 = rate)")
        code = 3
    else:
        artifact = {
            "probe_id": f"r479_p05_{int(time.time())}",
            "credential_fingerprint": record["credential"]["fingerprint"],
            "served_model": res["served_model"],
            "latency_s": res["latency_s"],
            "content_preview": res["content_preview"],
            "usage": res.get("usage", {}),
            "measured_at_utc": utc_now(),
        }
        blob = json.dumps(artifact, sort_keys=True).encode()
        artifact["sha256"] = hashlib.sha256(blob).hexdigest()
        record["artifact"] = artifact
        record["outcome"] = "LEDGER_LINE_GREEN"
        code = 0
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
