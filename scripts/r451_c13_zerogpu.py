#!/usr/bin/env python3
"""R451-C1.9 driver — the ONE bounded ZeroGPU experiment on the
canonical Space (no second Space; a temporary Space revision + a
temporary hardware request, both recorded and both reverted).

Phases (each idempotent, safe to re-invoke per tool call):

  upload   stage + upload the experiment tree (the minimal app +
           Dockerfile), WITHOUT touching the production engine tree's
           place in git (the Space repo's HEAD moves to the experiment
           revision temporarily — recorded; the production redeploy at
           the pinned engine SHA follows the experiment)
  hardware request the Space hardware zero-a10g (the ZeroGPU class)
  run      call POST /experiment ONCE (the bounded probe), capture the
           typed record, write R451/ZEROGPU_EXPERIMENT.json
  revert   request the Space hardware back to cpu-basic (the production
           class); the NEXT phase is the production redeploy at the
           pinned engine SHA (scripts/r451_c13_deploy.py)

Usage: HF_TOKEN=... python scripts/r451_c13_zerogpu.py <phase>
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
OUT = REPO / "R451" / "ZEROGPU_EXPERIMENT.json"

README_FRONTMATTER = """---
title: Toscanini Prod Validation
emoji: "\\U0001F3B5"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

<!-- R451-C1.9: the temporary ZeroGPU-experiment revision of the
canonical Space (the production engine is redeployed at the pinned
commit immediately after the experiment; this revision exists only to
measure the ZeroGPU transport resource class). -->

"""

DOCKERFILE = """# R451-C1.9 — the ZeroGPU experiment build (temporary canonical-Space
# revision; NOT the production engine image).
FROM python:3.12-slim
RUN set -eux; \\
    pip install --no-cache-dir "spaces" torch transformers accelerate; \\
    python -c "import spaces; print('spaces ok')"
COPY zerogpu_app.py /app/zerogpu_app.py
ENV PORT=7860
CMD ["python", "/app/zerogpu_app.py"]
"""


def _api():
    from huggingface_hub import HfApi
    return HfApi(token=HF_TOKEN)


def _probe(path: str, timeout: int = 60, method: str = "GET",
           token: str = ""):
    req = urllib.request.Request(
        f"{BASE}{path}", method=method,
        headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {})
    if method == "POST":
        req.add_header("Content-Type", "application/json")
        req.data = b"{}"
        if token:
            req.add_header("X-Experiment-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def _stage_status() -> str:
    req = urllib.request.Request(
        f"https://huggingface.co/api/spaces/{SPACE}/runtime",
        headers={"Authorization": f"Bearer {HF_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("stage", "UNKNOWN")
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


def phase_upload() -> int:
    api = _api()
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        (stage / "zerogpu_app.py").write_text(
            (REPO / "R451" / "zerogpu_app.py").read_text())
        (stage / "Dockerfile").write_text(DOCKERFILE)
        (stage / "README.md").write_text(README_FRONTMATTER)
        # pin the model revision (resolved LIVE now — deterministic
        # acquisition: the pinned sha is baked into the experiment env)
        try:
            req = urllib.request.Request(
                "https://huggingface.co/api/models/Qwen/Qwen3-1.7B",
                headers={"Authorization": f"Bearer {HF_TOKEN}"})
            with urllib.request.urlopen(req, timeout=30) as r:
                rev = json.loads(r.read().decode()).get("sha", "")
        except Exception:  # noqa: BLE001
            rev = ""
        rev = rev or os.environ.get("ZEROGPU_MODEL_REVISION", "")
        print(f"[zerogpu] pinned model revision: {rev[:12] or 'main'}")
        rev_file = {"revision": rev}
        import tarfile  # noqa: F401 — unused; keep imports minimal
        (stage / "model_pin.json").write_text(json.dumps(rev_file))
        secrets = {}
        if HF_TOKEN:
            api.add_space_secret(repo_id=SPACE, key="HF_TOKEN",
                                 value=HF_TOKEN)
        api.add_space_variable(repo_id=SPACE, key="ZEROGPU_MODEL",
                               value="Qwen/Qwen3-1.7B")
        if rev:
            api.add_space_variable(repo_id=SPACE, key="ZEROGPU_MODEL_"
                                                     "REVISION",
                                   value=rev)
        api.add_space_variable(repo_id=SPACE, key="ZEROGPU_DURATION_S",
                               value="240")
        if secrets:
            print(f"[zerogpu] secrets wired: {sorted(secrets)}")
        rev_out = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=("R451-C1.9: the temporary ZeroGPU experiment "
                            "revision (one bounded probe; the production "
                            "engine is redeployed at the pinned commit "
                            "right after)"))
        print(f"[zerogpu] experiment revision uploaded: {rev_out}")
    return 0


def phase_hardware(target: str = "zero-a10g") -> int:
    api = _api()
    print(f"[zerogpu] requesting hardware {target} ...")
    out = api.request_space_hardware(repo_id=SPACE, hardware=target)
    print(f"[zerogpu] hardware request: {out}")
    return 0


def phase_wait_runtime(timeout_s: int = 1500) -> int:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        stage = _stage_status()
        status, body = _probe("/status", timeout=30)
        print(f"[zerogpu] stage={stage} probe={status} "
              f"({int(time.time() - t0)}s)", flush=True)
        if status == 200 and body.get("spaces_available") is not None:
            print("[zerogpu] experiment app is UP")
            return 0
        time.sleep(20)
    print("[zerogpu] TIMEOUT waiting for the experiment runtime")
    return 1


def phase_run() -> int:
    token = os.environ.get("ZEROGPU_EXPERIMENT_TOKEN", "")
    print("[zerogpu] calling POST /experiment (the ONE bounded probe)...")
    status, rec = _probe("/experiment", timeout=900, method="POST",
                         token=token)
    print(f"[zerogpu] probe status={status}")
    if status != 200:
        print(json.dumps(rec, indent=1)[:2000])
        return 1
    rec["captured_by"] = ("scripts/r451_c13_zerogpu.py (the coding "
                          "environment, through the public Space URL)")
    rec["canonical_space"] = SPACE
    rec["hardware_at_experiment"] = "zero-a10g (ZeroGPU)"
    rec["budget_note"] = ("the operator-stated 40-minute ZeroGPU budget: "
                          "this experiment consumed "
                          f"{rec.get('gpu_minutes_consumed_estimate')} "
                          "estimated GPU minutes (ONE bounded probe)")
    OUT.write_text(json.dumps(rec, indent=1, default=str))
    print(f"[zerogpu] record -> {OUT}")
    print(f"[zerogpu] verdict: {rec.get('verdict')}")
    return 0


def phase_revert() -> int:
    return phase_hardware("cpu-basic")


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    if phase == "upload":
        return phase_upload()
    if phase == "hardware":
        return phase_hardware(sys.argv[2] if len(sys.argv) > 2
                              else "zero-a10g")
    if phase == "wait":
        return phase_wait_runtime(int(sys.argv[2]) if len(sys.argv) > 2
                                  else 1500)
    if phase == "run":
        return phase_run()
    if phase == "revert":
        return phase_revert()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
