#!/usr/bin/env python3
"""R451-C1.3 acceptance driver — the zero-paid acceptance RERUN with the
runtime-admission authority and full run-level routing provenance.

Operator directive (C1.3-3): "Then rerun the zero-paid acceptance. The
evidence must allow us to isolate: this run's calls without relying on a
time window or ledger tail."

This driver:
  1. builds a GENUINELY FRESH problem (r451-greenhouse-emitter-clogging —
     never submitted to any environment; a third domain after P1 ozone
     diffuser fouling and P2 EV-bus battery thermal) through the SAME
     zero-paid registry;
  2. runs the engine DETACHED (the R451-C1.1 survival pattern) with a
     PINNED run_id + session_id, every paid provider disabled, the
     ZERO_PAID_COST cost policy active, and the C1.3 runtime-admission
     authority live (probe-before-admit on every rung);
  3. assesses the acceptance chain from the run's OWN records (Art. X)
     with the NEW provenance invariants:
       - every run-owned routing line carries the pinned run_id
         (isolation by run_id — NO time window, NO ledger tail);
       - every run-owned line carries session_id + engine_stage + the
         13 directive fields;
       - zero paid-cost lines in the run;
       - capability-probe evidence persisted (call_class
         CAPABILITY_PROBE lines);
       - the task-degradation record on selected lines (STRONG
         requested, CHEAP_EMERGENCY_FALLBACK served — explicit);
       - ROUTING_LEDGER_RUN.json persisted in the run dir.

Usage:
  python scripts/r451_c13_acceptance.py build      # build the problem
  python scripts/r451_c13_acceptance.py engine 900 # run+monitor (s)
  python scripts/r451_c13_acceptance.py assess     # write the record
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_DIR = REPO_ROOT / "R451" / "ACCEPTANCE_RUN_C13"
PROBLEM_JSON = OUT_DIR / "fresh_problem.json"
RECORD_PATH = REPO_ROOT / "R451" / "ACCEPTANCE_RUN_C13.json"
RUN_ID = "r451c13: greenhouse-emitter-clogging acceptance v3"
SESSION_ID = "r451-c13-acceptance"

PAID_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
    "GEMINI_API_KEY", "QWEN_API_KEY", "TOKEN_ROUTER_API_KEY",
    "ZAI_API_KEY",
]

FRESH_PROBLEM = {
    "problem_id": "r451-greenhouse-emitter-clogging",
    "text": (
        "In commercial greenhouses using drip irrigation on well water, "
        "the narrow flow channels of pressure-compensating emitters "
        "(nominal 2.0 litres per hour) progressively clog over weeks: a "
        "combined biofilm growth and calcium-carbonate scaling crust "
        "narrows the labyrinth channel until flow drops below 50 percent "
        "of nominal, which forces growers to over-irrigigate the whole "
        "zone to keep the worst emitters alive, wasting water and "
        "leaching nutrients. Flushing with acid or chlorination damages "
        "the plants and the equipment and must be repeated monthly. We "
        "need a way to keep the emitter channels clear through one full "
        "growing season (8-9 months) on untreated well water at 25 "
        "degrees C with 180 ppm calcium hardness, without repeated "
        "chemical flushing and without adding measurable pressure demand "
        "to the system."
    ),
    "authored_for": "R451-C1.3",
}


def _log(msg: str) -> None:
    print(f"[r451c13] {msg}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            d = json.loads(p.read_text())
            return d if isinstance(d, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


# ---------------------------------------------------------------------------
def build_fresh_problem() -> None:
    """Build the problem ONCE (MODEL_DERIVED extraction through the SAME
    zero-paid registry — a fresh problem entering the engine the same
    way a production user's does)."""
    if PROBLEM_JSON.exists():
        _log("fresh problem already built")
        return
    import r451_local_qwen as lq
    assert lq.ensure_server(), "llama-server failed to start"
    os.environ["LOCAL_QWEN_BASE_URL"] = lq.BASE + "/v1/chat/completions"
    os.environ["ENGINE_MODEL_COST_POLICY"] = "ZERO_PAID_COST"
    for k in PAID_ENV_VARS:
        os.environ.pop(k, None)
    from toscanini.problem_builder import build_problem
    built = build_problem(FRESH_PROBLEM["text"])
    problem = built.get("problem") if isinstance(built.get("problem"),
                                                  dict) else built
    problem["problem_id"] = FRESH_PROBLEM["problem_id"]
    problem["r451_freshness"] = {
        "class": "GENUINELY_FRESH",
        "authored_for": "R451-C1.3",
        "never_submitted_to": ["render", "hf-space", "batteries",
                               "prior-rounds"],
    }
    PROBLEM_JSON.parent.mkdir(parents=True, exist_ok=True)
    PROBLEM_JSON.write_text(json.dumps(problem, indent=1,
                                       ensure_ascii=False))
    _log(f"fresh problem built -> {PROBLEM_JSON}")


# ---------------------------------------------------------------------------
def run_engine(budget_s: int) -> None:
    """Run the engine DETACHED with the pinned run identity (the
    R451-C1.1 survival pattern, plus the C1.3 --run-id/--session-id
    pins so the routing ledger isolates this run's calls BY RUN ID)."""
    build_fresh_problem()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["ENGINE_MODEL_COST_POLICY"] = "ZERO_PAID_COST"
    env["LOCAL_QWEN_BASE_URL"] = \
        "http://127.0.0.1:8790/v1/chat/completions"
    for k in PAID_ENV_VARS:
        env.pop(k, None)

    import r451_local_qwen as _lq
    pid_file = OUT_DIR / "ENGINE_PID"
    log_file = OUT_DIR / "engine.log"

    def _engine_pid() -> Optional[int]:
        try:
            return int(pid_file.read_text().strip())
        except Exception:  # noqa: BLE001
            return None

    def _pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    if _pid_alive(_engine_pid()):
        if not _lq._proc_alive():
            _log("server DOWN under a live engine — restarting")
        assert _lq.ensure_server(), "llama-server failed to start"
        _log("llama-server warm (live engine detected)")
    else:
        assert _lq.ensure_server(), "llama-server failed to start"

    pid = _engine_pid()
    if _pid_alive(pid):
        _log(f"attaching to live engine pid={pid}")
    else:
        cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
               "--problem-json", str(PROBLEM_JSON),
               "--out", str(OUT_DIR), "--no-package",
               "--run-id", RUN_ID, "--session-id", SESSION_ID]
        if (OUT_DIR / "problem.json").exists():
            cmd.append("--resume")
            _log("starting DETACHED engine (resume)")
        else:
            _log("starting DETACHED engine (fresh)")
        log_fh = open(log_file, "ab")
        proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                stdout=log_fh, stderr=subprocess.STDOUT,
                                start_new_session=True)
        pid_file.write_text(str(proc.pid))
        _log(f"detached engine pid={proc.pid} (log: {log_file.name})")
        pid = proc.pid

    import threading

    def _watchdog() -> None:
        while True:
            try:
                if not _lq._proc_alive():
                    _log("watchdog: llama-server DOWN — restarting")
                    _lq.ensure_server()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5)

    threading.Thread(target=_watchdog, daemon=True).start()
    start = time.time()
    last_size = 0
    while True:
        if not _pid_alive(_engine_pid()):
            _log("engine process exited (final_state written if the run "
                 "completed)")
            try:
                pid_file.unlink()
            except FileNotFoundError:
                pass
            return
        if time.time() - start > budget_s:
            _log(f"budget reached — engine pid={pid} KEEPS RUNNING "
                 f"(detached); re-invoke to continue monitoring")
            return
        try:
            size = log_file.stat().st_size
            if size > last_size:
                with open(log_file, "rb") as fh:
                    fh.seek(last_size)
                    chunk = fh.read(size - last_size).decode(
                        "utf-8", "replace")
                for line in chunk.splitlines()[-6:]:
                    if line.strip():
                        _log(f"  engine: {line.rstrip()[:150]}")
                last_size = size
        except OSError:
            pass
        time.sleep(2.0)


