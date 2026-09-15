#!/usr/bin/env python3
"""R463 — persist the operator's SIXTH and SEVENTH free-tier router
keys as HF Space secrets on the canonical production Space (prateekm1/
toscanini-prod-validation, R447-SPACE-OWNER).

The R462 round's DELIVERY_BLOCKED tuple named the missing HF_TOKEN as
its blocker; the operator re-provisioned the token and re-delivered
the keys in the same message (2026-09-15): "huggingface API: hf_...
+ https://aerolink.lat/dashboard/api-keys: aero_live_...". This
script is the r461_hf_secrets.py pattern extended to the sixth and
seventh keys (the R462 what_unblocks, verbatim: "the Space-secret
persistence path (the r461_hf_secrets.py pattern extended to the
sixth key)").

The keys ride the ENVIRONMENT ONLY (BS-021): TOKENHARBOR_API_KEY,
AEROLINK_API_KEY — read from .env.keys / the live env, written through
the HF API, never logged, never committed. The artifact records only
WHICH secrets are set (masked fingerprints), never values.

Both keys are for providers whose ADMISSION is unresolved (tokenharbor:
deferred to a Space-side measurement per R462; aerolink: refused at the
account-plan gate this round — R463/AEROLINK_OWNER_ESCALATION.json).
The secrets are INERT on the deployed app (no ProviderSpec reads them:
neither provider is in _SPEC_BY_ID); they persist so (a) the operator's
"never insert again" standing instruction holds and (b) the Space-side
admission probe path stays unblocked.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from huggingface_hub import HfApi

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"

KEY_VARS = ("TOKENHARBOR_API_KEY", "AEROLINK_API_KEY")


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (env only — BS-021)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R463", "space": SPACE,
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "secrets": {}}
    for var in KEY_VARS:
        val = os.environ.get(var, "").strip()
        if not val:
            print(f"WARN: {var} unset — the secret is NOT written "
                  f"(typed, honest)")
            out["secrets"][var] = {"set": False}
            continue
        api.add_space_secret(repo_id=SPACE, key=var, value=val)
        fp = f"{val[:6]}...{val[-4:]}"
        out["secrets"][var] = {"set": True, "key_fingerprint": fp,
                               "value": "<never recorded>"}
        print(f"secret set: {var} on {SPACE} (fingerprint {fp}, "
              f"value never logged)")

    out["standing_five"] = (
        "UNOROUTER_API_KEY / BYNARA_API_KEY / XKIRO_API_KEY / "
        "APINEX_API_KEY / BAI_API_KEY remain persisted from R461 "
        "(not re-writable this session — their values were wiped from "
        "the local environment by the reset; the Space holds them)")
    out["note"] = (
        "the sixth and seventh keys persist as Space secrets; both are "
        "admission-unresolved providers (tokenharbor: deferred to a "
        "Space-side measurement per R462; aerolink: refused at the "
        "account-plan gate per R463/AEROLINK_OWNER_ESCALATION.json) — "
        "the secrets are INERT on the deployed app until a future "
        "round registers their ProviderSpecs")
    path = REPO / "R463" / "HF_SPACE_SECRETS.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> R463/HF_SPACE_SECRETS.json (fingerprints only)")
    n_set = sum(1 for s in out["secrets"].values() if s.get("set"))
    print(f"secrets persisted: {n_set}/{len(KEY_VARS)}")
    return 0 if n_set == len(KEY_VARS) else 1


if __name__ == "__main__":
    sys.exit(main())
