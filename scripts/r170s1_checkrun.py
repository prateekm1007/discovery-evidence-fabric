#!/usr/bin/env python3
"""r170s1_checkrun.py — authenticated check-run read for a commit sha
(DIR 5 acceptance: the tip check-run from the API, quoted enums only)."""
import json, os, sys, time, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for line in (REPO / ".env.keys").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)
TOK = os.environ.get("GH_PAT", "")
SHA = sys.argv[1]
UA = "r170s1-checkrun-read"

def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOK}", "User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())

runs = api(f"https://api.github.com/repos/prateekm1007/discovery-evidence-fabric/commits/{SHA}/check-runs")
for c in runs.get("check_runs", []):
    print(c.get("name"), "|", c.get("status"), "|", c.get("conclusion"))
if not runs.get("check_runs"):
    print("no check-runs yet for", SHA)
