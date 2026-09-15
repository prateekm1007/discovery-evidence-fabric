#!/usr/bin/env python3
"""R472 — the CTO/engineer protocol: the implemented R472 diff goes to
the Atria-Dawn-Preview engineer as a two-pass REVIEW (the R470/R471
measured pattern: per-file split, reasoning_effort low, generous
max_tokens; engineer output is EVIDENCE, never authority — the CTO
reconciles every finding against the green tests).

Transcript: R472/ATRIA_ENGINEER_REVIEW.json (verbatim, findings typed).
Values (keys) come from the environment only (BS-021); the transcript
records the engineer's words and the CTO's dispositions, never secrets.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PLAIN_UA = "Python-urllib/3.11"
BASE = "https://api.atria-asi.ai"
MODEL = "Atria-Dawn-Preview"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "R472", "ATRIA_ENGINEER_REVIEW.json")

FILES = [
    ("toscanini/worker.py", "the POWER-leg fix (order + guarded "
     "durable copy) — the auditor's root cause is the ordering"),
    ("toscanini/user_state.py", "the COMPLETED_KILLED single-frame "
     "state (terminal de-collision)"),
    ("TOSCANINI_UI/webapp/components/Conversation.tsx",
     "the compliance-state mapping (the P2 dead-code defect)"),
]

SYSTEM = (
    "You are the delegated code ENGINEER in a CTO/engineer protocol. "
    "Review the provided diff against the stated intent. Report only "
    "defects you can argue from the code itself: correctness bugs, "
    "honesty-of-records problems, missed edge cases, test gaps. For "
    "each finding output: SEVERITY (BLOCKER/MAJOR/MINOR), FILE, "
    "FINDING (one paragraph), SUGGESTED_FIX. If a file is clean, say "
    "CLEAN for it. Do not restate the diff. Do not propose stylistic "
    "rewrites."
)


def _call(messages, max_tokens=12000):
    key = os.environ.get("ATRIA_API_KEY", "").strip()
    body = json.dumps({
        "model": MODEL, "messages": messages, "max_tokens": max_tokens,
        "reasoning_effort": "low", "temperature": 0.2,
    }).encode()
    r = urllib.request.Request(
        f"{BASE}/v1/chat/completions", data=body, headers={
            "Content-Type": "application/json", "User-Agent": PLAIN_UA,
            "Authorization": f"Bearer {key}"})
    t0 = time.time()
    last = ""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(r, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            ch = (data.get("choices") or [{}])[0]
            content = (ch.get("message") or {}).get("content")
            if content and content.strip():
                return {"ok": True, "content": content,
                        "latency_s": round(time.time() - t0, 1),
                        "finish": ch.get("finish_reason")}
            last = "EMPTY_CONTENT_WITH_FINISH"
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)[:200]
        time.sleep(4 + attempt * 4)
    return {"ok": False, "error": last,
            "latency_s": round(time.time() - t0, 1)}


def main() -> int:
    out = {"round": "R472",
           "protocol": "CTO/engineer — engineer REVIEW pass of the "
                       "implemented audit fixes (two-pass per file if "
                       "transport allows)",
           "engineer_model": MODEL,
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
           "passes": []}
    for path, intent in FILES:
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--", path], cwd=REPO,
            capture_output=True, text=True).stdout
        if not diff.strip():
            diff = "(no diff — new file or unchanged)"
        msg = (f"INTENT: {intent}\n\n"
               f"DIFF ({path}):\n```diff\n{diff[:14000]}\n```\n\n"
               "Review this diff. Findings or CLEAN per the system "
               "rules.")
        res = _call([{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": msg}])
        out["passes"].append({
            "file": path, "intent": intent,
            "diff_bytes": len(diff), "response": res})
        status = "OK" if res.get("ok") else f"FAILED ({res.get('error')})"
        print(f"[review] {path}: {status}")
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"WROTE {OUT}")
    ok = all(p["response"].get("ok") for p in out["passes"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
