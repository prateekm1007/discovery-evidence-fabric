#!/usr/bin/env python3
"""R447 phase-split deploy — upload + env contract in ONE tool call.

The sandbox kills every spawned process at the tool-call boundary (measured:
setsid+nohup+disown survives <90 s), so the monolithic deploy driver cannot
run to completion in the background. This script performs the phases that
MUST happen from this machine within one call:

  1. stage the tracked tree (git archive) at HEAD
  2. apply the R446-HF adapter Dockerfile (reuses the driver's function)
  3. write the Space README WITH the HF frontmatter (sdk: docker,
     app_port: 7860) — the CONFIG_ERROR the previous session hit (the
     git-archive overwrote the frontmatter) is fixed UPFRONT this time
  4. upload_folder to the canonical Space
  5. the env contract (variables + secrets)

The Docker BUILD then runs on HF's own infrastructure (independent of this
process's lifetime); build completion + identity verification happen in
follow-up polling calls (scripts/r447_deploy_verify.py).

Usage: HF_TOKEN=... GITHUB_TOKEN=... python scripts/r447_deploy_upload.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# reuse the canonical deploy driver's adapter (ONE implementation, Art. X)
sys.path.insert(0, str(REPO / "scripts"))
import r447_hf_deploy as driver  # noqa: E402

SPACE = driver.SPACE
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
PORTFOLIO_COMMIT = os.environ.get(
    "PORTFOLIO_COMMIT", "0914755c5832f332abe5d74ed1655cd27764ecc0")

README_FRONTMATTER = """---
title: Toscanini Prod Validation
emoji: "\\U0001F3B5"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

<!-- The HF Space card frontmatter (sdk: docker, app_port: 7860) — the
canonical engine README follows. The git-archive deploy would otherwise
strip it (the CONFIG_ERROR of the first R447 deploy, fixed upfront). -->

"""


def main() -> int:
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
        cwd=str(REPO)).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True,
        cwd=str(REPO)).stdout.strip()
    if dirty:
        print("FATAL: working tree dirty — commit first")
        return 2
    print(f"[r447-upload] target commit: {commit}")

    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", "HEAD"], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        n_files = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r447-upload] staged {n_files} tracked files "
              f"({archive.stat().st_size / 1e6:.0f} MB tar)")

        # the adapter Dockerfile (the R446-HF recipe)
        (stage / "Dockerfile").write_text(driver._adapter_dockerfile(commit))

        # the README WITH frontmatter (CONFIG_ERROR fixed upfront)
        engine_readme = (stage / "README.md").read_text(errors="replace") \
            if (stage / "README.md").exists() else ""
        (stage / "README.md").write_text(
            README_FRONTMATTER + engine_readme)

        print("[r447-upload] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"R447 deploy: engine tree at {commit[:12]} — the "
                f"run-not-found owner-capability transport fix "
                f"(X-Tosca-Owner header + SSE owner parameter + CHIPS "
                f"cookie + webapp persistence), the canonical Space "
                f"selection record, phases 1/2/6/7 (geometry identity "
                f"join, package terminal join, attacker v2, join "
                f"attacks), and the C2 system-Chromium alignment; "
                f"Space README frontmatter preserved upfront"),
        )
        print(f"[r447-upload] Space revision: {rev} "
              f"({time.time() - t0:.0f}s upload)")

    # the env contract
    api.add_space_variable(repo_id=SPACE, key="PORT", value="7860")
    api.add_space_variable(
        repo_id=SPACE, key="ZAI_BASE_URL",
        value="https://router.huggingface.co/v1/chat/completions")
    api.add_space_variable(repo_id=SPACE, key="ZAI_MODEL",
                           value="zai-org/GLM-5.3")
    api.add_space_variable(
        repo_id=SPACE, key="DURABLE_STATE_ENABLED", value="1")
    api.add_space_variable(
        repo_id=SPACE, key="DURABLE_STATE_BRANCH", value="runtime-state-hf")
    api.add_space_secret(repo_id=SPACE, key="ZAI_API_KEY", value=HF_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=GITHUB_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=PORTFOLIO_COMMIT)
    print("[r447-upload] env contract wired "
          "(ZAI_MODEL=zai-org/GLM-5.3, durable state on runtime-state-hf)")

    state = {"phase": "uploaded", "github_sha": commit, "space": SPACE,
             "space_revision": rev if isinstance(rev, str) else str(rev),
             "uploaded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}
    out = REPO / "scripts" / "r447_deploy_state.json"
    out.write_text(json.dumps(state, indent=1))
    print(f"[r447-upload] state -> {out}")
    print("[r447-upload] NEXT: the build runs on HF — poll with "
          "scripts/r447_deploy_verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
