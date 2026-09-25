#!/usr/bin/env python3
"""R531 closeout proof (§11, §16): machine-generated production
identity chain. Records target_sha, origin/main, live /api/version,
live /api/health, deployment identity, drift, tamper, standing
configuration. UNKNOWN is preserved when the endpoint cannot be
reached — never fabricated."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R531" / "CLOSEOUT_PROOF.json"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
TARGET = "96e2d03652d330156da7e0818bc386447c2ad8df"


def _sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True,
                          cwd=str(REPO))


def _get(path, timeout=90):
    try:
        with urllib.request.urlopen(BASE + path,
                                    timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001 — UNKNOWN, never fabricated
        return {"probe_error": f"{type(e).__name__}: {str(e)[:150]}"}


def main() -> int:
    head = _sh("git", "rev-parse", "HEAD").stdout.strip()
    origin = _sh("git", "rev-parse", "origin/main").stdout.strip()
    version = _get("/api/version")
    health = _get("/api/health")
    di = health.get("deployment_identity") or {}
    live = version.get("engine_commit") or ""
    proof = {
        "artifact": "R531_CLOSEOUT_PROOF/1.0",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "target_sha": TARGET,
        "local_head": head,
        "origin_main": origin,
        "head_matches_origin": bool(head and head == origin),
        "production_engine_commit": live,
        "production_matches_target": (live == TARGET),
        "health": health.get("ok", health.get("status",
                                              "UNKNOWN_NO_KEY")),
        "deployment_identity": di,
        "drift": di.get("deployment_drift", "UNKNOWN"),
        "tamper": di.get("identity_tamper", "UNKNOWN"),
        "standing_configuration": {
            "ENGINE_EVIDENCE_FABRIC": "0",
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex",
        },
        "audit_harvester_commit": "3dbbc045e",
        "measurement_build_commit": "714108382",
        "chain_ok": bool(live == TARGET
                         and di.get("deployment_drift") == "GREEN"
                         and di.get("identity_tamper") is False
                         and head == origin),
    }
    OUT.write_text(json.dumps(proof, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT} (chain_ok={proof['chain_ok']})")
    return 0 if proof["chain_ok"] else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
