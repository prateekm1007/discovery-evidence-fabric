#!/usr/bin/env python3
"""r105s2 P3 stage 5 — the XJTU-SY real-bearing life-course leg
(claim c-0130; auditor direction 7's dataset-model unblock).

THE DATASET: the sampled XJTU-SY run-to-failure life courses (B. Wang,
Y. Lei, N. Li, N. Li, IEEE Trans. Reliability 69(1):401-412, 2020,
DOI 10.1109/TR.2018.2882682 — the requested citation): Bearing3_1 /
Bearing3_2, 25.6 kHz, 1.2 s = 32768 rows per file, one file per minute
of life, sampled under the disk ceiling — 173 csvs total
(Bearing3_2: 100 files, Bearing3_1: 73 files).

VERIFIED STRUCTURE DISCLOSURE (runtime-verified, recorded verbatim):
the task context described 5 columns (Hour, Minute, Second,
Microsecond, vibration); the extracted sample files actually carry a
HEADER + 2 columns (Horizontal_vibration_signals,
Vertical_vibration_signals) — the sampler rewrote the raw 6-column
files. The typed rule "the LAST column is the vibration signal" is
kept: the RMS channel uses the last column
(Vertical_vibration_signals). Verified, not assumed.

FLAT-DIR DISCLOSURE: the sample dir is FLAT (no Bearing3_1/Bearing3_2
subfolders, no manifest; the 6-part RAR was deleted after sampling).
Bearing attribution is RECOVERED inside this script: the sampler
preserved each source file's 2019-01-31 mtime, and the RAR listing
(p3_data_cache/xjtu_sy_listing.txt, minute precision) stores the
archive mtime per (bearing, minute) — each minute index n exists in
BOTH bearings (lives: Bearing3_1 2538 min, Bearing3_2 2496 min, both
counted from the listing), so the per-file mtime decides the bearing.
The attribution is asserted unambiguous (0 ambiguous, 0 no-match) and
dumped to eval/r105s2_p3_stage5_xjtu_attribution.json.

THE MEASUREMENT (typed, stage-3 committed bytes): per bearing —
  1. the life-course channel = RMS of the vibration column per file
     (float64), files ordered by numeric minute index;
  2. p3s3.sliding_walk(channel, arm.predict_batch, k=100, min_prime=20)
     on the FULL channel — fit half, walk half (the degradation side);
  3. p3s3.static_walk on the same channel (the comparison row).

TYPED FLOOR DISCLOSURE: the committed sliding_walk floor
n >= 2*CTX + min_prime = 2*96+20 = 212 blocks channels shorter than
212 points, and the sampled courses (100 / 73 points) violate it. The
walk pair therefore runs FIRST exactly as typed (the AssertionError is
recorded verbatim); on that typed failure, the disclosed per-leg
adaptation re-parameterizes CTX per bearing to the largest value that
satisfies the SAME committed inequality, CTX = min(96, (n-min_prime)//2)
(Bearing3_2: 40, Bearing3_1: 26), with k=100 and min_prime=20 KEPT and
both module CTX constants (p3s3.CTX, p3s2.CTX — static_walk calibrates
through p3s2.fit_resid_q) set consistently; the committed walk function
bytes are otherwise untouched. The thin prime (10 residuals per fit
half) is typed per-leg — the stage-3 docstring's own provision.

ALARM-COUNTING NOTE: the CWRU-style per-machine-year alarm conversion
is typed NOT-APPLICABLE here — the sampled cadence is ~23-27-minute
steps of life, not the native 1-minute cadence, so a
steps-per-machine-year conversion would misstate the duty. Disclosed
in the record, not computed.

NO acceptance claims — measurements for the auditor.
"""
from __future__ import annotations

import argparse
import datetime
import datetime as dt
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
SAMPLE = Path("/home/z/my-project/p3_data_cache/xjtu_sample")
LISTING = Path("/home/z/my-project/p3_data_cache/xjtu_sy_listing.txt")
ATTR_OUT = REPO / "eval" / "r105s2_p3_stage5_xjtu_attribution.json"
OUT = REPO / "eval" / "r105s2_p3_stage5_xjtu_record.json"
CONF = 0.9                       # the committed CONF (stage-3 constant)
K_SLIDE = 100                    # typed
MIN_PRIME = 20                   # typed
CTX_COMMITTED = 96               # the committed stage-2/3 constant
BEARINGS = ["Bearing3_1", "Bearing3_2"]

