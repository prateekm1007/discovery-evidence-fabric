#!/usr/bin/env python3
"""R451-C1.3 phase-split deploy — upload + env contract in ONE call.

The same phase-split mechanics as scripts/r447_deploy_upload.py (the
sandbox kills spawned processes at the tool-call boundary), with the
R451-C1.3 changes:

  1. the engine tree at HEAD (git archive) — carrying the runtime-
     admission authority, the run-level routing provenance, and the
     env-gated llama-server entrypoint;
  2. the R451-C1.3 adapter Dockerfile: the llama.cpp llama-server built
     from the pinned tag b10930 + the sha-pinned Qwen3-1.7B Q4_K_M GGUF
     (fail-closed acquisition) — the canonical Space's OWN zero-paid
     local route (C1.8: the production Space independently proves it,
     never a claim that sandbox compute transfers);
  3. the Space README WITH the HF frontmatter (upfront, as R447 fixed);
  4. the env contract: the R447/R450 variables + LOCAL_QWEN_ENABLE=1
     (the entrypoint's gate for the local route).

R456-LEAN-2 (image slimming): the staged upload EXCLUDES the
round-evidence trees and CI-instrument directories (the runtime reads
none of them — the R455 measured production import closure + the
.dockerignore rule; ~520 MB of tracked bytes stay out of the Space
build). One canonical exclusion list lives in
scripts/r456_deploy_excludes.py; the drivers import it verbatim
(Art. X — one implementation).

Usage: HF_TOKEN=... GITHUB_TOKEN=... python scripts/r451_c13_deploy.py
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
sys.path.insert(0, str(REPO / "scripts"))

import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
PORTFOLIO_COMMIT = os.environ.get(
    "PORTFOLIO_COMMIT", "0914755c5832f332abe5d74ed1655cd27764ecc0")


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
    print(f"[r451c13-deploy] target commit: {commit}")

    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", "HEAD"], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        # R456-LEAN-2: the round-evidence + CI-instrument exclusion
        # (one canonical list; the runtime reads none of it)
        from r456_deploy_excludes import EXCLUDE_DIRS, EXCLUDE_FILES
        excluded_mb = 0.0
        for name in EXCLUDE_DIRS:
            target = stage / name
            if target.exists():
                excluded_mb += sum(f.stat().st_size for f in target.rglob("*")
                                   if f.is_file()) / 1e6
                import shutil
                shutil.rmtree(target, ignore_errors=True)
        for name in EXCLUDE_FILES:
            target = stage / name
            if target.exists():
                excluded_mb += target.stat().st_size / 1e6
                target.unlink()
        n_files = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r451c13-deploy] staged {n_files} tracked files "
              f"({archive.stat().st_size / 1e6:.0f} MB tar; "
              f"excluded {excluded_mb:.0f} MB of round/CI trees)")

        # the R451-C1.3 adapter Dockerfile (llama.cpp pinned tag build +
        # sha-pinned GGUF + the env-gated entrypoint route)
        (stage / "Dockerfile").write_text(
            driver._r451_c13_adapter_dockerfile(commit))

        # the README WITH frontmatter (the R447 CONFIG_ERROR fix)
        engine_readme = (stage / "README.md").read_text(errors="replace") \
            if (stage / "README.md").exists() else ""
        (stage / "README.md").write_text(
            uploader.README_FRONTMATTER + engine_readme)

        print("[r451c13-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"R451-C1.3 deploy: engine tree at {commit[:12]} — the "
                f"runtime-admission authority (probe-before-admit on "
                f"every rung incl. the local route), run-level routing "
                f"provenance (run_owned_call => run_id != null; the "
                f"13-field ledger lines; run isolation by run_id), "
                f"explicit task degradation, catalog-discovered "
                f"semantics, MODEL_NOT_FOUND relist recovery, the "
                f"unified selector — plus the Space's OWN zero-paid "
                f"local route: llama.cpp llama-server built from the "
                f"pinned tag b10930 + the sha-pinned Qwen3-1.7B Q4_K_M "
                f"GGUF, started by the env-gated entrypoint"),
        )
        print(f"[r451c13-deploy] Space revision: {rev} "
              f"({time.time() - t0:.0f}s upload)")

    # the env contract: the R447/R450 variables + the C1.3 gate
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
    # R451-C1.3: the zero-paid local route's entrypoint gate
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
    # R457-OPERATOR-TRANSPORT: the operator frontier ladder's keys —
    # env-injection ONLY (the values are read from the deploy
    # environment; they never appear in the repo, the image, or a URL)
    for _key_env, _secret in (("UNOROUTER_API_KEY", "UNOROUTER_KEY"),
                              ("XKIRO_API_KEY", "XKIRO_KEY"),
                              ("APINEX_API_KEY", "APINEX_KEY"),
                              ("BAI_API_KEY", "BAI_KEY")):
        _val = os.environ.get(_secret, "")
        if _val:
            api.add_space_secret(repo_id=SPACE, key=_key_env, value=_val)
            print(f"[r451c13-deploy] secret wired: {_key_env}")
        else:
            print(f"[r451c13-deploy] {_secret} not in env — {_key_env} "
                  f"NOT wired (the rung stays unavailable, honest)")
    print("[r451c13-deploy] env contract wired "
          "(LOCAL_QWEN_ENABLE=1, durable state on runtime-state-hf)")

    state = {"phase": "uploaded", "github_sha": commit, "space": SPACE,
             "space_revision": rev if isinstance(rev, str) else str(rev),
             "uploaded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}
    out = REPO / "scripts" / "r447_deploy_state.json"
    out.write_text(json.dumps(state, indent=1))
    print(f"[r451c13-deploy] state -> {out}")
    print("[r451c13-deploy] NEXT: the build runs on HF — poll with "
          "scripts/r447_deploy_verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
