"""R510 — deploy the nil-delta build to the canonical production Space.

Operator deploy directive (this turn): "deploy to Hugging Face now" with the
loop principle that every machine act runs as a coder autocommand. It does NOT
open GATE A (no verbatim "2.9.0 stands"/"revert" in transcript) or GATE B (no
(a)/(b) ruling) — resubmit stays shut; serving 2.9.0 != ratifying it.

Reuses the R481/R484/R487/R491/R504 machinery (stage/prune/frontmatter/
Dockerfile-ARG/variables/secrets/restart) with R510 attribution. Nil-delta
proof lives in R510/NIL_DELTA_PROOF.json: engine code (discovery_fabric/,
toscanini/, orchestrator/) zero files changed d7520b9b..HEAD; the only data
transition is the ratified 2.8.0->2.9.0 rebind (constitution + acknowledgment
capsule) plus annotation-only registry notes — behavior NIL, disclosed per
Art. VII. Pre-registration identity transfers; record "2.9.0 served pending
confirmation".

Secrets (Art. LXXVI): fingerprint-gated GITHUB_TOKEN + PORTFOLIO_COMMIT wiring
only; HF_TOKEN/ELSEVIER_API_KEY/ring keys standing untouched. BS-021:
fingerprints only, values in session env, never disk/logs/commits.
"""

import hashlib
import json
import os
import re as _re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

if not shutil.which("git"):  # Windows stock PATH gap (measured R510-C1)
    for _d in (r"C:\Program Files\Git\cmd", r"C:\Program Files\Git\bin",
               "/usr/bin", "/usr/local/bin"):
        _cand = os.path.join(_d, "git.exe" if os.name == "nt" else "git")
        if os.path.isfile(_cand):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r491_space_deploy as r491  # noqa: E402  (vault loader + space_get)
import r456_space_deploy as r456  # noqa: E402  (round-tree prune)
import r447_hf_deploy as driver  # noqa: E402   (SPACE constant)
import r447_deploy_upload as uploader  # noqa: E402 (README frontmatter)

SPACE = driver.SPACE
OUT = REPO / "R510" / "SPACE_DEPLOY_RECORD.json"


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
    if hashlib.sha256(gh_token.encode()).hexdigest()[:12] != "f1ebca5f9b62":
        print("FATAL: PAT fingerprint mismatch — rotation is a CEO act (LXXVI)")
        return 2
    if hashlib.sha256(hf_token.encode()).hexdigest()[:16] != "33bc7af22c628bc1":
        print("FATAL: HF fingerprint mismatch — STOP, register the delta")
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
    print(f"[r510-deploy] target commit: {commit}")

    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0]
    print(f"[r510-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first")
        return 2

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[r510-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]} const="
              f"{before.get('constitution_version', '?')}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r510-deploy] BEFORE probe pending ({type(exc).__name__})")

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
        print(f"[r510-deploy] staged {n_full} tracked files ({mb_full:.0f} MB)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r510-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        shipped = stage / "discovery_fabric" / "engine" / "calibration_records"
        shipped_names = sorted(p.name for p in shipped.glob("*.json")) \
            if shipped.exists() else []
        assert len(shipped_names) == 9, \
            f"prune ate calibration records: {shipped_names}"
        rbg_dir = stage / "scripts" / "r495_rbg"
        rbg_names = sorted(p.name for p in rbg_dir.glob("*.py")) \
            if rbg_dir.exists() else []
        assert rbg_names, "prune ate the RBG machinery"
        fes_ok = (stage / "discovery_fabric" / "prior_art_v2" /
                  "free_evidence_sources.py").is_file()
        assert fes_ok, "prune ate the free-evidence transport"
        const_ok = (stage / "EPISTEMIC_CONSTITUTION.md").is_file()
        assert const_ok, "prune ate the constitution file"
        const_v = ""
        if const_ok:
            m = _re.search(r"\*\*Version:\*\*\s*(\S+)",
                           (stage / "EPISTEMIC_CONSTITUTION.md")
                           .read_text(errors="replace"))
            const_v = m.group(1) if m else ""
        print(f"[r510-deploy] prune-proof: calibration_records="
              f"{len(shipped_names)} rbg={len(rbg_names)} "
              f"free_evidence_sources={fes_ok} constitution={const_v}")

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
            print("[r510-deploy] README frontmatter PREPENDED")
        else:
            print("[r510-deploy] README frontmatter already present")
        # hub-client upload prep reads README.md as strict UTF-8 (measured
        # R510: 0x97 byte trips 1.32.0); sanitize the STAGED copy only.
        readme_path.write_text(
            readme_path.read_text(errors="replace"), encoding="utf-8")
        print("[r510-deploy] staged README normalized to UTF-8 (repo bytes "
              "untouched)")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df_path.write_text(new_df)
        print(f"[r510-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r510-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R510 "
                f"nil-delta round: engine code byte-identical to d7520b9b "
                f"(0 files), constitution 2.9.0 SERVED pending confirmation "
                f"(GATE A still open; serving != ratifying) + the sealed "
                f"instruments + the free evidence legs (HF datasets-server + "
                f"EPO LOD SPARQL)"))
        print(f"[r510-deploy] upload DONE in {time.time()-t0:.0f}s — revision: {rev}")

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
    print("[r510-deploy] variables set (ZAI repoint PRESERVED)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN", value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT", value=val)
    print("[r510-deploy] secrets wired: GITHUB_TOKEN (fp-gated), "
          "PORTFOLIO_COMMIT — HF_TOKEN/ELSEVIER_API_KEY standing untouched")

    api.restart_space(repo_id=SPACE)
    print("[r510-deploy] Space restarted — poll /api/version for identity")

    rec = {
        "round": "R510", "space": SPACE,
        "commit": commit, "hf_revision": str(rev),
        "adapter": "r491 machinery re-driven with R510 attribution",
        "operator_directive": "deploy to Hugging Face now (end-to-end AI loop; "
                              "GATE A/B explicitly NOT opened by the directive)",
        "nil_delta_basis": "R510/NIL_DELTA_PROOF.json",
        "constitution_served": "2.9.0 served pending confirmation "
                               "(serving != ratifying; GATE A still open)",
        "before_identity": before,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "shipped_calibration_records_in_tree": shipped_names,
        "shipped_rbg_machinery": rbg_names,
        "shipped_free_evidence_transport": fes_ok,
        "shipped_constitution_version": const_v,
        "secrets_wired": ["GITHUB_TOKEN", "PORTFOLIO_COMMIT"],
        "secrets_fingerprints": {
            "GITHUB_TOKEN": "sha256:" + hashlib.sha256(
                gh_token.encode()).hexdigest()[:12],
        },
        "secrets_left_standing": "HF_TOKEN, ELSEVIER_API_KEY, ring keys — "
                                 "all untouched per Art. LXXVI",
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r510-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
