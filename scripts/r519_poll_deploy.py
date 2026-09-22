#!/usr/bin/env python3
"""R519 §24 — poll the canonical Space until /api/version engine_commit
equals origin/main (Art. LXXI). Observer-independent: rebuild lag is not
failure (Art. LXXIV); this script only observes.
"""
from __future__ import annotations

import json
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
HOST = SPACE.replace("/", "-").replace("_", "-")
URL = f"https://{HOST}.hf.space/api/version"


def version():
    try:
        with urllib.request.urlopen(
                urllib.request.Request(
                    URL, headers={"User-Agent": "r519-poll"}),
                timeout=30, context=ssl.create_default_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def runtime():
    tok = None
    # transient read for the probe only — never printed
    import os
    tok = os.environ.get("HF_TOKEN")
    h = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        with urllib.request.urlopen(
                urllib.request.Request(
                    f"https://huggingface.co/api/spaces/{SPACE}/runtime",
                    headers=h),
                timeout=30, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def main() -> int:
    target = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/main"],
        cwd=str(REPO), text=True).split()[0]
    deadline = time.time() + float(sys.argv[1]) if len(sys.argv) > 1 else \
        time.time() + 600
    first = time.time()
    while True:
        st, b = version()
        rt = runtime()
        ec = None
        if st == 200:
            try:
                ec = json.loads(b).get("engine_commit")
            except Exception:  # noqa: BLE001
                pass
        age = int(time.time() - first)
        print(f"[+{age:>4}s] /api/version={st} engine_commit={str(ec)[:12]} "
              f"runtime_stage={rt.get('stage')} "
              f"runtime_sha={str(rt.get('sha'))[:12]}", flush=True)
        if ec == target:
            print(f"MATCH: deployed engine_commit == origin/main == {target}")
            return 0
        if time.time() > deadline:
            print(f"NOT_YET: target={target[:12]} "
                  f"engine_commit={str(ec)[:12]} after {age}s — "
                  f"Space still building at target (observer-lag, "
                  f"Art. LXXIV). Re-poll later; never call this failure.")
            return 3


if __name__ == "__main__":
    raise SystemExit(main())
