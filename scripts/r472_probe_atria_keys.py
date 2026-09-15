#!/usr/bin/env python3
"""R472 — validate the operator's THREE new atria keys (ATRIA_API_KEY_11
through ATRIA_API_KEY_13) + re-probe the re-supplied ATRIA_API_KEY_8
before anything is persisted (probe-before-record; the R463/R467/R470
method).

Operator round (2026-09-16, third pass of the external audit in the
same message): thirteen keys listed at the console URL — keys 1-10
identical to the standing ring, keys 11-13 NEW this round, and key 8
RE-SUPPLIED (the same value the R470 probe measured as a DETERMINISTIC
401 x3 — the operator was invited to re-supply; the re-supply is the
same string, so the question is whether the ACCOUNT changed).

What this probe measures (typed, never assumed):
  1. DISTINCTNESS: all thirteen vault keys pairwise distinct;
  2. keys 11-13 VALIDITY: the bogus-key differential on GET /v1/models
     (auth evaluates before plan/gate logic — the R463 method);
  3. keys 11-13 CATALOG: model ids verbatim per key;
  4. key 8 RE-PROBE: catalog x3 with 8 s gaps — a 200 anywhere means
     the account-side exclusion CLEARED (reinstate); a deterministic
     401 x3 stands (the measured verdict outranks name-presence,
     Art. III);
  5. ONE tiny completion on ONE new key (budget-conserving: the ring
     is homogeneous; max_tokens 1024, reasoning_effort low — the
     R467/R469 lesson that reasoning burns the budget).

Keys come from the ENVIRONMENT ONLY (BS-021). The artifact records
measurements and FINGERPRINTS, never values.
"""
from __future__ import annotations

import itertools
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
OUT_DIR = os.path.join(REPO, "R472")

RING_SLOTS = [f"ATRIA_API_KEY{_s}" for _s in
              ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10",
               "_11", "_12", "_13"]]
NEW_SLOTS = ["ATRIA_API_KEY_11", "ATRIA_API_KEY_12", "ATRIA_API_KEY_13"]
REPROBE_SLOT = "ATRIA_API_KEY_8"


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
    keys = {name: os.environ.get(name, "").strip() for name in RING_SLOTS}
    missing = [n for n in NEW_SLOTS + [REPROBE_SLOT] if not keys[n]]
    if missing:
        print(f"FATAL: unset in session env (BS-021): {missing}")
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)

    out = {"round": "R472", "provider": "atria",
           "subject": "the operator's THREE new atria keys "
                      "(ATRIA_API_KEY_11.._13) + the RE-SUPPLIED "
                      "ATRIA_API_KEY_8 — the ring grows 9 valid -> up to "
                      "13 slots; third pass of the external audit is the "
                      "same message's work order",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "new_key_fingerprints": {n: fp(keys[n]) for n in NEW_SLOTS},
           "reprobe_key_fingerprint": fp(keys[REPROBE_SLOT]),
           "probes": []}

    # 1. distinctness across all thirteen
    dup = [f"{a}=={b}" for a, b in itertools.combinations(RING_SLOTS, 2)
           if keys[a] and keys[b] and keys[a] == keys[b]]
    out["thirteen_way_distinct"] = not dup
    out["duplicates"] = dup
    print(f"[1] distinctness: {'OK' if not dup else 'DUPLICATES: ' + str(dup)}")

    # 2+3. bogus differential + catalog per new key
    bogus_status, _, _, _ = _req(f"{BASE}/v1/models", BOGUS)
    out["bogus_differential"] = {"status": bogus_status}
    print(f"[2] bogus-key differential: {bogus_status} (expect 401)")
    for name in NEW_SLOTS:
        st, raw, dt, err = _req(f"{BASE}/v1/models", keys[name])
        body = _json(raw) or {}
        models = sorted(m.get("id", "") for m in body.get("data", []))
        verdict = "VALID" if (st == 200 and bogus_status == 401) else \
            (f"INVALID_{st}" if st == 401 else f"UNDETERMINED_{st}")
        out["probes"].append({
            "slot": name, "probe": "catalog", "status": st, "latency_s": dt,
            "models": models, "verdict": verdict, "err": err[:120]})
        print(f"[3] {name}: {st} {dt}s models={models} -> {verdict}")

    # 4. key-8 re-probe x3, 8 s apart (the R470 protocol)
    reprobe = []
    for i in range(3):
        st, raw, dt, err = _req(f"{BASE}/v1/models", keys[REPROBE_SLOT])
        body = _json(raw) or {}
        models = sorted(m.get("id", "") for m in body.get("data", []))
        reprobe.append({"attempt": i + 1, "status": st, "latency_s": dt,
                        "models": models, "err": err[:120]})
        print(f"[4] {REPROBE_SLOT} attempt {i+1}: {st} {dt}s models={models}")
        if i < 2:
            time.sleep(8)
    statuses = {p["status"] for p in reprobe}
    if 200 in statuses:
        out["key8_reprobe_verdict"] = "CLEARED_200_REINSTATE"
    elif statuses == {401}:
        out["key8_reprobe_verdict"] = "STILL_DETERMINISTIC_401_EXCLUDED"
    else:
        out["key8_reprobe_verdict"] = f"UNDETERMINED_{sorted(statuses)}"
    out["key8_reprobe"] = reprobe
    print(f"[4] key-8 verdict: {out['key8_reprobe_verdict']}")

    # 5. one tiny completion on ONE new key (key 11), low effort
    st, raw, dt, err = _req(
        f"{BASE}/v1/chat/completions", keys["ATRIA_API_KEY_11"],
        payload={"model": "Atria-Dawn-Preview", "max_tokens": 1024,
                 "reasoning_effort": "low",
                 "messages": [{"role": "user",
                               "content": "Reply with exactly: OK"}]})
    body = _json(raw) or {}
    ch = (body.get("choices") or [{}])[0]
    content = (ch.get("message") or {}).get("content")
    out["probes"].append({
        "slot": "ATRIA_API_KEY_11", "probe": "tiny_completion",
        "status": st, "latency_s": dt,
        "finish_reason": ch.get("finish_reason"),
        "content_nonempty": bool(content), "err": err[:120]})
    print(f"[5] tiny completion (key 11): {st} {dt}s content="
          f"{bool(content)} finish={ch.get('finish_reason')}")

    ok_new = all(p["verdict"] == "VALID" for p in out["probes"]
                 if p.get("probe") == "catalog")
    out["new_keys_all_valid"] = ok_new
    path = os.path.join(OUT_DIR, "PROBE_ATRIA_KEYS11TO13.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"WROTE {path}")
    return 0 if ok_new else 1


if __name__ == "__main__":
    sys.exit(main())
