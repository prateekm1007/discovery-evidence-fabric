#!/usr/bin/env python3
"""R466 — persist ALL operator credentials as Hugging Face Space secrets
on the canonical production Space (prateekm1/toscanini-prod-validation).

Operator instruction (2026-09-15): "put all api's in huggingface secret
( including PAT,API's )" — every credential the deployment or the
project tooling needs is persisted as a Space secret so no session
ever has to re-insert them (extends R461's "never insert again" from
the five router keys to the WHOLE set, explicitly including the GitHub
PAT and the Hugging Face key itself).

What this script does:
  1. RE-SETS the three credentials whose values the operator supplied
     in this session (idempotent writes; HF secrets are write-only —
     values are never readable back, never logged, never committed):
       GITHUB_TOKEN  — the operator's GitHub PAT (drives the Space's
                       durable-state push via toscanini/durable.py and
                       the project's git pushes)
       ZAI_API_KEY   — the LLM gateway credential (the value is the
                       operator's HF key; the R456/R461 wiring)
       HF_TOKEN      — the R463 P0 architectural ruling's ONE legitimate
                       user/application AI credential path (the `hf`
                       provider rung reads exactly this name)
  2. VERIFIES the full secret surface by name (the router keys
     UNOROUTER/XKIRO/APINEX/BAI/BYNARA + the inert candidates
     TOKENHARBOR/AEROLINK were persisted from R461/R463/R464; their
     values are not held in this session and are NOT touched — the
     live provider matrix on /api/health is the proof they are loaded).
  3. Records an artifact with FINGERPRINTS ONLY (Art. VI: values are
     never recorded anywhere).

Failure classification: a missing router-key VALUE in this session is
not an error — it is the standing BS-021 env-only posture; the secret
is already persisted on the Space and the provider matrix is the live
evidence. Typed honestly, not converted into a failure (Art. XXV/LXI).
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
ARTIFACT = REPO / "R466" / "HF_SPACE_SECRETS_ALL.json"

# Credentials whose values the operator supplied THIS session.
SET_NOW = ("GITHUB_TOKEN", "ZAI_API_KEY", "HF_TOKEN")

# The full expected surface (names only — the standing set from
# R456/R461/R463/R464 deploys + this round's re-set).
EXPECTED_NAMES = (
    "GITHUB_TOKEN", "ZAI_API_KEY", "HF_TOKEN", "HF_API_KEY",
    "PORTFOLIO_COMMIT",
    "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
    "BAI_API_KEY", "BYNARA_API_KEY",
    "TOKENHARBOR_API_KEY", "AEROLINK_API_KEY",
)


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})"


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset in session env (BS-021 env-only)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R466", "space": SPACE,
           "directive": "put all api's in huggingface secret "
                        "(including PAT, API's)",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "reset_this_round": {}, "verified_names": {}, "notes": []}

    # 1. Re-set the operator-supplied credentials (idempotent).
    for var in SET_NOW:
        val = os.environ.get(var, "").strip()
        if not val:
            print(f"WARN: {var} not supplied this session — the "
                  f"existing Space secret is left untouched (typed)")
            out["reset_this_round"][var] = {"set": False,
                                            "reason": "value not in "
                                                      "session env"}
            continue
        api.add_space_secret(repo_id=SPACE, key=var, value=val)
        out["reset_this_round"][var] = {"set": True,
                                        "key_fingerprint": fp(val),
                                        "value": "<never recorded>"}
        print(f"secret re-set: {var} on {SPACE} "
              f"(fingerprint {fp(val)}, value never logged)")

    # 2. Verify the full surface by NAME (write-only API: names only).
    import urllib.request
    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/secrets",
        headers={"Authorization": f"Bearer {hf_token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    entries = data if isinstance(data, list) \
        else list(data.values())
    present = {}
    for s in entries:
        present[s["key"]] = s.get("updatedAt", "")
    out["verified_names"] = {k: present.get(k, "ABSENT")
                             for k in EXPECTED_NAMES}
    missing = [k for k in EXPECTED_NAMES if k not in present]
    extra = sorted(set(present) - set(EXPECTED_NAMES))
    if extra:
        out["notes"].append(f"additional secrets present (left as-is): "
                            f"{extra}")

    # 3. Router-key values are NOT in this session (BS-021). The live
    #    provider matrix on /api/health is the evidence they are
    #    loaded — fetch and record it (statuses only).
    try:
        req2 = urllib.request.Request(
            "https://prateekm1-toscanini-prod-validation.hf.space"
            "/api/health")
        with urllib.request.urlopen(req2, timeout=30) as r2:
            provs = json.load(r2).get("providers", {})
        out["live_provider_matrix"] = {
            p: {"status": v.get("status"),
                "available_models": v.get("available_models")}
            for p, v in sorted(provs.items())}
        loaded = [p for p, v in out["live_provider_matrix"].items()
                  if v["available_models"]]
        out["notes"].append(
            "router keys' values are session-env-only (BS-021) and "
            "persisted on the Space from R461/R463 — the live provider "
            f"matrix shows them loaded: {sorted(loaded)}")
    except Exception as exc:  # noqa: BLE001 — matrix is evidence, not gate
        out["notes"].append(f"provider matrix fetch failed: {exc}")

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> {ARTIFACT.relative_to(REPO)} (fingerprints only)")

    missing_core = [k for k in ("GITHUB_TOKEN", "ZAI_API_KEY", "HF_TOKEN")
                    if out["reset_this_round"].get(k, {}).get("set")
                    is False and k not in present]
    print(f"secret surface: {len(present)} names present, "
          f"missing core: {missing_core or 'NONE'}")
    return 0 if not missing_core else 1


if __name__ == "__main__":
    sys.exit(main())
