"""tests/test_r399_gates.py — R399 W2: the cost/epistemic gates.

Intentional behavior changes (each documented per the R399 regression
gate rule 5 — 'every intentional behavior change must be explicitly
documented and tested'):

  W2.5  the skip cascade: after an upstream stage is SKIPPED, every
        stage downstream of it records SKIPPED_UPSTREAM_FAILURE (never
        OK-on-empty-input; the audit measured COLLISION..RANK reporting
        OK after RETRIEVE failed and SYNTHESIZE/VERIFY were skipped).
        The ENTRY JUSTIFICATION (one shared helper) stamps every stage
        entry with WHY it consumed compute (or honestly didn't).
  W2.3  the diversity grid + ensemble require >= 1 VERIFIED_EVIDENCE_
        ITEM: zero verified items -> SKIPPED_EVIDENCE_VERIFICATION_
        FAILED with the measured counts (no LLM candidates generated on
        unverified evidence).
  W2.1  a scientifically REJECTED run generates NO buyer dossier/PDF/
        ZIP artifacts (no package number, no CAD pass, no package
        report) — the epistemic record up to selection is complete and
        the release record stays honest (status != RELEASED with the
        reason).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_f_series_integration import (  # noqa: E402
    _survivor_env, CHAIN_PLAN)
from discovery_fabric.engine.run import EngineRun, DOWNSTREAM_BLOCKERS
from discovery_fabric.engine import stage_entry
from discovery_fabric.engine.candidate import Candidate


# ----------------------------------------------------------------------
# 1. The one shared helper: entry justification
# ----------------------------------------------------------------------

def test_entry_helper_allowed_and_skipped_vocabulary():
    env = Candidate(problem={"device": "x"}, problem_id="t")
    ok = stage_entry.justify("RETRIEVE", env, {}, set())
    assert ok["entry_status"] == "ALLOWED"
    assert ok["prerequisite"] == "UPSTREAM_COMPLETE"
    assert ok["prerequisite_evidence"] is not None

    skipped = stage_entry.justify(
        "ATTACK", env, {"SYNTHESIZE": "transport dead"}, set())
    assert skipped["entry_status"] == "SKIPPED"
    assert skipped["prerequisite"] == "UPSTREAM_COMPLETE"
    assert "UPSTREAM_TERMINAL_FAILURE" in skipped["skip_reason"]
    assert "SYNTHESIZE" in skipped["skip_reason"]

    # the cascade: SYNTHESIZE merely SKIPPED (not failed) still blocks
    cascade = stage_entry.justify("ATTACK", env, {}, {"SYNTHESIZE"})
    assert cascade["entry_status"] == "SKIPPED"
    assert "SKIPPED_UPSTREAM_FAILURE" in cascade["skip_reason"]


def test_entry_helper_verified_evidence_prerequisite():
    env = Candidate(problem={"device": "x"}, problem_id="t")
    # no classification at all -> not satisfied
    gate = stage_entry.justify("EXPLORATION_GRID", env, {}, set())
    assert gate["entry_status"] == "SKIPPED"
    assert gate["prerequisite"] == "VERIFIED_EVIDENCE"
    assert "EVIDENCE_VERIFICATION_FAILED" in gate["skip_reason"]
    assert gate["prerequisite_evidence"]["n_verified_evidence_items"] == 0

    # one DIRECT_SUPPORT item -> satisfied, counts recorded
    env.evidence_classification = {
        "n_items": 3,
        "counts": {"DIRECT_SUPPORT": 1, "PARTIAL_SUPPORT": 0,
                   "BACKGROUND": 2, "ANALOGY": 0, "CONTRADICTORY": 0,
                   "IRRELEVANT": 0},
        "items": [{"classification": "DIRECT_SUPPORT"},
                  {"classification": "BACKGROUND"},
                  {"classification": "BACKGROUND"}],
    }
    gate = stage_entry.justify("EXPLORATION_GRID", env, {}, set())
    assert gate["entry_status"] == "ALLOWED"
    assert gate["prerequisite_evidence"]["n_direct_support"] == 1

    # BACKGROUND only -> still not verified evidence for the mechanism
    env.evidence_classification["items"] = [
        {"classification": "BACKGROUND"}] * 3
    gate = stage_entry.justify("EXPLORATION_GRID", env, {}, set())
    assert gate["entry_status"] == "SKIPPED"


def test_downstream_blockers_cover_all_stages():
    # every stage except the roots must be downstream of some blocker
    roots = {"RETRIEVE", "FREEZE", "PREMISE_GATE"}
    covered = set()
    for blocked in DOWNSTREAM_BLOCKERS.values():
        covered |= blocked
    from discovery_fabric.engine.adapters import STAGE_ORDER
    assert covered >= set(STAGE_ORDER) - roots
    assert "PHYSICS" in DOWNSTREAM_BLOCKERS["PREMISE_GATE"]
    assert "PHYSICS" in DOWNSTREAM_BLOCKERS["SYNTHESIZE"]


# ----------------------------------------------------------------------
# 2. The skip cascade, end-to-end (audit's measured defect)
# ----------------------------------------------------------------------

def test_retrieve_failure_cascades_to_rank(tmp_path, monkeypatch):
    """A RETRIEVE failure skips SYNTHESIZE/VERIFY (existing behavior) —
    and now EVERY downstream stage records SKIPPED_UPSTREAM_FAILURE
    instead of executing OK on the empty envelope."""
    problem = {"problem_id": "r399-cascade",
               "device": "tunneled hemodialysis catheter",
               "failure_mode": "OCCLUSION",
               "failure": "catheter occlusion",
               "constraint": "x"}
    from discovery_fabric.engine import adapters
    calls = {"n": 0}

    def dead_retrieve(env, run_ctx):
        calls["n"] += 1
        raise RuntimeError("provider unreachable (fixture)")

    monkeypatch.setattr(
        adapters.A2RetrievalAdapter, "execute", dead_retrieve)
    run = EngineRun(problem, str(tmp_path), with_package=False)
    manifest = run.run()
    # classification never ran (skipped) -> the run is not a candidate
    # outcome (never fabricated). R416: a retrieval-dead run fails the
    # mechanism GENERATION (typed, infrastructure-class — never a
    # rejection); the evolution layer (transport also dead in the
    # hermetic suite) records the same typed terminal.
    assert manifest["final_status"] in (
        "UNKNOWN", "MECHANISM_GENERATION_FAILED")
    log = {e["stage"]: e["status"] for e in run.env.stage_log}
    assert log["RETRIEVE"] == "FAILED_EXPLICIT"
    assert log["SYNTHESIZE"] == "SKIPPED_UPSTREAM_FAILURE"
    assert log["VERIFY"] == "SKIPPED_UPSTREAM_FAILURE"
    # the R399 fix: everything downstream of the SKIP is skipped too —
    # no stage reports OK on an empty envelope
    for stage in ("MULTI_SOURCE_DISCOVERY", "COLLISION", "PHYSICS",
                  "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
                  "ADJUDICATION", "CLASSIFY", "NEXT_BEST_ACTION", "RANK"):
        assert log[stage] == "SKIPPED_UPSTREAM_FAILURE", stage
    # the entry justification is stamped on the skip records
    skip_entries = [e for e in run.env.stage_log
                    if e["status"] == "SKIPPED_UPSTREAM_FAILURE"]
    assert all(e.get("entry", {}).get("entry_status") == "SKIPPED"
               for e in skip_entries)
    assert any("UPSTREAM_TERMINAL_FAILURE" in
               e["entry"]["skip_reason"] for e in skip_entries)


# ----------------------------------------------------------------------
# 3. W2.3: the grid + ensemble evidence gate
# ----------------------------------------------------------------------

from tests.test_f_series_integration import CHAIN_PLAN, CTX


def _rejected_run_env():
    """A full-chain fixture whose naive candidate the loop REJECTED.

    The chain stages are executed OFFLINE through the fixture (the
    f-series _offline_chain pattern) so the conductor sees them done
    and only the post-RANK pipeline under test runs (hermetic: no LLM,
    no network)."""
    env = _survivor_env("fluidics_hydraulic", variant=421, chain=True)
    env.epistemic_state = {
        "final_status": "REJECTED",
        "reason": "fixture: evidence verification failed (audit W2.2 case)",
        "adjudication_blocked": False,
    }
    # zero verified evidence items: classification says BACKGROUND only
    env.evidence_classification = {
        "classifier_version": "evidence_classification/1.0.0",
        "n_items": len(env.evidence or []),
        "counts": {"DIRECT_SUPPORT": 0, "PARTIAL_SUPPORT": 0,
                   "BACKGROUND": len(env.evidence or []),
                   "ANALOGY": 0, "CONTRADICTORY": 0, "IRRELEVANT": 0},
        "items": [{"classification": "BACKGROUND"}
                  for _ in (env.evidence or [])],
        "mechanism_support": {"n_direct_support": 0,
                              "n_contradictory": 0},
    }
    env.adjudication = {"evidence_verification": {
        "verified": False, "evidence_class": "UNSUPPORTED",
        "issues": ["mechanism_span_not_verbatim"]}}
    return env


def test_grid_and_ensemble_skipped_on_unverified_evidence(tmp_path):
    env = _rejected_run_env()
    # phase 1: persist the fixture chain (D1 pattern) — every stage has
    # an OK envelope snapshot so the resumed conductor treats the chain
    # as done and ONLY the post-RANK pipeline under test executes
    run1 = EngineRun(env.problem, str(tmp_path), run_id="testrun:r399-grid-gate",
                     with_package=True)
    run1.env = env
    run1._persist("problem.json", run1.problem)
    for stage in ("RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
                  "VERIFY", "MULTI_SOURCE_DISCOVERY", "COLLISION",
                  "PHYSICS", "ATTACK", "CONTRADICTION",
                  "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
                  "NEXT_BEST_ACTION", "RANK"):
        run1._persist_envelope(stage)
    # phase 2: resume with the pre-chain stages disabled (offline
    # fixture; the conductor marks them DISABLED_BY_CONFIG)
    run2 = EngineRun.from_run_dir(
        str(tmp_path),
        disabled_stages=["RETRIEVE", "FREEZE", "PREMISE_GATE",
                         "SYNTHESIZE", "MULTI_SOURCE_DISCOVERY",
                         "COLLISION", "ATTACK"])
    manifest = run2.run()
    grid = json.loads((tmp_path / "EXPLORATION_GRID.json").read_text())
    assert grid["status"] == "SKIPPED_EVIDENCE_VERIFICATION_FAILED"
    assert grid["entry"]["entry_status"] == "SKIPPED"
    assert grid["entry"]["prerequisite"] == "VERIFIED_EVIDENCE"
    assert "EVIDENCE_VERIFICATION_FAILED" in grid["reason"]
    ens = json.loads((tmp_path / "ENSEMBLE_DISAGREEMENT.json").read_text())
    assert ens["status"] == "SKIPPED_EVIDENCE_VERIFICATION_FAILED"
    # no LLM candidates were generated: no grid specs on disk
    assert not list(tmp_path.glob("INVENTION_SPECIFICATION_grid-*.json"))
    # honest release record, no package
    rel = json.loads((tmp_path / "DISCOVERY_RELEASE.json").read_text())
    assert rel["status"] != "RELEASED"
    assert not (tmp_path / "PACKAGE_REPORT.json").exists()


# ----------------------------------------------------------------------
# 4. W2.1: scientifically rejected runs buy no dossier compute
# ----------------------------------------------------------------------

def test_rejected_run_generates_no_package_artifacts(tmp_path):
    """The audit's W2.1 case: a run classified REJECTED (scientific)
    records its epistemic outcome and STOPS before the expensive CAD
    pass, package-number allocation, PDF/ZIP/render and quality-gate
    compute. Operational failures (UNKNOWN/adjudication_blocked) do NOT
    take this gate — their state stays resumable."""
    env = _rejected_run_env()
    # give the selection a candidate to pick: verify one item so the
    # grid gate passes but the run stays REJECTED (the W2.1 case —
    # a grid candidate survives the gauntlet on a rejected run)
    env.evidence_classification["items"][0]["classification"] = \
        "DIRECT_SUPPORT"
    env.evidence_classification["counts"]["DIRECT_SUPPORT"] = 1
    env.evidence_classification["counts"]["BACKGROUND"] -= 1

    run1 = EngineRun(env.problem, str(tmp_path),
                     run_id="testrun:r399-package-gate",
                     with_package=True,
                     package_registry_path=str(
                         tmp_path / "sandbox_registry.json"))
    run1.env = env
    run1._persist("problem.json", run1.problem)
    for stage in ("RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
                  "VERIFY", "MULTI_SOURCE_DISCOVERY", "COLLISION",
                  "PHYSICS", "ATTACK", "CONTRADICTION",
                  "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
                  "NEXT_BEST_ACTION", "RANK"):
        run1._persist_envelope(stage)
    # hermetic candidate generation: the grid + ensemble produce a
    # fixture candidate (the GATES are what is under test, not the
    # LLM candidates — the W2.2 test above covers the gate itself)
    import discovery_fabric.engine.candidate_diversity as _cd
    import discovery_fabric.engine.ensemble as _ens
    # the grid fixture candidate reuses the SURVIVOR fixture's own
    # mechanism fields (the rich narrative that passes the E15-B
    # quality gate offline — the f-series D1 pattern)
    _fields = {k: v for k, v in env.mechanism_map.items()
               if k in ("mechanism", "intervention",
                        "expected_effect", "falsification_test",
                        "mechanism_source_span")}
    _fields["span_derivation"] = None
    _cd.generate_diverse_candidates = lambda problem, evidence: {
        "status": "OK", "grid": "fixture",
        "candidates": [{
            "candidate_id": "cand:DIV:fixture",
            "angle": "constraint_first", "provider_id": "fixture",
            "fields": _fields}]}
    _ens.ensemble_synthesize = lambda problem, evidence: {
        "ensemble": "fixture", "status": "OK", "members": []}

    run2 = EngineRun.from_run_dir(
        str(tmp_path),
        disabled_stages=["RETRIEVE", "FREEZE", "PREMISE_GATE",
                         "SYNTHESIZE", "MULTI_SOURCE_DISCOVERY",
                         "COLLISION", "ATTACK"],
        package_registry_path=str(tmp_path / "sandbox_registry.json"))
    manifest = run2.run()

    # the honest skip record exists with the measured basis
    skipped = json.loads(
        (tmp_path / "PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json")
        .read_text())
    assert skipped["entry_status"] == "SKIPPED"
    assert skipped["prerequisite"] == \
        "CANDIDATE_NOT_SCIENTIFICALLY_REJECTED"
    assert skipped["prerequisite_evidence"]["final_status"] == "REJECTED"
    # and NONE of the expensive artifacts ran:
    assert not (tmp_path / "CAD_PIPELINE_LEDGER.json").exists()
    assert not (tmp_path / "PACKAGE_REPORT.json").exists()
    assert not (tmp_path / "DOWNLOAD").exists()
    # no package number was allocated: the registry file itself was
    # never created (allocation is the first act of packaging — the
    # gate sits before it; a registry that exists must carry no
    # allocation for this run)
    reg_path = tmp_path / "sandbox_registry.json"
    if reg_path.exists():
        reg = json.loads(reg_path.read_text())
        allocated = [p for p in (reg.get("packages") or [])
                     if str(p.get("run_id", "")).startswith("testrun:r399")]
        assert allocated == []
    else:
        assert not (tmp_path / "PACKAGE_REPORT.json").exists()
    # the release record is honest and carries the reason
    rel = json.loads((tmp_path / "DISCOVERY_RELEASE.json").read_text())
    assert rel["status"] != "RELEASED"
    # R416: the GEN-1 REJECTED verdict is preserved in the epistemic
    # record (W2.1 skip record above + cemetery + lineage); the
    # run-level final_status is now the evolution-aware product state
    # (the hermetic suite has no transport, so no evolved generation
    # was produced and nothing was softened into a survivor).
    assert manifest["final_status"] in (
        "REJECTED", "INVENTION_UNDER_DEVELOPMENT",
        "MECHANISM_GENERATION_FAILED")
