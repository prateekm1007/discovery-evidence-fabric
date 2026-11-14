#!/usr/bin/env python3
"""Q6 gate v2: 30-pair live judge calibration on
crowllm/deepseek-v4-flash:free — WITH measured transport resilience.

The v1 run (eval/crowllm_judge_calibration_r11.json, kept as the
honest first measurement) failed 0/30 in ~1 s: the free pool's first
burst tripped the 3-consecutive circuit breaker, and every subsequent
pair failed INSTANTLY (BreakerOpen) — including the two whole-calibration
retries, which ran inside the 60 s cooldown. Root cause: the engine's
breaker (threshold 3) is tuned for sustained-outage storms, while
crowllm's free pool serves BURSTS that clear in seconds (measured,
eval/crowllm_gate_r11.json).

This driver keeps run_judge_calibration's scoring semantics
BYTE-EXACT (same corpus, same prompts, same parse) and adds ONLY
transport resilience at the driver layer:
  - FABRIC_BREAKER_THRESHOLD=60 for this process: the driver's own
    per-pair ladder (max 3 tries, 25 s pauses) bounds the request
    count (30 pairs x 2 engine attempts x 3 driver tries = 180
    worst case, ~120 expected); the breaker cannot kill the run
    before the ladder does
  - a paced wrapper around _judge_judgment_call: 8 s courtesy sleep
    before every judgment call + transport-failure retries with 25 s
    pauses (a failure NEVER becomes a verdict — a pair that exhausts
    the ladder keeps its typed JUDGE_TRANSPORT_FAILED outcome)
"""
import json
import os
import sys
import time

os.environ["FABRIC_BREAKER_THRESHOLD"] = "60"  # driver ladder bounds it

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

import eval.run as er  # noqa: E402

_orig_judge_call = er._judge_judgment_call
_PACE_S = 8
_RETRY_PAUSE_S = 25
_DRIVER_TRIES = 3


def _paced_judge_call(provider, model, prompt, **kw):
    time.sleep(_PACE_S)
    for try_i in range(1, _DRIVER_TRIES + 1):
        rec = _orig_judge_call(provider, model, prompt, **kw)
        if rec.get("outcome") != "JUDGE_TRANSPORT_FAILED":
            return rec
        if try_i < _DRIVER_TRIES:
            err = str((rec.get("errors") or [""])[0])[:80]
            print(f"    [pace-retry] try {try_i} transport fail "
                  f"({err}) — pause {_RETRY_PAUSE_S}s", flush=True)
            time.sleep(_RETRY_PAUSE_S)
    return rec


er._judge_judgment_call = _paced_judge_call

ROUTE = {"provider": "crowllm", "model": "deepseek-v4-flash:free"}
t0 = time.time()
print(f"[calib-v2] single full attempt on {ROUTE['provider']}/"
      f"{ROUTE['model']} (paced, driver-laddered)", flush=True)
result = er.run_judge_calibration(ROUTE)
wall = round(time.time() - t0, 1)
n_valid = result.get("n_valid")
n_pairs = result.get("n_pairs")
print(f"[calib-v2] wall={wall}s n_valid={n_valid}/{n_pairs} "
      f"correct={result.get('correct')} accuracy={result.get('accuracy')} "
      f"err={result.get('error_classes')}", flush=True)

out = {
    "record": "CROWLLM_JUDGE_CALIBRATION/1.0.1",
    "at": er.utc_now(),
    "route": ROUTE,
    "wall_s": wall,
    "transport_resilience": {
        "breaker_threshold_this_process": 60,
        "driver_ladder": f"{_DRIVER_TRIES} tries x "
                         f"(engine 1-immediate-retry), "
                         f"{_RETRY_PAUSE_S}s pause between tries, "
                         f"{_PACE_S}s pacing before every call",
        "v1_record": "eval/crowllm_judge_calibration_r11.json "
                     "(0/30 breaker-killed — kept as the honest "
                     "first measurement)",
    },
    "calibration": {k: result.get(k) for k in
                    ("calibrated", "n_pairs", "correct", "accuracy",
                     "threshold", "passed", "corpus_sha256", "n_valid",
                     "error_classes")},
    "threshold_rule": "passed == accuracy >= 0.8 (the D4 eligibility "
                      "gate)",
}
if result.get("details"):
    out["per_pair"] = [
        {"problem_id": d.get("problem_id"),
         "outcome": d.get("outcome"),
         "correct": d.get("correct"),
         "latency_s": d.get("latency_s")}
        for d in result["details"]]

path = "eval/crowllm_judge_calibration_r11_v2.json"
with open(path, "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"\ngate: {'PASS — D4/D5 may run NOW on this rung' if result.get('passed') else 'FAIL — xkiro 00:00Z path stands'}")
print(f"typed record -> {path}")
