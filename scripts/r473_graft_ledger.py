#!/usr/bin/env python3
"""R473: graft the 19 missing model_routing/ledger.jsonl records from
e245bbe back onto origin/runtime-state-hf, regenerate the integrity
manifest over the repaired tree, commit + push.

Context (verified this session): the 176->34 session-index incident was
already grafted at 8c9a70a/828be9b (index union 209, verified ALL GREEN
by scripts/r473_verify_graft.py). The one residual loss is the
model_routing ledger: graft v3 restored payloads from the 34-lineage
(143 records, epochs 1789513838+) while e245bbe carried 19 earlier
records (epochs 1789513186-1789513547) -> 0 verbatim matches. Root cause
of the loss class: restore() never re-materialized model_routing/, so a
fresh container pushed a shorter ledger over the branch. The code-level
closure (restore symmetry + shrink guard) lands on main in this round;
this script is the data repair.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = "/home/z/my-project/hf_space"
WORK = Path("/home/z/my-project/r473_work/rts-repair")
SOURCE_REF = "e245bbe"
BRANCH = "origin/runtime-state-hf"

def git(*args, cwd=REPO, check=True):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args}: {r.stderr}")
    return r

def main() -> int:
    # 1. worktree at the branch tip
    if WORK.exists():
        git("worktree", "remove", "--force", str(WORK), check=False)
    git("worktree", "add", "--detach", str(WORK), BRANCH)
    ledger = WORK / "model_routing" / "ledger.jsonl"
    tip_lines = [l for l in ledger.read_text().splitlines() if l.strip()]
    old_raw = git("show", f"{SOURCE_REF}:model_routing/ledger.jsonl").stdout
    old_lines = [l for l in old_raw.splitlines() if l.strip()]

    tip_ids = {json.loads(l).get("request_id") for l in tip_lines}
    missing = [l for l in old_lines
               if json.loads(l).get("request_id") not in tip_ids]
    print(f"tip ledger lines={len(tip_lines)}  e245bbe lines={len(old_lines)}"
          f"  missing request_ids={len(missing)}")
    if not missing:
        print("nothing to graft — branch already complete")
        return 0

    # 2. chronology: old epochs must all precede the tip's first epoch
    old_epochs = [float(json.loads(l).get("recorded_at_epoch") or 0) for l in missing]
    tip_first = float(json.loads(tip_lines[0]).get("recorded_at_epoch") or 0)
    assert max(old_epochs) < tip_first, \
        f"epoch overlap: max(old)={max(old_epochs)} vs first(tip)={tip_first}"
    missing_sorted = [l for _, l in sorted(zip(old_epochs, missing),
                                           key=lambda t: t[0])]
    ledger.write_text("\n".join(missing_sorted + tip_lines) + "\n")
    print(f"ledger repaired: {len(missing_sorted)} records prepended "
          f"(chronology preserved), total {len(missing_sorted) + len(tip_lines)}")

    # 3. regenerate the integrity manifest over the repaired tree
    file_hashes = {}
    for p in sorted(WORK.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(WORK).as_posix()
        if rel == ".git":
            continue  # worktree pointer file, not payload
        if rel in ("MANIFEST.json", "snapshot_log.jsonl"):
            continue  # the same exclusion constants durable.py enforces
        import hashlib
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        file_hashes[rel] = h.hexdigest()
    lines = sorted(f"{p} {s}" for p, s in file_hashes.items())
    tree_sha = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    manifest = {
        "schema": 1,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reason": "graft-v4-model-routing-ledger-restore",
        "engine_commit": None,
        "engine_commit_source": "R473_out_of_band_recovery",
        "files": file_hashes,
        "tree_sha256": tree_sha,
    }
    (WORK / "MANIFEST.json").write_bytes(
        json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n")
    print(f"MANIFEST regenerated: files={len(file_hashes)} tree={tree_sha[:16]}...")

    # 4. verify before committing
    assert len(file_hashes) == 2537 + 0, f"unexpected file count {len(file_hashes)}"
    new_lines = [l for l in ledger.read_text().splitlines() if l.strip()]
    new_ids = [json.loads(l).get("request_id") for l in new_lines]
    assert len(new_ids) == len(set(new_ids)), "duplicate request_id after graft"
    epochs = [float(json.loads(l).get("recorded_at_epoch") or 0) for l in new_lines]
    assert epochs == sorted(epochs), "chronology broken after graft"
    for l in old_lines:
        assert l in set(new_lines), "an e245bbe record did not survive"
    print("verify: no duplicate ids, chronology monotone, all e245bbe records present")

    # 5. commit + push
    git("add", "-A", cwd=WORK)
    git("-c", "user.name=toscanini-runtime", "-c",
        "user.email=runtime@toscanini.local", "commit", "-m",
        "runtime-state: graft v4: the 19 earliest model_routing records "
        "(e245bbe window, epochs 1789513186-1789513547) restored onto the "
        "ledger - the residual loss the graft v3 34-lineage payload "
        "restoration could not see; integrity manifest REGENERATED over "
        "the repaired tree; the loss mechanism (restore() never "
        "re-materialized model_routing/) is closed on main in the same "
        "round (restore symmetry + shrink guard, R473)", cwd=WORK)
    push = git("push", "origin", f"HEAD:refs/heads/runtime-state-hf",
               cwd=WORK, check=False)
    if push.returncode != 0:
        print(f"PUSH FAILED: {push.stderr}")
        return 1
    head = git("rev-parse", "HEAD", cwd=WORK).stdout.strip()
    remote = git("ls-remote", "origin", "runtime-state-hf").stdout.split()[0]
    print(f"pushed: local={head[:12]} remote={remote[:12]} "
          f"match={head == remote}")
    return 0 if head == remote else 1

if __name__ == "__main__":
    sys.exit(main())
