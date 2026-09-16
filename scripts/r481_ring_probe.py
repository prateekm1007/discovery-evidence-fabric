#!/usr/bin/env python3
"""R481 — the fresh atria ring measurement (the union-delivery round).

The two R478 lines raced (see R481/LINEAGE_RECONCILIATION.json): this
line measured slot 8 CLEAR at 17:52Z (catalog 200 x3 + a 200 tiny
completion -> REINSTATE per the R470/R472 flap criterion) while the
sibling R480 repoint (18:04Z) carried slot 8 INERT citing the OLDER
R472 verdict — the sibling could not see this line's unpushed
measurement. This probe re-measures ALL 15 slots NOW so the union
record carries the newest typed state (Art. XV: the flap history is
never erased; the latest typed measurement decides the live verdict).

BS-021: fingerprints only, never key values.
Artifact: R481/RING_PROBE.json (repo).
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VAULT = "/home/z/my-project/.secrets.env"
BASE = "https://api.atria-asi.ai"
OUT = Path(__file__).resolve().parents[1] / "R481" / "RING_PROBE.json"

SLOTS = ["ATRIA_API_KEY"] + [f"ATRIA_API_KEY_{i}" for i in range(2, 16)]


def load_vault():
    vals = {}
    with open(VAULT) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals


def fp(v: str) -> str:
    return f"{v[:7]}...{v[-4:]} (len {len(v)})"


def catalog(key: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        f"{BASE}/v1/models", headers={"Authorization": f"Bearer {key}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        ids = [m.get("id") for m in data.get("data", [])][:4]
        return {"http": r.status, "n_models": len(data.get("data", [])),
                "models": ids,
                "latency_ms": int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "error": e.read().decode()[:120]}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "error": repr(e)[:120]}


def tiny_completion(key: str, max_tokens: int = 32) -> dict:
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [{"role": "user",
                      "content": "Reply with exactly: ok"}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        content = ((data.get("choices") or [{}])[0]
                   .get("message", {}).get("content") or "")
        return {"http": r.status, "model": data.get("model"),
                "content": content[:40],
                "usage": data.get("usage"),
                "latency_ms": int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "error": e.read().decode()[:160]}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "error": repr(e)[:160]}


def main() -> int:
    vals = load_vault()
    OUT.parent.mkdir(exist_ok=True)
    out = {"round": "R481", "kind": "ring_probe",
           "why": ("the union-delivery round's fresh measurement — the "
                   "slot-8 flap contested between this line's R478 "
                   "17:52Z CLEAR and the sibling R480 18:04Z inert "
                   "carry (which cited the older R472 verdict)"),
           "base": BASE, "slots": {}, "slot8_remeasure": None,
           "head_completion": None}
    for slot in SLOTS:
        key = vals.get(slot, "")
        if not key:
            out["slots"][slot] = {"present": False}
            continue
        r = catalog(key)
        r["fingerprint"] = fp(key)
        out["slots"][slot] = r
        print(f"[ring] {slot}: http={r.get('http')} "
              f"models={r.get('n_models')} {r.get('fingerprint')}",
              flush=True)
        time.sleep(0.3)

    # slot 8: the flap — x3 catalog probes 8 s apart (the R470/R472
    # deterministic criterion: 200 x3 clears, 401 x3 excludes)
    key8 = vals.get("ATRIA_API_KEY_8", "")
    if key8:
        probes = []
        for i in range(3):
            probes.append(catalog(key8))
            if i < 2:
                time.sleep(8)
        all200 = all(p.get("http") == 200 for p in probes)
        out["slot8_remeasure"] = {
            "fingerprint": fp(key8), "probes": probes, "all_200": all200}
        if all200:
            out["slot8_remeasure"]["tiny_completion"] = \
                tiny_completion(key8)

    head = vals.get("ATRIA_API_KEY", "")
    if head:
        out["head_completion"] = tiny_completion(head)

    out["summary"] = {
        "slots_present": sum(1 for s in SLOTS if vals.get(s)),
        "slots_catalog_200":
            sum(1 for s in SLOTS
                if out["slots"].get(s, {}).get("http") == 200),
        "slot8_verdict": (
            "CLEAR_REINSTATED" if out.get("slot8_remeasure", {})
            .get("all_200") else "INVALID_STAY_EXCLUDED"),
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out["summary"], indent=1))
    print(f"[ring] written: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
