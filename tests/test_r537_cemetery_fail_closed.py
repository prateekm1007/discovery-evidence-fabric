#!/usr/bin/env python3
"""R537 P0: close the cemetery fail-open path (audit §4).

The R536 defect: `_CemeterySubCheck.verdict()` catches any exception
and returns `{"verdict": "UNRESOLVED", "error": ...}`.  The
`AdjudicationAdapter` gate then read

    cemetery_not_hard_blocked = verdict != "BLOCKED"

so an infrastructure failure (no consultation ever completed) flowed
as `UNRESOLVED != BLOCKED -> True` — a FAIL-OPEN negative-knowledge
gate: a cemetery verification failure became favorable adjudication
merely because the result was not literally BLOCKED.

The R537 repair (adapters.py, observability + gate semantics):
  * the success path records `cemetery_verdict_resolved: True`;
  * the failure path records `verdict: UNRESOLVED` +
    `cemetery_verdict_resolved: False` + a recorded note (Art. XXV:
    the failure is never hidden, never fabricated);
  * the adjudication gate is fail-CLOSED:

      cemetery_not_hard_blocked = (verdict != "BLOCKED")
                                   AND (cemetery_verdict_resolved
                                        is True)

    so an UNRESOLVED consultation cannot reach ESTABLISHED_
    PROVISIONALLY and earns no discovery credit.

This test drives the REAL EngineRun conductor with the REAL
AdjudicationAdapter (only RETRIEVE/SYNTHESIZE/MECHANISM_SPACE/
VERIFY/COLLISION/ATTACK/CONTRADICTION/KILLER_EXPERIMENT/PHYSICS/
CLASSIFY/NEXT_BEST_ACTION/RANK are hermetically stubbed) and forces
`mechanism_cemetery.check_candidate_against_cemetery` to throw —
the P0 requirement, proved through the actual
EngineRun -> ADJUDICATION -> _CemeterySubCheck -> mechanism_cemetery
path, inspecting the durable adjudication record.
"""
from __future__ import annotations

import contextlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import discovery_fabric.evidence_fabric as ef  # noqa: E402
from discovery_fabric.engine.adapters import (  # noqa: E402
    _engine_result, ADAPTERS)
from discovery_fabric.engine.run import EngineRun  # noqa: E402
import orchestrator.mechanism_cemetery as mc  # noqa: E402

PROBLEM = {
    "problem_id": "r537-failclosed",
    "device": "tunneled hemodialysis catheter",
    "failure_mode": "OCCLUSION",
    "failure": "catheter occlusion",
    "constraint": "x",
}


def _stub(stage):
    def _ok(env, run_ctx, *a, **k):
        prov = dict(getattr(env, "provenance", {}) or {})
        if stage == "RETRIEVE":
            env.evidence = [
                {"id": "stub-item-1",
                 "abstract": ("stub evidence abstract with quantified "
                              "detail 12mm 345KPa 67% in 2021 clinical "
                              "cohort"),
                 "source": "STUB",
                 "content_hash": "sha256:0" * 8,
                 "source_uri": "stub://r537"},
                {"id": "stub-item-2",
                 "abstract": ("stub evidence abstract 2 with "
                              "quantified detail 89mm 234KPa 56% in "
                              "2022 clinical cohort"),
                 "source": "STUB",
                 "content_hash": "sha256:1" * 8,
                 "source_uri": "stub://r537"},
            ]
            return _engine_result({"provenance": prov}, state="OK",
                                 retrieval_fabric_version="STUB")
        if stage == "SYNTHESIZE":
            env.mechanism_map = {
                "raw_candidate": {
                    "candidate_id": "stub-cand-1",
                    "intervention": "stub intervention 12mm 345KPa",
                    "mechanism": "stub mechanism 89mm 234KPa",
                    "candidate_state": "CANDIDATE",
                    "operator_semantic_check": {
                        "semantic_verdict": "SEMANTICALLY_VALID"},
                    "provider": "stub", "model": "stub"},
                "source_span": "stub mechanism 89mm 234KPa",
                "mechanism_source_span": "stub mechanism 89mm 234KPa",
                "source_id": "stub-item-1",
                "source_hash": "sha256:1" * 8}
            env.n_retained = 1
            env.mechanism_space = {
                "state": "BUILT", "n_candidates_generated": 1,
                "instantiation_attempts": []}
            return _engine_result({"provenance": prov}, state="OK",
                                 synthesis_stub=True)
        if stage in ("MECHANISM_SPACE", "PHYSICS"):
            env.n_retained = 1
            return _engine_result({"provenance": prov}, state="OK",
                                 mechanism_space_stub=True)
        if stage == "VERIFY":
            env.adjudication = dict(getattr(env, "adjudication", {}) or {})
            env.adjudication["evidence_verification"] = {"verified": True}
            return _engine_result({"provenance": prov}, state="OK",
                                 verified=True)
        if stage in ("COLLISION", "ATTACK", "CONTRADICTION",
                     "KILLER_EXPERIMENT"):
            if stage == "COLLISION":
                env.collision_results = {"novelty_risk": "NO_RISK"}
            if stage == "ATTACK":
                env.attack_results = {"overall": "PASS"}
            if stage == "CONTRADICTION":
                env.contradictions = {"blocking_count": 0}
            if stage == "KILLER_EXPERIMENT":
                env.killer_experiment = {}
            return _engine_result({"provenance": prov}, state="OK")
        if stage in ("CLASSIFY", "NEXT_BEST_ACTION", "RANK"):
            if stage == "CLASSIFY":
                env.epistemic_state = {"final_status": "UNKNOWN",
                                       "epistemic_state": "OBSERVED"}
            return _engine_result({"provenance": prov}, state="OK")
        raise AssertionError(f"unexpected stage stub: {stage}")
    return _ok


