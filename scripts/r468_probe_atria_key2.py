#!/usr/bin/env python3
"""R468 — validate the operator's SECOND atria key (ATRIA_API_KEY_2)
before it is persisted (probe-before-record; the R463/R467 method).

Operator instruction (2026-09-16, verbatim, key bodies redacted BS-021):
  "https://api.atria-asi.ai/console/keys: atr_6...Ku5f and atr_7...HJmm"
  "huggingface API : hf_M...NkNM"
  "save all these huggingface secret, and write in your constitution to
   look it up in huggingface secret, so you dont keep asking me again"

What this probe measures (typed, never assumed):
  1. key-1 IDENTITY: the re-supplied ATRIA_API_KEY fingerprint must match
     the R467-recorded fingerprint (the live registered credential —
     confirming the operator re-supplied the SAME key, not a rotation);
  2. key-2 VALIDITY: the bogus-key differential on GET /v1/models (auth
     evaluates before any plan/gate logic — the R463 method);
  3. key-2 CATALOG: same sole model as the R467 measurement
     (Atria-Dawn-Preview) — or whatever the catalog serves, verbatim;
  4. key-2 COMPLETION: one tiny PROBE_OK call (the R467 instrument).

Keys come from the ENVIRONMENT ONLY (BS-021). The artifact records
measurements and FINGERPRINTS, never values.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

PLAIN_UA = "Python-urllib/3.11"
BASE = "https://api.atria-asi.ai"
BOGUS = "atr_bogus differential key 000000000000000000"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "R468")


def _req(url, key, payload=None, timeout=60):
    headers = {"Content-Type": "application/json",
               "User-Agent": PLAIN_UA,
               "Authorization": f"Bearer {key}"}
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
    key1 = os.environ.get("ATRIA_API_KEY", "").strip()
    key2 = os.environ.get("ATRIA_API_KEY_2", "").strip()
    if not key2:
        print("FATAL: ATRIA_API_KEY_2 unset in session env (BS-021)")
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)

    out = {"round": "R468", "provider": "atria",
           "subject": "the operator's SECOND atria key (ATRIA_API_KEY_2) "
                      "— the backup/rotation credential supplied 2026-09-16",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "key2_fingerprint": fp(key2),
           "probes": []}

    # 1. key-1 identity vs the R467 record (consistency, not admission)
    r467 = None
    try:
        with open(os.path.join(REPO, "R467", "PROBE_CATALOG.json")) as f:
            r467 = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    if key1 and r467:
        recorded = r467.get("key_fingerprint", "")
        same = (recorded == fp(key1))
        out["key1_identity_check"] = {
            "r467_recorded_fingerprint": recorded,
            "resupplied_fingerprint": fp(key1),
            "same_key": same,
            "note": "the operator re-supplied the SAME live credential "
                    "R467 validated and registered" if same else
                    "DIFFERENT from the R467 key — a rotation signal; "
                    "escalate before treating either as live",
        }
        print(f"[key1_identity] same_key={same}")

    # 2. bogus-key differential on the catalog (the R463 validity method)
    s_bogus, raw_b, dt_b, err_b = _req(f"{BASE}/v1/models", BOGUS)
    out["probes"].append({"probe": "models_bogus_key",
                          "status": s_bogus, "seconds": dt_b,
                          "error": err_b[:200],
                          "note": "the validity differential control"})
    print(f"[models_bogus_key] {s_bogus} in {dt_b}s")

    # 3. key-2 catalog
    s_cat, raw_c, dt_c, err_c = _req(f"{BASE}/v1/models", key2)
    body_c = _json(raw_c)
    ids = []
    if isinstance(body_c, dict) and isinstance(body_c.get("data"), list):
        ids = [m.get("id") for m in body_c["data"] if m.get("id")]
    out["probes"].append({"probe": "models_key2", "status": s_cat,
                          "seconds": dt_c, "error": err_c[:200],
                          "model_ids": ids,
                          "body_keys": sorted(body_c.keys())[:12]
                          if isinstance(body_c, dict) else []})
    print(f"[models_key2] {s_cat} in {dt_c}s ids={ids}")

    valid = (s_cat == 200 and s_bogus in (401, 403)
             and s_cat != s_bogus)
    out["key2_validity"] = {
        "differential": f"catalog {s_cat} with key2 vs {s_bogus} with "
                        f"bogus key",
        "valid": valid,
        "note": "auth evaluates before plan/gate logic (the R463 method)"
                if valid else "the differential did not separate — "
                "do not persist as valid",
    }

    # 4. key-2 tiny completion (the R467 PROBE_OK instrument)
    comp_ok, comp_note = False, ""
    if valid and ids:
        payload = {"model": ids[0],
                   "messages": [{"role": "user",
                                 "content": "Reply with exactly: PROBE_OK"}],
                   "max_tokens": 4096, "temperature": 0}
        s_cmp, raw_m, dt_m, err_m = _req(
            f"{BASE}/v1/chat/completions", key2, payload)
        body_m = _json(raw_m)
        content = ""
        if isinstance(body_m, dict) and body_m.get("choices"):
            content = (body_m["choices"][0].get("message", {})
                       .get("content") or "")
        comp_ok = (s_cmp == 200 and bool(content.strip()))
        out["probes"].append({
            "probe": "completion_key2", "status": s_cmp, "seconds": dt_m,
            "error": err_m[:200],
            "content_nonempty": bool(content.strip()),
            "finish_reason": (body_m["choices"][0].get("finish_reason")
                              if isinstance(body_m, dict)
                              and body_m.get("choices") else None),
            "note": "tiny PROBE_OK call; the R467 small-cap starvation "
                    "lesson applied (4096 cap for the reasoning model)",
        })
        comp_note = content.strip()[:60]
        print(f"[completion_key2] {s_cmp} in {dt_m}s "
              f"content_nonempty={bool(content.strip())}")

    out["verdict"] = {
        "key2_valid": valid,
        "completion_ok": comp_ok,
        "role": "backup/rotation credential — NOT wired into the engine "
                "(the R467 registration reads exactly ATRIA_API_KEY, "
                "one key; the second key is persisted for rotation "
                "durability per the operator's save-all directive)",
    }

    path = os.path.join(OUT_DIR, "PROBE_ATRIA_KEY2.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"artifact -> R468/PROBE_ATRIA_KEY2.json (fingerprints only)")
    print(f"verdict: key2_valid={valid} completion_ok={comp_ok}")
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
