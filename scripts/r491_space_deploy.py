#!/usr/bin/env python3
"""R491 — the ring-pinned-calibration deploy: HEAD to the canonical
production Space.

THE R481/R484/R487 FLOW, this round's bearings:
  - R488's measured gate flip (UNKNOWN_NOT_CALIBRATED -> measured
    NOT_CALIBRATED, FPR 1.0 vs the 0.30 bar) rides this deploy from
    the in-tree shipped records (pending since R488 — the vault's
    HF_TOKEN was lost to the container recycle; the operator
    re-supplied it this round).
  - R490's A2_CALIBRATION_SCOPE annotation (metadata only).
  - R491: the require_provider ring pin on the calibration transport
    (fail-closed; the sealed-corpus measurement declares its ring) +
    the ring-bound kill authority in the calibration gate (a
    CALIBRATED state names the ring it was measured on; kills from a
    different ring escalate) + the A2 consumption gate (the R490
    owner ruling's destination: the uncalibrated gauntlet's KILL
    escalates in classify(), objections preserved verbatim — the R417
    treatment extended to the second attacker).

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


# the import-time credential contract (R451-C2): inject from the vault
# BEFORE the imports (the r481/r484/r487 pattern). Never persisted.
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
OUT = REPO / "R491" / "SPACE_DEPLOY_RECORD.json"


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
    print(f"[r491-deploy] target commit: {commit}")

    # push-before-deploy (the R477 orphan lesson)
    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0]
    print(f"[r491-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first "
              "(the orphan-commit class)")
        return 2

    try:
        before = space_get("/api/version", hf_token)
        print(f"[r491-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r491-deploy] BEFORE probe pending "
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
        print(f"[r491-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r491-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        # the calibration records MUST survive the prune (the R486
        # lesson): verify the shipped records are in the staged tree
        shipped = stage / "discovery_fabric" / "engine" / \
            "calibration_records"
        shipped_names = sorted(p.name for p in shipped.glob("*.json")) \
            if shipped.exists() else []
        print(f"[r491-deploy] shipped calibration records in-tree: "
              f"{shipped_names}")

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
            print("[r491-deploy] README frontmatter PREPENDED")
        else:
            print("[r491-deploy] README frontmatter already present")

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
        print(f"[r491-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r491-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R491 "
                f"ring-pinned-calibration round (the require_provider "
                f"fail-closed ring pin on the calibration transport; "
                f"the ring-bound kill authority in the calibration "
                f"gate; the A2 consumption gate — the R490 owner "
                f"ruling's destination; carrying the R488 measured "
                f"gate flip + the R490 A2 scope annotation) via the "
                f"r491 delta driver"))
        print(f"[r491-deploy] upload DONE in {time.time()-t0:.0f}s "
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
    print("[r491-deploy] variables set (ZAI repoint PRESERVED)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN",
                         value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT",
                         value=val)
    print("[r491-deploy] secrets wired: GITHUB_TOKEN (fp-gated), "
          "PORTFOLIO_COMMIT")

    api.restart_space(repo_id=SPACE)
    print("[r491-deploy] Space restarted — the ring-pinned measurement "
          "runs on this build (scripts/"
          "r491_ring_pinned_measurement.py)")

    rec = {
        "round": "R491", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune (r491 delta driver)",
        "behavior_bearing_payload": (
            "R491: the require_provider ring pin on /api/ops/"
            "calibration-attack (fail-closed — the sealed-corpus "
            "measurement declares its ring; a pinned provider that is "
            "unavailable yields a typed transport failure, NEVER a "
            "silent cascade) + the ring-bound kill authority in "
            "attacker_calibration (a CALIBRATED state names its "
            "measured ring; kills from a different ring escalate with "
            "a typed ring_mismatch) + the A2 consumption gate in "
            "classify.py (the R490 owner ruling's destination: while "
            "the gauntlet holds no shipped calibration meeting sealed "
            "bars, its KILL becomes ESCALATED_OBJECTION with "
            "objections preserved verbatim — the R417 treatment "
            "extended to the second attacker) + the unknown-verdict "
            "fail-closed vocabulary (PASS/KILLED + named non-"
            "scientific states; anything else is UNKNOWN)"),
        "riding_from_pending": (
            "R488's measured gate flip (the in-tree shipped v3 "
            "records -> resolve_state derives measured NOT_CALIBRATED, "
            "FPR 1.0 vs the 0.30 bar) + R490's A2_CALIBRATION_SCOPE "
            "annotation — both pending since their rounds on the lost "
            "HF write token; the operator re-supplied the token this "
            "round (verified live: whoami OK, repo.write + inference "
            "scopes; the inference router itself still 402 "
            "CREDIT_EXHAUSTED — the token's operative value is the "
            "deploy path)"),
        "delta_vs_r487_deploy": (
            "behavior commit moves 7d38eb4e -> HEAD; the atria ring + "
            "ZAI_API_KEY NOT re-wired (the deployed ring persists per "
            "the R480 proof); GITHUB_TOKEN re-wired fingerprint-gated; "
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
    print(f"[r491-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
