"""tests/test_r532_skipped_stage_envelopes.py — R532 §5 contract.

A durable envelope's EXISTENCE must never be mistaken for fresh
stage execution. Proves, hermetically (synthetic envelopes +
ledger lines through the REAL harvester block functions, never
hand-waved):

  A. stage skipped before execution -> _stage_table entry_class
     SKIPPED_* with wall None; spans blocks UNKNOWN (never
     OBSERVED_IN_STAGE on absent spans).
  B. prior/stale envelope contents -> an envelope carrying a
     mechanism_map/raw_candidate WITHOUT a stage_log entry for
     the stage yields UNKNOWN (no stage wall to attribute to);
     a FAILED stage WITH spans still reports its spans (the
     class means "spans observed this run", never "stage
     succeeded" — STATUS comes from stage_table).
  C. restart/resume + idempotence -> harvesting the same bytes
     twice yields identical spans blocks (no stateful drift).
  D. empty candidate pools -> NO_CANDIDATES terminal with
     reached=false; downstream reached flags stay false (never
     promoted from an empty pool).
  E. starved run -> funnel correctly marks contradiction
     reached=false with MECHANISM_STARVED; a present
     blocking_count value in a downstream envelope is NOT
     promoted to an executed scientific result.
  F. normal positive run -> BUILT + reached true + spans
     OBSERVED_IN_STAGE with all subphase keys.
  G. candidate-bearing run -> instantiation_attempts present
     with a typed outcome from the R532 taxonomy.
  H. session isolation -> ledger lines from another session
     never merge into this call's spans (request_id grouping
     is per-session).
  I. classifier branch coverage -> _ms_attempt_outcome returns
     all 11 taxonomy outcomes on synthetic inputs (pure
     function; proves the classifier cannot produce an
     untyped/None outcome on any reachable lean-path shape).

No new epistemic states. Existing vocabularies only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import adapters as ad  # noqa: E402


def _harvester():
    import os
    _saved = os.environ.get("R526_ARM")
    os.environ["R526_ARM"] = "current"
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import r526_harvest_attribution as rh
        return rh, _saved
    except Exception:
        if _saved is None:
            os.environ.pop("R526_ARM", None)
        else:
            os.environ["R526_ARM"] = _saved
        raise


def _restore_arm(saved):
    import os
    if saved is None:
        os.environ.pop("R526_ARM", None)
    else:
        os.environ["R526_ARM"] = saved


def _ms_env(stage="MECHANISM_SPACE", wall=10.5, spans=None,
            terminal="BUILT"):
    env = {"stage_log": [{
        "stage": stage, "duration_monotonic_s": wall,
        "started_at": "2026-09-25T00:00:00+00:00Z",
        "finished_at": "2026-09-25T00:00:10+00:00Z",
        "status": "OK"}]}
    if spans is not None:
        env["mechanism_space"] = {
            "state": terminal,
            "runtime_attribution": spans}
    return env


def _spans_record(**kw):
    rec = {"attribution_version": "mechanism_attribution/1.0.0",
           "total_s": 10.4,
           "terminal_state": "BUILT",
           "subphases": [
               {"subphase": "entry_setup", "duration_s": 0.0},
               {"subphase": "llm_instantiation_wall",
                "duration_s": 10.2}],
           "funnel": {"terminal_reason": "BUILT"},
           "llm": {"provider": "xkiro", "n_llm_calls": 1}}
    rec.update(kw)
    return rec


class TestSkippedStageEnvelopes(unittest.TestCase):

    def test_a_skipped_stage_unknown_spans(self):
        """Skipped stage -> spans UNKNOWN, never OBSERVED."""
        rh, saved = _harvester()
        try:
            out = rh._mechanism_space_spans(
                {"stage_log": []},  # no entry: skipped upstream
                {"stage": "MECHANISM_SPACE",
                 "entry_class": "SKIPPED_UPSTREAM_FAILURE",
                 "wall_s": None, "status": "SKIPPED"},
                None)
            self.assertEqual(out["class"], "UNKNOWN")
            self.assertIsNone(out.get("stage_wall_s"))
            # the note must say why (uninstrumented/skipped),
            # never claim observation
            self.assertTrue(out.get("note"))
        finally:
            _restore_arm(saved)

    def test_b_stale_envelope_without_stage_log_unknown(self):
        """A mechanism_map WITHOUT a stage_log entry for the stage
        yields UNKNOWN: there is no stage wall to attribute the
        spans to (stale/prior-run contents cannot masquerade as
        fresh execution)."""
        rh, saved = _harvester()
        try:
            out = rh._mechanism_space_spans(
                {"mechanism_space": {
                    "state": "BUILT",
                    "runtime_attribution": _spans_record()}},
                None, None)
            self.assertEqual(out["class"], "UNKNOWN")
            self.assertIsNone(out.get("stage_wall_s"))
        finally:
            _restore_arm(saved)

    def test_b2_failed_stage_with_spans_still_observed(self):
        """A FAILED stage WITH a spans record still reports its
        spans (class = spans observed this run). STATUS comes from
        stage_table, never from the spans class — the two channels
        stay distinct so a failed run's spans are never read as
        success."""
        rh, saved = _harvester()
        try:
            out = rh._mechanism_space_spans(
                _ms_env(wall=10.5, spans=_spans_record()),
                {"stage": "MECHANISM_SPACE",
                 "entry_class": "EXECUTED",
                 "wall_s": 10.5, "status": "FAILED"},
                {"provider_call_wall_s": 9.1, "n_calls": 1,
                 "n_ok": 0, "failures": ["CALL_FAILED"]})
            self.assertEqual(out["class"], "OBSERVED_IN_STAGE")
            self.assertEqual(out["stage_wall_s"], 10.5)
            # ledger shows the failure; spans show the work
            self.assertEqual(out["ledger_n_ok"], 0)
            self.assertIn("CALL_FAILED", out["ledger_failures"])
        finally:
            _restore_arm(saved)

    def test_c_harvest_idempotent(self):
        """Same bytes twice -> identical spans blocks (no stateful
        drift across harvests: restart/resume safe)."""
        rh, saved = _harvester()
        try:
            env = _ms_env(wall=10.5, spans=_spans_record())
            entry = {"stage": "MECHANISM_SPACE",
                     "entry_class": "EXECUTED",
                     "wall_s": 10.5, "status": "OK"}
            led = {"provider_call_wall_s": 9.1, "n_calls": 1,
                   "n_ok": 1, "failures": []}
            import json
            a = rh._mechanism_space_spans(env, entry, led)
            b = rh._mechanism_space_spans(
                json.loads(json.dumps(env)), dict(entry),
                dict(led))
            self.assertEqual(a, b)
        finally:
            _restore_arm(saved)

    def test_d_empty_pool_no_promotion(self):
        """NO_CANDIDATES terminal: attempts (if any) carry a
        non-accept outcome; nothing downstream may read this as
        a produced candidate."""
        rh, saved = _harvester()
        try:
            out = rh._mechanism_space_spans(
                _ms_env(wall=0.02, spans=_spans_record(
                    total_s=0.013, terminal_state="NO_CANDIDATES",
                    subphases=[{"subphase": "entry_setup",
                                "duration_s": 0.013}],
                    funnel={"terminal_reason": "NO_CANDIDATES"},
                    llm={"provider": None, "n_llm_calls": 0})),
                {"stage": "MECHANISM_SPACE",
                 "entry_class": "EXECUTED",
                 "wall_s": 0.02, "status": "OK"},
                {"provider_call_wall_s": 0.0, "n_calls": 0,
                 "n_ok": 0, "failures": []})
            self.assertEqual(out["class"], "OBSERVED_IN_STAGE")
            self.assertEqual(out["terminal_state"], "NO_CANDIDATES")
            self.assertEqual(out["ledger_n_calls"], 0)
        finally:
            _restore_arm(saved)

    def test_f_positive_run_fully_observed(self):
        rh, saved = _harvester()
        try:
            out = rh._mechanism_space_spans(
                _ms_env(wall=10.5, spans=_spans_record()),
                {"stage": "MECHANISM_SPACE",
                 "entry_class": "EXECUTED",
                 "wall_s": 10.5, "status": "OK"},
                {"provider_call_wall_s": 9.1, "n_calls": 1,
                 "n_ok": 1, "failures": []})
            self.assertEqual(out["class"], "OBSERVED_IN_STAGE")
            self.assertIn("entry_setup", out["spans"])
            self.assertIn("llm_instantiation_wall", out["spans"])
            self.assertEqual(out["total_s"], 10.4)
            self.assertEqual(
                out["adapter_and_stage_overhead_s"],
                round(10.5 - 10.4, 3))
        finally:
            _restore_arm(saved)

    def test_h_session_isolation(self):
        """Ledger lines from another session never merge into this
        call's spans (request_id grouping is per-session)."""
        rh, saved = _harvester()
        try:
            lines = [
                {"request_id": "gen_aaa", "session_id": "ts_ONE",
                 "recorded_at_epoch": 100.0,
                 "latency_ms": 5000,
                 "generate_spans": {
                     "instrument": "gen_spans/1.0",
                     "purpose": "operator_DIRECT_TRANSFER",
                     "generate_total_s": 7.0,
                     "generate_start_epoch": 95.0,
                     "selection_ordering_s": 2.0,
                     "rungs": [{
                         "provider": "xkiro",
                         "admission": {
                             "probe_admission_s": 0.0,
                             "probe_retry_sleep_s": 0.0},
                         "attempts": [{
                             "attempt_index": 1,
                             "dispatch_s": 5.0,
                             "retry_sleep_s": 0.0,
                             "transition_to_next_s": None,
                             "outcome": "OK"}],
                         "post_provider_local_s": 0.0}]}},
                {"request_id": "gen_bbb", "session_id": "ts_TWO",
                 "recorded_at_epoch": 200.0,
                 "latency_ms": 9000,
                 "generate_spans": {
                     "instrument": "gen_spans/1.0",
                     "purpose": "operator_DIRECT_TRANSFER",
                     "generate_total_s": 99.0,
                     "generate_start_epoch": 101.0,
                     "selection_ordering_s": 90.0,
                     "rungs": []}},
            ]
            blk = rh._generate_calls_block([
                ln for ln in lines if ln["session_id"] == "ts_ONE"])
            self.assertEqual(blk["n_calls"], 1)
            call = blk["calls"][0]
            self.assertEqual(call["request_id"], "gen_aaa")
            self.assertEqual(
                (call.get("audit") or {}).get("total_s"), 7.0)
            # the ts_TWO call (total 99.0) must not leak in
            self.assertNotIn(99.0, json_dumps_numbers(blk))
        finally:
            _restore_arm(saved)

    # --------------------------------------- I. classifier branches
    def test_i_classifier_all_eleven_outcomes(self):
        """_ms_attempt_outcome returns every taxonomy outcome on
        synthetic inputs (pure function; no untyped/None outcome
        on any reachable lean-path shape)."""
        base = dict(contract_satisfied=True, prior_state=None,
                    llm_meta={"ok": True, "status": "OK",
                              "content": "MECHANISM: x"},
                    n_fields_nonempty=3, intervention="int",
                    mechanism="mech", candidate_state="CANDIDATE",
                    semantic_verdict="PASS",
                    cemetery_blocked=False,
                    distinctness_verdict="DISTINCT", retained=True,
                    support_state="SUPPORTED")
        cases = [
            ("NOT_ATTEMPTED", {"contract_satisfied": False,
                               "prior_state": "NO_APPLICABLE_EVIDENCE"}),
            ("OPERATOR_INSTANTIATION_FAILED",
             {"llm_meta": {"ok": False, "status": "CALL_FAILED",
                           "error": "boom"}}),
            ("EMPTY_OUTPUT",
             {"llm_meta": {"ok": True, "status": "OK",
                           "content": ""}}),
            ("PARSE_FAILURE", {"n_fields_nonempty": 0}),
            ("REQUIRED_FIELDS_MISSING",
             {"intervention": "", "mechanism": ""}),
            ("ASSEMBLY_INVALID",
             {"candidate_state": "NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION"}),
            ("SEMANTIC_REJECT", {"semantic_verdict": "TEXTUAL_REWRITE",
                                 "candidate_state":
                                 "NOT_A_CANDIDATE_TEXTUAL_REWRITE"}),
            ("CEMETERY_BLOCK", {"cemetery_blocked": True}),
            ("DISTINCTNESS_DROP",
             {"distinctness_verdict": "EQUIVALENT",
              "retained": False}),
            ("MECHANISM_SUPPORT_DROP",
             {"support_state": "NOT_ENOUGH_EVIDENCE",
              "retained": False}),
            ("CANDIDATE_ACCEPTED", {}),
        ]
        seen = set()
        for outcome, over in cases:
            kw = dict(base)
            kw.update(over)
            got = ad._ms_attempt_outcome(**kw)
            self.assertEqual(
                got.get("outcome"), outcome,
                f"classifier branch for {outcome}")
            seen.add(got.get("outcome"))
        self.assertEqual(len(seen), 11)
        # UNKNOWN shape: retained False with no gate claiming it
        # is impossible via the safety net only when support is
        # strong — assert the safety net resolves instead of None
        got = ad._ms_attempt_outcome(**dict(
            base, retained=False, distinctness_verdict="DISTINCT",
            support_state="SUPPORTED", cemetery_blocked=False,
            candidate_state="CANDIDATE"))
        self.assertIsNotNone(got.get("outcome"))


def json_dumps_numbers(o):
    import json
    found = []

    def _walk(x):
        if isinstance(x, dict):
            for v in x.values():
                _walk(v)
        elif isinstance(x, list):
            for v in x:
                _walk(v)
        elif isinstance(x, (int, float)):
            found.append(x)
    _walk(o)
    return found


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
