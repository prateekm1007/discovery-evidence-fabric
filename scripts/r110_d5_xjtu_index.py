#!/usr/bin/env python3
"""r110_d5_xjtu_index.py — the Dir-5 stage 1: read the HF-mirror zip's
central directory by range-fetch (the tail), build the member index,
and select >=6 bearings (typed rule: per operating condition, the
bearings with n>=192 csv members, the FIRST 2 by index — deterministic;
the CTX=96 protocol floor). Prints the selection + byte budget; the
extract-measure-delete loop consumes this index."""
import json
import struct
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402

URL = ("https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_"
       "Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip")
TOKEN = os.environ.get("HF_TOKEN", "")
MIN_FILES = 192  # the CTX=96 floor: n >= 2*96 + 20 per the committed rule
OUT = REPO / "eval" / "r110_d5_zip_index.json"


def fetch_range(start, length):
    end = start + length - 1
    headers = {"Range": f"bytes={start}-{end}", "User-Agent": "r110s1"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    # probe total size via HEAD (follow the redirect chain the resolve
    # endpoint produces)
    req = urllib.request.Request(URL, headers={"User-Agent": "r110s1",
                                               "Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        cr = r.headers.get("Content-Range", "")
        total = int(cr.rsplit("/", 1)[1]) if "/" in cr else None
        final_url = r.geturl()
    print("total:", total, "| final host:", final_url.split("/")[2])
    assert total, "no Content-Range on the probe"

    # EOCD: scan the last 64KB+22 bytes for the signature
    tail_len = min(total, 65536 + 22)
    tail = fetch_range(total - tail_len, tail_len)
    ecd_off = tail.rfind(b"PK\x05\x06")
    assert ecd_off >= 0, "EOCD not found in the tail"
    # zip64: the locator (PK\x06\x07) sits immediately before the EOCD;
    # it points at the zip64 EOCD (PK\x06\x06) which carries the REAL
    # cd offset/size in 8-byte fields
    z64_cd_size = z64_cd_offset = z64_n = None
    loc = tail.rfind(b"PK\x06\x07", 0, ecd_off)
    if loc >= 0:
        z64_eocd_off = struct.unpack_from("<Q", tail, loc + 8)[0]
        blob = fetch_range(z64_eocd_off, 56)
        assert blob[:4] == b"PK\x06\x06", "zip64 EOCD signature missing"
        z64_n = struct.unpack_from("<Q", blob, 32)[0]
        z64_cd_size = struct.unpack_from("<Q", blob, 40)[0]
        z64_cd_offset = struct.unpack_from("<Q", blob, 48)[0]
        n_entries, cd_size, cd_offset = z64_n, z64_cd_size, z64_cd_offset
        print("zip64: entries", z64_n, "cd_size", z64_cd_size,
              "cd_offset", z64_cd_offset)
    else:
        n_entries = struct.unpack_from("<H", tail, ecd_off + 10)[0]
        cd_size = struct.unpack_from("<I", tail, ecd_off + 12)[0]
        cd_offset = struct.unpack_from("<I", tail, ecd_off + 16)[0]
        print("zip32: entries", n_entries, "cd_size", cd_size,
              "cd_offset", cd_offset)
    assert cd_offset > 0 and cd_size > 0, "CD location not resolved"
    print("entries:", n_entries, "| cd size:", cd_size,
          "| cd offset:", cd_offset)
    cd = fetch_range(cd_offset, min(cd_size, 200_000_000))
    assert len(cd) == cd_size, "CD fetch truncated"

    members, pos = [], 0
    while pos < len(cd) - 46:
        if cd[pos:pos + 4] != b"PK\x01\x02":
            break
        (comp_size, uncomp_size, name_len, extra_len, cmt_len,
         _disk, _iattr, _eattr, lho) = struct.unpack_from(
            "<IIHHHHHII", cd, pos + 20)
        method = struct.unpack_from("<H", cd, pos + 10)[0]
        name = cd[pos + 46:pos + 46 + name_len].decode("utf-8",
                                                       "replace")
        # zip64 extra field (id 0x0001) carries the real values when
        # the header fields are 0xFFFFFFFF
        if (0xFFFFFFFF in (comp_size, uncomp_size, lho)):
            ex = cd[pos + 46 + name_len:pos + 46 + name_len + extra_len]
            ep, vals = 0, {}
            while ep + 4 <= len(ex):
                eid, esz = struct.unpack_from("<HH", ex, ep)
                if eid == 0x0001:
                    body = ex[ep + 4:ep + 4 + esz]
                    bp = 0
                    if uncomp_size == 0xFFFFFFFF and bp + 8 <= len(body):
                        uncomp_size = struct.unpack_from("<Q", body,
                                                         bp)[0]
                        bp += 8
                    if comp_size == 0xFFFFFFFF and bp + 8 <= len(body):
                        comp_size = struct.unpack_from("<Q", body,
                                                       bp)[0]
                        bp += 8
                    if lho == 0xFFFFFFFF and bp + 8 <= len(body):
                        lho = struct.unpack_from("<Q", body, bp)[0]
                        bp += 8
                ep += 4 + esz
        members.append({"name": name, "offset": lho,
                        "comp_size": comp_size,
                        "uncomp_size": uncomp_size, "method": method})
        pos += 46 + name_len + extra_len + cmt_len
    print("members parsed:", len(members))

    import collections
    per_bearing = collections.defaultdict(list)
    for m in members:
        parts = m["name"].split("/")
        if len(parts) >= 3 and parts[-1].lower().endswith(".csv"):
            per_bearing[f"{parts[0]}/{parts[1]}"] = ...
            per_bearing[f"{parts[-2]}"] = per_bearing.get(
                f"{parts[-2]}", [])
            per_bearing[f"{parts[-2]}"].append(m)
        elif len(parts) == 2 and parts[-1].lower().endswith(".csv"):
            per_bearing[parts[0]].append(m)
    bearing_files = {k: v for k, v in per_bearing.items()
                     if isinstance(v, list) and "Bearing" in k}
    print("bearings found:", {k: len(v) for k, v in
                              sorted(bearing_files.items())})

    # the typed selection: per condition, the first 2 bearings with
    # n >= MIN_FILES
    conds = {}
    for k, v in bearing_files.items():
        cond = k.split("_")[0]
        conds.setdefault(cond, []).append((k, len(v)))
    selection = {}
    for cond, bs in sorted(conds.items()):
        bs.sort()
        picked = [b for b, n in bs if n >= MIN_FILES][:2]
        if not picked:
            picked = [b for b, _ in sorted(bs, key=lambda x: -x[1])][:2]
        for p in picked:
            selection[p] = bearing_files[p]
    budget = sum(m["comp_size"] for v in selection.values() for m in v)
    rec = {
        "record": "R110_D5_ZIP_INDEX/1.0.0",
        "total_bytes": total, "n_members": len(members),
        "bearings_found": {k: len(v) for k, v in
                           sorted(bearing_files.items())},
        "selected": {k: {"n_files": len(v),
                         "bytes": sum(m["comp_size"] for m in v)}
                     for k, v in sorted(selection.items())},
        "selected_n": len(selection),
        "range_fetch_budget_bytes": budget,
        "typed_rule": (f"per condition, the first 2 bearings with "
                       f"n>={MIN_FILES} csv members (the CTX=96 floor; "
                       "the largest-2 fallback typed)"),
    }
    (REPO / "eval" / "r110_d5_selected_members.json").write_text(
        json.dumps({k: [m["name"] for m in v]
                    for k, v in sorted(selection.items())},
                   indent=1, ensure_ascii=False) + "\n")
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print("selected:", json.dumps(rec["selected"], indent=1))
    print("range budget:", round(budget / 2**20, 1), "MB compressed")


if __name__ == "__main__":
    main()
