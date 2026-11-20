#!/usr/bin/env python3
"""r110_d5_xjtu_stream.py — the R110 direction 5: XJTU-SY extended to
6 bearings via the HF-mirror zip RANGE-FETCH, with the
extract-measure-delete loop running IN MEMORY (peak disk ~= one
member buffer — the 3.3GB ceiling never materializes the ~15GB
uncompressed set).

Protocol: the committed stage-5 walk pair (Bolt arm on the per-minute
RMS channel, sliding k=100/min_prime=20 vs static split-conformal,
fit half + walk half), reused verbatim from
scripts/r105s2_p3_stage5_xjtu.py; per bearing: coverage + alarm rate
WITH Wilson 95% CIs (computed by code), the RMS last/first ratio, and
the minute-step metadata."""
import io
import json
import struct
import sys
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402

import importlib.util  # noqa: E402
_s5 = importlib.util.spec_from_file_location(
    "s5", REPO / "scripts" / "r105s2_p3_stage5_xjtu.py")
s5 = importlib.util.module_from_spec(_s5)
sys.modules["s5"] = s5
_s5.loader.exec_module(s5)

IDX = json.loads((REPO / "eval" / "r110_d5_zip_index.json").read_text())
SEL = json.loads((REPO / "eval" / "r110_d5_selected_members.json")
                 .read_text())
OUT = REPO / "eval" / "r110_d5_xjtu_six_bearings.json"
URL = ("https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_"
       "Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip")
TOKEN = os.environ.get("HF_TOKEN", "")
SPAN_MAX = 32 * 2**20  # the grouped range-fetch cap


