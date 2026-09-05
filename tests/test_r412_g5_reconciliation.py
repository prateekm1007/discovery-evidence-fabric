"""tests/test_r412_g5_reconciliation.py — R412 G5 canonical-state correction pins.

R412 Phase 1 closed PCEF-2026-08-20-001 (G5 canonical-state/ledger version
drift) by APPENDING evidence-backed correction transitions through the
authoritative state mechanism (the append-only state transition ledger):

  CV-T06: V6 -> V22.6 (PHYSICAL_VALIDATION_PENDING) — the R6 benchtop
          protocol-hardening advance that had never been ledger-appended,
          anchored to scripts/r6_final_control_hierarchy.py @ 2506e9b5.
  CV-T07: V4 -> V5 (FROZEN_NEGATIVE_CEILING) — re-anchoring the original
          evidence-backed V5 negative-ceiling artifact that the stale
          consolidation-era re-bootstrap masked.

These tests pin the corrected state so a regression (silent overwrite,
history rewrite, or drift re-introduction) fails loudly.
"""

import json
import subprocess
from pathlib import Path

from epistemic_integrity.state_transition_ledger import StateTransitionLedger

REPO = Path(__file__).resolve().parents[1]
LEDGER_DIR = REPO / "epistemic_integrity" / "approved_provenance"
PORTFOLIO = REPO / "CANONICAL_STATE" / "PORTFOLIO.json"


def _ledger():
    return StateTransitionLedger(LEDGER_DIR)


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True, text=True,
        timeout=30)


def test_chain_integrity_holds_after_r412_correction():
    result = _ledger().verify_chain_integrity()
    assert result["chain_valid"], result.get("failures", [])[:3]


def test_projection_matches_portfolio_genuinely():
    """The G5 gate now passes GENUINELY (zero mismatches, no quarantine):
    the ledger projection equals PORTFOLIO.json for every certification-
    scoped territory. A regression in either direction fails here."""
    stl = _ledger()
    portfolio = json.loads(PORTFOLIO.read_text())
    committed = {t["id"]: t for t in portfolio.get("territories", [])}
    by_tid = {}
    for t in stl._events:
        by_tid.setdefault(t.territory_id, []).append(t)
    assert len(by_tid) >= 11, "expected the full territory set in the ledger"
    for tid, evs in sorted(by_tid.items()):
        term = sorted(evs, key=lambda e: e.global_sequence)[-1]
        if term.to_state == "NOT_IN_CERTIFICATION_SCOPE":
            continue
        ct = committed[tid]
        assert ct["current_state"] == term.to_state, (
            f"{tid}: state drift portfolio={ct['current_state']} "
            f"ledger={term.to_state}")
        cv = ct.get("frozen_at_version") or ""
        if cv and term.artifact_version:
            assert cv == term.artifact_version, (
                f"{tid}: version drift portfolio={cv} "
                f"ledger={term.artifact_version}")


def test_cv_t06_terminal_is_v22_6_evidence_backed():
    term = _ledger().get_current_transition("CV-T06")
    assert term.artifact_version == "V22.6"
    assert term.to_state == "PHYSICAL_VALIDATION_PENDING"
    assert term.transition_type == "EVIDENCE_BACKED"
    assert term.artifact_hash, "EVIDENCE_BACKED transitions require artifacts"
    assert "R412" in term.reason


def test_cv_t07_terminal_is_v5_evidence_backed():
    term = _ledger().get_current_transition("CV-T07")
    assert term.artifact_version == "V5"
    assert term.to_state == "FROZEN_NEGATIVE_CEILING"
    assert term.transition_type == "EVIDENCE_BACKED"
    assert term.artifact_hash, "EVIDENCE_BACKED transitions require artifacts"
    assert "R412" in term.reason


def test_stale_bootstrap_events_preserved_verbatim():
    """Art. XI: the correction SUPERSEDES the stale re-bootstraps by
    sequence position; it must not rewrite or remove them. The stale
    events (V6 bootstrap for CV-T06, V4 bootstrap for CV-T07) remain in
    the ledger verbatim."""
    stl = _ledger()
    t06 = stl.get_transition_chain("CV-T06")
    t07 = stl.get_transition_chain("CV-T07")
    stale_t06 = [e for e in t06 if e.artifact_version == "V6"
                 and e.transition_type == "BOOTSTRAPPED_FROM_CANONICAL_STATE"]
    stale_t07 = [e for e in t07 if e.artifact_version == "V4"
                 and e.transition_type == "BOOTSTRAPPED_FROM_CANONICAL_STATE"]
    assert stale_t06, "the historical V6 bootstrap events must be preserved"
    assert stale_t07, "the historical V4 bootstrap events must be preserved"
    # and they are NOT terminal anymore
    assert t06[-1].artifact_version == "V22.6"
    assert t07[-1].artifact_version == "V5"


def test_correction_artifacts_actually_exist_in_history():
    """The correction transitions anchor real artifacts: the R6 V22.6
    control-hierarchy blob at its introducing commit, and the T07 V5
    final-adjudication blob. Anchors that point at nothing would be
    fabricated provenance (Art. VI)."""
    r = _git("show", "2506e9b5:scripts/r6_final_control_hierarchy.py")
    assert r.returncode == 0 and r.stdout
    r = _git("show",
             "6720fada:CEREVASC_TERRITORY_7_V5_M5_ATTACK/"
             "V5_FINAL_ADJUDICATION.json")
    assert r.returncode == 0 and r.stdout


def test_pcef_record_remediated_and_archived():
    """PCEF-2026-08-20-001 is closed: remediation_state=REMEDIATED,
    status=ARCHIVED, with a revalidation entry citing the R412
    reconciliation evidence. The quarantine is retired by remediation,
    not by expiry or silence (Art. LXV)."""
    pcef = json.loads(
        (REPO / "CANONICAL_STATE" /
         "PRE_EXISTING_CERTIFICATION_FAILURES.json").read_text())
    assert pcef["record_id"] == "PCEF-2026-08-20-001"
    assert pcef["remediation_state"] == "REMEDIATED"
    assert pcef["status"] == "ARCHIVED"
    history = pcef.get("revalidation_history", [])
    assert history, "REMEDIATED requires a recorded revalidation entry"
    last = history[-1]
    for field in ("revalidated_at", "revalidated_by", "commit_sha",
                  "evidence_hash", "rationale"):
        assert last.get(field), f"revalidation entry missing {field}"
    assert "R412" in last["rationale"]
