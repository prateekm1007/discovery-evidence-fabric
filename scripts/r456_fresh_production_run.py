#!/usr/bin/env python3
"""R456 fresh production run through the REAL user path — the standing
acceptance (R455 protocol): a genuinely fresh problem, POST /api/run
(the X-Tosca-Owner transport — the embedded-context cookie discipline),
poll the result, and record what the run's own artifacts say. Expected
on the degraded-only route: the typed RUN_BLOCKED_CAPABILITY terminal
(0 retrieval calls, resumable — never a scientific verdict, Art. LXI),
proving the removal round changed nothing live-path-wise.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import uuid

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
OWNER = uuid.uuid4().hex
PROBLEM = (
    "A district heating network operator reports that steel "
    "distribution pipes buried since the 1980s are developing external "
    "chloride-induced pitting at insulating sleeve joints where road "
    "salt infiltrates the annular space; the 40-year design life is "
    "being reached at 25 years with pinpoint leaks appearing every "
    "winter, and relining the full 60-kilometer network is "
    "cost-prohibitive, so we need a way to extend the remaining pipe "
    "life by mitigating the external corrosion at the sleeve joints "
    "without excavating every joint.")
OUT = "scripts/r456_fresh_run.json"


def _req(path, data=None, timeout=120):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Content-Type": "application/json",
        "X-Tosca-Owner": OWNER,
        # the Space is private: every request carries the HF bearer
        # (the operator token; never embedded in the repo)
        "Authorization": f"Bearer {os.environ.get('HF_TOKEN', '')}",
    }
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method="POST" if data is not None
                                 else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def main() -> int:
    print(f"owner: {OWNER}")
    st, run = _req("/api/run", {"text": PROBLEM})
    print(f"POST /api/run -> {st} {json.dumps(run)[:200]}")
    rid = run.get("run_id") or run.get("id") or run.get("session_id")
    if not rid:
        print("FATAL: no run id returned")
        return 1
    deadline = time.time() + 1800
    last = None
    while time.time() < deadline:
        try:
            st, res = _req(f"/api/run/{rid}/result", timeout=60)
            last = res
            status = res.get("status")
            print(f"poll: status={status} "
                  f"outcome={(res.get('outcome') or {}).get('outcome') or res.get('final_status')}",
                  flush=True)
            if status in ("COMPLETE", "FAILED", "ERROR",
                          "RUN_BLOCKED", "BLOCKED"):
                break
        except Exception as exc:  # noqa: BLE001
            print(f"poll pending ({type(exc).__name__})", flush=True)
        time.sleep(20)
    out = {
        "run_id": rid,
        "owner_transport": "X-Tosca-Owner header (R447 embedded-context "
                           "discipline)",
        "problem_chars": len(PROBLEM),
        "final": last,
        "polled_until_utc": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
    }
    open(OUT, "w").write(json.dumps(out, indent=2))
    print(f"-> {OUT}")
    s = json.dumps(last or {})
    print("typed terminal present:",
          "RUN_BLOCKED" in s or "CAPABILITY" in s or "COMPLETE" in s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
