#!/usr/bin/env python3
"""r110_ci_read.py — the round-close remote CI read (the auditor's
R110 direction 1: 'read remote CI with ETag before closing any
round').

Mechanics: the GitHub combined-status endpoint for a named SHA,
queried with the vault GH_PAT and an If-None-Match ETag — a 304
means the state is UNCHANGED since the last read (no fresh poll
needed); a 200 carries the fresh state + the new ETag. The read
record (eval/r110_ci_read.json) carries the SHA, conclusions, the
ETag, and the read times — the round close cites it, and the next
close re-uses the ETag first.

Usage: python3 scripts/r110_ci_read.py [--wait-minutes N]
  - with --wait-minutes, re-reads until the checks complete or the
    budget expires (the in-progress state is typed, never guessed).
Exit codes: 0 GREEN (or UNCHANGED-GREEN via 304), 3 RED/FAILED,
2 INFRA (auth/limit), 1 INCOMPLETE after the wait budget.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r110_ci_read.json"
ETAG_FILE = REPO / "eval" / ".r110_ci_etag"
OWNER_REPO = "prateekm1007/discovery-evidence-fabric"


def vault_key(name: str) -> str:
    for line in (REPO / ".env.keys").read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(2)


def read_status(sha: str, etag: str | None):
    token = vault_key("GH_PAT") if os.path.exists(REPO / ".env.keys") \
        and any(l.startswith("GH_PAT=")
                for l in (REPO / ".env.keys").read_text().splitlines()) \
        else vault_key("GITHUB_TOKEN")
    url = (f"https://api.github.com/repos/{OWNER_REPO}/commits/"
           f"{sha}/status")
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "User-Agent": "r110-ci-read"}
    if etag:
        headers["If-None-Match"] = etag
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode())
            return r.headers.get("ETag"), body, r.status
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return etag, None, 304
        if e.code in (403, 429):
            raise SystemExit(2)
        raise


def main() -> int:
    args = sys.argv[1:]
    wait_minutes = 0
    if "--wait-minutes" in args:
        wait_minutes = int(args[args.index("--wait-minutes") + 1])
    sha = os.environ.get("CI_READ_SHA") or \
        subprocess_rev()
    etag = ETAG_FILE.read_text().strip() if ETAG_FILE.exists() else None
    deadline = time.time() + wait_minutes * 60
    while True:
        etag, body, code = read_status(sha, etag)
        if code == 304:
            rec = json.loads(OUT.read_text())
            rec["reads"].append({
                "at": now(), "sha": sha, "http": 304,
                "state": rec["reads"][-1]["state"] if rec.get("reads")
                else "UNKNOWN",
                "typed": "UNCHANGED since the last read (ETag hit)"})
            out_state = rec["reads"][-1]["state"]
        else:
            state = body.get("state")
            statuses = [{"context": s.get("context"),
                         "state": s.get("state"),
                         "target_url": s.get("target_url")}
                        for s in body.get("statuses", [])]
            rec_path = OUT
            rec = json.loads(rec_path.read_text()) if rec_path.exists() \
                else {"record": "R110_CI_READ/1.0.0", "reads": []}
            rec["reads"].append({
                "at": now(), "sha": sha, "http": 200,
                "state": state, "statuses": statuses,
                "total_count": body.get("total_count")})
            out_state = state
        if etag:
            ETAG_FILE.write_text(etag)
        OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                       + "\n")
        print(f"[{now()}] {sha[:9]} http={code} state={out_state}")
        if out_state in ("success", "failure", "error"):
            print("CI state:", out_state,
                  "(SUCCESS)" if out_state == "success" else "(RED)")
            return 0 if out_state == "success" else 3
        if time.time() >= deadline:
            print("INCOMPLETE: checks still "
                  f"{out_state} after the wait budget")
            return 1
        time.sleep(60)


def subprocess_rev() -> str:
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"],
                          capture_output=True, text=True,
                          cwd=REPO).stdout.strip()


def now() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    sys.exit(main())
