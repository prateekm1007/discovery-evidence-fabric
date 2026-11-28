#!/usr/bin/env python3
"""tests/test_article17_message_scan.py — EPISTEMIC v3.2.0 Art. 17 CI
wiring (AM52/V49 ratification): the secret scan extends to ALL refs and
FULL history INCLUDING COMMIT MESSAGES.

Grounded in F45/CORR-2 (auditor byte-probe): a full OpenRouter key shape
was embedded in the commit MESSAGE of 76c23fef7 — blob-only grep misses
message-embedded keys, and subject-prefix attribution misattributed the
finding to 35642149a5. The CI gate: scan every commit message on every
ref (local + remote) through the same detector battery as the blob scan,
require EXACT-SHA attribution on any finding, and fail-closed on an
unbaselined hit.

Zero LLM. Deterministic (git-local). No external calls.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import r45_all_refs_secret_scan as S  # noqa: E402

BASELINE_PATH = REPO / "eval" / "secret_scan_baseline.json"


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       cwd=REPO, timeout=120)
    assert r.returncode == 0, f"git {' '.join(args[:3])} failed: {r.stderr[-200:]}"
    return r.stdout


def _all_refs() -> list[str]:
    refs = _git("for-each-ref", "--format=%(refname)").split()
    refs += [l for l in _git("branch", "-r", "--format=%(refname)").split()]
    return sorted(set(refs))


def _all_commit_messages() -> list[tuple[str, str]]:
    """(exact_sha, message) for every commit reachable from any ref."""
    out = _git("log", "--all", "--format=%H%x1f%B%x1e")
    pairs = []
    for chunk in out.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, _, msg = chunk.partition("\x1f")
        if sha.strip():
            pairs.append((sha.strip(), msg.strip()))
    return pairs


def test_message_scan_unbaselined_zero() -> None:
    """F45 class: no commit message on any ref carries a live key shape
    outside the baseline. Findings are attributed by EXACT SHA (never a
    subject prefix)."""
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    fp_keys = {e.get("fingerprint") for e in baseline.get("baseline", [])}
    unbaselined: list[dict] = []
    for sha, msg in _all_commit_messages():
        for f in S.scan_text(msg, f"commit-message:{sha[:9]}"):
            if f.get("fingerprint") not in fp_keys:
                f["exact_sha"] = sha
                unbaselined.append(f)
    assert not unbaselined, (
        "unbaselined secret shapes in COMMIT MESSAGES (F45 class) — "
        f"{len(unbaselined)} finding(s), exact-SHA attribution: "
        + json.dumps(unbaselined[:3], default=str)[:600])


def test_findings_carry_exact_sha_attribution() -> None:
    """CORR-2 class: any finding the scanner emits (tree, history, or
    message surface) is attributed by EXACT SHA — the record schema has
    no subject-prefix-only attribution."""
    rep = REPO / "eval" / "r50_all_refs_scan_report.json"
    if rep.exists():
        doc = json.loads(rep.read_text(encoding="utf-8"))
        for f in doc.get("findings", []) + doc.get("raw_findings", []):
            prov = str(f.get("provenance", ""))
            assert f.get("exact_sha") or f.get("sha") or (
                "commit" not in prov.lower()), (
                "a commit-sourced finding without an exact SHA is the "
                "CORR-2 misattribution class")
    else:
        # the baseline carries provenance + enumeration per entry
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        for e in baseline.get("baseline", []):
            assert e.get("provenance") and e.get("fingerprint"), (
                "baseline entries carry provenance + fingerprint")


def test_history_pickaxe_surface_still_scanned() -> None:
    """The pre-existing surfaces (blob history via pickaxe, tips, staged)
    stay covered — the v3.2.0 addition EXTENDS the scan, never narrows
    it (forward-only, no verifier weakening)."""
    src = (REPO / "scripts" / "r45_all_refs_secret_scan.py").read_text(
        encoding="utf-8")
    for fn in ("scan_tips", "scan_history_pickaxe", "scan_staged",
               "scan_text"):
        assert f"def {fn}" in src, f"{fn} must remain part of the scan"
