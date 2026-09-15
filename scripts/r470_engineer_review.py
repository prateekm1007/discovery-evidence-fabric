#!/usr/bin/env python3
"""R470 — the CTO/engineer protocol, third exercise (REVIEW pass): the
engineer reviews the IMPLEMENTED diff per file (the measured-reliable
pattern after the design pass hit the reasoning-burn / 502 classes).

Files in scope (the load-bearing set):
  1. discovery_fabric/engine/directive_compliance.py (the new shared
     compliance instrument)
  2. discovery_fabric/a2/synthesize.py (constraint prompt block +
     mechanical check + one recorded repair retry)
  3. toscanini/worker.py (run-dir persistence + problem attach +
     compliance-semantics outcome card)
  4. toscanini/server.py (spawn-site constraint derivation)
  5. discovery_fabric/a2/classify.py (kill causes stated once)
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
OUT = REPO / "R470" / "ATRIA_ENGINEER_REVIEW_PASS2.json"

FILES = [
    "discovery_fabric/engine/directive_compliance.py",
    "discovery_fabric/a2/synthesize.py",
    "toscanini/worker.py",
    "discovery_fabric/a2/classify.py",
]

HEADER = """You are the delegated code/engineer for the Toscanini discovery
engine (CTO/engineer protocol). The CTO implemented the steering
directive-COMPLIANCE design (the external re-audit's P0-5 remainder:
power = exclude the parent's recorded mechanism from the child's
search; semantics = the outcome card judges compliance, not mere
change) plus the P1-3 record-layer fix (kill causes stated once).

Review THIS file's diff (and the new module in full). Look for:
correctness bugs, edge cases, security/secret-leak risks, Constitution
violations (the check must never mutate a verdict; no fuzzy matching
may enter verify.py; honest typing — a violated candidate is returned
with violation_final=true, never hidden; product surfaces carry no
transport vocabulary), and layering violations (engine modules must
not import from toscanini/).

Respond in EXACTLY this format:
FINDINGS: numbered list; each = SEVERITY (BLOCKER|MAJOR|MINOR|NOTE) |
location | the problem | the concrete fix.
VERDICT: APPROVE | APPROVE_WITH_FIXES | REQUEST_CHANGES.

"""

KEYS = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
        "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
        "ATRIA_API_KEY_7", "ATRIA_API_KEY_8", "ATRIA_API_KEY_9",
        "ATRIA_API_KEY_10"]


def call_atria(prompt: str, max_tokens: int, key: str,
               retries: int = 3) -> dict:
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "reasoning_effort": "low",
    }).encode()
    req = urllib.request.Request(
        "https://api.atria-asi.ai/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(5 + attempt * 5)
    raise RuntimeError(f"atria transport failed after {retries} "
                       f"attempts: {last}")


def diff_for(path: str) -> str:
    if (REPO / path).exists() and not (REPO / path).is_dir():
        if path in {f for f in FILES}:
            d = subprocess.run(
                ["git", "-C", str(REPO), "diff", "HEAD", "--", path],
                capture_output=True, text=True)
            if d.stdout.strip():
                return d.stdout
            # new file: send the full content
            body = (REPO / path).read_text()
            return f"NEW FILE (full content):\n```python\n{body}\n```"
    return f"(unavailable: {path})"


def main() -> int:
    key = next((os.environ[k] for k in KEYS
                if os.environ.get(k, "").strip()), "")
    if not key:
        print("NO_ATRIA_KEY", file=sys.stderr)
        return 2
    reviews = []
    for path in FILES:
        payload = diff_for(path)
        if len(payload) > 26000:
            payload = payload[:26000] + "\n... (truncated)"
        prompt = HEADER + f"\nFILE: {path}\n\n{payload}"
        print(f"engineer review: {path} ({len(payload)} chars) ...")
        try:
            resp = call_atria(prompt, 9000, key)
        except RuntimeError as exc:
            reviews.append({"file": path, "error": str(exc)})
            print(f"  TRANSPORT-FAILED: {path}")
            continue
        ch = (resp.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        reviews.append({
            "file": path,
            "model": resp.get("model"),
            "usage": resp.get("usage"),
            "finish_reason": ch.get("finish_reason"),
            "review_verbatim": content,
        })
        print(f"  -> {len(content)} chars, finish={ch.get('finish_reason')}")
    rec = {
        "round": "R470",
        "protocol": "CTO (this session) / engineer (Atria-Dawn-Preview)",
        "subject": ("steering directive-compliance implementation review "
                    "(P0-5 remainder) + P1-3 record-layer dedupe"),
        "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
        "key_fingerprint": (key[:6] + "..." + key[-4:]),
        "reviews": reviews,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"reviews saved: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
