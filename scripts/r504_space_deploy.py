#!/usr/bin/env python3
"""R504 — deploy 2.8.0 + the sealed instruments to the canonical
production Space.

THE OPERATOR DIRECTIVE (2026-09-18): "deploy 2.8.0 + the sealed
instruments, which also re-enables the R502 seal with HF_TOKEN
authenticated quota."

This driver reuses the R481/R484/R487/R491 deploy machinery (the same
stage/prune/frontmatter/Dockerfile-ARG/variables/secrets/restart flow)
with this round's attribution and message. THE R504 BEARING PAYLOAD:

  - constitution 2.8.0 (Article LXXVI — Credential Custody, R503) reaches
    /api/version — closing the R498-era "records ride the next deploy"
    tuple (production served 562c4ff0 / 2.6.0, DRIFT, 13 commits behind)
  - the sealed instruments: the RBG battery v4.1 (13 fixtures + the
    --corpus-leg-only mode), the calibration records (DIGESTS-pinned),
    the A2 gauntlet v4.2 attacker-computes standard
  - the free evidence legs (HF datasets-server + EPO LOD SPARQL) with
    the R504 HF_TOKEN attach-when-present authenticated quota — the
    Space's standing HF_TOKEN secret makes the DEPLOYED legs
    authenticated (measured R504: both-modes-live; degrade-never-fail)

BS-021: fingerprints only, never key values. Art. LXXVI §4: standing
secrets untouched except the operator-directed writes — this deploy
re-wires GITHUB_TOKEN (fingerprint-gated) and PORTFOLIO_COMMIT exactly
as every R481-family deploy did; HF_TOKEN and ELSEVIER_API_KEY are
standing and NOT touched.

Usage: python3 scripts/r504_space_deploy.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re as _re
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

import r491_space_deploy as r491  # noqa: E402  (vault loader + space_get)
import r456_space_deploy as r456  # noqa: E402  (round-tree prune)
import r447_hf_deploy as driver  # noqa: E402   (SPACE constant)
import r447_deploy_upload as uploader  # noqa: E402 (README frontmatter)

SPACE = driver.SPACE
OUT = REPO / "R504" / "SPACE_DEPLOY_RECORD.json"


def main() -> int:
    from huggingface_hub import HfApi
    vault = r491._load_vault()
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
        print("FATAL: PAT fingerprint != the registered wiring "
              "(f1ebca5f9b62) — rotation is a CEO act (Art. LXXVI §2); "
              "update the records before wiring")
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
    print(f"[r504-deploy] target commit: {commit}")

    # push-before-deploy (the R477 orphan lesson)
    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0]
    print(f"[r504-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first "
              "(the orphan-commit class)")
        return 2

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[r504-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]} const="
              f"{before.get('constitution_version', '?')}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r504-deploy] BEFORE probe pending "
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
        print(f"[r504-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r504-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        # the sealed instruments MUST survive the prune (the R486 lesson):
        # calibration records + the RBG machinery + the free-evidence
        # transport are verified present in the staged tree
        shipped = stage / "discovery_fabric" / "engine" / \
            "calibration_records"
        shipped_names = sorted(p.name for p in shipped.glob("*.json")) \
            if shipped.exists() else []
        rbg_dir = stage / "scripts" / "r495_rbg"
        rbg_names = sorted(p.name for p in rbg_dir.glob("*.py")) \
            if rbg_dir.exists() else []
        fes_ok = (stage / "discovery_fabric" / "prior_art_v2" /
                  "free_evidence_sources.py").is_file()
        const_ok = (stage / "EPISTEMIC_CONSTITUTION.md").is_file()
        const_v = ""
        if const_ok:
            m = _re.search(r"\*\*Version:\*\*\s*(\S+)",
                           (stage / "EPISTEMIC_CONSTITUTION.md")
                           .read_text(errors="replace"))
            const_v = m.group(1) if m else ""
        print(f"[r504-deploy] sealed instruments in staged tree: "
              f"calibration_records={len(shipped_names)} rbg={rbg_names} "
              f"free_evidence_sources={fes_ok} constitution={const_v}")

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
            print("[r504-deploy] README frontmatter PREPENDED")
        else:
            print("[r504-deploy] README frontmatter already present")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df_path.write_text(new_df)
        print(f"[r504-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r504-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R504 "
                f"deploy-2.8.0 round: constitution 2.8.0 (Article LXXVI "
                f"Credential Custody) + the sealed instruments (RBG "
                f"battery v4.1 with the corpus-leg-only mode, the "
                f"DIGESTS-pinned calibration records, the A2 v4.2 "
                f"attacker-computes standard) + the free evidence legs "
                f"(HF datasets-server + EPO LOD SPARQL) with the R504 "
                f"HF_TOKEN attach-when-present authenticated quota "
                f"(measured both-modes-live; degrade-never-fail) + the "
                f"Art. X instrument fix (relative imports resolved; the "
                f"true inventory is 188 files / 105,286 LOC)"))
        print(f"[r504-deploy] upload DONE in {time.time()-t0:.0f}s "
              f"— Space revision: {rev}")

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
    print("[r504-deploy] variables set (ZAI repoint PRESERVED)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=val)
    print("[r504-deploy] secrets wired: GITHUB_TOKEN (fp-gated), "
          "PORTFOLIO_COMMIT — HF_TOKEN/ELSEVIER_API_KEY standing, "
          "untouched (Art. LXXVI §4)")

    api.restart_space(repo_id=SPACE)
    print("[r504-deploy] Space restarted — poll /api/version for the "
          "identity tuple")

    rec = {
        "round": "R504", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r491 machinery re-driven with R504 attribution",
        "operator_directive": ("deploy 2.8.0 + the sealed instruments, "
                               "which also re-enables the R502 seal with "
                               "HF_TOKEN authenticated quota"),
        "behavior_bearing_payload": (
            "R504: constitution 2.8.0 + the sealed instruments reach "
            "production — the RBG battery v4.1 (--corpus-leg-only: "
            "F12/F13 only, zero debits, both standing leg seals "
            "referenced never re-claimed), the DIGESTS-pinned "
            "calibration records, the A2 v4.2 attacker-computes "
            "standard, the free evidence legs with HF_TOKEN "
            "attach-when-present authenticated quota (per-call LXXV "
            "provenance records the credential mode used) + the Art. X "
            "instrument fix (relative-import resolution; inventory "
            "128/68,312 -> 188/105,286) + registry 1.3.0 "
            "(AUTHENTICATED re-typed MEASURED_R504)"),
        "before_identity": before,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "shipped_calibration_records_in_tree": shipped_names,
        "shipped_rbg_machinery": rbg_names,
        "shipped_free_evidence_transport": fes_ok,
        "shipped_constitution_version": const_v,
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
            "HF_TOKEN (the authenticated-quota credential, R468/R503 "
            "verified), ELSEVIER_API_KEY, ZAI_API_KEY + ATRIA ring, "
            "NVIDIA/OPENROUTER/ENGINE_OPERATOR_KEY (R503 consolidated), "
            "UNOROUTER/XKIRO/APINEX/BAI/BYNARA/TOKENHARBOR/AEROLINK — "
            "all untouched per Art. LXXVI §2/§4"),
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r504-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
