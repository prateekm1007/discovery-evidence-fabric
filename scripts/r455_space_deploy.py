#!/usr/bin/env python3
"""R455-LEAN-1-DELETIONS Space deploy — the standing r447 pipeline reused for
the deadweight-elimination round (the R453-C2 precedent: same proven logic,
round-correct commit message + record fields).

The adapter Dockerfile transformation is IMPORTED VERBATIM from
scripts/r447_hf_deploy.py (the exact recipe every deployed revision since
R447 was built with — node runtime, chromium, node wiring, the identity
pin, the non-root runtime). Only the upload commit message and the state
record are round-specific.

Credentials: HF_TOKEN + GITHUB_TOKEN env-injection ONLY (R451-C2 scrub
discipline — never written to disk, URL, or the uploaded tree).
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
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

# the proven adapter (5-hunk Dockerfile transformation) — imported verbatim
from r447_hf_deploy import (  # noqa: E402
    SPACE, HF_TOKEN, GITHUB_TOKEN, BASE, PORTFOLIO_COMMIT,
    _adapter_dockerfile,
)

HF_SPACE_CARD_HEAD = '---\ntitle: Toscanini Prod Validation\nemoji: "\\U0001F3B5"\ncolorFrom: blue\ncolorTo: green\nsdk: docker\napp_port: 7860\npinned: false\n---\n\n<!-- The HF Space card frontmatter (sdk: docker, app_port: 7860) — the\ncanonical engine README follows. The git-archive deploy would otherwise\nstrip it (the CONFIG_ERROR of the first R447 deploy, fixed upfront). -->\n'

STATE_OUT = SCRIPTS / "r455_deploy_state.json"


def _log(msg: str) -> None:
    print(f"[r455-deploy] {msg}", flush=True)


def main() -> int:
    from huggingface_hub import HfApi
    if not HF_TOKEN or not GITHUB_TOKEN:
        _log("FATAL: HF_TOKEN / GITHUB_TOKEN missing — env-injection only")
        return 2
    api = HfApi(token=HF_TOKEN)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                            capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        _log("FATAL: working tree dirty — commit first")
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
        _log(f"staged {n_files} tracked files "
             f"({archive.stat().st_size / 1e6:.0f} MB tar)")

        (stage / "Dockerfile").write_text(_adapter_dockerfile(commit))
        # the HF Space card front matter — the git-archive tree's bare
        # README would otherwise strip it (the known first-R447-deploy
        # CONFIG_ERROR; fixed upfront in the standing pipeline)
        (stage / "README.md").write_text(HF_SPACE_CARD_HEAD + "\n" + (REPO / "README.md").read_text())

        _log("uploading to the canonical Space (build runs on HF)...")
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"R455-LEAN-1-DELETIONS deploy: engine tree at "
                f"{commit[:12]} — the deadweight elimination (378 files / "
                f"134,765 py LOC archived to archive/r455-lean/ per the "
                f"EXT-AUDIT-LEAN-R454 register; production import closure "
                f"unchanged; zero new test failures vs the recorded "
                f"baseline); no stage, gate, or epistemic control removed"),
        )
        _log(f"Space revision: {rev}")

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
            _write_state(commit, rev, stage_, None, False)
            return 3
        _log(f"space stage: {stage_} (waiting...)")
        time.sleep(45)
    _log(f"final stage: {stage_}")

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
        _write_state(commit, rev, stage_, None, False)
        return 3
    deployed = version.get("engine_commit")
    ok = deployed == commit
    _log(f"/api/version engine_commit={deployed} "
         f"{'== target (ART. LXXI VERIFIED)' if ok else '!= TARGET (DRIFT!)'}")

    _write_state(commit, rev, stage_, version, ok)
    return 0 if ok else 4


def _write_state(commit, rev, stage_, version, ok):
    record: Dict[str, Any] = {
        "artifact_type": "R455 HF deployment state",
        "round": "R455-LEAN-1-DELETIONS",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "github_sha": commit,
        "hf_space": SPACE,
        "hf_revision": rev,
        "space_stage": stage_,
        "deployed_engine_commit": (version or {}).get("engine_commit"),
        "constitution_version": (version or {}).get("constitution_version"),
        "identity_tuple_ok": ok,
    }
    STATE_OUT.write_text(json.dumps(record, indent=2))
    _log(f"state: {STATE_OUT}")


if __name__ == "__main__":
    sys.exit(main())
