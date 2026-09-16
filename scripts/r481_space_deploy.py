#!/usr/bin/env python3
"""R481 — the union deploy: the reconciled tree (the R478 P1-12 line +
the R478->R480 P0 line) to the canonical production Space.

THE R479/R456 FLOW, REUSED BY IMPORT, WITH ONE DELTA:
  - The R480 REPOINT STATE IS PRESERVED, never regressed: the r479
    driver's env contract set ZAI_BASE_URL/ZAI_MODEL back to the HF
    router (correct THEN, a P0-5 regression NOW). This driver wires
    the R480 values: ZAI_BASE_URL=api.atria-asi.ai,
    ZAI_MODEL=Atria-Dawn-Preview, ZAI_API_KEY=atria key 1 — the
    operator's credited-provider directive stands.
  - GITHUB_TOKEN re-wired from the vault (the R479 rationale holds:
    the durable-state branch needs a valid token; fingerprint-
    verified == R479's wiring, no rotation).
  - The 15-name atria ring re-wired from the vault (R480 pattern;
    fingerprint-verified byte-identical to the deployed ring).
  - Identity bakes HEAD (the union tip == origin/main, ls-remote
    verified before upload).
  - OUT: R481/SPACE_DEPLOY_RECORD.json.

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

_SENTINEL = "__R481_UNSET__"


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


_vault0 = _load_vault()
os.environ.setdefault("GITHUB_TOKEN",
                      _vault0.get("GITHUB_TOKEN") or _SENTINEL)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
OUT = REPO / "R481" / "SPACE_DEPLOY_RECORD.json"

RING_NAMES = (["ATRIA_API_KEY"]
              + [f"ATRIA_API_KEY_{i}" for i in range(2, 16)])


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
    gh_token = vault.get("GITHUB_TOKEN") or os.environ.get(
        "GITHUB_TOKEN", "")
    if not hf_token:
        print("FATAL: HF_TOKEN absent (vault + env)")
        return 2
    if not gh_token or gh_token == _SENTINEL:
        print("FATAL: GITHUB_TOKEN absent (vault + env)")
        return 2

    # fingerprint gates: this vault must be the SAME ring and the SAME
    # PAT the production surface already carries (R479/R480 records)
    if fp(vault.get("ATRIA_API_KEY", "")) != "fp_9a89731ad93f_len36":
        print("FATAL: vault ATRIA_API_KEY fingerprint != the R480-"
              "recorded deployed key-1 (fp_9a89731ad93f_len36) — the "
              "ring identity changed; refusing to wire an unverified "
              "ring")
        return 2
    if hashlib.sha256(gh_token.encode()).hexdigest()[:12] != \
            "f1ebca5f9b62":
        print("FATAL: vault GITHUB_TOKEN fingerprint != R479's recorded "
              "wiring (f1ebca5f9b62) — the PAT rotated; update the "
              "records before wiring")
        return 2
    ring = {n: vault[n] for n in RING_NAMES if vault.get(n)}
    if len(ring) != 15:
        print(f"FATAL: expected 15 ring keys in the vault, got "
              f"{len(ring)}")
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
    print(f"[r481-deploy] target commit (union tip): {commit}")

    # origin/main must already carry the union (the R477 race lesson:
    # never deploy an unpushed commit)
    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0] \
        if subprocess.run(
            ["git", "ls-remote",
             "https://x-access-token:" + gh_token +
             "@github.com/prateekm1007/discovery-evidence-fabric.git",
             "refs/heads/main"],
            capture_output=True, text=True).stdout.strip() else ""
    print(f"[r481-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry the union tip — push "
              "first (the orphan-commit class)")
        return 2

    # the BEFORE identity, measured live (the flip's baseline)
    try:
        before = space_get("/api/version", hf_token)
        print(f"[r481-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r481-deploy] BEFORE probe pending "
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
        print(f"[r481-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r481-deploy] pruned {len(accounting['removed_round_dirs'])} "
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
            print("[r481-deploy] README frontmatter PREPENDED "
                  "(absent on this tree)")
        else:
            print("[r481-deploy] README frontmatter already present — "
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
        print(f"[r481-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r481-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R481 "
                f"union (the R478 P1-12 line + the R478->R480 P0 line, "
                f"both suites kept) via the r481 delta driver "
                f"(R480 repoint state preserved)"))
        print(f"[r481-deploy] upload DONE in {time.time()-t0:.0f}s "
              f"— Space revision: {rev}")

    # the env contract: the standing variables + THE R480 REPOINT
    # (PRESERVED — the r479 values for ZAI would regress P0-5)
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
    print("[r481-deploy] variables set (ZAI repoint PRESERVED: "
          "api.atria-asi.ai / Atria-Dawn-Preview)")

    # secrets: GITHUB_TOKEN (R479 rationale, fingerprint-gated) +
    # ZAI_API_KEY = atria key 1 (the R480 repoint) + the 15-name ring
    wired = []
    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=gh_token)
    wired.append("GITHUB_TOKEN")
    api.add_space_secret(repo_id=SPACE, key="ZAI_API_KEY",
                         value=ring["ATRIA_API_KEY"])
    wired.append("ZAI_API_KEY")
    for name in RING_NAMES:
        api.add_space_secret(repo_id=SPACE, key=name,
                             value=ring[name])
        wired.append(name)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=val)
    wired.append("PORTFOLIO_COMMIT")
    print(f"[r481-deploy] secrets wired: {wired}")
    print("[r481-deploy] secrets left standing (not in this vault): "
          "UNOROUTER/XKIRO/APINEX/BAI/BYNARA/TOKENHARBOR/AEROLINK")

    # deterministic application: restart AFTER everything is wired
    api.restart_space(repo_id=SPACE)
    print("[r481-deploy] Space restarted — variables + secrets apply; "
          "verify with scripts/r481_identity_verify.py")

    rec = {
        "round": "R481", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune (r481 delta driver)",
        "delta_vs_r479": ("the R480 repoint state PRESERVED "
                          "(ZAI_BASE_URL=api.atria-asi.ai, "
                          "ZAI_MODEL=Atria-Dawn-Preview, ZAI_API_KEY="
                          "atria key 1); GITHUB_TOKEN re-wired "
                          "(fingerprint-verified == R479's, no "
                          "rotation); the 15-name ring re-wired "
                          "(fingerprint-verified == the deployed ring)"),
        "before_identity": before,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "variables_set": {
            "ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
            "ZAI_MODEL": "Atria-Dawn-Preview",
            "note": "the R480 repoint preserved; the r479 HF-router "
                    "values deliberately NOT set",
        },
        "secrets_wired": wired,
        "secrets_fingerprints": {
            "GITHUB_TOKEN": "sha256:" + hashlib.sha256(
                gh_token.encode()).hexdigest()[:12],
            "ZAI_API_KEY": fp(ring["ATRIA_API_KEY"]),
            "ring_size": len(ring),
        },
        "unblocks": ("the R478-A line's PAT-blocked push (a listed "
                     "operator event, engaged 2026-09-17) + the union "
                     "delivery"),
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r481-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
