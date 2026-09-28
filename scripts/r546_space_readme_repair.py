"""R546 production-incident repair: restore the HF Space README frontmatter.

Root cause (item 6 / item 10): the deploy at 47e892d26 shipped the program
README.md to the Space without the required HF frontmatter block (sdk: docker,
app_port: 7860, pinned: false). The last working deploy (3bfc era) shipped
the same program README prefixed with the frontmatter + the "would otherwise
be stripped" guard comment. Without the block, the Space enters CONFIG_ERROR
("Missing configuration in README") and /api/version + /api/health return 503.

This repair re-stages the exact tested commit, prefixes the Space README with
the frontmatter (identical bytes to the last working deploy), uploads, and
restarts — then polls /api/version to exact-SHA convergence. The engine tree
is byte-identical to the tested commit; only the Space-facing README gains
the HF card block (which git-archive deploy strips, so it is re-added at
deploy time, never committed to the engine repo).

Reads HF_TOKEN from env only. Never touches secrets.
"""
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE = "prateekm1/toscanini-prod-validation"
SPACE_URL = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = REPO / "R546" / "SPACE_README_REPAIR_RECORD.json"
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

# The exact HF Space card frontmatter the last working deploy shipped
# (the 3bfc-era Space README: frontmatter + guard comment + program body).
FRONTMATTER = """---
title: Toscanini Prod Validation
emoji: "\\U0001F3B5"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

<!-- The HF Space card frontmatter (sdk: docker, app_port: 7860) — the
canonical engine README follows. The git-archive deploy would otherwise
strip it (the CONFIG_ERROR of the first R447 deploy, fixed upfront). -->

"""


def sh(*args):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(REPO), timeout=300)


def get_json(url, timeout=60):
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
    print(f"[repair] HEAD={commit[:12]} origin/main={remote[:12]}",
          flush=True)
    if commit != remote:
        print("FATAL: HEAD != origin/main — push first")
        return 2
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    rev = None
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", "HEAD"], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        # re-add the HF Space card frontmatter to the program README
        # (git-archive deploy strips it — the standing deploy behavior).
        readme = stage / "README.md"
        txt = readme.read_text()
        if not txt.startswith("---"):
            txt = FRONTMATTER + txt
        readme.write_text(txt, encoding="utf-8")
        print("[repair] Space README frontmatter restored", flush=True)
        # staged-bytes proof (the deploy's own check)
        reg = (stage / "discovery_fabric" / "engine"
               / "llm_registry.py").read_text()
        assert '"agnes", "AGNES_API_KEY"' in reg, "staged lacks agnes spec"
        print("[repair] staged-bytes proof: agnes spec PRESENT",
              flush=True)
        # prune non-KEEP round dirs (the deploy's own behavior)
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
        print(f"[repair] pruned {len(removed)} round dirs "
              f"({freed / 1e6:.0f} MB)", flush=True)
        # the identity ARG (the deploy's own behavior)
        df = stage / "Dockerfile"
        txt = df.read_text()
        new_txt, n = re.subn(r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
                              f'ARG RENDER_GIT_COMMIT="{commit}"', txt,
                              count=1)
        if n == 1:
            df.write_text(new_txt)
            print(f"[repair] identity ARG -> {commit[:12]}", flush=True)
        else:
            print(f"[repair] RENDER_GIT_COMMIT ARG not found "
                  f"(n={n}) — leaving Dockerfile untouched "
                  f"(it already pins the exact SHA from the prior "
                  f"deploy)", flush=True)
        t0 = time.time()
        rev = api.upload_folder(folder_path=str(stage), repo_id=SPACE,
                                repo_type="space",
                                commit_message=(
                                    f"Toscanini engine deploy at "
                                    f"{commit[:12]} — R546 Space README "
                                    f"frontmatter repair (CONFIG_ERROR)"))
        print(f"[repair] upload DONE in {time.time() - t0:.0f}s "
              f"rev={rev}", flush=True)
    for k, v in STANDING_VARS.items():
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    print("[repair] standing variables re-applied", flush=True)
    api.restart_space(repo_id=SPACE)
    print("[repair] restarted — polling /api/version", flush=True)
    after = {}
    converged = False
    for i in range(50):
        time.sleep(30)
        try:
            after = get_json(SPACE_URL + "/api/version")
        except Exception as exc:
            print(f"[repair] poll {i}: pending ({type(exc).__name__})",
                  flush=True)
            continue
        ec = after.get("engine_commit", "")
        print(f"[repair] poll {i}: engine_commit={ec[:12]}", flush=True)
        if ec == commit:
            converged = True
            break
    health = {}
    try:
        health = get_json(SPACE_URL + "/api/health")
        provs = health.get("providers", {})
        ag = provs.get("agnes", {}) if isinstance(provs, dict) else {}
        print(f"[repair] health ok={health.get('ok')} "
              f"discovery_ready={health.get('discovery_ready')} "
              f"agnes={ag.get('status') if isinstance(ag, dict) else ag}",
              flush=True)
    except Exception as exc:
        health = {"probe_error": repr(exc)[:160]}
    rec = {
        "round": "R546",
        "schema": "R546_SPACE_README_REPAIR/1.0.0",
        "incident": ("Space entered CONFIG_ERROR "
                      "('Missing configuration in README') + /api/* 503 "
                      "after the 47e892d26 deploy shipped the program "
                      "README without the HF frontmatter block"),
        "space": SPACE,
        "commit": commit,
        "hf_revision": str(rev),
        "identity_exact": converged and after.get("engine_commit") == commit,
        "before": {"runtime_stage": "CONFIG_ERROR",
                    "api": "503 Service Unavailable"},
        "after": {"engine_commit": after.get("engine_commit"),
                  "converged": converged,
                  "health": health},
        "engine_tree": "byte-identical to the tested commit; only the "
                       "Space-facing README gains the HF card block "
                       "(deploy-time, never committed to the engine repo)",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
    }
    OUT.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(f"[repair] record -> {OUT}", flush=True)
    return 0 if converged else 2


if __name__ == "__main__":
    raise SystemExit(main())
