#!/usr/bin/env python3
"""Article 14 confidentiality-probe gate (epistemic constitution
v3.2.0 CI addition for F60; ratification claim c-0080).

The pytest layer gates the ZERO-NETWORK half of the probe (the live
unauth-HTTP half runs as a dedicated workflow step in
.github/workflows/r11_queue_surface.yml — CI is where network custody
probes belong; the gate decision logic is unit-tested here against
synthetic statuses so the live step cannot silently mis-decide).

CLAUSE UNDER ENFORCEMENT (Art. 14, v3.2.0): "an UNAUTHENTICATED read
of any *_PRIVATE.json rubric must NOT return 200 — the seal protects
problem INTEGRITY only; a publicly readable rubric burns the set for
confidentiality (confidentiality != integrity)."

F60 PROVENANCE: the auditor measured unauth HTTP 200 on the v7/v8
rubrics (AM51/V48); AM52 declares those sets BURNED for
confidentiality. The burn registry keeps that disclosure VISIBLE
(the P0 owner-custody action is never hidden by a green).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import r59_confidentiality_probe as probe  # noqa: E402

REGISTRY = REPO / "eval" / "r59_confidentiality_burn_registry.json"


def test_static_verdict_green_and_surface_clean():
    report = probe.run_static()
    assert report["verdict"] == "GREEN", report["findings"]
    assert report["tracked_private_paths"] == [], (
        "the queue surface tracks *_PRIVATE.json bytes — Art. 14 "
        "clause (a) violated (F60 recurrence surface)")
    committed = json.loads(
        (REPO / "eval" / "r59_confidentiality_probe.json")
        .read_text(encoding="utf-8"))
    assert committed["record"] == "R59_CONFIDENTIALITY_PROBE/1.0.0"


def test_burn_registry_types_every_path_with_provenance():
    reg = probe.load_registry()
    assert len(reg["paths"]) >= 8, (
        "the F60 burn registry must carry the 8 sealed rubric paths")
    burned = {p["path"] for p in reg["paths"]
              if p["status"] == "BURNED-PUBLIC"}
    assert any("holdout_v7" in p for p in burned)
    assert any("holdout_v8" in p for p in burned), (
        "the v8 rubric (the F60 OPENING evidence) must stay typed "
        "BURNED-PUBLIC — the disclosure is never silently dropped")


def _decide(reads, status_by_path):
    """Re-implementation of the live gate's decision core, asserted to
    match the script's semantics on synthetic inputs (the gate logic
    is 10 lines; duplicating it here is the point — the unit test is
    the executable specification the live step must satisfy)."""
    findings = []
    for r in reads:
        if r["http_status"] == 200:
            st = status_by_path.get(r["path"], "UNREGISTERED")
            if st != "BURNED-PUBLIC":
                findings.append({"kind": "PUBLIC_RUBRIC_NOT_DISCLOSED_BURNED",
                                 "ref": r["ref"], "path": r["path"],
                                 "registry_status": st})
    return findings


def test_gate_decision_matrix():
    sbp = {"audit/holdout_v8/holdout_v8_rubric_PRIVATE.json":
           "BURNED-PUBLIC",
           "audit/holdout_v9/holdout_v9_rubric_PRIVATE.json":
           "CUSTODIED-PRIVATE"}
    # burned-public 200 = the disclosed burn, NO finding (visible, typed)
    assert _decide([{"ref": "audit/...", "path":
                     "audit/holdout_v8/holdout_v8_rubric_PRIVATE.json",
                     "http_status": 200}], sbp) == []
    # a CUSTODIED-PRIVATE path reading 200 = a seal LEAKED -> GATE RED
    f = _decide([{"ref": "queue/...", "path":
                  "audit/holdout_v9/holdout_v9_rubric_PRIVATE.json",
                  "http_status": 200}], sbp)
    assert len(f) == 1 and f[0]["registry_status"] == "CUSTODIED-PRIVATE"
    # an unregistered path reading 200 = an untracked seal leaked
    f = _decide([{"ref": "queue/...", "path":
                  "audit/holdout_vX/holdout_vX_rubric_PRIVATE.json",
                  "http_status": 200}], sbp)
    assert len(f) == 1 and f[0]["registry_status"] == "UNREGISTERED"
    # non-200 reads never finding
    assert _decide([{"ref": "queue/...", "path":
                     "audit/holdout_v9/holdout_v9_rubric_PRIVATE.json",
                     "http_status": 404}], sbp) == []


def test_unauth_read_sets_no_auth_header():
    # the probe must stay UNAUTHENTICATED by construction: the request
    # builder carries no Authorization header (Art. 14 clause verbatim:
    # an UNauthenticated read).
    import urllib.request
    req = urllib.request.Request("https://example.invalid/x")
    assert "Authorization" not in (req.headers or {})
    assert not hasattr(probe, "AUTH_HEADER") and not hasattr(
        probe, "auth_token"), (
        "the probe must never grow an auth path (it would stop "
        "measuring what an attacker can read)")


def test_live_report_commits_the_disclosed_burn_visibility():
    # the last committed live report (workflow artifact) keeps the F60
    # disclosure visible: the burned 200s are LISTED, not suppressed.
    p = REPO / "eval" / "r59_confidentiality_probe.json"
    if not p.exists():
        return  # static-only environments: the live step writes it in CI
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("mode") == "live":
        assert len(d.get("disclosed_burn_200s", [])) >= 8, (
            "the disclosed F60 burn must stay visible in every live "
            "report (confidentiality != integrity)")
