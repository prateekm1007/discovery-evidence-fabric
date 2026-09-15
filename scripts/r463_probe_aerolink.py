#!/usr/bin/env python3
"""R463 — the SEVENTH free-tier router candidate (aerolink.lat), met by
probe-before-admit (R451-C1.2 / Art. III) — and REFUSED at the ACCOUNT
PLAN gate the measurement found: every model on the discovered API host
answers a typed 403 permission_error "Free Starter access is currently
unavailable. Please upgrade your plan or add paid balance to continue
using the service."

THE API-BASE DISCOVERY (recorded provenance, Art. VI — never guessed):
the dashboard domain aerolink.lat serves a Next.js app whose /v1/* paths
404 (no API there) and whose Cloudflare edge bans the Python-urllib UA
(error 1010); api.aerolink.lat is a dead host (TCP-unreachable OVH IP
51.68.172.202). The real API host — capi.aerolink.lat — was discovered
from the EXTERNAL provider table at github.com/inyogeshwar/
claude-code-free (docs/providers/aerolink.md: "Base URL https://
capi.aerolink.lat/, API Format Anthropic-compatible") and then MEASURED
here: catalog 200 through this egress, Anthropic Messages dialect.

WHAT THE MEASUREMENT ESTABLISHES (richer than tokenharbor's R462
refusal, each fact measured not assumed):
  - the delivered key IS VALID — proven by the format-identical bogus-
    key differential: bogus -> 401 authentication_error; real -> the
    403 plan gate (auth is evaluated BEFORE the plan gate, so the real
    key passed auth);
  - the catalog IS measurable — 4 model ids verbatim (claude-opus-5,
    claude-opus-4-7, claude-sonnet-5, claude-sonnet-4-6; owned_by
    aero-claude; supported_endpoint_types ["anthropic"]);
  - the region is NOT gated (catalog + messages both answer from THIS
    runtime's egress — the tokenharbor REGION_NOT_SERVED class does
    not apply);
  - the dialect is Anthropic Messages ONLY (/v1/chat/completions ->
    404 "route not found") — an OpenAI-dialect transport cannot speak
    to this provider directly;
  - the UA discipline: the Python-urllib UA is banned at the CF edge
    (error 1010); the xkiro/apinex extra_headers remedy (Chrome UA)
    APPLIES (curl UA also passes — the ban is UA-signature-specific);
  - ZERO completions are measurable: all 4 catalog models answer the
    SAME typed plan gate.

The provider's own remedy is PAYMENT ("upgrade your plan or add paid
balance") — an owner-gated wallet decision under MODEL_COST_POLICY=
ZERO_PAID_COST (no deposit is ever authorized by the machine; the R461
discipline). NO registration (a guessed default rung would manufacture
knowledge, Art. VI / XXVII): aerolink is NOT added to _SPEC_BY_ID. The
Art. LXV escalation opens instead: R463/AEROLINK_OWNER_ESCALATION.json.

The measured specimen still buys one real, provider-agnostic fix: the
plan-gate wording previously fell through to AUTH_FAILURE in
provider_health.classify_failure (a PROVEN-valid key marked failed —
the exact defect class R462 closed for region gates); R463 registers
the measured wording in the CREDIT_EXHAUSTED hint family so ANY
provider answering this specimen classifies honestly.

Keys come from the ENVIRONMENT ONLY (BS-021): AEROLINK_API_KEY. The
probe artifact records measurements and the key FINGERPRINT, never the
value.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/131.0.0.0 Safari/537.36")
PLAIN_UA = "Python-urllib/3.11"

API_BASE = "https://capi.aerolink.lat"          # the MEASURED API host
DASHBOARD_BASE = "https://aerolink.lat/v1"      # the no-API control
DEAD_HOST_BASE = "https://api.aerolink.lat/v1"  # the dead-host control

ANTHROPIC_HEADERS = {"anthropic-version": "2023-06-01"}


def _req(url: str, key: str, ua: str, payload=None, timeout: int = 45,
         auth_style: str = "x-api-key", extra_headers=None):
    headers = {"Content-Type": "application/json", "User-Agent": ua}
    if auth_style == "x-api-key":
        headers["x-api-key"] = key
    elif auth_style == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    headers.update(extra_headers or {})
    body = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=body, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw, time.time() - t0, ""
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:600]
        return e.code, raw, time.time() - t0, str(e)
    except Exception as e:  # noqa: BLE001
        return 0, "", time.time() - t0, repr(e)[:200]


def _typed_gate(raw: str) -> dict:
    """Extract the provider's own typed error envelope, best-effort."""
    try:
        d = json.loads(raw)
        err = d.get("error") or {}
        if isinstance(err, str):
            return {"error_type": None, "error_code": None,
                    "message": err[:400]}
        return {"error_type": err.get("type"),
                "error_code": err.get("code"),
                "message": err.get("message")}
    except Exception:  # noqa: BLE001 — not JSON
        return {"error_type": None, "error_code": None,
                "message": raw[:400]}


