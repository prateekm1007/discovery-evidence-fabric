#!/usr/bin/env python3
"""R467 — persist the operator's EIGHTH router key (ATRIA_API_KEY) as an
HF Space secret on the canonical production Space (prateekm1/
toscanini-prod-validation, R447-SPACE-OWNER).

Operator instruction (2026-09-15, verbatim): ".https://api.atria-asi.ai/
console/keys: <key> add this to the API's keys we are using to hugging
face, its gives 100million tokens of new model which is as good as
glm5.3 and finish the remaining issues. we should be token surplus now"

This is the r461/r463_hf_secrets.py pattern extended to the eighth key.
Unlike the sixth/seventh (inert candidates), atria is REGISTERED this
round (llm_registry._SPEC_BY_ID carries it; the ProviderSpec reads
exactly ATRIA_API_KEY) — the secret becomes the rung's live credential
on the next deploy.

The key rides the ENVIRONMENT ONLY (BS-021): ATRIA_API_KEY — read from
the live env, written through the HF API, never logged, never
committed. The artifact records only WHICH secret is set (masked
fingerprint), never the value.

The operator's declared budget ("100million tokens") has no measurable
provider surface (no usage/balance endpoint — the R467 probe measured
/v1/usage, /v1/balance, /v1/credits all 404/405), so the artifact
records the claim as OPERATOR-DECLARED, never as a measurement.
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

KEY_VARS = ("ATRIA_API_KEY",)


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (env only — BS-021)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R467", "space": SPACE,
           "directive": "add this to the API's keys we are using to "
                        "hugging face (the atria key)",
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

    out["standing_others"] = (
        "the five live router keys + TOKENHARBOR/AEROLINK + "
        "GITHUB_TOKEN/ZAI_API_KEY/HF_TOKEN remain persisted from "
        "R461/R463/R466 (write-only API — names verified by "
        "r466_hf_secrets_all.py)")
    out["operator_declared_budget"] = (
        "100 million tokens (operator-declared 2026-09-15; no provider "
        "usage/balance endpoint is measurable — the R467 probe measured "
        "/v1/usage, /v1/balance, /v1/credits all 404/405 — the claim is "
        "recorded, never converted into a measurement; Art. VI/XXV)")
    out["note"] = (
        "atria is REGISTERED this round (llm_registry PROVIDER_SPECS "
        "carries the spec; model_routing declares the STRONG rung) — "
        "unlike the inert sixth/seventh candidates, this secret becomes "
        "the live credential of the token-surplus rung on the next "
        "deploy")
    path = REPO / "R467" / "HF_SPACE_SECRETS.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> R467/HF_SPACE_SECRETS.json (fingerprints only)")
    n_set = sum(1 for s in out["secrets"].values() if s.get("set"))
    print(f"secrets persisted: {n_set}/{len(KEY_VARS)}")
    return 0 if n_set == len(KEY_VARS) else 1


if __name__ == "__main__":
    sys.exit(main())
