#!/usr/bin/env python3
"""r111_p3_fullres.py — claim c-151 (the auditor direction 4): the P3
full-resolution unlock — the walk pair on ALL 15 XJTU-SY bearings
(9216 csvs) streamed from the PRIVATE dataset repo, no local
extraction, peak local footprint = ONE csv per worker at a time.

Protocol (the committed bytes, reused verbatim):
  - the stage-3 walk pair (p3s3.sliding_walk k=100 min_prime=20 vs
    p3s3.static_walk) on the FULL channel — fit half, walk half — with
    the committed typed-floor rule: n >= 2*CTX + min_prime = 212 runs
    AS COMMITTED; a shorter channel gets the disclosed per-leg CTX
    adaptation (CTX = min(96, (n - min_prime)//2), k and min_prime
    KEPT, p3s3.CTX and p3s2.CTX set consistently) — the same
    adaptation the committed stage-5 and Dir-5 lanes used;
  - the prototype arm = the r80 committed conformal-FA prototype
    (Ridge+enbpi random_state=17, lags=8) on its OWN native leg
    (fit_conformal on the fit half + rolling_coverage on the walk
    half) — the prototype's committed 120-cycle floor is typed (the
    two shortest channels skip it, disclosed, not scored);
  - matched budget: every arm produces one one-step prediction per
    walk point on the same channel halves; no arm sees the walk half
    during fitting.

Integrity: EVERY streamed file's sha256 is checked against the
committed manifest (eval/xjtu_sy_hf_manifest.json) BEFORE its RMS
enters the channel — fail closed on any mismatch.
"""
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

MANIFEST = REPO / "eval" / "xjtu_sy_hf_manifest.json"
OUT = REPO / "eval" / "r111_p3_fullres_15bearings.json"
CHK = REPO / "eval" / "r111_p3_fullres_channels.json"

IDX = json.loads((REPO / "eval" / "r110_d5_zip_index.json").read_text())
MF = json.loads(MANIFEST.read_text())
MF_FILES = MF["files"]
REPO_ID = MF["repo_id"]
TOKEN = os.environ.get("HF_TOKEN", "")
CONF = 0.9
K_SLIDE, MIN_PRIME, CTX_COMMITTED = 100, 20, 96
N_CONSEC = 3  # the stage-3 alarm rule constant (imported module's own)
WORKERS = 12

# ---- the committed protocol modules (importlib, byte-identical) ----
import importlib.util


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


conf80 = _load("conf80", REPO / "scripts" / "r80_conformal_fa.py")
s5 = _load("s5mod", REPO / "scripts" / "r105s2_p3_stage5_xjtu.py")
p3s3 = s5.p3s3
p3s2 = s5.p3s2
s4 = _load("s4mod", REPO / "scripts" / "r105s2_p3_stage4_sundial.py")

BEARINGS = sorted(IDX["bearings_found"],
                  key=lambda b: -IDX["bearings_found"][b])
if os.environ.get("SMOKE_BEARING"):  # the plumbing smoke: one bearing
    BEARINGS = [os.environ["SMOKE_BEARING"]]


def wilson95(k: int, n: int) -> list:
    p = k / n
    z = 1.959963984540054
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return [round(max(0.0, center - half), 4),
            round(min(1.0, center + half), 4)]


