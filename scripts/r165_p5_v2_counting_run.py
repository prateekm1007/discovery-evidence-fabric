#!/usr/bin/env python3
"""r165_p5_v2_counting_run.py — the P5 v2 FRESH counting-run wrapper (claim c-0269).

V127 re-authorization: "run the same sealed corpus with live seats
for a counting verdict (the 21/30 was infra)". This wrapper:
  1. verifies BOTH seats are live (G0 tokenrouter + J2 cent-ai hy4)
     before firing — the r163s1 lesson: firing during a seat outage
     burns items fail-closed (the 21/30 infra-terminal);
  2. archives the infra-terminal 21/30 checkpoint + run record to
     eval/r159_p5_v2_infra_terminal/ (they stay committed in git
     history too — no history rewriting, forward-only);
  3. fires the UNMODIFIED runner (DIR 6: the instrument is intact —
     same prompts, same bars, same seats, same sealed corpus
     c9670d8dd4b55c0c) with a fresh checkpoint, i.e. all 30 items
     under live seats;
  4. the byte-resume design carries the run across windows if
     needed (heartbeats per item, DIR 7).

Seat gate: BOTH G0 and J2 must probe 200 OK. If J2 is still 503,
the wrapper exits 2 WITHOUT archiving or firing (the hold stands).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CKPT = REPO / "eval/r159_p5_v2_checkpoint.json"
OUT = REPO / "eval/r159_p5_v2_run.json"
ARCHIVE = REPO / "eval/r159_p5_v2_infra_terminal"


def probe(base: str, key: str, model: str) -> bool:
    body = {"model": model, "max_tokens": 300,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}]}
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def main() -> int:
    tr_key = os.environ.get("TOKENROUTER_API_KEY", "")
    cent_key = os.environ.get("CENT_AI_API_KEY", "")
    tr_base = os.environ.get("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1")
    cent_base = os.environ.get("CENT_AI_BASE_URL", "https://api.cent-ai.dev/v1")

    print("[gate] probing G0 (tokenrouter) ...", flush=True)
    if not probe(tr_base, tr_key, "deepseek/deepseek-v4.1-flash-1017-free"):
        print("[gate] G0 NOT live — refusing to fire (exit 2)", flush=True)
        return 2
    print("[gate] G0 live. probing J2 (cent-ai hy4-flash:free) ...", flush=True)
    if not probe(cent_base, cent_key, "hy4-flash:free"):
        print("[gate] J2 NOT live (still 503?) — refusing to fire; "
              "the 21/30 hold stands (exit 2)", flush=True)
        return 2
    print("[gate] BOTH seats live — firing the fresh counting run", flush=True)

    # archive the infra-terminal hold (forward-only; also in git history)
    if CKPT.exists() or OUT.exists():
        ARCHIVE.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        for f in (CKPT, OUT):
            if f.exists():
                dest = ARCHIVE / f"{f.stem}_{stamp}{f.suffix}"
                shutil.copy2(f, dest)
                print(f"[archive] {f.name} -> {dest.name}", flush=True)
        (ARCHIVE / "README.json").write_text(json.dumps({
            "record": "R159_P5_V2_INFRA_TERMINAL/1.0.0",
            "what": "the 21/30 infra-terminal run (all PARTIAL fail-closed "
                    "under the cent-ai hy4 503 outage 2026-11-26 09:32Z->; "
                    "J1 raw 6 REC / 12 PART / 3 NR, canary 0/21, T1 21/21, "
                    "0 interventions)",
            "fate": "archived for the fresh V127-authorized counting run; "
                    "also committed in git history (forward-only)",
            "archived_at": stamp,
        }, indent=1) + "\n")
        CKPT.unlink(missing_ok=True)
        OUT.unlink(missing_ok=True)

    # fire the UNMODIFIED runner (fresh checkpoint -> all 30 items)
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/r159_p5_v2_run.py")],
        cwd=REPO)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
