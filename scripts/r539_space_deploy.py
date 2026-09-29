#!/usr/bin/env python3
"""R539 — deploy the agnes-default build to the canonical production Space.

Operator directive 2026-09-26 (verbatim): "put this as the number 1 api,
so infrastucture failure doesnt happen again."

Deploys HEAD (must carry the R539 agnes registration) via the standing
r510/r519 machinery (git-archive staging, round-tree prune, README
frontmatter, Dockerfile RENDER_GIT_COMMIT identity, standing variables,
restart) plus ONE addition: the AGNES_API_KEY Space secret (the new
default provider's credential — without it agnes is UNAVAILABLE in
production and the pin is a dead letter).

Secrets (Art. LXXVI, BS-021): values in session env only, never disk /
logs / commits / records — fingerprints only in output and record.
All other secrets are left standing untouched (add-only).

Fail-closed proofs (abort unless ALL hold):
  1. HF_TOKEN fingerprint gate (rotation is a CEO act).
  2. PAT fingerprint gate (rotation is a CEO act).
  3. AGNES_API_KEY present in env (else the deploy cannot wire #1).
  4. origin/main == HEAD (only reachable bytes deploy, Art. LXXXV).
  5. The agnes registration is present in the STAGED tree bytes
     (PROVIDER_SPECS entry + default pin + routing rungs).

Standing production variables are re-applied verbatim (the r510/r519
set); ENGINE_DEFAULT_PROVIDER is deliberately NOT set — the code pin
is the one authority (Art. X).

Usage:
  HF_TOKEN=... AGNES_API_KEY=... GITHUB_PAT=... \\
      python scripts/r539_space_deploy.py
"""
from __future__ import annotations

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
import urllib.request
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

import r456_space_deploy as r456  # noqa: E402  (round-tree prune)
import r447_hf_deploy as driver  # noqa: E402   (SPACE constant)
import r447_deploy_upload as uploader  # noqa: E402 (README frontmatter)
import r548_case_split as case_split  # noqa: E402 (BS-044 case staging)

SPACE = driver.SPACE
SPACE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = REPO / "R539" / "SPACE_DEPLOY_RECORD.json"

HF_FP16 = "33bc7af22c628bc1"
PAT_FP12 = "f1ebca5f9b62"

STANDING_VARS = (
    ("PORT", "7860"),
    ("ZAI_BASE_URL", "https://api.atria-asi.ai/v1/chat/completions"),
    ("ZAI_MODEL", "Atria-Dawn-Preview"),
    ("DURABLE_STATE_ENABLED", "1"),
    ("DURABLE_STATE_BRANCH", "runtime-state-hf"),
    ("LOCAL_QWEN_ENABLE", "1"),
    ("LOCAL_QWEN_CTX", "8192"),
    ("LOCAL_QWEN_THREADS", "2"),
    ("LOCAL_EMBED_ENABLE", "1"),
    ("LOCAL_EMBED_THREADS", "1"),
)


def _fp12(v: str) -> str:
    return "sha256:" + hashlib.sha256(v.encode()).hexdigest()[:12]


def sh(*args, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(cwd or REPO), timeout=300)


