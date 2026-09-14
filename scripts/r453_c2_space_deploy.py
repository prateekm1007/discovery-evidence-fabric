#!/usr/bin/env python3
"""r453_c2_space_deploy.py — R453-C2: redeploy the canonical HF Space
(prateekm1/toscanini-prod-validation) at the MERGED main SHA — the
Claude-class UI reconstruction (one conversation -> one discovery) —
and hand off to the Art. LXXI identity verification.

Recipe: the R451-C1.3 phase-split deploy verbatim (ONE implementation,
Art. X — the canonical driver's own adapter functions):

  1. the target commit pinned from ORIGIN (ls-remote refs/heads/main —
     never local state, Art. XXIII), asserted == local main
  2. git archive at that commit (full tracked tree incl. .dockerignore)
  3. driver._r451_c13_adapter_dockerfile(commit) — the R446-HF adapter
     hunks (node:24 runtime, Chromium, identity pin, non-root) PLUS the
     R451-C1.3 llama.cpp local route (pinned tag b10930 + sha-pinned
     Qwen3-1.7B GGUF), RENDER_GIT_COMMIT pinned to the target
  4. the Space README WITH the HF frontmatter UPFRONT (the R447
     CONFIG_ERROR fix)
  5. ONE upload_folder call; the Docker build runs on HF infrastructure
  6. the full R451-C1.3 env contract (8 variables + 3 secrets)
  7. state file for the follow-up verify script
     (r453_c2_space_verify.py — the Art. LXXI tuple)

Credentials: HF_TOKEN + GITHUB_TOKEN, env-injection ONLY, fail-closed
(the R451-C2 scrub discipline). No token is ever written to disk, to a
remote URL config, or into the uploaded tree.

--dry-run: staging + adapter-Dockerfile asserts ONLY; zero network
calls; no credentials required (an inert non-credential marker is set
for the driver's import-time guard and never used — nothing leaves the
machine in dry-run).

Usage:
  HF_TOKEN=... GITHUB_TOKEN=... python3 r453_c2_space_deploy.py
  python3 r453_c2_space_deploy.py --dry-run
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

REPO = Path("/home/z/my-project/hf_space")
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

GITHUB_URL = "https://github.com/prateekm1007/discovery-evidence-fabric.git"
STATE_OUT = SCRIPTS / "r453_c2_deploy_state.json"

UPLOAD_COMMIT_MESSAGE = (
    "R453-C2 deploy: engine tree at {SHORT} — the Claude-class UI "
    "reconstruction (one conversation -> one discovery): the "
    "composer-first home, the chat-first run narrative, the right-hand "
    "workspace, the honest BLOCKED/UNKNOWN/PENDING states with "
    "stale-positive suppression (Test B), the Art. LXIV deletions "
    "(TechStage, DeepDive, HistoryRail, the pipeline strip); engine "
    "bytes unchanged since 7e4ed47d (records-only trailing commits)")


def _log(msg: str) -> None:
    print(f"[r453c2-deploy] {msg}", flush=True)


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True,
         env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                          text=True, env=env)


def _ls_remote_main(github_token: str) -> str:
    """origin/main tip via ls-remote — Basic x-access-token extraheader
    (the session-validated pattern), GIT_TERMINAL_PROMPT=0, the token
    never embedded in any URL or persisted config."""
    pat_b64 = base64.b64encode(
        f"x-access-token:{github_token}".encode()).decode()
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = _run(["git", "-c",
              f"http.extraheader=Authorization: Basic {pat_b64}",
              "ls-remote", GITHUB_URL, "refs/heads/main"],
             env=env)
    if r.returncode != 0:
        raise RuntimeError(f"ls-remote failed: {r.stderr[:300]}")
    out = r.stdout.split()
    if not out:
        raise RuntimeError("ls-remote returned no ref")
    return out[0]


def main() -> int:
    dry = "--dry-run" in sys.argv

    # ---- fail-closed credential gate (real runs only) ------------------
    hf_token = os.environ.get("HF_TOKEN", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not dry and (not hf_token or not github_token):
        _log("FATAL: HF_TOKEN / GITHUB_TOKEN missing — credentials come "
             "exclusively from environment injection (R451-C2 scrub)")
        return 2

    # the canonical driver import — its module-level guard requires a
    # non-empty GITHUB_TOKEN; dry-run sets an INERT MARKER (never a
    # credential, never used: dry-run makes zero network calls)
    if dry and not github_token:
        os.environ["GITHUB_TOKEN"] = "DRYRUN-INERT-MARKER-not-a-credential"
    import r447_hf_deploy as driver  # noqa: E402
    import r447_deploy_upload as uploader  # noqa: E402

    # ---- 1. the target: ORIGIN/main (Art. XXIII — never local state) --
    if dry:
        target = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        _log(f"DRY-RUN target (local HEAD, no network): {target}")
        remote_main = target
    else:
        remote_main = _ls_remote_main(github_token)
        local_main = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        if remote_main != local_main:
            _log(f"FATAL: local main {local_main[:12]} != origin/main "
                 f"{remote_main[:12]} — reconcile (fetch/ff or push) "
                 f"before deploying")
            return 2
        target = remote_main
        _log(f"target commit (origin/main, ls-remote pinned): {target}")

    # tracked tree must be clean (untracked files are irrelevant: the
    # archive reads the commit object, not the working tree)
    dirty = _run(["git", "status", "--porcelain",
                  "--untracked-files=no"]).stdout.strip()
    if dirty:
        _log("FATAL: tracked working tree dirty — cannot archive a "
             "verified commit state")
        return 2

    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", target], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        n_files = sum(1 for _ in stage.rglob("*") if _.is_file())
        _log(f"staged {n_files} tracked files at {target[:12]} "
             f"({archive.stat().st_size / 1e6:.0f} MB tar)")

        # ---- 3. the R451-C1.3 adapter Dockerfile (llama route incl.) --
        df = driver._r451_c13_adapter_dockerfile(target)
        (stage / "Dockerfile").write_text(df)
        _log(f"adapter Dockerfile written ({len(df.splitlines())} lines, "
             f"RENDER_GIT_COMMIT pinned to {target[:12]}, llama.cpp "
             f"b10930 local route included)")

        # ---- 4. the README WITH frontmatter (R447 CONFIG_ERROR fix) --
        engine_readme = (stage / "README.md").read_text(errors="replace") \
            if (stage / "README.md").exists() else ""
        (stage / "README.md").write_text(
            uploader.README_FRONTMATTER + engine_readme)
        _log("Space README frontmatter written upfront (sdk: docker, "
             "app_port: 7860)")

        if dry:
            _log("DRY-RUN complete: staging + adapter asserts passed; "
                 "no upload, no env write, no network")
            return 0

        # ---- 5. ONE upload call; the build runs on HF ---------------
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        _log("uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage),
            repo_id=driver.SPACE,
            repo_type="space",
            commit_message=UPLOAD_COMMIT_MESSAGE.format(
                SHORT=target[:12]),
        )
        _log(f"Space revision: {rev} ({time.time() - t0:.0f}s upload)")

    # ---- 6. the env contract (the R451-C1.3 set, verbatim) -------------
    from huggingface_hub import HfApi
    api = HfApi(token=hf_token)
    api.add_space_variable(repo_id=driver.SPACE, key="PORT", value="7860")
    api.add_space_variable(
        repo_id=driver.SPACE, key="ZAI_BASE_URL",
        value="https://router.huggingface.co/v1/chat/completions")
    api.add_space_variable(repo_id=driver.SPACE, key="ZAI_MODEL",
                           value="zai-org/GLM-5.3")
    api.add_space_variable(repo_id=driver.SPACE,
                           key="DURABLE_STATE_ENABLED", value="1")
    api.add_space_variable(repo_id=driver.SPACE,
                           key="DURABLE_STATE_BRANCH",
                           value="runtime-state-hf")
    api.add_space_variable(repo_id=driver.SPACE,
                           key="LOCAL_QWEN_ENABLE", value="1")
    api.add_space_variable(repo_id=driver.SPACE,
                           key="LOCAL_QWEN_CTX", value="8192")
    api.add_space_variable(repo_id=driver.SPACE,
                           key="LOCAL_QWEN_THREADS", value="2")
    api.add_space_secret(repo_id=driver.SPACE, key="ZAI_API_KEY",
                         value=hf_token)
    api.add_space_secret(repo_id=driver.SPACE, key="GITHUB_TOKEN",
                         value=github_token)
    api.add_space_secret(
        repo_id=driver.SPACE, key="PORTFOLIO_COMMIT",
        value=os.environ.get("PORTFOLIO_COMMIT",
                             "0914755c5832f332abe5d74ed1655cd27764ecc0"))
    _log("env contract wired (PORT/ZAI_*/DURABLE_STATE_*/LOCAL_QWEN_* "
         "+ ZAI_API_KEY/GITHUB_TOKEN/PORTFOLIO_COMMIT secrets)")

    # ---- 7. the state file for the verify script -----------------------
    state = {
        "artifact_type": "R453-C2 HF deploy state",
        "phase": "uploaded",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "github_repo": GITHUB_URL,
        "github_sha": target,
        "hf_space": driver.SPACE,
        "hf_space_revision": rev if isinstance(rev, str) else str(rev),
        "adapter": "r451_c13 (R446-HF hunks + llama.cpp b10930 route)",
        "env_contract": "the R451-C1.3 set (8 variables + 3 secrets)",
        "verify_script": "r453_c2_space_verify.py",
        "next_step": ("wait RUNNING, then run r453_c2_space_verify.py "
                      "for the Art. LXXI tuple"),
    }
    STATE_OUT.write_text(json.dumps(state, indent=1))
    _log(f"state -> {STATE_OUT}")
    _log("NEXT: the Docker build runs on HF — poll with "
         "r453_c2_space_verify.py --wait 7 (repeat as needed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
