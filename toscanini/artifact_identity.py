"""toscanini/artifact_identity.py — R396 Phase A: build-artifact identity.

The deployed engine's identity is BAKED INTO THE BUILD ARTIFACT at
Docker/build time and is the ONLY identity source for a hosted process:

  ARTIFACT_IDENTITY.json  {engine_commit, source, render_git_commit,
                           build_context_git_head, baked_at_utc}
  ARTIFACT_IDENTITY.sha256  sha256 of the json bytes, computed at build
                            time, baked as a sibling file

An environment variable can pin an EXPECTATION (the operator-declared
intended commit) but can never DEFINE the identity — an env var can be
set to any value by anyone with dashboard access, which is exactly the
deployment-identity-from-env defect R396 Phase A.3 removes.

Chain of custody (R396 A.6 — BUILD == RUNNING == HEALTH):
  BUILD   the image build writes the two files above (see Dockerfile:
          RENDER_GIT_COMMIT build-arg > git rev-parse HEAD >
          BUILD_CONTEXT_NO_GIT, each honestly labeled, never fabricated).
  RUNNING the process reads the json and re-hashes the bytes; a
          mismatch with the baked sha256 is IDENTITY_TAMPER — the
          running artifact is no longer the built artifact.
  HEALTH  /api/health reports the artifact-derived engine_commit, the
          runtime artifact hash and the tamper verdict. An external
          observer proves
          BUILD_ARTIFACT_SHA == RUNNING_ARTIFACT_SHA == HEALTH_REPORTED_SHA
          by comparing the deployed commit against the health payload
          with identity_tamper=false.

Restart vs deployment (R396 A.7): a restart does not change the
artifact; a deployment does. The health payload pairs the artifact
commit with the process boot time so an external observer can see
"same artifact, new boot" (restart) distinctly from "new artifact"
(deployment).

Local development (no artifact file): identity resolves from live git
(source "git"), exactly as before — never from an env var.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_JSON = REPO_ROOT / "ARTIFACT_IDENTITY.json"
ARTIFACT_SHA = REPO_ROOT / "ARTIFACT_IDENTITY.sha256"

# Process boot identity (R396 A.7): constant for the process lifetime;
# pairs with the (immutable) artifact commit so a restart is visible as
# a new boot time under the SAME artifact, never as a new deployment.
_BOOT_TIME_UTC = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
_BOOT_EPOCH = time.time()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def _read_baked() -> Optional[dict]:
    """Read and structurally validate the baked artifact identity file.
    Returns None when absent (local dev / non-artifact run)."""
    if not ARTIFACT_JSON.exists():
        return None
    try:
        raw = ARTIFACT_JSON.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001 — corrupted artifact is disclosed
        return {"_corrupt": True, "_raw_len": len(raw) if raw else 0}
    if not isinstance(doc, dict) or not doc.get("engine_commit"):
        return {"_corrupt": True}
    doc["_raw"] = raw
    return doc


def identity() -> Dict[str, Any]:
    """The full identity report — never raises, always honest.

    Priority (an environment variable is NEVER an identity source):
      1. build artifact (ARTIFACT_IDENTITY.json)  -> source build_artifact
      2. live git (local development)             -> source git
      3. unresolved                                -> source UNRESOLVED
    """
    baked = _read_baked()
    if baked is None:
        head = _git_head()
        if head:
            return {"engine_commit": head, "engine_commit_source": "git",
                    "artifact_file": False, "identity_tamper": None,
                    "artifact_sha256_runtime": None,
                    "artifact_sha256_baked": None,
                    "boot_time_utc": _BOOT_TIME_UTC,
                    "boot_epoch": _BOOT_EPOCH}
        return {"engine_commit": "", "engine_commit_source": "UNRESOLVED",
                "artifact_file": False, "identity_tamper": None,
                "artifact_sha256_runtime": None,
                "artifact_sha256_baked": None,
                "boot_time_utc": _BOOT_TIME_UTC,
                "boot_epoch": _BOOT_EPOCH}
    if baked.get("_corrupt"):
        return {"engine_commit": "", "engine_commit_source": "ARTIFACT_CORRUPT",
                "artifact_file": True, "identity_tamper": True,
                "artifact_sha256_runtime": None,
                "artifact_sha256_baked": None,
                "boot_time_utc": _BOOT_TIME_UTC,
                "boot_epoch": _BOOT_EPOCH}
    raw = baked["_raw"]
    runtime_sha = _sha256_bytes(raw)
    baked_sha = ""
    if ARTIFACT_SHA.exists():
        baked_sha = ARTIFACT_SHA.read_text().strip().split()[0] or ""
    if not baked_sha:
        # no build-time hash to compare against — tamper is UNKNOWN,
        # never fabricated True or False (Art. VI/XXV)
        tamper = None
    else:
        tamper = baked_sha != runtime_sha
    return {"engine_commit": baked.get("engine_commit") or "",
            "engine_commit_source": "build_artifact",
            "artifact_file": True,
            "identity_tamper": tamper,
            "artifact_sha256_runtime": runtime_sha,
            "artifact_sha256_baked": baked_sha or None,
            "artifact_source": baked.get("source"),
            "render_git_commit": baked.get("render_git_commit"),
            "build_context_git_head": baked.get("build_context_git_head"),
            "baked_at_utc": baked.get("baked_at_utc"),
            "boot_time_utc": _BOOT_TIME_UTC,
            "boot_epoch": _BOOT_EPOCH}


def resolve_engine_commit() -> Tuple[str, str]:
    """The two-tuple the server historically consumed (commit, source).
    The ENGINE_COMMIT env var is deliberately NOT consulted here."""
    ident = identity()
    return ident["engine_commit"], ident["engine_commit_source"]


def operator_declared_commit() -> Optional[str]:
    """The env-var pin, demoted to an EXPECTATION (R396 A.3). It may
    only be cross-checked against the artifact-derived identity; it
    never defines the identity. Kept named so no future edit can
    silently restore the old precedence."""
    return (os.environ.get("ENGINE_COMMIT") or "").strip() or None


def health_view() -> Dict[str, Any]:
    """The exact block /api/health embeds (no secrets)."""
    ident = identity()
    view = {k: v for k, v in ident.items() if k != "_raw"}
    # health-side aliases (the BUILD/RUNNING/HEALTH vocabulary of the
    # deployment_identity block in server.py — same values, one place)
    view["build_artifact_commit"] = view.get("engine_commit") or None
    view["build_artifact_sha256"] = view.get("artifact_sha256_baked")
    view["running_artifact_sha256"] = view.get("artifact_sha256_runtime")
    view["health_reported_commit"] = view.get("engine_commit") or None
    view["operator_declared_commit"] = operator_declared_commit()
    view["live_git_head"] = _git_head() or None
    view["rule"] = (
        "identity = build artifact only (env vars pin expectations, never "
        "identity); BUILD_ARTIFACT_SHA == RUNNING_ARTIFACT_SHA == "
        "HEALTH_REPORTED_SHA with identity_tamper=false; a new boot time "
        "under the same artifact is a RESTART, a changed artifact commit "
        "is a DEPLOYMENT (R396 A.3-A.7)")
    return view
