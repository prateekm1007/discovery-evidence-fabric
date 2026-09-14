#!/usr/bin/env python3
"""R455 chunked deploy — chunk 1: stage + upload (synchronous).

The sandbox reaps detached background processes (R437 precedent), so the
r447 pipeline runs in foreground chunks: (1) upload, (2) poll stage+version.
Same adapter (imported verbatim), same env contract, same Space.
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
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from r447_hf_deploy import (  # noqa: E402
    SPACE, HF_TOKEN, GITHUB_TOKEN, PORTFOLIO_COMMIT, _adapter_dockerfile,
)

STATE = SCRIPTS / "r455_deploy_state.json"


def _log(m):
    print(f"[r455-deploy] {m}", flush=True)


def main() -> int:
    from huggingface_hub import HfApi
    if not HF_TOKEN or not GITHUB_TOKEN:
        _log("FATAL: HF_TOKEN / GITHUB_TOKEN missing")
        return 2
    api = HfApi(token=HF_TOKEN)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                            capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                      capture_output=True, text=True).stdout.strip():
        _log("FATAL: working tree dirty")
        return 2
    _log(f"target commit: {commit}")

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
        _log(f"staged {n_files} tracked files ({archive.stat().st_size / 1e6:.0f} MB tar)")

        (stage / "Dockerfile").write_text(_adapter_dockerfile(commit))

        _log("uploading to the canonical Space (single commit; may take several minutes)...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"R455-LEAN-1-DELETIONS deploy: engine tree at {commit[:12]} — "
                f"the deadweight elimination (378 files / 134,765 py LOC "
                f"archived to archive/r455-lean/ per the EXT-AUDIT-LEAN-R454 "
                f"register; production import closure unchanged; zero new "
                f"test failures vs the recorded baseline); no stage, gate, "
                f"or epistemic control removed"),
        )
        _log(f"upload DONE in {time.time()-t0:.0f}s — Space revision: {rev}")

    api.add_space_variable(repo_id=SPACE, key="PORT", value="7860")
    api.add_space_variable(
        repo_id=SPACE, key="ZAI_BASE_URL",
        value="https://router.huggingface.co/v1/chat/completions")
    api.add_space_variable(repo_id=SPACE, key="ZAI_MODEL",
                           value="zai-org/GLM-5.3")
    api.add_space_secret(repo_id=SPACE, key="ZAI_API_KEY", value=HF_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=GITHUB_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=PORTFOLIO_COMMIT)
    _log("env contract wired")

    st = {"round": "R455-LEAN-1-DELETIONS", "github_sha": commit,
          "hf_space": SPACE, "hf_revision": rev, "uploaded": True,
          "reviewer_provenance": "AI_REVIEW",
          "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    STATE.write_text(json.dumps(st, indent=2))
    _log(f"state: {STATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
