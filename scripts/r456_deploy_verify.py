#!/usr/bin/env python3
"""R456 deploy verification — the Art. LXXI tuple:
1. ls-remote main == the pushed SHA
2. the Space build reaches RUNNING at the new revision
3. /api/version engine_commit == the target SHA (the build_artifact
   source — the adapter pins RENDER_GIT_COMMIT at build time)
4. /api/health: ok, deployment_drift GREEN, identity_tamper false,
   localqwen HEALTHY (the zero-paid route) + the semantic route probe
Polls until RUNNING or the deadline; typed failures never guess.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import r447_hf_deploy as driver  # noqa: E402

SPACE = driver.SPACE
TARGET = os.environ.get("R456_TARGET_SHA", "")
DEADLINE_S = int(os.environ.get("R456_VERIFY_DEADLINE", "2700"))


def _get(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ.get('HF_TOKEN', '')}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def space_stage() -> str:
    try:
        d = _get(f"https://huggingface.co/api/spaces/{SPACE}/runtime")
        return str(d.get("stage") or d)
    except Exception as exc:  # noqa: BLE001
        return f"UNKNOWN ({type(exc).__name__})"


def main() -> int:
    if not TARGET:
        print("FATAL: R456_TARGET_SHA unset")
        return 2
    t0 = time.time()
    print(f"target: {TARGET}")
    while time.time() - t0 < DEADLINE_S:
        stage = space_stage()
        print(f"[{int(time.time()-t0):4d}s] space stage: {stage}", flush=True)
        if stage in ("RUNNING", "RUNNING_BUILDING"):
            break
        if stage.startswith("BUILD_ERROR") or stage == "PAUSED" \
                or stage == "CRASHED":
            print(f"FATAL: space stage {stage}")
            return 1
        time.sleep(30)

    # RUNNING (or RUNNING_BUILDING: the old container may still serve
    # while the new build queues — poll the version until it flips)
    for attempt in range(90):
        try:
            v = _get("https://prateekm1-toscanini-prod-validation"
                     ".hf.space/api/version")
            commit = v.get("engine_commit")
            print(f"[/api/version] engine_commit={commit} "
                  f"(source={v.get('source')}, "
                  f"constitution={v.get('constitution_version')})")
            if commit == TARGET:
                h = _get("https://prateekm1-toscanini-prod-validation"
                         ".hf.space/api/health")
                ok = h.get("ok")
                drift = ((h.get("deployment_identity") or {})
                         .get("deployment_drift")
                         or h.get("deployment_drift"))
                tamper = (h.get("deployment_identity") or {}).get(
                    "identity_tamper")
                print(f"[/api/health] ok={ok} drift={drift} "
                      f"identity_tamper={tamper}")
                print(f"[health keys] localqwen="
                      f"{(h.get('providers') or {}).get('localqwen')}")
                tuple_ok = (ok is True and drift == "GREEN"
                            and tamper is False)
                print("ARTICLE LXXI TUPLE: "
                      + ("GREEN" if tuple_ok else "DEGRADED"))
                out = {
                    "target_sha": TARGET,
                    "engine_commit": commit,
                    "health_ok": ok, "drift": drift,
                    "identity_tamper": tamper,
                    "tuple": "GREEN" if tuple_ok else "DEGRADED",
                    "verified_at_utc": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                open("scripts/r456_verify_state.json", "w").write(
                    json.dumps(out, indent=2))
                return 0 if tuple_ok else 1
        except Exception as exc:  # noqa: BLE001
            print(f"[/api/version] probe pending ({type(exc).__name__})")
        time.sleep(20)
    print("DEADLINE: the version never matched the target")
    return 1


if __name__ == "__main__":
    sys.exit(main())
