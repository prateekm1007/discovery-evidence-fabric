#!/usr/bin/env python3
"""One-off: check a session's latest forensic stage (live)."""
import json
import os
import sys
import urllib.request

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
TOK = os.environ["HF_TOKEN"]
SESS = json.load(open(sys.argv[1], encoding="utf-8"))
IDX = int(sys.argv[2])
s = [x for x in SESS["submissions"] if x["problem_index"] == IDX][0]
req = urllib.request.Request(
    BASE + "/api/run/%s/worker-diagnostics" % s["session_id"],
    headers={"Authorization": "Bearer " + TOK,
             "X-Tosca-Owner": s.get("owner_key") or ""})
try:
    with urllib.request.urlopen(req, timeout=60) as x:
        st, d = x.status, json.loads(x.read().decode())
except Exception as e:  # noqa: BLE001
    print("ERR %s: %s" % (type(e).__name__, e))
    raise SystemExit(1)
print("diag:", st)
evs = d.get("spawn_forensics") or []
for e in evs[-8:]:
    print(" ", (e.get("ts_utc") or "?")[11:19], e.get("event"),
          "|", e.get("stage"))
print("log bytes:", d.get("worker_log_bytes"))
