#!/usr/bin/env python3
"""R470 — extend the atria ring on the HF Space secret surface: the
operator's LATEST key delivery adds THREE more keys (the message lists
ten; seven were already persisted at R468/R469). New names:
  ATRIA_API_KEY_8, ATRIA_API_KEY_9, ATRIA_API_KEY_10
Ring order after this round: ATRIA_API_KEY, _2 .. _10 (TEN slots,
~1B tokens operator-declared).

Article LXXIII: values are write-only — never logged, never committed
(fingerprints only); names live in the round record.
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
ARTIFACT = REPO / "R470" / "HF_SPACE_SECRETS_ATRIA_RING10.json"

NEW_NAMES = ("ATRIA_API_KEY_8", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10")
FULL_RING = tuple(["ATRIA_API_KEY"] +
                  [f"ATRIA_API_KEY_{i}" for i in range(2, 11)])


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})"


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (Article LXXIII lookup: session "
              "env -> vault; the vault should have supplied it)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R470", "space": SPACE,
           "directive": ("ten atria keys = the in-engine rotation ring "
                         "(~1B tokens, operator-declared); the operator's "
                         "latest message lists all ten — seven were "
                         "already on the surface, THREE are new"),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "set_this_round": {}, "verified_names": {},
           "ring_order_declared": list(FULL_RING), "notes": []}

    for var in NEW_NAMES:
        val = os.environ.get(var, "").strip()
        if not val:
            out["set_this_round"][var] = {"set": False,
                                          "reason": "value not in session"}
            out["notes"].append(f"WARN: {var} not supplied — left untouched")
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
    # the endpoint returns a DICT keyed by secret name (measured live
    # 2026-09-16; the R469 assumption of a list-of-entries was wrong —
    # the names are the keys, the values carry only updatedAt)
    present = set(data.keys()) if isinstance(data, dict) else {
        e.get("key") for e in data if isinstance(e, dict)}
    for var in FULL_RING:
        out["verified_names"][var] = ("PRESENT" if var in present
                                      else "ABSENT")
    missing = [k for k, v in out["verified_names"].items() if v != "PRESENT"]
    if missing:
        out["notes"].append(f"ABSENT after write: {missing}")
        print(f"ABSENT after write: {missing}")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"artifact: {ARTIFACT}")
    print("surface check: " + ", ".join(
        f"{k}={v}" for k, v in out["verified_names"].items()))
    return (1 if missing else 0)


if __name__ == "__main__":
    sys.exit(main())
