#!/usr/bin/env python3
"""R472 — extend the atria ring on the HF Space secret surface: the
operator's LATEST key delivery adds FIVE more keys (the message lists
fifteen; ten were already persisted at R467-R470). New names:
  ATRIA_API_KEY_11 .. ATRIA_API_KEY_15
Ring order after this round: ATRIA_API_KEY, _2 .. _15 (fifteen slots,
~1.5B tokens operator-declared; 14 VALID after the R472 probe — key 8
remains excluded: its re-probe answered a deterministic 401 x3 again).

Article LXXIII: values are write-only — never logged, never committed
(fingerprints only); names live in the round record.
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
ARTIFACT = REPO / "R472" / "HF_SPACE_SECRETS_ATRIA_RING15.json"

NEW_NAMES = tuple(f"ATRIA_API_KEY_{i}" for i in range(11, 16))
FULL_RING = tuple(["ATRIA_API_KEY"] +
                  [f"ATRIA_API_KEY_{i}" for i in range(2, 16)])


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})"


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (Article LXXIII lookup: session "
              "env -> vault; the vault should have supplied it)")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R472", "space": SPACE,
           "directive": ("fifteen atria keys = the in-engine rotation "
                         "ring (~1.5B tokens, operator-declared); the "
                         "operator's latest message lists all fifteen — "
                         "ten were already on the surface, FIVE are new"),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "set_this_round": {}, "verified_names": {},
           "ring_order_declared": list(FULL_RING), "notes": []}

    for var in NEW_NAMES:
        val = os.environ.get(var, "").strip()
        if not val:
            out["set_this_round"][var] = {"set": False,
                                          "reason": "value not in session"}
            out["notes"].append(f"WARN: {var} not supplied — left "
                                "untouched")
            print(f"WARN: {var} not supplied — left untouched")
            continue
        try:
            api.add_space_secret(repo_id=SPACE, key=var, value=val)
            out["set_this_round"][var] = {
                "set": True, "key_fingerprint": fp(val),
                "value": "<never recorded>"}
            print(f"[set] {var} = {fp(val)}")
        except Exception as e:  # noqa: BLE001
            out["set_this_round"][var] = {"set": False,
                                          "error": repr(e)[:200]}
            out["notes"].append(f"ERROR setting {var}: {repr(e)[:200]}")
            print(f"ERROR setting {var}: {repr(e)[:200]}")

    # verify by NAME (values are write-only; presence is the proof) —
    # the DIRECT secrets endpoint (the R470-measured method: a DICT
    # keyed by secret name; get_space_variables sees variables, not
    # secrets)
    import urllib.request
    try:
        req = urllib.request.Request(
            f"https://huggingface.co/api/spaces/{SPACE}/secrets",
            headers={"Authorization": f"Bearer {hf_token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        present = set(data.keys()) if isinstance(data, dict) else {
            e.get("key") for e in data if isinstance(e, dict)}
        for var in FULL_RING:
            out["verified_names"][var] = ("PRESENT" if var in present
                                          else "ABSENT")
        n_present = sum(1 for v in out["verified_names"].values()
                        if v == "PRESENT")
        out["verified_summary"] = {
            "n_names_present": n_present, "n_names_expected":
            len(FULL_RING),
            "all_present": n_present == len(FULL_RING)}
        print(f"[verify] {n_present}/{len(FULL_RING)} ring names PRESENT")
    except Exception as e:  # noqa: BLE001
        out["verified_summary"] = {"error": repr(e)[:200]}
        print(f"WARN: name verification unavailable: {repr(e)[:200]}")

    out["notes"].append(
        "key 8 (ATRIA_API_KEY_8) re-probed this round: deterministic "
        "401 x3 — the R470 exclusion STANDS; the Space surface may carry "
        "it inertly (the ring registration is the selection authority)")

    with open(ARTIFACT, "w") as f:
        json.dump(out, f, indent=1)
    print(f"artifact -> {ARTIFACT} (fingerprints only)")

    ok = all(v.get("set") for v in out["set_this_round"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
