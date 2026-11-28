#!/usr/bin/env python3
"""r105s2 P3 stage 5 helper — recover the Bearing3_1/Bearing3_2
attribution of the FLAT xjtu_sample dir (173 csvs, no subfolders —
the sampler that built it left no manifest and the 6-part RAR was
deleted after sampling).

The recovery signal: the sample files' filesystem mtimes are preserved
2019-01-31 timestamps that match the per-file mtimes stored INSIDE the
original RAR (xjtu_sy_listing.txt, minute precision) — i.e. the
sampler rewrote the csvs (6 raw cols -> 2 cols + header) but carried
the source file's mtime over. Each minute index n exists in BOTH
bearings (Bearing3_1 life 2538 min, Bearing3_2 life 2496 min), so the
per-file archive time decides which bearing a flat sample file came
from — with the ambiguity rate printed, not assumed.

Outputs: an attribution map JSON + stdout diagnostics.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

SAMPLE = Path("/home/z/my-project/p3_data_cache/xjtu_sample")
LISTING = Path("/home/z/my-project/p3_data_cache/xjtu_sy_listing.txt")
OUT = Path("/home/z/my-project/discovery-evidence-fabric/eval/"
           "r105s2_p3_stage5_xjtu_attribution.json")

LIFE = {"Bearing3_1": 2538, "Bearing3_2": 2496}

name_re = re.compile(
    r"^\s+XJTU-SY_Bearing_Datasets/\S+/(Bearing3_[12])/(\d+)\.csv\s*$")
meta_re = re.compile(
    r"^\s+(\d+)\s+(\d{2})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\s+")


def parse_listing():
    """(bearing, minute) -> 'HH:MM' archive mtime (minute precision)."""
    out, pending = {}, None
    for line in LISTING.read_text(errors="replace").splitlines():
        m = name_re.match(line)
        if m:
            pending = (m.group(1), int(m.group(2)))
            continue
        if pending:
            m2 = meta_re.match(line)
            if m2:
                out[pending] = f"{m2.group(5)}:{m2.group(6)}"
                pending = None
    return out


def main():
    arch = parse_listing()
    n_by_bearing = {}
    for (b, _m) in arch:
        n_by_bearing[b] = n_by_bearing.get(b, 0) + 1
    print(f"listing parse: {len(arch)} files -> {n_by_bearing} "
          f"(archive lives; expected {LIFE})", flush=True)

    files = sorted(SAMPLE.glob("*.csv"), key=lambda p: int(p.stem))
    print(f"sample dir: {len(files)} csvs", flush=True)

    attribution, ambiguous, no_match = {}, [], []
    for f in files:
        n = int(f.stem)
        st = f.stat()
        hhmm = dt.datetime.fromtimestamp(
            st.st_mtime, tz=dt.timezone.utc).strftime("%H:%M")
        cands = [b for b in LIFE
                 if arch.get((b, n)) == hhmm and n <= LIFE[b]]
        if len(cands) == 1:
            attribution[f.name] = cands[0]
        elif len(cands) > 1:
            ambiguous.append({"file": f.name, "mtime_hhmm": hhmm,
                              "candidates": cands})
        else:
            no_match.append({"file": f.name, "mtime_hhmm": hhmm,
                             "arch_3_1": arch.get(("Bearing3_1", n)),
                             "arch_3_2": arch.get(("Bearing3_2", n))})
    print(f"attributed: {len(attribution)}  ambiguous: {len(ambiguous)}  "
          f"no-match: {len(no_match)}", flush=True)
    if ambiguous:
        print(f"  ambiguous sample: {ambiguous[:10]}", flush=True)
    if no_match:
        print(f"  no-match sample: {no_match[:10]}", flush=True)

    groups = {"Bearing3_1": [], "Bearing3_2": []}
    for name, b in attribution.items():
        groups[b].append(int(name[:-4]))
    for b, ns in groups.items():
        ns.sort()
        diffs = [ns[i + 1] - ns[i] for i in range(len(ns) - 1)]
        print(f"{b}: {len(ns)} files, minutes {ns[0]}..{ns[-1]}, "
              f"diff min/median/max = "
              f"{min(diffs)}/{sorted(diffs)[len(diffs) // 2]}/{max(diffs)}",
              flush=True)
        print(f"  first 15: {ns[:15]}", flush=True)
        print(f"  last 5: {ns[-5:]}", flush=True)

    OUT.write_text(json.dumps({
        "method": ("flat xjtu_sample dir; per-file attribution via the "
                   "sampler-preserved source mtimes matched against the "
                   "RAR listing (xjtu_sy_listing.txt, minute precision); "
                   "the 6-part RAR itself was deleted after sampling"),
        "archive_lives": n_by_bearing,
        "n_sample_files": len(files),
        "n_attributed": len(attribution),
        "n_ambiguous": len(ambiguous),
        "n_no_match": len(no_match),
        "ambiguous": ambiguous,
        "no_match": no_match,
        "attribution": attribution,
    }, indent=1) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
