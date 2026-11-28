#!/usr/bin/env python3
"""Repair the 37 truncated repo files (all Bearing3_1): the prior
session's custody batches lost ~5-6 trailing rows on these members
(byte-diff evidence: Bearing3_1/1390.csv repo 32763 lines vs mirror
32769 lines, mirror crc-intact) — the range-fetch truncation class.
The mirror zip is the verified source (bytes over claims): each of the
37 members is re-fetched, CRC32-asserted against the zip CD, uploaded
in ONE commit, re-downloaded FROM THE REPO and re-verified, and the
manifest + record updated."""
import hashlib
import json
import os
import struct
import sys
import time
import urllib.request
import zlib
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
from huggingface_hub import HfApi, CommitOperationAdd, \
    hf_hub_download  # noqa: E402

URL = ("https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_"
       "Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip")
TOTAL = 5447931446
REPO = Path("/home/z/my-project/discovery-evidence-fabric")
MF = REPO / "eval" / "xjtu_sy_hf_manifest.json"
REC = REPO / "eval" / "r110s2_hf_upload_record.json"
TOKEN = os.environ.get("HF_TOKEN", "")


def fetch_span(start, length):
    headers = {"Range": f"bytes={start}-{start + length - 1}",
               "User-Agent": "r110s2-repair"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request(URL, headers=headers)
            with urllib.request.urlopen(req, timeout=600) as r:
                data = r.read()
                assert len(data) == length, \
                    f"truncated span fetch: {len(data)} != {length}"
                return data
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(5 * attempt)


def parse_cd():
    tail_len = min(TOTAL, 65536 + 22)
    tail = fetch_span(TOTAL - tail_len, tail_len)
    ecd_off = tail.rfind(b"PK\x05\x06")
    loc = tail.rfind(b"PK\x06\x07", 0, ecd_off)
    z64 = struct.unpack_from("<Q", tail, loc + 8)[0]
    blob = fetch_span(z64, 56)
    cd_size = struct.unpack_from("<Q", blob, 40)[0]
    cd_offset = struct.unpack_from("<Q", blob, 48)[0]
    cd = fetch_span(cd_offset, cd_size)
    out, pos = {}, 0
    while pos < len(cd) - 46:
        if cd[pos:pos + 4] != b"PK\x01\x02":
            break
        (comp_size, uncomp_size, name_len, extra_len, cmt_len,
         _d1, _d2, _d3, lho) = struct.unpack_from("<IIHHHHHII", cd,
                                                  pos + 20)
        method = struct.unpack_from("<H", cd, pos + 10)[0]
        crc = struct.unpack_from("<I", cd, pos + 16)[0]
        name = cd[pos + 46:pos + 46 + name_len].decode("utf-8",
                                                       "replace")
        if 0xFFFFFFFF in (comp_size, uncomp_size, lho):
            ex = cd[pos + 46 + name_len:pos + 46 + name_len + extra_len]
            ep = 0
            while ep + 4 <= len(ex):
                eid, esz = struct.unpack_from("<HH", ex, ep)
                if eid == 0x0001:
                    body = ex[ep + 4:ep + 4 + esz]
                    bp = 0
                    for field in ("u", "c", "l"):
                        pass
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
        out[name] = {"offset": lho, "comp_size": comp_size,
                     "uncomp_size": uncomp_size, "method": method,
                     "crc32": crc}
        pos += 46 + name_len + extra_len + cmt_len
    return out


def inflate(buf, off, name, m):
    (sig, _v, _f, method, _t, _d, _c, csize, usize, nlen,
     elen) = struct.unpack_from("<IHHHHHIIIHH", buf, off)
    assert sig == 0x04034b50
    data_start = off + 30 + nlen + elen
    raw = buf[data_start:data_start + csize]
    if method == 8:
        d = zlib.decompressobj(-15)
        raw = d.decompress(raw) + d.flush()
    assert len(raw) == m["uncomp_size"], f"{name}: size mismatch"
    assert (zlib.crc32(raw) & 0xFFFFFFFF) == m["crc32"], \
        f"{name}: crc mismatch vs CD"
    return raw


def main():
    mf = json.loads(MF.read_text())
    bad = sorted(mf["crc_mismatches"])
    files = mf["files"]
    print(f"repairing {len(bad)} files: "
          f"{sorted(set(f.split('/')[0] for f in bad))}", flush=True)
    cd = parse_cd()
    api = HfApi(token=TOKEN)

    ops = []
    expected = {}
    for rel in bad:
        member = files[rel]["zip_member"]
        m = cd[member]
        lh = fetch_span(m["offset"], min(m["comp_size"] + 512,
                                         m["comp_size"] + 512))
        (sig, _v, _f, _m, _t, _d, _c, csize_l, _u, nlen,
         elen) = struct.unpack_from("<IHHHHHIIIHH", lh, 0)
        assert sig == 0x04034b50
        data_start = 30 + nlen + elen
        # fetch the exact compressed span (the local header told us the
        # real sizes; refetch cleanly with the asserted length)
        full = fetch_span(m["offset"], 30 + nlen + elen
                          + m["comp_size"])
        data = inflate(full, 0, member, m)
        ops.append(CommitOperationAdd(path_in_repo=rel,
                                      path_or_fileobj=data))
        expected[rel] = data
        print(f"  {rel}: {len(data)} bytes, crc ok "
              f"({m['crc32']:08x})", flush=True)

    res = api.create_commit(
        repo_id=files and mf["repo_id"], operations=ops,
        repo_type="dataset",
        commit_message=("repair: re-upload the 37 truncated Bearing3_1 "
                        "members from the verified mirror (the prior "
                        "session's custody batches lost ~5-6 trailing "
                        "rows on these members; byte-diff evidence in "
                        "eval/r110s2_hf_upload_record.json; each member "
                        "crc32-asserted against the zip CD before "
                        "upload)"))
    print(f"repair commit: {res.oid[:10]}", flush=True)

    # verify FROM THE REPO
    still = []
    cache = Path("/tmp/hf_cache_repair")
    for i, rel in enumerate(bad):
        p = hf_hub_download(repo_id=mf["repo_id"], filename=rel,
                            repo_type="dataset", token=TOKEN,
                            local_dir=str(cache))
        data = Path(p).read_bytes()
        if (zlib.crc32(data) & 0xFFFFFFFF) != cd[files[rel]
                                                 ["zip_member"]]["crc32"]:
            still.append(rel)
        else:
            e = files[rel]
            e["size"] = len(data)
            e["sha256"] = hashlib.sha256(data).hexdigest()
            e["sha_source"] = "downloaded_repo_bytes_post_repair"
        Path(p).unlink(missing_ok=True)
    import shutil
    shutil.rmtree(cache, ignore_errors=True)

    mf["crc_mismatches"] = still
    mf["repair"] = {
        "n_repaired": len(bad) - len(still),
        "n_still_bad": len(still),
        "repair_commit": res.oid,
        "cause_typed": ("the prior session's custody batches truncated "
                        "~5-6 trailing rows on 37 Bearing3_1 members "
                        "(the range-fetch truncation class); the "
                        "mirror zip is the verified source (bytes over "
                        "claims) and the repair re-fetched each member "
                        "with a crc32 assert against the zip CD"),
    }
    MF.write_text(json.dumps(mf, indent=1, sort_keys=True) + "\n",
                  encoding="utf-8")
    res2 = api.upload_file(
        path_or_fileobj=MF.read_bytes(),
        path_in_repo="xjtu_sy_hf_manifest.json", repo_id=mf["repo_id"],
        repo_type="dataset",
        commit_message="manifest post-repair: the 37 repaired members "
                       "re-hashed from repo bytes (0 crc mismatches)"
                       if not still else
                       "manifest post-repair (mismatches remain)")
    rec = json.loads(REC.read_text())
    rec["crc_mismatches"] = len(still)
    rec["repair"] = mf["repair"]
    rec["repair_manifest_commit"] = res2.oid
    REC.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"repair done: {len(bad) - len(still)} repaired, "
          f"{len(still)} still bad; manifest {res2.oid[:10]}",
          flush=True)
    sys.exit(1 if still else 0)


if __name__ == "__main__":
    main()
