#!/usr/bin/env python3
"""R192S2 DIR 7c: post-merge README/ACTIVE_PATH authority check — the
typed answer + the fresh-clone header fix (forward-only, no history
rewrite, nothing deleted).

The bytes (checked this session at the merged tip 7da44fae5 lineage):
  git diff ecc6a5667 origin/main -- README.md ACTIVE_PATH.md  ->  EMPTY
  => README.md and ACTIVE_PATH.md are BYTE-IDENTICAL on both merge
     sides; the r191s2 merge (737b840d8) neither introduced nor changed
     them. The legacy portfolio-factory framing (Constitution v2.10.1,
     Art. XXXIX two-repo contract, R388 ACTIVE_PATH) predates the whole
     queue lineage and is doc drift, not a merge artifact.

THE TYPED ANSWER: at the merged tip the single authoritative contract is
EPISTEMIC_CONSTITUTION.md v3.3.0 (29 articles; the in-tree current
constitution). README.md and ACTIVE_PATH.md are HISTORICAL PROGRAM
DOCUMENTS of the R388-era Toscanini/portfolio program — NOT the
authoritative contract for the capability-first invention machine.
The capability-first program of record is the Discovery Imperative
preamble of EPISTEMIC_CONSTITUTION.md + the AM52/V-latest scoreboard
lane (eval/work_claims.json, the scored eval/ artifacts).

THE FIX: a typed authority banner at the very top of BOTH files so a
fresh clone cannot mistake the portfolio-factory contract for the
current one. Nothing else in either file is altered (honest history,
not a rewrite).
"""
import json, subprocess

BASE = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=".").stdout.strip()[:9]

BANNER = """> **AUTHORITY STATUS (typed, r192s2 post-merge check):** this is a
> HISTORICAL PROGRAM DOCUMENT of the R388-era Toscanini/portfolio
> program, preserved unchanged. It is NOT the authoritative contract of
> the current capability-first invention machine. The single
> authoritative contract is `EPISTEMIC_CONSTITUTION.md` **v3.3.0** (the
> 29-article owner-directed enforcement refactor — the "Constitution
> v2.10.1 / Article XXXIX" references below are STALE pointers to the
> superseded line). The current program of record: the Discovery
> Imperative preamble of the constitution + the capability-first
> scoreboard lane (`eval/work_claims.json`, the scored `eval/`
> artifacts, AM52/V-latest). Do not read the portfolio-factory
> two-repo contract as governing.

"""

for fname in ("README.md", "ACTIVE_PATH.md"):
    t = open(fname, encoding="utf-8").read()
    if "AUTHORITY STATUS (typed, r192s2 post-merge check)" in t:
        print(f"{fname}: banner already present, skipped")
        continue
    lines = t.splitlines(keepends=True)
    # insert AFTER the first heading line
    i = 1
    while i < len(lines) and lines[i].strip():
        i += 1
    new = "".join(lines[:i]) + "\n" + BANNER + "".join(lines[i:])
    open(fname, "w", encoding="utf-8").write(new)
    print(f"{fname}: banner inserted after heading (line {i})")

rec = {
    "record": "R192S2_POSTMERGE_AUTHORITY/1.0.0",
    "checked_at_tip": BASE,
    "bytes_checked": {
        "method": "git diff ecc6a5667 (pre-merge queue tip) origin/main -- README.md ACTIVE_PATH.md",
        "result": "EMPTY — byte-identical on both merge sides",
        "conclusion": ("the r191s2 merge (737b840d8) neither introduced "
                       "nor changed README.md/ACTIVE_PATH.md; the "
                       "legacy portfolio-factory framing predates the "
                       "queue lineage and rides both sides"),
    },
    "typed_answer": {
        "authoritative_contract": "EPISTEMIC_CONSTITUTION.md v3.3.0 (29 articles) — the ONLY current constitution",
        "readme_status": "HISTORICAL (R388-era Toscanini/portfolio program doc); its v2.10.1/Art.-XXXIX pointers are STALE",
        "active_path_status": "HISTORICAL (R388 15-stage production loop; not the capability-first lane's path)",
        "not_silently_kept": ("both files now carry the typed AUTHORITY "
                              "STATUS banner; nothing deleted, no "
                              "history rewrite (Arts. 4/16)"),
        "fresh_clone_behavior": "a fresh clone reads the banner FIRST and is routed to the v3.3.0 constitution",
    },
    "fix": "banner inserted at the top of README.md and ACTIVE_PATH.md (this change)",
}
with open("eval/r192s2_postmerge_authority.json", "w", encoding="utf-8") as fh:
    json.dump(rec, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print("record written: eval/r192s2_postmerge_authority.json")
