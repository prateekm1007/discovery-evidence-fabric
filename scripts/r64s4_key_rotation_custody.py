#!/usr/bin/env python3
"""R64s4 key rotation + Art.17 v3.3.0 custody extension.

Secrets arrive via env ONLY (never hardcoded, never printed, never committed):
  AGNES_KEY_A, AGNES_KEY_B  - the two owner-delivered agnes keys (original+new)
  HF_TOKEN_PROBE            - the owner-delivered HF token (vault unlock)

Flow:
 1. identify original vs new key by digest (r59 convention sha256[:12];
    original recorded as d0c666a3842f in eval/r59_credential_custody_r59s1.json)
 2. probe BOTH keys against the agnes models endpoint (zero v9 problem reads)
 3. register AGNES_API_KEY_2 in the gitignored .env.keys (chmod 600; the frozen
    gateway reads AGNES_API_KEY only - gateway bytes are NOT touched)
 4. HF vault: whoami + token digest vs recorded 33bc7af22c62; repo_info private;
    download operator_keys.json; digest-verify existing entries against local
    .env.keys values (Art. 17 restore verification); append AGNES_API_KEY_2
    (base64 + digest); upload; re-download; verify byte-identical + new entry
 5. write eval/r64s4_key_rotation_custody.json (digests + probe results ONLY)
"""
import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

REPO = Path(__file__).resolve().parent.parent
ENV_KEYS = REPO / ".env.keys"
VAULT = "prateekm1/operator-keys-vault"
AGNES_BASE = "https://apihub.agnes-ai.com/v1"
R59_ORIGINAL_DIGEST = "d0c666a3842f"
MASTER_TOKEN_DIGEST_RECORDED = "33bc7af22c62"
OUT = REPO / "eval" / "r64s4_key_rotation_custody.json"
D12 = lambda b: hashlib.sha256(b).hexdigest()[:12]

results = {"record": "R64S4_KEY_ROTATION_CUSTODY/1.0.0",
           "session": "builder-r64s4 (continuation)", "date": "2026-11-18",
           "values": False, "steps": {}}


def die(msg):
    print("FATAL:", msg)
    results["fatal"] = msg
    OUT.write_text(json.dumps(results, indent=1) + "\n")
    sys.exit(2)


def env(name):
    v = os.environ.get(name, "")
    if not v:
        die(f"env {name} missing")
    return v


def parse_envkeys(text):
    out = {}
    for ln in text.splitlines():
        ln = ln.strip()
        if "=" in ln and not ln.startswith("#"):
            k, _, v = ln.partition("=")
            out[k] = v
    return out


def probe_agnes(key):
    req = urllib.request.Request(
        f"{AGNES_BASE}/models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
        models = body.get("data") if isinstance(body, dict) else body
        n = len(models) if isinstance(models, list) else None
        return {"http": r.status, "models": n}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "models": None, "typed": "http_error"}


# ---- 1. identify keys -------------------------------------------------------
ka, kb = env("AGNES_KEY_A"), env("AGNES_KEY_B")
da, db = D12(ka.encode()), D12(kb.encode())
current = parse_envkeys(ENV_KEYS.read_text()).get("AGNES_API_KEY", "")
dc = D12(current.encode()) if current else None
results["steps"]["digests"] = {
    "candidate_a_digest12": da, "candidate_b_digest12": db,
    "current_stored_digest12": dc,
    "r59_original_digest12": R59_ORIGINAL_DIGEST}
if dc == da and dc != db:
    orig_label, orig_d, new_label, new_d, new_key = "A", da, "B", db, kb
elif dc == db and dc != da:
    orig_label, orig_d, new_label, new_d, new_key = "B", db, "A", da, ka
else:
    die(f"stored AGNES_API_KEY digest {dc} matches neither candidate "
        f"({da}/{db}); refusing to guess the original")
results["steps"]["identification"] = {
    "original": orig_label, "original_digest12": orig_d,
    "new": new_label, "new_digest12": new_d,
    "matches_r59_original_record": orig_d == R59_ORIGINAL_DIGEST}
