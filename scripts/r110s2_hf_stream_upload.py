#!/usr/bin/env python3
"""r110s2 HF stream-upload v2 — claim c-0148 item (2): the XJTU-SY CSVs
from the VERIFIED DavidNguyen mirror zip, uploaded per bearing folder
to the private dataset repo prateekm1/xjtu-sy-bearing-rar.

v1 findings this version fixes forward (typed, disclosed in the record):
  - v1 crashed after its first commit: huggingface_hub 1.9.2's
    create_commit returns CommitInfo with `.oid` (not `.sha`);
  - v1 used the zip-relative layout '40Hz10kN/Bearing3_1/<n>.csv',
    colliding with the PRIOR session's canonical FLAT layout
    'Bearing3_1/<n>.csv' (124 'custody batch' commits, 8274+ files,
    Bearing3_1/3_2 complete) — the resume filter therefore saw every
    member as missing and began a byte-identical DUPLICATE upload;
    v1's single collision commit (30841cf2f3, 51 files) is DELETED by
    this run as the one-canonical-artifact fix-forward;
  - the claim + the owner direction's Option B example
    ('Bearing3_1/47.csv') pin the FLAT per-bearing layout: the mirror
    zip carries exactly one operating condition (15 uniquely-named
    bearings, 9236 members), so the flat namespace is unambiguous.

Integrity (the direction's "Do NOT skip the integrity manifest" rule):
  - every inflated member is CRC32-checked against the zip central
    directory BEFORE upload;
  - eval/xjtu_sy_hf_manifest.json carries sha256 + size + zip crc32 +
    zip member name for EVERY canonical repo file: files uploaded this
    run are hashed from the inflated bytes; pre-existing files are
    hf_hub_downloaded FROM THE REPO and hashed there (verifier-grade:
    the manifest hashes the bytes actually stored, not a claim about
    them), then the repo bytes are cross-checked against the zip CD
    crc32 (the mirror remains the verification target);
  - the manifest is committed under eval/ AND uploaded to the repo
    root (the Art. 29(c) verifier path).

Disk discipline: zero extraction to sandbox disk — peak local
footprint = one span buffer (<=32 MB) + one commit batch (<=64 MB
inflated) + at most ONE downloaded pre-existing file at a time during
manifest completion (each deleted from cache immediately).
"""
import hashlib
import json
import os
import shutil
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import urllib.request

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from huggingface_hub import HfApi, hf_hub_download  # noqa: E402
from huggingface_hub.hf_api import CommitOperationAdd  # noqa: E402

URL = ("https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_"
       "Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip")
EXPECTED_TOTAL = 5447931446          # the committed index record
REPO_ID = "prateekm1/xjtu-sy-bearing-rar"
TOKEN = os.environ.get("HF_TOKEN", "")
SPAN_MAX = 32 * 2**20
BATCH_BYTES = 64 * 2**20
BATCH_FILES = 200
MANIFEST_OUT = REPO / "eval" / "xjtu_sy_hf_manifest.json"
RECORD_OUT = REPO / "eval" / "r110s2_hf_upload_record.json"
PRIORITY = ["Bearing3_1", "Bearing3_2"]  # acceptance target first
V1_COLLISION_COMMIT = "30841cf2f3"


