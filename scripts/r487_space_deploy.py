#!/usr/bin/env python3
"""R487 — the attacker-calibration deploy: HEAD (the R486 union records
95766e72 + the R487 v3 instrument) to the canonical production Space.

THE R481/R484 FLOW, one behavior delta:
  - BEARING: independent_attack/3.0.0 (the ANCHOR + ACCOMMODATION
    discipline — the R417 ruling's decisive repair) + the v3.0.0
    measurement-registry entry (fail-closed until measured) + the
    POST /api/ops/calibration-attack measurement transport.
  - The atria ring + ZAI_API_KEY are NOT re-wired (the vault ring was
    destroyed by the container recycle; the deployed ring persists per
    the R480 proof). GITHUB_TOKEN re-wired, fingerprint-gated.

The sealed-corpus v3 measurement runs on THIS build (the deployed
instrument with the production provider ring) immediately after.

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


# the import-time credential contract (R451-C2): r447_hf_deploy
# demands GITHUB_TOKEN in the ENVIRONMENT — inject from the vault
# BEFORE the imports (the r481/r484 pattern). Never persisted.
_vault0 = _load_vault()
_pat0 = (_vault0.get("GITHUB_TOKEN") or _vault0.get("GITHUB_PAT")
         or os.environ.get("GITHUB_TOKEN")
         or os.environ.get("GITHUB_PAT", ""))
if _pat0 and not os.environ.get("GITHUB_TOKEN"):
    os.environ["GITHUB_TOKEN"] = _pat0
_hf0 = _vault0.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "")
if _hf0 and not os.environ.get("HF_TOKEN"):
    os.environ["HF_TOKEN"] = _hf0

import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
OUT = REPO / "R487" / "SPACE_DEPLOY_RECORD.json"


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
    print(f"[r487-deploy] target commit: {commit}")

    # push-before-deploy (the R477 orphan lesson)
    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0]
    print(f"[r487-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first "
              "(the orphan-commit class)")
        return 2

    try:
        before = space_get("/api/version", hf_token)
        print(f"[r487-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r487-deploy] BEFORE probe pending "
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
        print(f"[r487-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r487-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        # the calibration records MUST survive the prune (the R486
        # lesson): verify the shipped records are in the staged tree
        shipped = stage / "discovery_fabric" / "engine" / \
            "calibration_records"
        shipped_names = sorted(p.name for p in shipped.glob("*.json")) \
            if shipped.exists() else []
        print(f"[r487-deploy] shipped calibration records in-tree: "
              f"{shipped_names}")

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
            print("[r487-deploy] README frontmatter PREPENDED")
        else:
            print("[r487-deploy] README frontmatter already present")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        import re as _re
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df_path.write_text(new_df)
        print(f"[r487-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r487-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R487 "
                f"attacker-calibration round (independent_attack/3.0.0: "
                f"the anchor + accommodation discipline; the v3 "
                f"measurement registry entry fail-closed; the "
                f"/api/ops/calibration-attack transport) via the r487 "
                f"delta driver"))
        print(f"[r487-deploy] upload DONE in {time.time()-t0:.0f}s "
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
    print("[r487-deploy] variables set (ZAI repoint PRESERVED)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=val)
    print("[r487-deploy] secrets wired: GITHUB_TOKEN (fp-gated), "
          "PORTFOLIO_COMMIT")

    api.restart_space(repo_id=SPACE)
    print("[r487-deploy] Space restarted — the v3 measurement runs on "
          "this build (scripts/r487_attacker_v3_measurement.py)")

    rec = {
        "round": "R487", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune (r487 delta driver)",
        "behavior_bearing_payload": (
            "independent_attack/3.0.0 — the ANCHOR floor (computation-"
            "only kills demote) + the ACCOMMODATION record-answer "
            "checks (concession-disposal / hedged-target / unstated-"
            "element / typical-value-premise; evidence-anchored kills "
            "never demoted) + the v3.0.0 gate registry entry (fail-"
            "closed until its own measurement ships) + the POST "
            "/api/ops/calibration-attack measurement transport (the "
            "sealed-corpus measurement executes on the deployed "
            "instrument with the production provider ring)"),
        "design_dryrun": (
            "R487/ATTACKER_V3_DESIGN_DRYRUN.json — the v3 rules on the "
            "frozen v2 raw outputs: TPR 1.0 (8/8), FPR 0.25 (1/4), "
            "TNR 0.75, all sealed bars met; near-miss cohort cost "
            "disclosed (2/3 demoted on v2-shaped outputs)"),
        "delta_vs_r486_deploy": (
            "behavior commit moves 99ac03c9 -> HEAD; the atria ring + "
            "ZAI_API_KEY NOT re-wired (vault ring lost to the "
            "container recycle; the deployed ring persists per the "
            "R480 proof); GITHUB_TOKEN re-wired fingerprint-gated; "
            "ZAI repoint preserved"),
        "before_identity": before,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "shipped_calibration_records_in_tree": shipped_names,
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r487-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
