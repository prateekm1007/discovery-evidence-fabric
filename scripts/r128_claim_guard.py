#!/usr/bin/env python3
"""R128 dir-1 (owner): claim-ID allocation guard — the registry's new
claim ids must come from the committed counter (eval/claim_next_id.txt),
monotonically, with the counter advancing in the SAME commit.

Reads the STAGED versions (git show :path) so it validates exactly what
is about to be committed. Collision-proofing across the two sessions:
after committing, push refs/claims/next (a git-ref counter) — a non-FF
push means the other session advanced the counter first, and you
re-derive from the remote before pushing the claims file.

Exits 1 with a typed message on any violation. --no-verify is the typed
escape and must be disclosed in the commit message."""
import json
import subprocess
import sys

REG = "eval/work_claims.json"
CNT = "eval/claim_next_id.txt"


def show(path, ref=":"):
    r = subprocess.run(["git", "show", f"{ref}{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True).stdout.split()
    reg_staged = REG in staged
    cnt_staged = CNT in staged
    if not reg_staged and not cnt_staged:
        return 0  # nothing this guard governs

    old_cnt = (show(CNT, "HEAD:") or "").strip() or "c-0000"
    new_cnt = (show(CNT) or "").strip() if cnt_staged else old_cnt
    old_ids = set()
    old_raw = show(REG, "HEAD:")
    if old_raw:
        try:
            old_ids = {c["claim_id"] for c in json.loads(old_raw)["claims"]}
        except Exception as e:  # noqa: BLE001
            print(f"claim guard: HEAD registry unreadable ({e}) — "
                  "refusing (fix the base first)", file=sys.stderr)
            return 1
    new_raw = show(REG) if reg_staged else old_raw
    if new_raw is None:
        print("claim guard: staged registry unreadable — refusing",
              file=sys.stderr)
        return 1
    new_ids = {c["claim_id"] for c in json.loads(new_raw)["claims"]}
    fresh = sorted(new_ids - old_ids)
    if not fresh:
        if new_cnt != old_cnt:
            print(f"claim guard: counter advanced {old_cnt}->{new_cnt} "
                  "with no new claim ids — refusing (the counter and "
                  "the registry advance atomically, one commit)", file=sys.stderr)
            return 1
        return 0

    def seq(cid):
        return int(cid.lstrip("c-")) if cid.startswith("c-") else -1

    lo, hi = seq(old_cnt), seq(new_cnt)
    for cid in fresh:
        s = seq(cid)
        if s < 0:
            print(f"claim guard: {cid} is not a c-N id — refusing",
                  file=sys.stderr)
            return 1
        if not (lo <= s < hi):
            print(f"claim guard: {cid} was NOT allocated from the "
                  f"counter (allocated range [{old_cnt}, {new_cnt})) "
                  "— refusing (dir 1: ids come from the counter; "
                  "re-derive and re-register)", file=sys.stderr)
            return 1
    if len(set(fresh)) != len(fresh):
        print("claim guard: duplicate fresh ids — refusing", file=sys.stderr)
        return 1
    print(f"claim guard: {len(fresh)} new id(s) allocated from the "
          f"counter [{old_cnt}, {new_cnt}) — OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