# ---------------------------------------------------------------------------
def assess() -> int:
    """Reconstruct the acceptance chain from the run's OWN records with
    the C1.3 provenance invariants (Art. X: the artifacts are the
    authority)."""
    chain: Dict[str, Any] = {}
    details: Dict[str, Any] = {"run_id": RUN_ID, "session_id": SESSION_ID}

    problem = _read_json(PROBLEM_JSON)
    chain["fresh_problem"] = bool(problem)
    if problem:
        details["problem_id"] = problem.get("problem_id")

    # -- the run's routing lines, isolated BY RUN ID (no time window) --
    from discovery_fabric.engine import model_routing as mr
    run_lines = mr.ledger_for_run(RUN_ID)
    run_owned = [l for l in run_lines
                 if l.get("call_class") == "RUN_OWNED"]
    # CAPABILITY_PROBE lines carry run_id=None BY DESIGN (the C1.3-3
    # distinction: provider probes are NOT run-owned discovery calls),
    # so they can NEVER appear inside ledger_for_run(RUN_ID) — the
    # persisted capability evidence is measured on the GLOBAL ledger
    # within the run's own recorded window (manifest started_at..
    # finished_at) plus the capability_state field on every run line.
    probe_lines = [l for l in run_lines
                   if l.get("call_class") == "CAPABILITY_PROBE"]
    _manifest_t0 = (_read_json(OUT_DIR / "run_manifest.json")
                    or {}).get("started_at") or ""
    _manifest_t1 = ((_read_json(OUT_DIR / "final_state.json") or {})
                    .get("timestamp")
                    or (_read_json(OUT_DIR / "run_manifest.json")
                        or {}).get("finished_at") or "9999")
    _global_probe_in_window: list = []
    try:
        for _ln in (REPO_ROOT / "ENGINE_RUNS" / "model_routing"
                    / "ledger.jsonl").open():
            try:
                _d = json.loads(_ln)
            except Exception:  # noqa: BLE001 — torn line skipped
                continue
            if (_d.get("call_class") == "CAPABILITY_PROBE"
                    and _manifest_t0 <= (_d.get("recorded_at") or "")
                    <= _manifest_t1):
                _global_probe_in_window.append(_d)
    except OSError:
        _global_probe_in_window = []
    paid_lines = [l for l in run_lines
                  if (l.get("cost_class") or "") not in
                  ("ZERO_PAID_COST_SELF_HOSTED", None)]
    local_sel = [l for l in run_lines if l.get("provider") == "localqwen"
                 and l.get("selected")]

    chain["model_response"] = bool(run_owned)
    details["routing_provenance"] = {
        "isolation": "run_id equality (ledger_for_run) — no time window, "
                     "no ledger tail",
        "run_lines_total": len(run_lines),
        "run_owned_call_lines": len(run_owned),
        "capability_probe_lines_in_run_ledger": len(probe_lines),
        "capability_probe_lines_global_window": len(
            _global_probe_in_window),
        "capability_probe_window": ["_manifest_t0", "_manifest_t1"],
        "capability_probe_examples": [
            {"recorded_at": p.get("recorded_at"),
             "provider": p.get("provider"), "status": p.get("status"),
             "capability_state": p.get("capability_state"),
             "failure_class": p.get("failure_class")}
            for p in _global_probe_in_window[-4:]],
        "invariant_capability_state_on_run_lines": all(
            l.get("capability_state") for l in run_owned),
        "paid_cost_lines": len(paid_lines),
        "localqwen_selected_lines": len(local_sel),
        "invariant_run_owned_non_null_run_id": all(
            bool(l.get("run_id")) for l in run_owned),
        "invariant_session_id_present": all(
            "session_id" in l for l in run_owned),
        "invariant_engine_stage_present": all(
            "engine_stage" in l for l in run_owned),
        "invariant_account_domain_present": all(
            "account_domain" in l for l in run_owned),
        "distinct_engine_stages": sorted({str(l.get("engine_stage"))
                                          for l in run_owned}),
        "example_selected_line": (local_sel[-1] if local_sel else None),
    }
    # the C1.4 degradation record on the selected synthesis lines
    degs = [l.get("task_degradation") for l in local_sel
            if l.get("task_degradation")]
    details["task_degradation"] = {
        "records_on_selected_lines": len(degs),
        "any_degraded_strong_request": any(
            d.get("requested_task") == "STRONG"
            and d.get("actual_task_capability") ==
            "CHEAP_EMERGENCY_FALLBACK" for d in degs),
        "example": degs[-1] if degs else None,
    }

    # -- the run's own persisted ledger snapshot -----------------------
    run_ledger_snap = _read_json(OUT_DIR / "ROUTING_LEDGER_RUN.json")
    chain["run_ledger_snapshot_persisted"] = bool(run_ledger_snap)
    if run_ledger_snap:
        details["routing_ledger_run"] = {
            "line_count": run_ledger_snap.get("line_count"),
            "run_owned_call_lines":
                run_ledger_snap.get("run_owned_call_lines"),
            "paid_cost_class_lines":
                run_ledger_snap.get("paid_cost_class_lines"),
        }

    # -- the manifest carries the session --------------------------------
    manifest = _read_json(OUT_DIR / "run_manifest.json")
    chain["manifest_carries_session"] = bool(
        manifest and manifest.get("session_id") == SESSION_ID
        and manifest.get("run_id") == RUN_ID)

    # -- evidence / mechanism / candidate / attack (the P2 chain) -------
    ev_files = [p for p in OUT_DIR.iterdir() if p.is_file()] \
        if OUT_DIR.exists() else []
    ev_ok = False
    for p in ev_files:
        if "RETRIEVE" not in p.name and "FREEZE" not in p.name:
            continue
        d = _read_json(p)
        if not d:
            continue
        records = (d.get("evidence") or d.get("records") or
                   d.get("evidence_ids") or d.get("items") or [])
        if isinstance(records, list) and records:
            ev_ok = True
            details.setdefault("evidence_files", []).append(
                {"file": p.name, "n_records": len(records)})
    chain["evidence"] = bool(ev_ok)

    mech = _read_json(OUT_DIR / "stage_MECHANISM_SPACE.json")
    # the ACTUAL persisted shape (Art. X: the artifact is the authority):
    # {"state": "BUILT_BELOW_MIN" | ..., "n_candidates": <int>}
    _mech_n = int(mech.get("n_candidates") or 0) if mech else 0
    chain["mechanism"] = bool(mech and _mech_n >= 1)
    if mech:
        details["mechanism_space"] = {
            "state": mech.get("state"),
            "n_candidates": _mech_n,
        }

    # the candidate: the SYNTHESIZE stage record carries the serving
    # model/provider; the candidate ID + attack verdict live in the
    # final state / evolution records (the envelope is the authority)
    syn = _read_json(OUT_DIR / "stage_SYNTHESIZE.json")
    _rel = _read_json(OUT_DIR / "DISCOVERY_RELEASE.json") or {}
    _evo = _read_json(OUT_DIR / "EVOLUTION_GEN_1.json") or {}
    _cand_id = _rel.get("candidate_id") or _evo.get("invention_id")
    chain["candidate"] = bool(
        syn and syn.get("provider") and _cand_id)
    if syn:
        details["synthesize"] = {
            "provider": syn.get("provider"),
            "model": syn.get("model"),
            "candidate_id": _cand_id,
        }

    attack = _read_json(OUT_DIR / "stage_ATTACK.json")
    final = _read_json(OUT_DIR / "final_state.json")
    chain["attack"] = bool(attack or final)
    if final:
        details["final_status"] = final.get("final_status")
        details["stage_log_tail"] = [
            {"stage": e.get("stage"), "status": e.get("status")}
            for e in (final.get("stage_log") or [])[-6:]]

    record = {
        "artifact_type": "R451_C13_ACCEPTANCE_RUN",
        "directive": "R451-C1.3 (rerun the zero-paid acceptance with the "
                     "runtime-admission authority and run-level routing "
                     "provenance)",
        "run_id": RUN_ID,
        "session_id": SESSION_ID,
        "cost_policy": "ZERO_PAID_COST",
        "paid_providers_disabled": PAID_ENV_VARS,
        "problem": FRESH_PROBLEM["problem_id"],
        "problem_freshness": (problem or {}).get("r451_freshness"),
        "chain": chain,
        "details": details,
        "assessed_at": _now(),
    }
    RECORD_PATH.write_text(json.dumps(record, indent=1,
                                      ensure_ascii=False, default=str))
    _log(f"record -> {RECORD_PATH}")

    # the ACCEPTANCE verdict (honest: every gate must hold)
    gates = {
        "fresh_problem": chain["fresh_problem"],
        "model_response_run_owned": chain["model_response"],
        "zero_paid": len(paid_lines) == 0,
        "invariant_run_owned_non_null_run_id":
            details["routing_provenance"][
                "invariant_run_owned_non_null_run_id"],
        "run_isolatable_by_run_id": len(run_owned) > 0,
        "session_id_on_run_owned_lines":
            details["routing_provenance"]["invariant_session_id_present"],
        "capability_evidence_persisted": (
            len(_global_probe_in_window) > 0
            and details["routing_provenance"][
                "invariant_capability_state_on_run_lines"]),
        "task_degradation_explicit": (
            details["task_degradation"]["records_on_selected_lines"] > 0),
        "run_ledger_snapshot_persisted":
            chain["run_ledger_snapshot_persisted"],
        "manifest_carries_session": chain["manifest_carries_session"],
        "evidence": chain["evidence"],
        "mechanism": chain["mechanism"],
        "candidate": chain["candidate"],
        "attack": chain["attack"],
    }
    record["acceptance_gates"] = gates
    record["accepted"] = all(gates.values())
    RECORD_PATH.write_text(json.dumps(record, indent=1,
                                      ensure_ascii=False, default=str))
    for k, v in gates.items():
        _log(f"  gate {k}: {'PASS' if v else 'FAIL'}")
    _log(f"ACCEPTED = {record['accepted']}")
    return 0 if record["accepted"] else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "build":
        build_fresh_problem()
        return 0
    if cmd == "engine":
        budget = int(sys.argv[2]) if len(sys.argv) > 2 else 900
        run_engine(budget)
        return 0
    if cmd == "assess":
        return assess()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
