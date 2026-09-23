#!/usr/bin/env python3
"""R521 — deploy ONE attribution arm tree to the canonical production Space.

R521 arms (frozen):
  before --commit <current production HEAD> (post-R520 main)
  after  --commit <main + exactly the ONE named R521 cliff intervention>

Stages the EXACT commit bytes via `git archive <commit>` (immune to
worktree state), runs the same prune/frontmatter/Dockerfile-ARG flow as
r519_space_deploy, uploads, re-applies the standing variables/secrets,
restarts, and writes its own record. The Dockerfile RENDER_GIT_COMMIT
ARG is stamped with the arm commit so /api/version reports the arm
identity (the battery preflight gates on it — Art. XLVII).

R521 fail-closed proofs (all must hold or the deploy aborts):
  1. The arm commit is an ancestor of origin/main (auditors verify
     reachable bytes — Art. LXXXV; unpushed bytes never deploy).
  2. Arm identity in the STAGED tree bytes, via CLI-supplied markers
     (the cliff is named AFTER attribution, so the marker cannot be
     hardcoded here without pre-committing to a cliff):
       before  tree MUST NOT contain --intervention-marker (when given).
       after   tree MUST contain --intervention-marker inside
               --intervention-file, AND --intervention-marker is recorded
               in the deploy record. after WITHOUT both flags REFUSES.
  3. Engine-diff guard (when --counterpart-commit is given): the
     discovery_fabric/TOSCANINI/TOSCANINI_UI/Dockerfile diff between
     the two arm commits MUST be exactly --allowed-diff-file (one file —
     the one R521 intervention and nothing else; Art. XLVII instrument
     identity). The allowed file is CLI-supplied and recorded, never
     defaulted.

Space variables/secrets are left exactly as standing — only the tree +
restart change per arm. Credential fingerprints only (Art. LXXVI).

Usage:
  HF_TOKEN=... GITHUB_PAT=... python scripts/r521_deploy_arm.py
      --arm before --commit <40-hex> --record R521/BEFORE_DEPLOY_RECORD.json
      --message "..." [--counterpart-commit <40-hex>]
  HF_TOKEN=... GITHUB_PAT=... python scripts/r521_deploy_arm.py
      --arm after --commit <40-hex> --record R521/AFTER_DEPLOY_RECORD.json
      --message "..." --counterpart-commit <40-hex>
      --intervention-marker <TOKEN> --intervention-file <path>
      --allowed-diff-file <path>
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


def sh(*args, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(cwd or REPO), timeout=300)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True,
                    choices=("before", "after"))
    ap.add_argument("--commit", required=True,
                    help="full 40-hex tree commit to deploy")
    ap.add_argument("--record", required=True,
                    help="repo-relative record path")
    ap.add_argument("--message", required=True,
                    help="Space upload commit message")
    ap.add_argument("--counterpart-commit", default="",
                    help="the other arm's full SHA (enables the "
                         "engine-diff guard)")
    ap.add_argument("--intervention-marker", default="",
                    help="token that MUST (after) / MUST NOT (before) "
                         "appear in the staged tree")
    ap.add_argument("--intervention-file", default="",
                    help="repo-relative file searched for the marker")
    ap.add_argument("--allowed-diff-file", default="",
                    help="the single engine file permitted to differ "
                         "between arms")
    args = ap.parse_args()
    from huggingface_hub import HfApi

    if not _re.fullmatch(r"[0-9a-f]{40}", args.commit):
        print("FATAL: --commit must be a full 40-hex SHA (no prefixes)")
        return 2
    if args.counterpart_commit and not _re.fullmatch(
            r"[0-9a-f]{40}", args.counterpart_commit):
        print("FATAL: --counterpart-commit must be a full 40-hex SHA")
        return 2
    if args.arm == "after" and not (
            args.intervention_marker and args.intervention_file
            and args.allowed_diff_file):
        print("FATAL: after-arm deploy requires --intervention-marker, "
              "--intervention-file and --allowed-diff-file (the cliff is "
              "named after attribution; refusing unmarked after-arm)")
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

    # proof 1: reachable from origin/main
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
    print(f"[r521-arm] arm={args.arm} commit={args.commit} "
          f"(reachable from origin/main: PROVEN)")

    # proof 3 (cheap, local, before staging): engine diff must be
    # exactly the one allowed file.
    if args.counterpart_commit:
        if not args.allowed_diff_file:
            print("FATAL: --counterpart-commit without "
                  "--allowed-diff-file — refusing open-ended diff")
            return 2
        d = sh("git", "diff", "--name-only", args.counterpart_commit,
               args.commit, "--", *ENGINE_PATHS)
        changed = sorted(d.stdout.split())
        print(f"[r521-arm] engine-diff "
              f"{args.counterpart_commit[:12]}..{args.commit[:12]}: "
              f"{changed}")
        if changed != [args.allowed_diff_file]:
            print(f"FATAL: engine diff is not exactly "
                  f"{args.allowed_diff_file} — arms differ by more than "
                  f"the one intervention (Art. XLVII)")
            return 2
        print("[r521-arm] engine-diff guard PROVEN "
              f"({args.allowed_diff_file} only)")

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[r521-arm] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r521-arm] BEFORE probe pending ({type(exc).__name__})")

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
        print(f"[r521-arm] staged {n_full} tracked files "
              f"({mb_full:.0f} MB) from {args.commit[:12]}")

        # ---- proof 2: arm identity in the STAGED bytes (fail-closed) ----
        marker_found = None
        if args.intervention_marker and args.intervention_file:
            target = stage / args.intervention_file
            if not target.is_file():
                print(f"FATAL: intervention file {args.intervention_file} "
                      f"absent from staged tree")
                return 2
            marker_found = (args.intervention_marker in
                            target.read_text(errors="replace"))
            if args.arm == "before" and marker_found:
                print("FATAL: before-arm tree already contains the "
                      "intervention marker — not a clean before")
                return 2
            if args.arm == "after" and not marker_found:
                print("FATAL: after-arm tree lacks the intervention "
                      "marker — wrong build")
                return 2
            print(f"[r521-arm] arm identity PROVEN in staged bytes "
                  f"(marker_present={marker_found})")
        else:
            print("[r521-arm] no intervention marker supplied "
                  "(before-arm baseline deploy)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r521-arm] pruned {len(accounting['removed_round_dirs'])} "
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
        print(f"[r521-arm] Dockerfile identity ARG -> {args.commit[:12]}")

        print("[r521-arm] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=args.message)
        print(f"[r521-arm] upload DONE in {time.time()-t0:.0f}s — "
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
    print("[r521-arm] variables re-applied identically (no arm delta)")

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN", value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT", value=val)
    print("[r521-arm] secrets rewired identically (fp-gated)")

    api.restart_space(repo_id=SPACE)
    print("[r521-arm] Space restarted — poll /api/version for identity")

    rec = {
        "round": "R521", "arm": args.arm, "space": SPACE,
        "commit": args.commit, "hf_revision": str(rev),
        "counterpart_commit": args.counterpart_commit or None,
        "adapter": "r519_space_deploy machinery re-driven per-arm "
                   "with R521 proofs",
        "arm_identity_proof": {
            "intervention_marker": args.intervention_marker or None,
            "intervention_file": args.intervention_file or None,
            "marker_present_in_staged_bytes": marker_found,
        },
        "engine_diff_guard": (
            f"{args.allowed_diff_file} only"
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
    print(f"[r521-arm] record -> {out}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
