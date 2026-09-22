#!/usr/bin/env python3
"""R519 — deploy the single-retirement-authority build to the canonical
production Space (Art. LXXI delivery standard).

Operator directive (this turn): "push it using PAT ... huggingface API:
hf_..." — registered credentials supplied in-session for the delivery
(HF fingerprint 33bc7af22c628bc1, GH fingerprint f1ebca5f9b62 — both
match the standing vault; no rotation, Art. LXXVI §2: values live only
in session env, never disk/logs/commits; fingerprints only in records).

Reuses the R481/R484/R487/R491/R504/R510/R512 machinery
(stage/prune/frontmatter/Dockerfile-ARG/variables/secrets/restart) with
R519 attribution. BEFORE this run: Space runtime_sha=5e6fcd28...,
/api/version engine_commit=a41c85b7 — DRIFT vs main (0c2139fe). This
deploy brings the Space to the exact target commit.
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

if not shutil.which("git"):
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

import r491_space_deploy as r491  # noqa: E402
import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
OUT = REPO / "R519" / "SPACE_DEPLOY_RECORD.json"
TARGET_SHA = "0c2139fe2a597f0b0648d56cc9ec332574be097f"


def main() -> int:
    from huggingface_hub import HfApi
    vault = r491._load_vault()
    hf_token = vault.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "")
    gh_token = (vault.get("GITHUB_TOKEN") or vault.get("GITHUB_PAT")
                or os.environ.get("GITHUB_PAT", "")
                or os.environ.get("GITHUB_TOKEN", ""))
    if not hf_token:
        print("FATAL: HF_TOKEN absent (vault + env)")
        return 2
    if not gh_token:
        print("FATAL: GITHUB_PAT/GITHUB_TOKEN absent (vault + env)")
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
    if commit != TARGET_SHA:
        print(f"FATAL: HEAD {commit[:12]} != expected R519 target "
              f"{TARGET_SHA[:12]} — do not deploy a different commit")
        return 2
    dirty = subprocess.run(["git", "status", "--porcelain"],
                           cwd=str(REPO), capture_output=True,
                           text=True).stdout.strip()
    if dirty:
        print(f"FATAL: working tree dirty:\n{dirty}")
        return 2
    print(f"[r519-deploy] target commit: {commit}")

    ls = subprocess.run(
        ["git", "ls-remote",
         "https://x-access-token:" + gh_token +
         "@github.com/prateekm1007/discovery-evidence-fabric.git",
         "refs/heads/main"],
        capture_output=True, text=True).stdout.split()[0]
    print(f"[r519-deploy] origin/main ls-remote: {ls[:12]}"
          f"{' == HEAD (verified)' if ls == commit else ' != HEAD'}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first")
        return 2

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[r519-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]} const="
              f"{before.get('constitution_version', '?')}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r519-deploy] BEFORE probe pending ({type(exc).__name__})")

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
        print(f"[r519-deploy] staged {n_full} tracked files ({mb_full:.0f} MB)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r519-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        shipped = stage / "discovery_fabric" / "engine" / "calibration_records"
        shipped_names = sorted(p.name for p in shipped.glob("*.json")) \
            if shipped.exists() else []
        assert len(shipped_names) == 9, \
            f"prune ate calibration records: {shipped_names}"
        const_ok = (stage / "EPISTEMIC_CONSTITUTION.md").is_file()
        assert const_ok, "prune ate the constitution file"
        const_v = ""
        if const_ok:
            m = _re.search(r"\*\*Version:\*\*\s*(\S+)",
                           (stage / "EPISTEMIC_CONSTITUTION.md")
                           .read_text(errors="replace"))
            const_v = m.group(1) if m else ""
        r519_ok = (stage / "R519" / "R519_ROUND_RECORD.json").is_file()
        replay_ok = (stage / "R519" / "CLEAN_REPLAY.json").is_file()
        graph_head = ""
        gpath = stage / "ACTIVE_DISCOVERY_GRAPH.json"
        if gpath.is_file():
            graph_head = json.loads(
                gpath.read_text(errors="replace")).get("repo_head", "")
        print(f"[r519-deploy] prune-proof: calibration_records="
              f"{len(shipped_names)} constitution={const_v} "
              f"r519_record={r519_ok} clean_replay={replay_ok} "
              f"graph_repo_head={graph_head[:12]}")

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
            print("[r519-deploy] README frontmatter PREPENDED")
        else:
            print("[r519-deploy] README frontmatter already present")
        readme_path.write_text(
            readme_path.read_text(errors="replace"), encoding="utf-8")
        print("[r519-deploy] staged README normalized to UTF-8 (repo bytes "
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
        print(f"[r519-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r519-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — R519 "
                f"single routing-retirement authority: RETIRED_ROUTE_"
                f"PROVIDERS table + is_route_retired/apply_route_"
                f"retirement across all chain sources (preferred/role/"
                f"cost/rung); explicit operator override recorded, never "
                f"silent; classification ROUTING_IMPLEMENTED_BUT_UNPROVEN"))
        print(f"[r519-deploy] upload DONE in {time.time()-t0:.0f}s — "
              f"revision: {rev}")

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
    print("[r519-deploy] variables set (ZAI repoint PRESERVED — routing "
          "retirement is code-level now; the env repoint is an explicit "
          "operator override, recorded per R519 §5)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN", value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT", value=val)
    print("[r519-deploy] secrets wired: GITHUB_TOKEN (fp-gated), "
          "PORTFOLIO_COMMIT — HF_TOKEN/ELSEVIER_API_KEY standing untouched")

    api.restart_space(repo_id=SPACE)
    print("[r519-deploy] Space restarted — poll /api/version for identity")

    rec = {
        "round": "R519", "space": SPACE,
        "commit": commit, "hf_revision": str(rev),
        "adapter": "r491 machinery re-driven with R519 attribution",
        "operator_directive": "push it using PAT + huggingface API "
                              "(delivery credentials supplied in-session)",
        "deploy_basis": "R519/R519_ROUND_RECORD.json — single retirement "
                        "authority + bypass closure (ROUTING_IMPLEMENTED_"
                        "BUT_UNPROVEN; routing shipped, performance proof "
                        "awaits credential-blocked battery)",
        "default": "ordinary/default routing blocks retired providers; "
                   "explicit operator override allowed and recorded only",
        "constitution_served": const_v,
        "before_identity": before,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "shipped_calibration_records_in_tree": shipped_names,
        "shipped_constitution_version": const_v,
        "shipped_r519_record": r519_ok,
        "shipped_clean_replay": replay_ok,
        "shipped_graph_repo_head": graph_head,
        "secrets_wired": ["GITHUB_TOKEN", "PORTFOLIO_COMMIT"],
        "secrets_fingerprints": {
            "GITHUB_TOKEN": "sha256:" + hashlib.sha256(
                gh_token.encode()).hexdigest()[:12],
            "HF_TOKEN": "sha256:" + hashlib.sha256(
                hf_token.encode()).hexdigest()[:16],
        },
        "secrets_left_standing": "HF_TOKEN, ELSEVIER_API_KEY, ring keys — "
                                 "all untouched per Art. LXXVI",
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
    print(f"[r519-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
