#!/usr/bin/env python3
"""R484 — the layer-join deploy: HEAD (the R483 IMPROVE-loop layer
join 1eb049c6 + the R484 flock fd fix f2b5f1b0) to the canonical
production Space.

THE R481 FLOW with ONE disclosed delta:
  - THE ATRIA RING IS NOT RE-WIRED this round: the container recycle
    destroyed the local vault's ring values (the LXXIII re-mirror
    carries PAT + HF_TOKEN only). Space secrets PERSIST through
    upload and restart (the R480 proof: the repoint rode variables +
    restart with the identity unchanged) — the deployed 15-name ring
    and ZAI_API_KEY stand as wired by R481/R483. Ring re-wiring
    re-arms when the operator re-supplies the ring (a listed
    reminder event, reported with this round).
  - GITHUB_TOKEN IS re-wired (fingerprint-gated == R479's wiring
    f1ebca5f9b62, no rotation) — the durable-state branch's push
    credential.

Everything else is the r481 driver's, unchanged: the R480 repoint
preservation (variables: api.atria-asi.ai / Atria-Dawn-Preview), the
push-before-deploy gate (the R477 orphan lesson), the identity bake
(RENDER_GIT_COMMIT), the round-tree prune, the deterministic
post-wire restart.

This is the behavior-bearing deploy the R483 record names: the
kill-evidence layer join (a killed PRIMARY joins the IMPROVE dead
list) — the campaign attempt on this build is the auditor's one
decisive question.

BS-021: fingerprints only, never key values.
"""
from __future__ import annotations

import hashlib
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
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
OUT = REPO / "R484" / "SPACE_DEPLOY_RECORD.json"


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


def fp(value: str) -> str:
    return ("fp_" + hashlib.sha256(value.encode()).hexdigest()[:12]
            + f"_len{len(value)}")


