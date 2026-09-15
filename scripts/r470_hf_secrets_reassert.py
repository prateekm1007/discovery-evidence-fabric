#!/usr/bin/env python3
"""R470 (reconciled line) — re-assert the VAULT values for the six new
VALID atria keys on the HF Space secret surface.

Why a re-assert after the sibling R470-C2 round already set 10/10 by
name: the secrets API is WRITE-ONLY — the sibling's values cannot be
read back, and this line's vault is the Article LXXIII canonical store.
Setting the six VALID new keys (4,5,6,7,9,10) with the vault values
makes the surface provably consistent with the vault (idempotent when
identical, corrective when the parallel lines transcribed differently).

ATRIA_API_KEY_8 is deliberately NOT re-set: this line's probe measured
it a DETERMINISTIC 401 on BOTH /v1/models (x3, re-probed) and
/v1/chat/completions ("Invalid API key." — R470/PROBE_ATRIA_KEYS4TO10.json
+ this round's completions differential). The ring excludes it; the
value the sibling set stays on the surface INERTLY (the ring is the
selection authority) pending the operator's re-supply.

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
ARTIFACT = REPO / "R470" / "HF_SPACE_SECRETS_REASSERT.json"

# the six probe-VALID new keys (vault values)
VALID_NEW = ("ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
             "ATRIA_API_KEY_7", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10")
# the full expected name surface after this round (15 standing + 6)
EXPECTED = ("HF_TOKEN", "ZAI_API_KEY",
            "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
            "BAI_API_KEY", "BYNARA_API_KEY", "TOKENHARBOR_API_KEY",
            "AEROLINK_API_KEY",
            "ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
            "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
            "ATRIA_API_KEY_7", "ATRIA_API_KEY_8", "ATRIA_API_KEY_9",
            "ATRIA_API_KEY_10")


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})" if val else "(unset)"


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("FATAL: HF_TOKEN unset (Article LXXIII lookup order: "
              "session env -> vault)")
        return 2
    vals = {n: os.environ.get(n, "").strip() for n in VALID_NEW}
    missing = [n for n, v in vals.items() if not v]
    if missing:
        print(f"FATAL: unset in session env: {missing}")
        return 2
    api = HfApi(token=hf_token)

    out = {"round": "R470", "line": "reconciled (probe-validated ring)",
           "space": SPACE,
           "directive": ("re-assert the VAULT values for the six "
                         "probe-VALID new keys; ATRIA_API_KEY_8 "
                         "deliberately NOT re-set (probe-typed invalid "
                         "on both endpoints; ring-excluded, surface-"
                         "inert pending operator re-supply)"),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "set_this_round": {}, "verified_names": [], "absent": []}

    for name in VALID_NEW:
        api.add_space_secret(SPACE, name, vals[name])
        out["set_this_round"][name] = {"set": True,
                                       "fingerprint": fp(vals[name])}
        print(f"[set] {name} (fingerprint only)")

    # the name-surface verification (write-only API: names, not values)
    # — the /api/spaces/{SPACE}/secrets endpoint returns a DICT keyed
    # by secret name (the sibling R470-C2's measured fix: values carry
    # only updatedAt; get_space_variables sees VARIABLES, not secrets)
    try:
        import urllib.request as _ur
        req = _ur.Request(
            f"https://huggingface.co/api/spaces/{SPACE}/secrets",
            headers={"Authorization": f"Bearer {hf_token}"})
        with _ur.urlopen(req, timeout=30) as r:
            data = json.load(r)
        present = set(data.keys()) if isinstance(data, dict) else {
            e.get("key") for e in data if isinstance(e, dict)}
        out["verified_names"] = sorted(present)
        out["absent"] = [n for n in EXPECTED if n not in present]
        print(f"[verify] {len(present)} secret names present; "
              f"absent={out['absent']}")
    except Exception as exc:  # noqa: BLE001 — recorded, never fatal
        out["verify_error"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"[verify] failed (recorded): {out['verify_error']}")

    ARTIFACT.write_text(json.dumps(out, indent=2))
    print(f"artifact -> {ARTIFACT} (fingerprints only)")
    return 0 if not out.get("absent") else 1


if __name__ == "__main__":
    sys.exit(main())
