#!/usr/bin/env python3
"""One-off: save live /result payloads for completed sessions, then
harvest them. Payloads are LOCAL-only (BS-021); harvest rows carry
metrics + payload sha (committable)."""
import hashlib
import json
import os
import sys
import urllib.request

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
TOK = os.environ["HF_TOKEN"]


def req(path, owner=""):
    r = urllib.request.Request(
        BASE + path,
        headers={"Authorization": "Bearer " + TOK,
                 "X-Tosca-Owner": owner})
    with urllib.request.urlopen(r, timeout=60) as x:
        return x.status, json.loads(x.read().decode())


def main():
    sess_file, indices = sys.argv[1], [int(i) for i in sys.argv[2:]]
    sess = json.load(open(sess_file, encoding="utf-8"))
    for s in sess["submissions"]:
        if s["problem_index"] not in indices:
            continue
        st, d = req("/api/run/%s/result" % s["session_id"],
                    owner=s.get("owner_key") or "")
        print(s["session_id"][:8], st,
              (d.get("status") or d.get("state") if st == 200 else d))
        if st != 200:
            continue
        p = "/tmp/r519_live_%s.json" % s["session_id"]
        open(p, "w", encoding="utf-8").write(json.dumps(d, indent=1))
        print("   saved", p, hashlib.sha256(
            open(p, "rb").read()).hexdigest()[:12],
            "state:", d.get("status") or d.get("state"))


if __name__ == "__main__":
    main()