print(f"identification: stored==candidate_{orig_label} ({orig_d}), "
      f"new=candidate_{new_label} ({new_d}); "
      f"r59-match={orig_d == R59_ORIGINAL_DIGEST}")

# ---- 2. probe both keys (zero v9 problem reads) -----------------------------
pa, pb = probe_agnes(ka), probe_agnes(kb)
results["steps"]["agnes_probes"] = {
    "candidate_a": {**pa, "digest12": da},
    "candidate_b": {**pb, "digest12": db}}
print("agnes probes:", json.dumps(results["steps"]["agnes_probes"]))
if pa.get("http") != 200 or pb.get("http") != 200:
    die("one of the agnes probes failed - refusing to register an unprobed key")

# ---- 3. register AGNES_API_KEY_2 (chmod 600) --------------------------------
lines = ENV_KEYS.read_text().splitlines()
if "AGNES_API_KEY_2" not in [l.split("=", 1)[0] for l in lines if "=" in l]:
    lines.append(f"AGNES_API_KEY_2={new_key}")
else:
    lines = [f"AGNES_API_KEY_2={new_key}" if l.startswith("AGNES_API_KEY_2=")
             else l for l in lines]
ENV_KEYS.write_text("\n".join(lines) + "\n")
ENV_KEYS.chmod(0o600)
results["steps"]["envkeys_update"] = {
    "added": "AGNES_API_KEY_2", "new_digest12": new_d,
    "perms": "600", "original_line_untouched": True}
print(f".env.keys updated (AGNES_API_KEY_2={new_d}, chmod 600, "
      f"original line untouched)")

# ---- 4. HF vault custody extension -------------------------------------------
tok = env("HF_TOKEN_PROBE")
tok_d = D12(tok.encode())
api = HfApi(token=tok)
who = api.whoami()
login = who.get("name")
role = (who.get("auth") or {}).get("accessToken", {}).get("role")
results["steps"]["hf_token"] = {
    "digest12": tok_d,
    "matches_recorded_master_digest_33bc7af22c62":
        tok_d == MASTER_TOKEN_DIGEST_RECORDED,
    "login": login, "token_role": role}
print(f"hf token: digest={tok_d} "
      f"(match33bc7af22c62={tok_d == MASTER_TOKEN_DIGEST_RECORDED}) "
      f"login={login} role={role}")

info = api.repo_info(repo_id=VAULT, repo_type="dataset")
results["steps"]["vault_repo"] = {"private": bool(getattr(info, "private", None)),
                                  "sha12": getattr(info, "sha", "")[:12]}
print("vault repo private:", getattr(info, "private", None))

local = parse_envkeys(ENV_KEYS.read_text())
vk = hf_hub_download(repo_id=VAULT, repo_type="dataset",
                     filename="operator_keys.json", token=tok)
vault = json.loads(Path(vk).read_text())


def entry_decode(v):
    if isinstance(v, dict):
        b = v.get("b64") or v.get("value_b64") or v.get("base64")
        d = v.get("sha256_12") or v.get("digest")
        return b, d
    return v, None


def entry_decode(v):
    if isinstance(v, dict):
        b = v.get("b64")
        d = next((v[k] for k in v if k.startswith("sha256")), None)
        return b, d
    return v, None


vault_keys = vault.get("keys") if isinstance(vault.get("keys"), dict) else {}
if not vault_keys:
    die("vault operator_keys.json has no 'keys' dict - refusing")
vault_check = {}
for name, v in vault_keys.items():
    b64, d = entry_decode(v)
    if not b64:
        vault_check[name] = {"error": "no b64 field",
                             "fields": sorted(v.keys()) if isinstance(v, dict)
                             else type(v).__name__}
        continue
    val = base64.b64decode(b64)
    calc = D12(val)
    local_val = local.get(name)
    ok_local = (local_val is not None and D12(local_val.encode()) == calc)
    vault_check[name] = {
        "digest12": calc,
        "stored_digest_field_matches": (d is None or d == calc),
        "matches_local_envkeys_value": ok_local}
results["steps"]["vault_restore_verification"] = vault_check
print("vault entries verified:", json.dumps(
    {k: v.get("matches_local_envkeys_value", "no-b64")
     for k, v in vault_check.items()}))
