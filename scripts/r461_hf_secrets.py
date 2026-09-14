#!/usr/bin/env python3
"""R461 — save the operator's FIVE free-tier router keys as HF Space
secrets on the canonical production Space (prateekm1/
toscanini-prod-validation, R447-SPACE-OWNER).

The operator's instruction (2026-09-15): "save this in hugging face
secrets so i dont have to keep insertig them again." The keys ride the
ENVIRONMENT ONLY (BS-021): UNOROUTER_API_KEY, BYNARA_API_KEY,
XKIRO_API_KEY, APINEX_API_KEY, BAI_API_KEY — read from .env.keys /
the live env, written through the HF API, never logged, never
committed. The artifact records only WHICH secrets are set (masked
fingerprints), never values.

The deploy driver (scripts/r456_space_deploy.py) re-wires the same
five at every deploy; this script exists so the keys are PERSISTED on
the Space independent of any single deploy (the operator's
"never insert again").
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

KEY_VARS = ("UNOROUTER_API_KEY", "BYNARA_API_KEY", "XKIRO_API_KEY",
            "APINEX_API_KEY", "BAI_API_KEY")


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (env only — BS-021)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R461", "space": SPACE,
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

    # the standing env-contract secrets the deploy driver also wires
    # (kept as-is if already set; the driver re-writes them at deploy)
    out["note"] = ("the five router keys are persisted as Space "
                   "secrets; the deploy driver re-wires the same set "
                   "at every deploy (env-injected, never in the repo)")
    path = REPO / "R461" / "HF_SPACE_SECRETS.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> R461/HF_SPACE_SECRETS.json (fingerprints only)")
    n_set = sum(1 for s in out["secrets"].values() if s.get("set"))
    print(f"secrets persisted: {n_set}/{len(KEY_VARS)}")
    return 0 if n_set == len(KEY_VARS) else 1


if __name__ == "__main__":
    sys.exit(main())
