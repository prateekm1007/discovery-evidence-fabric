#!/usr/bin/env python3
"""github_scan.py — the worldwide-GitHub target scanner (owner
merged-and-locked DIR 8; builder-r190s1).

Scans the named targets (GitHub REST API; the PAT is read from
.env.keys, env-only, never committed — an unauthenticated fallback
covers public metadata at a lower rate limit) and records, per target,
the repo state (exists / stars / last push / license) and the TYPED
WIRING DECISION the owner locked:

  MOOSE-Chem (ZonglinY/MOOSE-Chem)        -> WIRED (the Score-7
     rediscovery benchmark; eval/moose_chem/rediscovery_benchmark.json)
  AutoTRIZ (contradiction matrix)         -> typed principle table,
     OPTIONAL amplification, parked UNTIL DIR-4 measures
  CNIPA / AutoPatent (wangziying1004/AutoPatent,
     fanfanbox/triz-innovation-toolkit)    -> Score-8 prior-art, PARKED
     until an item needs Chinese literature
  HypoBench (rubric)                      -> Score-7 SCORING ONLY
  DO NOT INTEGRATE (typed, with the measured basis):
     open-collider (measured zero TWICE), SciAgents, FlagEmbedding

Writes: eval/github_scan_<YYYY-MM-DD>.json
Exit codes: 0 = scanned; 3 = typed refusal (no network / API down).
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUTD = REPO / "eval"

TARGETS = [
    {"key": "MOOSE-Chem", "full": "ZonglinY/MOOSE-Chem",
     "search": "MOOSE-Chem chemistry hypothesis rediscovery",
     "decision": "WIRED: the Score-7 rediscovery benchmark "
                 "(eval/moose_chem/rediscovery_benchmark.json; 51 "
                 "post-cutoff 2024 items; xlsx sha256 "
                 "6ebd5c313319e981...)",
     "basis": "ICLR 2025 (arXiv 2410.07076); the benchmark's items are "
              "real post-cutoff Nature/Science-level hypotheses with "
              "the true mechanism as the rediscovery target"},
    {"key": "AutoTRIZ", "full": None,
     "search": "AutoTRIZ contradiction matrix TRIZ invention",
     "decision": "TYPED PRINCIPLE TABLE (optional amplification) — "
                "PARKED until DIR-4 measures; the contradiction "
                "matrix becomes a typed principle table only on a "
                "measured need",
     "basis": "owner: optional amplification after DIR-4 measures"},
    {"key": "AutoPatent", "full": "wangziying1004/AutoPatent",
     "search": "AutoPatent automated patent generation",
     "decision": "Score-8 prior-art — PARKED until an item needs "
                "Chinese literature",
     "basis": "owner: park until an item needs Chinese literature"},
    {"key": "triz-innovation-toolkit", "full": "fanfanbox/"
     "triz-innovation-toolkit",
     "search": "TRIZ innovation toolkit contradiction principles",
     "decision": "Score-8 prior-art (with AutoPatent/CNIPA) — PARKED",
     "basis": "owner: park until an item needs Chinese literature"},
    {"key": "HypoBench", "full": None,
     "search": "HypoBench hypothesis benchmark rubric",
     "decision": "Score-7 SCORING ONLY (the rubric shapes the "
                "mechanism-match scoring; never a generator component)",
     "basis": "owner: HypoBench rubric -> Score-7 scoring only"},
    {"key": "open-collider", "full": None,
     "search": "open collider LLM idea collision",
     "decision": "DO NOT INTEGRATE", "basis": "measured ZERO twice"},
    {"key": "SciAgents", "full": None,
     "search": "SciAgents scientific discovery agents",
     "decision": "DO NOT INTEGRATE", "basis": "owner exclusion"},
    {"key": "FlagEmbedding", "full": None,
     "search": "FlagEmbedding BAAI embedding library",
     "decision": "DO NOT INTEGRATE", "basis": "owner exclusion"},
]


def _token() -> str:
    env = REPO / ".env.keys"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith(("GH_PAT=", "GITHUB_TOKEN=")):
                return line.split("=", 1)[1]
    import os
    return os.environ.get("GH_PAT", "")


def _get(url: str, token: str, timeout: float = 25.0):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def scan() -> int:
    token = _token()
    out = {
        "record": "GITHUB_SCAN/1.0.0",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "scanner": "scripts/github_scan.py",
        "auth": "authenticated" if token else "unauthenticated",
        "targets": [],
    }
    failures = 0
    for t in TARGETS:
        entry = {"key": t["key"], "decision": t["decision"],
                 "basis": t["basis"], "repo": None, "search_top": None}
        if t["full"]:
            try:
                d = _get(f"https://api.github.com/repos/{t['full']}",
                         token)
                entry["repo"] = {
                    "full_name": d.get("full_name"),
                    "exists": True,
                    "stars": d.get("stargazers_count"),
                    "pushed_at": d.get("pushed_at"),
                    "license": (d.get("license") or {}).get("spdx_id"),
                    "description": (d.get("description") or "")[:160],
                    "html_url": d.get("html_url"),
                }
            except Exception as e:  # noqa: BLE001 typed, per-target
                entry["repo"] = {"exists": False,
                                 "error": f"{type(e).__name__}: "
                                          f"{str(e)[:120]}"}
                failures += 1
        try:
            q = urllib.request.quote(t["search"])
            d = _get(f"https://api.github.com/search/repositories?q={q}"
                     f"&per_page=3", token)
            entry["search_top"] = [
                {"full_name": it.get("full_name"),
                 "stars": it.get("stargazers_count"),
                 "pushed_at": it.get("pushed_at")}
                for it in (d.get("items") or [])[:3]]
        except Exception as e:  # noqa: BLE001
            entry["search_top"] = {"error": f"{type(e).__name__}: "
                                            f"{str(e)[:120]}"}
        out["targets"].append(entry)
    out["n_targets"] = len(out["targets"])
    out["n_repo_failures"] = failures
    outp = OUTD / f"github_scan_{date.today().isoformat()}.json"
    outp.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"{outp}: {out['n_targets']} targets, {failures} repo lookup "
          "failures")
    if failures and failures == len(TARGETS):
        print("TYPED REFUSAL: every lookup failed (network/API down)")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(scan())
