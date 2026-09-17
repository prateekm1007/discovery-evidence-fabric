#!/usr/bin/env python3
"""R491 — register the operator-supplied credentials on the canonical
Space secret surface (Article LXXIII step 3), then verify BY NAME.

BS-021: values never printed, never logged; fingerprints only in output.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
VAULT = Path("/home/z/my-project/.secrets.env")
OUT = REPO / "R491" / "SECRETS_R491.json"


def _vault() -> dict:
    out = {}
    for line in VAULT.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _fp(v: str) -> str:
    return f"{v[:4]}...{v[-4:]} (len {len(v)})"


def main() -> int:
    vault = _vault()
    hf = vault.get("HF_TOKEN", "")
    if not hf:
        print("HF_TOKEN_ABSENT: cannot reach the Space secret surface")
        return 2

    names = ["LENS_API_TOKEN", "ELSEVIER_API_KEY"]
    record: dict = {
        "artifact_type": "R491_SECRETS_INVENTORY",
        "round": "R491",
        "space": SPACE,
        "registered_this_round": {},
        "surface_names_verified": None,
        "note": "values never recorded anywhere (BS-021); registration is not validation — see SOURCE_PROBE_R491.json for the measured provider-side states",
    }

    for name in names:
        value = vault.get(name, "")
        if not value:
            print(f"{name}: ABSENT from vault — not registered")
            continue
        # The R467/R468 measured-working path: huggingface_hub.HfApi
        # (raw-REST PUT /secrets/{name} answers 404; the library's
        # add_space_secret is the supported write transport).
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=hf)
            api.add_space_secret(repo_id=SPACE, key=name, value=value)
            ok, body = True, "add_space_secret OK"
        except Exception as exc:  # noqa: BLE001
            ok, body = False, f"{type(exc).__name__}: {exc}"[:200]
        record["registered_this_round"][name] = {
            "set": ok,
            "fingerprint": _fp(value),
            "response": body,
        }
        print(f"{name}: {'SET' if ok else 'FAILED'}")

    # verify by name (the API is write-only for values; names are listable)
    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/secrets",
        headers={"Authorization": f"Bearer {hf}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        entries = data if isinstance(data, list) else list(data.values())
        present = {s["key"] for s in entries if isinstance(s, dict) and "key" in s}
        record["surface_names_verified"] = sorted(present)
        print(f"surface holds {len(present)} names; new names present: "
              f"{[n for n in names if n in present]}")
    except Exception as exc:  # noqa: BLE001
        record["surface_names_verified"] = f"UNVERIFIED: {type(exc).__name__}: {exc}"[:200]
        print("surface verification FAILED (recorded honestly)")

    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(f"record: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
