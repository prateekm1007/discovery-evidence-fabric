#!/usr/bin/env python3
"""Record the typed apinex.bond window state (Art. LXI / Art. XXV).

Live-measured 2026-11-14T13:54Z with the owner-supplied credential
(vaulted as APINEX_API_KEY per Art. LXXXVII arrival custody BEFORE any
use; value never in tracked bytes, name only here):

  - KEY FORMAT VALID: the key passes the Cloudflare edge (bare requests
    get the CF HTML challenge; the key'd request reaches the JSON API
    layer) — the credential is well-formed enough to route
  - ACCOUNT STATE: HTTP 403 "Account suspended or missing"
    (authentication_error) on EVERY probe: both hosts
    (apinex.bond, api.apinex.bond), both auth header schemes
    (Authorization: Bearer, x-api-key, X-API-Key), both endpoints
    (/v1/models, /v1/chat/completions)
  - the error class is ACCOUNT-level, not key-typo-level: an unknown
    key would 401; this 403 names the account state
  - DASHBOARD: https://apinex.bond/keys renders (200) as a login-gated
    SPA — key activation/account state is a dashboard-side act

Consequence (typed): the apinex window cannot serve the D4/D5/D6
judge/generator calls this session. Nothing repo-side heals a suspended
account. The post-reset queue stays on the xkiro/mistral path (fixed
daily reset 00:00Z, confirmed by converging retry-after probes). If the
owner re-activates the account or supplies a fresh key, the queue picks
it up at call time from the vault (zero code change — the same
lookup-first contract as every other rung).
"""
import json
import pathlib

rec = {
 "record": "APINEX_WINDOW_STATE/1.0.0",
 "measured_at": "2026-11-14T13:54:00Z",
 "credential": "APINEX_API_KEY (owner-supplied 2026-11-14, sk-apxb- form; "
               "vaulted per Art. LXXXVII BEFORE any use)",
 "key_format_state": "VALID (passes the Cloudflare edge to the API layer)",
 "account_state": {
  "http": 403,
  "error": "Account suspended or missing",
  "type": "authentication_error",
  "probed": {
   "hosts": ["https://apinex.bond/v1",
             "https://api.apinex.bond/v1"],
   "auth_schemes": ["Authorization: Bearer", "x-api-key", "X-API-Key"],
   "endpoints": ["/v1/models", "/v1/chat/completions"],
   "all_same_error": True,
  },
  "error_class": "ACCOUNT_LEVEL (dashboard-side; a key typo would 401 — "
                 "this 403 names the account state)",
 },
 "dashboard": "https://apinex.bond/keys renders 200 as a login-gated SPA; "
              "activation/account state is an owner dashboard-side act",
 "consequence": {
  "d4_d5_d6": "stay on the xkiro/mistral post-reset path (fixed 00:00Z "
              "daily reset, confirmed by converging retry-after probes); "
              "scripts/post_reset_queue.sh unchanged",
  "recovery": "a re-activated account or fresh key is picked up at call "
              "time from the vault (lookup-first, zero code change)",
  "art": "Art. LXI (infrastructure absence is typed, never silently "
         "wasted); Art. XXV (typed, never manufactured)",
 },
}
out = pathlib.Path(
    "/home/z/my-project/def/eval/apinex_window_state_r11.json")
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(f"typed window state -> {out}")
