#!/usr/bin/env python3
"""R467 — second-pass Atria engineer review for worker.py / server.py
(the first pass exhausted the reasoning budget on these two largest
diffs; this pass raises the ceiling and appends to the artifact)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KEY = os.environ.get("ATRIA_API_KEY", "").strip()
OUT = REPO / "R467" / "ATRIA_ENGINEER_REVIEW.json"

PROMPT = """You are the delegated code/engineer reviewer for the Toscanini
discovery engine (R467 round). Review this per-file unified diff for real
defects BEFORE commit. Honest typed failure states (BLOCKED/FAILED/
UNKNOWN/NOT_RUN/REJECTED) are a constitutional requirement — flag any
path that fakes success. Also flag: None/arity bugs, path errors, secret
or provider-id leakage to the product surface, and any data loss in
snapshot/restore. Answer in EXACTLY this format (max 4 findings):
VERDICT: SHIP | FIX_FIRST
FINDINGS:
- <file:approx-line — issue — BLOCKER/MAJOR/MINOR — one-line rationale>
If nothing rises to a finding: VERDICT: SHIP with an empty FINDINGS list.
"""


def main() -> int:
    if not KEY:
        print("FATAL: ATRIA_API_KEY unset")
        return 2
    out = {}
    for f in ["toscanini/worker.py", "toscanini/server.py"]:
        diff = subprocess.run(["git", "diff", "--", f], cwd=REPO,
                              capture_output=True, text=True,
                              check=True).stdout
        body = json.dumps({
            "model": "Atria-Dawn-Preview",
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": diff}],
            "max_tokens": 5000, "temperature": 0.2,
            "reasoning_effort": "low"}).encode()
        req = urllib.request.Request(
            "https://api.atria-asi.ai/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {KEY}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
            ch = resp["choices"][0]
            out[f] = {"finish_reason": ch.get("finish_reason"),
                      "content": ch["message"].get("content") or "",
                      "completion_tokens":
                          resp.get("usage", {}).get("completion_tokens")}
            print(f, "->", ch.get("finish_reason"),
                  resp.get("usage", {}).get("completion_tokens"),
                  "tokens,", len(out[f]["content"]), "chars")
        except Exception as exc:  # noqa: BLE001
            out[f] = {"error": repr(exc)}
            print(f, "ERROR", exc)
        time.sleep(1)
    d = json.loads(OUT.read_text())
    d["per_file"].update(out)
    for f, r in out.items():
        for line in r.get("content", "").splitlines():
            if line.strip().startswith("VERDICT:"):
                d["verdict_lines"].append((f, line.strip()))
    d.setdefault("notes", []).append(
        "worker.py/server.py reviewed in a second pass at "
        "max_tokens=5000 after the first pass exhausted the reasoning "
        "budget at 3000")
    OUT.write_text(json.dumps(d, indent=2) + "\n")
    print("saved ->", OUT.relative_to(REPO))
    for f, r in out.items():
        print("== ", f)
        print(r.get("content", "")[:1400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
