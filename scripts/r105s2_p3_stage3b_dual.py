#!/usr/bin/env python3
"""r105s2 P3 stage 3b — the DUAL-INTERVAL arm (the stage-3 tension
resolved; claim c-0125).

THE TENSION (typed, from the stage-3 record): sliding conformal buys
coverage on drift (FD001 0.50->0.887) but the adaptive buffer FOLLOWS
a persistent shift — the CWRU fault detection collapsed (hp0 fault
coverage 0.97 = the fault absorbed into the intervals; the stage-1
fit-once prototype had detection 1.0 but drift coverage 0.50). One
adaptive mechanism cannot serve both requirements.

THE DUAL DESIGN (the classic FA-control structure):
  - the COVERAGE interval: sliding-window conformal (the drift remedy);
  - the ALARM interval: the FIXED healthy-baseline conformal q (never
    updated) with the N_CONSEC=3 counting rule — alarms fire only on
    persistent deviation from HEALTHY, which is what a fault is.

Arms: Chronos-Bolt predictor, 4 paired CWRU files (ground truth:
faulted vs normal). NO acceptance claims — measurements.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
OUT = REPO / "eval" / "r105s2_p3_stage3b_dual_record.json"
CONF = 0.9
CTX = 96
K_SLIDE = 100
N_CONSEC = 3

_s3spec = importlib.util.spec_from_file_location(
    "p3s3", REPO / "scripts" / "r105s2_p3_stage3.py")
p3s3 = importlib.util.module_from_spec(_s3spec)
sys.modules["p3s3"] = p3s3
_s3spec.loader.exec_module(p3s3)
p3s1 = p3s3.p3s1
p3s2 = p3s3.p3s2


def dual_eval(fit_hist: np.ndarray, healthy_walk: np.ndarray,
              fault_series: np.ndarray, predict_batch) -> dict:
    """The coverage interval slides (K=100 causal residuals, fit-half
    primed); the alarm interval is the FIXED fit-half quantile."""
    half = len(fit_hist)
    idx = list(range(CTX, half))
    X = np.stack([fit_hist[i - CTX:i] for i in idx])
    preds = predict_batch(X)
    resid = np.abs(np.asarray(preds) - fit_hist[CTX:half])
    buf = deque(resid[-K_SLIDE:], maxlen=K_SLIDE)
    q_fixed = float(np.quantile(resid, CONF))
    timings = []

    def step_batch(series: np.ndarray, start_q_slide):
        widx = list(range(CTX, len(series)))
        WX = np.stack([series[i - CTX:i] for i in widx])
        t0 = time.perf_counter()
        wpred = predict_batch(WX)
        timings.append((time.perf_counter() - t0) * 1000.0)
        return widx, wpred

    # healthy leg: coverage with the SLIDING q + alarms with FIXED q
    for label, series in [("healthy", healthy_walk),
                          ("fault", fault_series)]:
        widx, wpred = step_batch(series, None)
        buf2 = deque(resid[-K_SLIDE:], maxlen=K_SLIDE)
        cover = 0
        streak_f = alarms_f = 0
        streak_s = alarms_s = 0
        for j, i in enumerate(widx):
            y = series[i]
            q_s = float(np.quantile(list(buf2), CONF))
            in_s = (wpred[j] - q_s) <= y <= (wpred[j] + q_s)
            in_f = (wpred[j] - q_fixed) <= y <= (wpred[j] + q_fixed)
            cover += int(in_s)
            streak_s = streak_s + 1 if not in_s else 0
            if streak_s >= N_CONSEC:
                alarms_s += 1
                streak_s = 0
            streak_f = streak_f + 1 if not in_f else 0
            if streak_f >= N_CONSEC:
                alarms_f += 1
                streak_f = 0
            buf2.append(abs(float(wpred[j]) - float(y)))
        yield label, {"n_walk": len(widx),
                      "coverage_sliding": round(cover / len(widx), 4),
                      "q_fixed": round(q_fixed, 6),
                      "alarms_fixed": alarms_f,
                      "alarms_sliding": alarms_s}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    arm = p3s2.BoltArm()
    res = {}
    timings = []
    for hp, nfid, ifid in [(0, 97, 105), (1, 98, 106), (2, 99, 107),
                           (3, 100, 108)]:
        nb = p3s1.load_cwru(nfid)["rms"]
        fb = p3s1.load_cwru(ifid)["rms"]
        half = nb.shape[0] // 2
        out = {"normal_file": nfid, "fault_file": ifid}
        for label, series in dual_eval(nb[:half], nb[half:], fb,
                                       arm.predict_batch):
            out[label] = series
            timings.append(arm.last_ms)
        res[f"hp{hp}"] = out
        print(f"  hp{hp}: healthy alarms(fixed/sliding) "
              f"{out['healthy']['alarms_fixed']}/"
              f"{out['healthy']['alarms_sliding']} | fault alarms "
              f"{out['fault']['alarms_fixed']}/"
              f"{out['fault']['alarms_sliding']} | fault cov(slide) "
              f"{out['fault']['coverage_sliding']}", flush=True)

    # the FA gate arithmetic (typed cadence: 0.1s segments)
    seg_per_year = 365 * 86400 / 0.1
    fa = {}
    for hp, out in res.items():
        n_h = out["healthy"]["n_walk"]
        fa[f"hp{hp}"] = {
            "healthy_fixed_alarms": out["healthy"]["alarms_fixed"],
            "healthy_alarms_per_machine_year": round(
                out["healthy"]["alarms_fixed"] * seg_per_year / n_h, 2),
        }
    record = {
        "record": "R105S2_P3_STAGE3B_DUAL_INTERVAL/1.0.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r105s2",
        "claim": "c-0125 (p3-realdata-conformal-validation; stage 3b)",
        "tension_typed": ("one adaptive mechanism cannot serve both "
                          "requirements: sliding conformal follows a "
                          "persistent shift (the stage-3 CWRU fault "
                          "absorption), the fixed fit-once interval "
                          "loses drift coverage (the stage-1 FD001 "
                          "0.50)"),
        "dual_design": ("coverage = sliding q (K=100 causal "
                        "residuals); alarms = the FIXED healthy-"
                        "baseline q with the N_CONSEC=3 counting "
                        "rule — alarms mean persistent deviation "
                        "from HEALTHY, which is what a fault is"),
        "predictor": "chronos-bolt-base (the same arm as stage 3)",
        "results": res,
        "fa_gate_arithmetic": {
            "cadence_typed": ("CWRU 0.1s segments -> "
                              f"{int(seg_per_year)} segments per "
                              "machine-year; the healthy-leg alarms "
                              "extrapolate to the per-machine-year "
                              "rate the FA gate reads"),
            "per_pair": fa,
        },
        "timings_ms_median": round(float(np.median(timings)), 1),
        "no_acceptance_or_score_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
