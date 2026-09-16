#!/usr/bin/env python3
"""R479 — the R478 delivery-tuple closure deploy: operator credentials
arrived, the DELIVERY_BLOCKED_CREDENTIALS state (R478, Art. LXXI §4,
R467 precedent) is unblocked and this driver executes the named three
commands: deploy + identity-verify + the P0-5 transport probe (the
probe runs separately as r479_hf_router_probe.py so each artifact is
individually typed and recorded).

THE DELTA vs the r477 driver (everything else is the r477/r456 flow,
reused by import):
  - GITHUB_TOKEN: NOW RE-WIRED. The r477 rationale ("this session
    holds NO valid GitHub PAT") is void: the operator supplied a fresh
    PAT this round — which is also the R451 rotation escalation being
    closed (R451 scrubbed the leaked PAT and rotated to the operator).
    The runtime NEEDS a valid token for the durable-state branch
    (toscanini/durable.py); the standing secret's validity is
    unknowable from here (HF secrets are write-only by design), so
    wiring the operator-fresh PAT is the only verifiable-safe action.
    The r477 "GITHUB_TOKEN never wired" assert is deliberately
    INVERTED for this round, with this docstring as the record.
  - Identity: bakes HEAD (the R478 records tip 185c103aeb0c9c6f35fed
    a82f532128489bec69e == origin/main, ls-remote verified with the
    fresh PAT at round start).
  - OUT: R479/SPACE_DEPLOY_RECORD.json.
"""
from __future__ import annotations

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

# the r447/r456 import gate: satisfied by the REAL operator PAT from
# the vault (never the sentinel — asserted below).
_SENTINEL = "__R479_UNSET__"


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


_vault0 = _load_vault()
os.environ.setdefault("GITHUB_TOKEN",
                      _vault0.get("GITHUB_TOKEN") or _SENTINEL)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
OUT = REPO / "R479" / "SPACE_DEPLOY_RECORD.json"


def main() -> int:
    from huggingface_hub import HfApi
    vault = _load_vault()
    hf_token = vault.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "")
    gh_token = vault.get("GITHUB_TOKEN") or os.environ.get(
        "GITHUB_TOKEN", "")
    if not hf_token:
        print("FATAL: HF_TOKEN absent (vault + env)")
        return 2
    if not gh_token or gh_token == _SENTINEL:
        print("FATAL: GITHUB_TOKEN absent — the rotation wiring is "
              "this round's point; refusing a placeholder")
        return 2
    api = HfApi(token=hf_token)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                      capture_output=True, text=True).stdout.strip():
        print("FATAL: working tree dirty")
        return 2
    print(f"[r479-deploy] target commit: {commit}")
    print(f"[r479-deploy] GITHUB_TOKEN: re-wiring the operator-fresh "
          f"PAT (fingerprint sha256:{__import__('hashlib').sha256(gh_token.encode()).hexdigest()[:12]}) "
          f"— the R451 rotation escalation closes here")

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
        print(f"[r479-deploy] staged {n_full} tracked files "
              f"({mb_full:.0f} MB tar)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[r479-deploy] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed; kept: "
              f"{accounting['kept_round_dirs']}) — {n_pruned} files remain")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        import re as _re
        # both standing forms: the canonical empty default (this
        # checkout's lineage — the same anchor r447_hf_deploy.py:146
        # pins) and the r456-lineage pre-baked 40-hex form (r477)
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found in the "
                  "staged Dockerfile")
            return 2
        df_path.write_text(new_df)
        print(f"[r479-deploy] Dockerfile identity ARG -> {commit[:12]}")

        print("[r479-deploy] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=(
                f"Toscanini engine deploy at {commit[:12]} — the R479 "
                f"R478-tuple closure (operator credentials arrived; "
                f"GITHUB_TOKEN rotated per the R451 escalation; the "
                f"three named commands executing) via the r479 delta "
                f"driver"))
        print(f"[r479-deploy] upload DONE in {time.time()-t0:.0f}s "
              f"— Space revision: {rev}")

    # the env contract (variables only — same values as r456/r477)
    for k, v in (("PORT", "7860"),
                 ("ZAI_BASE_URL",
                  "https://router.huggingface.co/v1/chat/completions"),
                 ("ZAI_MODEL", "zai-org/GLM-5.3"),
                 ("DURABLE_STATE_ENABLED", "1"),
                 ("DURABLE_STATE_BRANCH", "runtime-state-hf"),
                 ("LOCAL_QWEN_ENABLE", "1"),
                 ("LOCAL_QWEN_CTX", "8192"),
                 ("LOCAL_QWEN_THREADS", "2"),
                 ("LOCAL_EMBED_ENABLE", "1"),
                 ("LOCAL_EMBED_THREADS", "1")):
        api.add_space_variable(repo_id=SPACE, key=k, value=v)

    # secrets: what this environment holds — INCLUDING the rotated
    # GITHUB_TOKEN (the r477 inversion; see docstring).
    wired, skipped = [], []
    for name in ("GITHUB_TOKEN", "ZAI_API_KEY", "PORTFOLIO_COMMIT",
                 "UNOROUTER_API_KEY", "XKIRO_API_KEY", "APINEX_API_KEY",
                 "BAI_API_KEY", "BYNARA_API_KEY", "TOKENHARBOR_API_KEY",
                 "AEROLINK_API_KEY", "ATRIA_API_KEY"):
        val = vault.get(name) or os.environ.get(name, "")
        if name == "ZAI_API_KEY":
            val = hf_token  # the r456 contract: zai rides the HF token
        if name == "PORTFOLIO_COMMIT" and not val:
            val = "0914755c5832f332abe5d74ed1655cd27764ecc0"
        if val:
            assert val != _SENTINEL, "sentinel must never be wired"
            api.add_space_secret(repo_id=SPACE, key=name, value=val)
            wired.append(name)
        else:
            skipped.append(name)
    print(f"[r479-deploy] secrets wired: {wired}")
    print(f"[r479-deploy] secrets left standing (unset here): {skipped}")
    assert "GITHUB_TOKEN" in wired, "rotation wiring must hold"

    rec = {
        "round": "R479", "space": SPACE,
        "commit": commit, "hf_revision": rev,
        "adapter": "r451_c13+round-tree-prune (r479 delta driver)",
        "delta_vs_r477": ("GITHUB_TOKEN re-wired with the "
                          "operator-fresh PAT (R451 rotation "
                          "escalation closed); everything else the "
                          "r477/r456 flow"),
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "secrets_wired": wired,
        "secrets_left_standing": skipped,
        "unblocks": ("R478 Art. LXXI §4 DELIVERY_BLOCKED_CREDENTIALS "
                     "tuple (escalation 1, opened 2026-09-16)"),
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1))
    print(f"[r479-deploy] record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
