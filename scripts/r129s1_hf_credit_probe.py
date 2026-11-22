#!/usr/bin/env python3
"""r129s1_hf_credit_probe.py — Dir 6 (the R129 verdict): a BOUNDED HF
credit headroom probe BEFORE any panel-scale use of the meta-llama
router. One whoami-v2 (token validity/perms) + ONE router call at
max_tokens=2 through the engine's wired hf_router_chat (the same
transport the c-0203 probe measured). Typed verdicts:
  HTTP 200 + usage bytes  -> FUNDED (headroom exists now)
  RouteRefused payment_required (402) -> REFUSAL_CLASS (typed)
The ABSOLUTE remaining balance is not queryable for an individual
token (HF exposes no per-user credits endpoint; the org usage API is
Enterprise-scoped) — headroom is therefore typed as an INFERENCE
from (a) the 200 status, (b) the probe's own measured spend, and
(c) the committed r128 usage bytes ($2.54e-06 for 46 tokens ->
5.52e-08 $/token blended) projected onto panel-scale estimates.
The token is read env-only from the gitignored vault; ONLY digests
and usage bytes are printed or committed (Art. 17 / F45 custody).

Usage: python3 scripts/r129s1_hf_credit_probe.py
Writes: eval/r129s1_hf_credit_probe.json
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402

_load_key_vault()

import discovery_fabric.engine.route_adapter as ra  # noqa: E402

OUT = REPO / "eval" / "r129s1_hf_credit_probe.json"
MODEL = "meta-llama/Llama-3.1-8B-Instruct"
EXPECTED_DIGEST = "33bc7af22c62"  # committed custody (v3.3.0 + c-0203)

# committed r128 usage bytes -> blended $/token (the projection basis)
R128_COST = 2.54e-06
R128_TOKENS = 38 + 8


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec: dict = {"record": "R129S1_HF_CREDIT_PROBE/1.0.0", "at": now,
                 "session": "builder-r129s1", "authority":
                 "the R129 verdict dir 6 (bounded probe before panel "
                 "use); values false, digests only (Art. 17/F45)"}

    # custody: digest-verify the vault token against the committed record
    tok = ra.resolve_vault_key("HF_TOKEN")
    rec["token_digest12"] = (hashlib.sha256(tok.encode()).hexdigest()[:12]
                             if tok else None)
    rec["digest_match_committed"] = rec["token_digest12"] == EXPECTED_DIGEST
    if not tok or not rec["digest_match_committed"]:
        rec["verdict"] = "REFUSED_CUSTODY_MISMATCH"
        OUT.write_text(json.dumps(rec, indent=1) + "\n")
        print("REFUSED: token digest mismatch / missing (typed)")
        return 2

    # probe 1: whoami-v2 (validity + permission class, no values)
    try:
        req = urllib.request.Request(
            "https://huggingface.co/api/whoami-v2", headers={
                "Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            who = json.loads(r.read())
        auth = who.get("auth") or {}
        acc = auth.get("accessToken") or {}
        rec["whoami"] = {
            "http": 200,
            "type": who.get("type"),
            "login": who.get("name"),
            "token_role": acc.get("role"),
            "global_perms": sorted(auth.get("global") or []),
            "scoped_perms_none": (who.get("auth")
                                  and acc.get("fineGrained") is not None
                                  and not acc.get("fineGrained", {})
                                  .get("scoped")) or None,
        }
    except Exception as e:  # noqa: BLE001
        rec["whoami"] = {"http": None,
                         "fail": f"{type(e).__name__}: {str(e)[:120]}"}

    # probe 2: ONE bounded router call, max_tokens=2 (the c-0203 shape)
    try:
        resp = ra.hf_router_chat(
            [{"role": "user",
              "content": "Reply with the single word: OK."}],
            model=MODEL, max_tokens=2, timeout_s=120.0)
        u = resp.get("usage") or {}
        rec["router_call"] = {
            "http": 200, "model": resp.get("model"),
            "content_head": (resp.get("content") or "")[:20],
            "finish_reason": resp.get("finish_reason"),
            "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "cached_tokens": (u.get("prompt_tokens_details") or {})
            .get("cached_tokens") if resp.get("usage") else None,
        }
        pt = u.get("prompt_tokens") or 0
        ct = u.get("completion_tokens") or 0
        rec["router_call"]["probe_cost_usd"] = round(
            (pt + ct) * R128_COST / R128_TOKENS, 12)
        rec["verdict"] = "FUNDED_HEADROOM_EXISTS"
    except ra.RouteRefused as e:
        rec["router_call"] = {"http_status_class": e.kind,
                              "detail": str(e)[:160]}
        rec["verdict"] = ("REFUSAL_CLASS_PAYMENT_REQUIRED"
                          if e.kind == "payment_required"
                          else f"REFUSAL_CLASS_{e.kind}")
    except Exception as e:  # noqa: BLE001
        rec["router_call"] = {"fail": f"{type(e).__name__}: "
                                      f"{str(e)[:140]}"}
        rec["verdict"] = "TRANSPORT_FAIL_UNTYPED"

    # panel-scale projection (the verdict's accept: headroom for
    # panel-scale runs). score-8 panel: >=3 families x 24 items x
    # ~2K prompt + ~0.2K completion tokens/call.
    panel_tokens = 3 * 24 * 2200
    rec["panel_projection"] = {
        "basis": "r128 committed usage (2.54e-06 USD / 46 tokens)",
        "blended_usd_per_token": R128_COST / R128_TOKENS,
        "score8_panel_tokens": panel_tokens,
        "score8_panel_cost_usd": round(
            panel_tokens * R128_COST / R128_TOKENS, 4),
        "gepa_compile_round_tokens": 48 * 2200,
        "gepa_compile_round_cost_usd": round(
            48 * 2200 * R128_COST / R128_TOKENS, 4),
    }
    rec["headroom_typing"] = (
        "ABSOLUTE BALANCE NOT QUERYABLE for an individual token (no "
        "per-user credits endpoint; org usage API is Enterprise-"
        "scoped). Typed inference: a 200 with usage bytes proves the "
        "token is FUNDED now; the probe's own spend was "
        f"${rec['router_call'].get('probe_cost_usd', 0):.2e}; the "
        "score-8 panel projects to ~$0.01 and a GEPA compile round "
        "to ~$0.005 — headroom is SUFFICIENT for panel-scale runs "
        "unless the balance is already near zero, which the 200 "
        "status makes unlikely but does not exclude. Refusal class "
        "typed: any 402 at panel time = payment_required, typed, "
        "never retried (Art. 3).")

    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print("verdict:", rec["verdict"])
    print("whoami:", json.dumps(rec.get("whoami", {})))
    print("router:", json.dumps(rec.get("router_call", {})))
    print("panel projection:", json.dumps(rec["panel_projection"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
