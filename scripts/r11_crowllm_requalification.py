#!/usr/bin/env python3
"""crowllm judge re-qualification on the operator-delivered key
(AM8 context: the retirement bar — probe, full-length gate, gold
calibration >= 0.8). The allowlisted rung deepseek-v4-flash:free is
503-dead this window (measured); the pool serves other families.
This script registers nothing — it measures CANDIDATE rungs through
the engine's own judge path and writes the typed record. The
qwen-3.8-max:free and gemini-3-flash:free rungs passed the
full-length gate live (6284-char real judge prompt, complete valid
rubric JSON, ~2 s wall) — this is their gold calibration.
"""
import json
import sys
import time
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from eval.run import run_judge_calibration  # noqa: E402

CANDIDATES = [
    # (provider, model) — judge candidates on crowllm, families
    # distinct from every served generator rung. Generator this
    # window: xkiro/mistral-14b (and zai gateway GLM-5.3 if it
    # serves). qwen-3.8-max (Qwen family) and gemini-3-flash (Gemini
    # family) both passed the full-length gate minutes ago.
    ("crowllm", "qwen-3.8-max:free"),
    ("crowllm", "gemini-3-flash:free"),
]

out = {
    "record": "CROWLLM_REQUALIFICATION_R11_R8/1.0.0",
    "at": datetime.datetime.now(datetime.UTC).isoformat(),
    "context": (
        "AM8 re-qualification bar for the retired crowllm judge role. "
        "The allowlisted rung deepseek-v4-flash:free (and v4.1) are "
        "503-dead this window (measured, 8 spaced probes). The "
        "operator delivered the same key + https://crowllm.com/v1/; "
        "the pool catalog (76 models) serves other families. Stage 1 "
        "probe + Stage 2 full-length gate measured live this window: "
        "qwen-3.8-max:free and gemini-3-flash:free return complete "
        "valid rubric JSON on the real 6284-char judge prompt (~2 s). "
        "Stage 3 (this run): the 30-pair gold calibration through the "
        "engine's own run_judge_calibration — the standing retirement "
        "bar (>= 0.8 accuracy, a failed pair counts WRONG per Art. "
        "XXV)."),
    "stages": {
        "1_capability_probe": {
            "deepseek-v4-flash:free": "FAIL 503 (8 spaced probes)",
            "deepseek-v4.1-flash:free": "FAIL 503",
            "qwen-3.8-max:free": "OK (tiny probe)",
            "gemini-3-flash:free": "OK (tiny probe)",
            "grok-4.7-fast:free": "OK tiny / TIMEOUT full-length",
            "gpt-4o-mini:free": "OK (tiny probe; not gated further)",
        },
        "2_full_length_gate": {
            "qwen-3.8-max:free": "PASS (complete valid rubric JSON, "
                                 "2.0 s wall)",
            "gemini-3-flash:free": "PASS (complete valid rubric JSON, "
                                   "1.9 s wall)",
        },
    },
    "calibrations": {},
}

for prov, model in CANDIDATES:
    print(f"[requal] gold calibration: {prov}/{model}", flush=True)
    t0 = time.time()
    res = run_judge_calibration({"provider": prov, "model": model})
    wall = round(time.time() - t0, 1)
    summary = {k: res.get(k) for k in (
        "calibrated", "passed", "n_pairs", "n_valid", "correct",
        "accuracy", "threshold", "answered_rate", "error_classes")}
    summary["wall_s"] = wall
    out["calibrations"][f"{prov}/{model}"] = summary
    print(f"  accuracy={summary['accuracy']} correct={summary['correct']}"
          f"/{summary['n_pairs']} valid={summary['n_valid']} "
          f"wall={wall}s", flush=True)
    # pacing between candidates (free pool courtesy)
    time.sleep(30)

path = REPO / "eval" / "crowllm_requalification_r11_r8.json"
path.write_text(json.dumps(out, indent=1, default=str) + "\n",
                encoding="utf-8")
print(f"-> {path}")
