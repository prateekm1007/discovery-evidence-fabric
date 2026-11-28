#!/usr/bin/env python3
"""r38_deepseek_qualification.py — R-JUDGE execution (AM34/35 §3,
claim c-0043): fresh qualification of the RETIRED judge rung
crowllm/deepseek-v4-flash:free under the v3 axis suffix.

The auditor's ruling grants this as an auditor act: "I authorise a
fresh calibration of the deepseek rung under the v3 axis suffix:
>=0.8 on the gold corpus makes it an ELIGIBLE judge rung and c-0026
may run on it; below 0.8 it stays retired."

Protocol (the standing re-qualification bar, precedent
scripts/r11_crowllm_requalification.py, measured transport
resilience from scripts/crowllm_calibration_v2.py):
  stage 1  capability probe — tiny call through the engine transport;
  stage 2  full-length gate — a REAL packet rubric prompt under the
           v3 axis suffix must return complete valid rubric JSON;
  stage 3  gold calibration — the engine's own run_judge_calibration
           (30 pairs, scoring semantics BYTE-EXACT, a failed pair
           counts WRONG per Art. XXV); >= 0.8 => ELIGIBLE.

No generator calls; no silent swap: the pre-registered c-0026 judge
(qwen-3.8-max:free) is untouched — this rung only becomes a SECOND
eligible rung the auditor's ruling authorises c-0026 to run on.
"""
import datetime
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")
os.environ.setdefault(
    "ZAI_GATEWAY_LOG",
    str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))

import eval.run as er  # noqa: E402
from eval.run import (  # noqa: E402
    _judge_judgment_call, _transport_call, run_judge_calibration)

ROUT = ("crowllm", "deepseek-v4-flash:free")
PACE_S = 8.0
RETRY_PAUSE_S = 25.0
DRIVER_TRIES = 3
OUT = REPO / "eval" / "deepseek_rung_qualification_r38.json"
LOG = REPO / "ENGINE_RUNS" / "r38_deepseek_qualification.log"

# the v3 suffix (byte-identical source to the r29 harness's)
V3_SUFFIX = (REPO / "scripts" / "_r29_axis_suffix_v3.txt").read_text()
V2_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
SUFFIX_MARKER = "=== PER-AXIS SCORING CONTRACT"


def _log(msg):
    line = f"[{datetime.datetime.now(datetime.UTC).isoformat()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _paced_judge_call(provider, model, prompt, **kw):
    """The crowllm_calibration_v2 paced wrapper: transport failures
    retry on the driver ladder; a failure NEVER becomes a verdict."""
    time.sleep(PACE_S)
    for try_i in range(1, DRIVER_TRIES + 1):
        rec = _judge_judgment_call(provider, model, prompt, **kw)
        if rec.get("outcome") != "JUDGE_TRANSPORT_FAILED":
            return rec
        if try_i < DRIVER_TRIES:
            err = str((rec.get("errors") or [""])[0])[:80]
            _log(f"    [pace-retry] try {try_i} transport fail ({err}) "
                 f"— pause {RETRY_PAUSE_S}s")
            time.sleep(RETRY_PAUSE_S)
    return rec


def _full_length_prompt():
    """A REAL packet rubric prompt under the v3 axis suffix — the same
    byte discipline as the r29 harness (_v3_prompt): pre-suffix prefix
    byte-identical to the packet prompt."""
    packet = json.loads((REPO / "eval" / "r27_judge_packet.json")
                        .read_text(encoding="utf-8"))
    row = packet["rows"][0]
    rp = row["rubric_prompt"]
    assert rp.endswith(V2_SUFFIX), "packet prompt v2 suffix missing"
    return row["problem_id"], rp[: -len(V2_SUFFIX)] + V3_SUFFIX


