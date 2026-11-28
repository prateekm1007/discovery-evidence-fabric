#!/usr/bin/env python3
"""r170s1_ci_detail.py — pull the failing check-run's details for a sha:
suite names + conclusions + annotations (the CI surface is an aggregate)."""
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
UA = "r170s1-ci-detail"

def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOK}", "User-Agent": UA,
        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())

runs = api(f"https://api.github.com/repos/prateekm1007/discovery-evidence-fabric/commits/{SHA}/check-runs")
for c in runs.get("check_runs", []):
    print("==", c.get("name"), "|", c.get("status"), "|", c.get("conclusion"), "| id", c.get("id"))
    if c.get("conclusion") not in (None, "success", "skipping"):
        det = api(c.get("url") + "/annotations")
        for a in det:
            print("   ANN:", a.get("annotation_level"), "|", a.get("path"),
                  "|", a.get("start_line"), "|", (a.get("message") or "")[:400])
        out = c.get("output")
        if out:
            print("   OUT title:", out.get("title"), "| summary:",
                  (out.get("summary") or "")[:600])