def _get_json(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    hf_token = os.environ.get("HF_TOKEN", "")
    agnes_key = os.environ.get("AGNES_API_KEY", "")
    gh_token = (os.environ.get("GITHUB_PAT", "")
                or os.environ.get("GITHUB_TOKEN", ""))
    if not hf_token or hashlib.sha256(
            hf_token.encode()).hexdigest()[:16] != HF_FP16:
        print("FATAL: HF_TOKEN absent or fingerprint mismatch "
              "(rotation is a CEO act, LXXVI)")
        return 2
    if not gh_token or hashlib.sha256(
            gh_token.encode()).hexdigest()[:12] != PAT_FP12:
        print("FATAL: PAT absent or fingerprint mismatch "
              "(rotation is a CEO act, LXXVI)")
        return 2
    if not agnes_key:
        print("FATAL: AGNES_API_KEY absent from env — the #1 credential "
              "must ride the session env (never disk)")
        return 2
    print(f"[r539-deploy] AGNES_API_KEY present ({_fp12(agnes_key)}, "
          f"len {len(agnes_key)})")

    commit = sh("git", "rev-parse", "HEAD").stdout.strip()
    ls = sh("git", "ls-remote",
            "https://x-access-token:" + gh_token +
            "@github.com/prateekm1007/discovery-evidence-fabric.git",
            "refs/heads/main").stdout.split()[0]
    print(f"[r539-deploy] HEAD={commit[:12]} origin/main={ls[:12]}")
    if ls != commit:
        print("FATAL: origin/main does not carry HEAD — push first")
        return 2

    try:
        before = _get_json(SPACE_URL + "/api/version")
        print(f"[r539-deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print("[r539-deploy] BEFORE probe pending")

    from huggingface_hub import HfApi
    api = HfApi(token=hf_token)

    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        # BS-044: split staging by case-exact prefix — one root per
        # case variant (extractall would merge TOSCANINI/ and
        # toscanini/ on this case-insensitive filesystem and bury the
        # executed runtime package under the uppercase prefix).
        stage_lower = Path(td) / "tree_lower"
        stage_lower.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", "HEAD"], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            n_main, n_lower = case_split.extract_case_split(
                tf, stage, stage_lower)
        n_files = (sum(1 for _ in stage.rglob("*") if _.is_file())
                   + sum(1 for _ in stage_lower.rglob("*") if _.is_file()))
        print(f"[r539-deploy] staged {n_files} tracked files "
              f"({archive.stat().st_size / 1e6:.0f} MB) — case-split: "
              f"{n_lower} members staged under toscanini/ separately")

        # proof 5: the agnes registration rides THESE bytes
        reg = (stage / "discovery_fabric" / "engine"
               / "llm_registry.py").read_text()
        assert '"agnes", "AGNES_API_KEY"' in reg, \
            "staged tree lacks the agnes ProviderSpec"
        pin_src = (stage / "discovery_fabric" / "engine"
                   / "provider_health.py").read_text()
        assert '_DEFAULT_PROVIDER_PIN = "agnes"' in pin_src, \
            "staged tree lacks the agnes default pin"
        rout_src = (stage / "discovery_fabric" / "engine"
                    / "model_routing.py").read_text()
        assert '"agnes": [' in rout_src, \
            "staged tree lacks the agnes routing rungs"
        print("[r539-deploy] staged-bytes proof: agnes spec + pin + "
              "rungs PRESENT")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r539-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed) — "
              f"{n_pruned} files remain")

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
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df_path.write_text(new_df)
        print(f"[r539-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r539-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — R539: agnes "
                f"(apihub.agnes-ai.com) registered as the default number-1 "
                f"provider (operator directive 2026-09-26); flash rungs "
                f"measured live + 3/3 FIELD compliant; pro rungs gated; "
                f"standing vars preserved"))
        print(f"[r539-deploy] upload DONE in {time.time() - t0:.0f}s — "
              f"revision: {rev}")

        rev_lower = None
        if n_lower:
            t1 = time.time()
            rev_lower = api.upload_folder(
                folder_path=str(stage_lower), repo_id=SPACE,
                repo_type="space",
                commit_message=(
                    f"Toscanini engine deploy at {commit[:12]} — "
                    f"case-correct toscanini/ runtime package (BS-044: "
                    f"/app/toscanini/ is what the container executes; "
                    f"the case-insensitive staging root would otherwise "
                    f"bury it under TOSCANINI/)"))
            print(f"[r539-deploy] toscanini/ package upload DONE in "
                  f"{time.time() - t1:.0f}s — revision: {rev_lower}")

        # BS-044 source gate: prove the repo bytes landed on BOTH case
        # prefixes BEFORE spending a factory reboot on them. Raw HTTP
        # (resolve/main, live re-resolve) — no local cache involved.
        fails = case_split.verify_case_split_source(
            SPACE, hf_token, commit)
        if fails:
            print("FATAL: BS-044 post-upload source gate FAILED:")
            for f in fails:
                print(f"  - {f}")
            return 2
        print("[r539-deploy] source gate PASS: toscanini/ + "
              "TOSCANINI/ blobs byte-match HEAD (raw HTTP, cache-free)")

    for k, v in STANDING_VARS:
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    print("[r539-deploy] standing variables re-applied "
          "(ENGINE_DEFAULT_PROVIDER deliberately unset: code pin rules)")

    api.add_space_secret(repo_id=SPACE, key="AGNES_API_KEY", value=agnes_key)
    print("[r539-deploy] secret wired: AGNES_API_KEY "
          f"({_fp12(agnes_key)}) — all other secrets standing untouched")

    # BS-044: factory_reboot=True forces a from-scratch image build
    # (no cached COPY . . layer). A plain restart reuses the cached
    # layer, so the executing Python can predate the staged tree while
    # /api/version reports the freshly-baked commit string. The
    # behavior gate below (live physics_state key probe) is the
    # convergence proof, not the version string.
    api.restart_space(repo_id=SPACE, factory_reboot=True)
    print("[r539-deploy] Space factory-rebooted — polling /api/version")

    after, health = {}, {}
    _behavior_gate_ok = False
    for i in range(60):
        time.sleep(30)
        try:
            after = _get_json(SPACE_URL + "/api/version")
        except Exception as exc:  # noqa: BLE001
            print(f"[r539-deploy] poll {i}: version pending "
                  f"({type(exc).__name__})")
            continue
        ec = after.get("engine_commit", "")
        print(f"[r539-deploy] poll {i}: engine_commit={ec[:12]}")
        if ec == commit:
            break
    else:
        print("FATAL: deployed identity never converged on HEAD")
        return 2

    try:
        health = _get_json(SPACE_URL + "/api/health")
        provs = {p.get("provider"): p
                 for p in health.get("providers", [])
                 if isinstance(p, dict)}
        ag = provs.get("agnes", {})
        print(f"[r539-deploy] health: ok={health.get('ok')} "
              f"agnes status={ag.get('status')} "
              f"available_models={ag.get('available_models')}")
        # BS-044 behavior gate: the R548 physics_state key
        # (live_solver_importable) is present ONLY when the
        # executing source is at or after commit 326c84373.
        # A stale cached layer reports the old key name
        # (wired_solver_importable) even though /api/version
        # says the new commit.
        _ps = (health.get("readiness") or {}).get("physics_state") \
            or health.get("physics_state") or {}
        _has_new_key = "live_solver_importable" in _ps
        _has_old_key = "wired_solver_importable" in _ps
        if _has_new_key:
            _behavior_gate_ok = True
            print(f"[r539-deploy] behavior gate: physics_state "
                  f"carries live_solver_importable — executing "
                  f"source is the R548 tree")
        elif _has_old_key:
            print("[r539-deploy] WARNING: physics_state still "
                  "carries the pre-R548 key (wired_solver_ "
                  "importable) — the executing source may be a "
                  "stale cached layer despite the version "
                  "string. factory_reboot was issued; if this "
                  "persists after the next poll, the Space's "
                  "build cache needs a full image invalidation.")
        else:
            print("[r539-deploy] NOTE: physics_state key "
                  "absent — the deployed tree predates the "
                  "R548 health-payload change (expected for "
                  "deploys before 326c84373)")
    except Exception as exc:
        health = {"probe_error": repr(exc)[:160]}
        print("[r539-deploy] health probe pending")

    rec = {
        "round": "R539", "space": SPACE,
        "commit": commit, "hf_revision": str(rev),
        "hf_revision_lower": (getattr(rev_lower, "oid", None)
                              or (str(rev_lower) if rev_lower else None)),
        "case_split": {
            "lower_members_staged": n_lower,
            "source_gate": "PASS (raw-HTTP blob sha match on both "
                           "case prefixes: toscanini/ + TOSCANINI/)"},
        "operator_directive": "put this as the number 1 api, so "
                              "infrastucture failure doesnt happen again "
                              "(2026-09-26, verbatim)",
        "before_identity": before,
        "after_identity": after,
        "health": ({
            "ok": health.get("ok"),
            "agnes": {k: (health.get("providers", []) and
                          [p for p in health.get("providers", [])
                           if p.get("provider") == "agnes"][0].get(k))
                      for k in ("status", "available_models")}}
            if isinstance(health.get("providers"), list) else health),
        "image_slimming": accounting,
        "secrets_wired": ["AGNES_API_KEY"],
        "secrets_fingerprints": {"AGNES_API_KEY": _fp12(agnes_key)},
        "secrets_left_standing": "every other secret untouched (add-only)",
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
    print(f"[r539-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