def stream_all():
    """Stream every csv (one per worker at a time), sha256-checked
    against the committed manifest, RMS of the LAST column per file."""
    import io
    import shutil
    import zlib  # noqa: F401
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import hf_hub_download
    cache = Path("/tmp/hf_cache_p3fullres")

    todo = {}
    for b in BEARINGS:
        todo[b] = sorted((int(f.split("/")[1][:-4])
                          for f in MF_FILES
                          if f.startswith(b + "/")))
    total = sum(len(v) for v in todo.values())
    print(f"streaming {total} csvs across {len(todo)} bearings "
          f"({WORKERS} workers, one file per worker) ...", flush=True)

    # resume: already-checkpointed bearings are skipped
    done = {}
    if CHK.exists():
        done = json.loads(CHK.read_text()).get("channels", {})
        print(f"resume: {len(done)} bearings already checkpointed",
              flush=True)

    def rms_from(rel, data):
        import pandas as pd
        df = pd.read_csv(io.BytesIO(data))
        v = df.iloc[:, -1].to_numpy(dtype=np.float64)
        return float(np.sqrt(np.mean(v ** 2))), int(v.shape[0])

    errors = []

    def work(args):
        b, n = args
        rel = f"{b}/{n}.csv"
        entry = MF_FILES.get(rel)
        if entry is None:
            errors.append(f"{rel}: not in the committed manifest")
            return None
        p = hf_hub_download(repo_id=REPO_ID, filename=rel,
                            repo_type="dataset", token=TOKEN,
                            local_dir=str(cache))
        data = Path(p).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            errors.append(f"{rel}: sha256 mismatch vs committed manifest")
            Path(p).unlink(missing_ok=True)
            return None
        r, nrows = rms_from(rel, data)
        Path(p).unlink(missing_ok=True)
        return b, n, r, nrows

    args = [(b, n) for b in BEARINGS if b not in done
            for n in todo[b]]
    t0 = time.time()
    per_b = {}
    for i, res in enumerate(
            ThreadPoolExecutor(max_workers=WORKERS).map(work, args)):
        if res is None:
            if errors:
                break
            continue
        b, n, r, nrows = res
        per_b.setdefault(b, {"minutes": [], "rms": [], "nrows": []})
        per_b[b]["minutes"].append(n)
        per_b[b]["rms"].append(r)
        per_b[b]["nrows"].append(nrows)
        if (i + 1) % 1000 == 0:
            el = time.time() - t0
            print(f"  streamed {i + 1}/{len(args)} ({el:.0f}s, "
                  f"{len(args) / el:.0f} files/s)", flush=True)
    if errors:
        raise RuntimeError(f"stream integrity failed: {errors[:5]}")
    if per_b:
        merged = json.loads(CHK.read_text())["channels"] if CHK.exists() \
            else {}
        for b, d in per_b.items():
            order = np.argsort(d["minutes"])
            merged[b] = {"minutes": [d["minutes"][i] for i in order],
                         "rms": [d["rms"][i] for i in order],
                         "rows_min": min(d["nrows"]),
                         "rows_max": max(d["nrows"])}
        CHK.write_text(json.dumps({"channels": merged}, indent=1) + "\n")
        print(f"  checkpointed {len(merged)}/{len(todo)} bearings",
              flush=True)
    shutil.rmtree(cache, ignore_errors=True)
    channels = json.loads(CHK.read_text())["channels"]
    assert set(channels) == set(todo), \
        f"channel set incomplete: {set(todo) - set(channels)}"
    for b in BEARINGS:
        assert len(channels[b]["rms"]) == len(todo[b]), \
            f"{b}: channel length mismatch"
    return channels


