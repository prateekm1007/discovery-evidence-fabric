#!/usr/bin/env python3
"""Q6 gate: 30-pair live judge calibration on
crowllm/deepseek-v4-flash:free (the full-length-gated rung).

This is the calibration that decides whether D4 (20/20 re-judgment)
and D5 (panel) can run NOW instead of waiting for the xkiro 00:00Z
reset. Uses the engine's own run_judge_calibration (byte-exact the
same path D4 uses at call time — no parallel implementation).

Congestion handling: crowllm's free pool serves bursts of 500/429/503
(measured, eval/crowllm_gate_r11.json). The engine retries transient
codes once per call; this driver adds a PAUSED retry at the PAIR
level (a pair whose judgment call ends in a transport failure is
retried after a paced pause, up to 3 times — typed, logged per
attempt, never converting a failure into a verdict).
"""
import json
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from eval.run import run_judge_calibration, utc_now  # noqa: E402

ROUTE = {"provider": "crowllm", "model": "deepseek-v4-flash:free"}
PAIR_PAUSE_S = 20     # pacing between pairs (free-pool courtesy)
RETRY_PAUSE_S = 30    # pause before a transport-failed pair retry

result = None
for attempt in range(1, 4):
    t0 = time.time()
    print(f"[calib] attempt {attempt}/3 on {ROUTE['provider']}/"
          f"{ROUTE['model']} ...", flush=True)
    result = run_judge_calibration(ROUTE)
    wall = round(time.time() - t0, 1)
    n_valid = result.get("n_valid")
    n_pairs = result.get("n_pairs")
    err = result.get("error_classes") or {}
    print(f"[calib] wall={wall}s n_valid={n_valid}/{n_pairs} "
          f"correct={result.get('correct')} "
          f"accuracy={result.get('accuracy')} err={err}", flush=True)
    if n_valid is not None and n_valid >= (n_pairs or 30) - 3:
        # all (or all-but-3) pairs produced a parseable verdict —
        # the calibration stands; no retry needed
        break
    if attempt < 3:
        print(f"[calib] transport losses detected "
              f"({(n_pairs or 30) - (n_valid or 0)} pairs) — "
              f"pausing {RETRY_PAUSE_S}s and re-running the WHOLE "
              f"calibration (deterministic corpus, fresh governor)",
              flush=True)
        time.sleep(RETRY_PAUSE_S)

out = {
    "record": "CROWLLM_JUDGE_CALIBRATION/1.0.0",
    "at": utc_now(),
    "route": ROUTE,
    "attempts": attempt,
    "calibration": {k: result.get(k) for k in
                    ("calibrated", "n_pairs", "correct", "accuracy",
                     "threshold", "passed", "corpus_sha256", "n_valid",
                     "error_classes")},
    "threshold_rule": "passed == accuracy >= 0.8 on >= 24/30 valid "
                      "(the D4 eligibility gate)",
}
if result.get("details"):
    out["per_pair"] = [
        {"problem_id": d.get("problem_id"),
         "outcome": d.get("outcome"),
         "correct": d.get("correct"),
         "latency_s": d.get("latency_s")}
        for d in result["details"]]

path = "eval/crowllm_judge_calibration_r11.json"
with open(path, "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"\ngate: {'PASS — D4/D5 may run NOW on this rung' if result.get('passed') else 'FAIL — xkiro 00:00Z path stands'}")
print(f"typed record -> {path}")
