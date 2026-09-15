#!/usr/bin/env python3
"""R469 — validate the operator's THIRD atria key (ATRIA_API_KEY_3)
before it is persisted (probe-before-record; the R463/R467/R468 method).

Operator instruction (2026-09-16, verbatim, key bodies redacted BS-021):
  "https://api.atria-asi.ai/console/keys: atr_6...Ku5f and
   atr_7...HJmm and atr_Q...ILrJ"
  "From Now on atira is out default API for discovery engine. Keep
   going to a new key of atira if one is exhausted. Wire it in the
   discovery engine. 4 api keys is 400million tokens"

What this probe measures (typed, never assumed):
  1. key-1/key-2 IDENTITY: the env-held ATRIA_API_KEY / ATRIA_API_KEY_2
     fingerprints must match the R467/R468-recorded fingerprints (the
     live registered credentials — confirming continuity, not rotation);
  2. key-3 VALIDITY: the bogus-key differential on GET /v1/models (auth
     evaluates before any plan/gate logic — the R463 method);
  3. key-3 CATALOG: same sole model as the R467/R468 measurements
     (Atria-Dawn-Preview) — or whatever the catalog serves, verbatim;
  4. key-3 COMPLETION: one tiny PROBE_OK call (the R467 instrument,
     4096 cap for the reasoning model);
  5. RING VIEW: all three keys' catalog statuses side by side (the
     ring the R469 wiring will rotate through).

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
OUT_DIR = os.path.join(REPO, "R469")


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
    return f"{val[:6]}...{val[-4:]} (len {len(val)})" if val else "(unset)"


def main() -> int:
    key1 = os.environ.get("ATRIA_API_KEY", "").strip()
    key2 = os.environ.get("ATRIA_API_KEY_2", "").strip()
    key3 = os.environ.get("ATRIA_API_KEY_3", "").strip()
    if not key3:
        print("FATAL: ATRIA_API_KEY_3 unset in session env (BS-021)")
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)

    out = {"round": "R469", "provider": "atria",
           "subject": "the operator's THIRD atria key (ATRIA_API_KEY_3) "
                      "— the ring's third credential supplied 2026-09-16; "
                      "the R469 directive makes atria the DEFAULT "
                      "provider with key-ring rotation on exhaustion",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "key3_fingerprint": fp(key3),
           "probes": []}

    # 1. key-1/key-2 identity vs the R467/R468 records (continuity check)
    rec1 = rec2 = None
    try:
        with open(os.path.join(REPO, "R467", "PROBE_CATALOG.json")) as f:
            rec1 = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(os.path.join(REPO, "R468", "PROBE_ATRIA_KEY2.json")) as f:
            rec2 = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    ident = {}
    if rec1:
        same = (rec1.get("key_fingerprint", "") == fp(key1))
        ident["key1_same_as_r467"] = same
        ident["key1_note"] = (
            "the SAME live credential R467 validated and registered"
            if same else
            "DIFFERENT from the R467 key — a rotation signal; escalate "
            "before treating either as live")
    if rec2:
        same2 = (rec2.get("key2_fingerprint", "") == fp(key2))
        ident["key2_same_as_r468"] = same2
        ident["key2_note"] = (
            "the SAME second credential R468 validated"
            if same2 else
            "DIFFERENT from the R468 key — a rotation signal; escalate")
    # all three keys must be DISTINCT (a re-supply of key1 as key3 would
    # make the ring's third slot redundant, not additive)
    ident["all_three_distinct"] = len({key1, key2, key3}) == 3
    out["identity_checks"] = ident
    print(f"[identity] key1_same={ident.get('key1_same_as_r467')} "
          f"key2_same={ident.get('key2_same_as_r468')} "
          f"all_distinct={ident['all_three_distinct']}")

    # 2. bogus-key differential on the catalog (the R463 validity method)
    s_bogus, raw_b, dt_b, err_b = _req(f"{BASE}/v1/models", BOGUS)
    out["probes"].append({"probe": "models_bogus_key",
                          "status": s_bogus, "seconds": dt_b,
                          "error": err_b[:200],
                          "note": "the validity differential control"})
    print(f"[models_bogus_key] {s_bogus} in {dt_b}s")

    # 3. the RING VIEW: every key's catalog status side by side
    ring = []
    for name, key in (("ATRIA_API_KEY", key1),
                      ("ATRIA_API_KEY_2", key2),
                      ("ATRIA_API_KEY_3", key3)):
        if not key:
            ring.append({"env_var": name, "status": "UNSET",
                         "fingerprint": fp(key)})
            continue
        s_c, raw_c, dt_c, err_c = _req(f"{BASE}/v1/models", key)
        body_c = _json(raw_c)
        ids = []
        if isinstance(body_c, dict) and isinstance(body_c.get("data"), list):
            ids = [m.get("id") for m in body_c["data"] if m.get("id")]
        ring.append({"env_var": name, "status": s_c, "seconds": dt_c,
                     "error": err_c[:200], "model_ids": ids,
                     "fingerprint": fp(key)})
        print(f"[models {name}] {s_c} in {dt_c}s ids={ids}")
    out["ring_catalog_view"] = ring

    # 4. key-3 tiny completion (the R467 PROBE_OK instrument)
    comp_ok, comp_note = False, ""
    key3_ids = next((r.get("model_ids") for r in ring
                     if r.get("env_var") == "ATRIA_API_KEY_3"), [])
    valid = (any(r.get("status") == 200 for r in ring
                 if r.get("env_var") == "ATRIA_API_KEY_3")
             and s_bogus in (401, 403))
    if valid and key3_ids:
        payload = {"model": key3_ids[0],
                   "messages": [{"role": "user",
                                 "content": "Reply with exactly: PROBE_OK"}],
                   "max_tokens": 4096, "temperature": 0}
        s_cmp, raw_m, dt_m, err_m = _req(
            f"{BASE}/v1/chat/completions", key3, payload)
        body_m = _json(raw_m)
        content = ""
        if isinstance(body_m, dict) and body_m.get("choices"):
            content = (body_m["choices"][0].get("message", {})
                       .get("content") or "")
        comp_ok = (s_cmp == 200 and bool(content.strip()))
        out["probes"].append({
            "probe": "completion_key3", "status": s_cmp, "seconds": dt_m,
            "error": err_m[:200],
            "content_nonempty": bool(content.strip()),
            "finish_reason": (body_m["choices"][0].get("finish_reason")
                              if isinstance(body_m, dict)
                              and body_m.get("choices") else None),
            "note": "tiny PROBE_OK call; the R467 small-cap starvation "
                    "lesson applied (4096 cap for the reasoning model)",
        })
        comp_note = content.strip()[:60]
        print(f"[completion_key3] {s_cmp} in {dt_m}s "
              f"content_nonempty={bool(content.strip())}")

    out["key3_validity"] = {
        "differential": "catalog 200 with key3 vs "
                        f"{s_bogus} with bogus key",
        "valid": valid,
        "note": "auth evaluates before plan/gate logic (the R463 method)"
                if valid else "the differential did not separate — "
                "do not persist as valid",
    }
    out["verdict"] = {
        "key3_valid": valid,
        "completion_ok": comp_ok,
        "ring_size_measured": sum(1 for r in ring
                                  if r.get("status") == 200),
        "role": "the ring's THIRD slot — the R469 wiring rotates "
                "ATRIA_API_KEY -> ATRIA_API_KEY_2 -> ATRIA_API_KEY_3 on "
                "exhaustion-class failures (the operator's keep-going "
                "directive), then the standing cascade advances",
    }

    path = os.path.join(OUT_DIR, "PROBE_ATRIA_KEY3.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"artifact -> R469/PROBE_ATRIA_KEY3.json (fingerprints only)")
    print(f"verdict: key3_valid={valid} completion_ok={comp_ok} "
          f"ring_200s={out['verdict']['ring_size_measured']}")
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