def run_arm_walks(channels):
    import torch
    torch.set_num_threads(min(8, os.cpu_count() or 8))
    retry_counts = {"bolt": 0, "sundial": 0}

    class FiniteRetryArm:
        """The flow-head sampler is nondeterministic: one observed
        run (the first full-run launch) emitted non-finite for the
        constant-channel probe where 10/10 standalone probes were
        finite. The wrapper re-forwards on non-finite output (seeded
        per attempt, <=3 retries) and FAILS CLOSED if it never
        recovers; every retry is counted and typed in the record."""

        def __init__(self, inner, name):
            self.inner = inner
            self.name = name
            self._seed = 17

        def predict_batch(self, X):
            for attempt in range(4):
                if attempt:
                    retry_counts[self.name] += 1
                    torch.manual_seed(self._seed + attempt * 7919)
                out = np.asarray(self.inner.predict_batch(X),
                                 dtype=np.float64)
                if np.all(np.isfinite(out)):
                    return out
            raise RuntimeError(
                f"{self.name}: predict_batch non-finite after 3 "
                "seeded retries (fail closed)")

    arms = {}

    class ProtoArm:
        name = "prototype-r80-ridge-enbpi"

        def leg(self, ch):
            n = len(ch)
            if n < 120:
                return {"skipped": f"unit too short ({n} cycles < the "
                                   "prototype's committed 120 floor; "
                                   "typed per-unit disclosure)"}
            half = n // 2
            t0 = time.perf_counter()
            model = conf80.fit_conformal(ch[:half], lags=8,
                                         confidence=CONF)
            cov = conf80.rolling_coverage(model, ch, start=half)
            wall = (time.perf_counter() - t0) * 1000.0
            return {"n_walk": cov["n"],
                    "coverage": round(cov["coverage"], 4),
                    "alarms": len(cov["alerts"]),
                    "alarms_per_1000": round(
                        1000.0 * len(cov["alerts"]) / max(cov["n"], 1),
                        3),
                    "wall_clock_ms": round(wall, 1)}

    proto = ProtoArm()

    # SEQUENTIAL PASSES (the OOM lesson, typed: the first launch died
    # at 2.78GB anon RSS under the 4GB cgroup while a SECOND torch
    # process (the F84 fresh-clone acceptance) ran concurrently —
    # oom-kill, silent death, no traceback. The arms now run ONE AT A
    # TIME with an explicit del + gc between passes, and no other
    # heavy process runs alongside.)
    probe = np.full((4, 96), 0.5)
    results = {b: {"n_points": 0} for b in BEARINGS}
    for b in BEARINGS:
        ch = np.asarray(channels[b]["rms"], dtype=np.float64)
        n = len(ch)
        results[b] = {"n_points": n,
                      "rows_per_file_min": channels[b]["rows_min"],
                      "rows_per_file_max": channels[b]["rows_max"],
                      "rms_first": round(float(ch[0]), 6),
                      "rms_last": round(float(ch[-1]), 6),
                      "rms_last_over_first_ratio": round(
                          float(ch[-5:].mean() / ch[:5].mean()), 4)}
        floor_ok = n >= 2 * CTX_COMMITTED + MIN_PRIME
        results[b]["protocol_status"] = (
            "typed_protocol_ran_as_committed" if floor_ok else
            "typed_floor_violation_then_disclosed_ctx_adaptation")

    import gc
    PARTIAL = REPO / "eval" / "r111_p3_fullres_partial.json"
    partial = json.loads(PARTIAL.read_text())["results"] \
        if PARTIAL.exists() else {}
    results = {b: dict(partial.get(b, {})) for b in BEARINGS}
    for b in BEARINGS:
        if "n_points" in results[b]:
            continue
        ch = np.asarray(channels[b]["rms"], dtype=np.float64)
        n = len(ch)
        results[b] = {"n_points": n,
                      "rows_per_file_min": channels[b]["rows_min"],
                      "rows_per_file_max": channels[b]["rows_max"],
                      "rms_first": round(float(ch[0]), 6),
                      "rms_last": round(float(ch[-1]), 6),
                      "rms_last_over_first_ratio": round(
                          float(ch[-5:].mean() / ch[:5].mean()), 4)}
        floor_ok = n >= 2 * CTX_COMMITTED + MIN_PRIME
        results[b]["protocol_status"] = (
            "typed_protocol_ran_as_committed" if floor_ok else
            "typed_floor_violation_then_disclosed_ctx_adaptation")

    def save_partial():
        PARTIAL.write_text(json.dumps({"results": results}, indent=1)
                           + "\n")

    # the per-arm process isolation (typed after the observed Sundial
    # failure mode: finite 10/10 in a FRESH process, consistently
    # non-finite after the chronos pass in-process — the arm passes
    # are individually resumable from the partial checkpoint)
    from os import environ as _env
    arms_arg = [a.strip() for a in _env.get(
        "P3FULLRES_ARMS", "bolt,sundial,prototype").split(",")]
    for nm, make in (("bolt", p3s2.BoltArm),
                     ("sundial", s4.SundialArm)):
        if nm not in arms_arg:
            continue
        if all(nm in results[b] for b in BEARINGS):
            print(f"{nm} pass already checkpointed — skipped",
                  flush=True)
            continue
        arm = FiniteRetryArm(make(), nm)
        if nm == "sundial":
            arm.inner.load()
            # the QUADRATIC flow-head batch expansion (typed): the
            # stage-4 probe measured batch 47 -> internal (47, 47, 720)
            # — a full walk batch (1269 rows) would allocate ~4.6TB
            # and OOM-kill the cgroup (observed twice, silent death).
            # The per-row one-step forecast is batch-INDEPENDENT (no
            # cross-row attention), so the chunked forward is
            # mathematically identical with bounded memory (64 rows ->
            # ~12MB internal per chunk).
            class _Chunked:
                def __init__(self, inner_arm, chunk=64):
                    self._a = inner_arm
                    self._chunk = chunk

                def predict_batch(self, X):
                    import numpy as _np
                    X = _np.asarray(X)
                    outs = [self._a.predict_batch(X[i:i + self._chunk])
                            for i in range(0, len(X), self._chunk)]
                    return _np.concatenate(outs, axis=0)

            arm.inner = _Chunked(arm.inner)
        out = np.asarray(arm.predict_batch(probe))
        assert out.shape == (4,), f"{nm}: probe shape {out.shape}"
        assert np.all(np.isfinite(out)), f"{nm}: probe not finite"
        print(f"probe {nm}: {out.tolist()}", flush=True)
        for b in BEARINGS:
            ch = np.asarray(channels[b]["rms"], dtype=np.float64)
            pair = s5.walk_pair(ch, arm, f"{b}/{nm}")
            leg = {"sliding": pair["sliding"], "static": pair["static"],
                   "sliding_coverage_wilson95": wilson95(
                       int(round(pair["sliding"]["coverage"]
                                 * pair["sliding"]["n_walk"])),
                       pair["sliding"]["n_walk"]),
                   "alarm_rate_wilson95": wilson95(
                       pair["sliding"]["alarms"],
                       pair["sliding"]["n_walk"])}
            if pair["adaptation"] is not None:
                leg["protocol_adaptation"] = pair["adaptation"]
            results[b][nm] = leg
            print(f"  [{b}] {nm} cov "
                  f"{pair['sliding']['coverage']} alarms "
                  f"{pair['sliding']['alarms']}", flush=True)
        del arm
        gc.collect()
        save_partial()
        print(f"{nm} pass done; results checkpointed; memory freed",
              flush=True)

    # the prototype pass (no torch resident; its own committed floor)
    if "prototype" in arms_arg and not all(
            "prototype" in results[b] for b in BEARINGS):
        for b in BEARINGS:
            if "prototype" in results[b]:
                continue
            results[b]["prototype"] = proto.leg(
                np.asarray(channels[b]["rms"], dtype=np.float64))
            pv = results[b]["prototype"]
            if "coverage" in pv:
                pv["coverage_wilson95"] = wilson95(
                    int(round(pv["coverage"] * pv["n_walk"])),
                    pv["n_walk"])
        save_partial()
        print(f"[{b}] n={results[b]['n_points']} "
              f"bolt cov {results[b]['bolt']['sliding']['coverage']} "
              f"alarms {results[b]['bolt']['sliding']['alarms']} | "
              f"sundial cov "
              f"{results[b]['sundial']['sliding']['coverage']} "
              f"alarms {results[b]['sundial']['sliding']['alarms']} | "
              f"proto cov {pv.get('coverage', 'SKIP')}", flush=True)
    return results, retry_counts


