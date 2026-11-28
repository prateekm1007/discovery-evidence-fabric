#!/usr/bin/env python3
"""R80: fetch the failing 'surface' check-run's output + annotations for a
pushed SHA (diagnosis only; token never printed — the r41 reader's pattern)."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "r41", Path(__file__).resolve().parent / "r41_remote_ci_read.py")
r41 = importlib.util.module_from_spec(spec)
sys.modules["r41"] = r41
spec.loader.exec_module(r41)

sha = sys.argv[1]
tok = r41._token()
url = (f"https://api.github.com/repos/{r41.OWNER_REPO}/commits/{sha}/"
       f"check-runs")
out = subprocess.run(
    ["curl", "-sS", "-H", f"Authorization: Bearer {tok}",
     "-H", "Accept: application/vnd.github+json", url],
    capture_output=True, text=True, timeout=60)
data = json.loads(out.stdout)
for cr in data.get("check_runs", []):
    print("check:", cr["name"], "| conclusion:", cr.get("conclusion"))
    o = cr.get("output") or {}
    print("title:", (o.get("title") or "")[:200])
    print("summary:", (o.get("summary") or "")[:1200])
    ann_url = cr.get("annotations_url", "").split("{")[0]
    if ann_url:
        ann = subprocess.run(
            ["curl", "-sS", "-H", f"Authorization: Bearer {tok}",
             "-H", "Accept: application/vnd.github+json", ann_url],
            capture_output=True, text=True, timeout=60)
        for a in json.loads(ann.stdout)[:12]:
            print(f"  [{a.get('annotation_level')}] "
                  f"L{a.get('start_line')}: {a.get('message')[:220]}")
# the workflow job step names + log tail
runs = subprocess.run(
    ["curl", "-sS", "-H", f"Authorization: Bearer {tok}",
     f"https://api.github.com/repos/{r41.OWNER_REPO}/commits/{sha}/"
     f"check-suites"], capture_output=True, text=True, timeout=60)
suites = json.loads(runs.stdout)
for s in suites.get("check_runs", []) or []:
    pass
suite_ids = [s["id"] for s in suites.get("check_suites", [])]
for sid in suite_ids[:2]:
    j = subprocess.run(
        ["curl", "-sS", "-H", f"Authorization: Bearer {tok}",
         f"https://api.github.com/repos/{r41.OWNER_REPO}/check-suites/"
         f"{sid}/check-runs"], capture_output=True, text=True, timeout=60)
    for cr in json.loads(j.stdout).get("check_runs", []):
        print("suite run:", cr["name"], cr.get("conclusion"),
              "| details:", (cr.get("details_url") or "")[-30:])
