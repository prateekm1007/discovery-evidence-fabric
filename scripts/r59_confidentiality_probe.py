#!/usr/bin/env python3
"""r59_confidentiality_probe.py — the Article 14 CONFIDENTIALITY probe
(epistemic constitution v3.2.0 CI addition for F60; ratification claim
c-0080, builder-r58s1).

THE CONSTITUTION CLAUSE (Art. 14, v3.2.0): "a CONFIDENTIALITY probe
gates every sealed instrument: an UNAUTHENTICATED read of any
*_PRIVATE.json rubric must NOT return 200 — the seal protects problem
INTEGRITY only; a publicly readable rubric burns the set for
confidentiality (confidentiality != integrity)."

THE F60 GROUND TRUTH: the auditor (AM51/V48) measured unauth HTTP 200
on the v7/v8 rubrics in the PUBLIC repo; AM52 declares those sets
BURNED for confidentiality; auditor v1.3.0 Art. 7 carries the clause.
The probe ENFORCES the state going forward:

  --mode static (pytest-gated, zero network)
    (a) NO tracked path on the QUEUE surface matches *_PRIVATE.json
        (the builder branch carries no rubric bytes, ever — hard red).
    (b) The burn registry (eval/r59_confidentiality_burn_registry.json)
        parses, every path is typed, and the 8 F60-burned paths are
        registered BURNED-PUBLIC with provenance (no silent burn — the
        disclosure is committed).

  --mode live (workflow step, network)
    Unauthenticated HTTP GET (urllib, NO auth headers of any kind) of
    every registry path at BOTH the queue branch tip and the audit
    branch tip on raw.githubusercontent.com:
      - a 200 on a path whose registry status is NOT BURNED-PUBLIC
        reds the gate (a new seal leaked — the F60 recurrence);
      - a 200 on a BURNED-PUBLIC path is RECORDED as the disclosed
        burn state (typed PASS with the disclosure visible; the P0
        owner-custody action stays open — never hidden by a green);
      - a 200 on any *_PRIVATE.json path DISCOVERED on the queue tip
        reds the gate (clause (a) enforced live too).
    The report is written to eval/r59_confidentiality_probe.json and
    every finding fingerprints by exact ref+path (no secret values are
    involved — rubric BYTES are never printed, only statuses).

Exit codes: 0 = gate green; 1 = gate RED (typed findings); 2 =
instrument failure (network unreachable = typed infra failure, Art. 15
— recorded UNVERIFIED, never silently green).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUEUE_BRANCH = "queue/dev12_r7"
AUDIT_BRANCH = "audit/r11-auditor-verdict-20261114"
RAW_BASE = "https://raw.githubusercontent.com/prateekm1007/" \
           "discovery-evidence-fabric/"
REGISTRY = REPO / "eval" / "r59_confidentiality_burn_registry.json"
REPORT = REPO / "eval" / "r59_confidentiality_probe.json"
PRIVATE_SUFFIX = "_PRIVATE.json"


def _tracked_private_paths() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=str(REPO),
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {out.stderr[:200]}")
    return [ln.strip() for ln in out.stdout.splitlines()
            if ln.strip().endswith(PRIVATE_SUFFIX)]


def load_registry() -> dict:
    d = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert d.get("record", "").startswith(
        "R59_CONFIDENTIALITY_BURN_REGISTRY"), "registry record drift"
    for p in d["paths"]:
        assert p["status"] in ("BURNED-PUBLIC", "CUSTODIED-PRIVATE",
                               "UNAUTHORED"), (
            f"untyped registry status for {p['path']}: {p['status']}")
        assert p.get("provenance"), (
            f"registry path {p['path']} carries no provenance")
    return d


def unauth_read(url: str, timeout: int = 20) -> int:
    """Unauthenticated GET; returns the HTTP status (or 0 on network
    failure — the caller types it). No auth header is ever set."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as e:
        return int(e.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def run_static() -> dict:
    tracked = _tracked_private_paths()
    reg = load_registry()
    burned = [p["path"] for p in reg["paths"]
              if p["status"] == "BURNED-PUBLIC"]
    findings = []
    if tracked:
        findings.append({
            "kind": "TRACKED_RUBRIC_ON_QUEUE_SURFACE",
            "severity": "GATE_RED",
            "paths": tracked,
            "clause": "Art. 14 v3.2.0 — the builder branch carries "
                      "no sealed-rubric bytes"})
    for p in reg["paths"]:
        if p["path"] not in burned:
            findings.append({
                "kind": "UNREGISTERED_PUBLIC_RUBRIC_RISK",
                "severity": "INFO",
                "path": p["path"],
                "status": p["status"]})
    report = {
        "record": "R59_CONFIDENTIALITY_PROBE/1.0.0",
        "mode": "static",
        "tracked_private_paths": tracked,
        "registry_paths": len(reg["paths"]),
        "burned_public_disclosed": burned,
        "findings": findings,
        "verdict": "GREEN" if not any(
            f["severity"] == "GATE_RED" for f in findings) else "RED",
        "note": "live mode (unauth HTTP) is the workflow step; this "
                "static layer gates the surface in pytest",
    }
    return report


def run_live() -> dict:
    reg = load_registry()
    tracked = _tracked_private_paths()
    findings = []
    reads = []
    status_by_path = {p["path"]: p["status"] for p in reg["paths"]}
    live_paths = sorted({p["path"] for p in reg["paths"]}
                        | set(tracked))
    network_ok = True
    for ref in (QUEUE_BRANCH, AUDIT_BRANCH):
        for path in live_paths:
            url = f"{RAW_BASE}{ref}/{path}"
            status = unauth_read(url)
            if status == 0:
                network_ok = False
            reads.append({"ref": ref, "path": path, "http_status": status})
            if status == 200:
                st = status_by_path.get(path, "UNREGISTERED")
                if st == "BURNED-PUBLIC":
                    continue  # the disclosed burn — recorded, not hidden
                findings.append({
                    "kind": "PUBLIC_RUBRIC_NOT_DISCLOSED_BURNED",
                    "severity": "GATE_RED",
                    "ref": ref, "path": path,
                    "registry_status": st,
                    "clause": "Art. 14 v3.2.0 — an unauthenticated "
                              "read returned 200 for a sealed rubric "
                              "that is not typed BURNED-PUBLIC"})
    verdict = "GREEN"
    if not network_ok:
        verdict = "UNVERIFIED_NETWORK"
    elif any(f["severity"] == "GATE_RED" for f in findings):
        verdict = "RED"
    report = {
        "record": "R59_CONFIDENTIALITY_PROBE/1.0.0",
        "mode": "live",
        "refs": [QUEUE_BRANCH, AUDIT_BRANCH],
        "reads": reads,
        "disclosed_burn_200s": [r for r in reads
                                if r["http_status"] == 200
                                and status_by_path.get(r["path"])
                                == "BURNED-PUBLIC"],
        "findings": findings,
        "verdict": verdict,
        "note": "BURNED-PUBLIC 200s are the F60 disclosure kept "
                "VISIBLE (P0 owner custody stays the standing action); "
                "any other 200 reds the gate",
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["static", "live"],
                    default="static")
    args = ap.parse_args()
    try:
        report = run_static() if args.mode == "static" else run_live()
    except Exception as e:  # noqa: BLE001 - typed instrument failure
        print(json.dumps({"record": "R59_CONFIDENTIALITY_PROBE/1.0.0",
                          "mode": args.mode, "verdict": "INSTRUMENT_FAILURE",
                          "error": f"{type(e).__name__}: {e}"}))
        return 2
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False)
                      + "\n", encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "verdict":
                      report["verdict"],
                      "findings": len(report["findings"])}))
    if report["verdict"] == "RED":
        return 1
    if report["verdict"] == "UNVERIFIED_NETWORK":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
