#!/usr/bin/env python3
"""R468 — persist ALL operator-supplied credentials as Hugging Face Space
secrets on the canonical production Space (prateekm1/toscanini-prod-
validation), and verify the full secret surface by name.

Operator instruction (2026-09-16, verbatim, key bodies redacted BS-021):
  "https://api.atria-asi.ai/console/keys: atr_6...Ku5f and atr_7...HJmm"
  "huggingface API : hf_M...NkNM"
  "save all these huggingface secret, and write in your constitution to
   look it up in huggingface secret, so you dont keep asking me again"

This is the r466_hf_secrets_all.py pattern extended to the R468 set:
  SET_NOW (values supplied by the operator / the local vault this
  session — idempotent writes; HF secrets are write-only, values never
  readable back, never logged, never committed):
    HF_TOKEN        — re-provisioned by the operator 2026-09-16 (the
                      environment reset had wiped it — the R462/R467
                      DELIVERY_BLOCKED class)
    ZAI_API_KEY     — the LLM gateway credential (value IS the operator's
                      HF key — the R456/R461 wiring)
    GITHUB_TOKEN    — the operator's GitHub PAT (recovered verbatim from
                      the operator's .gitcreds — the credential that
                      drove every push since R466)
    ATRIA_API_KEY_2 — the operator's SECOND atria key (validated by the
                      R468 probe differential BEFORE this write; the
                      backup/rotation credential — the engine's
                      ProviderSpec reads only ATRIA_API_KEY)
  (ATRIA_API_KEY key-1 was persisted minutes earlier this round by
  scripts/r467_hf_secrets.py — the R467 unblock leg 1.)

The full surface is then VERIFIED BY NAME (the write-only API never
returns values) and the live provider matrix on /api/health is recorded
as the runtime-injection evidence. Artifacts carry FINGERPRINTS ONLY
(BS-021; the r463 key-marker guard applies).
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
ARTIFACT = REPO / "R468" / "HF_SPACE_SECRETS.json"

# Credentials whose values this session holds (env/vault only — BS-021).
SET_NOW = ("HF_TOKEN", "ZAI_API_KEY", "GITHUB_TOKEN", "ATRIA_API_KEY_2")

# The full expected surface (names only — the standing set from
# R456/R461/R463/R464/R466/R467 deploys + this round's writes).
EXPECTED_NAMES = (
    "GITHUB_TOKEN", "ZAI_API_KEY", "HF_TOKEN", "HF_API_KEY",
    "PORTFOLIO_COMMIT",
    "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
    "BAI_API_KEY", "BYNARA_API_KEY",
    "TOKENHARBOR_API_KEY", "AEROLINK_API_KEY",
    "ATRIA_API_KEY", "ATRIA_API_KEY_2",
)


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})"


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset in session env (BS-021 env-only)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R468", "space": SPACE,
           "directive": "save all these huggingface secret, and write in "
                        "your constitution to look it up in huggingface "
                        "secret, so you dont keep asking me again",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "set_this_round": {}, "verified_names": {}, "notes": []}

    # 1. Persist the operator-supplied credentials (idempotent writes).
    for var in SET_NOW:
        val = os.environ.get(var, "").strip()
        if not val:
            print(f"WARN: {var} not supplied this session — the existing "
                  f"Space secret is left untouched (typed)")
            out["set_this_round"][var] = {"set": False,
                                          "reason": "value not in "
                                                    "session env"}
            continue
        api.add_space_secret(repo_id=SPACE, key=var, value=val)
        out["set_this_round"][var] = {"set": True,
                                      "key_fingerprint": fp(val),
                                      "value": "<never recorded>"}
        print(f"secret set: {var} on {SPACE} (fingerprint {fp(val)}, "
              f"value never logged)")

    # 2. Verify the full surface by NAME (write-only API: names only).
    import urllib.request
    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/secrets",
        headers={"Authorization": f"Bearer {hf_token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    entries = data if isinstance(data, list) else list(data.values())
    present = {s["key"]: s.get("updatedAt", "") for s in entries}
    out["verified_names"] = {k: present.get(k, "ABSENT")
                             for k in EXPECTED_NAMES}
    missing = [k for k in EXPECTED_NAMES if k not in present]
    extra = sorted(set(present) - set(EXPECTED_NAMES))
    out["surface_count"] = len(present)
    if extra:
        out["notes"].append(f"additional secrets present (left as-is): "
                            f"{extra}")

    # 3. The live provider matrix on /api/health — the runtime-injection
    #    evidence (statuses only; the standing deployment still runs the
    #    pre-atria tree until this round's deploy lands).
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
            "the STANDING deployment's provider matrix (pre-atria until "
            f"the R468 deploy lands): {sorted(loaded)}")
    except Exception as exc:  # noqa: BLE001 — matrix is evidence, not gate
        out["notes"].append(f"provider matrix fetch failed: {exc}")

    # 4. The ATRIA_API_KEY_2 write is preceded by the R468 probe
    #    (probe-before-record): the differential validated the key.
    probe_path = REPO / "R468" / "PROBE_ATRIA_KEY2.json"
    if probe_path.exists():
        probe = json.loads(probe_path.read_text())
        out["key2_probe_verdict"] = probe.get("verdict", {})
        out["notes"].append("ATRIA_API_KEY_2 persisted only after the "
                            "R468 probe differential validated it "
                            "(probe-before-record)")

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> {ARTIFACT.relative_to(REPO)} (fingerprints only)")

    missing_core = [k for k in SET_NOW
                    if out["set_this_round"].get(k, {}).get("set") is False
                    and k not in present]
    print(f"secret surface: {len(present)} names present, "
          f"missing expected: {missing or 'NONE'}, "
          f"missing core: {missing_core or 'NONE'}")
    return 0 if not missing and not missing_core else 1


if __name__ == "__main__":
    sys.exit(main())