# the committed protocol modules (stage 3 -> stage 2 -> stage 1)
_s3 = importlib.util.spec_from_file_location(
    "p3s3", REPO / "scripts" / "r105s2_p3_stage3.py")
p3s3 = importlib.util.module_from_spec(_s3)
sys.modules["p3s3"] = p3s3
_s3.loader.exec_module(p3s3)
p3s1 = p3s3.p3s1
p3s2 = p3s3.p3s2

_name_re = re.compile(
    r"^\s+XJTU-SY_Bearing_Datasets/\S+/(Bearing3_[12])/(\d+)\.csv\s*$")
_meta_re = re.compile(
    r"^\s+(\d+)\s+(\d{2})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\s+")


def archive_listing_map() -> dict:
    """(bearing, minute) -> 'HH:MM' archive mtime (minute precision),
    parsed from the RAR listing; also returns the per-bearing file
    counts (the archive lives)."""
    out, pending, lives = {}, None, {}
    for line in LISTING.read_text(errors="replace").splitlines():
        m = _name_re.match(line)
        if m:
            pending = (m.group(1), int(m.group(2)))
            continue
        if pending:
            m2 = _meta_re.match(line)
            if m2:
                out[pending] = f"{m2.group(5)}:{m2.group(6)}"
                lives[pending[0]] = lives.get(pending[0], 0) + 1
                pending = None
    return out, lives


def attribute_files(files: list) -> dict:
    """Flat-dir bearing attribution via the sampler-preserved mtimes
    matched against the RAR listing (see module docstring)."""
    arch, lives = archive_listing_map()
    life = {"Bearing3_1": lives["Bearing3_1"],
            "Bearing3_2": lives["Bearing3_2"]}
    attribution, ambiguous, no_match = {}, [], []
    for f in files:
        n = int(f.stem)
        hhmm = dt.datetime.fromtimestamp(
            f.stat().st_mtime, tz=dt.timezone.utc).strftime("%H:%M")
        cands = [b for b in BEARINGS
                 if arch.get((b, n)) == hhmm and n <= life[b]]
        if len(cands) == 1:
            attribution[f.name] = cands[0]
        elif len(cands) > 1:
            ambiguous.append({"file": f.name, "mtime_hhmm": hhmm,
                              "candidates": cands})
        else:
            no_match.append({"file": f.name, "mtime_hhmm": hhmm,
                             "arch_3_1": arch.get(("Bearing3_1", n)),
                             "arch_3_2": arch.get(("Bearing3_2", n))})
    return {"attribution": attribution, "ambiguous": ambiguous,
            "no_match": no_match, "archive_lives": life}


def load_bearing(files: list) -> tuple:
    """Sampled csvs in minute order -> (rms channel float64, row-count
    min/max). The csvs carry a header; the vibration signal is the LAST
    column (typed rule; verified structure recorded by the caller)."""
    rms, nrows = [], []
    for f in files:
        arr = np.loadtxt(f, delimiter=",", dtype=np.float64, skiprows=1)
        nrows.append(int(arr.shape[0]))
        rms.append(float(np.sqrt(np.mean(arr[:, -1] ** 2))))
    return np.asarray(rms, dtype=np.float64), nrows


