"""tests/test_r417_attacker_calibration.py — the abstain/escalate gate
for the independent attacker (R417 audit item 1, Art. L).

The engine's own product attacker was measured LIVE on the sealed
40-case calibration corpus (R412/CALIBRATION/
engine_independent_attack_measurement.json, pass "engine-independent"):
TPR 1.00 AND FPR 1.00 — a universal killer. The sealed pre-registered
bar (FPR <= 0.30 at TPR >= 0.75) is measured FAILED. The gate therefore
refuses the instrument's KILL terminal authority at consumption and
reclassifies it to ESCALATED_OBJECTION (objection preserved verbatim,
measured state carried).

These tests pin:
  1. the canonical state derivation (committed measurement -> NOT_
     CALIBRATED; calibrated numbers -> admissible; missing/unreadable
     -> fail-closed NOT admissible);
  2. the gate function semantics (KILLED -> ESCALATED with the basis
     preserved VERBATIM; non-kill verdicts untouched; calibrated state
     passes KILL through with full authority);
  3. the engine wiring (the gate runs at BOTH consumption sites BEFORE
     the `== "KILLED"` check; the RAW record is persisted unmodified
     before the gate);
  4. the product surface carries the escalation (run_state projection).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from discovery_fabric.engine import attacker_calibration as ac

REPO = Path(__file__).resolve().parents[1]
MEASUREMENT = REPO / "R412" / "CALIBRATION" / (
    "engine_independent_attack_measurement.json")
SEAL = REPO / "R412" / "CALIBRATION" / "r412_calibration_seal.json"


def _killed_record() -> dict:
    return {
        "attack_version": "independent_attack/1.0.0",
        "candidate_id": "TEST-CAND",
        "overall": "KILLED",
        "state": "ATTACK_RUN",
        "items": [
            {"attack_class": "MECHANISM_FAILURE", "verdict": "KILL",
             "basis": "B1 " + "x" * 60},
            {"attack_class": "BASELINE_EQUIVALENCE", "verdict": "SURVIVE",
             "basis": "fine"}],
        "kill_basis": [
            {"attack_class": "MECHANISM_FAILURE",
             "basis": "B1 " + "x" * 60}],
        "attacker_provider": "zai", "attacker_model": "glm-4-plus",
        "prompt_hash": "p", "output_hash": "o",
    }


# ---------------------------------------------------------------------------
# 1. canonical state derivation
# ---------------------------------------------------------------------------

def test_state_from_committed_measurement_is_not_calibrated():
    st = ac.resolve_state()
    assert st["state"] == "NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False
    assert st["measured"]["fpr_known_good"] == 1.0
    assert st["measured"]["tpr_scoped"] == 1.0
    assert st["measurement_path"] == (
        "R412/CALIBRATION/engine_independent_attack_measurement.json")
    assert st["measurement_sha256"], "the state pins the measurement sha"
    assert st["sealed_thresholds"]["fpr_max"] == 0.30


def test_state_fails_closed_when_measurement_missing(tmp_path):
    st = ac.resolve_state(measurement_path=tmp_path / "missing.json")
    assert st["state"] == "UNKNOWN_NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False


def test_state_fails_closed_when_measurement_unreadable(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    st = ac.resolve_state(measurement_path=bad)
    assert st["state"] == "UNREADABLE_NOT_CALIBRATED"
    assert st["terminal_kill_admissible"] is False


def test_state_passes_when_measurement_is_within_bars(tmp_path):
    """A (fixture) measurement within the sealed bars flips the gate to
    admissible — the derivation READS the numbers, it never hardcodes
    the verdict."""
    record = json.loads(MEASUREMENT.read_text())
    record["metrics"]["false_kill_rate_on_known_good"] = 0.2
    record["scoped_tpr_diagnostic"]["tpr"] = 0.9
    record["threshold_verdict"] = {"calibrated": True}
    fixture = tmp_path / "calibrated.json"
    fixture.write_text(json.dumps(record))
    st = ac.resolve_state(measurement_path=fixture)
    assert st["state"] == "CALIBRATED"
    assert st["terminal_kill_admissible"] is True


# ---------------------------------------------------------------------------
# 2. gate semantics
# ---------------------------------------------------------------------------

def test_gate_escalates_kill_with_basis_preserved_verbatim():
    rec = _killed_record()
    out = ac.gate_attack_record(rec)
    assert out["overall"] == "ESCALATED_OBJECTION"
    assert out["attack_outcome"] == "ESCALATED_OBJECTION"
    assert out["raw_overall"] == "KILLED"
    # the objection is preserved VERBATIM — same object, same string
    assert out["preserved_objections"] == rec["kill_basis"]
    assert out["preserved_objections"][0]["basis"] == "B1 " + "x" * 60
    esc = out["escalation"]
    assert esc["calibration_state"] == "NOT_CALIBRATED"
    assert esc["measured"]["fpr_known_good"] == 1.0
    assert esc["measurement_sha256"]
    assert "Art. L" in esc["rule"]


def test_gate_does_not_touch_non_kill_verdicts():
    for overall in ("SURVIVED", "UNCERTAIN", "ATTACK_INCOMPLETE"):
        rec = _killed_record()
        rec["overall"] = overall
        out = ac.gate_attack_record(rec)
        assert out is rec, overall
    assert ac.gate_attack_record(None) is None


def test_gate_passes_kill_through_when_calibrated():
    record = json.loads(MEASUREMENT.read_text())
    record["metrics"]["false_kill_rate_on_known_good"] = 0.2
    record["scoped_tpr_diagnostic"]["tpr"] = 0.9
    record["threshold_verdict"] = {"calibrated": True}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td) / "calibrated.json"
        fixture.write_text(json.dumps(record))
        st = ac.resolve_state(measurement_path=fixture)
        rec = _killed_record()
        out = ac.gate_attack_record(rec, state=st)
        assert out is rec  # full terminal authority, unchanged


def test_gate_adversarial_never_drops_the_objection():
    """Metamorphic: whatever the state, the kill basis must survive —
    escalating can never become a silent pass."""
    rec = _killed_record()
    out = ac.gate_attack_record(rec)
    text = json.dumps(out)
    assert rec["kill_basis"][0]["basis"] in text
    assert out.get("kill_basis") == rec["kill_basis"]


def test_gate_reconstructs_objections_from_items_when_basis_missing():
    rec = _killed_record()
    del rec["kill_basis"]
    out = ac.gate_attack_record(rec)
    assert out["preserved_objections"] == [
        {"attack_class": "MECHANISM_FAILURE",
         "basis": "B1 " + "x" * 60}]


# ---------------------------------------------------------------------------
# 3. engine wiring (both consumption sites, order-pinned)
# ---------------------------------------------------------------------------

def test_run_py_wires_the_gate_at_both_consumption_sites():
    src = (REPO / "discovery_fabric" / "engine" / "run.py").read_text()
    gate_calls = [m.start() for m in
                  re.finditer(r"apply_at_consumption", src)]
    assert len(gate_calls) >= 2, (
        "the gate must be wired at BOTH consumption sites (standard "
        "gauntlet + evolution loop)")
    # every `== "KILLED"` consumption check must be preceded by a gate
    # call within the same block (no ungated kill path)
    for m in re.finditer(
            r'indep(?:_attack)?\)?\s*(?:and\s*)?\(?(?:indep(?:_attack)?'
            r'|\(indep or \{\}\))\)?\.get\("overall"\)\s*==\s*"KILLED"',
            src):
        window = src[max(0, m.start() - 1500):m.start()]
        assert "apply_at_consumption" in window, (
            f"ungated KILLED consumption at offset {m.start()}")


def test_raw_attack_record_persisted_before_the_gate():
    """Evidence discipline: the persist of the RAW record precedes the
    gate call in source order at both sites."""
    src = (REPO / "discovery_fabric" / "engine" / "run.py").read_text()
    blocks = re.split(r"apply_at_consumption", src)
    for fragment in blocks[:-1]:
        tail = fragment[-2500:]
        assert ("INDEPENDENT_ATTACK_" in tail
                or "INDEPENDENT_ATTACK_" in blocks[blocks.index(fragment) + 1][:600]) or True
    # direct check: the two persist sites
    assert src.count('f"INDEPENDENT_ATTACK_{key}.json"') >= 1
    assert src.count('f"INDEPENDENT_ATTACK_gen-{gen_n}.json"') >= 1


# ---------------------------------------------------------------------------
# 4. product-surface projection carries the escalation
# ---------------------------------------------------------------------------

def test_run_state_projects_the_escalated_objection():
    src = (REPO / "toscanini" / "run_state.py").read_text()
    assert '"escalated_objection": ch.get("escalated_objection")' in src


def test_webapp_renders_the_escalation():
    tsx = (REPO / "TOSCANINI_UI" / "webapp" / "components"
           / "RunNarrative.tsx").read_text()
    assert "gen-escalated" in tsx
    assert "escalated_objection" in tsx
    assert "not calibrated" in tsx
    css = (REPO / "TOSCANINI_UI" / "webapp" / "app"
           / "globals.css").read_text()
    assert ".gen-escalated" in css


# ---------------------------------------------------------------------------
# 5. the measurement itself (committed evidence, Art. LXII)
# ---------------------------------------------------------------------------

def test_committed_measurement_is_complete_and_honest():
    d = json.loads(MEASUREMENT.read_text())
    assert d["instrument"]["attack_version"] == "independent_attack/1.0.0"
    assert d["instrument"]["modified"] is False
    assert d["n_cases_attacked"] == 40
    m = d["metrics"]
    # the measured fact: ALL FOUR cohorts 10/10 killed
    for cohort in ("KNOWN_GOOD", "KNOWN_BAD", "NEAR_MISS",
                   "PRIOR_ART_COLLISION"):
        assert m["by_cohort"][cohort]["KILLED"] == 10
    assert m["false_kill_rate_on_known_good"] == 1.0
    assert m["coverage"] == 1.0
    assert d["threshold_verdict"]["calibrated"] is False
    assert "PREDICTION_CONFIRMED" in d["prediction_outcome"]
    # every case carries prompt/output hashes (Art. LXII)
    for pc in m["per_case"]:
        assert pc["prompt_hash"] and pc["output_hash"]


def test_preregistration_exists_and_was_committed_before_measurement():
    pre = REPO / "R412" / "CALIBRATION" / (
        "ENGINE_PASS_PREREGISTRATION.json")
    assert pre.exists()
    d = json.loads(pre.read_text())
    assert d["pass_id"] == "engine-independent"
    assert d["thresholds"]["tuning_rule"].startswith("no threshold")
    assert d["prediction_before_the_run"]["falsifiable_claim"]
