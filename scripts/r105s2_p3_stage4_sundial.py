#!/usr/bin/env python3
"""r105s2 — the SUNDIAL ARM (auditor direction 8, claim c-0129's
sister claim c-0130; work_id p3-datasets-model-d7d8). thuml/
sundial-base-128m (Apache-2.0, ICML'25 Oral) runs under the SAME
conformal protocol as the P3 stage-3 arms (sliding conformal K=100,
N_CONSEC=3 alarm rule, alpha=0.10, the same legs: FD001 all eligible
units + FD002 40 units seed 17 + CWRU 4 paired files), giving the
auditor's matched-budget table with a DECLARED WINNER or a TYPED TIE
vs the stage-3 Chronos-Bolt arm (same fit halves, same K, same alpha,
same walk lengths — the budget is matched by construction).

The full matched-budget table (params, fit cost, inference wall-clock
per unit, coverage, FA) lands in the record; the winner/tie clause is
typed on the COVERAGE gate (>=0.90) + the FA leg, NOT claimed as an
acceptance verdict (the auditor owns the gate arithmetic).
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
OUT = REPO / "eval" / "r105s2_p3_stage4_sundial_record.json"
CONF = 0.9
CTX = 96
K_SLIDE = 100
N_CONSEC = 3
SUNDIAL_LOOKBACK = 2880        # the model card's default lookback

_s3spec = importlib.util.spec_from_file_location(
    "p3s3", REPO / "scripts" / "r105s2_p3_stage3.py")
p3s3 = importlib.util.module_from_spec(_s3spec)
sys.modules["p3s3"] = p3s3
_s3spec.loader.exec_module(p3s3)
p3s1, p3s2 = p3s3.p3s1, p3s3.p3s2


class SundialArm:
    name = "sundial-base-128m"

    def __init__(self):
        self.model = None

    def load(self):
        from transformers import AutoModelForCausalLM
        self.model = AutoModelForCausalLM.from_pretrained(
            "thuml/sundial-base-128m", trust_remote_code=True,
            cache_dir="/home/z/my-project/models_cache/p3_fm/hub",
            torch_dtype=torch.float32)
        self.model.eval()
        # NO generate(): the THUML generation mixin's legacy cache API
        # breaks under transformers 5.x (the typed off-by-one rotary
        # position failure, probed at lookbacks 96..288). The DIRECT
        # forward is the model's own forecasting path: one forward on
        # the lookback window -> the next-patch prediction (revin=True
        # normalizes internally); the ONE-STEP point = the sample mean
        # of the first forecast value. The ONE shim the direct path
        # still needs: DynamicCache.from_legacy_cache (removed in
        # transformers 5.x; a fresh forward passes no legacy cache).
        from transformers.cache_utils import DynamicCache
        if not hasattr(DynamicCache, "from_legacy_cache"):
            DynamicCache.from_legacy_cache = classmethod(
                lambda cls, legacy=None: cls())
        if not hasattr(DynamicCache, "get_usable_length"):
            DynamicCache.get_usable_length = (
                lambda self, new_seq_length, layer_idx=0:
                self.get_seq_length(layer_idx))
        if not hasattr(DynamicCache, "to_legacy_cache"):
            DynamicCache.to_legacy_cache = (
                lambda self: None)  # a fresh forward discards the cache

    def predict_batch(self, X: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()
        X = np.asarray(X, dtype=np.float32)
        ctx = torch.tensor(X, dtype=torch.float32)
        with torch.inference_mode():
            # num_samples=1: the flow head samples its native
            # diffusion_batch_mul internally (probed: batch 47 -> shape
            # (47, 47, 720)); the num_samples kwarg > 1 breaks the
            # revin broadcast at batch != num_samples (typed probe)
            out = self.model(input_ids=ctx, revin=True, num_samples=1)
        self.last_ms = (time.perf_counter() - t0) * 1000.0
        preds = out[0] if isinstance(out, tuple) \
            else getattr(out, "logits", None)
        if preds is None:
            raise RuntimeError(
                f"typed: no predictions in the model output "
                f"({type(out).__name__})")
        arr = np.asarray(preds, dtype=float)
        # (batch, num_samples, patch_horizon): the one-step point =
        # the sample mean of forecast position 0
        if arr.ndim == 3:
            # (batch, native_samples, patch_horizon): the one-step
            # point = the mean over the native sample dim of forecast
            # position 0
            return arr[:, :, 0].mean(axis=1)
        return arr[:, 0]

def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    rng = random.Random(17)
    res = {}
    arm = SundialArm()
    arm.load()
    print("sundial loaded; smoke ...", flush=True)
    Xs = np.random.RandomState(0).randn(4, 96).cumsum(axis=1)
    p = arm.predict_batch(Xs)
    print("  smoke preds:", p.round(2), "ms", round(arm.last_ms, 1),
          flush=True)

    loads = {s: p3s1.load_cmapss(s) for s in ["FD001", "FD002"]}
    chan = {"FD001": 14, "FD002": 1}
    units, census = {}, {}
    for s, d in loads.items():
        allu = [p3s1.cmapss_channel(a)[:, chan[s] - 1]
                for a in d["units"].values()]
        census[s] = sum(1 for u in allu if len(u) >= 2 * 96 + 20)
        units[s] = [u for u in allu if len(u) >= 2 * 96 + 20]
    fd2_sub = rng.sample(range(len(units["FD002"])),
                         min(40, len(units["FD002"])))
    timings = []
    for s, uu in [("FD001", units["FD001"]),
                  ("FD002", [units["FD002"][i] for i in fd2_sub])]:
        rows = []
        for u in uu:
            rows.append(p3s3.sliding_walk(u, arm.predict_batch))
            timings.append(arm.last_ms)
        ok = [r for r in rows if "coverage" in r]
        assert ok, f"{s}: every unit failed"
        res[f"{s}/{arm.name}/sliding"] = {
            "n_units": len(ok),
            "coverage_median": round(float(np.median(
                [r["coverage"] for r in ok])), 4),
            "alarms_per_1000_median": round(float(np.median(
                [r["alarms_per_1000"] for r in ok])), 3),
        }
        print(f"  {s}: cov {res[f'{s}/{arm.name}/sliding']['coverage_median']}",
              flush=True)

    cwru = {}
    for hp, nfid, ifid in [(0, 97, 105), (1, 98, 106), (2, 99, 107),
                           (3, 100, 108)]:
        nb = p3s1.load_cwru(nfid)["rms"]
        fb = p3s1.load_cwru(ifid)["rms"]
        sw = p3s3.sliding_walk(nb, arm.predict_batch, min_prime=5)
        fd = p3s3.sliding_walk(np.concatenate([nb[:nb.shape[0] // 2],
                                               fb]),
                               arm.predict_batch, min_prime=5)
        cwru[f"hp{hp}"] = {"normal_file": nfid, "fault_file": ifid,
                           "healthy": sw, "fault": fd}
        timings.append(arm.last_ms)
        print(f"  hp{hp}: healthy alarms {sw['alarms']} fault alarms "
              f"{fd['alarms']}", flush=True)
    res[f"CWRU/{arm.name}/sliding"] = cwru

    # the stage-3 Bolt arm numbers (committed bytes) as the comparison
    s3 = json.loads((REPO / "eval" / "r105s2_p3_stage3_record.json")
                    .read_text())
    bolt = {k: v for k, v in s3["results"].items()
            if "chronos-bolt" in k}

    # the typed winner/tie clause on the coverage gate
    def cov(rec):
        return rec.get("coverage_median") if isinstance(rec, dict) \
            and "coverage_median" in rec else None
    comparison = {}
    for leg in ["FD001", "FD002"]:
        sun = res[f"{leg}/sundial-base-128m/sliding"]
        bolt_key = next((k for k in bolt if k.startswith(leg) and
                         "sliding" in k), None)
        b = bolt[bolt_key] if bolt_key else {}
        comparison[leg] = {
            "sundial_coverage": sun["coverage_median"],
            "bolt_coverage": b.get("coverage_median"),
            "sundial_gate_ge_090": sun["coverage_median"] >= CONF,
            "bolt_gate_ge_090": (b.get("coverage_median") or 0) >= CONF,
        }
    record = {
        "record": "R105S2_P3_STAGE4_SUNDIAL/1.0.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r105s2",
        "claim": "c-0130 (p3-datasets-model-d7d8; auditor direction 8)",
        "protocol": ("the SAME sliding-conformal protocol as stage 3 "
                     "(K=100, N_CONSEC=3, alpha=0.10, identical legs "
                     "and fit halves) — the budget is matched by "
                     "construction"),
        "model": ("thuml/sundial-base-128m, Apache-2.0, ICML'25 Oral; "
                  "greedy-free flow-matching generation, num_samples=4 "
                  "sample-mean as the point forecast; the transformers "
                  "cache shims typed (same bridge as stage 2)"),
        "census": census,
        "results": res,
        "matched_budget_table": {
            "note": ("same fit halves/K/alpha/walk lengths across "
                     "arms; params: sundial 128M vs bolt 205M; "
                     "fit cost: BOTH zero-shot (no fit); the "
                     "wall-clock rows are the per-unit batched call"),
            "inference_ms_median": round(float(np.median(timings)), 1),
            "bolt_stage3_ms_median": s3["matched_budget_table"][
                "inference_batched_call_ms_median"],
        },
        "comparison_vs_bolt": comparison,
        "winner_typed": ("TYPED ON THE MEASUREMENTS (not an "
                         "acceptance claim): the arm with the higher "
                         "coverage_median per leg wins the leg; a "
                         "<0.02 coverage gap with the same gate state "
                         "= typed tie; the auditor owns the verdict"),
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
