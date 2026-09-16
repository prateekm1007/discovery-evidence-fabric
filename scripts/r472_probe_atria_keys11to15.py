#!/usr/bin/env python3
"""R472 — validate the operator's FIVE new atria keys (ATRIA_API_KEY_11
through ATRIA_API_KEY_15) before they are persisted (probe-before-record;
the R463/R467/R468/R469/R470 method), and RE-PROBE key 8 (the R470
deterministic-401 exclusion — the operator re-supplied it in the same
2026-09-16 list, so the verdict is re-measured, never assumed either way).

Operator instruction (2026-09-16 session 2, verbatim structure, values
redacted BS-021): fifteen keys total listed at the console URL — keys
1-10 identical to the R467-R470-registered credentials, keys 11-15 NEW
this round. The R470 ring grows 10 -> 15 slots.

What this probe measures (typed, never assumed):
  1. keys 1-10 identity: all fifteen pairwise distinct (a duplicate
     slot is redundant, not additive);
  2. keys 11-15 VALIDITY: the bogus-key differential on GET /v1/models
     (auth evaluates before plan/gate logic — the R463 method), per key,
     with the R470 non-200 re-probe discipline (2 confirmations 8 s
     apart before a key is typed invalid);
  3. key 8 RE-PROBE: the R470 record measured a deterministic 401 x3;
     this round re-measures (x3, 8 s apart) — a verdict is re-measured
     when the operator re-supplies, never carried forward (Art. III);
  4. keys 11-15 CATALOG: model ids verbatim per key;
  5. ONE tiny completion on ONE new key (budget-conserving: the ring is
     homogeneous, one live completion proves the chat endpoint serves
     the new keys; 4096 cap for the reasoning model — the R467 lesson).

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
OUT_DIR = os.path.join(REPO, "R472")

ALL_SLOTS = [f"ATRIA_API_KEY{_s}" for _s in
             ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10",
              "_11", "_12", "_13", "_14", "_15"]]
NEW_SLOTS = ALL_SLOTS[10:]
REPROBE_SLOTS = ("ATRIA_API_KEY_8",)


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
    keys = {name: os.environ.get(name, "").strip() for name in ALL_SLOTS}
    missing = [n for n in NEW_SLOTS if not keys[n]]
    if missing:
        print(f"FATAL: unset in session env (BS-021): {missing}")
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)

    out = {"round": "R472", "provider": "atria",
           "subject": "the operator's FIVE new atria keys "
                      "(ATRIA_API_KEY_11..ATRIA_API_KEY_15) — the ring "
                      "grows 10 -> 15 slots; PLUS the key-8 re-probe "
                      "(the R470 deterministic-401 exclusion re-measured "
                      "after the operator's re-supply)",
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "new_key_fingerprints": {n: fp(keys[n]) for n in NEW_SLOTS},
           "probes": []}

    # 1. all-fifteen distinctness (duplicate slots are redundant)
    present = [k for k in keys.values() if k]
    ident = {"all_present_pairwise_distinct":
             len(set(present)) == len(present),
             "n_present": len(present), "n_distinct": len(set(present))}
    # identity vs the R470 record for keys 1-10 (continuity, not rotation)
    try:
        with open(os.path.join(REPO, "R470",
                               "PROBE_ATRIA_KEYS4TO10.json")) as f:
            r470 = json.load(f)
        for row in r470.get("ring_catalog_view", []):
            name = row.get("env_var", "")
            if name in keys and keys[name]:
                ident[f"{name}_same_as_r470"] = (
                    row.get("fingerprint") == fp(keys[name]))
    except Exception:  # noqa: BLE001
        ident["r470_record_load"] = "unavailable"
    out["identity_checks"] = ident
    print(f"[identity] {ident}")

    # 2. bogus-key differential control
    s_bogus, raw_b, dt_b, err_b = _req(f"{BASE}/v1/models", BOGUS)
    out["probes"].append({"probe": "models_bogus_key",
                          "status": s_bogus, "seconds": dt_b,
                          "error": err_b[:200],
                          "note": "the validity differential control"})
    print(f"[models_bogus_key] {s_bogus} in {dt_b}s")
    differential_ok = s_bogus in (401, 403)

    # 3. per-key catalog: all fifteen side by side (the ring view at 15);
    #    a non-200 on a NEW key or a RE-PROBE key is re-probed twice more
    #    (8 s apart) before it is typed invalid — one flappy 4xx/5xx must
    #    not evict a slot, and one flappy 200 must not admit one
    ring = []
    for name in ALL_SLOTS:
        key = keys[name]
        if not key:
            ring.append({"env_var": name, "status": "UNSET",
                         "fingerprint": fp(key)})
            continue
        s_c, raw_c, dt_c, err_c = _req(f"{BASE}/v1/models", key)
        confirmations = []
        if (name in NEW_SLOTS or name in REPROBE_SLOTS) and s_c != 200:
            for attempt in (2, 3):
                time.sleep(8)
                s_r, raw_r, dt_r, err_r = _req(f"{BASE}/v1/models", key)
                confirmations.append({"attempt": attempt, "status": s_r,
                                      "seconds": dt_r,
                                      "error": err_r[:120]})
                if s_r == 200:
                    s_c, raw_c, dt_c, err_c = s_r, raw_r, dt_r, err_r
                    break
        body_c = _json(raw_c)
        ids = []
        if isinstance(body_c, dict) and isinstance(body_c.get("data"), list):
            ids = [m.get("id") for m in body_c["data"] if m.get("id")]
        entry = {"env_var": name, "status": s_c, "seconds": dt_c,
                 "error": err_c[:200], "model_ids": ids,
                 "fingerprint": fp(key)}
        if name in REPROBE_SLOTS:
            entry["reprobe_of"] = ("the R470 deterministic-401 verdict "
                                   "(excluded from the ring)")
        if confirmations:
            entry["non200_confirmations"] = confirmations
            entry["note"] = ("re-probed " + str(len(confirmations))
                             + "x after the first non-200 — "
                             + ("RECOVERED (transient)"
                                if s_c == 200 else
                                "DETERMINISTIC non-200 (typed invalid; "
                                "excluded from the ring, operator "
                                "re-supply invited)"))
        ring.append(entry)
        extra = ""
        if confirmations:
            extra = " confirmations=" + str(
                [(c["attempt"], c["status"]) for c in confirmations])
        print(f"[models {name}] {s_c} in {dt_c}s ids={ids}{extra}")
    out["ring_catalog_view"] = ring

    new_valid = {r["env_var"]: r["status"] == 200 for r in ring
                 if r["env_var"] in NEW_SLOTS}
    key8_reprobe = next((r for r in ring
                         if r["env_var"] == "ATRIA_API_KEY_8"), {})

    # 4. ONE tiny completion on ONE new key (budget-conserving; the ring
    #    is homogeneous — same account, same sole model)
    comp_ok, comp_note = False, ""
    first_valid_new = next((r for r in ring if r["env_var"] in NEW_SLOTS
                            and r.get("status") == 200), None)
    if first_valid_new and differential_ok and first_valid_new["model_ids"]:
        payload = {"model": first_valid_new["model_ids"][0],
                   "messages": [{"role": "user",
                                 "content": "Reply with exactly: PROBE_OK"}],
                   "max_tokens": 4096, "temperature": 0}
        # the R467-measured transient fast-fail: up to 3 real attempts,
        # 8 s apart — a transport flap is not a key verdict
        s_cmp, raw_m, dt_m, err_m, attempts_used = 0, "", 0.0, "", 0
        for attempt in (1, 2, 3):
            attempts_used = attempt
            s_cmp, raw_m, dt_m, err_m = _req(
                f"{BASE}/v1/chat/completions",
                keys[first_valid_new["env_var"]], payload)
            if s_cmp == 200:
                break
            print(f"[completion attempt {attempt}] {s_cmp} in {dt_m}s "
                  f"— transient; backing off 8 s")
            time.sleep(8)
        body_m = _json(raw_m)
        content = ""
        if isinstance(body_m, dict) and body_m.get("choices"):
            content = (body_m["choices"][0].get("message", {})
                       .get("content") or "")
        comp_ok = (s_cmp == 200 and bool(content.strip()))
        out["probes"].append({
            "probe": "completion_new_key_sample",
            "env_var": first_valid_new["env_var"],
            "status": s_cmp, "seconds": dt_m, "error": err_m[:200],
            "attempts_used": attempts_used,
            "content_nonempty": bool(content.strip()),
            "finish_reason": (body_m["choices"][0].get("finish_reason")
                              if isinstance(body_m, dict)
                              and body_m.get("choices") else None),
            "note": "tiny PROBE_OK call on ONE new key (budget-conserving; "
                    "4096 cap for the reasoning model — the R467 lesson; "
                    "up to 3 attempts on transient fast-fails)",
        })
        comp_note = content.strip()[:60]
        print(f"[completion_new_key_sample "
              f"{first_valid_new['env_var']}] {s_cmp} in {dt_m}s "
              f"attempts={attempts_used} "
              f"content_nonempty={bool(content.strip())}")

    out["new_keys_validity"] = {
        "differential": f"catalog 200 with each new key vs {s_bogus} bogus",
        "per_key_200": new_valid,
        "all_new_valid": all(new_valid.values()),
        "note": "auth evaluates before plan/gate logic (the R463 method)"
                if all(new_valid.values()) and differential_ok else
                "the differential did not separate on at least one key — "
                "do not persist that key as valid",
    }
    out["key8_reprobe_verdict"] = {
        "status": key8_reprobe.get("status"),
        "r470_verdict": "deterministic 401 x3 — excluded",
        "r472_verdict": ("VALID (catalog 200) — the operator's re-supply "
                         "measured live; re-admit to the ring"
                         if key8_reprobe.get("status") == 200 else
                         "STILL non-200 after the re-probe discipline — "
                         "the exclusion STANDS (the measured verdict "
                         "outranks the name-present surface, Art. III)"),
        "confirmations": key8_reprobe.get("non200_confirmations"),
    }
    out["verdict"] = {
        "all_new_keys_valid": all(new_valid.values()) and differential_ok,
        "key8_revalidated": key8_reprobe.get("status") == 200,
        "completion_ok": comp_ok,
        "ring_size_measured": sum(1 for r in ring
                                  if r.get("status") == 200),
        "role": "the ring grows to FIFTEEN slots — exhaustion-class "
                "failures rotate through every PRESENT slot on the same "
                "rung (the operator's keep-going directive), then the "
                "standing cascade advances",
        "budget_note": "15 keys x operator-declared 100M = the ~1.5B-token "
                       "surplus (OPERATOR-DECLARED; no usage endpoint is "
                       "measurable)",
    }

    path = os.path.join(OUT_DIR, "PROBE_ATRIA_KEYS11TO15.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"artifact -> R472/PROBE_ATRIA_KEYS11TO15.json (fingerprints only)")
    print(f"verdict: all_new_valid={out['verdict']['all_new_keys_valid']} "
          f"key8_revalidated={out['verdict']['key8_revalidated']} "
          f"completion_ok={comp_ok} "
          f"ring_200s={out['verdict']['ring_size_measured']}")
    return 0 if out["verdict"]["all_new_keys_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
