#!/usr/bin/env python3
"""One-off: watch post-restart resume behavior (live diagnostics)."""
import json
import os
import time
import urllib.request

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
TOK = os.environ["HF_TOKEN"]
SESS = json.load(open("R519/BATTERY_SESSIONS_BASELINE.json",
                       encoding="utf-8"))


def req(method, path, body=None, owner=""):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + TOK,
                 "X-Tosca-Owner": owner})
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            return x.status, json.loads(x.read().decode())
    except Exception as e:  # noqa: BLE001
        return None, {"error": "%s: %s" % (type(e).__name__, e)}


def diag(s):
    st, d = req("GET", "/api/run/%s/worker-diagnostics" % s["session_id"],
                owner=s.get("owner_key") or "")
    if st != 200:
        return "%s -> diag %s" % (s["session_id"][:8], st)
    evs = d.get("spawn_forensics") or []
    last = evs[-1] if evs else {}
    return "%s -> log=%sB events=%d last=%s/%s" % (
        s["session_id"][:8], d.get("worker_log_bytes"), len(evs),
        last.get("event"), last.get("stage"))


def main():
    t0 = time.time()
    while time.time() - t0 < 1500:
        el = int(time.time() - t0)
        print("[+%ds]" % el, flush=True)
        for s in SESS["submissions"]:
            print("   ", diag(s), flush=True)
        st, d = req("GET", "/api/health")
        wf = (d.get("worker_forensics") or {}) if st == 200 else {}
        print("    active:", wf.get("active_workers"),
              "orphans:", wf.get("orphans_reconciled_this_boot"),
              flush=True)
        time.sleep(180)


if __name__ == "__main__":
    main()
