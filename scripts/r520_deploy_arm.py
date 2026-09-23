#!/usr/bin/env python3
"""R520 — deploy ONE A/B arm tree to the canonical production Space.

R520 arms (frozen):
  baseline  --commit <post-R519 main, pre-R520-change> (the R519 routing
              build: atria retired from ordinary SYNTHESIS/ATTACK, zai
              retired from post-rank purposes; MS operator-instantiation
              route serves zai-first)
  optimized --commit <main + exactly the R520 MS routing change>
              (zai retired from the MS operator-instantiation purpose
              scope via the single authority)

Stages the EXACT commit bytes via `git archive <commit>` (immune to
worktree state), runs the same prune/frontmatter/Dockerfile-ARG flow as
r519_space_deploy, uploads, re-applies the standing variables/secrets,
restarts, and writes its own record. The Dockerfile RENDER_GIT_COMMIT
ARG is stamped with the arm commit so /api/version reports the arm
identity (the battery preflight gates on it — Art. XLVII).

R520 fail-closed proofs (all must hold or the deploy aborts):
  1. The arm commit is an ancestor of origin/main (auditors verify
     reachable bytes — Art. LXXXV; unpushed bytes never deploy).
  2. Arm identity in the STAGED tree bytes:
       baseline  tree MUST contain RETIRED_ROUTE_PROVIDERS with the pin
                 cleared AND MUST NOT contain
                 PURPOSE_MS_OPERATOR_INSTANTIATION anywhere.
       optimized tree MUST contain PURPOSE_MS_OPERATOR_INSTANTIATION
                 AND zai's retirement set MUST include that scope.
  3. Engine-diff guard (when --counterpart-commit is given): the
     discovery_fabric/TOSCANINI/TOSCANINI_UI/Dockerfile diff between
     the two arm commits MUST be exactly
     discovery_fabric/engine/provider_health.py — the one R520
     intervention and nothing else (Art. XLVII instrument identity).

Space variables/secrets are left exactly as standing — only the tree +
restart change per arm. Credential fingerprints only (Art. LXXVI).

Usage:
  HF_TOKEN=... GITHUB_PAT=... python scripts/r520_deploy_arm.py
      --arm baseline --commit <40-hex> --record R520/BASELINE_DEPLOY_RECORD.json
      --message "..." [--counterpart-commit <40-hex>]
"""
from __future__ import annotations

import argparse
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
ENGINE_PATHS = ["discovery_fabric", "TOSCANINI", "TOSCANINI_UI",
                "Dockerfile"]
MS_SCOPE_TOKEN = "PURPOSE_MS_OPERATOR_INSTANTIATION"


