#!/usr/bin/env python3
"""scripts/r52_gitleaks_gitmode.py — the GIT-MODE full-history secret
scan (roadmap P0 R52 item; claim c-0069). The gitleaks binary is not
available in this environment (typed in the record), so this runs the
gitleaks SEMANTICS with provider-format regexes over:
  1. every commit MESSAGE in the full history (git log --format=%B),
  2. every blob at every commit (git log -p --full-history) —
     i.e. tree content AND commit messages, the scope the R50/R51
     tree-blob scans missed (the 2 Aug-18 keys live in commit
     messages per the auditor's finding).
Findings are provider-format token SHAPES only; the scan never prints
a token value — hits are reported as (commit, provider, char-length,
path-or-message) with a 4-char masked prefix. The vault's own values
are additionally checked for exact-value presence in history (in
process, values never printed).

Output: eval/r52_gitleaks_gitmode.json appended to the enumeration
report lineage (r50_secret_scan_partial.json -> r51_secret_verification
.json -> this). Zero LLM, zero network.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r52_gitleaks_gitmode.json"

PROVIDERS = {
    "ghp_": re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    "gho_": re.compile(r"gho_[A-Za-z0-9]{36,}"),
    "github_pat_": re.compile(r"github_pat_[A-Za-z0-9_]{82,}"),
    "nvapi-": re.compile(r"nvapi-[A-Za-z0-9_-]{30,}"),
    "sk-or-": re.compile(r"sk-or-[A-Za-z0-9-]{60,}"),
    "sk-ant-": re.compile(r"sk-ant-[A-Za-z0-9_-]{40,}"),
    "AKIA": re.compile(r"AKIA[0-9A-Z]{16}"),
    "xoxb-": re.compile(r"xoxb-[0-9A-Za-z-]{20,}"),
}


def _mask(tok: str, prefix_len: int = 4) -> str:
    return tok[:prefix_len] + "…" + f"<{len(tok)} chars>"


def scan_messages() -> list:
    log = subprocess.run(
        ["git", "log", "--all", "--format=%H%x00%B%x00"],
        capture_output=True, text=True).stdout
    hits = []
    for chunk in log.split("\x00"):
        chunk = chunk.strip()
        if len(chunk) < 45 or "\n" not in chunk:
            continue
        sha = chunk.split("\n", 1)[0][:12]
        body = chunk.split("\n", 1)[1]
        for prov, rx in PROVIDERS.items():
            for tok in rx.findall(body):
                hits.append({"where": "commit_message", "commit": sha,
                             "provider": prov, "sample": _mask(tok)})
    return hits


def scan_patches() -> list:
    # every added/changed line in the full history (all branches),
    # STREAMED line-by-line (the buffered variant was OOM-killed at
    # 137 on this repo's history — typed in the record)
    proc = subprocess.Popen(
        ["git", "log", "--all", "-p", "--full-history", "-U0",
         "--format=commit %H"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        encoding="utf-8", errors="replace", bufsize=1)
    hits = []
    cur = None
    curfile = None
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.startswith("commit "):
            cur = line.split()[1][:12]
        elif line.startswith("+++ b/"):
            curfile = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            for prov, rx in PROVIDERS.items():
                for tok in rx.findall(body):
                    hits.append({"where": "patch_line",
                                 "commit": cur, "path": curfile,
                                 "provider": prov,
                                 "sample": _mask(tok)})
    proc.stdout.close()
    proc.wait()
    return hits


def scan_vault_values() -> list:
    vals = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if len(v.strip()) >= 12:
                vals[k.strip()] = v.strip()
    hits = []
    # per-ref exact-value presence (the `git grep val --all` form was
    # silently searching a PATH named --all — the R51 per-ref loop is
    # the proven correct method)
    refs = subprocess.run(["git", "for-each-ref", "--format=%(refname)"],
                          capture_output=True, text=True).stdout.split()
    for name, val in vals.items():
        for ref in refs:
            r = subprocess.run(["git", "grep", "-I", "-l", val, ref, "--"],
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                hits.append({"credential": name, "location": line,
                             "note": "exact vault value present in "
                                     "reachable history"})
    return hits


def main() -> None:
    msgs = scan_messages()
    patches = scan_patches()
    vault = scan_vault_values()
    by_prov = {}
    for h in msgs + patches:
        by_prov.setdefault(h["provider"], 0)
        by_prov[h["provider"]] += 1
    out = {
        "record": "R52_GITLEAKS_GITMODE/1.0.0",
        "session": "builder-r52s1",
        "method": "git-mode full-history scan with gitleaks semantics "
                  "(provider-format regexes over every commit message "
                  "in --all history, every added patch line, and exact "
                  "vault-value presence). The gitleaks BINARY is not "
                  "available in this environment (typed gap; the "
                  "CI-wired gitleaks step remains queued). No token "
                  "value is ever printed — 4-char masked prefixes only.",
        "scope_note": "this closes the R50/R51 tree-blob-only scope "
                      "gap the auditor named: commit messages and "
                      "patch lines across --all refs are now scanned",
        "counts_by_provider": by_prov,
        "commit_message_hits": msgs,
        "patch_line_hits_sample": patches[:40],
        "patch_line_hits_total": len(patches),
        "vault_value_history_hits": vault,
        "verdict": ("FINDINGS PRESENT — see counts; remediation stays "
                    "the P0.1 owner act (rotation + scrub)" if
                    (msgs or patches or vault) else
                    "0 findings in full history"),
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({"counts_by_provider": by_prov,
                      "message_hits": len(msgs),
                      "patch_hits_total": len(patches),
                      "vault_value_hits": len(vault),
                      "verdict": out["verdict"]}, indent=1))


if __name__ == "__main__":
    main()
