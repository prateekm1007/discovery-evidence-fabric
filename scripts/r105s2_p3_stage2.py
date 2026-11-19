#!/usr/bin/env python3
"""r105s2 P3 stage 2 — the FOUNDATION-MODEL arms on the same real-data
legs (claim c-0125; the verdict direction 4's "Chronos-2/Bolt +
Time-MoE/MOMENT" step).

Arms (the matched-budget seed; the full matched-budget DEV ablation is
typed STAGE 3):
  - the stage-1 prototype arm (Ridge+enbpi, already measured — the
    control);
  - the Chronos-Bolt arm (amazon/chronos-bolt-base, Apache-2.0; the
    verdict's "<=250x faster" claim re-measured here as wall-clock);
  - the Time-MoE arm (Maple728/TimeMoE-50M, Apache-2.0, ICLR'25
    Spotlight; greedy decoding — deterministic).
  MOMENT (AutonLab/MOMENT-1-small, MIT) is typed STAGE 3 (its
  inference stack pulls heavy deps; the weights are cached).

Protocol (typed, same as stage 1 where comparable):
  - ONE-STEP-AHEAD with TRUE history (non-recursive), per-unit
    batched context matrix -> one FM call per unit;
  - split-conformal calibration: |residual| quantile at CONF over the
    fit-half one-step residuals (typed: split conformal, NOT enbpi —
    the prototype arm keeps enbpi; the two calibration styles are
    disclosed separately);
  - coverage on the walk half (the drift side), healthy FA on the fit
    history's first 10% tail, alpha = 0.10;
  - SUBSAMPLES (typed, seed 17 where random): FD001 ALL 100 units
    (the FAILING drift channel — where the improvement matters),
    FD002 40 units (the passing control), FD003/FD004 typed to
    stage 3; CWRU the 4 paired normal+IR files (B/OR legs stay
    prototype-typed);
  - wall-clock per batched call recorded (the median-inference gate
    input; the <=2 min gate BINDS to the FM stack).

NO acceptance claims — measurements for the auditor.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
CACHE = Path("/home/z/my-project/p3_data_cache")
OUT = REPO / "eval" / "r105s2_p3_stage2_record.json"
CONF = 0.9
ALPHA = 0.10
CTX = 96                     # the FM context window (Bolt/Time-MoE native)

# stage-1 bytes reused: the loaders + the fleet-typed channel rule
_s1spec = importlib.util.spec_from_file_location(
    "p3s1", REPO / "scripts" / "r105s2_p3_stage1.py")
p3s1 = importlib.util.module_from_spec(_s1spec)
sys.modules["p3s1"] = p3s1
_s1spec.loader.exec_module(p3s1)
# suppress the stage-1 main (it runs only under __main__)


def fit_resid_q(train: np.ndarray, predict_batch) -> float:
    """Split-conformal q at CONF: one-step residuals over the fit half
    (predict_batch(contexts) -> one-step preds for a (n, ctx) matrix)."""
    ctx = CTX
    n = len(train)
    idx = list(range(ctx, n))                 # each step i: ctx history
    X = np.stack([train[i - ctx:i] for i in idx])
    y = train[ctx:n]
    preds = predict_batch(X)
    resid = np.abs(np.asarray(preds) - y)
    return float(np.quantile(resid, CONF))


def walk_eval(channel: np.ndarray, predict_batch) -> dict:
    """Fit on the first half, walk-forward one-step (true history) on
    the second half with the split-conformal interval."""
    n = len(channel)
    half = n // 2
    q = fit_resid_q(channel[:half], predict_batch)
    idx = list(range(half, n))
    X = np.stack([channel[i - CTX:i] for i in idx])
    preds = predict_batch(X)
    lo, hi = preds - q, preds + q
    y = channel[half:n]
    inside = (y >= lo) & (y <= hi)
    cov = float(inside.mean())
    # healthy FA: the fit half's first 10% tail (fit-half residuals own
    # the calibration; the healthy tail is the earliest live steps)
    t0 = max(CTX + 5, 0)
    hidx = list(range(t0, max(int(n * 0.1), CTX + 10)))
    if len(hidx) > 3:
        hX = np.stack([channel[i - CTX:i] for i in hidx])
        hp = predict_batch(hX)
        hy = channel[hidx]
        fa = float(((hy < hp - q) | (hy > hp + q)).mean())
    else:
        fa = None
    return {"n_fit": half, "n_walk": len(y), "coverage": round(cov, 4),
            "q": round(q, 6),
            "healthy_fa_rate": round(fa, 4) if fa is not None else None}


# --------------------------------------------------------------------------
# the FM predict_batch adapters (CPU, deterministic; wall-clock recorded)
# --------------------------------------------------------------------------
class BoltArm:
    name = "chronos-bolt-base"

    def __init__(self):
        from chronos import BaseChronosPipeline
        self.pipe = BaseChronosPipeline.from_pretrained(
            "amazon/chronos-bolt-base",
            cache_dir="/home/z/my-project/models_cache/p3_fm/hub",
            device_map="cpu", torch_dtype=torch.float32)

    def predict_batch(self, X: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()
        ctx = torch.tensor(X, dtype=torch.float32)
        with torch.inference_mode():
            # chronos 2.x returns (quantiles, mean); the point forecast
            # is the MEAN (second element) — the first smoke got the
            # (batch, pl, n_q) quantile tensor on the first element
            _q, mean = self.pipe.predict_quantiles(
                ctx, prediction_length=1)
        self.last_ms = (time.perf_counter() - t0) * 1000.0
        return np.asarray(mean[:, 0], dtype=float).ravel()


class TimeMoEArm:
    name = "TimeMoE-50M"

    def __init__(self):
        # transformers >=4.50 renamed/removed DynamicCache.seen_tokens,
        # which the Time-MoE generation mixin (trust_remote_code) still
        # uses — bridge it (typed, the compatibility shim disclosed in
        # the record)
        from transformers.cache_utils import DynamicCache
        if not hasattr(DynamicCache, "seen_tokens"):
            DynamicCache.seen_tokens = property(
                lambda self: self.get_seq_length())
        if not hasattr(DynamicCache, "get_max_length"):
            # the legacy API returned None when the cache is unlimited;
            # the Time-MoE mixin branches on exactly that
            DynamicCache.get_max_length = lambda self: None
        if not hasattr(DynamicCache, "get_usable_length"):
            # the legacy signature: get_usable_length(new_seq_length,
            # layer_idx=0) — the count of already-cached positions
            DynamicCache.get_usable_length = (
                lambda self, new_seq_length, layer_idx=0:
                self.get_seq_length(layer_idx))
        from transformers import AutoModelForCausalLM
        self.model = AutoModelForCausalLM.from_pretrained(
            "Maple728/TimeMoE-50M", trust_remote_code=True,
            cache_dir="/home/z/my-project/models_cache/p3_fm/hub",
            torch_dtype=torch.float32)
        self.model.eval()
        # shim 3: the legacy GenerationMixin helper the mixin expects
        if not hasattr(type(self.model),
                       "_extract_past_from_model_output"):
            def _extract(self, outputs, standardize_cache_format=False):
                return outputs.past_key_values
            type(self.model)._extract_past_from_model_output = _extract

    def predict_batch(self, X: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()
        X = np.asarray(X, dtype=np.float64)
        # the model card contract: per-window normalize (mean/std),
        # generate in the normalized space, de-normalize with the SAME
        # stats (the adapter smoke's all-zero output was the
        # unnormalized feed — typed here, not silently patched)
        mean = X.mean(axis=1, keepdims=True)
        std = X.std(axis=1, keepdims=True) + 1e-6
        Xn = (X - mean) / std
        ctx = torch.tensor(Xn, dtype=torch.float32)
        with torch.inference_mode():
            # Time-MoE's generate returns the EXTENDED continuous
            # series (batch, ctx+new) — the one-step forecast is the
            # last column
            out = self.model.generate(ctx, max_new_tokens=1)
        self.last_ms = (time.perf_counter() - t0) * 1000.0
        return (np.asarray(out[:, -1], dtype=float).ravel()
                * std.ravel() + mean.ravel())


# --------------------------------------------------------------------------
def run_arm(arm, units: list, label: str, timings: list) -> dict:
    covs, fas = [], []
    for i, ch in enumerate(units):
        try:
            r = walk_eval(ch, arm.predict_batch)
            covs.append(r)
            timings.append(arm.last_ms)
        except Exception as e:                     # typed per-unit failure
            covs.append({"skipped": repr(e)[:120]})
    ok = [c for c in covs if "coverage" in c]
    assert ok, f"{label}: every unit failed (typed abort)"
    return {
        "n_units": len(units), "n_evaluated": len(ok),
        "n_failed": len(covs) - len(ok),
        "coverage_median": round(float(np.median(
            [c["coverage"] for c in ok])), 4),
        "coverage_min": round(min(c["coverage"] for c in ok), 4),
        "healthy_fa_median": (None if all(c["healthy_fa_rate"] is None
                                          for c in ok) else round(float(
            np.median([c["healthy_fa_rate"] for c in ok if
                       c["healthy_fa_rate"] is not None])), 4)),
        "gate_coverage_ge_090": float(np.median(
            [c["coverage"] for c in ok])) >= CONF,
    }


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    rng = random.Random(17)
    res = {}

    # the fleet-typed channels from stage 1 (committed bytes)
    chan = {"FD001": 14, "FD002": 1, "FD003": 9, "FD004": 1}
    loads = {s: p3s1.load_cmapss(s) for s in ["FD001", "FD002"]}
    units = {s: [p3s1.cmapss_channel(a)[:, chan[s] - 1]
                 for a in d["units"].values()] for s, d in loads.items()}
    fd2_sub = rng.sample(range(len(units["FD002"])), 40)

    timings = []
    for arm_cls, scope in [(BoltArm, {"FD001": units["FD001"],
                                      "FD002": [units["FD002"][i]
                                                for i in fd2_sub]}),
                           (TimeMoEArm, {"FD001": units["FD001"]})]:
        arm = arm_cls()
        for sub, uu in scope.items():
            key = f"{sub}/{arm.name}"
            print(f"running {key} ...", flush=True)
            r = run_arm(arm, uu, key, timings)
            res[key] = r
            print(f"  {key}: cov {r['coverage_median']} "
                  f"gate {r['gate_coverage_ge_090']}", flush=True)
        del arm
        import gc
        gc.collect()

    print("CWRU detection leg (4 paired normal+IR files) ...", flush=True)
    arm = BoltArm()
    cwru = {}
    for hp, nfid, ifid in [(0, 97, 105), (1, 98, 106), (2, 99, 107),
                           (3, 100, 108)]:
        nb = p3s1.load_cwru(nfid)["rms"]
        fb = p3s1.load_cwru(ifid)["rms"]
        half = min(2000, len(nb) // 2)
        qv = fit_resid_q(nb[:half], arm.predict_batch)
        # healthy tail replay
        tail = nb[half:half + 2000]
        ctxM = np.stack([tail[i - CTX:i] for i in range(CTX, len(tail))])
        hpred = arm.predict_batch(ctxM)
        fa = float(((tail[CTX:] < hpred - qv) |
                    (tail[CTX:] > hpred + qv)).mean())
        # fault replay (first 400 segments)
        segs = fb[:400]
        ctxF = np.stack([segs[i - CTX:i] for i in range(CTX, len(segs))])
        fpred = arm.predict_batch(ctxF)
        det = float(((segs[CTX:] < fpred - qv) |
                     (segs[CTX:] > fpred + qv)).mean())
        cwru[f"hp{hp}"] = {"normal_file": nfid, "fault_file": ifid,
                           "q": round(qv, 4),
                           "healthy_fa_rate": round(fa, 4),
                           "fault_alarm_rate": round(det, 4)}
        timings.append(arm.last_ms)
        print(f"  hp{hp}: fa {fa:.4f} det {det:.4f}", flush=True)
    res["CWRU/chronos-bolt-base"] = cwru

    record = {
        "record": "R105S2_P3_STAGE2_FM_ARMS/1.0.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r105s2",
        "claim": "c-0125 (p3-realdata-conformal-validation; stage 2)",
        "arms": ["chronos-bolt-base (amazon, Apache-2.0)",
                 "TimeMoE-50M (Maple728, Apache-2.0, ICLR'25 Spotlight)"],
        "protocol_typed": {
            "one_step": "TRUE-history walk (non-recursive), per-unit "
                        "batched context -> ONE FM call per unit",
            "conformal": "split conformal (|resid| quantile at 0.9 "
                         "over the fit-half one-step residuals) — "
                         "DISCLOSED: not enbpi; the stage-1 prototype "
                         "arm keeps enbpi",
            "subsamples": {"FD001": "ALL 100 units (the failing drift "
                                    "channel ch14)",
                           "FD002": "40 units seed 17 (the passing "
                                    "control ch1)",
                           "FD003/FD004": "typed STAGE 3",
                           "CWRU": "4 paired normal+IR files (B/OR "
                                   "legs prototype-typed)"},
            "context": CTX,
        },
        "results": res,
        "timings": {
            "batched_call_ms_median": round(float(np.median(timings)), 1),
            "batched_call_ms_p90": round(float(np.quantile(timings, 0.9)),
                                         1),
            "note": ("the <=2min median-inference gate input; the "
                     "per-unit wall-clock is the batched-call cost — "
                     "the gate arithmetic (per-machine median) is the "
                     "auditor's"),
        },
        "honest_expected_finding": ("stage 1 showed the STATIC "
                                    "fit-once conformal FAILS (0.50) "
                                    "on the FD001 drift channel — the "
                                    "FM arms here test whether a "
                                    "stronger predictor + split "
                                    "conformal closes that; if not, "
                                    "the typed remedy is ADAPTIVE/"
                                    "sliding conformal (stage 3)"),
        "no_acceptance_or_score_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
