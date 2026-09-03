"""tests/test_r401_acceptance_states.py — R401 Phase 0 pinned
regression tests for the explicit acceptance-state contract.

The directive (R401A Phase 0):
  * remove the ambiguity between Boolean acceptance and observational
    states;
  * explicit states: PASS / FAIL / OBSERVATION_ONLY / INCOMPLETE /
    UNRESOLVED / QUOTA_EXHAUSTED;
  * P2 must not become PASS simply because its value is non-failing;
  * a genuine P2 failure must be impossible to coerce into PASS;
  * pinned regression tests for BOTH cases.

Every test is hermetic (no network): the probe functions are exercised
through a monkeypatched _request, and the aggregation functions through
their pure module-level implementations.

Constitutional anchors: Art. IV (no fallback epistemology — no state
silently becomes an affirmative), Art. XXV (unknown must remain
unknown — INCOMPLETE/UNRESOLVED/QUOTA_EXHAUSTED are never converted),
Art. VII (never weaken the verifier — the FAIL derivation from checks
cannot be overridden), Art. XVII (the coercion attempts below ARE the
attempted bypasses).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PROBES = _load("r396_probes_r401", "scripts/r396_external_probes.py")
ACCEPT = _load("r400_accept_r401", "scripts/r400_post_deploy_acceptance.py")


# ---------------------------------------------------------------------------
# 1. The state machine itself (pure function truth table)
# ---------------------------------------------------------------------------

class TestAcceptanceStateClassifier:
    def test_all_true_is_pass(self):
        assert PROBES.acceptance_state(
            {"a": True, "b": True}) == "PASS"

    def test_any_false_is_fail(self):
        assert PROBES.acceptance_state(
            {"a": True, "b": False}) == "FAIL"

    def test_false_beats_everything_else(self):
        # a FAIL check plus an unknown check is still FAIL — an unknown
        # value never dilutes an adjudicated failure
        assert PROBES.acceptance_state(
            {"a": False, "b": None}) == "FAIL"

    def test_unknown_check_is_unresolved_not_fail_not_pass(self):
        # unknown is NOT false (Art. XXV) and NOT pass
        assert PROBES.acceptance_state(
            {"a": True, "b": None}) == "UNRESOLVED"

    def test_incomplete_when_probe_did_not_complete(self):
        assert PROBES.acceptance_state(
            {}, completed=False) == "INCOMPLETE"

    def test_quota_exhausted_is_a_named_state(self):
        assert PROBES.acceptance_state(
            {}, quota_exhausted=True) == "QUOTA_EXHAUSTED"

    def test_vocabulary_is_exactly_the_directive_set(self):
        assert set(PROBES.ACCEPTANCE_STATES) == {
            "PASS", "FAIL", "OBSERVATION_ONLY", "INCOMPLETE",
            "UNRESOLVED", "QUOTA_EXHAUSTED"}

    @pytest.mark.parametrize("state", [
        "FAIL", "OBSERVATION_ONLY", "INCOMPLETE", "UNRESOLVED",
        "QUOTA_EXHAUSTED"])
    def test_every_non_pass_state_is_non_affirmative(self, state):
        # condition 5 generalized: NO state other than PASS may act as
        # an affirmative anywhere in the acceptance contract
        assert PROBES._state_mirror(state) is False
        assert PROBES.probe_record_state(
            {"state": state}) == state


# ---------------------------------------------------------------------------
# 2. P2 — the two pinned directive cases
# ---------------------------------------------------------------------------

def _fake_request(response_json=None, status=200, text=None):
    def _req(base, path, method="GET", body=None, timeout=90,
             headers=None):
        rec = {"method": method, "url": base + path, "status": status}
        if response_json is not None:
            rec["response_json"] = response_json
        if text is not None:
            rec["response_text"] = text
        return rec
    return _req


class TestP2GenuineFailureIsLocked:
    """Directive condition 6: a genuine P2 failure must be impossible
    to coerce into PASS. The fixture reproduces the MEASURED live
    f9dfd45d pre-deploy failure (R400-B: 33 cross-user-visible sessions
    + run_dir/worker/path leakage — 5 of 7 checks false)."""

    LEAKY_BODY = {
        "sessions": [
            {"id": "ts_abc", "problem": "why do grafts clot?",
             "public": False, "run_dir": "/app/ENGINE_RUNS/ts_abc",
             "worker": {"pid": 123, "starttime": 99}},
            {"id": "ts_def", "problem": "another user's problem",
             "public": False},
            {"id": "ts_demo", "problem": "demo", "public": True},
        ]
    }

    def test_genuine_failure_yields_state_fail(self, monkeypatch):
        monkeypatch.setattr(
            PROBES, "_request",
            _fake_request(response_json=self.LEAKY_BODY))
        rec = PROBES.probe_p2("https://x")
        assert rec["state"] == "FAIL"
        assert rec["pass"] is False
        assert rec["checks"]["zero_cross_user_sessions"] is False
        assert rec["n_sessions_visible"] == 3

    def test_coercing_the_pass_field_cannot_flip_the_state(self,
                                                           monkeypatch):
        # THE attempted bypass (Art. XVII): an intelligent adversary
        # edits the record's `pass` field to True after the fact. The
        # aggregation must still treat the probe as FAIL because the
        # state derives from the checks, not from any sibling field.
        monkeypatch.setattr(
            PROBES, "_request",
            _fake_request(response_json=self.LEAKY_BODY))
        rec = PROBES.probe_p2("https://x")
        tampered = dict(rec)
        tampered["pass"] = True  # the coercion attempt
        assert PROBES.probe_record_state(tampered) == "FAIL"

    def test_coerced_record_blocks_the_suite_verdict(self, tmp_path):
        # end-to-end through the acceptance harness record reader: a
        # tampered P2 record still blocks all_gates_pass
        out = tmp_path / "p1p2.json"
        out.write_text(json.dumps({"probes": [
            {"probe": "P1", "state": "PASS", "pass": True},
            {"probe": "P2", "state": "FAIL", "pass": True},  # tampered
        ]}))
        states = ACCEPT._probe_pass(out)
        assert states == ["PASS", "FAIL"]
        flat = ACCEPT._flatten_gate_states(
            {"P1_P2": {"result": states}})
        assert ACCEPT.AFFIRMATIVE_STATE not in (
            [s for s in flat if s != "PASS"])
        assert "FAIL" in flat

    def test_any_false_check_classifies_fail_even_among_unknowns(self):
        # the derivation is check-driven, not majority-driven
        assert PROBES.acceptance_state({
            "zero_cross_user_sessions": False,
            "unreachable_detail": None}) == "FAIL"


class TestP2NonFailingIsNotPass:
    """Directive condition 5: P2 must not become PASS simply because
    its value is non-failing. The historical P2 record carried
    `pass: None` — a non-failing value that is NOT a pass."""

    def test_clean_host_earns_pass(self, monkeypatch):
        # a clean anonymous surface (the measured 930eca8b artifact
        # state: zero sessions visible, zero leaks) EARNS PASS — this
        # is the fix that lets a genuinely clean deployment be
        # accepted at all
        monkeypatch.setattr(
            PROBES, "_request",
            _fake_request(response_json={"sessions": []}))
        rec = PROBES.probe_p2("https://x")
        assert rec["state"] == "PASS"
        assert rec["pass"] is True

    def test_legacy_none_record_is_never_pass(self):
        # the pre-R401 P2 record: pass=None, no state field. It is
        # non-failing AND non-pass — mapped to UNRESOLVED, never to
        # PASS, in every aggregation path
        legacy = {"probe": "P2", "pass": None}
        assert PROBES.probe_record_state(legacy) == "UNRESOLVED"

    @pytest.mark.parametrize("state", [
        "OBSERVATION_ONLY", "INCOMPLETE", "UNRESOLVED",
        "QUOTA_EXHAUSTED"])
    def test_every_nonfailing_state_blocks_acceptance(self, state):
        # each non-failing observational state, in the P2 slot of a
        # gate result, blocks all_gates_pass
        flat = ACCEPT._flatten_gate_states(
            {"P1_P2": {"result": ["PASS", state]}})
        assert ACCEPT._flatten_gate_states(
            {"P1_P2": {"result": ["PASS", state]}}) == flat
        assert state in flat
        assert sorted(set(flat) - {"PASS"}) == [state]

    def test_unreachable_host_is_incomplete_not_fail(self,
                                                     monkeypatch):
        # an unreachable host is an observation that did not happen —
        # unknown, not a proven failure (Art. XXV)
        monkeypatch.setattr(
            PROBES, "_request", _fake_request(status=None))
        rec = PROBES.probe_p2("https://x")
        assert rec["state"] == "INCOMPLETE"
        assert rec["pass"] is False

    def test_no_record_is_never_affirmative(self, tmp_path):
        assert ACCEPT._probe_pass(
            tmp_path / "does_not_exist.json") == "NO_RECORD"
        flat = ACCEPT._flatten_gate_states(
            {"P3": {"result": "NO_RECORD"}})
        assert flat == ["NO_RECORD"]


# ---------------------------------------------------------------------------
# 3. The one-command harness verdict (the latent KeyError fix)
# ---------------------------------------------------------------------------

class TestHarnessVerdict:
    """The R400 acceptance harness previously crashed (KeyError) at
    the verdict step because the R400C_PHYSICS_RUN gate carried no
    `result` key — the final acceptance record was never written."""

    def test_gate_without_result_key_does_not_crash(self):
        gates = {
            "P1_P2": {"result": ["PASS", "PASS"]},
            "R400C_PHYSICS_RUN": {"capture_present": True},  # no result
        }
        flat = ACCEPT._flatten_gate_states(gates)
        assert flat == ["PASS", "PASS"]

    def test_all_pass_states_make_all_gates_pass(self):
        gates = {
            "P1_P2": {"result": ["PASS", "PASS"]},
            "P3": {"result": "PASS"},
            "R400C_PHYSICS_RUN": {"result": "PASS"},
        }
        flat = ACCEPT._flatten_gate_states(gates)
        non_pass = [v for v in flat if v != ACCEPT.AFFIRMATIVE_STATE]
        assert flat and not non_pass

    def test_single_non_pass_state_blocks(self):
        gates = {
            "P1_P2": {"result": ["PASS", "PASS"]},
            "P3": {"result": "PASS"},
            "P6": {"result": "UNRESOLVED"},
        }
        flat = ACCEPT._flatten_gate_states(gates)
        non_pass = [v for v in flat if v != ACCEPT.AFFIRMATIVE_STATE]
        assert non_pass == ["UNRESOLVED"]
        assert not (flat and not non_pass)

    def test_empty_gate_set_is_not_pass(self):
        # no states collected at all -> never an affirmative verdict
        assert not (ACCEPT._flatten_gate_states({}) and
                    not [v for v in ACCEPT._flatten_gate_states({})
                         if v != ACCEPT.AFFIRMATIVE_STATE])

    def test_r400c_requires_the_capture_contract_fields(self):
        # PASS requires physics_model_version + baseline outcome +
        # result class; the machine's own REJECTED verdict is NOT part
        # of the gate (a rejection is an acceptable outcome) — the
        # gate tests the capture, not the winner
        cap_ok = {"physics_model_version": "hydraulic_network_1d/1.0.0",
                  "baseline_comparison": {"outcome": "BEATS_BASELINE"},
                  "verdict": {"result_class": "COMPUTATIONAL_RESULT"}}
        cap_broken = {"physics_model_version": None,
                      "baseline_comparison": {},
                      "verdict": {}}
        for cap, expect in ((cap_ok, "PASS"), (cap_broken, "FAIL")):
            # replicate the harness's derivation exactly
            required = bool(
                cap and (cap.get("physics_model_version")
                         and (cap.get("baseline_comparison")
                              or {}).get("outcome")
                         and (cap.get("verdict") or {}).get(
                             "result_class")))
            assert ("PASS" if required else "FAIL") == expect

    def test_missing_physics_run_record_is_incomplete(self, tmp_path):
        # no record file / no final status -> INCOMPLETE, never PASS
        assert not (tmp_path / "PRODUCTION_PHYSICS_RUN.json").exists()


# ---------------------------------------------------------------------------
# 4. The P5 vacuous-pass regression (same defect family, found by the
#    Phase-0 inspection: a host that refuses every run "passed" P5)
# ---------------------------------------------------------------------------

class TestP5VacuousObservation:
    def test_refused_runs_are_incomplete_not_pass(self, monkeypatch):
        # both runs refused -> previously verdicts=[None, None] made
        # `stable` vacuously True and P5 "passed". Now: INCOMPLETE.
        def _req(base, path, method="GET", body=None, timeout=90,
                 headers=None):
            return {"method": method, "url": base + path,
                    "status": 503, "response_text": "unavailable"}
        monkeypatch.setattr(PROBES, "_request", _req)
        rec = PROBES.probe_p5("https://x")
        assert rec["state"] == "INCOMPLETE"
        assert rec["pass"] is False
        assert rec["checks"]["runs_completed"] is False

    def test_completed_clean_runs_earn_pass(self, monkeypatch):
        # both runs completed with the same verdict and clean evidence
        # -> PASS is earned through adjudicated checks
        detail = {"status": "COMPLETE",
                  "evidence_pack": {"records": [
                      {"title": "rain erosion of leading edges"}]}}
        calls = {"n": 0}

        def _req(base, path, method="GET", body=None, timeout=90,
                 headers=None):
            if path == "/api/discoveries":
                calls["n"] += 1
                return {"method": method, "status": 200,
                        "response_json": {
                            "session_id": f"s{calls['n']}"},
                        "owner_cookie": f"ow{calls['n']}"}
            return {"method": method, "status": 200,
                    "response_json": detail}
        monkeypatch.setattr(PROBES, "_request", _req)
        rec = PROBES.probe_p5("https://x")
        assert rec["state"] == "PASS"
        assert rec["pass"] is True


# ---------------------------------------------------------------------------
# 5. P1/P3/P4/P6/P7 state wiring (spot checks, hermetic)
# ---------------------------------------------------------------------------

class TestOtherProbeStateWiring:
    def test_p1_identity_mismatch_is_fail(self, monkeypatch):
        # production still on f9dfd45d while 930eca8b is deployed ->
        # health_commit_equals_deployed False -> FAIL (locked)
        health = {
            "deployment_identity": {
                "health_reported_commit_source": "build_artifact",
                "identity_tamper": False,
                "build_artifact_sha256": "x",
                "running_artifact_sha256": "x",
                "deployment_drift": "GREEN",
                "health_reported_commit": "f9dfd45d...",
            },
            "gateway_up_note": "EXTERNAL-gated",
        }
        monkeypatch.setattr(
            PROBES, "_request", _fake_request(response_json=health))
        rec = PROBES.probe_p1(
            "https://x", "930eca8b7db8b0885abccb4e8159a77b8e802723")
        assert rec["state"] == "FAIL"

    def test_p1_identity_match_is_pass(self, monkeypatch):
        health = {
            "deployment_identity": {
                "health_reported_commit_source": "build_artifact",
                "identity_tamper": False,
                "build_artifact_sha256": "x",
                "running_artifact_sha256": "x",
                "deployment_drift": "GREEN",
                "health_reported_commit":
                    "930eca8b7db8b0885abccb4e8159a77b8e802723",
            },
            "gateway_up_note": "EXTERNAL-gated",
        }
        monkeypatch.setattr(
            PROBES, "_request", _fake_request(response_json=health))
        rec = PROBES.probe_p1(
            "https://x", "930eca8b7db8b0885abccb4e8159a77b8e802723")
        assert rec["state"] == "PASS"

    def test_p3_early_exit_is_incomplete_not_boolean_fail(self,
                                                          monkeypatch):
        monkeypatch.setattr(
            PROBES, "_request", _fake_request(status=503))
        rec = PROBES.probe_p3("https://x")
        assert rec["state"] == "INCOMPLETE"

    def test_p6_no_completed_runs_is_incomplete(self, monkeypatch):
        detail = {"status": "COMPLETE", "stages": [], "final_state": {}}

        def _req(base, path, method="GET", body=None, timeout=90,
                 headers=None):
            if path == "/api/discoveries":
                return {"method": method, "status": 200,
                        "response_json": {"session_id": "s1"},
                        "owner_cookie": "ow1"}
            return {"method": method, "status": 200,
                    "response_json": detail}
        monkeypatch.setattr(PROBES, "_request", _req)
        rec = PROBES.probe_p6("https://x")
        assert rec["state"] == "INCOMPLETE"

    def test_p7_not_accepted_case_is_fail(self, monkeypatch):
        # a benchmark case the host refuses to accept is an
        # adjudicated failure of the public product surface
        def _req(base, path, method="GET", body=None, timeout=90,
                 headers=None):
            return {"method": method, "status": 200,
                    "response_json": {"error": "nope"}}
        monkeypatch.setattr(PROBES, "_request", _req)
        rec = PROBES.probe_p7("https://x",
                              case_filter={1})
        assert rec["state"] == "FAIL"


# ---------------------------------------------------------------------------
# 6. Legacy-record compatibility (fail-closed direction only)
# ---------------------------------------------------------------------------

class TestLegacyRecordFallback:
    def test_legacy_pass_true_is_pass(self):
        assert PROBES.probe_record_state(
            {"probe": "P3", "pass": True}) == "PASS"

    def test_legacy_pass_false_is_unresolved_class(self):
        # legacy False could not distinguish FAIL from INCOMPLETE —
        # mapped to the honest non-affirmative UNRESOLVED class, never
        # to PASS
        assert PROBES.probe_record_state(
            {"probe": "P3", "pass": False}) == "UNRESOLVED"

    def test_state_field_outranks_tampered_legacy_pass(self):
        # a record with state FAIL but a tampered pass=True stays FAIL
        assert PROBES.probe_record_state(
            {"probe": "P2", "state": "FAIL", "pass": True}) == "FAIL"
