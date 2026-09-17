#!/usr/bin/env python3
"""scripts/r504_hf_auth_probe.py — R504 measure-before-integration probes.

The operator directive (2026-09-18): "deploy 2.8.0 + the sealed instruments,
which also re-enables the R502 seal with HF_TOKEN authenticated quota."

Before ANY integration of HF_TOKEN authenticated access into the free
evidence legs (Art. LXXV: source properties are MEASURED states, never
assumed; R500 discipline: measure every source before integration), this
probe measures the HF datasets-server in BOTH modes, per endpoint:

  pass 1  whoami (credential liveness — R503 verification precedent)
  pass 2  /splits   keyless vs authenticated
  pass 3  /rows     keyless vs authenticated
  pass 4  /search   keyless vs authenticated
          (the R500 deferred verification: "HF /search free retry after
           the provider's own warming window" — R499/R500 measured the
           500 INDEX_WARMING_TRANSIENT; this pass re-measures it)
  pass 5  response-header capture (any quota/rate-limit headers the
          provider serves, both modes)

Values are never printed (BS-021); the token is read from the local Art.
LXXIII vault and referenced by fingerprint only. Ledger:
R504/R504_HF_AUTH_PROBE.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R504" / "R504_HF_AUTH_PROBE.json"

VAULT = Path("/home/z/my-project/.secrets.env")
HF_DSER = "https://datasets-server.huggingface.co"
DATASET = "common-pile/uspto"
CONFIG = "default"
SPLIT = "train"
UA = "toscanini-rbg/1.0 (R504 auth probe; measure-before-integration)"

QUOTA_HEADER_HINTS = ("x-ratio", "quota", "rate", "limit", "remaining",
                      "x-ratelimit", "retry-after")


def load_token() -> str:
    tok = ""
    for line in VAULT.read_text().splitlines():
        line = line.strip()
        if line.startswith("HF_TOKEN="):
            tok = line.split("=", 1)[1].strip()
    if not tok:
        print("FATAL: HF_TOKEN absent from the local vault")
        sys.exit(2)
    return tok


def token_fp(tok: str) -> str:
    import hashlib
    return "len=%d sha256:12=%s" % (len(tok), hashlib.sha256(
        tok.encode()).hexdigest()[:12])


def probe(url: str, token: str = "", timeout: int = 60) -> dict:
    """One GET; returns typed status + headers-of-record + body digest."""
    import hashlib
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    t0 = time.time()
    rec: dict = {"url": url, "authenticated": bool(token)}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(2_000_000)
            rec["http_status"] = r.status
            rec["headers_of_record"] = {
                k: v for k, v in r.headers.items()
                if any(h in k.lower() for h in QUOTA_HEADER_HINTS)
                or k.lower() in ("content-type", "x-request-id")}
            try:
                js = json.loads(body)
                if isinstance(js, dict):
                    rec["body_keys"] = sorted(js.keys())[:12]
                    if "num_rows_total" in js:
                        rec["num_rows_total"] = js["num_rows_total"]
                    if "rows" in js:
                        rec["rows_returned"] = len(js["rows"])
                elif isinstance(js, list):
                    rec["body_list_len"] = len(js)
            except Exception as exc:  # noqa: BLE001
                rec["body_parse"] = f"PARSE_ERROR: {exc}"
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        body = e.read(200_000)
        try:
            js = json.loads(body)
            if isinstance(js, dict):
                rec["provider_error"] = str(js.get("error", ""))[:200]
        except Exception:  # noqa: BLE001
            rec["provider_error"] = body.decode("utf-8", "replace")[:200]
        rec["headers_of_record"] = {
            k: v for k, v in (e.headers or {}).items()
            if any(h in k.lower() for h in QUOTA_HEADER_HINTS)}
    except Exception as exc:  # noqa: BLE001
        rec["http_status"] = None
        rec["transport_error"] = f"{type(exc).__name__}: {exc}"[:200]
    rec["latency_ms"] = int((time.time() - t0) * 1000)
    rec["body_sha256_12"] = hashlib.sha256(
        repr(rec.get("rows_returned", "")) .encode()).hexdigest()[:12]
    return rec


def main() -> int:
    tok = load_token()
    print(f"[r504-probe] token fingerprint: {token_fp(tok)}")
    ledger: dict = {
        "record_id": "R504_HF_AUTH_PROBE",
        "purpose": ("measure-before-integration for HF_TOKEN authenticated "
                    "quota on the free evidence legs (operator directive "
                    "2026-09-18); both modes measured per endpoint; "
                    "includes the R500-deferred /search warming-window "
                    "retry"),
        "token_fingerprint": token_fp(tok),
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
        "dataset": DATASET,
    }

    # pass 1: whoami (credential liveness)
    import socket
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {tok}", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            js = json.loads(r.read())
        ledger["pass1_whoami"] = {
            "state": "LIVE", "name": js.get("name"),
            "type": js.get("type"),
            "auth_type": js.get("auth", {}).get("type"),
        }
    except Exception as exc:  # noqa: BLE001
        ledger["pass1_whoami"] = {"state": "FAILED",
                                  "error": f"{type(exc).__name__}"[:80]}
        print("[r504-probe] whoami FAILED — token unusable; aborting")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(ledger, indent=1))
        return 2

    # passes 2-5: per-endpoint, both modes
    endpoints = {
        "pass2_splits": f"{HF_DSER}/splits?dataset={urllib.parse.quote(DATASET)}",
        "pass3_rows": (f"{HF_DSER}/rows?dataset={urllib.parse.quote(DATASET)}"
                       f"&config={CONFIG}&split={SPLIT}&offset=0&length=2"),
        "pass4_search": (f"{HF_DSER}/search?dataset={urllib.parse.quote(DATASET)}"
                         f"&config={CONFIG}&split={SPLIT}"
                         f"&query={urllib.parse.quote('shunt valve')}"
                         f"&offset=0&length=3"),
        "pass5_catalog": ("https://huggingface.co/api/datasets?other=patents"
                          "&limit=5&full=false"),
    }
    for name, url in endpoints.items():
        keyless = probe(url, token="")
        authed = probe(url, token=tok)
        ledger[name] = {"keyless": keyless, "authenticated": authed}
        print(f"[r504-probe] {name}: keyless={keyless['http_status']} "
              f"authed={authed['http_status']} "
              f"(keyless {keyless['latency_ms']}ms / authed "
              f"{authed['latency_ms']}ms)")

    # typed comparison verdict per endpoint (MEASURED, never assumed)
    verdict = {}
    for name in endpoints:
        k = ledger[name]["keyless"].get("http_status")
        a = ledger[name]["authenticated"].get("http_status")
        if k == 200 and a == 200:
            v = "BOTH_MODES_LIVE"
        elif k != 200 and a == 200:
            v = "AUTH_ONLY_LIVE"
        elif k == 200 and a != 200:
            v = "AUTH_DEGRADES_NEVER_DEPLOY"
        else:
            v = "BOTH_MODES_NON_LIVE"
        verdict[name] = v
    ledger["typed_verdicts"] = verdict
    ledger["integration_ruling"] = (
        "authenticated header MAY be wired only where the authenticated "
        "mode measured >= the keyless mode (never degrades); the header is "
        "attached from the HF_TOKEN environment when present, and the "
        "per-call custody provenance records the mode actually used "
        "(LXXV clause 1: provenance = which source, which endpoint, "
        "which query, when — and now, under which credential mode)")
    ledger["reviewer_provenance"] = "AI_REVIEW"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ledger, indent=1))
    print(f"[r504-probe] ledger -> {OUT.relative_to(REPO)}")
    print(json.dumps(verdict, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
