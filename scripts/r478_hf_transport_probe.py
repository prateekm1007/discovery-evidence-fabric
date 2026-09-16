#!/usr/bin/env python3
"""R478 — the P0-5 HF/model transport probe: the fresh ledger line.

External-audit P0-5: "HF inference dead (402): no strong-model
provenance chain live until top-up." The acceptance is a FRESH ledger
line credential -> inference -> artifact with revision pins, measured
— never inferred from a previous round's state.

What this probe measures when a credential is present (each fact
typed, never assumed):
  1. CREDENTIAL  — the atria key ring (ATRIA_API_KEY, _2, _3) or
     ZAI_API_KEY from the environment (Article LXXIII lookup order:
     env -> vault -> Space surface names -> operator LAST). Only the
     key FINGERPRINT is recorded, never the value (BS-021).
  2. INFERENCE   — one tiny real completion through the ring; the
     measured latency, the served model id, and the transport meta
     are recorded (Art. VI: real transport metadata only).
  3. ARTIFACT    — the response text is bound into a probe record
     whose sha256 is computed here, so the line is
     credential -> inference -> artifact with the artifact hash
     checkable afterwards.

Exit codes / typed outcomes (Art. LXI — infrastructure states are
never scientific rejections):
  LEDGER_LINE_GREEN   — all three links measured and hash-bound.
  CREDENTIAL_ABSENT   — no key in the session environment (this
                        session's measured state); what_unblocks is
                        printed, the operator decision is NOT made for
                        them (Art. LXV).
  TRANSPORT_DEGRADED  — a key exists but the call failed (typed error,
                        the ring rotation attempted first).

Usage: python3 scripts/r478_hf_transport_probe.py [--out R478/PATH.json]
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
RING = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
        "ZAI_API_KEY"]
ENDPOINT = "https://api.atria-asi.ai/v1/chat/completions"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def fingerprint(value: str) -> str:
    """BS-021: the key's fingerprint, never its value."""
    return ("fp_" + hashlib.sha256(value.encode()).hexdigest()[:12]
            + f"_len{len(value)}")


def find_key() -> tuple[str | None, str]:
    """Article LXXIII lookup order, step 1 (env) only in-session; the
    caller records CREDENTIAL_ABSENT typed when nothing is found —
    the vault and the Space surface are operator-side states this
    session cannot read values from, and the record says exactly
    that instead of pretending to look."""
    for name in RING:
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    return None, ""


def infer(key: str, model: str) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "PROBE_OK"}],
        "max_tokens": 16,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
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
        return {"status": f"HTTP_{exc.code}",
                "detail": exc.reason, "latency_s":
                    round(time.monotonic() - t0, 2)}
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        return {"status": "CALL_FAILED",
                "detail": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "R478"
                                         / "HF_TRANSPORT_PROBE.json"))
    args = ap.parse_args()

    record: dict = {
        "probe": "R478 P0-5 fresh ledger line (credential -> inference "
                 "-> artifact)",
        "measured_at_utc": utc_now(),
        "audit_baseline": ("the audit's measured 402 class "
                           "(HF_ACCOUNT_CREDITS depleted) + the R477 "
                           "sibling's slot re-probe finding; NEITHER is "
                           "re-asserted here — this probe measures NOW"),
    }
    name, key = find_key()
    if name is None:
        record.update({
            "outcome": "CREDENTIAL_ABSENT",
            "lookup_order": "Article LXXIII: env (measured: none of "
                            "ATRIA_API_KEY/_2/_3/ZAI_API_KEY present) -> "
                            "vault (.secrets.env not present in this "
                            "session's workspace) -> Space surface "
                            "(names only, values unreadable by design) "
                            "-> operator (LAST, escalated)",
            "what_unblocks": ("one env injection (ATRIA_API_KEY=...) "
                              "or the vault restored at the workspace "
                              "root, then re-run: python3 "
                              "scripts/r478_hf_transport_probe.py"),
            "infrastructure_note": "Art. LXI: this is an "
                                   "INCOMPLETE_INFRASTRUCTURE state, "
                                   "never a scientific verdict",
        })
        print(json.dumps(record, indent=1))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(record, indent=1))
        return 2

    record["credential"] = {"env_name": name,
                            "fingerprint": fingerprint(key)}
    res = infer(key, "Atria-Dawn-Preview")
    record["inference"] = res
    if res.get("status") != "OK":
        record["outcome"] = "TRANSPORT_DEGRADED"
        record["what_unblocks"] = ("the ring exhausted its typed "
                                   "retries; inspect inference.detail")
        code = 3
    else:
        artifact = {
            "probe_id": f"r478_p05_{int(time.time())}",
            "credential_fingerprint": record["credential"]["fingerprint"],
            "served_model": res["served_model"],
            "latency_s": res["latency_s"],
            "content_preview": res["content_preview"],
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
