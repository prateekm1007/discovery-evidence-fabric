#!/usr/bin/env python3
"""R469 — persist the operator's SEVEN Atria keys as HF Space secrets.

Operator directive (2026-09-16): atria is the discovery engine's
DEFAULT API; seven keys ≈ 700M tokens; when one key exhausts the
engine advances to the next (the in-engine cascade the R469 tree
wires). The seven env names are the cascade order:
  ATRIA_API_KEY (primary) then ATRIA_API_KEY_2 .. ATRIA_API_KEY_7.

Article LXXIII: values are write-only — never logged, never committed
(fingerprints only). The live name inventory lives in the round record
(their LXXIII: names in records, never in the article).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from huggingface_hub import HfApi

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
ARTIFACT = REPO / "R469" / "HF_SPACE_SECRETS_ATRIA_CASCADE.json"

ATRIA_NAMES = tuple(["ATRIA_API_KEY"] +
                    [f"ATRIA_API_KEY_{i}" for i in range(2, 8)])


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})"


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (Article LXXIII lookup: session "
              "env -> vault -> ask; the vault should have supplied it)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R469", "space": SPACE,
           "directive": "seven atria keys = the in-engine rotation "
                        "cascade (~700M tokens, operator-declared); "
                        "atria is the engine's default API",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "set_this_round": {}, "verified_names": {}, "notes": []}

    for var in ATRIA_NAMES:
        val = os.environ.get(var, "").strip()
        if not val:
            out["set_this_round"][var] = {"set": False,
                                          "reason": "value not in session"}
            print(f"WARN: {var} not supplied — left untouched")
            continue
        api.add_space_secret(repo_id=SPACE, key=var, value=val)
        out["set_this_round"][var] = {"set": True,
                                      "key_fingerprint": fp(val),
                                      "value": "<never recorded>"}
        print(f"secret set: {var} (fingerprint {fp(val)})")

    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/secrets",
        headers={"Authorization": f"Bearer {hf_token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    entries = data if isinstance(data, list) else list(data.values())
    present = {s["key"] for s in entries}
    out["verified_names"] = {k: ("PRESENT" if k in present else "ABSENT")
                             for k in ATRIA_NAMES}
    missing = [k for k in ATRIA_NAMES if k not in present]
    print(f"atria surface: {len(ATRIA_NAMES) - len(missing)}/"
          f"{len(ATRIA_NAMES)} present; missing: {missing or 'NONE'}")
    total = sum(1 for k in ATRIA_NAMES if k in present)
    out["notes"].append(f"cascade surface: {total} live slots; "
                        "rotation order = env order")

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> {ARTIFACT.relative_to(REPO)} (fingerprints only)")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
