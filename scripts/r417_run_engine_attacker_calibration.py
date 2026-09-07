#!/usr/bin/env python3
"""scripts/r417_run_engine_attacker_calibration.py — audit item 1 (R417).

LIVE measurement of the ENGINE'S OWN product attacker
(discovery_fabric/engine/independent_attack.py) on the sealed 40-case
calibration corpus, per R412/CALIBRATION/
ENGINE_PASS_PREREGISTRATION.json (the scope, input mapping, denominators,
and prediction are fixed there BEFORE this run — Art. VIII/XXVII).

Reuses the R412 sealed metrics machinery (calibration_metrics.py:
preflight / pass_metrics / verdict_vs_thresholds) unchanged; writes its
own checkpoint JSONL and its own measurement record — the sealed
r412_attacker_measurement.json and its run JSONLs are NEVER rewritten.

CLI:
  --run              run/extend the pass (checkpointed, resume-safe)
  --summary          recompute the measurement record from the JSONL
  --limit N          process at most N pending cases (pace testing)

Constitutional grounding:
  - Art. L: this IS the attacker-calibration measurement for the
    product instrument.
  - Art. VIII/XXVII: preflight seal check before any attack; thresholds
    read from the seal at report time; nothing tuned to the corpus.
  - Art. LXI: transport failure is INCOMPLETE, re-queued within the
    bounded retry budget, never a verdict.
  - Art. LXII: per-case prompt/output hashes + env pins committed with
    the results; headline metrics regenerable from the JSONL evidence.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parents[1]
REPO = HERE
CAL = REPO / "R412" / "CALIBRATION"

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CAL))

from calibration_metrics import (  # noqa: E402
    outcome_of, pass_metrics, preflight, verdict_vs_thresholds)

CORPUS_PATH = CAL / "r412_attacker_calibration_corpus.json"
SEAL_PATH = CAL / "r412_calibration_seal.json"
RUNS_DIR = CAL / "runs"
STATE_PATH = RUNS_DIR / "engine-independent.jsonl"
MEASUREMENT_PATH = CAL / "engine_independent_attack_measurement.json"
PREREG_PATH = CAL / "ENGINE_PASS_PREREGISTRATION.json"

MAX_ATTEMPTS = 2
PACE_SECONDS = 1.0

ENV_PINS = {"ENGINE_LLM_PROVIDER": "zai", "ZAI_MODEL": "glm-4-plus"}


# ---------------------------------------------------------------------------
# zai gateway lifecycle (the R412 runner's pattern, self-contained)
# ---------------------------------------------------------------------------
GATEWAY_PORT = 8787


def _gateway_alive() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{GATEWAY_PORT}/healthz", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


class _ZaiGateway:
    def __init__(self) -> None:
        self.proc = None

    def __enter__(self):
        import subprocess
        from discovery_fabric.engine.adapters import load_credentials
        load_credentials()
        key = os.environ.get("ZAI_API_KEY", "")
        if not key:
            # the gateway key is generated per invocation; the engine's
            # ZAI_API_KEY must equal it (the registry sends ZAI_API_KEY
            # as the bearer token)
            key = os.environ.get("ZAI_GATEWAY_KEY", "")
        if not key:
            raise RuntimeError("ZAI_API_KEY/ZAI_GATEWAY_KEY missing")
        subprocess.run(["pkill", "-f", "zai_gateway.mjs"],
                       capture_output=True, timeout=5)
        time.sleep(0.5)
        env = dict(os.environ)
        env["ZAI_GATEWAY_KEY"] = key
        self.proc = subprocess.Popen(
            ["node", "scripts/zai_gateway.mjs", str(GATEWAY_PORT)],
            cwd=str(REPO), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        for _ in range(30):
            time.sleep(0.5)
            if _gateway_alive():
                return self
        self.__exit__(None, None, None)
        raise RuntimeError("zai gateway did not become healthy")

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except Exception:
                self.proc.kill()
        return False


# ---------------------------------------------------------------------------
# corpus case -> engine instrument inputs (the preregistered mapping)
# ---------------------------------------------------------------------------

def engine_inputs(case: Dict[str, Any]) -> Dict[str, Any]:
    cand = case["candidate"]
    ke = cand.get("killer_experiment") or {}
    testable = " ".join(
        x for x in [str(ke.get("experiment") or ""),
                    (f"Kill condition: {ke['kill_condition']}"
                     if ke.get("kill_condition") else "")] if x)
    baseline = cand.get("baseline") or {}
    chain = cand.get("causal_chain", "")
    mechanism = (" -> ".join(str(s) for s in chain) if isinstance(
        chain, list) else str(chain))
    candidate = {
        "candidate_id": cand.get("candidate_id") or case["case_id"],
        "mechanism": mechanism,
        "intervention": cand.get("intervention", ""),
        "predicted_effect": cand.get("predicted_effect", ""),
        "testable_prediction": testable,
        "novel_design_variable": cand.get("unexploited_phenomenon", ""),
        "known_failure_modes": cand.get("failure_modes") or [],
        "constraint_set": {
            "boundary_conditions": cand.get("boundary_conditions", "")},
    }
    problem = {
        "device": str(baseline.get("baseline_incumbent")
                      or cand.get("technology_name") or ""),
        "failure": str(cand.get("problem") or ""),
    }
    evidence = [{"id": r.get("record_id"), "title": r.get("title")}
                for r in (case.get("pool") or [])]
    return {"candidate": candidate, "problem": problem,
            "evidence": evidence}


def _attack_one(case: Dict[str, Any]) -> Dict[str, Any]:
    """Call the engine's independent_attack UNMODIFIED on the mapped
    case; wrap the result into the metrics-compatible record shape."""
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine.independent_attack import \
        independent_attack
    inp = engine_inputs(case)
    record = independent_attack(
        inp["candidate"], inp["problem"], inp["evidence"],
        None)  # generator_provider=None per the preregistration
    # adapter: engine record -> r411-compatible fields for
    # calibration_metrics (outcome_of reads status/verdict; the marker
    # check reads final_objection/surfaces)
    items = record.get("items") or []
    kills = [i for i in items if i.get("verdict") == "KILL"]
    adapted = dict(record)
    adapted["status"] = (
        "OK" if record.get("overall") != "ATTACK_INCOMPLETE" else "ERR")
    adapted["verdict"] = record.get("overall")
    adapted["kill_surfaces"] = [k.get("attack_class") for k in kills]
    adapted["final_objection"] = (
        record.get("kill_basis") and
        "; ".join(str(k.get("basis") or "")[:200]
                  for k in record["kill_basis"][:3])) or ""
    adapted["surfaces"] = {
        i.get("attack_class"): str(i.get("basis") or "") for i in items}
    adapted["engine_record_verbatim"] = record  # full fidelity
    return adapted


# ---------------------------------------------------------------------------
# checkpointing (the R412 pattern, compact)
# ---------------------------------------------------------------------------

def _read_lines() -> List[Dict[str, Any]]:
    if not STATE_PATH.exists():
        return []
    out = []
    for raw in STATE_PATH.read_text().splitlines():
        raw = raw.strip()
        if raw:
            out.append(json.loads(raw))
    return out


def _latest(lines, case_id):
    best = None
    for ln in lines:
        if ln.get("case_id") == case_id:
            if best is None or ln.get("attempt", 0) >= best.get(
                    "attempt", 0):
                best = ln
    return best


def run_pass(limit: Optional[int] = None) -> Dict[str, Any]:
    pre = preflight(CORPUS_PATH, SEAL_PATH)
    if not pre["ok"]:
        return {"status": "PREFLIGHT_FAILED", "preflight": pre}
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = corpus["cases"]

    saved_env = {k: os.environ.get(k, "") for k in ENV_PINS}
    for k, v in ENV_PINS.items():
        os.environ[k] = v
    gateway = _ZaiGateway()
    try:
        gateway.__enter__()
        lines = _read_lines()
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        pending = []
        for case in cases:
            last = _latest(lines, case["case_id"])
            if last is None:
                pending.append(case)
            elif outcome_of(last.get("attack") or {}) == "INCOMPLETE" and (
                    last.get("attempt", 1) < MAX_ATTEMPTS):
                pending.append(case)
        if limit is not None:
            pending = pending[:limit]
        n_new = 0
        for case in pending:
            last = _latest(lines, case["case_id"])
            attempt = (last.get("attempt", 0) + 1) if last else 1
            record = {
                "pass_id": "engine-independent",
                "case_id": case["case_id"],
                "label": case["ground_truth"]["label"],
                "expected_final": case["ground_truth"]["expected_final"],
                "attempt": attempt,
                "ts": datetime.now(timezone.utc).isoformat(),
                "attack": _attack_one(case),
            }
            with STATE_PATH.open("a") as f:
                f.write(json.dumps(record) + "\n")
            lines.append(record)
            n_new += 1
            print(f"  {case['case_id']} -> "
                  f"{(record['attack'] or {}).get('overall')}")
            if PACE_SECONDS > 0:
                time.sleep(PACE_SECONDS)
    finally:
        gateway.__exit__(None, None, None)
        for k, v in saved_env.items():
            if v:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
    print(f"new attack records: {n_new}")
    return summary()


def summary() -> Dict[str, Any]:
    corpus = json.loads(CORPUS_PATH.read_text())
    seal = json.loads(SEAL_PATH.read_text())
    cases = corpus["cases"]
    lines = _read_lines()
    results = []
    attempts: Dict[str, int] = {}
    for case in cases:
        last = _latest(lines, case["case_id"])
        if last is None:
            continue
        attempts[case["case_id"]] = last.get("attempt", 1)
        results.append({
            "case_id": case["case_id"],
            "label": case["ground_truth"]["label"],
            "expected_final": case["ground_truth"]["expected_final"],
            "attack": last.get("attack") or {},
        })
    metrics = pass_metrics(results, cases)
    thresholds = seal["pre_registered_thresholds"]
    verdict = verdict_vs_thresholds(metrics, thresholds)
    # scoped TPR diagnostic (preregistered): defect classes the engine
    # instrument actually attacks (prior-art delegated to the collision
    # instrument)
    scoped = [r for r in metrics["per_case"]
              if r["label"] in ("KNOWN_BAD", "NEAR_MISS")]
    scoped_killed = sum(1 for r in scoped if r["outcome"] == "KILLED")
    record = {
        "artifact_type": "R417_ENGINE_INDEPENDENT_ATTACK_MEASUREMENT",
        "pass_id": "engine-independent",
        "preregistration": "R412/CALIBRATION/ENGINE_PASS_PREREGISTRATION.json",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instrument": {
            "module": "discovery_fabric/engine/independent_attack.py",
            "attack_version": "independent_attack/1.0.0",
            "modified": False,
        },
        "corpus_sha256": preflight(CORPUS_PATH, SEAL_PATH)["corpus_sha256"],
        "env_pins": ENV_PINS,
        "n_cases_attacked": len(results),
        "n_attack_invocations": len(lines),
        "attempts_by_case": attempts,
        "metrics": metrics,
        "scoped_tpr_diagnostic": {
            "denominator": "KNOWN_BAD + NEAR_MISS (20 cases: the classes "
                           "the engine instrument attacks)",
            "killed": scoped_killed,
            "tpr": round(scoped_killed / max(1, len(scoped)), 4),
            "note": "diagnostic only; the threshold comparison uses the "
                    "conservative sealed-30 denominator (a "
                    "PRIOR_ART_COLLISION miss counts as a miss — the "
                    "coverage boundary is disclosed, never excused)",
        },
        "threshold_verdict": verdict,
        "prediction_outcome": None,  # filled below
        "reviewer_provenance": "AI_REVIEW (Art. LXVII)",
    }
    fpr = metrics.get("false_kill_rate_on_known_good")
    calibrated = verdict.get("calibrated")
    if calibrated is False:
        record["prediction_outcome"] = (
            "PREDICTION_CONFIRMED: the engine instrument measures "
            f"FPR {fpr} > {thresholds['fpr_max']} — the family "
            "generalization holds (hostile DESTROY-class protocols kill "
            "sealed known-good mechanisms at this rate)")
    elif calibrated is True:
        record["prediction_outcome"] = (
            "PREDICTION_FALSIFIED: the engine 6-class basis-validated "
            "protocol measures CALIBRATED where the family evidence "
            "predicted NOT_CALIBRATED — recorded for analysis, never "
            "tuned away")
    MEASUREMENT_PATH.write_text(json.dumps(record, indent=1))
    print(f"measurement record: {MEASUREMENT_PATH}")
    print(json.dumps({
        "coverage": metrics.get("coverage"),
        "parse": metrics.get("parse_completeness"),
        "fpr_known_good": fpr,
        "tpr_sealed_30": metrics.get("tpr"),
        "scoped_tpr": record["scoped_tpr_diagnostic"]["tpr"],
        "verdict": verdict,
    }, indent=1))
    return record


def main(argv: List[str]) -> int:
    if not argv or argv[0] == "--run":
        run_pass(limit=int(argv[1]) if len(argv) > 1 else None)
        return 0
    if argv[0] == "--summary":
        summary()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
