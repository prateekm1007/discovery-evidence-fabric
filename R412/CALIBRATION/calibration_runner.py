"""R412/CALIBRATION/calibration_runner.py — P0-1 live measurement
runner for the sealed attacker-calibration corpus.

Runs the R411 attack instrument (discovery_fabric/r411/attack.py,
UNMODIFIED — the measurement characterizes the deployed instrument,
Art. LIX) over the sealed 40-case corpus, one attacker model per pass,
with per-case checkpointing and resumability (the R411 discipline: the
sandbox reaps processes; INCOMPLETE transports are re-queued, never
converted into verdicts — Art. LXI).

Pass registry: each pass pins ENGINE_LLM_PROVIDER + the provider's
model override via environment (the same operator-pin mechanism the
R411 campaign used; the pins travel in every call's meta, never
silent). No prompt or threshold is tuned between passes.

CLI (scripts/r412_run_attacker_calibration.py):
  --pass <pass_id>    run/extend one attacker pass (checkpointed)
  --report            merge passes into the measurement record
  --limit N           process at most N pending cases (pace testing)

Constitutional grounding:
  - Art. L: this is the attacker-calibration measurement.
  - Art. VIII/XXVII: preflight verifies the sealed corpus hash before
    any attack; a mutated corpus aborts the run.
  - Art. LXI: transport failures are INCOMPLETE and re-queued up to a
    bounded retry budget; a case exceeding the budget stays INCOMPLETE
    in the record (honest, never silently retried later).
  - Art. LXII: per-case prompt/output hashes + the pass environment
    pins are committed with the results; the headline metrics are
    regenerable from the committed JSONL evidence.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent            # R412/CALIBRATION
REPO = HERE.parents[1]

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from calibration_metrics import (  # noqa: E402
    agreement, all_deaths_structured, outcome_of, pass_metrics,
    preflight, verdict_vs_thresholds)

CORPUS_PATH = HERE / "r412_attacker_calibration_corpus.json"
SEAL_PATH = HERE / "r412_calibration_seal.json"
RUNS_DIR = HERE / "runs"
MEASUREMENT_PATH = HERE / "r412_attacker_measurement.json"

# Pass registry: attacker instrument configurations measured on the
# frozen corpus. pass order = measurement order. The PRIMARY pass is
# minimax-m3:free via openrouter — the exact R411 operative attacker
# configuration whose 14 kills R412 is calibrating.
PASS_REGISTRY: Dict[str, Dict[str, str]] = {
    "minimax-m3": {
        "ENGINE_LLM_PROVIDER": "openrouter",
        "OPENROUTER_MODEL": "minimax/minimax-m3:free",
        "role": "primary (the R411 campaign's operative attacker)",
    },
    "glm-5.3-free": {
        "ENGINE_LLM_PROVIDER": "tokenrouter",
        "TOKENROUTER_MODEL": "z-ai/glm-5.3-free",
        "role": ("second instrument ATTEMPT (agreement measurement) — "
                 "live-measured 2026-09-05 on this corpus: "
                 "EmptyContentWithFinish at finish_reason=length on the "
                 "2600-token attack protocol (the same R411-recorded "
                 "transport failure); its INCOMPLETE checkpoint line is "
                 "kept as evidence, never deleted"),
    },
    "glm-4-plus": {
        "ENGINE_LLM_PROVIDER": "zai",
        "ZAI_MODEL": "glm-4-plus",
        "role": ("second instrument (agreement measurement; the R411 "
                 "campaign's GENERATOR model measured as attacker — "
                 "also the generator-family cross-check); sandbox-local "
                 "gateway managed as a child process per invocation"),
    },
}

DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_PACE_SECONDS = 2.0


# ---------------------------------------------------------------------------
# zai gateway lifecycle (the glm-4-plus pass needs the sandbox-local
# gateway up; r401's _start_gateway pattern, self-contained here because
# the R411 campaign's helper module was never committed — recorded as an
# R411 loose end in the R412 worklog)
# ---------------------------------------------------------------------------

GATEWAY_PORT = 8787
GATEWAY_HEALTH_URL = f"http://127.0.0.1:{GATEWAY_PORT}/healthz"


def _gateway_alive() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(GATEWAY_HEALTH_URL, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


class _ZaiGateway:
    """Start scripts/zai_gateway.mjs as a child process; terminate on
    exit (the sandbox reaps orphans — the R411 discipline: the gateway
    is managed per invocation, never left running)."""

    def __init__(self) -> None:
        self.proc = None

    def __enter__(self):
        import subprocess
        from discovery_fabric.engine.adapters import load_credentials
        load_credentials()
        key = os.environ.get("ZAI_API_KEY", "")
        if not key:
            raise RuntimeError("ZAI_API_KEY missing: the glm-4-plus "
                               "pass needs the local gateway credential")
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
            self.proc = None
        return False


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_corpus() -> Dict[str, Any]:
    return json.loads(CORPUS_PATH.read_text())


def _pass_state_path(pass_id: str) -> Path:
    return RUNS_DIR / f"{pass_id}.jsonl"


def _read_pass_lines(pass_id: str) -> List[Dict[str, Any]]:
    p = _pass_state_path(pass_id)
    if not p.exists():
        return []
    lines = []
    for raw in p.read_text().splitlines():
        raw = raw.strip()
        if raw:
            lines.append(json.loads(raw))
    return lines


def _latest_attempt(lines: List[Dict[str, Any]],
                    case_id: str) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    for ln in lines:
        if ln.get("case_id") == case_id:
            if best is None or ln.get("attempt", 0) >= best.get(
                    "attempt", 0):
                best = ln
    return best


def _pending_cases(cases: List[Dict[str, Any]], lines: List[Dict[str, Any]],
                   max_attempts: int) -> List[Dict[str, Any]]:
    """Cases to attack this invocation: never-attended cases first
    (corpus order), then INCOMPLETE cases still under the retry
    budget. Decisive (KILLED/SURVIVED) and budget-exhausted cases are
    NOT re-run: the record is append-only."""
    pending: List[Dict[str, Any]] = []
    for case in cases:
        last = _latest_attempt(lines, case["case_id"])
        if last is None:
            pending.append(case)
        elif outcome_of(last.get("attack") or {}) == "INCOMPLETE" and (
                last.get("attempt", 1) < max_attempts):
            pending.append(case)
    return pending


def _attack_one(case: Dict[str, Any]) -> Dict[str, Any]:
    """Run the R411 attack instrument on one sealed case, exactly as
    the campaign invoked it (no instrument changes)."""
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.r411.attack import attack_candidate
    return attack_candidate(
        case["candidate"], case["pool"], case["prior_art"],
        generator_provider=None)  # the corpus is deterministically
        # authored: there is no generator to separate from; the
        # independence_mode in the returned record stays as the
        # instrument computed it (SEPARATE_CONTEXT, honestly labelled
        # by the instrument itself)


def run_pass(pass_id: str, limit: Optional[int] = None,
             max_attempts: int = DEFAULT_MAX_ATTEMPTS,
             pace_seconds: float = DEFAULT_PACE_SECONDS,
             attack_fn: Optional[Callable[[Dict], Dict]] = None
             ) -> Dict[str, Any]:
    """Run or extend one attacker pass. Returns the pass summary.
    attack_fn is injectable for hermetic tests (defaults to the live
    instrument)."""
    if pass_id not in PASS_REGISTRY:
        raise SystemExit(f"unknown pass id: {pass_id} (known: "
                         f"{sorted(PASS_REGISTRY)})")
    pre = preflight(CORPUS_PATH, SEAL_PATH)
    if not pre["ok"]:
        return {
            "pass_id": pass_id,
            "status": "PREFLIGHT_FAILED",
            "preflight": pre,
            "note": "no attack was run (mutated corpus refuses "
                    "measurement, Art. VIII)",
        }

    corpus = _load_corpus()
    cases = corpus["cases"]

    # pin the pass environment BEFORE any call (pins are recorded in
    # every call's meta by the registry — never silent)
    pins = PASS_REGISTRY[pass_id]
    env_pins = {k: v for k, v in pins.items() if k != "role"}
    saved_env = {k: os.environ.get(k, "") for k in env_pins}
    for k, v in env_pins.items():
        os.environ[k] = v
    gateway = _ZaiGateway() if pass_id == "glm-4-plus" else None
    try:
        if gateway is not None:
            gateway.__enter__()
        lines = _read_pass_lines(pass_id)
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        state_path = _pass_state_path(pass_id)
        pending = _pending_cases(cases, lines, max_attempts)
        if limit is not None:
            pending = pending[:limit]
        attack = attack_fn or _attack_one
        n_new = 0
        for case in pending:
            last = _latest_attempt(lines, case["case_id"])
            attempt = (last.get("attempt", 0) + 1) if last else 1
            record = {
                "pass_id": pass_id,
                "case_id": case["case_id"],
                "label": case["ground_truth"]["label"],
                "expected_final": case["ground_truth"]["expected_final"],
                "attempt": attempt,
                "ts": _utcnow(),
                "attack": attack(case),
            }
            with state_path.open("a") as f:
                f.write(json.dumps(record) + "\n")
            lines.append(record)
            n_new += 1
            if pace_seconds > 0:
                time.sleep(pace_seconds)
    finally:
        if gateway is not None:
            gateway.__exit__(None, None, None)
        # restore prior values exactly (never leak pins between passes)
        for k, v in saved_env.items():
            if v:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    return _pass_summary(pass_id, corpus)


def _pass_summary(pass_id: str, corpus: Dict[str, Any]) -> Dict[str, Any]:
    """Collapse one pass's JSONL into per-case latest-attempt results
    and compute the metrics + threshold verdict."""
    lines = _read_pass_lines(pass_id)
    pins = PASS_REGISTRY[pass_id]
    results: List[Dict[str, Any]] = []
    attempts_by_case: Dict[str, int] = {}
    for case in corpus["cases"]:
        last = _latest_attempt(lines, case["case_id"])
        if last is None:
            continue
        attempts_by_case[case["case_id"]] = last.get("attempt", 1)
        results.append({
            "case_id": case["case_id"],
            "label": case["ground_truth"]["label"],
            "expected_final": case["ground_truth"]["expected_final"],
            "attack": last.get("attack") or {},
        })
    metrics = pass_metrics(results, corpus["cases"])
    seal = json.loads(SEAL_PATH.read_text())
    verdict = verdict_vs_thresholds(
        metrics, seal["pre_registered_thresholds"])
    deaths = all_deaths_structured(
        metrics["per_case"], corpus["cases"], results)
    n_attempted = len(lines)
    return {
        "pass_id": pass_id,
        "role": pins.get("role", ""),
        "env_pins": {k: v for k, v in pins.items() if k != "role"},
        "n_cases_in_corpus": corpus["n_cases"],
        "n_cases_attacked": len(results),
        "n_attack_invocations": n_attempted,
        "attempts_by_case": attempts_by_case,
        "metrics": metrics,
        "threshold_verdict": verdict,
        "structured_deaths": deaths,
        "reviewer_provenance": "AI_REVIEW",
    }


def build_report(pass_ids: List[str]) -> Dict[str, Any]:
    """Merge passes into the final measurement record. Passes missing
    data are reported as MISSING (honest), never skipped silently."""
    corpus = _load_corpus()
    seal = json.loads(SEAL_PATH.read_text())
    pre = preflight(CORPUS_PATH, SEAL_PATH)
    passes: List[Dict[str, Any]] = []
    pairwise: List[Dict[str, Any]] = []
    summaries: Dict[str, Dict[str, Any]] = {}
    for pid in pass_ids:
        if not _pass_state_path(pid).exists():
            passes.append({
                "pass_id": pid, "status": "MISSING",
                "role": PASS_REGISTRY.get(pid, {}).get("role", ""),
            })
            continue
        summary = _pass_summary(pid, corpus)
        summaries[pid] = summary
        passes.append(summary)
    for i, a in enumerate(pass_ids):
        for b in pass_ids[i + 1:]:
            if a in summaries and b in summaries:
                res_a = _pass_results(a, corpus)
                res_b = _pass_results(b, corpus)
                pairwise.append({
                    "pass_a": a, "pass_b": b,
                    **agreement(res_a, res_b)})
    primary = next(
        (p for p in passes if p.get("role", "").startswith("primary")),
        None)
    calibrated = None
    if primary and "threshold_verdict" in primary:
        calibrated = primary["threshold_verdict"]["calibrated"]
    return {
        "artifact_type": "R412_ATTACKER_CALIBRATION_MEASUREMENT",
        "run_id": "r412:attacker-calibration-v1",
        "created_in": "R412",
        "created_at": _utcnow(),
        "reviewer_provenance": "AI_REVIEW",
        "corpus_id": corpus["corpus_id"],
        "corpus_sha256": pre["corpus_sha256"],
        "seal_sha256": pre["seal_sha256"],
        "instrument": {
            "attack_module": "discovery_fabric/r411/attack.py",
            "attack_version": "R411-ATTACK-V1",
            "instrument_modified_for_measurement": False,
            "note": ("the instrument is measured EXACTLY as it ran the "
                     "R411 campaign (Art. LIX: no tuning against the "
                     "frozen corpus); attacker model selection is a "
                     "recorded instrument choice made BEFORE any future "
                     "campaign, enabled by — not derived from silently "
                     "— this measurement"),
        },
        "generator_note": (
            "the corpus is deterministically authored (no LLM "
            "generated it), so there is no generator to separate the "
            "attacker from; each pass pins one attacker "
            "provider/model via the same operator-pin mechanism the "
            "campaign used, recorded in env_pins and in every call's "
            "meta"),
        "pre_registered_thresholds": seal["pre_registered_thresholds"],
        "passes": passes,
        "agreement_between_passes": pairwise,
        "calibrated": calibrated,
        "calibration_verdict": (
            "CALIBRATED" if calibrated is True
            else "NOT_CALIBRATED" if calibrated is False
            else "NOT_MEASURED (primary pass missing)"),
        "honest_notes": [
            "coverage counts transport-completed attacks (Art. LXI: "
            "INCOMPLETE is never a verdict)",
            "threshold-comparison metrics use the sealed full "
            "denominators (TPR=killed/30, FPR=false-killed/10); "
            "conditional variants are diagnostics",
            "agreement is measured on parallel single attackers; NO "
            "majority-vote ensemble is formed (R412 directive)",
            "every verdict in this record is AI_REVIEW (Art. LXVII): "
            "the corpus authoring and the attack runs are both "
            "machine work; human review remains unperformed and "
            "unclaimed",
        ],
    }


def _pass_results(pass_id: str,
                  corpus: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines = _read_pass_lines(pass_id)
    results = []
    for case in corpus["cases"]:
        last = _latest_attempt(lines, case["case_id"])
        if last is None:
            continue
        results.append({
            "case_id": case["case_id"],
            "label": case["ground_truth"]["label"],
            "expected_final": case["ground_truth"]["expected_final"],
            "attack": last.get("attack") or {},
        })
    return results


def main(argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pass", dest="pass_id",
                    help="pass id from the registry")
    ap.add_argument("--report", action="store_true",
                    help="merge passes into the measurement record")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--passes",
                    default="minimax-m3,glm-5.3-free,glm-4-plus",
                    help="pass ids included in the report")
    args = ap.parse_args(argv)

    if args.report:
        report = build_report([p.strip() for p in
                               args.passes.split(",") if p.strip()])
        MEASUREMENT_PATH.write_text(json.dumps(report, indent=1))
        print(f"measurement written: {MEASUREMENT_PATH}")
        print("calibration verdict:", report["calibration_verdict"])
        for p in report["passes"]:
            if p.get("status") == "MISSING":
                print(f"  pass {p['pass_id']}: MISSING")
                continue
            m = p["metrics"]
            v = p["threshold_verdict"]
            print(f"  pass {p['pass_id']} ({p.get('role','')}): "
                  f"TPR={m['confusion']['positives']['TPR']} "
                  f"FPR={m['confusion']['negatives']['FPR']} "
                  f"coverage={m['coverage']} "
                  f"parse={m['parse_completeness']} "
                  f"-> {v['verdict']}")
        for pair in report["agreement_between_passes"]:
            print(f"  agreement {pair['pass_a']} vs {pair['pass_b']}: "
                  f"{pair['agreement_rate']} "
                  f"({pair['n_agree']}/{pair['n_cases_both_decisive']})")
        return 0

    if not args.pass_id:
        ap.error("either --pass <id> or --report is required")
    summary = run_pass(args.pass_id, limit=args.limit)
    if summary.get("status") == "PREFLIGHT_FAILED":
        print("PREFLIGHT FAILED — corpus mutated, refusing to attack:")
        for prob in summary["preflight"]["problems"]:
            print(f"  - {prob}")
        return 2
    m = summary["metrics"]
    v = summary["threshold_verdict"]
    print(f"pass {args.pass_id}: attacked {m['n']}/"
          f"{summary['n_cases_in_corpus']} cases "
          f"({summary['n_attack_invocations']} invocations)")
    print(f"  TPR={m['confusion']['positives']['TPR']} "
          f"FPR={m['confusion']['negatives']['FPR']} "
          f"coverage={m['coverage']} "
          f"parse_completeness={m['parse_completeness']}")
    print(f"  false kills on KNOWN_GOOD: {m['false_kills']}")
    print(f"  -> {v['verdict']} {v['checks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
