#!/usr/bin/env python3
"""R523 — deploy the AFTER arm (the ONE named cliff intervention) to the
canonical production Space.

R523 arms (frozen):
  current -- already-served production build 8f4fc755 (openalex excluded,
             evidence fabric off) — the attribution arm, already durable.
  after   -- main + exactly the ONE named R523 cliff intervention:
             provider_health.retirement_scopes_for_purpose resolves the
             technical_-prefixed purpose family (TECHNICAL_STATE_EXTRACTION)
             to PURPOSE_POST_RANK_TECHNICAL, so zai's existing targeted
             post-rank retirement filters it out of the ordinary chain.

Same machinery as r522_deploy_arm (git-archive staging, prune,
frontmatter, Dockerfile RENDER_GIT_COMMIT identity, standing vars,
secrets, restart) — re-driven per-round, never mutating historical
round scripts (Art. LXIV/LXXIV).

Fail-closed proofs (all must hold or the deploy aborts):
  1. The arm commit is an ancestor of origin/main (Art. LXXXV).
  2. Arm identity in the STAGED bytes: discovery_fabric/engine/
     provider_health.py MUST contain the R523 resolver branch marker
     (`p.startswith("technical_")`) AND zai's retirement must stay data
     in RETIRED_ROUTE_PROVIDERS (no per-provider branch scattered in).
  3. Engine-diff guard vs the production counterpart: the engine diff
     MUST be exactly discovery_fabric/engine/provider_health.py (the one
     intervention and nothing else — Art. XLVII).

Standing winner configuration is re-applied verbatim, including the
R522 winners ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex and
ENGINE_EVIDENCE_FABRIC=0 (held identical on both arms).

Usage:
  HF_TOKEN=... GITHUB_PAT=... python scripts/r523_deploy_arm.py
      --arm after --commit <40-hex> --record R523/AFTER_DEPLOY_RECORD.json
      --message "..." --counterpart-commit <40-hex>
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
# The single file the R523 intervention may change over production
# 8f4fc755 (Art. XLVII instrument identity; CLI-supplied, recorded).
R523_ALLOWED_DIFF_FILE = "discovery_fabric/engine/provider_health.py"
# the R523 resolver branch marker (staged-bytes identity proof)
R523_MARKER = 'p.startswith("technical_")'


def sh(*args, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(cwd or REPO), timeout=300)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True, choices=("after",))
    ap.add_argument("--commit", required=True,
                    help="full 40-hex tree commit to deploy")
    ap.add_argument("--record", required=True,
                    help="repo-relative record path")
    ap.add_argument("--message", required=True,
                    help="Space upload commit message")
    ap.add_argument("--counterpart-commit", required=True,
                    help="the current production SHA (enables the "
                         "engine-diff guard)")
    ap.add_argument("--intervention-marker", required=True,
                    help="token that MUST appear in the staged tree")
    ap.add_argument("--intervention-file", required=True,
                    help="repo-relative file searched for the marker")
    ap.add_argument("--allowed-diff-file", required=True,
                    help="the single engine file permitted to differ "
                         "between the production and after commits")
    args = ap.parse_args()
    from huggingface_hub import HfApi

    for name in (args.commit, args.counterpart_commit):
        if not _re.fullmatch(r"[0-9a-f]{40}", name):
            print("FATAL: commits must be full 40-hex SHAs (no prefixes)")
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
    print(f"[r523-arm] arm={args.arm} commit={args.commit} "
          f"(reachable from origin/main: PROVEN)")

    # engine-diff guard vs the production counterpart
    d = sh("git", "diff", "--name-only", args.counterpart_commit,
           args.commit, "--", *ENGINE_PATHS)
    changed = sorted(d.stdout.split())
    print(f"[r523-arm] engine-diff "
          f"{args.counterpart_commit[:12]}..{args.commit[:12]}: {changed}")
    if changed != [args.allowed_diff_file]:
        print(f"FATAL: engine diff is not exactly "
              f"{args.allowed_diff_file} — arms differ by more than the "
              f"one named intervention (Art. XLVII)")
        return 2
    print(f"[r523-arm] engine-diff guard PROVEN "
          f"({args.allowed_diff_file} only)")

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[r523-arm] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[r523-arm] BEFORE probe pending ({type(exc).__name__})")

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
        print(f"[r523-arm] staged {n_full} tracked files "
              f"({mb_full:.0f} MB) from {args.commit[:12]}")

        # ---- R523 arm identity, fail-closed, in the STAGED bytes ----
        ph_bytes = stage / "discovery_fabric" / "engine" / "provider_health.py"
        ph_text = ph_bytes.read_text(errors="replace") \
            if ph_bytes.is_file() else ""
        assert 'p.startswith("technical_")' in ph_text, \
            "staged tree lacks the R523 technical_-family resolver branch"
        assert "PURPOSE_POST_RANK_TECHNICAL" in ph_text and \
            "RETIRED_ROUTE_PROVIDERS" in ph_text, \
            "staged tree lacks the R519/R520 retirement authority"
        # no per-provider branch scattered into the authority or the
        # technical_state call site (retirement stays data, R519 §6)
        assert 'if provider == "zai"' not in ph_text and \
            'if provider_id == "zai"' not in ph_text, \
            "a per-provider branch was scattered into provider_health"
        ts = (stage / "discovery_fabric" / "engine" / "technical_state.py")
        ts_text = ts.read_text(errors="replace") if ts.is_file() else ""
        assert 'purpose="TECHNICAL_STATE_EXTRACTION"' in ts_text, \
            "staged tree lacks the technical_state extraction purpose"
        print("[r523-arm] R523 intervention PROVEN in staged bytes "
              "(single resolver branch; no scattered provider branch)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r523-arm] pruned {len(accounting['removed_round_dirs'])} "
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
        print(f"[r523-arm] Dockerfile identity ARG -> {args.commit[:12]}")

        print("[r523-arm] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=args.message)
        print(f"[r523-arm] upload DONE in {time.time()-t0:.0f}s — "
              f"revision: {rev}")

    standing_vars = {
        "PORT": "7860",
        "ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
        "ZAI_MODEL": "Atria-Dawn-Preview",
        "DURABLE_STATE_ENABLED": "1",
        "DURABLE_STATE_BRANCH": "runtime-state-hf",
        "LOCAL_QWEN_ENABLE": "1",
        "LOCAL_QWEN_CTX": "8192",
        "LOCAL_EMBED_ENABLE": "1",
        "LOCAL_EMBED_THREADS": "1",
        # R521/R522 winner configuration: HELD IDENTICAL on the after arm
        "ENGINE_EVIDENCE_FABRIC": "0",
        "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex",
    }
    for k, v in standing_vars.items():
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    readback = {}
    try:
        live = dict(api.get_space_variables(repo_id=SPACE))
        for k in ("ENGINE_EVIDENCE_FABRIC",
                  "ENGINE_RETRIEVE_EXCLUDE_SOURCES"):
            obj = live.get(k)
            readback[k] = getattr(obj, "value", None)
    except Exception as exc:  # noqa: BLE001
        readback = {"probe_error": repr(exc)[:160]}
    print(f"[r523-arm] production read-back: {readback}")
    if readback.get("ENGINE_RETRIEVE_EXCLUDE_SOURCES") != "openalex" or \
            readback.get("ENGINE_EVIDENCE_FABRIC") != "0":
        print("FATAL: standing winner configuration NOT read back — "
              "refusing to call this the measured configuration")
        return 2

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN", value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT", value=val)
    print("[r523-arm] secrets rewired identically (fp-gated)")

    api.restart_space(repo_id=SPACE)
    print("[r523-arm] Space restarted — poll /api/version for identity")

    rec = {
        "round": "R523", "arm": args.arm, "space": SPACE,
        "commit": args.commit, "hf_revision": str(rev),
        "counterpart_commit": args.counterpart_commit or None,
        "adapter": "r519/r522_space_deploy machinery re-driven per-arm",
        "arm_identity_proof": {
            "intervention_marker": args.intervention_marker,
            "intervention_file": args.intervention_file,
            "marker_present_in_staged_bytes": True,
        },
        "engine_diff_guard": f"{args.allowed_diff_file} only",
        "variable_delta": None,
        "variable_readback": readback,
        "standing_configuration": {
            "ENGINE_EVIDENCE_FABRIC": "0",
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex",
        },
        "intervention": "provider_health.retirement_scopes_for_purpose "
                        "maps technical_-family purposes to "
                        "PURPOSE_POST_RANK_TECHNICAL (zai already retired "
                        "from that scope; the technical_state extraction "
                        "chain drops zai on ordinary routing)",
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
    print(f"[r523-arm] record -> {out}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
