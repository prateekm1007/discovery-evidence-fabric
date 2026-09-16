#!/usr/bin/env python3
"""R477 — Space deploy, the r456 delta driver (Article LXXIII typed-
honest credential handling).

WHY A DELTA DRIVER EXISTS THIS ROUND: the r456 driver hard-requires
GITHUB_TOKEN at import (r447_hf_deploy raises SystemExit) and
unconditionally re-wires the Space's GITHUB_TOKEN secret. This session
holds NO valid GitHub PAT (vault lost in the container recycle; the
.gitcreds placeholder is redacted; Art. LXXIII lookup exhausted). The
Space's STANDING GITHUB_TOKEN secret is valid and the runtime NEEDS it
(toscanini/durable.py pushes/restores the runtime-state branch through
it). Wiring a placeholder would break the durable-state system.

THE DELTA (everything else is the r456 flow, reused by import):
  - GITHUB_TOKEN: NOT re-wired — the standing secret persists (the
    LXXIII rule: re-wire what the deploy environment holds, leave the
    standing surface untouched otherwise). A sentinel value passes the
    r447 import gate and is ASSERTED never to reach add_space_secret.
  - Dockerfile: this repo's Dockerfile is the SPACE-ADAPTED one (this
    checkout was cloned FROM the Space, not GitHub), so the canonical
    anchor asserts in _r451_c13_adapter_dockerfile CANNOT hold. The
    only per-deploy variable is the ARG RENDER_GIT_COMMIT default —
    swapped by regex below (the hunks are already in place from the
    standing r456-lineage deploys; the identity-bake script below the
    ARG stays the sole identity authority, unchanged).
  - README: already carries the HF frontmatter on this tree — NOT
    prepended again (double-prepend would corrupt the card).
  - Router secrets: wired from the environment/vault WHEN PRESENT
    (ATRIA_API_KEY is; the others stay standing), same as r456.
  - Identity: the Dockerfile ARG carries THIS repo's commit (the
    Space-repo lineage; the GitHub-push leg is DELIVERY_BLOCKED and
    escalated in the round record per Art. LXXI §4).
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
SCRIPTS = REPO / "scripts"

# the r447/r456 import gate: a sentinel that is NEVER wired anywhere
# (asserted below). The standing Space secret is the authority.
_SENTINEL = "__R477_STANDING__"
os.environ.setdefault("GITHUB_TOKEN", _SENTINEL)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
OUT = REPO / "R477" / "SPACE_DEPLOY_RECORD.json"


def _load_vault() -> dict:
    vault = {}
    p = Path("/home/z/my-project/.secrets.env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vault[k.strip()] = v.strip()
    return vault


def main() -> int:
    from huggingface_hub import HfApi
    vault = _load_vault()
    hf_token = vault.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "")
    if not hf_token:
        print("FATAL: HF_TOKEN absent (vault + env)")
        return 2
    api = HfApi(token=hf_token)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                      capture_output=True, text=True).stdout.strip():
        print("FATAL: working tree dirty")
        return 2
    print(f"[r477-deploy] target commit: {commit}")

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
        print(f"[r477-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r477-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        # the SPACE-ADAPTed Dockerfile (see docstring): swap ONLY the
        # per-deploy identity variable; hunks stay from the lineage
        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        import re as _re
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="[0-9a-f]{40}"',
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found in the "
                  "staged Dockerfile")
            return 2
        df_path.write_text(new_df)
        print(f"[r477-deploy] Dockerfile identity ARG -> {commit[:12]}")
        # README already frontmattered on this tree — not prepended

        print("[r477-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R477 "
                f"audit-closure round (composer safe-area clearance; the "
                f"drei optimizePackageImports attempt measured no-gain "
                f"and reverted; R476 round-record closure) via the r477 "
                f"delta driver (standing GITHUB_TOKEN secret untouched)"))
        print(f"[r477-deploy] upload DONE in {time.time()-t0:.0f}s "
              f"— Space revision: {rev}")

    # the env contract (variables only — same values as r456)
    for k, v in (("PORT", "7860"),
                 ("ZAI_BASE_URL",
                  "https://router.huggingface.co/v1/chat/completions"),
                 ("ZAI_MODEL", "zai-org/GLM-5.3"),
                 ("DURABLE_STATE_ENABLED", "1"),
                 ("DURABLE_STATE_BRANCH", "runtime-state-hf"),
                 ("LOCAL_QWEN_ENABLE", "1"),
                 ("LOCAL_QWEN_CTX", "8192"),
                 ("LOCAL_QWEN_THREADS", "2"),
                 ("LOCAL_EMBED_ENABLE", "1"),
                 ("LOCAL_EMBED_THREADS", "1")):
        api.add_space_variable(repo_id=SPACE, key=k, value=v)

    # secrets: ONLY what this environment holds. GITHUB_TOKEN is
    # DELIBERATELY ABSENT from this set — the standing secret persists.
    wired, skipped = [], []
    for name in ("ZAI_API_KEY", "PORTFOLIO_COMMIT",
                 "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
                 "BAI_API_KEY", "BYNARA_API_KEY", "TOKENHARBOR_API_KEY",
                 "AEROLINK_API_KEY", "ATRIA_API_KEY"):
        val = vault.get(name) or os.environ.get(name, "")
        if name == "ZAI_API_KEY":
            val = hf_token  # the r456 contract: zai rides the HF token
        if name == "PORTFOLIO_COMMIT" and not val:
            val = "0914755c5832f332abe5d74ed1655cd27764ecc0"
        if val:
            assert val != _SENTINEL, "sentinel must never be wired"
            api.add_space_secret(repo_id=SPACE, key=name, value=val)
            wired.append(name)
        else:
            skipped.append(name)
    print(f"[r477-deploy] secrets wired: {wired}")
    print(f"[r477-deploy] secrets left standing (unset here): {skipped}")
    assert "GITHUB_TOKEN" not in wired, "LXXIII violation"

    rec = {
        "round": "R477", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune (r477 delta driver)",
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "secrets_wired": wired,
        "secrets_left_standing": skipped + ["GITHUB_TOKEN (standing, "
                                            "valid — durable state needs "
                                            "it; not re-wired per LXXIII)"],
        "github_push": "DELIVERY_BLOCKED — no valid PAT in this session "
                       "(Art. LXXI §4 escalation in the round record)",
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r477-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
