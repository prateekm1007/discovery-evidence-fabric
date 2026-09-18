"""R510 observer tick (B1) — stateless single watchdog poll for scheduler use.

Runs scripts/r509_battery_watchdog.py --live --once as a subprocess and appends
one JSONL row to R510/WATCHDOG_TICK_LOG.jsonl. Observer-side only: read-only
Space GETs + a durable-branch fetch; never touches workers, never resubmits,
never writes secrets (BS-021). A tick failure is an OBSERVATION_GAP about the
watcher, never evidence about the watched runs (Art. LXXIV/XXV).

Windows note (measured R510-C1): the watchdog shells out to plain `git`, which
is absent from PATH on stock Windows (WinError 2 -> fail-closed
OBSERVATION_GAP). This wrapper prepends the standard install locations when
`git` is not already resolvable, on Windows and POSIX alike.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHDOG = os.path.join(REPO, "scripts", "r509_battery_watchdog.py")
TICK_LOG = os.path.join(REPO, "R510", "WATCHDOG_TICK_LOG.jsonl")
ALERT_LOG = os.path.join(REPO, "R510", "WATCHDOG_TICK_ALERTS.jsonl")

GIT_DIRS = (
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files\Git\bin",
    "/usr/bin",
    "/usr/local/bin",
)


def ensure_git_on_path() -> str:
    found = shutil.which("git")
    if found:
        return found
    for d in GIT_DIRS:
        cand = os.path.join(d, "git.exe" if os.name == "nt" else "git")
        if os.path.isfile(cand):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            return cand
    return ""


def main() -> int:
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    git = ensure_git_on_path()
    row = {"at": at, "tick": "r510-observe-tick", "reviewer_provenance": "AI_REVIEW"}
    if not git:
        row["result"] = "OBSERVATION_GAP"
        row["error"] = "git executable not found on PATH"
    else:
        try:
            r = subprocess.run(
                [sys.executable, WATCHDOG, "--live", "--once",
                 "--alert-log", ALERT_LOG],
                cwd=REPO, capture_output=True, text=True, timeout=600)
            row["result"] = "TICK_OK" if r.returncode == 0 else "TICK_NONZERO"
            row["exit"] = r.returncode
            row["tail"] = (r.stdout + r.stderr)[-800:]
        except Exception as e:  # watcher-side failure only, never run evidence
            row["result"] = "OBSERVATION_GAP"
            row["error"] = type(e).__name__ + ": " + str(e)[:200]
    os.makedirs(os.path.dirname(TICK_LOG), exist_ok=True)
    with open(TICK_LOG, "a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
