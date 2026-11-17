#!/usr/bin/env python3
"""scripts/r51_secret_verification.py — P0.3 content-level verification.

Takes the R50 prefix-level enumeration (eval/r50_secret_scan_partial.json)
and classifies every distinct hit at CONTENT level:

  - pattern_mention  : the string is a regex/pattern fragment inside a
                       scanner, test, or audit script (the literal
                       'ghp_' prefix followed by a pattern, not a token)
  - audit_record     : the file is itself a credential-audit / security
                       -scan / round-record document discussing tokens
  - masked_or_short  : the matched string is shorter than a real token
                       of that provider's format (e.g. ghp_ + <36 chars)
  - full_format      : the string matches the provider's REAL token
                       shape (ghp_ + 36+ alnum; nvapi- + 30+; sk-or- +
                       60+; github_pat_ + 22+ [fine-grained]) — flagged
                       LIVE-LOOKING; each such file goes to the report
                       with branch+path (F59 precision), and the
                       remediation stays the P0.1 owner act (rotation +
                       history scrub) regardless of usability.

Also re-probes the two known findings precisely:
  - F45: is the vault GH_PAT value present on any public ref (exact
         value comparison in-process; the value is NEVER printed)?
  - F60: are *_PRIVATE.json rubric files reachable UNAUTHENTICATED
         (raw.githubusercontent, no auth header) — HTTP 200 = public.

Output: eval/r51_secret_verification.json. Zero LLM, zero external
credential use (the vault PAT is used only for the F45 equality test
in-process; unauth probes deliberately carry NO credentials).
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r51_secret_verification.json"

PROVIDER_RE = {
    "ghp_": re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    "gho_": re.compile(r"gho_[A-Za-z0-9]{36,}"),
    "github_pat_": re.compile(r"github_pat_[A-Za-z0-9_]{82,}"),
    "nvapi-": re.compile(r"nvapi-[A-Za-z0-9_-]{30,}"),
    "sk-or-": re.compile(r"sk-or-[A-Za-z0-9-]{60,}"),
}
SHORT_RE = {
    "ghp_": re.compile(r"ghp_[A-Za-z0-9]{4,35}\b"),
    "gho_": re.compile(r"gho_[A-Za-z0-9]{4,35}\b"),
    "github_pat_": re.compile(r"github_pat_[A-Za-z0-9_]{4,81}\b"),
    "nvapi-": re.compile(r"nvapi-[A-Za-z0-9_-]{4,29}\b"),
    "sk-or-": re.compile(r"sk-or-[A-Za-z0-9-]{4,59}\b"),
}
PATTERN_CONTEXT_RE = re.compile(
    r"(re\.compile|regex|\[A-Za-z0-9\]|\{20,\}|\{36,\}|pattern|REDACTED"
    r"|xxxx|MASKED|fingerprint|redact)", re.I)
AUDIT_PATH_RE = re.compile(
    r"(AUDIT|SECRETS|SECURITY|RECORD|credential|_SCAN|HISTORICAL|"
    r"LIVE_PROOF|env_view)", re.I)


def vault_value(key: str) -> str:
    for line in (REPO / ".env.keys").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def ref_blob(ref: str, path: str) -> str:
    r = subprocess.run(["git", "show", f"{ref}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def classify(ref: str, path: str, prefix: str) -> dict:
    blob = ref_blob(ref, path)
    if not blob:
        return {"class": "unreadable", "live_looking": []}
    full = PROVIDER_RE[prefix].findall(blob)
    classes = []
    if PATTERN_CONTEXT_RE.search(blob) and not full:
        classes.append("pattern_mention")
    if AUDIT_PATH_RE.search(path):
        classes.append("audit_record")
    if full:
        classes.append("full_format")
    elif SHORT_RE[prefix].search(blob):
        classes.append("masked_or_short")
    if not classes:
        classes.append("pattern_mention")
    return {"class": classes[0], "classes": classes,
            "live_looking": full[:3] if False else
            [f"<{prefix}+{len(t) - len(prefix)} chars>" for t in full[:3]]}


def main() -> None:
    scan = json.loads((REPO / "eval" / "r50_secret_scan_partial.json")
                      .read_text())
    hits = scan.get("hits", {})
    # only path-form entries (ref:path) are content-verifiable here
    by_prefix = defaultdict(list)
    for pat, entries in hits.items():
        for e in entries:
            if ":" in e:
                ref, path = e.split(":", 1)
                by_prefix[pat].append((ref, path))
    verified = {}
    live_looking = []
    for pat, pairs in sorted(by_prefix.items()):
        classes = defaultdict(list)
        for ref, path in pairs:
            c = classify(ref, path, pat)["class"]
            classes[c].append(f"{ref}:{path}")
        verified[pat] = {k: len(v) for k, v in classes.items()}
        if "full_format" in classes:
            for p in classes["full_format"]:
                live_looking.append({"pattern": pat, "location": p})
    # F45: exact vault-value presence on any public ref (value never
    # printed)
    pat_value = vault_value("GH_PAT")
    f45 = {"checked": bool(pat_value), "locations": []}
    if pat_value:
        refs = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)"],
            capture_output=True, text=True).stdout.split()
        for ref in refs:
            r = subprocess.run(["git", "grep", "-l", pat_value, ref, "--"],
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                f45["locations"].append(line)
    f45["verdict"] = ("LIVE LEAK CONFIRMED" if f45["locations"]
                      else "vault value not found on any ref")
    # F60: unauth probe of *_PRIVATE.json on the public default branch
    f60 = {"probes": []}
    names = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "origin/main"],
        capture_output=True, text=True).stdout.splitlines()
    private_paths = [p for p in names if p.endswith("_PRIVATE.json")]
    for p in private_paths:
        url = ("https://raw.githubusercontent.com/prateekm1007/"
               "discovery-evidence-fabric/main/" + p)
        req = urllib.request.Request(url, headers={"User-Agent":
                                                   "unauth-probe"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                status, size = r.status, len(r.read())
        except urllib.error.HTTPError as e:
            status, size = e.code, 0
        except Exception as ex:
            status, size = f"{type(ex).__name__}", 0
        f60["probes"].append({"path": p, "unauth_status": status,
                              "bytes": size})
    f60["verdict"] = ("PUBLIC — unauth 200 on "
                      f"{sum(1 for x in f60['probes'] if x['unauth_status'] == 200)}"
                      f"/{len(f60['probes'])} rubric files"
                      if f60["probes"] else "no *_PRIVATE.json on main")
    out = {
        "record": "R51_SECRET_VERIFICATION/1.0.0",
        "session": "builder-r51s1",
        "method": "content-level classification of the r50 prefix hits "
                  "(provider-format regexes; pattern-context + audit-path "
                  "context checks) + F45 exact-value presence scan (value "
                  "never printed) + F60 unauth raw probes",
        "classification_counts": verified,
        "live_looking": live_looking,
        "f45_vault_pat": f45,
        "f60_rubric_unauth": f60,
        "remediation": "any full_format/live finding is remediated by the "
                       "P0.1 owner act (rotation + private custody + "
                       "history scrub); classification never deletes or "
                       "rewrites history",
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({"classification_counts": verified,
                      "live_looking_n": len(live_looking),
                      "f45": f45["verdict"],
                      "f45_locations": f45["locations"],
                      "f60": f60["verdict"]}, indent=1))


if __name__ == "__main__":
    main()
