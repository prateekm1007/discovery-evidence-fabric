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

# R401 Phase 0: the explicit acceptance-state vocabulary is owned by
# the probe module (one authority, Art. X) — the harness imports it
# rather than redefining it.
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "r396_external_probes", REPO_ROOT / "scripts" /
    "r396_external_probes.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ACCEPTANCE_STATES = _mod.ACCEPTANCE_STATES


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
    """R401 Phase 0: return the EXPLICIT acceptance state of every
    probe in a completed probe report (a list), or the single state
    "NO_RECORD" when the report file does not exist (fail-closed:
    a missing record is INCOMPLETE-class, never silently skipped).

    The per-record mapping is owned by the probe module's
    probe_record_state (one authority, Art. X): PASS only on an
    explicit state == PASS; legacy `pass: None` never becomes PASS."""
    if not out_json.exists():
        return "NO_RECORD"
    d = json.loads(out_json.read_text())
    states = [_mod.probe_record_state(p) for p in d.get("probes", [])]
    return states or "NO_RECORD"


# R401 Phase 0: the gate aggregation works on EXPLICIT states, never
# on Booleans. PASS is the only affirmative state; every other state
# (FAIL / OBSERVATION_ONLY / INCOMPLETE / UNRESOLVED /
# QUOTA_EXHAUSTED / NO_RECORD) blocks acceptance and is listed by name
# in non_affirmative_states — none is ever converted (Art. XXV).
AFFIRMATIVE_STATE = "PASS"


def _flatten_gate_states(gates: Dict[str, Any]) -> List[str]:
    """Flatten every gate's `result` (a state string or a list of state
    strings) into one state list. This also fixes the latent KeyError:
    the R400C gate previously carried no `result` key at all, so the
    verdict step crashed before writing the final acceptance record."""
    flat: List[str] = []
    for g in gates.values():
        res = g.get("result")
        if isinstance(res, list):
            flat.extend(res)
        elif res is not None:
            flat.append(res)
    return flat


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
    run_record: Dict[str, Any] = {}
    if cap_json.exists():
        d = json.loads(cap_json.read_text())
        cap = d.get("r400c_capture")
        run_record = d
    # R401 Phase 0: the physics-chain gate is adjudicated on the SAME
    # explicit-state contract as the probes (this also fixes the latent
    # KeyError: this gate previously had no `result` key, so the final
    # verdict step crashed). PASS requires the capture contract fields
    # to be present; a finished run with a broken/absent capture is
    # FAIL; no record or a non-terminal run is INCOMPLETE (nothing was
    # proven, Art. XXV). The machine's own verdict (REJECTED is an
    # acceptable outcome) is NOT part of this gate — the gate tests the
    # capture contract, not the winner.
    final_status = run_record.get("final_status")
    required_capture = bool(
        cap and (cap.get("physics_model_version")
                 and (cap.get("baseline_comparison") or {}).get("outcome")
                 and (cap.get("verdict") or {}).get("result_class")))
    if not cap_json.exists() or not final_status:
        r400c_state = "INCOMPLETE"
    elif required_capture:
        r400c_state = "PASS"
    else:
        r400c_state = "FAIL"
    verdict["gates"]["R400C_PHYSICS_RUN"] = {
        "result": r400c_state,
        "capture_present": cap is not None,
        "physics_model_version": (cap or {}).get("physics_model_version"),
        "baseline_comparison_outcome": (
            (cap or {}).get("baseline_comparison") or {}).get("outcome"),
        "result_class_verdict": ((cap or {}).get("verdict") or {}).get(
            "result_class"),
        "final_status": final_status,
        "exec": r}
    flush()

    # ---- 6. the verdict (never converts non-affirmatives) ----------
    flat = _flatten_gate_states(verdict["gates"])
    non_pass = [v for v in flat if v != AFFIRMATIVE_STATE]
    verdict["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime())
    verdict["all_gates_pass"] = bool(flat) and not non_pass
    verdict["n_gate_states"] = len(flat)
    # INCOMPLETE/FAILED/UNRESOLVED/QUOTA_EXHAUSTED/OBSERVATION_ONLY/
    # NO_RECORD stay exactly what they are (Art. XXV) — named, counted,
    # never converted into an affirmative result
    verdict["non_affirmative_states"] = non_pass
    verdict["non_affirmative_counts"] = {
        s: non_pass.count(s) for s in sorted(set(non_pass))}
    flush()
    (OUT_DIR / "POST_DEPLOY_ACCEPTANCE.json").write_text(
        json.dumps(verdict, indent=1, default=str))
    print(json.dumps({k: v for k, v in verdict.items()
                      if k != "gates"}, indent=1, default=str))
    print("\ngate details -> R400/POST_DEPLOY_ACCEPTANCE.json")
    return 0 if verdict["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
