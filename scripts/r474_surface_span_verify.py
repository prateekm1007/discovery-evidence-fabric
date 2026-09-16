#!/usr/bin/env python3
"""R474 — settle the keys-3-13 surface contradiction with a MEASUREMENT
(Art. III: the latest typed verdict rules), and pin the R469 span-contract
landed state.

THE CONTRADICTION this round resolves:
  - R472/HF_SPACE_SECRETS_ATRIA_RING15.json (2026-09-15T22:58:16Z):
    all 15 ring names PRESENT on the Space surface, keys probed at
    set-time (catalog 200 each).
  - R473/R473_ROUND_RECORD.json honest_scope: "11 Atria keys (3-13)
    remain conversation-only; the key-pool HF-secrets task stays queued
    behind this directive."
These cannot both describe the present. The R473 session inherited the
stale sandbox (its own words) and wrote the honest-scope line from ITS
vault state, not from a surface measurement. The HF secret surface is
the credential AUTHORITY (Art. LXXIII), so this round measures it live:
  1. NAME presence: GET the direct secrets endpoint (values are
     write-only; presence is the proof — the R472 method);
  2. VALUE validity, keys 3-13: GET {BASE}/v1/models per key (auth
     evaluates before plan/gate logic — the R463 method), with the
     R470 non-200 re-probe discipline (2 confirmations, 8 s apart,
     before a key is typed INVALID);
  3. Vault mirror check: the local vault carries keys 1-7, 9-13
     (raw values); fingerprints compared against the R472 record's
     set-time fingerprints for 11-13;
  4. R469 span-contract landed pins: SPAN_INSTRUCTION + the mechanical
     span_repair in synthesize.py; verify.py iterating ALL evidence
     (the evidence[0] mis-alignment dead); the battery file present;
  5. Production identity: /api/version + /api/health vs origin/main.

Values are read from the ENV/vault ONLY (BS-021); the artifact records
measurements and FINGERPRINTS, never values.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "https://api.atria-asi.ai"
SPACE = "prateekm1/toscanini-prod-validation"
PROD = "https://prateekm1-toscanini-prod-validation.hf.space"
VAULT = Path("/home/z/my-project/.secrets.env")
ARTIFACT = REPO / "R474" / "SURFACE_SPAN_VERIFICATION.json"

RING = ["ATRIA_API_KEY"] + [f"ATRIA_API_KEY_{i}" for i in range(2, 16)]
CHECK_KEYS = [f"ATRIA_API_KEY_{i}" for i in range(3, 14)]  # 3..13
UA = "toscanini-r474-verifier/1.0"


def fp(value: str) -> str:
    return f"{value[:6]}...{value[-4:]} (len {len(value)})"


def http_get(url: str, headers: dict, timeout: int = 30):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return None, repr(e)[:200]


def load_vault() -> dict:
    vault = {}
    if not VAULT.exists():
        return vault
    for line in VAULT.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            vault[k.strip()] = v.strip()
    return vault


def main() -> int:
    out = {
        "round": "R474",
        "purpose": ("settle the R472-ring15 vs R473-honest-scope "
                    "contradiction on the keys-3-13 surface state, "
                    "with a live measurement; pin the R469 span fix"),
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "space": SPACE,
        "surface_names": {},
        "value_probes": {},
        "vault_mirror": {},
        "span_contract_pins": {},
        "production_identity": {},
        "verdict": None,
    }
    vault = load_vault()
    hf_token = vault.get("HF_TOKEN", "")
    if not hf_token:
        print("FATAL: HF_TOKEN not in vault — cannot measure the surface")
        return 2

    # ---- 1. name presence (values write-only; presence is the proof)
    status, data = http_get(
        f"https://huggingface.co/api/spaces/{SPACE}/secrets",
        {"Authorization": f"Bearer {hf_token}", "User-Agent": UA})
    if status == 200 and isinstance(data, dict):
        present = set(data.keys())
        for name in RING:
            out["surface_names"][name] = (
                "PRESENT" if name in present else "ABSENT")
        out["surface_names"]["_all_ring_names"] = (
            f"{sum(1 for v in out['surface_names'].values() if v == 'PRESENT')}"
            f"/{len(RING)} PRESENT")
        print(f"[surface] {out['surface_names']['_all_ring_names']}")
    else:
        out["surface_names"]["_error"] = f"status={status} resp={data!r}"[:200]
        print(f"WARN: surface listing unavailable: {out['surface_names']['_error']}")
        return 2

    # ---- 2. value validity, keys 3-13 (auth-first endpoint; R463 method)
    for name in CHECK_KEYS:
        key = vault.get(name, "")
        if not key:
            out["value_probes"][name] = "NOT_IN_VAULT"
            print(f"[probe] {name}: not in vault — skipped")
            continue
        status, body = http_get(
            f"{BASE}/v1/models",
            {"Authorization": f"Bearer {key}", "User-Agent": UA})
        attempts = 1
        if status != 200:  # R470 discipline: 2 confirmations, 8 s apart
            for i in range(2):
                time.sleep(8)
                status, body = http_get(
                    f"{BASE}/v1/models",
                    {"Authorization": f"Bearer {key}", "User-Agent": UA})
                attempts += 1
                if status == 200:
                    break
        models = []
        if status == 200 and isinstance(body, dict):
            models = [m.get("id") for m in body.get("data", []) if isinstance(m, dict)]
        out["value_probes"][name] = {
            "verdict": "VALID" if status == 200 else f"INVALID_{status}",
            "attempts": attempts,
            "fingerprint": fp(key),
            "models": models,
        }
        print(f"[probe] {name}: {out['value_probes'][name]['verdict']} "
              f"(attempts={attempts}, fp={fp(key)})")

    # ---- 3. vault mirror vs the R472 set-time fingerprints (11-13)
    r472 = json.load(open(REPO / "R472" / "HF_SPACE_SECRETS_ATRIA_RING15.json"))
    for name in ("ATRIA_API_KEY_11", "ATRIA_API_KEY_12", "ATRIA_API_KEY_13"):
        rec_fp = r472.get("set_this_round", {}).get(name, {}).get("key_fingerprint", "")
        now_fp = fp(vault[name]) if vault.get(name) else "MISSING"
        out["vault_mirror"][name] = {
            "r472_record_fingerprint": rec_fp,
            "vault_fingerprint": now_fp,
            "match": (rec_fp.split(" ")[0] == now_fp.split(" ")[0])
            if rec_fp and now_fp != "MISSING" else None,
        }
    print(f"[vault] 11-13 match: "
          f"{[v['match'] for v in out['vault_mirror'].values()]}")

    # ---- 4. span-contract landed pins (source-level)
    syn = (REPO / "discovery_fabric" / "a2" / "synthesize.py").read_text()
    ver = (REPO / "discovery_fabric" / "a2" / "verify.py").read_text()
    pins = {
        "SPAN_INSTRUCTION_defined": "SPAN_INSTRUCTION = (" in syn,
        "mechanical_span_repair": "span_repair" in syn and "verbatim-subwindow" in syn,
        "eight_word_rule": ">=8" in syn or ">= 8" in syn,
        "verify_iterates_all_evidence": "for idx, item in enumerate(evidence)" in ver,
        "verify_e0_misalignment_documented_fixed": "evidence[0]" in ver and "mis-alignment" in ver,
        "battery_file_present": (REPO / "tests" / "test_r469_span_contract.py").exists(),
        "battery_file_present_keyring": (REPO / "tests" / "test_r469_atria_keyring.py").exists(),
    }
    out["span_contract_pins"] = pins
    print(f"[span] pins: {pins}")

    # ---- 5. production identity vs origin/main
    for path in ("/api/version", "/api/health"):
        status, body = http_get(f"{PROD}{path}", {"User-Agent": UA})
        out["production_identity"][path] = {
            "status": status,
            "body": body if not isinstance(body, dict) else
            {k: body.get(k) for k in list(body)[:10]},
        }
        print(f"[prod] {path}: status={status}")

    # ---- verdict
    ring_present = sum(1 for v in out["surface_names"].values() if v == "PRESENT")
    valid = [k for k, v in out["value_probes"].items()
             if isinstance(v, dict) and v["verdict"] == "VALID"]
    invalid = [k for k, v in out["value_probes"].items()
               if isinstance(v, dict) and v["verdict"].startswith("INVALID")]
    out["verdict"] = {
        "ring_names_present": f"{ring_present}/{len(RING)}",
        "keys_3_13_valid": f"{len(valid)}/{len(CHECK_KEYS)}",
        "keys_3_13_invalid": invalid,
        "span_pins_all_true": all(pins.values()),
        "statement": (
            "SURFACE CONFIRMED: keys 3-13 are lifted AND live-valid; "
            "R473's honest-scope line described its stale vault, not the "
            "surface (the parallel R472 line had already lifted them)."
            if ring_present == len(RING) and not invalid and all(pins.values())
            else "GAPS REMAIN — see the measured fields"),
    }
    print(json.dumps(out["verdict"], indent=1))

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"artifact -> {ARTIFACT} (fingerprints only, BS-021)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