def walk_pair(channel: np.ndarray, arm, label: str) -> dict:
    """Attempt the committed walk pair exactly as typed (CTX=96); on the
    typed-floor AssertionError, apply the disclosed per-leg CTX
    adaptation and rerun."""
    n = len(channel)
    p3s3.CTX = CTX_COMMITTED
    p3s2.CTX = CTX_COMMITTED
    typed_err = None
    t0 = time.perf_counter()
    try:
        sl = p3s3.sliding_walk(channel, arm.predict_batch,
                               k=K_SLIDE, min_prime=MIN_PRIME)
        st = p3s3.static_walk(channel, arm.predict_batch)
        status = "typed_protocol_ran_as_committed"
    except AssertionError as e:
        typed_err = str(e)
        sl = st = None
        status = "typed_floor_violation"
    wall_typed = (time.perf_counter() - t0) * 1000.0

    adaptation = None
    if sl is None:
        ctx = min(CTX_COMMITTED, (n - MIN_PRIME) // 2)
        if ctx < 8 or n < 2 * ctx + MIN_PRIME:
            raise RuntimeError(
                f"{label}: n={n} below even the adapted floor "
                f"(2*CTX+min_prime with CTX={ctx})")
        p3s3.CTX = ctx
        p3s2.CTX = ctx
        t0 = time.perf_counter()
        sl = p3s3.sliding_walk(channel, arm.predict_batch,
                               k=K_SLIDE, min_prime=MIN_PRIME)
        st = p3s3.static_walk(channel, arm.predict_batch)
        wall_adapted = (time.perf_counter() - t0) * 1000.0
        adaptation = {
            "reason": (f"sampled channel n={n} < committed floor "
                       f"2*CTX+min_prime={2 * CTX_COMMITTED + MIN_PRIME} "
                       "(the sampled ~23-27-minute cadence, not a "
                       "protocol re-fit)"),
            "ctx_adapted": ctx,
            "ctx_kept_committed_for_typed_attempt": CTX_COMMITTED,
            "k_kept": K_SLIDE,
            "min_prime_kept": MIN_PRIME,
            "committed_inequality_kept": "n >= 2*CTX + min_prime",
            "modules_set_consistently": ["p3s3.CTX", "p3s2.CTX"],
            "committed_walk_bytes_untouched": True,
            "walk_leg_wall_clock_ms": round(wall_adapted, 1),
            "typed_attempt_error_verbatim": typed_err,
            "typed_attempt_wall_clock_ms": round(wall_typed, 1),
        }
        status = "typed_floor_violation_then_disclosed_ctx_adaptation"
    return {"sliding": sl, "static": st, "status": status,
            "adaptation": adaptation}


def parse_args(argv=None):
    """The owner-directed source flag (claim c-0148): --source hf
    streams the committed 173-file sample from the owner's PRIVATE HF
    dataset repo per-file (ephemeral cache, one csv peak); --source
    local (DEFAULT) is the committed flat-dir path, byte-identical
    behavior. The hf implementation lives in
    scripts/r110s2_hf_stage5_source.py (lazily imported — zero import
    cost and zero behavior change on the default path)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["local", "hf"],
                    default="local")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.source == "hf":
        import importlib.util as _ilu
        _hf = _ilu.spec_from_file_location(
            "r110s2_hf_stage5_source",
            Path(__file__).resolve().parent
            / "r110s2_hf_stage5_source.py")
        _hfm = importlib.util.module_from_spec(_hf)
        sys.modules["r110s2_hf_stage5_source"] = _hfm
        _hf.loader.exec_module(_hfm)
        return _hfm.run_hf_source(sys.modules[__name__])
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    # ---- flat-dir attribution + per-bearing channels ----
    all_files = sorted(SAMPLE.glob("*.csv"), key=lambda p: int(p.stem))
    if not all_files:
        raise FileNotFoundError(f"{SAMPLE}: no csv files found")
    att = attribute_files(all_files)
    assert not att["ambiguous"] and not att["no_match"], \
        (f"flat-dir attribution not unambiguous: "
         f"{len(att['ambiguous'])} ambiguous, "
         f"{len(att['no_match'])} no-match — see {ATTR_OUT}")
    n_files = len(all_files)
    print(f"flat-dir attribution: {n_files}/{n_files} csvs -> bearings "
          f"(0 ambiguous, 0 no-match; archive lives "
          f"{att['archive_lives']})", flush=True)
    ATTR_OUT.write_text(json.dumps({
        "method": ("flat xjtu_sample dir (no subfolders, no sampler "
                   "manifest, RAR deleted after sampling); per-file "
                   "attribution via the sampler-preserved source mtimes "
                   "matched against the RAR listing "
                   "(p3_data_cache/xjtu_sy_listing.txt, minute "
                   "precision); each minute index exists in BOTH "
                   "bearings (archive lives in archive_lives)"),
        **att,
        "n_sample_files": n_files,
    }, indent=1) + "\n")

    channels, meta = {}, {}
    for b in BEARINGS:
        bfiles = [f for f in all_files
                  if att["attribution"][f.name] == b]
        ch, nrows = load_bearing(bfiles)
        channels[b] = ch
        minutes = [int(f.stem) for f in bfiles]
        diffs = [minutes[i + 1] - minutes[i]
                 for i in range(len(minutes) - 1)]
        meta[b] = {
            "minute_index_first": minutes[0],
            "minute_index_last": minutes[-1],
            "measured_step_median": sorted(diffs)[len(diffs) // 2],
            "measured_step_min": min(diffs),
            "measured_step_max": max(diffs),
            "rows_per_file_min": min(nrows),
            "rows_per_file_max": max(nrows),
        }
        print(f"  {b}: {len(bfiles)} csvs, minutes "
              f"{minutes[0]}..{minutes[-1]}, step median "
              f"{meta[b]['measured_step_median']} "
              f"(range {min(diffs)}..{max(diffs)}), rows/file "
              f"{min(nrows)}-{max(nrows)}, RMS {ch[0]:.4f} -> "
              f"{ch[-1]:.4f}", flush=True)

    # ---- the typed CSV-structure verification (verbatim) ----
    vfile = [f for f in all_files
             if att["attribution"][f.name] == BEARINGS[0]][0]
    with open(vfile, "r") as fh:
        first_two = [next(fh).rstrip("\n") for _ in range(2)]
    n_cols = len(first_two[1].split(","))
    print(f"  structure verification ({BEARINGS[0]}/{vfile.name}): "
          f"header={first_two[0]!r}, {n_cols} data columns",
          flush=True)

    # ---- the FM arm (the Chronos-Bolt cache must be refetched first) ----
    print("loading the Chronos-Bolt arm (amazon/chronos-bolt-base) ...",
          flush=True)
    arm = p3s2.BoltArm()

    # ---- the typed per-bearing protocol ----
    results, honest_flags = {}, []
    for b in BEARINGS:
        ch = channels[b]
        n = len(ch)
        print(f"[{b}] n_points={n} — typed walk pair "
              f"(sliding k={K_SLIDE} min_prime={MIN_PRIME} vs static) ...",
              flush=True)
        pair = walk_pair(ch, arm, b)
        first5 = [round(float(v), 6) for v in ch[:5]]
        last5 = [round(float(v), 6) for v in ch[-5:]]
        ratio = float(np.mean(ch[-5:]) / np.mean(ch[:5]))
        entry = {"n_points": n,
                 "minute_index_first": meta[b]["minute_index_first"],
                 "minute_index_last": meta[b]["minute_index_last"],
                 "measured_step_median": meta[b]["measured_step_median"],
                 "rows_per_file_min": meta[b]["rows_per_file_min"],
                 "rows_per_file_max": meta[b]["rows_per_file_max"],
                 "rms_first5": first5, "rms_last5": last5,
                 "rms_last_over_first_ratio": round(ratio, 4),
                 "protocol_status": pair["status"],
                 "sliding": pair["sliding"], "static": pair["static"]}
        if pair["adaptation"] is not None:
            entry["protocol_adaptation"] = pair["adaptation"]
        results[b] = entry
        print(f"  {b}: sliding cov {pair['sliding']['coverage']} "
              f"alarms {pair['sliding']['alarms']} "
              f"(per1000 {pair['sliding']['alarms_per_1000']}) | "
              f"static cov {pair['static']['coverage']} "
              f"alarms {pair['static']['alarms']} "
              f"(per1000 {pair['static']['alarms_per_1000']}) | "
              f"rms last/first x{ratio:.3f}", flush=True)
        if ratio < 1.05:
            honest_flags.append(
                f"{b}: mean(last5 RMS) is only {ratio * 100:.1f}% of "
                "mean(first5 RMS) (<105%) — the sampled segment may not "
                "span the degradation onset")

    # ---- the record ----
    honest_note = (
        "the RMS life-course is non-stationary (run-to-failure); the "
        "sliding-vs-static comparison is the drift lesson re-measured on "
        "real bearing data")
    if honest_flags:
        honest_note += " | " + "; ".join(honest_flags)

    record = {
        "record": "R105S2_P3_STAGE5_XJTU/1.0.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r105s2",
        "claim": "c-0130 (p3-datasets-model-d7d8; auditor direction 7)",
        "dataset": {
            "sample_dir": "/home/z/my-project/p3_data_cache/xjtu_sample",
            "n_files": n_files,
            "bearings": {b: sum(1 for f in all_files
                                if att["attribution"][f.name] == b)
                         for b in BEARINGS},
            "sampled_cadence_typed": (
                "every 25th (Bearing3_2) / 30th (Bearing3_1) minute of "
                "life — a SAMPLE within the disk ceiling; the "
                "full-resolution re-extract is typed when disk allows"),
            "measured_cadence_disclosure": {
                "note": ("the typed cadence above did not match the "
                         "extracted sample exactly; the measured "
                         "minute-index steps are recorded per bearing "
                         "(the sample is irregular, not fixed-cadence)"),
                **{b: {"files": sum(1 for f in all_files
                                    if att["attribution"][f.name] == b),
                       "minute_index_first": meta[b]["minute_index_first"],
                       "minute_index_last": meta[b]["minute_index_last"],
                       "step_median": meta[b]["measured_step_median"],
                       "step_range": [meta[b]["measured_step_min"],
                                      meta[b]["measured_step_max"]]}
                   for b in BEARINGS},
                "archive_lives_minutes": att["archive_lives"],
            },
            "flat_dir_attribution": {
                "note": ("the task context described Bearing3_1/"
                         "Bearing3_2 subfolders; the sample dir is "
                         "FLAT (no subfolders, no sampler manifest, "
                         "RAR deleted after sampling). Attribution "
                         "recovered via the sampler-preserved source "
                         "mtimes vs the RAR listing (minute precision) "
                         "— asserted unambiguous here; full map in "
                         "eval/r105s2_p3_stage5_xjtu_attribution.json"),
                "n_ambiguous": 0, "n_no_match": 0,
            },
            "citation": (
                "B. Wang, Y. Lei, N. Li, N. Li, IEEE Trans. Reliability "
                "69(1):401-412, 2020, DOI 10.1109/TR.2018.2882682 "
                "(requested citation)"),
            "extraction": (
                "7zz 25.01 (static binary, /home/z/my-project/tools/7zz) "
                "from the 6-part RAR5 set — the unblock the auditor "
                "direction 7 asked for"),
            "csv_structure_verified": {
                "file": f"{BEARINGS[0]}/{vfile.name}",
                "first_two_lines": first_two,
                "note": ("the task context described 5 columns (Hour, "
                         "Minute, Second, Microsecond, vibration); the "
                         "extracted sample actually carries a header + "
                         "2 columns (Horizontal_vibration_signals, "
                         "Vertical_vibration_signals) — the sampler "
                         "rewrote the raw 6-column files"),
                "n_data_columns": n_cols,
                "rows_per_file": [meta[BEARINGS[0]]["rows_per_file_min"],
                                  meta[BEARINGS[0]]["rows_per_file_max"]],
                "rms_column": ("last column (Vertical_vibration_signals) "
                               "— the typed 'last column is the "
                               "vibration signal' rule, kept"),
            },
            "alarm_per_machine_year_conversion": (
                "NOT-APPLICABLE: the sampled cadence is ~23-27-minute "
                "intervals of life, not the native 1-minute cadence — "
                "the CWRU-style per-machine-year conversion would "
                "misstate the duty; disclosed, not computed"),
        },
        "protocol_typed": {
            "channel": "RMS of the vibration column per file (float64), "
                       "files ordered by numeric minute index",
            "walk": "stage-3 committed sliding_walk vs static_walk on "
                    "the FULL channel — fit half, walk half (the "
                    "degradation side)",
            "sliding": f"k={K_SLIDE}, min_prime={MIN_PRIME} (typed)",
            "static": "split-conformal fit-once q (p3s2.fit_resid_q)",
            "arm": "chronos-bolt-base (p3s2.BoltArm, one-shot "
                   "predict_batch on the context matrix)",
            "ctx_committed": CTX_COMMITTED,
        },
        "results": results,
        "honest_note": honest_note,
        "no_acceptance_claims": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
