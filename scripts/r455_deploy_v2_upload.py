#!/usr/bin/env python3
"""R455 chunked deploy v2 — the R451-C1.3 production adapter.

The first R455 upload used the plain r447 adapter, which omits the
llama.cpp local route — regressing the Space's zero-paid transport (the
same regression the R446-C1 deploy introduced; root-caused this round from
/api/health localqwen credential=NOT_CONFIGURED). This redeploy uses the
r451_c13 adapter (llama.cpp b10930 + sha-pinned Qwen3-1.7B Q4_K_M GGUF +
env-gated entrypoint) and the full R451-C1.3 env contract, plus the Space
card front matter (the CONFIG_ERROR fix). Synchronous chunks (the sandbox
reaps background processes).
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
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
PORTFOLIO_COMMIT = os.environ.get(
    "PORTFOLIO_COMMIT", "0914755c5832f332abe5d74ed1655cd27764ecc0")
STATE = SCRIPTS / "r455_deploy_state.json"


def _log(m):
    print(f"[r455-deploy-v2] {m}", flush=True)


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

        # the R451-C1.3 adapter Dockerfile (llama.cpp pinned tag build +
        # sha-pinned GGUF + the env-gated entrypoint route)
        (stage / "Dockerfile").write_text(
            driver._r451_c13_adapter_dockerfile(commit))

        # the README WITH front matter (the CONFIG_ERROR fix)
        engine_readme = (stage / "README.md").read_text(errors="replace") \
            if (stage / "README.md").exists() else ""
        (stage / "README.md").write_text(
            uploader.README_FRONTMATTER + engine_readme)

        _log("uploading to the canonical Space (R451-C1.3 adapter)...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"R455-LEAN-1-DELETIONS redeploy: engine tree at "
                f"{commit[:12]} with the R451-C1.3 production adapter — "
                f"the deadweight elimination (378 files / 134,765 py LOC "
                f"archived to archive/r455-lean/; production import "
                f"closure unchanged; zero new test failures) + the "
                f"Space's own zero-paid local route RESTORED (the plain "
                f"r447 adapter dropped it in the R446-C1 deploy — "
                f"root-caused this round from localqwen "
                f"credential=NOT_CONFIGURED) + the Space card frontmatter "
                f"(the CONFIG_ERROR fix, now pinned in the driver)"),
        )
        _log(f"upload DONE in {time.time()-t0:.0f}s — Space revision: {rev}")

    # the env contract: the R447/R450 variables + the C1.3 local-route gate
    api.add_space_variable(repo_id=SPACE, key="PORT", value="7860")
    api.add_space_variable(
        repo_id=SPACE, key="ZAI_BASE_URL",
        value="https://router.huggingface.co/v1/chat/completions")
    api.add_space_variable(repo_id=SPACE, key="ZAI_MODEL",
                           value="zai-org/GLM-5.3")
    api.add_space_variable(repo_id=SPACE, key="DURABLE_STATE_ENABLED",
                           value="1")
    api.add_space_variable(repo_id=SPACE, key="DURABLE_STATE_BRANCH",
                           value="runtime-state-hf")
    api.add_space_variable(repo_id=SPACE, key="LOCAL_QWEN_ENABLE",
                           value="1")
    api.add_space_variable(repo_id=SPACE, key="LOCAL_QWEN_CTX",
                           value="8192")
    api.add_space_variable(repo_id=SPACE, key="LOCAL_QWEN_THREADS",
                           value="2")
    api.add_space_secret(repo_id=SPACE, key="ZAI_API_KEY", value=HF_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=GITHUB_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=PORTFOLIO_COMMIT)
    _log("env contract wired (LOCAL_QWEN_ENABLE=1, durable state on runtime-state-hf)")

    st = {"round": "R455-LEAN-1-DELETIONS", "github_sha": commit,
          "hf_space": SPACE, "hf_revision": rev, "adapter": "r451_c13",
          "uploaded": True, "reviewer_provenance": "AI_REVIEW",
          "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    STATE.write_text(json.dumps(st, indent=2))
    _log(f"state: {STATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
