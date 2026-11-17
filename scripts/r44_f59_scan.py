#!/usr/bin/env python3
"""r44_f59_scan.py — the F59 precision fix: a PER-BRANCH byte-grep for
THE LIVE token (exact match, not a shape pattern), with the exposure
set reported as exact (branch, path) pairs. The F59 lesson: the R43
disclosures over-claimed reachability by matching credential SHAPES
(ghp_*-shaped strings in scan RECORDS) rather than the live token
itself; the auditor's byte-grep governs and the reported set must
EQUAL theirs (currently r448/visual-lab × 2 files).

Custody: the token is read AT RUNTIME from the gitignored vault
(.env.keys, the sanctioned store) into memory only — this script
carries no secret, prints no value, and writes only counts and
locations. Coverage: every remote branch tip tree (git grep -F) plus
a pickaxe sweep (git log -S<token> --all) that finds every commit
where the exact byte string enters or leaves ANY reachable history —
the precise reachability answer, no shape false positives."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _vault_token() -> str:
    txt = (REPO / ".env.keys").read_text(encoding="utf-8")
    for line in txt.splitlines():
        if line.startswith("GH_PAT="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("no GH_PAT in the vault (typed abort)")


def sh(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, cwd=str(REPO))


def main():
    tok = _vault_token()
    assert tok.startswith("ghp_") and len(tok) >= 30, (
        "vault token shape unexpected (typed abort)")
    # the distinctive middle segment — matching precision without ever
    # writing the token into a command line visible in logs
    needle = tok[4:20]

    branches = sh(["git", "ls-remote", "--heads", "origin"]).stdout
    tips = {}
    for ln in branches.splitlines():
        sha, ref = ln.split()
        tips[ref.replace("refs/heads/", "")] = sha

    exposure = {}
    for br, sha in sorted(tips.items()):
        out = sh(["git", "grep", "-l", "-F", needle, sha, "--", "."],
                 timeout=300)
        paths = sorted({ln.split(":", 1)[1] for ln in
                        out.stdout.splitlines() if ":" in ln})
        if paths:
            exposure[br] = {"tip": sha[:12], "paths": paths}

    # pickaxe: every commit in ANY reachable history where the exact
    # byte string enters or leaves (the true exposure set, tips or not)
    pick = sh(["git", "log", f"-S{needle}", "--all", "--format=%H %s"],
              timeout=300)
    pickaxe_commits = []
    for ln in pick.stdout.splitlines():
        if ln.strip():
            h, _, s = ln.strip().partition(" ")
            pickaxe_commits.append({"sha": h[:12],
                                    "subject": s[:80],
                                    "on_branches": sorted(
                                        br for br, sha in tips.items()
                                        if sh(["git", "merge-base",
                                               "--is-ancestor", h, sha]
                                              ).returncode == 0)})
    # the blob locations for each pickaxe hit (path-level precision)
    loc = {}
    for c in pickaxe_commits:
        full_sha = None
        for br, sha in tips.items():
            r = sh(["git", "merge-base", "--is-ancestor",
                    c["sha"], sha])
        g = sh(["git", "grep", "-l", "-F", needle,
                c["sha"], "--", "."], timeout=120)
        paths = sorted({ln.split(":", 1)[1] for ln in
                        g.stdout.splitlines() if ":" in ln})
        if paths:
            loc[c["sha"]] = paths

    auditor_set = {"r448/visual-lab": {
        "paths": ["scripts/r447_hf_deploy.py",
                  "scripts/r447_canonical_space_record.py"]}}
    reported = {br: v["paths"] for br, v in exposure.items()}
    matches_auditor = (
        set(reported) == set(auditor_set)
        and all(sorted(reported[b]) == sorted(auditor_set[b]["paths"])
                for b in auditor_set))
    result = {
        "record": "R44_F59_EXPOSURE_SCAN/1.0.0",
        "method": "exact live-token byte-grep (git grep -F, the "
                  "distinctive middle segment) over EVERY remote "
                  "branch tip tree + a git log -S pickaxe sweep over "
                  "all reachable history; values never printed or "
                  "written",
        "n_branches_scanned": len(tips),
        "exposure_set": exposure,
        "pickaxe_commits": pickaxe_commits,
        "pickaxe_blob_locations": loc,
        "auditor_byte_verified_set": auditor_set,
        "exposure_set_equals_auditor": matches_auditor,
        "f59_note": "the R43 verifier record's 'R451/CREDENTIAL_SCAN_* "
                    "carry credential-shaped strings reachable from "
                    "main' was a SHAPE match, not the live token — "
                    "F59 opened for the over-claim; this scan "
                    "supersedes it with the exact-token set",
        "written": "2026-11-17"}
    out = REPO / "eval" / "r44_f59_scan.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print("branches scanned:", len(tips))
    print("tip exposure set:",
          json.dumps({b: v["paths"] for b, v in exposure.items()}))
    print("pickaxe commits:", len(pickaxe_commits))
    print("exposure_set_equals_auditor:", matches_auditor)


if __name__ == "__main__":
    main()
