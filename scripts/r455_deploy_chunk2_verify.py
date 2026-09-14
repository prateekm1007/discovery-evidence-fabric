#!/usr/bin/env python3
"""R455 chunked deploy — chunk 2: poll space stage + /api/version identity."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r447_hf_deploy import SPACE, HF_TOKEN, BASE  # noqa: E402

STATE = Path(__file__).resolve().parent / "r455_deploy_state.json"


def _log(m):
    print(f"[r455-verify] {m}", flush=True)


def main() -> int:
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)
    st = json.loads(STATE.read_text())
    commit = st["github_sha"]

    deadline = time.time() + 480  # stay inside one Bash chunk
    stage_ = None
    while time.time() < deadline:
        info = api.space_info(repo_id=SPACE)
        rt = info.runtime
        stage_ = getattr(rt, "stage", None) if rt else None
        if stage_ == "RUNNING":
            break
        if stage_ in ("BUILD_ERROR", "RUNTIME_ERROR"):
            _log(f"FATAL: space stage {stage_}")
            return 3
        _log(f"space stage: {stage_} (waiting...)")
        time.sleep(40)
    _log(f"stage now: {stage_}")
    if stage_ != "RUNNING":
        _log("still building — rerun this chunk")
        return 1

    version = None
    deadline = time.time() + 240
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                BASE + "/api/version",
                headers={"Authorization": f"Bearer {HF_TOKEN}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                version = json.loads(r.read())
                break
        except Exception as exc:  # noqa: BLE001
            _log(f"version poll: {type(exc).__name__} (waiting...)")
            time.sleep(20)
    if not version:
        _log("FATAL: /api/version unreachable")
        return 3
    deployed = version.get("engine_commit")
    ok = deployed == commit
    _log(f"/api/version engine_commit={deployed} "
         f"{'== target (ART. LXXI VERIFIED)' if ok else '!= TARGET (DRIFT!)'}")
    _log(f"constitution: {version.get('constitution_version')} "
         f"source: {version.get('source')}")

    # health tuple
    try:
        req = urllib.request.Request(
            BASE + "/api/health",
            headers={"Authorization": f"Bearer {HF_TOKEN}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            health = json.loads(r.read())
        _log(f"/api/health ok={health.get('ok')} "
             f"drift={health.get('deployment_drift', health.get('drift'))} "
             f"tamper={health.get('identity_tamper')} "
             f"discovery_ready={health.get('discovery_ready')}")
        st["health"] = {
            "ok": health.get("ok"),
            "deployment_drift": health.get("deployment_drift", health.get("drift")),
            "identity_tamper": health.get("identity_tamper"),
            "discovery_ready": health.get("discovery_ready"),
        }
    except Exception as exc:  # noqa: BLE001
        _log(f"health poll failed: {type(exc).__name__}")
    st["deployed_engine_commit"] = deployed
    st["identity_tuple_ok"] = ok
    st["space_stage"] = stage_
    st["version_payload_keys"] = sorted(version.keys())
    STATE.write_text(json.dumps(st, indent=2))
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
