#!/usr/bin/env python3
"""R519 §24 deployment identity proof (transient credential use).

Proves: origin/main == target SHA; records deployed Space SHA + health.
Reads tokens from env (HF_TOKEN / GIT_PAT); writes ONLY names +
fingerprints + typed states — never values (Art. LXXVI / BS-021).
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
HOST = SPACE.replace("/", "-").replace("_", "-")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fp(v: str | None) -> str | None:
    return hashlib.sha256((v or "").encode()).hexdigest()[:16] if v else None


def get(url: str, tok: str | None = None, timeout: int = 30):
    h = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(url, headers=h),
            timeout=timeout, context=ssl.create_default_context())
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def main() -> int:
    hf = os.environ.get("HF_TOKEN") or ""
    target = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO), text=True).strip()
    remote = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/main"],
        cwd=str(REPO), text=True).split()[0]

    space_meta: dict = {}
    if hf:
        st, b = get(f"https://huggingface.co/api/spaces/{SPACE}", hf)
        if st == 200:
            d = json.loads(b)
            rt = d.get("runtime") or {}
            space_meta = {
                "http_status": st,
                "stage": rt.get("stage"),
                "host": rt.get("host"),
                "runtime_sha": rt.get("sha"),
                "last_modified": d.get("lastModified"),
            }
        else:
            space_meta = {"http_status": st, "error": str(b)[:200]}
    else:
        space_meta = {"status": "HF_TOKEN_ABSENT"}

    health: dict = {}
    for path in ("/api/version", "/health", "/"):
        st, b = get(f"https://{HOST}.hf.space{path}", hf or None)
        health[path] = {"http_status": st, "body_head": b[:300]}
        if st == 200 and path == "/api/version":
            try:
                v = json.loads(b)
                health["engine_commit"] = v.get("engine_commit") or \
                    v.get("commit")
            except Exception:  # noqa: BLE001
                pass

    pat_present = bool(os.environ.get("GIT_PAT"))

    pushed = (remote == target)
    deployed_sha = space_meta.get("runtime_sha")
    if not pushed:
        overall = "DELIVERY_BLOCKED"
    elif deployed_sha == target:
        overall = "GREEN" if health.get("/api/version", {}).get(
            "http_status") in (200, 404) else "DEGRADED"
    else:
        overall = "DRIFT"

    rec = {
        "artifact": "R519_DEPLOY_RECORD/1.0",
        "round": "R519",
        "parent_round": "R518",
        "created_at_utc": utcnow(),
        "target_sha": target,
        "origin_main_sha": remote,
        "ls_remote_verified": True,
        "push_identity": ("MATCH" if pushed else "MISMATCH"),
        "space": {
            "id": SPACE,
            "url": f"https://huggingface.co/spaces/{SPACE}",
            "runtime_stage": space_meta.get("stage"),
            "runtime_sha": deployed_sha,
            "http_status": space_meta.get("http_status"),
            "error": space_meta.get("error"),
            "status": space_meta.get("status"),
        },
        "health_check": health,
        "deployed_sha_matches_target": bool(deployed_sha == target),
        "overall": overall,
        "credential_custody_note": (
            "Tokens used transiently from the session environment only; "
            "never written to file, log, commit, or artifact. Fingerprint "
            "of credential source recorded (names only)."),
        "credential_fingerprints": {
            "HF_TOKEN": fp(hf),
            "GIT_PAT": fp(os.environ.get("GIT_PAT")),
        },
        "hf_token_present": bool(hf),
        "git_pat_present": pat_present,
        "production_deployment": {
            "target_sha": target,
            "deployed_sha": deployed_sha,
            "deploy_id": None,
            "health_check_result": ("GREEN" if overall == "GREEN" else
                                    "BLOCKED" if "BLOCKED" in overall
                                    else "DEGRADED"),
            "drift": ("GREEN" if deployed_sha == target else "DRIFT"),
            "blocked_by": (
                None if deployed_sha == target and pushed else
                "Space runtime not yet rebuilt to target SHA at measurement "
                "time" if pushed else "push not verified"),
            "what_unblocks": (
                "Space auto-build on push to main; re-poll runtime_sha "
                "until it equals target_sha (observer-independent — "
                "Art. LXXIV: observation lag is not build failure)"
                if pushed else "git push origin main"),
        },
        "does_not_overwrite": "R512/SPACE_DEPLOY_RECORD.json (historical)",
        "reviewer_provenance": "AI_REVIEW",
    }
    out = REPO / "R519" / "R519_DEPLOY_RECORD.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({"overall": overall, "target": target,
                      "deployed": deployed_sha,
                      "push_identity": rec["push_identity"]}, indent=2))
    return 0 if overall == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
