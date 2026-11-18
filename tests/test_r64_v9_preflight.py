#!/usr/bin/env python3
"""CI-gated guard for the v9 one-shot pre-flight invariants (claim
c-0087): the seal replica verifies at the pinned audit sha, the
instrument stays structurally rubric-isolated, the frozen-loop
byte-baselines hold, and the attestation plumbing is present.

Discipline: the frozen files' baselines are CHECKED HERE, not
regenerated — any future edit to a frozen file must consciously update
eval/r64_v9_preflight.json's baselines in the same commit (the
auditor's re-freeze act), and until then CI stays red. The pre-flight
NEVER executes the instrument and NEVER probes any gateway.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r64_v9_preflight import (  # noqa: E402
    AUDIT_SHA_DEFAULT, attestation_plumbing, freeze_baselines,
    instrument_constant, rubric_isolation_proof, run_preflight,
    verify_seal_replica)
import hashlib


def _load_record():
    rec = json.loads((REPO / "eval" / "r64_v9_preflight.json")
                     .read_text(encoding="utf-8"))
    assert rec["verdict"].startswith("PREFLIGHT_PASS"), rec["verdict"]
    return rec


def test_preflight_passes_at_pinned_audit_sha():
    rec = run_preflight(AUDIT_SHA_DEFAULT, None)
    assert rec["verdict"].startswith("PREFLIGHT_PASS")
    assert rec["checks"]["seal_recipe_replica"]["verified"]
    assert rec["checks"]["problem_count_and_mix"]["ok"]
    assert rec["checks"]["problem_schema_fields"]["ok"]
    assert rec["checks"]["preregistration"]["burn_after_use"] is True


def test_recorded_record_matches_pinned_run():
    """The committed record is the pinned run's own output (no
    hand-edited evidence)."""
    rec = _load_record()
    assert rec["audit_sha_pinned"] == AUDIT_SHA_DEFAULT
    live = run_preflight(AUDIT_SHA_DEFAULT, None)
    assert (live["checks"]["seal_recipe_replica"]["recomputed"]
            == rec["checks"]["seal_recipe_replica"]["recomputed"])
    assert (live["checks"]["freeze_baselines_sha16"]
            == rec["checks"]["freeze_baselines_sha16"]), (
        "a frozen file drifted from the recorded baseline — update the "
        "baselines consciously (the re-freeze act) or revert")


def test_instrument_stays_rubric_isolated():
    src = (REPO / "scripts" / "r60_v9_one_shot.py").read_text(
        encoding="utf-8")
    iso = rubric_isolation_proof(src)
    assert iso["isolated"], iso
    assert iso["rubric_mentions"] >= 1, (
        "the custody contract prose must stay in the instrument")


def test_instrument_constants_undrifted():
    src = (REPO / "scripts" / "r60_v9_one_shot.py").read_text(
        encoding="utf-8")
    machine = (REPO / "scripts" / "r40_machine_v77.py").read_text(
        encoding="utf-8")
    assert instrument_constant(src, "EXPECTED_SEAL") == (
        "502e93d84b19dcda5b0a7d656a3195e509ddec8247aad2e6b"
        "ddec082e10f34ce")
    assert instrument_constant(src, "EXPECTED_N") == "30"
    # the registered model is OWNED by the frozen machine module and
    # re-asserted by the instrument at run time (byte-reuse) — the
    # r64s4 owner-directed registration superseding R36 per AM60
    # (contract-fit decided: agnes-3.0-flash)
    assert re.search(r'^V77_REQUEST_MODEL\s*=\s*"agnes-3.0-flash"',
                     machine, re.M), "registered model drifted"
    assert 'm.V77_REQUEST_MODEL == "agnes-3.0-flash"' in src, (
        "the instrument's byte-reuse assertion went missing")
    assert "engine_route" in instrument_constant(src, "MEASURED_PATH")


def test_attestation_plumbing_complete_on_current_bytes():
    src = (REPO / "scripts" / "r60_v9_one_shot.py").read_text(
        encoding="utf-8")
    assert attestation_plumbing(src)["complete"]


def test_frozen_loop_bytes_hold():
    rec = _load_record()
    now = freeze_baselines()
    assert now == rec["checks"]["freeze_baselines_sha16"], (
        {k: (now.get(k), rec["checks"]["freeze_baselines_sha16"].get(k))
         for k in now
         if now.get(k) != rec["checks"]["freeze_baselines_sha16"].get(k)})


def test_preregistration_seal_matches_instrument():
    """Drift guard: the prereg at the pinned audit sha carries the same
    seal the instrument asserts (checked inside the pre-flight too —
    here it guards the RECORD's evidence chain)."""
    rec = _load_record()
    s = rec["checks"]["seal_recipe_replica"]
    assert s["recomputed"] == s["doc_selection_sha256"] == \
        s["prereg_selection_sha256"] == s["instrument_expected_seal"]
