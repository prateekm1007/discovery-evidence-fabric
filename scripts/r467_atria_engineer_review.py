#!/usr/bin/env python3
"""R467 — per-file Atria engineer review (the 30K-char single-shot
diff exhausts the reasoning budget even at reasoning_effort=low; the
per-file review keeps each call inside the model's reasoning headroom
— measured this session). Evidence artifact, CTO weighs findings.
"""
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

FILES = [
    "discovery_fabric/engine/llm_registry.py",
    "discovery_fabric/engine/model_routing.py",
    "discovery_fabric/engine/runtime_admission.py",
    "discovery_fabric/engine/transport_capability.py",
    "toscanini/conversational/transport_invisibility.py",
    "toscanini/durable.py",
    "toscanini/worker.py",
    "toscanini/server.py",
]

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


def review_one(diff: str) -> dict:
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": diff},
        ],
        "max_tokens": 3000,
        "temperature": 0.2,
        "reasoning_effort": "low",
    }).encode()
    req = urllib.request.Request(
        "https://api.atria-asi.ai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                out = json.load(r)
            ch = out["choices"][0]
            return {"finish_reason": ch.get("finish_reason"),
                    "content": ch["message"].get("content") or "",
                    "completion_tokens":
                        out.get("usage", {}).get("completion_tokens")}
        except Exception as exc:  # noqa: BLE001 — retry, typed last err
            last_err = repr(exc)
            time.sleep(4)
    return {"finish_reason": "ERROR", "content": "",
            "completion_tokens": 0, "error": last_err}


def main() -> int:
    if not KEY:
        print("FATAL: ATRIA_API_KEY unset")
        return 2
    results = {}
    for f in FILES:
        diff = subprocess.run(["git", "diff", "--", f], cwd=REPO,
                              capture_output=True, text=True,
                              check=True).stdout
        if not diff.strip():
            continue
        r = review_one(diff)
        results[f] = r
        print(f"{f}: finish={r['finish_reason']} "
              f"tokens={r['completion_tokens']} "
              f"content={len(r['content'])} chars")
        time.sleep(1)

    verdicts = []
    for f, r in results.items():
        for line in r["content"].splitlines():
            if line.strip().startswith("VERDICT:"):
                verdicts.append((f, line.strip()))
    rec = {
        "round": "R467",
        "protocol": "CTO (main session) / ENGINEER (Atria-Dawn-Preview), "
                    "per-file review (single-shot 30K-char diff exhausts "
                    "the reasoning budget — measured, 3 attempts)",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "key_fingerprint": f"{KEY[:6]}...{KEY[-4:]}",
        "per_file": results,
        "verdict_lines": verdicts,
        "note": "review is evidence weighed by the CTO against the "
                "green test suite; recorded verbatim",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"\nartifact -> {OUT.relative_to(REPO)}")
    for f, v in verdicts:
        print(f"  {v}  <- {f.split('/')[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
