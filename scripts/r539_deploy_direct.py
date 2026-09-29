"""R539 direct deploy: stage HEAD, patch identity, upload, vars, restart,
poll to convergence. Reads HF_TOKEN from env only. Never touches secrets
(AGNES_API_KEY already wired add-only). No git-token handling."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
SPACE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = REPO / "R539" / "SPACE_DEPLOY_RECORD.json"
HF_FP16 = "33bc7af22c628bc1"
KEEP_ROUNDS = {"R412", "R413", "R449"}
STANDING_VARS = {
    "PORT": "7860",
    "ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
    "ZAI_MODEL": "Atria-Dawn-Preview",
    "DURABLE_STATE_ENABLED": "1",
    "DURABLE_STATE_BRANCH": "runtime-state-hf",
    "LOCAL_QWEN_ENABLE": "1",
    "LOCAL_QWEN_CTX": "8192",
    "LOCAL_EMBED_ENABLE": "1",
    "LOCAL_EMBED_THREADS": "1",
    "ENGINE_EVIDENCE_FABRIC": "0",
    "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex",
}


def sh(*args):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(REPO), timeout=300)


def get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    tok = os.environ.get("HF_TOKEN", "")
    if not tok or hashlib.sha256(tok.encode()).hexdigest()[:16] != HF_FP16:
        print("FATAL: HF_TOKEN absent or fingerprint mismatch")
        return 2
    commit = sh("git", "rev-parse", "HEAD").stdout.strip()
    remote = sh("git", "ls-remote", "origin",
                "refs/heads/main").stdout.split()[0]
    print(f"[deploy] HEAD={commit[:12]} origin/main={remote[:12]}",
          flush=True)
    if commit != remote:
        print("FATAL: HEAD != origin/main — push first")
        return 2
    try:
        before = get_json(SPACE_URL + "/api/version")
        print(f"[deploy] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}", flush=True)
    except Exception as exc:
        before = {"probe_error": repr(exc)[:160]}
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", "HEAD"], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        reg = (stage / "discovery_fabric" / "engine"
               / "llm_registry.py").read_text()
        assert '"agnes", "AGNES_API_KEY"' in reg, "staged lacks agnes spec"
        pin = (stage / "discovery_fabric" / "engine"
               / "provider_health.py").read_text()
        assert '_DEFAULT_PROVIDER_PIN = "agnes"' in pin, "staged lacks pin"
        print("[deploy] staged-bytes proof: agnes spec + pin PRESENT",
              flush=True)
        removed, freed = [], 0
        for child in sorted(stage.iterdir()):
            m = re.fullmatch(r"R(\d+)", child.name)
            if child.is_dir() and m and ("R" + m.group(1)) not in KEEP_ROUNDS:
                sz = sum(f.stat().st_size for f in child.rglob("*")
                         if f.is_file())
                freed += sz
                removed.append(child.name)
                import shutil
                shutil.rmtree(child)
        print(f"[deploy] pruned {len(removed)} round dirs "
              f"({freed / 1e6:.0f} MB freed)", flush=True)
        df = stage / "Dockerfile"
        txt = df.read_text()
        new_txt, n = re.subn(r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
                             f'ARG RENDER_GIT_COMMIT="{commit}"', txt,
                             count=1)
        if n != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df.write_text(new_txt)
        print(f"[deploy] identity ARG -> {commit[:12]}", flush=True)
        t0 = time.time()
        rev = api.upload_folder(folder_path=str(stage), repo_id=SPACE,
                                repo_type="space",
                                commit_message=(
                                    f"Toscanini engine deploy at "
                                    f"{commit[:12]} — R539 agnes default "
                                    f"provider (operator directive)"))
        print(f"[deploy] upload DONE in {time.time() - t0:.0f}s rev={rev}",
              flush=True)
    for k, v in STANDING_VARS.items():
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    print("[deploy] standing variables re-applied", flush=True)
    api.restart_space(repo_id=SPACE)
    print("[deploy] restarted — polling /api/version", flush=True)
    after = {}
    for i in range(40):
        time.sleep(30)
        try:
            after = get_json(SPACE_URL + "/api/version")
        except Exception as exc:
            print(f"[deploy] poll {i}: pending ({type(exc).__name__})",
                  flush=True)
            continue
        ec = after.get("engine_commit", "")
        print(f"[deploy] poll {i}: engine_commit={ec[:12]}", flush=True)
        if ec == commit:
            break
    else:
        print("FATAL: identity never converged on HEAD")
        return 2
    try:
        health = get_json(SPACE_URL + "/api/health")
        provs = health.get("providers", [])
        ag = next((p for p in provs
                   if isinstance(p, dict) and p.get("provider") == "agnes"),
                  {}) if isinstance(provs, list) else provs.get("agnes", {})
        print(f"[deploy] health ok={health.get('ok')} agnes={ag}",
              flush=True)
    except Exception as exc:
        health = {"probe_error": repr(exc)[:160]}
    rec = {
        "round": "R539", "space": SPACE, "commit": commit,
        "hf_revision": str(rev),
        "operator_directive": "put this as the number 1 api (2026-09-26)",
        "before_identity": before, "after_identity": after,
        "health": health if isinstance(health, dict) else {"raw": health},
        "standing_configuration": {
            "ENGINE_EVIDENCE_FABRIC": "0",
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex"},
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(f"[deploy] record -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
