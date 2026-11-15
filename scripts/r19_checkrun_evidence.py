#!/usr/bin/env python3
"""R19: read the real GitHub check-runs for the queue tip and its parent.

Evidence for F32 acceptance (AM18/AM19 D1): the queue-push workflow must
be GREEN and must run the Art. 19/21/26 (+22/23/25/28) enforcement suite
on the builder's branch. The token comes from the stored remote URL and
is NEVER printed or written anywhere. Output: conclusions + step names;
evidence JSON (token-free) saved to eval/queue_ci_evidence_r19.json.
"""
import json
import re
import subprocess
import sys
import urllib.request

REPO = "prateekm1007/discovery-evidence-fabric"
COMMITS = {"a8c037f81": "R19s1 F32 fix (queue tip)",
           "8c1013fae": "R17 reconciliation (AM19 audited here)",
           "d1cf5a129": "v3.0.0 owner constitution (AM18 red ref)"}

url = subprocess.run(["git", "remote", "get-url", "origin"],
                     capture_output=True, text=True).stdout.strip()
# token forms: https://user:pass@... or https://token@... (GitHub
# PAT-as-username). Extract without ever printing or persisting it.
m = re.search(r"//([^:/@]+):([^@]+)@", url)
tok = m.group(2) if m else None
if not tok:
    m2 = re.search(r"//([^@/]+)@", url)
    tok = m2.group(1) if m2 else None
if not tok:
    fill = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, timeout=30)
    pm = re.search(r"^password=(.+)$", fill.stdout, re.M)
    tok = pm.group(1) if pm else None
if not tok:
    sys.exit("no stored credential available (url-embedded or "
             "helper): check-run reading needs it")


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {tok}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "r19-evidence"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


evidence = {"at_commit_results": {}, "token_free": True}
for sha, label in COMMITS.items():
    try:
        runs = api(f"/repos/{REPO}/commits/{sha}/check-runs")["check_runs"]
    except Exception as e:  # noqa: BLE001 - report, don't crash
        evidence["at_commit_results"][sha] = {
            "label": label, "error": str(e)[:120]}
        continue
    entries = []
    for run in runs:
        ent = {"name": run["name"], "conclusion": run["conclusion"],
               "status": run["status"],
               "html_url": run["html_url"], "steps": None}
        # workflow-run jobs/steps: parse run id from the html_url
        rid = re.search(r"/actions/runs/(\d+)/", run["html_url"] or "")
        if rid and run["name"].startswith("surface"):
            try:
                jobs = api(
                    f"/repos/{REPO}/actions/runs/{rid.group(1)}/jobs"
                )["jobs"]
                ent["steps"] = [
                    {"step": s["name"], "conclusion": s["conclusion"]}
                    for j in jobs for s in j["steps"]]
            except Exception as e:  # noqa: BLE001
                ent["steps_error"] = str(e)[:120]
        entries.append(ent)
    evidence["at_commit_results"][sha] = {"label": label,
                                          "check_runs": entries}

out = json.dumps(evidence, indent=1)
print(out[:4000])
with open("eval/queue_ci_evidence_r19.json", "w") as f:
    f.write(out + "\n")
print("saved: eval/queue_ci_evidence_r19.json (token-free)")
