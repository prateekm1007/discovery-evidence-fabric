#!/usr/bin/env python3
"""r170s1_ci_log.py — pull the failed job's log tail for a commit sha."""
import json, os, sys, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for line in (REPO / ".env.keys").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)
TOK = os.environ.get("GH_PAT", "")
SHA = sys.argv[1]
UA = "r170s1-ci-log"

def api(url, raw=False):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOK}", "User-Agent": UA,
        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
        return b if raw else json.loads(b.decode())

runs = api(f"https://api.github.com/repos/prateekm1007/discovery-evidence-fabric/actions/runs?head_sha={SHA}&per_page=3")
for run in runs.get("workflow_runs", []):
    print("RUN", run.get("id"), run.get("name"), run.get("conclusion"))
    jobs = api(f"https://api.github.com/repos/prateekm1007/discovery-evidence-fabric/actions/runs/{run['id']}/jobs")
    for j in jobs.get("jobs", []):
        print(" JOB", j.get("id"), j.get("name"), j.get("conclusion"))
        for s in j.get("steps", []):
            if s.get("conclusion") not in ("success", "skipped", None):
                print("   STEP FAILED:", s.get("name"), s.get("conclusion"))
        if j.get("conclusion") not in ("success", "skipped", None):
            log = api(j.get("url") + "/logs", raw=True).decode("utf-8", "replace")
            lines = log.splitlines()
            keep = [l for l in lines if ("FAIL" in l.upper() or "ERROR" in l.upper()
                    or "assert" in l.lower() or "=====" in l)]
            print("   LOG lines:", len(lines), "| filtered:", len(keep))
            for l in keep[-40:]:
                print("   |", l[:220])