def space_get(path: str, token: str, timeout: int = 60) -> dict:
    import urllib.request
    req = urllib.request.Request(
        f"https://prateekm1-toscanini-prod-validation.hf.space{path}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    from huggingface_hub import HfApi
    vault = _load_vault()
    hf_token = vault.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "")
    gh_token = (vault.get("GITHUB_TOKEN") or vault.get("GITHUB_PAT")
                or os.environ.get("GITHUB_TOKEN", "")
                or os.environ.get("GITHUB_PAT", ""))
    if not hf_token:
        print("FATAL: HF_TOKEN absent (vault + env)")
        return 2
    if not gh_token:
        print("FATAL: GITHUB_TOKEN/GITHUB_PAT absent (vault + env)")
        return 2
    if hashlib.sha256(gh_token.encode()).hexdigest()[:12] != \
            "f1ebca5f9b62":
        print("FATAL: PAT fingerprint != R479's recorded wiring "
              "(f1ebca5f9b62) — the PAT rotated; update the records "
              "before wiring")
        return 2

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"],
                           cwd=str(REPO), capture_output=True,
                           text=True).stdout.strip()
    if dirty:
        print(f"FATAL: working tree dirty:\n{dirty}")
        return 2
    print(f"[r484-deploy] target commit: {commit}")

    # push-before-deploy (the R477 orphan lesson): origin/main must
    # already carry HEAD
    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0]
    print(f"[r484-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first "
              "(the orphan-commit class)")
        return 2

    # the BEFORE identity, measured live (the flip's baseline)
    try:
        before = space_get("/api/version", hf_token)
        print(f"[r484-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r484-deploy] BEFORE probe pending "
              f"({type(exc).__name__})")

    api = HfApi(token=hf_token)

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
        print(f"[r484-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r484-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        # the README frontmatter (the r456 CONFIG_ERROR fix, pinned;
        # idempotence-guarded)
        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
            print("[r484-deploy] README frontmatter PREPENDED "
                  "(absent on this tree)")
        else:
            print("[r484-deploy] README frontmatter already present — "
                  "not prepended")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        import re as _re
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found in the "
                  "staged Dockerfile")
            return 2
        df_path.write_text(new_df)
        print(f"[r484-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r484-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R484 "
                f"layer-join round (the R483 IMPROVE-loop layer join + "
                f"the flock fd fix) via the r484 delta driver (ring "
                f"NOT re-wired: the vault ring destroyed by the "
                f"container recycle; the deployed ring persists)"))
        print(f"[r484-deploy] upload DONE in {time.time()-t0:.0f}s "
              f"— Space revision: {rev}")

    # the env contract: the standing variables + THE R480 REPOINT
    # (PRESERVED — setting them to anything else would regress P0-5)
    for k, v in (("PORT", "7860"),
                 ("ZAI_BASE_URL",
                  "https://api.atria-asi.ai/v1/chat/completions"),
                 ("ZAI_MODEL", "Atria-Dawn-Preview"),
                 ("DURABLE_STATE_ENABLED", "1"),
                 ("DURABLE_STATE_BRANCH", "runtime-state-hf"),
                 ("LOCAL_QWEN_ENABLE", "1"),
                 ("LOCAL_QWEN_CTX", "8192"),
                 ("LOCAL_QWEN_THREADS", "2"),
                 ("LOCAL_EMBED_ENABLE", "1"),
                 ("LOCAL_EMBED_THREADS", "1")):
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    print("[r484-deploy] variables set (ZAI repoint PRESERVED: "
          "api.atria-asi.ai / Atria-Dawn-Preview)")

    # THE DELTA (disclosed): the atria ring + ZAI_API_KEY are NOT
    # re-wired — the container recycle destroyed the vault's ring
    # values; the Space's deployed secrets persist through upload +
    # restart (the R480 proof). GITHUB_TOKEN IS re-wired
    # (fingerprint-gated above).
    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=val)
    print("[r484-deploy] secrets wired: GITHUB_TOKEN (fp-gated), "
          "PORTFOLIO_COMMIT")
    print("[r484-deploy] DELTA: ATRIA ring + ZAI_API_KEY NOT re-wired "
          "(vault ring lost to the container recycle; the deployed "
          "ring persists — re-arms on the operator's ring re-supply)")

    # deterministic application: restart AFTER everything is wired
    api.restart_space(repo_id=SPACE)
    print("[r484-deploy] Space restarted — verify with "
          "scripts/r481_identity_verify.py")

    rec = {
        "round": "R484", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune (r484 delta driver)",
        "delta_vs_r481": (
            "the atria 15-name ring + ZAI_API_KEY NOT re-wired: the "
            "container recycle destroyed the local vault's ring "
            "values; Space secrets persist through upload + restart "
            "(the R480 proof) so the deployed ring stands; ring "
            "re-wiring re-arms on the operator's re-supply (a listed "
            "reminder event). GITHUB_TOKEN re-wired, "
            "fingerprint-verified == R479's wiring (no rotation)"),
        "behavior_bearing_payload": (
            "the R483 IMPROVE-loop layer join (1eb049c6: a killed "
            "PRIMARY joins the IMPROVE dead list — kill_class "
            "ATTACK_GAUNTLET, span/bundle inheritance from the dead "
            "entry, derivation-trace rung) + the R484 flock fd fix "
            "(f2b5f1b0)"),
        "before_identity": before,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "variables_set": {
            "ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
            "ZAI_MODEL": "Atria-Dawn-Preview",
            "note": "the R480 repoint preserved",
        },
        "secrets_wired": ["GITHUB_TOKEN", "PORTFOLIO_COMMIT"],
        "secrets_fingerprints": {
            "GITHUB_TOKEN": "sha256:" + hashlib.sha256(
                gh_token.encode()).hexdigest()[:12],
        },
        "secrets_left_standing": (
            "ZAI_API_KEY + ATRIA_API_KEY ring (15) persist from the "
            "R481/R483 wirings; UNOROUTER/XKIRO/APINEX/BAI/BYNARA/"
            "TOKENHARBOR/AEROLINK standing"),
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r484-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
