#!/usr/bin/env python3
"""r21_ci_receipt.py — token-free queue-CI check-run receipts for the R21
Art. 29 round (read-only GitHub API GETs; the PAT stays in the vault and
is never printed, per Art. 12/17 and the F33 custody rules).
Writes eval/queue_ci_evidence_r21.json."""
import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from r7_queue_runner import _load_key_vault  # noqa: E402

_load_key_vault()
PAT = os.environ["GH_PAT"]
SHA_FILE = sys.argv[1] if len(sys.argv) > 1 else None

COMMITS = SHA_FILE.split(",") if SHA_FILE else [
    "b5cf10c4e", "f123879fd", "4de6e4c38", "d3d143223"]
API = "https://api.github.com/repos/prateekm1007/discovery-evidence-fabric"


def resolve(sha):
    req = urllib.request.Request(
        f"{API}/commits/{sha}", headers={"Authorization": f"token {PAT}",
                                         "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["sha"]


def checks(full_sha):
    req = urllib.request.Request(
        f"{API}/commits/{full_sha}/check-runs?per_page=20",
        headers={"Authorization": f"token {PAT}",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("check_runs", [])


evidence = {"record": "QUEUE_CI_EVIDENCE_R21/1.0.0 (token-free)",
            "at": datetime.datetime.now(datetime.UTC).isoformat().replace(
                "+00:00", "Z"),
            "commits": []}
for sha in COMMITS:
    full = resolve(sha)
    runs = checks(full)
    evidence["commits"].append({
        "sha": sha, "full_sha": full,
        "check_runs": [{"name": c.get("name"), "status": c.get("status"),
                        "conclusion": c.get("conclusion"),
                        "html_url": c.get("html_url")} for c in runs]})
    for c in runs:
        print(f"{sha} {c.get('name'):<42} {c.get('status'):<10} "
              f"{c.get('conclusion')}")
(REPO / "eval" / "queue_ci_evidence_r21.json").write_text(
    json.dumps(evidence, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("-> eval/queue_ci_evidence_r21.json")
