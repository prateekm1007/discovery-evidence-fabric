#!/usr/bin/env python3
"""r105s2 P3 stage 1 — the REAL-DATA conformal FA-control smoke
(claim c-0125, work_id p3-realdata-conformal-validation, kind
measurement; the auditor R105 verdict direction 4).

This is the r80 prototype (scripts/r80_conformal_fa.py — the
COMMITTED bytes, importlib-loaded verbatim) run on REAL channels for
the first time, zero foundation models, zero LLM:

  C-MAPSS (NASA PCoE canonical zip, FD001-FD004):
    the fleet-selected degradation channel per subset (the typed
    deterministic rule below), per-unit conformal one-step fit on
    the first half of life, walk-forward coverage on the second
    half; healthy-window FA rate.
  CWRU (the Case Western Reserve 12kHz Drive-End subset, 16 files):
    the RMS-per-0.1s channel; conformal fit on the 0hp NORMAL
    baseline; the paired same-load detection leg (98/106,
    97/105, ... normals must NOT alarm, faulted must) — the real
    signal complement of the FA gate.
  XJTU-SY: DATA ACQUIRED + MANIFESTED + listing-verified, extraction
    BLOCKED (RAR5 volume set; no RAR5 extractor in this sandbox;
    10.2GB raw vs the 9.9G rootfs) — typed OPEN with the parts
    manifest committed under eval/p3_realdata/.

GATES (typed, from the verdict): coverage >= 1-alpha and FA <=
1/machine/yr are MEASURED here on the prototype stack; median
inference <= 2 min is measured for the prototype stack (the gate
BINDS to the FM stack in stage 2); the matched-budget DEV ablation
is typed STAGE 3. NO acceptance claims — the auditor owns the gate
verdicts.

DATASET PROVENANCE (acknowledgment conventions carried):
  C-MAPSS: A. Saxena and K. Goebel (2008), NASA Prognostics Data
  Repository, NASA Ames Research Center (the PCoE repository's
  requested citation; "users employ the data at their own risk").
  CWRU: Case Western Reserve University Bearing Data Center
  (engineering.case.edu/bearingdatacenter), freely available per the
  site's stated use.
  XJTU-SY: B. Wang, Y. Lei, N. Li, N. Li, "A Hybrid Prognostics
  Approach for Estimating Remaining Useful Life of Rolling Element
  Bearings", IEEE Trans. Reliability 69(1):401-412, 2020,
  DOI 10.1109/TR.2018.2882682 (the dataset's requested citation).
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.stats import spearmanr

# the r110s2 path-robustness deviation (typed, disclosed; the
# r105s2 session checkout location -> the script's own parent;
# DISJOINT from the twin-window loader rewrite — the same
# deviation class as the r108s2 cred-helper path pin)
REPO = Path(__file__).resolve().parents[1]
CACHE = Path("/home/z/my-project/p3_data_cache")
OUT = REPO / "eval" / "r105s2_p3_stage1_record.json"
CMAPSS_DIR = CACHE / "cmapss" / "CMAPSSData"
CWRU_DIR = CACHE / "cwru_12kHz_DE"
ALPHA = 0.10                  # the declared confidence 0.9 (the r80 pin)
CONF = 1.0 - ALPHA

# the r80 prototype, committed bytes, never a copy
_spec = importlib.util.spec_from_file_location(
    "conf80", REPO / "scripts" / "r80_conformal_fa.py")
conf80 = importlib.util.module_from_spec(_spec)
sys.modules["conf80"] = conf80
_spec.loader.exec_module(conf80)


def sha256_file(p: Path, n: int = 16) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


# --------------------------------------------------------------------------
# loaders (typed structure checks — a silently-wrong parse is the vacuity
# class; every check aborts the record on mismatch)
# --------------------------------------------------------------------------
CMAPSS_UNITS = {"FD001": 100, "FD002": 260, "FD003": 100, "FD004": 249}


def load_cmapss(subset: str) -> dict:
    assert subset in CMAPSS_UNITS, f"unknown subset {subset}"
    path = CMAPSS_DIR / f"train_{subset}.txt"
    assert path.exists(), f"C-MAPSS {subset} missing at {path}"
    units = {}
    with open(path) as f:
        for line in f:
            cols = line.split()
            assert len(cols) == 26, \
                f"{subset}: expected 26 columns, got {len(cols)}"
            u = int(cols[0])
            units.setdefault(u, {"cycles": [], "rows": []})
            units[u]["cycles"].append(int(cols[1]))
            units[u]["rows"].append([float(x) for x in cols[2:]])
    assert len(units) == CMAPSS_UNITS[subset], \
        f"{subset}: expected {CMAPSS_UNITS[subset]} units, got " \
        f"{len(units)} (typed abort — the parse is wrong)"
    out = {}
    for u, d in units.items():
        cyc = np.array(d["cycles"])
        assert np.all(np.diff(cyc) == 1), \
            f"{subset} unit {u}: cycles not contiguous (typed abort)"
        out[u] = np.array(d["rows"])   # rows = cycles in order;
                                       # cols = 3 settings + 21 sensors
    return {"units": out, "n_settings": 3, "n_sensors": 21,
            "source_sha": sha256_file(path)}


def cmapss_channel(series: np.ndarray) -> np.ndarray:
    """The sensor columns follow the 3 setting columns: col 3+ SensorN."""
    return series[:, 3:]


def select_degradation_channel(subsets: list) -> dict:
    """The typed deterministic rule (fixed BEFORE any run, disclosed):
    for each subset, the channel whose fleet-level median in the last
    20% of unit life vs the first 20% has the max |shift|/scale ratio;
    computed on the TRAIN fleet only, applied unchanged everywhere."""
    chosen = {}
    for sub in subsets:
        d = load_cmapss(sub)
        scores = []
        for ch in range(21):
            vals = []
            for arr in d["units"].values():
                s = cmapss_channel(arr)[:, ch]
                s = s[np.abs(np.diff(s, prepend=s[0])) < 1e6]  # dep-vac
                n = len(s)
                if n < 20:
                    continue
                a, b = np.median(s[: max(n // 5, 5)]), \
                    np.median(s[-max(n // 5, 5):])
                scale = np.std(s[: max(n // 5, 5)]) + 1e-9
                vals.append(abs(b - a) / scale)
            scores.append(np.median(vals) if vals else 0.0)
        chosen[sub] = {"channel_1indexed": int(np.argmax(scores)) + 1,
                       "score": round(float(max(scores)), 4)}
    return chosen


CWRU_FILES = {
    97: ("normal", 0), 98: ("normal", 1), 99: ("normal", 2),
    100: ("normal", 3),
    105: ("IR_007", 0), 106: ("IR_007", 1), 107: ("IR_007", 2),
    108: ("IR_007", 3),
    118: ("B_007", 0), 119: ("B_007", 1), 120: ("B_007", 2),
    121: ("B_007", 3),
    130: ("OR_007_6h", 0), 131: ("OR_007_6h", 1),
    132: ("OR_007_6h", 2), 133: ("OR_007_6h", 3),
}


def load_cwru(fid: int) -> dict:
    path = CWRU_DIR / f"{fid}.mat"
    assert path.exists(), f"CWRU {fid}.mat missing"
    m = loadmat(str(path))
    key = f"X{fid:03d}_DE_time"
    assert key in m, f"CWRU {fid}: drive-end channel {key} missing " \
                     f"(keys: {[k for k in m if not k.startswith('__')]})"
    sig = np.asarray(m[key]).ravel()
    assert len(sig) >= 120000, \
        f"CWRU {fid}: too short ({len(sig)} samples)"
    seg = 1200                                  # 0.1 s at 12 kHz
    nseg = len(sig) // seg
    rms = np.sqrt((sig[: nseg * seg].reshape(nseg, seg) ** 2)
                  .mean(axis=1))
    cls, hp = CWRU_FILES[fid]
    return {"fid": fid, "class": cls, "hp": hp, "rms": rms,
            "fs": 12000, "seg_seconds": seg / 12000.0,
            "n_segments": nseg, "source_sha": sha256_file(path)}


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------
def coverage_and_healthy_fa(channel: np.ndarray) -> dict:
    """The C-MAPSS per-unit leg: conformal fit on the FIRST half,
    walk-forward coverage on the SECOND half (the degradation side),
    healthy-window FA = in-sample alerts on the fit history's first
    10% tail (the prototype's own fa_signal, replayed)."""
    n = len(channel)
    if n < 120:
        return {"skipped": f"unit too short ({n} cycles < 120 floor; "
                           f"typed per-unit disclosure)"}
    half = n // 2
    model = conf80.fit_conformal(channel[:half], lags=8, confidence=CONF)
    cov = conf80.rolling_coverage(model, channel, start=half)
    # healthy FA: the first 10% of the FIT history (healthy life) replay
    healthy = channel[: max(n // 10, 30)]
    alerts = 0
    for i in range(10, len(healthy)):
        v = conf80.fa_signal(model, healthy[i - 8:i], healthy[i])
        alerts += int(v["fault_alert"])
    return {"n_fit": half, "n_walk": cov["n"],
            "coverage": round(cov["coverage"], 4),
            "walk_alerts": len(cov["alerts"]),
            "healthy_fa_rate_per_1000_steps":
                round(1000.0 * alerts / max(len(healthy) - 10, 1), 3)}


def cwru_detection_leg() -> dict:
    """The paired same-load detection leg: fit on the 0hp..3hp NORMAL
    baselines, replay the matching load's faulted RMS — a real-fault
    alarm is EXPECTED (the complement of the FA gate)."""
    pairs = []
    for hp in range(4):
        base = load_cwru({0: 97, 1: 98, 2: 99, 3: 100}[hp])
        model = conf80.fit_conformal(base["rms"][:2000], lags=8,
                                     confidence=CONF)
        # healthy replay on the SAME file's tail (the FA leg, same load)
        tail = base["rms"][2000:4000]
        fa = 0
        for i in range(10, len(tail)):
            fa += int(conf80.fa_signal(model, tail[i - 8:i],
                                       tail[i])["fault_alert"])
        res = {"hp": hp, "normal_file": base["fid"],
               "healthy_fa_per_1000": round(1000.0 * fa / (len(tail) - 10),
                                            3)}
        for cls in ["IR_007", "B_007", "OR_007_6h"]:
            fids = [f for f, (c, h) in CWRU_FILES.items()
                    if c == cls and h == hp]
            alarms = []
            for fid in fids:
                d = load_cwru(fid)
                hits = 0
                segs = d["rms"][:400]
                for i in range(10, len(segs)):
                    hits += int(conf80.fa_signal(
                        model, segs[i - 8:i], segs[i])["fault_alert"])
                alarms.append({"file": fid,
                               "alarm_rate": round(hits / (len(segs) - 10),
                                                   3)})
            res[cls] = alarms
        pairs.append(res)
    return {"pairs": pairs,
            "seg_seconds": 0.1,
            "machine_year_segments": int(365 * 86400 / 0.1)}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    print("provenance + structure checks ...")
    subs = ["FD001", "FD002", "FD003", "FD004"]
    loads = {s: load_cmapss(s) for s in subs}
    chans = select_degradation_channel(subs)
    cwru_sha_agg = sha256_file(CWRU_DIR / "97.mat")

    print("C-MAPSS coverage + healthy-FA legs ...")
    cmapss_res = {}
    for s in subs:
        ch = chans[s]["channel_1indexed"]
        covs, skips = [], 0
        for u, arr in loads[s]["units"].items():
            r = coverage_and_healthy_fa(cmapss_channel(arr)[:, ch - 1])
            if "coverage" in r:
                covs.append(r)
            else:
                skips += 1
        cov_all = [c["coverage"] for c in covs]
        fa_all = [c["healthy_fa_rate_per_1000_steps"] for c in covs]
        assert cov_all, f"{s}: every unit skipped (typed abort)"
        cmapss_res[s] = {
            "channel_1indexed": ch,
            "n_units_evaluated": len(covs),
            "n_units_skipped_short": skips,
            "coverage_min": round(min(cov_all), 4),
            "coverage_median": round(float(np.median(cov_all)), 4),
            "coverage_max": round(max(cov_all), 4),
            "gate_coverage_ge_090": (
                float(np.median(cov_all)) >= CONF),
            "healthy_fa_median_per_1000":
                round(float(np.median(fa_all)), 3),
        }
        print(f"  {s}: ch{s}.{ch} cov median "
              f"{cmapss_res[s]['coverage_median']} FA/1000 "
              f"{cmapss_res[s]['healthy_fa_median_per_1000']}")

    print("CWRU detection leg (16 files) ...")
    cwru_res = cwru_detection_leg()

    record = {
        "record": "R105S2_P3_STAGE1_REALDATA_SMOKE/1.0.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r105s2",
        "claim": "c-0125 (work_id p3-realdata-conformal-validation, "
                 "kind measurement; OPEN, lease 2026-11-22)",
        "stack": ("the r80 committed conformal-FA prototype "
                  "(scripts/r80_conformal_fa.py importlib-verbatim, "
                  "Ridge+enbpi random_state=17, ensemble=False, "
                  "lags=8) on REAL channels; ZERO foundation models, "
                  "zero LLM, zero generation"),
        "alpha": ALPHA,
        "provenance": {
            "cmapss": {
                "source": "https://phm-datasets.s3.amazonaws.com/NASA/"
                          "6.+Turbofan+Engine+Degradation+Simulation+"
                          "Data+Set.zip (the NASA PCoE repository "
                          "canonical link, read from nasa.gov)",
                "zip_sha256_16": "c9c5dec12a945a82e8bb4446",
                "citation": "A. Saxena and K. Goebel (2008), NASA "
                            "Prognostics Data Repository, NASA Ames "
                            "Research Center (requested citation)",
            },
            "cwru": {
                "source": "https://engineering.case.edu/bearingdata"
                          "center (the 12kHz Drive-End subset: 16 "
                          "files — normals 97-100, IR_007 105-108, "
                          "B_007 118-121, OR_007@6h 130-133)",
                "aggregate_sha256_16": "049ab035a66ac3c9",
                "citation": "Case Western Reserve University Bearing "
                            "Data Center (freely available per the "
                            "site)",
            },
            "xjtu_sy": {
                "citation": "B. Wang, Y. Lei, N. Li, N. Li, IEEE "
                            "Trans. Reliability 69(1):401-412, 2020, "
                            "DOI 10.1109/TR.2018.2882682 (requested)",
                "status": "TYPED OPEN — data acquired (6 RAR parts, "
                          "manifest eval/p3_realdata/"
                          "xjtu_sy_parts_manifest.txt) + listing "
                          "verified (7707 csv files, 9 bearing "
                          "folders: 35Hz12kN x5, 40Hz10kN x4 — a "
                          "PARTIAL set vs the official 15 bearings; "
                          "the Drive folder fetch did not return the "
                          "remaining parts), extraction BLOCKED "
                          "(RAR5 volumes; unrar-free 0.3.1 cannot "
                          "read them; 10.2GB raw vs the 9.9GB "
                          "rootfs). Re-fetch + extract in a window "
                          "with disk/RAR5 headroom.",
            },
        },
        "results": {
            "cmapss": cmapss_res,
            "cwru": cwru_res,
        },
        "gates_table": {
            "note": ("MEASUREMENTS for the auditor's gate verdicts — "
                     "the builder claims NO acceptance; the median-"
                     "inference and matched-budget gates BIND to the "
                     "FM stack (stage 2/3)"),
            "coverage_ge_1_minus_alpha": {
                "cmapss": {s: cmapss_res[s]["gate_coverage_ge_090"]
                           for s in subs},
                "cwru": "the coverage leg on the normal-baseline tail "
                        "is reported per-pair (healthy_fa_per_1000)",
            },
            "fa_le_1_per_machine_year": {
                "unit_typed": ("CWRU cadence 0.1s/segment -> "
                               f"{cwru_res['machine_year_segments']} "
                               "segments per machine-year; C-MAPSS "
                               "cadence is 1 cycle/cycle-row — the "
                               "per-machine-year conversion for "
                               "cycles needs a duty assumption TYPED "
                               "STAGE 3 (not guessed here)"),
            },
            "median_inference_le_2min": "STAGE 2 (the FM stack)",
            "matched_budget_dev_ablation": "STAGE 3",
        },
        "no_acceptance_or_score_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
