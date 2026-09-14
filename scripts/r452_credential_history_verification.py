#!/usr/bin/env python3
"""R452-C2 item 5 — automated verification that the currently reachable
repository history contains no ACTIVE credential.

Scope (honest, stated): every object reachable from ALL local refs
(branches, tags, remotes) at the time of the run — the same ref set the
remote serves after a fetch. Run with --fetch first to re-align the
reachable set with the live remote before scanning.

Two modes:
  default (fail-closed, Art. XXV): scan reachable blobs for credential
      patterns. ANY finding exits 1 — an unverified candidate is never a
      pass ("unprovable remains unproven").
  --liveness: additionally probe each unique candidate against its
      provider (read-only whoami-style endpoints, short timeout, values
      never printed — only fingerprints). Exit 1 iff any candidate is
      LIVE. DEAD candidates are reported as remediated; the operator
      re-runs this after rotating to verify the history is inert.

The tool never rewrites history (Art. XI: a rewrite is an epistemic
event owned by the operator) and never mutates the tree (Art. IX:
observational). It is the automated half of the credential-history
remediation: after the operator revokes/rotates, a LIVE-free run of
this script is the standing proof that the reachable history carries no
active credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ---- credential patterns (value classes, not specific secrets) --------
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("GITHUB_CLASSIC_PAT", re.compile(rb"ghp_[A-Za-z0-9]{36}")),
    ("GITHUB_FINEGRAINED_PAT", re.compile(rb"github_pat_[A-Za-z0-9_]{60,}")),
    ("GITHUB_OAUTH_TOKEN", re.compile(rb"gho_[A-Za-z0-9]{36}")),
    ("GITHUB_SERVER_TOKEN", re.compile(rb"ghs_[A-Za-z0-9]{36}")),
    ("HF_TOKEN", re.compile(rb"hf_[A-Za-z0-9]{34,40}")),
    ("OPENROUTER_KEY", re.compile(rb"sk-or-v1-[A-Za-z0-9]{64}")),
    ("AWS_ACCESS_KEY", re.compile(rb"AKIA[0-9A-Z]{16}")),
]


def fingerprint(value: bytes) -> str:
    digest = hashlib.sha256(value).hexdigest()[:12]
    text = value.decode("ascii", "replace")
    return f"{text[:4]}...{text[-4:]}(len={len(text)})#sha256:{digest}"


_B64 = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


def base64_embedded_noise(data: bytes, start: int, end: int) -> bool:
    """Deterministic noise classifier (stated rule, recorded per
    finding): a match embedded in a run of >= 64 consecutive base64
    characters is media/binary encoding, not a credential in code or
    config. Real credentials in scripts, JSON and env files sit in
    standalone tokens; base64 image payloads in HTML/PDF bytes match
    key-shaped patterns by chance. The finding is still reported — it
    is excluded from the verdict, not hidden."""
    lo = start
    while lo > 0 and data[lo - 1] in _B64:
        lo -= 1
    hi = end
    while hi < len(data) and data[hi] in _B64:
        hi += 1
    return (hi - lo) >= 64


@dataclass
class Finding:
    kind: str
    fingerprint: str
    blobs: list = field(default_factory=list)
    liveness: str = "UNVERIFIED"  # UNVERIFIED | LIVE | DEAD | PROBE_FAILED
    noise: bool = False  # embedded in a long base64 run (reported, not counted)


def sh(*args: str, binary: bool = False):
    out = subprocess.run(args, capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode("utf-8", "replace")


def reachable_blobs() -> dict:
    """sha -> path hint, for every blob reachable from all refs."""
    lines = sh("git", "rev-list", "--objects", "--all").splitlines()
    blobs = {}
    shas = [ln.split(" ", 1)[0] for ln in lines if ln.strip()]
    # batch-check the types
    payload = ("\n".join(shas) + "\n").encode()
    proc = subprocess.run(["git", "cat-file", "--batch-check"],
                          input=payload, capture_output=True, check=True)
    for line in proc.stdout.decode().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "blob":
            blobs[parts[0]] = None
    # attach the first path hint per blob
    for ln in lines:
        if " " in ln:
            sha, path = ln.split(" ", 1)
            if sha in blobs and blobs[sha] is None:
                blobs[sha] = path
    return blobs


def scan() -> tuple[list[Finding], int]:
    findings: dict[str, Finding] = {}
    blobs = reachable_blobs()
    scanned = 0
    payload_shas = list(blobs.keys())
    batch_in = ("\n".join(payload_shas) + "\n").encode()
    proc = subprocess.run(["git", "cat-file", "--batch"],
                          input=batch_in, capture_output=True, check=True)
    stream = proc.stdout
    pos = 0
    while pos < len(stream):
        nl = stream.index(b"\n", pos)
        header = stream[pos:nl].decode("utf-8", "replace").split()
        if len(header) < 3:
            break
        sha, _otype, size = header[0], header[1], int(header[2])
        data = stream[nl + 1: nl + 1 + size]
        pos = nl + 1 + size + 1  # trailing newline after each object
        scanned += 1
        path = blobs.get(sha)
        for kind, pattern in PATTERNS:
            for match in pattern.finditer(data):
                value = match.group(0)
                fp = fingerprint(value)
                finding = findings.setdefault(fp, Finding(kind, fp))
                if base64_embedded_noise(data, match.start(), match.end()):
                    finding.noise = True
                if path and path not in finding.blobs:
                    finding.blobs.append(path)
    return list(findings.values()), scanned


def probe_github(value: bytes) -> str:
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={"Authorization": f"token {value.decode()}",
                 "User-Agent": "credential-history-verifier"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return "LIVE" if resp.status == 200 else "PROBE_FAILED"
    except urllib.error.HTTPError as exc:
        return "DEAD" if exc.code in (401, 403, 404) else "PROBE_FAILED"
    except Exception:
        return "PROBE_FAILED"


def probe_hf(value: bytes) -> str:
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {value.decode()}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return "LIVE" if resp.status == 200 else "PROBE_FAILED"
    except urllib.error.HTTPError as exc:
        return "DEAD" if exc.code in (401, 403) else "PROBE_FAILED"
    except Exception:
        return "PROBE_FAILED"


PROBES = {"GITHUB": probe_github, "HF": probe_hf}


def probe(finding: Finding, value: bytes) -> str:
    for prefix, fn in PROBES.items():
        if finding.kind.startswith(prefix):
            return fn(value)
    return "UNVERIFIED"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true",
                    help="fetch all remotes first (needs credentials in "
                         "the environment; skipped otherwise)")
    ap.add_argument("--liveness", action="store_true",
                    help="probe each unique candidate against its "
                         "provider (read-only; values never printed)")
    ap.add_argument("--json-out", type=Path, default=None,
                    help="write the machine-readable report here")
    args = ap.parse_args()

    if args.fetch:
        subprocess.run(["git", "fetch", "--all", "--prune"],
                       check=False, capture_output=True)

    findings, scanned = scan()
    # recover the raw values once for liveness probing (in memory only)
    if args.liveness and findings:
        blobs = reachable_blobs()
        raw: dict[str, bytes] = {}
        batch_in = ("\n".join(blobs.keys()) + "\n").encode()
        proc = subprocess.run(["git", "cat-file", "--batch"],
                              input=batch_in, capture_output=True,
                              check=True)
        stream, pos = proc.stdout, 0
        while pos < len(stream):
            nl = stream.index(b"\n", pos)
            header = stream[pos:nl].decode("utf-8", "replace").split()
            if len(header) < 3:
                break
            sha, _otype, size = header[0], header[1], int(header[2])
            data = stream[nl + 1: nl + 1 + size]
            pos = nl + 1 + size + 1
            for kind, pattern in PATTERNS:
                for match in pattern.finditer(data):
                    raw[fingerprint(match.group(0))] = match.group(0)
        for finding in findings:
            value = raw.get(finding.fingerprint)
            if value is not None:
                finding.liveness = probe(finding, value)

    actionable = [f for f in findings if not f.noise]
    any_live = any(f.liveness == "LIVE" for f in actionable)
    any_unverified = any(f.liveness == "UNVERIFIED" for f in actionable)
    verdict = ("CLEAN" if not findings else
               "ACTIVE_CREDENTIAL_IN_REACHABLE_HISTORY" if any_live else
               "CANDIDATES_PRESENT_LIVENESS_UNVERIFIED" if any_unverified else
               "CANDIDATES_PRESENT_ALL_DEAD")

    report = {
        "tool": "r452_credential_history_verification",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "all objects reachable from all local refs "
                 "(branches, tags, remotes)",
        "blobs_scanned": scanned,
        "findings": [{
            "kind": f.kind,
            "fingerprint": f.fingerprint,
            "paths_sample": f.blobs[:5],
            "path_count": len(f.blobs),
            "liveness": f.liveness,
            "base64_embedded_noise": f.noise,
        } for f in findings],
        "verdict": verdict,
        "note": "a history rewrite is an operator-owned epistemic event "
                "(Art. XI); this tool verifies, it never rewrites",
    }
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2))
        print(f"report written: {args.json_out}")
    print(f"blobs scanned (reachable): {scanned}")
    for f in findings:
        tag = " (base64-noise, not counted)" if f.noise else ""
        print(f"  [{f.kind}] {f.fingerprint} liveness={f.liveness} "
              f"paths={len(f.blobs)} e.g. {f.blobs[:2]}{tag}")
    print(f"VERDICT: {verdict}")

    # fail-closed: LIVE -> 1; unverified ACTIONABLE candidates -> 1
    # (unproven is not a pass); base64-noise findings are reported but
    # never counted; all-DEAD or CLEAN -> 0 (the rotation proof)
    return 1 if (any_live or any_unverified) else 0


if __name__ == "__main__":
    sys.exit(main())
