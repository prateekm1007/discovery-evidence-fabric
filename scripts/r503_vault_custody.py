#!/usr/bin/env python3
"""R503 — Credential custody audit + vault consolidation (no rotation).

Operator directive (2026-09-18, verbatim):
  "huggingface API : <redacted-supplied-in-session>
   keep all keys safe in huggingface secrets. do not rotate them unless
   i the CEO says so. update that in the constitution. all keys,
   API's should be there."

Executed, in order:
  1. VERIFY the operator-supplied HF token (whoami) — measured byte-identical
     to the registered hf_MrZ...NkNM (len 37) credential (R468 fingerprint match
     + Space HF_TOKEN updatedAt 2026-09-15T16:45:28.599Z == R468 set event).
     => re-store, NOT a rotation.
  2. MEASURE both credential surfaces: Space secret NAMES (write-only) and
     Render env names+values (values in-process, never printed).
  3. CONSOLIDATE: add Render-held credential names missing from the Space
     vault (NVIDIA_API_KEY, OPENROUTER_API_KEY, ENGINE_OPERATOR_KEY).
     Existing standing secrets are left untouched (r456 typed-honest pattern).
  4. RECREATE the local Art. LXXIII vault (/home/z/my-project/.secrets.env)
     from held values only (HF_TOKEN from the operator directive; GITHUB_TOKEN
     from the session injection file). Values never printed.
  5. OUTPUT names + fingerprints + statuses ONLY (BS-021).

Typed states used (Art. VI/XXV — unknown stays unknown):
  PRESENT_ON_BOTH / ADDED_TO_VAULT_THIS_ROUND / PRESENT_VAULT_ONLY /
  CUSTODY_GAP_VALUE_NOT_HELD_HERE / REGISTERED_ABSENT_VALUE_NOT_HELD
"""
import json
import os
import re
import stat
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SPACE = "prateekm1/toscanini-prod-validation"
RENDER_API = "https://api.render.com/v1"
RENDER_SVC = "srv-dabp678jo6nc738fg2u0"
LOCAL_VAULT = Path("/home/z/my-project/.secrets.env")
OUT = Path(__file__).resolve().parents[1] / "R503" / "R503_VAULT_CUSTODY_AUDIT.json"

HF_TOKEN = Path("/home/z/my-project/scripts/.hf_token").read_text().strip()
GH_PAT = Path("/home/z/my-project/scripts/.gh_pat").read_text().strip()


def fp(v: str) -> str:
    return f"{v[:6]}...{v[-4:]} (len {len(v)})"


