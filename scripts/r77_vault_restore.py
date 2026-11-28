#!/usr/bin/env python3
"""r77_vault_restore.py — the GENERAL HF-vault custody restore (the
Art. 17 v3.3.0 "look it up there" clause made operational).

Why this exists: every sandbox reprovision (CORR-3, VAULT_LOST_,
the r64 incident, reprovision #3 at R77) lost the session-local
`.env.keys` vault, and every recovery so far hand-rolled a
session-local script that DIED WITH THE SANDBOX — work that dies with
the sandbox is not evidence (Art. 18) and the next reprovision starts
from zero again. This script is the committed, typed, fail-closed
restore path every future session runs FIRST.

What it does (zero LLM probes, zero inference, one read-only GET):
  1. Reads the HF master token from env HF_TOKEN (never argv, never
     logged — the value is the custody bootstrap, not a record byte).
  2. Fetches the owner's PRIVATE vault dataset file
     (prateekm1/operator-keys-vault -> operator_keys.json) — the
     repository itself is committed-DIGEST-ONLY (Art. 17: values live
     under owner privacy control; a public vault would burn every
     credential in it — auditor Art. 12 v1.3.0 typed constraint).
  3. Decodes each key entry, recomputes sha256[:12], and CROSS-CHECKS
     it against the vault's own digest field — fail-closed on any
     decode/digest mismatch (a corrupt or tampered vault never
     reaches .env.keys).
  4. Merges into the session-local .env.keys (0o600, gitignored):
     vault-managed keys are canonical (vault wins on conflict);
     pre-existing session keys not managed by the vault are KEPT and
     reported (never silently dropped — Art. 16 accounting habit).
  5. Cross-references the committed custody records
     (eval/r59_credential_custody_r59s1.json + the Art. 17 v3.3.0
     master-token digest) and prints a per-key
     COMMITTED_RECORD_MATCH report — a mismatch is a typed ROTATION
     TO DISCLOSE in the round record, not a silent overwrite.

Output discipline: DIGESTS ONLY are ever printed. Values never
appear in stdout, tracebacks, or the record (the caller's round
record carries digests, per the eval/r59 convention).

Exit codes (typed, Art. 3):
  0 restore OK (any per-key status is reported in the summary)
  2 vault fetch/parse/decode/digest failure (fail closed)
  3 HF_TOKEN missing (typed INFRA_CREDENTIAL_MISSING — the ONE
    master reminder is the caller's job, never routine re-asking)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VAULT_REPO = "prateekm1/operator-keys-vault"
VAULT_FILE = "operator_keys.json"
ENV_KEYS = REPO / ".env.keys"
COMMITTED_RECORD = REPO / "eval" / "r59_credential_custody_r59s1.json"
MASTER_TOKEN_DIGEST = "0af8db243dee"  # Art. 17 v3.3.0 typed state
# (R159S2 ROTATION TO DISCLOSE: the prior master 33bc7af22c62 was
# reported EXPIRED by the owner and re-delivered dead-on-arrival
# (eval/r159s2_hf_rekey_event.json); the owner then delivered the
# ROTATED token whose whoami-v2 probe returned 200; the digest above
# is the post-rotation typed state — eval/r159s2_hf_rotation_restore.json)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def d12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def fetch_vault(token: str) -> dict:
    """One read-only GET straight off the resolve endpoint (bypasses
    the hub cache — force_download is unreliable across hub majors,
    the r64s4 lesson)."""
    req = urllib.request.Request(
        f"https://huggingface.co/datasets/{VAULT_REPO}/resolve/main/"
        f"{VAULT_FILE}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        doc = json.loads(r.read().decode("utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("keys"), dict):
        raise ValueError("vault payload is not the expected "
                         "{record, keys{}} shape")
    return doc


def decode_entry(entry) -> tuple[str, str]:
    """(value, digest12) from one vault entry. Typed failure on any
    malformed entry — never a silent skip."""
    if isinstance(entry, dict):
        b64 = entry.get("b64")
        field_digest = (entry.get("sha256_12") or entry.get("digest"))
        if not b64:
            raise ValueError("entry missing b64 payload")
        val = base64.b64decode(b64).decode("utf-8")
        dig = d12(val.encode("utf-8"))
        if field_digest and field_digest != dig:
            raise ValueError(
                f"vault self-digest MISMATCH (field {field_digest} != "
                f"recomputed {dig}) — fail closed, value discarded")
        return val, dig
    if isinstance(entry, str):
        val = entry
        if val.startswith("b64:"):
            val = base64.b64decode(val[4:]).decode("utf-8")
        return val, d12(val.encode("utf-8"))
    raise ValueError(f"unsupported entry type {type(entry).__name__}")


def committed_digests() -> dict:
    """Digests recorded in the tracked repo (eval/r59 convention +
    the v3.3.0 master-token digest). Absent file -> empty map (typed
    NEW for everything, never a crash)."""
    out = {}
    try:
        rec = json.loads(COMMITTED_RECORD.read_text(encoding="utf-8"))
        out.update({k.upper(): v for k, v in
                    (rec.get("vault_post", {}).get("digests") or {}).items()
                    if isinstance(v, str)})
    except FileNotFoundError:
        pass
    out["HF_TOKEN"] = MASTER_TOKEN_DIGEST
    return out


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("REFUSED (typed INFRA_CREDENTIAL_MISSING, exit 3): HF_TOKEN "
              "absent — the master credential is owner-delivered on "
              "request (the ONE master reminder rule; never routine "
              "re-asking). Zero vault bytes read.")
        return 3
    try:
        doc = fetch_vault(token)
    except Exception as e:  # noqa: BLE001 — typed custody telemetry
        print(f"FAILED (typed exit 2): vault fetch/parse error class "
              f"{type(e).__name__}: {str(e)[:120]}")
        return 2

    keys = doc["keys"]
    pre = {}
    if ENV_KEYS.exists():
        for line in ENV_KEYS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                pre[k] = v

    restored, failed = {}, []
    for name, entry in keys.items():
        try:
            val, dig = decode_entry(entry)
        except Exception as e:  # noqa: BLE001
            failed.append({"key": name, "typed": type(e).__name__,
                           "detail": str(e)[:100]})
            continue
        restored[name] = (val, dig)

    if not restored:
        print("FAILED (typed exit 2): zero keys decoded from the vault — "
              "fail closed, .env.keys untouched.")
        return 2

    # merge: vault-managed keys canonical; session-only keys kept+reported
    merged = dict(pre)
    vault_names = set(restored)
    session_only = sorted(set(pre) - vault_names)
    for name, (val, _dig) in restored.items():
        merged[name] = val

    ref = committed_digests()
    lines = [f"{k}={merged[k]}" for k in sorted(merged)]
    ENV_KEYS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_KEYS.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600

    print(f"RESTORED {len(restored)} vault-managed keys + "
          f"{len(session_only)} session-only kept -> {ENV_KEYS} "
          f"(0o600, gitignored)")
    for name in sorted(restored):
        dig = restored[name][1]
        ref_dig = ref.get(name)
        match = ("COMMITTED_RECORD_MATCH" if ref_dig == dig else
                 "ROTATION_TO_DISCLOSE" if ref_dig else "NEW_IN_RECORDS")
        print(f"  {name}: sha256_12={dig} [{match}]")
    for name in session_only:
        print(f"  {name}: session-only (kept, not vault-managed)")
    for f in failed:
        print(f"  {f['key']}: FAILED {f['typed']} ({f['detail']})")
    if failed:
        print(f"NOTE: {len(failed)} key(s) failed decode and were NOT "
              "written — disclose in the round record (Art. 5).")
    self_check = doc.get("custody") or doc.get("record")
    print(f"vault self-description: {str(self_check)[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
