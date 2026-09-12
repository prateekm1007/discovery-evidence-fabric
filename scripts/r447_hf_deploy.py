#!/usr/bin/env python3
"""scripts/r447_hf_deploy.py — R447 Phases 3/8: deploy the current main
tree to the existing Hugging Face production-validation Space
(prateekm1/toscanini-prod-validation) and verify the identity chain.

Method (the R446-HF deployment's own recipe):
  1. stage the tracked tree at the target commit (git archive — the
     full tracked tree INCLUDING .dockerignore; the HF Space's Docker
     build applies the ignore semantics itself, no hand-rolled filter)
  2. the R446-HF adapter Dockerfile (node:24 runtime + Chromium +
     renderer deps + non-root user), applied to the canonical Dockerfile
     programmatically, with RENDER_GIT_COMMIT pinned to the target
  3. one upload commit on the Space repo; the build runs on HF
  4. the env contract: PORT/ZAI_BASE_URL/ZAI_MODEL variables +
     ZAI_API_KEY/GITHUB_TOKEN/PORTFOLIO_COMMIT secrets — with
     ZAI_MODEL re-pointed at zai-org/GLM-5.3 (the Phase 6 live
     measurement: the R446 pin deepseek-ai/DeepSeek-V4-Flash-0731 now
     reasons unboundedly on long prompts through the router — empty
     content at 2048 tokens — so the fresh E2E runs would
     transport-fail; GLM-5.3 measured serving content in 7-31 s)
  5. wait RUNNING; verify /api/version == the target commit
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

SPACE = "prateekm1/toscanini-prod-validation"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
OUT = REPO / "R447" / "HF_DEPLOYMENT_RECORD.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    raise SystemExit(
        "GITHUB_TOKEN missing: credentials come exclusively from "
        "environment/secret injection (R451-C2 Step 1 scrub)")
PORTFOLIO_COMMIT = os.environ.get(
    "PORTFOLIO_COMMIT", "0914755c5832f332abe5d74ed1655cd27764ecc0")

# ---- the R446-HF adapter hunks (applied to the canonical Dockerfile) --
HUNK_NODE_RUNTIME = """
# ---------- R446-HF ADAPTER: runtime Node 24 (the Visual Compiler's ----------
# renderer driver at RUNTIME; the canonical image carried node only in the
# webapp builder stage. Node 24 = the R445-C2/R446-C2 measured environment
# (sandbox node v24.19.0) and satisfies puppeteer-core@25.9.0's engine floor
# (>=22.12; node:20 measured EBADENGINE at build). bookworm glibc —
# forward-compatible with trixie. The webapp BUILDER stays node:20-alpine
# (the webapp's own pinned toolchain, unchanged).
FROM node:24-bookworm-slim AS node-runtime
"""

HUNK_APT = ("      chromium fonts-liberation libstdc++6 \\\n")

HUNK_NODE_WIRING = """
# ---------- R446-HF ADAPTER: Node + Chromium wiring ----------
# node + npm from the pinned node:24 image (npm-cli symlink); Chromium from
# Debian trixie (SwiftShader/ANGLE included — render.js launches with
# --use-angle=swiftshader --enable-unsafe-swiftshader --no-sandbox).
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \\
    && node --version && npm --version
ENV CHROME_PATH=/usr/bin/chromium

# The Visual Compiler renderer deps: pinned three@0.175.0 + puppeteer-core
# (the SAME versions the webapp and the R445-C2 measurements used; the
# build FAILS if three resolves to anything else — render_worker's
# renderer_deps_present() contract, enforced at image build time too).
RUN cd /app/discovery_fabric/engine/visual_compiler/renderer \\
    && npm ci --omit=dev --no-audit --no-fund \\
    && node -e "const fs=require('fs'); \\
        const v=JSON.parse(fs.readFileSync(\\
          'node_modules/three/package.json','utf8')).version; \\
        if (v!=='0.175.0') { console.error('three version mismatch: '+v); \\
        process.exit(1); } console.log('renderer three@'+v+' pinned OK')"
"""

HUNK_IDENTITY_ARG = """# ---------- R446-HF/R447 ADAPTER: deployment identity pin ----------
# HF Space builds receive no build args (unlike Render). The GitHub
# source SHA is pinned HERE as the ARG default: the same R396 A.3
# priority-1 mechanism, supplied by deployment config instead of a
# build arg. The identity-bake script below is UNCHANGED and remains
# the only identity authority (env vars can never define it).
ARG RENDER_GIT_COMMIT="{COMMIT}"
"""

HUNK_NONROOT = """
# ---------- R446-HF ADAPTER: non-root runtime ----------
# HF Spaces best practice: run as UID 1000. /portfolio is pre-created
# (the entrypoint's mkdir needs a writable parent); /app is chowned so
# ENGINE_RUNS/ and run dirs are writable by the engine.
RUN useradd -m -u 1000 -s /bin/bash toscanini \\
    && mkdir -p /portfolio && chown toscanini /portfolio \\
    && chown -R toscanini /app