def http_json(url: str, token: str, method: str = "GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read()
    return json.loads(body) if body else {}


# --- 1. operator token verification (whoami) --------------------------------
who = http_json("https://huggingface.co/api/whoami-v2", HF_TOKEN)
operator_token = {
    "whoami": who.get("name"),
    "type": who.get("type"),
    "fingerprint": fp(HF_TOKEN),
    "matches_registered_R468_HF_TOKEN": fp(HF_TOKEN) == "hf_MrZ...NkNM (len 37)",
    "verdict": "RE-STORE_OF_REGISTERED_CREDENTIAL (not a rotation)",
}
assert who.get("name") == "prateekm1", "operator token identity unexpected"

# --- 2. measure surfaces ------------------------------------------------------
# NOTE: the secrets endpoint returns a DICT keyed by name (verified live);
# the first draft parsed it as a list and saw an empty surface — the incident
# is disclosed in write_events_this_round below (Art. XV).
space_raw = http_json(f"https://huggingface.co/api/spaces/{SPACE}/secrets", HF_TOKEN)
if isinstance(space_raw, dict):
    space_names = {k: v.get("updatedAt") for k, v in space_raw.items() if isinstance(v, dict)}
else:
    space_names = {s["key"]: s.get("updatedAt") for s in space_raw if isinstance(s, dict) and s.get("key")}

render_src = Path("/home/z/my-project/scripts/hf446_secrets.py")
render_key = re.search(r'RENDER_KEY\s*=\s*"([^"]+)"', render_src.read_text()).group(1)
render_env = {}
url = f"{RENDER_API}/services/{RENDER_SVC}/env-vars?limit=100"
while url:
    body = http_json(url, render_key)
    for item in body if isinstance(body, list) else body.get("envVars", []):
        d = item.get("envVar") or item
        if d.get("key"):
            render_env[d["key"]] = d.get("value", "")
    nxt = None
    if not isinstance(body, list) and body.get("links", {}).get("next"):
        nxt = body["links"]["next"]["href"]
    url = (nxt and (RENDER_API + nxt)) or None

CREDENTIAL_NAMES = {
    "NVIDIA_API_KEY",
    "OPENROUTER_API_KEY",
    "ENGINE_OPERATOR_KEY",
    "GITHUB_TOKEN",
    "HF_TOKEN",
    "ELSEVIER_API_KEY",
    "LENS_API_TOKEN",
    "PATENTBEAR_API_KEY",
}

# --- 3. write events this round (consolidation + the disclosed incident) ------
# The consolidation writes ALREADY HAPPENED in the first (buggy) execution.
# This pass re-posts NOTHING (idempotent guard: the intended names are present).
# Measured outcome of the four POSTs issued by the first execution:
#   ENGINE_OPERATOR_KEY / NVIDIA_API_KEY / OPENROUTER_API_KEY — intended adds
#   (sources: Render env, values in-process, never printed).
#   GITHUB_TOKEN — UNINTENDED standing-secret overwrite: the buggy empty-surface
#   parse made an already-present name look missing; the value written was
#   MEASURED byte-identical to the registered PAT (sha256[:16] f1ebca5f9b622f3e
#   == the R497 lift-in record fingerprint == local .gh_pat) — an effective
#   no-op on the value, disclosed here as a write event (Art. XV).
write_events_this_round = {
    "ENGINE_OPERATOR_KEY": {"intent": "INTENDED_ADD", "source": "RENDER_ENV (in-process, never printed)", "standing_secret_touched": False},
    "NVIDIA_API_KEY": {"intent": "INTENDED_ADD", "source": "RENDER_ENV (in-process, never printed)", "standing_secret_touched": False},
    "OPENROUTER_API_KEY": {"intent": "INTENDED_ADD", "source": "RENDER_ENV (in-process, never printed)", "standing_secret_touched": False},
    "GITHUB_TOKEN": {
        "intent": "UNINTENDED_OVERWRITE",
        "source": "RENDER_ENV (in-process, never printed)",
        "standing_secret_touched": True,
        "value_fingerprint": "sha256:f1ebca5f9b622f3e",
        "registered_fingerprint": "sha256:f1ebca5f9b622f3e (R497 lift-in record)",
        "effective_effect": "NO-OP (written value measured byte-identical to the standing value)",
        "disclosure": "the first execution parsed the secrets endpoint as a list, measured an empty surface, and re-set an already-present name; the value was verified identical, so the standing credential is unchanged; disclosed per Art. XV",
    },
}

# --- 4. recreate the local vault from held values only -----------------------
vault_lines = [
    f"HF_TOKEN={HF_TOKEN}",
    f"GITHUB_TOKEN={GH_PAT}",
]
LOCAL_VAULT.write_text("\n".join(vault_lines) + "\n")
LOCAL_VAULT.chmod(stat.S_IRUSR | stat.S_IWUSR)

# --- 5. post-verification (names only) ---------------------------------------
space_after_raw = http_json(f"https://huggingface.co/api/spaces/{SPACE}/secrets", HF_TOKEN)
if isinstance(space_after_raw, dict):
    space_after = {k: v.get("updatedAt") for k, v in space_after_raw.items() if isinstance(v, dict)}
else:
    space_after = {s["key"]: s.get("updatedAt") for s in space_after_raw if isinstance(s, dict) and s.get("key")}

record = {
    "record_id": "R503_VAULT_CUSTODY_AUDIT",
    "measured_at_utc": datetime.now(timezone.utc).isoformat(),
    "operator_directive_verbatim": "keep all keys safe in huggingface secrets. do not rotate them unless i the CEO says so. update that in the constitution. all keys, API's should be there.",
    "vault_of_record": f"https://huggingface.co/spaces/{SPACE} (secret surface, write-only)",
    "operator_token_verification": operator_token,
    "space_secret_names_before_this_pass": sorted(space_names),
    "space_secret_count_before_this_pass": len(space_names),
    "space_secret_count_before_round": 28,
    "render_env_names": sorted(render_env),
    "render_note": "legacy production surface (stale-surface escalation stands); values used in-process only as consolidation source",
    "write_events_this_round": write_events_this_round,
    "standing_secrets_touched": ["GITHUB_TOKEN (value-identical overwrite, measured no-op; disclosed)"],
    "rotation_events_this_round": [],
    "rotation_policy": "NO ROTATION — CEO-gated only (the ruling this round ratifies as Art. LXXVI)",
    "local_vault_recreated": str(LOCAL_VAULT),
    "local_vault_names": ["HF_TOKEN", "GITHUB_TOKEN"],
    "space_secret_names_after": sorted(space_after),
    "space_secret_count_after": len(space_after),
    "custody_gaps": [
        {
            "name": "PATENTBEAR_API_KEY",
            "state": "CUSTODY_GAP_VALUE_NOT_HELD_HERE",
            "registered_fingerprint": "561b6e70f5b5ea7f (R497 rotation record)",
            "detail": "the R497-era session vault (/home/z/my-project/.secrets.env) was lost to an environment reset; the Space vault surface has no PATENTBEAR_API_KEY name; the value cannot be fabricated or reconstructed (Art. VI/XXV)",
            "what_unblocks": "a session holding the value sets it on the Space vault surface, or the operator re-supplies the key",
        },
        {
            "name": "EPO_OPS_KEY / PATENTSVIEW_KEY (Tier-1 primary-verification credentials, Art. LXXV clause 3)",
            "state": "REGISTERED_ABSENT_VALUE_NOT_HELD",
            "detail": "never held; typed REQUIRES_REGISTRATION since R499",
            "what_unblocks": "free operator registration (EPO OPS) / PatentsView account",
        },
    ],
    "values_in_repository": False,
    "bs021_note": "no secret value appears in this record, any log, or any committed artifact — fingerprints only",
    "reviewer_provenance": "AI_REVIEW",
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(record, indent=2) + "\n")
print("write events:", json.dumps(sorted(write_events_this_round)))
print("space secrets now:", len(space_after), sorted(space_after))
print("record:", OUT)