def main() -> int:
    out = {
        "record": "DEEPSEEK_RUNG_QUALIFICATION_R38/1.0.0",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "claim": "c-0043 (builder-r20s2, base f85d0dbbf)",
        "authorization": ("R-JUDGE (AM34/35 §3): fresh calibration of "
                          "the RETIRED deepseek-v4-flash:free rung "
                          "under the v3 axis suffix; >=0.8 gold makes "
                          "it ELIGIBLE; below 0.8 it stays retired"),
        "route": {"provider": ROUT[0], "model": ROUT[1]},
        "stages": {},
    }
    # ---- stage 1: capability probe
    t0 = time.time()
    r = _transport_call(ROUT[0], ROUT[1], "Reply with exactly: OK",
                        "You are a servability probe. English only.",
                        max_tokens=20)
    s1 = {"tiny_status": r.get("status"),
          "content_chars": len(str(r.get("content") or "")),
          "error": (r.get("error") or "")[:160],
          "latency_s": round(time.time() - t0, 1)}
    out["stages"]["1_capability_probe"] = s1
    _log(f"[stage1] {s1}")
    if r.get("status") != "OK" or not str(r.get("content") or "").strip():
        out["verdict"] = "NOT_SERVABLE this window — rung stays retired"
        out["gate"] = "FAIL"
        OUT.write_text(json.dumps(out, indent=1, default=str) + "\n",
                       encoding="utf-8")
        print(json.dumps(out, indent=1, default=str)[:400])
        return 2

    # ---- stage 2: full-length gate under the v3 axis suffix
    pid, prompt = _full_length_prompt()
    er._judge_judgment_call = _paced_judge_call  # paced for stage 2
    t0 = time.time()
    jc = _paced_judge_call(ROUT[0], ROUT[1], prompt, max_tokens=4000)
    s2 = {"problem_id": pid,
          "prompt_chars": len(prompt),
          "axis_suffix": "v3 (calibrated F pins)",
          "outcome": jc.get("outcome"),
          "valid_rubric_json": bool(jc.get("valid")),
          "latency_s": round(time.time() - t0, 1)}
    out["stages"]["2_full_length_gate_v3"] = s2
    _log(f"[stage2] {s2}")
    if not jc.get("valid"):
        out["verdict"] = ("full-length gate FAILED under v3 — rung "
                          "stays retired")
        out["gate"] = "FAIL"
        OUT.write_text(json.dumps(out, indent=1, default=str) + "\n",
                       encoding="utf-8")
        print(json.dumps(out, indent=1, default=str)[:400])
        return 2

    # ---- stage 3: the engine's own 30-pair gold calibration
    t0 = time.time()
    res = run_judge_calibration({"provider": ROUT[0], "model": ROUT[1]})
    wall = round(time.time() - t0, 1)
    s3 = {k: res.get(k) for k in (
        "calibrated", "passed", "n_pairs", "n_valid", "correct",
        "accuracy", "threshold", "answered_rate", "error_classes")}
    s3["wall_s"] = wall
    out["stages"]["3_gold_calibration_engine"] = s3
    _log(f"[stage3] accuracy={s3['accuracy']} correct={s3['correct']}"
         f"/{s3['n_pairs']} valid={s3['n_valid']} wall={wall}s")

    acc = s3.get("accuracy")
    n_pairs = s3.get("n_pairs") or 0
    n_valid = s3.get("n_valid") or 0
    answered = (n_valid / n_pairs) if n_pairs else 0.0
    out["stages"]["3_gold_calibration_engine"]["answered_share"] = \
        round(answered, 3)
    # R38 lesson (the D4 pin, applied): a TRANSPORT-degraded gold run
    # must never type a capability retirement — pairs that exhaust the
    # ladder count WRONG per Art. XXV, so a flapping pool tanks the
    # accuracy for availability reasons. Eligibility needs BOTH the
    # bar met AND a healthy answered share; otherwise the typed
    # verdict is INCONCLUSIVE_TRANSPORT (retry later, rung NOT retired).
    if isinstance(acc, (int, float)) and acc >= 0.8 and answered >= 0.9:
        out["gate"] = "PASS"
        out["verdict"] = ("ELIGIBLE judge rung — c-0026 may run on it "
                          "(auditor act R-JUDGE)")
    elif answered < 0.9:
        out["gate"] = "INCONCLUSIVE_TRANSPORT"
        out["verdict"] = ("TRANSPORT-DEGRADED gold run (answered "
                          f"{n_valid}/{n_pairs}) — INCONCLUSIVE, not a "
                          "capability retirement; retry when the pool "
                          "stabilizes; the rung's retired status is "
                          "unchanged but this record is NOT the "
                          "retirement evidence")
    else:
        out["gate"] = "FAIL"
        out["verdict"] = ("BELOW 0.8 on healthy transport — the rung "
                          "STAYS RETIRED (typed; no silent swap; the "
                          "pre-registered qwen route remains the judge)")
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n",
                   encoding="utf-8")
    print(json.dumps(out, indent=1, default=str)[:600])
    return 0 if eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
