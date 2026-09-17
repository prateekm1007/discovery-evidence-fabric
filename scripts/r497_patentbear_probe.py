#!/usr/bin/env python3
"""R497 — PatentBear key rotation + live transport probe (self-measuring).

The operator supplied a new PatentBear key (pb_live_..., fingerprint-only in
records, Art. LXXIII). Coder 2's R496 named the bearer-capable token as the
exact missing piece for the PATENT_BLIND patent side. This probe measures:

  A. liveness   — the real production code path (search_patent_bear) on a
                  broad guaranteed-hit query
  B. bad-key    — same endpoint, garbage key: MUST fail (proves key-dependence;
                  the F9 discipline: key presence is not liveness, and a 200
                  must be attributable to THE key)
  C. true-zero  — nonsense query: MUST return success with zero hits
                  (true NO_RESULTS semantics, never absence-from-failure)
  D. domain     — a collision-real query from the A2 corpus domain
                  (water treatment), typed
  M. meter      — the provider-reported monthly_remaining before/after

Typed states per Art. XXI.3 / LXI: provider failures are never absence.
Writes R497/R497_PATENTBEAR_PROBE.json. Run from the repo root.
"""
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/z/my-project/repos/discovery-evidence-fabric")
VAULT = Path("/home/z/my-project/.secrets.env")
ENVKEYS = REPO / ".env.keys"
METER = REPO / "patent_sources" / "patentbear_meter.json"
OUT = REPO / "R497" / "R497_PATENTBEAR_PROBE.json"


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_vault_key() -> tuple:
    txt = VAULT.read_text()
    m = re.search(r"^PATENTBEAR_API_KEY=(.+)$", txt, re.M)
    if not m:
        sys.exit("FATAL: PATENTBEAR_API_KEY absent from vault (Art. LXXIII)")
    return m.group(1).strip(), sha16(m.group(1).strip())


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def main():
    key, fp = load_vault_key()
    t0 = time.time()
    record = {
        "probe_id": "R497_PATENTBEAR_PROBE",
        "probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operator_directive": "patent bear api key supplied by the operator (2026-09-18, "
                              "rotation of the R378-era key whose meter hit the reserve floor "
                              "2026-08-31); Coder 2's R496 named the bearer-capable token as "
                              "the exact missing piece for the PATENT_BLIND patent side",
        "key_fingerprint_vault": fp,
        "old_key_fingerprint": "UNKNOWN (the R378-era key is not present in this environment; "
                               "unprovable stays unproven, Art. XXV)",
        "reviewer_provenance": "AI_REVIEW",
        "probes": {},
    }

    # ---- 0. key rotation into the engine's KEYS_FILE (untracked, local) ----
    lines = []
    if ENVKEYS.exists():
        lines = [l for l in ENVKEYS.read_text().splitlines()
                 if l.strip() and not l.startswith("PATENT_BEAR_API_KEY=")]
    lines.append(f"PATENT_BEAR_API_KEY={key}")
    ENVKEYS.write_text("\n".join(lines) + "\n")
    os.chmod(ENVKEYS, 0o600)
    record["envkeys"] = {
        "path": ".env.keys (untracked, gitignored, local-only)",
        "names": [l.split("=")[0] for l in lines],
        "values_committed": False,
    }

    # ---- 1. meter rotation event (tracked file — visible state change) ----
    old_meter = json.loads(METER.read_text())
    METER.write_text(json.dumps({
        "monthly_remaining": None,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reserve_floor": int(os.environ.get("PATENTBEAR_RESERVE_FLOOR", "2")),
        "note": "KEY ROTATION 2026-09-18: operator-supplied pb_live_ key (fingerprint "
                f"{fp}) replaces the R378-era key whose meter read 2 (reserve floor) on "
                "2026-08-31; the new key's quota is UNKNOWN until the provider reports it "
                "(missing = UNKNOWN, never guessed); previous state preserved in git history",
    }, indent=1) + "\n")
    record["meter_rotation"] = {
        "before": old_meter,
        "after_state": "UNKNOWN (rotation; provider report pending)",
    }

    # ---- 2. import the REAL production path fresh (reads .env.keys at import) ----
    sys.path.insert(0, str(REPO))
    src = importlib.import_module("discovery_fabric.prior_art_v2.sources")

    def run_probe(name, fn):
        t = time.time()
        try:
            r = fn()
            entry = {
                "state": "OK" if r.success else "TYPED_FAILURE",
                "success": r.success,
                "latency_ms": r.latency_ms,
                "hits": len(r.hits) if r.hits else 0,
                "error": (r.error or None),
                "error_code": r.error_code,
                "rate_limit_remaining": r.rate_limit_remaining,
                "hit_ids": [h.patent_id or h.doi for h in (r.hits or [])][:8],
            }
        except Exception as e:  # noqa: BLE001 — typed, never silent
            entry = {"state": "EXCEPTION", "error": f"{type(e).__name__}: {e}"}
        entry["wall_s"] = round(time.time() - t, 2)
        record["probes"][name] = entry
        print(f"[{name}] {entry['state']} hits={entry.get('hits')} "
              f"err={str(entry.get('error'))[:80]}")
        return entry

    # A. liveness — broad guaranteed-hit query (Coder 2's probe class)
    a = run_probe("A_liveness", lambda: src.search_patent_bear("virtual reality", 5))

    # B. bad-key control — same MCP call, garbage key, raw HTTP (never touches meter)
    def bad_key_probe():
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "search_patents",
                       "arguments": {"query": "virtual reality", "max_hits": 5,
                                     "scope": "patents", "sort": "relevance"}}
        }).encode()
        hdr = {"Authorization": "Bearer pb_live_GARBAGECONTROLKEY0000000000000000",
               "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2025-06-18"}
        status, body, lat = src._http_post("https://www.patentbear.com/mcp",
                                           payload, headers=hdr, timeout=30)
        return {"status": status, "body_head": body.decode("utf-8", "ignore")[:300],
                "latency_ms": lat}
    try:
        b = bad_key_probe()
        record["probes"]["B_bad_key_control"] = {
            "state": "AUTH_FAILED_AS_EXPECTED" if b["status"] != 200 else "UNEXPECTED_200",
            "http": b["status"], "body_head": b["body_head"], "latency_ms": b["latency_ms"],
        }
        print(f"[B_bad_key_control] http={b['status']} head={b['body_head'][:60]}")
    except Exception as e:  # noqa: BLE001
        record["probes"]["B_bad_key_control"] = {"state": "EXCEPTION", "error": str(e)}

    # C. true-zero control — nonsense query must be success + 0 hits (NO_RESULTS)
    run_probe("C_true_zero", lambda: src.search_patent_bear(
        "qqzzxxwbar9 qwvzjmplk zzxcvbnmloi", 5))

    # D. domain probe — collision-real query from the A2 corpus domain
    run_probe("D_domain", lambda: src.search_patent_bear(
        "electrochlorination ballast water treatment", 8))

    # M. meter after (provider-reported)
    record["meter_after"] = json.loads(METER.read_text())

    # classification
    live = a.get("success") and a.get("hits", 0) > 0
    b_failed = record["probes"].get("B_bad_key_control", {}).get(
        "state") == "AUTH_FAILED_AS_EXPECTED"
    if live and b_failed:
        cls = ("PATENTBEAR_TRANSPORT_LIVE (key-attributable: the operator's key opens "
               "the transport AND the garbage key is refused - key presence IS liveness "
               "here, measured, unlike the PatSnap shape R496 typed)")
    elif live:
        cls = ("PATENTBEAR_200_NOT_KEY_ATTRIBUTABLE (bad-key control also passed - "
               "endpoint may be open; liveness NOT attributable to the key)")
    else:
        cls = "PATENTBEAR_TRANSPORT_NOT_OPEN (typed: %s)" % a.get("error")
    record["classification"] = cls
    record["probe_wall_s_total"] = round(time.time() - t0, 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1) + "\n")
    print("\nCLASSIFICATION:", cls)
    print("meter_after:", record["meter_after"])
    print(f"record -> {OUT}")


if __name__ == "__main__":
    main()