def sh(*args, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(cwd or REPO))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True,
                    choices=("baseline", "optimized"))
    ap.add_argument("--commit", required=True,
                    help="full 40-hex tree commit to deploy")
    ap.add_argument("--record", required=True,
                    help="repo-relative record path")
    ap.add_argument("--message", required=True,
                    help="Space upload commit message")
    ap.add_argument("--counterpart-commit", default="",
                    help="the other arm's full SHA (enables the "
                         "engine-diff guard)")
    args = ap.parse_args()
    from huggingface_hub import HfApi

    if not _re.fullmatch(r"[0-9a-f]{40}", args.commit):
        print("FATAL: --commit must be a full 40-hex SHA (no prefixes)")
        return 2
    if args.counterpart_commit and not _re.fullmatch(
            r"[0-9a-f]{40}", args.counterpart_commit):
        print("FATAL: --counterpart-commit must be a full 40-hex SHA")
        return 2
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
        print("FATAL: PAT fingerprint mismatch — rotation is a CEO act")
        return 2
    if hashlib.sha256(hf_token.encode()).hexdigest()[:16] != "33bc7af22c628bc1":
        print("FATAL: HF fingerprint mismatch — STOP, register the delta")
        return 2

    # proof 1: the arm commit must exist AND be reachable from origin/main
    t = sh("git", "cat-file", "-t", args.commit)
    if t.stdout.strip() != "commit":
        print(f"FATAL: {args.commit[:12]} is not a commit object")
        return 2
    anc = sh("git", "merge-base", "--is-ancestor", args.commit,
             "origin/main")
    if anc.returncode != 0:
        print(f"FATAL: {args.commit[:12]} is not reachable from "
              f"origin/main — push first (Art. LXXXV)")
        return 2
    print(f"[r520-arm] arm={args.arm} commit={args.commit} "
          f"(reachable from origin/main: PROVEN)")

    # proof 3 (order before staging: cheap, local): engine diff between
    # the arms must be exactly the one R520 intervention file.
    if args.counterpart_commit:
        d = sh("git", "diff", "--name-only", args.counterpart_commit,
               args.commit, "--", *ENGINE_PATHS)
        changed = sorted(d.stdout.split())
        print(f"[r520-arm] engine-diff "
              f"{args.counterpart_commit[:12]}..{args.commit[:12]}: "
              f"{changed}")
        if changed != ["discovery_fabric/engine/provider_health.py"]:
            print("FATAL: engine diff is not exactly the one R520 "
                  "intervention file — arms differ by more than the "
                  "MS route (Art. XLVII instrument identity)")
            return 2
        print("[r520-arm] engine-diff guard PROVEN "
              "(provider_health.py only)")

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[r520-arm] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r520-arm] BEFORE probe pending ({type(exc).__name__})")

    api = HfApi(token=hf_token)
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", args.commit], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        n_full = sum(1 for _ in stage.rglob("*") if _.is_file())
        mb_full = archive.stat().st_size / 1e6
        print(f"[r520-arm] staged {n_full} tracked files "
              f"({mb_full:.0f} MB) from {args.commit[:12]}")

        # ---- proof 2: arm identity in the STAGED bytes (fail-closed) ----
        ph = (stage / "discovery_fabric" / "engine" /
              "provider_health.py").read_text(errors="replace")
        assert "RETIRED_ROUTE_PROVIDERS" in ph, \
            "staged tree lacks the single retirement authority"
        assert '_DEFAULT_PROVIDER_PIN = ""' in ph, \
            "staged tree must carry the cleared default pin"
        zai_block = _re.search(
            r'"zai":\s*\{([^}]*)\}', ph)
        zai_has_ms_scope = bool(
            zai_block and MS_SCOPE_TOKEN in zai_block.group(1))
        if args.arm == "baseline":
            assert MS_SCOPE_TOKEN not in ph, \
                "baseline tree must predate the R520 MS scope"
            assert not zai_has_ms_scope, \
                "baseline zai set must not carry the MS scope"
        else:
            assert MS_SCOPE_TOKEN in ph, \
                "optimized tree lacks the R520 MS scope constant"
            assert zai_has_ms_scope, \
                "optimized zai set must include the MS scope"
        print(f"[r520-arm] arm identity PROVEN in staged bytes "
              f"(zai_ms_scope={zai_has_ms_scope})")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r520-arm] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed) — "
              f"{n_pruned} files remain")

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

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
        readme_path.write_text(
            readme_path.read_text(errors="replace"), encoding="utf-8")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{args.commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df_path.write_text(new_df)
        print(f"[r520-arm] Dockerfile identity ARG -> {args.commit[:12]}")

        print("[r520-arm] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=args.message)
        print(f"[r520-arm] upload DONE in {time.time()-t0:.0f}s — "
              f"revision: {rev}")

    for k, v in (("PORT", "7860"),
                 ("ZAI_BASE_URL",
                  "https://api.atria-asi.ai/v1/chat/completions"),
                 ("ZAI_MODEL", "Atria-Dawn-Preview"),
                 ("DURABLE_STATE_ENABLED", "1"),
                 ("DURABLE_STATE_BRANCH", "runtime-state-hf"),
                 ("LOCAL_QWEN_ENABLE", "1"),
                 ("LOCAL_QWEN_CTX", "8192"),
                 ("LOCAL_EMBED_ENABLE", "1"),
                 ("LOCAL_EMBED_THREADS", "1")):
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    print("[r520-arm] variables re-applied identically (no arm delta)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN", value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT", value=val)
    print("[r520-arm] secrets rewired identically (fp-gated)")

    api.restart_space(repo_id=SPACE)
    print("[r520-arm] Space restarted — poll /api/version for identity")

    rec = {
        "round": "R520", "arm": args.arm, "space": SPACE,
        "commit": args.commit, "hf_revision": str(rev),
        "counterpart_commit": args.counterpart_commit or None,
        "adapter": "r519_space_deploy machinery re-driven per-arm "
                   "with R520 proofs",
        "arm_identity_proof": {
            "retirement_authority_present": True,
            "default_pin_cleared": True,
            "zai_ms_scope": zai_has_ms_scope,
            "expected": args.arm == "optimized",
        },
        "engine_diff_guard": (
            "provider_health.py only"
            if args.counterpart_commit else "not run (no counterpart)"),
        "before_identity": before,
        "constitution_served": const_v,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "shipped_calibration_records_in_tree": shipped_names,
        "secrets_wired": ["GITHUB_TOKEN", "PORTFOLIO_COMMIT"],
        "secrets_fingerprints": {
            "GITHUB_TOKEN": "sha256:" + hashlib.sha256(
                gh_token.encode()).hexdigest()[:12],
            "HF_TOKEN": "sha256:" + hashlib.sha256(
                hf_token.encode()).hexdigest()[:16],
        },
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out = REPO / args.record
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
    print(f"[r520-arm] record -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