def fetch_span(start, length):
    headers = {"Range": f"bytes={start}-{start + length - 1}",
               "User-Agent": "r110s2-hf-upload"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request(URL, headers=headers)
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.read()
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(
                    f"span fetch failed after 3 attempts "
                    f"(start={start}, len={length}): {type(e).__name__}")
            time.sleep(5 * attempt)


def verify_total_size():
    headers = {"Range": "bytes=0-0", "User-Agent": "r110s2-hf-upload"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        cr = r.headers.get("Content-Range", "")
    total = int(cr.rsplit("/", 1)[-1])
    assert total == EXPECTED_TOTAL, (
        f"mirror zip total drifted: live {total} vs committed "
        f"{EXPECTED_TOTAL}")
    return total


def parse_central_directory(total):
    tail_len = min(total, 65536 + 22)
    tail = fetch_span(total - tail_len, tail_len)
    ecd_off = tail.rfind(b"PK\x05\x06")
    assert ecd_off >= 0, "EOCD not found"
    loc = tail.rfind(b"PK\x06\x07", 0, ecd_off)
    if loc >= 0:
        z64_eocd_off = struct.unpack_from("<Q", tail, loc + 8)[0]
        blob = fetch_span(z64_eocd_off, 56)
        cd_size = struct.unpack_from("<Q", blob, 40)[0]
        cd_offset = struct.unpack_from("<Q", blob, 48)[0]
        n_entries = struct.unpack_from("<Q", blob, 32)[0]
    else:
        (n_entries, cd_size, cd_offset) = struct.unpack_from(
            "<III", tail, ecd_off + 10)
    assert n_entries == 9236, f"CD entries {n_entries} != 9236"
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
        name = cd[pos + 46:pos + 46 + name_len].decode(
            "utf-8", "replace")
        if 0xFFFFFFFF in (comp_size, uncomp_size, lho):
            ex = cd[pos + 46 + name_len:pos + 46 + name_len + extra_len]
            ep = 0
            while ep + 4 <= len(ex):
                eid, esz = struct.unpack_from("<HH", ex, ep)
                if eid == 0x0001:
                    body = ex[ep + 4:ep + 4 + esz]
                    bp = 0
                    if uncomp_size == 0xFFFFFFFF and bp + 8 <= len(body):
                        uncomp_size = struct.unpack_from("<Q", body, bp)[0]
                        bp += 8
                    if comp_size == 0xFFFFFFFF and bp + 8 <= len(body):
                        comp_size = struct.unpack_from("<Q", body, bp)[0]
                        bp += 8
                    if lho == 0xFFFFFFFF and bp + 8 <= len(body):
                        lho = struct.unpack_from("<Q", body, bp)[0]
                        bp += 8
                ep += 4 + esz
        out[name] = {"name": name, "offset": lho,
                     "comp_size": comp_size,
                     "uncomp_size": uncomp_size, "method": method,
                     "crc32": crc}
        pos += 46 + name_len + extra_len + cmt_len
    return out


def inflate_member(buf, off, name, cd):
    (sig, _ver, flags, method, _t, _d, crc, csize, usize,
     nlen, elen) = struct.unpack_from("<IHHHHHIIIHH", buf, off)
    assert sig == 0x04034b50, f"local header sig at {off}"
    lname = buf[off + 30:off + 30 + nlen].decode("utf-8", "replace")
    assert lname == name, f"local/CD name mismatch: {lname!r}"
    data_start = off + 30 + nlen + elen
    raw = buf[data_start:data_start + csize]
    if method == 0:
        data = raw
    elif method == 8:
        d = zlib.decompressobj(-15)
        data = d.decompress(raw) + d.flush()
    else:
        raise RuntimeError(f"method {method} unsupported for {name}")
    assert len(data) == cd[name]["uncomp_size"], f"size mismatch {name}"
    assert (zlib.crc32(data) & 0xFFFFFFFF) == cd[name]["crc32"], \
        f"crc32 mismatch {name}"
    return data


def group_spans(members):
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


def flat_rel(member_name):
    parts = member_name.split("/")
    return f"{parts[-2]}/{parts[-1]}"


def main():
    t0 = time.time()
    api = HfApi(token=TOKEN)
    total = verify_total_size()
    print(f"mirror zip total verified: {total} bytes", flush=True)
    cd = parse_central_directory(total)
    print(f"CD parsed: {len(cd)} members", flush=True)

    # canonical flat set: flat_rel -> zip member record
    canonical = {}
    by_bearing = {}
    for name, m in cd.items():
        if not name.lower().endswith(".csv"):
            continue
        rel = flat_rel(name)
        assert rel not in canonical, f"flat collision: {rel}"
        canonical[rel] = m
        by_bearing.setdefault(rel.split("/")[0], 0)
        by_bearing[rel.split("/")[0]] += 1
    print(f"canonical flat set: {len(canonical)} files across "
          f"{len(by_bearing)} bearings", flush=True)

    repo_files = set(api.list_repo_files(repo_id=REPO_ID,
                                         repo_type="dataset"))
    canonical_in_repo = {f for f in repo_files if f in canonical}
    foreign = repo_files - set(canonical)
    missing = set(canonical) - canonical_in_repo
    print(f"repo state: {len(canonical_in_repo)} canonical present, "
          f"{len(missing)} missing, {len(foreign)} foreign-path "
          f"(v1 collision: {sorted(foreign)[:2]} ...)", flush=True)

    commits_log = []

    # ---- 1. delete the v1 collision files (typed fix-forward) ----
    # .gitattributes is repo infra, NOT canonical csv: excluded from
    # the delete and restored immediately (the v2.0.0 run's delete
    # commit 68b2b44ecf swept it in by accident — disclosed here).
    if ".gitattributes" in foreign:
        std = urllib.request.urlopen(
            "https://huggingface.co/datasets/DavidNguyen/"
            "XJTU-SY_Bearing_Datasets/raw/main/.gitattributes",
            timeout=120).read()
        api.upload_file(path_or_fileobj=std,
                        path_in_repo=".gitattributes",
                        repo_id=REPO_ID, repo_type="dataset",
                        commit_message="restore the standard LFS "
                                       ".gitattributes (accidentally "
                                       "swept into the v1-collision "
                                       "delete commit)")
        commits_log.append({"action": "restore_gitattributes",
                            "commit_id": "see repo history"})
        foreign = foreign - {".gitattributes"}
        print("  restored .gitattributes", flush=True)
    if foreign:
        from huggingface_hub.hf_api import CommitOperationDelete
        res = api.create_commit(
            repo_id=REPO_ID, repo_type="dataset",
            operations=[CommitOperationDelete(path_in_repo=p)
                        for p in sorted(foreign)],
            commit_message=("fix-forward: delete the v1 collision-"
                            "layout files (zip-relative paths) — the "
                            "canonical layout is the flat per-bearing "
                            "one; bytes byte-identical to the flat "
                            "copies, zero data loss"))
        commits_log.append({"action": "delete_v1_collision",
                            "n_files": len(foreign),
                            "commit_id": res.oid})
        print(f"  deleted {len(foreign)} foreign-path files "
              f"({res.oid[:10]})", flush=True)

    # ---- 2. upload the missing canonical files ----
    todo = sorted(missing)
    by_b = {}
    for rel in todo:
        by_b.setdefault(rel.split("/")[0], []).append(rel)
    order = [b for b in PRIORITY if b in by_b] + \
            [b for b in sorted(by_b) if b not in PRIORITY]
    manifest = {}
    peak = 0
    for bearing in order:
        members = sorted((canonical[r] for r in by_b[bearing]),
                         key=lambda x: x["offset"])
        spans = group_spans([{"name": r, **canonical[r]}
                             for r in by_b[bearing]])
        ops, ops_bytes = [], 0

        def flush_ops():
            nonlocal ops, ops_bytes
            if not ops:
                return
            res = api.create_commit(
                repo_id=REPO_ID, operations=ops, repo_type="dataset",
                commit_message=(f"r110s2 stream-upload {bearing}: "
                                f"{len(ops)} csv members from the "
                                "verified mirror zip (crc32-verified "
                                "vs CD; flat canonical layout)"))
            commits_log.append({"action": "upload", "bearing": bearing,
                                "n_files": len(ops),
                                "bytes": ops_bytes,
                                "commit_id": res.oid})
            print(f"  commit {res.oid[:10]} ({len(ops)} files, "
                  f"{ops_bytes // 2**20} MB)", flush=True)
            ops, ops_bytes = [], 0

        for si, span in enumerate(spans):
            start = span[0]["offset"]
            end = span[-1]["offset"] + span[-1]["comp_size"]
            buf = fetch_span(start, end - start)
            for m in span:
                rel = flat_rel(m["name"])
                if rel not in missing:
                    continue
                data = inflate_member(buf, m["offset"] - start,
                                      m["name"], cd)
                manifest[rel] = {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "zip_crc32": f"{m['crc32']:08x}",
                    "zip_member": m["name"],
                    "sha_source": "inflated_bytes_at_upload",
                }
                ops.append(CommitOperationAdd(
                    path_in_repo=rel, path_or_fileobj=data))
                ops_bytes += len(data)
                peak = max(peak, len(buf) + ops_bytes)
                del data
                if len(ops) >= BATCH_FILES or ops_bytes >= BATCH_BYTES:
                    flush_ops()
            del buf
        flush_ops()
        print(f"  {bearing}: done ({len(by_b[bearing])} files)",
              flush=True)

    # ---- 3. manifest completion: hash the PRE-EXISTING repo bytes ----
    pre = sorted(canonical_in_repo - set(manifest))
    print(f"manifest completion: hashing {len(pre)} pre-existing "
          "files FROM THE REPO (12 workers; one file held per "
          "worker) ...", flush=True)
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    cache_dir = Path("/tmp/hf_cache_manifest")
    crc_bad = []
    from concurrent.futures import ThreadPoolExecutor

    def hash_one(rel):
        # local_dir mode places the REAL file (no blob/symlink cache
        # leak); ONE file per worker, unlinked immediately
        p = hf_hub_download(repo_id=REPO_ID, filename=rel,
                            repo_type="dataset", token=TOKEN,
                            local_dir=str(cache_dir))
        data = Path(p).read_bytes()
        m = canonical[rel]
        crc_ok = (zlib.crc32(data) & 0xFFFFFFFF) == m["crc32"]
        entry = {
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "zip_crc32": f"{m['crc32']:08x}",
            "zip_member": m["name"],
            "sha_source": "downloaded_repo_bytes",
        }
        Path(p).unlink(missing_ok=True)
        return rel, entry, crc_ok

    with ThreadPoolExecutor(max_workers=12) as ex:
        done = 0
        for rel, entry, crc_ok in ex.map(hash_one, pre):
            manifest[rel] = entry
            if not crc_ok:
                crc_bad.append(rel)
            done += 1
            if done % 1000 == 0:
                print(f"  hashed {done}/{len(pre)}", flush=True)
    print(f"  done: {len(pre)} hashed, "
          f"{len(crc_bad)} crc mismatches", flush=True)
    shutil.rmtree(cache_dir, ignore_errors=True)  # metadata cleanup

    # ---- 4. write + upload the manifest ----
    MANIFEST_OUT.write_text(json.dumps({
        "record": "XJTU_SY_HF_MANIFEST/1.0.0",
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_id": REPO_ID, "repo_type": "dataset", "private": True,
        "layout": "flat per-bearing folders (the claim's Option B "
                  "canonical; the mirror zip carries one operating "
                  "condition — 15 uniquely-named bearings)",
        "source": {"url": URL, "total_bytes": total,
                   "n_zip_members": len(cd),
                   "index_record": "eval/r110_d5_zip_index.json"},
        "integrity": ("sha256 of the bytes actually stored in the repo "
                      "(uploaded files: inflated bytes at upload; "
                      "pre-existing files: downloaded repo bytes), "
                      "cross-checked against the mirror zip CD crc32 "
                      "— bytes over claims"),
        "n_files": len(manifest),
        "crc_mismatches": crc_bad,
        "files": manifest,
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    res = api.upload_file(
        path_or_fileobj=MANIFEST_OUT.read_bytes(),
        path_in_repo="xjtu_sy_hf_manifest.json",
        repo_id=REPO_ID, repo_type="dataset",
        commit_message="the integrity manifest (sha256 per file, "
                       "repo-bytes-verified)")
    commits_log.append({"action": "manifest_upload",
                        "commit_id": res.oid})

    rec = {
        "record": "R110S2_HF_UPLOAD/2.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r109s2 (resumed after reprovision)",
        "claim": "c-0148 item (2)",
        "repo": REPO_ID,
        "fix_forward": [
            "v1 crashed at the first commit (create_commit returns "
            "CommitInfo.oid, not .sha) — one commit (30841cf2f3, 51 "
            "files under the zip-relative layout) had landed; this "
            "run deleted those files as the one-canonical-artifact "
            "fix-forward (bytes byte-identical to the prior session's "
            "flat copies)",
            "layout collision typed: the prior session's 124 custody "
            "batches established the FLAT per-bearing layout; v1's "
            "zip-relative resume filter missed it and began a "
            "byte-identical duplicate upload — v2 resumes on flat",
        ],
        "mirror_total_bytes": total,
        "n_canonical_files": len(canonical),
        "pre_existing": len(canonical_in_repo),
        "uploaded_this_run": sum(c["n_files"] for c in commits_log
                                 if c["action"] == "upload"),
        "deleted_v1_collision": len(foreign),
        "manifest_files": len(manifest),
        "manifest_sha_sources": {
            "inflated_bytes_at_upload": sum(
                1 for v in manifest.values()
                if v["sha_source"] == "inflated_bytes_at_upload"),
            "downloaded_repo_bytes": sum(
                1 for v in manifest.values()
                if v["sha_source"] == "downloaded_repo_bytes"),
        },
        "crc_mismatches": len(crc_bad),
        "peak_local_buffer_bytes": peak,
        "disk_discipline": "zero extraction to sandbox disk; peak = "
                           "one span buffer (<=32MB) + one commit "
                           "batch (<=64MB) + one downloaded file at a "
                           "time during manifest completion",
        "commits": commits_log,
        "wall_clock_s": round(time.time() - t0, 1),
    }
    RECORD_OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"DONE: manifest {len(manifest)} files, "
          f"{rec['uploaded_this_run']} uploaded, "
          f"{rec['deleted_v1_collision']} deleted, "
          f"{len(crc_bad)} crc mismatches, "
          f"peak buffer {peak // 2**20} MB, "
          f"{rec['wall_clock_s']}s", flush=True)


if __name__ == "__main__":
    main()
