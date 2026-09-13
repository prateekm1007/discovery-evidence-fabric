#!/usr/bin/env python3
"""R447 live decisive test — the run-not-found fix on the PRODUCTION
canonical Space, under the EXACT conditions of the defect:

  the huggingface.co iframe blocks the tosca_owner cookie, so the browser
  sends NO cookie on any request. Pre-fix, every request was a NEW
  visitor: the run 404'd ("Run not found") and the rail was empty.

The test (a REAL fresh run on the production user path — never a replay):
  1. POST /api/run with NO cookie, NO header  -> must return owner_key
     (the capability the client persists)
  2. GET  /api/run/{id}/result with NOTHING   -> 404 (the OLD defect,
     reproduced live as the negative control)
  3. GET  /api/run/{id}/result with ONLY the
     X-Tosca-Owner header                      -> 200 (THE FIX)
  4. GET  /api/sessions with ONLY the header   -> the run IS in the rail
  5. GET  /api/run/{id}/stream?owner=<key>     -> 200 SSE (EventSource
     transport; no cookie in play)
  6. a SECOND visitor (different valid key)    -> 404 (privacy intact)

Usage: HF_TOKEN=... python scripts/r447_live_run_not_found_test.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

PROBLEM = ("Our district heating network loses 8 percent of pumped heat "
           "through uninsulated valve chambers built before 1980; find a "
           "retrofit mechanism that cuts the losses without excavating "
           "the streets.")


def call(method, path, headers=None, body=None, sse=False):
    hdrs = {"Authorization": f"Bearer {HF_TOKEN}"}
    hdrs.update(headers or {})
    payload = None
    if body is not None:
        payload = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=payload,
                                 headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read(400 if sse else 65536).decode("utf-8", "replace")
            ctype = r.headers.get("Content-Type", "")
            if sse or "event-stream" in ctype:
                return r.status, {"_sse_head": raw[:200]}
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, {"_raw": raw[:200]}
    except urllib.error.HTTPError as e:
        return e.code, {"_http_error": True}


def main() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'  — ' + detail if detail else ''}")

    print("[live-test] 1. run creation with NO cookie (the iframe browser)")
    status, body = call("POST", "/api/run", body={"text": PROBLEM})
    run_id = body.get("session_id") or body.get("run_id")
    owner_key = body.get("owner_key")
    check("POST /api/run returns 200 with a run id",
          status == 200 and bool(run_id), f"run={run_id}")
    check("the response carries the caller's own owner_key",
          bool(owner_key) and len(owner_key) >= 8,
          f"key={owner_key and owner_key[:8]}…")

    print("[live-test] 2. the OLD defect, live negative control (no "
          "cookie, no header)")
    status, _ = call("GET", f"/api/run/{run_id}/result")
    check("result poll with NO identity -> 404 (the pre-fix "
          "'Run not found' condition reproduced live)",
          status == 404)

    print("[live-test] 3. THE FIX — the header the client persisted")
    status, body = call("GET", f"/api/run/{run_id}/result",
                        headers={"X-Tosca-Owner": owner_key})
    check("result poll with ONLY X-Tosca-Owner -> 200 (was the "
          "user-facing defect; now closed)",
          status == 200 and (body.get("session_id") == run_id),
          f"status={body.get('status')}")

    print("[live-test] 4. the history rail")
    status, body = call("GET", "/api/sessions",
                        headers={"X-Tosca-Owner": owner_key})
    ids = [s.get("session_id") for s in body.get("sessions", [])]
    check("the rail shows the run to the header caller",
          status == 200 and run_id in ids, f"rail={len(ids)} run(s)")
    check("the rail response also carries the caller's own owner_key",
          body.get("owner_key") == owner_key)

    print("[live-test] 5. the SSE stream (EventSource transport)")
    status, body = call("GET",
                        f"/api/run/{run_id}/stream?owner={owner_key}",
                        sse=True)
    check("stream opens with the owner query parameter -> 200 SSE",
          status == 200 and "hello" in body.get("_sse_head", ""),
          body.get("_sse_head", "")[:60].replace("\n", " "))

    print("[live-test] 6. privacy — a second visitor")
    status, _ = call("GET", f"/api/run/{run_id}/result",
                     headers={"X-Tosca-Owner": "e" * 32})
    check("a different valid key still gets the enumeration-safe 404",
          status == 404)

    ok = all(r[1] for r in results)
    print(f"\n[live-test] {'ALL CHECKS PASS — the run-not-found defect is '
          f'closed on production' if ok else 'FAILURES PRESENT'}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "r447_live_test_result.json")
    with open(out, "w") as f:
        json.dump({"run_id": run_id, "all_pass": ok,
                   "checks": [{"name": n, "pass": p, "detail": d}
                              for n, p, d in results]}, f, indent=1)
    print(f"[live-test] result -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
