#!/usr/bin/env python3
"""scripts/r400_post_deploy_acceptance.py — R400 ONE-COMMAND live
acceptance harness.

Runs AFTER the operator deploys the R399 artifact (930eca8b) to Render.
It performs, against the PUBLIC HOST only (no local substitution —
R400-B):

  1. P1 identity-chain proof with --deployed-sha 930eca8b...
     (BUILD_ARTIFACT_SHA == RUNNING_ARTIFACT_SHA == HEALTH_REPORTED_SHA,
     identity_tamper=false, source=build_artifact, drift GREEN)
  2. P2 anonymous tenancy isolation
  3. P3 false-premise gate   P4 incomplete-search gate
  4. P5 relevance x2         P6 determinism x3
  5. P7 the 18-case production benchmark (batched 3 cases at a time —
     resumable; every completed case is flushed to disk)
  6. R400-C production physics chain run (PROBLEM -> PREMISE GATE ->
     EVIDENCE -> MECHANISM -> CAD -> PLAUSIBILITY -> PHYSICS ->
     BASELINE -> ATTACK) with the full 12-field capture contract
  7. A machine-readable acceptance verdict that NEVER converts
     INCOMPLETE / FAILED / UNRESOLVED / QUOTA_EXHAUSTED into an
     affirmative result (Art. XXV).

Usage:
  python3 scripts/r400_post_deploy_acceptance.py \
      [--base https://toscanini-engine-docker.onrender.com]

Exit code 0 only when every gate passes live.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOYED_SHA = "930eca8b7db8b0885abccb4e8159a77b8e802723"
OUT_DIR = REPO_ROOT / "R400"


def _run(cmd: List[str], timeout_s: int) -> Dict[str, Any]:
    """Run a subprocess, capture everything (Art. XV: a timeout is a
    recorded outcome, never a silent loss)."""
    started = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout_s, cwd=str(REPO_ROOT))
        return {"cmd": cmd, "returncode": p.returncode,
                "stdout_tail": p.stdout[-3000:],
                "stderr_tail": p.stderr[-2000:],
                "elapsed_s": round(time.time() - started, 1),
                "timed_out": False}
    except subprocess.TimeoutExpired as e:
        return {"cmd": cmd, "returncode": None,
                "stdout_tail": (e.stdout or b"")[-3000:]
                if isinstance(e.stdout, bytes) else str(e.stdout)[-3000:],
                "stderr_tail": "", "elapsed_s": timeout_s,
                "timed_out": True}


def _probe_pass(out_json: Path) -> Any:
    if not out_json.exists():
        return "NO_RECORD"
    d = json.loads(out_json.read_text())
    return [p.get("pass") for p in d.get("probes", [])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base",
                    default="https://toscanini-engine-docker.onrender.com")
    args = ap.parse_args()
    base = args.base
    verdict: Dict[str, Any] = {
        "suite": "R400 post-deploy live acceptance",
        "base": base,
        "deployed_sha": DEPLOYED_SHA,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "gates": {},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    def flush() -> None:
        (OUT_DIR / "POST_DEPLOY_ACCEPTANCE.json").write_text(
            json.dumps(verdict, indent=1, default=str))

    # ---- 1. identity chain (P1 with the pinned target) -------------
    r = _run([sys.executable, "scripts/r396_external_probes.py",
              "--base", base, "--p", "1,2",
              "--deployed-sha", DEPLOYED_SHA,
              "--out", str(OUT_DIR / "LIVE_PROBES_P1_P2_postdeploy.json")],
             240)
    verdict["gates"]["P1_P2"] = {"result": _probe_pass(
        OUT_DIR / "LIVE_PROBES_P1_P2_postdeploy.json"), "exec": r}
    flush()

    # ---- 2. P3 + P4 ------------------------------------------------
    r = _run([sys.executable, "scripts/r396_external_probes.py",
              "--base", base, "--p", "3",
              "--out", str(OUT_DIR / "LIVE_PROBES_P3_postdeploy.json")],
             570)
    verdict["gates"]["P3"] = {"result": _probe_pass(
        OUT_DIR / "LIVE_PROBES_P3_postdeploy.json"), "exec": r}
    flush()

    r = _run([sys.executable, "scripts/r396_external_probes.py",
              "--base", base, "--p", "4",
              "--out", str(OUT_DIR / "LIVE_PROBES_P4_postdeploy.json")],
             570)
    verdict["gates"]["P4"] = {"result": _probe_pass(
        OUT_DIR / "LIVE_PROBES_P4_postdeploy.json"), "exec": r}
    flush()

    # ---- 3. P5 (x2 runs) + P6 (x3 runs) ----------------------------
    r = _run([sys.executable, "scripts/r396_external_probes.py",
              "--base", base, "--p", "5",
              "--out", str(OUT_DIR / "LIVE_PROBES_P5_postdeploy.json")],
             590)
    verdict["gates"]["P5"] = {"result": _probe_pass(
        OUT_DIR / "LIVE_PROBES_P5_postdeploy.json"), "exec": r}
    flush()

    r = _run([sys.executable, "scripts/r396_external_probes.py",
              "--base", base, "--p", "6",
              "--out", str(OUT_DIR / "LIVE_PROBES_P6_postdeploy.json")],
             590)
    verdict["gates"]["P6"] = {"result": _probe_pass(
        OUT_DIR / "LIVE_PROBES_P6_postdeploy.json"), "exec": r}
    flush()

    # ---- 4. P7 18-case benchmark in resumable batches of 3 ---------
    p7_results = []
    for lo in range(1, 19, 3):
        rng = f"{lo}-{min(lo + 2, 18)}"
        out_json = OUT_DIR / f"LIVE_PROBES_P7cases{rng}_postdeploy.json"
        r = _run([sys.executable, "scripts/r396_external_probes.py",
                  "--base", base, "--p", "7", "--p7-cases", rng,
                  "--out", str(out_json)], 590)
        if out_json.exists():
            d = json.loads(out_json.read_text())
            for p in d.get("probes", []):
                p7_results.append(p.get("pass"))
        verdict["gates"][f"P7_{rng}"] = {"result": _probe_pass(out_json),
                                         "exec": r}
        flush()

    # ---- 5. R400-C production physics chain run (live host) --------
    r = _run([sys.executable, "scripts/r400_production_chain_run.py",
              "--base", base,
              "--out", str(OUT_DIR /
                           "PRODUCTION_PHYSICS_RUN_live_postdeploy.json")],
             590)
    cap = None
    cap_json = OUT_DIR / "PRODUCTION_PHYSICS_RUN_live_postdeploy.json"
    if cap_json.exists():
        d = json.loads(cap_json.read_text())
        cap = d.get("r400c_capture")
    verdict["gates"]["R400C_PHYSICS_RUN"] = {
        "capture_present": cap is not None,
        "physics_model_version": (cap or {}).get("physics_model_version"),
        "baseline_comparison_outcome": (
            (cap or {}).get("baseline_comparison") or {}).get("outcome"),
        "result_class_verdict": ((cap or {}).get("verdict") or {}).get(
            "result_class"),
        "exec": r}
    flush()

    # ---- 6. the verdict (never converts non-affirmatives) ----------
    gate_results = [g["result"] for g in verdict["gates"].values()]
    flat = [v for grp in gate_results for v in
            (grp if isinstance(grp, list) else [grp])]
    non_pass = [v for v in flat if v is not True]
    verdict["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime())
    verdict["all_gates_pass"] = not non_pass and flat
    verdict["non_affirmative_states"] = non_pass  # INCOMPLETE/FAILED/
    # UNRESOLVED/QUOTA_EXHAUSTED stay exactly what they are (Art. XXV)
    flush()
    (OUT_DIR / "POST_DEPLOY_ACCEPTANCE.json").write_text(
        json.dumps(verdict, indent=1, default=str))
    print(json.dumps({k: v for k, v in verdict.items()
                      if k != "gates"}, indent=1, default=str))
    print("\ngate details -> R400/POST_DEPLOY_ACCEPTANCE.json")
    return 0 if verdict["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
