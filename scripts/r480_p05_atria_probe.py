#!/usr/bin/env python3
"""R480 — P0-5 closure probe: the atria ledger line, measured NOW.

The R479 round closed the deploy + identity-verify legs and measured
the HF-router leg TRANSPORT_DEGRADED (402 account billing). The
operator's answer this round: "repointing ZAI to a credited provider"
— the atria keys (the R470/R472 ring, re-supplied for this workspace).

This probe measures, BEFORE any Space rewiring (probe-before-wire,
Art. III — the same method the R467/R470/R472 registrations used):
  1. CATALOG    — GET /v1/models with key 1 -> 200 + the model list.
  2. CONTROL    — the format-identical bogus key -> 401 (auth
                  evaluates; proves the 200 is not a gate artifact,
                  the R463 method).
  3. INFERENCE  — the r478 probe contract (tiny real completion,
                  Atria-Dawn-Preview, max_tokens 16) -> the fresh
                  ledger line credential -> inference -> artifact,
                  sha256-bound. Reuses the committed r478 probe for
                  this link so the artifact contract is IDENTICAL.

Typed outcomes (Art. LXI):
  LEDGER_LINE_GREEN   — all links measured and hash-bound.
  TRANSPORT_DEGRADED  — a key exists but a link failed (typed detail).

Usage: python3 scripts/r480_p05_atria_probe.py [--out R480/PATH.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = "https://api.atria-asi.ai/v1/models"
BOGUS = "atr_" + "0" * 40  # format-identical, definitely invalid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def fingerprint(value: str) -> str:
    """BS-021: the key's fingerprint, never its value."""
    return ("fp_" + hashlib.sha256(value.encode()).hexdigest()[:12]
            + f"_len{len(value)}")


def vault_key() -> tuple[str | None, str]:
    """The atria ring from env (LXXIII step 1) or the vault."""
    for i in [""] + [f"_{n}" for n in range(2, 16)]:
        name = f"ATRIA_API_KEY{i}"
        v = os.environ.get(name, "").strip()
        if v:
            return f"env:{name}", v
    p = Path("/home/z/my-project/.secrets.env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "ATRIA_API_KEY" and v.strip():
                    return "vault:ATRIA_API_KEY", v.strip()
    return None, ""


def get_json(url: str, key: str) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {key}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return {"status": resp.status,
                    "latency_s": round(time.monotonic() - t0, 2),
                    "body": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code,
                "latency_s": round(time.monotonic() - t0, 2),
                "detail": exc.reason}
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        return {"status": "CALL_FAILED",
                "detail": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "R480"
                                         / "ATRIA_LEDGER_LINE.json"))
    args = ap.parse_args()

    record: dict = {
        "probe": ("R480 P0-5 closure: the atria ledger line "
                  "(credential -> catalog -> control -> inference -> "
                  "artifact), probe-before-wire"),
        "measured_at_utc": utc_now(),
        "operator_directive": ("repointing ZAI to a credited provider "
                               "(api.atria-asi.ai/console/keys) — the "
                               "operator-supplied atria key set, "
                               "re-supplied this round"),
        "ring_history": ("the R470/R472 registration: 15 keys, slot 8 "
                         "EXCLUDED by its measured INVALID verdict "
                         "(deterministic 401 x3, flapping disclosed); "
                         "this probe re-measures key 1 fresh"),
    }
    src, key = vault_key()
    if src is None:
        record.update({"outcome": "CREDENTIAL_ABSENT",
                       "what_unblocks": ("one env injection "
                                         "(ATRIA_API_KEY=...) or the "
                                         "vault restored")})
        print(json.dumps(record, indent=1))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(record, indent=1))
        return 2

    record["credential"] = {"source": src, "fingerprint": fingerprint(key)}

    cat = get_json(CATALOG, key)
    models = [m.get("id") for m in (cat.get("body") or {}).get("data", [])]
    record["catalog"] = {"status": cat["status"],
                         "latency_s": cat.get("latency_s"),
                         "models": models}
    ctrl = get_json(CATALOG, BOGUS)
    record["bogus_key_control"] = {"status": ctrl["status"],
                                   "latency_s": ctrl.get("latency_s")}

    # the inference link: the committed r478 probe contract, reused
    # verbatim so the artifact is byte-compatible with the R478 line
    env = dict(os.environ, ATRIA_API_KEY=key)
    out = Path(args.out)
    probe = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "r478_hf_transport_probe.py"),
         "--out", str(out)], env=env, capture_output=True, text=True,
        timeout=300)
    try:
        line = json.loads(out.read_text())
    except Exception:  # noqa: BLE001 — typed, never silent
        line = {"outcome": "PROBE_SCRIPT_ERROR",
                "detail": probe.stdout[-400:] + probe.stderr[-400:]}
    record["inference_ledger_line"] = {
        "via": "scripts/r478_hf_transport_probe.py (the committed "
               "P0-5 contract, reused verbatim)",
        "outcome": line.get("outcome"),
        "inference": line.get("inference"),
        "artifact_sha256": (line.get("artifact") or {}).get("sha256"),
    }

    ok = (cat.get("status") == 200 and models
          and ctrl.get("status") == 401
          and line.get("outcome") == "LEDGER_LINE_GREEN")
    record["outcome"] = "LEDGER_LINE_GREEN" if ok else "TRANSPORT_DEGRADED"
    if not ok:
        record["what_unblocks"] = ("inspect the typed sub-outcomes: "
                                   "catalog/bogus-control/inference — "
                                   "an auth-class failure on key 1 "
                                   "rotates the ring, an "
                                   "exhaustion-class failure is the "
                                   "operator's billing action")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
