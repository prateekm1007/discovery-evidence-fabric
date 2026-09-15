#!/usr/bin/env python3
"""R456 chunked deploy — the R451-C1.3 production adapter + the §C.10
image slimming (round trees pruned from the staged Space tree).

The R455 v2 driver staged the FULL `git archive HEAD` (~579 MB tar; 456
MB of it R* round evidence the engine never reads — the audit's §C.10
finding). This driver stages the same tree MINUS the round trees (keep
set: R412 / R413 / R449 — the only dirs with LIVE runtime file reads,
path-literal-verified and recorded in .dockerignore) and MINUS the
Blender layer (removed from the Dockerfile itself — audit §O.4/§J).

The adapter is imported verbatim from the r447/r455 pipeline (not
reimplemented); the README frontmatter fix (the CONFIG_ERROR lesson)
and the env contract (LOCAL_QWEN_ENABLE=1, durable state on
runtime-state-hf) are carried unchanged.
"""
from __future__ import annotations

import json
import os
import re
import shutil
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
STATE = SCRIPTS / "r456_deploy_state.json"

# §C.10 keep set — live runtime reads only (see .dockerignore note)
ROUND_KEEP = {"R412", "R413", "R449"}
_ROUND_DIR_RE = re.compile(r"^R\d")


def _log(m):
    print(f"[r456-deploy] {m}", flush=True)


def _prune_round_trees(stage: Path) -> dict:
    """Remove R* round dirs except the keep set; return the accounting."""
    removed, kept, freed = [], [], 0
    for entry in sorted(stage.iterdir()):
        if not entry.is_dir() or not _ROUND_DIR_RE.match(entry.name):
            continue
        if entry.name in ROUND_KEEP:
            kept.append(entry.name)
            continue
        size = sum(f.stat().st_size for f in entry.rglob("*")
                   if f.is_file())
        freed += size
        removed.append(entry.name)
        shutil.rmtree(entry)
    return {"removed_round_dirs": removed, "kept_round_dirs": kept,
            "bytes_freed": freed,
            "mb_freed": round(freed / 1e6, 1)}


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
        n_full = sum(1 for _ in stage.rglob("*") if _.is_file())
        mb_full = archive.stat().st_size / 1e6
        _log(f"staged {n_full} tracked files ({mb_full:.0f} MB tar)")

        # ---- §C.10: round trees out of the shipping image ------------
        accounting = _prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        _log(f"pruned {len(accounting['removed_round_dirs'])} round dirs "
             f"({accounting['mb_freed']} MB freed on disk; kept: "
             f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        # the R451-C1.3 adapter Dockerfile (llama.cpp pinned-tag build +
        # sha-pinned GGUF + the env-gated entrypoint route; NO Blender)
        (stage / "Dockerfile").write_text(
            driver._r451_c13_adapter_dockerfile(commit))

        # the README WITH front matter (the CONFIG_ERROR fix, pinned)
        engine_readme = (stage / "README.md").read_text(errors="replace") \
            if (stage / "README.md").exists() else ""
        (stage / "README.md").write_text(
            uploader.README_FRONTMATTER + engine_readme)

        # carry the .dockerignore semantics into the staged tree (the
        # HF builder honors it; the prune above is the belt, this the
        # suspenders)
        _log("uploading to the canonical Space (R451-C1.3 adapter, "
             "round-tree-pruned)...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=SPACE,
            repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the standing "
                f"R456+ tree shape (round trees pruned from the Space "
                f"tree, keep set R412/R413/R449 live-read; the R451-C1.3 "
                f"adapter Dockerfile, NO Blender) + the R467 eighth "
                f"free-tier router (atria — the token-surplus STRONG "
                f"rung; ATRIA_API_KEY wired — see R467/ records)"),
        )
        _log(f"upload DONE in {time.time()-t0:.0f}s — Space revision: {rev}")

    # the env contract: the R447/R450 variables + the C1.3 local-route gate
    api.add_space_variable(repo_id=SPACE, key="PORT", value="7860")
    api.add_space_variable(
        repo_id=SPACE, key="ZAI_BASE_URL",
        value="https://router.huggingface.co/v1/chat/completions")
    api.add_space_variable(
        repo_id=SPACE, key="ZAI_MODEL",
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
    # R456: the zero-paid semantic-relevance engine (Phase-P1 reranker)
    api.add_space_variable(repo_id=SPACE, key="LOCAL_EMBED_ENABLE",
                           value="1")
    api.add_space_variable(repo_id=SPACE, key="LOCAL_EMBED_THREADS",
                           value="1")
    api.add_space_secret(repo_id=SPACE, key="ZAI_API_KEY", value=HF_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=GITHUB_TOKEN)
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=PORTFOLIO_COMMIT)
    # R456-A3 + R461: the operator's free-tier router set (FIVE DISTINCT
    # economic accounts; token exhaustion on one advances the cascade to
    # the next — the operator's rotation rule). The keys come from the
    # operator via env injection at deploy time; they are NEVER in the
    # repo, the commit, or any artifact (BS-021). R461 adds BYNARA (the
    # fifth router, its account-entry gate resolved by the owner's
    # telegram join 2026-09-15).
    # R463: TOKENHARBOR (the sixth candidate, admission DEFERRED to a
    # Space-side measurement per R462) and AEROLINK (the seventh
    # candidate, admission refused at the account-plan gate this round)
    # join the wiring set — their secrets are INERT on the deployed app
    # (no ProviderSpec reads them: neither is in _SPEC_BY_ID); they are
    # wired so the operator's "never insert again" persistence holds and
    # the Space-side admission probe path stays unblocked (R462's
    # what_unblocks). Unset keys are skipped typed-honestly (the standing
    # five remain persisted from R461 if unset here).
    # R467: ATRIA (the EIGHTH router — REGISTERED this round, not inert:
    # the ProviderSpec reads exactly this name; the token-surplus rung
    # the R466 reaudit's MECHANISM-stage constraint asked for). Same
    # BS-021 discipline: env-injected at deploy time when present,
    # skipped typed-honestly when unset (the standing secret persists
    # from scripts/r467_hf_secrets.py otherwise).
    for env_name, var in (("UNOROUTER_API_KEY", "UNOROUTER_API_KEY"),
                          ("XKIRO_API_KEY", "XKIRO_API_KEY"),
                          ("APINEX_API_KEY", "APINEX_API_KEY"),
                          ("BAI_API_KEY", "BAI_API_KEY"),
                          ("BYNARA_API_KEY", "BYNARA_API_KEY"),
                          ("TOKENHARBOR_API_KEY", "TOKENHARBOR_API_KEY"),
                          ("AEROLINK_API_KEY", "AEROLINK_API_KEY"),
                          ("ATRIA_API_KEY", "ATRIA_API_KEY")):
        val = os.environ.get(var, "")
        if val:
            api.add_space_secret(repo_id=SPACE, key=env_name, value=val)
            _log(f"secret wired: {env_name} (value never logged)")
        else:
            _log(f"WARN: {var} unset — the router stays unavailable "
                 f"(typed, honest)")
    _log("env contract wired (LOCAL_QWEN_ENABLE=1, durable state on "
         "runtime-state-hf)")

    st = {
        "round": "R456",
        "github_sha": commit,
        "hf_space": SPACE,
        "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune",
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "uploaded": True,
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    STATE.write_text(json.dumps(st, indent=2))
    _log(f"state: {STATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
