#!/usr/bin/env python3
"""R80: list Actions runs for a SHA, find the failed job, dump failing step
names + log tail. Token never printed."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

sha = sys.argv[1]
if len(sha) < 40:
    sha = subprocess.run(["git", "rev-parse", sha], capture_output=True,
                         text=True, check=True).stdout.strip()
tok = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
hdr = ["-H", f"Authorization: Bearer {tok}"]


def api(url):
    r = subprocess.run(["curl", "-sS", *hdr, url], capture_output=True,
                       text=True, timeout=60)
    return json.loads(r.stdout)


runs = api(f"https://api.github.com/repos/prateekm1007/"
           f"discovery-evidence-fabric/actions/runs?head_sha={sha}")
for run in runs.get("workflow_runs", []):
    print(f"run {run['id']} | {run['name']} | {run['conclusion']}")
    if run["conclusion"] == "success":
        continue
    jobs = api(run["jobs_url"])
    for job in jobs.get("jobs", []):
        print(f"  job {job['id']} | {job['name']} | {job['conclusion']}")
        for st in job.get("steps", []):
            print(f"    step: {st['name']} -> {st['conclusion']}")
        if job["conclusion"] == "failure":
            log = subprocess.run(
                ["curl", "-sSL", *hdr,
                 f"https://api.github.com/repos/prateekm1007/"
                 f"discovery-evidence-fabric/actions/jobs/{job['id']}/logs"],
                capture_output=True, text=True, timeout=120)
            lines = log.stdout.splitlines()
            # keep the tail where the failure surfaces
            tail = [l for l in lines[-80:]]
            print("  --- log tail ---")
            for l in tail:
                print("   ", l[:200])