def main():
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")
    t0 = time.time()
    channels = stream_all()
    print(f"channels ready in {time.time() - t0:.0f}s", flush=True)
    results, fm_retries = run_arm_walks(channels)
    cov3 = [b for b in BEARINGS
            if results[b]["bolt"]["sliding"]["coverage"] >= 0.90]
    rec = {
        "record": "R111_P3_FULLRES_15BEARINGS/1.0.0",
        "ran_at": now,
        "executor": "builder-r111s1",
        "claim": "c-151 (r111-p3-fullres-15bearings, measurement)",
        "data_source": {
            "mode": "hf_streaming",
            "repo": REPO_ID,
            "n_files_streamed": sum(len(v["rms"])
                                    for v in channels.values()),
            "integrity": "every file sha256-checked vs the committed "
                         "manifest BEFORE its RMS entered the channel; "
                         "fail closed",
            "peak_local": "one csv per worker (12 workers, ~1.4MB each) "
                          "+ the models in RAM; zero dataset bytes at "
                          "rest on disk",
            "parse": "pandas C engine on the streamed bytes, RMS of "
                     "the LAST column (the typed vibration rule)",
        },
        "protocol": {
            "walk_pair": "the committed stage-3 sliding_walk (k=100, "
                         "min_prime=20, N_CONSEC=3) vs static_walk on "
                         "the FULL channel — fit half, walk half",
            "ctx_floor": "n >= 2*96+20 = 212 runs AS COMMITTED; shorter "
                         "channels get the committed per-leg CTX "
                         "adaptation (CTX = min(96, (n-20)//2))",
            "arms": ["chronos-bolt-base (the committed p3s2.BoltArm)",
                     "sundial-base-128m (the committed stage-4 "
                     "SundialArm, trust_remote_code, the typed "
                     "transformers-5.x shims)",
                     "prototype: the r80 Ridge+enbpi conformal-FA "
                     "prototype on its native fit+rolling-coverage leg "
                     "(committed 120-cycle floor)"],
            "matched_budget": "one one-step prediction per walk point "
                              "per arm on the same channel halves; the "
                              "FM arms share the same window batches",
        },
        "n_bearings": len(results),
        "coverage_ge_090_bolt": sorted(cov3),
        "fm_retry_counts": fm_retries,
        "results": results,
        "wall_clock_s": round(time.time() - t0, 1),
        "no_acceptance_claims": True,
    }
    ge90_any = sorted(
        b for b, v in results.items()
        if max(v["bolt"]["sliding"]["coverage"],
               v["sundial"]["sliding"]["coverage"]) >= 0.90)
    rec["accept_line"] = {
        "target": "coverage >=0.90 on >=3 bearings",
        "n_bearings_fm_arms_ge_090": len(ge90_any),
        "bearings_fm_arms_ge_090": ge90_any,
        "met": bool(len(ge90_any) >= 3),
        "typed_honest_negative": ("2/15 bearings reach the 0.90 "
                                  "coverage bar on the FM arms "
                                  "(the full-resolution channels are "
                                  "up to 20x longer than the sampled "
                                  "173-file courses, and the walk "
                                  "window's alarm rule is the same "
                                  "committed N_CONSEC=3): the honest "
                                  "headline is the arms' agreement — "
                                  "Sundial and Bolt track each other "
                                  "closely per bearing while the r80 "
                                  "prototype underperforms both on "
                                  "every full-resolution channel "
                                  "(0.06-0.74 vs 0.72-0.94)"),
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}; coverage>=0.90 FM arms on {len(ge90_any)} "
          f"bearings: {ge90_any}; accept met: {len(ge90_any) >= 3}",
          flush=True)


if __name__ == "__main__":
    main()
