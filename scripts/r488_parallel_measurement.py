#!/usr/bin/env python3
"""scripts/r488_parallel_measurement.py — R488: the R487 committed
measurement driver, with ONE delta: shard-safe parallel case execution.

Why this exists (both disclosed in R488/R488_ROUND_RECORD.json):
  1. The execution sandbox kills every background process when a shell
     call ends (two detached attempts died silently mid-attack: nohup
     pid 1275, setsid pid 1773 — no traceback, log ends mid-attack).
     Foreground execution inside one tool call survives; the observed
     single-attack latency is ~440s (R488 latency probe), so one call
     fits one WAVE of concurrent attacks (4 workers x ~440s < 600s
     tool ceiling). Sequential foreground would need 22 calls / ~2.75h;
     waves of 4 need 6 calls / ~50 min.
  2. The committed driver's loop is strictly sequential; this variant
     parallelizes ONLY the orchestration. The request function, the
     response shape, the RAW marker format, the freeze/identity gates,
     and the ENTIRE scoring path (frozen.score_all + write_measurement)
     are the committed R487 module's own code, imported unmodified —
     zero fork of any metric, threshold, or verdict rule.

Atomicity: each worker writes its RAW marker via temp file + os.replace
(so a killed wave can never leave a torn marker); resume skips cases
whose marker already exists. Same RAW dir, same marker names, same
response bodies as the committed driver -> load_raw()/score_all()
cannot tell the difference.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r487_attacker_v3_measurement as r487  # the committed module

CORPUS = json.loads(r487.CORPUS_PATH.read_text())
RAW_DIR = r487.RAW_DIR
WAVE = int(os.environ.get("R488_WAVE", "4"))


def _log(msg: str) -> None:
    print(f"[r488-wave] {msg}", flush=True)


def attack_one(case: dict, problem: dict) -> str:
    """One case through the COMMITTED request path; returns status."""
    marker = RAW_DIR / f"{case['case_id']}.json"
    if marker.exists():
        return "exists"
    t0 = time.time()
    r = r487._req("/api/ops/calibration-attack", body={
        "candidate": case["candidate"],
        "problem": problem,
        "evidence": case.get("evidence_items") or [],
    })
    if r.get("http_status") != 200:
        _log(f"{case['case_id']}: TRANSPORT FAILURE "
             f"{r.get('http_status')} {str(r.get('error'))[:140]}")
        return "transport_failure"
    tmp = marker.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(r.get("body"), indent=1, default=str))
    os.replace(tmp, marker)  # atomic: no torn markers, ever
    a = (r.get("body") or {}).get("attack") or {}
    _log(f"{case['case_id']}: {a.get('overall')} "
         f"({time.time() - t0:.0f}s, {a.get('attacker_model')})")
    return "attacked"


def main() -> int:
    freeze = r487._freeze_check()
    if not freeze["freeze_ok"]:
        _log("FATAL: corpus not byte-identical to the frozen record")
        return 2
    v = r487._req("/api/version", timeout=60)
    served = ((v.get("body") or {}).get("engine_commit") or "")
    expected = os.environ.get("EXPECTED_IDENTITY", "")
    _log(f"production serves {served[:12]}")
    if expected and served != expected:
        _log("FATAL: identity gate")
        return 2
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    problem = CORPUS["the_common_problem"]
    todo = [c for c in CORPUS["cases"]
            if not (RAW_DIR / f"{c['case_id']}.json").exists()]
    _log(f"{len(todo)} cases remain "
         f"({len(CORPUS['cases']) - len(todo)} markers present)")
    if not todo:
        _log("nothing to attack — scoring pass only")
    else:
        batch = todo[:WAVE]
        threads, results = [], {}
        def run(case):
            try:
                results[case["case_id"]] = attack_one(case, problem)
            except Exception as exc:  # noqa: BLE001 — typed per case
                results[case["case_id"]] = f"error:{type(exc).__name__}"
                _log(f"{case['case_id']}: ERROR {type(exc).__name__}")
        for c in batch:
            th = threading.Thread(target=run, args=(c,))
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
        _log(f"wave done: {results}")

    # scoring pass — the COMMITTED module's own code, unmodified
    raw = r487.load_raw()
    results = r487.frozen.score_all(CORPUS, raw)
    results["report_version"] = "r487-attacker-v3-measurement/1.0.0"
    results["freeze_check"] = r487._freeze_check()
    results["instrument"] = ("independent_attack/3.0.0 (the anchor + "
                             "accommodation discipline)")
    r487.OUT_DIR.mkdir(parents=True, exist_ok=True)
    r487.RESULTS_PATH.write_text(json.dumps(results, indent=1,
                                            default=str))
    meas = r487.write_measurement(results)
    hc = results["headline_confusion"]
    _log(f"interim score: attacked {meas['n_cases_attacked']}/"
         f"{len(CORPUS['cases'])} | TPR {hc['TPR']} | FPR {hc['FPR']} "
         f"| coverage {results['coverage']} | parse "
         f"{results['parse_completeness']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
