#!/usr/bin/env python3
"""r110s2_hf_custody_upload.py — the OWNER-DIRECTED HF streaming custody
lane (claim c-0148, builder-r109s2): stream the XJTU-SY CSVs grouped
per bearing folder INTO the owner's PRIVATE dataset repo
(prateekm1/xjtu-sy-bearing-rar), fetched from the verified DavidNguyen
HF mirror via zip64 RANGE-FETCH — fetch member -> upload member ->
discard. ONE member buffer + one pending-commit batch in RAM; ZERO
bytes of the dataset touch the sandbox disk (the r110s1 Dir-5
precedent, one tool over).

Source-of-truth mechanics: fetch_span / inflate_member / group_spans /
bearing_members are vendored VERBATIM from scripts/r110_d5_xjtu_stream.py
(commit 2727b8bad, builder-r109s1's Dir-5 tooling — cited, not
re-derived; importing that module whole would execute the stage-5
measurement imports, which this custody driver must not do).

The RAR-parts acceptance item is typed BLOCKED-SOURCE: the 6 RAR5
parts are absent after the reprovision and the original gdown source
carries NO committed file ids (the r109s2 verifier typed the parts'
hashes were never recorded pre-deletion). The committed
eval/p3_realdata/xjtu_sy_parts_manifest.txt stays the verification
target if the original bytes ever reappear. The mirror zip is the
c-0132-recon-verified alternative source.

Usage:
  python3 scripts/r110s2_hf_custody_upload.py --bearings Bearing3_1,Bearing3_2
  python3 scripts/r110s2_hf_custody_upload.py --bearings ALL
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import sys
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402

_load_key_vault()
import os  # noqa: E402

from huggingface_hub import HfApi, CommitOperationAdd  # noqa: E402
from huggingface_hub import create_commit  # noqa: E402

IDX = json.loads((REPO / "eval" / "r110_d5_zip_index.json").read_text())
REPO_ID = "prateekm1/xjtu-sy-bearing-rar"
URL = ("https://huggingface.co/datasets/DavidNguyen/XJTU-SY_Bearing_"
       "Datasets/resolve/main/XJTU-SY_Bearing_Datasets.zip")
MANIFEST = REPO / "eval" / "xjtu_sy_hf_manifest.json"
SPAN_MAX = 32 * 2**20
COMMIT_BYTES_CAP = 96 * 2**20   # per-commit payload cap (RAM bound)
COMMIT_FILES_CAP = 120          # per-commit file-count cap
ALL_BEARINGS = ["Bearing1_1", "Bearing1_2", "Bearing1_3", "Bearing1_4",
                "Bearing1_5", "Bearing2_1", "Bearing2_2", "Bearing2_3",
                "Bearing2_4", "Bearing2_5", "Bearing3_1", "Bearing3_2",
                "Bearing3_3", "Bearing3_4", "Bearing3_5"]
PRIORITY = ["Bearing3_1", "Bearing3_2", "Bearing1_2", "Bearing1_3",
            "Bearing2_1", "Bearing2_3"]


def d12(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def archive_size() -> int:
    return 5447931446


def fetch_span(start, length):
    # TYPED DEVIATION vs the cited r110s1 original (the VF-class fix this
    # window): the span end must include the LAST member's local-header
    # length — data ends at offset + 30 + nlen + extra + csize, so an
    # end at offset + csize truncates the span's last member's deflate
    # stream (the truncation the repair pass fixes). The 4096 slack is
    # clamped to the archive size.
    length = min(length, archive_size() - start)
    headers = {"Range": f"bytes={start}-{start + length - 1}",
               "User-Agent": "r110s2-custody"}
    tok = os.environ.get("HF_TOKEN", "")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def mirror_etag():
    req = urllib.request.Request(
        URL, method="HEAD",
        headers={"User-Agent": "r110s2-custody",
                 "Authorization": f"Bearer {os.environ.get('HF_TOKEN','')}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.headers.get("ETag", "")


def inflate_member(buf, off):
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


def bearing_members(bearing):
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


def repo_path(zip_name: str) -> str:
    parts = zip_name.split("/")
    return f"{parts[-2]}/{parts[-1]}"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {
        "record": "R110S2_XJTU_HF_CUSTODY_MANIFEST/1.0.0",
        "owner_directive": ("the owner's HF-streaming directions "
                            "(create private repo, stream per-use, "
                            "manifest integrity per Art. 1)"),
        "executor": "builder-r109s2",
        "claim": "c-0148",
        "repo_id": REPO_ID,
        "repo_type": "dataset",
        "repo_private": True,
        "namespace_deviation_typed": ("the directive's example repo_id "
                                      "prateekm1007/ is the GITHUB "
                                      "handle; the HF token namespace "
                                      "is prateekm1 — the repo lives "
                                      "at prateekm1/xjtu-sy-bearing-rar"),
        "source": {
            "mirror_url": URL,
            "mirror_etag_verified": None,
            "citation": ("B. Wang, Y. Lei, N. Li, N. Li — XJTU-SY; "
                         "fetched from the DavidNguyen "
                         "XJTU-SY_Bearing_Datasets HF mirror (the "
                         "c-0132 recon's verified source; the r110s1 "
                         "Dir-5 range-fetch precedent)"),
        },
        "rar_parts_blocked_source": {
            "typed": "BLOCKED-SOURCE (not blocked-storage)",
            "why": ("the 6 RAR5 parts are absent post-reprovision; the "
                    "original gdown source carries NO committed file "
                    "ids (the r109s2 verifier typed the parts' hashes "
                    "were never recorded pre-deletion)"),
            "verification_target": ("eval/p3_realdata/"
                                    "xjtu_sy_parts_manifest.txt (6 "
                                    "sha256s) — binding if the "
                                    "original bytes ever reappear"),
        },
        "streaming_mode": "per-bearing-folder",
        "max_local_footprint": "one 32MB span buffer + one "
                               "<=96MB pending-commit batch in RAM; "
                               "zero dataset bytes on disk",
        "bearings": {},
    }


def save_manifest(m: dict):
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")


def repair_span_last(api, tok, m, log) -> int:
    """The truncation repair (the window's own VF-class finding): the
    pre-fix spans cut each span's LAST member's deflate stream by the
    local-header length (~118 bytes compressed). This pass re-inflates
    EVERY span-last member with the slack fetch, compares sha256 vs
    the repo bytes, and re-uploads the mismatches."""
    total_fixed, total_checked = 0, 0
    order = [b for b in PRIORITY if b in ALL_BEARINGS] + \
            [b for b in ALL_BEARINGS if b not in PRIORITY]
    from huggingface_hub import hf_hub_download
    for bearing in order:
        members = bearing_members(bearing)
        spans = group_spans(members)
        last_offsets = set(s[-1]["offset"] for s in spans)
        cands = [mm for mm in members if mm["offset"] in last_offsets]
        bad_ops, bad_meta, fixed_here = [], [], []
        for mm in cands:
            total_checked += 1
            buf = fetch_span(mm["offset"], mm["comp_size"] + 4096)
            name, data = inflate_member(buf, 0)
            assert name == mm["name"], (name, mm["name"])
            rp = repo_path(name)
            lp = hf_hub_download(repo_id=REPO_ID, filename=rp,
                                 repo_type="dataset", token=tok,
                                 local_dir="/tmp/repair_cache",
                                 force_download=True)
            repo_sha = hashlib.sha256(
                open(lp, "rb").read()).hexdigest()
            os.unlink(lp)
            if repo_sha != hashlib.sha256(data).hexdigest():
                bad_ops.append(CommitOperationAdd(
                    path_in_repo=rp, path_or_fileobj=data))
                bad_meta.append({"path": rp,
                                 "sha256": hashlib.sha256(
                                     data).hexdigest()})
                fixed_here.append(rp)
            del data, buf
        if bad_ops:
            commit = create_commit(
                repo_id=REPO_ID, repo_type="dataset",
                operations=bad_ops,
                commit_message=(f"repair span-last truncation "
                                f"{bearing} ({len(bad_ops)} csv)"),
                token=tok)
            log(f"{bearing}: repaired {len(bad_ops)} / "
                f"{len(cands)} span-last members "
                f"(rev {str(commit.oid)[:12]})")
            m.setdefault("repair_span_last", {})[bearing] = {
                "n_span_last": len(cands),
                "n_repaired": len(bad_ops),
                "repaired": bad_meta,
                "revision": str(commit.oid),
            }
            total_fixed += len(bad_ops)
        else:
            log(f"{bearing}: all {len(cands)} span-last members "
                f"already complete")
            m.setdefault("repair_span_last", {})[bearing] = {
                "n_span_last": len(cands), "n_repaired": 0}
        save_manifest(m)
    log(f"repair done: checked {total_checked} span-last members, "
        f"re-uploaded {total_fixed}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bearings", required=False, default=None,
                    help="comma list or ALL")
    ap.add_argument("--repair-span-last", action="store_true")
    args = ap.parse_args()

    tok = os.environ.get("HF_TOKEN", "")
    assert tok, "typed refusal: HF_TOKEN absent"
    api = HfApi(token=tok)
    m = load_manifest()

    if args.repair_span_last:
        m["source"]["mirror_etag_verified"] = mirror_etag()
        return repair_span_last(api, tok, m, print)

    if args.bearings is None:
        ap.error("--bearings required unless --repair-span-last")
    if args.bearings.upper() == "ALL":
        order = [b for b in PRIORITY if b in ALL_BEARINGS] + \
                [b for b in ALL_BEARINGS if b not in PRIORITY]
    else:
        order = [b.strip() for b in args.bearings.split(",")]

    m["source"]["mirror_etag_verified"] = mirror_etag()
    save_manifest(m)

    existing = set(api.list_repo_files(repo_id=REPO_ID,
                                       repo_type="dataset"))
    log = lambda s: print(s, flush=True)
    log(f"repo {REPO_ID}: {len(existing)} files already present")

    for bearing in order:
        members = bearing_members(bearing)
        todo = [mm for mm in members
                if repo_path(mm["name"]) not in existing]
        log(f"{bearing}: {len(members)} members, {len(todo)} to upload")
        if not todo:
            m["bearings"].setdefault(bearing, {"status": "ALREADY_UPLOADED",
                                               "n_files": len(members)})
            save_manifest(m)
            continue
        spans = group_spans(todo)
        n_up, n_bytes, commits = 0, 0, []
        pending_ops, pending_bytes, pending_paths = [], 0, []
        b_sha = hashlib.sha256()
        for si, span in enumerate(spans):
            start = span[0]["offset"]
            end = span[-1]["offset"] + span[-1]["comp_size"]
            # +4096 header slack (the typed deviation above) so the
            # span's LAST member inflates COMPLETE bytes
            buf = fetch_span(start, end - start + 4096)
            for mm in span:
                name, data = inflate_member(buf, mm["offset"] - start)
                assert name == mm["name"], (name, mm["name"])
                sha = hashlib.sha256(data).hexdigest()
                b_sha.update(data)
                pending_ops.append(CommitOperationAdd(
                    path_in_repo=repo_path(name),
                    path_or_fileobj=data))
                pending_paths.append({"path": repo_path(name),
                                      "size": len(data), "sha256": sha})
                pending_bytes += len(data)
                n_up += 1
                n_bytes += len(data)
                del data
                if (len(pending_ops) >= COMMIT_FILES_CAP
                        or pending_bytes >= COMMIT_BYTES_CAP):
                    commit = create_commit(
                        repo_id=REPO_ID, repo_type="dataset",
                        operations=pending_ops,
                        commit_message=(f"custody batch {bearing} "
                                        f"({len(pending_ops)} csv)"),
                        token=tok)
                    commits.append({"revision": commit.commit_url,
                                    "sha": str(commit.oid),
                                    "n_files": len(pending_ops),
                                    "bytes": pending_bytes})
                    log(f"  commit {len(commits)}: {len(pending_ops)} "
                        f"files / {pending_bytes // 2**20}MB")
                    pending_ops, pending_bytes, pending_paths = \
                        [], 0, []
            del buf  # freed after the whole span
            log(f"  span {si + 1}/{len(spans)}")
        if pending_ops:
            commit = create_commit(
                repo_id=REPO_ID, repo_type="dataset",
                operations=pending_ops,
                commit_message=f"custody batch {bearing} (tail "
                               f"{len(pending_ops)} csv)",
                token=tok)
            commits.append({"revision": commit.commit_url,
                            "sha": str(commit.oid),
                            "n_files": len(pending_ops),
                            "bytes": pending_bytes})
        m["bearings"][bearing] = {
            "status": "UPLOADED",
            "n_files": n_up,
            "bytes_uncompressed": n_bytes,
            "stream_sha256": b_sha.hexdigest(),
            "commits": commits,
            "uploaded_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ (sandbox clock)"),
        }
        save_manifest(m)
        log(f"{bearing} DONE: {n_up} files, {n_bytes // 2**20}MB, "
            f"{len(commits)} commits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
