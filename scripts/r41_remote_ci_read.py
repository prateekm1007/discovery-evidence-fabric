#!/usr/bin/env python3
"""r41_remote_ci_read.py — the D2 hard rule made executable (claim
c-0055): NO round reports green from local runs alone. The pushed
SHA's check-run conclusion is read from the GitHub API and the
{pushed_sha, remote_ci_conclusion, check_runs} block is emitted (and
optionally applied into a round record). A local-only green is a
typed defect from this rule forward.

Token handling: the credential is read from the gitignored vault by
NAME (GH_PAT, then GITHUB_TOKEN) into os.environ and passed to curl
in memory — the value is never printed, logged, or written anywhere
(the vault contract, Art. X: names only ever reach logs).

Exit codes: 0 all check-runs success; 1 any failure/timed_out/
cancelled/startup_failure; 2 API error (typed — the read could not
happen; a round may NOT claim green on exit 2); 3 pending/in-progress
(a round waits and re-reads; it may not claim green either).
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

OWNER_REPO = "prateekm1007/discovery-evidence-fabric"
_BAD = {"failure", "timed_out", "cancelled", "startup_failure",
        "action_required", "stale"}


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _token() -> str:
    import os
    for name in ("GH_PAT", "GITHUB_TOKEN"):
        v = os.environ.get(name)
        if v:
            return v
    raise RuntimeError("no GitHub credential in the vault (GH_PAT / "
                       "GITHUB_TOKEN) — the remote conclusion cannot "
                       "be read, so no green may be claimed")


def read_check_runs(sha: str) -> dict:
    """Read the check-runs for a pushed SHA. Returns the block; never
    prints the token."""
    tok = _token()
    out = subprocess.run(
        ["curl", "-s", "--max-time", "30",
         f"https://api.github.com/repos/{OWNER_REPO}/commits/{sha}/"
         f"check-runs",
         "-H", f"Authorization: Bearer {tok}",
         "-H", "Accept: application/vnd.github+json"],
        capture_output=True, text=True, timeout=40)
    if out.returncode != 0:
        return {"read_error": f"curl exit {out.returncode}"}
    try:
        d = json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"read_error": "non-JSON response (rate limit or auth)"}
    if d.get("message") and "check_runs" not in d:
        return {"read_error": str(d["message"])[:200]}
    runs = [{"name": cr.get("name"),
             "status": cr.get("status"),
             "conclusion": cr.get("conclusion")}
            for cr in (d.get("check_runs") or [])]
    if not runs:
        return {"read_error": "no check-runs recorded for the SHA "
                              "(CI may not have triggered — a push "
                              "without a check-run is NOT green)"}
    return {"pushed_sha": sha, "check_runs": runs, "read_at": _now()}


def conclude(block: dict) -> int:
    if "read_error" in block:
        block["remote_ci_conclusion"] = "unreadable"
        print(json.dumps(block, indent=1))
        print("REMOTE-CI: UNREADABLE — no green may be claimed "
              "(typed; fix the read, never the claim)", flush=True)
        return 2
    concl = []
    for r in block["check_runs"]:
        if r["status"] != "completed":
            return _pending(r)
        concl.append(r["conclusion"])
    if any(c in _BAD or c is None for c in concl):
        block["remote_ci_conclusion"] = "failure"
        print(json.dumps(block, indent=1))
        print("REMOTE-CI: FAILURE — the pushed gate is red; fix "
              "forward-only, never the claim", flush=True)
        return 1
    block["remote_ci_conclusion"] = "success"
    print(json.dumps(block, indent=1))
    print("REMOTE-CI: SUCCESS (read from the check-run API — the "
          "green is the remote's, not a local pytest run)", flush=True)
    return 0


def _pending(r: dict) -> int:
    print(json.dumps({"pushed_sha": r.get("name"), "status":
                      r["status"]}, indent=1))
    print("REMOTE-CI: PENDING — wait and re-read; no green yet",
          flush=True)
    return 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True)
    ap.add_argument("--apply", help="round-record JSON path; the "
                    "remote_ci block is written into it")
    a = ap.parse_args()
    block = read_check_runs(a.sha)
    rc = conclude(block)
    if a.apply and "read_error" not in block:
        rec = json.loads(Path(a.apply).read_text(encoding="utf-8"))
        rec["remote_ci"] = block
        Path(a.apply).write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main() or 0)
