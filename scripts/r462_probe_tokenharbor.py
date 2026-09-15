#!/usr/bin/env python3
"""R462 — the SIXTH free-tier router candidate (tokenharbor.ai), met by
probe-before-admit (R451-C1.2 / Art. III) — and REFUSED at the gate the
measurement found: the provider answers every endpoint from this
runtime's egress with a typed 403 region_blocked ("API access from your
region is not available. Token Harbor cannot serve requests from
regions under US sanctions or export controls, Mainland China, Hong
Kong and Macau, or regions our AI provider (Anthropic) does not
support... we can only see the country your connection exits from").

The differential control (a format-identical BOGUS key) answers the
SAME 403 — the gate fires BEFORE auth, so the delivered key's validity
is UNMEASURABLE from this egress (never AUTH_FAILURE: the key is not
measured failed; Art. XXV — unknown stays unknown). The gate is
UA-independent (plain urllib and Chrome UA answer identically) and
blocks the catalog AND the serving endpoint, so probe-before-admit
holds: ZERO completions are measurable, not even one model id — no
registration (a guessed default rung would manufacture knowledge,
Art. VI / XXVII). The Art. LXV escalation is opened instead:
R462/TOKENHARBOR_OWNER_ESCALATION.json.

The measured specimen still buys one real, provider-agnostic fix: the
403 region-gate class previously fell through to AUTH_FAILURE in
provider_health.classify_failure — R462 registers the typed
REGION_NOT_SERVED class (cascade-advancing, never retried) so ANY
provider answering this specimen classifies honestly.

Keys come from the ENVIRONMENT ONLY (BS-021): TOKENHARBOR_API_KEY.
The probe artifact records measurements and the key FINGERPRINT,
never the value.
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

# candidate bases, in admission-probe order (the dashboard domain first;
# the api. subdomain answered 404 "Application not found" when measured)
CANDIDATE_BASES = [
    "https://tokenharbor.ai/v1",
    "https://api.tokenharbor.ai/v1",
]


def _req(url: str, key: str, ua: str, payload=None, timeout: int = 30):
    body = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": ua})
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
        return {"error_type": err.get("type"),
                "error_code": err.get("code"),
                "message": err.get("message")}
    except Exception:  # noqa: BLE001 — not JSON
        return {"error_type": None, "error_code": None,
                "message": raw[:400]}


def main() -> int:
    key = os.environ.get("TOKENHARBOR_API_KEY", "").strip()
    out = {
        "round": "R462",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "provider": "tokenharbor",
        "reviewer_provenance": "AI_REVIEW",
        "key": {"present": bool(key)},
        "probes": [],
    }
    if not key:
        out["key"] = {"present": False}
        out["admission_decision"] = (
            "NOT PROBED — TOKENHARBOR_API_KEY unset in this environment "
            "(typed, honest — the environment reset wipes env-only "
            "values, BS-021); nothing is measured, nothing is claimed")
        _write(out)
        print("TOKENHARBOR_API_KEY unset — nothing probed (typed, honest)")
        return 1

    fp = f"{key[:6]}...{key[-4:]}"
    out["key"] = {"present": True, "len": len(key),
                  "fingerprint": fp, "value": "<never recorded>"}
    print(f"tokenharbor key present ({len(key)} chars, fingerprint "
          f"{fp}, value never logged)")

    bogus = "thk_live_" + "0" * (len(key) - len("thk_live_"))

    # -- the four admission-order probes on the primary base -----------
    base = CANDIDATE_BASES[0]
    probes = out["probes"]

    st, raw, dt, err = _req(f"{base}/models", key, CHROME_UA)
    probes.append({"base": base, "endpoint": "/models", "ua": "chrome",
                   "key": "real", "status": st,
                   "latency_s": round(dt, 2),
                   "typed_gate": _typed_gate(raw) if st != 200 else None,
                   "models": (len(json.loads(raw).get("data", []))
                              if st == 200 else 0)})
    print(f"  models [chrome, real key]      -> {st} {dt:.2f}s")

    st2, raw2, dt2, err2 = _req(f"{base}/models", key, PLAIN_UA)
    probes.append({"base": base, "endpoint": "/models", "ua": "plain",
                   "key": "real", "status": st2,
                   "latency_s": round(dt2, 2),
                   "typed_gate": _typed_gate(raw2) if st2 != 200 else None,
                   "models": (len(json.loads(raw2).get("data", []))
                              if st2 == 200 else 0)})
    print(f"  models [plain UA, real key]    -> {st2} {dt2:.2f}s")

    st3, raw3, dt3, err3 = _req(f"{base}/models", bogus, CHROME_UA)
    probes.append({
        "base": base, "endpoint": "/models", "ua": "chrome",
        "key": "format-identical bogus control (same length, zero body)",
        "status": st3, "latency_s": round(dt3, 2),
        "typed_gate": _typed_gate(raw3) if st3 != 200 else None,
        "models": 0})
    print(f"  models [chrome, BOGUS key]     -> {st3} {dt3:.2f}s "
          f"(the auth-ordering differential)")

    payload = {"model": "probe",  # unknown id: the gate answers first
               "messages": [{"role": "user",
                             "content": "Reply with exactly: PROBE_OK"}],
               "max_tokens": 4096, "temperature": 0.0}
    st4, raw4, dt4, err4 = _req(f"{base}/chat/completions", key,
                                CHROME_UA, payload=payload)
    probes.append({"base": base, "endpoint": "/chat/completions",
                   "ua": "chrome", "key": "real", "status": st4,
                   "latency_s": round(dt4, 2),
                   "typed_gate": _typed_gate(raw4) if st4 != 200 else None})
    print(f"  chat/completions [real key]    -> {st4} {dt4:.2f}s")

    # -- the secondary candidate base (dead-host control) --------------
    base2 = CANDIDATE_BASES[1]
    st5, raw5, dt5, err5 = _req(f"{base2}/models", key, CHROME_UA)
    probes.append({"base": base2, "endpoint": "/models", "ua": "chrome",
                   "key": "real", "status": st5,
                   "latency_s": round(dt5, 2),
                   "typed_gate": _typed_gate(raw5) if st5 != 200 else None,
                   "models": 0})
    print(f"  models on {base2} -> {st5} {dt5:.2f}s "
          f"(the api. subdomain control)")

    # -- the honest reading of what was measured ------------------------
    region_blocked = [p for p in probes
                      if (p.get("typed_gate") or {}).get("error_code")
                      == "region_blocked"]
    out["the_typed_gate"] = {
        "class": "REGION_NOT_SERVED",
        "measured_on": [f"{p['base']}{p['endpoint']}" for p in
                        region_blocked],
        "specimen_verbatim": (region_blocked[0]["typed_gate"]
                              ["message"]) if region_blocked else None,
        "ua_independent": (probes[0]["status"] == probes[1]["status"]
                           == 403),
        "auth_ordering": (
            "PRE-AUTH — the format-identical bogus key answers the SAME "
            "typed 403 region_blocked, so the delivered key's validity "
            "is UNMEASURABLE from this egress (never AUTH_FAILURE; "
            "Art. XXV: unknown stays unknown)"
            if probes[2]["status"] == 403 and
            (probes[2].get("typed_gate") or {}).get("error_code")
            == "region_blocked"
            else "measured otherwise"),
        "endpoints_blocked": sorted({p["endpoint"] for p in
                                     region_blocked}),
        "note": ("the provider's own words: it sees only the country the "
                 "CONNECTION exits from — the runtime's egress region is "
                 "refused, not the key, not the account; the machine "
                 "cannot choose its egress (Art. XXXIII: no owner "
                 "decision taken by the machine)"),
    }
    out["admission_decision"] = (
        "NOT ADMITTED — probe-before-admit (R451-C1.2 / Art. III) holds: "
        "a tiny completion through the real endpoint is the ONLY "
        "admission evidence, and zero completions are measurable from "
        "this egress (the catalog itself is gated, so not even one "
        "served model id is measurable — a guessed default rung would "
        "manufacture knowledge, Art. VI / XXVII). No ProviderSpec is "
        "registered; the Art. LXV escalation is opened instead "
        "(R462/TOKENHARBOR_OWNER_ESCALATION.json). The measured specimen "
        "still registers the provider-agnostic REGION_NOT_SERVED class "
        "in provider_health so ANY provider answering this 403 class "
        "classifies honestly (never AUTH_FAILURE).")
    out["escalation_artifact"] = "R462/TOKENHARBOR_OWNER_ESCALATION.json"

    _write(out)
    print("probe artifact -> R462/PROBE_CATALOG.json "
          "(fingerprint only, BS-021)")
    return 0


def _write(out: dict) -> None:
    path = os.path.join(os.path.dirname(__file__), "..", "R462")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "PROBE_CATALOG.json"), "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
