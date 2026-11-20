#!/usr/bin/env python3
"""r110s2_hf_stage5_source.py — the `--source hf` implementation for the
stage-5 XJTU-SY leg (the owner-directed HF streaming path; claim
c-0148, builder-r109s2).

WHAT IT DOES: reconstructs the EXACT committed 173-file sample from
the committed attribution record (eval/r105s2_p3_stage5_xjtu_attribution.json
— filename -> bearing; no mtimes needed, the HF repo folders are
explicit), streams each csv from the owner's PRIVATE dataset repo
(prateekm1/xjtu-sy-bearing-rar) via hf_hub_download into an ephemeral
/tmp cache, computes the committed RMS channel (LAST column, typed
rule), deletes the local file IMMEDIATELY after use (peak local
footprint ~= one csv, ~1.3MB), and runs the stage-5 walk_pair VERBATIM
(the committed protocol module refs are passed in by the caller —
zero protocol bytes duplicated).

WHY A SEPARATE MODULE: the committed r105s2 record bytes must stay
untouched (Art. 4) — the HF run writes its own acceptance record
(eval/r110s2_p3_stage5_hf_acceptance.json) with the match-vs-committed
booleans; the stage-5 script keeps its local path byte-identical as
the default (--source local).

NO acceptance claims — the match booleans are measurements for the
auditor.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
ATTR = REPO / "eval" / "r105s2_p3_stage5_xjtu_attribution.json"
COMMITTED = REPO / "eval" / "r105s2_p3_stage5_xjtu_record.json"
OUT = REPO / "eval" / "r110s2_p3_stage5_hf_acceptance.json"
HF_CACHE = Path("/tmp/hf_cache_xjtu")
REPO_ID = "prateekm1/xjtu-sy-bearing-rar"
BEARINGS = ["Bearing3_1", "Bearing3_2"]


def rms_from_bytes(csv_bytes: bytes):
    import io
    arr = np.loadtxt(io.BytesIO(csv_bytes), delimiter=",",
                     dtype=np.float64, skiprows=1)
    return (float(np.sqrt(np.mean(arr[:, -1] ** 2))),
            int(arr.shape[0]))


def stream_channel(bearing: str, minutes: list, log) -> tuple:
    """hf_hub_download per file -> RMS -> delete; minute order."""
    from huggingface_hub import hf_hub_download
    import os
    tok = os.environ.get("HF_TOKEN", "")
    if HF_CACHE.exists():
        shutil.rmtree(HF_CACHE)
    HF_CACHE.mkdir(parents=True)
    entries = {}
    peak = 0
    for n in sorted(minutes):
        t0 = time.perf_counter()
        p = hf_hub_download(repo_id=REPO_ID,
                            filename=f"{bearing}/{n}.csv",
                            repo_type="dataset", token=tok,
                            local_dir=str(HF_CACHE))
        size = Path(p).stat().st_size
        peak = max(peak, size)
        rms, nrows = rms_from_bytes(Path(p).read_bytes())
        entries[n] = (rms, nrows)
        Path(p).unlink(missing_ok=True)
        log(f"  {bearing}/{n}.csv rms={rms:.4f} "
            f"({(time.perf_counter() - t0) * 1000:.0f} ms)")
    minutes_sorted = sorted(entries)
    ch = np.asarray([entries[mn][0] for mn in minutes_sorted],
                    dtype=np.float64)
    nrows = [entries[mn][1] for mn in minutes_sorted]
    return ch, nrows, minutes_sorted, peak


def run_hf_source(s5, log=None) -> int:
    """s5 = the loaded r105s2_p3_stage5_xjtu module (walk_pair, arm
    constants, p3s2 refs). Writes the acceptance record; returns 0."""
    log = log or (lambda s: print(s, flush=True))
    att = json.loads(ATTR.read_text())["attribution"]
    committed = json.loads(COMMITTED.read_text())

    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    log("loading the Chronos-Bolt arm (local, zero LLM) ...")
    arm = s5.p3s2.BoltArm()

    results, peak_all = {}, 0
    for bearing in BEARINGS:
        minutes = sorted(int(Path(k).stem) for k, v in att.items()
                         if v == bearing)
        log(f"{bearing}: {len(minutes)} sampled minutes "
            f"({minutes[0]}..{minutes[-1]})")
        ch, nrows, mins, peak = stream_channel(bearing, minutes, log)
        peak_all = max(peak_all, peak)
        pair = s5.walk_pair(ch, arm, bearing)
        sl, st = pair["sliding"], pair["static"]
        results[bearing] = {
            "n_points": len(ch),
            "minute_index_first": mins[0],
            "minute_index_last": mins[-1],
            "rows_per_file_min": min(nrows),
            "rows_per_file_max": max(nrows),
            "rms_first5": [round(float(v), 6) for v in ch[:5]],
            "rms_last5": [round(float(v), 6) for v in ch[-5:]],
            "rms_last_over_first_ratio": round(
                float(ch[-1]) / max(float(ch[0]), 1e-9), 4),
            "protocol_status": pair["status"],
            "sliding": sl, "static": st,
            "protocol_adaptation": pair["adaptation"],
        }

    # ---- match-vs-committed (the owner's acceptance item) ----
    match = {}
    for bearing, r in results.items():
        c = committed["results"][bearing]
        sl_match = (round(r["sliding"]["coverage"], 4)
                    == round(c["sliding"]["coverage"], 4)
                    and r["sliding"]["alarms"] == c["sliding"]["alarms"]
                    and r["sliding"]["n_walk"] == c["sliding"]["n_walk"])
        st_match = (round(r["static"]["coverage"], 4)
                    == round(c["static"]["coverage"], 4)
                    and r["static"]["alarms"] == c["static"]["alarms"])
        rms_match = (r["rms_first5"] == c["rms_first5"]
                     and r["rms_last5"] == c["rms_last5"])
        match[bearing] = {
            "sliding_coverage_alarms_match": bool(sl_match),
            "static_coverage_alarms_match": bool(st_match),
            "rms_endpoints_match": bool(rms_match),
            "committed": {"sliding": {"coverage": c["sliding"]["coverage"],
                                      "alarms": c["sliding"]["alarms"],
                                      "n_walk": c["sliding"]["n_walk"]},
                          "static": {"coverage": c["static"]["coverage"],
                                     "alarms": c["static"]["alarms"]}},
            "hf_run": {"sliding": {"coverage": r["sliding"]["coverage"],
                                   "alarms": r["sliding"]["alarms"],
                                   "n_walk": r["sliding"]["n_walk"]},
                       "static": {"coverage": r["static"]["coverage"],
                                  "alarms": r["static"]["alarms"]}},
        }

    from huggingface_hub import HfApi
    import os
    api = HfApi(token=os.environ.get("HF_TOKEN", ""))
    tip = api.repo_info(REPO_ID, repo_type="dataset")

    rec = {
        "record": "R110S2_P3_STAGE5_HF_ACCEPTANCE/1.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r109s2",
        "claim": "c-0148",
        "owner_direction": ("the HF-streaming acceptance item: the "
                            "stage-5 walk pair run from HF-sourced "
                            "bytes must match the committed 173-file "
                            "sample run"),
        "source": {
            "mode": "hf_streaming",
            "repo_id": REPO_ID,
            "repo_type": "dataset",
            "repo_private": True,
            "repo_tip_sha": str(tip.sha),
            "streaming_mode": "per-file hf_hub_download -> RMS -> "
                              "immediate delete (ephemeral /tmp cache)",
            "max_local_footprint_bytes_one_csv": int(peak_all),
            "sample_reconstruction": ("the EXACT committed 173-minute "
                                      "set from the committed "
                                      "attribution record"),
        },
        "results": results,
        "match_vs_committed": match,
        "acceptance": all(
            all(v.values() for k, v in m.items()
                if isinstance(v, bool)) for m in match.values()),
        "protocol_provenance": ("walk_pair + constants reused VERBATIM "
                                "from scripts/r105s2_p3_stage5_xjtu.py "
                                "(the committed stage-5 bytes; the "
                                "local path untouched, default "
                                "--source local)"),
        "zero_llm_calls": True,
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    if HF_CACHE.exists():
        shutil.rmtree(HF_CACHE)
    log(f"wrote {OUT} | acceptance={rec['acceptance']}")
    return 0