USER toscanini
ENV HOME=/home/toscanini
"""


def _log(msg: str) -> None:
    print(f"[r447-deploy] {msg}", flush=True)


def _run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    r = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                       text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr[:300]}")
    return r.stdout.strip()


def _adapter_dockerfile(commit: str) -> str:
    """The canonical Dockerfile + the R446-HF adapter hunks, pinned to
    the target commit (the exact recipe the R446-HF deployment used)."""
    df = (REPO / "Dockerfile").read_text()

    # 1. the node:24 runtime stage after the webapp builder
    anchor = "RUN NEXT_OUTPUT=export npm run build && node verify-export.mjs\n"
    assert anchor in df
    df = df.replace(anchor, anchor + HUNK_NODE_RUNTIME, 1)

    # 2. chromium in the apt set
    apt_anchor = "      libxi6 libxfixes3 libsm6 libice6 libxkbcommon0 \\\n"
    assert apt_anchor in df, "apt anchor not found"
    df = df.replace(apt_anchor, apt_anchor + HUNK_APT, 1)

    # 3. node wiring + renderer deps after the webapp export copy
    wire_anchor = ("COPY --from=webapp-builder /webapp/out "
                   "./TOSCANINI_UI/webapp-export\n")
    assert wire_anchor in df
    df = df.replace(wire_anchor, wire_anchor + HUNK_NODE_WIRING, 1)

    # 4. the identity pin
    arg_anchor = 'ARG RENDER_GIT_COMMIT=""\n'
    assert arg_anchor in df
    df = df.replace(arg_anchor,
                    HUNK_IDENTITY_ARG.replace("{COMMIT}", commit), 1)

    # 5. the non-root runtime before the entrypoint chmod
    ep_anchor = "RUN chmod +x /app/toscanini/container-entrypoint.sh\n"
    assert ep_anchor in df
    df = df.replace(ep_anchor, HUNK_NONROOT + "\n" + ep_anchor, 1)
    return df


def main() -> int:
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)

    # ---- 1. the target commit (clean tree) ----------------------------
    commit = _run(["git", "rev-parse", "HEAD"])
    dirty = _run(["git", "status", "--porcelain"])
    if dirty:
        _log("FATAL: working tree dirty — commit first")
        return 2
    _log(f"target commit: {commit}")

    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        # ---- 2. stage the tracked tree (git archive) ------------------
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", "HEAD"], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        n_files = sum(1 for _ in stage.rglob("*") if _.is_file())
        _log(f"staged {n_files} tracked files "
             f"({archive.stat().st_size / 1e6:.0f} MB tar)")

        # ---- 3. the adapter Dockerfile --------------------------------
        (stage / "Dockerfile").write_text(_adapter_dockerfile(commit))

        # ---- 4. upload (one commit on the Space repo) ------------------
        _log("uploading to the Space (the build runs on HF)...")
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"R447 deploy: engine tree at {commit[:12]} (the Phase "
                f"1/2/6/7 fixes: the geometry identity join, the package "
                f"terminal join, attacker v2, the join attacks) + "
                f"ZAI_MODEL re-point at zai-org/GLM-5.3 (the Phase 6 "
                f"live measurement: the previous pin reasons unboundedly "
                f"through the router)"),
        )
        _log(f"Space revision: {rev}")

    # ---- 5. the env contract ------------------------------------------
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
    _log("env contract wired (ZAI_MODEL=zai-org/GLM-5.3)")

    # ---- 6. wait for RUNNING + verify identity -----------------------
    deadline = time.time() + 2400
    stage_ = None
    while time.time() < deadline:
        info = api.space_info(repo_id=SPACE)
        rt = info.runtime
        stage_ = getattr(rt, "stage", None) if rt else None
        if stage_ == "RUNNING":
            break
        if stage_ in ("BUILD_ERROR", "RUNTIME_ERROR"):
            _log(f"FATAL: space stage {stage_}")
            return 3
        _log(f"space stage: {stage_} (waiting...)")
        time.sleep(45)
    _log(f"final stage: {stage_}")

    # the app may still be starting inside the container; poll version
    version = None
    deadline = time.time() + 900
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                BASE + "/api/version",
                headers={"Authorization": f"Bearer {HF_TOKEN}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                version = json.loads(r.read())
                break
        except Exception as exc:  # noqa: BLE001
            _log(f"version poll: {type(exc).__name__} (waiting...)")
            time.sleep(25)
    if not version:
        _log("FATAL: /api/version unreachable")
        return 3
    deployed = version.get("engine_commit")
    ok = deployed == commit
    _log(f"/api/version engine_commit={deployed} "
         f"{'== target (VERIFIED)' if ok else '!= TARGET (DRIFT!)'}")

    record: Dict[str, Any] = {
        "artifact_type": "R447 HF deployment record",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "github_repo": "https://github.com/prateekm1007/"
                       "discovery-evidence-fabric",
        "github_sha": commit,
        "hf_space": SPACE,
        "hf_revision": rev,
        "space_stage": stage_,
        "zai_model": "zai-org/GLM-5.3",
        "zai_model_basis": (
            "the Phase 6 live measurement: the R446 pin "
            "deepseek-ai/DeepSeek-V4-Flash-0731 reasons unboundedly on "
            "long prompts through the router (empty content at 2048 "
            "tokens); GLM-5.3 measured serving content in 7-31 s"),
        "api_version": version,
        "identity_verified": ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1))
    _log(f"record -> {OUT}")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
