#!/usr/bin/env python3
"""R146s1-b conflict resolver: semantic merge of the work-claims registry
for the repeated non-FF rebase cycles (the twin pushes while this lane
verifies). Reads the git STAGES (ours=mine / theirs=twin), never the
conflicted working file.

Merge semantics (idempotent, order-independent):
  - claims: dict-union by claim_id, theirs wins on the SAME id EXCEPT
    my c-0252 infra_state (typed only on my side)
  - trailer_violations / canonical_claim_violations / corrections:
    set-union by sha (or id) prefix — dedupes the peer-catch overlap
    (both lanes registered 1d5954da3; one entry survives)
  - c-0250 artifact_paths: union of both sides
  - counter: the max (lexicographic on c-NNNN)
Usage: python3 scripts/r146s1b_resolve_registry.py <theirs_rev>
"""
import json
import subprocess
import sys

THEIRS = sys.argv[1] if len(sys.argv) > 1 else "origin/queue/dev12_r7"
MINE = sys.argv[2] if len(sys.argv) > 2 else "REBASE_HEAD"


def show(rev):
    return json.loads(subprocess.run(
        ["git", "show", f"{rev}:eval/work_claims.json"],
        capture_output=True, text=True, check=True).stdout)


def resolve(theirs_rev, mine_rev):
    reg_t = show(theirs_rev)
    reg_m = show(mine_rev)
    reg = reg_t  # theirs is the base (their registry rewrite)

    by_id = {c["claim_id"]: c for c in reg["claims"]}
    m_by = {c["claim_id"]: c for c in reg_m["claims"]}

    # claims union (theirs wins per id, except my typed fields)
    for cid, mc in m_by.items():
        if cid not in by_id:
            reg["claims"].append(mc)
            by_id[cid] = mc
    if "c-0252" in m_by and "infra_state" in m_by["c-0252"]:
        by_id["c-0252"]["infra_state"] = m_by["c-0252"]["infra_state"]

    # violation registers: union by sha/id prefix
    for key in ("trailer_violations", "canonical_claim_violations",
                "corrections"):
        seen = set()
        out = []
        for src in (reg.get(key, []), reg_m.get(key, [])):
            for v in src:
                k = str(v.get("sha") or v.get("id") or "")[:10]
                if k and k in seen:
                    continue
                seen.add(k)
                out.append(v)
        reg[key] = out

    # c-0250 paths union + note
    if "c-0250" in by_id and "c-0250" in m_by:
        a = by_id["c-0250"]
        b = m_by["c-0250"]
        a["artifact_paths"] = sorted(
            set(a.get("artifact_paths", []))
            | set(b.get("artifact_paths", [])))
        if "paths_note" in b:
            a["paths_note"] = b["paths_note"]

    # counter: max
    ct = subprocess.run(["git", "show",
                         f"{theirs_rev}:eval/claim_next_id.txt"],
                        capture_output=True, text=True).stdout.strip()
    try:
        cm = subprocess.run(["git", "show",
                             f"{mine_rev}:eval/claim_next_id.txt"],
                            capture_output=True, text=True).stdout.strip()
    except Exception:
        cm = "c-0000"
    counter = max(ct, cm)
    return reg, counter


if __name__ == "__main__":
    reg, counter = resolve(THEIRS, MINE)
    with open("eval/work_claims.json", "w") as f:
        json.dump(reg, f, ensure_ascii=True, indent=2)
        f.write("\n")
    with open("eval/claim_next_id.txt", "w") as f:
        f.write(counter + "\n")
    n_claims = len(reg["claims"])
    print(f"resolved: {n_claims} claims; counter {counter}")
