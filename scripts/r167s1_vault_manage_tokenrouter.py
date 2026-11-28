#!/usr/bin/env python3
"""r167s1_vault_manage_tokenrouter.py — R167-F1: vault-manage TOKENROUTER.

The auditor's R167-F1 direction (V131): TOKENROUTER_API_KEY is not
vault-managed, so every sandbox recycle needs manual re-patching while
r77 restores the other 8. This act adds TOKENROUTER_API_KEY to the
owner vault dataset (prateekm1/operator-keys-vault, operator_keys.json)
with its typed digest (c148574f6215) so r77_vault_restore.py restores
all 9 in one command. HF master stays directions-delivered (it unlocks
the vault — it cannot live inside it). The value never prints, never
commits: b64 + digest only, same schema as the other 8 entries.
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


def d12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    val = os.environ.get("TOKENROUTER_API_KEY", "").strip()
    if not token or not val:
        print("REFUSED: HF_TOKEN or TOKENROUTER_API_KEY missing in env")
        return 3
    dig = d12(val.encode())
    if dig != "c148574f6215":
        print(f"REFUSED: TOKENROUTER digest {dig} != the typed c148574f6215 —"
              " the env value is not the canonical vault-state key")
        return 3

    # fetch the current vault doc
    req = urllib.request.Request(
        f"https://huggingface.co/datasets/{VAULT_REPO}/resolve/main/{VAULT_FILE}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        doc = json.loads(r.read().decode("utf-8"))

    if "TOKENROUTER_API_KEY" in doc["keys"]:
        e = doc["keys"]["TOKENROUTER_API_KEY"]
        have = e.get("sha256_12") or e.get("digest")
        if have == dig:
            print(f"already vault-managed at digest {dig} — nothing to do")
            return 0
        print(f"REFUSED: vault carries TOKENROUTER at digest {have} != {dig};"
              " manual reconciliation required (never a silent overwrite)")
        return 3

    doc["keys"]["TOKENROUTER_API_KEY"] = {
        "b64": base64.b64encode(val.encode()).decode(),
        "sha256_12": dig,
    }
    doc.setdefault("vault_notes", []).append({
        "at": "2026-11-26T16:45:00Z",
        "act": "R167-F1 (V131): TOKENROUTER_API_KEY vault-managed (digest"
               f" {dig}); r77_vault_restore.py now restores all 9 keys —"
               " recycle recovery is one command (the auditor's direction;",
        "by": "builder-r167s1 (the auditor's R167-F1 direction; delegated"
              " owner act, digests-only disclosure)",
    })

    # upload via the hub library (same endpoint family r77 reads)
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=json.dumps(doc, indent=1, ensure_ascii=False).encode(),
        path_in_repo=VAULT_FILE,
        repo_id=VAULT_REPO,
        repo_type="dataset",
        commit_message="R167-F1 (V131): vault-manage TOKENROUTER_API_KEY "
                       f"(sha256_12 {dig}) — r77 restores all 9; digest-only "
                       "disclosure, no plaintext in the commit",
    )
    print(f"uploaded: TOKENROUTER_API_KEY vault-managed at digest {dig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