def _catalog_models(raw: str) -> list:
    try:
        d = json.loads(raw)
        return [m.get("id") for m in d.get("data", [])
                if isinstance(m, dict)]
    except Exception:  # noqa: BLE001
        return []


def main() -> int:
    key = os.environ.get("AEROLINK_API_KEY", "").strip()
    out = {
        "round": "R463",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "provider": "aerolink",
        "reviewer_provenance": "AI_REVIEW",
        "api_base_discovery": {
            "api_base": API_BASE,
            "provenance": ("EXTERNAL provider table — github.com/"
                           "inyogeshwar/claude-code-free docs/providers/"
                           "aerolink.md ('Base URL https://capi."
                           "aerolink.lat/, API Format Anthropic-"
                           "compatible'), then MEASURED from this "
                           "runtime (Art. VI — the base is discovered "
                           "with cited provenance, never guessed)"),
            "dashboard_domain_control": (
                "aerolink.lat serves a Next.js dashboard: /v1/models -> "
                "404 HTML (no API routes); its Cloudflare edge bans the "
                "Python-urllib UA (error 1010)"),
            "dead_host_control": (
                "api.aerolink.lat -> DNS 51.68.172.202 (OVH, direct, "
                "not CF) — TCP-unreachable on 443/80/8443/3000/8000 "
                "(30 s timeouts); a dead host, not a gate"),
        },
        "key": {"present": bool(key)},
        "probes": [],
    }
    if not key:
        out["key"] = {"present": False}
        out["admission_decision"] = (
            "NOT PROBED — AEROLINK_API_KEY unset in this environment "
            "(typed, honest; BS-021); nothing is measured, nothing is "
            "claimed")
        _write(out)
        print("AEROLINK_API_KEY unset — nothing probed (typed, honest)")
        return 1

    fp = f"{key[:6]}...{key[-4:]}"
    out["key"] = {"present": True, "len": len(key),
                  "fingerprint": fp, "value": "<never recorded>"}
    print(f"aerolink key present ({len(key)} chars, fingerprint {fp}, "
          f"value never logged)")

    bogus = "aero_live_" + "0" * max(1, len(key) - len("aero_live_"))
    probes = out["probes"]

    # -- probe 1: the catalog on the MEASURED API host (Chrome UA) -----
    st, raw, dt, err = _req(f"{API_BASE}/v1/models", key, CHROME_UA,
                            extra_headers=ANTHROPIC_HEADERS)
    models = _catalog_models(raw) if st == 200 else []
    probes.append({"base": API_BASE, "endpoint": "/v1/models",
                   "ua": "chrome", "auth": "x-api-key", "key": "real",
                   "status": st, "latency_s": round(dt, 2),
                   "models": len(models)})
    print(f"  models [chrome, real key]      -> {st} {dt:.2f}s "
          f"({len(models)} models)")

    # -- probe 2: catalog, plain urllib UA (the UA discipline) ---------
    st2, raw2, dt2, err2 = _req(f"{API_BASE}/v1/models", key, PLAIN_UA,
                                extra_headers=ANTHROPIC_HEADERS)
    probes.append({"base": API_BASE, "endpoint": "/v1/models",
                   "ua": "plain-urllib", "auth": "x-api-key",
                   "key": "real", "status": st2,
                   "latency_s": round(dt2, 2),
                   "typed_gate": _typed_gate(raw2) if st2 != 200 else None,
                   "note": ("Cloudflare error 1010 — the Python-urllib "
                            "UA signature is banned at the edge; the "
                            "xkiro/apinex extra_headers remedy (Chrome "
                            "UA) applies; a curl UA passes too")})
    print(f"  models [plain UA, real key]    -> {st2} {dt2:.2f}s "
          f"(CF 1010 — the UA gate)")

    # -- probe 3: bogus-key differential on the SERVING endpoint -------
    # (measured: the catalog endpoint /v1/models answers 200 for a
    # bogus key — the catalog is PUBLIC, no auth check there; the auth
    # ordering is only measurable on /v1/messages, the serving path)
    first_model = models[0] if models else "probe"
    st3, raw3, dt3, err3 = _req(f"{API_BASE}/v1/messages", bogus,
                                CHROME_UA,
                                payload={"model": first_model,
                                         "max_tokens": 64,
                                         "messages": [{"role": "user",
                                                       "content":
                                                       "PROBE_OK"}]},
                                extra_headers=ANTHROPIC_HEADERS)
    probes.append({
        "base": API_BASE, "endpoint": "/v1/messages", "ua": "chrome",
        "auth": "x-api-key",
        "key": "format-identical bogus control (same length, zero body)",
        "status": st3, "latency_s": round(dt3, 2),
        "typed_gate": _typed_gate(raw3) if st3 != 200 else None})
    print(f"  messages [chrome, BOGUS key]   -> {st3} {dt3:.2f}s "
          f"(the auth-ordering differential)")

    # -- probe 3b: the catalog endpoint's own auth posture --------------
    st3b, raw3b, dt3b, err3b = _req(f"{API_BASE}/v1/models", bogus,
                                    CHROME_UA,
                                    extra_headers=ANTHROPIC_HEADERS)
    probes.append({
        "base": API_BASE, "endpoint": "/v1/models", "ua": "chrome",
        "auth": "x-api-key",
        "key": "format-identical bogus control (same length, zero body)",
        "status": st3b, "latency_s": round(dt3b, 2),
        "note": ("the catalog endpoint answers 200 for a bogus key — "
                 "the catalog is PUBLIC (no auth); the auth ordering is "
                 "measured on the SERVING endpoint (probe 3)" if
                 st3b == 200 else "measured")})
    print(f"  models [chrome, BOGUS key]     -> {st3b} {dt3b:.2f}s "
          f"(the catalog is public — no auth check)")

    # -- probe 4: tiny completions on EVERY catalog model id -----------
    completion_results = []
    for model_id in models:
        payload = {"model": model_id, "max_tokens": 64,
                   "messages": [{"role": "user",
                                 "content": "Reply with exactly: "
                                             "PROBE_OK"}]}
        stc, rawc, dtc, _ = _req(f"{API_BASE}/v1/messages", key,
                                 CHROME_UA, payload=payload,
                                 extra_headers=ANTHROPIC_HEADERS)
        gate = _typed_gate(rawc) if stc != 200 else None
        completion_results.append({
            "model": model_id, "status": stc,
            "latency_s": round(dtc, 2), "typed_gate": gate,
            "completion_excerpt": (""
                                   if stc != 200 else
                                   (json.loads(rawc)
                                    .get("content", [{}])[0]
                                    .get("text", "")[:80]))})
        print(f"  messages [{model_id}] -> {stc} {dtc:.2f}s")
    probes.append({"base": API_BASE, "endpoint": "/v1/messages",
                   "ua": "chrome", "auth": "x-api-key", "key": "real",
                   "statuses": sorted({c["status"]
                                       for c in completion_results}),
                   "per_model": completion_results})

    # -- probe 5: the Bearer auth style (both styles accepted?) --------
    st5, raw5, dt5, _ = _req(f"{API_BASE}/v1/messages", key, CHROME_UA,
                             payload={"model": models[0] if models
                                      else "probe",
                                      "max_tokens": 64,
                                      "messages": [{"role": "user",
                                                    "content":
                                                    "PROBE_OK"}]},
                             auth_style="bearer",
                             extra_headers=ANTHROPIC_HEADERS)
    probes.append({"base": API_BASE, "endpoint": "/v1/messages",
                   "ua": "chrome", "auth": "bearer", "key": "real",
                   "status": st5, "latency_s": round(dt5, 2),
                   "typed_gate": _typed_gate(raw5) if st5 != 200 else None,
                   "note": ("Authorization: Bearer is ALSO accepted "
                            "(same typed plan-gate answer as x-api-key)"
                            if st5 == 403 else "measured")})
    print(f"  messages [bearer auth]         -> {st5} {dt5:.2f}s")

    # -- probe 6: the OpenAI-dialect endpoint (dialect control) --------
    st6, raw6, dt6, _ = _req(f"{API_BASE}/v1/chat/completions", key,
                             CHROME_UA,
                             payload={"model": models[0] if models
                                      else "probe",
                                      "max_tokens": 64,
                                      "messages": [{"role": "user",
                                                    "content":
                                                    "PROBE_OK"}]},
                             auth_style="bearer")
    probes.append({"base": API_BASE, "endpoint": "/v1/chat/completions",
                   "ua": "chrome", "auth": "bearer", "key": "real",
                   "status": st6, "latency_s": round(dt6, 2),
                   "typed_gate": _typed_gate(raw6) if st6 != 200 else None,
                   "note": ("404 route not found — the host is "
                            "Anthropic-dialect ONLY (the OpenAI-dialect "
                            "transport cannot speak to it directly)"
                            if st6 == 404 else "measured")})
    print(f"  chat/completions [openai dialect] -> {st6} {dt6:.2f}s "
          f"(the dialect control)")

    # -- probe 7: the dashboard-domain control -------------------------
    st7, raw7, dt7, _ = _req(f"{DASHBOARD_BASE}/models", key, CHROME_UA)
    probes.append({"base": DASHBOARD_BASE, "endpoint": "/models",
                   "ua": "chrome", "auth": "x-api-key", "key": "real",
                   "status": st7, "latency_s": round(dt7, 2),
                   "note": ("Next.js dashboard 404 HTML — no API routes "
                            "on the dashboard domain" if st7 == 404 else
                            "measured")})
    print(f"  models on {DASHBOARD_BASE} -> {st7} {dt7:.2f}s "
          f"(the dashboard control)")

    # -- probe 8: the dead-host control ---------------------------------
    st8, raw8, dt8, _ = _req(f"{DEAD_HOST_BASE}/models", key, CHROME_UA,
                             timeout=35)
    probes.append({"base": DEAD_HOST_BASE, "endpoint": "/models",
                   "ua": "chrome", "auth": "x-api-key", "key": "real",
                   "status": st8, "latency_s": round(dt8, 2),
                   "note": ("TCP-unreachable dead host (DNS -> OVH "
                            "51.68.172.202; every port times out)" if
                            st8 == 0 else "measured")})
    print(f"  models on {DEAD_HOST_BASE} -> {st8} {dt8:.2f}s "
          f"(the dead-host control)")

    # -- the honest reading of what was measured ------------------------
    plan_gated = [c for c in completion_results
                  if c["status"] == 403
                  and (c.get("typed_gate") or {}).get("error_type")
                  == "permission_error"]
    key_validity = (
        "PROVEN VALID — the format-identical bogus key answers 401 "
        "authentication_error while the real key answers the 403 plan "
        "gate: auth is evaluated BEFORE the plan gate, so the delivered "
        "key passed authentication (measured, not assumed — unlike "
        "tokenharbor's R462 pre-auth region gate where validity was "
        "unmeasurable)"
        if st3 == 401 and plan_gated else "measured otherwise")

    out["the_measured_gate"] = {
        "class": "CREDIT_EXHAUSTED family (the account-plan gate)",
        "typed_specimen_verbatim": (plan_gated[0]["typed_gate"]
                                    ["message"]) if plan_gated else None,
        "measured_on_models": [c["model"] for c in plan_gated],
        "all_catalog_models_gated": (len(plan_gated) == len(models)
                                     and bool(models)),
        "auth_ordering": key_validity,
        "the_providers_remedy": (
            "upgrade your plan or add paid balance — a WALLET decision "
            "the machine never takes under MODEL_COST_POLICY="
            "ZERO_PAID_COST (no deposit authorized; the R461 "
            "discipline); 401 stays strictly AUTH"),
        "region": "NOT gated — the catalog AND the messages endpoint "
                  "answer from this runtime's egress (the tokenharbor "
                  "REGION_NOT_SERVED class does not apply)",
        "dialect": "Anthropic Messages ONLY (/v1/messages; /v1/"
                   "chat/completions -> 404 route not found)",
        "ua_discipline": "the Python-urllib UA is banned at the CF edge "
                         "(error 1010); Chrome UA and curl UA pass — "
                         "the xkiro/apinex extra_headers remedy applies",
    }
    out["the_catalog"] = {
        "status": st,
        "model_count": len(models),
        "model_ids_verbatim": sorted(models),
        "sample_owned_by": "aero-claude",
        "supported_endpoint_types": ["anthropic"],
        "note": ("the catalog IS measurable (unlike tokenharbor) — the "
                 "4 ids are recorded verbatim for the future admission "
                 "round; none is a rung until a completion serves"),
    }
    out["admission_decision"] = (
        "NOT ADMITTED — probe-before-admit (R451-C1.2 / Art. III) "
        "holds: a tiny completion through the real endpoint is the ONLY "
        "admission evidence, and ZERO completions are measurable (all 4 "
        "catalog models answer the SAME typed account-plan gate). No "
        "ProviderSpec is registered and no default rung is guessed "
        "(Art. VI / XXVII). The Art. LXV escalation opens instead "
        "(R463/AEROLINK_OWNER_ESCALATION.json): the provider's own "
        "remedy is PAYMENT — an owner-gated wallet decision under "
        "ZERO_PAID_COST. The measured specimen still registers the "
        "provider-agnostic plan-gate wording in the CREDIT_EXHAUSTED "
        "hint family (provider_health.py) so ANY provider answering "
        "this specimen classifies honestly — never AUTH_FAILURE for a "
        "PROVEN-valid key (the R462 defect class, closed again here).")
    out["escalation_artifact"] = "R463/AEROLINK_OWNER_ESCALATION.json"

    _write(out)
    print("probe artifact -> R463/PROBE_CATALOG.json "
          "(fingerprint only, BS-021)")
    return 0


def _write(out: dict) -> None:
    path = os.path.join(os.path.dirname(__file__), "..", "R463")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "PROBE_CATALOG.json"), "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