bad = [k for k, v in vault_check.items()
       if v.get("error")
       or (k != "AGNES_API_KEY_2"
           and not v["stored_digest_field_matches"])
       or (k != "AGNES_API_KEY_2" and k in local
           and not v["matches_local_envkeys_value"])]
if bad:
    die(f"vault digest verification FAILED for: {bad}")
results["steps"]["remediation_disclosure"] = {
    "typed": "PRE_EXISTING_ENTRY_MISMATCH_OWNED_KEY",
    "note": "a prior invocation of THIS script (variable-shadowing bug: the "
            "candidate label 'B' was used instead of the key bytes) wrote "
            "b64('B') under AGNES_API_KEY_2 with the real key's digest in "
            "the digest field; that entry is script-OWNED and is rewritten "
            "and digest-verified in the extension step below (Art. 5 "
            "disclosure; the buggy commit remains in the vault history)",
    "observed_pre_state": vault_check.get("AGNES_API_KEY_2")}

digest_field = next((k for v in vault_keys.values() if isinstance(v, dict)
                     for k in v if k.startswith("sha256")), "sha256_12")
model = vault_keys.get("AGNES_API_KEY")
new_entry = dict(model) if isinstance(model, dict) else {}
new_entry["b64"] = base64.b64encode(new_key.encode()).decode()
new_entry[digest_field] = new_d
vault_keys["AGNES_API_KEY_2"] = new_entry
pre_b64 = {k: entry_decode(v)[0] for k, v in vault_keys.items()
           if k != "AGNES_API_KEY_2"}


def vault_fetch_raw():
    """Fetch the vault file straight from the resolve endpoint (bypasses the
    hub cache - force_download is unreliable across hub majors)."""
    req = urllib.request.Request(
        f"https://huggingface.co/datasets/{VAULT}/resolve/main/"
        f"operator_keys.json",
        headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


cur = vault_fetch_raw()
cur_keys = cur.get("keys", {})
already = (entry_decode(cur_keys.get("AGNES_API_KEY_2", {}))[0]
           == new_entry["b64"])
uploaded = False
if not already:
    import tempfile
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    tmp.write(json.dumps(vault, indent=1) + "\n")
    tmp.close()
    api.upload_file(path_or_fileobj=tmp.name,
                    path_in_repo="operator_keys.json",
                    repo_id=VAULT, repo_type="dataset",
                    commit_message="r64s4: +AGNES_API_KEY_2 (digest-only "
                                   "custody record in tracked repo)")
    uploaded = True
    cur = vault_fetch_raw()
    cur_keys = cur.get("keys", {})
b2, d2 = entry_decode(cur_keys.get("AGNES_API_KEY_2", {}))
recheck = D12(base64.b64decode(b2)) if b2 else None
unchanged = all(entry_decode(cur_keys.get(k, {}))[0] == b64
                for k, b64 in pre_b64.items())
local_match = (local.get("AGNES_API_KEY_2") is not None
               and D12(local["AGNES_API_KEY_2"].encode()) == recheck)
results["steps"]["vault_extension"] = {
    "added": "AGNES_API_KEY_2", "new_digest12": new_d,
    "digest_field": digest_field,
    "uploaded_this_run": uploaded,
    "post_upload_digest_ok": recheck == new_d,
    "stored_digest_field_matches": d2 == new_d,
    "matches_local_envkeys_value": local_match,
    "pre_existing_entries_byte_unchanged": unchanged,
    "vault_keys": sorted(cur_keys)}
print(f"vault extension: post-upload digest ok={recheck == new_d}, "
      f"existing entries unchanged={unchanged}")

results["verdict"] = ("CUSTODY_EXTENDED"
                      if (recheck == new_d and unchanged and local_match
                          and d2 == new_d)
                      else "FAILED")
OUT.write_text(json.dumps(results, indent=1) + "\n")
print("record written:", OUT, "| verdict:", results["verdict"])
sys.exit(0 if results["verdict"] == "CUSTODY_EXTENDED" else 1)
