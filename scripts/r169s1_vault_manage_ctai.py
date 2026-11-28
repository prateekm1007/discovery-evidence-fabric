#!/usr/bin/env python3
"""r169s1_vault_manage_ctai.py — the owner's ctai delivery vault-managed.

The owner's instruction (this window): "https://api.cantrustai.xyz + /v1
token: ctai_... use it for judges, save it in huggingface vault." The
R167-F1 pattern: add CTAI_API_KEY + CTAI_BASE_URL to the operator vault
dataset (prateekm1/operator-keys-vault, operator_keys.json) as
{b64, sha256_12} entries — digest-only disclosure, never a plaintext
commit — so r77_vault_restore.py restores 11/11 keys and every future
recycle recovers with one command.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VAULT_REPO = "prateekm1/operator-keys-vault"
VAULT_FILE = "operator_keys.json"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

KEY = os.environ.get("CTAI_API_KEY", "").strip()  # vault-managed (r77_vault_restore.py); never committed (r177s1 strip — the historical literal is BURNED, auditor Art.12 v1.3.0)
BASE = "https://api.cantrustai.xyz/v1"


def d12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def fetch_vault(token: str) -> dict:
    req = urllib.request.Request(
        f"https://huggingface.co/datasets/{VAULT_REPO}/resolve/main/"
        f"{VAULT_FILE}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        doc = json.loads(r.read().decode("utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("keys"), dict):
        raise ValueError("vault payload is not the expected shape")
    return doc


def main() -> int:
    if not KEY:
        print("REFUSED: CTAI_API_KEY missing — vault-managed (r77_vault_restore.py); never committed (r177s1)")
        return 3
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("REFUSED: HF_TOKEN (the master) missing — it is "
              "directions-delivered, never vault-managed")
        return 3
    doc = fetch_vault(token)
    keys = doc["keys"]

    adds = {}
    if "CTAI_API_KEY" not in keys:
        adds["CTAI_API_KEY"] = {
            "b64": base64.b64encode(KEY.encode()).decode(),
            "sha256_12": d12(KEY.encode()),
        }
    if "CTAI_BASE_URL" not in keys:
        adds["CTAI_BASE_URL"] = {
            "b64": base64.b64encode(BASE.encode()).decode(),
            "sha256_12": d12(BASE.encode()),
        }
    if not adds:
        print("already vault-managed — nothing to do")
        return 0
    keys.update(adds)
    doc.setdefault("vault_notes", []).append({
        "at": "2026-11-27T10:50:00Z",
        "act": "the owner's ctai delivery vault-managed: "
               + ", ".join(f"{k} ({v['sha256_12']})"
                           for k, v in adds.items())
               + " — for judge use (the owner's instruction this window); "
               "digests only, no plaintext in the commit",
        "by": "builder-r169s1 (the owner's instruction; R167-F1 pattern)",
    })

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=json.dumps(doc, indent=1,
                                   ensure_ascii=False).encode(),
        path_in_repo=VAULT_FILE,
        repo_id=VAULT_REPO,
        repo_type="dataset",
        commit_message="R169S1 (owner instruction): vault-manage "
                       "CTAI_API_KEY + CTAI_BASE_URL ("
                       + ", ".join(f"{k} sha256_12={v['sha256_12']}"
                                   for k, v in adds.items())
                       + ") — for judges; digest-only disclosure",
    )
    print(f"uploaded: {', '.join(adds)} "
          f"({', '.join(v['sha256_12'] for v in adds.values())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