def fetch_span(start, length):
    headers = {"Range": f"bytes={start}-{start + length - 1}",
               "User-Agent": "r110s1-stream"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def rms_last_column(csv_bytes):
    """The typed channel: sqrt(mean(vibration^2)) per file — the LAST
    column (the stage-5 rule). pandas C-engine fast path."""
    import pandas as pd
    df = pd.read_csv(io.BytesIO(csv_bytes))
    v = df.iloc[:, -1].to_numpy(dtype=np.float64)
    return float(np.sqrt(np.mean(v ** 2))), int(v.shape[0])


def inflate_member(buf, off):
    """Parse one local header at off inside buf; return (name, raw
    csv bytes) inflated per the method."""
    (sig, _ver, flags, method, _t, _d, _crc, csize, usize,
     nlen, elen) = struct.unpack_from("<IHHHHHIIIHH", buf, off)
    assert sig == 0x04034b50, f"local header sig at {off}"
    name = buf[off + 30:off + 30 + nlen].decode("utf-8", "replace")
    data_start = off + 30 + nlen + elen
    if csize == 0xFFFFFFFF or usize == 0xFFFFFFFF:
        raise RuntimeError("streaming zip64 member unsupported")
    raw = buf[data_start:data_start + csize]
    if method == 0:
        data = raw
    elif method == 8:
        d = zlib.decompressobj(-15)
        data = d.decompress(raw) + d.flush()
    else:
        raise RuntimeError(f"method {method} unsupported")
    return name, data


def group_spans(members):
    """Members sorted by offset -> fetch spans (gap <= 4KB header
    slack; each span <= SPAN_MAX)."""
    spans, cur = [], []
    for m in sorted(members, key=lambda x: x["offset"]):
        if not cur:
            cur = [m]
            continue
        prev_end = cur[-1]["offset"] + cur[-1]["comp_size"] + 4096
        if (m["offset"] <= prev_end
                and (m["offset"] + m["comp_size"]
                     - cur[0]["offset"]) <= SPAN_MAX):
            cur.append(m)
        else:
            spans.append(cur)
            cur = [m]
    if cur:
        spans.append(cur)
    return spans


def stream_bearing(bearing, members, arm, log):
    entries = {}
    spans = group_spans(members)
    log(f"  {bearing}: {len(members)} members in {len(spans)} spans")
    for si, span in enumerate(spans):
        start = span[0]["offset"]
        end = span[-1]["offset"] + span[-1]["comp_size"]
        buf = fetch_span(start, end - start)
        for m in span:
            off = m["offset"] - start
            name, data = inflate_member(buf, off)
            assert name.endswith(".csv"), name
            minute = int(name.split("/")[-1].split(".")[0])
            rms, nrows = rms_last_column(data)
            entries[minute] = (rms, nrows)
            del data
        del buf  # freed AFTER the whole span (the member loop reuses it)
        log(f"    span {si + 1}/{len(spans)} done "
            f"({sum(m['comp_size'] for m in span) // 2**20} MB)")
    minutes = sorted(entries)
    ch = np.asarray([entries[mn][0] for mn in minutes],
                    dtype=np.float64)
    nrows = [entries[mn][1] for mn in minutes]
    log(f"  {bearing}: channel n={len(ch)} "
        f"({minutes[0]}..{minutes[-1]}), "
        f"RMS {ch[0]:.4f} -> {ch[-1]:.4f}")
    pair = s5.walk_pair(ch, arm, bearing)
    return {"n_points": len(ch),
            "minute_index_first": minutes[0],
            "minute_index_last": minutes[-1],
            "rows_per_file_min": min(nrows),
            "rows_per_file_max": max(nrows),
            "rms_first5": [round(float(v), 6) for v in ch[:5]],
            "rms_last5": [round(float(v), 6) for v in ch[-5:]],
            "rms_last_over_first_ratio": round(
                float(ch[-1]) / max(float(ch[0]), 1e-9), 4),
            "protocol_status": pair["status"],
            "sliding": pair["sliding"], "static": pair["static"],
            "protocol_adaptation": pair["adaptation"]}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def with_cis(res):
    for leg in ("sliding", "static"):
        r = res.get(leg) or {}
        n = r.get("n_walk")
        cov = r.get("coverage")
        al = r.get("alarms")
        if n:
            r["coverage_wilson95"] = wilson(round(cov * n), n)
            r["alarm_rate_wilson95"] = wilson(al, n)
    return res


def main():
    log = lambda s: print(s, flush=True)
    results = {}
    log("loading the Chronos-Bolt arm ...")
    arm = s5.p3s2.BoltArm()
    for bearing in sorted(SEL):
        members = SEL[bearing]
        # resolve comp sizes from the index record? The selected-
        # members file carries names only — re-derive sizes from the
        # index record's bearings_found? The index record does not
        # carry per-member sizes; rebuild from a fresh CD read via
        # the index script's parse (import its main? re-run inline).
        members_full = bearing_members(bearing)
        res = stream_bearing(bearing, members_full, arm, log)
        results[bearing] = with_cis(res)
        log(f"  {bearing}: coverage "
            f"{results[bearing]['sliding'].get('coverage')} "
            f"(CI {results[bearing]['sliding'].get(
                'coverage_wilson95')})")
    rec = {
        "record": "R110_D5_XJTU_SIX_BEARINGS/1.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r109s1",
        "direction": "the R110 direction 5",
        "method": ("HF-mirror zip range-fetch (zip64 central "
                   "directory parsed; grouped member spans) — the "
                   "extract-measure-delete loop runs IN MEMORY: one "
                   "member buffer peak, the ~15GB uncompressed set "
                   "never touches disk (the 3.3GB ceiling honored)"),
        "protocol": "the committed stage-5 walk pair, reused verbatim "
                    "(Bolt arm, sliding k=100/min_prime=20 vs static "
                    "split-conformal, fit half + walk half)",
        "n_bearings": len(results),
        "results": results,
        "citation": ("B. Wang, Y. Lei, N. Li, N. Li, IEEE Trans. "
                     "Industrial Electronics — XJTU-SY; fetched from "
                     "the DavidNguyen/XJTU-SY_Bearing_Datasets HF "
                     "mirror (the c-0132 recon's verified source)"),
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    log(f"wrote {OUT} ({len(results)} bearings)")


def bearing_members(bearing):
    """Re-parse the CD for the selected bearing's full member records
    (names + offsets + sizes) — the index script kept names only."""
    import struct as _st
    total = 5447931446
    tail_len = min(total, 65536 + 22)
    tail = fetch_span(total - tail_len, tail_len)
    ecd_off = tail.rfind(b"PK\x05\x06")
    loc = tail.rfind(b"PK\x06\x07", 0, ecd_off)
    z64_eocd_off = _st.unpack_from("<Q", tail, loc + 8)[0]
    blob = fetch_span(z64_eocd_off, 56)
    cd_size = _st.unpack_from("<Q", blob, 40)[0]
    cd_offset = _st.unpack_from("<Q", blob, 48)[0]
    cd = fetch_span(cd_offset, cd_size)
    out, pos = [], 0
    while pos < len(cd) - 46:
        if cd[pos:pos + 4] != b"PK\x01\x02":
            break
        (comp_size, uncomp_size, name_len, extra_len, cmt_len,
         _d1, _d2, _d3, lho) = _st.unpack_from("<IIHHHHHII", cd,
                                               pos + 20)
        method = _st.unpack_from("<H", cd, pos + 10)[0]
        name = cd[pos + 46:pos + 46 + name_len].decode(
            "utf-8", "replace")
        if (0xFFFFFFFF in (comp_size, uncomp_size, lho)):
            ex = cd[pos + 46 + name_len:pos + 46 + name_len
                    + extra_len]
            ep = 0
            while ep + 4 <= len(ex):
                eid, esz = _st.unpack_from("<HH", ex, ep)
                if eid == 0x0001:
                    body = ex[ep + 4:ep + 4 + esz]
                    bp = 0
                    if uncomp_size == 0xFFFFFFFF and bp + 8 <= len(body):
                        uncomp_size = _st.unpack_from("<Q", body,
                                                      bp)[0]
                        bp += 8
                    if comp_size == 0xFFFFFFFF and bp + 8 <= len(body):
                        comp_size = _st.unpack_from("<Q", body, bp)[0]
                        bp += 8
                    if lho == 0xFFFFFFFF and bp + 8 <= len(body):
                        lho = _st.unpack_from("<Q", body, bp)[0]
                        bp += 8
                ep += 4 + esz
        parts = name.split("/")
        if (len(parts) >= 2 and parts[-2] == bearing
                and parts[-1].lower().endswith(".csv")):
            out.append({"name": name, "offset": lho,
                        "comp_size": comp_size,
                        "uncomp_size": uncomp_size,
                        "method": method})
        pos += 46 + name_len + extra_len + cmt_len
    return out


if __name__ == "__main__":
    main()
