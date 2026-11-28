#!/usr/bin/env python3
"""Byte-level diff of one crc-mismatched file: mirror-zip member vs the
bytes actually stored in the private HF repo. Values never printed —
digests + structural diffs only."""
import json
import struct
import sys
import urllib.request
import zlib

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric/scripts")
import os
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
from huggingface_hub import hf_hub_download  # noqa: E402

URL = ("https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_"
       "Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip")
TOKEN = os.environ.get("HF_TOKEN", "")
REPO_ID = "prateekm1/xjtu-sy-bearing-rar"


def fetch_span(start, length):
    headers = {"Range": f"bytes={start}-{start + length - 1}",
               "User-Agent": "r110s2-diff"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def member_bytes(member_name, total=5447931446):
    tail_len = min(total, 65536 + 22)
    tail = fetch_span(total - tail_len, tail_len)
    ecd_off = tail.rfind(b"PK\x05\x06")
    loc = tail.rfind(b"PK\x06\x07", 0, ecd_off)
    z64 = struct.unpack_from("<Q", tail, loc + 8)[0]
    blob = fetch_span(z64, 56)
    cd_size = struct.unpack_from("<Q", blob, 40)[0]
    cd_offset = struct.unpack_from("<Q", blob, 48)[0]
    cd = fetch_span(cd_offset, cd_size)
    pos = 0
    while pos < len(cd) - 46:
        if cd[pos:pos + 4] != b"PK\x01\x02":
            break
        (comp_size, uncomp_size, name_len, extra_len, cmt_len,
         _d1, _d2, _d3, lho) = struct.unpack_from("<IIHHHHHII", cd,
                                                  pos + 20)
        method = struct.unpack_from("<H", cd, pos + 10)[0]
        crc = struct.unpack_from("<I", cd, pos + 16)[0]
        name = cd[pos + 46:pos + 46 + name_len].decode(
            "utf-8", "replace")
        if name == member_name:
            lh = fetch_span(lho, 30 + 256)
            (sig, _v, _f, _m, _t, _d, _c, csize_l, usize_l, nlen,
             elen) = struct.unpack_from("<IHHHHHIIIHH", lh, 0)
            data_start = lho + 30 + nlen + elen
            raw = fetch_span(data_start, comp_size)
            if method == 8:
                d = zlib.decompressobj(-15)
                raw = d.decompress(raw) + d.flush()
            # the CD crc32 is of the UNCOMPRESSED data (inflate first)
            assert crc == (zlib.crc32(raw) & 0xFFFFFFFF), \
                "the mirror member itself fails its CD crc"
            return raw, crc
        pos += 46 + name_len + extra_len + cmt_len
    raise SystemExit(f"member {member_name} not in CD")


def main():
    mf = json.load(open("/home/z/my-project/discovery-evidence-fabric"
                        "/eval/xjtu_sy_hf_manifest.json"))
    bad = sorted(mf["crc_mismatches"])[0]
    print("real-mismatch sample:", bad)
    entry = mf["files"][bad]
    print(f"diffing {bad} (repo sha {entry['sha256'][:12]}, "
          f"size {entry['size']})")
    zip_bytes, zip_crc = member_bytes(entry["zip_member"])
    print(f"zip member: crc {zip_crc:08x} (CD), size {len(zip_bytes)}, "
          f"sha {zlib.crc32(zip_bytes) & 0xFFFFFFFF:08x}-crc")
    import hashlib
    print(f"zip bytes sha256: {hashlib.sha256(zip_bytes).hexdigest()[:12]}")
    p = hf_hub_download(repo_id=REPO_ID, filename=bad, repo_type="dataset",
                        token=TOKEN, local_dir="/tmp/hf_diff_one")
    repo_bytes = open(p, "rb").read()
    print(f"repo bytes: size {len(repo_bytes)}, "
          f"sha {hashlib.sha256(repo_bytes).hexdigest()[:12]}")
    # structural diff
    zl = zip_bytes.decode("utf-8", "replace").splitlines()
    rl = repo_bytes.decode("utf-8", "replace").splitlines()
    print(f"lines: zip {len(zl)} vs repo {len(rl)}")
    print(f"zip header:   {zl[0][:80]!r}")
    print(f"repo header:  {rl[0][:80]!r}")
    diffs = sum(1 for a, b in zip(zl, rl) if a != b)
    print(f"differing lines (aligned prefix): {diffs}")
    for i, (a, b) in enumerate(zip(zl[:5], rl[:5])):
        if a != b:
            print(f"  line {i}: zip={a[:60]!r} repo={b[:60]!r}")
            break
    import shutil
    shutil.rmtree("/tmp/hf_diff_one", ignore_errors=True)


if __name__ == "__main__":
    main()
