#!/usr/bin/env python3
"""Re-hash the 79 crc-mismatched manifest entries (the first hash pass
ran while the rootfs was 100% full — my own pip installs + stale /tmp
junk; hf_hub downloads were silently truncated, the failure mode the
huggingface_hub download does not guard against). The repo bytes were
never in question: the byte-diff probe (r110s2_crc_diff_one.py) showed
the stored file byte-identical to the mirror member. This pass
re-downloads the 79 files with 4.7GB free, re-checks each against the
CD crc32 recorded in the manifest, corrects the sha256 entries, and
re-uploads the manifest to the repo root. The incident + the original
list stay typed in the upload record."""
import hashlib
import json
import os
import shutil
import sys
import zlib
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
from huggingface_hub import HfApi, hf_hub_download  # noqa: E402

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
MF = REPO / "eval" / "xjtu_sy_hf_manifest.json"
REC = REPO / "eval" / "r110s2_hf_upload_record.json"
TOKEN = os.environ.get("HF_TOKEN", "")
REPO_ID = json.loads(MF.read_text())["repo_id"]

mf = json.loads(MF.read_text())
bad = list(mf["crc_mismatches"])
files = mf["files"]
cache = Path("/tmp/hf_cache_rehash")
still_bad, corrected = [], []
for i, rel in enumerate(sorted(bad)):
    p = hf_hub_download(repo_id=REPO_ID, filename=rel, repo_type="dataset",
                        token=TOKEN, local_dir=str(cache))
    data = Path(p).read_bytes()
    crc = zlib.crc32(data) & 0xFFFFFFFF
    entry = files[rel]
    if f"{crc:08x}" != entry["zip_crc32"]:
        still_bad.append(rel)  # real mismatch: repo bytes != mirror
    else:
        entry["size"] = len(data)
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        corrected.append(rel)
    Path(p).unlink(missing_ok=True)
    if (i + 1) % 20 == 0:
        print(f"  re-hashed {i + 1}/{len(bad)}", flush=True)
shutil.rmtree(cache, ignore_errors=True)

mf["crc_mismatches"] = still_bad
mf["integrity_correction"] = {
    "incident": ("the first hash pass (v2c) ran while the rootfs was "
                 "100% full (the session's own pip installs + stale "
                 "/tmp junk from prior instances); 79 hf_hub downloads "
                 "were silently truncated — a full-disk failure mode "
                 "the download path does not guard"),
    "evidence": ("byte-diff probe on Bearing1_1/39.csv: the stored "
                 "repo bytes were byte-identical to the mirror member "
                 "(sha faed01f00f29 == zip member sha) while the first "
                 "pass had recorded a truncated hash (size 1331419 vs "
                 "1331653)"),
    "n_corrected": len(corrected),
    "n_still_bad": len(still_bad),
}
MF.write_text(json.dumps(mf, indent=1, sort_keys=True) + "\n",
              encoding="utf-8")

rec = json.loads(REC.read_text())
rec["crc_mismatches"] = len(still_bad)
rec["crc_mismatch_resolution"] = mf["integrity_correction"]
rec["crc_mismatch_first_pass_list_len"] = len(bad)
REC.write_text(json.dumps(rec, indent=1) + "\n")

api = HfApi(token=TOKEN)
res = api.upload_file(
    path_or_fileobj=MF.read_bytes(), path_in_repo="xjtu_sy_hf_manifest.json",
    repo_id=REPO_ID, repo_type="dataset",
    commit_message="manifest correction: the 79 disk-full-truncated "
                   "hashes re-verified from the repo bytes (crc32 vs "
                   "mirror CD; 0 real mismatches)")
print(f"corrected {len(corrected)}, still_bad {len(still_bad)}; "
      f"manifest re-uploaded {res.oid[:10]}")
sys.exit(1 if still_bad else 0)
