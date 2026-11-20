#!/usr/bin/env python3
"""r105s2 P3 stage 5 — the XJTU-SY real-bearing life-course leg
(claim c-0130; auditor direction 7's dataset-model unblock).

THE DATASET: the sampled XJTU-SY run-to-failure life courses (B. Wang,
Y. Lei, N. Li, N. Li, IEEE Trans. Reliability 69(1):401-412, 2020,
DOI 10.1109/TR.2018.2882682 — the requested citation): Bearing3_1 /
Bearing3_2, 25.6 kHz, 1.2 s = 32768 rows per file, one file per minute
of life, sampled under the disk ceiling — 173 csvs total
(Bearing3_2: 100 files, Bearing3_1: 73 files).

SOURCES (claim c-0148 adds the HF streaming path, --source hf|local):
  local (default, byte-compat): the flat sample dir
    /home/z/my-project/p3_data_cache/xjtu_sample (173 csvs) — the
    original disk-bound path, kept for sandbox environments with the
    sample on disk.
  hf (claim c-0148 item (4)): per-bearing CSVs streamed from the
    PRIVATE dataset repo prateekm1/xjtu-sy-bearing-rar (the verified
    DavidNguyen mirror zip's members, uploaded per the flat canonical
    layout; sha256 integrity manifest at eval/xjtu_sy_hf_manifest.json
    + the repo root). The sampled minute SET is pinned by the committed
    attribution record (eval/r105s2_p3_stage5_xjtu_attribution.json —
    73 + 100 files), so the HF path reproduces the committed sample
    exactly without any local sample bytes. Each file is fetched into
    /tmp/hf_cache_stage5, read, and DELETED immediately (peak local
    footprint = one csv, ~1.5MB — the ~15GB uncompressed set and the
    3.3GB sandbox ceiling never meet). Attribution on the HF path is
    inherent (per-bearing folders) and CROSS-CHECKED against the
    committed attribution record (counts + every minute index).

VERIFIED STRUCTURE DISCLOSURE (runtime-verified, recorded verbatim):
the task context described 5 columns (Hour, Minute, Second,
Microsecond, vibration); the extracted sample files actually carry a
HEADER + 2 columns (Horizontal_vibration_signals,
Vertical_vibration_signals) — the sampler rewrote the raw 6-column
files. The typed rule "the LAST column is the vibration signal" is
kept: the RMS channel uses the last column
(Vertical_vibration_signals). Verified, not assumed. The HF path
re-verifies the structure on ITS OWN bytes (the mirror zip's csvs).

FLAT-DIR DISCLOSURE (local path only): the sample dir is FLAT (no
Bearing3_1/Bearing3_2 subfolders, no manifest; the 6-part RAR was
deleted after sampling). Bearing attribution is RECOVERED inside this
script: the sampler preserved each source file's 2019-01-31 mtime, and
the RAR listing (p3_data_cache/xjtu_sy_listing.txt, minute precision)
stores the archive mtime per (bearing, minute) — each minute index n
exists in BOTH bearings (lives: Bearing3_1 2538 min, Bearing3_2 2496
min, both counted from the listing), so the per-file mtime decides the
bearing. The attribution is asserted unambiguous (0 ambiguous, 0
no-match) and dumped to eval/r105s2_p3_stage5_xjtu_attribution.json.
The HF path stores files under per-bearing folders, so the mtime
recovery is not needed there — but the committed attribution map is
cross-checked (count per bearing + every minute) and the assertion
kept.

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
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

# the r110s2 path-robustness fix-forward (VERIFIER, typed + disclosed):
# the rewrite re-introduced the r105s2 session's hardcoded checkout
# path; the worktree-safe value is the script's own parent (the
# same deviation class as the r108s2 cred-helper path pin; the twin
# window's sandbox masked the defect). SAMPLE/LISTING stay absolute
# (local-branch-only paths; the --source hf branch never touches them).
REPO = Path(__file__).resolve().parents[1]
SAMPLE = Path("/home/z/my-project/p3_data_cache/xjtu_sample")
LISTING = Path("/home/z/my-project/p3_data_cache/xjtu_sy_listing.txt")
ATTR_OUT = REPO / "eval" / "r105s2_p3_stage5_xjtu_attribution.json"
ATTR_COMMITTED = REPO / "eval" / "r105s2_p3_stage5_xjtu_attribution.json"
OUT = REPO / "eval" / "r105s2_p3_stage5_xjtu_record.json"
HF_MANIFEST = REPO / "eval" / "xjtu_sy_hf_manifest.json"
HF_REPO_DEFAULT = "prateekm1/xjtu-sy-bearing-rar"
HF_TMP = Path("/tmp/hf_cache_stage5")
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


def _hf_repo_id() -> str:
    """The repo id from the committed integrity manifest (bytes over
    claims); the default is the claim-c-0148 repo."""
    if HF_MANIFEST.exists():
        rid = json.loads(HF_MANIFEST.read_text()).get("repo_id")
        if rid:
            return rid
    return HF_REPO_DEFAULT


def hf_fetch_csv(rel: str, repo_id: str) -> bytes:
    """ONE csv from the private HF dataset repo, fetched to /tmp,
    read, DELETED — the streaming seam the mock CI fixture patches.
    Peak local footprint: one csv."""
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from huggingface_hub import hf_hub_download
    HF_TMP.mkdir(parents=True, exist_ok=True)
    p = Path(hf_hub_download(repo_id=repo_id, filename=rel,
                             repo_type="dataset", token=os.environ.get(
                                 "HF_TOKEN", ""),
                             local_dir=str(HF_TMP)))
    data = p.read_bytes()
    p.unlink(missing_ok=True)
    return data


def rms_from_csv_bytes(data: bytes) -> tuple:
    """(rms of the LAST column, n_rows) — the typed channel rule, on
    csv bytes (header kept)."""
    arr = np.loadtxt(io.BytesIO(data), delimiter=",",
                     dtype=np.float64, skiprows=1)
    return float(np.sqrt(np.mean(arr[:, -1] ** 2))), int(arr.shape[0])


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
    return out


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


def load_source_local() -> dict:
    """The original disk-bound path (byte-compat)."""
    all_files = sorted(SAMPLE.glob("*.csv"), key=lambda p: int(p.stem))
    if not all_files:
        raise FileNotFoundError(f"{SAMPLE}: no csv files found")
    att = attribute_files(all_files)
    assert not att["ambiguous"] and not att["no_match"], \
        (f"flat-dir attribution not unambiguous: "
         f"{len(att['ambiguous'])} ambiguous, "
         f"{len(att['no_match'])} no-match — see {ATTR_OUT}")
    ATTR_OUT.write_text(json.dumps({
        "method": ("flat xjtu_sample dir (no subfolders, no sampler "
                   "manifest, RAR deleted after sampling); per-file "
                   "attribution via the sampler-preserved source mtimes "
                   "matched against the RAR listing "
                   "(p3_data_cache/xjtu_sy_listing.txt, minute "
                   "precision); each minute index exists in BOTH "
                   "bearings (archive lives in archive_lives)"),
        **att,
        "n_sample_files": len(all_files),
    }, indent=1) + "\n")
    channels, meta, minutes_by_bearing = {}, {}, {}
    for b in BEARINGS:
        bfiles = [f for f in all_files
                  if att["attribution"][f.name] == b]
        ch, nrows = load_bearing(bfiles)
        channels[b] = ch
        minutes = [int(f.stem) for f in bfiles]
        minutes_by_bearing[b] = minutes
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
    # ---- the typed CSV-structure verification (verbatim) ----
    vfile = [f for f in all_files
             if att["attribution"][f.name] == BEARINGS[0]][0]
    with open(vfile, "r") as fh:
        first_two = [next(fh).rstrip("\n") for _ in range(2)]
    struct_info = {"file": f"{BEARINGS[0]}/{vfile.name}",
                   "first_two_lines": first_two,
                   "n_data_columns": len(first_two[1].split(","))}
    return {"att": att, "channels": channels, "meta": meta,
            "minutes_by_bearing": minutes_by_bearing,
            "struct": struct_info, "n_files": len(all_files),
            "rows": {b: None for b in BEARINGS}}


def load_source_hf() -> dict:
    """The c-0148 streaming path: the sampled minute set is pinned by
    the COMMITTED attribution record; each csv is fetched from the
    private HF repo, hashed, RMS'd, deleted. Attribution is inherent
    (per-bearing folders) and cross-checked against the committed map;
    every fetched file's sha256 is cross-checked against the committed
    manifest when it covers the file."""
    repo_id = _hf_repo_id()
    committed = json.loads(ATTR_COMMITTED.read_text())
    att_map = committed["attribution"]
    # the committed keys are the flat sample filenames ("47.csv")
    by_bearing = {b: sorted((int(f[:-4]) for f, bb in att_map.items()
                             if bb == b)) for b in BEARINGS}
    counts = {b: len(by_bearing[b]) for b in BEARINGS}
    assert counts == {"Bearing3_1": 73, "Bearing3_2": 100}, \
        f"committed attribution counts drifted: {counts}"
    lives = committed["archive_lives"]
    for b in BEARINGS:
        for n in by_bearing[b]:
            assert 1 <= n <= lives[b], \
                f"{b}: minute {n} outside the archive life {lives[b]}"
    mf = json.loads(HF_MANIFEST.read_text()) if HF_MANIFEST.exists() \
        else {"files": {}}
    mf_files = mf.get("files", {})
    channels, meta, minutes_by_bearing = {}, {}, {}
    fetched, sha_checked, sha_mismatch = 0, 0, []
    struct_info = None
    for b in BEARINGS:
        rms, nrows = [], []
        minutes = by_bearing[b]
        minutes_by_bearing[b] = minutes
        for n in minutes:
            rel = f"{b}/{n}.csv"
            data = hf_fetch_csv(rel, repo_id)
            fetched += 1
            entry = mf_files.get(rel)
            if entry:
                sha_checked += 1
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    sha_mismatch.append(rel)
            if b == BEARINGS[0] and n == minutes[0] and struct_info \
                    is None:
                lines = data.decode("utf-8", "replace").splitlines()
                struct_info = {"file": f"{b}/{n}.csv (HF repo {repo_id})",
                               "first_two_lines":
                                   lines[0:2] if len(lines) >= 2 else lines,
                               "n_data_columns":
                                   len(lines[1].split(","))
                                   if len(lines) >= 2 else None}
            r, nr = rms_from_csv_bytes(data)
            rms.append(r)
            nrows.append(nr)
            del data
        channels[b] = np.asarray(rms, dtype=np.float64)
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
    assert not sha_mismatch, \
        f"HF bytes disagree with the committed manifest: {sha_mismatch}"
    att = {"attribution": {f"{b}/{n}.csv": b
                           for b in BEARINGS for n in by_bearing[b]},
           "ambiguous": [], "no_match": [],
           "archive_lives": dict(lives)}
    return {"att": att, "channels": channels, "meta": meta,
            "minutes_by_bearing": minutes_by_bearing,
            "struct": struct_info, "n_files": fetched,
            "rows": {"sha256_checked": sha_checked,
                     "mismatches": len(sha_mismatch),
                     "manifest_coverage": f"{sha_checked}/{fetched}"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["local", "hf"], default="local",
                    help="local: the flat sample dir (byte-compat "
                         "default); hf: stream the pinned sample from "
                         "the private dataset repo (claim c-0148)")
    args = ap.parse_args()
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    if args.source == "local":
        src = load_source_local()
        print(f"flat-dir attribution: {src['n_files']}/{src['n_files']} "
              f"csvs -> bearings (0 ambiguous, 0 no-match; archive "
              f"lives {src['att']['archive_lives']})", flush=True)
        dataset_source_block = {
            "sample_dir": str(SAMPLE),
            "extraction": (
                "7zz 25.01 (static binary, /home/z/my-project/tools/7zz) "
                "from the 6-part RAR5 set — the unblock the auditor "
                "direction 7 asked for"),
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
        }
    else:
        src = load_source_hf()
        repo_id = _hf_repo_id()
        print(f"HF streaming: {src['n_files']} csvs fetched+deleted "
              f"(one at a time) from {repo_id}; sha256 checked "
              f"{src['rows']['sha256_checked']}/{src['n_files']} "
              f"against the committed manifest", flush=True)
        dataset_source_block = {
            "hf_repo": repo_id,
            "hf_repo_type": "dataset",
            "streaming_mode": "per-bearing-folder, one csv at a time "
                              "(fetch -> RMS -> delete; peak local "
                              "footprint = one csv)",
            "tmp_dir": str(HF_TMP) + " (cleaned after the run)",
            "sample_selection": ("pinned by the committed attribution "
                                 "record (73 + 100 minutes), so the HF "
                                 "path reproduces the committed 173-file "
                                 "sample exactly"),
            "integrity": src["rows"],
            "flat_dir_attribution": {
                "note": ("not needed on the HF path: files are stored "
                         "under per-bearing folders; the committed "
                         "attribution map is cross-checked (counts + "
                         "archive-life bounds) and kept"),
                "n_ambiguous": 0, "n_no_match": 0,
            },
        }

    channels, meta, att = src["channels"], src["meta"], src["att"]
    struct_info = src["struct"]
    for b in BEARINGS:
        ch = channels[b]
        minutes = src["minutes_by_bearing"][b]
        print(f"  {b}: {len(minutes)} csvs, minutes "
              f"{minutes[0]}..{minutes[-1]}, step median "
              f"{meta[b]['measured_step_median']}, rows/file "
              f"{meta[b]['rows_per_file_min']}-"
              f"{meta[b]['rows_per_file_max']}, RMS {ch[0]:.4f} -> "
              f"{ch[-1]:.4f}", flush=True)
    print(f"  structure verification ({struct_info['file']}): "
          f"header={struct_info['first_two_lines'][0]!r}, "
          f"{struct_info['n_data_columns']} data columns", flush=True)

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

    # ---- the acceptance block (claim c-0148 item (5)) ----
    acceptance = None
    if args.source == "hf":
        import subprocess
        base = json.loads(subprocess.run(
            ["git", "-C", str(REPO), "show",
             "HEAD:eval/r105s2_p3_stage5_xjtu_record.json"],
            capture_output=True, text=True, check=True).stdout)
        diffs = []
        for b in BEARINGS:
            for field in ("n_points", "minute_index_first",
                          "minute_index_last", "rows_per_file_min",
                          "rows_per_file_max", "protocol_status",
                          "rms_first5", "rms_last5"):
                if results[b].get(field) != base["results"][b].get(field):
                    diffs.append(f"{b}.{field}: "
                                 f"{base['results'][b].get(field)} -> "
                                 f"{results[b].get(field)}")
            for leg in ("sliding", "static"):
                for field in ("n_walk", "coverage", "alarms",
                              "alarms_per_1000"):
                    if (results[b][leg].get(field)
                            != base["results"][b][leg].get(field)):
                        diffs.append(f"{b}.{leg}.{field}: "
                                     f"{base['results'][b][leg].get(field)}"
                                     f" -> "
                                     f"{results[b][leg].get(field)}")
        acceptance = {
            "target": ("the stage-5 walk pair executed from HF-sourced "
                       "bytes must match the committed 173-file sample "
                       "numbers (claim c-0148 item (5))"),
            "committed_record_sha256": hashlib.sha256(
                json.dumps(base, sort_keys=True,
                           ensure_ascii=False).encode()).hexdigest(),
            "fields_compared": ("per bearing: n_points, minute bounds, "
                                "rows/file bounds, protocol_status, "
                                "rms_first5/last5, per leg: n_walk, "
                                "coverage, alarms, alarms_per_1000"),
            "identical": not diffs,
            "diffs": diffs,
        }
        print(f"acceptance vs committed 173-file numbers: "
              f"{'IDENTICAL' if not diffs else str(len(diffs)) + ' DIFFS'}",
              flush=True)

    # ---- the record ----
    honest_note = (
        "the RMS life-course is non-stationary (run-to-failure); the "
        "sliding-vs-static comparison is the drift lesson re-measured on "
        "real bearing data")
    if honest_flags:
        honest_note += " | " + "; ".join(honest_flags)

    record = {
        "record": "R105S2_P3_STAGE5_XJTU/1.1.0",
        "ran_at": f"{now} (sandbox clock, TRUE UTC)",
        "executor": "builder-r109s2",
        "claim": "c-0130 (p3-datasets-model-d7d8; auditor direction 7)"
                 if args.source == "local" else
                 "c-0148 item (4)+(5): the HF streaming path",
        "data_source": ("local_sample_dir" if args.source == "local"
                        else "hf_streaming"),
        "hf_streaming": None if args.source == "local" else {
            "data_source": "hf_streaming",
            "hf_repo": _hf_repo_id(),
            "hf_repo_type": "dataset",
            "streaming_mode": "per-bearing-folder",
            "max_local_footprint_mb": 2,
            "max_local_footprint_note": (
                "steady-state peak = ONE csv (~1.5MB) held in /tmp, "
                "deleted immediately after its RMS is taken; the "
                "one-span upload/manifest buffers (<=64MB) belong to "
                "the upload lane, not this loader"),
            "integrity_check": "sha256 per file vs the committed "
                               "manifest (eval/xjtu_sy_hf_manifest.json "
                               "+ the repo root copy)",
            "manifest_file": "eval/xjtu_sy_hf_manifest.json",
        },
        "dataset": {
            "n_files": src["n_files"],
            "bearings": {b: sum(1 for f, bb in att["attribution"].items()
                                if bb == b) for b in BEARINGS},
            "sampled_cadence_typed": (
                "every 25th (Bearing3_2) / 30th (Bearing3_1) minute of "
                "life — a SAMPLE within the disk ceiling; the "
                "full-resolution re-extract is typed when disk allows"),
            "measured_cadence_disclosure": {
                "note": ("the typed cadence above did not match the "
                         "extracted sample exactly; the measured "
                         "minute-index steps are recorded per bearing "
                         "(the sample is irregular, not fixed-cadence)"),
                **{b: {"files": sum(1 for f, bb in
                                    att["attribution"].items()
                                    if bb == b),
                       "minute_index_first": meta[b]["minute_index_first"],
                       "minute_index_last": meta[b]["minute_index_last"],
                       "step_median": meta[b]["measured_step_median"],
                       "step_range": [meta[b]["measured_step_min"],
                                      meta[b]["measured_step_max"]]}
                   for b in BEARINGS},
                "archive_lives_minutes": att["archive_lives"],
            },
            "citation": (
                "B. Wang, Y. Lei, N. Li, N. Li, IEEE Trans. Reliability "
                "69(1):401-412, 2020, DOI 10.1109/TR.2018.2882682 "
                "(requested citation)"),
            "csv_structure_verified": {
                "file": struct_info["file"],
                "first_two_lines": struct_info["first_two_lines"],
                "note": ("the task context described 5 columns (Hour, "
                         "Minute, Second, Microsecond, vibration); the "
                         "extracted sample actually carries a header + "
                         "2 columns (Horizontal_vibration_signals, "
                         "Vertical_vibration_signals) — the sampler "
                         "rewrote the raw 6-column files"),
                "n_data_columns": struct_info["n_data_columns"],
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
            **dataset_source_block,
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
        "acceptance_vs_committed": acceptance,
        "honest_note": honest_note,
        "no_acceptance_claims": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
