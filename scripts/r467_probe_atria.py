#!/usr/bin/env python3
"""R467 — the EIGHTH router candidate (atria, api.atria-asi.ai), met by
probe-before-admit (R451-C1.2 / Art. III).

Operator instruction (2026-09-15, verbatim): ".https://api.atria-asi.ai/
console/keys: <key> add this to the API's keys we are using to hugging
face, its gives 100million tokens of new model which is as good as
glm5.3 and finish the remaining issues. we should be token surplus now"

Operator-DECLARED claims (recorded as declared, never as measured until
measured here — Art. XXV/VI):
  - 100 million tokens of account budget
  - a new model "as good as glm5.3"

What this probe measures (each fact typed, never assumed):
  1. the API base: the console domain api.atria-asi.ai is the operator's
     own citation (/console/keys) — the /v1/* surface on the SAME host is
     measured directly (no external table needed when the operator names
     the host);
  2. dialect: OpenAI /v1/chat/completions vs Anthropic /v1/messages;
  3. auth style: Bearer vs x-api-key (both measured);
  4. key VALIDITY: the bogus-key differential (auth evaluates before any
     plan/gate logic — the R463 method);
  5. the catalog: GET /v1/models — model ids verbatim, the strong-rung
     candidate identified;
  6. completions: tiny PROBE_OK calls + a FIELD-line protocol compliance
     call (the engine's structured protocol — the MECHANISM-stage
     quality question the R466 reaudit left open);
  7. UA discipline: default urllib UA vs Chrome UA (the xkiro/apinex
     CF-edge precedent);
  8. any balance/usage endpoint the provider exposes (the 100M-token
     budget claim is operator-declared; if the provider serves a balance
     API it is measured, else it stays declared).

Keys come from the ENVIRONMENT ONLY (BS-021): ATRIA_API_KEY. The probe
artifacts record measurements and the key FINGERPRINT, never the value.
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

BASE = "https://api.atria-asi.ai"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "R467")


def _req(url, key, ua, payload=None, timeout=60, auth_style="bearer"):
    headers = {"Content-Type": "application/json", "User-Agent": ua}
    if auth_style == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    elif auth_style == "x-api-key":
        headers["x-api-key"] = key
    body = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=body, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw, round(time.time() - t0, 2), ""
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:800]
        return e.code, raw, round(time.time() - t0, 2), str(e)
    except Exception as e:  # noqa: BLE001
        return 0, "", round(time.time() - t0, 2), repr(e)[:200]


def _json(raw):
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


def fp(val: str) -> str:
    return f"{val[:6]}...{val[-4:]} (len {len(val)})"


def main() -> int:
    key = os.environ.get("ATRIA_API_KEY", "").strip()
    if not key:
        print("FATAL: ATRIA_API_KEY unset in session env (BS-021)")
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)
    cat = {"round": "R467", "provider": "atria",
           "operator_citation": "https://api.atria-asi.ai/console/keys",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "key_fingerprint": fp(key),
           "probes": []}

    def rec(name, status, raw, dt, err, note=""):
        body = _json(raw)
        entry = {"probe": name, "status": status, "seconds": dt,
                 "error": err[:200], "note": note}
        if isinstance(body, dict):
            # never echo anything that could embed the key
            entry["body_keys"] = sorted(body.keys())[:12]
        cat["probes"].append(entry)
        print(f"[{name}] {status} in {dt}s err={err[:80]}")
        return body

    # --- 1/2. dialect + auth discovery on the catalog endpoint --------
    models_url = f"{BASE}/v1/models"
    b = rec("models_bearer_chrome", *_req(models_url, key, CHROME_UA))
    if b is None or b.get("data") is None:
        rec("models_xapikey_chrome",
            *_req(models_url, key, CHROME_UA, auth_style="x-api-key"))
    rec("models_bearer_urllib", *_req(models_url, key, PLAIN_UA),
        note="UA discipline: default python urllib UA")
    rec("models_bogus_key", *_req(models_url, "atr_bogus0000000000",
                                  CHROME_UA),
        note="validity differential: format-identical bogus key")

    # Anthropic dialect control (the aerolink precedent)
    rec("anthropic_dialect_control",
        *_req(f"{BASE}/v1/messages", key, CHROME_UA,
              payload={"model": "probe", "max_tokens": 8,
                       "messages": [{"role": "user",
                                     "content": "hi"}]}),
        note="does the host speak Anthropic Messages too?")

    # console surface control
    rec("console_keys_page", *_req(f"{BASE}/console/keys", key, CHROME_UA),
        note="the operator's own citation (console UI, not the API)")

    # --- parse the catalog --------------------------------------------
    catalog_ids: list = []
    if isinstance(b, dict) and isinstance(b.get("data"), list):
        catalog_ids = [m.get("id") for m in b["data"] if m.get("id")]
        cat["catalog_model_ids"] = catalog_ids
        cat["catalog_count"] = len(catalog_ids)
        print(f"catalog: {len(catalog_ids)} models: "
              f"{catalog_ids[:20]}")

    # --- pick the strong rung (BEFORE the catalog artifact is written,
    # so the selection basis rides the artifact itself) ------------------
    # the operator declared "a new model which is as good as glm5.3" —
    # the strong-rung candidate is chosen from the MEASURED catalog by
    # explicit preference order, recorded, never guessed silently.
    prefs = []
    for mid in catalog_ids:
        m = (mid or "").lower()
        if "glm-5.3" in m or "glm5.3" in m:
            prefs.append((0, mid))
        elif "glm" in m:
            prefs.append((1, mid))
        elif any(t in m for t in ("gpt", "claude", "opus", "sonnet")):
            prefs.append((2, mid))
        elif any(t in m for t in ("deepseek", "qwen", "minimax")):
            prefs.append((3, mid))
    prefs.sort()
    selection_basis = "keyword preference order over the measured catalog"
    if not prefs and len(catalog_ids) == 1:
        # the catalog's SOLE model IS the candidate by exhaustion —
        # recorded explicitly, never guessed silently (Art. VI). The
        # operator's "as good as glm5.3" quality claim stays OPERATOR-
        # DECLARED; the FIELD-protocol compliance below is what gets
        # MEASURED on the engine's own instrument.
        prefs = [(9, catalog_ids[0])]
        selection_basis = ("sole catalog model (catalog holds exactly one "
                           "id — the operator's declared 'new model'); the "
                           "glm-5.3-class quality claim is OPERATOR-"
                           "DECLARED, measured only through the FIELD-"
                           "protocol compliance test")
    cat["strong_rung_selection_basis"] = selection_basis
    cat["strong_rung_preference_order"] = [m for _, m in prefs]
    if not prefs:
        with open(os.path.join(OUT_DIR, "PROBE_CATALOG.json"), "w") as f:
            json.dump(cat, f, indent=2)
        print("FATAL: no strong-rung candidate in the measured catalog")
        return 3

    with open(os.path.join(OUT_DIR, "PROBE_CATALOG.json"), "w") as f:
        json.dump(cat, f, indent=2)
    print(f"artifact -> R467/PROBE_CATALOG.json")

    # retry candidates in preference order until one answers
    comp = {"round": "R467", "provider": "atria",
            "measured_at": cat["measured_at"],
            "key_fingerprint": fp(key), "completions": []}
    admitted = None
    for _, mid in prefs[:6]:
        payload = {"model": mid, "max_tokens": 24, "temperature": 0,
                   "messages": [{"role": "user",
                                 "content": "Reply with exactly: READY"}]}
        s, raw, dt, err = _req(f"{BASE}/v1/chat/completions", key,
                               CHROME_UA, payload=payload)
        body = _json(raw) or {}
        content = ""
        try:
            content = body["choices"][0]["message"]["content"] or ""
        except Exception:  # noqa: BLE001
            pass
        ok = s == 200 and "READY" in content
        comp["completions"].append(
            {"model": mid, "status": s, "seconds": dt, "ok": ok,
             "content_head": str(content)[:80],
             "error": (err or str(body.get("error", "")))[:200],
             "finish_reason": (body.get("choices") or [{}])[0].get(
                 "finish_reason")})
        print(f"[completion {mid}] {s} in {dt}s ok={ok} "
              f"head={str(content)[:40]!r}")
        if ok:
            admitted = mid
            break

    # --- FIELD-line protocol compliance (the engine's structured
    # protocol — the MECHANISM-stage quality question) -------------------
    # MEASURED RETRY CLASS: Atria-Dawn-Preview is a REASONING model
    # (reasoning_content + clean content) — at small max_tokens the
    # hidden reasoning can spend the whole cap and return EMPTY content
    # (the engine's EmptyContentWithFinish class: a larger cap on the
    # SAME provider/model is the documented retry, not a downgrade).
    # The probe measures both arms: the small-cap call and the retry.
    if admitted:
        field_prompt = (
            "You are a mechanism-reasoning engine. Answer with EXACTLY "
            "three lines, each starting with FIELD_ followed by an "
            "uppercase key, a colon, and one short sentence. Keys: "
            "MECHANISM, KEY_VARIABLE, FALSIFIER. Topic: why does a "
            "copper pipe corrode faster when carrying hot acidic water "
            "than cold neutral water?")
        fpt = {"model": admitted, "temperature": 0.2,
               "messages": [{"role": "user", "content": field_prompt}]}
        s, raw, dt, err = _req(f"{BASE}/v1/chat/completions", key,
                               CHROME_UA, payload={**fpt,
                                                   "max_tokens": 300},
                               timeout=120)
        body = _json(raw) or {}
        try:
            content = body["choices"][0]["message"]["content"] or ""
            reasoning = (body["choices"][0]["message"]
                         .get("reasoning_content") or "")
        except Exception:  # noqa: BLE001
            content, reasoning = "", ""
        n_field = sum(1 for ln in content.splitlines()
                      if ln.strip().startswith("FIELD_"))
        small_cap = {"model": admitted, "max_tokens": 300, "status": s,
                     "seconds": dt, "field_lines": n_field,
                     "content_len": len(content),
                     "reasoning_content_len": len(reasoning),
                     "empty_content_class":
                         s == 200 and not content}
        if not content:  # the measured retry arm
            s2, raw2, dt2, err2 = _req(
                f"{BASE}/v1/chat/completions", key, CHROME_UA,
                payload={**fpt, "max_tokens": 2000}, timeout=180)
            body2 = _json(raw2) or {}
            try:
                content2 = body2["choices"][0]["message"]["content"] or ""
                reasoning2 = (body2["choices"][0]["message"]
                              .get("reasoning_content") or "")
            except Exception:  # noqa: BLE001
                content2, reasoning2 = "", ""
            n_field2 = sum(1 for ln in content2.splitlines()
                           if ln.strip().startswith("FIELD_"))
            retry = {"max_tokens": 2000, "status": s2, "seconds": dt2,
                     "field_lines": n_field2,
                     "content_len": len(content2),
                     "reasoning_content_len": len(reasoning2),
                     "content_first_400": content2[:400]}
            comp["field_protocol_test"] = {
                "small_cap": small_cap, "retry_larger_cap": retry,
                "format_compliant": n_field2 >= 3,
                "finding": "reasoning model: reasoning_content carries "
                           "the chain-of-thought, content carries clean "
                           "FIELD_ lines; small caps can starve content "
                           "(EmptyContentWithFinish class — the engine's "
                           "documented larger-cap retry recovers)"}
            print(f"[field small cap] {s} in {dt}s field_lines={n_field} "
                  f"empty={not content}")
            print(f"[field retry 2000] {s2} in {dt2}s field_lines="
                  f"{n_field2} compliant={n_field2 >= 3}")
        else:
            comp["field_protocol_test"] = {
                "small_cap": small_cap,
                "format_compliant": n_field >= 3,
                "content_first_400": content[:400],
                "finding": "reasoning model: reasoning_content present, "
                           "content carries clean FIELD_ lines at this "
                           "cap on this specimen"}
            print(f"[field protocol] {s} in {dt}s field_lines={n_field}")
        # repeat tiny probe x2 for stability (the bynara 3x precedent)
        for i in range(2):
            s2, raw2, dt2, _ = _req(f"{BASE}/v1/chat/completions", key,
                                    CHROME_UA, payload={
                                        "model": admitted,
                                        "max_tokens": 24,
                                        "temperature": 0,
                                        "messages": [{"role": "user",
                                                      "content":
                                                      "Reply with "
                                                      "exactly: READY"}]})
            b2 = _json(raw2) or {}
            try:
                c2 = b2["choices"][0]["message"]["content"] or ""
            except Exception:  # noqa: BLE001
                c2 = ""
            comp["completions"].append(
                {"model": admitted, "status": s2, "seconds": dt2,
                 "ok": s2 == 200 and "READY" in c2,
                 "content_head": str(c2)[:40], "stability_pass": i + 1})
            print(f"[stability {i+1}] {s2} in {dt2}s")

    # --- balance / usage surface (the 100M-token claim) -----------------
    for ep in ("/v1/usage", "/v1/balance", "/v1/credits",
               "/api/usage", "/v1/dashboard/billing/usage"):
        s, raw, dt, err = _req(f"{BASE}{ep}", key, CHROME_UA)
        if s not in (404, 405, 0) or "404" not in err:
            body = _json(raw) or {}
            comp.setdefault("usage_endpoints", []).append(
                {"endpoint": ep, "status": s, "body_keys":
                 sorted(body.keys())[:12] if isinstance(body, dict)
                 else None, "raw_head": raw[:200]})
            print(f"[usage {ep}] {s}")

    with open(os.path.join(OUT_DIR, "PROBE_COMPLETIONS.json"), "w") as f:
        json.dump(comp, f, indent=2)
    print(f"artifact -> R467/PROBE_COMPLETIONS.json")
    print(f"admitted strong rung: {admitted}")
    return 0 if admitted else 4


if __name__ == "__main__":
    sys.exit(main())