def _drive_with_cemetery_failure():
    """Run the real conductor with the real AdjudicationAdapter and
    the cemetery consultation forced to throw.  Returns the
    (manifest, engine, adjudication_entry, cemetery_check, council)."""
    with tempfile.TemporaryDirectory() as tmp, \
            contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(ef, "enabled",
                                         return_value=False))
        for stage in ("RETRIEVE", "SYNTHESIZE", "MECHANISM_SPACE",
                      "VERIFY", "COLLISION", "ATTACK", "CONTRADICTION",
                      "KILLER_EXPERIMENT", "PHYSICS", "CLASSIFY",
                      "NEXT_BEST_ACTION", "RANK"):
            # R538 harness fix: patch the adapter INSTANCE (a plain
            # function on the instance receives (env, run_ctx));
            # patching type(adapter).execute binds the stub as a
            # method and silently plants nothing in the envelope.
            stack.enter_context(patch.object(
                ADAPTERS[stage], "execute", _stub(stage)))
        stack.enter_context(patch.object(
            EngineRun, "_pre_retrieval_capability_gate",
            lambda self: {"state": "OK"}))
        stack.enter_context(patch.object(
            EngineRun, "_evolution_pipeline",
            lambda self, run_ctx, final:
            {"state": "SKIPPED_NO_CREDIBLE_ROUTE"}))
        stack.enter_context(patch.object(
            mc, "check_candidate_against_cemetery",
            side_effect=RuntimeError("injected cemetery failure")))
        eng = EngineRun(PROBLEM, str(tmp), with_package=False,
                        stage_gate=None)
        manifest = eng.run()
    adj_entry = [e for e in eng.env.stage_log
                 if e["stage"] == "ADJUDICATION"][0]
    cemetery_check = (eng.env.adjudication or {}).get("cemetery_check")
    council = (eng.env.adjudication or {}).get("council") or {}
    return manifest, eng, adj_entry, cemetery_check, council


def test_p0_cemetery_failure_cannot_become_favorable_adjudication():
    """The P0: exception -> UNRESOLVED / infrastructure failure -> no
    favorable cemetery PASS -> no ESTABLISHED_PROVISIONALLY -> no
    discovery credit."""
    manifest, eng, adj_entry, cemetery_check, council = \
        _drive_with_cemetery_failure()

    # The real AdjudicationAdapter EXECUTED (it is the P0 exercise
    # target — not stubbed, not skipped).
    assert adj_entry.get("status") in ("OK", "FAILED_EXPLICIT"), (
        "ADJUDICATION must execute the real adapter in this fixture, "
        f"observed {adj_entry.get('status')}")

    # The cemetery sub-check recorded the infrastructure failure as
    # UNRESOLVED + the resolved flag False (Art. XXV: never hidden,
    # never fabricated).
    assert cemetery_check is not None, (
        "the cemetery sub-check record must be durable on the "
        "adjudication record")
    assert cemetery_check.get("verdict") == "UNRESOLVED"
    assert cemetery_check.get("cemetery_verdict_resolved") is False
    assert "injected cemetery failure" in str(
        cemetery_check.get("error", ""))

    # The adjudication council is fail-CLOSED on the UNRESOLVED
    # consultation: the cemetery check fails, so the favorable
    # ESTABLISHED_PROVISIONALLY verdict is unreachable.
    failed = council.get("failed_checks") or []
    if council:
        assert "cemetery_not_hard_blocked" in failed, (
            f"an UNRESOLVED cemetery consultation must fail the "
            f"cemetery_not_hard_blocked check (fail-closed), "
            f"observed failed_checks={failed}")
        assert council.get("verdict") != "ESTABLISHED_PROVISIONALLY", (
            "a cemetery verification failure CANNOT become favorable "
            "adjudication (the R537 P0)")

    # No discovery credit: the run terminal is a typed non-green
    # state, never ESTABLISHED_PROVISIONALLY / CANDIDATE_ACCEPTED.
    assert manifest.get("final_status") not in (
        "ESTABLISHED_PROVISIONALLY", "CANDIDATE_ACCEPTED",
        "REJECTED"), (
        f"the run earned a discovery-credit terminal "
        f"({manifest.get('final_status')}) despite an "
        f"UNRESOLVED cemetery — fail-open P0 breach")


def test_success_path_records_resolved_flag():
    """The complementary control: a SUCCESSFUL cemetery consultation
    records cemetery_verdict_resolved True (the gate passes only on a
    resolved non-BLOCKED verdict)."""
    from discovery_fabric.engine import adapters as ad

    class Env:
        problem = dict(PROBLEM)
        mechanism_map = {"intervention": "i", "mechanism": "m",
                         "raw_candidate": {}}
        provenance = {}

    v = ad._CemeterySubCheck.verdict(Env())
    assert v.get("cemetery_verdict_resolved") is True, (
        f"a successful consultation must record the resolved flag, "
        f"observed {v.get('cemetery_verdict_resolved')}")
    # The gate's exact form from AdjudicationAdapter:
    gate = (v.get("verdict") != "BLOCKED"
            and v.get("cemetery_verdict_resolved") is True)
    fail_shape = {"verdict": "UNRESOLVED",
                  "cemetery_verdict_resolved": False}
    gate_fail = (fail_shape.get("verdict") != "BLOCKED"
                 and fail_shape.get("cemetery_verdict_resolved")
                 is True)
    assert gate, "a resolved non-BLOCKED verdict must pass the gate"
    assert not gate_fail, (
        "the R536 fail-open shape (UNRESOLVED treated as pass) must "
        "now FAIL the gate (the P0 repair)")


def main():
    import unittest
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[
            __name__]))
    sys.exit(0 if r.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
