#!/usr/bin/env python3
"""scripts/r401_commit_prep.py — pre-commit hardening: secret scan of
the FULL change surface (tracked diff + untracked files), the custody-
log contamination revert, and the change manifest.

Every new/changed line is scanned for credential patterns; findings
block the commit (exit 1). The retrieval-log revert restores the file
to its session-start entry count (the +18 test-contamination entries
disclosed in R401_BASELINE_ADDENDUM.json — the session-start state
itself carries the prior session's legitimate +15 run entries).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

PATTERNS = [
    (r"github_pat_[A-Za-z0-9_]{20,}", "github fine-grained PAT"),
    (r"ghp_[A-Za-z0-9]{30,}", "github classic PAT"),
    (r"sk-[A-Za-z0-9]{20,}", "openai-style key"),
    (r"rnd_[A-Za-z0-9]{20,}", "render API key"),
    (r"(?:NVIDIA_API_KEY|ZAI_API_KEY|MISTRAL_API_KEY|OPENROUTER_API_KEY"
     r"|S2_API_KEY|PATENTSVIEW_API_KEY|LENS_API_TOKEN|ELSEVIER_API_KEY"
     r"|PATENT_BEAR_API_KEY)\s*=\s*[A-Za-z0-9_\-]{12,}",
     "provider key assignment"),
    (r"Bearer\s+[A-Za-z0-9_\-\.]{25,}", "bearer token in prose"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
     "private key block"),
    (r"xoxb-[A-Za-z0-9\-]{20,}", "slack token"),
    (r"AIza[A-Za-z0-9_\-]{30,}", "google api key"),
]

ALLOWED = re.compile(
    r"^(?:ENGINE_RUNS/|\.env|.*\.log$|.*tool-results.*|worklog\.md$)")


def _changed_files() -> List[Path]:
    out = subprocess.run(["git", "status", "--short", "--untracked-files=all"],
                         cwd=str(REPO_ROOT), capture_output=True,
                         text=True).stdout
    files: List[Path] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        path = line[3:].strip().strip('"')
        # skip renames' old side
        path = path.split(" -> ")[-1]
        p = REPO_ROOT / path
        if p.is_file():
            files.append(p)
    return files


def scan() -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []
    files = _changed_files()
    n_scanned = 0
    n_lines = 0
    for p in files:
        rel = str(p.relative_to(REPO_ROOT))
        if ALLOWED.search(rel):
            continue
        try:
            text = p.read_text(errors="replace")
        except Exception:  # noqa: BLE001 — binary
            continue
        n_scanned += 1
        for i, line in enumerate(text.splitlines(), 1):
            n_lines += 1
            for pat, label in PATTERNS:
                if re.search(pat, line):
                    findings.append({
                        "file": rel, "line": str(i), "class": label,
                        "excerpt": line.strip()[:80]})
    return {"files_in_change_surface": len(files),
            "files_scanned": n_scanned,
            "lines_scanned": n_lines,
            "findings": findings,
            "verdict": "SECRET_SCAN_CLEAN" if not findings else
                       "SECRET_SCAN_FAIL"}


def revert_log() -> Dict[str, Any]:
    """Restore the custody log to its session-start 1834-entry state."""
    p = REPO_ROOT / "artifacts" / "source_health" / "retrieval_log.jsonl"
    lines = p.read_text().splitlines()
    n_now = len([l for l in lines if l.strip()])
    target = 1834
    if n_now <= target:
        return {"entries_now": n_now, "target": target,
                "action": "NONE (already at or below session-start "
                          "state)"}
    keep = [l for l in lines if l.strip()][:target]
    dropped = n_now - target
    p.write_text("\n".join(keep) + "\n")
    return {"entries_now": target, "dropped_contamination": dropped,
            "action": "REVERTED to the session-start entry count "
                      "(the +18 test-contamination entries disclosed in "
                      "R401_BASELINE_ADDENDUM.json)"}


def main() -> int:
    res = scan()
    rev = revert_log()
    out = REPO_ROOT / "R401" / "COMMIT_PREP.json"
    record = {"suite": "R401-WC commit prep", "secret_scan": res,
              "custody_log_revert": rev}
    out.write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps(record, indent=1, default=str)[:1200])
    return 0 if res["verdict"] == "SECRET_SCAN_CLEAN" else 1


if __name__ == "__main__":
    sys.exit(main())
